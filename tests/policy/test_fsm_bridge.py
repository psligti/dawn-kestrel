"""Tests for FSM bridge policy implementation.

This module tests the FSM-based policy engine:
- FSMPolicy implements PolicyEngine protocol
- propose() returns valid StepProposal
"""

from __future__ import annotations

import pytest

from dawn_kestrel.policy import (
    BudgetInfo,
    Constraint,
    EventSummary,
    PolicyEngine,
    PolicyInput,
    StepProposal,
    TodoItem,
)
from dawn_kestrel.policy.fsm_bridge import FSMPolicy


class TestFSMPolicyProtocol:
    """Test FSMPolicy protocol compliance."""

    def test_fsm_policy_implements_protocol(self):
        """FSMPolicy implements PolicyEngine protocol."""
        engine = FSMPolicy()
        assert isinstance(engine, PolicyEngine)

    def test_fsm_policy_has_propose_method(self):
        """FSMPolicy has propose method."""
        engine = FSMPolicy()
        assert hasattr(engine, "propose")
        assert callable(engine.propose)


class TestFSMPolicyPropose:
    """Test FSMPolicy.propose method."""

    def test_propose_returns_step_proposal(self):
        """FSMPolicy.propose returns a StepProposal."""
        engine = FSMPolicy()
        input_data = PolicyInput(goal="Test goal")
        result = engine.propose(input_data)

        assert isinstance(result, StepProposal)

    def test_propose_returns_valid_proposal_structure(self):
        """FSMPolicy.propose returns a valid proposal with all required fields."""
        engine = FSMPolicy()
        input_data = PolicyInput(goal="Test goal")
        result = engine.propose(input_data)

        # Check all required fields exist
        assert hasattr(result, "intent")
        assert hasattr(result, "target_todo_ids")
        assert hasattr(result, "requested_context")
        assert hasattr(result, "actions")
        assert hasattr(result, "completion_claims")
        assert hasattr(result, "risk_level")
        assert hasattr(result, "notes")

        # Check types
        assert isinstance(result.intent, str)
        assert isinstance(result.target_todo_ids, list)
        assert isinstance(result.requested_context, list)
        assert isinstance(result.actions, list)
        assert isinstance(result.completion_claims, list)

    def test_propose_with_empty_input(self):
        """FSMPolicy.propose works with minimal PolicyInput."""
        engine = FSMPolicy()
        input_data = PolicyInput(goal="")
        result = engine.propose(input_data)

        assert isinstance(result, StepProposal)

    def test_propose_with_complex_input(self):
        """FSMPolicy.propose works with complex PolicyInput."""
        engine = FSMPolicy()
        input_data = PolicyInput(
            goal="Complex goal",
            active_todos=[
                TodoItem(id="1", description="First todo", status="in_progress"),
                TodoItem(id="2", description="Second todo", status="pending"),
            ],
            last_events=[
                EventSummary(
                    event_type="file_read",
                    timestamp="2024-01-01T00:00:00Z",
                    summary="Read config.py",
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

    def test_propose_idempotent(self):
        """FSMPolicy.propose returns valid results on repeated calls."""
        engine = FSMPolicy()
        input_data = PolicyInput(goal="Test goal")

        result1 = engine.propose(input_data)
        result2 = engine.propose(input_data)

        assert isinstance(result1, StepProposal)
        assert isinstance(result2, StepProposal)


class TestFSMPolicyIntegration:
    """Integration tests for FSMPolicy."""

    def test_fsm_policy_never_rejects(self):
        """FSMPolicy never raises ProposalRejected (until FSM logic is wired)."""
        engine = FSMPolicy()

        # Try various inputs - none should raise
        inputs = [
            PolicyInput(goal=""),
            PolicyInput(goal="Test", active_todos=[]),
            PolicyInput(
                goal="Test",
                budgets=BudgetInfo(max_iterations=1),
            ),
        ]

        for input_data in inputs:
            result = engine.propose(input_data)
            assert isinstance(result, StepProposal)

    def test_fsm_policy_can_be_used_as_policy_engine(self):
        """FSMPolicy can be used anywhere a PolicyEngine is expected."""

        def use_policy_engine(engine: PolicyEngine, goal: str) -> StepProposal:
            """Function that accepts any PolicyEngine."""
            input_data = PolicyInput(goal=goal)
            return engine.propose(input_data)

        fsm_engine = FSMPolicy()
        result = use_policy_engine(fsm_engine, "Test goal")

        assert isinstance(result, StepProposal)
