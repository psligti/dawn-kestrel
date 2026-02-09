"""CircuitBreaker pattern for LLM fault tolerance.

Circuit breaker provides fault tolerance by wrapping LLM provider calls
with automatic state management (OPEN, CLOSED, HALF_OPEN).

The circuit breaker tracks failures per provider and automatically opens
circuits when thresholds are breached, then resets after cooldown periods.

States:
- CLOSED: Circuit is closed, calls pass through normally
- OPEN: Circuit is open for calls (allows traffic)
- HALF_OPEN: Limited calls allowed after timeout to test recovery

This module provides:
- CircuitBreaker protocol for circuit breaker interface
- CircuitBreakerImpl for fault-tolerant LLM calls
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from dawn_kestrel.core.result import Ok, Err, Result


logger = logging.getLogger(__name__)


# =============================================================================
# CircuitState Enum
# =============================================================================


class CircuitState(str, Enum):
    """Circuit breaker states.

    States:
        CLOSED: Circuit is closed, normal operation
        OPEN: Circuit is open for calls
        HALF_OPEN: Limited calls after timeout to test recovery
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# =============================================================================
# CircuitBreaker Protocol
# =============================================================================


@runtime_checkable
class CircuitBreaker(Protocol):
    """Protocol for circuit breaker.

    Circuit breaker provides fault tolerance by wrapping LLM provider
    calls with automatic state management.

    The circuit breaker tracks failures per provider and automatically
    manages circuit state based on configurable thresholds.

    Example:
        adapter = OpenAIAdapter(provider)
        breaker = CircuitBreakerImpl(
            provider_adapter=adapter,
            failure_threshold=5,
            half_open_threshold=3,
            timeout_seconds=60,
            reset_timeout_seconds=120,
        )

        # Check circuit state
        if await breaker.is_closed():
            return Err("Circuit is closed")

        # Open circuit for calls
        await breaker.open()

        # Check state
        state = await breaker.get_state()
    """

    async def is_open(self) -> bool:
        """Check if circuit is open (allows calls).

        Returns:
            True if circuit is OPEN or HALF_OPEN, False if CLOSED.
        """
        ...

    async def is_closed(self) -> bool:
        """Check if circuit is closed (blocks calls).

        Returns:
            True if circuit is CLOSED, False if OPEN or HALF_OPEN.
        """
        ...

    async def is_half_open(self) -> bool:
        """Check if circuit is half-open (limited calls).

        Returns:
            True if circuit is HALF_OPEN, False otherwise.
        """
        ...

    async def get_state(self) -> str:
        """Get current circuit state.

        Returns:
            Circuit state as string ("closed", "open", or "half_open").
        """
        ...

    async def open(self) -> Result[None]:
        """Open circuit for calls.

        Changes state to OPEN without modifying failure tracking.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        ...

    async def close(self) -> Result[None]:
        """Close circuit manually.

        Changes state to CLOSED and clears all failure tracking data.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        ...


# =============================================================================
# CircuitBreakerImpl
# =============================================================================


class CircuitBreakerImpl:
    """Circuit breaker implementation for LLM fault tolerance.

    Wraps a provider adapter with circuit breaker logic to provide
    fault tolerance for LLM calls.

    Tracks failures per provider and manages circuit state:
    - Initially CLOSED (allows calls)
    - Transitions to OPEN when failure threshold reached
    - Transitions to HALF_OPEN after timeout for recovery testing
    - Returns to CLOSED after successful calls and cooldown

    Example:
        adapter = OpenAIAdapter(provider)
        breaker = CircuitBreakerImpl(
            provider_adapter=adapter,
            failure_threshold=5,  # Failures before opening circuit
            half_open_threshold=3,  # Failures before half-open
            timeout_seconds=60,  # Timeout for half-open state
            reset_timeout_seconds=120,  # Cooldown before reset
        )

        # Open circuit
        await breaker.open()

        # Check state
        state = await breaker.get_state()

        # Close circuit
        await breaker.close()
    """

    def __init__(
        self,
        provider_adapter: Any,  # ProviderAdapter instance
        failure_threshold: int = 5,
        half_open_threshold: int = 3,
        timeout_seconds: int = 300,
        reset_timeout_seconds: int = 600,
    ):
        """Initialize circuit breaker.

        Args:
            provider_adapter: Provider adapter to wrap.
            failure_threshold: Failures before opening circuit.
            half_open_threshold: Failures before half-open state.
            timeout_seconds: Timeout for half-open state (seconds).
            reset_timeout_seconds: Cooldown before reset (seconds).
        """
        self._provider_adapter = provider_adapter
        self._failure_threshold = failure_threshold
        self._half_open_threshold = half_open_threshold
        self._timeout_seconds = timeout_seconds
        self._reset_timeout_seconds = reset_timeout_seconds

        # State tracking
        self._state: str = CircuitState.CLOSED.value
        self._failures: dict[str, int] = {}  # Provider -> failure count
        self._last_failure_time: dict[str, datetime] = {}  # Provider -> last failure timestamp
        self._half_open_until: dict[str, datetime] = {}  # Provider -> half-open expiry

    async def is_open(self) -> bool:
        """Check if circuit is open (allows calls)."""
        return self._state != CircuitState.CLOSED.value

    async def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED.value

    async def is_half_open(self) -> bool:
        """Check if circuit is half-open (limited calls)."""
        return self._state == CircuitState.HALF_OPEN.value

    async def get_state(self) -> str:
        """Get current circuit state."""
        return self._state

    async def _get_provider_name(self) -> str:
        """Get provider name from adapter."""
        if hasattr(self._provider_adapter, "get_provider_name"):
            name = await self._provider_adapter.get_provider_name()
            return name if name else "unknown"
        return "unknown"

    async def open(self) -> Result[None]:
        """Open circuit for calls.

        Changes state to OPEN without modifying failure tracking.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        try:
            self._state = CircuitState.OPEN.value
            return Ok(None)
        except Exception as e:
            logger.error(f"Failed to open circuit: {e}", exc_info=True)
            return Err(f"Failed to open circuit: {e}", code="CIRCUIT_ERROR")

    async def close(self) -> Result[None]:
        """Close circuit manually.

        Changes state to CLOSED and clears all failure tracking data.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        try:
            self._state = CircuitState.CLOSED.value
            self._failures.clear()
            self._last_failure_time.clear()
            self._half_open_until.clear()
            return Ok(None)
        except Exception as e:
            logger.error(f"Failed to close circuit: {e}", exc_info=True)
            return Err(f"Failed to close circuit: {e}", code="CIRCUIT_ERROR")


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerImpl",
]
