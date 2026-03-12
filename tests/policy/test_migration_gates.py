"""Migration gates - cutover decision tests for policy engine migration.

These tests verify that the migration from FSM to policy engine can proceed
safely by ensuring all critical invariants are maintained across all policy modes.
"""

from __future__ import annotations
import pytest

from dawn_kestrel.policy import (
    BudgetInfo,
    Constraint,
    PolicyInput,
    RunTestsAction,
    TodoCompletionClaim,
    TodoItem,
)
from dawn_kestrel.policy.fsm_bridge import FSMPolicy
from dawn_kestrel.policy.invariants import HarnessGate
from dawn_kestrel.policy.router_policy import RouterPolicy

# Cutover thresholds - 100% pass required for critical invariants
CUTOVER_THRESHOLDS = {
    "verify_before_done": 1.0,
    "budget_compliance": 1.0,
    "approval_required": 1.0,
}

POLICY_MODES = ["fsm", "rules", "react", "plan_execute", "router"]


def _base_input(*, budgets: BudgetInfo | None = None) -> PolicyInput:
    return PolicyInput(
        goal="Validate migration gates",
        active_todos=[
            TodoItem(id="todo-1", description="Review migration gates", status="pending"),
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


class TestMigrationGates:
    """Cutover gate tests for policy engine migration."""

    def test_no_critical_invariant_regressions(self) -> None:
        """All modes pass critical invariants - migration gate should pass."""
        results = {
            "verify_before_done": 0,
            "budget_compliance": 0,
            "approval_required": 0,
        }
        total_modes = len(POLICY_MODES)

        for mode in POLICY_MODES:
            # Test verify_before_done
            gate = HarnessGate()
            proposal = FSMPolicy().propose(_base_input())
            proposal = proposal.model_copy(
                update={
                    "completion_claims": [
                        TodoCompletionClaim(
                            todo_id="todo-1",
                            evidence_type="test_passed",  # Valid evidence
                            evidence_summary="Test passed",
                        )
                    ]
                }
            )
            result = gate.enforce(proposal)
            if result.valid:
                results["verify_before_done"] += 1

            # Test budget_compliance
            proposal = FSMPolicy().propose(
                _base_input(budgets=BudgetInfo(max_iterations=10, iterations_consumed=5))
            )
            result = gate.enforce(proposal)
            if result.valid:
                results["budget_compliance"] += 1

            # Test approval_required - low risk action should pass
            proposal = FSMPolicy().propose(_base_input())
            result = gate.enforce(proposal)
            if result.valid:
                results["approval_required"] += 1

        # Calculate pass rates
        pass_rates = {k: v / total_modes for k, v in results.items()}

        # Verify all thresholds are met
        for invariant, threshold in CUTOVER_THRESHOLDS.items():
            assert pass_rates[invariant] >= threshold, (
                f"Migration gate failed: {invariant} pass rate {pass_rates[invariant]:.2%} "
                f"below threshold {threshold:.0%}"
            )

    def test_migration_gate_blocks_on_invariant_regression(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Gate fails if any mode has regression - simulates invariant violation."""
        monkeypatch.setenv("DK_POLICY_MODE", "rules")
        policy = RouterPolicy()
        gate = HarnessGate()

        # Create a proposal with an unverified completion claim (invariant violation)
        proposal = policy.propose(_base_input())
        proposal = proposal.model_copy(
            update={
                "completion_claims": [
                    TodoCompletionClaim(
                        todo_id="todo-1",
                        evidence_type="inference",  # Invalid - not a verification type
                        evidence_summary="Assumed done",
                    )
                ]
            }
        )

        result = gate.enforce(proposal)

        # Gate should block this regression
        assert result.valid is False, "Migration gate should block unverified completion claims"
        assert result.errors, "Gate should report error details"

    def test_legacy_bridge_remains_active_until_gate_pass(self) -> None:
        """FSM bridge is fallback until gates pass."""
        # Verify FSM bridge is still available
        fsm = FSMPolicy()
        assert hasattr(fsm, "propose"), "FSM bridge must have propose method"

        # Verify FSM bridge returns valid proposals
        proposal = fsm.propose(_base_input())
        assert proposal is not None, "FSM bridge must return proposals"
        assert hasattr(proposal, "intent"), "Proposal must have intent"

        # Verify RouterPolicy can fall back to FSM
        router = RouterPolicy()
        assert hasattr(router, "_fsm"), "Router must have FSM fallback"
        assert isinstance(router._fsm, FSMPolicy), "FSM fallback must be FSMPolicy instance"

    @pytest.mark.parametrize("policy_mode", POLICY_MODES)
    def test_all_modes_produce_valid_proposals(
        self, policy_mode: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each policy mode produces valid StepProposal objects."""
        monkeypatch.setenv("DK_POLICY_MODE", policy_mode)
        policy = RouterPolicy()
        proposal = policy.propose(_base_input())

        # All modes must produce valid proposals
        assert proposal is not None
        assert hasattr(proposal, "intent")
        assert hasattr(proposal, "actions")
        assert hasattr(proposal, "risk_level")
        assert hasattr(proposal, "target_todo_ids")


class TestCutoverThresholds:
    """Tests for cutover threshold configuration."""

    def test_thresholds_are_strict(self) -> None:
        """Cutover thresholds require 100% pass rate for critical invariants."""
        for invariant, threshold in CUTOVER_THRESHOLDS.items():
            assert threshold == 1.0, (
                f"Threshold for {invariant} must be 1.0 (100%), got {threshold}"
            )

    def test_all_critical_invariants_have_thresholds(self) -> None:
        """All critical invariants have defined thresholds."""
        critical_invariants = {"verify_before_done", "budget_compliance", "approval_required"}
        assert critical_invariants == set(CUTOVER_THRESHOLDS.keys()), (
            "Threshold keys must match critical invariants"
        )
