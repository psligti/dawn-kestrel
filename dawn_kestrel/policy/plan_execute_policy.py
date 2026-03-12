"""Plan-Execute policy engine implementation.

This module provides a simple policy engine for plan-execute agent patterns.
The PlanExecutePolicy implements the PolicyEngine protocol with deterministic
TODO selection logic.

Behavior:
- If no TODOs in input → return minimal proposal (plan generation will be added later)
- If TODOs exist → return minimal proposal targeting first pending TODO
- Deterministic: same input always produces same output

This is a lightweight policy intended to be extended with plan generation
capabilities in future iterations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dawn_kestrel.policy.contracts import (
    PolicyInput,
    RiskLevel,
    StepProposal,
    TodoItem,
)

if TYPE_CHECKING:
    from dawn_kestrel.policy.engine import PolicyEngine


class PlanExecutePolicy:
    """Simple plan-execute policy with deterministic TODO selection.

    This implementation provides minimal proposal generation targeting
    the first pending TODO. It serves as a foundation for plan-execute
    agent patterns where:
    1. A planning phase generates TODOs
    2. An execution phase targets TODOs sequentially

    Determinism guarantee:
    Same input always produces same output (no randomness, no time-dependent logic).

    Example:
        >>> policy = PlanExecutePolicy()
        >>> input_data = PolicyInput(goal="Fix bug")
        >>> proposal = policy.propose(input_data)
        >>> proposal.intent
        'No pending TODOs - awaiting plan generation'
    """

    def propose(self, input: PolicyInput) -> StepProposal:
        """Evaluate input and return a step proposal.

        Decision logic:
        1. If no pending TODOs → return minimal proposal (plan generation needed)
        2. If pending TODOs exist → target first pending TODO deterministically

        Args:
            input: Current runtime state including goals, todos, constraints

        Returns:
            StepProposal: A proposal targeting the first pending TODO, or
                         a minimal no-op proposal if no pending TODOs exist
        """
        # Find the first pending TODO using deterministic selection
        first_pending = self._get_first_pending_todo(input.active_todos)

        if first_pending is None:
            return self._create_no_todos_proposal(input)

        return self._create_todo_targeting_proposal(first_pending)

    def _get_first_pending_todo(self, todos: list[TodoItem]) -> TodoItem | None:
        """Get the first pending TODO using deterministic selection.

        Selection order (deterministic):
        1. Filter to only pending TODOs
        2. Sort by priority (high > medium > low)
        3. Within same priority, first in list wins (stable sort)

        Args:
            todos: List of TODO items

        Returns:
            First pending TODO, or None if no pending TODOs exist
        """
        pending_todos = [t for t in todos if t.status == "pending"]

        if not pending_todos:
            return None

        # Sort by priority (high=0, medium=1, low=2) - deterministic ordering
        priority_order = {"high": 0, "medium": 1, "low": 2}
        pending_todos.sort(key=lambda t: priority_order.get(t.priority, 1))

        return pending_todos[0]

    def _create_no_todos_proposal(self, input: PolicyInput) -> StepProposal:
        """Create a minimal proposal when no pending TODOs exist.

        This indicates that plan generation is needed (to be implemented later).

        Args:
            input: Current runtime state

        Returns:
            A minimal no-op proposal indicating plan generation is needed
        """
        return StepProposal(
            intent="No pending TODOs - awaiting plan generation",
            target_todo_ids=[],
            requested_context=[],
            actions=[],
            completion_claims=[],
            risk_level=RiskLevel.LOW,
            notes="No pending TODOs available. Plan generation will be added in future iteration.",
        )

    def _create_todo_targeting_proposal(self, todo: TodoItem) -> StepProposal:
        """Create a minimal proposal targeting a specific TODO.

        This is a lightweight proposal that identifies the TODO to work on
        without prescribing specific actions. The execution phase can expand
        on this proposal.

        Args:
            todo: The TODO item to target

        Returns:
            A minimal proposal targeting the specified TODO
        """
        return StepProposal(
            intent=f"Execute TODO: {todo.description}",
            target_todo_ids=[todo.id],
            requested_context=[],
            actions=[],
            completion_claims=[],
            risk_level=RiskLevel.LOW,
            notes=f"Minimal proposal targeting TODO '{todo.id}' (priority: {todo.priority})",
        )


__all__ = ["PlanExecutePolicy"]
