"""Tests for DocumentationReviewer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.agents.review.agents.documentation import DocumentationReviewer
from dawn_kestrel.agents.review.base import ReviewContext
from dawn_kestrel.agents.review.contracts import ReviewOutput


@pytest.fixture
def reviewer() -> DocumentationReviewer:
    return DocumentationReviewer()


@pytest.fixture
def sample_context() -> ReviewContext:
    return ReviewContext(
        changed_files=["src/module.py", "README.md"],
        diff="+ class Foo:\n+     def bar(self):\n+         return 1\n",
        repo_root="/test/repo",
    )


@pytest.mark.asyncio
async def test_review_with_findings(reviewer: DocumentationReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(
        return_value='{"agent":"documentation","summary":"Found docs issues","severity":"warning","scope":{"relevant_files":["src/module.py"],"ignored_files":[],"reasoning":"docs relevant"},"findings":[{"id":"doc-1","title":"Missing docstring","severity":"warning","confidence":"high","owner":"dev","estimate":"S","evidence":"src/module.py","risk":"usage unclear","recommendation":"add docstring"}],"merge_gate":{"decision":"needs_changes","must_fix":[],"should_fix":["doc-1"],"notes_for_coding_agent":[]}}'
    )

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        result = await reviewer.review(sample_context)

    assert isinstance(result, ReviewOutput)
    assert result.agent == "documentation"
    assert result.severity == "warning"
    assert len(result.findings) == 1


@pytest.mark.asyncio
async def test_review_handles_invalid_json(reviewer: DocumentationReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(return_value="This is not valid JSON")

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        result = await reviewer.review(sample_context)

    assert result.severity == "critical"
    assert "Error parsing LLM response" in result.summary


@pytest.mark.asyncio
async def test_review_timeout(reviewer: DocumentationReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(side_effect=TimeoutError("Request timed out after 60s"))

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        with pytest.raises(TimeoutError):
            await reviewer.review(sample_context)


@pytest.mark.asyncio
async def test_review_with_no_findings_returns_merge(reviewer: DocumentationReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(
        return_value='{"agent":"documentation","summary":"No issues","severity":"merge","scope":{"relevant_files":[],"ignored_files":[],"reasoning":"none"},"findings":[],"merge_gate":{"decision":"approve","must_fix":[],"should_fix":[],"notes_for_coding_agent":[]}}'
    )

    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        result = await reviewer.review(sample_context)

    assert result.severity == "merge"
    assert result.merge_gate.decision == "approve"
    assert len(result.findings) == 0
