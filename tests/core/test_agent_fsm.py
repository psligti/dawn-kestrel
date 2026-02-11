"""Tests for AgentFSM (agent finite state machine)."""

import pytest
import warnings
from dawn_kestrel.core.result import Result, Ok, Err


class TestAgentFSMInitialization:
    """Test AgentFSM initialization."""

    def test_init_with_valid_state_sets_state(self):
        """Initialize FSM with valid state sets state correctly."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        assert fsm._state == "idle"

        fsm = AgentFSMImpl("running")
        assert fsm._state == "running"

        fsm = AgentFSMImpl("paused")
        assert fsm._state == "paused"

        fsm = AgentFSMImpl("completed")
        assert fsm._state == "completed"

        fsm = AgentFSMImpl("failed")
        assert fsm._state == "failed"

        fsm = AgentFSMImpl("cancelled")
        assert fsm._state == "cancelled"

    def test_init_with_invalid_state_raises_valueerror(self):
        """Initialize FSM with invalid state raises ValueError."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        with pytest.raises(ValueError) as exc_info:
            AgentFSMImpl("unknown_state")

        assert "Invalid initial state" in str(exc_info.value)

    def test_default_initial_state_is_idle(self):
        """Default initial state is 'idle'."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl()
        assert fsm._state == "idle"


class TestAgentFSMStateQuery:
    """Test AgentFSM state query methods."""

    @pytest.mark.asyncio
    async def test_get_state_returns_current_state(self):
        """get_state returns the current state."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("running")
        state = await fsm.get_state()
        assert state == "running"

        fsm._state = "completed"
        state = await fsm.get_state()
        assert state == "completed"

    @pytest.mark.asyncio
    async def test_get_state_does_not_modify_state(self):
        """get_state does not modify the internal state."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        initial_state = fsm._state

        await fsm.get_state()

        assert fsm._state == initial_state


class TestAgentFSMTransitionValidation:
    """Test AgentFSM transition validation."""

    @pytest.mark.asyncio
    async def test_valid_transition_returns_true(self):
        """is_transition_valid returns True for valid transitions."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        assert await fsm.is_transition_valid("idle", "running") is True
        assert await fsm.is_transition_valid("idle", "cancelled") is True

        fsm._state = "running"
        assert await fsm.is_transition_valid("running", "paused") is True
        assert await fsm.is_transition_valid("running", "completed") is True
        assert await fsm.is_transition_valid("running", "failed") is True
        assert await fsm.is_transition_valid("running", "cancelled") is True

        fsm._state = "paused"
        assert await fsm.is_transition_valid("paused", "running") is True
        assert await fsm.is_transition_valid("paused", "cancelled") is True

        fsm._state = "completed"
        assert await fsm.is_transition_valid("completed", "idle") is True

        fsm._state = "failed"
        assert await fsm.is_transition_valid("failed", "idle") is True
        assert await fsm.is_transition_valid("failed", "cancelled") is True

        fsm._state = "cancelled"
        assert await fsm.is_transition_valid("cancelled", "idle") is True

    @pytest.mark.asyncio
    async def test_invalid_transition_returns_false(self):
        """is_transition_valid returns False for invalid transitions."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        assert await fsm.is_transition_valid("idle", "completed") is False
        assert await fsm.is_transition_valid("idle", "failed") is False
        assert await fsm.is_transition_valid("idle", "paused") is False

        fsm._state = "running"
        assert await fsm.is_transition_valid("running", "idle") is False

        fsm._state = "completed"
        assert await fsm.is_transition_valid("completed", "running") is False
        assert await fsm.is_transition_valid("completed", "paused") is False

    @pytest.mark.asyncio
    async def test_transition_from_unknown_state_returns_false(self):
        """is_transition_valid returns False when from_state is unknown."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        assert await fsm.is_transition_valid("unknown", "running") is False

    @pytest.mark.asyncio
    async def test_all_valid_transitions_are_allowed(self):
        """Verify all defined valid transitions are allowed."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")

        # Idle transitions
        assert await fsm.is_transition_valid("idle", "running") is True
        assert await fsm.is_transition_valid("idle", "cancelled") is True

        # Running transitions
        assert await fsm.is_transition_valid("running", "paused") is True
        assert await fsm.is_transition_valid("running", "completed") is True
        assert await fsm.is_transition_valid("running", "failed") is True
        assert await fsm.is_transition_valid("running", "cancelled") is True

        # Paused transitions
        assert await fsm.is_transition_valid("paused", "running") is True
        assert await fsm.is_transition_valid("paused", "cancelled") is True

        # Completed transitions
        assert await fsm.is_transition_valid("completed", "idle") is True

        # Failed transitions
        assert await fsm.is_transition_valid("failed", "idle") is True
        assert await fsm.is_transition_valid("failed", "cancelled") is True

        # Cancelled transitions
        assert await fsm.is_transition_valid("cancelled", "idle") is True


class TestAgentFSMStateTransition:
    """Test AgentFSM state transition methods."""

    @pytest.mark.asyncio
    async def test_transition_to_valid_state_succeeds(self):
        """Transition to valid state succeeds and returns Ok."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        result = await fsm.transition_to("running")

        assert isinstance(result, Ok)
        assert result.is_ok() is True
        assert fsm._state == "running"

    @pytest.mark.asyncio
    async def test_transition_to_invalid_state_returns_err(self):
        """Transition to invalid state returns Err."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        result = await fsm.transition_to("completed")

        assert isinstance(result, Err)
        assert result.is_err() is True
        assert fsm._state == "idle"  # State unchanged
        assert "Invalid state transition" in result.error

    @pytest.mark.asyncio
    async def test_transition_updates_state(self):
        """Transition to valid state updates the internal state."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")

        await fsm.transition_to("running")
        assert fsm._state == "running"

        await fsm.transition_to("paused")
        assert fsm._state == "paused"

        await fsm.transition_to("running")
        assert fsm._state == "running"

        await fsm.transition_to("completed")
        assert fsm._state == "completed"

    @pytest.mark.asyncio
    async def test_multiple_valid_transitions_work(self):
        """Multiple valid transitions in sequence work correctly."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")

        # idle -> running -> paused -> running -> completed -> idle
        result1 = await fsm.transition_to("running")
        assert result1.is_ok()
        assert fsm._state == "running"

        result2 = await fsm.transition_to("paused")
        assert result2.is_ok()
        assert fsm._state == "paused"

        result3 = await fsm.transition_to("running")
        assert result3.is_ok()
        assert fsm._state == "running"

        result4 = await fsm.transition_to("completed")
        assert result4.is_ok()
        assert fsm._state == "completed"

        result5 = await fsm.transition_to("idle")
        assert result5.is_ok()
        assert fsm._state == "idle"


class TestAgentFSMInvalidStates:
    """Test AgentFSM rejection of invalid state transitions."""

    @pytest.mark.asyncio
    async def test_transition_from_idle_to_completed_fails(self):
        """Transition from idle to completed should fail."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        result = await fsm.transition_to("completed")

        assert result.is_err()
        assert fsm._state == "idle"
        assert result.code == "INVALID_TRANSITION"

    @pytest.mark.asyncio
    async def test_transition_from_running_to_idle_fails(self):
        """Transition from running to idle should fail."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("running")
        result = await fsm.transition_to("idle")

        assert result.is_err()
        assert fsm._state == "running"
        assert result.code == "INVALID_TRANSITION"

    @pytest.mark.asyncio
    async def test_transition_to_unknown_state_fails(self):
        """Transition to unknown state should fail."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        result = await fsm.transition_to("unknown_state")

        assert result.is_err()
        assert fsm._state == "idle"
        assert result.code == "INVALID_TRANSITION"


class TestAgentFSMStateConstants:
    """Test AgentFSM state constants and transitions."""

    def test_valid_states_contains_all_lifecycle_states(self):
        """VALID_STATES contains all required lifecycle states."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        required_states = {"idle", "running", "paused", "completed", "failed", "cancelled"}
        assert AgentFSMImpl.VALID_STATES == required_states

    def test_valid_transitions_are_complete(self):
        """VALID_TRANSITIONS contains all required transitions."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        transitions = AgentFSMImpl.VALID_TRANSITIONS

        # Check idle transitions
        assert "idle" in transitions
        assert transitions["idle"] == {"running", "cancelled"}

        # Check running transitions
        assert "running" in transitions
        assert transitions["running"] == {"paused", "completed", "failed", "cancelled"}

        # Check paused transitions
        assert "paused" in transitions
        assert transitions["paused"] == {"running", "cancelled"}

        # Check completed transitions
        assert "completed" in transitions
        assert transitions["completed"] == {"idle"}

        # Check failed transitions
        assert "failed" in transitions
        assert transitions["failed"] == {"idle", "cancelled"}

        # Check cancelled transitions
        assert "cancelled" in transitions
        assert transitions["cancelled"] == {"idle"}


class TestAgentFSMProtocol:
    """Test AgentFSM protocol compliance."""

    def test_protocol_is_runtime_checkable(self):
        """AgentFSM protocol is runtime_checkable."""
        from dawn_kestrel.core.agent_fsm import AgentFSM, AgentFSMImpl
        from typing import runtime_checkable

        fsm = AgentFSMImpl()
        assert isinstance(fsm, AgentFSM) is True

    @pytest.mark.asyncio
    async def test_implementation_satisfies_protocol(self):
        """AgentFSMImpl satisfies AgentFSM protocol."""
        from dawn_kestrel.core.agent_fsm import AgentFSM, AgentFSMImpl

        fsm = AgentFSMImpl("idle")

        # Check get_state method exists
        assert hasattr(fsm, "get_state")
        state = await fsm.get_state()
        assert state == "idle"

        # Check is_transition_valid method exists
        assert hasattr(fsm, "is_transition_valid")
        is_valid = await fsm.is_transition_valid("idle", "running")
        assert is_valid is True

        # Check transition_to method exists and returns Result
        assert hasattr(fsm, "transition_to")
        result = await fsm.transition_to("running")
        assert isinstance(result, Result)


class TestAgentFSMErrorHandling:
    """Test AgentFSM error handling and Result types."""

    @pytest.mark.asyncio
    async def test_invalid_transition_returns_err_with_code(self):
        """Invalid transition returns Err with error code."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        result = await fsm.transition_to("completed")

        assert isinstance(result, Err)
        assert result.code is not None
        assert result.code == "INVALID_TRANSITION"
        assert len(result.error) > 0

    @pytest.mark.asyncio
    async def test_result_unwrap_raises_on_err(self):
        """Result.unwrap() raises ValueError on Err."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        result = await fsm.transition_to("completed")

        with pytest.raises(ValueError) as exc_info:
            result.unwrap()

        assert "Invalid state transition" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_result_unwrap_or_returns_default_on_err(self):
        """Result.unwrap_or() returns default on Err."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        fsm = AgentFSMImpl("idle")
        result = await fsm.transition_to("completed")

        default_value = "default"
        assert result.unwrap_or(default_value) == default_value


class TestAgentFSMDeprecation:
    """Test AgentFSM deprecation warnings."""

    def test_agent_fsm_impl_emits_deprecation_warning(self):
        """AgentFSMImpl emits DeprecationWarning when instantiated."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        with pytest.warns(DeprecationWarning, match="AgentFSMImpl is deprecated"):
            AgentFSMImpl("idle")

    def test_agent_fsm_impl_warning_mentions_facade_create_fsm(self):
        """Deprecation warning mentions Facade.create_fsm."""
        from dawn_kestrel.core.agent_fsm import AgentFSMImpl

        with pytest.warns(DeprecationWarning, match="Facade.create_fsm"):
            AgentFSMImpl("idle")

    def test_review_fsm_impl_emits_deprecation_warning(self):
        """ReviewFSMImpl emits DeprecationWarning when instantiated."""
        from dawn_kestrel.agents.review.fsm_security import ReviewFSMImpl

        with pytest.warns(DeprecationWarning, match="ReviewFSMImpl is deprecated"):
            ReviewFSMImpl("idle")

    def test_review_fsm_impl_warning_mentions_facade_create_fsm(self):
        """ReviewFSM deprecation warning mentions Facade.create_fsm."""
        from dawn_kestrel.agents.review.fsm_security import ReviewFSMImpl

        with pytest.warns(DeprecationWarning, match="Facade.create_fsm"):
            ReviewFSMImpl("idle")
