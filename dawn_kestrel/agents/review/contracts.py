"""Review agent contracts and data models.

Defines the data models for review agent outputs, including ReviewOutput,
Finding, Scope, MergeGate, Check, and Skip.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for review findings and overall review."""

    CRITICAL = "critical"
    """Critical issues that must block merge"""

    WARNING = "warning"
    """Warning-level issues that should be fixed"""

    INFO = "info"
    """Informational findings"""

    MERGE = "merge"
    """Ready to merge (no significant issues)"""


class Confidence(str, Enum):
    """Confidence levels for review findings."""

    HIGH = "high"
    """High confidence in the finding"""

    MEDIUM = "medium"
    """Medium confidence"""

    LOW = "low"
    """Low confidence"""


class Estimate(str, Enum):
    """Effort estimates for fixing findings."""

    XS = "XS"
    """Extra small (minutes)"""

    S = "S"
    """Small (< 1 hour)"""

    M = "M"
    """Medium (1-4 hours)"""

    L = "L"
    """Large (1-2 days)"""


class MergeDecision(str, Enum):
    """Merge gate decision types."""

    APPROVE = "approve"
    """Approve merge"""

    APPROVE_WITH_WARNINGS = "approve_with_warnings"
    """Approve but note warnings"""

    NEEDS_CHANGES = "needs_changes"
    """Request changes before merge"""

    BLOCK = "block"
    """Block merge"""


class Scope(BaseModel):
    """Scope of the review - which files were relevant and why."""

    relevant_files: list[str] = Field(
        default_factory=list,
        description="Files relevant to the review",
    )
    """Files that matched the agent's relevance patterns"""

    ignored_files: list[str] = Field(
        default_factory=list,
        description="Files ignored by the review",
    )
    """Files that didn't match the agent's relevance patterns"""

    reasoning: str = Field(
        description="Explanation of scope and relevance decisions",
    )
    """Why these files were selected for review"""

    model_config = {"extra": "forbid"}


class Check(BaseModel):
    """A check performed by the agent."""

    name: str = Field(description="Name of the check")
    """Human-readable check name"""

    required: bool = Field(description="Whether this check must pass")
    """True if merge depends on this check passing"""

    commands: list[str] = Field(
        default_factory=list,
        description="Commands or steps to perform the check",
    )
    """Shell commands, analyzer calls, or other check procedures"""

    why: str = Field(description="Why this check is important")
    """Rationale for including this check"""

    expected_signal: str | None = Field(
        default=None,
        description="Expected output if check passes",
    )
    """What to look for to confirm the check passed"""

    model_config = {"extra": "forbid"}


class Skip(BaseModel):
    """A check that was skipped with justification."""

    name: str = Field(description="Name of the skipped check")
    """Which check was skipped"""

    why_safe: str = Field(description="Why skipping is safe")
    """Justification for why skipping doesn't compromise review quality"""

    when_to_run: str = Field(description="When this check should be run instead")
    """Conditions under which this check would be relevant"""

    model_config = {"extra": "forbid"}


class Finding(BaseModel):
    """A single finding from a review."""

    id: str = Field(description="Unique identifier for the finding")
    """e.g., SEC-001, PERF-045"""

    title: str = Field(description="Human-readable title")
    """Brief description of the issue"""

    severity: Severity = Field(description="Severity level")
    """How serious the issue is"""

    confidence: Confidence = Field(description="Confidence level")
    """How confident the agent is in this finding"""

    owner: str = Field(description="Team or owner responsible")
    """Who should fix this (e.g., 'security', 'performance', 'docs')"""

    estimate: Estimate = Field(description="Effort estimate")
    """How long to fix"""

    evidence: str = Field(description="Evidence supporting the finding")
    """Specific diff content, line numbers, code examples"""

    risk: str = Field(description="Explanation of the risk")
    """What could go wrong if this isn't fixed"""

    recommendation: str = Field(description="Suggested fix approach")
    """How to resolve the issue"""

    suggested_patch: str | None = Field(
        default=None,
        description="Concrete code patch suggestion",
    )
    """Optional specific code fix"""

    model_config = {"extra": "forbid"}


class MergeGate(BaseModel):
    """Merge gate decision and blocking conditions."""

    decision: MergeDecision = Field(description="Merge decision")
    """approve, approve_with_warnings, needs_changes, or block"""

    must_fix: list[str] = Field(
        default_factory=list,
        description="Finding IDs that must be fixed before merge",
    )
    """Critical findings that block merge"""

    should_fix: list[str] = Field(
        default_factory=list,
        description="Finding IDs that should ideally be fixed",
    )
    """Non-blocking findings that should be addressed"""

    notes_for_coding_agent: list[str] = Field(
        default_factory=list,
        description="Notes to provide to the coding agent",
    )
    """Context and guidance for the agent making the fixes"""

    model_config = {"extra": "forbid"}


class ReviewOutput(BaseModel):
    """Complete output from a review agent.

    This is the contract between review agents and the orchestrator.
    Agents must return this structure with their findings and merge decision.
    """

    agent: str = Field(description="Name of the agent")
    """Which agent produced this review"""

    summary: str = Field(description="High-level summary of the review")
    """One or two sentence overview"""

    severity: Severity = Field(description="Overall severity")
    """Highest severity of findings, or 'merge' if no significant issues"""

    scope: Scope = Field(description="Scope of the review")
    """Which files were reviewed and why"""

    checks: list[Check] = Field(
        default_factory=list,
        description="Checks performed by the agent",
    )
    """Analyzers, scans, and verifications executed"""

    skips: list[Skip] = Field(
        default_factory=list,
        description="Checks skipped with justification",
    )
    """Checks that were intentionally not performed"""

    findings: list[Finding] = Field(
        default_factory=list,
        description="Findings from the review",
    )
    """Issues discovered during review"""

    merge_gate: MergeGate = Field(description="Merge gate decision")
    """Whether to approve and what needs fixing"""

    model_config = {"extra": "forbid"}
