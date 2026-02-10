"""Characterization tests that lock current review behavior during refactors."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from dawn_kestrel.agents.review.agents.security import SecurityReviewer
from dawn_kestrel.agents.review.base import BaseReviewerAgent, ReviewContext
from dawn_kestrel.agents.review.contracts import (
    Finding,
    MergeGate,
    ReviewInputs,
    ReviewOutput,
    Scope,
)
from dawn_kestrel.agents.review.orchestrator import PRReviewOrchestrator


class _TimeoutMockReviewer(BaseReviewerAgent):
    def __init__(self, name: str, should_timeout: bool = False):
        self._name = name
        self._should_timeout = should_timeout

    def get_agent_name(self) -> str:
        return self._name

    def get_system_prompt(self) -> str:
        return "mock"

    def get_relevant_file_patterns(self) -> list[str]:
        return ["*.py"]

    def get_allowed_tools(self) -> list[str]:
        return []

    async def review(self, context: ReviewContext) -> ReviewOutput:
        if self._should_timeout:
            raise TimeoutError("simulated timeout")
        return ReviewOutput(
            agent=self._name,
            summary="ok",
            severity="merge",
            scope=Scope(relevant_files=context.changed_files, ignored_files=[], reasoning="ok"),
            checks=[],
            skips=[],
            findings=[],
            merge_gate=MergeGate(
                decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[]
            ),
        )


class _FailingMockReviewer(BaseReviewerAgent):
    def __init__(self, name: str):
        self._name = name

    def get_agent_name(self) -> str:
        return self._name

    def get_system_prompt(self) -> str:
        return "mock"

    def get_relevant_file_patterns(self) -> list[str]:
        return ["*.py"]

    def get_allowed_tools(self) -> list[str]:
        return []

    async def review(self, context: ReviewContext) -> ReviewOutput:
        raise RuntimeError("simulated failure")


@pytest.mark.asyncio
async def test_merge_decision_priority_order_is_blocking_then_critical_then_warning() -> None:
    """Lock merge decision priority order for mixed findings."""
    orchestrator = PRReviewOrchestrator([])

    results = [
        ReviewOutput(
            agent="warning-agent",
            summary="warning",
            severity="warning",
            scope=Scope(relevant_files=[], ignored_files=[], reasoning="warning"),
            checks=[],
            skips=[],
            findings=[
                Finding(
                    id="W001",
                    title="Warning issue",
                    severity="warning",
                    confidence="high",
                    owner="dev",
                    estimate="S",
                    evidence="line",
                    risk="minor",
                    recommendation="fix warning",
                )
            ],
            merge_gate=MergeGate(
                decision="approve_with_warnings",
                must_fix=[],
                should_fix=["warning from merge_gate"],
                notes_for_coding_agent=[],
            ),
        ),
        ReviewOutput(
            agent="critical-agent",
            summary="critical",
            severity="critical",
            scope=Scope(relevant_files=[], ignored_files=[], reasoning="critical"),
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
                    evidence="line",
                    risk="major",
                    recommendation="fix critical",
                )
            ],
            merge_gate=MergeGate(
                decision="needs_changes",
                must_fix=["critical from merge_gate"],
                should_fix=[],
                notes_for_coding_agent=[],
            ),
        ),
        ReviewOutput(
            agent="blocking-agent",
            summary="blocking",
            severity="blocking",
            scope=Scope(relevant_files=[], ignored_files=[], reasoning="blocking"),
            checks=[],
            skips=[],
            findings=[
                Finding(
                    id="B001",
                    title="Blocking issue",
                    severity="blocking",
                    confidence="high",
                    owner="security",
                    estimate="L",
                    evidence="line",
                    risk="severe",
                    recommendation="fix blocking",
                )
            ],
            merge_gate=MergeGate(
                decision="block",
                must_fix=["blocking from merge_gate"],
                should_fix=[],
                notes_for_coding_agent=[],
            ),
        ),
    ]

    decision = orchestrator.compute_merge_decision(results)

    assert decision.decision == "block"
    assert "Critical issue: fix critical" in decision.must_fix
    assert "Blocking issue: fix blocking" in decision.must_fix
    assert "warning from merge_gate" in decision.should_fix
    assert "Warning issue: fix warning" in decision.should_fix


@pytest.mark.asyncio
async def test_timeout_fallback_output_shape_is_stable() -> None:
    """Lock orchestrator timeout fallback shape for refactor safety."""
    orchestrator = PRReviewOrchestrator(
        [_TimeoutMockReviewer("fast"), _TimeoutMockReviewer("slow", should_timeout=True)]
    )

    inputs = ReviewInputs(
        repo_root="/tmp/repo",
        base_ref="main",
        head_ref="feature",
        timeout_seconds=1,
    )

    with (
        patch(
            "dawn_kestrel.agents.review.utils.git.get_changed_files",
            AsyncMock(return_value=["src/file.py"]),
        ),
        patch(
            "dawn_kestrel.agents.review.utils.git.get_diff",
            AsyncMock(return_value="diff content"),
        ),
    ):
        results = await orchestrator.run_subagents_parallel(inputs)

    timeout_result = next(result for result in results if result.agent == "slow")

    assert timeout_result.summary == "Agent timed out"
    assert timeout_result.severity == "critical"
    assert timeout_result.scope.relevant_files == []
    assert timeout_result.scope.ignored_files == []
    assert timeout_result.scope.reasoning == "Timeout"
    assert timeout_result.findings == []
    assert timeout_result.checks == []
    assert timeout_result.skips == []
    assert timeout_result.merge_gate.decision == "needs_changes"
    assert timeout_result.merge_gate.must_fix == []
    assert timeout_result.merge_gate.should_fix == []


@pytest.mark.asyncio
async def test_exception_fallback_output_shape_is_stable() -> None:
    """Lock orchestrator exception fallback shape for refactor safety."""
    orchestrator = PRReviewOrchestrator([_FailingMockReviewer("boom")])

    inputs = ReviewInputs(
        repo_root="/tmp/repo",
        base_ref="main",
        head_ref="feature",
        timeout_seconds=1,
    )

    with (
        patch(
            "dawn_kestrel.agents.review.utils.git.get_changed_files",
            AsyncMock(return_value=["src/file.py"]),
        ),
        patch(
            "dawn_kestrel.agents.review.utils.git.get_diff",
            AsyncMock(return_value="diff content"),
        ),
    ):
        results = await orchestrator.run_subagents_parallel(inputs)

    assert len(results) == 1
    result = results[0]
    assert result.agent == "boom"
    assert result.summary == "Agent failed with exception"
    assert result.severity == "critical"
    assert result.scope.relevant_files == []
    assert result.scope.ignored_files == []
    assert result.scope.reasoning == "Exception"
    assert result.findings == []
    assert result.checks == []
    assert result.skips == []
    assert result.merge_gate.decision == "needs_changes"


@pytest.mark.asyncio
async def test_security_reviewer_skips_llm_for_non_relevant_files() -> None:
    """Lock no-relevant-files behavior for SecurityReviewer."""
    reviewer = SecurityReviewer()
    context = ReviewContext(
        changed_files=["README.md"],
        diff="+ docs only",
        repo_root="/tmp/repo",
    )

    with patch(
        "dawn_kestrel.agents.review.agents.security.SimpleReviewAgentRunner"
    ) as mock_runner_cls:
        result = await reviewer.review(context)

    assert result.agent == "security"
    assert result.summary == "No security-relevant files changed. Security review not applicable."
    assert result.severity == "merge"
    assert result.scope.relevant_files == []
    assert result.scope.reasoning == "No files matched relevance patterns"
    assert result.findings == []
    assert result.merge_gate.decision == "approve"
    assert mock_runner_cls.call_count == 0
