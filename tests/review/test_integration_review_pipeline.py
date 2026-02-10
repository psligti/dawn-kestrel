"""Integration tests for PR review pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from dawn_kestrel.agents.review.agents.architecture import ArchitectureReviewer
from dawn_kestrel.agents.review.agents.changelog import ReleaseChangelogReviewer
from dawn_kestrel.agents.review.agents.dependencies import DependencyLicenseReviewer
from dawn_kestrel.agents.review.agents.diff_scoper import DiffScoperReviewer
from dawn_kestrel.agents.review.agents.documentation import DocumentationReviewer
from dawn_kestrel.agents.review.agents.linting import LintingReviewer
from dawn_kestrel.agents.review.agents.performance import PerformanceReliabilityReviewer
from dawn_kestrel.agents.review.agents.requirements import RequirementsReviewer
from dawn_kestrel.agents.review.agents.security import SecurityReviewer
from dawn_kestrel.agents.review.agents.telemetry import TelemetryMetricsReviewer
from dawn_kestrel.agents.review.agents.unit_tests import UnitTestsReviewer
from dawn_kestrel.agents.review.contracts import ReviewInputs
from dawn_kestrel.agents.review.orchestrator import PRReviewOrchestrator
from dawn_kestrel.agents.review.utils.executor import ExecutionResult


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
        '    """Function docs."""\n'
        "    return None\n\n"
        "class Bar:\n"
        '    """Class docs."""\n'
        "    def baz(self) -> None:\n"
        '        """Method docs."""\n'
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
        LintingReviewer(),
        UnitTestsReviewer(),
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

    with (
        patch(
            "dawn_kestrel.agents.review.utils.git.get_changed_files",
            AsyncMock(return_value=["src/module.py"]),
        ),
        patch(
            "dawn_kestrel.agents.review.utils.git.get_diff",
            AsyncMock(return_value=diff),
        ),
    ):
        output = await orchestrator.run_review(inputs)

    assert len(output.subagent_results) == 11
    assert output.merge_decision.decision in {"needs_changes", "block", "approve"}
    assert "Review completed" in output.merge_decision.notes_for_coding_agent[0]
