"""ProviderBus - Centralized bus for coordinating all provider API calls.

Solves the multi-instance rate limiting problem by providing a singleton
that all provider calls route through, ensuring shared rate limit state
across sessions, agents, and provider instances.

Key features:
- Global singleton for cross-session coordination
- Shared rate limit tracking per provider
- Concurrency control via per-provider semaphores
- 429 handling with automatic backoff
- Event emission for observability
- Support for both local and Redis-backed rate limiters

Example:
    from dawn_kestrel.llm.provider_bus import provider_bus

    # All provider calls automatically go through the bus
    result = await provider_bus.execute("zai", lambda: provider.stream(...))
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from dawn_kestrel.core.event_bus import Events, bus
from dawn_kestrel.core.result import Err, Ok, Result
from dawn_kestrel.llm.provider_limits import (
    PROVIDER_LIMITS,
    LocalRateLimitTracker,
    ProviderRateLimit,
    RateLimitTracker,
    create_rate_limit_tracker,
    get_provider_limit,
)

if TYPE_CHECKING:
    pass

from dawn_kestrel.core.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ProviderBus:
    """Singleton bus that coordinates all provider API calls.

    Ensures rate limits are respected across all sessions and provider
    instances. All provider API calls should route through this bus.

    Features:
    - Shared rate limit state (local or Redis-backed)
    - Per-provider concurrency control via semaphores
    - Automatic 429 handling with backoff
    - Event emission for monitoring

    Thread Safety:
        Not thread-safe. Designed for async single-process use.
        For multi-process, use Redis-backed rate limiter.
    """

    _instance: ProviderBus | None = None

    def __init__(
        self,
        rate_tracker: RateLimitTracker | None = None,
        backend: str = "local",
        redis_url: str | None = None,
    ) -> None:
        """Initialize the provider bus.

        Args:
            rate_tracker: Optional custom rate tracker. If None, creates one.
            backend: "local" for in-memory, "redis" for distributed.
            redis_url: Redis URL (required if backend="redis").
        """
        if rate_tracker is not None:
            self._rate_tracker = rate_tracker
        else:
            self._rate_tracker = create_rate_limit_tracker(backend=backend, redis_url=redis_url)

        # Per-provider semaphores for concurrency control
        self._semaphores: dict[str, asyncio.Semaphore] = {}

        # Track active requests per provider for monitoring
        self._active_requests: dict[str, int] = {}

        # Statistics
        self._stats: dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "rate_limited_requests": 0,
            "429_errors": 0,
            "total_wait_time_ms": 0,
        }

        # Lock for atomic updates
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> ProviderBus:
        """Get the global singleton instance.

        Creates the instance on first call using settings for Redis configuration.
        Subsequent calls return the same instance.

        Returns:
            The global ProviderBus singleton.
        """
        if cls._instance is None:
            # Read Redis config from settings
            redis_url = settings.redis_url
            backend = settings.rate_limit_backend

            # Override backend to redis if URL is set
            if redis_url and backend == "local":
                backend = "redis"
                logger.info(f"Redis URL configured, switching to Redis backend")

            cls._instance = cls(backend=backend, redis_url=redis_url)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance.

        Useful for testing or when switching rate limit backends.
        """
        cls._instance = None

    def _get_semaphore(self, provider_id: str) -> asyncio.Semaphore:
        """Get or create semaphore for provider.

        Args:
            provider_id: Provider identifier.

        Returns:
            Semaphore for the provider.
        """
        if provider_id not in self._semaphores:
            limit = get_provider_limit(provider_id)
            self._semaphores[provider_id] = asyncio.Semaphore(limit.concurrent_requests)
        return self._semaphores[provider_id]

    async def _emit_request_event(
        self,
        provider_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Emit a provider request event to the event bus.

        Args:
            provider_id: Provider identifier.
            event_type: Event type (queued, started, completed, rate_limited).
            data: Optional additional data.
        """
        event_data = {
            "provider_id": provider_id,
            "event_type": event_type,
            "timestamp": time.time(),
            "active_requests": self._active_requests.get(provider_id, 0),
        }
        if data:
            event_data.update(data)
        await bus.publish(Events.PROVIDER_REQUEST_QUEUED, event_data)

    async def execute(
        self,
        provider_id: str,
        operation: Callable[[], Awaitable[T]],
        max_429_retries: int = 3,
    ) -> Result[T]:
        """Execute a provider operation with rate limiting and concurrency control.

        All provider API calls should go through this method to ensure
        proper rate limiting across all sessions.

        Args:
            provider_id: Provider identifier (e.g., "zai", "openai").
            operation: Async callable that performs the actual API call.
            max_429_retries: Maximum retries on 429 errors.

        Returns:
            Result containing the operation result or an error.
        """
        provider_key = provider_id.lower().replace("-", "_")
        semaphore = self._get_semaphore(provider_key)
        limit = get_provider_limit(provider_key)

        async with self._lock:
            self._stats["total_requests"] += 1

        # Check rate limit before acquiring semaphore
        check_result = await self._rate_tracker.check_allowed(provider_key)
        if check_result.is_err():
            return Err(
                f"Rate limit check failed",
                code="RATE_LIMIT_CHECK_ERROR",
            )

        allowed, wait_seconds = check_result.unwrap()

        if not allowed:
            async with self._lock:
                self._stats["rate_limited_requests"] += 1
                self._stats["total_wait_time_ms"] += int(wait_seconds * 1000)

            logger.info(f"Rate limit reached for {provider_key}, waiting {wait_seconds:.2f}s")
            await self._emit_request_event(
                provider_key,
                "rate_limited",
                {"wait_seconds": wait_seconds},
            )
            await asyncio.sleep(wait_seconds)

        # Acquire semaphore for concurrency control
        async with semaphore:
            async with self._lock:
                self._active_requests[provider_key] = self._active_requests.get(provider_key, 0) + 1

            await self._emit_request_event(provider_key, "started")

            try:
                # Execute with 429 retry handling
                last_error: Exception | None = None
                for attempt in range(max_429_retries + 1):
                    try:
                        result = await operation()

                        async with self._lock:
                            self._stats["successful_requests"] += 1

                        return Ok(result)

                    except Exception as e:
                        error_str = str(e).lower()
                        is_429 = (
                            "rate limit" in error_str
                            or "1302" in error_str  # Z.AI rate limit code
                            or "429" in error_str
                        )

                        if is_429 and attempt < max_429_retries:
                            async with self._lock:
                                self._stats["429_errors"] += 1

                            # Record 429 for circuit breaker tracking
                            backoff = limit.calculate_backoff_with_jitter(attempt)
                            await self._rate_tracker.record_429(provider_key, backoff)

                            logger.warning(
                                f"Rate limit hit for {provider_key}, "
                                f"retrying in {backoff:.2f}s (attempt {attempt + 1}/{max_429_retries})"
                            )
                            await self._emit_request_event(
                                provider_key,
                                "rate_limited",
                                {"attempt": attempt + 1, "backoff": backoff},
                            )
                            await asyncio.sleep(backoff)
                            continue

                        last_error = e
                        break

                # All retries exhausted
                async with self._lock:
                    self._stats["successful_requests"] += 0  # Keep for clarity

                error_msg = str(last_error) if last_error else "Unknown error"
                return Err(
                    f"Provider operation failed after {max_429_retries} retries: {error_msg}",
                    code="PROVIDER_ERROR",
                    retryable=True,
                )

            finally:
                async with self._lock:
                    current = self._active_requests.get(provider_key, 0)
                    self._active_requests[provider_key] = max(0, current - 1)

                await self._emit_request_event(provider_key, "completed")

    async def execute_stream(
        self,
        provider_id: str,
        operation: Callable[[], Awaitable[AsyncIterator[T]]],
    ) -> AsyncIterator[Result[T]]:
        """Execute a streaming provider operation with rate limiting.

        For streaming operations, rate limiting is applied before the stream
        starts. The stream itself is not rate limited per-chunk.

        Args:
            provider_id: Provider identifier.
            operation: Async callable that returns an async iterator.

        Yields:
            Result containing each stream event or an error.
        """
        provider_key = provider_id.lower().replace("-", "_")
        semaphore = self._get_semaphore(provider_key)
        limit = get_provider_limit(provider_key)

        async with self._lock:
            self._stats["total_requests"] += 1

        # Check rate limit
        check_result = await self._rate_tracker.check_allowed(provider_key)
        if check_result.is_err():
            yield Err(
                "Rate limit check failed",
                code="RATE_LIMIT_CHECK_ERROR",
            )
            return

        allowed, wait_seconds = check_result.unwrap()

        if not allowed:
            async with self._lock:
                self._stats["rate_limited_requests"] += 1

            logger.info(f"Rate limit reached for {provider_key}, waiting {wait_seconds:.2f}s")
            await self._emit_request_event(
                provider_key,
                "rate_limited",
                {"wait_seconds": wait_seconds},
            )
            await asyncio.sleep(wait_seconds)

        # Acquire semaphore and stream
        async with semaphore:
            async with self._lock:
                self._active_requests[provider_key] = self._active_requests.get(provider_key, 0) + 1

            await self._emit_request_event(provider_key, "started")

            try:
                stream = await operation()
                async for item in stream:
                    yield Ok(item)

                async with self._lock:
                    self._stats["successful_requests"] += 1

            except Exception as e:
                error_str = str(e).lower()
                is_429 = "rate limit" in error_str or "1302" in error_str or "429" in error_str

                if is_429:
                    async with self._lock:
                        self._stats["429_errors"] += 1

                    backoff = limit.calculate_backoff_with_jitter(0)
                    await self._rate_tracker.record_429(provider_key, backoff)
                    yield Err(
                        f"Rate limit hit during stream: {e}",
                        code="RATE_LIMIT_EXCEEDED",
                        retryable=True,
                    )
                else:
                    yield Err(
                        f"Stream error: {e}",
                        code="PROVIDER_ERROR",
                        retryable=False,
                    )

            finally:
                async with self._lock:
                    current = self._active_requests.get(provider_key, 0)
                    self._active_requests[provider_key] = max(0, current - 1)

                await self._emit_request_event(provider_key, "completed")

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about provider bus usage.

        Returns:
            Dictionary with usage statistics.
        """
        async with self._lock:
            stats = self._stats.copy()
            stats["active_requests"] = dict(self._active_requests)
            return stats

    async def get_provider_stats(self, provider_id: str) -> dict[str, Any]:
        """Get statistics for a specific provider.

        Args:
            provider_id: Provider identifier.

        Returns:
            Dictionary with provider-specific statistics.
        """
        provider_key = provider_id.lower().replace("-", "_")
        async with self._lock:
            return {
                "active_requests": self._active_requests.get(provider_key, 0),
                "concurrent_limit": get_provider_limit(provider_key).concurrent_requests,
                "requests_per_minute": get_provider_limit(provider_key).requests_per_minute,
            }

    async def reset_rate_limits(self, provider_id: str | None = None) -> None:
        """Reset rate limit state for a provider or all providers.

        Args:
            provider_id: Provider to reset, or None for all.
        """
        if provider_id:
            provider_key = provider_id.lower().replace("-", "_")
            await self._rate_tracker.reset(provider_key)
            logger.info(f"Reset rate limits for {provider_key}")
        else:
            # Reset all known providers
            for provider_key in PROVIDER_LIMITS:
                await self._rate_tracker.reset(provider_key)
            logger.info("Reset rate limits for all providers")


# Global singleton instance
provider_bus = ProviderBus.get_instance()


__all__ = [
    "ProviderBus",
    "provider_bus",
]
