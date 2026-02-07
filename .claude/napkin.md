# Napkin

## Corrections
| Date | Source | What Went Wrong | What To Do Instead |
|------|--------|----------------|-------------------|
| 2026-02-07 | self | Tried `python -m build` but command not found | Use `uv build` instead when build module not available, or activate venv first |
| 2026-02-07 | self | Tried running full pytest suite with 1300 tests | Use targeted subsets with `-k` flag to avoid timeout (e.g., `-k "compat or config"`) |

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
