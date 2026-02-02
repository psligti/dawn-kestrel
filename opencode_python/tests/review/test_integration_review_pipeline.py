"""Integration tests for PR review pipeline."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from opencode_python.agents.review.agents.architecture import ArchitectureReviewer
from opencode_python.agents.review.agents.changelog import ReleaseChangelogReviewer
from opencode_python.agents.review.agents.dependencies import DependencyLicenseReviewer
from opencode_python.agents.review.agents.diff_scoper import DiffScoperReviewer
from opencode_python.agents.review.agents.documentation import DocumentationReviewer
from opencode_python.agents.review.agents.linting import LintingReviewer
from opencode_python.agents.review.agents.performance import PerformanceReliabilityReviewer
from opencode_python.agents.review.agents.requirements import RequirementsReviewer
from opencode_python.agents.review.agents.security import SecurityReviewer
from opencode_python.agents.review.agents.telemetry import TelemetryMetricsReviewer
from opencode_python.agents.review.agents.unit_tests import UnitTestsReviewer
from opencode_python.agents.review.contracts import ReviewInputs
from opencode_python.agents.review.orchestrator import PRReviewOrchestrator
from opencode_python.agents.review.utils.executor import ExecutionResult


class AsyncExecutor:
    async def execute(self, command: str, timeout: int = 60):
        return ExecutionResult(
            command=command,
            exit_code=0,
            stdout="",
            stderr="",
            timeout=False,
            parsed_findings=[],
            files_modified=[],
            duration_seconds=0.1,
        )


class SyncExecutor:
    def execute(self, command: str, timeout: int, cwd: str):
        return ExecutionResult(
            command=command,
            exit_code=0,
            stdout="",
            stderr="",
            timeout=False,
            parsed_findings=[],
            files_modified=[],
            duration_seconds=0.1,
        )


@pytest.mark.asyncio
async def test_review_pipeline_runs_all_subagents(tmp_path: Path):
    module_path = tmp_path / "src" / "module.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(
        '"""Module docs."""\n'
        "def foo() -> None:\n"
        "    \"\"\"Function docs.\"\"\"\n"
        "    return None\n\n"
        "class Bar:\n"
        "    \"\"\"Class docs.\"\"\"\n"
        "    def baz(self) -> None:\n"
        "        \"\"\"Method docs.\"\"\"\n"
        "        return None\n"
    )

    diff = """diff --git a/src/module.py b/src/module.py
+++ b/src/module.py
@@ -1,1 +1,1 @@
-# old
+# new
"""

    agents = [
        DiffScoperReviewer(),
        ArchitectureReviewer(),
        SecurityReviewer(),
        DocumentationReviewer(),
        LintingReviewer(executor=AsyncExecutor()),
        UnitTestsReviewer(executor=SyncExecutor(), repo_root=str(tmp_path)),
        RequirementsReviewer(),
        PerformanceReliabilityReviewer(),
        DependencyLicenseReviewer(),
        ReleaseChangelogReviewer(),
        TelemetryMetricsReviewer(),
    ]

    orchestrator = PRReviewOrchestrator(agents)
    inputs = ReviewInputs(
        repo_root=str(tmp_path),
        base_ref="main",
        head_ref="feature",
        timeout_seconds=30,
    )

    with patch(
        "opencode_python.agents.review.utils.git.get_changed_files",
        AsyncMock(return_value=["src/module.py"]),
    ), patch(
        "opencode_python.agents.review.utils.git.get_diff",
        AsyncMock(return_value=diff),
    ):
        output = await orchestrator.run_review(inputs)

    assert len(output.subagent_results) == 11
    assert output.merge_decision.decision in {"needs_changes", "block", "approve"}
    assert "Review completed" in output.merge_decision.notes_for_coding_agent[0]
