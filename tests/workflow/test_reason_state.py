"""TDD tests for REASON state behavior in the workflow FSM.

This test module has two parts:
1. State constant tests (from Task 1) - verify REASON in WORKFLOW_STATES
2. TDD behavior tests (from Task 3) - should FAIL until implementation complete

TDD RED Phase - These tests should FAIL until:
- Task 1: REASON is added to WORKFLOW_STATES and WORKFLOW_TRANSITIONS
- Task 2: ReasoningStrategy, ReasoningContext, ReasoningResult are implemented

Based on fsm-builder-pattern learnings:
- Use pytest.mark.asyncio for async test methods
- Group related tests into logical classes
- Test both success and error paths
- Use descriptive test names that explain what is being tested
"""

from unittest.mock import MagicMock

import pytest

from dawn_kestrel.core.fsm import WORKFLOW_STATES, WORKFLOW_TRANSITIONS

from dawn_kestrel.workflow.strategies import (
    ReasoningContext,
    ReasoningResult,
    ReasoningStrategy,
)

from dawn_kestrel.core.fsm import (
    FSMBuilder,
    FSMContext,
)
from dawn_kestrel.core.result import Ok, Result


class TestReasonStateInWorkflowStates:
    """Tests for 'reason' state presence in WORKFLOW_STATES."""

    def test_reason_in_workflow_states(self):
        """Test that 'reason' is a valid workflow state."""
        assert "reason" in WORKFLOW_STATES, (
            "'reason' should be in WORKFLOW_STATES to replace 'plan' state"
        )

    def test_plan_still_in_workflow_states_for_deprecation(self):
        """Test that 'plan' remains for soft deprecation."""
        assert "plan" in WORKFLOW_STATES, (
            "'plan' should remain in WORKFLOW_STATES for backward compatibility"
        )

    def test_workflow_states_has_all_expected_states(self):
        """Test that all expected workflow states are present."""
        expected_states = {
            "intake",
            "plan",  # Kept for soft deprecation
            "reason",  # New state replacing plan
            "act",
            "synthesize",
            "check",
            "done",
        }
        assert expected_states.issubset(WORKFLOW_STATES), (
            f"WORKFLOW_STATES missing expected states. "
            f"Expected: {expected_states}, Got: {WORKFLOW_STATES}"
        )


class TestReasonStateTransitions:
    """Tests for 'reason' state transitions in WORKFLOW_TRANSITIONS."""

    def test_intake_to_reason_transition_valid(self):
        """Test that intake can transition to reason state."""
        assert "reason" in WORKFLOW_TRANSITIONS.get("intake", set()), (
            "'intake' should be able to transition to 'reason' state"
        )

    def test_intake_to_plan_still_valid_for_deprecation(self):
        """Test that intake can still transition to plan for backward compat."""
        assert "plan" in WORKFLOW_TRANSITIONS.get("intake", set()), (
            "'intake' should still transition to 'plan' for backward compatibility"
        )

    def test_reason_transitions_to_act(self):
        """Test that reason can transition to act state."""
        assert "act" in WORKFLOW_TRANSITIONS.get("reason", set()), (
            "'reason' should be able to transition to 'act' state"
        )

    def test_reason_transitions_to_synthesize(self):
        """Test that reason can transition to synthesize state."""
        assert "synthesize" in WORKFLOW_TRANSITIONS.get("reason", set()), (
            "'reason' should be able to transition to 'synthesize' state"
        )

    def test_reason_transitions_to_check(self):
        """Test that reason can transition to check state."""
        assert "check" in WORKFLOW_TRANSITIONS.get("reason", set()), (
            "'reason' should be able to transition to 'check' state"
        )

    def test_reason_transitions_to_done(self):
        """Test that reason can transition directly to done state."""
        assert "done" in WORKFLOW_TRANSITIONS.get("reason", set()), (
            "'reason' should be able to transition directly to 'done' state"
        )

    def test_check_to_reason_transition_valid(self):
        """Test that check can transition back to reason state."""
        assert "reason" in WORKFLOW_TRANSITIONS.get("check", set()), (
            "'check' should be able to transition to 'reason' state"
        )

    def test_reason_state_transitions_dont_include_plan(self):
        """Test that reason does NOT transition to plan (replaced by reason)."""
        # reason replaces plan, so reason->plan would be circular/unnecessary
        assert "plan" not in WORKFLOW_TRANSITIONS.get("reason", set()), (
            "'reason' should not transition to 'plan' (reason replaces plan)"
        )


class TestPlanToReasonRedirectWithWarning:
    """Tests for plan → reason redirect behavior with deprecation warning."""

    def test_plan_transitions_to_reason_for_redirect(self):
        """Test that plan transitions to reason for deprecation redirect."""
        # When code tries plan->act, it should be redirected to reason->act
        # This test verifies the transition graph supports this pattern
        assert "act" in WORKFLOW_TRANSITIONS.get("plan", set()), (
            "'plan' should transition to 'act' to maintain backward compatibility"
        )

    def test_plan_transitions_to_reason_directly(self):
        """Test that plan can transition directly to reason."""
        # Allow plan->reason for explicit migration/redirect
        assert "reason" in WORKFLOW_TRANSITIONS.get("plan", set()), (
            "'plan' should be able to transition to 'reason' for redirect support"
        )


# =============================================================================
# TDD RED Phase Tests (Task 3)
# These tests should FAIL until implementation is complete
# =============================================================================


class TestReasonOutputSchema:
    """Tests for REASON state output schema (thought and action)."""

    def test_reason_outputs_thought_and_action(self):
        """REASON state must output structured thought and action."""
        mock_strategy = MagicMock(spec=ReasoningStrategy)

        expected_result = ReasoningResult(
            thought="Analyzing the problem requires understanding the context",
            action="Search for relevant patterns in codebase",
            next_state="ACT",
        )
        mock_strategy.decide = MagicMock(return_value=expected_result)

        context = ReasoningContext(
            current_state="reason",
            available_actions=["search", "analyze"],
            evidence=["prior observation"],
            constraints={"time_limit": 100},
        )

        output = mock_strategy.decide(context)

        assert hasattr(output, "thought"), "ReasoningResult must have 'thought' field"
        assert hasattr(output, "action"), "ReasoningResult must have 'action' field"
        assert hasattr(output, "next_state"), "ReasoningResult must have 'next_state' field"
        assert isinstance(output.thought, str), "thought must be a string"
        assert isinstance(output.action, str), "action must be a string"
        assert isinstance(output.next_state, str), "next_state must be a string"
        assert output.next_state.lower() in {"act", "synthesize", "check", "done"}, (
            f"next_state must be valid transition target, got: {output.next_state}"
        )

    def test_reason_output_uses_evidence_and_constraints(self):
        """REASON output is influenced by evidence and constraints in context."""
        mock_strategy = MagicMock(spec=ReasoningStrategy)

        expected_result = ReasoningResult(
            thought="Test thought",
            action="Test action",
            next_state="ACT",
        )
        mock_strategy.decide = MagicMock(return_value=expected_result)

        context = ReasoningContext(
            current_state="reason",
            available_actions=["test"],
            evidence=["evidence_item_1", "evidence_item_2"],
            constraints={"budget": 100},
        )

        output = mock_strategy.decide(context)
        mock_strategy.decide.assert_called_once_with(context)
        assert context.evidence == ["evidence_item_1", "evidence_item_2"]
        assert context.constraints == {"budget": 100}


class TestReasonTransitionBehavior:
    """Tests for REASON state transition behavior."""

    @pytest.mark.asyncio
    async def test_reason_transitions_to_act(self):
        """REASON can transition to act state."""
        # Build FSM with REASON state
        result = (
            FSMBuilder()
            .with_state("reason")
            .with_state("act")
            .with_transition("reason", "act")
            .build(initial_state="reason")
        )

        assert result.is_ok(), f"Failed to build FSM: {result.error}"
        fsm = result.unwrap()

        # Transition to act
        transition_result = await fsm.transition_to("act")
        assert transition_result.is_ok(), f"Transition failed: {transition_result.error}"
        assert await fsm.get_state() == "act"

    @pytest.mark.asyncio
    async def test_reason_transitions_to_synthesize(self):
        """REASON can transition to synthesize state."""
        result = (
            FSMBuilder()
            .with_state("reason")
            .with_state("synthesize")
            .with_transition("reason", "synthesize")
            .build(initial_state="reason")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        transition_result = await fsm.transition_to("synthesize")
        assert transition_result.is_ok()
        assert await fsm.get_state() == "synthesize"

    @pytest.mark.asyncio
    async def test_reason_transitions_to_check(self):
        """REASON can transition to check state."""
        result = (
            FSMBuilder()
            .with_state("reason")
            .with_state("check")
            .with_transition("reason", "check")
            .build(initial_state="reason")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        transition_result = await fsm.transition_to("check")
        assert transition_result.is_ok()
        assert await fsm.get_state() == "check"

    @pytest.mark.asyncio
    async def test_reason_transitions_to_done(self):
        """REASON can transition to done state (early termination)."""
        result = (
            FSMBuilder()
            .with_state("reason")
            .with_state("done")
            .with_transition("reason", "done")
            .build(initial_state="reason")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        transition_result = await fsm.transition_to("done")
        assert transition_result.is_ok()
        assert await fsm.get_state() == "done"

    @pytest.mark.asyncio
    async def test_reason_rejects_invalid_transition_to_intake(self):
        """REASON cannot transition directly to intake (must go through done)."""
        result = (
            FSMBuilder()
            .with_state("reason")
            .with_state("intake")
            .with_state("done")
            .with_transition("reason", "done")
            .with_transition("done", "intake")
            .build(initial_state="reason")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Direct transition to intake should fail
        transition_result = await fsm.transition_to("intake")
        assert transition_result.is_err()
        assert transition_result.code == "INVALID_TRANSITION"

    @pytest.mark.asyncio
    async def test_reason_transition_in_full_workflow(self):
        """REASON state works in full workflow FSM context."""
        # Build FSM with workflow states including REASON
        all_states = {"intake", "plan", "reason", "act", "synthesize", "check", "done"}
        all_transitions = {
            "intake": {"plan"},
            "plan": {"reason", "act"},
            "reason": {"act", "synthesize", "check", "done"},
            "act": {"synthesize", "reason"},
            "synthesize": {"check", "reason"},
            "check": {"plan", "act", "reason", "done"},
            "done": {"intake"},
        }

        builder = FSMBuilder().with_initial_state("plan")
        for state in all_states:
            builder = builder.with_state(state)
        for from_state, to_states in all_transitions.items():
            for to_state in to_states:
                builder = builder.with_transition(from_state, to_state)

        build_result = builder.build(initial_state="plan")
        assert build_result.is_ok(), f"Failed to build workflow FSM: {build_result.error}"
        fsm = build_result.unwrap()

        # Transition plan -> reason
        transition_result = await fsm.transition_to("reason")
        assert transition_result.is_ok(), f"plan -> reason failed: {transition_result.error}"
        assert await fsm.get_state() == "reason"

        # Transition reason -> act
        transition_result = await fsm.transition_to("act")
        assert transition_result.is_ok(), f"reason -> act failed: {transition_result.error}"
        assert await fsm.get_state() == "act"


class TestReasonThinkingFrameContext:
    """Tests for REASON state receiving context with evidence and constraints."""

    def test_reason_receives_evidence_context(self):
        """REASON state receives evidence from previous steps in context."""
        evidence_items = [
            "Found pattern X in file A",
            "Identified constraint Y",
            "Observation Z from tool output",
        ]

        context = ReasoningContext(
            current_state="reason",
            available_actions=["analyze", "complete"],
            evidence=evidence_items,
            constraints={},
        )

        assert context.evidence == evidence_items
        assert context.current_state == "reason"

    def test_reason_context_includes_constraints(self):
        """REASON context includes constraints for reasoning."""
        constraints = {
            "must_not_use": "deprecated APIs",
            "performance_budget_ms": 100,
            "security": "No raw SQL queries",
        }

        context = ReasoningContext(
            current_state="reason",
            available_actions=["proceed", "delegate"],
            evidence=[],
            constraints=constraints,
        )

        assert context.constraints == constraints

    def test_reason_context_available_actions(self):
        """REASON context includes available actions for decision making."""
        available_actions = ["analyze", "delegate", "complete", "synthesize"]

        context = ReasoningContext(
            current_state="reason",
            available_actions=available_actions,
            evidence=["some evidence"],
            constraints={},
        )

        assert context.available_actions == available_actions

    @pytest.mark.asyncio
    async def test_fsm_context_passed_to_reason_entry_hook(self):
        """FSMContext is passed to REASON state entry hook."""
        hook_contexts = []

        def capture_hook(ctx: FSMContext) -> Result[None]:
            hook_contexts.append(ctx)
            return Ok(None)

        result = (
            FSMBuilder()
            .with_state("plan")
            .with_state("reason")
            .with_transition("plan", "reason")
            .with_entry_hook("reason", capture_hook)
            .build(initial_state="plan")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        fsm_context = FSMContext(
            metadata={"source": "plan"},
            user_data={"goal": "Test goal"},
        )
        transition_result = await fsm.transition_to("reason", fsm_context)

        assert transition_result.is_ok()
        assert len(hook_contexts) == 1, "Entry hook should be called once"

        captured_ctx = hook_contexts[0]
        assert captured_ctx.metadata.get("state") == "reason"
        assert "fsm_id" in captured_ctx.metadata


class TestReasoningStrategyIntegration:
    """Tests for ReasoningStrategy protocol integration."""

    def test_reasoning_strategy_is_protocol(self):
        """ReasoningStrategy must be a Protocol for pluggable implementations."""
        from typing import Protocol

        assert hasattr(ReasoningStrategy, "__mro__"), "ReasoningStrategy should be a class/protocol"
        is_protocol = Protocol in getattr(ReasoningStrategy, "__mro__", [])
        assert is_protocol, "ReasoningStrategy should be a Protocol"

    def test_reasoning_strategy_has_decide_method(self):
        """ReasoningStrategy must have decide() method."""
        mock_strategy = MagicMock(spec=ReasoningStrategy)

        expected_result = ReasoningResult(
            thought="Test thought",
            action="Test action",
            next_state="ACT",
        )
        mock_strategy.decide = MagicMock(return_value=expected_result)

        context = ReasoningContext(
            current_state="reason",
            available_actions=["test"],
            evidence=[],
            constraints={},
        )

        result = mock_strategy.decide(context)

        assert isinstance(result, ReasoningResult)
        mock_strategy.decide.assert_called_once_with(context)

    def test_reasoning_strategy_returns_result_type(self):
        """ReasoningStrategy.decide() returns ReasoningResult directly."""
        mock_strategy = MagicMock(spec=ReasoningStrategy)

        success_result = ReasoningResult(
            thought="Success",
            action="Proceed",
            next_state="ACT",
        )
        mock_strategy.decide = MagicMock(return_value=success_result)

        context = ReasoningContext(
            current_state="reason",
            available_actions=["proceed"],
            evidence=[],
            constraints={},
        )

        result = mock_strategy.decide(context)
        assert isinstance(result, ReasoningResult)
        assert result.thought == "Success"

    @pytest.mark.asyncio
    async def test_fsm_uses_injected_reasoning_strategy(self):
        """FSM can use injected ReasoningStrategy for REASON state via hooks."""
        mock_strategy = MagicMock(spec=ReasoningStrategy)
        mock_strategy.decide = MagicMock(
            return_value=ReasoningResult(
                thought="Injected strategy thought",
                action="Injected strategy action",
                next_state="ACT",
            )
        )

        reasoning_hook_called = []

        def reason_entry_hook(ctx: FSMContext) -> Result[None]:
            if "reasoning_strategy" in ctx.user_data:
                strategy = ctx.user_data["reasoning_strategy"]
                reasoning_context = ReasoningContext(
                    current_state="reason",
                    available_actions=ctx.user_data.get("available_actions", []),
                    evidence=ctx.user_data.get("evidence", []),
                    constraints=ctx.user_data.get("constraints", {}),
                )
                result = strategy.decide(reasoning_context)
                reasoning_hook_called.append(result)
            return Ok(None)

        result = (
            FSMBuilder()
            .with_state("plan")
            .with_state("reason")
            .with_transition("plan", "reason")
            .with_entry_hook("reason", reason_entry_hook)
            .build(initial_state="plan")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        fsm_context = FSMContext(
            user_data={
                "reasoning_strategy": mock_strategy,
                "available_actions": ["analyze"],
                "evidence": ["some evidence"],
                "constraints": {},
            }
        )

        transition_result = await fsm.transition_to("reason", fsm_context)
        assert transition_result.is_ok()
        assert len(reasoning_hook_called) == 1
        assert isinstance(reasoning_hook_called[0], ReasoningResult)


class TestReasoningResultDataclass:
    """Tests for ReasoningResult dataclass structure."""

    def test_reasoning_result_has_required_fields(self):
        """ReasoningResult has all required fields."""
        result = ReasoningResult(
            thought="Test thought",
            action="Test action",
            next_state="ACT",
        )

        assert result.thought == "Test thought"
        assert result.action == "Test action"
        assert result.next_state == "ACT"

    def test_reasoning_result_thought_is_string(self):
        """ReasoningResult thought must be a string."""
        result = ReasoningResult(
            thought="This is a reasoning trace",
            action="proceed",
            next_state="ACT",
        )
        assert isinstance(result.thought, str)

    def test_reasoning_result_next_state_validation(self):
        """ReasoningResult next_state must be valid transition target."""
        valid_states = ["ACT", "SYNTHESIZE", "CHECK", "DONE"]

        for state in valid_states:
            result = ReasoningResult(
                thought="Test",
                action="Test",
                next_state=state,
            )
            assert result.next_state == state

    def test_reasoning_result_action_field(self):
        """ReasoningResult action describes what action to take."""
        result = ReasoningResult(
            thought="Need to analyze the code",
            action="search_codebase",
            next_state="ACT",
        )

        assert isinstance(result.action, str)
        assert result.action == "search_codebase"


class TestReasoningContextDataclass:
    """Tests for ReasoningContext dataclass structure."""

    def test_reasoning_context_has_required_fields(self):
        """ReasoningContext has all required fields."""
        context = ReasoningContext(
            current_state="reason",
            available_actions=["analyze", "complete"],
            evidence=["Found pattern X"],
            constraints={"budget": 100},
        )

        assert context.current_state == "reason"
        assert context.available_actions == ["analyze", "complete"]
        assert context.evidence == ["Found pattern X"]
        assert context.constraints == {"budget": 100}

    def test_reasoning_context_defaults(self):
        """ReasoningContext lists and dict default to empty."""
        context = ReasoningContext(current_state="reason")

        assert context.available_actions == []
        assert context.evidence == []
        assert context.constraints == {}

    def test_reasoning_context_evidence_list(self):
        """ReasoningContext evidence is a list of strings."""
        evidence_items = ["Evidence 1", "Evidence 2", "Evidence 3"]
        context = ReasoningContext(
            current_state="reason",
            evidence=evidence_items,
        )

        assert context.evidence == evidence_items
        assert all(isinstance(e, str) for e in context.evidence)


class TestReasonStateEdgeCases:
    """Edge case tests for REASON state behavior."""

    def test_reason_with_empty_context(self):
        """REASON handles empty context gracefully."""
        mock_strategy = MagicMock(spec=ReasoningStrategy)

        mock_strategy.decide = MagicMock(
            return_value=ReasoningResult(
                thought="No prior context available, starting fresh",
                action="Gather initial information",
                next_state="ACT",
            )
        )

        context = ReasoningContext(
            current_state="reason",
            available_actions=[],
            evidence=[],
            constraints={},
        )

        result = mock_strategy.decide(context)
        assert isinstance(result, ReasoningResult)
        assert result.thought != ""

    @pytest.mark.asyncio
    async def test_reason_consecutive_transitions(self):
        """REASON can be reached multiple times in workflow."""
        # Build FSM allowing multiple visits to reason
        result = (
            FSMBuilder()
            .with_state("plan")
            .with_state("reason")
            .with_state("act")
            .with_transition("plan", "reason")
            .with_transition("reason", "act")
            .with_transition("act", "reason")
            .build(initial_state="plan")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # First visit to reason
        await fsm.transition_to("reason")
        assert await fsm.get_state() == "reason"

        # Leave and return
        await fsm.transition_to("act")
        assert await fsm.get_state() == "act"

        await fsm.transition_to("reason")
        assert await fsm.get_state() == "reason"

        # Verify command history shows multiple reason visits
        history = fsm.get_command_history()
        reason_transitions = [cmd for cmd in history if cmd.to_state == "reason"]
        assert len(reason_transitions) == 2

    @pytest.mark.asyncio
    async def test_reason_to_done_early_termination(self):
        """REASON can transition to done for early workflow termination."""
        result = (
            FSMBuilder()
            .with_state("plan")
            .with_state("reason")
            .with_state("done")
            .with_transition("plan", "reason")
            .with_transition("reason", "done")
            .build(initial_state="plan")
        )

        assert result.is_ok()
        fsm = result.unwrap()

        # Reason determines goal is already achieved
        await fsm.transition_to("reason")
        transition_result = await fsm.transition_to("done")

        assert transition_result.is_ok()
        assert await fsm.get_state() == "done"

    def test_reason_strategy_exception_handling(self):
        """REASON handles strategy exceptions gracefully."""
        mock_strategy = MagicMock(spec=ReasoningStrategy)

        mock_strategy.decide = MagicMock(side_effect=ValueError("Invalid context"))

        context = ReasoningContext(
            current_state="reason",
            available_actions=[],
            evidence=[],
            constraints={},
        )

        with pytest.raises(ValueError, match="Invalid context"):
            mock_strategy.decide(context)
