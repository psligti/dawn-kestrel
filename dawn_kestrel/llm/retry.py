"""Retry + Backoff pattern for transient failure handling.

Retry pattern with exponential backoff provides resilience for LLM calls
by automatically retrying transient failures with configurable delays.

This module provides:
- BackoffStrategy protocol for delay calculation
- ExponentialBackoff, LinearBackoff, FixedBackoff implementations
- RetryExecutor protocol for retry execution
- RetryExecutorImpl with circuit breaker integration
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Callable, Protocol, runtime_checkable

from dawn_kestrel.core.result import Err, Result


logger = logging.getLogger(__name__)


# =============================================================================
# BackoffStrategy Protocol
# =============================================================================


@runtime_checkable
class BackoffStrategy(Protocol):
    """Protocol for backoff calculation.

    Backoff strategy calculates delay before next retry attempt.
    Different implementations provide different backoff algorithms:
    - Exponential: Delay doubles each retry
    - Linear: Delay increases linearly
    - Fixed: Constant delay between retries

    Example:
        backoff = ExponentialBackoff(base_delay_ms=100, max_delay_ms=5000)
        delay = await backoff.calculate_delay(attempt=2, base_delay_ms=100, max_delay_ms=5000)
    """

    async def calculate_delay(
        self,
        attempt: int,
        base_delay_ms: float,
        max_delay_ms: float,
    ) -> float:
        """Calculate delay before next retry attempt.

        Args:
            attempt: Current attempt number (0-based).
            base_delay_ms: Base delay in milliseconds.
            max_delay_ms: Maximum delay in milliseconds.

        Returns:
            Delay in milliseconds.
        """
        ...


# =============================================================================
# ExponentialBackoff
# =============================================================================


class ExponentialBackoff:
    """Exponential backoff with jitter.

    Calculates delay using exponential formula:
    delay = base_delay_ms * (exponential_base ** attempt)

    Jitter adds randomness to avoid thundering herd problem.

    Example:
        backoff = ExponentialBackoff(
            base_delay_ms=100,
            max_delay_ms=30000,
            exponential_base=2.0,
            jitter=True,
        )
        delay = await backoff.calculate_delay(attempt=1, base_delay_ms=100, max_delay_ms=30000)
        # delay = 200ms (with ±10% jitter if enabled)
    """

    def __init__(
        self,
        base_delay_ms: float = 100,
        max_delay_ms: float = 30000,  # 30 seconds max
        exponential_base: float = 2.0,  # Doubles delay each retry
        jitter: bool = True,  # Add randomness to avoid thundering herd
    ):
        """Initialize exponential backoff.

        Args:
            base_delay_ms: Base delay in milliseconds.
            max_delay_ms: Maximum delay in milliseconds.
            exponential_base: Multiplier for each retry (2.0 = double).
            jitter: Enable random jitter (±10%).
        """
        self._base_delay_ms = base_delay_ms
        self._max_delay_ms = max_delay_ms
        self._exponential_base = exponential_base
        self._jitter = jitter

    async def calculate_delay(
        self,
        attempt: int,
        base_delay_ms: float,
        max_delay_ms: float,
    ) -> float:
        """Calculate exponential delay with optional jitter.

        Args:
            attempt: Current attempt number (0-based).
            base_delay_ms: Base delay in milliseconds.
            max_delay_ms: Maximum delay in milliseconds.

        Returns:
            Delay in milliseconds.
        """
        # Calculate exponential delay
        delay = base_delay_ms * (self._exponential_base**attempt)

        # Add jitter if enabled (±10%)
        if self._jitter:
            jitter_value = random.uniform(-0.1, 0.1)
            delay = delay * (1 + jitter_value)

        # Cap at max delay
        delay = min(delay, max_delay_ms)

        return delay


# =============================================================================
# LinearBackoff
# =============================================================================


class LinearBackoff:
    """Linear (fixed interval) backoff.

    Calculates delay using linear formula:
    delay = min(base_delay_ms * (attempt + 1), max_delay_ms)

    Example:
        backoff = LinearBackoff(base_delay_ms=100, max_delay_ms=10000)
        delay = await backoff.calculate_delay(attempt=1, base_delay_ms=100, max_delay_ms=10000)
        # delay = 200ms
    """

    def __init__(
        self,
        base_delay_ms: float = 100,
        max_delay_ms: float = 10000,  # 10 seconds max
    ):
        """Initialize linear backoff.

        Args:
            base_delay_ms: Base delay in milliseconds.
            max_delay_ms: Maximum delay in milliseconds.
        """
        self._base_delay_ms = base_delay_ms
        self._max_delay_ms = max_delay_ms

    async def calculate_delay(
        self,
        attempt: int,
        base_delay_ms: float,
        max_delay_ms: float,
    ) -> float:
        """Calculate linear delay.

        Args:
            attempt: Current attempt number (0-based).
            base_delay_ms: Base delay in milliseconds.
            max_delay_ms: Maximum delay in milliseconds.

        Returns:
            Delay in milliseconds.
        """
        # Linear increase
        delay = min(base_delay_ms * (attempt + 1), max_delay_ms)
        return delay


# =============================================================================
# FixedBackoff
# =============================================================================


class FixedBackoff:
    """Fixed interval backoff.

    Always returns the same delay regardless of attempt number.

    Example:
        backoff = FixedBackoff(delay_ms=5000)
        delay = await backoff.calculate_delay(attempt=1, base_delay_ms=100, max_delay_ms=5000)
        # delay = 5000ms (always)
    """

    def __init__(
        self,
        delay_ms: float = 5000,  # 5 seconds
    ):
        """Initialize fixed backoff.

        Args:
            delay_ms: Constant delay in milliseconds.
        """
        self._delay_ms = delay_ms

    async def calculate_delay(
        self,
        attempt: int,
        base_delay_ms: float,
        max_delay_ms: float,
    ) -> float:
        """Return constant delay.

        Args:
            attempt: Current attempt number (0-based, ignored).
            base_delay_ms: Base delay in milliseconds (ignored).
            max_delay_ms: Maximum delay in milliseconds (ignored).

        Returns:
            Constant delay in milliseconds.
        """
        return self._delay_ms


# =============================================================================
# RetryExecutor Protocol
# =============================================================================


@runtime_checkable
class RetryExecutor(Protocol):
    """Protocol for retry executor with backoff.

    Retry executor provides automatic retry logic with configurable
    backoff strategies and circuit breaker integration.

    Example:
        backoff = ExponentialBackoff(base_delay_ms=100, max_delay_ms=5000)
        retry = RetryExecutorImpl(max_attempts=3, backoff=backoff)

        result = await retry.execute(
            func=llm_call,
            max_attempts=3,
            backoff=backoff,
        )
    """

    async def execute(
        self,
        func: Callable[..., Any],
        max_attempts: int = 3,
        backoff: BackoffStrategy | None = None,
        circuit_breaker: Any = None,
    ) -> Result[Any]:
        """Execute function with retry logic.

        Args:
            func: Async function to execute.
            max_attempts: Maximum number of attempts.
            backoff: Backoff strategy for delays.
            circuit_breaker: Optional circuit breaker to check before retries.

        Returns:
            Result[Any]: Result on success or final failure.
        """
        ...

    async def get_stats(self) -> dict[str, Any]:
        """Get retry statistics.

        Returns:
            Dict with attempt counts, failures, etc.
        """
        ...


# =============================================================================
# RetryExecutorImpl
# =============================================================================


class RetryExecutorImpl:
    """Retry executor with exponential backoff and circuit breaker integration.

    Wraps async functions with automatic retry logic for transient failures.
    Supports configurable backoff strategies and circuit breaker integration.

    Example:
        backoff = ExponentialBackoff(base_delay_ms=100, max_delay_ms=5000)
        circuit_breaker = CircuitBreakerImpl(...)

        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
            circuit_breaker=circuit_breaker,
            transient_errors={TimeoutError, Exception},
        )

        result = await retry.execute(llm_call)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        backoff: BackoffStrategy | None = None,  # Will default to ExponentialBackoff
        circuit_breaker: Any = None,
        transient_errors: set[type] | None = None,
    ):
        """Initialize retry executor.

        Args:
            max_attempts: Maximum number of retry attempts.
            backoff: Backoff strategy (defaults to ExponentialBackoff).
            circuit_breaker: Optional circuit breaker for fault tolerance.
            transient_errors: Set of error types to retry (default: all exceptions).
        """
        self._max_attempts = max_attempts
        self._backoff = backoff or ExponentialBackoff()
        self._circuit_breaker = circuit_breaker
        self._transient_errors = transient_errors or {Exception, TimeoutError}
        self._stats: dict[str, Any] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "retry_count": 0,
        }

    def set_circuit_breaker(self, circuit_breaker: Any) -> None:
        """Set circuit breaker for resource isolation.

        Args:
            circuit_breaker: Circuit breaker instance.
        """
        self._circuit_breaker = circuit_breaker

    def add_transient_error(self, error_type: type) -> None:
        """Add error type as transient (retryable).

        Args:
            error_type: Exception class to retry on.
        """
        self._transient_errors.add(error_type)

    async def execute(
        self,
        func: Callable[..., Any],
        max_attempts: int | None = None,
        backoff: BackoffStrategy | None = None,
    ) -> Result[Any]:
        """Execute function with retry logic and backoff.

        Retries function on transient errors with configurable backoff.
        Checks circuit breaker before each attempt if configured.

        Args:
            func: Async function to execute.
            max_attempts: Maximum number of attempts (overrides instance default).
            backoff: Backoff strategy (overrides instance default).

        Returns:
            Result[Any]: Result on success or final failure.
        """
        max_attempts = max_attempts or self._max_attempts
        backoff = backoff or self._backoff
        attempt = 0

        while attempt < max_attempts:
            # Check circuit breaker (if CLOSED, blocks calls)
            if self._circuit_breaker and await self._circuit_breaker.is_closed():
                return Err(
                    f"Circuit is closed for {self._get_function_name(func)} (CIRCUIT_OPEN)",
                    code="CIRCUIT_OPEN",
                )

            try:
                # Execute function
                result = await func()

                # Check if Result type
                if isinstance(result, Result):
                    # Result is Ok
                    if result.is_ok():
                        # Success - update stats and return
                        self._stats["successful_calls"] += 1
                        self._stats["total_calls"] += 1
                        return result

                    # Result is Err - check if error is retryable
                    # Err has error attribute (string), code attribute, and retryable flag
                    if hasattr(result, "retryable") and not result.retryable:
                        # Permanent error - don't retry
                        self._stats["failed_calls"] += 1
                        self._stats["total_calls"] += 1
                        return result

                    # Transient error - increment retry count
                    self._stats["retry_count"] += 1
                    attempt += 1
                else:
                    # Non-Result return value - treat as success
                    self._stats["successful_calls"] += 1
                    self._stats["total_calls"] += 1
                    return result

            except Exception as e:
                # Check if exception is transient
                is_transient = any(
                    isinstance(e, error_type) for error_type in self._transient_errors
                )
                if is_transient:
                    # Transient error - increment retry count
                    self._stats["retry_count"] += 1
                    attempt += 1
                else:
                    # Permanent error - don't retry
                    self._stats["failed_calls"] += 1
                    self._stats["total_calls"] += 1
                    return Err(f"Permanent error: {e}", code="PERMANENT_ERROR")

            # Calculate backoff delay before retry (if not last attempt)
            if attempt < max_attempts:
                # Get default base/max delay from backoff strategy
                base_delay_ms = 100
                max_delay_ms = 30000

                if isinstance(backoff, ExponentialBackoff):
                    # Use configured values from ExponentialBackoff
                    base_delay_ms = backoff._base_delay_ms
                    max_delay_ms = backoff._max_delay_ms

                delay = await backoff.calculate_delay(
                    attempt=attempt - 1,  # Next attempt
                    base_delay_ms=base_delay_ms,
                    max_delay_ms=max_delay_ms,
                )

                # Wait before retry
                await asyncio.sleep(delay / 1000)  # Convert ms to seconds

        # Max attempts exceeded
        self._stats["failed_calls"] += 1
        self._stats["total_calls"] += 1
        return Err(
            f"Max retry attempts ({max_attempts}) exceeded for {self._get_function_name(func)} (MAX_RETRIES_EXCEEDED)",
            code="MAX_RETRIES_EXCEEDED",
        )

    def _get_function_name(self, func: Callable) -> str:
        """Get function name for error messages.

        Args:
            func: Function to get name from.

        Returns:
            Function name or 'unknown_function'.
        """
        return func.__name__ if hasattr(func, "__name__") else "unknown_function"

    async def get_stats(self) -> dict[str, Any]:
        """Get retry statistics.

        Returns:
            Dict with attempt counts, failures, etc.
        """
        return self._stats.copy()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "BackoffStrategy",
    "ExponentialBackoff",
    "LinearBackoff",
    "FixedBackoff",
    "RetryExecutor",
    "RetryExecutorImpl",
]
