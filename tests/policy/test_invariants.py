import importlib
import json
from typing import Any, Protocol

import pytest

contracts = importlib.import_module("dawn_kestrel.policy.contracts")
invariants_module = importlib.import_module("dawn_kestrel.policy.invariants")

EditFileAction = contracts.EditFileAction
ReadFileAction = contracts.ReadFileAction
RequestApprovalAction = contracts.RequestApprovalAction
RunTestsAction = contracts.RunTestsAction
StepProposal = contracts.StepProposal
TodoCompletionClaim = contracts.TodoCompletionClaim
HarnessInvariants = invariants_module.HarnessInvariants
HarnessGate = invariants_module.HarnessGate


class InvariantsProtocol(Protocol):
    def verify_before_done(self, proposal: Any) -> bool: ...

    def approval_required(self, proposal: Any) -> bool: ...

    def budget_exhausted(self, proposal: Any) -> bool: ...


@pytest.fixture
def invariants() -> InvariantsProtocol:
    return HarnessInvariants()


class TestVerifyBeforeDone:
    def test_allows_no_completion_claims(self, invariants: InvariantsProtocol) -> None:
        proposal = StepProposal(
            intent="Read file",
            actions=[ReadFileAction(path="README.md")],
        )

        assert invariants.verify_before_done(proposal) is True

    def test_rejects_unverified_completion_claims(self, invariants: InvariantsProtocol) -> None:
        proposal = StepProposal(
            intent="Mark todo done",
            completion_claims=[
                TodoCompletionClaim(
                    todo_id="todo-1",
                    evidence_type="file_modified",
                    evidence_summary="Updated implementation",
                )
            ],
        )

        assert invariants.verify_before_done(proposal) is False

    def test_allows_verified_completion_claims(self, invariants: InvariantsProtocol) -> None:
        proposal = StepProposal(
            intent="Mark todo done with tests",
            completion_claims=[
                TodoCompletionClaim(
                    todo_id="todo-2",
                    evidence_type="test_passed",
                    evidence_summary="Tests passed",
                )
            ],
        )

        assert invariants.verify_before_done(proposal) is True


class TestApprovalRequired:
    def test_requires_approval_for_edit_file(self, invariants: InvariantsProtocol) -> None:
        proposal = StepProposal(
            intent="Edit file",
            actions=[EditFileAction(path="main.py", content="updated")],
        )

        assert invariants.approval_required(proposal) is False

    def test_allows_approval_with_request_action(self, invariants: InvariantsProtocol) -> None:
        proposal = StepProposal(
            intent="Run tests with approval",
            actions=[
                RunTestsAction(test_path="tests/"),
                RequestApprovalAction(message="Run tests?"),
            ],
        )

        assert invariants.approval_required(proposal) is True

    def test_allows_non_sensitive_actions_without_approval(
        self, invariants: InvariantsProtocol
    ) -> None:
        proposal = StepProposal(
            intent="Read file",
            actions=[ReadFileAction(path="README.md")],
        )

        assert invariants.approval_required(proposal) is True


class TestBudgetExhausted:
    def test_false_when_no_budget_marker(self, invariants: InvariantsProtocol) -> None:
        proposal = StepProposal(
            intent="Continue work",
            actions=[ReadFileAction(path="README.md")],
            notes="",
        )

        assert invariants.budget_exhausted(proposal) is False

    def test_true_when_budget_marker_present(self, invariants: InvariantsProtocol) -> None:
        proposal = StepProposal(
            intent="Stop due to limits",
            actions=[],
            notes="Budget exhausted after 5 iterations.",
        )

        assert invariants.budget_exhausted(proposal) is True


class TestHarnessGate:
    def test_done_gate_passes(self) -> None:
        gate = HarnessGate()
        proposal = StepProposal(
            intent="Mark todo done",
            completion_claims=[
                TodoCompletionClaim(
                    todo_id="todo-1",
                    evidence_type="test_passed",
                    evidence_summary="Tests passed",
                )
            ],
        )

        result = gate.enforce(proposal)

        assert result.valid is True
        assert result.errors == []

    def test_done_gate_blocks_without_evidence(self) -> None:
        gate = HarnessGate()
        proposal = StepProposal(
            intent="Mark todo done without verification",
            completion_claims=[
                TodoCompletionClaim(
                    todo_id="todo-2",
                    evidence_type="file_modified",
                    evidence_summary="Updated files",
                )
            ],
        )

        result = gate.enforce(proposal)

        assert result.valid is False
        assert result.errors
        payload = json.loads(result.errors[0])
        assert payload["policy_id"] == "harness_invariants"
        assert payload["reason_code"] == "UNVERIFIED_COMPLETION"

    def test_approval_gate_enforced(self) -> None:
        gate = HarnessGate()
        proposal = StepProposal(
            intent="Run tests",
            actions=[RunTestsAction(test_path="tests/")],
        )

        result = gate.enforce(proposal)

        assert result.valid is False
        assert result.errors
        payload = json.loads(result.errors[0])
        assert payload["reason_code"] == "APPROVAL_REQUIRED"
        assert payload["blocked_action_type"] == "RUN_TESTS"

    def test_budget_exhaustion_halt(self) -> None:
        gate = HarnessGate()
        proposal = StepProposal(
            intent="Stop",
            actions=[ReadFileAction(path="README.md")],
            notes="Budget exhausted after 3 steps.",
        )

        result = gate.enforce(proposal)

        assert result.valid is False
        assert result.errors
        payload = json.loads(result.errors[0])
        assert payload["reason_code"] == "BUDGET_EXHAUSTED"
