"""Tests for ArchitectureReviewer."""
import pytest

from opencode_python.agents.review.agents import architecture as architecture_module
from opencode_python.agents.review.contracts import Finding

from opencode_python.agents.review.agents.architecture import ArchitectureReviewer
from opencode_python.agents.review.base import ReviewContext


@pytest.mark.asyncio
async def test_architecture_reviewer_no_relevant_files():
    reviewer = ArchitectureReviewer()
    context = ReviewContext(
        changed_files=["README.md"],
        diff="+ docs update",
        repo_root="/repo",
    )

    output = await reviewer.review(context)

    assert output.severity == "merge"
    assert output.merge_gate.decision == "approve"
    assert "No relevant architectural changes" in output.summary


@pytest.mark.asyncio
async def test_architecture_reviewer_detects_breaking_and_boundary_issues():
    reviewer = ArchitectureReviewer()
    diff = """diff --git a/src/controllers/api.py b/src/controllers/api.py
+++ b/src/controllers/api.py
@@ -1,2 +1,3 @@
- def public_api():
+ from infrastructure.db import Client
+ def public_api():
"""
    context = ReviewContext(
        changed_files=["src/controllers/api.py"],
        diff=diff,
        repo_root="/repo",
    )

    output = await reviewer.review(context)

    assert output.severity == "warning"
    assert output.merge_gate.decision == "needs_changes"
    finding_ids = {finding.id for finding in output.findings}
    assert "ARCH-BOUNDARY-001" in finding_ids


def _make_finding(finding_id: str, severity: str) -> Finding:
    return Finding(
        id=finding_id,
        title="Issue",
        severity=severity,
        confidence="high",
        owner="dev",
        estimate="S",
        evidence="e",
        risk="r",
        recommendation="fix",
    )


def test_architecture_circular_import_detection(monkeypatch):
    reviewer = ArchitectureReviewer()
    diff = "\n".join([
        "+++ b/src/a.py",
        "+ from app.core import Thing",
        "+++ b/src/b.py",
        "+ from app.services import Other",
    ])

    original_search = architecture_module.re.search
    call_state = {"count": 0}

    def fake_search(pattern, string, flags=0):
        if pattern == r"^\+\s*from\s+(\S+)":
            stripped = string.lstrip()
            if stripped.startswith("from "):
                module = stripped.split()[1]

                class Match:
                    def group(self, idx):
                        return module

                return Match()

        if pattern == r"^\+\+\+\s*(\S+)":
            call_state["count"] += 1
            file_path = "src/a.py" if call_state["count"] == 1 else "src/b.py"

            class Match:
                def group(self, idx):
                    return file_path

            return Match()
        return original_search(pattern, string, flags)

    monkeypatch.setattr(architecture_module.re, "search", fake_search)
    findings = reviewer._check_circular_imports(diff)
    assert any(f.id == "ARCH-CIRCULAR-001" for f in findings)


def test_architecture_detects_god_class_and_breaking_changes():
    reviewer = ArchitectureReviewer()
    methods = [f"+     def m{i}(self):\n+         pass" for i in range(21)]
    diff = "\n".join([
        "+ class Big:",
        *methods,
        "+ class Small:",
        "+     pass",
    ])
    findings = reviewer._check_god_objects(diff)
    assert any(f.id == "ARCH-GOD-001" for f in findings)

    breaking = reviewer._check_breaking_changes("-- def public_api():")
    assert any(f.id == "ARCH-BREAKING-001" for f in breaking)


def test_architecture_summary_and_merge_gate():
    reviewer = ArchitectureReviewer()
    findings = [
        _make_finding("a", "blocking"),
        _make_finding("b", "critical"),
        _make_finding("c", "warning"),
    ]
    summary = reviewer._generate_summary(findings, "blocking")
    assert "blocking" in summary
    merge_gate = reviewer._compute_merge_gate(findings, "blocking")
    assert merge_gate.decision == "block"


def test_architecture_prompts_and_empty_findings_behavior():
    reviewer = ArchitectureReviewer()
    assert reviewer.get_system_prompt() == reviewer._SYSTEM_PROMPT
    assert reviewer.get_relevant_file_patterns() == ["**/*.py"]
    assert reviewer._compute_severity([]) == "merge"

    findings = reviewer._check_god_objects("+ class")
    assert findings == []
