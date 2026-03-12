"""Tests for policy engine implementation.

This module tests the policy engine components:
- PolicyEngine protocol compliance
- DefaultPolicyEngine behavior
- ProposalRejected exception
"""

from __future__ import annotations

import pytest

from dawn_kestrel.policy import (
    DefaultPolicyEngine,
    PolicyEngine,
    PolicyInput,
    ProposalRejected,
    StepProposal,
)


class TestPolicyEngineProtocol:
    """Test PolicyEngine protocol."""

    def test_policy_engine_is_protocol(self):
        """PolicyEngine is a Protocol."""
        from typing import Protocol

        assert issubclass(PolicyEngine, Protocol)

    def test_default_engine_implements_protocol(self):
        """DefaultPolicyEngine implements PolicyEngine protocol."""
        engine = DefaultPolicyEngine()
        assert isinstance(engine, PolicyEngine)

    def test_custom_implementation(self):
        """Custom implementation can satisfy the protocol."""

        class CustomEngine:
            def propose(self, input: PolicyInput) -> StepProposal:
                return StepProposal(intent="Custom proposal")

        engine = CustomEngine()
        assert isinstance(engine, PolicyEngine)


class TestDefaultPolicyEngine:
    """Test DefaultPolicyEngine implementation."""

    def test_default_engine_returns_step_proposal(self):
        """DefaultPolicyEngine.propose returns a StepProposal."""
        engine = DefaultPolicyEngine()
        input_data = PolicyInput(goal="Test goal")
        result = engine.propose(input_data)

        assert isinstance(result, StepProposal)

    def test_default_engine_returns_minimal_proposal(self):
        """DefaultPolicyEngine returns minimal valid proposal."""
        engine = DefaultPolicyEngine()
        input_data = PolicyInput(goal="Test goal")
        result = engine.propose(input_data)

        assert result.intent == "No action proposed"
        assert result.target_todo_ids == []
        assert result.requested_context == []
        assert result.actions == []
        assert result.completion_claims == []

    def test_default_engine_with_complex_input(self):
        """DefaultPolicyEngine works with complex PolicyInput."""
        from dawn_kestrel.policy import (
            BudgetInfo,
            Constraint,
            EventSummary,
            TodoItem,
        )

        engine = DefaultPolicyEngine()
        input_data = PolicyInput(
            goal="Complex goal",
            active_todos=[TodoItem(id="1", description="First todo", status="in_progress")],
            last_events=[
                EventSummary(
                    event_type="file_read",
                    timestamp="2024-01-01T00:00:00Z",
                    summary="Read test.py",
                )
            ],
            budgets=BudgetInfo(max_iterations=50, iterations_consumed=10),
            constraints=[
                Constraint(
                    constraint_type="file_pattern",
                    value="src/**/*.py",
                    description="Only modify src files",
                )
            ],
        )

        result = engine.propose(input_data)
        assert isinstance(result, StepProposal)

    def test_default_engine_never_rejects(self):
        """DefaultPolicyEngine never raises ProposalRejected."""
        from dawn_kestrel.policy import BudgetInfo

        engine = DefaultPolicyEngine()

        # Try various inputs - none should raise
        inputs = [
            PolicyInput(goal=""),
            PolicyInput(goal="Test", active_todos=[]),
            PolicyInput(goal="Test", budgets=BudgetInfo(max_iterations=1)),
        ]

        for input_data in inputs:
            result = engine.propose(input_data)
            assert isinstance(result, StepProposal)


class TestProposalRejected:
    """Test ProposalRejected exception."""

    def test_exception_with_reason_only(self):
        """ProposalRejected with just a reason."""
        exc = ProposalRejected(reason="Test rejection")

        assert exc.reason == "Test rejection"
        assert exc.feedback == {}
        assert exc.retry_allowed is True
        assert str(exc) == "Test rejection"

    def test_exception_with_all_fields(self):
        """ProposalRejected with all fields."""
        feedback = {"field": "value", "suggestion": "Try again"}
        exc = ProposalRejected(
            reason="Test rejection",
            feedback=feedback,
            retry_allowed=False,
        )

        assert exc.reason == "Test rejection"
        assert exc.feedback == feedback
        assert exc.retry_allowed is False

    def test_exception_feedback_default_empty_dict(self):
        """ProposalRejected feedback defaults to empty dict."""
        exc = ProposalRejected(reason="Test")

        assert exc.feedback == {}
        assert isinstance(exc.feedback, dict)

    def test_exception_retry_allowed_default_true(self):
        """ProposalRejected retry_allowed defaults to True."""
        exc = ProposalRejected(reason="Test")

        assert exc.retry_allowed is True

    def test_exception_is_exception(self):
        """ProposalRejected is an Exception."""
        assert issubclass(ProposalRejected, Exception)

    def test_exception_can_be_raised_and_caught(self):
        """ProposalRejected can be raised and caught."""
        with pytest.raises(ProposalRejected) as exc_info:
            raise ProposalRejected(
                reason="Test exception",
                feedback={"key": "value"},
                retry_allowed=False,
            )

        assert exc_info.value.reason == "Test exception"
        assert exc_info.value.feedback == {"key": "value"}
        assert exc_info.value.retry_allowed is False

    def test_exception_with_none_feedback(self):
        """ProposalRejected with None feedback gets empty dict."""
        exc = ProposalRejected(reason="Test", feedback=None)

        assert exc.feedback == {}


class TestEngineIntegration:
    """Integration tests for policy engine components."""

    def test_engine_can_raise_proposal_rejected(self):
        """Custom engine can raise ProposalRejected."""

        class RejectingEngine:
            def propose(self, input: PolicyInput) -> StepProposal:
                raise ProposalRejected(
                    reason="Always reject",
                    feedback={"reason": "Testing rejection"},
                    retry_allowed=False,
                )

        engine = RejectingEngine()

        with pytest.raises(ProposalRejected) as exc_info:
            engine.propose(PolicyInput(goal="Test"))

        assert exc_info.value.reason == "Always reject"
        assert exc_info.value.retry_allowed is False

    def test_engine_can_modify_proposals(self):
        """Custom engine can modify proposals before returning."""

        class ModifyingEngine:
            def propose(self, input: PolicyInput) -> StepProposal:
                # Return a modified proposal
                return StepProposal(
                    intent=f"Processing: {input.goal}",
                    target_todo_ids=["auto-1"],
                )

        engine = ModifyingEngine()
        result = engine.propose(PolicyInput(goal="Original goal"))

        assert result.intent == "Processing: Original goal"
        assert result.target_todo_ids == ["auto-1"]
