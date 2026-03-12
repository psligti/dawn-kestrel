"""Policy evaluation matrix - runs scenarios against all policy modes."""

import json
from typing import Optional

import pytest

from dawn_kestrel.policy import (
    BudgetInfo,
    Constraint,
    PolicyInput,
    RunTestsAction,
    TodoCompletionClaim,
    TodoItem,
)
from dawn_kestrel.policy.invariants import HarnessGate
from dawn_kestrel.policy.router_policy import RouterPolicy

POLICY_MODES = ["fsm", "rules", "react", "plan_execute", "router"]


def _base_input(*, budgets: Optional[BudgetInfo] = None) -> PolicyInput:
    return PolicyInput(
        goal="Validate policy invariants",
        active_todos=[
            TodoItem(id="todo-1", description="Review policy matrix", status="pending"),
        ],
        budgets=budgets or BudgetInfo(),
        constraints=[
            Constraint(
                constraint_type="custom",
                value="approval_required",
                description="High-risk action requires approval",
                severity="hard",
            )
        ],
    )


class TestPolicyEvalMatrix:
    """Run evaluation scenarios against all policy modes."""

    @pytest.mark.parametrize("policy_mode", POLICY_MODES)
    def test_verify_before_done_all_modes(
        self, policy_mode: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify completion claims require evidence in all modes."""
        monkeypatch.setenv("DK_POLICY_MODE", policy_mode)
        policy = RouterPolicy()
        proposal = policy.propose(_base_input())
        proposal = proposal.model_copy(
            update={
                "completion_claims": [
                    TodoCompletionClaim(
                        todo_id="todo-1",
                        evidence_type="inference",
                        evidence_summary="Assumed done",
                    )
                ]
            }
        )

        gate = HarnessGate()
        result = gate.enforce(proposal)

        assert result.valid is False
        assert result.errors
        payload = json.loads(result.errors[0])
        assert payload["reason_code"] == "UNVERIFIED_COMPLETION"

    @pytest.mark.parametrize("policy_mode", POLICY_MODES)
    def test_budget_compliance_all_modes(
        self, policy_mode: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Budget exhaustion is handled correctly in all modes."""
        monkeypatch.setenv("DK_POLICY_MODE", policy_mode)
        policy = RouterPolicy()
        budgets = BudgetInfo(max_iterations=100, iterations_consumed=100)
        proposal = policy.propose(_base_input(budgets=budgets))
        proposal = proposal.model_copy(update={"notes": "Budget exhausted after 100 iterations."})

        gate = HarnessGate()
        result = gate.enforce(proposal)

        assert result.valid is False
        assert result.errors
        payload = json.loads(result.errors[0])
        assert payload["reason_code"] == "BUDGET_EXHAUSTED"

    @pytest.mark.parametrize("policy_mode", POLICY_MODES)
    def test_approval_required_all_modes(
        self, policy_mode: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """High-risk actions require approval in all modes."""
        monkeypatch.setenv("DK_POLICY_MODE", policy_mode)
        policy = RouterPolicy()
        proposal = policy.propose(_base_input())
        proposal = proposal.model_copy(update={"actions": [RunTestsAction(test_path="tests/")]})

        gate = HarnessGate()
        result = gate.enforce(proposal)

        assert result.valid is False
        assert result.errors
        payload = json.loads(result.errors[0])
        assert payload["reason_code"] == "APPROVAL_REQUIRED"
