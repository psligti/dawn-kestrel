"""Rule-based policy engine implementation.

This module provides a deterministic, rule-based policy engine that
makes decisions based on priority-ordered rules. The RulesPolicy
implements the PolicyEngine protocol and provides predictable behavior
for agent decision-making.

Rule priority (highest to lowest):
1. Budget exhaustion - If any budget limit is reached, return minimal proposal
2. High-risk situation - If high-risk conditions detected, request approval
3. Default - Return minimal proposal targeting first pending TODO

Determinism guarantee:
Same input always produces same output (no randomness, no time-dependent logic).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dawn_kestrel.policy.contracts import (
    BudgetInfo,
    ContextRequest,
    PolicyInput,
    RequestApprovalAction,
    RiskLevel,
    StepProposal,
    TodoItem,
)

if TYPE_CHECKING:
    from dawn_kestrel.policy.engine import PolicyEngine


class RulesPolicy:
    """Rule-based policy engine with priority-ordered decision rules.

    This implementation evaluates the policy input against a series of
    rules in priority order. The first matching rule determines the
    output proposal. This ensures deterministic behavior: the same
    input will always produce the same output.

    Rules (in priority order):
        1. Budget Exhaustion: If any budget limit is reached or exceeded,
           return a minimal no-op proposal.
        2. High-Risk Situation: If high-risk conditions are detected
           (hard constraints present, budget critically low), return
           a proposal requesting human approval.
        3. Default: Return a minimal proposal targeting the first
           pending TODO item.

    Example:
        >>> policy = RulesPolicy()
        >>> input_data = PolicyInput(goal="Fix bug")
        >>> proposal = policy.propose(input_data)
        >>> proposal.intent
        'No pending TODOs to address'
    """

    # Budget thresholds for high-risk detection (percentage of max)
    CRITICAL_BUDGET_THRESHOLD = 0.9  # 90% consumed = critical

    def propose(self, input: PolicyInput) -> StepProposal:
        """Evaluate input and return an approved step proposal.

        Applies rules in priority order and returns the proposal from
        the first matching rule.

        Args:
            input: Current runtime state including goals, todos, constraints

        Returns:
            StepProposal: An approved proposal for the next action

        The decision process is:
            1. Check if any budget is exhausted → minimal proposal
            2. Check if high-risk situation → request approval
            3. Default → target first pending TODO
        """
        # Rule 1: Budget exhaustion (highest priority)
        if self._is_budget_exhausted(input.budgets):
            return self._create_budget_exhausted_proposal()

        # Rule 2: High-risk situation
        if self._is_high_risk_situation(input):
            return self._create_approval_request_proposal(input)

        # Rule 3: Default - target first pending TODO
        return self._create_default_proposal(input)

    def _is_budget_exhausted(self, budgets: BudgetInfo) -> bool:
        """Check if any budget limit has been reached or exceeded.

        Args:
            budgets: Budget constraints and consumption status

        Returns:
            True if any budget is exhausted, False otherwise
        """
        return (
            budgets.iterations_consumed >= budgets.max_iterations
            or budgets.tool_calls_consumed >= budgets.max_tool_calls
            or budgets.wall_time_consumed >= budgets.max_wall_time_seconds
            or budgets.subagent_calls_consumed >= budgets.max_subagent_calls
        )

    def _is_high_risk_situation(self, input: PolicyInput) -> bool:
        """Check if the current situation is high-risk.

        High-risk conditions include:
        - Hard constraints present in the input
        - Budget critically low (>= 90% consumed on any dimension)

        Args:
            input: Current runtime state

        Returns:
            True if high-risk conditions detected, False otherwise
        """
        # Check for hard constraints
        has_hard_constraints = any(
            constraint.severity == "hard" for constraint in input.constraints
        )

        # Check for critically low budget
        has_critical_budget = self._is_budget_critical(input.budgets)

        return has_hard_constraints or has_critical_budget

    def _is_budget_critical(self, budgets: BudgetInfo) -> bool:
        """Check if any budget is at critical level (>= 90% consumed).

        Args:
            budgets: Budget constraints and consumption status

        Returns:
            True if any budget is at critical level, False otherwise
        """
        # Avoid division by zero for budgets with max of 0
        if budgets.max_iterations > 0:
            if (
                budgets.iterations_consumed / budgets.max_iterations
                >= self.CRITICAL_BUDGET_THRESHOLD
            ):
                return True
        if budgets.max_tool_calls > 0:
            if (
                budgets.tool_calls_consumed / budgets.max_tool_calls
                >= self.CRITICAL_BUDGET_THRESHOLD
            ):
                return True
        if budgets.max_wall_time_seconds > 0:
            if (
                budgets.wall_time_consumed / budgets.max_wall_time_seconds
                >= self.CRITICAL_BUDGET_THRESHOLD
            ):
                return True
        if budgets.max_subagent_calls > 0:
            if (
                budgets.subagent_calls_consumed / budgets.max_subagent_calls
                >= self.CRITICAL_BUDGET_THRESHOLD
            ):
                return True

        return False

    def _create_budget_exhausted_proposal(self) -> StepProposal:
        """Create a minimal proposal for when budget is exhausted.

        Returns:
            A minimal no-op proposal indicating budget exhaustion
        """
        return StepProposal(
            intent="Budget exhausted - no further actions possible",
            target_todo_ids=[],
            requested_context=[],
            actions=[],
            completion_claims=[],
            risk_level=RiskLevel.LOW,
            notes="All available budget has been consumed. Cannot propose further actions.",
        )

    def _create_approval_request_proposal(self, input: PolicyInput) -> StepProposal:
        """Create a proposal requesting human approval for high-risk situation.

        Args:
            input: Current runtime state

        Returns:
            A proposal that requests human approval before proceeding
        """
        # Build a descriptive message about why approval is needed
        reasons: list[str] = []
        if any(c.severity == "hard" for c in input.constraints):
            reasons.append("hard constraints are active")
        if self._is_budget_critical(input.budgets):
            reasons.append("budget is critically low")

        reason_text = " and ".join(reasons) if reasons else "high-risk conditions detected"

        approval_action = RequestApprovalAction(
            message=f"Approval required before proceeding: {reason_text}. Goal: {input.goal}",
            options=["approve", "reject", "modify"],
        )

        return StepProposal(
            intent=f"Request approval due to: {reason_text}",
            target_todo_ids=[],
            requested_context=[],
            actions=[approval_action],
            completion_claims=[],
            risk_level=RiskLevel.HIGH,
            notes="High-risk situation detected. Human approval required.",
        )

    def _create_default_proposal(self, input: PolicyInput) -> StepProposal:
        """Create a minimal proposal targeting the first pending TODO.

        If no pending TODOs exist, returns a minimal no-op proposal.

        Args:
            input: Current runtime state

        Returns:
            A minimal proposal targeting the first pending TODO, or a
            no-op proposal if no pending TODOs exist
        """
        # Find the first pending TODO
        first_pending = self._get_first_pending_todo(input.active_todos)

        if first_pending is None:
            return StepProposal(
                intent="No pending TODOs to address",
                target_todo_ids=[],
                requested_context=[],
                actions=[],
                completion_claims=[],
                risk_level=RiskLevel.LOW,
                notes="All TODOs are completed or no TODOs defined.",
            )

        # Create a minimal proposal that references the first pending TODO
        # This is a lightweight proposal - the agent can expand on it
        return StepProposal(
            intent=f"Address TODO: {first_pending.description}",
            target_todo_ids=[first_pending.id],
            requested_context=[],
            actions=[],
            completion_claims=[],
            risk_level=RiskLevel.LOW,
            notes=f"Minimal proposal targeting first pending TODO (priority: {first_pending.priority})",
        )

    def _get_first_pending_todo(self, todos: list[TodoItem]) -> TodoItem | None:
        """Get the first pending TODO from the list.

        Priority order: high > medium > low
        Within same priority, first in list wins.

        Args:
            todos: List of TODO items

        Returns:
            First pending TODO, or None if no pending TODOs exist
        """
        pending_todos = [t for t in todos if t.status == "pending"]

        if not pending_todos:
            return None

        # Sort by priority (high first)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        pending_todos.sort(key=lambda t: priority_order.get(t.priority, 1))

        return pending_todos[0]


__all__ = ["RulesPolicy"]
