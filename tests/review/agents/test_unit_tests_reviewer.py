"""Test UnitTestsReviewer agent with LLM-based analysis."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from opencode_python.agents.review.agents.unit_tests import UnitTestsReviewer
from opencode_python.agents.review.base import ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate
from opencode_python.core.models import Session


class TestUnitTestsReviewerLLMBased:
    """Test UnitTestsReviewer with LLM-based analysis."""

    @pytest.fixture
    def reviewer(self):
        """Create a UnitTestsReviewer instance."""
        return UnitTestsReviewer()

    @pytest.fixture
    def sample_context(self):
        """Create a sample review context."""
        return ReviewContext(
            changed_files=["src/calculator.py", "tests/test_calculator.py"],
            diff="+ def add(a: int, b: int) -> int:\n+     return a + b",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/add-calculator"
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
            "agent": "unit_tests",
            "summary": "Unit test review complete.",
            "severity": "warning",
            "scope": {
                "relevant_files": ["src/calculator.py", "tests/test_calculator.py"],
                "ignored_files": [],
                "reasoning": "Unit test review analyzed 2 relevant files for test coverage and quality."
            },
            "findings": [
                {
                    "id": "TEST-MISSING-001",
                    "title": "New function without tests: add",
                    "severity": "warning",
                    "confidence": "medium",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "Added new function: add",
                    "risk": "New code without tests may hide bugs and regressions.",
                    "recommendation": "Add unit tests for the new function to verify behavior and catch regressions.",
                    "suggested_patch": null
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": [],
                "should_fix": ["TEST-MISSING-001"],
                "notes_for_coding_agent": [
                    "Add unit tests for the new add() function."
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

        with patch('opencode_python.agents.review.agents.unit_tests.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.unit_tests.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                mock_ai_session_cls.assert_called_once()
                mock_ai_session.process_message.assert_called_once()
                process_args = mock_ai_session.process_message.call_args
                assert "options" in process_args[1]

                assert isinstance(result, ReviewOutput)
                assert result.agent == "unit_tests"
                assert result.severity == "warning"
                assert len(result.findings) == 1
                assert result.findings[0].id == "TEST-MISSING-001"
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

        with patch('opencode_python.agents.review.agents.unit_tests.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.unit_tests.Session') as mock_session_cls:
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

        with patch('opencode_python.agents.review.agents.unit_tests.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.unit_tests.Session') as mock_session_cls:
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

        with patch('opencode_python.agents.review.agents.unit_tests.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.unit_tests.Session') as mock_session_cls:
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
            "agent": "unit_tests",
            "summary": "No test issues detected.",
            "severity": "merge",
            "scope": {
                "relevant_files": ["src/calculator.py"],
                "ignored_files": [],
                "reasoning": "Unit test review analyzed 1 relevant file."
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

        with patch('opencode_python.agents.review.agents.unit_tests.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.unit_tests.Session') as mock_session_cls:
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

        with patch('opencode_python.agents.review.agents.unit_tests.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.unit_tests.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                await reviewer.review(sample_context)

                assert captured_message is not None
                assert "## Review Context" in captured_message
                assert "src/calculator.py" in captured_message
                assert sample_context.diff in captured_message

    @pytest.mark.asyncio
    async def test_review_with_blocking_severity(
        self,
        reviewer,
        sample_context,
        mock_session
    ):
        """Test that review() returns blocking severity for failing tests."""
        mock_ai_session = MagicMock()
        mock_message = MagicMock()
        mock_message.text = """{
            "agent": "unit_tests",
            "summary": "Unit test review complete. Found 1 blocking issue(s): - 1 blocking",
            "severity": "blocking",
            "scope": {
                "relevant_files": ["src/calculator.py", "tests/test_calculator.py"],
                "ignored_files": [],
                "reasoning": "Unit test review analyzed 2 relevant files."
            },
            "findings": [
                {
                    "id": "TEST-FAILURE-001",
                    "title": "Test failure in test_calculator.py",
                    "severity": "blocking",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "Test test_add failed",
                    "risk": "Failing tests indicate broken functionality or regression.",
                    "recommendation": "Fix the failing test or the underlying code.",
                    "suggested_patch": null
                }
            ],
            "merge_gate": {
                "decision": "block",
                "must_fix": ["TEST-FAILURE-001"],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Fix the failing test test_add in test_calculator.py."
                ]
            }
        }"""

        async def mock_process_message(user_message, options=None):
            return mock_message

        mock_ai_session.process_message = mock_process_message

        with patch('opencode_python.agents.review.agents.unit_tests.AISession') as mock_ai_session_cls:
            mock_ai_session_cls.return_value = mock_ai_session

            with patch('opencode_python.agents.review.agents.unit_tests.Session') as mock_session_cls:
                mock_session_cls.return_value = mock_session

                result = await reviewer.review(sample_context)

                assert isinstance(result, ReviewOutput)
                assert result.severity == "blocking"
                assert result.merge_gate.decision == "block"
                assert len(result.findings) == 1
                assert result.findings[0].severity == "blocking"
