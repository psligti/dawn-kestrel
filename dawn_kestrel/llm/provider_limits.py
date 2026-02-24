"""Provider rate limit configuration with guardrails.

Provides per-provider rate limit defaults that account for multi-process
deployments by using conservative limits and jittered backoff.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from dawn_kestrel.core.result import Ok, Result

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ProviderRateLimit:
    """Rate limit configuration for a specific provider.

    Attributes:
        requests_per_minute: Max requests per minute (conservative for multi-process).
        tokens_per_minute: Max tokens per minute (if applicable).
        concurrent_requests: Max concurrent in-flight requests.
        retry_after_multiplier: Multiplier for Retry-After header (safety buffer).
        jitter_range: (min, max) random jitter in seconds for backoff.
        backoff_base: Base seconds for exponential backoff.
        backoff_max: Maximum seconds for exponential backoff.
    """

    requests_per_minute: int = 60
    tokens_per_minute: int = 100000
    concurrent_requests: int = 5
    retry_after_multiplier: float = 1.5
    jitter_range: tuple[float, float] = (0.1, 0.5)
    backoff_base: float = 1.0
    backoff_max: float = 60.0

    def calculate_backoff_with_jitter(self, attempt: int) -> float:
        """Calculate backoff with exponential increase and jitter.

        Args:
            attempt: The retry attempt number (0-indexed).

        Returns:
            Backoff duration in seconds with jitter applied.
        """
        exponential = self.backoff_base * (2**attempt)
        capped = min(exponential, self.backoff_max)
        jitter = random.uniform(*self.jitter_range)
        return capped + jitter

    def parse_retry_after(self, retry_after: str | None) -> float:
        """Parse Retry-After header with safety multiplier.

        Args:
            retry_after: Value from Retry-After header (seconds or date).

        Returns:
            Wait time in seconds with multiplier applied.
        """
        if not retry_after:
            return self.backoff_base * self.retry_after_multiplier

        try:
            seconds = float(retry_after)
            return seconds * self.retry_after_multiplier
        except ValueError:
            pass

        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(retry_after)
            delta = dt.timestamp() - time.time()
            return max(0, delta * self.retry_after_multiplier)
        except Exception:
            return self.backoff_base * self.retry_after_multiplier


PROVIDER_LIMITS: dict[str, ProviderRateLimit] = {
    "openai": ProviderRateLimit(
        requests_per_minute=500,
        tokens_per_minute=200000,
        concurrent_requests=10,
    ),
    "anthropic": ProviderRateLimit(
        requests_per_minute=60,
        tokens_per_minute=100000,
        concurrent_requests=5,
    ),
    "zai": ProviderRateLimit(
        requests_per_minute=60,
        tokens_per_minute=100000,
        concurrent_requests=5,
    ),
    "zai_coding_plan": ProviderRateLimit(
        requests_per_minute=60,
        tokens_per_minute=100000,
        concurrent_requests=3,
    ),
    "github_copilot": ProviderRateLimit(
        requests_per_minute=100,
        tokens_per_minute=50000,
        concurrent_requests=5,
    ),
}


def get_provider_limit(provider_id: str) -> ProviderRateLimit:
    """Get rate limit config for a provider.

    Args:
        provider_id: The provider identifier.

    Returns:
        ProviderRateLimit for the provider, or default if not found.
    """
    provider_key = provider_id.lower().replace("-", "_")
    return PROVIDER_LIMITS.get(provider_key, ProviderRateLimit())


@runtime_checkable
class RateLimitTracker(Protocol):
    """Protocol for tracking rate limit state."""

    async def check_allowed(self, key: str, cost: int = 1) -> Result[tuple[bool, float]]:
        """Check if request is allowed.

        Args:
            key: Resource key (e.g., provider_id).
            cost: Cost of this request (default 1).

        Returns:
            Result containing (allowed, wait_seconds) tuple.
        """
        ...

    async def record_429(self, key: str, retry_after: float) -> None:
        """Record a 429 response for circuit breaker tracking.

        Args:
            key: Resource key.
            retry_after: Suggested wait time from provider.
        """
        ...

    async def reset(self, key: str) -> None:
        """Reset rate limit state for a key."""
        ...


class LocalRateLimitTracker:
    """In-memory rate limit tracker with jittered backoff.

    Designed for single-process use with conservative defaults.
    Falls back to this when Redis is unavailable.
    """

    def __init__(
        self,
        provider_limits: dict[str, ProviderRateLimit] | None = None,
        default_limit: ProviderRateLimit | None = None,
    ):
        self._limits = provider_limits or PROVIDER_LIMITS
        self._default = default_limit or ProviderRateLimit()
        self._buckets: dict[str, dict[str, Any]] = {}
        self._429_counts: dict[str, int] = {}
        self._429_last_time: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def _get_limit(self, key: str) -> ProviderRateLimit:
        return self._limits.get(key, self._default)

    async def check_allowed(self, key: str, cost: int = 1) -> Result[tuple[bool, float]]:
        """Check if request is allowed using token bucket."""
        async with self._lock:
            now = time.time()
            limit = self._get_limit(key)

            if key not in self._buckets:
                self._buckets[key] = {
                    "tokens": limit.requests_per_minute,
                    "last_refill": now,
                    "refill_rate": limit.requests_per_minute / 60.0,
                    "capacity": limit.requests_per_minute,
                }

            bucket = self._buckets[key]
            elapsed = now - bucket["last_refill"]
            bucket["tokens"] = min(
                bucket["capacity"], bucket["tokens"] + elapsed * bucket["refill_rate"]
            )
            bucket["last_refill"] = now

            if bucket["tokens"] >= cost:
                bucket["tokens"] -= cost
                return Ok((True, 0.0))

            tokens_needed = cost - bucket["tokens"]
            wait_seconds = tokens_needed / bucket["refill_rate"]
            wait_with_jitter = wait_seconds + random.uniform(*limit.jitter_range)
            return Ok((False, wait_with_jitter))

    async def record_429(self, key: str, retry_after: float) -> None:
        """Record 429 response for tracking."""
        async with self._lock:
            now = time.time()

            if key in self._429_last_time:
                if now - self._429_last_time[key] > 300:
                    self._429_counts[key] = 0

            self._429_counts[key] = self._429_counts.get(key, 0) + 1
            self._429_last_time[key] = now

            if self._429_counts[key] >= 3:
                logger.warning(
                    f"Provider {key} returned 3+ 429s recently. Circuit breaker should activate."
                )

    async def reset(self, key: str) -> None:
        """Reset rate limit state."""
        async with self._lock:
            self._buckets.pop(key, None)
            self._429_counts.pop(key, None)
            self._429_last_time.pop(key, None)

    def get_429_count(self, key: str) -> int:
        """Get recent 429 count for circuit breaker decisions."""
        return self._429_counts.get(key, 0)


def create_rate_limit_tracker(
    backend: str = "local",
    redis_url: str | None = None,
    **kwargs,
) -> RateLimitTracker:
    """Factory for creating rate limit trackers.

    Args:
        backend: "local" for in-memory, "redis" for distributed.
        redis_url: Redis connection URL (required if backend="redis").
        **kwargs: Additional arguments for the tracker.

    Returns:
        RateLimitTracker instance.
    """
    if backend == "redis":
        try:
            from dawn_kestrel.llm.distributed_limiter import RedisRateLimitTracker

            return RedisRateLimitTracker(redis_url=redis_url, **kwargs)
        except ImportError:
            logger.warning(
                "Redis backend requested but redis package not installed. "
                "Falling back to local tracker."
            )
            return LocalRateLimitTracker(**kwargs)

    return LocalRateLimitTracker(**kwargs)


__all__ = [
    "ProviderRateLimit",
    "PROVIDER_LIMITS",
    "get_provider_limit",
    "RateLimitTracker",
    "LocalRateLimitTracker",
    "create_rate_limit_tracker",
]
