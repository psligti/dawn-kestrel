"""Test PerformanceReliabilityReviewer agent with LLM-based analysis."""
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
            changed_files=["src/data_processor.py", "src/api_client.py"],
            diff="+ for item in items:\n+     data = db.query(item.id)\n+     return data",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/add-processing"
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
            "agent": "performance",
            "summary": "Found 1 performance issue(s).",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/data_processor.py", "src/api_client.py"],
                "ignored_files": [],
                "reasoning": "Performance review analyzed 2 relevant files for complexity, IO amplification, and reliability issues."
            },
            "findings": [
                {
                    "id": "perf-001",
                    "title": "N+1 database query inside loop",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "L",
                    "evidence": "Line 2: +     data = db.query(item.id)",
                    "risk": "N+1 query pattern causes O(n) database calls instead of O(1) or O(1/batch)",
                    "recommendation": "Use batch queries, JOIN, prefetch_related, or load all data before the loop"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["perf-001"],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Fix N+1 database query issue before merging."
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

        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                mock_ai_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()
                process_args = mock_ai_session.process_message.call_args

                # Verify result is valid ReviewOutput
                assert isinstance(result, ReviewOutput)
                assert result.agent == "performance"
                assert result.severity == "critical"
                assert len(result.findings) == 1
                assert result.findings[0].id == "perf-001"
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
        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
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
        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
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
        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
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
            "agent": "performance",
            "summary": "No performance or reliability issues detected.",
            "severity": "merge",
            "scope": {
                "relevant_files": ["src/data_processor.py"],
                "ignored_files": [],
                "reasoning": "Performance review analyzed 1 relevant file."
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
        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
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
        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                await reviewer.review(sample_context)

                # Verify message includes context
                assert captured_message is not None
                assert "## Review Context" in captured_message
                assert "src/data_processor.py" in captured_message
                assert sample_context.diff in captured_message

    @pytest.mark.asyncio
    async def test_review_handles_blocking_severity(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() correctly handles blocking severity from LLM."""
        # Mock AISession to return blocking review
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = """{
            "agent": "performance",
            "summary": "Found 1 blocking issue(s).",
            "severity": "blocking",
            "scope": {
                "relevant_files": ["src/data_processor.py"],
                "ignored_files": [],
                "reasoning": "Performance review found critical infinite retry risk."
            },
            "findings": [
                {
                    "id": "perf-block-001",
                    "title": "Infinite retry loop risk",
                    "severity": "blocking",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "Line 10: while True: try: await api_call()",
                    "risk": "Infinite retry loops can hang applications and exhaust resources",
                    "recommendation": "Always include retry limits, exponential backoff, and timeout mechanisms"
                }
            ],
            "merge_gate": {
                "decision": "block",
                "must_fix": ["perf-block-001"],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Fix infinite retry risk before merge."
                ]
            }
        }"""

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        # Patch AISession
        with patch('opencode_python.agents.review.agents.performance.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            # Patch Session creation
            with patch('opencode_python.agents.review.agents.performance.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "blocking"
                assert result.merge_gate.decision == "block"
                assert len(result.findings) == 1
                assert result.findings[0].severity == "blocking"
