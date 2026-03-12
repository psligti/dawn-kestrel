"""Tests for the PlanExecutePolicy implementation.

This test suite verifies the plan-execute policy engine behavior:
1. Returns minimal proposal when no TODOs exist
2. Targets first pending TODO when TODOs exist
3. Deterministic TODO selection (priority-based)
4. Same input always produces same output
"""

import pytest

from dawn_kestrel.policy import (
    PolicyInput,
    PlanExecutePolicy,
    RiskLevel,
    StepProposal,
    TodoItem,
)


class TestPlanExecutePolicyBasics:
    """Basic functionality tests for PlanExecutePolicy."""

    def test_implements_propose_method(self) -> None:
        """PlanExecutePolicy should have a propose method."""
        policy = PlanExecutePolicy()
        assert hasattr(policy, "propose")
        assert callable(policy.propose)

    def test_returns_step_proposal(self) -> None:
        """propose() should return a StepProposal instance."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(goal="Test goal")

        result = policy.propose(input_data)

        assert isinstance(result, StepProposal)

    def test_proposal_no_todos(self) -> None:
        """With no TODOs, should return minimal no-op proposal."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(goal="Test goal", active_todos=[])

        result = policy.propose(input_data)

        assert "No pending TODOs" in result.intent
        assert result.target_todo_ids == []
        assert result.actions == []
        assert result.risk_level == RiskLevel.LOW


class TestNoTodosBehavior:
    """Tests for behavior when no pending TODOs exist."""

    def test_empty_todos_list(self) -> None:
        """Empty todos list should return no-todos proposal."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(goal="Test", active_todos=[])

        result = policy.propose(input_data)

        assert "No pending TODOs" in result.intent
        assert result.target_todo_ids == []

    def test_all_todos_completed(self) -> None:
        """All completed TODOs should result in no-todos proposal."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="1", description="Task 1", status="completed"),
                TodoItem(id="2", description="Task 2", status="completed"),
            ],
        )

        result = policy.propose(input_data)

        assert "No pending TODOs" in result.intent
        assert result.target_todo_ids == []

    def test_all_todos_in_progress(self) -> None:
        """All in-progress TODOs should result in no-todos proposal."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="1", description="Task 1", status="in_progress"),
                TodoItem(id="2", description="Task 2", status="in_progress"),
            ],
        )

        result = policy.propose(input_data)

        assert "No pending TODOs" in result.intent
        assert result.target_todo_ids == []

    def test_mixed_non_pending_statuses(self) -> None:
        """Mixed non-pending statuses should result in no-todos proposal."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="1", description="Completed", status="completed"),
                TodoItem(id="2", description="In progress", status="in_progress"),
                TodoItem(id="3", description="Blocked", status="blocked"),
                TodoItem(id="4", description="Skipped", status="skipped"),
            ],
        )

        result = policy.propose(input_data)

        assert "No pending TODOs" in result.intent
        assert result.target_todo_ids == []


class TestTodoTargeting:
    """Tests for TODO targeting behavior."""

    def test_targets_first_pending_todo(self) -> None:
        """Should target the first pending TODO."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(id="todo-1", description="First task", status="pending"),
                TodoItem(id="todo-2", description="Second task", status="pending"),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["todo-1"]
        assert "First task" in result.intent

    def test_ignores_completed_todos(self) -> None:
        """Should skip completed TODOs and target first pending."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(id="todo-1", description="Completed", status="completed"),
                TodoItem(id="todo-2", description="Pending", status="pending"),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["todo-2"]

    def test_ignores_in_progress_todos(self) -> None:
        """Should skip in-progress TODOs and target first pending."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(id="todo-1", description="In progress", status="in_progress"),
                TodoItem(id="todo-2", description="Pending", status="pending"),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["todo-2"]

    def test_single_pending_todo(self) -> None:
        """Should correctly target a single pending TODO."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(id="only-todo", description="The only task", status="pending"),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["only-todo"]
        assert "The only task" in result.intent


class TestPriorityOrdering:
    """Tests for priority-based TODO selection."""

    def test_priority_ordering_high_first(self) -> None:
        """High priority TODOs should be targeted first."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(id="low", description="Low priority", status="pending", priority="low"),
                TodoItem(id="high", description="High priority", status="pending", priority="high"),
                TodoItem(
                    id="medium", description="Medium priority", status="pending", priority="medium"
                ),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["high"]

    def test_priority_ordering_medium_over_low(self) -> None:
        """Medium priority should be selected over low."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(id="low", description="Low priority", status="pending", priority="low"),
                TodoItem(
                    id="medium", description="Medium priority", status="pending", priority="medium"
                ),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["medium"]

    def test_priority_ordering_all_priorities(self) -> None:
        """High > Medium > Low ordering should be enforced."""
        policy = PlanExecutePolicy()

        # When all three priorities are present, high should be selected
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="low", description="Low task", status="pending", priority="low"),
                TodoItem(
                    id="medium", description="Medium task", status="pending", priority="medium"
                ),
                TodoItem(id="high", description="High task", status="pending", priority="high"),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["high"]

    def test_priority_stable_sort_within_same_priority(self) -> None:
        """Within same priority, first in list should be selected (stable sort)."""
        policy = PlanExecutePolicy()

        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="first", description="First", status="pending", priority="medium"),
                TodoItem(id="second", description="Second", status="pending", priority="medium"),
                TodoItem(id="third", description="Third", status="pending", priority="medium"),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["first"]


class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_same_input_same_output(self) -> None:
        """Same input should always produce same output."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(id="todo-1", description="Task 1", status="pending"),
                TodoItem(id="todo-2", description="Task 2", status="pending"),
            ],
        )

        result1 = policy.propose(input_data)
        result2 = policy.propose(input_data)

        assert result1.intent == result2.intent
        assert result1.target_todo_ids == result2.target_todo_ids
        assert result1.actions == result2.actions
        assert result1.risk_level == result2.risk_level

    def test_determinism_with_no_todos(self) -> None:
        """No-todos case should be deterministic."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(goal="Test", active_todos=[])

        result1 = policy.propose(input_data)
        result2 = policy.propose(input_data)

        assert result1.intent == result2.intent
        assert result1.target_todo_ids == result2.target_todo_ids

    def test_determinism_with_priority_todos(self) -> None:
        """Priority ordering should be deterministic."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="low", description="Low", status="pending", priority="low"),
                TodoItem(id="high", description="High", status="pending", priority="high"),
            ],
        )

        result1 = policy.propose(input_data)
        result2 = policy.propose(input_data)

        assert result1.target_todo_ids == result2.target_todo_ids == ["high"]


class TestProposalStructure:
    """Tests for proposal structure and content."""

    def test_proposal_is_minimal(self) -> None:
        """Proposals should be minimal (no actions)."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(id="todo-1", description="Task", status="pending"),
            ],
        )

        result = policy.propose(input_data)

        # Minimal means no actions, just targeting
        assert result.actions == []
        assert result.requested_context == []
        assert result.completion_claims == []

    def test_proposal_includes_todo_description_in_intent(self) -> None:
        """Intent should include the TODO description."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(id="todo-1", description="Implement feature X", status="pending"),
            ],
        )

        result = policy.propose(input_data)

        assert "Implement feature X" in result.intent

    def test_proposal_notes_include_priority(self) -> None:
        """Notes should include the TODO priority."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(
                    id="todo-1", description="High priority task", status="pending", priority="high"
                ),
            ],
        )

        result = policy.propose(input_data)

        assert "high" in result.notes.lower()

    def test_no_todos_proposal_mentions_plan_generation(self) -> None:
        """No-todos proposal should mention plan generation."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(goal="Test", active_todos=[])

        result = policy.propose(input_data)

        assert (
            "plan generation" in result.intent.lower() or "plan generation" in result.notes.lower()
        )


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_todo_with_default_priority(self) -> None:
        """Should handle TODO with default priority (medium)."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="todo-1", description="Task", status="pending"),
                # priority defaults to "medium"
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["todo-1"]

    def test_blocked_and_skipped_todos_ignored(self) -> None:
        """Blocked and skipped TODOs should be ignored."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="1", description="Blocked", status="blocked"),
                TodoItem(id="2", description="Skipped", status="skipped"),
                TodoItem(id="3", description="Pending", status="pending"),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["3"]

    def test_many_todos_selects_first_pending(self) -> None:
        """With many TODOs, should deterministically select first pending by priority."""
        policy = PlanExecutePolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id=f"todo-{i}", description=f"Task {i}", status="pending", priority="low")
                for i in range(100)
            ]
            + [
                TodoItem(
                    id="high-priority", description="Important", status="pending", priority="high"
                )
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["high-priority"]

    def test_goal_is_not_used_in_decision(self) -> None:
        """Goal should not affect proposal targeting (only TODOs matter)."""
        policy = PlanExecutePolicy()

        input1 = PolicyInput(
            goal="First goal",
            active_todos=[TodoItem(id="todo-1", description="Task", status="pending")],
        )
        input2 = PolicyInput(
            goal="Different goal",
            active_todos=[TodoItem(id="todo-1", description="Task", status="pending")],
        )

        result1 = policy.propose(input1)
        result2 = policy.propose(input2)

        # Targeting should be the same (based on TODOs, not goal)
        assert result1.target_todo_ids == result2.target_todo_ids
