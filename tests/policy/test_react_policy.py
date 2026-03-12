"""Tests for the ReActPolicy implementation.

This test suite verifies the ReAct-style policy engine behavior:
1. PolicyEngine protocol compliance
2. max_retries configuration
3. Minimal proposal generation
"""

import pytest

from dawn_kestrel.policy import (
    PolicyInput,
    ReActPolicy,
    RiskLevel,
    StepProposal,
)


class TestReActPolicyBasics:
    """Basic functionality tests for ReActPolicy."""

    def test_implements_propose_method(self) -> None:
        """ReActPolicy should have a propose method."""
        policy = ReActPolicy()
        assert hasattr(policy, "propose")
        assert callable(policy.propose)

    def test_returns_step_proposal(self) -> None:
        """propose() should return a StepProposal instance."""
        policy = ReActPolicy()
        input_data = PolicyInput(goal="Test goal")

        result = policy.propose(input_data)

        assert isinstance(result, StepProposal)

    def test_default_proposal_structure(self) -> None:
        """Should return minimal valid proposal with expected structure."""
        policy = ReActPolicy()
        input_data = PolicyInput(goal="Test goal")

        result = policy.propose(input_data)

        assert result.intent == "No action proposed"
        assert result.target_todo_ids == []
        assert result.requested_context == []
        assert result.actions == []
        assert result.completion_claims == []
        assert result.risk_level == RiskLevel.LOW


class TestMaxRetriesConfig:
    """Tests for max_retries configuration."""

    def test_default_max_retries(self) -> None:
        """Default max_retries should be 3."""
        policy = ReActPolicy()

        assert policy.max_retries == 3

    def test_custom_max_retries(self) -> None:
        """Should accept custom max_retries value."""
        policy = ReActPolicy(max_retries=5)

        assert policy.max_retries == 5

    def test_zero_max_retries(self) -> None:
        """Should allow zero max_retries."""
        policy = ReActPolicy(max_retries=0)

        assert policy.max_retries == 0

    def test_high_max_retries(self) -> None:
        """Should allow high max_retries values."""
        policy = ReActPolicy(max_retries=100)

        assert policy.max_retries == 100


class TestPolicyInputHandling:
    """Tests for handling various PolicyInput configurations."""

    def test_handles_empty_goal(self) -> None:
        """Should handle empty goal string."""
        policy = ReActPolicy()
        input_data = PolicyInput(goal="")

        result = policy.propose(input_data)

        assert isinstance(result, StepProposal)

    def test_handles_todos(self) -> None:
        """Should handle PolicyInput with todos."""
        policy = ReActPolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                {"id": "1", "description": "Task 1", "status": "pending"},
            ],
        )

        result = policy.propose(input_data)

        assert isinstance(result, StepProposal)

    def test_handles_constraints(self) -> None:
        """Should handle PolicyInput with constraints."""
        policy = ReActPolicy()
        input_data = PolicyInput(
            goal="Test",
            constraints=[
                {"constraint_type": "permission", "value": "read_only", "severity": "hard"},
            ],
        )

        result = policy.propose(input_data)

        assert isinstance(result, StepProposal)


class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_same_input_same_output(self) -> None:
        """Same input should always produce same output."""
        policy = ReActPolicy()
        input_data = PolicyInput(goal="Test goal")

        result1 = policy.propose(input_data)
        result2 = policy.propose(input_data)

        assert result1.intent == result2.intent
        assert result1.target_todo_ids == result2.target_todo_ids
        assert result1.actions == result2.actions
        assert result1.risk_level == result2.risk_level

    def test_multiple_calls_consistent(self) -> None:
        """Multiple calls should all return identical results."""
        policy = ReActPolicy()
        input_data = PolicyInput(goal="Test goal")

        results = [policy.propose(input_data) for _ in range(5)]

        # All results should have the same intent
        intents = [r.intent for r in results]
        assert len(set(intents)) == 1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_large_max_retries(self) -> None:
        """Should handle very large max_retries values."""
        policy = ReActPolicy(max_retries=1_000_000)

        assert policy.max_retries == 1_000_000

    def test_negative_max_retries(self) -> None:
        """Should accept negative max_retries (though not recommended)."""
        policy = ReActPolicy(max_retries=-1)

        assert policy.max_retries == -1
