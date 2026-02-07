"""Tests for RequirementsReviewer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.agents.review.agents.requirements import RequirementsReviewer
from dawn_kestrel.agents.review.base import ReviewContext


@pytest.fixture
def reviewer() -> RequirementsReviewer:
    return RequirementsReviewer()


@pytest.fixture
def sample_context() -> ReviewContext:
    return ReviewContext(
        changed_files=["src/app.py", "src/user_service.py"],
        diff="+ def create_user(name, email):\n+     return user",
        repo_root="/test/repo",
        pr_description="Must validate email format",
    )


@pytest.mark.asyncio
async def test_review_with_requirement_gaps(reviewer: RequirementsReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(
        return_value='{"agent":"requirements","summary":"Missing requirement","severity":"critical","scope":{"relevant_files":["src/user_service.py"],"ignored_files":[],"reasoning":"requirements mismatch"},"findings":[{"id":"req-1","title":"Email validation missing","severity":"critical","confidence":"high","owner":"dev","estimate":"M","evidence":"no validation in diff","risk":"invalid input accepted","recommendation":"add validation"}],"merge_gate":{"decision":"needs_changes","must_fix":["req-1"],"should_fix":[],"notes_for_coding_agent":[]}}'
    )
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(sample_context)
    assert output.agent == "requirements"
    assert output.severity == "critical"


@pytest.mark.asyncio
async def test_review_invalid_json(reviewer: RequirementsReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(return_value="invalid")
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(sample_context)
    assert output.severity == "critical"


@pytest.mark.asyncio
async def test_review_timeout(reviewer: RequirementsReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(side_effect=TimeoutError("timed out"))
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        with pytest.raises(TimeoutError):
            await reviewer.review(sample_context)
