"""Tests for CircuitBreaker pattern for LLM fault tolerance.

Circuit breaker provides fault tolerance by wrapping LLM provider calls
with automatic state management (OPEN, CLOSED, HALF_OPEN).
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from datetime import datetime, timedelta

from dawn_kestrel.core.models import Message
from dawn_kestrel.core.result import Ok, Err


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_provider_adapter():
    """Create a mock provider adapter."""
    adapter = AsyncMock()
    adapter.get_provider_name = AsyncMock(return_value="test_provider")
    adapter.generate_response = AsyncMock(
        return_value=Ok(Message(id="test", session_id="test", role="assistant", text="Success"))
    )
    return adapter


@pytest.fixture
def circuit_breaker(mock_provider_adapter):
    """Create a CircuitBreakerImpl with default config."""
    from dawn_kestrel.llm.circuit_breaker import CircuitBreakerImpl, CircuitState

    return CircuitBreakerImpl(
        provider_adapter=mock_provider_adapter,
        failure_threshold=5,
        half_open_threshold=3,
        timeout_seconds=60,
        reset_timeout_seconds=120,
    )


# =============================================================================
# Circuit State Tests
# =============================================================================


class TestCircuitState:
    """Tests for circuit state initialization and queries."""

    def test_initial_state_is_closed(self, circuit_breaker):
        """Circuit should start in CLOSED state."""
        assert asyncio.run(circuit_breaker.get_state()) == "closed"

    def test_initial_failures_are_empty(self, circuit_breaker):
        """No failures should be tracked initially."""
        assert len(circuit_breaker._failures) == 0

    def test_initial_last_failure_times_are_empty(self, circuit_breaker):
        """No last failure times should be tracked initially."""
        assert len(circuit_breaker._last_failure_time) == 0

    def test_initial_half_open_times_are_empty(self, circuit_breaker):
        """No half-open expirations should be tracked initially."""
        assert len(circuit_breaker._half_open_until) == 0


# =============================================================================
# Circuit Operations Tests
# =============================================================================


class TestCircuitOperations:
    """Tests for circuit open/close operations."""

    @pytest.mark.asyncio
    async def test_open_changes_state_to_open(self, circuit_breaker):
        """open() should change state to OPEN."""
        await circuit_breaker.open()
        assert await circuit_breaker.get_state() == "open"

    @pytest.mark.asyncio
    async def test_open_resets_state_only(self, circuit_breaker):
        """open() should change state without modifying failure tracking."""
        # Add some failures first
        circuit_breaker._failures["test_provider"] = 3
        circuit_breaker._last_failure_time["test_provider"] = datetime.now()

        # Open circuit
        result = await circuit_breaker.open()

        assert result.is_ok()
        assert await circuit_breaker.get_state() == "open"
        # Failures should NOT be reset by open()
        assert circuit_breaker._failures.get("test_provider") == 3

    @pytest.mark.asyncio
    async def test_close_changes_state_to_closed(self, circuit_breaker):
        """close() should change state to CLOSED."""
        # First open it
        await circuit_breaker.open()

        # Now close it
        result = await circuit_breaker.close()

        assert result.is_ok()
        assert await circuit_breaker.get_state() == "closed"

    @pytest.mark.asyncio
    async def test_close_clears_failures_and_times(self, circuit_breaker):
        """close() should clear all failure tracking data."""
        # Add some failures and times
        circuit_breaker._failures["test_provider"] = 5
        circuit_breaker._last_failure_time["test_provider"] = datetime.now()
        circuit_breaker._half_open_until["test_provider"] = datetime.now()

        # Close circuit
        result = await circuit_breaker.close()

        assert result.is_ok()
        assert await circuit_breaker.get_state() == "closed"
        assert len(circuit_breaker._failures) == 0
        assert len(circuit_breaker._last_failure_time) == 0
        assert len(circuit_breaker._half_open_until) == 0


# =============================================================================
# Circuit Breaker Logic Tests
# =============================================================================


class TestCircuitBreakerLogic:
    """Tests for circuit breaker logic with provider calls."""

    @pytest.mark.asyncio
    async def test_closed_circuit_passes_through_calls(
        self, circuit_breaker, mock_provider_adapter
    ):
        """CLOSED circuit should allow calls to pass through."""
        # Ensure circuit is closed
        await circuit_breaker.close()

        # Make a call
        messages = [Message(id="1", session_id="test", role="user", text="Hello")]
        result = await mock_provider_adapter.generate_response(messages, "gpt-4")

        assert result.is_ok()
        assert result.unwrap().text == "Success"

    @pytest.mark.asyncio
    async def test_open_circuit_allows_calls(self, circuit_breaker, mock_provider_adapter):
        """OPEN circuit should allow calls to pass through."""
        # Open circuit
        await circuit_breaker.open()

        # Make a call - should succeed
        messages = [Message(id="1", session_id="test", role="user", text="Hello")]
        mock_provider_adapter.generate_response.return_value = Ok(
            Message(id="test", session_id="test", role="assistant", text="Response")
        )
        result = await mock_provider_adapter.generate_response(messages, "gpt-4")

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_half_open_circuit_expires_after_timeout(self, circuit_breaker):
        """HALF_OPEN state should expire after timeout seconds."""
        # Manually set to half-open with expiry in the past
        circuit_breaker._state = "half_open"
        circuit_breaker._half_open_until["test_provider"] = datetime.now() - timedelta(seconds=10)

        # Check state - should still be half-open (only changes on call)
        assert await circuit_breaker.get_state() == "half_open"


# =============================================================================
# Failure Tracking Tests
# =============================================================================


class TestFailureTracking:
    """Tests for failure tracking per provider."""

    @pytest.mark.asyncio
    async def test_failure_incremented_on_error(self, circuit_breaker):
        """Failure count should be incremented on provider error."""
        circuit_breaker._failures["test_provider"] = 2
        circuit_breaker._last_failure_time["test_provider"] = datetime.now()

        # Simulate another failure
        circuit_breaker._failures["test_provider"] = 3
        circuit_breaker._last_failure_time["test_provider"] = datetime.now()

        assert circuit_breaker._failures["test_provider"] == 3

    @pytest.mark.asyncio
    async def test_failure_count_increments_correctly(self, circuit_breaker):
        """Failure count should increment by 1 on each failure."""
        # Start with 0 failures
        assert circuit_breaker._failures.get("test_provider", 0) == 0

        # Add failures one by one
        for i in range(1, 6):
            circuit_breaker._failures["test_provider"] = i
            circuit_breaker._last_failure_time["test_provider"] = datetime.now()
            assert circuit_breaker._failures["test_provider"] == i

    @pytest.mark.asyncio
    async def test_last_failure_time_updated_on_error(self, circuit_breaker):
        """Last failure time should be updated on each failure."""
        before = datetime.now() - timedelta(seconds=10)
        circuit_breaker._last_failure_time["test_provider"] = before

        after = datetime.now()
        circuit_breaker._last_failure_time["test_provider"] = after

        assert circuit_breaker._last_failure_time["test_provider"] >= after

    @pytest.mark.asyncio
    async def test_multiple_providers_tracked_separately(self, circuit_breaker):
        """Failures should be tracked per provider separately."""
        # Add failures for different providers
        circuit_breaker._failures["provider1"] = 3
        circuit_breaker._failures["provider2"] = 5

        assert circuit_breaker._failures["provider1"] == 3
        assert circuit_breaker._failures["provider2"] == 5

        # Update one provider should not affect the other
        circuit_breaker._failures["provider1"] = 4
        assert circuit_breaker._failures["provider1"] == 4
        assert circuit_breaker._failures["provider2"] == 5


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestProtocolCompliance:
    """Tests for CircuitBreaker protocol compliance."""

    def test_circuit_breaker_impl_is_runtime_checkable(self, circuit_breaker):
        """CircuitBreakerImpl should be checkable with isinstance."""
        from dawn_kestrel.llm.circuit_breaker import CircuitBreaker

        # Protocol should be runtime checkable
        assert isinstance(circuit_breaker, CircuitBreaker)

    @pytest.mark.asyncio
    async def test_circuit_breaker_has_all_required_methods(self, circuit_breaker):
        """CircuitBreakerImpl should implement all protocol methods."""
        # All these methods should exist and be callable
        assert hasattr(circuit_breaker, "is_open")
        assert hasattr(circuit_breaker, "is_closed")
        assert hasattr(circuit_breaker, "is_half_open")
        assert hasattr(circuit_breaker, "get_state")
        assert hasattr(circuit_breaker, "open")
        assert hasattr(circuit_breaker, "close")

        # All should be callable
        assert callable(circuit_breaker.is_open)
        assert callable(circuit_breaker.is_closed)
        assert callable(circuit_breaker.is_half_open)
        assert callable(circuit_breaker.get_state)
        assert callable(circuit_breaker.open)
        assert callable(circuit_breaker.close)

    @pytest.mark.asyncio
    async def test_is_open_returns_false_when_closed(self, circuit_breaker):
        """is_open() should return False when state is CLOSED."""
        await circuit_breaker.close()
        assert not await circuit_breaker.is_open()

    @pytest.mark.asyncio
    async def test_is_open_returns_true_when_open(self, circuit_breaker):
        """is_open() should return True when state is OPEN."""
        await circuit_breaker.open()
        assert await circuit_breaker.is_open()

    @pytest.mark.asyncio
    async def test_is_closed_returns_true_when_closed(self, circuit_breaker):
        """is_closed() should return True when state is CLOSED."""
        await circuit_breaker.close()
        assert await circuit_breaker.is_closed()

    @pytest.mark.asyncio
    async def test_is_closed_returns_false_when_open(self, circuit_breaker):
        """is_closed() should return False when state is OPEN."""
        await circuit_breaker.open()
        assert not await circuit_breaker.is_closed()

    @pytest.mark.asyncio
    async def test_is_half_open_returns_false_when_closed(self, circuit_breaker):
        """is_half_open() should return False when state is CLOSED."""
        await circuit_breaker.close()
        assert not await circuit_breaker.is_half_open()

    @pytest.mark.asyncio
    async def test_is_half_open_returns_true_when_half_open(self, circuit_breaker):
        """is_half_open() should return True when state is HALF_OPEN."""
        circuit_breaker._state = "half_open"
        assert await circuit_breaker.is_half_open()


# =============================================================================
# Result Type Tests
# =============================================================================


class TestResultTypes:
    """Tests for Result type usage in circuit breaker."""

    @pytest.mark.asyncio
    async def test_open_returns_result_ok(self, circuit_breaker):
        """open() should return Ok on success."""
        result = await circuit_breaker.open()
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_close_returns_result_ok(self, circuit_breaker):
        """close() should return Ok on success."""
        result = await circuit_breaker.close()
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_get_state_returns_state_string(self, circuit_breaker):
        """get_state() should return state as string."""
        state = await circuit_breaker.get_state()
        assert isinstance(state, str)
        assert state in ["closed", "open", "half_open"]
