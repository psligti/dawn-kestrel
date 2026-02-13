# Security Review Agent - FSM Builder Migration

## TL;DR

> **Quick Summary**: Migrate SecurityReviewerAgent from manual FSM to FSMBuilder Pattern - replacing deprecated ReviewFSMImpl with fluent API, event publishing, reliability wrappers, and full observability.
> 
> **Deliverables**:
> - Refactored `SecurityReviewerAgent` using FSMBuilder fluent API
> - All 8 states and transitions declared via builder
> - Entry/exit hooks for state handlers
> - Guard conditions (max_iterations, confidence_threshold)
> - Event publishing via EventMediator
> - Observers (logging + metrics + alerts)
> - Reliability wrappers (CircuitBreaker, RetryExecutor, RateLimiter) on all hooks
> - Updated tests (TDD approach)
> - Removed deprecated ReviewFSMImpl
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Baseline tests → State handlers → Events/observers → Reliability → Integration tests

---

## Context

### Original Request
"I want to have a review agent for security updated with the usage of these new patterns."

### Interview Summary
**Key Discussions**:
- User wants complete migration to FSMBuilder Pattern (not a wrapper)
- Full event publishing for observability
- All hooks wrapped with reliability (CircuitBreaker, RetryExecutor, RateLimiter)
- Observers for logging, metrics, and alerts
- Subagent integration: blocking await within hooks
- Hook exceptions: selective retry (TimeoutError/NetworkError only)
- CircuitBreaker: auto-retry 3 times before FAIL
- FSM: one-shot per review session (no reset needed)
- No state persistence (in-memory only)
- Test strategy: TDD (RED-GREEN-REFACTOR)

**Research Findings**:
- FSM framework: `dawn_kestrel/core/fsm.py` - FSM Protocol, FSMImpl, FSMBuilder with 10 fluent methods
- FSM state repository: `dawn_kestrel/core/fsm_state_repository.py` - Repository pattern with SessionStorage
- Event mediator: `dawn_kestrel/core/mediator.py` - Event publishing interface
- Observer pattern: `dawn_kestrel/core/observer.py` - Observer protocol and notification system
- Workflow FSM: `dawn_kestrel/agents/workflow_fsm.py` - Phase-based FSM example to follow
- Current security review agent: `dawn_kestrel/agents/review/fsm_security.py` - Manual FSM with deprecated ReviewFSMImpl
- Subagents: `dawn_kestrel/agents/review/subagents/*` - Various security scanners (keep as-is)
- Tests: `tests/review/agents/test_fsm_security_*.py` - Existing tests for deduplication and confidence

### Metis Review
**Identified Gaps** (addressed):
- **Observer requirements**: Resolved - observers will log events, push metrics, and alert on failures
- **CircuitBreaker behavior**: Resolved - auto-retry with 3 attempts before transition to FAILED
- **Hook exception handling**: Resolved - selective retry (TimeoutError/NetworkError), others fail to FAILED
- **Subagent async integration**: Resolved - blocking await within hooks with timeout protection
- **FSM reusability**: Resolved - one-shot FSM per review session
- **Baseline verification**: Included as Task 0 - capture test results before migration
- **Event publishing verification**: Included in acceptance criteria
- **Observer registration verification**: Included in acceptance criteria
- **Reliability wrapper verification**: Included in acceptance criteria
- **Guard condition verification**: Included in acceptance criteria

---

## Work Objectives

### Core Objective
Refactor SecurityReviewerAgent to use FSMBuilder Pattern, replacing manual state machine with declarative FSM, event publishing, reliability wrappers, and full observability.

### Concrete Deliverables
- `dawn_kestrel/agents/review/fsm_security.py` - Migrated SecurityReviewerAgent using FSMBuilder
- `dawn_kestrel/agents/review/observers/` - New observer implementations:
  - `logging_observer.py` - Logs all FSM state changes to file
  - `metrics_observer.py` - Pushes FSM events to Prometheus/StatsD
  - `alerting_observer.py` - Alerts on FAILED transitions and threshold violations
- `tests/review/agents/test_fsm_security_builder.py` - TDD tests for FSM-based agent
- Updated `tests/review/agents/test_fsm_security_dedup.py` - Adapted to new FSM
- Updated `tests/review/agents/test_fsm_security_confidence.py` - Adapted to new FSM
- Removed deprecated ReviewFSMImpl class

### Definition of Done
- [ ] SecurityReviewerAgent uses FSMBuilder to declare states and transitions
- [ ] All 8 states declared via `with_state()`: IDLE, INITIAL_EXPLORATION, DELEGATING_INVESTIGATION, REVIEWING_RESULTS, CREATING_REVIEW_TASKS, FINAL_ASSESSMENT, COMPLETED, FAILED
- [ ] All transitions declared via `with_transition()`
- [ ] Entry hooks for each state calling existing handler methods
- [ ] Exit hooks for each state
- [ ] Guard conditions: max_iterations=3, confidence_threshold=0.8
- [ ] EventMediator configured and publishes all state transitions
- [ ] Three observers registered: logging, metrics, alerting
- [ ] ReliabilityConfig with CircuitBreaker (threshold=3), RetryExecutor (max_retries=2), RateLimiter (10 req/s)
- [ ] Subagent calls are blocking await within hooks
- [ ] Hook exceptions: TimeoutError/NetworkError retry (3 times), others fail to FAILED
- [ ] CircuitBreaker: auto-retry hook 3 times before transition to FAILED
- [ ] All existing tests pass (deduplication, confidence, FSM framework)
- [ ] New TDD tests for FSMBuilder usage pass
- [ ] Deprecated ReviewFSMImpl class removed
- [ ] In-memory state (no persistence to repository)
- [ ] One-shot FSM per review session

### Must Have
- FSMBuilder fluent API usage (with_state, with_transition, with_entry_hook, with_exit_hook, with_guard, with_mediator, with_observer, with_reliability, build)
- All 8 current states preserved
- All current transitions preserved
- EventMediator publishing every state transition
- Three observers: logging, metrics, alerting
- Reliability wrappers on all entry/exit hooks
- Guard conditions for max_iterations and confidence_threshold
- TDD tests (RED-GREEN-REFACTOR) for each state/transition
- Blocking await for subagent calls
- Selective retry for hook exceptions (TimeoutError/NetworkError only)

### Must NOT Have (Guardrails)
- Subagent modifications (keep subagents/* unchanged)
- FSM framework changes (no changes to dawn_kestrel/core/fsm.py)
- New states beyond current 8
- State persistence to repository (in-memory only)
- Non-blocking subagent calls
- All exceptions retrying (selective only)
- Changes to DI container for other agents
- Deprecated ReviewFSMImpl class remaining
- Breaking changes to existing tests (adapt but don't remove test logic)

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> This is NOT conditional — it applies to EVERY task, regardless of test strategy.
>
> **FORBIDDEN** — acceptance criteria that require:
> - "User manually tests..." / "사용자가 직접 테스트..."
> - "User visually confirms..." / "사용자가 눈으로 확인..."
> - "User interacts with..." / "사용자가 직접 조작..."
> - "Ask user to verify..." / "사용자에게 확인 요청..."
> - ANY step where a human must perform an action
>
> **ALL verification is executed by the agent** using tools (Playwright, interactive_bash, curl, etc.). No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest, tests/core/test_fsm.py, tests/review/agents/)
- **Automated tests**: YES (TDD)
- **Framework**: pytest

### If TDD Enabled

Each TODO follows RED-GREEN-REFACTOR:

**Task Structure**:
1. **RED**: Write failing test first
   - Test file: `tests/review/agents/test_fsm_security_builder.py`
   - Test command: `pytest tests/review/agents/test_fsm_security_builder.py -v -k "test_name"`
   - Expected: FAIL (test exists, implementation doesn't)
2. **GREEN**: Implement minimum code to pass
   - Command: `pytest tests/review/agents/test_fsm_security_builder.py -v -k "test_name"`
   - Expected: PASS
3. **REFACTOR**: Clean up while keeping green
   - Command: `pytest tests/review/agents/test_fsm_security_builder.py -v`
   - Expected: PASS (still)

**Test Setup Task** (infrastructure exists, verify):
- [ ] Task 0.1: Verify test infrastructure
  - Command: `pytest tests/core/test_fsm.py::test_fsm_builder_basic_states -v`
  - Verify: Test passes (FSM framework working)

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

> Whether TDD is enabled or not, EVERY task MUST include Agent-Executed QA Scenarios.
> - **With TDD**: QA scenarios complement unit tests at integration/E2E level
> - **Without TDD**: QA scenarios are the PRIMARY verification method
>
> These describe how the executing agent DIRECTLY verifies the deliverable
> by running it — opening browsers, executing commands, sending API requests.
> The agent performs what a human tester would do, but automated via tools.

**Verification Tool by Deliverable Type:**

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| **Python Code** | Bash (pytest, python) | Run tests, execute scripts, check return codes |
| **FSM/State** | Bash (python, grep) | Run FSM, verify transitions, check state |

**Each Scenario MUST Follow This Format:**

```
Scenario: [Descriptive name — what user action/flow is being verified]
  Tool: [Bash]
  Preconditions: [What must be true before this scenario runs]
  Steps:
    1. [Exact action with specific command/endpoint]
    2. [Next action with expected intermediate state]
    3. [Assertion with exact expected value]
  Expected Result: [Concrete, observable outcome]
  Failure Indicators: [What would indicate failure]
  Evidence: [Output capture / response body path]
```

**Scenario Detail Requirements:**
- **Commands**: Specific bash commands with exact paths
- **Data**: Concrete test data (file paths, state names, repository paths)
- **Assertions**: Exact values (state names, return codes, test counts)
- **Negative Scenarios**: At least ONE failure/error scenario per feature
- **Evidence Paths**: Specific file paths (`.sisyphus/evidence/task-N-scenario-name.log`)

---

## Execution Strategy

### Parallel Execution Waves

> Maximize throughput by grouping independent tasks into parallel waves.
> Each wave completes before the next begins.

```
Wave 1 (Start Immediately):
├── Task 0: Baseline verification + FSM framework test
└── Task 1: State declarations (8 states) + transitions

Wave 2 (After Wave 1):
├── Task 2: Entry hooks (INITIAL_EXPLORATION, DELEGATING_INVESTIGATION)
├── Task 3: Entry hooks (REVIEWING_RESULTS, FINAL_ASSESSMENT)
├── Task 4: Exit hooks (all states)
└── Task 5: Guard conditions (max_iterations, confidence_threshold)

Wave 3 (After Wave 2):
├── Task 6: EventMediator integration + event publishing
├── Task 7: Observers (logging, metrics, alerting)
├── Task 8: Reliability wrappers (CircuitBreaker, RetryExecutor, RateLimiter)
└── Task 9: Hook exception handling (selective retry)

Wave 4 (After Wave 3):
├── Task 10: Subagent integration (blocking await)
├── Task 11: Remove deprecated code
├── Task 12: Update existing tests (deduplication, confidence)
└── Task 13: Integration tests + cleanup

Critical Path: Task 0 → Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8 → Task 9 → Task 10 → Task 11 → Task 12 → Task 13
Parallel Speedup: ~50% faster than sequential (3 parallel waves)
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 0 | None | 1 | None (first) |
| 1 | 0 | 2, 3, 4, 5 | None (first wave) |
| 2 | 1 | 6, 7, 8, 9 | 3, 4, 5 |
| 3 | 1 | 6, 7, 8, 9 | 2, 4, 5 |
| 4 | 1 | 6, 7, 8, 9 | 2, 3, 5 |
| 5 | 1 | 6, 7, 8, 9 | 2, 3, 4 |
| 6 | 2, 3, 4, 5 | 10 | 7, 8, 9 |
| 7 | 2, 3, 4, 5 | 10 | 6, 8, 9 |
| 8 | 2, 3, 4, 5 | 10 | 6, 7, 9 |
| 9 | 2, 3, 4, 5 | 10 | 6, 7, 8 |
| 10 | 6, 7, 8, 9 | 11, 12 | None (final wave) |
| 11 | 10 | 12, 13 | None (final wave) |
| 12 | 10, 11 | 13 | None (final wave) |
| 13 | 10, 11, 12 | None | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 0, 1 | task(category="unspecified-high", load_skills=[], run_in_background=false) |
| 2 | 2, 3, 4, 5 | dispatch parallel after Wave 1 completes |
| 3 | 6, 7, 8, 9 | dispatch parallel after Wave 2 completes |
| 4 | 10, 11, 12, 13 | dispatch parallel after Wave 3 completes |

---

## TODOs

- [ ] 0. Baseline Verification + Test Infrastructure

  **What to do**:
  - [ ] Capture baseline test results BEFORE migration
  - [ ] Verify FSM framework is working correctly
  - [ ] Verify existing security review tests pass
  - [ ] Document baseline test counts

  **Must NOT do**:
  - Do NOT modify any code in this task (verification only)
  - Do NOT start migration before baseline is captured

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Simple verification and documentation task
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed for bash commands and test execution

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (must complete first)
  - **Blocks**: Task 1 (all migration depends on baseline)
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Test References** (to verify and run):
  - `tests/review/agents/test_fsm_security_dedup.py` - Existing deduplication tests
  - `tests/review/agents/test_fsm_security_confidence.py` - Existing confidence tests
  - `tests/core/test_fsm.py` - FSM framework tests to verify infrastructure

  **Current Implementation References** (to understand baseline):
  - `dawn_kestrel/agents/review/fsm_security.py:1-100` - Current SecurityReviewerAgent structure
  - `dawn_kestrel/agents/review/fsm_security.py:ReviewState` - Current state enum

  **FSM Framework References** (to understand API):
  - `dawn_kestrel/core/fsm.py:FSMBuilder` - FSMBuilder fluent API
  - `tests/core/test_fsm.py:test_fsm_builder_basic_states` - Example FSMBuilder usage

  **Documentation References** (patterns to follow):
  - `docs/patterns.md:Section 22` - FSM Builder Pattern documentation

  **WHY Each Reference Matters** (explain the relevance):
  - `tests/review/agents/test_fsm_security_dedup.py` - Baseline test to ensure behavior preserved after migration
  - `tests/review/agents/test_fsm_security_confidence.py` - Baseline test for confidence threshold logic
  - `tests/core/test_fsm.py` - Verify FSM framework infrastructure is working before migration
  - `dawn_kestrel/agents/review/fsm_security.py` - Current implementation to understand structure and behavior
  - `dawn_kestrel/core/fsm.py:FSMBuilder` - API to use for migration
  - `tests/core/test_fsm.py:test_fsm_builder_basic_states` - Example pattern for building FSM

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.
  > REPLACE all placeholders with actual values from task context.

  **If TDD (tests enabled):**
  - [ ] Test file created: tests/review/agents/test_fsm_security_builder.py
  - [ ] Test covers: baseline verification (capture existing test results)
  - [ ] pytest tests/review/agents/test_fsm_security_dedup.py -v → PASS (baseline)
  - [ ] pytest tests/review/agents/test_fsm_security_confidence.py -v → PASS (baseline)
  - [ ] pytest tests/core/test_fsm.py::test_fsm_builder_basic_states -v → PASS (framework OK)
  - [ ] Baseline results documented in .sisyphus/evidence/task-0-baseline.log

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  \`\`\`
  Scenario: Capture baseline test results before migration
    Tool: Bash
    Preconditions: Codebase in clean state (no migration started)
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. pytest tests/review/agents/test_fsm_security_dedup.py -v > .sisyphus/evidence/task-0-baseline-dedup.log
      3. Assert: Output contains "passed" and no "failed"
      4. pytest tests/review/agents/test_fsm_security_confidence.py -v > .sisyphus/evidence/task-0-baseline-confidence.log
      5. Assert: Output contains "passed" and no "failed"
      6. pytest tests/core/test_fsm.py::test_fsm_builder_basic_states -v > .sisyphus/evidence/task-0-baseline-fsm.log
      7. Assert: Output contains "passed" and no "failed"
    Expected Result: All baseline tests pass, results captured for comparison
    Failure Indicators: Any test fails in baseline, evidence file not created
    Evidence: .sisyphus/evidence/task-0-baseline-dedup.log, .sisyphus/evidence/task-0-baseline-confidence.log, .sisyphus/evidence/task-0-baseline-fsm.log

  Scenario: Verify FSM framework infrastructure is working
    Tool: Bash
    Preconditions: FSM framework code exists (dawn_kestrel/core/fsm.py)
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "from dawn_kestrel.core.fsm import FSMBuilder; print('FSMBuilder imported successfully')"
      3. Assert: Output contains "FSMBuilder imported successfully"
      4. pytest tests/core/test_fsm.py::test_fsm_builder_basic_states -v --tb=short
      5. Assert: Test passes with "passed" in output
    Expected Result: FSM framework is importable and tests pass
    Failure Indicators: ImportError, test fails
    Evidence: .sisyphus/evidence/task-0-fsm-framework-test.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] Baseline test results in .sisyphus/evidence/task-0-baseline-*.log
  - [ ] FSM framework test output in .sisyphus/evidence/task-0-fsm-framework-test.log

  **Commit**: NO (baseline verification only)
  - No commit for this task (verification only)

- [ ] 1. State Declarations + Transitions (FSMBuilder Setup)

  **What to do**:
  - [ ] Import FSMBuilder and FSM types from dawn_kestrel.core.fsm
  - [ ] Create FSMReliabilityConfig with CircuitBreaker (threshold=3), RetryExecutor (max_retries=2), RateLimiter (rate=10)
  - [ ] Use FSMBuilder to declare all 8 states: IDLE, INITIAL_EXPLORATION, DELEGATING_INVESTIGATION, REVIEWING_RESULTS, CREATING_REVIEW_TASKS, FINAL_ASSESSMENT, COMPLETED, FAILED
  - [ ] Declare all transitions matching VALID_TRANSITIONS from current implementation
  - [ ] Build FSM with initial_state="IDLE"
  - [ ] Write TDD tests for state declarations and transitions
  - [ ] Verify FSM can be created and get_state() returns "IDLE"

  **Must NOT do**:
  - Do NOT add entry/exit hooks yet (next tasks)
  - Do NOT add guards yet (next tasks)
  - Do NOT configure EventMediator yet (next tasks)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: High-complexity refactoring task requiring FSM framework understanding
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 1, must follow Task 0)
  - **Blocks**: Tasks 2, 3, 4, 5 (hooks and guards depend on FSM structure)
  - **Blocked By**: Task 0 (baseline verification)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **FSM Framework References** (API to use):
  - `dawn_kestrel/core/fsm.py:FSMBuilder` - FSMBuilder class and all fluent methods
  - `dawn_kestrel/core/fsm.py:FSMReliabilityConfig` - Reliability config dataclass
  - `dawn_kestrel/core/fsm.py:FSMContext` - Context dataclass for transitions

  **Current Implementation References** (states and transitions to replicate):
  - `dawn_kestrel/agents/review/fsm_security.py:ReviewState` - State enum with 8 states
  - `dawn_kestrel/agents/review/fsm_security.py:VALID_TRANSITIONS` - Transition mapping to replicate

  **Test References** (pattern to follow):
  - `tests/core/test_fsm.py:test_fsm_builder_basic_states` - Example state declaration pattern
  - `tests/core/test_fsm.py:test_fsm_builder_transitions` - Example transition pattern

  **Documentation References** (patterns to follow):
  - `docs/patterns.md:Section 22` - FSM Builder Pattern documentation

  **WHY Each Reference Matters** (explain the relevance):
  - `dawn_kestrel/core/fsm.py:FSMBuilder` - Contains the exact API to use (with_state, with_transition, with_reliability, build)
  - `dawn_kestrel/core/fsm.py:FSMReliabilityConfig` - Configuration for reliability wrappers
  - `dawn_kestrel/agents/review/fsm_security.py:ReviewState` - Source of truth for state names
  - `dawn_kestrel/agents/review/fsm_security.py:VALID_TRANSITIONS` - Source of truth for transitions
  - `tests/core/test_fsm.py:test_fsm_builder_basic_states` - Working example of FSMBuilder usage
  - `tests/core/test_fsm.py:test_fsm_builder_transitions` - Working example of transition declarations

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.
  > REPLACE all placeholders with actual values from task context.

  **If TDD (tests enabled):**
  - [ ] Test file created: tests/review/agents/test_fsm_security_builder.py
  - [ ] Test covers: 8 states declared, all transitions declared, FSM builds successfully
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_state_declarations -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_transitions -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_fsm_build -v → PASS
  - [ ] fsm.get_state() returns "IDLE" after build

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  \`\`\`
  Scenario: FSM declares all 8 states correctly
    Tool: Bash
    Preconditions: Code has FSMBuilder setup with state declarations
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
agent = SecurityReviewerAgent()
states = ['IDLE', 'INITIAL_EXPLORATION', 'DELEGATING_INVESTIGATION', 'REVIEWING_RESULTS', 'CREATING_REVIEW_TASKS', 'FINAL_ASSESSMENT', 'COMPLETED', 'FAILED']
print('State declaration test passed')
"
      3. Assert: Output contains "State declaration test passed"
    Expected Result: FSM declares all 8 states successfully
    Failure Indicators: Missing state, ImportError
    Evidence: .sisyphus/evidence/task-1-state-declarations.log

  Scenario: FSM declares all transitions correctly
    Tool: Bash
    Preconditions: FSM has state declarations
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
agent = SecurityReviewerAgent()
transitions = agent.fsm.is_transition_valid('IDLE', 'INITIAL_EXPLORATION')
print(f'IDLE -> INITIAL_EXPLORATION: {transitions}')
assert transitions == True
transitions = agent.fsm.is_transition_valid('INITIAL_EXPLORATION', 'FAILED')
print(f'INITIAL_EXPLORATION -> FAILED: {transitions}')
assert transitions == True
"
      3. Assert: Output shows both transitions as True
    Expected Result: All transitions declared correctly
    Failure Indicators: Missing transition, assertion failure
    Evidence: .sisyphus/evidence/task-1-transitions.log

  Scenario: FSM builds with initial state IDLE
    Tool: Bash
    Preconditions: FSM has state and transition declarations
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
agent = SecurityReviewerAgent()
state = agent.fsm.get_state()
print(f'Initial state: {state}')
assert state == 'IDLE'
"
      3. Assert: Output shows "Initial state: IDLE"
    Expected Result: FSM builds successfully with IDLE as initial state
    Failure Indicators: State is not IDLE, build fails
    Evidence: .sisyphus/evidence/task-1-fsm-build.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] State declarations test output in .sisyphus/evidence/task-1-state-declarations.log
  - [ ] Transitions test output in .sisyphus/evidence/task-1-transitions.log
  - [ ] FSM build test output in .sisyphus/evidence/task-1-fsm-build.log

  **Commit**: YES
  - Message: `refactor(security): add FSMBuilder state declarations and transitions`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`
  - Pre-commit: `pytest tests/review/agents/test_fsm_security_builder.py -v`

- [ ] 2. Entry Hooks - INITIAL_EXPLORATION + DELEGATING_INVESTIGATION

  **What to do**:
  - [ ] Add with_entry_hook() for INITIAL_EXPLORATION state
  - [ ] Hook calls existing _initial_exploration() method
  - [ ] Add with_entry_hook() for DELEGATING_INVESTIGATION state
  - [ ] Hook calls existing _delegate_investigation_tasks() method
  - [ ] Hooks receive FSMContext with repo_root, base_ref, head_ref
  - [ ] Write TDD tests for entry hooks
  - [ ] Verify hooks are called when entering states

  **Must NOT do**:
  - Do NOT modify the handler methods themselves (they should work as-is)
  - Do NOT add exit hooks yet (next task)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Requires understanding of FSM hooks and existing handler methods
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 4, 5)
  - **Blocks**: Tasks 6, 7, 8, 9 (events, observers, reliability need all hooks)
  - **Blocked By**: Task 1 (FSM structure must exist)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **FSM Framework References** (hook API):
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_entry_hook()` - Entry hook API
  - `dawn_kestrel/core/fsm.py:FSMContext` - Context structure for hooks

  **Current Implementation References** (handler methods to call):
  - `dawn_kestrel/agents/review/fsm_security.py:_initial_exploration()` - Method to call on INITIAL_EXPLORATION entry
  - `dawn_kestrel/agents/review/fsm_security.py:_delegate_investigation_tasks()` - Method to call on DELEGATING_INVESTIGATION entry

  **Test References** (pattern to follow):
  - `tests/core/test_fsm.py:test_fsm_entry_hooks` - Example entry hook test pattern

  **WHY Each Reference Matters** (explain the relevance):
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_entry_hook()` - API to register entry hook
  - `dawn_kestrel/core/fsm.py:FSMContext` - Structure to pass context to hooks
  - `dawn_kestrel/agents/review/fsm_security.py:_initial_exploration()` - Business logic to call
  - `dawn_kestrel/agents/review/fsm_security.py:_delegate_investigation_tasks()` - Business logic to call
  - `tests/core/test_fsm.py:test_fsm_entry_hooks` - Test pattern for verifying hook calls

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.
  > REPLACE all placeholders with actual values from task context.

  **If TDD (tests enabled):**
  - [ ] Test covers: INITIAL_EXPLORATION entry hook called, DELEGATING_INVESTIGATION entry hook called
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_initial_exploration_entry_hook -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_delegating_investigation_entry_hook -v → PASS
  - [ ] Hooks call existing handler methods

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  \`\`\`
  Scenario: Entry hook called when entering INITIAL_EXPLORATION
    Tool: Bash
    Preconditions: FSM has entry hook for INITIAL_EXPLORATION
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio
async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    await agent.fsm.transition_to('INITIAL_EXPLORATION', context)
    print('INITIAL_EXPLORATION entry hook called')
asyncio.run(test())
"
      3. Assert: Output contains "INITIAL_EXPLORATION entry hook called"
    Expected Result: Entry hook is called when transitioning to INITIAL_EXPLORATION
    Failure Indicators: Entry hook not called, transition fails
    Evidence: .sisyphus/evidence/task-2-initial-exploration-hook.log

  Scenario: Entry hook called when entering DELEGATING_INVESTIGATION
    Tool: Bash
    Preconditions: FSM has entry hook for DELEGATING_INVESTIGATION
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio
async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    await agent.fsm.transition_to('INITIAL_EXPLORATION', context)
    await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    print('DELEGATING_INVESTIGATION entry hook called')
asyncio.run(test())
"
      3. Assert: Output contains "DELEGATING_INVESTIGATION entry hook called"
    Expected Result: Entry hook is called when transitioning to DELEGATING_INVESTIGATION
    Failure Indicators: Entry hook not called, transition fails
    Evidence: .sisyphus/evidence/task-2-delegating-investigation-hook.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] INITIAL_EXPLORATION hook test output in .sisyphus/evidence/task-2-initial-exploration-hook.log
  - [ ] DELEGATING_INVESTIGATION hook test output in .sisyphus/evidence/task-2-delegating-investigation-hook.log

  **Commit**: YES
  - Message: `refactor(security): add entry hooks for INITIAL_EXPLORATION and DELEGATING_INVESTIGATION`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`
  - Pre-commit: `pytest tests/review/agents/test_fsm_security_builder.py::test_initial_exploration_entry_hook -v`

- [ ] 3. Entry Hooks - REVIEWING_RESULTS + FINAL_ASSESSMENT

  **What to do**:
  - [ ] Add with_entry_hook() for REVIEWING_RESULTS state
  - [ ] Hook calls existing _review_investigation_results() method
  - [ ] Add with_entry_hook() for FINAL_ASSESSMENT state
  - [ ] Hook calls existing _generate_final_assessment() method
  - [ ] Write TDD tests for these entry hooks
  - [ ] Verify hooks are called when entering states

  **Must NOT do**:
  - Do NOT modify the handler methods themselves
  - Do NOT add exit hooks yet (next task)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Similar to Task 2 - hook wiring with existing handlers
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 4, 5)
  - **Blocks**: Tasks 6, 7, 8, 9
  - **Blocked By**: Task 1

  **References** (CRITICAL - Be Exhaustive):

  **FSM Framework References** (hook API):
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_entry_hook()` - Entry hook API

  **Current Implementation References** (handler methods to call):
  - `dawn_kestrel/agents/review/fsm_security.py:_review_investigation_results()` - Method to call on REVIEWING_RESULTS entry
  - `dawn_kestrel/agents/review/fsm_security.py:_generate_final_assessment()` - Method to call on FINAL_ASSESSMENT entry

  **Test References** (pattern to follow):
  - `tests/core/test_fsm.py:test_fsm_entry_hooks` - Example entry hook test pattern

  **WHY Each Reference Matters**:
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_entry_hook()` - API to register entry hook
  - `dawn_kestrel/agents/review/fsm_security.py:_review_investigation_results()` - Business logic to call
  - `dawn_kestrel/agents/review/fsm_security.py:_generate_final_assessment()` - Business logic to call

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test covers: REVIEWING_RESULTS entry hook called, FINAL_ASSESSMENT entry hook called
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_reviewing_results_entry_hook -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_final_assessment_entry_hook -v → PASS

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: Entry hook called when entering REVIEWING_RESULTS
    Tool: Bash
    Preconditions: FSM has entry hook for REVIEWING_RESULTS
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio
async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    await agent.fsm.transition_to('INITIAL_EXPLORATION', context)
    await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    await agent.fsm.transition_to('REVIEWING_RESULTS', context)
    print('REVIEWING_RESULTS entry hook called')
asyncio.run(test())
"
      3. Assert: Output contains "REVIEWING_RESULTS entry hook called"
    Expected Result: Entry hook is called when transitioning to REVIEWING_RESULTS
    Evidence: .sisyphus/evidence/task-3-reviewing-results-hook.log

  Scenario: Entry hook called when entering FINAL_ASSESSMENT
    Tool: Bash
    Preconditions: FSM has entry hook for FINAL_ASSESSMENT
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio
async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    await agent.fsm.transition_to('INITIAL_EXPLORATION', context)
    await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    await agent.fsm.transition_to('REVIEWING_RESULTS', context)
    await agent.fsm.transition_to('FINAL_ASSESSMENT', context)
    print('FINAL_ASSESSMENT entry hook called')
asyncio.run(test())
"
      3. Assert: Output contains "FINAL_ASSESSMENT entry hook called"
    Expected Result: Entry hook is called when transitioning to FINAL_ASSESSMENT
    Evidence: .sisyphus/evidence/task-3-final-assessment-hook.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] REVIEWING_RESULTS hook test output in .sisyphus/evidence/task-3-reviewing-results-hook.log
  - [ ] FINAL_ASSESSMENT hook test output in .sisyphus/evidence/task-3-final-assessment-hook.log

  **Commit**: YES
  - Message: `refactor(security): add entry hooks for REVIEWING_RESULTS and FINAL_ASSESSMENT`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`

- [ ] 4. Exit Hooks (All States)

  **What to do**:
  - [ ] Add with_exit_hook() for all 8 states
  - [ ] Exit hooks for IDLE: log exit
  - [ ] Exit hooks for INITIAL_EXPLORATION: log exit, update iteration count
  - [ ] Exit hooks for DELEGATING_INVESTIGATION: log exit
  - [ ] Exit hooks for REVIEWING_RESULTS: log exit, record findings count
  - [ ] Exit hooks for CREATING_REVIEW_TASKS: log exit
  - [ ] Exit hooks for FINAL_ASSESSMENT: log exit
  - [ ] Exit hooks for COMPLETED: log exit
  - [ ] Exit hooks for FAILED: log exit, error details
  - [ ] Write TDD tests for exit hooks
  - [ ] Verify hooks are called when exiting states

  **Must NOT do**:
  - Do NOT modify handler methods
  - Do NOT add guards yet (next task)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Similar to Tasks 2 and 3 - hook wiring
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 3, 5)
  - **Blocks**: Tasks 6, 7, 8, 9
  - **Blocked By**: Task 1

  **References** (CRITICAL - Be Exhaustive):

  **FSM Framework References** (hook API):
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_exit_hook()` - Exit hook API

  **Test References** (pattern to follow):
  - `tests/core/test_fsm.py:test_fsm_exit_hooks` - Example exit hook test pattern

  **WHY Each Reference Matters**:
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_exit_hook()` - API to register exit hook
  - `tests/core/test_fsm.py:test_fsm_exit_hooks` - Test pattern for verifying exit hook calls

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test covers: all 8 exit hooks called in correct order
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_exit_hooks -v → PASS
  - [ ] Exit hooks log correctly

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: Exit hooks called when exiting states
    Tool: Bash
    Preconditions: FSM has exit hooks for all states
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio
async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    await agent.fsm.transition_to('INITIAL_EXPLORATION', context)
    await agent.fsm.transition_to('IDLE', context)
    print('Exit hooks called for IDLE and INITIAL_EXPLORATION')
asyncio.run(test())
"
      3. Assert: Output contains "Exit hooks called for IDLE and INITIAL_EXPLORATION"
    Expected Result: Exit hooks are called when exiting states
    Evidence: .sisyphus/evidence/task-4-exit-hooks.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] Exit hooks test output in .sisyphus/evidence/task-4-exit-hooks.log

  **Commit**: YES
  - Message: `refactor(security): add exit hooks for all states`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`

- [ ] 5. Guard Conditions (max_iterations, confidence_threshold)

  **What to do**:
  - [ ] Add with_guard() for INITIAL_EXPLORATION → DELEGATING_INVESTIGATION transition
  - [ ] Guard checks max_iterations <= 3
  - [ ] Add with_guard() for REVIEWING_RESULTS → FINAL_ASSESSMENT transition
  - [ ] Guard checks confidence_threshold >= 0.8
  - [ ] Write TDD tests for guards
  - [ ] Verify guards block invalid transitions
  - [ ] Verify guards allow valid transitions

  **Must NOT do**:
  - Do NOT modify handler logic (guards should only check conditions)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Guard conditions require business logic understanding
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 3, 4)
  - **Blocks**: Tasks 6, 7, 8, 9
  - **Blocked By**: Task 1

  **References** (CRITICAL - Be Exhaustive):

  **FSM Framework References** (guard API):
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_guard()` - Guard API
  - `dawn_kestrel/core/fsm.py:FSMContext` - Context for accessing iteration_count and confidence

  **Current Implementation References** (business rules to enforce):
  - `dawn_kestrel/agents/review/fsm_security.py:self.max_iterations` - Max iterations limit
  - `dawn_kestrel/agents/review/fsm_security.py:self.confidence_threshold` - Confidence threshold

  **Test References** (pattern to follow):
  - `tests/review/agents/test_fsm_security_confidence.py` - Confidence threshold tests

  **WHY Each Reference Matters**:
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_guard()` - API to register guard
  - `dawn_kestrel/core/fsm.py:FSMContext` - Structure for accessing business rule values
  - `dawn_kestrel/agents/review/fsm_security.py:self.max_iterations` - Business rule value
  - `dawn_kestrel/agents/review/fsm_security.py:self.confidence_threshold` - Business rule value
  - `tests/review/agents/test_fsm_security_confidence.py` - Existing confidence test logic to replicate

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test covers: max_iterations guard blocks > 3 iterations
  - [ ] Test covers: confidence_threshold guard blocks < 0.8 confidence
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_max_iterations_guard -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_confidence_threshold_guard -v → PASS
  - [ ] Guards block invalid transitions, allow valid transitions

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: Max iterations guard blocks transition
    Tool: Bash
    Preconditions: FSM has max_iterations guard
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio
async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    context.user_data['iteration_count'] = 4
    result = await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    assert result.is_err() == True
    print('Guard blocked transition (iteration_count > 3)')
asyncio.run(test())
"
      3. Assert: Output contains "Guard blocked transition"
    Expected Result: Guard blocks transition when iteration_count > 3
    Failure Indicators: Transition succeeds when it should be blocked
    Evidence: .sisyphus/evidence/task-5-max-iterations-guard.log

  Scenario: Confidence threshold guard blocks transition
    Tool: Bash
    Preconditions: FSM has confidence_threshold guard
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio
async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    context.user_data['confidence'] = 0.6
    result = await agent.fsm.transition_to('FINAL_ASSESSMENT', context)
    assert result.is_err() == True
    print('Guard blocked transition (confidence < 0.8)')
asyncio.run(test())
"
      3. Assert: Output contains "Guard blocked transition"
    Expected Result: Guard blocks transition when confidence < 0.8
    Failure Indicators: Transition succeeds when it should be blocked
    Evidence: .sisyphus/evidence/task-5-confidence-guard.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] Max iterations guard test output in .sisyphus/evidence/task-5-max-iterations-guard.log
  - [ ] Confidence threshold guard test output in .sisyphus/evidence/task-5-confidence-guard.log

  **Commit**: YES
  - Message: `refactor(security): add guard conditions for max_iterations and confidence_threshold`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`

- [ ] 6. EventMediator Integration + Event Publishing

  **What to do**:
  - [ ] Add with_mediator() to FSMBuilder
  - [ ] Configure EventMediator instance (from DI container or mock for tests)
  - [ ] Publish FSM state transition events via EventMediator
  - [ ] Event data includes: fsm_id, from_state, to_state, timestamp, agent_id, review_id
  - [ ] Write TDD tests for event publishing
  - [ ] Verify events are published for each transition
  - [ ] Verify event data structure

  **Must NOT do**:
  - Do NOT modify EventMediator interface or implementation
  - Do NOT create new event types (use existing DOMAIN events)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Event publishing requires EventMediator understanding
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 7, 8, 9)
  - **Blocks**: Task 10 (subagent integration needs events working)
  - **Blocked By**: Tasks 2, 3, 4, 5 (all hooks and guards must exist)

  **References** (CRITICAL - Be Exhaustive):

  **FSM Framework References** (mediator API):
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_mediator()` - Mediator API
  - `dawn_kestrel/core/mediator.py:EventMediator` - Mediator interface

  **DI Container References** (mediator provider):
  - `dawn_kestrel/core/di_container.py` - DI container with event_mediator provider

  **Test References** (pattern to follow):
  - `tests/core/test_fsm.py:test_fsm_mediator_integration` - Example mediator test pattern

  **WHY Each Reference Matters**:
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_mediator()` - API to register mediator
  - `dawn_kestrel/core/mediator.py:EventMediator` - Interface to understand publish() method
  - `dawn_kestrel/core/di_container.py` - Where to get EventMediator instance
  - `tests/core/test_fsm.py:test_fsm_mediator_integration` - Working example of mediator integration

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test covers: EventMediator.publish() called for each transition
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_event_publishing -v → PASS
  - [ ] Event data structure verified (fsm_id, from_state, to_state, timestamp)

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: Events published for state transitions
    Tool: Bash
    Preconditions: FSM has EventMediator configured
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
from dawn_kestrel.core.mediator import EventMediator
import asyncio

class MockMediator(EventMediator):
    def __init__(self):
        self.events = []
    async def publish(self, event):
        self.events.append(event)
        print(f'Event published: {event.event_type}, data: {event.data}')

async def test():
    agent = SecurityReviewerAgent()
    agent.mediator = MockMediator()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    await agent.fsm.transition_to('INITIAL_EXPLORATION', context)
    assert len(agent.mediator.events) == 1
    print('Event published for IDLE -> INITIAL_EXPLORATION')
asyncio.run(test())
"
      3. Assert: Output contains "Event published for IDLE -> INITIAL_EXPLORATION"
    Expected Result: Event is published via EventMediator for each transition
    Failure Indicators: Event not published, event data incomplete
    Evidence: .sisyphus/evidence/task-6-event-publishing.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] Event publishing test output in .sisyphus/evidence/task-6-event-publishing.log

  **Commit**: YES
  - Message: `refactor(security): add EventMediator integration and event publishing`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`

- [ ] 7. Observers (Logging, Metrics, Alerting)

  **What to do**:
  - [ ] Create `dawn_kestrel/agents/review/observers/logging_observer.py`
    - Observer that logs all FSM state transitions to file
    - Log format: `[timestamp] FSM {fsm_id}: {from_state} → {to_state}, agent_id={agent_id}`
  - [ ] Create `dawn_kestrel/agents/review/observers/metrics_observer.py`
    - Observer that pushes FSM events to Prometheus/StatsD
    - Metrics: security_fsm_transitions_total, security_fsm_state_duration_seconds
  - [ ] Create `dawn_kestrel/agents/review/observers/alerting_observer.py`
    - Observer that alerts on FAILED transitions
    - Alert when: transition to FAILED, max_iterations exceeded, confidence_threshold not met
  - [ ] Register all three observers via with_observer() in FSMBuilder
  - [ ] Write TDD tests for observers
  - [ ] Verify observers receive notifications
  - [ ] Verify logging observer writes to file
  - [ ] Verify metrics observer pushes metrics
  - [ ] Verify alerting observer triggers alerts

  **Must NOT do**:
  - Do NOT create additional observers beyond these three
  - Do NOT implement complex alerting (simple logging is sufficient)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Observer implementation requires understanding of Observer protocol
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 6, 8, 9)
  - **Blocks**: Task 10 (subagent integration needs observability)
  - **Blocked By**: Tasks 2, 3, 4, 5 (all FSM hooks must exist)

  **References** (CRITICAL - Be Exhaustive):

  **FSM Framework References** (observer API):
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_observer()` - Observer API
  - `dawn_kestrel/core/observer.py:Observer` - Observer protocol interface

  **Test References** (pattern to follow):
  - `tests/core/test_fsm.py:test_fsm_observers` - Example observer test pattern

  **WHY Each Reference Matters**:
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_observer()` - API to register observer
  - `dawn_kestrel/core/observer.py:Observer` - Interface to implement (on_notify method)
  - `tests/core/test_fsm.py:test_fsm_observers` - Test pattern for verifying observer notifications

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Observer files created: logging_observer.py, metrics_observer.py, alerting_observer.py
  - [ ] Test covers: logging observer logs transitions
  - [ ] Test covers: metrics observer pushes metrics
  - [ ] Test covers: alerting observer alerts on FAILED
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_logging_observer -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_metrics_observer -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_alerting_observer -v → PASS
  - [ ] Log file created at .sisyphus/evidence/security-fsm.log

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: Logging observer logs all state transitions
    Tool: Bash
    Preconditions: Logging observer registered
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
from dawn_kestrel.agents.review.observers.logging_observer import LoggingObserver
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    logging_observer = LoggingObserver()
    await agent.fsm.register_observer(logging_observer)
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    await agent.fsm.transition_to('INITIAL_EXPLORATION', context)
    print('Logging observer notified')
asyncio.run(test())
"
      3. cat .sisyphus/evidence/security-fsm.log
      4. Assert: Log contains "IDLE → INITIAL_EXPLORATION"
    Expected Result: Logging observer writes transitions to log file
    Failure Indicators: Log file not created or empty, missing transitions
    Evidence: .sisyphus/evidence/task-7-logging-observer.log, .sisyphus/evidence/security-fsm.log

  Scenario: Metrics observer pushes FSM metrics
    Tool: Bash
    Preconditions: Metrics observer registered (mock metrics client)
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
from dawn_kestrel.agents.review.observers.metrics_observer import MetricsObserver
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    metrics_observer = MetricsObserver(mock=True)
    await agent.fsm.register_observer(metrics_observer)
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    await agent.fsm.transition_to('INITIAL_EXPLORATION', context)
    print('Metrics observer notified')
asyncio.run(test())
"
      3. Assert: Output contains "Metrics observer notified"
    Expected Result: Metrics observer receives notifications
    Failure Indicators: Metrics observer not notified
    Evidence: .sisyphus/evidence/task-7-metrics-observer.log

  Scenario: Alerting observer alerts on FAILED transition
    Tool: Bash
    Preconditions: Alerting observer registered
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
from dawn_kestrel.agents.review.observers.alerting_observer import AlertingObserver
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    alerting_observer = AlertingObserver(mock=True)
    await agent.fsm.register_observer(alerting_observer)
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    await agent.fsm.transition_to('FAILED', context)
    print('Alerting observer notified of FAILURE')
asyncio.run(test())
"
      3. Assert: Output contains "Alerting observer notified of FAILURE"
    Expected Result: Alerting observer triggers alert on FAILED transition
    Failure Indicators: Alert not triggered
    Evidence: .sisyphus/evidence/task-7-alerting-observer.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] Logging observer test output in .sisyphus/evidence/task-7-logging-observer.log
  - [ ] Metrics observer test output in .sisyphus/evidence/task-7-metrics-observer.log
  - [ ] Alerting observer test output in .sisyphus/evidence/task-7-alerting-observer.log
  - [ ] FSM log file at .sisyphus/evidence/security-fsm.log

  **Commit**: YES
  - Message: `refactor(security): add observers (logging, metrics, alerting)`
  - Files: `dawn_kestrel/agents/review/observers/logging_observer.py`, `dawn_kestrel/agents/review/observers/metrics_observer.py`, `dawn_kestrel/agents/review/observers/alerting_observer.py`, `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`

- [ ] 8. Reliability Wrappers (CircuitBreaker, RetryExecutor, RateLimiter)

  **What to do**:
  - [ ] Configure FSMReliabilityConfig:
    - CircuitBreaker: threshold=3, timeout_seconds=60
    - RetryExecutor: max_retries=2, backoff_seconds=1
    - RateLimiter: rate_per_second=10
  - [ ] Add with_reliability() to FSMBuilder
  - [ ] All entry/exit hooks wrapped with reliability
  - [ ] Write TDD tests for reliability wrappers
  - [ ] Verify CircuitBreaker trips after 3 failures
  - [ ] Verify RetryExecutor retries on hook failures
  - [ ] Verify RateLimiter blocks excessive calls

  **Must NOT do**:
  - Do NOT modify reliability wrapper implementations
  - Do NOT add additional reliability features beyond these three

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Reliability wrappers require understanding of FSMReliabilityConfig
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 6, 7, 9)
  - **Blocks**: Task 10 (subagent integration needs reliability)
  - **Blocked By**: Tasks 2, 3, 4, 5 (all hooks must exist)

  **References** (CRITICAL - Be Exhaustive):

  **FSM Framework References** (reliability API):
  - `dawn_kestrel/core/fsm.py:FSMReliabilityConfig` - Reliability config dataclass
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_reliability()` - Reliability API
  - `dawn_kestrel/core/fsm.py:CircuitBreaker` - CircuitBreaker interface
  - `dawn_kestrel/core/fsm.py:RetryExecutor` - RetryExecutor interface
  - `dawn_kestrel/core/fsm.py:RateLimiter` - RateLimiter interface

  **Test References** (pattern to follow):
  - `tests/core/test_fsm.py:test_fsm_reliability_wrappers` - Example reliability test pattern

  **WHY Each Reference Matters**:
  - `dawn_kestrel/core/fsm.py:FSMReliabilityConfig` - Configuration structure to use
  - `dawn_kestrel/core/fsm.py:FSMBuilder.with_reliability()` - API to register reliability
  - `dawn_kestrel/core/fsm.py:CircuitBreaker` - CircuitBreaker interface to configure
  - `dawn_kestrel/core/fsm.py:RetryExecutor` - RetryExecutor interface to configure
  - `dawn_kestrel/core/fsm.py:RateLimiter` - RateLimiter interface to configure
  - `tests/core/test_fsm.py:test_fsm_reliability_wrappers` - Working example of reliability usage

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test covers: CircuitBreaker trips after 3 failures
  - [ ] Test covers: RetryExecutor retries 2 times on failure
  - [ ] Test covers: RateLimiter blocks > 10 calls per second
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_circuit_breaker -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_retry_executor -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_rate_limiter -v → PASS
  - [ ] FSMReliabilityConfig configured with correct values

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: CircuitBreaker trips after 3 hook failures
    Tool: Bash
    Preconditions: CircuitBreaker configured with threshold=3
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
from dawn_kestrel.core.result import Err
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    context.user_data['force_failure'] = True
    for i in range(3):
        result = await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
        assert result.is_err() == True
        print(f'Attempt {i+1}: CircuitBreaker not tripped yet')
    result = await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    assert result.code() == 'CIRCUIT_BREAKER_TRIPPED'
    print('CircuitBreaker tripped after 3 failures')
asyncio.run(test())
"
      3. Assert: Output contains "CircuitBreaker tripped after 3 failures"
    Expected Result: CircuitBreaker trips and blocks 4th attempt
    Failure Indicators: CircuitBreaker doesn't trip, more than 3 attempts allowed
    Evidence: .sisyphus/evidence/task-8-circuit-breaker.log

  Scenario: RetryExecutor retries hook 2 times on failure
    Tool: Bash
    Preconditions: RetryExecutor configured with max_retries=2
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    context.user_data['flaky_failure'] = True
    result = await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    print(f'Hook retried: {context.user_data.get(\"retry_count\", 0)} times')
    assert result.is_ok() == True
    print('RetryExecutor retried successfully')
asyncio.run(test())
"
      3. Assert: Output shows retry_count >= 2, transition succeeds
    Expected Result: RetryExecutor retries 2 times, hook succeeds on 3rd attempt
    Failure Indicators: Not enough retries, hook doesn't succeed
    Evidence: .sisyphus/evidence/task-8-retry-executor.log

  Scenario: RateLimiter blocks excessive hook calls
    Tool: Bash
    Preconditions: RateLimiter configured with rate=10 per second
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    for i in range(15):
        result = await agent.fsm.transition_to('INITIAL_EXPLORATION', context)
        if result.is_err() and result.code() == 'RATE_LIMIT_EXCEEDED':
            print(f'RateLimiter blocked on attempt {i+1}')
            break
    assert result.is_err() == True
asyncio.run(test())
"
      3. Assert: Output contains "RateLimiter blocked on attempt"
    Expected Result: RateLimiter blocks calls after 10 per second
    Failure Indicators: RateLimiter doesn't block, more than 10 calls allowed
    Evidence: .sisyphus/evidence/task-8-rate-limiter.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] CircuitBreaker test output in .sisyphus/evidence/task-8-circuit-breaker.log
  - [ ] RetryExecutor test output in .sisyphus/evidence/task-8-retry-executor.log
  - [ ] RateLimiter test output in .sisyphus/evidence/task-8-rate-limiter.log

  **Commit**: YES
  - Message: `refactor(security): add reliability wrappers (CircuitBreaker, RetryExecutor, RateLimiter)`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`

- [ ] 9. Hook Exception Handling (Selective Retry)

  **What to do**:
  - [ ] Update entry/exit hook error handling
  - [ ] TimeoutError and NetworkError: retry up to 3 times with exponential backoff
  - [ ] All other exceptions: transition to FAILED state immediately
  - [ ] Write TDD tests for exception handling
  - [ ] Verify TimeoutError/NetworkError are retried
  - [ ] Verify other exceptions fail to FAILED

  **Must NOT do**:
  - Do NOT retry all exceptions (selective only)
  - Do NOT modify FSM framework exception handling

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Exception handling requires understanding of hook error patterns
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 6, 7, 8)
  - **Blocks**: Task 10 (subagent integration needs error handling)
  - **Blocked By**: Tasks 2, 3, 4, 5 (all hooks must exist)

  **References** (CRITICAL - Be Exhaustive):

  **FSM Framework References** (error handling in hooks):
  - `dawn_kestrel/core/fsm.py:FSMImpl._execute_with_reliability()` - How hooks execute with reliability

  **Current Implementation References** (exception types to handle):
  - `dawn_kestrel/agents/review/fsm_security.py:TimeoutError` - Timeout exception to catch and retry
  - `dawn_kestrel/agents/review/fsm_security.py:NetworkError` - Network exception to catch and retry

  **WHY Each Reference Matters**:
  - `dawn_kestrel/core/fsm.py:FSMImpl._execute_with_reliability()` - Understanding of how hooks execute
  - `dawn_kestrel/agents/review/fsm_security.py:TimeoutError` - Exception type to retry
  - `dawn_kestrel/agents/review/fsm_security.py:NetworkError` - Exception type to retry

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test covers: TimeoutError retried 3 times
  - [ ] Test covers: NetworkError retried 3 times
  - [ ] Test covers: Other exceptions fail to FAILED
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_timeout_error_retry -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_network_error_retry -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_other_exception_fail -v → PASS

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: TimeoutError retried 3 times before FAIL
    Tool: Bash
    Preconditions: Hook throws TimeoutError
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    context.user_data['raise_timeout'] = True
    result = await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    assert context.user_data.get('retry_count', 0) == 3
    print(f'TimeoutError retried {context.user_data[\"retry_count\"]} times before FAIL')
asyncio.run(test())
"
      3. Assert: Output shows retry_count == 3, transition fails to FAILED
    Expected Result: TimeoutError retried 3 times, then fails to FAILED
    Failure Indicators: Not enough retries, doesn't fail to FAILED
    Evidence: .sisyphus/evidence/task-9-timeout-retry.log

  Scenario: NetworkError retried 3 times before FAIL
    Tool: Bash
    Preconditions: Hook throws NetworkError
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    context.user_data['raise_network_error'] = True
    result = await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    assert context.user_data.get('retry_count', 0) == 3
    print(f'NetworkError retried {context.user_data[\"retry_count\"]} times before FAIL')
asyncio.run(test())
"
      3. Assert: Output shows retry_count == 3, transition fails to FAILED
    Expected Result: NetworkError retried 3 times, then fails to FAILED
    Failure Indicators: Not enough retries, doesn't fail to FAILED
    Evidence: .sisyphus/evidence/task-9-network-error-retry.log

  Scenario: Other exceptions fail immediately to FAILED
    Tool: Bash
    Preconditions: Hook raises ValueError
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
from dawn_kestrel.core.result import Err
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    context.user_data['raise_value_error'] = True
    result = await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    assert result.is_err() == True
    assert agent.fsm.get_state() == 'FAILED'
    print('ValueError caused immediate transition to FAILED')
asyncio.run(test())
"
      3. Assert: Output contains "ValueError caused immediate transition to FAILED"
    Expected Result: Other exceptions cause immediate FAILED transition
    Failure Indicators: Exception retried, doesn't fail to FAILED
    Evidence: .sisyphus/evidence/task-9-other-exception-fail.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] TimeoutError retry test output in .sisyphus/evidence/task-9-timeout-retry.log
  - [ ] NetworkError retry test output in .sisyphus/evidence/task-9-network-error-retry.log
  - [ ] Other exception test output in .sisyphus/evidence/task-9-other-exception-fail.log

  **Commit**: YES
  - Message: `refactor(security): add selective retry for hook exceptions (TimeoutError/NetworkError)`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`

- [ ] 10. Subagent Integration (Blocking Await)

  **What to do**:
  - [ ] Update DELEGATING_INVESTIGATION entry hook
  - [ ] Subagent calls are blocking await (non-fire-and-forget)
  - [ ] Add timeout protection for subagent calls (30s timeout)
  - [ ] Subagent results collected and stored in context
  - [ ] Write TDD tests for subagent integration
  - [ ] Verify subagent calls are awaited
  - [ ] Verify timeout protection works
  - [ ] Verify subagent results are stored

  **Must NOT do**:
  - Do NOT modify subagent implementations (keep subagents/* unchanged)
  - Do NOT make subagent calls non-blocking

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Subagent integration requires understanding of async/await patterns
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 4, final tasks)
  - **Blocks**: Tasks 11, 12, 13
  - **Blocked By**: Tasks 6, 7, 8, 9 (events, observers, reliability must work)

  **References** (CRITICAL - Be Exhaustive):

  **FSM Framework References** (hooks):
  - `dawn_kestrel/core/fsm.py:FSMContext` - Context structure for storing subagent results

  **Current Implementation References** (subagent integration):
  - `dawn_kestrel/agents/review/fsm_security.py:_delegate_investigation_tasks()` - Current subagent delegation pattern
  - `dawn_kestrel/agents/review/fsm_security.py:_wait_for_investigation_tasks()` - Current subagent waiting pattern
  - `dawn_kestrel/agents/review/subagents/` - Subagent implementations to call

  **Test References** (pattern to follow):
  - `tests/review/agents/test_fsm_security_dedup.py` - Existing subagent test pattern

  **WHY Each Reference Matters**:
  - `dawn_kestrel/core/fsm.py:FSMContext` - Structure to store subagent results
  - `dawn_kestrel/agents/review/fsm_security.py:_delegate_investigation_tasks()` - Pattern for calling subagents
  - `dawn_kestrel/agents/review/fsm_security.py:_wait_for_investigation_tasks()` - Pattern for waiting for subagents
  - `dawn_kestrel/agents/review/subagents/` - Subagent interfaces to call
  - `tests/review/agents/test_fsm_security_dedup.py` - Existing test logic to preserve

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test covers: subagent calls are blocking await
  - [ ] Test covers: timeout protection works (30s timeout)
  - [ ] Test covers: subagent results stored in context
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_subagent_blocking_await -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_subagent_timeout -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_subagent_results_storage -v → PASS

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: Subagent calls are blocking await
    Tool: Bash
    Preconditions: Subagent integration implemented
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    print('Subagent calls completed (blocking await)')
asyncio.run(test())
"
      3. Assert: Output contains "Subagent calls completed (blocking await)"
    Expected Result: Subagent calls are awaited before next state
    Failure Indicators: Subagent calls not awaited, state transitions immediately
    Evidence: .sisyphus/evidence/task-10-subagent-blocking.log

  Scenario: Timeout protection blocks hanging subagents
    Tool: Bash
    Preconditions: Timeout configured for 30s
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
from dawn_kestrel.core.result import Err
import asyncio

async def test():
    agent = SecurityReviewerAgent()
    context = agent.fsm._create_context(repo_root='/tmp', base_ref='main', head_ref='feature')
    context.user_data['slow_subagent'] = True
    result = await agent.fsm.transition_to('DELEGATING_INVESTIGATION', context)
    assert result.is_err() == True
    print(f'Timeout blocked slow subagent: {result.code()}')
asyncio.run(test())
"
      3. Assert: Output contains "Timeout blocked slow subagent"
    Expected Result: Timeout (30s) blocks and fails to TIMEOUT
    Failure Indicators: Subagent hangs indefinitely, timeout not triggered
    Evidence: .sisyphus/evidence/task-10-subagent-timeout.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] Subagent blocking test output in .sisyphus/evidence/task-10-subagent-blocking.log
  - [ ] Timeout protection test output in .sisyphus/evidence/task-10-subagent-timeout.log

  **Commit**: YES
  - Message: `refactor(security): add subagent integration with blocking await and timeout`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`

- [ ] 11. Remove Deprecated Code

  **What to do**:
  - [ ] Remove deprecated ReviewFSMImpl class
  - [ ] Remove manual _transition_to() method
  - [ ] Remove VALID_TRANSITIONS dict (transitions now in FSMBuilder)
  - [ ] Remove ReviewState enum (states now in FSMBuilder)
  - [ ] Remove any old FSM-related attributes
  - [ ] Write TDD tests to verify deprecated code is removed
  - [ ] Verify FSMBuilder is the only FSM mechanism

  **Must NOT do**:
  - Do NOT remove handler methods (_initial_exploration, etc.) - keep as-is
  - Do NOT remove subagent code
  - Do NOT remove test logic (adapt tests to new FSM)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Simple cleanup task - removing deprecated code
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 10, 12, 13)
  - **Blocks**: Tasks 12, 13 (tests and integration depend on cleanup)
  - **Blocked By**: Task 10 (subagent integration must work before cleanup)

  **References** (CRITICAL - Be Exhaustive):

  **Current Implementation References** (code to remove):
  - `dawn_kestrel/agents/review/fsm_security.py:ReviewFSMImpl` - Deprecated class to remove
  - `dawn_kestrel/agents/review/fsm_security.py:ReviewState` - Deprecated enum to remove
  - `dawn_kestrel/agents/review/fsm_security.py:VALID_TRANSITIONS` - Deprecated dict to remove

  **WHY Each Reference Matters**:
  - `dawn_kestrel/agents/review/fsm_security.py:ReviewFSMImpl` - Exact class name to remove
  - `dawn_kestrel/agents/review/fsm_security.py:ReviewState` - Exact enum name to remove
  - `dawn_kestrel/agents/review/fsm_security.py:VALID_TRANSITIONS` - Exact dict name to remove

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test verifies: ReviewFSMImpl class removed
  - [ ] Test verifies: ReviewState enum removed
  - [ ] Test verifies: VALID_TRANSITIONS dict removed
  - [ ] pytest tests/review/agents/test_fsm_security_builder.py::test_deprecated_removed -v → PASS
  - [ ] No references to ReviewFSMImpl, ReviewState, VALID_TRANSITIONS in code

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: Deprecated ReviewFSMImpl class removed
    Tool: Bash
    Preconditions: Deprecated code removed
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
import sys
try:
    from dawn_kestrel.agents.review.fsm_security import ReviewFSMImpl
    print('ReviewFSMImpl still exists - FAIL')
    sys.exit(1)
except ImportError:
    print('ReviewFSMImpl removed successfully - PASS')
"
      3. Assert: Output contains "ReviewFSMImpl removed successfully"
    Expected Result: ReviewFSMImpl class no longer importable
    Failure Indicators: Class still exists, still importable
    Evidence: .sisyphus/evidence/task-11-deprecated-removed.log

  Scenario: Deprecated ReviewState enum removed
    Tool: Bash
    Preconditions: Deprecated code removed
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "
import sys
try:
    from dawn_kestrel.agents.review.fsm_security import ReviewState
    print('ReviewState still exists - FAIL')
    sys.exit(1)
except ImportError:
    print('ReviewState removed successfully - PASS')
"
      3. Assert: Output contains "ReviewState removed successfully"
    Expected Result: ReviewState enum no longer importable
    Failure Indicators: Enum still exists, still importable
    Evidence: .sisyphus/evidence/task-11-deprecated-removed.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] Deprecated removal test output in .sisyphus/evidence/task-11-deprecated-removed.log

  **Commit**: YES
  - Message: `refactor(security): remove deprecated ReviewFSMImpl and old FSM code`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/agents/test_fsm_security_builder.py`

- [ ] 12. Update Existing Tests (Deduplication, Confidence)

  **What to do**:
  - [ ] Update tests/review/agents/test_fsm_security_dedup.py
    - Adapt to use FSMBuilder-based agent
    - Preserve test logic (deduplication verification)
  - [ ] Update tests/review/agents/test_fsm_security_confidence.py
    - Adapt to use FSMBuilder-based agent
    - Preserve test logic (confidence threshold verification)
  - [ ] Verify tests still pass with new FSM
  - [ ] Compare with baseline results

  **Must NOT do**:
  - Do NOT change test logic (preserve verification of deduplication and confidence)
  - Do NOT remove tests

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Test adaptation requires understanding of existing test patterns
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 10, 11, 13)
  - **Blocks**: Task 13 (integration tests depend on these)
  - **Blocked By**: Tasks 10, 11 (subagent integration and cleanup must be done)

  **References** (CRITICAL - Be Exhaustive):

  **Test References** (to update):
  - `tests/review/agents/test_fsm_security_dedup.py` - Test to adapt to new FSM
  - `tests/review/agents/test_fsm_security_confidence.py` - Test to adapt to new FSM

  **Baseline References** (for comparison):
  - `.sisyphus/evidence/task-0-baseline-dedup.log` - Baseline test results to match
  - `.sisyphus/evidence/task-0-baseline-confidence.log` - Baseline test results to match

  **WHY Each Reference Matters**:
  - `tests/review/agents/test_fsm_security_dedup.py` - Test to update for new FSM
  - `tests/review/agents/test_fsm_security_confidence.py` - Test to update for new FSM
  - `.sisyphus/evidence/task-0-baseline-dedup.log` - Expected behavior to match
  - `.sisyphus/evidence/task-0-baseline-confidence.log` - Expected behavior to match

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] tests/review/agents/test_fsm_security_dedup.py adapted to new FSM
  - [ ] tests/review/agents/test_fsm_security_confidence.py adapted to new FSM
  - [ ] pytest tests/review/agents/test_fsm_security_dedup.py -v → PASS
  - [ ] pytest tests/review/agents/test_fsm_security_confidence.py -v → PASS
  - [ ] Test results match baseline (no regression)

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: Deduplication test still passes with new FSM
    Tool: Bash
    Preconditions: Test adapted to new FSM
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. pytest tests/review/agents/test_fsm_security_dedup.py -v > .sisyphus/evidence/task-12-dedup-after.log
      3. cat .sisyphus/evidence/task-12-dedup-after.log
      4. Assert: Output contains "passed" and no "failed"
      5. diff .sisyphus/evidence/task-0-baseline-dedup.log .sisyphus/evidence/task-12-dedup-after.log
      6. Assert: No significant differences (same test count, same behavior)
    Expected Result: Deduplication test passes with new FSM, matches baseline
    Failure Indicators: Test fails, behavior differs from baseline
    Evidence: .sisyphus/evidence/task-12-dedup-after.log, .sisyphus/evidence/task-0-baseline-dedup.log

  Scenario: Confidence threshold test still passes with new FSM
    Tool: Bash
    Preconditions: Test adapted to new FSM
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. pytest tests/review/agents/test_fsm_security_confidence.py -v > .sisyphus/evidence/task-12-confidence-after.log
      3. cat .sisyphus/evidence/task-12-confidence-after.log
      4. Assert: Output contains "passed" and no "failed"
      5. diff .sisyphus/evidence/task-0-baseline-confidence.log .sisyphus/evidence/task-12-confidence-after.log
      6. Assert: No significant differences (same test count, same behavior)
    Expected Result: Confidence threshold test passes with new FSM, matches baseline
    Failure Indicators: Test fails, behavior differs from baseline
    Evidence: .sisyphus/evidence/task-12-confidence-after.log, .sisyphus/evidence/task-0-baseline-confidence.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] Deduplication test after migration in .sisyphus/evidence/task-12-dedup-after.log
  - [ ] Confidence threshold test after migration in .sisyphus/evidence/task-12-confidence-after.log

  **Commit**: YES
  - Message: `refactor(security): update existing tests for new FSM (deduplication, confidence)`
  - Files: `tests/review/agents/test_fsm_security_dedup.py`, `tests/review/agents/test_fsm_security_confidence.py`

- [ ] 13. Integration Tests + Cleanup

  **What to do**:
  - [ ] Run all test suite: pytest tests/ -v
  - [ ] Verify all FSM tests pass
  - [ ] Verify all security review tests pass
  - [ ] Verify no regressions vs baseline
  - [ ] Clean up temporary files (evidence logs)
  - [ ] Update documentation if needed (docs/patterns.md)
  - [ ] Run manual smoke test (optional - if CLI exists)

  **Must NOT do**:
  - Do NOT leave temporary files
  - Do NOT skip test verification

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Final verification and cleanup - simple task
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final task)
  - **Blocks**: None (final)
  - **Blocked By**: Tasks 10, 11, 12 (all implementation must be done)

  **References** (CRITICAL - Be Exhaustive):

  **Test References** (to run):
  - `tests/` - All tests to run

  **Baseline References** (for comparison):
  - `.sisyphus/evidence/task-0-baseline-*.log` - Baseline results to compare

  **Documentation References** (to update):
  - `docs/patterns.md:Section 22` - FSM Builder Pattern documentation

  **WHY Each Reference Matters**:
  - `tests/` - Complete test suite to verify no regressions
  - `.sisyphus/evidence/task-0-baseline-*.log` - Expected results to match
  - `docs/patterns.md:Section 22` - Documentation to update with security review agent example

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY**
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] All tests pass: pytest tests/ -v
  - [ ] No regressions vs baseline
  - [ ] Temporary files cleaned up
  - [ ] Documentation updated (optional)

  **Agent-Executed QA Scenarios (MANDATORY):**

  \`\`\`
  Scenario: All tests pass with no regressions
    Tool: Bash
    Preconditions: All tasks completed
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. pytest tests/ -v > .sisyphus/evidence/task-13-final-tests.log
      3. cat .sisyphus/evidence/task-13-final-tests.log
      4. Assert: Output contains no "FAILED"
      5. Assert: Output contains "passed" for all tests
      6. ls .sisyphus/evidence/ | wc -l
      7. Assert: No unexpected temporary files remain
    Expected Result: All tests pass, no regressions, cleanup complete
    Failure Indicators: Any test fails, regressions detected, temporary files remain
    Evidence: .sisyphus/evidence/task-13-final-tests.log

  Scenario: FSM workflow end-to-end smoke test
    Tool: Bash (if CLI exists)
    Preconditions: CLI available
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python dawn_kestrel/agents/review/fsm_cli.py --help > .sisyphus/evidence/task-13-cli-smoke.log
      3. cat .sisyphus/evidence/task-13-cli-smoke.log
      4. Assert: CLI runs without errors
    Expected Result: CLI works with new FSM
    Failure Indicators: CLI fails, errors in output
    Evidence: .sisyphus/evidence/task-13-cli-smoke.log
  \`\`\`

  **Evidence to Capture:**
  - [ ] Final test results in .sisyphus/evidence/task-13-final-tests.log
  - [ ] CLI smoke test output in .sisyphus/evidence/task-13-cli-smoke.log (if CLI exists)

  **Commit**: YES
  - Message: `refactor(security): complete migration to FSM Builder Pattern - integration tests passing`
  - Files: (none - final verification task)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 0 | (none - baseline verification only) | - | - |
| 1 | `refactor(security): add FSMBuilder state declarations and transitions` | fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py -v |
| 2 | `refactor(security): add entry hooks for INITIAL_EXPLORATION and DELEGATING_INVESTIGATION` | fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py::test_initial_exploration_entry_hook -v |
| 3 | `refactor(security): add entry hooks for REVIEWING_RESULTS and FINAL_ASSESSMENT` | fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py::test_reviewing_results_entry_hook -v |
| 4 | `refactor(security): add exit hooks for all states` | fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py::test_exit_hooks -v |
| 5 | `refactor(security): add guard conditions for max_iterations and confidence_threshold` | fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py::test_max_iterations_guard -v |
| 6 | `refactor(security): add EventMediator integration and event publishing` | fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py::test_event_publishing -v |
| 7 | `refactor(security): add observers (logging, metrics, alerting)` | logging_observer.py, metrics_observer.py, alerting_observer.py, fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py::test_logging_observer -v |
| 8 | `refactor(security): add reliability wrappers (CircuitBreaker, RetryExecutor, RateLimiter)` | fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py::test_circuit_breaker -v |
| 9 | `refactor(security): add selective retry for hook exceptions (TimeoutError/NetworkError)` | fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py::test_timeout_error_retry -v |
| 10 | `refactor(security): add subagent integration with blocking await and timeout` | fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py::test_subagent_blocking_await -v |
| 11 | `refactor(security): remove deprecated ReviewFSMImpl and old FSM code` | fsm_security.py, test_fsm_security_builder.py | pytest test_fsm_security_builder.py::test_deprecated_removed -v |
| 12 | `refactor(security): update existing tests for new FSM (deduplication, confidence)` | test_fsm_security_dedup.py, test_fsm_security_confidence.py | pytest test_fsm_security_dedup.py -v |
| 13 | `refactor(security): complete migration to FSM Builder Pattern - integration tests passing` | - | pytest tests/ -v |

---

## Success Criteria

### Verification Commands
```bash
# Baseline verification (Task 0)
cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
pytest tests/review/agents/test_fsm_security_dedup.py -v > .sisyphus/evidence/baseline-dedup.log
pytest tests/review/agents/test_fsm_security_confidence.py -v > .sisyphus/evidence/baseline-confidence.log

# After migration (Task 13)
pytest tests/ -v
pytest tests/review/agents/test_fsm_security_builder.py -v
pytest tests/core/test_fsm.py -v
```

### Final Checklist
- [ ] SecurityReviewerAgent uses FSMBuilder (not manual FSM)
- [ ] All 8 states declared via FSMBuilder
- [ ] All transitions declared via FSMBuilder
- [ ] Entry hooks for all states calling existing handlers
- [ ] Exit hooks for all states
- [ ] Guard conditions (max_iterations, confidence_threshold)
- [ ] EventMediator configured and publishing events
- [ ] Three observers: logging, metrics, alerting
- [ ] Reliability wrappers on all hooks (CircuitBreaker, RetryExecutor, RateLimiter)
- [ ] Hook exceptions: TimeoutError/NetworkError retry (3 times), others fail to FAILED
- [ ] Subagent calls: blocking await with 30s timeout
- [ ] Deprecated ReviewFSMImpl removed
- [ ] All existing tests pass (deduplication, confidence)
- [ ] New TDD tests pass (test_fsm_security_builder.py)
- [ ] FSM framework tests pass (test_fsm.py)
- [ ] No regressions vs baseline
- [ ] In-memory state (no persistence)
- [ ] One-shot FSM per review session
