# Problems

(append-only)
- 2026-02-06: Exact `opencode_python.sdk` compatibility check is blocked in this environment by missing runtime dependency `pydantic` (importing `dawn_kestrel.sdk.client` fails before alias assertion). Verified module identity and namespace behavior with `opencode_python.utils.json_parser` instead.
- 2026-02-06: `python3 -m compileall dawn_kestrel` still reports pre-existing syntax errors in `dawn_kestrel/agents/review/neighbors.py` and `dawn_kestrel/agents/review/pr_facts.py` (known baseline issue, unrelated to shim implementation).
- 2026-02-06: Follow-up: exact `opencode_python.sdk` alias checks pass when run with the project virtualenv interpreter (`./opencode_python/.venv/bin/python`), which has required runtime dependencies installed.
