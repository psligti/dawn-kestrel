"""Tests for PerformanceReliabilityReviewer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.agents.review.agents.performance import PerformanceReliabilityReviewer
from dawn_kestrel.agents.review.base import ReviewContext


@pytest.fixture
def reviewer() -> PerformanceReliabilityReviewer:
    return PerformanceReliabilityReviewer()


@pytest.fixture
def sample_context() -> ReviewContext:
    return ReviewContext(
        changed_files=["src/app.py", "src/api/service.py"],
        diff="+ while True:\n+     pass\n+ for item in items: db.execute('select 1')",
        repo_root="/test/repo",
    )


@pytest.mark.asyncio
async def test_review_with_findings(reviewer: PerformanceReliabilityReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(
        return_value='{"agent":"performance","summary":"Found performance issues","severity":"critical","scope":{"relevant_files":["src/app.py"],"ignored_files":[],"reasoning":"performance-relevant changes"},"findings":[{"id":"perf-1","title":"N+1 query","severity":"critical","confidence":"high","owner":"dev","estimate":"M","evidence":"service loop","risk":"slow requests","recommendation":"batch queries"}],"merge_gate":{"decision":"needs_changes","must_fix":["perf-1"],"should_fix":[],"notes_for_coding_agent":[]}}'
    )
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(sample_context)
    assert output.agent == "performance"
    assert output.severity == "critical"


@pytest.mark.asyncio
async def test_review_invalid_json(reviewer: PerformanceReliabilityReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(return_value="not valid json")
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(sample_context)
    assert output.severity == "critical"


@pytest.mark.asyncio
async def test_review_timeout_raises(reviewer: PerformanceReliabilityReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(side_effect=TimeoutError("LLM request timed out"))
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        with pytest.raises(TimeoutError):
            await reviewer.review(sample_context)
