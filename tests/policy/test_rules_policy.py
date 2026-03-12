"""Tests for the RulesPolicy implementation.

This test suite verifies the rule-based policy engine behavior:
1. Budget exhaustion detection
2. High-risk situation detection
3. Default proposal generation
4. Determinism (same input = same output)
"""

import pytest

from dawn_kestrel.policy import (
    BudgetInfo,
    Constraint,
    PolicyInput,
    RequestApprovalAction,
    RiskLevel,
    RulesPolicy,
    StepProposal,
    TodoItem,
)


class TestRulesPolicyBasics:
    """Basic functionality tests for RulesPolicy."""

    def test_implements_propose_method(self) -> None:
        """RulesPolicy should have a propose method."""
        policy = RulesPolicy()
        assert hasattr(policy, "propose")
        assert callable(policy.propose)

    def test_returns_step_proposal(self) -> None:
        """propose() should return a StepProposal instance."""
        policy = RulesPolicy()
        input_data = PolicyInput(goal="Test goal")

        result = policy.propose(input_data)

        assert isinstance(result, StepProposal)

    def test_default_proposal_no_todos(self) -> None:
        """With no TODOs, should return minimal no-op proposal."""
        policy = RulesPolicy()
        input_data = PolicyInput(goal="Test goal", active_todos=[])

        result = policy.propose(input_data)

        assert "No pending TODOs" in result.intent
        assert result.target_todo_ids == []
        assert result.actions == []
        assert result.risk_level == RiskLevel.LOW


class TestBudgetExhaustion:
    """Tests for budget exhaustion detection."""

    def test_iterations_exhausted(self) -> None:
        """Should detect when iterations budget is exhausted."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            budgets=BudgetInfo(
                max_iterations=100,
                iterations_consumed=100,  # Exhausted
            ),
        )

        result = policy.propose(input_data)

        assert "Budget exhausted" in result.intent
        assert result.actions == []
        assert result.target_todo_ids == []

    def test_iterations_over_consumed(self) -> None:
        """Should detect when iterations are over-consumed."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            budgets=BudgetInfo(
                max_iterations=100,
                iterations_consumed=150,  # Over limit
            ),
        )

        result = policy.propose(input_data)

        assert "Budget exhausted" in result.intent

    def test_tool_calls_exhausted(self) -> None:
        """Should detect when tool calls budget is exhausted."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            budgets=BudgetInfo(
                max_tool_calls=1000,
                tool_calls_consumed=1000,
            ),
        )

        result = policy.propose(input_data)

        assert "Budget exhausted" in result.intent

    def test_wall_time_exhausted(self) -> None:
        """Should detect when wall time budget is exhausted."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            budgets=BudgetInfo(
                max_wall_time_seconds=3600.0,
                wall_time_consumed=3600.0,
            ),
        )

        result = policy.propose(input_data)

        assert "Budget exhausted" in result.intent

    def test_subagent_calls_exhausted(self) -> None:
        """Should detect when subagent calls budget is exhausted."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            budgets=BudgetInfo(
                max_subagent_calls=50,
                subagent_calls_consumed=50,
            ),
        )

        result = policy.propose(input_data)

        assert "Budget exhausted" in result.intent

    def test_budget_priority_over_other_rules(self) -> None:
        """Budget exhaustion should take priority over other rules."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="1", description="Task 1", status="pending", priority="high")
            ],
            constraints=[
                Constraint(constraint_type="permission", value="read_only", severity="hard")
            ],
            budgets=BudgetInfo(
                max_iterations=100,
                iterations_consumed=100,  # Exhausted
            ),
        )

        result = policy.propose(input_data)

        # Should be budget exhausted, not approval request
        assert "Budget exhausted" in result.intent
        assert not any(isinstance(a, RequestApprovalAction) for a in result.actions)


class TestHighRiskSituation:
    """Tests for high-risk situation detection."""

    def test_hard_constraint_triggers_approval(self) -> None:
        """Hard constraints should trigger approval request."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test goal",
            constraints=[
                Constraint(
                    constraint_type="permission",
                    value="read_only",
                    severity="hard",
                )
            ],
        )

        result = policy.propose(input_data)

        assert "Request approval" in result.intent.lower() or "approval" in result.intent.lower()
        assert any(isinstance(a, RequestApprovalAction) for a in result.actions)
        assert result.risk_level == RiskLevel.HIGH

    def test_soft_constraint_does_not_trigger_approval(self) -> None:
        """Soft constraints should not trigger approval request."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test goal",
            constraints=[
                Constraint(
                    constraint_type="permission",
                    value="read_only",
                    severity="soft",
                )
            ],
        )

        result = policy.propose(input_data)

        # Should not be an approval request
        assert not any(isinstance(a, RequestApprovalAction) for a in result.actions)

    def test_critical_iterations_budget_triggers_approval(self) -> None:
        """Budget at >= 90% consumed should trigger approval request."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test goal",
            budgets=BudgetInfo(
                max_iterations=100,
                iterations_consumed=90,  # Exactly 90%
            ),
        )

        result = policy.propose(input_data)

        assert any(isinstance(a, RequestApprovalAction) for a in result.actions)

    def test_critical_tool_calls_budget_triggers_approval(self) -> None:
        """Critical tool calls budget should trigger approval."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test goal",
            budgets=BudgetInfo(
                max_tool_calls=1000,
                tool_calls_consumed=900,  # 90%
            ),
        )

        result = policy.propose(input_data)

        assert any(isinstance(a, RequestApprovalAction) for a in result.actions)

    def test_approval_message_includes_goal(self) -> None:
        """Approval request message should include the goal."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Implement feature X",
            constraints=[
                Constraint(
                    constraint_type="permission",
                    value="strict",
                    severity="hard",
                )
            ],
        )

        result = policy.propose(input_data)

        approval_actions = [a for a in result.actions if isinstance(a, RequestApprovalAction)]
        assert len(approval_actions) == 1
        assert "Implement feature X" in approval_actions[0].message

    def test_approval_options(self) -> None:
        """Approval request should have expected options."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            constraints=[
                Constraint(
                    constraint_type="permission",
                    value="strict",
                    severity="hard",
                )
            ],
        )

        result = policy.propose(input_data)

        approval_actions = [a for a in result.actions if isinstance(a, RequestApprovalAction)]
        assert len(approval_actions) == 1
        assert "approve" in approval_actions[0].options
        assert "reject" in approval_actions[0].options


class TestDefaultProposal:
    """Tests for default proposal generation."""

    def test_targets_first_pending_todo(self) -> None:
        """Should target the first pending TODO."""
        policy = RulesPolicy()
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
        policy = RulesPolicy()
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
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test goal",
            active_todos=[
                TodoItem(id="todo-1", description="In progress", status="in_progress"),
                TodoItem(id="todo-2", description="Pending", status="pending"),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["todo-2"]

    def test_priority_ordering_high_first(self) -> None:
        """High priority TODOs should be targeted first."""
        policy = RulesPolicy()
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
        policy = RulesPolicy()
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

    def test_proposal_is_minimal(self) -> None:
        """Default proposal should be minimal (no actions)."""
        policy = RulesPolicy()
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


class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_same_input_same_output(self) -> None:
        """Same input should always produce same output."""
        policy = RulesPolicy()
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

    def test_determinism_with_budget_exhausted(self) -> None:
        """Budget exhaustion should be deterministic."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            budgets=BudgetInfo(
                max_iterations=100,
                iterations_consumed=100,
            ),
        )

        result1 = policy.propose(input_data)
        result2 = policy.propose(input_data)

        assert result1.intent == result2.intent

    def test_determinism_with_hard_constraints(self) -> None:
        """Hard constraint handling should be deterministic."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            constraints=[
                Constraint(
                    constraint_type="permission",
                    value="read_only",
                    severity="hard",
                )
            ],
        )

        result1 = policy.propose(input_data)
        result2 = policy.propose(input_data)

        assert result1.intent == result2.intent
        assert len(result1.actions) == len(result2.actions)


class TestRulePriority:
    """Tests for rule priority ordering."""

    def test_budget_over_hard_constraint(self) -> None:
        """Budget exhaustion has higher priority than hard constraints."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            constraints=[
                Constraint(
                    constraint_type="permission",
                    value="read_only",
                    severity="hard",
                )
            ],
            budgets=BudgetInfo(
                max_iterations=100,
                iterations_consumed=100,  # Exhausted
            ),
        )

        result = policy.propose(input_data)

        # Budget exhaustion wins
        assert "Budget exhausted" in result.intent

    def test_hard_constraint_over_default(self) -> None:
        """Hard constraints have higher priority than default rule."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="todo-1", description="Task", status="pending"),
            ],
            constraints=[
                Constraint(
                    constraint_type="permission",
                    value="read_only",
                    severity="hard",
                )
            ],
        )

        result = policy.propose(input_data)

        # Hard constraint wins, not default
        assert any(isinstance(a, RequestApprovalAction) for a in result.actions)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_budget_limits(self) -> None:
        """Should handle zero budget limits without division errors."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            budgets=BudgetInfo(
                max_iterations=0,
                max_tool_calls=0,
                max_wall_time_seconds=0.0,
                max_subagent_calls=0,
                iterations_consumed=0,
                tool_calls_consumed=0,
                wall_time_consumed=0.0,
                subagent_calls_consumed=0,
            ),
        )

        result = policy.propose(input_data)

        assert isinstance(result, StepProposal)

    def test_just_under_critical_threshold(self) -> None:
        """Budget just under 90% should not trigger high-risk."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            budgets=BudgetInfo(
                max_iterations=100,
                iterations_consumed=89,  # Just under 90%
            ),
        )

        result = policy.propose(input_data)

        # Should not be approval request
        assert not any(isinstance(a, RequestApprovalAction) for a in result.actions)

    def test_empty_constraints_list(self) -> None:
        """Empty constraints should not trigger high-risk."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            constraints=[],
        )

        result = policy.propose(input_data)

        # Should be default proposal, not approval request
        assert not any(isinstance(a, RequestApprovalAction) for a in result.actions)

    def test_multiple_hard_constraints(self) -> None:
        """Multiple hard constraints should still trigger single approval."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            constraints=[
                Constraint(constraint_type="permission", value="r1", severity="hard"),
                Constraint(constraint_type="tool_restriction", value="r2", severity="hard"),
            ],
        )

        result = policy.propose(input_data)

        approval_actions = [a for a in result.actions if isinstance(a, RequestApprovalAction)]
        assert len(approval_actions) == 1  # Single approval request

    def test_all_todos_completed(self) -> None:
        """All completed TODOs should result in no-op proposal."""
        policy = RulesPolicy()
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

    def test_mixed_todo_statuses(self) -> None:
        """Should correctly identify pending among mixed statuses."""
        policy = RulesPolicy()
        input_data = PolicyInput(
            goal="Test",
            active_todos=[
                TodoItem(id="1", description="Completed", status="completed"),
                TodoItem(id="2", description="In progress", status="in_progress"),
                TodoItem(id="3", description="Blocked", status="blocked"),
                TodoItem(id="4", description="Pending", status="pending"),
            ],
        )

        result = policy.propose(input_data)

        assert result.target_todo_ids == ["4"]
