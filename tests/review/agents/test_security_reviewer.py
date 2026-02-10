"""Test SecurityReviewer agent with LLM-based analysis."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dawn_kestrel.agents.review.agents.security import SecurityReviewer
from dawn_kestrel.agents.review.base import ReviewContext
from dawn_kestrel.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate
from dawn_kestrel.core.models import Session


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
            head_ref="feature/add-auth",
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
            version="1.0",
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
        self, reviewer, sample_context, sample_review_output_json
    ):
        """Test that review() uses SimpleReviewAgentRunner and parses output."""
        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value=sample_review_output_json)

        with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
            result = await reviewer.review(sample_context)

            mock_runner.run_with_retry.assert_called_once()

            assert isinstance(result, ReviewOutput)
            assert result.agent == "security"
            assert result.severity == "critical"
            assert len(result.findings) == 1
            assert result.findings[0].id == "secret-1"
            assert result.merge_gate.decision == "needs_changes"

    @pytest.mark.asyncio
    async def test_review_handles_missing_api_key_by_raising_exception(
        self, reviewer, sample_context
    ):
        """Test that review() raises exception when API key is missing."""
        # Patch SimpleReviewAgentRunner.run_with_retry to raise exception
        with patch(
            "dawn_kestrel.core.harness.SimpleReviewAgentRunner.run_with_retry",
            side_effect=ValueError("API key not found for provider"),
        ):
            # Should raise exception
            with pytest.raises(ValueError, match="API key not found"):
                await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_handles_invalid_json_response(self, reviewer, sample_context):
        """Test that review() returns error ReviewOutput for invalid JSON."""
        # Patch SimpleReviewAgentRunner.run_with_retry to return invalid JSON
        with patch(
            "dawn_kestrel.core.harness.SimpleReviewAgentRunner.run_with_retry",
            return_value="This is not valid JSON",
        ):
            # Should return error ReviewOutput with severity='critical'
            result = await reviewer.review(sample_context)

            assert isinstance(result, ReviewOutput)
            assert result.severity == "critical"
            assert "error" in result.summary.lower() or "invalid" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_review_handles_timeout_error_by_raising_exception(
        self, reviewer, sample_context
    ):
        """Test that review() raises exception on timeout."""
        # Patch SimpleReviewAgentRunner.run_with_retry to raise timeout
        with patch(
            "dawn_kestrel.core.harness.SimpleReviewAgentRunner.run_with_retry",
            side_effect=TimeoutError("Request timed out after 60s"),
        ):
            # Should raise exception
            with pytest.raises(TimeoutError):
                await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_with_no_findings_returns_merge_severity(self, reviewer, sample_context):
        """Test that review() returns severity='merge' when no findings."""
        # Mock runner to return clean review JSON
        clean_review_json = """{
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

        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value=clean_review_json)

        with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
            result = await reviewer.review(sample_context)

            assert isinstance(result, ReviewOutput)
            assert result.severity == "merge"
            assert result.merge_gate.decision == "approve"
            assert len(result.findings) == 0

    @pytest.mark.asyncio
    async def test_review_includes_system_prompt_and_context_in_message(
        self, reviewer, sample_context, sample_review_output_json
    ):
        """Test that review() includes system prompt and formatted context."""
        # Mock runner to capture system_prompt and formatted_context
        mock_runner = MagicMock()
        captured_system_prompt = None
        captured_formatted_context = None

        async def mock_run_with_retry(system_prompt, formatted_context):
            nonlocal captured_system_prompt, captured_formatted_context
            captured_system_prompt = system_prompt
            captured_formatted_context = formatted_context
            return sample_review_output_json

        mock_runner.run_with_retry = mock_run_with_retry

        with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
            result = await reviewer.review(sample_context)

            # Verify runner was called
            assert captured_system_prompt is not None
            assert captured_formatted_context is not None

            # Verify system prompt contains security reviewer instructions
            assert "security" in captured_system_prompt.lower()

            # Verify formatted context includes expected information
            assert "## Review Context" in captured_formatted_context
            assert "src/auth.py" in captured_formatted_context
            assert sample_context.diff in captured_formatted_context
            assert "config/api.yaml" in captured_formatted_context

            # Verify result is parsed correctly
            assert isinstance(result, ReviewOutput)
            assert result.agent == "security"
