# Review Harness Refactor Plan

## TL;DR

> **Quick Summary**: Refactor the review harness to align with the README architecture by separating agent configuration from execution, centralizing LLM/tool orchestration, and introducing a loop FSM with budgets and result aggregation—while preserving existing behavior and enabling frequent merges from parent.
>
> **Deliverables**:
> - New harness infrastructure modules (runner, budgets, aggregator, FSM)
> - Centralized LLM client/adapters and tool invocation abstraction
> - Review agents converted to config/strategy-only with preserved output schema
> - Discovery/tooling refactor to use ToolRegistry instead of subprocess
> - Compatibility checks + parity tests for review outputs
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 2–3 waves
> **Critical Path**: LLM client → AgentRunner → Agent refactor → Aggregator/FSM → Parity tests

---

## Context

### Original Request
Analyze and refactor `opencode_python/src/opencode_python/agents/review/` and the harness in `opencode_python/src/opencode_python/core` to better align with the README harness architecture, reduce duplication, and relocate reusable logic. Apply design patterns where appropriate. Ensure frequent merges from parent branch to reduce toil.

### Interview Summary
**Key Discussions**:
- Current review agents embed execution and tooling; needs separation into config + shared harness execution.
- Must be able to merge parent often; no branch policy or CI constraints.
- Test strategy: **TDD**.

**Research Findings**:
- Core already has ToolRegistry, AgentRuntime, ContextBuilder, AgentContext/Result, EventBus, SessionManager.
- Review orchestrator duplicates aggregation and looping logic; BaseReviewerAgent is a god class.
- README vision includes FSM loop, budgets, result aggregation, skills catalog.

### Metis Review
**Identified Gaps** (addressed):
- Need to preserve external interfaces and behavior (output schema, error handling).
- Define invariants and parity checks for review output.
- Avoid unnecessary changes to core modules unless a gap is proven.
- Add acceptance criteria tied to executable commands.
- Address edge cases: budget exhaustion, missing tools, tool failures.

---

## Work Objectives

### Core Objective
Refactor the review harness to align with README architecture by centralizing execution logic, enforcing loop/budget controls, and preserving existing review agent outputs and interfaces.

### Concrete Deliverables
- `core/harness/runner.py` with Template Method execution flow
- `core/harness/budgets.py` and `core/harness/fsm.py`
- `core/harness/aggregation.py` for contract validation and dedupe
- `core/llm/` client with provider adapters and retry/timeout decorators
- Review agents converted to config/strategy-only (no direct AISession usage)
- Discovery module refactored to use ToolRegistry tools
- Parity test fixtures and tests validating unchanged outputs

### Definition of Done
- All existing review CLI entrypoints still function (`opencode-review`, `opencode-review-generate-docs`).
- Review outputs conform to `ReviewOutput` schema and match baseline snapshots for fixtures.
- New harness loop enforces budgets and stop conditions without altering output when not triggered.
- TDD tests added and passing (pytest).

### Must Have
- Maintain backward compatibility for review output schemas and CLI usage.
- Frequent merges from parent are part of the execution strategy.

### Must NOT Have (Guardrails)
- No changes to core ToolRegistry, AgentRuntime, EventBus, SessionManager unless necessary for documented gap.
- No new agent types or unrelated features.
- No changes to output JSON schemas unless explicitly approved.

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.

### Test Decision
- **Infrastructure exists**: YES (pytest in `pyproject.toml`)
- **Automated tests**: TDD
- **Framework**: pytest (+ pytest-asyncio)

### If TDD Enabled
Each TODO follows RED-GREEN-REFACTOR with pytest.

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)
All tasks include automated verification with pytest and CLI execution where applicable.

---

## Execution Strategy

### Sync Strategy (to reduce drift)
- Merge parent branch **before starting each wave** and **after completing each wave**.
- Prefer merge (not rebase) to preserve history and avoid rewrite.
- Resolve conflicts immediately; rerun the wave’s tests after each merge.

### Parallel Execution Waves

Wave 1 (Start Immediately):
- Task 1: Baseline tests + fixture snapshots
- Task 2: LLM client abstraction

Wave 2 (After Wave 1):
- Task 3: AgentRunner + context consolidation
- Task 4: Review agent refactor to config-only

Wave 3 (After Wave 2):
- Task 5: Aggregator + budgets/FSM
- Task 6: Discovery refactor to tools

Wave 4 (After Wave 3):
- Task 7: Parity verification + CLI checks

Critical Path: Task 2 → Task 3 → Task 4 → Task 5 → Task 7

---

## TODOs

> Implementation + Test = ONE Task. Never separate.

- [x] 1. Establish baseline review output fixtures and parity tests (TDD)

  **What to do**:
  - Create fixtures representing minimal review inputs (diff, changed_files, PR metadata)
  - Write pytest asserting `ReviewOutput` schema validation and baseline summary structure
  - Capture baseline outputs from current orchestrator for comparison

  **Must NOT do**:
  - Do not change existing review agent code yet

  **Recommended Agent Profile**:
  - **Category**: quick
    - Reason: Test scaffolding only
  - **Skills**: [git-master]
    - git-master: ensure atomic commits and test verification workflow
  - **Skills Evaluated but Omitted**:
    - frontend-ui-ux: not relevant

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1)
  - **Blocks**: Tasks 3–7 (baseline required)

  **References**:
  - `opencode_python/src/opencode_python/agents/review/contracts.py` - ReviewOutput schema
  - `opencode_python/src/opencode_python/agents/review/orchestrator.py` - current output assembly
  - `opencode_python/pyproject.toml` - pytest config and testpaths

  **Acceptance Criteria**:
  - [ ] `pytest tests/review/test_parity_baseline.py` → PASS
  - [ ] Baseline JSON fixture saved under `tests/fixtures/review_baseline/*.json`
  - [ ] Schema validation test ensures output matches `ReviewOutput`

  **Agent-Executed QA Scenarios**:
  - Scenario: Baseline output validation
    - Tool: Bash (pytest)
    - Steps:
      1. Run: `pytest tests/review/test_parity_baseline.py`
      2. Assert: exit code 0
    - Expected Result: tests pass, baseline fixture validated

---

- [x] 2. Introduce centralized LLM client abstraction (Adapter + Decorator)

  **What to do**:
  - Create `core/llm/client.py` with provider-agnostic interface
  - Add retry/timeout/logging decorators
  - Ensure compatibility with current AISession semantics

  **Must NOT do**:
  - Do not change review agent outputs yet

  **Recommended Agent Profile**:
  - **Category**: unspecified-high
  - **Skills**: [git-master]

  **Parallelization**: Wave 1

  **References**:
  - `opencode_python/src/opencode_python/ai_session.py` - current LLM handling
  - `opencode_python/src/opencode_python/agents/review/agents/security.py` - duplicated LLM flow

  **Acceptance Criteria**:
  - [ ] Unit tests for LLM client pass
  - [ ] No change to current review outputs (baseline parity holds)

  **QA Scenario**:
  - Run `pytest tests/llm/test_client.py`

---

- [x] 3. Implement AgentRunner (Template Method) and context consolidation

  **What to do**:
  - Create `core/harness/runner.py` using ContextBuilder + LLM client
  - Move prompt formatting out of BaseReviewerAgent
  - Ensure runner returns ReviewOutput-compatible results

  **Must NOT do**:
  - Do not remove BaseReviewerAgent yet

  **References**:
  - `opencode_python/src/opencode_python/agents/runtime.py`
  - `opencode_python/src/opencode_python/context/builder.py`
  - `opencode_python/src/opencode_python/agents/review/base.py`

  **Acceptance Criteria**:
  - [ ] New runner unit tests pass
  - [ ] Runner produces identical output for baseline fixture

---

- [x] 4. Refactor review agents to config-only + strategies

  **What to do**:
  - Remove AISession calls from agents
  - Convert to declarative config + relevance strategies
  - Ensure ReviewOutput schema preserved

  **References**:
  - `opencode_python/src/opencode_python/agents/review/agents/*.py`
  - `opencode_python/src/opencode_python/agents/review/contracts.py`

  **Acceptance Criteria**:
  - [ ] All review agents use AgentRunner
  - [ ] Baseline parity test still passes

---

- [x] 5. Add result aggregation + budgets/FSM loop

  **What to do**:
  - Implement `core/harness/aggregation.py` (dedupe + contract checks)
  - Implement `core/harness/budgets.py` and `core/harness/fsm.py`
  - Hook orchestrator into new loop without changing outputs

  **References**:
  - `opencode_python/src/opencode_python/agents/review/orchestrator.py`
  - README loop FSM section

  **Acceptance Criteria**:
  - [ ] Budget enforcement tests pass
  - [ ] Aggregator dedupe yields same output as previous orchestrator

---

- [x] 6. Refactor discovery to use ToolRegistry

  **What to do**:
  - Convert subprocess calls in `discovery.py` to ToolRegistry invocations
  - Ensure behavior matches existing discovery outputs

  **References**:
  - `opencode_python/src/opencode_python/agents/review/discovery.py`
  - `opencode_python/src/opencode_python/tools/framework.py`

  **Acceptance Criteria**:
  - [ ] Discovery tests pass with tool-based implementation
  - [ ] Fallback behavior unchanged

---

- [ ] 7. Parity verification + CLI compatibility checks

  **What to do**:
  - Add tests to compare new outputs vs baseline fixtures
  - Verify CLI entrypoints still work

  **Acceptance Criteria**:
  - [ ] `pytest tests/review/test_parity_baseline.py` → PASS
  - [ ] `opencode-review --help` exit code 0

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `test(review): add baseline parity fixtures` | tests/fixtures, tests/review | pytest |
| 2 | `feat(llm): add client abstraction` | core/llm | pytest |
| 3 | `feat(harness): add agent runner` | core/harness | pytest |
| 4 | `refactor(review): config-only agents` | agents/review/agents | pytest |
| 5 | `feat(harness): add budgets and aggregation` | core/harness | pytest |
| 6 | `refactor(review): tool-based discovery` | agents/review/discovery.py | pytest |
| 7 | `test(review): add parity + cli checks` | tests/review | pytest |

---

## Success Criteria

### Verification Commands
```bash
pytest
opencode-review --help
```

### Final Checklist
- [ ] All baseline parity tests pass
- [ ] Review outputs conform to schema
- [ ] CLI entrypoints unchanged
- [ ] FSM/budgets enforced when enabled
- [ ] Frequent parent merges incorporated during execution
