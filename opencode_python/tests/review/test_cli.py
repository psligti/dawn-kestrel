"""Tests for review CLI helpers."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock
from click.testing import CliRunner

from opencode_python.agents.review import cli as review_cli
from opencode_python.agents.review.contracts import Finding, MergeGate, OrchestratorOutput, ToolPlan


class DummyConsole:
    def __init__(self):
        self.messages: list[str] = []

    def print(self, message: str = "") -> None:
        self.messages.append(message)


def _make_output(decision: str) -> OrchestratorOutput:
    finding = Finding(
        id="F-1",
        title="Issue",
        severity="warning",
        confidence="high",
        owner="dev",
        estimate="S",
        evidence="e",
        risk="r",
        recommendation="fix",
        suggested_patch="patch",
    )
    merge_gate = MergeGate(
        decision=decision,
        must_fix=["a"] * 6,
        should_fix=["b"] * 6,
        notes_for_coding_agent=["Review completed"],
    )
    tool_plan = ToolPlan(proposed_commands=["ruff check"], auto_fix_available=True, execution_summary="summary")
    return OrchestratorOutput(
        merge_decision=merge_gate,
        findings=[finding],
        tool_plan=tool_plan,
        subagent_results=[],
        summary="summary",
        total_findings=1,
    )


def test_get_subagents_core_and_optional():
    assert len(review_cli.get_subagents()) == 6
    assert len(review_cli.get_subagents(include_optional=True)) == 11


def test_terminal_formatting_helpers(monkeypatch):
    console = DummyConsole()
    monkeypatch.setattr(review_cli, "console", console)

    review_cli.format_terminal_progress("agent", "started", {})
    review_cli.format_terminal_progress("agent", "completed", {})
    review_cli.format_terminal_progress("agent", "error", {"error": "boom"})

    assert any("Started review" in msg for msg in console.messages)
    assert any("Completed" in msg for msg in console.messages)
    assert any("Error" in msg for msg in console.messages)


def test_result_to_markdown_and_terminal_summary(monkeypatch):
    output = _make_output("block")
    markdown = review_cli.result_to_markdown(output)
    assert "PR Review Results" in markdown
    assert "Tool Plan" in markdown
    assert "Notes for Coding Agent" in markdown
    assert "Suggested patch" in markdown

    console = DummyConsole()
    monkeypatch.setattr(review_cli, "console", console)
    review_cli.print_terminal_summary(output)
    assert any("Must Fix" in msg for msg in console.messages)
    assert any("Should Fix" in msg for msg in console.messages)


def test_terminal_summary_needs_changes(monkeypatch):
    output = _make_output("needs_changes")
    console = DummyConsole()
    monkeypatch.setattr(review_cli, "console", console)

    review_cli.print_terminal_summary(output)
    assert any("NEEDS CHANGES" in msg for msg in console.messages)


def test_result_to_markdown_needs_changes_includes_required_section():
    output = _make_output("needs_changes")
    markdown = review_cli.result_to_markdown(output)
    assert "Required Changes" in markdown


def test_terminal_result_and_error_formatting(monkeypatch):
    console = DummyConsole()
    monkeypatch.setattr(review_cli, "console", console)

    class DummyResult:
        def __init__(self, severity: str, findings: list) -> None:
            self.severity = severity
            self.findings = findings

    review_cli.format_terminal_result("agent", DummyResult("blocking", [1]))
    review_cli.format_terminal_result("agent", DummyResult("critical", []))
    review_cli.format_terminal_result("agent", DummyResult("warning", [1, 2]))
    review_cli.format_terminal_result("agent", DummyResult("merge", []))
    review_cli.format_terminal_error("agent", "boom")

    assert any("blocking" in msg for msg in console.messages)
    assert any("critical" in msg for msg in console.messages)
    assert any("warnings" in msg for msg in console.messages)
    assert any("No issues" in msg for msg in console.messages)
    assert any("Failed" in msg for msg in console.messages)


def test_cli_review_json_output(monkeypatch, tmp_path: Path):
    output = _make_output("approve")
    async_mock = AsyncMock(return_value=output)
    def fake_orchestrator(*args, **kwargs):
        return type("O", (), {"run_review": async_mock})()

    monkeypatch.setattr(review_cli, "PRReviewOrchestrator", fake_orchestrator)
    monkeypatch.setattr(review_cli, "get_subagents", lambda include_optional=False: [])
    runner = CliRunner()

    result = runner.invoke(
        review_cli.review,
        ["--repo-root", str(tmp_path), "--output", "json"],
    )

    assert result.exit_code == 0
    assert "total_findings" in result.output


def test_cli_review_markdown_output(monkeypatch, tmp_path: Path):
    output = _make_output("approve")
    async_mock = AsyncMock(return_value=output)

    def fake_orchestrator(*args, **kwargs):
        return type("O", (), {"run_review": async_mock})()

    monkeypatch.setattr(review_cli, "PRReviewOrchestrator", fake_orchestrator)
    monkeypatch.setattr(review_cli, "get_subagents", lambda include_optional=False: [])
    console = DummyConsole()
    monkeypatch.setattr(review_cli, "console", console)

    runner = CliRunner()
    result = runner.invoke(
        review_cli.review,
        ["--repo-root", str(tmp_path), "--output", "markdown"],
    )

    assert result.exit_code == 0
    assert any("PR Review Results" in msg for msg in console.messages)


def test_cli_review_terminal_output_streams_progress(monkeypatch, tmp_path: Path):
    output = _make_output("approve")

    class DummyResult:
        def __init__(self, severity: str, findings: list) -> None:
            self.severity = severity
            self.findings = findings

    class FakeOrchestrator:
        async def run_review(self, inputs, stream_callback=None):
            if stream_callback:
                await stream_callback("agent", "started", {})
                await stream_callback("agent", "completed", {}, result=DummyResult("warning", [1]))
                await stream_callback("agent", "error", {}, error_msg="boom")
            return output

    monkeypatch.setattr(review_cli, "PRReviewOrchestrator", lambda *args, **kwargs: FakeOrchestrator())
    monkeypatch.setattr(review_cli, "get_subagents", lambda include_optional=False: [])
    console = DummyConsole()
    monkeypatch.setattr(review_cli, "console", console)

    runner = CliRunner()
    result = runner.invoke(
        review_cli.review,
        ["--repo-root", str(tmp_path), "--output", "terminal"],
    )

    assert result.exit_code == 0
    assert any("Starting PR review" in msg for msg in console.messages)
    assert any("Review complete" in msg for msg in console.messages)


def test_cli_review_handles_keyboard_interrupt(monkeypatch, tmp_path: Path):
    def fake_run(coro, *args, **kwargs):
        coro.close()
        raise KeyboardInterrupt()

    monkeypatch.setattr(review_cli.asyncio, "run", fake_run)
    console = DummyConsole()
    monkeypatch.setattr(review_cli, "console", console)

    runner = CliRunner()
    result = runner.invoke(
        review_cli.review,
        ["--repo-root", str(tmp_path), "--output", "terminal"],
    )

    assert result.exit_code == 0
    assert any("Review interrupted" in msg for msg in console.messages)


def test_cli_review_raises_click_exception_on_error(monkeypatch, tmp_path: Path):
    def fake_run(coro, *args, **kwargs):
        coro.close()
        raise RuntimeError("boom")

    monkeypatch.setattr(review_cli.asyncio, "run", fake_run)
    console = DummyConsole()
    monkeypatch.setattr(review_cli, "console", console)

    runner = CliRunner()
    result = runner.invoke(
        review_cli.review,
        ["--repo-root", str(tmp_path), "--output", "terminal"],
    )

    assert result.exit_code != 0
    assert any("Error" in msg for msg in console.messages)
