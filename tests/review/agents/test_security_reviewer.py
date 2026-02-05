"""Test SecurityReviewer agent with LLM-based analysis."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from opencode_python.agents.review.agents.security import SecurityReviewer
from opencode_python.agents.review.base import ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate
from opencode_python.core.models import Session


class TestSecurityReviewerLLMBased:
    """Test SecurityReviewer with LLM-based analysis."""

    @pytest.fixture
    def reviewer(self):
        """Create a SecurityReviewer instance."""
        return SecurityReviewer()

    @pytest.fixture
    def sample_context(self):
        """Create a sample review context."""
        return ReviewContext(
            changed_files=["src/auth.py", "config/api.yaml"],
            diff="+ api_key = 'sk-1234567890abcdef'\n+ password = 'secret123'",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/add-auth"
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
        """Sample valid LLM response JSON."""
        return """{
            "agent": "security",
            "summary": "Found 1 security issue(s).",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/auth.py", "config/api.yaml"],
                "ignored_files": [],
                "reasoning": "Security review analyzed 2 relevant files for secrets, injection risks, and auth issues."
            },
            "findings": [
                {
                    "id": "secret-1",
                    "title": "API key exposed",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "security",
                    "estimate": "S",
                    "evidence": "Line 1: + api_key = 'sk-1234567890abcdef'",
                    "risk": "Exposed credentials can be used to compromise systems and data.",
                    "recommendation": "Remove secrets from code and use environment variables or secret managers.",
                    "suggested_patch": "Replace hardcoded secret with os.getenv('API_KEY')"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": [],
                "should_fix": ["secret-1"],
                "notes_for_coding_agent": [
                    "Ensure all secrets are stored in environment variables or secret managers."
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

        with patch('opencode_python.agents.review.agents.security.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.security.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                mock_ai_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()
                process_args = mock_ai_session.process_message.call_args
                assert "system_prompt" in process_args[1].get('options', {}) or \
                       sample_context.diff in process_args[0][0]

                # Verify result is valid ReviewOutput
                assert isinstance(result, ReviewOutput)
                assert result.agent == "security"
                assert result.severity == "critical"
                assert len(result.findings) == 1
                assert result.findings[0].id == "secret-1"
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
        with patch('opencode_python.agents.review.agents.security.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.security.Session') as mock_session_cls:
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
        with patch('opencode_python.agents.review.agents.security.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.security.Session') as mock_session_cls:
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
        with patch('opencode_python.agents.review.agents.security.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.security.Session') as mock_session_cls:
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
            "agent": "security",
            "summary": "No security vulnerabilities detected.",
            "severity": "merge",
            "scope": {
                "relevant_files": ["src/auth.py"],
                "ignored_files": [],
                "reasoning": "Security review analyzed 1 relevant file."
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
        with patch('opencode_python.agents.review.agents.security.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.security.Session') as mock_session_cls:
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
        with patch('opencode_python.agents.review.agents.security.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.security.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                await reviewer.review(sample_context)

                # Verify message includes context
                assert captured_message is not None
                assert "## Review Context" in captured_message
                assert "src/auth.py" in captured_message
                assert sample_context.diff in captured_message
