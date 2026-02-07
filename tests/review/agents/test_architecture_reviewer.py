"""Tests for ArchitectureReviewer - LLM-based analysis."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.agents.review.agents.architecture import ArchitectureReviewer
from dawn_kestrel.agents.review.base import ReviewContext
from dawn_kestrel.agents.review.contracts import ReviewOutput, Finding, Scope, MergeGate


class TestArchitectureReviewerLLMBased:
    """Test ArchitectureReviewer with LLM-based analysis."""

    @pytest.fixture
    def reviewer(self):
        """Create an ArchitectureReviewer instance."""
        return ArchitectureReviewer()

    @pytest.fixture
    def sample_context(self):
        """Create a sample review context."""
        return ReviewContext(
            changed_files=["src/app.py", "src/controllers/api.py"],
            diff="+ def public_api():\n+ from infrastructure.db import Client\n+ def public_api():",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature/add-api",
            pr_title="Add public API",
            pr_description="Adds public API endpoint"
        )

    @pytest.fixture
    def sample_review_output_json(self):
        """Sample valid LLM response JSON for architecture issues."""
        return """{
            "agent": "architecture",
            "summary": "Architecture review complete. Found boundary violation and circular dependency",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/app.py", "src/controllers/api.py"],
                "ignored_files": [],
                "reasoning": "Architecture review for API changes"
            },
            "findings": [
                {
                    "id": "ARCH-BOUNDARY-001",
                    "title": "Boundary violation - cross-layer dependency",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "File: src/controllers/api.py | Line: 2 | imports from infrastructure.db layer",
                    "risk": "Cross-layer dependencies create tight coupling and make testing difficult",
                    "recommendation": "Consider introducing abstraction layer or dependency injection"
                },
                {
                    "id": "ARCH-CIRCULAR-001",
                    "title": "Circular dependency detected",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "L",
                    "evidence": "File: src/app.py | Dependency chain: app -> infrastructure.db -> app",
                    "risk": "Circular dependencies cause runtime failures and make code impossible to test",
                    "recommendation": "Refactor to break circular dependency by introducing abstraction layer"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["ARCH-BOUNDARY-001", "ARCH-CIRCULAR-001"],
                "should_fix": [],
                "notes_for_coding_agent": [
                    "Found 2 critical architectural issues that must be fixed:",
                    "  1. Boundary violation: Cross-layer dependency from infrastructure.db",
                    "  2. Circular dependency: app -> infrastructure.db -> app",
                    "Consider refactoring to introduce proper layering and break circular dependencies"
                ]
            }
        }"""

    @pytest.fixture
    def sample_no_findings_json(self):
        """Sample LLM response with no findings."""
        return """{
            "agent": "architecture",
            "summary": "No relevant architectural changes",
            "severity": "merge",
            "scope": {
                "relevant_files": [],
                "ignored_files": ["README.md"],
                "reasoning": "No Python files changed"
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
        sample_review_output_json
    ):
        """Test that review() uses SimpleReviewAgentRunner to get review output."""
        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value=sample_review_output_json)

        with patch('dawn_kestrel.core.harness.SimpleReviewAgentRunner', return_value=mock_runner):
            result = await reviewer.review(sample_context)

            mock_runner.run_with_retry.assert_called_once()
            assert isinstance(result, ReviewOutput)
            assert result.agent == "architecture"
            assert result.severity == "critical"
            assert len(result.findings) == 2

    @pytest.mark.asyncio
    async def test_review_handles_missing_api_key_by_raising_exception(
        self,
        reviewer,
        sample_context
    ):
        """Test that review() raises exception when API key is missing."""
        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(side_effect=ValueError("API key missing"))

        with patch('dawn_kestrel.core.harness.SimpleReviewAgentRunner', return_value=mock_runner):
            with pytest.raises(ValueError) as exc_info:
                await reviewer.review(sample_context)
            assert "API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_review_handles_invalid_json_response(
        self,
        reviewer,
        sample_context
    ):
        """Test that review() returns error ReviewOutput on invalid JSON."""
        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value="not valid json")

        with patch('dawn_kestrel.core.harness.SimpleReviewAgentRunner', return_value=mock_runner):
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
        sample_context
    ):
        """Test that review() raises TimeoutError on timeout."""
        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(side_effect=TimeoutError("LLM request timed out"))

        with patch('dawn_kestrel.core.harness.SimpleReviewAgentRunner', return_value=mock_runner):
            with pytest.raises(TimeoutError):
                await reviewer.review(sample_context)

    @pytest.mark.asyncio
    async def test_review_with_no_findings_returns_merge_severity(
        self,
        reviewer,
        sample_no_findings_json
    ):
        """Test that review() returns merge severity when no findings."""
        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value=sample_no_findings_json)

        with patch('dawn_kestrel.core.harness.SimpleReviewAgentRunner', return_value=mock_runner):
            result = await reviewer.review(ReviewContext(
                changed_files=["README.md"],
                diff="+ Update docs",
                repo_root="/test/repo",
            ))

            assert isinstance(result, ReviewOutput)
            assert result.agent == "architecture"
            assert result.severity == "merge"
            assert len(result.findings) == 0
            assert result.merge_gate.decision == "approve"
            assert "No relevant architectural changes" in result.summary

    @pytest.mark.asyncio
    async def test_review_includes_system_prompt_and_context_in_message(
        self,
        reviewer,
        sample_context,
        sample_review_output_json
    ):
        """Test that review() includes system prompt and context in message."""
        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value=sample_review_output_json)

        with patch('dawn_kestrel.core.harness.SimpleReviewAgentRunner', return_value=mock_runner):
            result = await reviewer.review(sample_context)

            mock_runner.run_with_retry.assert_called_once()
            assert isinstance(result, ReviewOutput)

    @pytest.mark.asyncio
    async def test_review_with_boundary_violation_finding(
        self,
        reviewer,
        sample_context,
    ):
        """Test that LLM correctly identifies and returns boundary violation findings."""
        boundary_violation_json = """{
            "agent": "architecture",
            "summary": "Found boundary violation",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/controllers/api.py"],
                "ignored_files": [],
                "reasoning": "Architecture review"
            },
            "findings": [
                {
                    "id": "ARCH-BOUNDARY-001",
                    "title": "Boundary violation - cross-layer dependency",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "M",
                    "evidence": "imports from infrastructure.db layer",
                    "risk": "Cross-layer dependencies create tight coupling",
                    "recommendation": "Introduce abstraction layer"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["ARCH-BOUNDARY-001"],
                "should_fix": [],
                "notes_for_coding_agent": []
            }
        }"""

        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value=boundary_violation_json)

        with patch('dawn_kestrel.core.harness.SimpleReviewAgentRunner', return_value=mock_runner):
            result = await reviewer.review(sample_context)

            assert result.severity == "critical"
            assert any(f.id == "ARCH-BOUNDARY-001" for f in result.findings)
            assert result.merge_gate.decision == "needs_changes"

    @pytest.mark.asyncio
    async def test_review_with_circular_dependency_finding(
        self,
        reviewer,
        sample_context,
    ):
        """Test that LLM correctly identifies and returns circular dependency findings."""
        circular_dep_json = """{
            "agent": "architecture",
            "summary": "Found circular dependency",
            "severity": "critical",
            "scope": {
                "relevant_files": ["src/app.py"],
                "ignored_files": [],
                "reasoning": "Architecture review"
            },
            "findings": [
                {
                    "id": "ARCH-CIRCULAR-001",
                    "title": "Circular dependency detected",
                    "severity": "critical",
                    "confidence": "high",
                    "owner": "dev",
                    "estimate": "L",
                    "evidence": "Dependency chain: app -> infrastructure.db -> app",
                    "risk": "Circular dependencies cause runtime failures",
                    "recommendation": "Refactor to break circular dependency"
                }
            ],
            "merge_gate": {
                "decision": "needs_changes",
                "must_fix": ["ARCH-CIRCULAR-001"],
                "should_fix": [],
                "notes_for_coding_agent": []
            }
        }"""

        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value=circular_dep_json)

        with patch('dawn_kestrel.core.harness.SimpleReviewAgentRunner', return_value=mock_runner):
            result = await reviewer.review(sample_context)

            assert result.severity == "critical"
            assert any(f.id == "ARCH-CIRCULAR-001" for f in result.findings)
            assert result.merge_gate.decision == "needs_changes"

    def test_architecture_reviewer_metadata_helpers(self, reviewer):
        """Test that ArchitectureReviewer metadata helpers work correctly."""
        assert reviewer.get_agent_name() == "architecture"
        assert "Architecture Review Subagent" in reviewer.get_system_prompt()
        assert reviewer.get_relevant_file_patterns() == ["**/*.py"]

    @pytest.mark.asyncio
    async def test_review_handles_invalid_json_from_runner(
        self,
        reviewer,
        sample_context
    ):
        """Test that review() returns standardized critical fallback when runner returns invalid JSON."""
        mock_runner = MagicMock()
        mock_runner.run_with_retry = AsyncMock(return_value="invalid json {bad syntax}")

        with patch('dawn_kestrel.core.harness.SimpleReviewAgentRunner', return_value=mock_runner):
            result = await reviewer.review(sample_context)

            assert isinstance(result, ReviewOutput)
            assert result.severity == "critical"
            assert "Error parsing LLM response" in result.summary
            assert len(result.findings) == 0
            assert result.merge_gate.decision == "needs_changes"
            assert "Review LLM response format" in result.merge_gate.notes_for_coding_agent[0]
