"""Tests for DiffScoperReviewer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.agents.review.agents.diff_scoper import DiffScoperReviewer
from dawn_kestrel.agents.review.base import ReviewContext
from dawn_kestrel.agents.review.contracts import ReviewOutput


@pytest.fixture
def reviewer() -> DiffScoperReviewer:
    return DiffScoperReviewer()


@pytest.fixture
def sample_context() -> ReviewContext:
    return ReviewContext(
        changed_files=["src/api.py", "config/settings.py", "tests/test_api.py"],
        diff="+ def new_api_endpoint():\n+     return {'status': 'ok'}\n- old_api_endpoint()",
        repo_root="/test/repo",
    )


@pytest.mark.asyncio
async def test_review_with_routing_output(reviewer: DiffScoperReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(
        return_value='{"agent":"diff_scoper","summary":"Diff Scoping Analysis","severity":"warning","scope":{"relevant_files":["src/api.py"],"ignored_files":[],"reasoning":"analyze all"},"findings":[{"id":"route-code","title":"Route to code reviewer","severity":"warning","confidence":"high","owner":"dev","estimate":"S","evidence":"src/api.py","risk":"medium","recommendation":"route to code reviewer"}],"merge_gate":{"decision":"approve","must_fix":[],"should_fix":[],"notes_for_coding_agent":["routing guidance"]}}'
    )

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        result = await reviewer.review(sample_context)

    assert isinstance(result, ReviewOutput)
    assert result.agent == "diff_scoper"
    assert result.severity == "warning"
    assert len(result.findings) == 1


@pytest.mark.asyncio
async def test_review_missing_api_key_raises(reviewer: DiffScoperReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(side_effect=ValueError("API key not found for provider"))

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        with pytest.raises(ValueError, match="API key"):
            await reviewer.review(sample_context)


@pytest.mark.asyncio
async def test_review_invalid_json_returns_fallback(reviewer: DiffScoperReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(return_value="This is not valid JSON")

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        result = await reviewer.review(sample_context)

    assert result.severity == "critical"
    assert result.merge_gate.decision == "needs_changes"


@pytest.mark.asyncio
async def test_review_timeout_error_raises(reviewer: DiffScoperReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(side_effect=TimeoutError("Request timed out"))

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        with pytest.raises(TimeoutError):
            await reviewer.review(sample_context)
