"""Tests for LintingReviewer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.agents.review.agents.linting import LintingReviewer
from dawn_kestrel.agents.review.base import ReviewContext
from dawn_kestrel.agents.review.contracts import ReviewOutput


@pytest.fixture
def reviewer() -> LintingReviewer:
    return LintingReviewer()


@pytest.fixture
def sample_context() -> ReviewContext:
    return ReviewContext(
        changed_files=["src/app.py", "pyproject.toml"],
        diff="+ def my_function(x):\n+     return x * 2\n+ print('hello')",
        repo_root="/test/repo",
    )


@pytest.mark.asyncio
async def test_review_with_findings(reviewer: LintingReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(
        return_value='{"agent":"linting","summary":"Found lint issues","severity":"critical","scope":{"relevant_files":["src/app.py"],"ignored_files":[],"reasoning":"python files changed"},"findings":[{"id":"lint-1","title":"Line too long","severity":"critical","confidence":"high","owner":"dev","estimate":"S","evidence":"src/app.py:1","risk":"style/CI fail","recommendation":"format file"}],"merge_gate":{"decision":"needs_changes","must_fix":["lint-1"],"should_fix":[],"notes_for_coding_agent":[]}}'
    )

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        result = await reviewer.review(sample_context)

    assert isinstance(result, ReviewOutput)
    assert result.agent == "linting"
    assert result.severity == "critical"


@pytest.mark.asyncio
async def test_review_no_relevant_files_returns_merge(reviewer: LintingReviewer) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(return_value="{}")

    context = ReviewContext(changed_files=["README.md"], diff="+ docs", repo_root="/test/repo")

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        result = await reviewer.review(context)

    assert result.severity == "merge"
    assert "No Python or lint config files changed" in result.summary
    mock_runner.run_with_retry.assert_not_called()


@pytest.mark.asyncio
async def test_review_invalid_json(reviewer: LintingReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(return_value="not valid json")

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        result = await reviewer.review(sample_context)

    assert result.severity == "critical"
    assert result.merge_gate.decision == "needs_changes"


@pytest.mark.asyncio
async def test_review_timeout(reviewer: LintingReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(side_effect=TimeoutError("Request timed out"))

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        with pytest.raises(TimeoutError):
            await reviewer.review(sample_context)
