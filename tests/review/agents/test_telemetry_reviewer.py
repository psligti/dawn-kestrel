"""Tests for TelemetryMetricsReviewer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.agents.review.agents.telemetry import TelemetryMetricsReviewer
from dawn_kestrel.agents.review.base import ReviewContext


@pytest.fixture
def reviewer() -> TelemetryMetricsReviewer:
    return TelemetryMetricsReviewer()


@pytest.fixture
def sample_context() -> ReviewContext:
    return ReviewContext(
        changed_files=["src/service.py", "src/api/handler.py"],
        diff="+ except Exception: pass\n+ logger.info('token=%s', token)",
        repo_root="/test/repo",
    )


@pytest.mark.asyncio
async def test_review_with_telemetry_findings(reviewer: TelemetryMetricsReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(
        return_value='{"agent":"telemetry","summary":"Found telemetry issues","severity":"critical","scope":{"relevant_files":["src/service.py"],"ignored_files":[],"reasoning":"logging changes"},"findings":[{"id":"tele-1","title":"Sensitive data logged","severity":"critical","confidence":"high","owner":"security","estimate":"M","evidence":"token logged","risk":"PII leakage","recommendation":"mask token"}],"merge_gate":{"decision":"needs_changes","must_fix":["tele-1"],"should_fix":[],"notes_for_coding_agent":[]}}'
    )
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(sample_context)
    assert output.agent == "telemetry"
    assert output.severity == "critical"


@pytest.mark.asyncio
async def test_review_invalid_json(reviewer: TelemetryMetricsReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(return_value="invalid")
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        output = await reviewer.review(sample_context)
    assert output.severity == "critical"


@pytest.mark.asyncio
async def test_review_timeout(reviewer: TelemetryMetricsReviewer, sample_context: ReviewContext) -> None:
    mock_runner = MagicMock()
    mock_runner.run_with_retry = AsyncMock(side_effect=TimeoutError("timed out"))
    with patch("dawn_kestrel.core.harness.SimpleReviewAgentRunner", return_value=mock_runner):
        with pytest.raises(TimeoutError):
            await reviewer.review(sample_context)
