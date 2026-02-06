"""Migration and precedence checks for planning documentation."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SPEC_PATH = REPO_ROOT / "opencode_python/docs/planning-agent-orchestration.md"
INTEGRATION_MAP_PATH = REPO_ROOT / ".sisyphus/integration-map.md"
PLAN_ENTER_PATH = REPO_ROOT / "opencode_python/src/opencode_python/tools/prompts/plan_enter.txt"
PLAN_EXIT_PATH = REPO_ROOT / "opencode_python/src/opencode_python/tools/prompts/plan_exit.txt"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_migration_doc_required_sections_present() -> None:
    spec_text = _read(CANONICAL_SPEC_PATH)

    required_sections = [
        "## Runtime Integration Notes",
        "### Canonical Source",
        "### Runtime Surfaces",
        "### Safety Guarantees (Preserved)",
        "## Version History",
        "## References",
    ]

    for section in required_sections:
        assert section in spec_text, f"Missing migration section: {section}"


def test_policy_precedence_has_no_contradictions() -> None:
    spec_text = _read(CANONICAL_SPEC_PATH)
    integration_text = _read(INTEGRATION_MAP_PATH)

    canonical_path = "opencode_python/docs/planning-agent-orchestration.md"

    assert canonical_path in spec_text
    assert canonical_path in integration_text
    assert "Canonical source for rewritten planning policy" in integration_text
    assert "Runtime mirror surfaces" in integration_text


def test_runtime_surface_paths_exist() -> None:
    for path in [CANONICAL_SPEC_PATH, INTEGRATION_MAP_PATH, PLAN_ENTER_PATH, PLAN_EXIT_PATH]:
        assert path.exists(), f"Missing required migration surface: {path}"


def test_migration_notes_preserve_plan_safety_semantics() -> None:
    spec_text = _read(CANONICAL_SPEC_PATH)

    safety_clauses = [
        "Edit/write tools denied",
        "Tool filtering",
        "Exit to build mode",
    ]

    for clause in safety_clauses:
        assert clause in spec_text, f"Missing safety compatibility note: {clause}"
