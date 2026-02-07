# Napkin

## Corrections
| Date | Source | What Went Wrong | What To Do Instead |
|------|--------|----------------|-------------------|
| 2026-02-07 | self | Failed to commit after task completion | FOLLOW THE WORKFLOW: After each task completes and verification passes, IMMEDIATELY commit to changes. The workflow is: Verify → Mark in plan → Commit → Next task. Skipping the commit step leaves work untracked and can cause confusion. |

## User Preferences
- Use `uv` package manager for build and install operations
- Capture both stdout and stderr when verifying CLI commands
- Use `.sisyphus/evidence/` directory for verification artifacts

## Patterns That Work
- Build wheel: `uv build` (creates both .whl and .tar.gz in dist/)
- Install wheel: `uv pip install -U dist/*.whl`
- Capture CLI output: `command 1>stdout.txt 2>stderr.txt; echo "Exit code: $?"`
- Run targeted tests: `pytest -q -k "test_filter_pattern"`
- Use shell redirection to capture both stdout and stderr separately
- Check exit codes to verify commands succeeded (0 = success)

## Patterns That Don't Work
- Running full pytest suite (1300 tests) - times out after 120s
- Assuming `python` command exists - use `python3` or activate venv first
- Using `python -m build` without checking if build module is installed

## Domain Notes
- Package rename: opencode_python → dawn_kestrel
- Distribution name: dawn-kestrel (with hyphen)
- CLI commands: dawn-kestrel (main), parkcode/opencode-review/opencode-review-generate-docs (deprecated)
- Deprecated aliases emit warnings to stderr but still exit with code 0
- Pre-existing test failures documented in learnings (not caused by rename)
- Config filename conflict warning is pre-existing issue from Task 1

### Multi-Task Orchestration Learnings (2026-02-07)
- **Successful 7-task refactoring**: Split dawn-kestrel-flatten-rename into parallelizable waves (tasks 1-2, 3-4, 5-6-7)
- **Subagent verification**: Use session_read to extract learnings from subagent sessions before finalizing
- **All tasks verified independently**: Each task had its own acceptance criteria and verification evidence
- **Evidence preservation**: All CLI, pytest, and build evidence captured to `.sisyphus/evidence/`
- **Documentation completeness**: All 12 doc files updated, plus new `docs/STRUCTURE.md` created
- **Test coverage**: pytest suite updated with new tests for compat shims, CLI deprecations, config migration
- **Subagent learnings captured**: Extracted from sessions ses_3c5ce9d8bffeVeuMTy7yIZvju7, ses_3c5c96543ffeFgF6EkGYCB6KlE, and ses_3c5befdc5ffefAIhd28Y2KNBDK

