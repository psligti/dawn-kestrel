"""Tests for LintingReviewer - LLM-based analysis."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from opencode_python.agents.review.agents.linting import LintingReviewer
from opencode_python.agents.review.base import ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate
from opencode_python.core.models import Session


class TestLintingReviewerLLMBased:
    """Test LintingReviewer with LLM-based analysis."""

    @pytest.fixture
    def reviewer(self):
        """Create a LintingReviewer instance."""
        return LintingReviewer()

    @pytest.fixture
    def sample_context(self):
        """Create a sample review context."""
        return ReviewContext(
            changed_files=["src/app.py", "pyproject.toml"],
            diff="+ def my_function(x):\n+     return x * 2\n+ print('hello')",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/add-function"
        )

    @pytest.fixture
    def mock_session(self):
        """Create a mock Session object."""
        return Session(
            id="test-session-id",
            slug="test-session",
            project_id="test-project",
            directory="/test/repo",
            title="Test Session",
            version="1.0"
        )

    @pytest.fixture
    def sample_review_output_json(self):
        """Sample valid LLM response JSON for linting issues."""
        return """{
            "agent": "linting",
            "summary": "Linting review complete. Found 2 total issues: - 1 critical/blocking issues - 1 warnings",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/app.py", "pyproject.toml"],
                "ignored_files": [],
                "reasoning": "Linting and formatting review for Python files and lint configs"
            },
            "findings": [
                {
                    "id": "lint-1",
                    "title": "Line too long (E501)",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "S",
                    "evidence": "File: src/app.py | Line: 120 | Column: 100 | Message: Line too long (120 > 88 characters)",
                    "risk": "Long lines reduce readability and may break in some tools",
                    "recommendation": "Break long line to adhere to line length limit"
                },
                {
                    "id": "lint-2",
                    "title": "Missing return type annotation",
                    "severity": "warning",
                    "confidence": "medium",
                    "owner": "dev",
                    "estimate": "S",
                    "evidence": "File: src/app.py | Function: my_function lacks return type annotation",
                    "risk": "Missing type hints reduce code maintainability and type safety",
                    "recommendation": "Add return type annotation to function 'my_function'"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["lint-1"],
                "should_fix": ["lint-2"],
                "notes_for_coding_agent": [
                    "Found 1 critical linting issues that must be fixed:",
                    "  - Line too long (E501)",
                    "Found 1 style warnings that should be fixed:",
                    "  - Missing return type annotation",
                    "Run 'ruff check --fix' to auto-fix many issues",
                    "Run 'ruff format' to fix formatting issues",
                    "Consider adding type hints to improve code maintainability"
                ]
            }
        }"""

    @pytest.mark.asyncio
    async def test_review_creates_ai_session_and_calls_process_message(
        self,
        reviewer,
        sample_context,
        mock_session,
        sample_review_output_json
    ):
        """Test that review() creates AISession and calls process_message()."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = sample_review_output_json

        mock_ai_session.process_message = AsyncMock(return_value=mock_message)
                
        with patch('opencode_python.agents.review.agents.linting.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.linting.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                mock_ai_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()

                # Verify result is valid ReviewOutput
                assert isinstance(result, ReviewOutput)
                assert result.agent == "linting"
                assert result.severity == "critical"
                assert len(result.findings) == 2
                assert result.findings[0].id == "lint-1"
                assert result.merge_gate.decision == "needs_changes"

    @pytest.mark.asyncio
    async def test_review_handles_missing_api_key_by_raising_exception(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() raises exception when API key is missing."""
        # Mock AISession to raise exception
        mock_ai_session = MagicMock()

        async def mock_process_message(user_message, options=None):
            raise ValueError("API key not found for provider")

        mock_ai_session.process_message = mock_process_message

        # Patch AISession
        with patch('opencode_python.agents.review.agents.linting.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.linting.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                # Should raise exception
                with pytest.raises(ValueError, match="API key"):
                    await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_handles_invalid_json_response(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() returns error ReviewOutput for invalid JSON."""
        # Mock AISession to return invalid JSON
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = "This is not valid JSON"

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        # Patch AISession
        with patch('opencode_python.agents.review.agents.linting.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.linting.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                # Should return error ReviewOutput with severity='critical'
                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "critical"
                assert "error" in result.summary.lower() or "invalid" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_review_handles_timeout_error_by_raising_exception(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() raises exception on timeout."""
        # Mock AISession to raise timeout
        mock_ai_session = MagicMock()

        async def mock_process_message(user_message, options=None):
            raise TimeoutError("Request timed out after 60s")

        mock_ai_session.process_message = mock_process_message

        # Patch AISession
        with patch('opencode_python.agents.review.agents.linting.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.linting.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                # Should raise exception
                with pytest.raises(TimeoutError):
                    await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_with_no_findings_returns_merge_severity(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() returns severity='merge' when no findings."""
        # Mock AISession to return clean review
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = """{
            "agent": "linting",
            "summary": "Linting review complete. No issues found.",
            "severity": "merge",
            "scope": {
                "relevant_files": ["src/app.py", "pyproject.toml"],
                "ignored_files": [],
                "reasoning": "Linting and formatting review for Python files and lint configs"
            },
            "findings": [],
            "merge_gate": {
                "decision": "approve",
                "must_fix": [],
                "should_fix": [],
                "notes_for_coding_agent": []
            }
        }"""

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        # Patch AISession
        with patch('opencode_python.agents.review.agents.linting.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.linting.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "merge"
                assert result.merge_gate.decision == "approve"
                assert len(result.findings) == 0

    @pytest.mark.asyncio
    async def test_review_includes_system_prompt_and_context_in_message(
        self,
        reviewer,
        sample_context,
        mock_session,
        sample_review_output_json
    ):
        """Test that review() includes system prompt and formatted context."""
        # Mock AISession
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = sample_review_output_json

        captured_message = None

        async def mock_process_message(user_message, options=None):
            nonlocal captured_message
            captured_message = user_message
            return mock_message

        mock_ai_session.process_message = mock_process_message

        # Patch AISession
        with patch('opencode_python.agents.review.agents.linting.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.linting.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                await reviewer.review(sample_context)

                # Verify message includes context
                assert captured_message is not None
                assert "## Review Context" in captured_message
                assert "src/app.py" in captured_message
                assert sample_context.diff in captured_message

    @pytest.mark.asyncio
    async def test_review_with_non_relevant_files_returns_merge(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() returns merge decision for non-relevant files."""
        # Create context with non-relevant files
        context_no_relevant = ReviewContext(
            changed_files=["README.md"],
            diff="+ documentation update",
            repo_root="/test/repo",
        )

        # For non-relevant files, the agent should return early without calling LLM
        result = await reviewer.review(context_no_relevant)

        assert isinstance(result, ReviewOutput)
        assert result.severity == "merge"
        assert result.merge_gate.decision == "approve"
        assert "No Python or lint config files changed" in result.summary

    def test_linting_reviewer_metadata_helpers(self, reviewer):
        """Test that metadata helper methods still work."""
        assert reviewer.get_agent_name() == "linting"
        assert "Linting & Style Review Subagent" in reviewer.get_system_prompt()
        assert any("*.py" in pattern for pattern in reviewer.get_relevant_file_patterns())
