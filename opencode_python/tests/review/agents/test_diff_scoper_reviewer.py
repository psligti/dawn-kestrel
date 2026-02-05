"""Test DiffScoperReviewer agent with LLM-based analysis."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from opencode_python.agents.review.agents.diff_scoper import DiffScoperReviewer
from opencode_python.agents.review.base import ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate, Check
from opencode_python.core.models import Session


class TestDiffScoperReviewerLLMBased:
    """Test DiffScoperReviewer with LLM-based analysis."""

    @pytest.fixture
    def reviewer(self):
        """Create a DiffScoperReviewer instance."""
        return DiffScoperReviewer()

    @pytest.fixture
    def sample_context(self):
        """Create a sample review context."""
        return ReviewContext(
            changed_files=["src/api.py", "config/settings.py", "tests/test_api.py"],
            diff="+ def new_api_endpoint():\n+     return {'status': 'ok'}\n- old_api_endpoint()",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/add-api"
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
        """Sample valid LLM response JSON for diff scoping."""
        return """{
            "agent": "diff_scoper",
            "summary": "Diff Scoping Analysis: MEDIUM RISK\\n\\n## Change Summary\\n- Files changed: 3\\n- Lines added: 2\\n- Lines removed: 1\\n- Total code changes: 3",
            "severity": "warning",
            "scope": {
                "relevant_files": ["src/api.py", "config/settings.py", "tests/test_api.py"],
                "ignored_files": [],
                "reasoning": "Diff scoper analyzes all 3 changed files to assess overall risk and routing"
            },
            "checks": [
                {
                    "name": "format_check",
                    "required": false,
                    "commands": ["pre-commit run --all-files"],
                    "why": "Quick format validation",
                    "expected_signal": "passed"
                },
                {
                    "name": "lint_check",
                    "required": false,
                    "commands": ["ruff check"],
                    "why": "Code quality validation",
                    "expected_signal": "No errors found"
                }
            ],
            "findings": [
                {
                    "id": "route-code",
                    "title": "Route to Code Reviewer",
                    "severity": "warning",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "S",
                    "evidence": "File: src/api.py",
                    "risk": "medium",
                    "recommendation": "Python code changes with medium risk, requires code review",
                    "suggested_patch": null
                }
            ],
            "merge_gate": {
                "decision": "approve",
                "must_fix": [],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Risk Rationale: MEDIUM risk classification based on diff analysis",
                    "routing: {\\"code\\": \\"Recommended: code review for medium/high risk changes\\"}"
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
                
        with patch('opencode_python.agents.review.agents.diff_scoper.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.diff_scoper.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                mock_ai_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()
                process_args = mock_ai_session.process_message.call_args
                assert sample_context.diff in process_args[0][0]

                # Verify result is valid ReviewOutput
                assert isinstance(result, ReviewOutput)
                assert result.agent == "diff_scoper"
                assert result.severity == "warning"
                assert len(result.findings) == 1
                assert result.findings[0].id == "route-code"
                assert result.merge_gate.decision == "approve"
                assert len(result.checks) == 2

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
        with patch('opencode_python.agents.review.agents.diff_scoper.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.diff_scoper.Session') as mock_session_cls:
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
        with patch('opencode_python.agents.review.agents.diff_scoper.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.diff_scoper.Session') as mock_session_cls:
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
        with patch('opencode_python.agents.review.agents.diff_scoper.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.diff_scoper.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                # Should raise exception
                with pytest.raises(TimeoutError):
                    await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_with_high_risk_returns_critical_severity(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() returns severity='critical' for high risk changes."""
        # Mock AISession to return high-risk review
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = """{
            "agent": "diff_scoper",
            "summary": "Diff Scoping Analysis: HIGH RISK",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/auth.py", "src/security.py"],
                "ignored_files": [],
                "reasoning": "Diff scoper analyzes all 2 changed files to assess overall risk and routing"
            },
            "checks": [
                {
                    "name": "security_scan",
                    "required": true,
                    "commands": ["bandit -r ."],
                    "why": "Security vulnerability scan for high-risk changes",
                    "expected_signal": "No issues found"
                }
            ],
            "findings": [
                {
                    "id": "risk-classification",
                    "title": "High Risk Change Detected",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "Files changed: 2, Risk level: high",
                    "risk": "high",
                    "recommendation": "This change touches critical paths or has significant impact. Route to specialized reviewers.",
                    "suggested_patch": null
                }
            ],
            "merge_gate": {
                "decision": "approve",
                "must_fix": [],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Risk Rationale: HIGH risk classification based on diff analysis",
                    "routing: {\\"security\\": \\"Critical: security/auth changes detected\\"}"
                ]
            }
        }"""

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        # Patch AISession
        with patch('opencode_python.agents.review.agents.diff_scoper.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.diff_scoper.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "critical"
                assert result.merge_gate.decision == "approve"
                assert result.findings[0].risk == "high"

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
        with patch('opencode_python.agents.review.agents.diff_scoper.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.diff_scoper.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                await reviewer.review(sample_context)

                # Verify message includes context
                assert captured_message is not None
                assert "## Review Context" in captured_message
                assert "src/api.py" in captured_message
                assert sample_context.diff in captured_message
                assert "Diff Scoper Subagent" in captured_message
