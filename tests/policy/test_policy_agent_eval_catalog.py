from __future__ import annotations

import json

import pytest

from dawn_kestrel.policy import (
    BudgetInfo,
    Constraint,
    EditFileAction,
    PolicyInput,
    RunTestsAction,
    SearchRepoAction,
    StepProposal,
    TodoCompletionClaim,
    TodoItem,
)
from dawn_kestrel.policy.engine import PolicyEngine
from dawn_kestrel.policy.invariants import HarnessGate
from dawn_kestrel.policy.router_policy import RouterPolicy


def _reason_code_from_errors(errors: list[str]) -> str:
    assert errors, "expected at least one structured rejection error"
    payload = json.loads(errors[0])
    return str(payload["reason_code"])


def _input(
    *,
    goal: str,
    todos: list[TodoItem] | None = None,
    budgets: BudgetInfo | None = None,
    constraints: list[Constraint] | None = None,
) -> PolicyInput:
    return PolicyInput(
        goal=goal,
        active_todos=todos
        or [
            TodoItem(
                id="todo-1",
                description="Inspect repository and propose safe next step",
                status="pending",
                priority="high",
            )
        ],
        budgets=budgets or BudgetInfo(),
        constraints=constraints or [],
    )


@pytest.mark.parametrize(
    "mode",
    ["fsm", "rules", "react", "plan_execute", "router"],
)
def test_eval_policy_mode_baselines_return_proposals(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DK_POLICY_MODE", mode)
    policy = RouterPolicy()

    proposal = policy.propose(_input(goal=f"baseline-{mode}"))

    assert isinstance(proposal, StepProposal)
    assert proposal.intent


def test_eval_rules_deterministic_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DK_POLICY_MODE", "rules")
    policy = RouterPolicy()
    input_data = _input(goal="rules-determinism")

    p1 = policy.propose(input_data)
    p2 = policy.propose(input_data)

    assert p1.intent == p2.intent
    assert p1.target_todo_ids == p2.target_todo_ids
    assert p1.get_action_types() == p2.get_action_types()


def test_eval_plan_execute_progression(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DK_POLICY_MODE", "plan_execute")
    policy = RouterPolicy()

    proposal = policy.propose(
        _input(
            goal="plan progression",
            todos=[
                TodoItem(id="todo-a", description="first task", status="pending", priority="high"),
                TodoItem(id="todo-b", description="second task", status="pending", priority="low"),
            ],
        )
    )

    assert proposal.target_todo_ids
    assert proposal.target_todo_ids[0] == "todo-a"


def test_eval_router_mode_selection_prefers_rules_under_strict_constraints() -> None:
    policy = RouterPolicy()

    proposal = policy.propose(
        _input(
            goal="router strictness",
            constraints=[
                Constraint(
                    constraint_type="permission",
                    value="read_only",
                    severity="hard",
                    description="No risky operations without approval",
                )
            ],
        )
    )

    assert proposal.intent.lower().startswith("request approval")


@pytest.mark.parametrize(
    "action,expected_reason",
    [
        (
            EditFileAction(path="README.md", operation="replace", content="updated"),
            "APPROVAL_REQUIRED",
        ),
        (RunTestsAction(test_path="tests/"), "APPROVAL_REQUIRED"),
    ],
)
def test_eval_approval_gate_high_risk_actions(
    action: EditFileAction | RunTestsAction,
    expected_reason: str,
) -> None:
    gate = HarnessGate()
    proposal = StepProposal(intent="high-risk op", actions=[action])

    result = gate.enforce(proposal)

    assert result.valid is False
    assert _reason_code_from_errors(result.errors) == expected_reason


def test_eval_budget_soft_pressure_stays_valid() -> None:
    gate = HarnessGate()
    proposal = StepProposal(intent="conservative step", notes="80 percent budget consumed")

    result = gate.enforce(proposal)

    assert result.valid is True


def test_eval_budget_hard_stop_is_blocked() -> None:
    gate = HarnessGate()
    proposal = StepProposal(intent="cannot continue", notes="budget exhausted after retries")

    result = gate.enforce(proposal)

    assert result.valid is False
    assert _reason_code_from_errors(result.errors) == "BUDGET_EXHAUSTED"


def test_eval_done_gate_verification_required_blocks_unverified_completion() -> None:
    gate = HarnessGate()
    proposal = StepProposal(
        intent="done claim",
        completion_claims=[
            TodoCompletionClaim(
                todo_id="todo-1",
                evidence_type="inference",
                evidence_summary="looks done",
            )
        ],
    )

    result = gate.enforce(proposal)

    assert result.valid is False
    assert _reason_code_from_errors(result.errors) == "UNVERIFIED_COMPLETION"


def test_eval_todo_evidence_required_accepts_verified_completion() -> None:
    gate = HarnessGate()
    proposal = StepProposal(
        intent="verified done",
        completion_claims=[
            TodoCompletionClaim(
                todo_id="todo-1",
                evidence_type="test_passed",
                evidence_summary="pytest policy suite passed",
                evidence_refs=["tests/policy/test_policy_eval_suite.py"],
            )
        ],
    )

    result = gate.enforce(proposal)

    assert result.valid is True


def test_eval_ordering_todo_verify_done_contract_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DK_POLICY_MODE", "plan_execute")
    policy = RouterPolicy()
    proposal = policy.propose(
        _input(
            goal="todo then verify then done",
            todos=[
                TodoItem(id="todo-1", description="complete ordered workflow", status="pending")
            ],
        )
    )

    assert isinstance(proposal.target_todo_ids, list)


def test_eval_router_fallback_resilience(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = RouterPolicy()

    class _BoomPolicy:
        def propose(self, input: PolicyInput) -> StepProposal:
            raise RuntimeError("forced policy failure")

    def _select_policy(_input_data: PolicyInput) -> PolicyEngine:
        return _BoomPolicy()

    monkeypatch.setattr(policy, "_select_policy", _select_policy)

    proposal = policy.propose(_input(goal="router fallback"))

    assert proposal.intent == "FSM-based action (not yet wired)"


def test_eval_rejection_disallowed_search_without_approval() -> None:
    gate = HarnessGate()
    proposal = StepProposal(
        intent="safe search",
        actions=[SearchRepoAction(pattern="policy", file_pattern="*.py")],
    )

    result = gate.enforce(proposal)

    assert result.valid is True
