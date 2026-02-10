# Security Agent Improvement Execution Plan

## TL;DR

> **Quick Summary**: Operationalize `docs/security-agent-improvement-plan.md` into a deterministic, diff-aware, evidence-first security review pipeline by fixing FSM state/dedup flaws first, then replacing mock analysis with real diff scanning, then hardening with tests, logging, and performance controls.
>
> **Deliverables**:
> - Correct dedup/state tracking in FSM review orchestration
> - Real diff-based security scanning outputs (not simulated findings)
> - Validation gates for changed-files-only findings and mandatory evidence
> - Expanded pytest coverage (unit + integration) and rollout-ready docs
> - Large-diff performance handling, bounded parallelization, and confidence scoring
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 6 waves
> **Critical Path**: Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 6 -> Task 8 -> Task 14

---

## Context

### Original Request
Review `docs/security-agent-improvement-plan.md` and create an executable plan for it.

### Interview Summary
**Key Discussions**:
- Analysis-first pass was requested and completed (parallel explore + librarian + targeted repo inspection).
- Full source scope (US-001..US-006 and TD-001..TD-018) is retained.
- This plan is implementation-focused but remains planning-only in this session.

**Research Findings**:
- `docs/security-agent-improvement-plan.md` is comprehensive but partially aspirational; concrete execution details needed.
- Existing implementation surfaces:
  - `dawn_kestrel/agents/review/fsm_security.py` (FSM orchestration, todo/task lifecycle, mock subagent execution)
  - `dawn_kestrel/agents/review/agents/security.py` (LLM security reviewer)
  - `dawn_kestrel/agents/review/context_builder.py` (changed-files and diff source)
  - `dawn_kestrel/agents/review/agents/diff_scoper.py` (risk/routing pre-pass)
  - `tests/review/agents/test_security_reviewer.py` (existing test baseline)
- Current gaps visible in code:
  - duplicate/overlapping todo creation logic in FSM example flow,
  - `_simulate_subagent_execution()` uses static mock findings,
  - `_review_investigation_results()` appends without global dedup,
  - prompt context has diff size and file list but not robust hunk-level usage.

### Metis Review
**Identified Gaps (resolved by this plan)**:
- Add explicit guardrails to prevent scope creep and API drift.
- Define failure-mode acceptance criteria (timeouts, malformed outputs, missing diff context).
- Add deterministic behavior constraints (ordering, dedup rules, bounded fan-out).
- Make assumptions explicit and provide defaults for ambiguous items.

---

## Work Objectives

### Core Objective
Deliver a reliable security-review workflow that reports only unique, evidence-backed findings tied to changed code, with stable state across FSM iterations and measurable validation/performance.

### Concrete Deliverables
- Updated orchestration behavior in `dawn_kestrel/agents/review/fsm_security.py`.
- Diff-context and filtering integration through `dawn_kestrel/agents/review/context_builder.py` and prompt builders.
- Security review integration alignment with `dawn_kestrel/agents/review/agents/security.py` and `dawn_kestrel/agents/review/agents/diff_scoper.py`.
- New/updated tests under `tests/review/agents/` and `tests/review/` for dedup/state/real-analysis behaviors.
- Documentation updates reflecting real-analysis mode and verification expectations.

### Definition of Done
- [ ] No duplicate findings in final output for repeated iterations with identical subagent results.
- [ ] 100% of final findings reference changed files only.
- [ ] 100% of final findings contain non-empty evidence that maps to diff content.
- [ ] All targeted test suites pass, and full pytest passes.
- [ ] Performance target met for large diff scenario (<= 5 minutes for 100-file PR baseline test harness).

### Must Have
- Deterministic state transitions and dedup logic.
- Diff-aware, changed-lines-focused finding generation.
- Strict validation gates (file path, line mapping, evidence, uniqueness).
- Clear logs for skipped tasks/findings and reasons.

### Must NOT Have (Guardrails)
- No implementation outside defined scope of TD-001..TD-018.
- No unchecked freeform command execution from model outputs.
- No findings for unchanged files.
- No acceptance criteria that require manual human verification.
- No silent backward-incompatible API shape changes in reviewer contracts.
- No broad Agentic SDK refactors outside `dawn_kestrel/agents/review/` unless explicitly unavoidable.

### Defaults Applied
- **Diff chunk budget**: 5000 characters per subagent prompt segment (deterministic truncation order).
- **Parallel scanner cap**: 4 concurrent subagent tasks maximum.
- **Confidence threshold**: 0.50 default inclusion threshold (configurable).
- **Error strategy**: malformed finding payloads are rejected and logged; review continues unless critical system failure occurs.

### SDK Change Budget
- **Preferred edit scope**: `dawn_kestrel/agents/review/*`, `tests/review/*`, and related docs.
- **Allowed with justification**: minimal contract touches tightly coupled to review output behavior.
- **Disallowed by default**: cross-cutting SDK-wide API redesigns, runtime architecture rewrites, or unrelated module churn.

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> Every acceptance criterion must be executable by agent tooling (bash/pytest/etc.).

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: Tests-after
- **Framework**: `pytest`

### Agent-Executed QA Scenarios (MANDATORY)
- Every task includes at least one happy-path and one negative-path scenario.
- Evidence is command output and/or saved artifacts under `.sisyphus/evidence/`.

---

## Execution Strategy

### Parallel Execution Waves

```text
Wave 1 (Start Immediately):
├── Task 1: Baseline contracts + assumptions lock
└── Task 10: Documentation skeleton and ADR prep

Wave 2 (After Wave 1):
├── Task 2: Dedup + task-state persistence correctness
└── Task 9: Logging/audit hardening

Wave 3 (After Wave 2):
├── Task 3: Diff-context propagation into delegation prompts
└── Task 7: Unit tests for state/dedup/validation

Wave 4 (After Wave 3):
├── Task 4: Real scanner execution path (replace mock simulation)
└── Task 6: Validation gate for changed-files/evidence/uniqueness

Wave 5 (After Wave 4):
├── Task 5: FSM review-task generation and re-delegation safeguards
├── Task 8: Integration tests for end-to-end real analysis
├── Task 11: Large-diff optimization and cache strategy
└── Task 12: Parallel subagent execution with bounded concurrency

Wave 6 (After Wave 5):
├── Task 13: Confidence scoring + threshold behavior
└── Task 14: Full regression + rollout gate

Critical Path: 1 -> 2 -> 3 -> 4 -> 6 -> 8 -> 14
Parallel Speedup: ~35-45% vs sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|----------------------|
| 1 | None | 2, 3, 7 | 10 |
| 2 | 1 | 3, 4, 5, 6, 7 | 9 |
| 3 | 1, 2 | 4, 6, 8 | 7 |
| 4 | 2, 3 | 6, 8, 11, 12 | 6 |
| 5 | 2, 4 | 8, 14 | 8, 11, 12 |
| 6 | 2, 3, 4 | 8, 14 | 4 |
| 7 | 1, 2, 3 | 8, 14 | 3 |
| 8 | 3, 4, 5, 6, 7 | 14 | 11, 12 |
| 9 | 1, 2 | 14 | 2 |
| 10 | 1 | 14 | 1 |
| 11 | 4 | 14 | 12, 8 |
| 12 | 4 | 14 | 11, 8 |
| 13 | 8, 12 | 14 | None |
| 14 | 5, 6, 8, 9, 10, 11, 12, 13 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 10 | `task(category="unspecified-high", load_skills=["git-master"], run_in_background=false)` and `task(category="writing", load_skills=["git-master"], run_in_background=false)` |
| 2 | 2, 9 | Same category in two independent runs |
| 3 | 3, 7 | Diff/context implementation + test pack in parallel |
| 4 | 4, 6 | Real analysis path and validation gate integration |
| 5 | 5, 8, 11, 12 | Split across executor-focused agents |
| 6 | 13, 14 | Final quality controls and system-wide verification |

---

## TODOs

- [x] 1. Lock baseline contracts, assumptions, and measurable success gates

  **What to do**:
  - Capture current behavior contracts for findings, todos, and FSM transitions.
  - Define explicit defaults for unresolved ambiguities (diff chunk size, concurrency cap, confidence threshold, error behavior).
  - Record backward-compatibility expectations for reviewer output schema.

  **Must NOT do**:
  - Do not modify runtime behavior in this task.
  - Do not introduce new features outside documented TD scope.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: cross-cutting contract analysis with downstream implementation impact.
  - **Skills**: [`git-master`]
    - `git-master`: keeps contract changes traceable and atomic.
  - **Skills Evaluated but Omitted**:
    - `playwright`: no browser work.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 10)
  - **Blocks**: 2, 3, 7
  - **Blocked By**: None

  **References**:
  - `docs/security-agent-improvement-plan.md` - source objectives and TD list.
  - `dawn_kestrel/agents/review/fsm_security.py:207` - orchestrator state model and lifecycle.
  - `dawn_kestrel/agents/review/base.py` - shared review abstractions.
  - `dawn_kestrel/agents/review/contracts.py` - output contract constraints.

  **Acceptance Criteria**:
  - [ ] Contract/defaults document created and checked into docs/plans path.
  - [ ] Explicit defaults include: diff chunking, timeout handling, concurrency cap, confidence threshold.
  - [ ] No production code modified in this task.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Contract/defaults artifact includes required fields
    Tool: Bash
    Preconditions: Artifact file added
    Steps:
      1. Run: python -m pytest -q tests/review -k "contract or defaults"
      2. Assert: exit code 0
      3. Run: grep for required keys (diff_chunk_size, max_parallel_subagents, confidence_threshold)
    Expected Result: artifact contains all required defaults
    Failure Indicators: missing required keys or failing tests
    Evidence: terminal output capture

  Scenario: No runtime changes in baseline task
    Tool: Bash
    Preconditions: Task branch with Task 1 only
    Steps:
      1. Run: git diff --name-only HEAD~1..HEAD
      2. Assert: only planning/doc files changed
    Expected Result: no runtime files changed
    Failure Indicators: runtime source files appear in diff
    Evidence: git diff file list output
  ```

  **Commit**: YES
  - Message: `docs(plan): lock baseline contracts and defaults`
  - Files: planning/docs artifacts only
  - Pre-commit: targeted docs/contract checks

---

- [x] 2. Implement finding/task dedup and persistent task-state correctness (TD-001, TD-002, TD-003)

  **What to do**:
  - Add processed finding/task tracking sets and enforce skip-on-processed behavior.
  - Ensure todo completion updates are idempotent and count logic is accurate.
  - Prevent reprocessing/redelegation across iterations.

  **Must NOT do**:
  - Do not allow duplicate append paths.
  - Do not mutate completed tasks back to pending without explicit rule.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: state-machine correctness and idempotency are safety-critical.
  - **Skills**: [`git-master`]
    - `git-master`: disciplined iterative commits around state logic.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 9)
  - **Blocks**: 3, 4, 5, 6, 7
  - **Blocked By**: 1

  **References**:
  - `dawn_kestrel/agents/review/fsm_security.py:242` - state containers and initialization.
  - `dawn_kestrel/agents/review/fsm_security.py:644` - task delegation loop.
  - `dawn_kestrel/agents/review/fsm_security.py:910` - result processing and append logic.
  - `dawn_kestrel/agents/review/fsm_security.py:953` - review-task creation IDs.

  **Acceptance Criteria**:
  - [ ] Duplicate findings with identical IDs are reported once.
  - [ ] Completed tasks are not redelegated in subsequent iterations.
  - [ ] Todo completion fraction reflects true completed/total count.
  - [ ] New tests verify idempotent behavior across 2+ loop iterations.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Dedup across repeated iterations
    Tool: Bash
    Preconditions: new tests for repeated-iteration dedup added
    Steps:
      1. Run: python -m pytest -q tests/review/agents -k dedup_iteration
      2. Assert: exit code 0
      3. Assert: reported total findings equals unique IDs count
    Expected Result: duplicate findings not re-added
    Failure Indicators: count inflation across iterations
    Evidence: pytest output and assertion logs

  Scenario: Completed task is not redelegated
    Tool: Bash
    Preconditions: task-state regression test added
    Steps:
      1. Run: python -m pytest -q tests/review/agents -k no_redelegation
      2. Assert: exit code 0
      3. Assert: delegated task IDs remain stable after second loop
    Expected Result: previously completed tasks are skipped
    Failure Indicators: additional duplicate delegation events
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `fix(security-review): enforce finding/task dedup and stable todo state`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, tests
  - Pre-commit: targeted pytest for dedup/state

---

- [x] 3. Pass actionable diff context into subagent prompts (TD-004)

  **What to do**:
  - Enhance `_build_subagent_prompt()` to include diff hunks and file-level context, not only file names and diff size.
  - Implement truncation/chunk strategy with deterministic ordering for large diffs.
  - Include changed file list and hunk metadata (file path, approximate line ranges).

  **Must NOT do**:
  - Do not pass full unbounded diffs into prompt.
  - Do not lose association between findings and diff hunk source.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: prompt engineering tied to deterministic parsing and scalability.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 7)
  - **Blocks**: 4, 6, 8
  - **Blocked By**: 1, 2

  **References**:
  - `dawn_kestrel/agents/review/fsm_security.py:684` - subagent prompt builder target.
  - `dawn_kestrel/agents/review/context_builder.py:71` - context build source for changed files/diff.
  - `dawn_kestrel/agents/review/utils/git.py` - diff and changed-file retrieval path.

  **Acceptance Criteria**:
  - [ ] Prompt includes changed files and diff hunk snippets with bounded size.
  - [ ] Chunking deterministic across repeated runs for same diff input.
  - [ ] Tests validate truncation behavior and metadata presence.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Prompt contains bounded diff context
    Tool: Bash
    Preconditions: prompt-construction test exists
    Steps:
      1. Run: python -m pytest -q tests/review/agents -k prompt_diff_context
      2. Assert: exit code 0
      3. Assert: prompt contains changed files and diff snippet markers
    Expected Result: subagent receives targeted diff context
    Failure Indicators: prompt missing diff blocks or file metadata
    Evidence: pytest output

  Scenario: Large diff truncation remains deterministic
    Tool: Bash
    Preconditions: synthetic large-diff fixture added
    Steps:
      1. Run: python -m pytest -q tests/review/agents -k diff_truncation_deterministic
      2. Assert: exit code 0
      3. Assert: repeated prompt builds produce identical output
    Expected Result: deterministic truncation/chunking
    Failure Indicators: non-deterministic prompt order/content
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `feat(security-review): add bounded diff context to subagent prompts`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, tests
  - Pre-commit: prompt-focused pytest

---

- [x] 4. Replace simulated subagent execution with real diff-based scanners (TD-005, TD-006, TD-007, TD-008)

  **What to do**:
  - Replace `_simulate_subagent_execution()` mock payloads with real analyzer logic over changed/added lines.
  - Implement analyzer routines for secrets, injections, unsafe functions, crypto issues.
  - Ensure output includes accurate file path, line number, severity, and evidence from diff.

  **Must NOT do**:
  - Do not emit static findings unrelated to current diff.
  - Do not scan unchanged code paths by default.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: central behavior replacement with broad impact.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 6)
  - **Blocks**: 6, 8, 11, 12
  - **Blocked By**: 2, 3

  **References**:
  - `dawn_kestrel/agents/review/fsm_security.py:737` - simulation path to replace.
  - `dawn_kestrel/agents/review/agents/security.py:37` - security check intent and pattern baseline.
  - `dawn_kestrel/agents/review/agents/diff_scoper.py:31` - risk/routing context for scanner prioritization.

  **Acceptance Criteria**:
  - [ ] Findings generated only when real diff evidence exists.
  - [ ] Secret/injection/unsafe/crypto analyzers each covered by tests.
  - [ ] No scanner emits results for unchanged files/removed lines unless explicitly configured.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Real analyzers detect seeded vulnerabilities in synthetic diff
    Tool: Bash
    Preconditions: integration fixtures with known seeded vulnerabilities
    Steps:
      1. Run: python -m pytest -q tests/review/agents -k real_scanner_seeded
      2. Assert: exit code 0
      3. Assert: findings include expected IDs/severities and match seeded lines
    Expected Result: real analyzers produce grounded findings
    Failure Indicators: no findings, wrong file/line mapping, or static mock signatures
    Evidence: pytest output

  Scenario: Clean diff produces no false positives for unchanged files
    Tool: Bash
    Preconditions: clean-diff fixture exists
    Steps:
      1. Run: python -m pytest -q tests/review/agents -k unchanged_file_no_findings
      2. Assert: exit code 0
      3. Assert: findings list empty or only changed-file references
    Expected Result: no off-scope findings
    Failure Indicators: findings referencing files absent from changed_files
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `feat(security-review): replace mock scanners with real diff-based analysis`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, helper modules, tests
  - Pre-commit: scanner-specific pytest suite

---

- [x] 5. Harden dynamic review-task creation and prevent runaway loops (supports TD-002/TD-003 lifecycle goals)

  **What to do**:
  - Ensure review tasks (ID >= 100) are created once per unique need.
  - Add guards against recursive growth and duplicate dependency references.
  - Enforce max-iteration and stop reasons with explicit logs.

  **Must NOT do**:
  - Do not create review tasks from duplicate finding references.
  - Do not allow unbounded todo growth across iterations.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: loop-control correctness under dynamic planning.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 8, 11, 12)
  - **Blocks**: 8, 14
  - **Blocked By**: 2, 4

  **References**:
  - `dawn_kestrel/agents/review/fsm_security.py:953` - dynamic review task creation.
  - `dawn_kestrel/agents/review/fsm_security.py:310` - main iteration loop and max iteration guard.

  **Acceptance Criteria**:
  - [ ] Duplicate review tasks are not created from same finding set.
  - [ ] Iteration loop terminates with explicit stop reason when caps reached.
  - [ ] Todo counts remain consistent with created/completed sets.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Review-task creation remains bounded
    Tool: Bash
    Preconditions: loop-control tests added
    Steps:
      1. Run: python -m pytest -q tests/review/agents -k review_task_bounded
      2. Assert: exit code 0
      3. Assert: number of dynamic todos does not exceed configured limit
    Expected Result: bounded task generation
    Failure Indicators: unbounded todo growth or repeated duplicate review tasks
    Evidence: pytest output

  Scenario: Max-iteration stop triggers safely
    Tool: Bash
    Preconditions: max-iteration negative test added
    Steps:
      1. Run: python -m pytest -q tests/review/agents -k max_iteration_stop
      2. Assert: exit code 0
      3. Assert: final assessment includes stop note and no crash
    Expected Result: safe deterministic stop behavior
    Failure Indicators: infinite loop or abrupt exception without context
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `fix(security-review): bound dynamic review-task generation and loop control`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, tests
  - Pre-commit: lifecycle-focused pytest

---

- [x] 6. Add strict validation gates for changed-files scope, evidence quality, and uniqueness (TD-009, TD-010, TD-011)

  **What to do**:
  - Filter out any finding whose file is not in `context.changed_files`.
  - Reject empty/invalid evidence and non-resolvable line mappings.
  - Add uniqueness checks by ID and content signature.

  **Must NOT do**:
  - Do not allow findings without evidence into final assessment.
  - Do not allow duplicate semantic findings from multi-scanner overlap.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: correctness gate for final output integrity.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 4)
  - **Blocks**: 8, 14
  - **Blocked By**: 2, 3, 4

  **References**:
  - `dawn_kestrel/agents/review/fsm_security.py:910` - findings ingestion pipeline.
  - `dawn_kestrel/agents/review/context_builder.py:127` - context changed_files source.
  - `docs/security-agent-improvement-plan.md` - acceptance requirements for evidence and changed-file scope.

  **Acceptance Criteria**:
  - [ ] 100% of final findings reference files from `changed_files`.
  - [ ] Findings with empty/invalid evidence are dropped and logged.
  - [ ] Duplicate ID/content findings collapse to one canonical finding.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Off-scope findings are filtered
    Tool: Bash
    Preconditions: fixture includes mixed in-scope and out-of-scope findings
    Steps:
      1. Run: python -m pytest -q tests/review/agents -k filter_unchanged_files
      2. Assert: exit code 0
      3. Assert: resulting findings reference only changed files
    Expected Result: out-of-scope findings excluded
    Failure Indicators: any unchanged-file finding remains
    Evidence: pytest output

  Scenario: Missing evidence causes finding rejection
    Tool: Bash
    Preconditions: fixture includes empty evidence finding
    Steps:
      1. Run: python -m pytest -q tests/review/agents -k reject_empty_evidence
      2. Assert: exit code 0
      3. Assert: rejected finding absent from final assessment
    Expected Result: evidence-less findings never ship
    Failure Indicators: empty-evidence findings present in output
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `fix(security-review): enforce finding scope evidence and uniqueness gates`
  - Files: orchestrator/validation logic + tests
  - Pre-commit: validation pytest suite

---

- [x] 7. Build unit test suite for dedup/state/prompt/validation regressions (TD-012)

  **What to do**:
  - Add focused unit tests for dedup, task-state persistence, prompt context format, and validation gates.
  - Keep tests deterministic and fixture-based.

  **Must NOT do**:
  - Do not couple unit tests to network/external tool dependencies.
  - Do not duplicate integration-coverage scenarios here.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: high-value guardrails around core correctness behavior.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 3)
  - **Blocks**: 8, 14
  - **Blocked By**: 1, 2, 3

  **References**:
  - `tests/review/agents/test_security_reviewer.py` - existing unit-test style.
  - `dawn_kestrel/agents/review/fsm_security.py` - primary behavior under test.

  **Acceptance Criteria**:
  - [ ] New test cases cover dedup, no-redelegation, validation filtering, and prompt diff context.
  - [ ] Unit test suite passes consistently across repeated runs.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Unit suite passes for core correctness behaviors
    Tool: Bash
    Preconditions: new unit tests added
    Steps:
      1. Run: python -m pytest -q tests/review/agents/test_security_reviewer.py
      2. Assert: exit code 0
      3. Run: python -m pytest -q tests/review/agents -k "dedup or state or validation"
      4. Assert: exit code 0
    Expected Result: correctness regressions guarded
    Failure Indicators: failures in dedup/state/validation tests
    Evidence: pytest output

  Scenario: Unit tests remain deterministic
    Tool: Bash
    Preconditions: same suite runnable repeatedly
    Steps:
      1. Run unit suite twice back-to-back
      2. Assert: both runs pass with identical test outcomes
    Expected Result: no flaky behavior in core unit tests
    Failure Indicators: intermittent failures
    Evidence: two-run output logs
  ```

  **Commit**: YES
  - Message: `test(security-review): add unit coverage for dedup state and validation`
  - Files: `tests/review/agents/*`
  - Pre-commit: unit pytest commands

---

- [x] 8. Build integration tests for real analysis flow with seeded diffs (TD-013)

  **What to do**:
  - Create integration fixtures representing clean and vulnerable diffs.
  - Validate full pipeline: context -> delegation prompt -> scanner -> validation -> final assessment.
  - Include performance-friendly fixture sizes and large-diff fixture seeds.

  **Must NOT do**:
  - Do not rely on manual inspection for integration pass/fail.
  - Do not include external network dependencies.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: end-to-end confidence and regression control.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with 5, 11, 12)
  - **Blocks**: 13, 14
  - **Blocked By**: 3, 4, 5, 6, 7

  **References**:
  - `tests/review/agents/test_security_reviewer.py` - test conventions and helpers.
  - `dawn_kestrel/agents/review/fsm_security.py:310` - orchestrated flow under test.
  - `dawn_kestrel/agents/review/context_builder.py:71` - context construction path.

  **Acceptance Criteria**:
  - [ ] Vulnerable seeded diff produces expected findings with matching evidence.
  - [ ] Clean seeded diff produces no high-confidence false positives.
  - [ ] Integration suite is deterministic and CI-suitable.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Vulnerable fixture yields expected findings
    Tool: Bash
    Preconditions: vulnerable integration fixture added
    Steps:
      1. Run: python -m pytest -q tests/review -k integration_vulnerable_diff
      2. Assert: exit code 0
      3. Assert: expected finding IDs and evidence snippets present
    Expected Result: vulnerabilities detected accurately
    Failure Indicators: missed seeded vulnerabilities or mismatched evidence
    Evidence: pytest output

  Scenario: Clean fixture controls false positives
    Tool: Bash
    Preconditions: clean integration fixture added
    Steps:
      1. Run: python -m pytest -q tests/review -k integration_clean_diff
      2. Assert: exit code 0
      3. Assert: no high/critical findings returned
    Expected Result: low false-positive behavior
    Failure Indicators: high/critical findings on clean fixture
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `test(security-review): add integration fixtures for real diff analysis`
  - Files: integration tests/fixtures
  - Pre-commit: integration pytest commands

---

- [x] 9. Add structured logging and auditability improvements (TD-014)

  **What to do**:
  - Add explicit log events for dedup skips, task skip reasons, and validation rejects.
  - Standardize message format for iteration and finding lifecycle events.
  - Ensure logs do not leak sensitive values in plaintext.

  **Must NOT do**:
  - Do not log raw secrets or full sensitive payloads.
  - Do not produce ambiguous skip messages without IDs/reasons.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: observability with security/privacy constraints.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 2)
  - **Blocks**: 14
  - **Blocked By**: 1, 2

  **References**:
  - `dawn_kestrel/agents/review/fsm_security.py:394` - lifecycle logging anchor points.
  - `dawn_kestrel/agents/review/agents/security.py:136` - existing logging patterns.
  - OWASP LLM02 logging hygiene guidance.

  **Acceptance Criteria**:
  - [ ] Logs include structured skip/reject reasons with finding/task IDs.
  - [ ] Secret-like patterns are redacted in logs.
  - [ ] Logging tests validate required fields and redaction behavior.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Skip/reject logs include required metadata
    Tool: Bash
    Preconditions: log validation tests added
    Steps:
      1. Run: python -m pytest -q tests/review -k logging_metadata
      2. Assert: exit code 0
      3. Assert: logs contain task_id/finding_id/reason fields
    Expected Result: actionable audit logs
    Failure Indicators: missing IDs or skip reason text
    Evidence: pytest output

  Scenario: Sensitive values are redacted in logs
    Tool: Bash
    Preconditions: redaction fixture added
    Steps:
      1. Run: python -m pytest -q tests/review -k logging_redaction
      2. Assert: exit code 0
      3. Assert: raw secret tokens absent from emitted logs
    Expected Result: no sensitive leakage
    Failure Indicators: plain secret-like strings in output
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `chore(security-review): add structured and redacted lifecycle logging`
  - Files: reviewer modules + logging tests
  - Pre-commit: logging-focused pytest

---

- [x] 10. Update documentation and implementation notes (TD-015)

  **What to do**:
  - Document dedup strategy, real-analysis mode, validation gates, and diff-context rules.
  - Add a brief ADR note on chosen defaults (chunking, concurrency, confidence threshold).
  - Update reviewer docs with expected finding schema examples.

  **Must NOT do**:
  - Do not leave docs describing mock behavior after real analyzers ship.
  - Do not introduce contradictory docs across files.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: documentation-first deliverables.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: 14
  - **Blocked By**: 1

  **References**:
  - `docs/security-agent-improvement-plan.md` - source objectives.
  - `docs/reviewers/security_reviewer.md` - reviewer docs target.
  - `dawn_kestrel/agents/review/agents/security.py` - current reviewer behavior reference.

  **Acceptance Criteria**:
  - [ ] Docs explain real analysis vs historical mock behavior.
  - [ ] Docs include deterministic validation and dedup rules.
  - [ ] Docs include at least one changed-files-only finding example.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Docs include required sections
    Tool: Bash
    Preconditions: docs updated
    Steps:
      1. Run: grep for headings "Deduplication", "Diff Context", "Validation Gates"
      2. Assert: each heading exists in target docs
    Expected Result: complete operational documentation
    Failure Indicators: missing mandatory sections
    Evidence: grep output

  Scenario: No stale mock-mode instructions remain
    Tool: Bash
    Preconditions: docs migration completed
    Steps:
      1. Run: grep for stale phrases like "simulate_subagent_execution only"
      2. Assert: no stale-only instructions remain
    Expected Result: docs reflect current architecture
    Failure Indicators: stale behavioral docs still present
    Evidence: grep output
  ```

  **Commit**: YES
  - Message: `docs(security-review): document dedup diff-context and validation flow`
  - Files: reviewer docs + ADR note
  - Pre-commit: docs consistency checks

---

- [x] 11. Optimize large-diff handling and parsing reuse (TD-016)

  **What to do**:
  - Implement chunking and parsing reuse to avoid repeated diff parsing per scanner.
  - Add configurable limits and graceful truncation notes in output.
  - Measure baseline vs optimized runtime in test harness.

  **Must NOT do**:
  - Do not compromise evidence fidelity for speed.
  - Do not cache across unrelated PR contexts without isolation.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: performance optimization with correctness guardrails.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with 5, 8, 12)
  - **Blocks**: 14
  - **Blocked By**: 4

  **References**:
  - `dawn_kestrel/agents/review/context_builder.py:125` - single diff retrieval path.
  - `dawn_kestrel/agents/review/fsm_security.py:684` - prompt and diff usage path.

  **Acceptance Criteria**:
  - [ ] Large-diff fixture completes within defined budget.
  - [ ] Parser reuse/caching path tested for consistency.
  - [ ] Findings parity maintained between optimized and non-optimized mode.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Large-diff performance meets budget
    Tool: Bash
    Preconditions: performance fixture and benchmark test added
    Steps:
      1. Run: python -m pytest -q tests/review -k large_diff_performance
      2. Assert: exit code 0
      3. Assert: measured runtime <= configured threshold
    Expected Result: acceptable runtime for large diffs
    Failure Indicators: timeout or runtime above threshold
    Evidence: benchmark test output

  Scenario: Optimization does not change findings semantics
    Tool: Bash
    Preconditions: parity test added
    Steps:
      1. Run: python -m pytest -q tests/review -k optimization_parity
      2. Assert: exit code 0
      3. Assert: optimized and baseline findings match on ID/file/line/severity
    Expected Result: performance win without correctness regression
    Failure Indicators: mismatched findings across modes
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `perf(security-review): optimize large-diff parsing and reuse`
  - Files: diff handling modules + performance tests
  - Pre-commit: perf/parity pytest commands

---

- [x] 12. Add bounded parallel subagent execution and safe aggregation (TD-017)

  **What to do**:
  - Execute independent scanner tasks concurrently with configured cap.
  - Add safe aggregation that preserves deterministic merge order.
  - Ensure shared-state mutation is synchronized/idempotent.

  **Must NOT do**:
  - Do not introduce race conditions in findings/todos state.
  - Do not allow uncontrolled fan-out beyond cap.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: concurrency + determinism correctness.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with 5, 8, 11)
  - **Blocks**: 13, 14
  - **Blocked By**: 4

  **References**:
  - `dawn_kestrel/agents/review/fsm_security.py:644` - current sequential delegation path.
  - `dawn_kestrel/agents/review/fsm_security.py:910` - aggregation merge point.

  **Acceptance Criteria**:
  - [ ] Concurrent execution respects configured max concurrency.
  - [ ] Aggregated findings order is deterministic across runs.
  - [ ] No race-condition regressions in state tracking tests.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Concurrency cap is enforced
    Tool: Bash
    Preconditions: concurrency fixture and instrumentation test added
    Steps:
      1. Run: python -m pytest -q tests/review -k concurrency_cap
      2. Assert: exit code 0
      3. Assert: max in-flight subagent tasks never exceeds configured cap
    Expected Result: bounded parallel execution
    Failure Indicators: observed in-flight count exceeds cap
    Evidence: pytest output

  Scenario: Parallel aggregation remains deterministic
    Tool: Bash
    Preconditions: deterministic merge test added
    Steps:
      1. Run: python -m pytest -q tests/review -k parallel_deterministic_merge
      2. Assert: exit code 0
      3. Assert: repeated runs produce same ordered finding IDs
    Expected Result: deterministic final output
    Failure Indicators: ordering flakiness across runs
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `feat(security-review): add bounded parallel scanner execution`
  - Files: delegation/aggregation paths + tests
  - Pre-commit: concurrency pytest commands

---

- [x] 13. Add finding confidence scoring and threshold filtering (TD-018)

  **What to do**:
  - Introduce confidence scoring field normalization.
  - Add configurable threshold policy for final report inclusion/severity adjustment.
  - Ensure confidence metadata appears in final findings and logs.

  **Must NOT do**:
  - Do not drop high-severity findings solely due to malformed confidence field; use safe fallback.
  - Do not make threshold behavior implicit or hidden.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: policy-level output behavior that affects risk posture.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 6
  - **Blocks**: 14
  - **Blocked By**: 8, 12

  **References**:
  - `dawn_kestrel/agents/review/fsm_security.py:995` - final assessment assembly.
  - `dawn_kestrel/agents/review/contracts.py` - finding schema compatibility.

  **Acceptance Criteria**:
  - [ ] Confidence included in final finding metadata.
  - [ ] Threshold behavior configurable and test-covered.
  - [ ] Invalid confidence values handled with deterministic fallback.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Threshold filters low-confidence findings
    Tool: Bash
    Preconditions: threshold tests and fixtures added
    Steps:
      1. Run: python -m pytest -q tests/review -k confidence_threshold
      2. Assert: exit code 0
      3. Assert: low-confidence findings are filtered or demoted per policy
    Expected Result: predictable threshold behavior
    Failure Indicators: inconsistent inclusion across runs
    Evidence: pytest output

  Scenario: Malformed confidence input uses safe default
    Tool: Bash
    Preconditions: malformed confidence fixture added
    Steps:
      1. Run: python -m pytest -q tests/review -k malformed_confidence
      2. Assert: exit code 0
      3. Assert: fallback confidence applied and logged
    Expected Result: robust parsing under malformed input
    Failure Indicators: crash or undefined confidence behavior
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `feat(security-review): add confidence scoring and threshold policy`
  - Files: contracts/final assessment/tests
  - Pre-commit: confidence policy tests

---

- [x] 14. Final regression, metrics validation, and rollout gate

  **What to do**:
  - Run targeted and full test suites.
  - Validate success metrics from source plan (accuracy, dedup, evidence, performance, false-positive rate).
  - Produce rollout notes with phased enablement and fallback.

  **Must NOT do**:
  - Do not ship with failing deterministic, dedup, or validation tests.
  - Do not skip metric collection for large-diff and clean-diff fixtures.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: final quality gate across all changed subsystems.
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 6
  - **Blocks**: None
  - **Blocked By**: 5, 6, 8, 9, 10, 11, 12, 13

  **References**:
  - `docs/security-agent-improvement-plan.md:386` - success metric definitions.
  - `tests/review/agents/test_security_reviewer.py` - baseline reviewer tests.
  - `dawn_kestrel/agents/review/fsm_security.py` - final behavior under gate.

  **Acceptance Criteria**:
  - [ ] Targeted suites for security-review behavior pass.
  - [ ] Full `pytest` pass.
  - [ ] Measured metrics satisfy source thresholds or documented exceptions with explicit rationale.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Targeted regression pack is green
    Tool: Bash
    Preconditions: all implementation tasks completed
    Steps:
      1. Run: python -m pytest -q tests/review/agents/test_security_reviewer.py
      2. Run: python -m pytest -q tests/review -k "dedup or validation or integration or performance or concurrency"
      3. Assert: all commands exit 0
    Expected Result: impacted areas pass
    Failure Indicators: non-zero exit from any targeted suite
    Evidence: terminal output logs

  Scenario: Full suite catches hidden regressions
    Tool: Bash
    Preconditions: targeted pack green
    Steps:
      1. Run: python -m pytest -q
      2. Assert: exit code 0
    Expected Result: no hidden regressions outside reviewed modules
    Failure Indicators: failures in non-targeted modules
    Evidence: full pytest output
  ```

  **Commit**: YES
  - Message: `chore(security-review): finalize rollout gate and regression verification`
  - Files: tests/docs/rollout notes
  - Pre-commit: targeted pack + full `pytest -q`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1, 10 | `docs(plan): lock security-review contracts and docs baseline` | docs/ADR/plans | docs checks |
| 2, 3 | `fix(security-review): stabilize state and diff-context delegation` | FSM/context/tests | targeted pytest |
| 4, 6 | `feat(security-review): real diff scanners with strict validation gates` | scanners/validation/tests | targeted + integration pytest |
| 5, 9 | `fix(security-review): harden iteration control and audit logging` | FSM/logging/tests | targeted pytest |
| 11, 12, 13 | `feat(security-review): add performance concurrency and confidence controls` | perf/concurrency/contracts/tests | perf/concurrency pytest |
| 14 | `chore(security-review): complete regression and rollout gate` | tests/docs/rollout | full pytest |

---

## Success Criteria

### Verification Commands

```bash
python -m pytest -q tests/review/agents/test_security_reviewer.py
python -m pytest -q tests/review -k "dedup or state or prompt_diff_context or validation"
python -m pytest -q tests/review -k "integration_vulnerable_diff or integration_clean_diff"
python -m pytest -q tests/review -k "large_diff_performance or optimization_parity"
python -m pytest -q tests/review -k "concurrency_cap or parallel_deterministic_merge"
python -m pytest -q tests/review -k "confidence_threshold or malformed_confidence"
python -m pytest -q
```

### Final Checklist
- [x] Findings are unique across iterations and final report.
- [x] Findings map only to changed files and diff-backed evidence.
- [x] Todo/task lifecycle remains deterministic and bounded.
- [x] Logging is structured, redacted, and actionable.
- [x] Performance and concurrency targets are met without correctness regression.
- [x] Full test suite passes and rollout notes are ready.
