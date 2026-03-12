from __future__ import annotations

import json

from dawn_kestrel.policy.validator import ValidationResult

from .contracts import StepProposal


class HarnessInvariants:
    _VERIFICATION_EVIDENCE_TYPES = {
        "test_passed",
        "build_succeeded",
        "manual_review",
    }
    _APPROVAL_REQUIRED_ACTIONS = {"EDIT_FILE", "RUN_TESTS"}
    _BUDGET_EXHAUSTED_MARKERS = (
        "budget_exhausted",
        "budget exhausted",
        "budget_exceeded",
        "budget exceeded",
    )

    def verify_before_done(self, proposal: StepProposal) -> bool:
        if not proposal.completion_claims:
            return True
        return any(
            claim.evidence_type in self._VERIFICATION_EVIDENCE_TYPES
            for claim in proposal.completion_claims
        )

    def approval_required(self, proposal: StepProposal) -> bool:
        action_types = set(proposal.get_action_types())
        if not self._APPROVAL_REQUIRED_ACTIONS.intersection(action_types):
            return True
        return "REQUEST_APPROVAL" in action_types

    def budget_exhausted(self, proposal: StepProposal) -> bool:
        notes = proposal.notes.lower().strip()
        if not notes:
            return False
        return any(marker in notes for marker in self._BUDGET_EXHAUSTED_MARKERS)


class HarnessGate:
    _POLICY_ID = "harness_invariants"
    _APPROVAL_REQUIRED_ACTIONS = {"EDIT_FILE", "RUN_TESTS"}

    def __init__(self, invariants: HarnessInvariants | None = None) -> None:
        self._invariants = invariants or HarnessInvariants()

    def enforce(self, proposal: StepProposal) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if self._invariants.budget_exhausted(proposal):
            errors.append(
                self._format_rejection(
                    reason_code="BUDGET_EXHAUSTED",
                    blocked_action_type=self._first_action_type(proposal) or "HALT",
                    blocked_action_risk=self._proposal_risk(proposal),
                    remediation_hints=[
                        "Stop execution and request additional budget approval",
                        "Summarize progress before exiting",
                    ],
                )
            )
            return self._build_result(valid=False, errors=errors, warnings=warnings)

        if not self._invariants.verify_before_done(proposal):
            errors.append(
                self._format_rejection(
                    reason_code="UNVERIFIED_COMPLETION",
                    blocked_action_type="COMPLETE_TODO",
                    blocked_action_risk=self._proposal_risk(proposal),
                    remediation_hints=[
                        "Provide verification evidence (test_passed, build_succeeded, manual_review)",
                        "Include evidence references for completed work",
                    ],
                )
            )
            return self._build_result(valid=False, errors=errors, warnings=warnings)

        if not self._invariants.approval_required(proposal):
            errors.append(
                self._format_rejection(
                    reason_code="APPROVAL_REQUIRED",
                    blocked_action_type=self._approval_blocked_action(proposal),
                    blocked_action_risk=self._proposal_risk(proposal),
                    remediation_hints=[
                        "Add a REQUEST_APPROVAL action before high-risk operations",
                        "Wait for explicit approval before proceeding",
                    ],
                )
            )
            return self._build_result(valid=False, errors=errors, warnings=warnings)

        return self._build_result(valid=True, errors=errors, warnings=warnings)

    @staticmethod
    def _build_result(
        valid: bool,
        errors: list[str],
        warnings: list[str],
    ) -> ValidationResult:
        return ValidationResult(valid=valid, errors=errors, warnings=warnings)

    def _format_rejection(
        self,
        reason_code: str,
        blocked_action_type: str,
        blocked_action_risk: str,
        remediation_hints: list[str],
    ) -> str:
        payload = {
            "policy_id": self._POLICY_ID,
            "reason_code": reason_code,
            "blocked_action_type": blocked_action_type,
            "blocked_action_risk": blocked_action_risk,
            "remediation_hints": remediation_hints,
        }
        return json.dumps(payload)

    @staticmethod
    def _proposal_risk(proposal: StepProposal) -> str:
        risk_level = proposal.risk_level
        return getattr(risk_level, "value", str(risk_level))

    @staticmethod
    def _first_action_type(proposal: StepProposal) -> str | None:
        action_types = proposal.get_action_types()
        return action_types[0] if action_types else None

    def _approval_blocked_action(self, proposal: StepProposal) -> str:
        action_types = proposal.get_action_types()
        for action_type in action_types:
            if action_type in self._APPROVAL_REQUIRED_ACTIONS:
                return action_type
        return action_types[0] if action_types else "UNKNOWN"


__all__ = [
    "HarnessInvariants",
    "HarnessGate",
]
