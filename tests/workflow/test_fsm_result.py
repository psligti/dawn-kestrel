"""Tests for FSM Result pattern implementation."""

from typing import cast

import pytest

from dawn_kestrel.core.result import Err, Ok, Result
from dawn_kestrel.workflow import assert_transition, WORKFLOW_FSM_TRANSITIONS


class TestFSMResultPatternValidTransitions:
    """Tests for valid state transitions returning Ok Result."""

    def test_transition_intake_to_plan_returns_ok(self):
        """Test valid transition from intake to plan returns Ok."""
        result = assert_transition("intake", "plan")
        assert result.is_ok()
        assert not result.is_err()
        assert result.unwrap() == "plan"

    def test_transition_plan_to_act_returns_ok(self):
        """Test valid transition from plan to act returns Ok."""
        result = assert_transition("plan", "act")
        assert result.is_ok()
        assert result.unwrap() == "act"

    def test_transition_act_to_synthesize_returns_ok(self):
        """Test valid transition from act to synthesize returns Ok."""
        result = assert_transition("act", "synthesize")
        assert result.is_ok()
        assert result.unwrap() == "synthesize"

    def test_transition_synthesize_to_evaluate_returns_ok(self):
        """Test valid transition from synthesize to evaluate returns Ok."""
        result = assert_transition("synthesize", "evaluate")
        assert result.is_ok()
        assert result.unwrap() == "evaluate"

    def test_transition_evaluate_to_done_returns_ok(self):
        """Test valid transition from evaluate to done returns Ok."""
        result = assert_transition("evaluate", "done")
        assert result.is_ok()
        assert result.unwrap() == "done"

    def test_transition_to_failed_state_returns_ok(self):
        """Test transition to failed state returns Ok."""
        result = assert_transition("intake", "failed")
        assert result.is_ok()
        assert result.unwrap() == "failed"

    def test_transition_done_to_intake_returns_ok(self):
        """Test transition from done to intake returns Ok (restart)."""
        result = assert_transition("done", "intake")
        assert result.is_ok()
        assert result.unwrap() == "intake"

    def test_failed_to_intake_returns_ok(self):
        """Test transition from failed to intake returns Ok (retry)."""
        result = assert_transition("failed", "intake")
        assert result.is_ok()
        assert result.unwrap() == "intake"


class TestFSMResultPatternInvalidFromState:
    """Tests for invalid from_state returning Err Result."""

    def test_invalid_from_state_returns_err(self):
        """Test that invalid from_state returns Err."""
        result = assert_transition("invalid_state", "plan")
        assert result.is_err()
        assert not result.is_ok()

    def test_invalid_from_state_has_correct_code(self):
        """Test that invalid from_state has correct error code."""
        result = assert_transition("invalid_state", "plan")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            assert err_result.code == "INVALID_FROM_STATE"

    def test_invalid_from_state_error_message(self):
        """Test that invalid from_state has descriptive error message."""
        result = assert_transition("invalid_state", "plan")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            assert "Invalid from_state" in err_result.error
            assert "invalid_state" in err_result.error
            assert "Valid states" in err_result.error

    def test_invalid_from_state_lists_valid_states(self):
        """Test that invalid from_state error lists all valid states."""
        result = assert_transition("invalid_state", "plan")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            for state in WORKFLOW_FSM_TRANSITIONS.keys():
                assert state in err_result.error


class TestFSMResultPatternInvalidTransition:
    """Tests for invalid state transitions returning Err Result."""

    def test_invalid_transition_returns_err(self):
        """Test that invalid transition returns Err."""
        result = assert_transition("intake", "done")
        assert result.is_err()
        assert not result.is_ok()

    def test_invalid_transition_has_correct_code(self):
        """Test that invalid transition has correct error code."""
        result = assert_transition("intake", "done")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            assert err_result.code == "INVALID_TRANSITION"

    def test_invalid_transition_error_message(self):
        """Test that invalid transition has descriptive error message."""
        result = assert_transition("intake", "done")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            assert "Invalid state transition" in err_result.error
            assert "intake -> done" in err_result.error
            assert "Valid transitions" in err_result.error

    def test_invalid_transition_lists_valid_transitions(self):
        """Test that invalid transition error lists valid transitions."""
        result = assert_transition("intake", "done")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            for valid_state in WORKFLOW_FSM_TRANSITIONS["intake"]:
                assert valid_state in err_result.error

    def test_transition_from_plan_to_invalid_returns_err(self):
        """Test invalid transition from plan returns Err."""
        result = assert_transition("plan", "intake")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            assert err_result.code == "INVALID_TRANSITION"

    def test_transition_from_act_to_invalid_returns_err(self):
        """Test invalid transition from act returns Err."""
        result = assert_transition("act", "intake")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            assert err_result.code == "INVALID_TRANSITION"


class TestFSMResultPatternMethods:
    """Tests for Result pattern methods on transition results."""

    def test_ok_result_unwrap_returns_state(self):
        """Test that Ok result unwrap returns the target state."""
        result = assert_transition("intake", "plan")
        assert result.unwrap() == "plan"

    def test_ok_result_unwrap_or_returns_state(self):
        """Test that Ok result unwrap_or returns the target state."""
        result = assert_transition("intake", "plan")
        assert result.unwrap_or("default") == "plan"

    def test_err_result_unwrap_raises_value_error(self):
        """Test that Err result unwrap raises ValueError."""
        result = assert_transition("intake", "done")
        with pytest.raises(ValueError) as exc_info:
            result.unwrap()
        assert "Invalid state transition" in str(exc_info.value)

    def test_err_result_unwrap_or_returns_default(self):
        """Test that Err result unwrap_or returns default."""
        result = assert_transition("intake", "done")
        assert result.unwrap_or("default") == "default"

    def test_err_result_retryable_is_false(self):
        """Test that Err result has retryable=False."""
        result = assert_transition("intake", "done")
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            assert err_result.retryable is False


class TestFSMResultPatternChaining:
    """Tests for Result pattern chaining with transition results."""

    def test_bind_on_valid_transition(self):
        """Test binding a function to valid transition result."""

        def uppercase_state(state: str) -> Result[str]:
            return Ok(state.upper())

        result = assert_transition("intake", "plan").bind(uppercase_state)
        assert result.is_ok()
        assert result.unwrap() == "PLAN"

    def test_bind_short_circuits_on_invalid_transition(self):
        """Test that bind short-circuits on invalid transition."""

        def uppercase_state(state: str) -> Result[str]:
            return Ok(state.upper())

        result = assert_transition("intake", "done").bind(uppercase_state)
        assert result.is_err()
        if result.is_err():
            err_result = cast(Err[str], result)
            assert err_result.code == "INVALID_TRANSITION"

    def test_chain_multiple_transitions(self):
        """Test chaining multiple transition validations."""
        # Simulate a workflow: intake -> plan -> act
        first = assert_transition("intake", "plan")
        second = assert_transition("plan", "act")

        assert first.is_ok()
        assert second.is_ok()
        assert first.unwrap() == "plan"
        assert second.unwrap() == "act"


class TestFSMResultPatternAllValidTransitions:
    """Comprehensive tests for all valid transitions in the FSM."""

    def test_all_valid_transitions_return_ok(self):
        """Test that all defined valid transitions return Ok."""
        for from_state, to_states in WORKFLOW_FSM_TRANSITIONS.items():
            for to_state in to_states:
                result = assert_transition(from_state, to_state)
                assert result.is_ok(), f"Transition {from_state} -> {to_state} should be Ok"

    def test_all_transitions_return_correct_state(self):
        """Test that all valid transitions return the correct target state."""
        for from_state, to_states in WORKFLOW_FSM_TRANSITIONS.items():
            for to_state in to_states:
                result = assert_transition(from_state, to_state)
                assert result.unwrap() == to_state, (
                    f"Transition {from_state} -> {to_state} should return {to_state}"
                )
