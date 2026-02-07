"""Characterization tests for orchestrator merge decision parity.

These tests lock current behavior to ensure parity before/after refactor.
They are designed to FAIL initially (TDD RED phase) and then pass
after implementation changes preserve the same behavior.

Behaviors characterized:
1. Merge decision priority ordering: blocking > critical > warning > merge
2. Agent timeout fallback output shape
3. No-relevant-files reviewer output behavior (via orchestrator integration)
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from dawn_kestrel.agents.review.base import BaseReviewerAgent, ReviewContext
from dawn_kestrel.agents.review.contracts import (
    Finding,
    MergeGate,
    OrchestratorOutput,
    ReviewInputs,
    ReviewOutput,
    Scope,
)
from dawn_kestrel.agents.review.orchestrator import PRReviewOrchestrator


class TimeoutMockAgent(BaseReviewerAgent):
    """Mock agent that simulates timeout."""

    def __init__(self, agent_name: str):
        self._agent_name = agent_name

    def get_agent_name(self) -> str:
        return self._agent_name

    async def review(self, context: ReviewContext) -> ReviewOutput:
        # Sleep longer than timeout to trigger timeout
        await asyncio.sleep(100)
        raise Exception("Should timeout")

    def get_system_prompt(self) -> str:
        return f"Mock {self._agent_name}"

    def get_relevant_file_patterns(self) -> list[str]:
        return ["*.py"]

    def get_allowed_tools(self) -> list[str]:
        return []


class TestMergeDecisionPriorityOrdering:
    """Characterize merge decision priority: blocking > critical > warning > merge.

    These tests verify the PRD policy is correctly implemented in
    PRReviewOrchestrator.compute_merge_decision().
    """

    @pytest.mark.asyncio
    async def test_blocking_findings_override_critical_and_warning(self):
        """CHARACTERIZATION: Blocking findings result in 'block' decision.

        Even when critical and warning findings are present, blocking findings
        should cause the merge decision to be 'block'.

        PRD Policy: blocking > critical > warning > merge
        """
        orchestrator = PRReviewOrchestrator([])

        results = [
            ReviewOutput(
                agent="agent1",
                summary="Critical issue",
                severity="critical",
                scope=Scope(relevant_files=[], ignored_files=[], reasoning=""),
                checks=[],
                skips=[],
                findings=[
                    Finding(
                        id="C001",
                        title="Critical issue",
                        severity="critical",
                        confidence="high",
                        owner="security",
                        estimate="M",
                        evidence="",
                        risk="",
                        recommendation="Fix critical",
                    )
                ],
                merge_gate=MergeGate(
                    decision="needs_changes", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                ),
            ),
            ReviewOutput(
                agent="agent2",
                summary="Warning issue",
                severity="warning",
                scope=Scope(relevant_files=[], ignored_files=[], reasoning=""),
                checks=[],
                skips=[],
                findings=[
                    Finding(
                        id="W001",
                        title="Warning issue",
                        severity="warning",
                        confidence="medium",
                        owner="dev",
                        estimate="S",
                        evidence="",
                        risk="",
                        recommendation="Fix warning",
                    )
                ],
                merge_gate=MergeGate(
                    decision="needs_changes", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                ),
            ),
            ReviewOutput(
                agent="agent3",
                summary="Blocking issue",
                severity="blocking",
                scope=Scope(relevant_files=[], ignored_files=[], reasoning=""),
                checks=[],
                skips=[],
                findings=[
                    Finding(
                        id="B001",
                        title="Blocking security flaw",
                        severity="blocking",
                        confidence="high",
                        owner="security",
                        estimate="L",
                        evidence="",
                        risk="Critical",
                        recommendation="Fix immediately",
                    )
                ],
                merge_gate=MergeGate(
                    decision="block", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                ),
            ),
        ]

        decision = orchestrator.compute_merge_decision(results)

        # CHARACTERIZATION: Blocking findings should result in 'block' decision
        assert decision.decision == "block", \
            "Blocking findings must result in 'block' decision (PRD policy: blocking > critical > warning > merge)"
        assert len(decision.must_fix) > 0, \
            "Blocking findings should be added to must_fix list"
        # Verify blocking finding is in must_fix
        assert any("Blocking security flaw" in fix for fix in decision.must_fix), \
            "Blocking finding should be in must_fix list"

    @pytest.mark.asyncio
    async def test_critical_findings_result_in_needs_changes(self):
        """CHARACTERIZATION: Critical findings (without blocking) result in 'needs_changes'.

        When critical findings are present but no blocking findings,
        the merge decision should be 'needs_changes'.

        PRD Policy: blocking > critical > warning > merge
        """
        orchestrator = PRReviewOrchestrator([])

        results = [
            ReviewOutput(
                agent="agent1",
                summary="Critical issue",
                severity="critical",
                scope=Scope(relevant_files=[], ignored_files=[], reasoning=""),
                checks=[],
                skips=[],
                findings=[
                    Finding(
                        id="C001",
                        title="Critical security flaw",
                        severity="critical",
                        confidence="high",
                        owner="security",
                        estimate="M",
                        evidence="",
                        risk="High",
                        recommendation="Fix immediately",
                    )
                ],
                merge_gate=MergeGate(
                    decision="needs_changes", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                ),
            ),
        ]

        decision = orchestrator.compute_merge_decision(results)

        # CHARACTERIZATION: Critical findings should result in 'needs_changes' (not 'block')
        assert decision.decision == "needs_changes", \
            "Critical findings (without blocking) should result in 'needs_changes' decision"
        assert len(decision.must_fix) > 0, \
            "Critical findings should be added to must_fix list"
        assert any("Critical security flaw" in fix for fix in decision.must_fix), \
            "Critical finding should be in must_fix list"

    @pytest.mark.asyncio
    async def test_warning_findings_result_in_approve_with_warnings(self):
        """CHARACTERIZATION: Warning findings (without blocking/critical) result in 'approve_with_warnings'.

        When only warning findings are present with no blocking or critical findings,
        the merge decision should be 'approve_with_warnings'.

        PRD Policy: blocking > critical > warning > merge
        """
        orchestrator = PRReviewOrchestrator([])

        results = [
            ReviewOutput(
                agent="agent1",
                summary="Style warnings",
                severity="warning",
                scope=Scope(relevant_files=[], ignored_files=[], reasoning=""),
                checks=[],
                skips=[],
                findings=[
                    Finding(
                        id="W001",
                        title="Line too long",
                        severity="warning",
                        confidence="medium",
                        owner="dev",
                        estimate="S",
                        evidence="",
                        risk="Low",
                        recommendation="Break long line",
                    )
                ],
                merge_gate=MergeGate(
                    decision="needs_changes", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                ),
            ),
        ]

        decision = orchestrator.compute_merge_decision(results)

        # CHARACTERIZATION: Warning findings should result in 'approve_with_warnings'
        assert decision.decision == "approve_with_warnings", \
            "Warning findings (without blocking/critical) should result in 'approve_with_warnings' decision"
        assert len(decision.should_fix) > 0, \
            "Warning findings should be added to should_fix list"
        assert any("Line too long" in fix for fix in decision.should_fix), \
            "Warning finding should be in should_fix list"

    @pytest.mark.asyncio
    async def test_no_findings_result_in_approve(self):
        """CHARACTERIZATION: No findings result in 'approve' decision.

        When no blocking, critical, or warning findings are present,
        the merge decision should be 'approve'.

        PRD Policy: blocking > critical > warning > merge
        """
        orchestrator = PRReviewOrchestrator([])

        results = [
            ReviewOutput(
                agent="agent1",
                summary="No issues",
                severity="merge",
                scope=Scope(relevant_files=[], ignored_files=[], reasoning=""),
                checks=[],
                skips=[],
                findings=[],
                merge_gate=MergeGate(
                    decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[]
                ),
            ),
        ]

        decision = orchestrator.compute_merge_decision(results)

        # CHARACTERIZATION: No findings should result in 'approve'
        assert decision.decision == "approve", \
            "No findings should result in 'approve' decision"
        assert len(decision.must_fix) == 0, \
            "No findings should result in empty must_fix list"
        assert len(decision.should_fix) == 0, \
            "No findings should result in empty should_fix list"


class TestAgentTimeoutFallbackOutputShape:
    """Characterize agent timeout fallback output shape.

    These tests verify that when an agent times out, the orchestrator
    returns a ReviewOutput with specific structure that represents a
    graceful failure mode.
    """

    @pytest.mark.asyncio
    async def test_timeout_returns_critical_severity(self):
        """CHARACTERIZATION: Timeout returns severity='critical'.

        When an agent times out, the fallback ReviewOutput should have
        severity='critical' to indicate a critical failure occurred.
        """
        agents = [TimeoutMockAgent("timeout_agent")]
        orchestrator = PRReviewOrchestrator(agents)

        inputs = ReviewInputs(
            repo_root="/tmp/repo",
            base_ref="main",
            head_ref="feature",
            timeout_seconds=1,  # Short timeout to trigger
        )

        with patch(
            "dawn_kestrel.agents.review.utils.git.get_changed_files",
            AsyncMock(return_value=["src/file.py"]),
        ), patch(
            "dawn_kestrel.agents.review.utils.git.get_diff",
            AsyncMock(return_value="diff content"),
        ):
            results = await orchestrator.run_subagents_parallel(inputs)

        assert len(results) == 1
        timed_out_result = results[0]

        # CHARACTERIZATION: Timeout should result in critical severity
        assert timed_out_result.severity == "critical", \
            "Agent timeout must return severity='critical'"

    @pytest.mark.asyncio
    async def test_timeout_has_correct_summary(self):
        """CHARACTERIZATION: Timeout returns summary='Agent timed out'."""
        agents = [TimeoutMockAgent("timeout_agent")]
        orchestrator = PRReviewOrchestrator(agents)

        inputs = ReviewInputs(
            repo_root="/tmp/repo",
            base_ref="main",
            head_ref="feature",
            timeout_seconds=1,
        )

        with patch(
            "dawn_kestrel.agents.review.utils.git.get_changed_files",
            AsyncMock(return_value=["src/file.py"]),
        ), patch(
            "dawn_kestrel.agents.review.utils.git.get_diff",
            AsyncMock(return_value="diff content"),
        ):
            results = await orchestrator.run_subagents_parallel(inputs)

        timed_out_result = results[0]

        # CHARACTERIZATION: Timeout should have specific summary
        assert "timed out" in timed_out_result.summary.lower(), \
            "Agent timeout summary should contain 'timed out'"

    @pytest.mark.asyncio
    async def test_timeout_scope_structure(self):
        """CHARACTERIZATION: Timeout returns Scope with specific structure.

        When an agent times out, the Scope should have:
        - relevant_files: [] (empty list)
        - ignored_files: [] (empty list)
        - reasoning: "Timeout"
        """
        agents = [TimeoutMockAgent("timeout_agent")]
        orchestrator = PRReviewOrchestrator(agents)

        inputs = ReviewInputs(
            repo_root="/tmp/repo",
            base_ref="main",
            head_ref="feature",
            timeout_seconds=1,
        )

        with patch(
            "dawn_kestrel.agents.review.utils.git.get_changed_files",
            AsyncMock(return_value=["src/file.py"]),
        ), patch(
            "dawn_kestrel.agents.review.utils.git.get_diff",
            AsyncMock(return_value="diff content"),
        ):
            results = await orchestrator.run_subagents_parallel(inputs)

        timed_out_result = results[0]

        # CHARACTERIZATION: Timeout Scope structure
        assert timed_out_result.scope.relevant_files == [], \
            "Timeout scope should have empty relevant_files list"
        assert timed_out_result.scope.ignored_files == [], \
            "Timeout scope should have empty ignored_files list"
        assert timed_out_result.scope.reasoning == "Timeout", \
            "Timeout scope reasoning should be 'Timeout'"

    @pytest.mark.asyncio
    async def test_timeout_has_empty_lists(self):
        """CHARACTERIZATION: Timeout returns empty checks, skips, findings lists.

        When an agent times out, the ReviewOutput should have:
        - checks: [] (empty list)
        - skips: [] (empty list)
        - findings: [] (empty list)
        """
        agents = [TimeoutMockAgent("timeout_agent")]
        orchestrator = PRReviewOrchestrator(agents)

        inputs = ReviewInputs(
            repo_root="/tmp/repo",
            base_ref="main",
            head_ref="feature",
            timeout_seconds=1,
        )

        with patch(
            "dawn_kestrel.agents.review.utils.git.get_changed_files",
            AsyncMock(return_value=["src/file.py"]),
        ), patch(
            "dawn_kestrel.agents.review.utils.git.get_diff",
            AsyncMock(return_value="diff content"),
        ):
            results = await orchestrator.run_subagents_parallel(inputs)

        timed_out_result = results[0]

        # CHARACTERIZATION: Timeout should have empty lists
        assert timed_out_result.checks == [], \
            "Timeout should have empty checks list"
        assert timed_out_result.skips == [], \
            "Timeout should have empty skips list"
        assert timed_out_result.findings == [], \
            "Timeout should have empty findings list"

    @pytest.mark.asyncio
    async def test_timeout_merge_gate_decision(self):
        """CHARACTERIZATION: Timeout returns MergeGate with decision='needs_changes'.

        When an agent times out, the MergeGate should have:
        - decision: "needs_changes"
        - must_fix: [] (empty list)
        - should_fix: [] (empty list)
        - notes_for_coding_agent: [] (empty list)
        """
        agents = [TimeoutMockAgent("timeout_agent")]
        orchestrator = PRReviewOrchestrator(agents)

        inputs = ReviewInputs(
            repo_root="/tmp/repo",
            base_ref="main",
            head_ref="feature",
            timeout_seconds=1,
        )

        with patch(
            "dawn_kestrel.agents.review.utils.git.get_changed_files",
            AsyncMock(return_value=["src/file.py"]),
        ), patch(
            "dawn_kestrel.agents.review.utils.git.get_diff",
            AsyncMock(return_value="diff content"),
        ):
            results = await orchestrator.run_subagents_parallel(inputs)

        timed_out_result = results[0]

        # CHARACTERIZATION: Timeout MergeGate structure
        assert timed_out_result.merge_gate.decision == "needs_changes", \
            "Timeout merge_gate decision should be 'needs_changes'"
        assert timed_out_result.merge_gate.must_fix == [], \
            "Timeout merge_gate should have empty must_fix list"
        assert timed_out_result.merge_gate.should_fix == [], \
            "Timeout merge_gate should have empty should_fix list"
        assert timed_out_result.merge_gate.notes_for_coding_agent == [], \
            "Timeout merge_gate should have empty notes_for_coding_agent list"


class TestNoRelevantFilesReviewerOutputBehavior:
    """Characterize no-relevant-files reviewer output behavior.

    These tests verify that when a reviewer finds no relevant files,
    it returns a ReviewOutput with specific structure indicating
    the review was not applicable.
    """

    @pytest.mark.asyncio
    async def test_security_reviewer_no_relevant_files_returns_merge_severity(self):
        """CHARACTERIZATION: Security reviewer with no relevant files returns severity='merge'.

        When security reviewer pattern matching finds no relevant files,
        the ReviewOutput should have severity='merge' to indicate
        the review is not blocking.
        """
        from dawn_kestrel.agents.review.agents.security import SecurityReviewer

        reviewer = SecurityReviewer()

        # Context with only non-security files
        context = ReviewContext(
            changed_files=["README.md", "docs/guide.md"],
            diff="+ documentation update",
            repo_root="/test/repo",
            base_ref="main",
            head_ref="feature",
        )

        result = await reviewer.review(context)

        # CHARACTERIZATION: No relevant files should result in merge severity
        assert result.severity == "merge", \
            "Security reviewer with no relevant files should return severity='merge'"

    @pytest.mark.asyncio
    async def test_security_reviewer_no_relevant_files_summary(self):
        """CHARACTERIZATION: Security reviewer with no relevant files has specific summary."""
        from dawn_kestrel.agents.review.agents.security import SecurityReviewer

        reviewer = SecurityReviewer()

        context = ReviewContext(
            changed_files=["README.md"],
            diff="+ docs update",
            repo_root="/test/repo",
        )

        result = await reviewer.review(context)

        # CHARACTERIZATION: Summary should indicate no relevant files
        assert "no security-relevant files" in result.summary.lower() or \
               "not applicable" in result.summary.lower(), \
            "Security reviewer summary should indicate no relevant files found"

    @pytest.mark.asyncio
    async def test_security_reviewer_no_relevant_files_merge_gate_approve(self):
        """CHARACTERIZATION: Security reviewer with no relevant files returns approve decision."""
        from dawn_kestrel.agents.review.agents.security import SecurityReviewer

        reviewer = SecurityReviewer()

        context = ReviewContext(
            changed_files=["README.md"],
            diff="+ docs",
            repo_root="/test/repo",
        )

        result = await reviewer.review(context)

        # CHARACTERIZATION: Merge gate should be approve
        assert result.merge_gate.decision == "approve", \
            "Security reviewer with no relevant files should return approve decision"
        assert result.merge_gate.must_fix == [], \
            "No relevant files should result in empty must_fix"
        assert result.merge_gate.should_fix == [], \
            "No relevant files should result in empty should_fix"

    @pytest.mark.asyncio
    async def test_security_reviewer_no_relevant_files_notes(self):
        """CHARACTERIZATION: Security reviewer with no relevant files has specific notes."""
        from dawn_kestrel.agents.review.agents.security import SecurityReviewer

        reviewer = SecurityReviewer()

        context = ReviewContext(
            changed_files=["README.md"],
            diff="+ docs",
            repo_root="/test/repo",
        )

        result = await reviewer.review(context)

        # CHARACTERIZATION: Notes should explain why
        assert len(result.merge_gate.notes_for_coding_agent) > 0, \
            "No relevant files should have explanatory notes"
        note_text = result.merge_gate.notes_for_coding_agent[0]
        assert "no security-relevant" in note_text.lower() or \
               "not changed" in note_text.lower(), \
            "Notes should explain that no security-relevant files were changed"

    @pytest.mark.asyncio
    async def test_security_reviewer_no_relevant_files_empty_findings(self):
        """CHARACTERIZATION: Security reviewer with no relevant files has empty findings."""
        from dawn_kestrel.agents.review.agents.security import SecurityReviewer

        reviewer = SecurityReviewer()

        context = ReviewContext(
            changed_files=["README.md"],
            diff="+ docs",
            repo_root="/test/repo",
        )

        result = await reviewer.review(context)

        # CHARACTERIZATION: No relevant files should have no findings
        assert result.findings == [], \
            "Security reviewer with no relevant files should have empty findings list"
