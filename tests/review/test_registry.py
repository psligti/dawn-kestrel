"""Tests for ReviewerRegistry."""
from __future__ import annotations

import pytest

from dawn_kestrel.agents.review.registry import ReviewerRegistry
from dawn_kestrel.agents.review.base import BaseReviewerAgent
from dawn_kestrel.agents.review.contracts import ReviewInputs, ReviewOutput


class MockCustomReviewer(BaseReviewerAgent):
    """Mock custom reviewer for testing."""

    def get_agent_name(self) -> str:
        return "custom_reviewer"

    def get_system_prompt(self) -> str:
        return "Custom system prompt"

    def get_allowed_tools(self) -> list[str]:
        return []

    def get_relevant_file_patterns(self) -> list[str]:
        return ["**/*.py"]

    def is_relevant_to_changes(self, changed_files: list[str]) -> bool:
        return True

    async def review(self, inputs: ReviewInputs) -> ReviewOutput:
        from dawn_kestrel.agents.review.contracts import MergeGate, Scope, Finding
        return ReviewOutput(
            agent="custom_reviewer",
            summary="Mock review",
            severity="merge",
            scope=Scope(
                relevant_files=[],
                ignored_files=[],
                reasoning="Mock"
            ),
            checks=[],
            skips=[],
            findings=[],
            merge_gate=MergeGate(
                decision="approve",
                must_fix=[],
                should_fix=[],
                notes_for_coding_agent=[]
            )
        )


class TestReviewerRegistryBasics:
    """Test basic registry functionality and parity with original behavior."""

    def test_get_core_reviewers_returns_six_agents(self):
        """Verify get_core_reviewers returns 6 agents (parity with original)."""
        core_reviewers = ReviewerRegistry.get_core_reviewers()
        assert len(core_reviewers) == 6
        assert all(isinstance(r, BaseReviewerAgent) for r in core_reviewers)

    def test_get_all_reviewers_returns_eleven_agents(self):
        """Verify get_all_reviewers returns 11 agents (parity with original)."""
        all_reviewers = ReviewerRegistry.get_all_reviewers()
        assert len(all_reviewers) == 11
        assert all(isinstance(r, BaseReviewerAgent) for r in all_reviewers)

    def test_get_all_names_contains_all_expected_agents(self):
        """Verify registry contains all expected agent names."""
        all_names = ReviewerRegistry.get_all_names()
        expected_names = [
            "architecture",
            "security",
            "documentation",
            "telemetry",
            "linting",
            "unit_tests",
            "diff_scoper",
            "requirements",
            "performance",
            "dependencies",
            "changelog",
        ]
        assert sorted(all_names) == sorted(expected_names)

    def test_get_core_names_contains_only_core_agents(self):
        """Verify core names only contain core agents."""
        core_names = ReviewerRegistry.get_core_names()
        expected_core = [
            "architecture",
            "security",
            "documentation",
            "telemetry",
            "linting",
            "unit_tests",
        ]
        assert sorted(core_names) == sorted(expected_core)
        assert len(core_names) == 6

    def test_get_optional_names_contains_only_optional_agents(self):
        """Verify optional names only contain optional agents."""
        optional_names = ReviewerRegistry.get_optional_names()
        expected_optional = [
            "diff_scoper",
            "requirements",
            "performance",
            "dependencies",
            "changelog",
        ]
        assert sorted(optional_names) == sorted(expected_optional)
        assert len(optional_names) == 5


class TestReviewerRegistryKnownAgents:
    """Test creating reviewers by known names (parity with original AGENT_MAP)."""

    def test_create_reviewer_architecture(self):
        """Verify architecture reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("architecture")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "architecture"

    def test_create_reviewer_security(self):
        """Verify security reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("security")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "security"

    def test_create_reviewer_documentation(self):
        """Verify documentation reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("documentation")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "documentation"

    def test_create_reviewer_telemetry(self):
        """Verify telemetry reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("telemetry")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "telemetry"

    def test_create_reviewer_linting(self):
        """Verify linting reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("linting")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "linting"

    def test_create_reviewer_unit_tests(self):
        """Verify unit_tests reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("unit_tests")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "unit_tests"

    def test_create_reviewer_diff_scoper(self):
        """Verify diff_scoper reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("diff_scoper")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "diff_scoper"

    def test_create_reviewer_requirements(self):
        """Verify requirements reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("requirements")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "requirements"

    def test_create_reviewer_performance(self):
        """Verify performance reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("performance")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "performance"

    def test_create_reviewer_dependencies(self):
        """Verify dependencies reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("dependencies")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "dependencies"

    def test_create_reviewer_changelog(self):
        """Verify changelog reviewer can be created."""
        reviewer = ReviewerRegistry.create_reviewer("changelog")
        assert isinstance(reviewer, BaseReviewerAgent)
        assert reviewer.get_agent_name() == "release_changelog"


class TestReviewerRegistryUnknownAgents:
    """Test unknown agent handling (negative path)."""

    def test_get_reviewer_unknown_name_raises_keyerror(self):
        """Verify get_reviewer raises KeyError for unknown name."""
        with pytest.raises(KeyError) as exc_info:
            ReviewerRegistry.get_reviewer("unknown_agent")

        error_msg = str(exc_info.value)
        assert "Unknown reviewer" in error_msg
        assert "unknown_agent" in error_msg
        assert "Available reviewers" in error_msg

    def test_create_reviewer_unknown_name_raises_keyerror(self):
        """Verify create_reviewer raises KeyError for unknown name."""
        with pytest.raises(KeyError) as exc_info:
            ReviewerRegistry.create_reviewer("unknown_agent")

        error_msg = str(exc_info.value)
        assert "Unknown reviewer" in error_msg
        assert "unknown_agent" in error_msg

    def test_error_message_lists_available_reviewers(self):
        """Verify error message includes list of available reviewers."""
        with pytest.raises(KeyError) as exc_info:
            ReviewerRegistry.get_reviewer("unknown_agent")

        error_msg = str(exc_info.value)
        for name in ReviewerRegistry.get_all_names():
            assert name in error_msg


class TestReviewerRegistryCustomRegistration:
    """Test custom reviewer registration (extension seam)."""

    def test_register_custom_reviewer(self):
        """Verify custom reviewer can be registered."""
        ReviewerRegistry.register("custom", MockCustomReviewer, is_core=False)

        reviewer = ReviewerRegistry.create_reviewer("custom")
        assert isinstance(reviewer, MockCustomReviewer)

        all_names = ReviewerRegistry.get_all_names()
        assert "custom" in all_names

    def test_register_duplicate_name_raises_value_error(self):
        """Verify registering duplicate name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ReviewerRegistry.register("security", MockCustomReviewer)

        error_msg = str(exc_info.value)
        assert "already registered" in error_msg
        assert "security" in error_msg

    def test_registered_custom_reviewer_in_all_names(self):
        """Verify custom reviewer name appears in get_all_names() if registered."""
        ReviewerRegistry.register("custom2", MockCustomReviewer, is_core=True)

        all_names = ReviewerRegistry.get_all_names()
        assert "custom2" in all_names

    def test_registered_custom_reviewer_in_core_names_if_core(self):
        """Verify custom reviewer name appears in get_core_names() if is_core=True."""
        ReviewerRegistry.register("custom3", MockCustomReviewer, is_core=True)

        core_names = ReviewerRegistry.get_core_names()
        assert "custom3" in core_names
