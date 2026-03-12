"""Review workflow specialization for code review.

This module provides a specialized multi-agent workflow for code review,
implementing the pattern from iron-rook's PRReviewOrchestrator with
11 specialized reviewers.

The review workflow coordinates multiple specialized agents to analyze
different aspects of a PR (security, architecture, documentation, etc.).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from dawn_kestrel.workflow.multi_agent import (
    AggregationSpec,
    AggregationStrategy,
    AgentExecutionResult,
    AgentSpec,
    ConflictResolution,
    ExecutionMode,
    FindingsAggregator,
    MultiAgentWorkflow,
    WorkflowResult,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Severity levels for review findings."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKING = "blocking"


class MergeDecision(str, Enum):
    """Merge decision options."""

    APPROVE = "approve"
    APPROVE_WITH_WARNINGS = "approve_with_warnings"
    NEEDS_CHANGES = "needs_changes"
    BLOCK = "block"


@dataclass
class Finding:
    """A finding from a reviewer agent.

    Attributes:
        id: Unique identifier for the finding
        reviewer: Name of the reviewer agent
        severity: Severity level
        message: Human-readable description
        location: File path and line numbers
        suggestion: Optional fix suggestion
        auto_fix_available: Whether this can be auto-fixed
    """

    id: str
    reviewer: str
    severity: Severity
    message: str
    location: str | None = None
    suggestion: str | None = None
    auto_fix_available: bool = False


@dataclass
class ReviewContext:
    """Context for a code review.

    Attributes:
        changed_files: List of changed file paths
        diff: The PR diff content
        repo_root: Repository root path
        pr_number: Optional PR number
        base_branch: Base branch name
        target_branch: Target branch name
        metadata: Additional metadata
    """

    changed_files: list[str]
    diff: str
    repo_root: str
    pr_number: int | None = None
    base_branch: str = "main"
    target_branch: str = "HEAD"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewOutput:
    """Output from a review workflow.

    Attributes:
        findings: All findings from reviewers
        must_fix: Findings that must be fixed before merge
        should_fix: Findings that should be fixed but are not blocking
        merge_decision: Final merge decision
        confidence: Confidence in the review (0.0-1.0)
        reviewers_run: List of reviewers that were executed
        total_findings: Total number of findings
    """

    findings: list[Finding]
    must_fix: list[Finding]
    should_fix: list[Finding]
    merge_decision: MergeDecision
    confidence: float
    reviewers_run: list[str]
    total_findings: int = 0

    def __post_init__(self):
        self.total_findings = len(self.findings)


class ReviewWorkflow:
    """Multi-agent workflow specialized for code review.

    This implements the pattern from iron-rook's PRReviewOrchestrator,
    coordinating 11 specialized reviewer agents to analyze different
    aspects of a PR.

    Core reviewers (always run):
    - architecture: Code structure and design patterns
    - security: Security vulnerabilities and risks
    - documentation: Doc coverage and quality
    - telemetry_metrics: Metrics and observability
    - linting: Code style and formatting
    - unit_tests: Test coverage and quality

    Optional reviewers (conditional):
    - diff_scoper: Scope analysis
    - requirements: Requirements coverage
    - performance_reliability: Performance issues
    - dependency_license: Dependency checks
    - release_changelog: Release notes

    Example:
        workflow = ReviewWorkflow(
            reviewers=["security", "architecture", "docs"],
            mode=ExecutionMode.PARALLEL,
        )

        result = await workflow.review(context)
        if result.merge_decision == MergeDecision.APPROVE:
            print("PR is ready to merge")
    """

    CORE_REVIEWERS = [
        "architecture",
        "security",
        "documentation",
        "telemetry_metrics",
        "linting",
        "unit_tests",
    ]

    OPTIONAL_REVIEWERS = [
        "diff_scoper",
        "requirements",
        "performance_reliability",
        "dependency_license",
        "release_changelog",
    ]

    def __init__(
        self,
        reviewers: list[str] | None = None,
        mode: ExecutionMode = ExecutionMode.PARALLEL,
        timeout_per_reviewer: float = 60.0,
        include_optional: bool = False,
    ):
        """Initialize the review workflow.

        Args:
            reviewers: Specific reviewers to use (None = all core)
            mode: Execution mode (PARALLEL recommended)
            timeout_per_reviewer: Timeout in seconds per reviewer
            include_optional: Include optional reviewers
        """
        if reviewers is None:
            reviewers = self.CORE_REVIEWERS.copy()
            if include_optional:
                reviewers.extend(self.OPTIONAL_REVIEWERS)

        self.reviewers = reviewers
        self.mode = mode
        self.timeout_per_reviewer = timeout_per_reviewer

        self._workflow = MultiAgentWorkflow[ReviewContext, dict[str, Any]](
            agents=[
                AgentSpec(
                    name=reviewer,
                    agent=self._create_reviewer_agent(reviewer),
                    timeout_seconds=timeout_per_reviewer,
                )
                for reviewer in reviewers
            ],
            execution_mode=mode,
            aggregation=AggregationSpec(
                strategy=AggregationStrategy.MERGE,
                conflict_resolution=ConflictResolution.HIGHEST_SEVERITY,
            ),
        )

    def _create_reviewer_agent(self, name: str) -> Any:
        """Create a reviewer agent by name.

        This is a factory method that returns a simple callable
        that can be executed by the workflow.
        """

        async def review_agent(input: ReviewContext, context: dict[str, Any]) -> dict[str, Any]:
            return {
                "reviewer": name,
                "findings": [],
                "status": "completed",
            }

        review_agent.__name__ = f"{name}_reviewer"
        return review_agent

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Execute the review workflow.

        Args:
            context: Review context with PR information

        Returns:
            ReviewOutput with findings and merge decision
        """
        logger.info(f"Starting review with {len(self.reviewers)} reviewers")

        result: WorkflowResult[dict[str, Any]] = await self._workflow.execute(
            input=context,
            context={"repo_root": context.repo_root},
        )

        all_findings = self._extract_findings(result)
        must_fix, should_fix = self._categorize_findings(all_findings)
        merge_decision = self._compute_merge_decision(all_findings)
        confidence = self._compute_confidence(result)

        return ReviewOutput(
            findings=all_findings,
            must_fix=must_fix,
            should_fix=should_fix,
            merge_decision=merge_decision,
            confidence=confidence,
            reviewers_run=result.execution_order,
        )

    def _extract_findings(self, result: WorkflowResult[dict[str, Any]]) -> list[Finding]:
        """Extract all findings from workflow results."""
        findings = []

        for reviewer_name, agent_result in result.agent_results.items():
            if not agent_result.is_success or agent_result.output is None:
                continue

            output = agent_result.output
            if isinstance(output, dict) and "findings" in output:
                for finding_data in output["findings"]:
                    if isinstance(finding_data, dict):
                        findings.append(
                            Finding(
                                id=finding_data.get("id", f"{reviewer_name}_{len(findings)}"),
                                reviewer=reviewer_name,
                                severity=Severity(finding_data.get("severity", "info")),
                                message=finding_data.get("message", ""),
                                location=finding_data.get("location"),
                                suggestion=finding_data.get("suggestion"),
                                auto_fix_available=finding_data.get("auto_fix_available", False),
                            )
                        )

        return findings

    def _categorize_findings(self, findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
        """Categorize findings into must-fix and should-fix."""
        must_fix = []
        should_fix = []

        for finding in findings:
            if finding.severity in (Severity.BLOCKING, Severity.CRITICAL):
                must_fix.append(finding)
            else:
                should_fix.append(finding)

        return must_fix, should_fix

    def _compute_merge_decision(self, findings: list[Finding]) -> MergeDecision:
        """Compute merge decision based on findings."""
        severities = [f.severity for f in findings]

        if Severity.BLOCKING in severities:
            return MergeDecision.BLOCK
        elif Severity.CRITICAL in severities:
            return MergeDecision.NEEDS_CHANGES
        elif Severity.WARNING in severities:
            return MergeDecision.APPROVE_WITH_WARNINGS
        else:
            return MergeDecision.APPROVE

    def _compute_confidence(self, result: WorkflowResult[dict[str, Any]]) -> float:
        """Compute confidence score based on execution results."""
        if not result.agent_results:
            return 0.0

        successful = sum(1 for r in result.agent_results.values() if r.is_success)
        total = len(result.agent_results)

        return successful / total if total > 0 else 0.0


__all__ = [
    "Severity",
    "MergeDecision",
    "Finding",
    "ReviewContext",
    "ReviewOutput",
    "ReviewWorkflow",
]
