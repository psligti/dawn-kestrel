"""Tests for review workflow module.

Tests cover:
- Severity: severity levels
- MergeDecision: merge decisions
- Finding: review finding model
- ReviewContext: review context
- ReviewOutput: review output
- ReviewWorkflow: workflow coordination
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.workflow.review import (
    Finding,
    MergeDecision,
    ReviewContext,
    ReviewOutput,
    ReviewWorkflow,
    Severity,
)
from dawn_kestrel.workflow.multi_agent import ExecutionMode


@pytest.fixture
def sample_context() -> ReviewContext:
    """Create a sample ReviewContext for testing."""
    return ReviewContext(
        changed_files=["src/main.py", "tests/test_main.py"],
        diff="diff content",
        repo_root="/repo",
        pr_number=123,
    )


@pytest.fixture
def sample_finding() -> Finding:
    """Create a sample Finding for testing."""
    return Finding(
        id="find-1",
        reviewer="security",
        severity=Severity.WARNING,
        message="Potential security issue",
        location="src/main.py:42",
    )


@pytest.fixture
def workflow() -> ReviewWorkflow:
    """Create a ReviewWorkflow with default settings."""
    return ReviewWorkflow(
        reviewers=["security", "architecture"],
        mode=ExecutionMode.PARALLEL,
    )


class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_values(self) -> None:
        """All severity values should be defined."""
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.CRITICAL.value == "critical"
        assert Severity.BLOCKING.value == "blocking"


class TestMergeDecision:
    """Tests for MergeDecision enum."""

    def test_merge_decision_values(self) -> None:
        """All merge decision values should be defined."""
        assert MergeDecision.APPROVE.value == "approve"
        assert MergeDecision.APPROVE_WITH_WARNINGS.value == "approve_with_warnings"
        assert MergeDecision.NEEDS_CHANGES.value == "needs_changes"
        assert MergeDecision.BLOCK.value == "block"


class TestFinding:
    """Tests for Finding dataclass."""

    def test_create_with_required_fields(self) -> None:
        """Finding should require id, reviewer, severity, message."""
        finding = Finding(
            id="test-1",
            reviewer="test",
            severity=Severity.INFO,
            message="Test finding",
        )

        assert finding.id == "test-1"
        assert finding.reviewer == "test"
        assert finding.severity == Severity.INFO
        assert finding.message == "Test finding"

    def test_default_values(self) -> None:
        """Finding should have defaults for optional fields."""
        finding = Finding(
            id="test-1",
            reviewer="test",
            severity=Severity.INFO,
            message="Test",
        )

        assert finding.location is None
        assert finding.suggestion is None
        assert finding.auto_fix_available is False

    def test_custom_values(self) -> None:
        """Finding should accept custom values."""
        finding = Finding(
            id="test-1",
            reviewer="security",
            severity=Severity.CRITICAL,
            message="Critical issue",
            location="file.py:10",
            suggestion="Fix the issue",
            auto_fix_available=True,
        )

        assert finding.location == "file.py:10"
        assert finding.suggestion == "Fix the issue"
        assert finding.auto_fix_available is True


class TestReviewContext:
    """Tests for ReviewContext dataclass."""

    def test_create_with_required_fields(self) -> None:
        """ReviewContext should require changed_files, diff, repo_root."""
        context = ReviewContext(
            changed_files=["file.py"],
            diff="diff",
            repo_root="/repo",
        )

        assert context.changed_files == ["file.py"]
        assert context.diff == "diff"
        assert context.repo_root == "/repo"

    def test_default_values(self) -> None:
        """ReviewContext should have defaults."""
        context = ReviewContext(
            changed_files=[],
            diff="",
            repo_root="/repo",
        )

        assert context.pr_number is None
        assert context.base_branch == "main"
        assert context.target_branch == "HEAD"
        assert context.metadata == {}

    def test_custom_values(self) -> None:
        """ReviewContext should accept custom values."""
        context = ReviewContext(
            changed_files=["file.py"],
            diff="diff",
            repo_root="/repo",
            pr_number=42,
            base_branch="develop",
            target_branch="feature",
            metadata={"key": "value"},
        )

        assert context.pr_number == 42
        assert context.base_branch == "develop"
        assert context.target_branch == "feature"
        assert context.metadata == {"key": "value"}


class TestReviewOutput:
    """Tests for ReviewOutput dataclass."""

    def test_create_with_required_fields(self, sample_finding: Finding) -> None:
        """ReviewOutput should require all fields."""
        output = ReviewOutput(
            findings=[sample_finding],
            must_fix=[],
            should_fix=[sample_finding],
            merge_decision=MergeDecision.APPROVE,
            confidence=0.95,
            reviewers_run=["security"],
        )

        assert output.findings == [sample_finding]
        assert output.merge_decision == MergeDecision.APPROVE
        assert output.confidence == 0.95

    def test_total_findings_auto_calculated(self, sample_finding: Finding) -> None:
        """total_findings should be auto-calculated in __post_init__."""
        output = ReviewOutput(
            findings=[sample_finding, sample_finding],
            must_fix=[],
            should_fix=[sample_finding, sample_finding],
            merge_decision=MergeDecision.APPROVE,
            confidence=1.0,
            reviewers_run=["security"],
        )

        assert output.total_findings == 2


class TestReviewWorkflow:
    """Tests for ReviewWorkflow class."""

    def test_core_reviewers_defined(self) -> None:
        """CORE_REVIEWERS should be defined."""
        assert "security" in ReviewWorkflow.CORE_REVIEWERS
        assert "architecture" in ReviewWorkflow.CORE_REVIEWERS

    def test_optional_reviewers_defined(self) -> None:
        """OPTIONAL_REVIEWERS should be defined."""
        assert "diff_scoper" in ReviewWorkflow.OPTIONAL_REVIEWERS

    def test_create_with_custom_reviewers(self) -> None:
        """ReviewWorkflow should accept custom reviewer list."""
        workflow = ReviewWorkflow(reviewers=["security", "docs"])

        assert workflow.reviewers == ["security", "docs"]

    def test_create_with_default_reviewers(self) -> None:
        """ReviewWorkflow should use core reviewers by default."""
        workflow = ReviewWorkflow()

        assert workflow.reviewers == ReviewWorkflow.CORE_REVIEWERS

    def test_create_with_optional_reviewers(self) -> None:
        """ReviewWorkflow should include optional reviewers when requested."""
        workflow = ReviewWorkflow(include_optional=True)

        for reviewer in ReviewWorkflow.OPTIONAL_REVIEWERS:
            assert reviewer in workflow.reviewers

    def test_custom_timeout(self) -> None:
        """ReviewWorkflow should accept custom timeout."""
        workflow = ReviewWorkflow(timeout_per_reviewer=120.0)

        assert workflow.timeout_per_reviewer == 120.0

    @pytest.mark.asyncio
    async def test_review_returns_output(
        self, workflow: ReviewWorkflow, sample_context: ReviewContext
    ) -> None:
        """review should return ReviewOutput."""
        output = await workflow.review(sample_context)

        assert isinstance(output, ReviewOutput)

    @pytest.mark.asyncio
    async def test_review_tracks_reviewers_run(
        self, workflow: ReviewWorkflow, sample_context: ReviewContext
    ) -> None:
        """review should track which reviewers ran."""
        output = await workflow.review(sample_context)

        assert len(output.reviewers_run) == len(workflow.reviewers)

    @pytest.mark.asyncio
    async def test_review_computes_merge_decision(
        self, workflow: ReviewWorkflow, sample_context: ReviewContext
    ) -> None:
        """review should compute merge decision."""
        output = await workflow.review(sample_context)

        assert isinstance(output.merge_decision, MergeDecision)

    @pytest.mark.asyncio
    async def test_review_computes_confidence(
        self, workflow: ReviewWorkflow, sample_context: ReviewContext
    ) -> None:
        """review should compute confidence score."""
        output = await workflow.review(sample_context)

        assert 0.0 <= output.confidence <= 1.0


class TestMergeDecisionLogic:
    """Tests for merge decision computation."""

    def test_block_on_blocking_finding(self) -> None:
        """Merge decision should be BLOCK for blocking findings."""
        workflow = ReviewWorkflow()
        findings = [
            Finding(
                id="1",
                reviewer="test",
                severity=Severity.BLOCKING,
                message="Blocking",
            )
        ]

        decision = workflow._compute_merge_decision(findings)
        assert decision == MergeDecision.BLOCK

    def test_needs_changes_on_critical(self) -> None:
        """Merge decision should be NEEDS_CHANGES for critical findings."""
        workflow = ReviewWorkflow()
        findings = [
            Finding(
                id="1",
                reviewer="test",
                severity=Severity.CRITICAL,
                message="Critical",
            )
        ]

        decision = workflow._compute_merge_decision(findings)
        assert decision == MergeDecision.NEEDS_CHANGES

    def test_approve_with_warnings(self) -> None:
        """Merge decision should be APPROVE_WITH_WARNINGS for warnings."""
        workflow = ReviewWorkflow()
        findings = [
            Finding(
                id="1",
                reviewer="test",
                severity=Severity.WARNING,
                message="Warning",
            )
        ]

        decision = workflow._compute_merge_decision(findings)
        assert decision == MergeDecision.APPROVE_WITH_WARNINGS

    def test_approve_no_issues(self) -> None:
        """Merge decision should be APPROVE when no issues."""
        workflow = ReviewWorkflow()
        findings: list[Finding] = []

        decision = workflow._compute_merge_decision(findings)
        assert decision == MergeDecision.APPROVE

    def test_approve_only_info(self) -> None:
        """Merge decision should be APPROVE when only info findings."""
        workflow = ReviewWorkflow()
        findings = [
            Finding(
                id="1",
                reviewer="test",
                severity=Severity.INFO,
                message="Info",
            )
        ]

        decision = workflow._compute_merge_decision(findings)
        assert decision == MergeDecision.APPROVE


class TestFindingsCategorization:
    """Tests for findings categorization."""

    def test_categorize_must_fix(self) -> None:
        """Blocking and critical findings should be must-fix."""
        workflow = ReviewWorkflow()
        findings = [
            Finding(
                id="1",
                reviewer="test",
                severity=Severity.BLOCKING,
                message="Block",
            ),
            Finding(
                id="2",
                reviewer="test",
                severity=Severity.CRITICAL,
                message="Critical",
            ),
        ]

        must_fix, should_fix = workflow._categorize_findings(findings)

        assert len(must_fix) == 2
        assert len(should_fix) == 0

    def test_categorize_should_fix(self) -> None:
        """Warning and info findings should be should-fix."""
        workflow = ReviewWorkflow()
        findings = [
            Finding(
                id="1",
                reviewer="test",
                severity=Severity.WARNING,
                message="Warning",
            ),
            Finding(
                id="2",
                reviewer="test",
                severity=Severity.INFO,
                message="Info",
            ),
        ]

        must_fix, should_fix = workflow._categorize_findings(findings)

        assert len(must_fix) == 0
        assert len(should_fix) == 2


class TestConfidenceComputation:
    """Tests for confidence score computation."""

    def test_confidence_all_success(self) -> None:
        """Confidence should be 1.0 when all reviewers succeed."""
        from dawn_kestrel.workflow.multi_agent import (
            AgentExecutionResult,
            ExecutionStatus,
            WorkflowResult,
        )

        workflow = ReviewWorkflow()
        result = WorkflowResult(
            success=True,
            agent_results={
                "r1": AgentExecutionResult(
                    agent_name="r1",
                    status=ExecutionStatus.COMPLETED,
                ),
                "r2": AgentExecutionResult(
                    agent_name="r2",
                    status=ExecutionStatus.COMPLETED,
                ),
            },
        )

        confidence = workflow._compute_confidence(result)
        assert confidence == 1.0

    def test_confidence_partial_success(self) -> None:
        """Confidence should reflect partial success rate."""
        from dawn_kestrel.workflow.multi_agent import (
            AgentExecutionResult,
            ExecutionStatus,
            WorkflowResult,
        )

        workflow = ReviewWorkflow()
        result = WorkflowResult(
            success=True,
            agent_results={
                "r1": AgentExecutionResult(
                    agent_name="r1",
                    status=ExecutionStatus.COMPLETED,
                ),
                "r2": AgentExecutionResult(
                    agent_name="r2",
                    status=ExecutionStatus.FAILED,
                    error="Failed",
                ),
            },
        )

        confidence = workflow._compute_confidence(result)
        assert confidence == 0.5

    def test_confidence_no_results(self) -> None:
        """Confidence should be 0.0 with no results."""
        from dawn_kestrel.workflow.multi_agent import WorkflowResult

        workflow = ReviewWorkflow()
        result = WorkflowResult(success=True, agent_results={})

        confidence = workflow._compute_confidence(result)
        assert confidence == 0.0
