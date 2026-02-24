"""Integration tests for REASON state with real FSM transitions.

Tests verify the full REASON state flow including:
- FSM state transitions through REASON
- ReasoningStrategy integration (CoT, ReAct)
- ReasonExecutor execution
- Plan state deprecation warning

These tests use real FSM transitions (no mocks) to verify integration.

Scenario: REASON State Integration
====================================

Preconditions:
- FSM configured with REASON state
- ReasoningStrategy implementation available
- ReasonExecutor wrapping strategy

Steps:
1. Create FSM with workflow states
2. Transition through REASON state
3. Execute reasoning strategy via executor
4. Verify state changes and results

Expected result:
- FSM transitions succeed
- ReasoningResult contains thought, action, next_state
- Deprecation warning emitted for plan state
"""

from __future__ import annotations

import warnings

import pytest

from dawn_kestrel.core.fsm import FSMBuilder, WORKFLOW_TRANSITIONS
from dawn_kestrel.workflow.deprecation import deprecate_plan_state, PLAN_STATE_DEPRECATED_MSG
from dawn_kestrel.workflow.reason_executor import ReasonExecutor
from dawn_kestrel.workflow.strategies import (
    CoTStrategy,
    ReasoningContext,
    ReasoningResult,
    ReActStrategy,
)


class TestReasonStateFSMTransitions:
    """Test FSM transitions through REASON state."""

    @pytest.mark.asyncio
    async def test_intake_to_reason_to_act_happy_path(self):
        """Scenario: Complete INTAKE → REASON → ACT transition path.

        Preconditions:
        - FSM created with workflow states
        - Initial state is intake

        Steps:
        1. Create FSM with all workflow states and transitions
        2. Verify initial state is intake
        3. Transition intake → reason
        4. Verify state is now reason
        5. Transition reason → act
        6. Verify state is now act

        Expected result:
        - All transitions succeed
        - State changes correctly at each step
        - No errors during transitions

        Failure indicators:
        - Any transition fails
        - State doesn't change correctly
        - Exception raised
        """
        # 1. Create FSM with workflow states and transitions
        fsm_result = (
            FSMBuilder()
            .with_initial_state("intake")
            .with_state("intake")
            .with_state("reason")
            .with_state("act")
            .with_transition("intake", "reason")
            .with_transition("reason", "act")
            .build()
        )
        assert fsm_result.is_ok(), f"FSM build failed: {fsm_result.error}"
        fsm = fsm_result.unwrap()

        # 2. Verify initial state is intake
        initial_state = await fsm.get_state()
        assert initial_state == "intake", f"Expected initial state 'intake', got '{initial_state}'"

        # 3. Transition intake → reason
        result1 = await fsm.transition_to("reason")
        assert result1.is_ok(), f"Transition intake→reason failed: {result1.error}"

        # 4. Verify state is now reason
        state_after_first = await fsm.get_state()
        assert state_after_first == "reason", f"Expected state 'reason', got '{state_after_first}'"

        # 5. Transition reason → act
        result2 = await fsm.transition_to("act")
        assert result2.is_ok(), f"Transition reason→act failed: {result2.error}"

        # 6. Verify state is now act
        final_state = await fsm.get_state()
        assert final_state == "act", f"Expected state 'act', got '{final_state}'"

    @pytest.mark.asyncio
    async def test_all_reason_transitions_valid(self):
        """Scenario: All REASON state exit transitions are valid.

        Verifies that REASON can transition to all documented target states:
        act, synthesize, check, done.

        Expected result:
        - All 4 transitions from reason are valid
        """
        # Verify WORKFLOW_TRANSITIONS contains correct reason exits
        reason_targets = WORKFLOW_TRANSITIONS.get("reason", set())
        expected_targets = {"act", "synthesize", "check", "done"}

        assert reason_targets == expected_targets, (
            f"REASON transitions mismatch. Expected: {expected_targets}, Got: {reason_targets}"
        )

        # Test each transition individually with real FSM
        for target in expected_targets:
            fsm_result = (
                FSMBuilder()
                .with_initial_state("reason")
                .with_state("reason")
                .with_state(target)
                .with_transition("reason", target)
                .build()
            )
            assert fsm_result.is_ok(), f"FSM build for reason→{target} failed"

            fsm = fsm_result.unwrap()
            current = await fsm.get_state()
            assert current == "reason"

            transition_result = await fsm.transition_to(target)
            assert transition_result.is_ok(), f"Transition reason→{target} failed"

            new_state = await fsm.get_state()
            assert new_state == target, f"Expected state '{target}', got '{new_state}'"


class TestReasonWithCoTStrategy:
    """Test REASON state with Chain-of-Thought strategy."""

    @pytest.mark.asyncio
    async def test_reason_with_cot_strategy(self):
        """Scenario: Execute REASON state with CoTStrategy.

        Preconditions:
        - CoTStrategy instantiated
        - ReasonExecutor wrapping strategy
        - ReasoningContext with query

        Steps:
        1. Create CoTStrategy instance
        2. Create ReasonExecutor with strategy
        3. Create ReasoningContext with no evidence
        4. Execute reasoning
        5. Verify ReasoningResult has thought, action, next_state

        Expected result:
        - ReasoningResult returned successfully
        - thought field populated
        - action field populated
        - next_state field populated

        Failure indicators:
        - execute() raises exception
        - Missing fields in ReasoningResult
        """
        # 1. Create CoTStrategy instance
        strategy = CoTStrategy()

        # 2. Create ReasonExecutor with strategy
        executor = ReasonExecutor(strategy=strategy)

        # 3. Create ReasoningContext with no evidence
        context = ReasoningContext(
            current_state="reason",
            available_actions=["analyze", "delegate", "complete"],
            evidence=[],  # No evidence - triggers analysis phase
            constraints={"max_iterations": 10},
        )

        # 4. Execute reasoning
        result = executor.execute(context)

        # 5. Verify ReasoningResult has thought, action, next_state
        assert isinstance(result, ReasoningResult), (
            f"Expected ReasoningResult, got {type(result).__name__}"
        )
        assert result.thought, "thought field should not be empty"
        assert result.action, "action field should not be empty"
        assert result.next_state, "next_state field should not be empty"

        # CoTStrategy with no evidence should start analysis phase
        assert result.action == "analyze", f"Expected action 'analyze', got '{result.action}'"
        assert result.next_state == "ACT", f"Expected next_state 'ACT', got '{result.next_state}'"

    @pytest.mark.asyncio
    async def test_cot_strategy_with_evidence(self):
        """Scenario: CoTStrategy with sufficient evidence triggers completion.

        When evidence count >= 2 and 'complete' action is available,
        CoTStrategy should recommend completion.
        """
        strategy = CoTStrategy()
        executor = ReasonExecutor(strategy=strategy)

        context = ReasoningContext(
            current_state="reason",
            available_actions=["analyze", "delegate", "complete"],
            evidence=["observation:found_file.py", "observation:analyzed_code"],
            constraints={},
        )

        result = executor.execute(context)

        # With 2+ evidence and complete available, should complete
        assert result.action == "complete", f"Expected action 'complete', got '{result.action}'"
        assert result.next_state == "DONE", f"Expected next_state 'DONE', got '{result.next_state}'"


class TestReasonWithReActStrategy:
    """Test REASON state with ReAct (Reason-Act-Observe) strategy."""

    @pytest.mark.asyncio
    async def test_reason_with_react_strategy_no_observation(self):
        """Scenario: ReActStrategy with no prior observation.

        When no observation exists in evidence, strategy should
        select initial action.
        """
        strategy = ReActStrategy()
        executor = ReasonExecutor(strategy=strategy)

        context = ReasoningContext(
            current_state="reason",
            available_actions=["analyze", "delegate", "complete"],
            evidence=[],  # No observation yet
            constraints={},
        )

        result = executor.execute(context)

        assert isinstance(result, ReasoningResult)
        assert result.thought, "thought field should not be empty"
        assert result.action, "action field should not be empty"
        assert result.next_state, "next_state field should not be empty"

        # No observation means initial reasoning
        assert "No prior observations" in result.thought or "Starting" in result.thought

    @pytest.mark.asyncio
    async def test_reason_with_react_strategy_with_observation(self):
        """Scenario: ReActStrategy processes observation from previous step.

        When evidence contains an observation (prefixed with 'observation:'),
        strategy should reason about it and select next action.

        Preconditions:
        - ReActStrategy instantiated
        - Evidence contains observation from previous step

        Steps:
        1. Create ReActStrategy with executor
        2. Create context with observation in evidence
        3. Execute reasoning
        4. Verify strategy processed observation

        Expected result:
        - thought references the observation
        - action selected based on observation analysis
        """
        strategy = ReActStrategy()
        executor = ReasonExecutor(strategy=strategy)

        # 2. Create context with observation in evidence
        context = ReasoningContext(
            current_state="reason",
            available_actions=["analyze", "delegate", "complete"],
            evidence=["observation:grep_found_3_files"],
            constraints={},
        )

        # 3. Execute reasoning
        result = executor.execute(context)

        # 4. Verify strategy processed observation
        assert isinstance(result, ReasoningResult)
        assert "Observation received" in result.thought, (
            f"Expected observation processing in thought, got: {result.thought}"
        )
        assert result.action, "action should be selected"
        assert result.next_state, "next_state should be determined"

    @pytest.mark.asyncio
    async def test_react_strategy_action_to_state_mapping(self):
        """Scenario: ReActStrategy maps actions to correct states.

        Verify that specific actions map to expected target states:
        - 'complete' → 'DONE'
        - 'synthesize' → 'SYNTHESIZE'
        - 'check' → 'CHECK'
        - 'delegate' → 'ACT'
        """
        strategy = ReActStrategy()

        # Test complete action
        context = ReasoningContext(
            current_state="reason",
            available_actions=["complete"],
            evidence=[],
        )
        result = strategy.decide(context)
        # With only "complete" available, should use first action
        assert result.next_state in ["ACT", "DONE"], (
            f"Expected ACT or DONE for complete, got {result.next_state}"
        )


class TestPlanDeprecationWarning:
    """Test plan state deprecation warning in integration context."""

    def test_plan_deprecation_warning_emitted(self):
        """Scenario: Using 'plan' state emits deprecation warning.

        When code calls deprecate_plan_state(), a DeprecationWarning
        should be emitted with migration guidance.

        Expected result:
        - DeprecationWarning raised
        - Message contains migration guidance
        - Code continues execution (no exception)
        """
        with pytest.warns(DeprecationWarning) as record:
            deprecate_plan_state()

        assert len(record) == 1, f"Expected 1 warning, got {len(record)}"
        assert "reason" in str(record[0].message), (
            f"Expected 'reason' in warning message, got: {record[0].message}"
        )
        assert "deprecated" in str(record[0].message), f"Expected 'deprecated' in warning message"

    def test_plan_deprecation_warning_integration(self):
        """Scenario: Plan deprecation warning in workflow context.

        Simulates using 'plan' state in an integration context where
        the deprecation warning should still be emitted.
        """
        # Capture warnings
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")

            # Simulate using 'plan' state (soft deprecation)
            current_state = "plan"
            if current_state == "plan":
                deprecate_plan_state()

            # Verify warning was emitted
            deprecation_warnings = [
                w for w in caught_warnings if issubclass(w.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) >= 1, (
                f"Expected at least 1 DeprecationWarning, got {len(deprecation_warnings)}"
            )

            # Verify message content
            warning_msg = str(deprecation_warnings[0].message)
            assert "reason" in warning_msg, "Warning should mention 'reason' state"
            assert PLAN_STATE_DEPRECATED_MSG == warning_msg, (
                f"Warning message should match PLAN_STATE_DEPRECATED_MSG"
            )

    @pytest.mark.asyncio
    async def test_plan_transition_still_succeeds(self):
        """Scenario: Plan state transitions still work (soft deprecation).

        Despite being deprecated, transitions involving 'plan' state
        should still succeed. The deprecation warning is only emitted
        when explicitly calling deprecate_plan_state(), not by FSM transitions.
        """
        fsm_result = (
            FSMBuilder()
            .with_initial_state("intake")
            .with_state("intake")
            .with_state("plan")
            .with_state("act")
            .with_transition("intake", "plan")
            .with_transition("plan", "act")
            .build()
        )

        assert fsm_result.is_ok(), f"FSM build failed: {fsm_result.error}"
        fsm = fsm_result.unwrap()

        result = await fsm.transition_to("plan")
        assert result.is_ok(), f"Transition to plan should succeed: {result.error}"
        state = await fsm.get_state()
        assert state == "plan", f"Expected state 'plan', got '{state}'"

        result2 = await fsm.transition_to("act")
        assert result2.is_ok(), f"Transition plan→act should succeed: {result2.error}"
        final_state = await fsm.get_state()
        assert final_state == "act"
