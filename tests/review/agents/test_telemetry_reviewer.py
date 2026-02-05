"""Test TelemetryMetricsReviewer agent with LLM-based analysis."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from opencode_python.agents.review.agents.telemetry import TelemetryMetricsReviewer
from opencode_python.agents.review.base import ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate
from opencode_python.core.models import Session


class TestTelemetryMetricsReviewerLLMBased:
    """Test TelemetryMetricsReviewer with LLM-based analysis."""

    @pytest.fixture
    def reviewer(self):
        """Create a TelemetryMetricsReviewer instance."""
        return TelemetryMetricsReviewer()

    @pytest.fixture
    def sample_context(self):
        """Create a sample review context."""
        return ReviewContext(
            changed_files=["src/app.py", "src/logger.py"],
            diff="+ def handle_request():\n+     try:\n+         data = fetch_data()\n+         return data\n+     except:\n+         pass",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/add-telemetry"
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
            "agent": "telemetry",
            "summary": "Found 1 telemetry issue(s).",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/app.py", "src/logger.py"],
                "ignored_files": [],
                "reasoning": "Telemetry review analyzed 2 relevant files for logging quality and observability coverage."
            },
            "findings": [
                {
                    "id": "silent-exception-1",
                    "title": "Silent exception handler",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "S",
                    "evidence": "Line 3: +     except: pass",
                    "risk": "Silent exception handlers hide errors and make debugging impossible.",
                    "recommendation": "Add logging or re-raise exception with context.",
                    "suggested_patch": "except Exception as e:\\n    logger.error(f'Error in handle_request: {e}')\\n    raise"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["silent-exception-1"],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Ensure all exception handlers have appropriate logging or re-raise logic."
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

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                mock_ai_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()
                process_args = mock_ai_session.process_message.call_args
                assert "system_prompt" in process_args[1].get('options', {}) or \
                       sample_context.diff in process_args[0][0]

                assert isinstance(result, ReviewOutput)
                assert result.agent == "telemetry"
                assert result.severity == "critical"
                assert len(result.findings) == 1
                assert result.findings[0].id == "silent-exception-1"
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

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
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

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
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

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

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
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = """{
            "agent": "telemetry",
            "summary": "No telemetry issues detected.",
            "severity": "merge",
            "scope": {
                "relevant_files": ["src/app.py"],
                "ignored_files": [],
                "reasoning": "Telemetry review analyzed 1 relevant file."
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

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
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
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = sample_review_output_json

        captured_message = None

        async def mock_process_message(user_message, options=None):
            nonlocal captured_message
            captured_message = user_message
            return mock_message

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                await reviewer.review(sample_context)

                assert captured_message is not None
                assert "## Review Context" in captured_message
                assert "src/app.py" in captured_message
                assert sample_context.diff in captured_message

    @pytest.mark.asyncio
    async def test_review_with_multiple_telemetry_findings(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() handles multiple telemetry findings."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = """{
            "agent": "telemetry",
            "summary": "Found 2 telemetry issue(s).",
            "severity": "warning",
            "scope": {
                "relevant_files": ["src/app.py", "src/logger.py"],
                "ignored_files": [],
                "reasoning": "Telemetry review analyzed 2 relevant files."
            },
            "findings": [
                {
                    "id": "log-quality-1",
                    "title": "String concatenation in log",
                    "severity": "warning",
                    "confidence": "medium",
                    "owner": "dev",
                    "estimate": "S",
                    "evidence": "logger.info('Processing ' + data)",
                    "risk": "Poor logging quality makes logs harder to parse.",
                    "recommendation": "Use structured logging with f-strings.",
                    "suggested_patch": "logger.info(f'Processing {data}')"
                },
                {
                    "id": "missing-metrics-1",
                    "title": "IO operation without metrics",
                    "severity": "warning",
                    "confidence": "low",
                    "owner": "dev",
                    "estimate": "S",
                    "evidence": "def fetch_data():",
                    "risk": "Missing metrics make it difficult to monitor performance.",
                    "recommendation": "Add metrics for IO operations.",
                    "suggested_patch": "metrics.counter('fetch_data').increment()"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": [],
                "should_fix": ["log-quality-1", "missing-metrics-1"],
                "notes_for_coding_agent": []
            }
        }"""

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "warning"
                assert len(result.findings) == 2
                assert result.merge_gate.decision == "needs_changes"
                assert len(result.merge_gate.should_fix) == 2

    @pytest.mark.asyncio
    async def test_review_with_sensitive_data_finding(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() detects sensitive data in logs."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = """{
            "agent": "telemetry",
            "summary": "Found 1 critical issue(s).",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/app.py"],
                "ignored_files": [],
                "reasoning": "Telemetry review analyzed 1 relevant file."
            },
            "findings": [
                {
                    "id": "sensitive-log-1",
                    "title": "Logging sensitive data",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "S",
                    "evidence": "logger.info(f'Password: {password}')",
                    "risk": "Logging sensitive data can lead to security breaches.",
                    "recommendation": "Remove sensitive data from logs or redact it.",
                    "suggested_patch": "logger.info('Password logged')"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["sensitive-log-1"],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Ensure sensitive data is never logged."
                ]
            }
        }"""

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "critical"
                assert len(result.findings) == 1
                assert result.findings[0].id == "sensitive-log-1"
                assert result.merge_gate.decision == "needs_changes"
                assert len(result.merge_gate.must_fix) == 1
