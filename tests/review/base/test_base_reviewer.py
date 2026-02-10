"""Test BaseReviewerAgent abstract class and its utility methods."""

import pytest
from abc import ABC, abstractmethod
from dawn_kestrel.agents.review.base import BaseReviewerAgent, ReviewContext


class MockReviewerAgent(BaseReviewerAgent):
    """Mock agent for testing BaseReviewerAgent."""

    def get_system_prompt(self) -> str:
        """Get the system prompt for the mock reviewer."""
        return "Test system prompt"

    def get_agent_name(self) -> str:
        """Get the agent name for the mock reviewer."""
        return "MockReviewerAgent"

    def get_allowed_tools(self) -> list[str]:
        """Get allowed tools for the mock reviewer."""
        return []

    def get_relevant_file_patterns(self) -> list[str]:
        """Get file patterns relevant to the mock reviewer."""
        return ["*.py", "tests/**"]

    async def review(self, context: ReviewContext) -> object:  # type: ignore
        """Perform review on the given context."""
        return None  # type: ignore


class MockReviewerWithNoPatterns(BaseReviewerAgent):
    """Mock agent with no file patterns."""

    def get_system_prompt(self) -> str:
        """Get the system prompt for the mock reviewer."""
        return "Test system prompt"

    def get_agent_name(self) -> str:
        """Get the agent name for the mock reviewer."""
        return "MockReviewerWithNoPatterns"

    def get_allowed_tools(self) -> list[str]:
        """Get allowed tools for the mock reviewer."""
        return []

    def get_relevant_file_patterns(self) -> list[str]:
        """Get file patterns relevant to the mock reviewer."""
        return []

    async def review(self, context: ReviewContext) -> object:  # type: ignore
        """Perform review on the given context."""
        return None  # type: ignore


class TestBaseReviewerAgentAbstract:
    """Test that BaseReviewerAgent is properly abstract."""

    def test_base_reviewer_agent_is_abstract(self):
        """Test that BaseReviewerAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseReviewerAgent()

    def test_base_reviewer_agent_requires_abstract_methods(self):
        """Test that BaseReviewerAgent has required abstract methods."""
        # Verify abstract methods exist
        assert hasattr(BaseReviewerAgent, "review")
        assert hasattr(BaseReviewerAgent, "get_system_prompt")
        assert hasattr(BaseReviewerAgent, "get_relevant_file_patterns")

        # Verify they are abstract
        # This is tested by attempting to instantiate BaseReviewerAgent directly
        # which should raise TypeError


class TestIsRelevantToChanges:
    """Test the is_relevant_to_changes utility method."""

    def test_is_relevant_to_changes_with_matching_pattern(self):
        """Test that is_relevant_to_changes returns True when files match patterns."""
        agent = MockReviewerAgent()
        changed_files = ["src/main.py", "tests/test_utils.py"]

        result = agent.is_relevant_to_changes(changed_files)

        assert result is True

    def test_is_relevant_to_changes_with_no_matching_pattern(self):
        """Test that is_relevant_to_changes returns False when no files match patterns."""
        agent = MockReviewerAgent()
        changed_files = ["docs/api.md", "README.md"]

        result = agent.is_relevant_to_changes(changed_files)

        assert result is False

    def test_is_relevant_to_changes_with_empty_patterns(self):
        """Test that is_relevant_to_changes returns False when agent has no patterns."""
        agent = MockReviewerWithNoPatterns()
        changed_files = ["src/main.py", "tests/test_utils.py"]

        result = agent.is_relevant_to_changes(changed_files)

        assert result is False

    def test_is_relevant_to_changes_with_multiple_patterns(self):
        """Test that is_relevant_to_changes returns True when any pattern matches."""
        agent = MockReviewerAgent()
        changed_files = ["src/main.py", "config.yaml"]

        result = agent.is_relevant_to_changes(changed_files)

        assert result is True

    def test_is_relevant_to_changes_with_special_glob_patterns(self):
        """Test that is_relevant_to_changes works with special glob patterns like **."""
        agent = MockReviewerAgent()
        changed_files = ["src/auth/auth.py", "src/auth/utils/auth_helpers.py"]

        result = agent.is_relevant_to_changes(changed_files)

        assert result is True

    def test_is_relevant_to_changes_with_nested_path(self):
        """Test that is_relevant_to_changes works with deeply nested paths."""
        agent = MockReviewerAgent()
        changed_files = ["tests/unit/services/auth_service_test.py"]

        result = agent.is_relevant_to_changes(changed_files)

        assert result is True

    def test_is_relevant_to_changes_with_single_file(self):
        """Test that is_relevant_to_changes works with a single file."""
        agent = MockReviewerAgent()
        changed_files = ["src/main.py"]

        result = agent.is_relevant_to_changes(changed_files)

        assert result is True

    def test_is_relevant_to_changes_with_case_sensitive_paths(self):
        """Test that is_relevant_to_changes is case-sensitive for nested paths."""
        agent = MockReviewerAgent()
        changed_files = ["src/Main.py", "src/main.py"]

        result = agent.is_relevant_to_changes(["src/Main.py"])

        assert result is True

    def test_is_relevant_to_changes_with_complex_pattern(self):
        """Test that is_relevant_to_changes handles complex patterns correctly."""
        agent = MockReviewerAgent()
        changed_files = ["src/auth/api.py", "src/auth/middleware/auth_middleware.py"]

        result = agent.is_relevant_to_changes(changed_files)

        assert result is True

    def test_is_relevant_to_changes_with_ignored_files(self):
        """Test that is_relevant_to_changes only matches relevant patterns."""
        agent = MockReviewerAgent()
        changed_files = ["README.md", "docs/api.md"]

        result = agent.is_relevant_to_changes(changed_files)

        assert result is False


class TestFormatInputsForPrompt:
    """Test the format_inputs_for_prompt utility method."""

    def test_format_inputs_for_prompt_basic(self):
        """Test that format_inputs_for_prompt generates formatted context."""
        agent = MockReviewerAgent()
        context = ReviewContext(
            changed_files=["src/main.py"],
            diff="+ def foo():\n+     return 'hello'",
            repo_root="/repo",
            base_ref="main",
            head_ref="feature/test",
        )

        result = agent.format_inputs_for_prompt(context)

        assert "## Review Context" in result
        assert "src/main.py" in result
        assert "Repository Root" in result
        assert "Git Diff" in result
        assert "Diff Content" in result
        assert "Base Ref" in result
        assert "Head Ref" in result

    def test_format_inputs_for_prompt_without_git_refs(self):
        """Test that format_inputs_for_prompt works without git refs."""
        agent = MockReviewerAgent()
        context = ReviewContext(
            changed_files=["src/main.py"],
            diff="+ def foo():\n+     return 'hello'",
            repo_root="/repo",
        )

        result = agent.format_inputs_for_prompt(context)

        assert "## Review Context" in result
        assert "src/main.py" in result
        assert "Repository Root" in result
        # Should not have Git Diff section
        assert "Git Diff" not in result

    def test_format_inputs_for_prompt_with_pr_info(self):
        """Test that format_inputs_for_prompt includes PR info when available."""
        agent = MockReviewerAgent()
        context = ReviewContext(
            changed_files=["src/main.py"],
            diff="+ def foo():\n+     return 'hello'",
            repo_root="/repo",
            pr_title="Test PR",
            pr_description="This is a test PR",
        )

        result = agent.format_inputs_for_prompt(context)

        assert "## Review Context" in result
        assert "src/main.py" in result
        assert "Pull Request" in result
        assert "Test PR" in result
        assert "This is a test PR" in result

    def test_format_inputs_for_prompt_multiline_diff(self):
        """Test that format_inputs_for_prompt handles multiline diff correctly."""
        agent = MockReviewerAgent()
        context = ReviewContext(
            changed_files=["src/main.py"],
            diff="+ def foo():\n+     return 'hello'\n+ def bar():\n+     return 'world'",
            repo_root="/repo",
        )

        result = agent.format_inputs_for_prompt(context)

        assert "```diff" in result
        assert "+ def foo():" in result
        assert "+ def bar():" in result
        assert "```" in result

    def test_format_inputs_for_prompt_multiple_files(self):
        """Test that format_inputs_for_prompt handles multiple changed files."""
        agent = MockReviewerAgent()
        context = ReviewContext(
            changed_files=["src/main.py", "src/utils.py", "tests/test_main.py"],
            diff="+ def foo():\n+     return 'hello'",
            repo_root="/repo",
        )

        result = agent.format_inputs_for_prompt(context)

        assert "src/main.py" in result
        assert "src/utils.py" in result
        assert "tests/test_main.py" in result

    def test_format_inputs_for_prompt_empty_list(self):
        """Test that format_inputs_for_prompt handles empty changed files list."""
        agent = MockReviewerAgent()
        context = ReviewContext(
            changed_files=[], diff="+ def foo():\n+     return 'hello'", repo_root="/repo"
        )

        result = agent.format_inputs_for_prompt(context)

        assert "## Review Context" in result
        assert "### Changed Files" in result
        # Changed files section should exist but be empty

    def test_format_inputs_for_prompt_no_diff(self):
        """Test that format_inputs_for_prompt handles case with no diff."""
        agent = MockReviewerAgent()
        context = ReviewContext(changed_files=["src/main.py"], diff="", repo_root="/repo")

        result = agent.format_inputs_for_prompt(context)

        assert "## Review Context" in result
        assert "### Diff Content" in result
        assert result.count("```diff") == 1  # Only one code block

    def test_format_inputs_for_prompt_code_block_format(self):
        """Test that format_inputs_for_prompt uses proper markdown code block formatting."""
        agent = MockReviewerAgent()
        context = ReviewContext(
            changed_files=["src/main.py"],
            diff="+ def foo():\n+     return 'hello'",
            repo_root="/repo",
        )

        result = agent.format_inputs_for_prompt(context)

        # Should have opening and closing code block markers
        assert "```diff" in result
        assert "```" in result
        lines = result.split("\n")
        diff_start_idx = None
        diff_end_idx = None

        for i, line in enumerate(lines):
            if line.strip() == "```diff":
                diff_start_idx = i
            if line.strip() == "```" and diff_start_idx is not None:
                diff_end_idx = i
                break

        assert diff_start_idx is not None
        assert diff_end_idx is not None
        assert diff_end_idx > diff_start_idx

    def test_format_inputs_for_prompt_leading_trailing_whitespace(self):
        """Test that format_inputs_for_prompt doesn't have excessive whitespace."""
        agent = MockReviewerAgent()
        context = ReviewContext(
            changed_files=["src/main.py"],
            diff="+ def foo():\n+     return 'hello'",
            repo_root="/repo",
        )

        result = agent.format_inputs_for_prompt(context)

        cleaned = result.rstrip()
        lines = cleaned.split("\n")

        assert lines[-1] != ""
        for i, line in enumerate(lines):
            if i > 0:
                assert not line.startswith(" ")


class TestReviewContext:
    """Test the ReviewContext data model."""

    def test_review_context_creation(self):
        """Test that ReviewContext can be created successfully."""
        context = ReviewContext(
            changed_files=["src/main.py"],
            diff="+ def foo():\n+     return 'hello'",
            repo_root="/repo",
        )

        assert context.changed_files == ["src/main.py"]
        assert context.diff == "+ def foo():\n+     return 'hello'"
        assert context.repo_root == "/repo"

    def test_review_context_with_optional_fields(self):
        """Test that ReviewContext works with optional fields."""
        context = ReviewContext(
            changed_files=["src/main.py"],
            diff="+ def foo():\n+     return 'hello'",
            repo_root="/repo",
            base_ref="main",
            head_ref="feature/test",
            pr_title="Test PR",
            pr_description="This is a test PR",
        )

        assert context.base_ref == "main"
        assert context.head_ref == "feature/test"
        assert context.pr_title == "Test PR"
        assert context.pr_description == "This is a test PR"

    def test_review_context_empty_optional_fields(self):
        """Test that ReviewContext works with None for optional fields."""
        context = ReviewContext(
            changed_files=["src/main.py"],
            diff="+ def foo():\n+     return 'hello'",
            repo_root="/repo",
        )

        assert context.base_ref is None
        assert context.head_ref is None
        assert context.pr_title is None
        assert context.pr_description is None

    def test_review_context_extra_forbidden(self):
        """Test that ReviewContext raises error on extra fields."""
        with pytest.raises(ValueError):
            ReviewContext(
                changed_files=["src/main.py"],
                diff="+ def foo():\n+     return 'hello'",
                repo_root="/repo",
                extra_field="should raise error",
            )
