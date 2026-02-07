# Dawn Kestrel: Flatten Repo + Rename + Namespace Hygiene

## TL;DR

> **Quick Summary**: Absorb the nested `opencode_python/` project into the repo root, rename the Python package to `dawn_kestrel` and the distribution to `dawn-kestrel`, consolidate docs/tests, and keep a temporary compatibility layer so old imports/CLI/config dirs still work (with deprecation warnings).
>
> **Deliverables**:
> - Root-level Python project layout with `dawn_kestrel/`, `tests/`, `docs/`, `scripts/`
> - Distribution rename to `dawn-kestrel` + new CLI `dawn-kestrel` with subcommands (`review`, `docs`)
> - Deprecated compatibility: `import opencode_python`, legacy CLI commands, and legacy config dirs (`opencode-python` + `opencode_python`)
> - Logging namespace correctness: log record names come from `dawn_kestrel.*` (no stale hard-coded namespaces)
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Layout/packaging → import rename + compat shims → tests/docs + verification

---

## Context

### Original Request
- "Lets talk about the file and folder schema. It is all over the place" + follow-up: flatten/merge, reduce sprawl, ensure logging is from the correct namespace.

### Interview Summary (Decisions)
- Flatten/merge `opencode_python/` into repo root; fully absorb (no independent subproject boundary).
- Rename:
  - Import package: `dawn_kestrel`
  - Distribution name: `dawn-kestrel`
- CLI:
  - New command: `dawn-kestrel` with subcommands (`review`, `docs`, plus existing CLI commands)
  - Keep old commands (`parkcode`, `opencode-review`, `opencode-review-generate-docs`) as deprecated aliases.
- Source layout: **no `src/` layout**; package lives at repo root: `dawn_kestrel/`.
- User dirs: canonical XDG dirs use **hyphen**: `~/.config/dawn-kestrel`, `~/.local/share/dawn-kestrel`, `~/.cache/dawn-kestrel`.
- Compatibility (temporary): keep old import path `opencode_python`, old CLI aliases, and migrate/read legacy config dirs (`opencode-python` and `opencode_python`).
- Distribution compatibility: **do not** keep `pip install opencode-python`.
- Test strategy: **tests-after** (pytest), including new tests for shims/migration.

### Repository Findings (Evidence)
- Packaging + tooling located at `opencode_python/pyproject.toml`:
  - `[project] name = "opencode-python"`
  - `[project.scripts] parkcode/opencode-review/opencode-review-generate-docs`
  - `[tool.pytest.ini_options] pythonpath = "src"`, coverage `--cov=opencode_python`
- CLI is already a Click group at `opencode_python/src/opencode_python/cli/main.py` and currently wires review commands in:
  - `from opencode_python.agents.review.cli import review, generate_docs` then `cli.add_command(review)` / `cli.add_command(generate_docs)`
- Settings include both hyphen and underscore legacy dirs and an `OPENCODE_PYTHON_` env prefix:
  - `opencode_python/src/opencode_python/core/settings.py`
- Logging is mostly rename-safe already:
  - Many modules use `logger = logging.getLogger(__name__)` (e.g., `opencode_python/src/opencode_python/llm/client.py`)
  - Explicit `logging.basicConfig(... force=True)` exists in `opencode_python/src/opencode_python/agents/review/cli.py`

### Metis Review (Incorporated)
- Set guardrails: no import-time side effects; migration idempotent; do not delete legacy dirs; deprecation warnings to stderr.
- Explicitly define config migration precedence + conflicts and test it.
- Ensure compat shims are thin so loggers remain `dawn_kestrel.*`.
- Add automatable acceptance criteria for packaging/install, CLI aliases, import warnings, config migration, and logging namespace.

---

## Work Objectives

### Core Objective
Create a coherent root-level project layout and namespace (`dawn_kestrel`) while preserving existing behavior via temporary compatibility shims and ensuring logging attribution is correct.

### Must Have
- Single root-level Python project with `pyproject.toml` at repo root.
- Canonical code under `dawn_kestrel/` (no nested `opencode_python/src/...`).
- `dawn-kestrel` distribution builds and installs successfully.
- New CLI `dawn-kestrel` works; old CLI entry points continue to work as deprecated aliases.
- `import opencode_python` continues to work as a deprecated alias to `dawn_kestrel`.
- Config dir migration: reads legacy dirs; canonicalizes to `dawn-kestrel` dirs without deleting legacy.
- Logging record names come from `dawn_kestrel.*` for real code paths.

### Must NOT Have (Guardrails)
- No global logging configuration at import time (only at CLI entry boundary).
- No silent deletion of legacy config/data/cache directories.
- No unrelated refactors (format churn, type cleanups, reorganizing internals beyond what flatten/rename requires).
- No continued publication of `opencode-python` distribution.

### Defaults Applied (override if desired)
- Deprecation window: keep compat shims until next minor release (or 90 days), then remove.
- Config merge precedence when both legacy dirs exist:
  - Prefer existing canonical `dawn-kestrel` dir if present; else merge legacy dirs with precedence `opencode-python` (hyphen) > `opencode_python` (underscore); on filename conflicts, keep higher-precedence file and emit a warning.

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> All verification is agent-executed (commands and tool-driven checks). No manual "try it" steps.

### Test Decision
- **Infrastructure exists**: YES (pytest in `opencode_python/pyproject.toml`)
- **Automated tests**: Tests-after
- **Framework**: pytest

### Verification Commands (candidates)
- `pytest -q`
- `python -m build`
- `python -m pip install -U dist/*.whl`
- `dawn-kestrel --help`
- `dawn-kestrel review --help`
- `dawn-kestrel docs --help`
- `opencode-review --help` (deprecated alias)
- `opencode-review-generate-docs --help` (deprecated alias)
- `parkcode --help` (deprecated alias)

### Evidence Capture
- UI not involved; capture CLI stdout/stderr and pytest output as evidence under `.sisyphus/evidence/`.
- Suggested filenames:
  - `.sisyphus/evidence/cli-help-dawn-kestrel.txt`
  - `.sisyphus/evidence/cli-help-opencode-review-deprecated.txt`
  - `.sisyphus/evidence/pytest.txt`
  - `.sisyphus/evidence/import-compat-warning.txt`

### Agent-Executed QA Scenarios (examples to include per task)

Scenario: Import compat shim emits deprecation warning
  Tool: Bash (python)
  Preconditions: Built wheel installed or editable install active
  Steps:
    1. Run a Python snippet importing `opencode_python` with warnings capture
    2. Assert at least one DeprecationWarning mentions `dawn_kestrel`
    3. Assert imported objects come from `dawn_kestrel` (e.g., module name)
  Expected Result: Import succeeds; warning emitted; behavior preserved

Scenario: Legacy config dirs are migrated/canonicalized
  Tool: Bash (python + env)
  Preconditions: Temporary XDG dirs populated with legacy files
  Steps:
    1. Set `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` to temp dirs
    2. Create both legacy dirs and place distinct marker files
    3. Run `dawn-kestrel --help` (or a lightweight command that loads settings)
    4. Assert canonical `dawn-kestrel` dirs exist
    5. Assert canonical files chosen per precedence rule; legacy dirs remain
  Expected Result: Deterministic migration without deletions

Scenario: Logging namespace uses dawn_kestrel
  Tool: Bash (python)
  Preconditions: Logging configured at CLI entry (or test config)
  Steps:
    1. Import a representative module from `dawn_kestrel` that emits a log
    2. Capture a log record via pytest caplog (preferred) or a custom handler
    3. Assert `record.name.startswith("dawn_kestrel")`
  Expected Result: No `opencode_python.*` logger names for real code paths

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Foundation + layout):
- Task 1: Root-level layout + packaging move
- Task 2: New CLI command surface (`dawn-kestrel` group) with subcommands

Wave 2 (Rename + compatibility):
- Task 3: Rename imports/modules to `dawn_kestrel` and build compat shim `opencode_python`
- Task 4: Config dir + env var compatibility/migration rules

Wave 3 (Docs/tests + hardening):
- Task 5: Update tests + add new shim/migration/logging tests
- Task 6: Update docs and any hard-coded paths; add a simple structure map doc
- Task 7: End-to-end verification (build wheel, install, run CLI, run tests)

---

## TODOs

- [x] 1. Establish root project layout and move packaging to repo root

  **What to do**:
  - Move `opencode_python/pyproject.toml` to repo root `pyproject.toml` and adjust paths for the new flat package layout.
  - Move code from `opencode_python/src/opencode_python/` to `dawn_kestrel/` at repo root.
  - Move `opencode_python/tests/` to `tests/` and `opencode_python/docs/` to `docs/`.
  - Update pytest discovery to match the new layout (remove/adjust `pythonpath = "src"`, ensure `testpaths = ["tests"]`).
  - Keep `scripts/validate-docs.py` at root; decide where other root docs belong (keep at root or fold into `docs/`).
  - Remove/absorb any nested git state under `opencode_python/` (e.g., `opencode_python/HEAD`, any `opencode_python/.git`).

  **Must NOT do**:
  - Do not change runtime behavior beyond path/name changes required for the move.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `git-master` (safe moves/renames + commit hygiene)

  **Parallelization**:
  - Can Run In Parallel: YES (with Task 2)

  **References**:
  - `opencode_python/pyproject.toml` - current packaging, scripts, pytest config (must be translated to root + new package)
  - `opencode_python/src/opencode_python/` - canonical code tree to move
  - `opencode_python/tests/` - test tree to move and update
  - `opencode_python/docs/` - docs tree to move and update
  - `scripts/validate-docs.py` - root tooling to keep working

  **Acceptance Criteria**:
  - Running from repo root, `python -c "import dawn_kestrel; print(dawn_kestrel.__name__)"` prints `dawn_kestrel`.

  **Agent-Executed QA Scenarios**:

  Scenario: Repo-root import works after move
    Tool: Bash (python)
    Preconditions: Files moved; repo root is the project root
    Steps:
      1. Run: `python -c "import dawn_kestrel; print(dawn_kestrel.__file__)"`
      2. Assert: exit code 0
      3. Capture stdout/stderr to `.sisyphus/evidence/import-dawn-kestrel.txt`
    Expected Result: Import resolves from repo root
    Evidence: `.sisyphus/evidence/import-dawn-kestrel.txt`

- [x] 2. Implement new CLI surface: `dawn-kestrel` Click group + subcommands

  **What to do**:
  - Ensure the new distribution exposes a top-level console script `dawn-kestrel`.
  - Keep existing CLI group behavior from `opencode_python/src/opencode_python/cli/main.py`, but migrate to `dawn_kestrel/cli/...`.
  - Rename/reshape commands so review docs generation becomes `dawn-kestrel docs` (and `dawn-kestrel review`).
  - Wire deprecated aliases:
    - `parkcode` should invoke `dawn-kestrel` (or print a deprecation warning and then invoke)
    - `opencode-review` should invoke `dawn-kestrel review`
    - `opencode-review-generate-docs` should invoke `dawn-kestrel docs`

  **Must NOT do**:
  - Do not configure global logging at import time.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `git-master`

  **Parallelization**:
  - Can Run In Parallel: YES (with Task 1)

  **References**:
  - `opencode_python/src/opencode_python/cli/main.py` - existing click group + command wiring
  - `opencode_python/src/opencode_python/agents/review/cli.py` - review and generate_docs commands
  - `opencode_python/pyproject.toml` `[project.scripts]` - current script targets

  **Acceptance Criteria**:
  - `dawn-kestrel --help` exits 0
  - `dawn-kestrel review --help` exits 0
  - `dawn-kestrel docs --help` exits 0

  **Agent-Executed QA Scenarios**:

  Scenario: New CLI help works
    Tool: Bash
    Preconditions: Package installed (editable or wheel)
    Steps:
      1. Run: `dawn-kestrel --help > .sisyphus/evidence/cli-help-dawn-kestrel.txt 2>&1`
      2. Assert: exit code 0
      3. Run: `dawn-kestrel review --help > .sisyphus/evidence/cli-help-dawn-kestrel-review.txt 2>&1`
      4. Assert: exit code 0
      5. Run: `dawn-kestrel docs --help > .sisyphus/evidence/cli-help-dawn-kestrel-docs.txt 2>&1`
      6. Assert: exit code 0
    Expected Result: Help text renders for all commands
    Evidence: `.sisyphus/evidence/cli-help-dawn-kestrel.txt`

  Scenario: Deprecated CLI aliases still work and warn
    Tool: Bash
    Preconditions: Package installed; legacy scripts still declared
    Steps:
      1. Run: `opencode-review --help > .sisyphus/evidence/cli-help-opencode-review-deprecated.txt 2>&1`
      2. Assert: exit code 0
      3. Assert: output contains a clear deprecation notice mentioning `dawn-kestrel`
    Expected Result: Alias works, warns, and remains non-breaking
    Evidence: `.sisyphus/evidence/cli-help-opencode-review-deprecated.txt`

- [x] 3. Rename imports to `dawn_kestrel` and add `opencode_python` import compatibility shim

  **What to do**:
  - Update internal imports from `opencode_python.*` to `dawn_kestrel.*` throughout code and tests.
  - Create an `opencode_python/` package that:
    - Emits a DeprecationWarning on import
    - Redirects *module loading* to `dawn_kestrel.*` so real code executes under the `dawn_kestrel` module names (preserves `logging.getLogger(__name__)` namespaces)
    - Registers `sys.modules["opencode_python.*"] = sys.modules["dawn_kestrel.*"]` aliases after loading the real module
  - Keep shim code minimal and side-effect-free (no global logging config, no filesystem writes).

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `git-master`

  **References**:
  - `opencode_python/src/opencode_python/__init__.py` - current public API exports to mirror
  - Any file importing `opencode_python` (grep surface is large; start with SDK + CLI)

  **Acceptance Criteria**:
  - `python -c "import dawn_kestrel"` succeeds
  - `python -c "import opencode_python"` succeeds and emits a DeprecationWarning
  - `python -c "import opencode_python.sdk; import dawn_kestrel.sdk; import sys; assert sys.modules['opencode_python.sdk'] is sys.modules['dawn_kestrel.sdk']"` exits 0
  - `pytest -q` passes (or failing tests are updated in Task 5)

  **Agent-Executed QA Scenarios**:

  Scenario: Compat import preserves new logger namespace
    Tool: Bash (python)
    Preconditions: Compat shim implemented
    Steps:
      1. Run a Python snippet that imports a representative module via `opencode_python` and emits a log record
      2. Assert: emitted record name starts with `dawn_kestrel.` (not `opencode_python.`)
      3. Capture output to `.sisyphus/evidence/log-namespace-via-compat.txt`
    Expected Result: Logs attribute to `dawn_kestrel.*` even when imported via old name
    Evidence: `.sisyphus/evidence/log-namespace-via-compat.txt`

- [x] 4. Config dirs + env var compatibility/migration (XDG + legacy)

  **What to do**:
  - Update defaults in settings to canonical `dawn-kestrel` dirs.
  - Continue reading legacy dirs (`opencode-python` and `opencode_python`) during the deprecation window.
  - Support both env var namespaces:
    - New: `DAWN_KESTREL_...`
    - Legacy: `OPENCODE_PYTHON_...`
  - Implement env precedence (new wins) without requiring duplicating every field alias by hand (prefer a pydantic-settings custom env source).
  - Define idempotent merge/precedence rules and ensure warnings are actionable.

  **Must NOT do**:
  - Do not delete legacy dirs automatically.
  - Do not create dirs on import; only on first explicit use if necessary.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `git-master`

  **References**:
  - `opencode_python/src/opencode_python/core/settings.py` - current app_name, XDG defaults, env_file locations, env_prefix
  - `opencode_python/tests/test_config.py` and `opencode_python/tests/test_multi_env_loading.py` - expectations around config dirs and env handling

  **Acceptance Criteria**:
  - Pytest includes new tests that set `XDG_*_HOME` and validate canonicalization/migration.

  **Agent-Executed QA Scenarios**:

  Scenario: XDG legacy dirs are merged deterministically
    Tool: Bash (python + env)
    Preconditions: Tests or a script can set XDG env vars
    Steps:
      1. Create temp dirs; set `XDG_CONFIG_HOME` and populate both legacy names with distinct marker files
      2. Run a settings load (or CLI command that loads settings)
      3. Assert canonical `dawn-kestrel` dir exists and contains expected merged results
      4. Assert legacy dirs still exist
    Expected Result: Deterministic precedence; idempotent behavior
    Evidence: `.sisyphus/evidence/xdg-migration.txt`

- [x] 5. Update pytest suite for rename + add coverage for compat shims and logging namespace

  **What to do**:
  - Update tests to import/patch `dawn_kestrel.*` instead of `opencode_python.*` where appropriate.
  - Add explicit tests for:
    - Import shim warning (`import opencode_python`)
    - CLI alias commands still work and warn
    - Legacy config dirs merge precedence
    - Logging record namespace (`record.name.startswith("dawn_kestrel")`)
  - Update coverage target from `--cov=opencode_python` to `--cov=dawn_kestrel`.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `git-master`

  **References**:
  - `opencode_python/pyproject.toml` `[tool.pytest.ini_options] addopts` - coverage target to rename
  - `opencode_python/tests/test_planning_docs_migration.py` - hard-coded canonical doc/prompt paths
  - `opencode_python/src/opencode_python/agents/review/cli.py` - logging config + CLI flows

  **Acceptance Criteria**:
  - `pytest -q` passes

  **Agent-Executed QA Scenarios**:

  Scenario: Full test suite passes under new layout
    Tool: Bash
    Preconditions: Moves/renames complete
    Steps:
      1. Run: `pytest -q > .sisyphus/evidence/pytest.txt 2>&1`
      2. Assert: exit code 0
    Expected Result: All tests green
    Evidence: `.sisyphus/evidence/pytest.txt`

- [x] 6. Update docs + add a “Where does X go?” structure map

  **What to do**:
  - Replace references to `opencode_python/` paths and `opencode-python` install name with `dawn_kestrel` / `dawn-kestrel`.
  - Update canonical pointers in planning docs and prompt references.
  - Add a short structure guide mapping key directories (code/tests/docs/scripts) and logging namespace rules.

  **Recommended Agent Profile**:
  - Category: `writing`
  - Skills: `git-master`

  **References**:
  - `opencode_python/README.md` - install/import examples
  - `opencode_python/docs/getting-started.md` - install/import examples
  - `opencode_python/docs/planning-agent-orchestration.md` - canonical pointers
  - `opencode_python/src/opencode_python/tools/prompts/plan_enter.txt` and `plan_exit.txt` - referenced by docs

  **Acceptance Criteria**:
  - `python scripts/validate-docs.py` (or equivalent) runs successfully if that script is part of doc checks.

- [x] 7. End-to-end verification: build + install + CLI smoke + logging namespace

  **What to do**:
  - Build wheel/sdist, install wheel into a clean environment, run CLI help commands, run pytest.
  - Verify deprecated aliases still work and emit warnings on stderr.
  - Capture evidence artifacts (stdout/stderr) for key scenarios.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `git-master`

  **Acceptance Criteria**:
  - `python -m build` succeeds
  - `python -m pip install -U dist/*.whl` succeeds
  - `dawn-kestrel --help` exits 0
  - `opencode-review --help` exits 0 and emits deprecation warning to stderr
  - `pytest -q` passes

---

## Commit Strategy (suggested)
- Commit after each wave with messages like:
  - `refactor(layout): flatten opencode_python into repo root`
  - `refactor(cli): add dawn-kestrel entrypoint with subcommands`
  - `refactor(rename): migrate namespace to dawn_kestrel with compat shims`
  - `test(rename): update pytest suite for new namespace and migration`
  - `docs(rename): update installation/import paths and structure map`
