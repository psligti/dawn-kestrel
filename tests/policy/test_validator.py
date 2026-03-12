"""Tests for proposal validation."""

import pytest
from pydantic import ValidationError

from dawn_kestrel.policy.contracts import (
    ReadFileAction,
    RiskLevel,
    StepProposal,
)
from dawn_kestrel.policy.validator import ProposalValidator, ValidationResult


class TestProposalValidator:
    """Tests for ProposalValidator class."""

    @pytest.fixture
    def validator(self) -> ProposalValidator:
        """Create a validator instance."""
        return ProposalValidator()

    def test_valid_proposal_passes(self, validator: ProposalValidator) -> None:
        """A valid proposal should pass validation with no errors."""
        proposal = StepProposal(
            intent="Read the authentication module",
            actions=[ReadFileAction(path="auth.py")],
            risk_level=RiskLevel.LOW,
        )

        result = validator.validate(proposal)

        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert result.errors == []
        # May have warnings, but no errors

    def test_invalid_action_type_fails(self, validator: ProposalValidator) -> None:
        """A proposal with an unknown action type should fail validation.
        
        Note: Pydantic validates action types during model construction,
        so invalid types are rejected before reaching our validator.
        This test verifies that behavior.
        """
        with pytest.raises(ValidationError) as exc_info:
            StepProposal(
                intent="Do something invalid",
                actions=[
                    {
                        "action_type": "INVALID_ACTION",
                        "path": "test.py",
                    }
                ],
                risk_level=RiskLevel.LOW,
            )
        
        # Verify the error mentions the invalid action type
        assert "INVALID_ACTION" in str(exc_info.value)
    def test_missing_required_fields_fails(self, validator: ProposalValidator) -> None:
        """A proposal missing required fields should fail validation."""
        # Create a proposal with empty intent
        proposal = StepProposal(
            intent="",  # Empty intent should fail
            actions=[ReadFileAction(path="test.py")],
            risk_level=RiskLevel.LOW,
        )

        result = validator.validate(proposal)

        assert result.valid is False
        assert len(result.errors) > 0
        assert any("intent" in err.lower() and "required" in err.lower() for err in result.errors)

    def test_empty_intent_fails(self, validator: ProposalValidator) -> None:
        """A proposal with whitespace-only intent should fail."""
        proposal = StepProposal(
            intent="   \n\t  ",  # Whitespace only
            actions=[ReadFileAction(path="test.py")],
            risk_level=RiskLevel.LOW,
        )

        result = validator.validate(proposal)

        assert result.valid is False
        assert any("intent" in err.lower() for err in result.errors)

    def test_valid_all_action_types(self, validator: ProposalValidator) -> None:
        """All valid action types should pass validation."""
        from dawn_kestrel.policy.contracts import (
            EditFileAction,
            RequestApprovalAction,
            RunTestsAction,
            SearchRepoAction,
            SummarizeAction,
            UpsertTodosAction,
        )

        proposals = [
            StepProposal(
                intent="Read file",
                actions=[ReadFileAction(path="test.py")],
                risk_level=RiskLevel.LOW,
            ),
            StepProposal(
                intent="Search repo",
                actions=[SearchRepoAction(pattern="test")],
                risk_level=RiskLevel.LOW,
            ),
            StepProposal(
                intent="Edit file",
                actions=[EditFileAction(path="test.py", content="new content")],
                risk_level=RiskLevel.MED,
            ),
            StepProposal(
                intent="Run tests",
                actions=[RunTestsAction(test_path="tests/")],
                risk_level=RiskLevel.MED,
            ),
            StepProposal(
                intent="Update todos",
                actions=[UpsertTodosAction(todos=[{"id": "1", "description": "Test"}])],
                risk_level=RiskLevel.LOW,
            ),
            StepProposal(
                intent="Request approval",
                actions=[RequestApprovalAction(message="Approve this?")],
                risk_level=RiskLevel.MED,
            ),
            StepProposal(
                intent="Summarize",
                actions=[SummarizeAction(content="Long text to summarize")],
                risk_level=RiskLevel.LOW,
            ),
        ]

        for proposal in proposals:
            result = validator.validate(proposal)
            assert result.valid, f"Proposal failed: {proposal.intent}, errors: {result.errors}"

    def test_valid_risk_levels(self, validator: ProposalValidator) -> None:
        """All valid risk levels should pass validation."""
        for risk_level in [RiskLevel.LOW, RiskLevel.MED, RiskLevel.HIGH]:
            proposal = StepProposal(
                intent=f"Test with {risk_level.value} risk",
                actions=[ReadFileAction(path="test.py")],
                risk_level=risk_level,
            )

            result = validator.validate(proposal)
            assert result.valid, f"Risk level {risk_level} should be valid"

    def test_empty_actions_warning(self, validator: ProposalValidator) -> None:
        """A proposal with no actions should generate a warning."""
        proposal = StepProposal(
            intent="Context-only request",
            actions=[],  # No actions
            risk_level=RiskLevel.LOW,
        )

        result = validator.validate(proposal)

        # Should still be valid
        assert result.valid is True
        # But should have a warning
        assert len(result.warnings) > 0
        assert any("no actions" in warn.lower() for warn in result.warnings)

    def test_todo_target_without_claim_warning(self, validator: ProposalValidator) -> None:
        """Targeting TODOs without completion claims should generate a warning."""
        proposal = StepProposal(
            intent="Work on TODO",
            target_todo_ids=["todo-1", "todo-2"],
            actions=[ReadFileAction(path="test.py")],
            risk_level=RiskLevel.LOW,
            completion_claims=[],  # No claims despite targeting TODOs
        )

        result = validator.validate(proposal)

        # Should still be valid
        assert result.valid is True
        # But should have a warning
        assert len(result.warnings) > 0
        assert any("completion_claims" in warn.lower() for warn in result.warnings)

    def test_multiple_errors_reported(self, validator: ProposalValidator) -> None:
        """Multiple validation errors should all be reported.
        
        Note: Invalid action types are caught by Pydantic during construction.
        This test verifies that our validator catches other issues like empty intent.
        """
        proposal = StepProposal(
            intent="",  # Missing intent - our validator catches this
            actions=[ReadFileAction(path="test.py")],  # Valid action
            risk_level=RiskLevel.LOW,
        )

        result = validator.validate(proposal)

        assert result.valid is False
        # Should have error for empty intent
        assert any("intent" in err.lower() for err in result.errors)
        assert len(result.errors) >= 1

class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_dataclass_fields(self) -> None:
        """ValidationResult should have expected fields."""
        result = ValidationResult(
            valid=True,
            errors=[],
            warnings=["test warning"],
        )

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == ["test warning"]

    def test_default_lists(self) -> None:
        """ValidationResult should have empty lists by default."""
        result = ValidationResult(valid=True)

        assert result.errors == []
        assert result.warnings == []
