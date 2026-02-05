"""Tests for PerformanceReliabilityReviewer - LLM-based analysis."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from opencode_python.agents.review.agents.performance import PerformanceReliabilityReviewer
from opencode_python.agents.review.base import ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate
from opencode_python.core.models import Session


class TestPerformanceReliabilityReviewerLLMBased:
    """Test PerformanceReliabilityReviewer with LLM-based analysis."""

    @pytest.fixture
    def reviewer(self):
        """Create a PerformanceReliabilityReviewer instance."""
        return PerformanceReliabilityReviewer()

    @pytest.fixture
    def sample_context(self):
        """Create a sample review context."""
        return ReviewContext(
            changed_files=["src/app.py", "src/api/service.py"],
            diff="+ while True:\n+     pass\n+ for item in items: db.execute('select 1')",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/performance-opt"
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
        """Sample valid LLM response JSON for performance issues."""
        return """{
            "agent": "performance",
            "summary": "Performance review complete. Found retry logic issue and IO amplification",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/app.py", "src/api/service.py"],
                "ignored_files": [],
                "reasoning": "Performance review for API changes"
            },
            "findings": [
                {
                    "id": "PERF-RETRY-001",
                    "title": "Bare except catches all exceptions",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "File: src/app.py | Lines: 2-4 | Bare except catches all exceptions including expected ones",
                    "risk": "Silent failures hide bugs and make debugging impossible",
                    "recommendation": "Catch only specific expected exceptions, not broad Exception"
                },
                {
                    "id": "PERF-IO-001",
                    "title": "Database query in loop",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "L",
                    "evidence": "File: src/api/service.py | Loop: 7 | Executes database query for each item without batching",
                    "risk": "N+1 queries cause excessive database load and slow response times",
                    "recommendation": "Batch queries or use cursor-based iteration"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["PERF-RETRY-001", "PERF-IO-001"],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Found 2 critical performance issues that must be fixed:",
                    "  1. Bare except catches all exceptions",
                    "  2. Database query in loop causes IO amplification",
                    "Consider using specific exception types and batching database queries"
                ]
            }
        }"""

    @pytest.fixture
    def sample_no_findings_json(self):
        """Sample LLM response with no findings."""
        return """{
            "agent": "performance",
            "summary": "No relevant performance changes",
            "severity": "merge",
            "scope": {
                "relevant_files": [],
                "ignored_files": ["README.md"],
                "reasoning": "No performance-related files changed"
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
                
        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                mock_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()

                assert isinstance(result, ReviewOutput)
                assert result.agent == "performance"
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

        with patch('opencode_python.agents.review.agents.performance.settings') as mock_settings:
            from opencode_python.core import settings
            mock_settings.get_api_key_for_provider.return_value = None

            with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
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

        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
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

        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
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

        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.agent == "performance"
                assert result.severity == "merge"
                assert len(result.findings) == 0
                assert result.merge_gate.decision == "approve"
                assert "No relevant performance changes" in result.summary

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

        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                call_args = mock_ai_session.process_message.call_args
                args, kwargs = call_args
                user_message = args[0]

                assert "Performance & Reliability Review Subagent" in user_message
                assert "src/app.py" in user_message
                assert "src/api/service.py" in user_message
                assert reviewer.get_system_prompt() in user_message

    @pytest.mark.asyncio
    async def test_review_with_blocking_severity_for_critical_issues(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that critical findings return blocking severity."""
        blocking_json = """{
            "agent": "performance",
            "summary": "Critical performance issues found",
            "severity": "blocking",
            "scope": {
                "relevant_files": ["src/app.py"],
                "ignored_files": [],
                "reasoning": "Performance review"
            },
            "findings": [
                {
                    "id": "PERF-RETRY-001",
                    "title": "Infinite loop detected",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "File: src/app.py | Line: 3 | while True: without break condition",
                    "risk": "Infinite loop causes CPU hang and denial of service",
                    "recommendation": "Add break condition or use explicit iteration limits"
                }
            ],
            "merge_gate": {
                "decision": "block",
                "must_fix": ["PERF-RETRY-001"],
                "should_fix": [],
                "notes_for_coding_agent": []
            }
        }"""

        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = blocking_json

        mock_ai_session.process_message = AsyncMock(return_value=mock_message)

        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert result.severity == "blocking"
                assert result.merge_gate.decision == "block"

    def test_get_system_prompt_returns_performance_prompt(self, reviewer):
        """Test that get_system_prompt returns correct performance prompt."""
        system_prompt = reviewer.get_system_prompt()
        assert "Performance & Reliability Review Subagent" in system_prompt
        assert "complexity regressions" in system_prompt
        assert "IO amplification" in system_prompt
        assert "retry/backoff/timeouts correctness" in system_prompt

    def test_performance_reviewer_metadata_helpers(self, reviewer):
        """Test that PerformanceReliabilityReviewer metadata helpers work correctly."""
        assert reviewer.get_agent_name() == "performance"
        assert "Performance & Reliability Review Subagent" in reviewer.get_system_prompt()
        assert reviewer.get_relevant_file_patterns() == ["**/*.py", "**/*.rs", "**/*.go", "**/*.js", "**/*.ts", "**/*.tsx", "**/config/**", "**/database/**", "**/db/**", "**/network/**", "**/api/**", "**/services/**"]
