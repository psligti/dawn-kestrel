"""RouterPolicy - delegates to sub-policies based on signals and feature flags.

This module provides a policy engine that routes decisions to different
sub-policies based on runtime signals and feature flags. The RouterPolicy
acts as a meta-policy that selects the appropriate policy implementation
based on the current context.

Routing logic (in priority order):
1. If DK_POLICY_MODE env var is set → use that policy directly
2. If budget pressure is high (>= 80% iterations consumed) → RulesPolicy
3. If strictness is high (hard constraints present) → RulesPolicy
4. If ambiguity is high (many incomplete TODOs and no clear next step) → ReActPolicy
5. If tool intensity is high (file/edit-heavy TODOs) → PlanExecutePolicy
6. Default → RulesPolicy

Fallback behavior:
- On any exception from the selected policy → fallback to FSMPolicy
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

from dawn_kestrel.core.event_bus import bus
from dawn_kestrel.policy.contracts import PolicyInput, StepProposal
from dawn_kestrel.policy.fsm_bridge import FSMPolicy
from dawn_kestrel.policy.plan_execute_policy import PlanExecutePolicy
from dawn_kestrel.policy.react_policy import ReActPolicy
from dawn_kestrel.policy.rules_policy import RulesPolicy

if TYPE_CHECKING:
    from dawn_kestrel.policy.engine import PolicyEngine


class RouterPolicy:
    """Routes to sub-policies based on signals and feature flags.

    This implementation selects the appropriate policy engine based on
    runtime signals such as environment variables and budget consumption.
    It acts as a meta-policy that delegates to specialized policies.

    Routing strategy:
        1. Feature flag (DK_POLICY_MODE): If set, use the specified policy
        2. Budget pressure: If >= 80% of iterations consumed, use RulesPolicy
        3. Strictness: If hard constraints present, use RulesPolicy
        4. Ambiguity: If many incomplete TODOs with no clear next step, use ReActPolicy
        5. Tool intensity: If TODOs indicate heavy file/edit work, use PlanExecutePolicy
        6. Default: Use RulesPolicy

    Fallback:
        If the selected policy raises an exception, fallback to FSMPolicy.

    Example:
        >>> policy = RouterPolicy()
        >>> input_data = PolicyInput(goal="Fix bug")
        >>> proposal = policy.propose(input_data)
        >>> proposal.intent
        'Budget exhausted - no further actions possible'
    """

    # Budget threshold for conservative mode (percentage of max iterations)
    CONSERVATIVE_BUDGET_THRESHOLD = 0.8  # 80% consumed = switch to conservative mode
    AMBIGUITY_TODO_THRESHOLD = 3
    TOOL_INTENSITY_THRESHOLD = 0.5

    def __init__(self) -> None:
        """Initialize the router policy with all sub-policies."""
        self._rules = RulesPolicy()
        self._react = ReActPolicy()
        self._plan_execute = PlanExecutePolicy()
        self._fsm = FSMPolicy()

    def propose(self, input: PolicyInput) -> StepProposal:
        """Route to the appropriate sub-policy and return its proposal.

        Routing logic (in priority order):
            1. Check DK_POLICY_MODE env var
            2. Check budget consumption (>= 80% → RulesPolicy)
            3. Default to RulesPolicy

        On exception from selected policy, fallback to FSMPolicy.

        Args:
            input: Current runtime state including goals, todos, constraints

        Returns:
            StepProposal: An approved proposal from the selected sub-policy

        Note:
            If DK_POLICY_MODE is set, valid values are:
            - "rules" → RulesPolicy
            - "react" → ReActPolicy
            - "plan_execute" → PlanExecutePolicy
            - "fsm" → FSMPolicy
        """
        policy_name = "unknown"
        try:
            # Select the appropriate policy
            policy = self._select_policy(input)
            policy_name = policy.__class__.__name__

            # Delegate to the selected policy
            return policy.propose(input)

        except Exception as e:
            # Fallback to FSMPolicy on any exception
            self._emit_fallback_event(policy_name, str(e))
            return self._fsm.propose(input)

    def _select_policy(self, input: PolicyInput) -> PolicyEngine:
        """Select the appropriate policy based on signals.

        Selection priority:
            1. DK_POLICY_MODE env var (if set)
            2. Budget pressure (>= 80% → RulesPolicy)
            3. Strictness (hard constraints → RulesPolicy)
            4. Ambiguity (many incomplete TODOs, no clear next step → ReActPolicy)
            5. Tool intensity (file/edit-heavy TODOs → PlanExecutePolicy)
            6. Default → RulesPolicy

        Args:
            input: Current runtime state

        Returns:
            The selected policy engine
        """
        # Priority 1: Check for explicit policy mode override
        policy_mode = os.getenv("DK_POLICY_MODE")
        if policy_mode:
            return self._get_policy_by_name(policy_mode)

        # Priority 2: Check budget pressure
        if self._compute_budget_headroom(input) <= (1.0 - self.CONSERVATIVE_BUDGET_THRESHOLD):
            return self._rules

        if self._compute_strictness(input) > 0.0:
            return self._rules

        if self._compute_ambiguity(input) >= 1.0:
            return self._react

        if self._compute_tool_intensity(input) >= self.TOOL_INTENSITY_THRESHOLD:
            return self._plan_execute

        return self._rules

    def _get_policy_by_name(self, mode: str) -> PolicyEngine:
        """Get a policy instance by name.

        Args:
            mode: Policy mode name (case-insensitive)

        Returns:
            The corresponding policy instance

        Note:
            Unknown modes default to RulesPolicy
        """
        mode_lower = mode.lower()
        policy_map: dict[str, PolicyEngine] = {
            "rules": self._rules,
            "react": self._react,
            "plan_execute": self._plan_execute,
            "fsm": self._fsm,
        }
        return policy_map.get(mode_lower, self._rules)

    def _compute_strictness(self, input: PolicyInput) -> float:
        total_constraints = len(input.constraints)
        if total_constraints == 0:
            return 0.0
        hard_constraints = sum(
            1 for constraint in input.constraints if constraint.severity == "hard"
        )
        return hard_constraints / total_constraints

    def _compute_budget_headroom(self, input: PolicyInput) -> float:
        max_iterations = input.budgets.max_iterations
        if max_iterations <= 0:
            return 1.0
        remaining = max_iterations - input.budgets.iterations_consumed
        return max(0.0, min(1.0, remaining / max_iterations))

    def _compute_ambiguity(self, input: PolicyInput) -> float:
        if not input.active_todos:
            return 0.0
        incomplete = [
            todo
            for todo in input.active_todos
            if todo.status in {"pending", "in_progress", "blocked"}
        ]
        if not incomplete:
            return 0.0
        pending = [todo for todo in incomplete if todo.status == "pending"]
        if len(incomplete) > self.AMBIGUITY_TODO_THRESHOLD and not pending:
            return 1.0
        return len(incomplete) / max(1, len(input.active_todos))

    def _compute_tool_intensity(self, input: PolicyInput) -> float:
        relevant_todos = [
            todo for todo in input.active_todos if todo.status in {"pending", "in_progress"}
        ]
        if not relevant_todos:
            return 0.0
        keywords = (
            "edit",
            "modify",
            "refactor",
            "rename",
            "delete",
            "remove",
            "move",
            "update",
            "write",
            "create",
            "add",
            "implement",
            "fix",
            "test",
            "build",
            "lint",
            "format",
        )
        matches = 0
        for todo in relevant_todos:
            description = todo.description.lower()
            if any(keyword in description for keyword in keywords):
                matches += 1
        return matches / len(relevant_todos)

    def _emit_fallback_event(self, policy_name: str, error_message: str) -> None:
        event_data = {
            "policy": policy_name,
            "error": error_message,
        }
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(bus.publish("policy.router.fallback", event_data))
            return
        loop.create_task(bus.publish("policy.router.fallback", event_data))


__all__ = ["RouterPolicy"]
