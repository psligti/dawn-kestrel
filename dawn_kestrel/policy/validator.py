"""Proposal validation for the policy engine.

This module provides validation logic for StepProposal objects,
ensuring they conform to schema requirements and business rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dawn_kestrel.policy.contracts import Action, RiskLevel, StepProposal

# Valid action types from the Action discriminated union
VALID_ACTION_TYPES = {
    "READ_FILE",
    "SEARCH_REPO",
    "EDIT_FILE",
    "RUN_TESTS",
    "UPSERT_TODOS",
    "REQUEST_APPROVAL",
    "SUMMARIZE",
}


@dataclass
class ValidationResult:
    """Result of validating a StepProposal.

    Attributes:
        valid: Whether the proposal passed validation
        errors: List of validation errors (blocking issues)
        warnings: List of validation warnings (non-blocking issues)
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ProposalValidator:
    """Validates StepProposal objects against schema and business rules.

    This validator checks:
    - Required fields are present and valid
    - Action types are known/supported
    - Risk levels are valid enum values
    - Additional business rule constraints
    """

    def validate(self, proposal: StepProposal) -> ValidationResult:
        """Validate a StepProposal.

        Args:
            proposal: The proposal to validate

        Returns:
            ValidationResult with valid flag, errors, and warnings
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check required fields
        if not proposal.intent or not proposal.intent.strip():
            errors.append("Field 'intent' is required and cannot be empty")

        # Validate action types
        for i, action in enumerate(proposal.actions):
            action_type = action.action_type
            if action_type not in VALID_ACTION_TYPES:
                errors.append(
                    f"Action at index {i} has unknown action_type '{action_type}'. "
                    f"Valid types: {', '.join(sorted(VALID_ACTION_TYPES))}"
                )

        # Validate risk level
        if not isinstance(proposal.risk_level, RiskLevel):
            try:
                # Try to convert string to RiskLevel
                RiskLevel(proposal.risk_level)
            except (ValueError, TypeError):
                errors.append(
                    f"Invalid risk_level '{proposal.risk_level}'. "
                    f"Valid values: {', '.join([r.value for r in RiskLevel])}"
                )

        # Add warnings for empty actions (non-blocking)
        if not proposal.actions:
            warnings.append(
                "Proposal has no actions - this may be intentional for context requests"
            )

        # Check for potential issues
        if proposal.target_todo_ids and not proposal.completion_claims:
            warnings.append(
                "Proposal targets TODOs but has no completion_claims - "
                "consider adding claims if this step completes work"
            )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )


__all__ = [
    "ValidationResult",
    "ProposalValidator",
    "VALID_ACTION_TYPES",
]
