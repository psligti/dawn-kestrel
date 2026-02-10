"""Tests for BaseReviewerAgent abstract base class using TDD approach."""

import pytest
from abc import ABC, abstractmethod
from typing import List
from pydantic import ValidationError

from dawn_kestrel.agents.review.base import BaseReviewerAgent, ReviewContext
from dawn_kestrel.agents.review.contracts import ReviewOutput, Scope, MergeGate


class TestReviewContext:
    """Test ReviewContext model validation."""

    def test_review_context_minimal(self):
        """Test ReviewContext with minimal fields."""
        context = ReviewContext(
            changed_files=["src/main.py", "tests/test_main.py"],
            diff="diff --git a/src/main.py b/src/main.py",
            repo_root="/path/to/repo",
        )
        assert context.changed_files == ["src/main.py", "tests/test_main.py"]
        assert context.diff == "diff --git a/src/main.py b/src/main.py"
        assert context.repo_root == "/path/to/repo"

    def test_review_context_with_optional_fields(self):
        """Test ReviewContext with optional fields."""
        context = ReviewContext(
            changed_files=["src/auth.py"],
            diff="+ def authenticate():",
            repo_root="/repo",
            base_ref="main",
            head_ref="feature/auth",
            pr_title="Add authentication",
            pr_description="Implement OAuth flow",
        )
        assert context.base_ref == "main"
        assert context.head_ref == "feature/auth"
        assert context.pr_title == "Add authentication"
        assert context.pr_description == "Implement OAuth flow"


class TestBaseReviewerAgent:
    """Test BaseReviewerAgent abstract class."""

    def test_base_reviewer_agent_is_abstract(self):
        """Test BaseReviewerAgent is an abstract base class."""
        assert issubclass(BaseReviewerAgent, ABC)

    def test_cannot_instantiate_base_class_directly(self):
        """Test BaseReviewerAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseReviewerAgent()

    def test_required_abstract_methods_exist(self):
        """Test all required abstract methods are defined."""
        import inspect

        abstract_methods = [
            name
            for name, obj in inspect.getmembers(BaseReviewerAgent)
            if getattr(obj, "__isabstractmethod__", False)
        ]
        required = {"review", "get_system_prompt", "get_relevant_file_patterns"}
        assert required.issubset(set(abstract_methods))

    def test_concrete_subclass_implementation(self):
        """Test a concrete subclass can be created and instantiated."""

        class ConcreteReviewer(BaseReviewerAgent):
            """Concrete implementation for testing."""

            def get_agent_name(self) -> str:
                return "ConcreteReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

            def get_system_prompt(self) -> str:
                return "You are a code reviewer."

            def get_relevant_file_patterns(self) -> List[str]:
                return ["*.py"]

            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="concrete-reviewer",
                    summary="No issues found",
                    severity="merge",
                    scope=Scope(
                        relevant_files=context.changed_files,
                        ignored_files=[],
                        reasoning="Testing concrete implementation",
                    ),
                    checks=[],
                    skips=[],
                    findings=[],
                    merge_gate=MergeGate(
                        decision="approve",
                        must_fix=[],
                        should_fix=[],
                        notes_for_coding_agent=["LGTM"],
                    ),
                )

        # Can instantiate
        reviewer = ConcreteReviewer()
        assert isinstance(reviewer, BaseReviewerAgent)

        # Has required methods
        assert hasattr(reviewer, "review")
        assert hasattr(reviewer, "get_system_prompt")
        assert hasattr(reviewer, "get_relevant_file_patterns")

        # Methods work
        prompt = reviewer.get_system_prompt()
        assert prompt == "You are a code reviewer."

        patterns = reviewer.get_relevant_file_patterns()
        assert patterns == ["*.py"]

    def test_is_relevant_to_changes_with_match(self):
        """Test is_relevant_to_changes returns True when files match patterns."""

        class TestReviewer(BaseReviewerAgent):
            def get_agent_name(self) -> str:
                return "TestReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self) -> List[str]:
                return ["src/**/*.py", "tests/**/*.py"]

            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="test",
                    summary="test",
                    severity="merge",
                    scope=Scope(relevant_files=[], reasoning="test"),
                    checks=[],
                    skips=[],
                    findings=[],
                    merge_gate=MergeGate(
                        decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                    ),
                )

        reviewer = TestReviewer()
        changed_files = ["src/main.py", "tests/test_main.py", "README.md"]
        assert reviewer.is_relevant_to_changes(changed_files) is True

    def test_is_relevant_to_changes_no_match(self):
        """Test is_relevant_to_changes returns False when no files match patterns."""

        class TestReviewer(BaseReviewerAgent):
            def get_agent_name(self) -> str:
                return "TestReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self) -> List[str]:
                return ["src/**/*.py"]

            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="test",
                    summary="test",
                    severity="merge",
                    scope=Scope(relevant_files=[], reasoning="test"),
                    checks=[],
                    skips=[],
                    findings=[],
                    merge_gate=MergeGate(
                        decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                    ),
                )

        reviewer = TestReviewer()
        changed_files = ["README.md", "docs/api.md"]
        assert reviewer.is_relevant_to_changes(changed_files) is False

    def test_is_relevant_to_changes_empty_patterns(self):
        """Test is_relevant_to_changes returns False when no patterns defined."""

        class TestReviewer(BaseReviewerAgent):
            def get_agent_name(self) -> str:
                return "TestReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self) -> List[str]:
                return []

            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="test",
                    summary="test",
                    severity="merge",
                    scope=Scope(relevant_files=[], reasoning="test"),
                    checks=[],
                    skips=[],
                    findings=[],
                    merge_gate=MergeGate(
                        decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                    ),
                )

        reviewer = TestReviewer()
        changed_files = ["src/main.py"]
        assert reviewer.is_relevant_to_changes(changed_files) is False

    def test_format_inputs_for_prompt(self):
        """Test format_inputs_for_prompt formats context for prompt."""

        class TestReviewer(BaseReviewerAgent):
            def get_agent_name(self) -> str:
                return "TestReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self) -> List[str]:
                return ["*.py"]

            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="test",
                    summary="test",
                    severity="merge",
                    scope=Scope(relevant_files=[], reasoning="test"),
                    checks=[],
                    skips=[],
                    findings=[],
                    merge_gate=MergeGate(
                        decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                    ),
                )

        reviewer = TestReviewer()
        context = ReviewContext(
            changed_files=["src/main.py", "tests/test.py"],
            diff="+ def new_function():",
            repo_root="/repo",
            pr_title="Add new feature",
            pr_description="Implements X",
        )

        formatted = reviewer.format_inputs_for_prompt(context)
        assert "src/main.py" in formatted
        assert "tests/test.py" in formatted
        assert "new_function" in formatted
        assert "Add new feature" in formatted
        assert "Implements X" in formatted

    def test_format_inputs_for_prompt_minimal_context(self):
        """Test format_inputs_for_prompt with minimal context."""

        class TestReviewer(BaseReviewerAgent):
            def get_agent_name(self) -> str:
                return "TestReviewer"

            def get_allowed_tools(self) -> List[str]:
                return []

            def get_system_prompt(self) -> str:
                return "Test"

            def get_relevant_file_patterns(self) -> List[str]:
                return ["*.py"]

            async def review(self, context: ReviewContext) -> ReviewOutput:
                return ReviewOutput(
                    agent="test",
                    summary="test",
                    severity="merge",
                    scope=Scope(relevant_files=[], reasoning="test"),
                    checks=[],
                    skips=[],
                    findings=[],
                    merge_gate=MergeGate(
                        decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                    ),
                )

        reviewer = TestReviewer()
        context = ReviewContext(
            changed_files=["src/main.py"], diff="+ line1\n+ line2", repo_root="/repo"
        )

        formatted = reviewer.format_inputs_for_prompt(context)
        assert "src/main.py" in formatted
        assert "line1" in formatted
        assert "line2" in formatted
