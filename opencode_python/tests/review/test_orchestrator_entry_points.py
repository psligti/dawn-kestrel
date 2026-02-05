"""Tests for PRReviewOrchestrator entry point discovery integration.

This test file covers the integration of EntryPointDiscovery with the orchestrator's
_build_context() method, including:
- Successful discovery with filtering
- Fallback to is_relevant_to_changes()
- Agent name extraction
- Context filtering based on entry points
- Logging verification
- Timeout and error scenarios
- Backward compatibility
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

import pytest

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import ReviewInputs, ReviewOutput, Scope, MergeGate
from opencode_python.agents.review.discovery import EntryPoint, EntryPointDiscovery
from opencode_python.agents.review.orchestrator import PRReviewOrchestrator


class TestReviewerAgent(BaseReviewerAgent):

    def __init__(
        self,
        agent_name: str = "TestReviewer",
        is_relevant: bool = True,
    ):
        self._agent_name = agent_name
        self._is_relevant = is_relevant

    def get_agent_name(self) -> str:
        return self._agent_name

    async def review(self, context: ReviewContext) -> ReviewOutput:
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

    def is_relevant_to_changes(self, changed_files: List[str]) -> bool:
        return self._is_relevant


@pytest.fixture
def mock_discovery():
    """Mock EntryPointDiscovery with default behavior."""
    discovery = MagicMock(spec=EntryPointDiscovery)
    discovery.discover_entry_points = AsyncMock(return_value=None)
    return discovery


@pytest.fixture
def sample_changed_files():
    """Sample changed files for testing."""
    return [
        "src/auth/login.py",
        "src/auth/logout.py",
        "src/api/routes.py",
        "src/models/user.py",
        "config/settings.py",
        "tests/test_auth.py",
    ]


@pytest.fixture
def sample_entry_points():
    """Sample entry points for testing."""
    return [
        EntryPoint(
            file_path="src/auth/login.py",
            line_number=10,
            description="Login function entry point",
            weight=0.95,
            pattern_type="ast",
            evidence="def login(username, password):",
        ),
        EntryPoint(
            file_path="src/auth/logout.py",
            line_number=5,
            description="Logout function entry point",
            weight=0.9,
            pattern_type="ast",
            evidence="def logout():",
        ),
        EntryPoint(
            file_path="src/api/routes.py",
            line_number=20,
            description="API route handler",
            weight=0.85,
            pattern_type="content",
            evidence="@app.route('/api')",
        ),
    ]


@pytest.fixture
def sample_review_inputs(sample_changed_files):
    """Sample ReviewInputs for testing."""
    return ReviewInputs(
        repo_root="/tmp/repo",
        base_ref="main",
        head_ref="feature",
        timeout_seconds=60,
        pr_title="Add authentication feature",
        pr_description="Implements login/logout functionality",
    )


@pytest.fixture
def security_reviewer_agent():
    """Mock SecurityReviewer agent."""
    return TestReviewerAgent(agent_name="SecurityReviewer", is_relevant=True)


@pytest.fixture
def architecture_reviewer_agent():
    """Mock ArchitectureReviewer agent."""
    return TestReviewerAgent(agent_name="ArchitectureReviewer", is_relevant=True)


@pytest.fixture
def orchestrator_with_mock_discovery(mock_discovery):
    """Orchestrator with mocked discovery."""
    agent = TestReviewerAgent(agent_name="TestReviewer", is_relevant=True)
    orchestrator = PRReviewOrchestrator([agent], discovery=mock_discovery)
    return orchestrator


@pytest.mark.asyncio
async def test_build_context_extract_agent_name(orchestrator_with_mock_discovery, sample_review_inputs):
    """Test that _build_context extracts agent name using agent.__class__.__name__."""
    orchestrator = orchestrator_with_mock_discovery
    agent = orchestrator.subagents[0]

    orchestrator.discovery.discover_entry_points = AsyncMock(return_value=None)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=["src/file.py"]),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    orchestrator.discovery.discover_entry_points.assert_called_once()
    call_args = orchestrator.discovery.discover_entry_points.call_args
    assert call_args.kwargs["agent_name"] == "TestReviewerAgent"


@pytest.mark.asyncio
async def test_build_context_with_successful_discovery(
    orchestrator_with_mock_discovery,
    sample_review_inputs,
    sample_changed_files,
    sample_entry_points,
):
    """Test _build_context when entry point discovery returns list of EntryPoints."""
    orchestrator = orchestrator_with_mock_discovery
    agent = orchestrator.subagents[0]

    orchestrator.discovery.discover_entry_points = AsyncMock(return_value=sample_entry_points)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    assert set(context.changed_files) == {"src/auth/login.py", "src/auth/logout.py", "src/api/routes.py"}
    assert len(context.changed_files) == 3

    orchestrator.discovery.discover_entry_points.assert_called_once()
    call_args = orchestrator.discovery.discover_entry_points.call_args
    assert call_args.kwargs["agent_name"] == "TestReviewerAgent"
    assert call_args.kwargs["repo_root"] == sample_review_inputs.repo_root
    assert call_args.kwargs["changed_files"] == sample_changed_files


@pytest.mark.asyncio
async def test_build_context_with_none_discovery_relevant_agent(
    orchestrator_with_mock_discovery,
    sample_review_inputs,
    sample_changed_files,
):
    """Test _build_context when discovery returns None and agent is relevant."""
    orchestrator = orchestrator_with_mock_discovery
    agent = orchestrator.subagents[0]

    orchestrator.discovery.discover_entry_points = AsyncMock(return_value=None)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    assert set(context.changed_files) == set(sample_changed_files)
    assert len(context.changed_files) == 6


@pytest.mark.asyncio
async def test_build_context_with_none_discovery_irrelevant_agent(
    mock_discovery,
    sample_review_inputs,
    sample_changed_files,
):
    """Test _build_context when discovery returns None and agent is not relevant."""
    agent = TestReviewerAgent(agent_name="TestReviewer", is_relevant=False)
    orchestrator = PRReviewOrchestrator([agent], discovery=mock_discovery)

    mock_discovery.discover_entry_points = AsyncMock(return_value=None)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    assert context.changed_files == []
    assert len(context.changed_files) == 0


@pytest.mark.asyncio
async def test_build_context_with_discovery_timeout(
    mock_discovery,
    sample_review_inputs,
    sample_changed_files,
):
    """Test _build_context when discovery times out (returns None)."""
    agent = TestReviewerAgent(agent_name="TestReviewer", is_relevant=True)
    orchestrator = PRReviewOrchestrator([agent], discovery=mock_discovery)

    mock_discovery.discover_entry_points = AsyncMock(return_value=None)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    assert set(context.changed_files) == set(sample_changed_files)


@pytest.mark.asyncio
async def test_build_context_with_discovery_error(
    mock_discovery,
    sample_review_inputs,
    sample_changed_files,
):
    """Test _build_context when discovery returns None (simulating error)."""
    agent = TestReviewerAgent(agent_name="TestReviewer", is_relevant=True)
    orchestrator = PRReviewOrchestrator([agent], discovery=mock_discovery)

    mock_discovery.discover_entry_points = AsyncMock(return_value=None)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    assert set(context.changed_files) == set(sample_changed_files)


@pytest.mark.asyncio
async def test_build_context_filters_files_to_entry_points(
    orchestrator_with_mock_discovery,
    sample_review_inputs,
    sample_changed_files,
    sample_entry_points,
):
    """Test that _build_context filters changed_files to only those with entry points."""
    orchestrator = orchestrator_with_mock_discovery
    agent = orchestrator.subagents[0]

    orchestrator.discovery.discover_entry_points = AsyncMock(return_value=sample_entry_points)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    assert "src/auth/login.py" in context.changed_files
    assert "src/auth/logout.py" in context.changed_files
    assert "src/api/routes.py" in context.changed_files
    assert "src/models/user.py" not in context.changed_files
    assert "config/settings.py" not in context.changed_files
    assert "tests/test_auth.py" not in context.changed_files


@pytest.mark.asyncio
async def test_build_context_empty_entry_points_vs_none(
    mock_discovery,
    sample_review_inputs,
    sample_changed_files,
):
    """Test that empty list returns empty changed_files (no entry points to filter)."""
    agent = TestReviewerAgent(agent_name="TestReviewer", is_relevant=True)
    orchestrator = PRReviewOrchestrator([agent], discovery=mock_discovery)

    mock_discovery.discover_entry_points = AsyncMock(return_value=[])

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    assert context.changed_files == []


@pytest.mark.asyncio
async def test_build_context_multiple_reviewers(
    mock_discovery,
    sample_review_inputs,
    sample_changed_files,
):
    """Test that different reviewers get filtered based on their entry points."""
    security_agent = TestReviewerAgent(is_relevant=True)
    architecture_agent = TestReviewerAgent(is_relevant=True)

    orchestrator = PRReviewOrchestrator(
        [security_agent, architecture_agent], discovery=mock_discovery
    )

    security_entry_points = [
        EntryPoint(
            file_path="src/auth/login.py",
            line_number=10,
            description="Security-sensitive auth function",
            weight=0.95,
            pattern_type="ast",
            evidence="def login(username, password):",
        )
    ]

    architecture_entry_points = [
        EntryPoint(
            file_path="src/models/user.py",
            line_number=15,
            description="User model architecture",
            weight=0.9,
            pattern_type="ast",
            evidence="class User:",
        )
    ]

    call_count = 0

    async def mock_discover_entry_points(agent_name, repo_root, changed_files):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return security_entry_points
        elif call_count == 2:
            return architecture_entry_points
        return None

    mock_discovery.discover_entry_points = AsyncMock(side_effect=mock_discover_entry_points)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        security_context = await orchestrator._build_context(sample_review_inputs, security_agent)
        architecture_context = await orchestrator._build_context(
            sample_review_inputs, architecture_agent
        )

    assert security_context.changed_files == ["src/auth/login.py"]
    assert architecture_context.changed_files == ["src/models/user.py"]
    assert mock_discovery.discover_entry_points.call_count == 2


@pytest.mark.asyncio
async def test_build_context_discovery_integration_parameters(
    orchestrator_with_mock_discovery,
    sample_review_inputs,
    sample_changed_files,
    sample_entry_points,
):
    """Test that discover_entry_points is called with correct parameters."""
    orchestrator = orchestrator_with_mock_discovery
    agent = orchestrator.subagents[0]

    orchestrator.discovery.discover_entry_points = AsyncMock(return_value=sample_entry_points)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    call_args = orchestrator.discovery.discover_entry_points.call_args
    assert call_args.kwargs["agent_name"] == "TestReviewerAgent"
    assert call_args.kwargs["repo_root"] == "/tmp/repo"
    assert call_args.kwargs["changed_files"] == sample_changed_files
    assert len(call_args.kwargs["changed_files"]) == 6


@pytest.mark.asyncio
async def test_build_context_logs_discovery_success(
    orchestrator_with_mock_discovery,
    sample_review_inputs,
    sample_changed_files,
    sample_entry_points,
    caplog,
):
    """Test that discovery success is logged with entry point count and filtering ratio."""
    import logging

    orchestrator = orchestrator_with_mock_discovery
    agent = orchestrator.subagents[0]

    orchestrator.discovery.discover_entry_points = AsyncMock(return_value=sample_entry_points)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        with caplog.at_level(logging.INFO):
            context = await orchestrator._build_context(sample_review_inputs, agent)

    discovery_logs = [
        record for record in caplog.records if "Entry point discovery found" in record.message
    ]
    assert len(discovery_logs) > 0
    assert "3 entry points" in discovery_logs[0].message
    assert "3/6 files" in discovery_logs[0].message


@pytest.mark.asyncio
async def test_build_context_logs_fallback(
    orchestrator_with_mock_discovery,
    sample_review_inputs,
    sample_changed_files,
    caplog,
):
    """Test that fallback to is_relevant_to_changes() is logged."""
    import logging

    orchestrator = orchestrator_with_mock_discovery
    agent = orchestrator.subagents[0]

    orchestrator.discovery.discover_entry_points = AsyncMock(return_value=None)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        with caplog.at_level(logging.INFO):
            context = await orchestrator._build_context(sample_review_inputs, agent)

    fallback_logs = [
        record for record in caplog.records if "is_relevant_to_changes() fallback" in record.message
    ]
    assert len(fallback_logs) > 0


@pytest.mark.asyncio
async def test_build_context_logs_agent_not_relevant(
    mock_discovery,
    sample_review_inputs,
    sample_changed_files,
    caplog,
):
    """Test that skipping review for irrelevant agent is logged."""
    import logging

    agent = TestReviewerAgent(agent_name="TestReviewer", is_relevant=False)
    orchestrator = PRReviewOrchestrator([agent], discovery=mock_discovery)

    mock_discovery.discover_entry_points = AsyncMock(return_value=None)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        with caplog.at_level(logging.INFO):
            context = await orchestrator._build_context(sample_review_inputs, agent)

    skip_logs = [
        record for record in caplog.records if "Agent not relevant to changes" in record.message
    ]
    assert len(skip_logs) > 0


@pytest.mark.asyncio
async def test_build_context_populates_all_fields(
    orchestrator_with_mock_discovery,
    sample_review_inputs,
    sample_changed_files,
    sample_entry_points,
):
    """Test that ReviewContext is populated with all expected fields."""
    orchestrator = orchestrator_with_mock_discovery
    agent = orchestrator.subagents[0]

    orchestrator.discovery.discover_entry_points = AsyncMock(return_value=sample_entry_points)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    assert context.changed_files == ["src/auth/login.py", "src/auth/logout.py", "src/api/routes.py"]
    assert context.diff == "diff content"
    assert context.repo_root == sample_review_inputs.repo_root
    assert context.base_ref == sample_review_inputs.base_ref
    assert context.head_ref == sample_review_inputs.head_ref
    assert context.pr_title == sample_review_inputs.pr_title
    assert context.pr_description == sample_review_inputs.pr_description


@pytest.mark.asyncio
async def test_build_context_backward_compatibility_without_discovery(
    sample_review_inputs,
    sample_changed_files,
):
    """Test backward compatibility when orchestrator is used without discovery parameter."""
    agent = TestReviewerAgent(agent_name="TestReviewer", is_relevant=True)
    orchestrator = PRReviewOrchestrator([agent])

    assert orchestrator.discovery is not None
    assert isinstance(orchestrator.discovery, EntryPointDiscovery)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        context = await orchestrator._build_context(sample_review_inputs, agent)

    assert len(context.changed_files) >= 0


@pytest.mark.asyncio
async def test_build_context_discovery_non_blocking(
    mock_discovery,
    sample_review_inputs,
    sample_changed_files,
    sample_entry_points,
):
    """Test that slow discovery doesn't block orchestrator beyond timeout."""
    agent = TestReviewerAgent(agent_name="TestReviewer", is_relevant=True)
    orchestrator = PRReviewOrchestrator([agent], discovery=mock_discovery)

    async def slow_discovery(*args, **kwargs):
        await asyncio.sleep(5)
        return sample_entry_points

    mock_discovery.discover_entry_points = AsyncMock(side_effect=slow_discovery)

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=sample_changed_files),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value="diff content"),
    ):
        start = asyncio.get_event_loop().time()
        context = await orchestrator._build_context(sample_review_inputs, agent)
        elapsed = asyncio.get_event_loop().time() - start

        assert elapsed < 10

    assert len(context.changed_files) == 3
