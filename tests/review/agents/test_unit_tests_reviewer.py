"""Test UnitTestsReviewer agent with LLM-based analysis."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dawn_kestrel.agents.review.agents.unit_tests import UnitTestsReviewer
from dawn_kestrel.agents.review.base import ReviewContext
from dawn_kestrel.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate
from dawn_kestrel.core.models import Session


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
            head_ref="feature/add-calculator",
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
        self, reviewer, sample_context, sample_review_output_json
    ):
        """Test that review() uses SimpleReviewAgentRunner and parses output."""
        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value=sample_review_output_json)

        with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
            result = await reviewer.review(sample_context)

            mock_runner.run_with_retry.assert_called_once()

            assert isinstance(result, ReviewOutput)
            assert result.agent == "unit_tests"
            assert result.severity == "warning"
            assert len(result.findings) == 1
            assert result.findings[0].id == "TEST-MISSING-001"
            assert result.merge_gate.decision == "needs_changes"

    @pytest.mark.asyncio
    async def test_review_handles_missing_api_key_by_raising_exception(
        self, reviewer, sample_context
    ):
        """Test that review() raises exception when API key is missing."""
        with patch(
            "dawn_kestrel.core.harness.SimpleReviewAgentRunner.run_with_retry",
            side_effect=ValueError("API key not found for provider"),
        ):
            with pytest.raises(ValueError, match="API key not found"):
                await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_handles_invalid_json_response(self, reviewer, sample_context):
        """Test that review() returns error ReviewOutput for invalid JSON."""
        with patch(
            "dawn_kestrel.core.harness.SimpleReviewAgentRunner.run_with_retry",
            return_value="This is not valid JSON",
        ):
            result = await reviewer.review(sample_context)

            assert isinstance(result, ReviewOutput)
            assert result.severity == "critical"
            assert "error" in result.summary.lower() or "invalid" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_review_handles_timeout_error_by_raising_exception(
        self, reviewer, sample_context
    ):
        """Test that review() raises exception on timeout."""
        with patch(
            "dawn_kestrel.core.harness.SimpleReviewAgentRunner.run_with_retry",
            side_effect=TimeoutError("Request timed out after 60s"),
        ):
            with pytest.raises(TimeoutError):
                await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_with_no_findings_returns_merge_severity(self, reviewer, sample_context):
        """Test that review() returns severity='merge' when no findings."""
        clean_review_json = """{
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

            assert captured_system_prompt is not None
            assert captured_formatted_context is not None

            assert "unit test" in captured_system_prompt.lower()

            assert "## Review Context" in captured_formatted_context
            assert "src/calculator.py" in captured_formatted_context
            assert sample_context.diff in captured_formatted_context

            assert isinstance(result, ReviewOutput)
            assert result.agent == "unit_tests"

    @pytest.mark.asyncio
    async def test_review_with_blocking_severity(self, reviewer, sample_context):
        """Test that review() returns blocking severity for failing tests."""
        blocking_review_json = """{
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

        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value=blocking_review_json)

        with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
            result = await reviewer.review(sample_context)

            assert isinstance(result, ReviewOutput)
            assert result.severity == "blocking"
            assert result.merge_gate.decision == "block"
            assert len(result.findings) == 1
            assert result.findings[0].severity == "blocking"
