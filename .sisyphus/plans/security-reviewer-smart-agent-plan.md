# Make Security Reviewer Smarter + Add Todo Orchestration Skill

## TL;DR

> **Quick Summary**: Convert the security reviewer from a fixed checklist prompt to a principle-led, risk-driven expert that can propose targeted follow-up delegation, while moving enforcement (determinism/safety/auditability) into orchestrator guardrails.
>
> **Deliverables**:
> - Smarter security reviewer prompt + compatibility with existing doc generation/tests
> - Orchestrator support for validated, capped, deterministic delegation requests
> - New todo/progress/parallelization skill for agents
> - Durable todo persistence backing `todoread`/`todowrite`
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 5 waves
> **Critical Path**: Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 7

---

## Context

### Original Request
Plan how to improve `dawn_kestrel/agents/review/agents/security.py` so it explains the security objective and risk model more than a rigid procedure, and let the agent decide/coordinate next checks (including sub-agent help). Also create a new skill for todo creation, progress tracking, and parallel work decomposition.

### Interview Summary
**Key Discussions**:
- Desired direction is "thin harness, model-driven control" but still production-safe.
- Existing architecture already supports delegation and parallel execution; leverage it rather than introducing a brand-new framework.
- Test strategy selected: **tests-after**.

**Research Findings**:
- Security reviewer prompt is currently prescriptive in `dawn_kestrel/agents/review/agents/security.py`.
- Review orchestration already runs subagents in parallel in `dawn_kestrel/agents/review/orchestrator.py`.
- General delegation runtime exists in `dawn_kestrel/agents/orchestrator.py` and `dawn_kestrel/tools/additional.py`.
- Todo read/write tools exist, but persistence is stubbed in `dawn_kestrel/core/session.py`.
- Skill discovery expects `SKILL.md` under `.opencode/skill/**` or `.claude/skills/**` via `dawn_kestrel/skills/loader.py`.

### Metis Review
**Identified Gaps (addressed in this plan)**:
- Preserve doc-gen contract: keep headings `Blocking conditions:` and `High-signal file patterns:` unless doc-gen/tests are updated in lockstep.
- Treat model-proposed commands/delegations as untrusted; validate with allowlists, budgets, and deterministic ordering.
- Avoid fake todo capability: implement either explicit ephemeral mode or real persistence. This plan includes real persistence.
- Eliminate nondeterministic set ordering in tool-plan generation.

---

## Work Objectives

### Core Objective
Create a smarter security review flow where intelligence emerges from risk-based analysis and controlled delegation, while preserving deterministic and auditable behavior through harness-level policy.

### Concrete Deliverables
- Updated security reviewer prompt behavior in `dawn_kestrel/agents/review/agents/security.py`.
- Delegation-request parsing/validation and orchestration handling in review orchestration components.
- Deterministic, policy-guarded tool/delegation execution paths.
- New skill file for todo/progress/parallelization under `.opencode/skill/`.
- Functional todo persistence wired through `SessionManager` + storage.
- Tests and documentation updates validating behavior and compatibility.

### Definition of Done
- [ ] Security reviewer operates with principle-led risk reasoning and still emits valid `ReviewOutput` JSON.
- [ ] Delegation requests are validated, capped, and merged deterministically.
- [ ] `todowrite` then `todoread` round-trips persisted todos for a session.
- [ ] Targeted and full pytest runs pass.

### Must Have
- Preserve current reliability/safety posture while increasing model autonomy.
- Keep audit trail quality high (clear notes/evidence for proposed checks/delegations).
- Maintain compatibility with doc generation and existing security reviewer tests.

### Must NOT Have (Guardrails)
- No unchecked execution of model-suggested commands.
- No nondeterministic command ordering from set-based dedupe.
- No "todo skill" that pretends persistence while backend stays no-op.
- No broad permission escalation for all agents without explicit policy.

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> All verification must be agent-executable through commands/tools. No manual QA.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: Tests-after
- **Framework**: pytest

### Agent-Executed QA Scenarios (applies to every task)
- Every task includes at least one happy-path and one negative-path scenario.
- Evidence must be terminal output or generated artifacts under deterministic paths.

---

## Execution Strategy

### Parallel Execution Waves

```text
Wave 1 (Start Immediately):
├── Task 1: Reframe security prompt + preserve doc-gen contracts
└── Task 5: Add todo-orchestrator skill scaffold

Wave 2 (After Wave 1):
├── Task 2: Add delegation request contract/parsing
└── Task 6: Implement todo persistence backend

Wave 3 (After Wave 2):
└── Task 3: Add deterministic/safe orchestrator guardrails

Wave 4 (After Wave 3):
└── Task 4: Execute targeted second-wave delegation from validated requests

Wave 5 (After Wave 4):
└── Task 7: Integration tests, docs, rollout notes

Critical Path: 1 -> 2 -> 3 -> 4 -> 7
Parallel Speedup: ~30-35% faster than strict sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|----------------------|
| 1 | None | 2, 7 | 5 |
| 2 | 1 | 3, 4, 7 | 6 |
| 3 | 2 | 4, 7 | None |
| 4 | 2, 3 | 7 | None |
| 5 | None | 6, 7 | 1 |
| 6 | 5 | 7 | 2 |
| 7 | 1, 2, 3, 4, 6 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 5 | `delegate_task(category="unspecified-high", load_skills=["git-master"])` |
| 2 | 2, 6 | Same category, split into two independent executions |
| 3 | 3 | Single focused execution with deterministic test pass |
| 4 | 4 | Single focused execution with orchestration tests |
| 5 | 7 | Final integration pass + docs + full suite |

---

## TODOs

- [ ] 1. Reframe `security.py` prompt to principle-led risk analysis while preserving contracts

  **What to do**:
  - Rewrite `get_system_prompt()` in `dawn_kestrel/agents/review/agents/security.py` to emphasize goals, risk triage, evidence standards, and dynamic check selection.
  - Keep `Blocking conditions:` and `High-signal file patterns:` sections (or update doc-gen + tests in same task).
  - Preserve valid output via `get_review_output_schema()` and existing review runner flow.

  **Must NOT do**:
  - Do not remove schema output requirements.
  - Do not introduce direct command execution from prompt text.
  - Do not break doc-gen parsing assumptions silently.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: nuanced prompt + compatibility refactor with behavior-sensitive tests.
  - **Skills**: [`git-master`]
    - `git-master`: useful for disciplined, auditable iterative changes.
  - **Skills Evaluated but Omitted**:
    - `playwright`: no browser workflow.
    - `dev-browser`: no browser workflow.
    - `frontend-ui-ux`: not UI work.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 5)
  - **Blocks**: 2, 7
  - **Blocked By**: None

  **References**:
  - `dawn_kestrel/agents/review/agents/security.py` - primary prompt and behavior target.
  - `dawn_kestrel/agents/review/base.py` - shared review execution contract and runner usage.
  - `dawn_kestrel/agents/review/doc_gen.py` - prompt-heading parsing dependency.
  - `tests/review/test_doc_gen.py` - regression checks for doc generation behavior.
  - `tests/review/agents/test_security_reviewer.py` - direct security reviewer expectations.

  **Acceptance Criteria**:
  - [ ] `SecurityReviewer.get_system_prompt()` remains schema-compatible and principle-led.
  - [ ] Required headings remain compatible with doc-gen behavior (or tests/docs updated consistently).
  - [ ] `python -m pytest -q tests/review/agents/test_security_reviewer.py` passes.
  - [ ] `python -m pytest -q tests/review/test_doc_gen.py` passes.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Security prompt preserves required structural anchors
    Tool: Bash
    Preconditions: Local repo checkout available
    Steps:
      1. Run: python -m pytest -q tests/review/test_doc_gen.py
      2. Assert: exit code is 0
      3. Run: python -m pytest -q tests/review/agents/test_security_reviewer.py
      4. Assert: exit code is 0
    Expected Result: Prompt rewrite does not break schema/doc-gen contracts
    Failure Indicators: Any failure in doc_gen or security reviewer tests
    Evidence: Terminal output capture from both pytest runs

  Scenario: Prompt rewrite avoids over-prescriptive regression
    Tool: Bash
    Preconditions: Updated prompt is in place
    Steps:
      1. Run a focused assertion test (new/updated) validating prompt includes principle-led guidance and no hardcoded mandatory command sequence
      2. Assert: test exits 0
    Expected Result: Prompt emphasizes why/risk over rigid command choreography
    Failure Indicators: Test detects hardcoded sequential command mandates
    Evidence: Targeted test output
  ```

  **Commit**: YES (groups with 1)
  - Message: `refactor(review): make security prompt principle-led`
  - Files: `dawn_kestrel/agents/review/agents/security.py`, related tests/docs
  - Pre-commit: `python -m pytest -q tests/review/agents/test_security_reviewer.py tests/review/test_doc_gen.py`

---

- [ ] 2. Add validated delegation-request contract for reviewer outputs

  **What to do**:
  - Define a deterministic delegation request format (agent, reason, priority, constraints, expected outputs).
  - Parse delegation requests from reviewer output without breaking current `ReviewOutput` contract (e.g., structured note payload).
  - Add validation for malformed/unknown requests and surface safe skips.

  **Must NOT do**:
  - Do not allow arbitrary free-form delegation execution.
  - Do not require breaking schema migration unless explicitly planned and tested.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: contract design and compatibility handling.
  - **Skills**: [`git-master`]
    - `git-master`: helps keep contract changes atomic and test-backed.
  - **Skills Evaluated but Omitted**:
    - `playwright`: not relevant.
    - `dev-browser`: not relevant.
    - `frontend-ui-ux`: not relevant.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 6)
  - **Blocks**: 3, 4, 7
  - **Blocked By**: 1

  **References**:
  - `dawn_kestrel/agents/review/contracts.py` - output contract types and merge structures.
  - `dawn_kestrel/agents/review/orchestrator.py` - consumer of subagent outputs.
  - `dawn_kestrel/agents/review/agents/diff_scoper.py` - precedent for structured routing notes.
  - `tests/review/test_orchestrator.py` - orchestration behavior test surface.

  **Acceptance Criteria**:
  - [ ] Valid delegation request payloads parse into typed internal objects.
  - [ ] Invalid payloads are ignored safely with explicit skip reason.
  - [ ] Existing orchestrator tests pass after parser integration.
  - [ ] New parser tests cover valid, malformed, and unknown-agent cases.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Valid delegation request parsing
    Tool: Bash
    Preconditions: Parser and tests added
    Steps:
      1. Run: python -m pytest -q tests/review/test_orchestrator.py -k delegation
      2. Assert: exit code is 0 and valid request case passes
    Expected Result: Structured delegation notes are parsed correctly
    Failure Indicators: Parser rejects valid payloads or mutates fields unexpectedly
    Evidence: Targeted pytest output

  Scenario: Malformed delegation payload is safely skipped
    Tool: Bash
    Preconditions: Negative test exists for malformed payload
    Steps:
      1. Run: python -m pytest -q tests/review/test_orchestrator.py -k malformed
      2. Assert: exit code is 0 and skip path is asserted
    Expected Result: No crash; explicit skip reason retained
    Failure Indicators: Unhandled exception or unsafe fallback execution
    Evidence: Targeted pytest output
  ```

  **Commit**: YES (groups with 2)
  - Message: `feat(review): add validated delegation request contract`
  - Files: contracts/orchestrator/tests
  - Pre-commit: `python -m pytest -q tests/review/test_orchestrator.py`

---

- [ ] 3. Enforce deterministic and safe orchestrator execution policy

  **What to do**:
  - Replace nondeterministic command dedupe/order with stable deterministic ordering.
  - Enforce allowed tool/command prefixes before including or executing proposed checks.
  - Add budget caps (max delegated actions, max concurrency, timeout boundaries) and deterministic stop reasons.

  **Must NOT do**:
  - Do not silently reorder in non-reproducible ways.
  - Do not bypass allowlists due to malformed payload edge cases.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: safety-critical orchestration behavior.
  - **Skills**: [`git-master`]
    - `git-master`: supports careful, traceable policy refactor.
  - **Skills Evaluated but Omitted**:
    - `playwright`: not relevant.
    - `dev-browser`: not relevant.
    - `frontend-ui-ux`: not relevant.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: 4, 7
  - **Blocked By**: 2

  **References**:
  - `dawn_kestrel/agents/review/orchestrator.py` - tool plan generation and merge behavior.
  - `dawn_kestrel/agents/review/utils/executor.py` - command execution surface.
  - `dawn_kestrel/agents/builtin.py` - existing planning orchestration controls to mirror.
  - `tests/review/test_orchestrator.py` - deterministic behavior assertions.

  **Acceptance Criteria**:
  - [ ] Tool-plan command ordering is deterministic and test-covered.
  - [ ] Disallowed command prefixes are rejected or moved to safe skips.
  - [ ] Budget and timeout controls are enforced with explicit notes.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Deterministic tool-plan ordering
    Tool: Bash
    Preconditions: Determinism test exists
    Steps:
      1. Run: python -m pytest -q tests/review/test_orchestrator.py -k deterministic
      2. Assert: repeated runs produce identical sorted command lists
    Expected Result: Stable output across runs
    Failure Indicators: Flaky order-dependent failures
    Evidence: pytest output from deterministic test

  Scenario: Disallowed command proposal is blocked
    Tool: Bash
    Preconditions: Negative test exists for blocked command
    Steps:
      1. Run: python -m pytest -q tests/review/test_orchestrator.py -k disallowed
      2. Assert: command is rejected/skipped with explicit reason
    Expected Result: Unsafe command never reaches execution plan
    Failure Indicators: command appears in final proposed_commands
    Evidence: targeted pytest output
  ```

  **Commit**: YES (groups with 3)
  - Message: `fix(review): enforce deterministic safe orchestration policy`
  - Files: review orchestrator/executor/tests
  - Pre-commit: `python -m pytest -q tests/review/test_orchestrator.py`

---

- [ ] 4. Execute targeted second-wave subagent delegation from validated security requests

  **What to do**:
  - Add second-wave orchestration pass: run initial reviewers, then run only validated delegated follow-ups.
  - Keep hard caps on follow-up count and fan-out.
  - Merge second-wave findings deterministically and annotate provenance (which parent request generated which run).

  **Must NOT do**:
  - Do not create recursive/unbounded delegation loops.
  - Do not let unknown subagent names execute.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: cross-agent orchestration and merge semantics.
  - **Skills**: [`git-master`]
    - `git-master`: maintains focused commit/test sequencing for complex orchestration edits.
  - **Skills Evaluated but Omitted**:
    - `playwright`: not relevant.
    - `dev-browser`: not relevant.
    - `frontend-ui-ux`: not relevant.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4
  - **Blocks**: 7
  - **Blocked By**: 2, 3

  **References**:
  - `dawn_kestrel/agents/review/orchestrator.py` - subagent scheduling and result merge path.
  - `dawn_kestrel/agents/review/registry.py` - valid reviewer resolution.
  - `dawn_kestrel/agents/orchestrator.py` - delegation/task lifecycle patterns.
  - `tests/review/test_orchestrator.py` - extension point for second-wave tests.

  **Acceptance Criteria**:
  - [ ] Valid delegated follow-up reviewers run under configured cap.
  - [ ] Unknown/excess requests are skipped with explicit notes.
  - [ ] Final findings include deterministic provenance and no duplicate inflation.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Valid second-wave delegation executes and merges
    Tool: Bash
    Preconditions: New second-wave orchestration tests exist
    Steps:
      1. Run: python -m pytest -q tests/review/test_orchestrator.py -k second_wave
      2. Assert: delegated agent runs are recorded and merged
      3. Assert: final merge output includes provenance metadata
    Expected Result: Controlled second-wave enrichment works
    Failure Indicators: no second-wave results or duplicate/unstable merging
    Evidence: targeted pytest output

  Scenario: Recursive or over-cap delegation is prevented
    Tool: Bash
    Preconditions: cap/loop protection tests exist
    Steps:
      1. Run: python -m pytest -q tests/review/test_orchestrator.py -k cap
      2. Assert: extra requests are skipped with explicit reason
    Expected Result: no runaway delegation
    Failure Indicators: more than cap follow-ups executed
    Evidence: targeted pytest output
  ```

  **Commit**: YES (groups with 4)
  - Message: `feat(review): add capped second-wave delegation`
  - Files: review orchestrator/registry/tests
  - Pre-commit: `python -m pytest -q tests/review/test_orchestrator.py`

---

- [ ] 5. Add `todo-orchestrator` skill for todo creation/progress/parallelization guidance

  **What to do**:
  - Add `.opencode/skill/todo-orchestrator/SKILL.md` with explicit procedure:
    - generate todo list from objective
    - track status transitions (`pending`, `in_progress`, `completed`, `cancelled`)
    - identify independent tasks for parallel execution
    - enforce stop conditions (no new evidence/stagnation)
  - Ensure skill loader discovery and injector formatting behavior remain deterministic.

  **Must NOT do**:
  - Do not couple skill behavior to nonfunctional persistence assumptions.
  - Do not rely on ambiguous status values.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: primary output is high-quality procedural `SKILL.md` content.
  - **Skills**: [`git-master`]
    - `git-master`: helps keep new skill artifact isolated and auditable.
  - **Skills Evaluated but Omitted**:
    - `playwright`: not relevant.
    - `dev-browser`: not relevant.
    - `frontend-ui-ux`: not relevant.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: 6, 7
  - **Blocked By**: None

  **References**:
  - `dawn_kestrel/skills/loader.py` - expected skill discovery paths.
  - `dawn_kestrel/skills/injector.py` - injection format and truncation behavior.
  - `tests/test_skill_injector.py` - deterministic injection tests.
  - `dawn_kestrel/agents/builtin.py` - agent permission context for skill usability.

  **Acceptance Criteria**:
  - [ ] Skill file exists at `.opencode/skill/todo-orchestrator/SKILL.md`.
  - [ ] Loader discovers the skill by name.
  - [ ] Injector includes skill content in deterministic order.
  - [ ] Skill text defines parallelization and progress update rules.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Skill discovery and injection
    Tool: Bash
    Preconditions: Skill file added in supported path
    Steps:
      1. Run: python -m pytest -q tests/test_skill_injector.py
      2. Assert: exit code is 0
      3. Run targeted new test validating loader discovers "todo-orchestrator"
      4. Assert: discovered skill name equals "todo-orchestrator"
    Expected Result: Skill is loadable and injectable
    Failure Indicators: skill not found or injected output not deterministic
    Evidence: pytest output

  Scenario: Invalid skill path does not break prompt building
    Tool: Bash
    Preconditions: Negative test added for missing skill lookup
    Steps:
      1. Run: python -m pytest -q tests/test_skill_injector.py -k invalid_skill
      2. Assert: base prompt still returned with no crash
    Expected Result: graceful handling of absent skill files
    Failure Indicators: exceptions during prompt construction
    Evidence: targeted pytest output
  ```

  **Commit**: YES (groups with 5)
  - Message: `feat(skill): add todo-orchestrator guidance skill`
  - Files: `.opencode/skill/todo-orchestrator/SKILL.md`, related tests
  - Pre-commit: `python -m pytest -q tests/test_skill_injector.py`

---

- [ ] 6. Implement durable todo persistence backing `todowrite`/`todoread`

  **What to do**:
  - Implement `SessionManager.get_todos()` and `SessionManager.update_todos()` in `dawn_kestrel/core/session.py`.
  - Add storage persistence path for todos in `dawn_kestrel/storage/store.py` (session-scoped JSON records).
  - Ensure `dawn_kestrel/tools/additional.py` todo tools preserve IDs/states and round-trip correctly.

  **Must NOT do**:
  - Do not silently drop todo IDs or state transitions.
  - Do not allow invalid status values through persistence layer.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: storage + session + tool wiring changes with contract implications.
  - **Skills**: [`git-master`]
    - `git-master`: supports careful staged edits across storage/session/tools.
  - **Skills Evaluated but Omitted**:
    - `playwright`: not relevant.
    - `dev-browser`: not relevant.
    - `frontend-ui-ux`: not relevant.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 2)
  - **Blocks**: 7
  - **Blocked By**: 5

  **References**:
  - `dawn_kestrel/core/session.py` - stubbed todo methods to implement.
  - `dawn_kestrel/storage/store.py` - persistence primitives and key layout.
  - `dawn_kestrel/tools/additional.py` - `TodoTool` and `TodowriteTool` behavior.
  - `tests/conftest.py` - shared test fixture patterns for session/storage.

  **Acceptance Criteria**:
  - [ ] `todowrite` persists todos per session.
  - [ ] `todoread` returns persisted values for same session.
  - [ ] Invalid todo status handling is tested and deterministic.
  - [ ] `python -m pytest -q tests/test_todo_tools.py` passes.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Todo round-trip persistence
    Tool: Bash
    Preconditions: Persistence implementation completed
    Steps:
      1. Run targeted tests for session todo storage (new test file)
      2. Assert: write then read returns same todo IDs/descriptions/states
      3. Assert: data is isolated by session_id
    Expected Result: reliable session-scoped persistence
    Failure Indicators: empty reads after write, cross-session bleed
    Evidence: targeted pytest output

  Scenario: Invalid state rejected safely
    Tool: Bash
    Preconditions: Negative test for invalid todo state added
    Steps:
      1. Run targeted negative tests for invalid state input
      2. Assert: invalid state is rejected or normalized per contract
      3. Assert: no corrupted persisted records
    Expected Result: robust state validation
    Failure Indicators: invalid states persisted silently
    Evidence: targeted pytest output
  ```

  **Commit**: YES (groups with 6)
  - Message: `feat(todo): persist session todos and round-trip tools`
  - Files: session/storage/tools/tests
  - Pre-commit: targeted todo/session pytest command

---

- [ ] 7. Final integration: tests, docs, and rollout safeguards

  **What to do**:
  - Add/refresh docs describing new security reviewer behavior, delegation policy, and todo skill usage.
  - Add rollout notes (shadow-mode first, then active delegation).
  - Run full verification suite and capture outputs.

  **Must NOT do**:
  - Do not ship without deterministic orchestration tests.
  - Do not ship without explicit note on command/delegation policy.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: cross-cutting integration and release hardening.
  - **Skills**: [`git-master`]
    - `git-master`: keeps integration commits clean and reviewable.
  - **Skills Evaluated but Omitted**:
    - `playwright`: not relevant.
    - `dev-browser`: not relevant.
    - `frontend-ui-ux`: not relevant.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 5
  - **Blocks**: None
  - **Blocked By**: 1, 2, 3, 4, 6

  **References**:
  - `docs/planning-agent-orchestration.md` - policy and stop-condition conventions.
  - `dawn_kestrel/agents/builtin.py` - planning orchestration controls.
  - `tests/review/test_doc_gen.py` - doc contract regression.
  - `tests/review/test_orchestrator.py` - orchestration correctness.
  - `tests/test_skill_injector.py` - skill integration stability.

  **Acceptance Criteria**:
  - [ ] Targeted test suites for security/doc-gen/orchestrator/skills/todo pass.
  - [ ] Full test suite passes.
  - [ ] Documentation includes rollout mode and guardrails.

  **Agent-Executed QA Scenarios**:

  ```text
  Scenario: Targeted regression pack
    Tool: Bash
    Preconditions: All code changes complete
    Steps:
      1. Run: python -m pytest -q tests/review/agents/test_security_reviewer.py
      2. Run: python -m pytest -q tests/review/test_doc_gen.py
      3. Run: python -m pytest -q tests/review/test_orchestrator.py
      4. Run: python -m pytest -q tests/test_skill_injector.py
      5. Run: python -m pytest -q tests/test_todo_tools.py
      6. Assert: all commands exit 0
    Expected Result: all impacted domains pass targeted checks
    Failure Indicators: any single non-zero exit
    Evidence: terminal output log for each command

  Scenario: Full-suite safety net
    Tool: Bash
    Preconditions: Targeted pack green
    Steps:
      1. Run: python -m pytest -q
      2. Assert: exit code is 0
    Expected Result: no hidden regressions
    Failure Indicators: failures outside targeted packs
    Evidence: full pytest output
  ```

  **Commit**: YES (groups with 7)
  - Message: `chore(review): finalize smart-security rollout and docs`
  - Files: docs/tests/remaining integration files
  - Pre-commit: targeted regression pack + `python -m pytest -q`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `refactor(review): make security prompt principle-led` | security reviewer + related tests | targeted security/doc-gen pytest |
| 2-3 | `feat(review): add validated delegation with deterministic policy` | contracts/orchestrator/executor/tests | orchestrator pytest |
| 5-6 | `feat(todo): add orchestration skill and persistent todos` | skill/session/storage/tools/tests | skill + todo pytest |
| 7 | `chore(review): finalize rollout docs and regression coverage` | docs + integration tests | targeted pack + full pytest |

---

## Success Criteria

### Verification Commands

```bash
python -m pytest -q tests/review/agents/test_security_reviewer.py
python -m pytest -q tests/review/test_doc_gen.py
python -m pytest -q tests/review/test_orchestrator.py
python -m pytest -q tests/test_skill_injector.py
python -m pytest -q tests/test_todo_tools.py
python -m pytest -q
```

### Final Checklist
- [ ] Security reviewer is principle-led, not rigid-command-led.
- [ ] Doc-gen/security tests remain green.
- [ ] Delegation requests are validated, capped, and deterministic.
- [ ] Todo skill exists and is discoverable.
- [ ] Todo persistence is functional and tested.
- [ ] Full suite passes with no regressions.
