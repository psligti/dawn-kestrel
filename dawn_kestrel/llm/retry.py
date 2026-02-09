"""RetryExecutor pattern for handling transient failures.

RetryExecutor provides automatic retry with exponential backoff for
operations that may fail temporarily.

The retry executor tracks attempts, handles backoff delays, and
distinguishes between retryable and non-retryable errors.

This module provides:
- RetryExecutor protocol for retry interface
- RetryExecutorImpl for fault-tolerant operations
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from dawn_kestrel.core.result import Ok, Err, Result
from dawn_kestrel.llm.circuit_breaker import CircuitBreaker


logger = logging.getLogger(__name__)


# =============================================================================
# BackoffStrategy Protocol
# =============================================================================


@runtime_checkable
class BackoffStrategy(Protocol):
    """Protocol for backoff strategies.

    Defines how delay increases between retry attempts.
    """

    async def calculate_delay(
        self, attempt: int, base_delay_ms: float, max_delay_ms: float
    ) -> float:
        """Calculate delay for given attempt.

        Args:
            attempt: Attempt number (0-indexed).
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
    """Exponential backoff strategy.

    Delay grows exponentially: delay = base_delay_ms * (exponential_base ** attempt)

    Example:
        backoff = ExponentialBackoff(
            base_delay_ms=100,
            max_delay_ms=5000,
            exponential_base=2.0,
            jitter=False,
        )
        # Attempt 0: 100ms
        # Attempt 1: 200ms
        # Attempt 2: 400ms
        # Attempt 3: 800ms
        # ...
    """

    def __init__(
        self,
        base_delay_ms: float = 100.0,
        max_delay_ms: float = 5000.0,
        exponential_base: float = 2.0,
        jitter: bool = False,
    ):
        """Initialize exponential backoff.

        Args:
            base_delay_ms: Base delay in milliseconds.
            max_delay_ms: Maximum delay in milliseconds.
            exponential_base: Base for exponential growth (default: 2.0).
            jitter: Whether to add random jitter (default: False).
        """
        self._base_delay_ms = base_delay_ms
        self._max_delay_ms = max_delay_ms
        self._exponential_base = exponential_base
        self._jitter = jitter

    async def calculate_delay(
        self, attempt: int, base_delay_ms: float, max_delay_ms: float
    ) -> float:
        """Calculate delay for given attempt."""
        delay = base_delay_ms * (self._exponential_base**attempt)
        delay = min(delay, max_delay_ms)

        if self._jitter:
            import random

            jitter_amount = delay * 0.1  # 10% jitter
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay += jitter

        return delay


class LinearBackoff:
    """Linear backoff strategy.

    Delay increases linearly: delay = base_delay_ms * (attempt + 1)

    Example:
        backoff = LinearBackoff(
            base_delay_ms=100,
            max_delay_ms=5000,
        )
        # Attempt 0: 100ms
        # Attempt 1: 200ms
        # Attempt 2: 300ms
        # Attempt 3: 400ms
        # ...
    """

    def __init__(self, base_delay_ms: float = 100.0, max_delay_ms: float = 5000.0):
        """Initialize linear backoff.

        Args:
            base_delay_ms: Base delay in milliseconds.
            max_delay_ms: Maximum delay in milliseconds.
        """
        self._base_delay_ms = base_delay_ms
        self._max_delay_ms = max_delay_ms

    async def calculate_delay(
        self, attempt: int, base_delay_ms: float, max_delay_ms: float
    ) -> float:
        """Calculate delay for given attempt."""
        delay = base_delay_ms * (attempt + 1)
        return min(delay, max_delay_ms)


class FixedBackoff:
    """Fixed backoff strategy.

    Delay remains constant: delay = delay_ms

    Example:
        backoff = FixedBackoff(delay_ms=500)
        # Attempt 0: 500ms
        # Attempt 1: 500ms
        # Attempt 2: 500ms
        # ...
    """

    def __init__(self, delay_ms: float = 500.0):
        """Initialize fixed backoff.

        Args:
            delay_ms: Constant delay in milliseconds.
        """
        self._delay_ms = delay_ms

    async def calculate_delay(
        self, attempt: int, base_delay_ms: float, max_delay_ms: float
    ) -> float:
        """Calculate delay for given attempt."""
        return self._delay_ms


# =============================================================================
# RetryExecutor Protocol
# =============================================================================


@runtime_checkable
class RetryExecutor(Protocol):
    """Protocol for retry executor.

    RetryExecutor handles automatic retries with exponential backoff
    for operations that may fail temporarily.

    Example:
        executor = RetryExecutorImpl(
            max_attempts=3,
            backoff=ExponentialBackoff(base_delay=0.1, max_delay=10.0),
        )

        # Execute with retry
        result = await executor.execute(
            lambda: provider.generate_response(messages),
            max_attempts=3,
        )
    """

    async def execute(
        self,
        operation: Callable[[], Any],
        max_attempts: int = 3,
        backoff: Optional[BackoffStrategy] = None,
    ) -> Result[Any]:
        """Execute operation with retry logic.

        Args:
            operation: Async function to execute.
            max_attempts: Maximum number of attempts.
            backoff: Optional backoff strategy (uses default if None).

        Returns:
            Result[Any]: Result on success or error with retry info.
        """
        ...

    async def get_attempt_count(self) -> int:
        """Get number of attempts for last execution."""
        ...

    async def get_stats(self) -> dict[str, Any]:
        """Get retry statistics."""
        ...


# =============================================================================
# RetryExecutorImpl
# =============================================================================


class RetryExecutorImpl:
    """Retry executor implementation for fault-tolerant operations.

    Wraps operations with automatic retry logic and exponential backoff.
    Tracks retry statistics and handles both sync and async operations.

    Distinguishes between retryable and non-retryable errors:
    - Retryable: Returns Err with retryable=True
    - Non-retryable: Returns Err with retryable=False

    Example:
        executor = RetryExecutorImpl(
            max_attempts=3,
            backoff=ExponentialBackoff(base_delay_ms=100, max_delay_ms=5000),
        )

        result = await executor.execute(
            lambda: provider.generate_response(messages),
            max_attempts=3,
        )

        if result.is_ok():
            response = result.unwrap()
            stats = await executor.get_stats()
            print(f"Success after {stats['attempts']} attempts")
    """

    def __init__(
        self,
        max_attempts: int = 3,
        backoff: Optional[BackoffStrategy] = None,
        transient_errors: Optional[set[type[Exception]]] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        """Initialize retry executor.

        Args:
            max_attempts: Maximum number of attempts.
            backoff: Optional backoff strategy (uses ExponentialBackoff if None).
            transient_errors: Exception types that should trigger retry (optional).
            circuit_breaker: Optional circuit breaker for fault tolerance (optional).
        """
        self._max_attempts = max_attempts
        self._backoff = backoff or ExponentialBackoff()
        self._transient_errors = transient_errors or set()
        self._circuit_breaker = circuit_breaker

        # Statistics
        self._stats: dict[str, Any] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_attempts": 0,
            "last_attempt_count": 0,
            "retry_count": 0,
            "errors_by_type": {},
        }

    async def execute(
        self,
        operation: Callable[[], Any],
        max_attempts: Optional[int] = None,
        backoff: Optional[BackoffStrategy] = None,
    ) -> Result[Any]:
        """Execute operation with retry logic.

        Args:
            operation: Async function to execute.
            max_attempts: Maximum attempts (uses instance default if None).
            backoff: Optional backoff strategy (uses instance default if None).

        Returns:
            Result[Any]: Result on success or error with retry info.
        """
        max_attempts = max_attempts or self._max_attempts
        backoff_strategy = backoff or self._backoff

        # Check circuit breaker before executing
        if self._circuit_breaker and await self._circuit_breaker.is_closed():
            return Err("CIRCUIT_OPEN", code="CIRCUIT_OPEN")

        self._stats["total_calls"] += 1
        self._stats["last_attempt_count"] = 0
        self._stats["retry_count"] = 0

        last_error: Optional[Err] = None
        attempts = 0

        for attempt in range(max_attempts):
            attempts += 1
            self._stats["total_attempts"] += 1
            self._stats["last_attempt_count"] = attempts

            try:
                # Execute operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation()
                else:
                    result = operation()

                # Check if result is a Result type
                if hasattr(result, "is_ok") and hasattr(result, "is_err"):
                    if result.is_ok():
                        self._stats["successful_calls"] += 1
                        return result
                    else:
                        # Check if error is retryable
                        if hasattr(result, "retryable") and not result.retryable:
                            # Non-retryable error, return immediately
                            self._stats["failed_calls"] += 1
                            return result
                        last_error = result
                else:
                    # Direct value, return immediately
                    self._stats["successful_calls"] += 1
                    return Ok(result)

            except Exception as e:
                # Check if exception is in transient_errors
                if self._transient_errors and type(e) in self._transient_errors:
                    # Transient error, retry
                    logger.error(f"Operation failed on attempt {attempt + 1}: {e}", exc_info=True)
                    last_error = Err(str(e), code="EXECUTION_ERROR", retryable=True)
                else:
                    # Permanent error, return immediately
                    logger.error(f"Permanent error on attempt {attempt + 1}: {e}", exc_info=True)
                    self._stats["failed_calls"] += 1
                    return Err(str(e), code="PERMANENT_ERROR", retryable=False)

            # If not last attempt, wait before retry
            if attempt < max_attempts - 1:
                # Increment retry count for this retry attempt
                self._stats["retry_count"] += 1
                # Get delay parameters from backoff strategy
                base_delay_ms = getattr(backoff_strategy, "_base_delay_ms", 100.0)
                max_delay_ms = getattr(backoff_strategy, "_max_delay_ms", 5000.0)
                delay_ms = await backoff_strategy.calculate_delay(
                    attempt, base_delay_ms, max_delay_ms
                )
                delay_s = delay_ms / 1000.0  # Convert to seconds
                logger.debug(f"Retry {attempt + 2}/{max_attempts} after {delay_s:.2f}s delay")
                await asyncio.sleep(delay_s)
            else:
                # Last attempt failed, increment retry_count to match total attempts
                self._stats["retry_count"] += 1

        # All attempts failed
        self._stats["failed_calls"] += 1

        if last_error:
            # Track error type
            error_code = getattr(last_error, "code", "unknown")
            self._stats["errors_by_type"][error_code] = (
                self._stats["errors_by_type"].get(error_code, 0) + 1
            )
            # Return MAX_RETRIES_EXCEEDED error instead of last_error
            return Err("MAX_RETRIES_EXCEEDED", code="MAX_RETRIES_EXCEEDED")

        return Err("MAX_RETRIES_EXCEEDED", code="MAX_RETRIES_EXCEEDED")

    async def get_attempt_count(self) -> int:
        """Get number of attempts for last execution."""
        return self._stats["last_attempt_count"]

    async def get_stats(self) -> dict[str, Any]:
        """Get retry statistics."""
        return self._stats.copy()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "RetryExecutor",
    "RetryExecutorImpl",
    "BackoffStrategy",
    "ExponentialBackoff",
    "LinearBackoff",
    "FixedBackoff",
]
