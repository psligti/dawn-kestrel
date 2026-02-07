"""Tests for DependencyLicenseReviewer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.agents.review.agents.dependencies import DependencyLicenseReviewer
from dawn_kestrel.agents.review.agents import dependencies as dependencies_module
from dawn_kestrel.agents.review.base import ReviewContext
from dawn_kestrel.agents.review.contracts import ReviewOutput


@pytest.fixture
def reviewer() -> DependencyLicenseReviewer:
    return DependencyLicenseReviewer()


@pytest.fixture
def dep_context() -> ReviewContext:
    return ReviewContext(
        changed_files=["pyproject.toml", "src/main.py"],
        diff="+ requests = \"^2.31.0\"",
        repo_root="/repo",
    )


@pytest.mark.asyncio
async def test_dependency_reviewer_with_llm_findings(reviewer: DependencyLicenseReviewer, dep_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(
        return_value='{"agent":"dependencies","summary":"Found issues","severity":"critical","scope":{"relevant_files":["pyproject.toml"],"ignored_files":[],"reasoning":"dependency files changed"},"findings":[{"id":"dep-1","title":"Loosened pin","severity":"critical","confidence":"high","owner":"dev","estimate":"S","evidence":"pyproject.toml","risk":"non-reproducible builds","recommendation":"pin exact version"}],"merge_gate":{"decision":"needs_changes","must_fix":["dep-1"],"should_fix":[],"notes_for_coding_agent":[]}}'
    )

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(dep_context)

    assert isinstance(output, ReviewOutput)
    assert output.agent == "dependencies"
    assert output.severity == "critical"
    assert output.merge_gate.decision == "needs_changes"


@pytest.mark.asyncio
async def test_dependency_reviewer_skips_when_no_dependency_files(reviewer: DependencyLicenseReviewer) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(return_value="{}")

    context = ReviewContext(
        changed_files=["src/app.py"],
        diff="+ print('hello')",
        repo_root="/repo",
    )

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(context)

    assert output.severity == "merge"
    assert output.merge_gate.decision == "approve"
    assert "No dependency files changed" in output.summary
    mock_runner.run_with_retry.assert_not_called()


@pytest.mark.asyncio
async def test_dependency_reviewer_handles_invalid_json(reviewer: DependencyLicenseReviewer, dep_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(return_value="not valid json")

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(dep_context)

    assert output.severity == "critical"
    assert output.merge_gate.decision == "needs_changes"
    assert "Error parsing LLM response" in output.summary


@pytest.mark.asyncio
async def test_dependency_reviewer_timeout(reviewer: DependencyLicenseReviewer, dep_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(side_effect=TimeoutError("timed out"))

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        with pytest.raises(TimeoutError):
            await reviewer.review(dep_context)


def test_dependency_reviewer_metadata(reviewer: DependencyLicenseReviewer) -> None:
    assert reviewer.get_agent_name() == "dependencies"
    assert reviewer.get_system_prompt() == dependencies_module.DEPENDENCY_SYSTEM_PROMPT
    assert "pyproject.toml" in reviewer.get_relevant_file_patterns()
