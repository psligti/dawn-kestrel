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
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from dawn_kestrel.core.result import Ok, Err, Result


logger = logging.getLogger(__name__)


# =============================================================================
# BackoffStrategy Protocol
# =============================================================================


@runtime_checkable
class BackoffStrategy(Protocol):
    """Protocol for backoff strategies.

    Defines how delay increases between retry attempts.
    """

    def get_delay(self, attempt: int) -> float:
        """Get delay for given attempt.

        Args:
            attempt: Attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        ...

    def get_delay_until(self, attempt: int) -> datetime:
        """Get absolute time to attempt given retry.

        Args:
            attempt: Attempt number (0-indexed).

        Returns:
            Datetime when next attempt should occur.
        """
        ...


# =============================================================================
# ExponentialBackoff
# =============================================================================


class ExponentialBackoff:
    """Exponential backoff strategy.

    Delay grows exponentially: delay = base_delay * (2 ** attempt)

    Example:
        backoff = ExponentialBackoff(base_delay=0.1, max_delay=10.0)
        # Attempt 0: 0.1s
        # Attempt 1: 0.2s
        # Attempt 2: 0.4s
        # Attempt 3: 0.8s
        # ...
    """

    def __init__(self, base_delay: float = 0.1, max_delay: float = 60.0):
        """Initialize exponential backoff.

        Args:
            base_delay: Initial delay in seconds.
            max_delay: Maximum delay in seconds.
        """
        self._base_delay = base_delay
        self._max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        """Get delay for given attempt."""
        delay = self._base_delay * (2**attempt)
        return min(delay, self._max_delay)

    def get_delay_until(self, attempt: int) -> datetime:
        """Get absolute time to attempt given retry."""
        delay = self.get_delay(attempt)
        return datetime.now() + timedelta(seconds=delay)


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
            backoff=ExponentialBackoff(base_delay=0.1, max_delay=10.0),
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
    ):
        """Initialize retry executor.

        Args:
            max_attempts: Maximum number of attempts.
            backoff: Optional backoff strategy (uses ExponentialBackoff if None).
        """
        self._max_attempts = max_attempts
        self._backoff = backoff or ExponentialBackoff()

        # Statistics
        self._stats: dict[str, Any] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_attempts": 0,
            "last_attempt_count": 0,
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

        self._stats["total_calls"] += 1
        self._stats["last_attempt_count"] = 0

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
                # Exception occurred, treat as retryable
                logger.error(f"Operation failed on attempt {attempt + 1}: {e}", exc_info=True)
                last_error = Err(str(e), code="EXECUTION_ERROR", retryable=True)

            # If not last attempt, wait before retry
            if attempt < max_attempts - 1:
                delay = backoff_strategy.get_delay(attempt)
                logger.debug(f"Retry {attempt + 2}/{max_attempts} after {delay:.2f}s delay")
                await asyncio.sleep(delay)

        # All attempts failed
        self._stats["failed_calls"] += 1

        if last_error:
            # Track error type
            error_code = getattr(last_error, "code", "unknown")
            self._stats["errors_by_type"][error_code] = (
                self._stats["errors_by_type"].get(error_code, 0) + 1
            )
            return last_error

        return Err("Operation failed after all attempts", code="RETRY_EXHAUSTED")

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
]
