"""Tests for PerformanceReliabilityReviewer."""
import pytest

from opencode_python.agents.review.contracts import Finding

from opencode_python.agents.review.agents.performance import PerformanceReliabilityReviewer
from opencode_python.agents.review.base import ReviewContext


@pytest.mark.asyncio
async def test_performance_reviewer_detects_retry_and_io_issues(monkeypatch):
    reviewer = PerformanceReliabilityReviewer()
    monkeypatch.setattr(
        PerformanceReliabilityReviewer,
        "_check_concurrency_issues",
        lambda self, diff: [],
    )
    diff = """diff --git a/src/app.py b/src/app.py
+++ b/src/app.py
@@ -1,1 +1,6 @@
+ while True:
+     try:
+         pass
+     except Exception:
+         pass
+ for item in items: db.execute("select 1")
"""
    context = ReviewContext(
        changed_files=["src/app.py"],
        diff=diff,
        repo_root="/repo",
    )

    output = await reviewer.review(context)

    assert output.severity == "blocking"
    assert output.merge_gate.decision == "block"
    finding_ids = {finding.id for finding in output.findings}
    assert "PERF-RETRY-001" in finding_ids
    assert "PERF-IO-001" in finding_ids


@pytest.mark.asyncio
async def test_performance_reviewer_skips_when_no_relevant_files():
    reviewer = PerformanceReliabilityReviewer()
    context = ReviewContext(
        changed_files=["README.md"],
        diff="+ docs",
        repo_root="/repo",
    )

    output = await reviewer.review(context)

    assert output.severity == "merge"
    assert output.merge_gate.decision == "approve"


def test_get_system_prompt_returns_performance_prompt():
    reviewer = PerformanceReliabilityReviewer()
    system_prompt = reviewer.get_system_prompt()
    
    assert system_prompt == "You are the Performance & Reliability Review Subagent.\n\nUse this shared behavior:\n- If changed_files or diff are missing, request them.\n- Focus on hot paths, IO amplification, retries, timeouts, concurrency hazards.\n- Propose minimal checks first; escalate if core systems changed.\n\nSpecialize in:\n- complexity regressions (O(n^2), unbounded loops)\n- IO amplification (extra queries/reads)\n- retry/backoff/timeouts correctness\n- concurrency hazards (async misuse, shared mutable state)\n- memory/cpu hot paths, caching correctness\n- failure modes and graceful degradation\n\nRelevant changes:\n- loops, batching, pagination, retries\n- network clients, DB access, file IO\n- orchestration changes, parallelism, caching\n\nChecks you may request:\n- targeted benchmarks (if repo has them)\n- profiling hooks or smoke run command\n- unit tests for retry/timeout behavior\n\nBlocking:\n- infinite/unbounded retry risk\n- missing timeouts on network calls in critical paths\n- concurrency bugs with shared mutable state\n\nReturn JSON with agent=\"performance_reliability\" using the standard schema.\nReturn JSON only."


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


def test_performance_io_checks_and_summary():
    reviewer = PerformanceReliabilityReviewer()
    diff = "\n".join([
        "+ for item in items: db.execute('select 1')",
        "+ for item in items: requests.get('https://example.com')",
    ])

    io_findings = reviewer._check_io_amplification(diff)
    finding_ids = {finding.id for finding in io_findings}
    assert "PERF-IO-001" in finding_ids
    assert "PERF-IO-002" in finding_ids

    summary = reviewer._generate_summary([
        _make_finding("a", "blocking"),
        _make_finding("b", "critical"),
        _make_finding("c", "warning"),
    ])
    assert "blocking" in summary
    assert "critical" in summary
    assert "warning" in summary


def test_performance_concurrency_checks_with_monkeypatched_regex(monkeypatch):
    reviewer = PerformanceReliabilityReviewer()

    class DummyMatch:
        def __init__(self, start: int) -> None:
            self._start = start

        def start(self) -> int:
            return self._start

    class DummyPattern:
        def __init__(self, matches: list[DummyMatch]) -> None:
            self._matches = matches

        def finditer(self, text: str):
            return iter(self._matches)

    import re as std_re

    def fake_compile(pattern: str, flags: int = 0):
        if pattern.startswith(r"^\+\s*global"):
            return DummyPattern([DummyMatch(0)])
        if pattern.startswith(r"^\+\s*(?:asyncio\.create_task"):
            return DummyPattern([DummyMatch(0)])
        return std_re.compile(pattern, flags)

    monkeypatch.setattr(
        "opencode_python.agents.review.agents.performance.re.compile",
        fake_compile,
    )

    diff = "\n".join([
        "+ global counter",
        "+ counter += 1",
    ])
    findings = reviewer._check_concurrency_issues(diff)
    finding_ids = {finding.id for finding in findings}
    assert "PERF-CONC-001" in finding_ids
    assert "PERF-CONC-002" in finding_ids


def test_performance_merge_gate_branches():
    reviewer = PerformanceReliabilityReviewer()
    merge_gate = reviewer._compute_merge_gate("blocking", [_make_finding("x", "blocking")])
    assert merge_gate.decision == "block"

    merge_gate = reviewer._compute_merge_gate("critical", [_make_finding("y", "critical")])
    assert merge_gate.decision == "needs_changes"

    merge_gate = reviewer._compute_merge_gate("warning", [_make_finding("z", "warning")])
    assert merge_gate.decision == "needs_changes"


def test_performance_complexity_and_severity_for_empty_findings():
    reviewer = PerformanceReliabilityReviewer()
    diff = "+             value = 1"
    findings = reviewer._check_complexity(diff)
    assert any(f.id == "PERF-COMPLEX-002" for f in findings)

    assert reviewer._compute_severity([]) == "merge"
    assert reviewer._compute_severity([_make_finding("w", "warning")]) == "warning"
    merge_gate = reviewer._compute_merge_gate("merge", [])
    assert merge_gate.decision == "approve"
    assert "No performance" in reviewer._generate_summary([])
