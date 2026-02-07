# Planning Agent Initial Conversation + Orchestration Upgrade

## TL;DR

> **Quick Summary**: Upgrade planning-agent behavior so the first 2-3 turns are clearer and faster while enforcing measurable orchestration controls: subagent-first execution, evidence per iteration, bounded budgets, stagnation detection, and strategy switching.
>
> **Deliverables**:
> - Rewritten planning-agent instruction specification (authoritative source)
> - Runtime prompt-pack integration points updated to consume/reflect the new policy
> - Automated prompt-contract and loop-control tests
> - Migration and rollout notes for maintainers
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 1 -> Task 3 -> Task 4 -> Task 6

---

## Context

### Original Request
Improve the planning agent for initial conversation quality by using a tool-driven orchestration model, informed by local mermaid diagrams in `opencode_python/src/opencode_python/agents/review/README.md` and external ideas from the referenced X thread, and deliver both instruction rewrite and executable work plan.

### Interview Summary
**Key Discussions**:
- User direction: subagent-first behavior, mandatory evidence each iteration, explicit tool playbooks, bounded budgets, stagnation triggers, and strategy switching.
- Output preference confirmed: deliver both rewritten instruction set and implementation work plan.

**Research Findings**:
- Existing strengths: structured output contracts and policy merge gates already exist in review subsystem.
- Existing gaps: no first-class iterative FSM loop for planning, no global budget/stagnation controller in current review orchestration path.
- UX improvements with low friction: triad lock-in, budget-first bounding box, novelty checkpoint, stagnation tripwire, decision gate.

### Metis Review
**Identified Gaps** (addressed in this plan):
- Missing explicit exceptions for subagent-first on trivial tasks.
- Missing objective definitions for stagnation and strategy switching.
- Missing anti-evidence-theater guardrail.
- Missing fully agent-executable acceptance criteria for prompt behavior.
- Missing explicit tie-break rules for conflicting subagent evidence.

---

## Work Objectives

### Core Objective
Introduce a practical, testable planning-agent policy that improves first-turn clarity without over-interviewing, while making orchestration safety measurable and enforceable.

### Concrete Deliverables
- Updated planning-agent instruction spec in repository docs.
- Prompt/runtime integration updates for planning flows.
- New test coverage for prompt contract and loop controls.
- Rollout notes documenting defaults, overrides, and safety behavior.

### Definition of Done
- [ ] New instruction spec includes explicit sections for objective, orchestration plan, gates, stop conditions, and single-question escalation.
- [ ] Prompt integration points reflect the spec and preserve existing agent runtime compatibility.
- [ ] Automated tests validate first-turn structure and stagnation strategy-switch behavior.
- [ ] `uv run pytest tests/test_context_builder.py tests/test_skill_injector.py tests/test_agent_runtime.py` passes.
- [ ] `uv run pytest tests/review/test_orchestrator.py tests/review/test_contracts.py` passes.
- [ ] `uv run ruff check src tests` passes.

### Must Have
- Subagent-first policy with explicit fast-path exceptions for trivial/simple tasks.
- Per-iteration evidence requirement with objective novelty checks.
- Explicit budget schema (iterations/tool calls/time) and deterministic stop behavior.
- Strategy-switch rule triggered by stagnation criteria.
- Final state must be either actionable recommendation or one precise blocking question.

### Must NOT Have (Guardrails)
- No vague directives like "explore more" without subagent/tool assignment.
- No acceptance criteria requiring manual human interaction.
- No unbounded loops or implicit retries.
- No hard-coding brittle static decomposition when dynamic dispatch is feasible.
- No prompt rewrite that breaks existing plan/build mode safety semantics.

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> All verification in this plan must be executable by the agent through tools/commands.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: YES (Tests-after)
- **Framework**: `pytest` (with `uv run`), `ruff`

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

Each task below includes both happy-path and negative/error QA scenarios with explicit commands and evidence artifacts.

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Start Immediately):
- Task 1: Baseline integration map and policy contract inventory

Wave 2 (After Wave 1):
- Task 2: Author canonical planning-agent instruction spec
- Task 3: Integrate spec into runtime prompt surfaces

Wave 3 (After Wave 2):
- Task 4: Add prompt-contract and loop-control automated tests
- Task 5: Write rollout/migration documentation

Wave 4 (After Wave 3):
- Task 6: Full verification run and evidence capture

Critical Path: 1 -> 3 -> 4 -> 6
Parallel Speedup: ~35-45% faster than strict sequential execution.

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3 | None |
| 2 | 1 | 4, 5 | 3 |
| 3 | 1 | 4, 5 | 2 |
| 4 | 2, 3 | 6 | 5 |
| 5 | 2, 3 | 6 | 4 |
| 6 | 4, 5 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1 | `delegate_task(category="unspecified-high", load_skills=["git-master"], run_in_background=false)` |
| 2 | 2, 3 | Dispatch in parallel after Task 1 |
| 3 | 4, 5 | Dispatch in parallel after Wave 2 |
| 4 | 6 | Single verification integrator task |

---

## TODOs

- [x] 1. Build Integration Surface Map and Lock Scope
   
   - [x] 2. Author Canonical Planning-Agent Instruction Spec (completed: .sisyphus/integration-map.md, 474 lines)

     **Commit**: YES (group A)
     - Message: `docs(planning): define canonical orchestration policy spec`
   
   - [x] 2. Author Canonical Planning-Agent Instruction Spec

  **What to do**:
  - Create a single authoritative instruction spec for planning-agent behavior.
  - Include required structure: Objective, Subagent Orchestration Plan, Gates/Evaluation, Stop Conditions, Next Best Question.
  - Encode first-2-3-turn UX policies: triad lock-in, budget-first, novelty checkpoint, stagnation tripwire, decision gate.

  **Must NOT do**:
  - Do not embed provider-specific brittle wording.
  - Do not duplicate contradictory rules across multiple docs.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: high-precision policy authoring and clarity.
  - **Skills**: `git-master`
    - `git-master`: helps maintain atomic change discipline and traceability.
  - **Skills Evaluated but Omitted**:
    - `dev-browser`: no browser workflow required.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 3)
  - **Blocks**: 4, 5
  - **Blocked By**: 1

  **References**:
  - `opencode_python/src/opencode_python/agents/review/README.md:61` - FSM loop anatomy and stop rationale.
  - `opencode_python/src/opencode_python/agents/review/README.md:97` - evidence-per-iteration requirement.
  - `opencode_python/src/opencode_python/agents/review/README.md:200` - layered budget gates concept.
  - `AGENTIC_REVIEW_PRD.md:708` - orchestrator prompt format patterns.
  - `.sisyphus/drafts/planning-agent-initial-conversation-orchestration.md:1` - consolidated local research decisions.

  **Acceptance Criteria**:
  - [ ] Spec includes explicit budget model, stagnation triggers, and strategy-switch policy.
  - [ ] Spec defines anti-evidence-theater rule and fast-path exceptions for trivial tasks.
  - [ ] Spec defines terminal outcomes: actionable recommendation OR one precise blocking question.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Required-section contract validation
    Tool: Bash
    Preconditions: Spec file created
    Steps:
      1. Run: uv run pytest tests/test_planning_prompt_contract.py::test_required_sections_present -q
      2. Assert: exit code 0
      3. Save report: .sisyphus/evidence/task-2-required-sections.txt
    Expected Result: All required headings and clauses present
    Evidence: .sisyphus/evidence/task-2-required-sections.txt

  Scenario: Forbidden-pattern negative validation
    Tool: Bash
    Preconditions: Spec text finalized
    Steps:
      1. Run: uv run pytest tests/test_planning_prompt_contract.py::test_forbidden_vague_directives_absent -q
      2. Assert: exit code 0
      3. Save report: .sisyphus/evidence/task-2-forbidden-patterns.txt
    Expected Result: No forbidden vague directives
    Evidence: .sisyphus/evidence/task-2-forbidden-patterns.txt
  ```

  **Commit**: YES (group B)
  - Message: `docs(planning): define canonical orchestration policy spec`

- [ ] 3. Integrate Spec into Runtime Prompt Surfaces

  **What to do**:
  - Update runtime-facing planning prompt surfaces to reflect the canonical spec.
  - Preserve existing plan/build mode semantics while adding measurable orchestration controls.
  - Add explicit mapping notes where full runtime alignment is deferred.

  **Must NOT do**:
  - Do not break existing tool permission safety for plan mode.
  - Do not silently diverge from canonical spec language.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: policy-to-runtime integration with backward compatibility constraints.
  - **Skills**: `git-master`
    - `git-master`: enforce minimal, auditable integration deltas.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: not applicable.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 2)
  - **Blocks**: 4, 5
  - **Blocked By**: 1

  **References**:
  - `opencode_python/src/opencode_python/tools/prompts/plan_enter.txt:1` - plan-mode behavior contract.
  - `opencode_python/src/opencode_python/tools/prompts/plan_exit.txt:1` - plan-exit behavior contract.
  - `opencode_python/src/opencode_python/context/builder.py:160` - agent base prompt fallback and injection behavior.
  - `opencode_python/src/opencode_python/skills/injector.py:60` - injected prompt ordering and formatting.
  - `opencode_python/src/opencode_python/agents/builtin.py:40` - plan agent constraints and permissions.

  **Acceptance Criteria**:
  - [ ] Plan mode still blocks edit/write behavior exactly as before.
  - [ ] Runtime planning prompts include budget/stagnation/switch directives.
  - [ ] Canonical spec and runtime prompts are linked with sync instructions.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Plan-mode safety regression check
    Tool: Bash
    Preconditions: Prompt integration changes applied
    Steps:
      1. Run: uv run pytest tests/test_agent_runtime.py::TestAgentRuntimeToolFiltering::test_tool_filtering_plan_agent -q
      2. Assert: exit code 0
      3. Save output: .sisyphus/evidence/task-3-plan-safety.txt
    Expected Result: plan agent still denies edit/write tools
    Evidence: .sisyphus/evidence/task-3-plan-safety.txt

  Scenario: Prompt-sync negative check
    Tool: Bash
    Preconditions: Canonical spec + runtime prompts updated
    Steps:
      1. Run: uv run pytest tests/test_planning_prompt_contract.py::test_runtime_surfaces_match_canonical_mandatory_clauses -q
      2. Assert: exit code 0
      3. Save output: .sisyphus/evidence/task-3-sync-negative.txt
    Expected Result: No canonical/runtime drift on mandatory clauses
    Evidence: .sisyphus/evidence/task-3-sync-negative.txt
  ```

  **Commit**: YES (group C)
  - Message: `feat(planning): align runtime prompts with orchestration policy`

- [ ] 4. Add Automated Prompt-Contract and Loop-Control Tests

  **What to do**:
  - Add tests that assert required planning output sections and stop behavior.
  - Add tests for stagnation-triggered strategy switch and single-question escalation.
  - Add negative tests for evidence-theater and over-interviewing behavior.

  **Must NOT do**:
  - Do not rely on manual interpretation of generated text.
  - Do not leave thresholds undocumented in test fixtures.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: behavior-contract test design across orchestration boundaries.
  - **Skills**: `git-master`
    - `git-master`: precise test-only change isolation and commit hygiene.
  - **Skills Evaluated but Omitted**:
    - `playwright`: no browser assertions required.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 5)
  - **Blocks**: 6
  - **Blocked By**: 2, 3

  **References**:
  - `opencode_python/tests/test_context_builder.py:394` - prompt structure assertion style.
  - `opencode_python/tests/test_skill_injector.py:50` - expected-sections contract testing style.
  - `opencode_python/tests/test_agent_runtime.py:589` - plan-mode behavioral regression test pattern.
  - `opencode_python/src/opencode_python/agents/review/contracts.py:183` - schema-enforced output contract concept.

  **Acceptance Criteria**:
  - [ ] New tests validate required output sections for planning responses.
  - [ ] New tests validate stagnation trigger causes strategy switch within configured threshold.
  - [ ] New tests validate escalation produces exactly one precise blocking question.
  - [ ] New tests validate anti-evidence-theater condition.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Prompt contract happy-path test run
    Tool: Bash
    Preconditions: New tests added under tests/
    Steps:
      1. Run: uv run pytest tests/test_context_builder.py tests/test_skill_injector.py -q
      2. Run: uv run pytest tests/test_agent_runtime.py -q
      3. Assert: both commands exit 0
      4. Save output: .sisyphus/evidence/task-4-contract-happy.txt
    Expected Result: Prompt and runtime contract tests pass
    Evidence: .sisyphus/evidence/task-4-contract-happy.txt

  Scenario: Stagnation control negative test
    Tool: Bash
    Preconditions: Loop-control tests implemented
    Steps:
      1. Run: uv run pytest tests/test_planning_prompt_contract.py::test_stagnation_trigger_forces_strategy_switch -q
      2. Run: uv run pytest tests/test_planning_prompt_contract.py::test_budget_exhaustion_emits_single_blocking_question -q
      3. Assert: both exit codes 0
      4. Save output: .sisyphus/evidence/task-4-stagnation-negative.txt
    Expected Result: Negative test demonstrates guardrail is enforced
    Evidence: .sisyphus/evidence/task-4-stagnation-negative.txt
  ```

  **Commit**: YES (group D)
  - Message: `test(planning): enforce prompt contract and loop controls`

- [ ] 5. Add Rollout and Migration Documentation

  **What to do**:
  - Document defaults, override points, and fallback policy.
  - Document budget knobs and stagnation thresholds with rationale.
  - Document compatibility notes and phased rollout guidance.

  **Must NOT do**:
  - Do not leave ambiguous policy precedence between old and new docs.
  - Do not omit rollback steps.

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: policy communication and change-management clarity.
  - **Skills**: `git-master`
    - `git-master`: keep docs changes atomic and traceable.
  - **Skills Evaluated but Omitted**:
    - `dev-browser`: no browser automation needed.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 4)
  - **Blocks**: 6
  - **Blocked By**: 2, 3

  **References**:
  - `DOCUMENTATION.md:900` - current PR review workflow diagram.
  - `AGENTIC_REVIEW_PRD.md:851` - existing execution workflow conventions.
  - `opencode_python/README.md:25` - user-facing entry point for review tooling docs.

  **Acceptance Criteria**:
  - [ ] Migration doc defines rollout steps and rollback path.
  - [ ] Docs explicitly state deterministic stop conditions and escalation behavior.
  - [ ] Docs include example "good" vs "bad" planning turn outputs.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Documentation completeness check
    Tool: Bash
    Preconditions: Migration docs updated
    Steps:
      1. Run: uv run pytest tests/test_planning_docs_migration.py::test_migration_doc_required_sections_present -q
      2. Assert: exit code 0
      3. Save output: .sisyphus/evidence/task-5-docs-completeness.txt
    Expected Result: Migration docs are complete and machine-checkable
    Evidence: .sisyphus/evidence/task-5-docs-completeness.txt

  Scenario: Contradiction negative check
    Tool: Bash
    Preconditions: Old/new docs coexist
    Steps:
      1. Run: uv run pytest tests/test_planning_docs_migration.py::test_policy_precedence_has_no_contradictions -q
      2. Assert: exit code 0
      3. Save output: .sisyphus/evidence/task-5-docs-negative.txt
    Expected Result: Policy precedence is unambiguous
    Evidence: .sisyphus/evidence/task-5-docs-negative.txt
  ```

  **Commit**: YES (group E)
  - Message: `docs(planning): add rollout and migration guide`

- [ ] 6. Execute Full Verification Suite and Publish Evidence Pack

  **What to do**:
  - Run all required lint/tests for changed areas.
  - Capture evidence artifacts and summarize pass/fail.
  - Confirm no unresolved placeholders remain in policy docs/tests.

  **Must NOT do**:
  - Do not skip failing checks.
  - Do not ship without evidence artifacts for happy + negative scenarios.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: deterministic execution of already-defined commands.
  - **Skills**: `git-master`
    - `git-master`: disciplined execution log and final change hygiene.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: irrelevant to verification commands.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: 4, 5

  **References**:
  - `opencode_python/pyproject.toml:83` - pytest config and testpaths.
  - `opencode_python/pyproject.toml:75` - linting tool configuration.

  **Acceptance Criteria**:
  - [ ] `uv run ruff check src tests` passes.
  - [ ] `uv run pytest tests/test_context_builder.py tests/test_skill_injector.py tests/test_agent_runtime.py` passes.
  - [ ] `uv run pytest tests/review/test_orchestrator.py tests/review/test_contracts.py` passes.
  - [ ] Evidence files saved under `.sisyphus/evidence/` for all scenario checks.

  **Agent-Executed QA Scenarios**:
  ```text
  Scenario: Full suite happy path
    Tool: Bash
    Preconditions: All implementation tasks completed
    Steps:
      1. Run: uv run ruff check src tests
      2. Run: uv run pytest tests/test_context_builder.py tests/test_skill_injector.py tests/test_agent_runtime.py
      3. Run: uv run pytest tests/review/test_orchestrator.py tests/review/test_contracts.py
      4. Assert: all exit codes 0
      5. Save logs: .sisyphus/evidence/task-6-full-suite.txt
    Expected Result: Lint and test suites pass
    Evidence: .sisyphus/evidence/task-6-full-suite.txt

  Scenario: Failing-check negative path handling
    Tool: Bash
    Preconditions: Negative-case tests implemented
    Steps:
      1. Run: uv run pytest tests/test_planning_prompt_contract.py::test_rejects_evidence_theater_outputs -q
      2. Run: uv run pytest tests/test_planning_prompt_contract.py::test_prevents_over_interviewing_after_budget_limit -q
      3. Assert: both exit codes 0
      4. Save output: .sisyphus/evidence/task-6-fail-negative.txt
    Expected Result: Verification process reliably blocks on failures
    Evidence: .sisyphus/evidence/task-6-fail-negative.txt
  ```

  **Commit**: NO

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `docs(planning): map prompt integration surfaces` | mapping/spec notes | targeted pytest baseline |
| 2 | `docs(planning): define canonical orchestration policy spec` | policy spec docs | section/forbidden-pattern checks |
| 3 | `feat(planning): align runtime prompts with orchestration policy` | prompt/config surfaces | plan-mode tool filtering test |
| 4 | `test(planning): enforce prompt contract and loop controls` | new/updated tests | pytest targeted suites |
| 5 | `docs(planning): add rollout and migration guide` | migration docs | docs completeness checks |

---

## Success Criteria

### Verification Commands
```bash
# run from opencode_python/
uv run ruff check src tests
uv run pytest tests/test_context_builder.py tests/test_skill_injector.py tests/test_agent_runtime.py
uv run pytest tests/review/test_orchestrator.py tests/review/test_contracts.py
```

### Final Checklist
- [ ] Canonical planning instruction spec created and approved.
- [ ] Runtime prompt surfaces aligned to canonical spec.
- [ ] First-2-3-turn behavior contract covered by automated tests.
- [ ] Budget/stagnation/strategy-switch controls testable and documented.
- [ ] Evidence pack captured in `.sisyphus/evidence/`.
- [ ] No human-dependent acceptance criterion remains.
