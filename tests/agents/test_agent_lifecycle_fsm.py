"""Test suite for AgentLifecycleFSM.

Tests the AgentLifecycleFSM state machine with all valid transitions
and state validation.
"""

import pytest

from dawn_kestrel.core.result import Ok, Err
from dawn_kestrel.agents.agent_lifecycle_fsm import create_lifecycle_fsm, VALID_LIFECYCLE_STATES


@pytest.fixture
def lifecycle_fsm():
    """Create an AgentLifecycleFSM instance for testing."""
    result = create_lifecycle_fsm()
    assert result.is_ok(), f"Failed to create lifecycle FSM: {result}"
    return result.unwrap()


class TestAgentLifecycleFSMStates:
    """Test lifecycle FSM state definitions."""

    def test_all_states_are_defined(self):
        """Test that all required states are defined."""
        expected_states = {"idle", "running", "paused", "completed", "failed", "cancelled"}
        assert VALID_LIFECYCLE_STATES == expected_states

    async def test_fsm_creates_with_idle_state(self, lifecycle_fsm):
        """Test that FSM starts in idle state."""
        state = await lifecycle_fsm.get_state()
        assert state == "idle"


class TestAgentLifecycleFSMValidTransitions:
    """Test valid state transitions."""

    async def test_idle_to_running(self, lifecycle_fsm):
        """Test idle -> running transition is valid."""
        result = await lifecycle_fsm.transition_to("running")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "running"

    async def test_idle_to_cancelled(self, lifecycle_fsm):
        """Test idle -> cancelled transition is valid."""
        result = await lifecycle_fsm.transition_to("cancelled")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "cancelled"

    async def test_running_to_paused(self, lifecycle_fsm):
        """Test running -> paused transition is valid."""
        # First transition to running
        await lifecycle_fsm.transition_to("running")

        # Then transition to paused
        result = await lifecycle_fsm.transition_to("paused")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "paused"

    async def test_running_to_completed(self, lifecycle_fsm):
        """Test running -> completed transition is valid."""
        # First transition to running
        await lifecycle_fsm.transition_to("running")

        # Then transition to completed
        result = await lifecycle_fsm.transition_to("completed")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "completed"

    async def test_running_to_failed(self, lifecycle_fsm):
        """Test running -> failed transition is valid."""
        # First transition to running
        await lifecycle_fsm.transition_to("running")

        # Then transition to failed
        result = await lifecycle_fsm.transition_to("failed")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "failed"

    async def test_running_to_cancelled(self, lifecycle_fsm):
        """Test running -> cancelled transition is valid."""
        # First transition to running
        await lifecycle_fsm.transition_to("running")

        # Then transition to cancelled
        result = await lifecycle_fsm.transition_to("cancelled")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "cancelled"

    async def test_paused_to_running(self, lifecycle_fsm):
        """Test paused -> running transition is valid."""
        # First transition: idle -> running -> paused
        await lifecycle_fsm.transition_to("running")
        await lifecycle_fsm.transition_to("paused")

        # Then transition back to running
        result = await lifecycle_fsm.transition_to("running")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "running"

    async def test_paused_to_cancelled(self, lifecycle_fsm):
        """Test paused -> cancelled transition is valid."""
        # First transition: idle -> running -> paused
        await lifecycle_fsm.transition_to("running")
        await lifecycle_fsm.transition_to("paused")

        # Then transition to cancelled
        result = await lifecycle_fsm.transition_to("cancelled")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "cancelled"

    async def test_completed_to_idle_reset(self, lifecycle_fsm):
        """Test completed -> idle reset transition is valid."""
        # First transition: idle -> running -> completed
        await lifecycle_fsm.transition_to("running")
        await lifecycle_fsm.transition_to("completed")

        # Then reset to idle
        result = await lifecycle_fsm.transition_to("idle")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "idle"

    async def test_failed_to_idle_reset(self, lifecycle_fsm):
        """Test failed -> idle reset transition is valid."""
        # First transition: idle -> running -> failed
        await lifecycle_fsm.transition_to("running")
        await lifecycle_fsm.transition_to("failed")

        # Then reset to idle
        result = await lifecycle_fsm.transition_to("idle")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "idle"

    async def test_cancelled_to_idle_reset(self, lifecycle_fsm):
        """Test cancelled -> idle reset transition is valid."""
        # First transition to cancelled
        await lifecycle_fsm.transition_to("cancelled")

        # Then reset to idle
        result = await lifecycle_fsm.transition_to("idle")
        assert result.is_ok(), f"Transition failed: {result}"
        state = await lifecycle_fsm.get_state()
        assert state == "idle"


class TestAgentLifecycleFSMInvalidTransitions:
    """Test invalid state transitions."""

    async def test_idle_to_completed_is_invalid(self, lifecycle_fsm):
        """Test idle -> completed transition is invalid."""
        result = await lifecycle_fsm.transition_to("completed")
        assert result.is_err(), "Transition should have failed"
        assert "INVALID_TRANSITION" in result.code

    async def test_idle_to_failed_is_invalid(self, lifecycle_fsm):
        """Test idle -> failed transition is invalid."""
        result = await lifecycle_fsm.transition_to("failed")
        assert result.is_err(), "Transition should have failed"
        assert "INVALID_TRANSITION" in result.code

    async def test_idle_to_paused_is_invalid(self, lifecycle_fsm):
        """Test idle -> paused transition is invalid."""
        result = await lifecycle_fsm.transition_to("paused")
        assert result.is_err(), "Transition should have failed"
        assert "INVALID_TRANSITION" in result.code

    async def test_running_to_idle_is_invalid(self, lifecycle_fsm):
        """Test running -> idle transition is invalid."""
        # First transition to running
        await lifecycle_fsm.transition_to("running")

        # Try to transition back to idle (should fail - must go through completed/failed/cancelled)
        result = await lifecycle_fsm.transition_to("idle")
        assert result.is_err(), "Transition should have failed"
        assert "INVALID_TRANSITION" in result.code

    async def test_paused_to_completed_is_invalid(self, lifecycle_fsm):
        """Test paused -> completed transition is invalid."""
        # First transition: idle -> running -> paused
        await lifecycle_fsm.transition_to("running")
        await lifecycle_fsm.transition_to("paused")

        # Try to transition to completed (should fail - must resume to running first)
        result = await lifecycle_fsm.transition_to("completed")
        assert result.is_err(), "Transition should have failed"
        assert "INVALID_TRANSITION" in result.code

    async def test_paused_to_failed_is_invalid(self, lifecycle_fsm):
        """Test paused -> failed transition is invalid."""
        # First transition: idle -> running -> paused
        await lifecycle_fsm.transition_to("running")
        await lifecycle_fsm.transition_to("paused")

        # Try to transition to failed (should fail - must resume to running first)
        result = await lifecycle_fsm.transition_to("failed")
        assert result.is_err(), "Transition should have failed"
        assert "INVALID_TRANSITION" in result.code

    async def test_completed_to_running_is_invalid(self, lifecycle_fsm):
        """Test completed -> running transition is invalid."""
        # First transition: idle -> running -> completed
        await lifecycle_fsm.transition_to("running")
        await lifecycle_fsm.transition_to("completed")

        # Try to transition to running (should fail - must reset to idle first)
        result = await lifecycle_fsm.transition_to("running")
        assert result.is_err(), "Transition should have failed"
        assert "INVALID_TRANSITION" in result.code

    async def test_failed_to_running_is_invalid(self, lifecycle_fsm):
        """Test failed -> running transition is invalid."""
        # First transition: idle -> running -> failed
        await lifecycle_fsm.transition_to("running")
        await lifecycle_fsm.transition_to("failed")

        # Try to transition to running (should fail - must reset to idle first)
        result = await lifecycle_fsm.transition_to("running")
        assert result.is_err(), "Transition should have failed"
        assert "INVALID_TRANSITION" in result.code

    async def test_cancelled_to_running_is_invalid(self, lifecycle_fsm):
        """Test cancelled -> running transition is invalid."""
        # First transition to cancelled
        await lifecycle_fsm.transition_to("cancelled")

        # Try to transition to running (should fail - must reset to idle first)
        result = await lifecycle_fsm.transition_to("running")
        assert result.is_err(), "Transition should have failed"
        assert "INVALID_TRANSITION" in result.code


class TestAgentLifecycleFSMTransitionValidation:
    """Test is_transition_valid method."""

    async def test_idle_to_running_is_valid(self, lifecycle_fsm):
        """Test is_transition_valid returns True for idle -> running."""
        is_valid = await lifecycle_fsm.is_transition_valid("idle", "running")
        assert is_valid is True

    async def test_idle_to_completed_is_invalid(self, lifecycle_fsm):
        """Test is_transition_valid returns False for idle -> completed."""
        is_valid = await lifecycle_fsm.is_transition_valid("idle", "completed")
        assert is_valid is False

    async def test_running_to_paused_is_valid(self, lifecycle_fsm):
        """Test is_transition_valid returns True for running -> paused."""
        is_valid = await lifecycle_fsm.is_transition_valid("running", "paused")
        assert is_valid is True

    async def test_invalid_state_returns_false(self, lifecycle_fsm):
        """Test is_transition_valid returns False for invalid state."""
        is_valid = await lifecycle_fsm.is_transition_valid("unknown_state", "running")
        assert is_valid is False


class TestAgentLifecycleFSMCompleteWorkflow:
    """Test complete agent lifecycle workflow."""

    async def test_full_success_workflow(self, lifecycle_fsm):
        """Test complete successful workflow: idle -> running -> completed -> idle."""
        # Start in idle
        assert await lifecycle_fsm.get_state() == "idle"

        # Start running
        result = await lifecycle_fsm.transition_to("running")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "running"

        # Complete
        result = await lifecycle_fsm.transition_to("completed")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "completed"

        # Reset to idle
        result = await lifecycle_fsm.transition_to("idle")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "idle"

    async def test_pause_and_resume_workflow(self, lifecycle_fsm):
        """Test workflow with pause and resume: idle -> running -> paused -> running -> completed -> idle."""
        # Start in idle
        assert await lifecycle_fsm.get_state() == "idle"

        # Start running
        result = await lifecycle_fsm.transition_to("running")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "running"

        # Pause
        result = await lifecycle_fsm.transition_to("paused")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "paused"

        # Resume
        result = await lifecycle_fsm.transition_to("running")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "running"

        # Complete
        result = await lifecycle_fsm.transition_to("completed")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "completed"

        # Reset to idle
        result = await lifecycle_fsm.transition_to("idle")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "idle"

    async def test_failure_workflow(self, lifecycle_fsm):
        """Test failure workflow: idle -> running -> failed -> idle."""
        # Start in idle
        assert await lifecycle_fsm.get_state() == "idle"

        # Start running
        result = await lifecycle_fsm.transition_to("running")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "running"

        # Fail
        result = await lifecycle_fsm.transition_to("failed")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "failed"

        # Reset to idle
        result = await lifecycle_fsm.transition_to("idle")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "idle"

    async def test_cancellation_workflow(self, lifecycle_fsm):
        """Test cancellation workflow: idle -> cancelled -> idle."""
        # Start in idle
        assert await lifecycle_fsm.get_state() == "idle"

        # Cancel immediately
        result = await lifecycle_fsm.transition_to("cancelled")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "cancelled"

        # Reset to idle
        result = await lifecycle_fsm.transition_to("idle")
        assert result.is_ok()
        assert await lifecycle_fsm.get_state() == "idle"
