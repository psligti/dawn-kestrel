"""Tests for TelemetryMetricsReviewer - LLM-based analysis."""
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
            changed_files=["src/service.py", "src/api/handler.py"],
            diff="+ try:\n+     pass\n+ except Exception: pass\n+ logger.info(\"token=%s\", token)",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/telemetry"
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
        """Sample valid LLM response JSON for telemetry issues."""
        return """{
            "agent": "telemetry",
            "summary": "Telemetry review complete. Found silent exception and sensitive data logging",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/service.py", "src/api/handler.py"],
                "ignored_files": [],
                "reasoning": "Telemetry review for logging changes"
            },
            "findings": [
                {
                    "id": "silent-exception-001",
                    "title": "Bare except catches all exceptions silently",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "File: src/service.py | Line: 3 | Bare except Exception: pass swallows all errors",
                    "risk": "Silent failures hide bugs and make debugging impossible",
                    "recommendation": "Catch specific expected exceptions and log them with context"
                },
                {
                    "id": "sensitive-log-001",
                    "title": "PII potentially logged",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "security",
                    "estimate": "M",
                    "evidence": "File: src/api/handler.py | Line: 4 | logger.info logs token value without masking",
                    "risk": "Sensitive data in logs can leak user information",
                    "recommendation": "Redact or mask sensitive values in logs"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["silent-exception-001", "sensitive-log-001"],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Found 2 critical telemetry issues that must be fixed:",
                    "  1. Bare except catches all exceptions silently",
                    "  2. PII potentially logged without masking",
                    "Implement structured logging with proper exception handling and data masking"
                ]
            }
        }"""

    @pytest.fixture
    def sample_no_findings_json(self):
        """Sample LLM response with no findings."""
        return """{
            "agent": "telemetry",
            "summary": "No relevant telemetry changes",
            "severity": "merge",
            "scope": {
                "relevant_files": [],
                "ignored_files": ["README.md"],
                "reasoning": "No logging or observability files changed"
            },
            "findings": [],
            "merge_gate": {
                "decision": "approve",
                "must_fix": [],
                "should_fix": [],
                "notes_for_coding_agent": []
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

                mock_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()

                assert isinstance(result, ReviewOutput)
                assert result.agent == "telemetry"
                assert result.severity == "critical"
                assert len(result.findings) == 2

    @pytest.mark.asyncio
    async def test_review_handles_missing_api_key_by_raising_exception(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() raises exception when API key is missing."""
        mock_ai_session = MagicMock()

        with patch('opencode_python.agents.review.agents.telemetry.settings') as mock_settings:
            from opencode_python.core import settings
            mock_settings.api_key = None

            with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
                mock_ai_session_cls.return_value = mock_ai_session

                with pytest.raises(ValueError) as exc_info:
                    await reviewer.review(sample_context)
                assert "API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_review_handles_invalid_json_response(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() returns error ReviewOutput on invalid JSON."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = "not valid json"

        mock_ai_session.process_message = AsyncMock(return_value=mock_message)

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "critical"
                assert "Error parsing LLM response" in result.summary
                assert len(result.findings) == 0
                assert result.merge_gate.decision == "needs_changes"

    @pytest.mark.asyncio
    async def test_review_handles_timeout_error_by_raising_exception(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() raises TimeoutError on timeout."""
        mock_ai_session = MagicMock()

        async def mock_process_message(user_message, options=None):
            import asyncio
            raise TimeoutError("LLM request timed out")

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
        mock_session,
        sample_no_findings_json
    ):
        """Test that review() returns merge severity when no findings."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = sample_no_findings_json

        mock_ai_session.process_message = AsyncMock(return_value=mock_message)

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.agent == "telemetry"
                assert result.severity == "merge"
                assert len(result.findings) == 0
                assert result.merge_gate.decision == "approve"
                assert "No relevant telemetry changes" in result.summary

    @pytest.mark.asyncio
    async def test_review_includes_system_prompt_and_context_in_message(
        self,
        reviewer,
        sample_context,
        mock_session,
        sample_review_output_json
    ):
        """Test that review() includes system prompt and context in message."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = sample_review_output_json

        mock_ai_session.process_message = AsyncMock(return_value=mock_message)

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                call_args = mock_ai_session.process_message.call_args
                args, kwargs = call_args
                user_message = args[0]

                assert "Telemetry & Metrics Review Subagent" in user_message
                assert "src/service.py" in user_message
                assert "src/api/handler.py" in user_message
                assert reviewer.get_system_prompt() in user_message

    @pytest.mark.asyncio
    async def test_review_with_sensitive_data_finding(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that LLM correctly identifies and returns sensitive data findings."""
        sensitive_data_json = """{
            "agent": "telemetry",
            "summary": "Found sensitive data in logs",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/api/handler.py"],
                "ignored_files": [],
                "reasoning": "Telemetry review"
            },
            "findings": [
                {
                    "id": "sensitive-log-001",
                    "title": "PII potentially logged",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "security",
                    "estimate": "M",
                    "evidence": "File: src/api/handler.py | Line: 4 | logger.info logs user.email without masking",
                    "risk": "Sensitive data in logs can leak user information",
                    "recommendation": "Redact or mask sensitive values in logs"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["sensitive-log-001"],
                "should_fix": [],
                "notes_for_coding_agent": []
            }
        }"""

        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = sensitive_data_json

        mock_ai_session.process_message = AsyncMock(return_value=mock_message)

        with patch('opencode_python.agents.review.agents.telemetry.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.telemetry.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert result.severity == "critical"
                assert any(f.id == "sensitive-log-001" for f in result.findings)
                assert result.merge_gate.decision == "needs_changes"

    def test_get_system_prompt_returns_telemetry_prompt(self, reviewer):
        """Test that get_system_prompt returns correct telemetry prompt."""
        system_prompt = reviewer.get_system_prompt()
        assert "Telemetry & Metrics Review Subagent" in system_prompt
        assert "logging quality" in system_prompt
        assert "observability coverage" in system_prompt

    def test_telemetry_reviewer_metadata_helpers(self, reviewer):
        """Test that TelemetryMetricsReviewer metadata helpers work correctly."""
        assert reviewer.get_agent_name() == "telemetry"
        assert "Telemetry & Metrics Review Subagent" in reviewer.get_system_prompt()
        assert reviewer.get_relevant_file_patterns() == ["**/*.py", "**/logging/**", "**/observability/**", "**/metrics/**", "**/tracing/**", "**/monitoring/**"]
