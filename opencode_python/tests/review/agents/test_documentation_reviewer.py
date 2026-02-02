"""Test DocumentationReviewer agent with LLM-based analysis."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from opencode_python.agents.review.agents.documentation import DocumentationReviewer
from opencode_python.agents.review.base import ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate
from opencode_python.core.models import Session


class TestDocumentationReviewerLLMBased:
    """Test DocumentationReviewer with LLM-based analysis."""

    @pytest.fixture
    def reviewer(self):
        """Create a DocumentationReviewer instance."""
        return DocumentationReviewer()

    @pytest.fixture
    def sample_context(self):
        """Create a sample review context."""
        return ReviewContext(
            changed_files=["src/module.py", "README.md"],
            diff="+ class Foo:\n+     def bar(self):\n+         return 1\n",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/add-foo"
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
        """Sample valid LLM response JSON for documentation review."""
        return """{
            "agent": "documentation",
            "summary": "Found 2 documentation issue(s).",
            "severity": "warning",
            "scope": {
                "relevant_files": ["src/module.py", "README.md"],
                "ignored_files": [],
                "reasoning": "Documentation review analyzed 2 relevant files for docstrings and README consistency."
            },
            "findings": [
                {
                    "id": "doc-missing-class-Foo-10",
                    "title": "Public class 'Foo' lacks docstring",
                    "severity": "warning",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "File: src/module.py:10 - Class 'Foo' is public but has no docstring. Has 1 public methods.",
                    "risk": "Users may not understand the class's purpose or how to use it",
                    "recommendation": "Add docstring to class 'Foo' describing its purpose and usage"
                },
                {
                    "id": "doc-missing-readme-update",
                    "title": "README does not document new class 'Foo'",
                    "severity": "warning",
                    "confidence": "medium",
                    "owner": "docs",
                    "estimate": "M",
                    "evidence": "Class 'Foo' added to src/module.py but no corresponding documentation found in README.md",
                    "risk": "Users may not be aware of the new public API",
                    "recommendation": "Document the 'Foo' class in README.md with usage examples"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": [],
                "should_fix": ["doc-missing-class-Foo-10", "doc-missing-readme-update"],
                "notes_for_coding_agent": [
                    "Add docstrings to public functions/classes",
                    "Document configuration changes in README.md",
                    "Update usage examples for new features"
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

        with patch('opencode_python.agents.review.agents.documentation.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.documentation.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                mock_ai_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()
                process_args = mock_ai_session.process_message.call_args
                assert "system_prompt" in process_args[1].get('options', {}) or \
                       sample_context.diff in process_args[0][0]

                # Verify result is valid ReviewOutput
                assert isinstance(result, ReviewOutput)
                assert result.agent == "documentation"
                assert result.severity == "warning"
                assert len(result.findings) == 2
                assert result.findings[0].id == "doc-missing-class-Foo-10"
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
        with patch('opencode_python.agents.review.agents.documentation.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.documentation.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                # Should raise exception
                with pytest.raises(ValueError, match="API key not found"):
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
        with patch('opencode_python.agents.review.agents.documentation.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.documentation.Session') as mock_session_cls:
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
        with patch('opencode_python.agents.review.agents.documentation.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.documentation.Session') as mock_session_cls:
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
            "agent": "documentation",
            "summary": "Documentation review passed. All public functions/classes have docstrings.",
            "severity": "merge",
            "scope": {
                "relevant_files": ["src/module.py"],
                "ignored_files": [],
                "reasoning": "Documentation review analyzed 1 relevant file for docstrings and README consistency."
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
        with patch('opencode_python.agents.review.agents.documentation.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.documentation.Session') as mock_session_cls:
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
        with patch('opencode_python.agents.review.agents.documentation.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.documentation.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                await reviewer.review(sample_context)

                # Verify message includes context
                assert captured_message is not None
                assert "## Review Context" in captured_message
                assert "src/module.py" in captured_message
                assert sample_context.diff in captured_message
