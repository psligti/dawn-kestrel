"""Tests for RequirementsReviewer - LLM-based analysis."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from opencode_python.agents.review.agents.requirements import RequirementsReviewer
from opencode_python.agents.review.base import ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate
from opencode_python.core.models import Session


class TestRequirementsReviewerLLMBased:
    """Test RequirementsReviewer with LLM-based analysis."""

    @pytest.fixture
    def reviewer(self):
        """Create a RequirementsReviewer instance."""
        return RequirementsReviewer()

    @pytest.fixture
    def sample_context(self):
        """Create a sample review context."""
        return ReviewContext(
            changed_files=["src/app.py", "src/user_service.py"],
            diff="+ def create_user(name, email):\n+     user = User(name=name, email=email)\n+     user.save()\n+     return user",
            repo_root="/test/repo",
            pr_title="Add user creation flow",
            pr_description="- Must validate email format\n- Must handle duplicate email error\n- Must log successful creation",
            base_ref="main",
            head_ref="feature/user-creation"
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
        """Sample valid LLM response JSON for requirements analysis."""
        return r"""{
            "agent": "requirements",
            "summary": "Requirements review complete. Found 3 issues: - 1 critical requirements not met - 2 warnings",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/app.py", "src/user_service.py"],
                "ignored_files": [],
                "reasoning": "Requirements review analyzing implementation against stated requirements"
            },
            "findings": [
                {
                    "id": "REQ-001",
                    "title": "Email validation not implemented",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "Requirement: Must validate email format. No email validation logic found in create_user function",
                    "risk": "Invalid email addresses may be stored, causing data integrity issues",
                    "recommendation": "Add email validation using regex or email-validator library before creating user",
                    "suggested_patch": "import re\ndef validate_email(email):\n    return re.match(r'^[^@]+@[^@]+\\.[^@]+$', email) is not None\nif not validate_email(email):\n    raise ValueError('Invalid email format')"
                },
                {
                    "id": "REQ-002",
                    "title": "Duplicate email error handling missing",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "Requirement: Must handle duplicate email error. No try/except block or duplicate check found",
                    "risk": "Application will crash with database integrity error on duplicate email",
                    "recommendation": "Add exception handling for duplicate key constraint violation",
                    "suggested_patch": "try:\n    user.save()\nexcept IntegrityError as e:\n    raise ValueError('Email already registered') from e"
                },
                {
                    "id": "REQ-003",
                    "title": "Logging not implemented",
                    "severity": "warning",
                    "confidence": "medium",
                    "owner": "dev",
                    "estimate": "S",
                    "evidence": "Requirement: Must log successful creation. No logging statements found in create_user function",
                    "risk": "No audit trail for user creation events",
                    "recommendation": "Add logging statement after successful user creation",
                    "suggested_patch": "logger.info(f'User created successfully: {email}')"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["REQ-001", "REQ-002"],
                "should_fix": ["REQ-003"],
                "notes_for_coding_agent": [
                    "Found 2 critical requirements not met that must be fixed:",
                    "  - Email validation not implemented",
                    "  - Duplicate email error handling missing",
                    "Found 1 warning that should be fixed:",
                    "  - Logging not implemented"
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

        with patch('opencode_python.agents.review.agents.requirements.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.requirements.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                mock_ai_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()

                assert isinstance(result, ReviewOutput)
                assert result.agent == "requirements"
                assert result.severity == "critical"
                assert len(result.findings) == 3
                assert result.findings[0].id == "REQ-001"
                assert result.merge_gate.decision == "needs_changes"

    @pytest.mark.asyncio
    async def test_review_handles_missing_api_key_by_raising_exception(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() raises exception when API key is missing."""
        mock_ai_session = MagicMock()

        async def mock_process_message(user_message, options=None):
            raise ValueError("API key not found for provider")

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.requirements.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.requirements.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

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
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = "This is not valid JSON"

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.requirements.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.requirements.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

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
        mock_ai_session = MagicMock()

        async def mock_process_message(user_message, options=None):
            raise TimeoutError("Request timed out after 60s")

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.requirements.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.requirements.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                with pytest.raises(TimeoutError, match="timed out"):
                    await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_passes_correct_context_to_llm(
        self,
        reviewer,
        sample_context,
        mock_session,
        sample_review_output_json
    ):
        """Test that review() formats context correctly for LLM."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = sample_review_output_json

        mock_ai_session.process_message = AsyncMock(return_value=mock_message)

        with patch('opencode_python.agents.review.agents.requirements.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.requirements.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                await reviewer.review(sample_context)

                call_args = mock_ai_session.process_message.call_args
                user_message = call_args[0][0]

                assert "Requirements Review Subagent" in user_message
                assert "Must validate email format" in user_message
                assert "def create_user" in user_message
                assert "src/app.py" in user_message

    @pytest.mark.asyncio
    async def test_review_handles_empty_findings_gracefully(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() handles LLM response with no findings."""
        empty_json = """{
            "agent": "requirements",
            "summary": "All requirements met",
            "severity": "merge",
            "scope": {
                "relevant_files": ["src/app.py"],
                "ignored_files": [],
                "reasoning": "Implementation matches all requirements"
            },
            "findings": [],
            "merge_gate": {
                "decision": "approve",
                "must_fix": [],
                "should_fix": [],
                "notes_for_coding_agent": ["All requirements successfully implemented"]
            }
        }"""

        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = empty_json

        mock_ai_session.process_message = AsyncMock(return_value=mock_message)

        with patch('opencode_python.agents.review.agents.requirements.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.requirements.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert result.severity == "merge"
                assert result.merge_gate.decision == "approve"
                assert len(result.findings) == 0

    @pytest.mark.asyncio
    async def test_get_agent_name_and_system_prompt(self, reviewer):
        """Test basic reviewer metadata methods."""
        assert reviewer.get_agent_name() == "requirements"
        assert "Requirements Review Subagent" in reviewer.get_system_prompt()
        assert "Compare stated requirements" in reviewer.get_system_prompt()

    @pytest.mark.asyncio
    async def test_get_relevant_file_patterns(self, reviewer):
        """Test that requirements reviewer is relevant to all files."""
        patterns = reviewer.get_relevant_file_patterns()
        assert "**/*" in patterns
