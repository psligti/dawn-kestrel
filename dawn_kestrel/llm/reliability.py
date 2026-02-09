"""LLMReliability pattern for combined resilience.

LLMReliability provides a unified wrapper combining all reliability patterns:
- Rate limiting: Prevent API overload
- Circuit breaking: Isolate failing providers
- Retry with backoff: Handle transient failures

Patterns are applied in correct order for maximum resilience:
1. Rate limiting (prevent overload)
2. Circuit breaker (check circuit state)
3. Retry with backoff (handle failures)

This module provides:
- LLMReliability protocol for reliability interface
- LLMReliabilityImpl combining all patterns
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Protocol, runtime_checkable

from dawn_kestrel.core.result import Ok, Err, Result
from dawn_kestrel.llm.circuit_breaker import CircuitBreaker
from dawn_kestrel.llm.retry import RetryExecutor, ExponentialBackoff
from dawn_kestrel.llm.rate_limiter import RateLimiter


logger = logging.getLogger(__name__)


# =============================================================================
# LLMReliability Protocol
# =============================================================================


@runtime_checkable
class LLMReliability(Protocol):
    """Protocol for LLM resilience with combined patterns.

    LLMReliability wraps provider calls with multiple resilience patterns
    applied in correct order for maximum fault tolerance.

    Pattern Order:
        1. Rate limiting (prevent API overload)
        2. Circuit breaking (check circuit state)
        3. Retry with backoff (handle transient failures)

    Example:
        reliability = LLMReliabilityImpl(
            rate_limiter=RateLimiterImpl(
                default_capacity=10,
                default_refill_rate=0.166667,  # 10 tokens/min
            ),
            circuit_breaker=CircuitBreakerImpl(
                failure_threshold=5,
                timeout_seconds=300,
            ),
            retry_executor=RetryExecutorImpl(
                max_attempts=3,
                backoff=ExponentialBackoff(base_delay=0.1, max_delay=10.0),
            ),
        )

        # Generate with all resilience patterns
        result = await reliability.generate_with_resilience(
            messages=[Message(role="user", text="Hello")],
            provider_adapter=provider,
            resource="openai",
        )
    """

    async def generate_with_resilience(
        self,
        provider_adapter: Any,
        messages: list[Any],
        model: str = "default",
        resource: str = "default",
        **kwargs,
    ) -> Result[Any]:
        """Generate LLM response with all resilience layers.

        Args:
            provider_adapter: Provider adapter to wrap.
            messages: List of messages for context.
            model: Model identifier.
            resource: Resource identifier for rate limiting.
            **kwargs: Additional provider parameters.

        Returns:
            Result[Any]: Response on success or error with resilience info.
        """
        ...

    async def get_stats(self) -> dict[str, Any]:
        """Get reliability statistics.

        Returns:
            Dictionary with reliability metrics.
        """
        ...


# =============================================================================
# LLMReliabilityImpl
# =============================================================================


class LLMReliabilityImpl:
    """LLM reliability wrapper combining all patterns.

    Wraps provider adapter calls with multiple resilience layers:
    - Rate limiter: Prevent API overload
    - Circuit breaker: Isolate failing providers
    - Retry executor: Handle transient failures with backoff

    Pattern Ordering:
        1. Rate limiting (first - check before any work)
        2. Circuit breaker (second - fail fast if circuit open)
        3. Retry with backoff (last - handle actual failures)

    Graceful Degradation:
        If rate limit exceeded: Return error immediately (no retry)
        If circuit open: Return error immediately (no retry)
        If transient failure: Retry with exponential backoff
        If permanent failure: Return error without retry

    Example:
        reliability = LLMReliabilityImpl(
            rate_limiter=RateLimiterImpl(default_capacity=10),
            circuit_breaker=CircuitBreakerImpl(failure_threshold=5),
            retry_executor=RetryExecutorImpl(max_attempts=3),
        )

        result = await reliability.generate_with_resilience(
            messages=[Message(role="user", text="Hello")],
            provider_adapter=provider,
            resource="openai",
        )

        if result.is_ok():
            response = result.unwrap()
        else:
            error = result.error
            logger.error(f"Generation failed: {error}")
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_executor: Optional[RetryExecutor] = None,
    ):
        """Initialize LLM reliability wrapper.

        Args:
            rate_limiter: Optional rate limiter for API throttling.
            circuit_breaker: Optional circuit breaker for fault tolerance.
            retry_executor: Optional retry executor for transient failures.
        """
        self._rate_limiter = rate_limiter if rate_limiter is not None else None
        self._circuit_breaker = circuit_breaker
        self._retry_executor = retry_executor

        # Combined statistics
        self._stats: dict[str, Any] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rate_limit_rejections": 0,
            "circuit_rejections": 0,
            "retry_attempts": 0,
            "errors_by_type": {},
        }

    def set_rate_limiter(self, rate_limiter: RateLimiter) -> None:
        """Set rate limiter for resilience.

        Args:
            rate_limiter: Rate limiter instance.
        """
        self._rate_limiter = rate_limiter() if rate_limiter else None

    def set_circuit_breaker(self, circuit_breaker: CircuitBreaker) -> None:
        """Set circuit breaker for resilience.

        Args:
            circuit_breaker: Circuit breaker instance.
        """
        self._circuit_breaker = circuit_breaker

    def set_retry_executor(self, retry_executor: RetryExecutor) -> None:
        """Set retry executor for resilience.

        Args:
            retry_executor: Retry executor instance.
        """
        self._retry_executor = retry_executor

    async def generate_with_resilience(
        self,
        provider_adapter: Any,
        messages: list[Any],
        model: str = "default",
        resource: str = "default",
        **kwargs,
    ) -> Result[Any]:
        """Generate LLM response with all resilience layers.

        Pattern Order:
            1. Rate limiting - prevent API overload
            2. Circuit breaker - fail fast if circuit open
            3. Retry with backoff - handle transient failures

        Args:
            provider_adapter: Provider adapter to wrap.
            messages: List of messages for context.
            model: Model identifier.
            resource: Resource identifier for rate limiting.
            **kwargs: Additional provider parameters.

        Returns:
            Result[Any]: Response on success or error with resilience info.
        """
        self._stats["total_calls"] += 1

        # Get provider name for tracking
        provider_name = await self._get_provider_name(provider_adapter)

        # Layer 1: Rate limiting (prevents API overload)
        if self._rate_limiter:
            rate_result = await self._rate_limiter.try_acquire(resource, tokens=1)
            if rate_result.is_err():
                self._stats["rate_limit_rejections"] += 1
                self._stats["failed_calls"] += 1
                self._stats["errors_by_type"]["rate_limit"] = (
                    self._stats["errors_by_type"].get("rate_limit", 0) + 1
                )
                logger.warning(
                    f"Rate limit exceeded for {provider_name}/{resource}: {rate_result.error}"
                )
                return Err(
                    f"Rate limit exceeded for {provider_name}/{resource}",
                    code="RATE_LIMIT_EXCEEDED",
                    retryable=False,
                )

        # Layer 2: Circuit breaker (fail fast if circuit is closed)
        if self._circuit_breaker:
            is_closed = await self._circuit_breaker.is_closed()
            if is_closed:
                self._stats["circuit_rejections"] += 1
                self._stats["failed_calls"] += 1
                self._stats["errors_by_type"]["circuit_breaker"] = (
                    self._stats["errors_by_type"].get("circuit_breaker", 0) + 1
                )
                logger.warning(f"Circuit is closed for {provider_name}")
                return Err(
                    f"Circuit is closed for {provider_name}",
                    code="CIRCUIT_CLOSED",
                    retryable=False,
                )

        # Layer 3: Retry with backoff (handle transient failures)
        async def _call_provider():
            """Call provider adapter."""
            result = await provider_adapter.generate_response(messages, model, **kwargs)

            # Track errors for circuit breaker
            if result.is_err():
                # Note: In a full implementation, we'd update circuit breaker here
                # For now, we just log the error
                logger.debug(f"Provider error for {provider_name}: {result.error}")

            return result

        # Execute with retry if configured
        if self._retry_executor:
            result = await self._retry_executor.execute(_call_provider)
            attempt_count = await self._retry_executor.get_attempt_count()
            if attempt_count > 1:
                self._stats["retry_attempts"] += attempt_count - 1
        else:
            # No retry, call directly
            result = await _call_provider()

        # Update statistics
        if result.is_ok():
            self._stats["successful_calls"] += 1
        else:
            self._stats["failed_calls"] += 1
            error_code = getattr(result, "code", "unknown")
            self._stats["errors_by_type"][error_code] = (
                self._stats["errors_by_type"].get(error_code, 0) + 1
            )

        return result

    async def _get_provider_name(self, provider_adapter: Any) -> str:
        """Get provider name from adapter.

        Args:
            provider_adapter: Provider adapter instance.

        Returns:
            Provider name string.
        """
        if hasattr(provider_adapter, "get_provider_name"):
            try:
                return await provider_adapter.get_provider_name()
            except Exception:
                pass
        return "unknown"

    async def get_stats(self) -> dict[str, Any]:
        """Get reliability statistics.

        Returns:
            Dictionary with reliability metrics including
            total calls, successes, failures, and error breakdown.
        """
        stats = self._stats.copy()

        # Add pattern-specific stats if available
        if self._rate_limiter:
            stats["rate_limiter_stats"] = await self._rate_limiter.get_available("default")

        if self._retry_executor:
            retry_stats = await self._retry_executor.get_stats()
            stats["retry_stats"] = retry_stats

        if self._circuit_breaker:
            stats["circuit_state"] = await self._circuit_breaker.get_state()

        return stats


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "LLMReliability",
    "LLMReliabilityImpl",
]
