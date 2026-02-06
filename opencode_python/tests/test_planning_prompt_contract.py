"""Contract tests for planning orchestration policy text."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SPEC_PATH = REPO_ROOT / "opencode_python/docs/planning-agent-orchestration.md"


def _read_spec() -> str:
    return CANONICAL_SPEC_PATH.read_text(encoding="utf-8")


def test_required_sections_present() -> None:
    spec_text = _read_spec()

    required_sections = [
        "## Objective",
        "## Subagent Orchestration Plan",
        "## Gates and Evaluation",
        "## Stop Conditions",
        "## Next Best Question (Escalation Path)",
        "## First 2-3 Turn UX Policies",
    ]

    for section in required_sections:
        assert section in spec_text, f"Missing required section: {section}"


def test_forbidden_vague_directives_absent() -> None:
    spec_text = _read_spec()
    lines_with_phrase = [
        line.strip() for line in spec_text.splitlines() if "explore more" in line.lower()
    ]

    assert lines_with_phrase, "Expected forbidden phrase to be documented for enforcement"
    for line in lines_with_phrase:
        assert "forbidden" in line.lower() or "vague directives" in line.lower()


def test_stagnation_trigger_forces_strategy_switch() -> None:
    spec_text = _read_spec()

    required_triggers = [
        "Repeated Failure Signature",
        "No New Files",
        "Confidence Plateau",
        "Redundant Queries",
    ]
    required_switch_contract = [
        "Forced Strategy Switch",
        "Declare the current strategy failed",
        "Switch to a fundamentally different approach",
        "max_iterations = 2",
        "max_subagent_calls = 3",
    ]

    for trigger in required_triggers:
        assert trigger in spec_text, f"Missing stagnation trigger: {trigger}"

    for clause in required_switch_contract:
        assert clause in spec_text, f"Missing strategy-switch clause: {clause}"


def test_budget_exhaustion_emits_single_blocking_question() -> None:
    spec_text = _read_spec()

    assertions = [
        "Behavior on budget exhaustion",
        "MUST produce a blocking question",
        "A valid blocking question must",
        "Be Singular",
        "One question, not a list",
    ]

    for clause in assertions:
        assert clause in spec_text, f"Missing escalation requirement: {clause}"


def test_rejects_evidence_theater_outputs() -> None:
    spec_text = _read_spec()

    assert "Evidence Theater" in spec_text
    assert "Anti-Evidence-Theater Rule" in spec_text
    assert "STOP and ask a blocking question" in spec_text


def test_prevents_over_interviewing_after_budget_limit() -> None:
    spec_text = _read_spec()

    assert "Over-Interviewing" in spec_text
    assert "Asking questions that could be answered by available tools" in spec_text
    assert "Escalate to blocking question IF:" in spec_text
    assert "Budget exhausted (any layer)" in spec_text
