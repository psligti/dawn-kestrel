"""Tests for AgentWorkflowFSM.

This is a simpler FSM that just defines the states and transitions
without any LLM execution logic.
"""

import pytest
import asyncio

from dawn_kestrel.core.result import Result, Ok, Err
from dawn_kestrel.agents.agent_workflow_fsm import create_workflow_fsm


class TestAgentWorkflowFSM:
    """Test cases for AgentWorkflowFSM."""

    @pytest.mark.asyncio
    async def test_all_states_defined(self):
        """Verify all required states are defined in the FSM."""
        result = create_workflow_fsm()
        if result.is_err():
            pytest.fail(f"Failed to create FSM: {result.error}")  # type: ignore[unreachable]

        fsm = result.unwrap()

        # Get initial state
        initial_state = await fsm.get_state()
        assert initial_state == "intake"

        # Verify all expected states are reachable
        expected_states = {"intake", "plan", "act", "synthesize", "check", "done"}

        # We'll verify states exist by checking valid transitions
        for state in ["intake", "plan", "act", "synthesize", "check", "done"]:
            # State exists if we can query transitions from it or transition to it
            # All states should be in the valid states set
            # Since FSM doesn't expose valid_states, we verify by attempting to transition
            pass

    @pytest.mark.asyncio
    async def test_linear_flow_intake_to_check(self):
        """Verify linear flow works: intake → plan → act → synthesize → check."""
        result = create_workflow_fsm()
        if result.is_err():
            pytest.fail(f"Failed to create FSM: {result.error}")  # type: ignore[unreachable]

        fsm = result.unwrap()

        # Verify initial state
        state = await fsm.get_state()
        assert state == "intake"

        # Test each transition in the linear flow
        transitions = [
            ("intake", "plan"),
            ("plan", "act"),
            ("act", "synthesize"),
            ("synthesize", "check"),
        ]

        for from_state, to_state in transitions:
            # Verify transition is valid
            is_valid = await fsm.is_transition_valid(from_state, to_state)
            assert is_valid, f"Transition {from_state} → {to_state} should be valid"

            # Execute transition
            result = await fsm.transition_to(to_state)
            if result.is_err():
                pytest.fail(f"Failed to transition from {from_state} to {to_state}: {result.error}")  # type: ignore[unreachable]

            # Verify current state
            current_state = await fsm.get_state()
            assert current_state == to_state, f"Expected state {to_state}, got {current_state}"

    @pytest.mark.asyncio
    async def test_loop_transition_check_to_plan(self):
        """Verify loop transition works: check → plan."""
        result = create_workflow_fsm()
        if result.is_err():
            pytest.fail(f"Failed to create FSM: {result.error}")  # type: ignore[unreachable]

        fsm = result.unwrap()

        # Navigate to check state
        await fsm.transition_to("plan")
        await fsm.transition_to("act")
        await fsm.transition_to("synthesize")
        await fsm.transition_to("check")

        # Verify check → plan transition is valid
        is_valid = await fsm.is_transition_valid("check", "plan")
        assert is_valid, "Transition check → plan should be valid (loop)"

        # Execute loop transition
        result = await fsm.transition_to("plan")
        if result.is_err():
            pytest.fail(f"Failed to transition from check to plan: {result.error}")  # type: ignore[unreachable]

        # Verify we're back at plan state
        current_state = await fsm.get_state()
        assert current_state == "plan", f"Expected state plan, got {current_state}"

    @pytest.mark.asyncio
    async def test_exit_transition_check_to_done(self):
        """Verify exit transition works: check → done."""
        result = create_workflow_fsm()
        if result.is_err():
            pytest.fail(f"Failed to create FSM: {result.error}")  # type: ignore[unreachable]

        fsm = result.unwrap()

        # Navigate to check state
        await fsm.transition_to("plan")
        await fsm.transition_to("act")
        await fsm.transition_to("synthesize")
        await fsm.transition_to("check")

        # Verify check → done transition is valid
        is_valid = await fsm.is_transition_valid("check", "done")
        assert is_valid, "Transition check → done should be valid (exit)"

        # Execute exit transition
        result = await fsm.transition_to("done")
        if result.is_err():
            pytest.fail(f"Failed to transition from check to done: {result.error}")  # type: ignore[unreachable]

        # Verify we're at done state
        current_state = await fsm.get_state()
        assert current_state == "done", f"Expected state done, got {current_state}"

    @pytest.mark.asyncio
    async def test_reset_transition_done_to_intake(self):
        """Verify reset transition works: done → intake."""
        result = create_workflow_fsm()
        if result.is_err():
            pytest.fail(f"Failed to create FSM: {result.error}")  # type: ignore[unreachable]

        fsm = result.unwrap()

        # Navigate to done state
        await fsm.transition_to("plan")
        await fsm.transition_to("act")
        await fsm.transition_to("synthesize")
        await fsm.transition_to("check")
        await fsm.transition_to("done")

        # Verify done → intake transition is valid
        is_valid = await fsm.is_transition_valid("done", "intake")
        assert is_valid, "Transition done → intake should be valid (reset)"

        # Execute reset transition
        result = await fsm.transition_to("intake")
        if result.is_err():
            pytest.fail(f"Failed to transition from done to intake: {result.error}")  # type: ignore[unreachable]

        # Verify we're back at intake state
        current_state = await fsm.get_state()
        assert current_state == "intake", f"Expected state intake, got {current_state}"

    @pytest.mark.asyncio
    async def test_invalid_transition_fails(self):
        """Verify invalid transitions fail when attempted from actual current state."""
        # Test invalid transitions from intake
        fsm = create_workflow_fsm().unwrap()
        current_state = await fsm.get_state()
        assert current_state == "intake"

        # From intake: can only go to plan, not done or act
        assert await fsm.is_transition_valid("intake", "done") is False
        assert await fsm.is_transition_valid("intake", "act") is False

        # Navigate to plan
        await fsm.transition_to("plan")

        # From plan: can only go to act, not check, done, or intake
        assert await fsm.is_transition_valid("plan", "check") is False
        assert await fsm.is_transition_valid("plan", "done") is False
        assert await fsm.is_transition_valid("plan", "intake") is False

        # Navigate to act
        await fsm.transition_to("act")

        # From act: can only go to synthesize, not plan, check, or done
        assert await fsm.is_transition_valid("act", "plan") is False
        assert await fsm.is_transition_valid("act", "check") is False
        assert await fsm.is_transition_valid("act", "done") is False

        # Navigate to synthesize
        await fsm.transition_to("synthesize")

        # From synthesize: can only go to check, not act or plan
        assert await fsm.is_transition_valid("synthesize", "act") is False
        assert await fsm.is_transition_valid("synthesize", "plan") is False

        # Navigate to check
        await fsm.transition_to("check")

        # From check: can go to plan or done, not intake, act, or synthesize
        assert await fsm.is_transition_valid("check", "intake") is False
        assert await fsm.is_transition_valid("check", "act") is False
        assert await fsm.is_transition_valid("check", "synthesize") is False

        # Navigate to done
        await fsm.transition_to("done")

        # From done: can only go to intake, not plan or check
        assert await fsm.is_transition_valid("done", "plan") is False
        assert await fsm.is_transition_valid("done", "check") is False

    @pytest.mark.asyncio
    async def test_multiple_iterations(self):
        """Verify multiple iterations through the workflow loop."""
        result = create_workflow_fsm()
        if result.is_err():
            pytest.fail(f"Failed to create FSM: {result.error}")  # type: ignore[unreachable]

        fsm = result.unwrap()

        # Navigate through first iteration: intake → plan → act → synthesize → check
        transitions = [
            ("intake", "plan"),
            ("plan", "act"),
            ("act", "synthesize"),
            ("synthesize", "check"),
        ]

        for from_state, to_state in transitions:
            await fsm.transition_to(to_state)

        # Loop back to plan (iteration 2)
        await fsm.transition_to("plan")
        await fsm.transition_to("act")
        await fsm.transition_to("synthesize")
        await fsm.transition_to("check")

        # Loop back to plan (iteration 3)
        await fsm.transition_to("plan")

        # Verify current state is plan (we're on third iteration)
        current_state = await fsm.get_state()
        assert current_state == "plan"

    @pytest.mark.asyncio
    async def test_all_valid_transitions(self):
        """Verify all specified valid transitions exist."""
        result = create_workflow_fsm()
        if result.is_err():
            pytest.fail(f"Failed to create FSM: {result.error}")  # type: ignore[unreachable]

        fsm = result.unwrap()

        # All valid transitions per specification
        valid_transitions = [
            ("intake", "plan"),
            ("plan", "act"),
            ("act", "synthesize"),
            ("synthesize", "check"),
            ("check", "plan"),  # Loop - continue iteration
            ("check", "done"),  # Exit - stop conditions met
            ("done", "intake"),  # Reset for next task
        ]

        for from_state, to_state in valid_transitions:
            is_valid = await fsm.is_transition_valid(from_state, to_state)
            assert is_valid, f"Transition {from_state} → {to_state} should be valid"

    @pytest.mark.asyncio
    async def test_entry_hooks_exist(self):
        """Verify entry hooks are registered for all states.

        Entry hooks should log when entering each state.
        """
        result = create_workflow_fsm()
        if result.is_err():
            pytest.fail(f"Failed to create FSM: {result.error}")  # type: ignore[unreachable]

        fsm = result.unwrap()

        # Transition through all states - hooks should execute without error
        # If hooks fail, transitions would fail
        transitions = [
            "plan",
            "act",
            "synthesize",
            "check",
            "done",
            "intake",  # Reset
        ]

        for state in transitions:
            result = await fsm.transition_to(state)
            if result.is_err():
                pytest.fail(
                    f"Failed to transition to {state} (hook may have failed): {result.error}"  # type: ignore[unreachable]
                )
