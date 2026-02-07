"""Tests for ReleaseChangelogReviewer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.agents.review.agents.changelog import ReleaseChangelogReviewer
from dawn_kestrel.agents.review.base import ReviewContext


@pytest.fixture
def reviewer() -> ReleaseChangelogReviewer:
    return ReleaseChangelogReviewer()


@pytest.fixture
def sample_context() -> ReviewContext:
    return ReviewContext(
        changed_files=["src/api.py"],
        diff="- def api_get(id: int) -> str:\n+ def api_get(user_id: int) -> str:",
        repo_root="/repo",
    )


@pytest.mark.asyncio
async def test_review_with_breaking_change_finding(reviewer: ReleaseChangelogReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(
        return_value='{"agent":"release_changelog","summary":"Breaking change without changelog","severity":"critical","scope":{"relevant_files":["src/api.py"],"ignored_files":[],"reasoning":"api changed"},"findings":[{"id":"rel-1","title":"Changelog missing","severity":"critical","confidence":"high","owner":"dev","estimate":"S","evidence":"api signature changed","risk":"undocumented breaking change","recommendation":"update changelog"}],"merge_gate":{"decision":"needs_changes","must_fix":["rel-1"],"should_fix":[],"notes_for_coding_agent":[]}}'
    )

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(sample_context)

    assert output.agent == "release_changelog"
    assert output.severity == "critical"


@pytest.mark.asyncio
async def test_review_invalid_json(reviewer: ReleaseChangelogReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(return_value="invalid")
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(sample_context)
    assert output.severity == "critical"


@pytest.mark.asyncio
async def test_review_timeout(reviewer: ReleaseChangelogReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(side_effect=TimeoutError("timed out"))
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        with pytest.raises(TimeoutError):
            await reviewer.review(sample_context)
