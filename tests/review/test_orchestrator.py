"""Tests for PRReviewOrchestrator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dawn_kestrel.agents.review.base import BaseReviewerAgent, ReviewContext
from dawn_kestrel.agents.review.contracts import (
    Check,
    Finding,
    MergeGate,
    OrchestratorOutput,
    ReviewInputs,
    ReviewOutput,
    Scope,
    Skip,
    ToolPlan,
)
from dawn_kestrel.agents.review.orchestrator import PRReviewOrchestrator
from dawn_kestrel.agents.review.streaming import ReviewStreamManager
from dawn_kestrel.agents.review.utils.executor import CommandExecutor, ExecutionResult


class MockReviewerAgent(BaseReviewerAgent):

    def __init__(
        self,
        agent_name: str,
        output: ReviewOutput | None = None,
        should_timeout: bool = False,
        should_fail: bool = False,
    ):
        self._agent_name = agent_name
        self._output = output
        self._should_timeout = should_timeout
        self._should_fail = should_fail

    def get_agent_name(self) -> str:
        return self._agent_name

    async def review(self, context: ReviewContext) -> ReviewOutput:
        if self._should_timeout:
            await asyncio.sleep(10)
            raise Exception("Should timeout")

        if self._should_fail:
            raise RuntimeError("Simulated agent failure")

        if self._output:
            return self._output

        return ReviewOutput(
            agent=self._agent_name,
            summary=f"Mock review by {self._agent_name}",
            severity="merge",
            scope=Scope(
                relevant_files=context.changed_files,
                ignored_files=[],
                reasoning="Mock review",
            ),
            checks=[],
            skips=[],
            findings=[],
            merge_gate=MergeGate(
                decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[]
            ),
        )

    def get_system_prompt(self) -> str:
        return f"Mock system prompt for {self._agent_name}"

    def get_relevant_file_patterns(self) -> list[str]:
        return ["*.py"]


@pytest.fixture
def mock_command_executor():
    executor = MagicMock(spec=CommandExecutor)
    executor.execute = AsyncMock(return_value=ExecutionResult(
        command="pytest",
        exit_code=0,
        stdout="PASSED",
        stderr="",
        timeout=False,
        duration_seconds=0.5,
    ))
    return executor


@pytest.fixture
def mock_stream_manager():
    manager = MagicMock(spec=ReviewStreamManager)
    manager.start_stream = AsyncMock()
    manager.emit_progress = AsyncMock()
    manager.emit_result = AsyncMock()
    manager.emit_error = AsyncMock()
    return manager


@pytest.fixture
def sample_review_outputs():
    return [
        ReviewOutput(
            agent="security",
            summary="Security review",
            severity="merge",
            scope=Scope(
                relevant_files=["src/file.py"],
                ignored_files=[],
                reasoning="Security check",
            ),
            checks=[],
            skips=[],
            findings=[],
            merge_gate=MergeGate(
                decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[]
            ),
        ),
        ReviewOutput(
            agent="linting",
            summary="Linting review",
            severity="warning",
            scope=Scope(
                relevant_files=["src/file.py"],
                ignored_files=[],
                reasoning="Linting check",
            ),
            checks=[],
            skips=[],
            findings=[
                Finding(
                    id="LINT001",
                    title="Line too long",
                    severity="warning",
                    confidence="high",
                    owner="dev",
                    estimate="S",
                    evidence="Line 100 exceeds 88 characters",
                    risk="Code readability",
                    recommendation="Break long line",
                )
            ],
            merge_gate=MergeGate(
                decision="needs_changes",
                must_fix=[],
                should_fix=["Fix line length"],
                notes_for_coding_agent=[],
            ),
        ),
    ]


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    agents = [MockReviewerAgent("agent1"), MockReviewerAgent("agent2")]
    orchestrator = PRReviewOrchestrator(agents)

    assert orchestrator.subagents == agents
    assert isinstance(orchestrator.command_executor, CommandExecutor)
    assert isinstance(orchestrator.stream_manager, ReviewStreamManager)


@pytest.mark.asyncio
async def test_orchestrator_with_custom_dependencies(mock_command_executor, mock_stream_manager):
    agents = [MockReviewerAgent("agent1")]
    orchestrator = PRReviewOrchestrator(
        agents, command_executor=mock_command_executor, stream_manager=mock_stream_manager
    )

    assert orchestrator.command_executor == mock_command_executor
    assert orchestrator.stream_manager == mock_stream_manager


@pytest.mark.asyncio
async def test_run_subagents_parallel_success():

    agents = [
        MockReviewerAgent("agent1"),
        MockReviewerAgent("agent2"),
        MockReviewerAgent("agent3"),
    ]
    orchestrator = PRReviewOrchestrator(agents)

    inputs = ReviewInputs(
        repo_root="/tmp/repo",
        base_ref="main",
        head_ref="feature",
        timeout_seconds=60,
    )

    with patch(
        "dawn_kestrel.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=["src/file.py"]),
    ), patch(
        "dawn_kestrel.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        results = await orchestrator.run_subagents_parallel(inputs)

    assert len(results) == 3
    assert all(r.agent.startswith("agent") for r in results)
    assert all(r.severity == "merge" for r in results)


@pytest.mark.asyncio
async def test_run_subagents_parallel_with_timeout():

    agents = [
        MockReviewerAgent("agent1"),
        MockReviewerAgent("agent2", should_timeout=True),
        MockReviewerAgent("agent3"),
    ]
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

    assert len(results) == 3
    assert results[0].severity == "merge"
    assert results[1].severity == "critical"
    assert "timed out" in results[1].summary
    assert results[2].severity == "merge"


@pytest.mark.asyncio
async def test_run_subagents_parallel_with_exception():

    agents = [
        MockReviewerAgent("agent1"),
        MockReviewerAgent("agent2", should_fail=True),
        MockReviewerAgent("agent3"),
    ]
    orchestrator = PRReviewOrchestrator(agents)

    inputs = ReviewInputs(
        repo_root="/tmp/repo",
        base_ref="main",
        head_ref="feature",
        timeout_seconds=60,
    )

    with patch(
        "dawn_kestrel.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=["src/file.py"]),
    ), patch(
        "dawn_kestrel.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        results = await orchestrator.run_subagents_parallel(inputs)

    assert len(results) == 3
    assert results[0].severity == "merge"
    assert results[1].severity == "critical"
    assert "failed" in results[1].summary
    assert results[2].severity == "merge"


@pytest.mark.asyncio
async def test_run_subagents_parallel_with_streaming(mock_stream_manager):

    agents = [MockReviewerAgent("agent1")]
    orchestrator = PRReviewOrchestrator(agents, stream_manager=mock_stream_manager)

    inputs = ReviewInputs(
        repo_root="/tmp/repo",
        base_ref="main",
        head_ref="feature",
        timeout_seconds=60,
    )

    with patch(
        "dawn_kestrel.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=["src/file.py"]),
    ), patch(
        "dawn_kestrel.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        results = await orchestrator.run_subagents_parallel(
            inputs, stream_callback=lambda x: None
        )

    assert len(results) == 1
    mock_stream_manager.emit_progress.assert_called_once()
    mock_stream_manager.emit_result.assert_called_once()


@pytest.mark.asyncio
async def test_execute_command_delegates_to_executor(mock_command_executor):

    orchestrator = PRReviewOrchestrator(
        [], command_executor=mock_command_executor
    )

    result = await orchestrator.execute_command("pytest", timeout=30)

    mock_command_executor.execute.assert_called_once_with("pytest", timeout=30)
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_compute_merge_decision_approve():

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
        )
    ]

    decision = orchestrator.compute_merge_decision(results)

    assert decision.decision == "approve"
    assert len(decision.must_fix) == 0
    assert len(decision.should_fix) == 0


@pytest.mark.asyncio
async def test_compute_merge_decision_needs_changes():

    orchestrator = PRReviewOrchestrator([])

    results = [
        ReviewOutput(
            agent="agent1",
            summary="Warnings found",
            severity="warning",
            scope=Scope(relevant_files=[], ignored_files=[], reasoning=""),
            checks=[],
            skips=[],
            findings=[
                Finding(
                    id="W001",
                    title="Warning",
                    severity="warning",
                    confidence="high",
                    owner="dev",
                    estimate="S",
                    evidence="",
                    risk="",
                    recommendation="Fix warning",
                )
            ],
            merge_gate=MergeGate(
                decision="needs_changes",
                must_fix=[],
                should_fix=["Fix warning"],
                notes_for_coding_agent=[],
            ),
        )
    ]

    decision = orchestrator.compute_merge_decision(results)

    assert decision.decision == "approve_with_warnings"
    assert len(decision.must_fix) == 0
    assert len(decision.should_fix) == 2


@pytest.mark.asyncio
async def test_compute_merge_decision_block():

    orchestrator = PRReviewOrchestrator([])

    results = [
        ReviewOutput(
            agent="agent1",
            summary="Blocking issue",
            severity="blocking",
            scope=Scope(relevant_files=[], ignored_files=[], reasoning=""),
            checks=[],
            skips=[],
            findings=[
                Finding(
                    id="B001",
                    title="Security flaw",
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
                decision="block",
                must_fix=["Fix security flaw"],
                should_fix=[],
                notes_for_coding_agent=[],
            ),
        )
    ]

    decision = orchestrator.compute_merge_decision(results)

    assert decision.decision == "block"
    assert len(decision.must_fix) == 2
    assert len(decision.should_fix) == 0


@pytest.mark.asyncio
async def test_dedupe_findings():

    orchestrator = PRReviewOrchestrator([])

    findings = [
        Finding(
            id="F001",
            title="Duplicate finding",
            severity="warning",
            confidence="high",
            owner="dev",
            estimate="S",
            evidence="",
            risk="",
            recommendation="Fix",
        ),
        Finding(
            id="F001",
            title="Duplicate finding",
            severity="warning",
            confidence="high",
            owner="dev",
            estimate="S",
            evidence="",
            risk="",
            recommendation="Fix",
        ),
        Finding(
            id="F002",
            title="Different finding",
            severity="critical",
            confidence="high",
            owner="security",
            estimate="M",
            evidence="",
            risk="",
            recommendation="Fix",
        ),
    ]

    deduped = orchestrator.dedupe_findings(findings)

    assert len(deduped) == 2
    assert deduped[0].id == "F001"
    assert deduped[1].id == "F002"


@pytest.mark.asyncio
async def test_generate_tool_plan():

    orchestrator = PRReviewOrchestrator([])

    results = [
        ReviewOutput(
            agent="agent1",
            summary="Linting review",
            severity="warning",
            scope=Scope(relevant_files=[], ignored_files=[], reasoning=""),
            checks=[
                Check(
                    name="ruff check",
                    required=True,
                    commands=["ruff check"],
                    why="Linting",
                )
            ],
            skips=[],
            findings=[],
            merge_gate=MergeGate(
                decision="needs_changes", must_fix=[], should_fix=[], notes_for_coding_agent=[]
            ),
        )
    ]

    tool_plan = orchestrator.generate_tool_plan(results)

    assert tool_plan.auto_fix_available is True
    assert len(tool_plan.proposed_commands) == 1
    assert tool_plan.proposed_commands[0] == "ruff check"


@pytest.mark.asyncio
async def test_run_review_full_workflow(sample_review_outputs):

    agent1 = MockReviewerAgent("agent1", output=sample_review_outputs[0])
    agent2 = MockReviewerAgent("agent2", output=sample_review_outputs[1])
    orchestrator = PRReviewOrchestrator([agent1, agent2])

    inputs = ReviewInputs(
        repo_root="/tmp/repo",
        base_ref="main",
        head_ref="feature",
        timeout_seconds=60,
    )

    with patch(
        "dawn_kestrel.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=["src/file.py"]),
    ), patch(
        "dawn_kestrel.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        output = await orchestrator.run_review(inputs)

    assert isinstance(output, OrchestratorOutput)
    assert output.merge_decision.decision == "approve_with_warnings"
    assert output.total_findings == 1
    assert len(output.subagent_results) == 2
    assert "2 subagents" in output.summary


@pytest.mark.asyncio
async def test_run_review_with_streaming(mock_stream_manager):

    agent = MockReviewerAgent("agent1")
    orchestrator = PRReviewOrchestrator([agent], stream_manager=mock_stream_manager)

    inputs = ReviewInputs(
        repo_root="/tmp/repo",
        base_ref="main",
        head_ref="feature",
        timeout_seconds=60,
    )

    with patch(
        "dawn_kestrel.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=["src/file.py"]),
    ), patch(
        "dawn_kestrel.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        output = await orchestrator.run_review(inputs, stream_callback=lambda x: None)

    mock_stream_manager.start_stream.assert_called_once()
    assert isinstance(output, OrchestratorOutput)
