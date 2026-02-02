"""Tests for TelemetryMetricsReviewer."""
import pytest

from opencode_python.agents.review.agents.telemetry import TelemetryMetricsReviewer
from opencode_python.agents.review.base import ReviewContext


@pytest.mark.asyncio
async def test_telemetry_reviewer_detects_sensitive_logging_and_silent_exceptions():
    reviewer = TelemetryMetricsReviewer()
    diff = """diff --git a/src/service.py b/src/service.py
+++ b/src/service.py
@@ -1,1 +1,3 @@
+ try:
+     pass
+ except Exception: pass
+ logger.info("token=%s", token)
"""
    context = ReviewContext(
        changed_files=["src/service.py"],
        diff=diff,
        repo_root="/repo",
    )

    output = await reviewer.review(context)

    assert output.severity == "critical"
    assert output.merge_gate.decision == "needs_changes"
    finding_ids = {finding.id for finding in output.findings}
    assert any(f_id.startswith("silent-exception-") for f_id in finding_ids)
    assert any(f_id.startswith("sensitive-log-") for f_id in finding_ids)
