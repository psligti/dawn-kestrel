# FSM Builder Pattern - Workflow-Oriented FSM (Intake/Plan/Act/Synthesize/Check/Done)

## TL;DR

> **Quick Summary**: Create a comprehensive, workflow-oriented FSM framework + fluent builder, then implement a concrete **agent workflow FSM** with phases `intake → plan → act → synthesize → check → done`. `plan/act/synthesize/check` form a sub-loop that repeats until stop conditions are met or the initial intent is satisfied. **Each phase is executed via an LLM prompt** (Act is the tool-using phase).
>
> **Deliverables**:
> - New FSM framework module: `dawn_kestrel/core/fsm.py`
> - FSM builder with fluent API: `FSMBuilder` class
> - Integration tests: `tests/core/test_fsm.py` (80%+ coverage)
> - Workflow FSM: phase loop `intake → plan → act → synthesize → check → done` (LLM-prompted phases)
> - Integration: run workflow loop via AgentRuntime + AgentOrchestrator
> - Documentation updates for patterns.md
>
> **Estimated Effort**: Large (complex integration of multiple patterns)
> **Parallel Execution**: YES - 2 waves (core FSM first, then integrations)
> **Critical Path**: FSM protocol → FSMImpl → FSMBuilder → workflow phase contracts → workflow FSM loop → tests → integration → docs

---

## Context

### Original Request
Create a FSM with all the bells and whistles. Add in a builder pattern that helps use all the patterns mentioned in @docs/patterns.md

### Interview Summary
**Key Discussions & User Decisions**:
- **Purpose**: Multi-domain FSM - Configurable for different use cases (agents, workflows, pipelines, etc.)
- **Pattern Integration**: All patterns requested, but limited to 12 relevant patterns via Metis analysis
- **Features Selected** (all requested by user):
  - State persistence (Repository pattern, immediate persistence per transition)
  - Event publishing (Mediator + Observer, all state changes)
  - Reliability wrappers (Retry + Circuit Breaker + Rate Limiter + Bulkhead for external actions only)
  - Command-based transitions with audit logging (no undo/redo)
  - State entry/exit hooks (log and continue on error)
  - Guard conditions
- **Migration Strategy**: Replace existing FSM implementations (AgentFSMImpl, ReviewFSMImpl)
- **Hook Error Handling**: Log and continue (state change completes)
- **Thread Safety**: Not required (matching existing patterns - NOT thread-safe)
- **State Model**: Flat states with string identifiers (matching existing FSMs)
- **Builder API**: Fluent with `.with_*()` methods (10-15 methods max)

**Research Findings**:
- All 21 patterns documented and most already implemented in codebase
- Existing FSMs: `AgentFSMImpl` (6 states), `ReviewFSMImpl` (8 states) - both basic implementations
- Existing builder: `ContextBuilder` for agent contexts (not fluent)
- Test infrastructure: pytest with pytest-asyncio, all patterns have test files
- Pattern locations:
  - Result: `dawn_kestrel/core/result.py`
  - Commands: `dawn_kestrel/core/commands.py`
  - Mediator: `dawn_kestrel/core/mediator.py`
  - Observer: `dawn_kestrel/core/observer.py`
  - Repository: `dawn_kestrel/core/repositories.py`
  - Circuit Breaker: `dawn_kestrel/llm/circuit_breaker.py`
  - Retry: `dawn_kestrel/llm/retry.py`
  - Rate Limiter: `dawn_kestrel/llm/rate_limiter.py`
  - Bulkhead: `dawn_kestrel/llm/bulkhead.py`
  - DI Container: `dawn_kestrel/core/di_container.py`
  - Facade: `dawn_kestrel/core/facade.py`

### Metis Review
**Identified Gaps (addressed in plan)**:
- **Guardrails Applied**: Limited to 12 relevant patterns (NOT all 21), explicitly excluded Decorator/Proxy, Composite, Null Object, Strategy patterns as not FSM-relevant
- **Scope Boundaries**: No state visualization, debugging tools, export/import features
- **Thread Safety**: NOT thread-safe (matches existing patterns)
- **Migration Path**: Replace existing FSMs, update AgentRuntime
- **Edge Cases**: Hook exceptions, concurrent transitions, persistence failures, observer unregistration, command audit after multiple transitions
- **Integration Points**: DI Container, AgentRuntime, Facade, Storage, Plugin Discovery
- **Missing Acceptance Criteria**: Added comprehensive test categories for all features

**Guardrails from Metis Review**:
- ❌ **MUST NOT**: Integrate Decorator/Proxy, Composite, Null Object, Strategy patterns (not relevant to FSM)
- ❌ **MUST NOT**: Add state visualization, debugging tools, or export/import features
- ❌ **MUST NOT**: Add thread safety or synchronization primitives
- ❌ **MUST NOT**: Modify existing FSM implementations (create new module)
- ❌ **MUST NOT**: Add hierarchical states or state machine compilation
- ✅ **MUST**: Create new FSM framework as separate module (`dawn_kestrel/core/fsm.py`)
- ✅ **MUST**: Replace existing FSMs (AgentFSMImpl, ReviewFSMImpl)
- ✅ **MUST**: Use fluent builder API with `.with_*()` methods (10-15 methods max)
- ✅ **MUST**: Match thread safety model of existing patterns (NOT thread-safe)
- ✅ **MUST**: Follow existing code conventions (Result returns, Protocol-based design, docstrings)

---

## Work Objectives

### Core Objective
Create a comprehensive, multi-domain FSM framework with fluent builder pattern that integrates 12 relevant design patterns, providing state persistence, event publishing, reliability wrappers for external actions, command-based transitions with audit logging, state entry/exit hooks, and guard conditions.

### Workflow FSM Requirement (Agent Loop)

Implement a concrete **workflow FSM** whose states match the harness loop:

- **States (in order)**: `intake` → `plan` → `act` → `synthesize` → `check` → `done`
- **Sub-loop**: `plan` → `act` → `synthesize` → `check` → (`plan` again OR `done`)
- **Phase semantics** (LLM prompt per phase):
  - `intake`: capture initial intent + constraints + initial evidence snapshot
  - `plan`: generate/modify/prioritize todos
  - `act`: use tools to perform work against top-priority todos
  - `synthesize`: review/merge results and update todo statuses
  - `check`: decide whether to continue loop; enforce stop conditions
  - `done`: emit final result + stop reason
- **Stop conditions** (must be supported):
  - success/intent met
  - no new info / stagnation
  - budget reached (iterations/tool calls/wall time)
  - human input required (blocking question)
  - risk threshold exceeded

Each phase MUST be implemented as an LLM call (prompt + structured output), with code-level enforcement for hard budgets regardless of LLM response.

### Concrete Deliverables
- `dawn_kestrel/core/fsm.py` - New FSM module with FSM protocol and FSMImpl
- `dawn_kestrel/core/fsm_builder.py` - FSMBuilder with fluent API
- `tests/core/test_fsm.py` - Comprehensive test suite (80%+ coverage)
- `dawn_kestrel/core/fsm_state_repository.py` - FSMStateRepository for persistence
- Migration updates: Update AgentRuntime, remove/deprecate AgentFSMImpl and ReviewFSMImpl
- Documentation updates: Add FSM Builder Pattern to `docs/patterns.md`

### Definition of Done
- [x] FSM protocol and implementation with all requested features
- [x] FSMBuilder with fluent API (10-15 methods)
- [x] State persistence via FSMStateRepository
- [x] Event publishing via EventMediator
- [x] Observer registration for state changes
- [x] Command-based transitions with audit logging
- [x] State entry/exit hooks with error handling (log and continue)
- [x] Guard conditions for transition validation
- [x] Reliability wrappers for external actions (Circuit Breaker, Retry, Rate Limiter, Bulkhead)
- [x] All tests passing (80%+ coverage)
- [x] Existing code migrated to use new FSM
- [x] Documentation updated

### Must Have
- **Multi-domain support**: FSM configurable for different domains (agents, workflows, pipelines, etc.)
- **Pattern integration**: 12 relevant patterns integrated (Result, Command, Mediator, Observer, Repository, Circuit Breaker, Retry, Rate Limiter, Bulkhead, Facade, DI Container)
- **Fluent builder API**: Method chaining with `.with_*()` or `.enable_*()` methods (10-15 methods max)
- **State persistence**: Repository-based immediate persistence per transition
- **Event publishing**: All state changes published via Mediator
- **Observer support**: Register/unregister observers for state changes
- **Command audit logging**: Commands created for transitions with provenance tracking
- **State entry/exit hooks**: Optional hooks execute on state change (log and continue on error)
- **Guard conditions**: Optional guards validate transitions before execution
- **Reliability wrappers**: External actions wrapped with Circuit Breaker, Retry, Rate Limiter, Bulkhead
- **Result-based errors**: All operations return `Result[T]` (no exceptions)
- **Protocol-based design**: FSM protocol for multiple implementations
- **String state identifiers**: Flat states with string names (matching existing FSMs)
- **NOT thread-safe**: Match existing pattern behavior

### Must NOT Have (Guardrails)
- ❌ Thread safety or synchronization primitives (locks, semaphores)
- ❌ Hierarchical states or substates
- ❌ State visualization tools, graph export, or debug UI
- ❌ FSM DSL or external configuration formats
- ❌ Undo/redo capability (audit logging only)
- ❌ Full state history persistence (only current state)
- ❌ State machine validation or compilation tools
- ❌ Decorator/Proxy pattern integration (not FSM-relevant)
- ❌ Composite pattern integration (states not hierarchical)
- ❌ Null Object pattern integration (no "null states")
- ❌ Strategy pattern integration (transitions not algorithm selection)
- ❌ More than 15 builder methods
- ❌ Extensive tutorial docs or migration guides (docstrings only)
- ❌ Inline examples or comments beyond docstrings
- ❌ Hooks persisting state (use Repository integration)
- ❌ Hooks publishing events (use Mediator integration)

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
- **Infrastructure exists**: YES (pytest with pytest-asyncio)
- **Automated tests**: YES (TDD - RED-GREEN-REFACTOR)
- **Framework**: pytest with pytest-asyncio

### Test Setup Task (Infrastructure exists - skip setup)

### If TDD Enabled

Each TODO follows RED-GREEN-REFACTOR:

**Task Structure:**
1. **RED**: Write failing test first
   - Test file: `tests/core/test_fsm.py`
   - Test command: `pytest tests/core/test_fsm.py -k test_name`
   - Expected: FAIL (test exists, implementation doesn't)
2. **GREEN**: Implement minimum code to pass
   - Command: `pytest tests/core/test_fsm.py -k test_name`
   - Expected: PASS
3. **REFACTOR**: Clean up while keeping green
   - Command: `pytest tests/core/test_fsm.py -k test_name`
   - Expected: PASS (still)

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
| **Library/Module** | Bash (pytest, Python REPL) | Import, create FSMs, transition states, assert behavior |
| **FSM Logic** | Bash (pytest) | Run test suite, assert state transitions, guard conditions, hooks |
| **Persistence** | Bash (pytest) | Create FSM with persistence, transition, verify state saved |
| **Events** | Bash (pytest) | Subscribe to Mediator events, trigger transition, assert event received |

**Each Scenario MUST Follow This Format:**

```
Scenario: [Descriptive name — what behavior is being verified]
  Tool: Bash (pytest)
  Preconditions: [What must be true before this scenario runs]
  Steps:
    1. [Exact command with specific test name]
    2. [Next action with expected intermediate state]
    3. [Assertion with exact expected value]
  Expected Result: [Concrete, observable outcome]
  Failure Indicators: [What would indicate failure]
  Evidence: [Test output path / pytest results]
```

**Scenario Detail Requirements:**
- **Test names**: Specific test function names from test file
- **Assertions**: Exact values (`assert result.is_ok()`, not "verify it works")
- **Data**: Concrete test data (`"idle"`, `"running"`, not `"[initial_state]"`)
- **Failure modes**: Error cases tested alongside happy paths
- **Evidence**: Test output captured

---

## Execution Strategy

### Parallel Execution Waves

> Maximize throughput by grouping independent tasks into parallel waves.
> Each wave completes before the next begins.

```
Wave 1 (Start Immediately):
├── Task 1: FSM Protocol design
├── Task 2: FSMImpl core implementation
└── Task 3: FSMBuilder base implementation

Wave 2 (After Wave 1):
├── Task 4: State persistence integration
├── Task 5: Event publishing integration
├── Task 6: Observer integration
├── Task 7: Command-based transitions
├── Task 8: State entry/exit hooks
└── Task 9: Guard conditions

Wave 3 (After Wave 2):
├── Task 10: Reliability wrappers (Circuit Breaker, Retry, Rate Limiter, Bulkhead)
├── Task 11: FSMStateRepository implementation
└── Task 12: DI Container integration

Wave 4 (After Wave 3):
├── Task 13: Comprehensive test suite (tests/core/test_fsm.py)
└── Task 14: Facade integration

Wave 5 (After Wave 4):
├── Task 15: AgentRuntime migration (use new FSM)
└── Task 16: Deprecate/remove AgentFSMImpl, ReviewFSMImpl

Wave 6 (After Wave 5):
└── Task 17: Documentation update (docs/patterns.md)

Critical Path: Task 1 → Task 2 → Task 3 → Task 7 → Task 13 → Task 15 → Task 17
Parallel Speedup: ~50% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3 | 2, 3 |
| 2 | 1 | 4, 5, 6, 7, 8, 9 | 3 |
| 3 | 1 | 10, 12 | 2, 4, 5, 6, 7, 8, 9 |
| 4 | 2 | 10, 13 | 5, 6, 7, 8, 9, 11, 12 |
| 5 | 2 | 10, 13 | 4, 6, 7, 8, 9, 11, 12 |
| 6 | 2 | 10, 13 | 4, 5, 7, 8, 9, 11, 12 |
| 7 | 2 | 10, 13 | 4, 5, 6, 8, 9, 11, 12 |
| 8 | 2 | 10, 13 | 4, 5, 6, 7, 9, 11, 12 |
| 9 | 2 | 10, 13 | 4, 5, 6, 7, 8, 11, 12 |
| 10 | 3, 4, 5, 6, 7, 8, 9 | 13 | 11, 12 |
| 11 | 2 | 13 | 4, 5, 6, 7, 8, 9, 10, 12 |
| 12 | 3 | 13 | 4, 5, 6, 7, 8, 9, 10, 11 |
| 13 | 10, 11, 12 | 14, 15 | 14 |
| 14 | 13 | 15 | 15 |
| 15 | 13 | 16, 17 | 16 |
| 16 | 15 | 17 | 17 |
| 17 | 15 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|---------|-------------------|
| 1 | 1, 2, 3 | task(category="unspecified-high", load_skills=[], run_in_background=false) |
| 2 | 4, 5, 6, 7, 8, 9 | task(category="unspecified-high", load_skills=[], run_in_background=false) |
| 3 | 10, 11, 12 | task(category="unspecified-high", load_skills=[], run_in_background=false) |
| 4 | 13, 14 | task(category="quick", load_skills=[], run_in_background=false) |
| 5 | 15, 16 | task(category="unspecified-high", load_skills=[], run_in_background=false) |
| 6 | 17 | task(category="quick", load_skills=[], run_in_background=false) |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info.

- [x] 1. Design FSM Protocol and Core Data Structures

  **What to do**:
  - Define FSM protocol with essential methods: `get_state()`, `transition_to()`, `is_transition_valid()`
  - Define FSMConfig dataclass for builder configuration (states, transitions, hooks, guards, etc.)
  - Define FSMContext dataclass for context passed to hooks and guards
  - Define TransitionConfig dataclass for transition metadata (from_state, to_state, guards, hooks)
  - Import Result pattern: `from dawn_kestrel.core.result import Result, Ok, Err`
  - Follow Protocol-based design pattern with `@runtime_checkable`

  **Must NOT do**:
  - Add thread safety or locks
  - Add hierarchical states or state classes
  - Add state visualization or debugging features

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Protocol and dataclass design requires careful architecture decisions
  - **Skills**: None needed
    - No external skills required for this core design task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/agent_fsm.py:AgentFSM` protocol (lines 29-69) - Protocol-based FSM design pattern to follow
  - `dawn_kestrel/core/result.py:Result, Ok, Err` (lines 1-50) - Result pattern for type-safe error handling
  - `dawn_kestrel/core/commands.py:Command, BaseCommand` (lines 1-100) - Command pattern structure and CommandContext

  **Test References** (testing patterns to follow):
  - `tests/core/test_agent_fsm.py:TestAgentFSMInitialization` (lines 7-46) - Test patterns for FSM initialization

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:15. State (FSM) Pattern` (lines 1154-1226) - FSM pattern specification and valid transitions
  - `docs/patterns.md:10. Command Pattern` (lines 774-850) - Command pattern for provenance tracking
  - `docs/patterns.md:3. Result Pattern` (lines 209-307) - Result pattern for explicit error handling

  **WHY Each Reference Matters** (explain the relevance):
  - FSM protocol shows existing FSM design patterns that new FSM should follow for consistency
  - Result pattern shows how all existing code returns errors without exceptions
  - Command pattern shows how to implement provenance tracking for state transitions
  - Test patterns show testing conventions (pytest, Result-based assertions)

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test file created: tests/core/test_fsm.py
  - [ ] Test covers: FSM protocol has get_state, transition_to, is_transition_valid methods
  - [ ] pytest tests/core/test_fsm.py::TestFSMProtocol::test_fsm_protocol_has_required_methods → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSM protocol defines required methods
    Tool: Bash (pytest)
    Preconditions: dawn_kestrel/core/fsm.py exists with FSM protocol defined
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMProtocol::test_fsm_protocol_has_required_methods -v
      2. Assert: Test passes (PASSED in output)
    Expected Result: FSM protocol has get_state(), transition_to(), is_transition_valid() methods
    Failure Indicators: Test fails with "method not found" or "protocol missing method" errors
    Evidence: pytest output showing test results
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all FSM protocol tests

  **Commit**: YES (groups with 2, 3)
  - Message: `feat(core): add FSM protocol and data structures`
  - Files: dawn_kestrel/core/fsm.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMProtocol`

- [x] 2. Implement FSMImpl Core (State Management and Transition Validation)

  **What to do**:
  - Implement FSMImpl class with internal state tracking (_state)
  - Implement get_state() method returning current state string
  - Implement transition_to(new_state) with Result return (Ok/Err)
  - Implement is_transition_valid(from_state, to_state) returning bool
  - Define VALID_STATES and VALID_TRANSITIONS class variables (configurable via builder)
  - Import Result pattern for explicit error handling
  - Follow pattern from AgentFSMImpl but make states configurable

  **Must NOT do**:
  - Add thread safety or locks
  - Add hierarchical states or nested state logic
  - Modify existing AgentFSMImpl

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Core FSM logic requires careful state transition implementation
  - **Skills**: None needed
    - No external skills required for this implementation task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Tasks 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17
  - **Blocked By**: Task 1 (needs FSM protocol definition)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/agent_fsm.py:AgentFSMImpl` (lines 72-199) - Core FSM implementation pattern to follow
  - `dawn_kestrel/core/result.py:Result, Ok, Err` (lines 1-50) - Result pattern for error handling
  - `dawn_kestrel/core/agent_fsm.py:VALID_STATES, VALID_TRANSITIONS` (lines 96-113) - State and transition validation pattern

  **Test References** (testing patterns to follow):
  - `tests/core/test_agent_fsm.py:TestAgentFSMStateQuery` (lines 49-...) - Test patterns for state queries
  - `tests/core/test_agent_fsm.py:TestAgentFSMTransition` (lines ...-...) - Test patterns for transitions

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:15. State (FSM) Pattern` (lines 1169-1208) - FSM implementation details and state validation

  **WHY Each Reference Matters** (explain the relevance):
  - AgentFSMImpl shows existing FSM implementation patterns to follow for consistency
  - Result pattern shows how to return errors without exceptions
  - State validation patterns show how to validate transitions and reject invalid moves

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test file updated: tests/core/test_fsm.py
  - [ ] Test covers: FSMImpl initialization, state queries, valid transitions, invalid transitions
  - [ ] pytest tests/core/test_fsm.py::TestFSMImpl::test_fsm_impl_initializes_with_initial_state → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMImpl::test_fsm_impl_returns_current_state → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMImpl::test_fsm_impl_transitions_to_valid_state → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMImpl::test_fsm_impl_rejects_invalid_transition → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSMImpl manages state transitions correctly
    Tool: Bash (pytest)
    Preconditions: FSMImpl implemented in dawn_kestrel/core/fsm.py
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMImpl::test_fsm_impl_initializes_with_initial_state -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMImpl::test_fsm_impl_transitions_to_valid_state -v
      4. Assert: Test passes (PASSED in output)
      5. Run: pytest tests/core/test_fsm.py::TestFSMImpl::test_fsm_impl_rejects_invalid_transition -v
      6. Assert: Test passes (PASSED in output)
    Expected Result: FSMImpl correctly manages state and validates transitions
    Failure Indicators: Tests fail with assertion errors or unexpected exceptions
    Evidence: pytest output showing all FSMImpl tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all FSMImpl core tests

  **Commit**: YES (groups with 1, 3)
  - Message: `feat(core): implement FSMImpl core state management`
  - Files: dawn_kestrel/core/fsm.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMImpl`

- [x] 3. Implement FSMBuilder with Fluent API

  **What to do**:
  - Create FSMBuilder class with method chaining pattern
  - Implement with_state(state) method to add valid state
  - Implement with_transition(from_state, to_state) method to add valid transition
  - Implement with_entry_hook(state, hook) method to add entry callback
  - Implement with_exit_hook(state, hook) method to add exit callback
  - Implement with_guard(from_state, to_state, guard) method to add guard condition
  - Implement with_persistence(repository) method to enable state persistence
  - Implement with_mediator(mediator) method to enable event publishing
  - Implement with_observer(observer) method to add observer
  - Implement build() method returning FSM instance
  - Validate builder configuration (all states used in transitions defined)
  - Return Err from build() if configuration invalid

  **Must NOT do**:
  - Add more than 15 builder methods
  - Add methods for state visualization or debugging
  - Add methods for undo/redo (audit only, no undo capability)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Builder API design requires careful fluent method chaining and validation
  - **Skills**: None needed
    - No external skills required for this builder implementation task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Tasks 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17
  - **Blocked By**: Task 1 (needs FSM protocol definition)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/context/builder.py:ContextBuilder` (lines 19-91) - Existing builder pattern to follow for API design
  - `dawn_kestrel/core/agent_fsm.py:create_agent_fsm` (lines 182-199) - Factory function pattern for FSM creation

  **Test References** (testing patterns to follow):
  - `tests/core/test_facade.py:TestFacadeInitialization` (lines ...-...) - Test patterns for builder/factory patterns

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:Builder Pattern` (implicit in ContextBuilder) - Builder pattern for fluent API design

  **WHY Each Reference Matters** (explain the relevance):
  - ContextBuilder shows existing builder API patterns and method naming conventions to follow
  - Factory function shows how FSMs are currently created and can be replaced with builder

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test file updated: tests/core/test_fsm.py
  - [ ] Test covers: FSMBuilder fluent API, state/transition/hook/guard configuration, build validation
  - [ ] pytest tests/core/test_fsm.py::TestFSMBuilder::test_fsm_builder_fluent_api_creates_fsm → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMBuilder::test_fsm_builder_validates_invalid_configuration → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMBuilder::test_fsm_builder_with_entry_hook → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMBuilder::test_fsm_builder_with_exit_hook → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMBuilder::test_fsm_builder_with_guard_condition → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSMBuilder fluent API creates valid FSM with all features
    Tool: Bash (pytest)
    Preconditions: FSMBuilder implemented in dawn_kestrel/core/fsm.py
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMBuilder::test_fsm_builder_fluent_api_creates_fsm -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMBuilder::test_fsm_builder_with_entry_hook -v
      4. Assert: Test passes (PASSED in output)
      5. Run: pytest tests/core/test_fsm.py::TestFSMBuilder::test_fsm_builder_with_guard_condition -v
      6. Assert: Test passes (PASSED in output)
    Expected Result: FSMBuilder creates valid FSMs with hooks and guards configured
    Failure Indicators: Tests fail with builder API errors or configuration validation errors
    Evidence: pytest output showing all FSMBuilder tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all FSMBuilder tests

  **Commit**: YES (groups with 1, 2)
  - Message: `feat(core): implement FSMBuilder with fluent API`
  - Files: dawn_kestrel/core/fsm.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMBuilder`

- [x] 4. Integrate State Persistence via Repository Pattern

  **What to do**:
  - Create FSMStateRepository protocol with get_state, set_state methods
  - Create FSMStateRepositoryImpl wrapping SessionStorage or new FSM-specific storage
  - Update FSMImpl to accept optional repository in constructor
  - Implement persistence in transition_to(): after state change, persist via repository
  - Use Result pattern for repository operations (Ok/Err returns)
  - Handle persistence failures: log error, return Err from transition_to()
  - Follow existing repository pattern from dawn_kestrel/core/repositories.py

  **Must NOT do**:
  - Use Unit of Work (Repository pattern requested: immediate persistence)
  - Add persistence hooks (use Repository integration)
  - Persist full state history (only current state)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Persistence integration requires careful async error handling and Result pattern usage
  - **Skills**: None needed
    - No external skills required for this persistence integration task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7, 8, 9)
  - **Blocked By**: Task 2 (needs FSMImpl core implementation)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/repositories.py:SessionRepository` (lines 309-367) - Repository pattern and Result returns to follow
  - `dawn_kestrel/core/repositories.py:SessionRepositoryImpl` (lines 353-...) - Repository implementation pattern to follow
  - `dawn_kestrel/storage/store.py:SessionStorage` (lines 1-...) - Storage layer for repository to wrap

  **Test References** (testing patterns to follow):
  - `tests/core/test_repositories.py:TestSessionRepository::test_get_by_id_returns_session` (lines ...-...) - Test patterns for repository operations

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:4. Repository Pattern` (lines 309-401) - Repository pattern specification

  **WHY Each Reference Matters** (explain the relevance):
  - SessionRepository shows existing repository protocol and implementation patterns to follow
  - Repository test patterns show how to test async Result-based operations

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Repository module created: dawn_kestrel/core/fsm_state_repository.py
  - [ ] Test covers: FSMStateRepository.get_state, set_state, Result returns, error handling
  - [ ] pytest tests/core/test_fsm.py::TestFSMPersistence::test_fsm_persists_state_to_repository → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMPersistence::test_fsm_handles_persistence_failure → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSM persists state to repository after transition
    Tool: Bash (pytest)
    Preconditions: FSMStateRepository implemented and FSMImpl accepts repository
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMPersistence::test_fsm_persists_state_to_repository -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMPersistence::test_fsm_handles_persistence_failure -v
      4. Assert: Test passes (PASSED in output)
    Expected Result: FSM persists state to repository on every transition, handles failures gracefully
    Failure Indicators: Tests fail with persistence errors or state not saved
    Evidence: pytest output showing all persistence tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all persistence tests

  **Commit**: YES (groups with 5, 6, 7, 8, 9)
  - Message: `feat(core): integrate state persistence via Repository pattern`
  - Files: dawn_kestrel/core/fsm.py, dawn_kestrel/core/fsm_state_repository.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMPersistence`

- [x] 5. Integrate Event Publishing via Mediator Pattern

  **What to do**:
  - Update FSMImpl to accept optional EventMediator in constructor
  - Import EventMediator from dawn_kestrel/core.mediator
  - Create FSM-specific EventType (or use existing DOMAIN/APPLICATION/SYSTEM/LLM)
  - Publish state change event in transition_to() after state change applied
  - Event data should include: fsm_id, from_state, to_state, timestamp
  - Use Result pattern for publish operations (Ok/Err returns)
  - Handle publish failures: log error (log and continue on error)
  - Follow existing Mediator pattern from dawn_kestrel/core/mediator.py

  **Must NOT do**:
  - Filter events (all state changes as requested by user)
  - Add event hooks (use Mediator integration)
  - Publish hook execution events (only state changes)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Event integration requires understanding of Mediator pattern and async event publishing
  - **Skills**: None needed
    - No external skills required for this event integration task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6, 7, 8, 9)
  - **Blocked By**: Task 2 (needs FSMImpl core implementation)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/mediator.py:EventMediator` (lines 43-69) - EventMediator protocol to use for publishing
  - `dawn_kestrel/core/mediator.py:EventType` (lines 19-42) - Event types to use for FSM events
  - `dawn_kestrel/core/mediator.py:Event` (lines 15-17) - Event dataclass for state change events

  **Test References** (testing patterns to follow):
  - `tests/core/test_mediator.py:TestEventMediator::test_publishes_event` (lines ...-...) - Test patterns for mediator operations

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:8. Mediator Pattern` (lines 630-695) - Mediator pattern specification

  **WHY Each Reference Matters** (explain the relevance):
  - EventMediator shows existing mediator API to follow for event publishing
  - Event types and Event dataclass show how to structure FSM state change events

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test covers: FSM publishes events via Mediator on state change, Event data includes fsm_id, from_state, to_state, timestamp
  - [ ] pytest tests/core/test_fsm.py::TestFSMEvents::test_fsm_publishes_state_change_event → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMEvents::test_fsm_event_data_correct → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSM publishes state change events via Mediator
    Tool: Bash (pytest)
    Preconditions: FSMImpl integrated with EventMediator
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMEvents::test_fsm_publishes_state_change_event -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMEvents::test_fsm_event_data_correct -v
      4. Assert: Test passes (PASSED in output)
    Expected Result: FSM publishes events for all state changes with correct data
    Failure Indicators: Tests fail with event not published or incorrect event data
    Evidence: pytest output showing all event tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all event tests

  **Commit**: YES (groups with 4, 6, 7, 8, 9)
  - Message: `feat(core): integrate event publishing via Mediator pattern`
  - Files: dawn_kestrel/core/fsm.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMEvents`

- [x] 6. Integrate Observer Pattern for State Changes

  **What to do**:
  - Update FSMImpl to accept optional list of observers in constructor
  - Import Observable and Observer from dawn_kestrel/core.observer
  - Implement register_observer(observer) method to add observer
  - Implement unregister_observer(observer) method to remove observer
  - Notify all observers on state change in transition_to()
  - Pass event data to observers (same as published to mediator)
  - Handle observer notification failures: log error (log and continue on error)
  - Follow existing Observer pattern from dawn_kestrel/core/observer.py

  **Must NOT do**:
  - Add observer hooks (use Observer pattern directly)
  - Filter notifications to observers (all state changes)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Observer integration requires understanding of Observable protocol and safe notification patterns
  - **Skills**: None needed
    - No external skills required for this observer integration task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 7, 8, 9)
  - **Blocked By**: Task 2 (needs FSMImpl core implementation)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/observer.py:Observable` (lines 107-118) - Observable protocol to implement
  - `dawn_kestrel/core/observer.py:Observer` (lines 106-107) - Observer protocol to use
  - `dawn_kestrel/core/observer.py:ObservableImpl` (lines 120-...) - Observable implementation pattern to follow

  **Test References** (testing patterns to follow):
  - `tests/core/test_observer.py:TestObservable::test_register_observer` (lines ...-...) - Test patterns for observer registration

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:14. Observer Pattern` (lines 1091-1153) - Observer pattern specification

  **WHY Each Reference Matters** (explain the relevance):
  - Observable protocol shows required methods for observer integration
  - Observer implementation shows safe notification patterns (handling observer unregistration during notification)

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test covers: FSM registers/unregisters observers, notifies observers on state change, handles notification failures
  - [ ] pytest tests/core/test_fsm.py::TestFSMObserver::test_fsm_registers_observer → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMObserver::test_fsm_unregisters_observer → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMObserver::test_fsm_notifies_observers → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMObserver::test_fsm_handles_observer_failure → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSM notifies registered observers on state change
    Tool: Bash (pytest)
    Preconditions: FSMImpl integrated with Observer pattern
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMObserver::test_fsm_registers_observer -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMObserver::test_fsm_notifies_observers -v
      4. Assert: Test passes (PASSED in output)
      5. Run: pytest tests/core/test_fsm.py::TestFSMObserver::test_fsm_handles_observer_failure -v
      6. Assert: Test passes (PASSED in output)
    Expected Result: FSM registers, unregisters, and notifies observers correctly, handles failures gracefully
    Failure Indicators: Tests fail with observer registration errors or notification failures
    Evidence: pytest output showing all observer tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all observer tests

  **Commit**: YES (groups with 4, 5, 7, 8, 9)
  - Message: `feat(core): integrate Observer pattern for state changes`
  - Files: dawn_kestrel/core/fsm.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMObserver`

- [x] 7. Integrate Command-Based Transitions with Audit Logging

  **What to do**:
  - Create TransitionCommand extending BaseCommand from dawn_kestrel.core.commands
  - Implement execute() to perform state transition
  - Implement get_provenance() to return audit data (fsm_id, from_state, to_state, timestamp)
  - Update FSMImpl to create and execute TransitionCommand for each transition
  - Maintain command history list (for audit, not undo/redo)
  - Implement get_command_history() method returning list of executed commands
  - Return Result[TransitionCommand] from transition_to() for audit trail
  - Follow existing Command pattern from dawn_kestrel/core/commands.py

  **Must NOT do**:
  - Implement undo() or can_undo() (audit only, no undo/redo capability)
  - Allow redo of commands (only provenance tracking)
  - Expose full command history (only via get_command_history())

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Command integration requires understanding of BaseCommand pattern and provenance tracking
  - **Skills**: None needed
    - No external skills required for this command integration task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6, 8, 9)
  - **Blocked By**: Task 2 (needs FSMImpl core implementation)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/commands.py:Command` (lines 787-797) - Command protocol to implement
  - `dawn_kestrel/core/commands.py:BaseCommand` (lines 799-850) - BaseCommand class to extend
  - `dawn_kestrel/core/commands.py:CommandContext` (lines 774-786) - CommandContext structure for provenance

  **Test References** (testing patterns to follow):
  - `tests/core/test_commands.py:TestCommandExecution::test_command_returns_result` (lines ...-...) - Test patterns for command operations

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:10. Command Pattern` (lines 774-850) - Command pattern specification

  **WHY Each Reference Matters** (explain the relevance):
  - Command protocol shows required methods for transition command implementation
  - BaseCommand shows provenance tracking pattern to follow for audit logging

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test covers: TransitionCommand created, execute() performs transition, get_provenance() returns audit data, get_command_history() returns list
  - [ ] pytest tests/core/test_fsm.py::TestFSMCommands::test_transition_command_created → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMCommands::test_transition_command_executes → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMCommands::test_command_provenance_includes_audit_data → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMCommands::test_command_history_accessible → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSM creates TransitionCommand with audit logging for each state change
    Tool: Bash (pytest)
    Preconditions: TransitionCommand implemented and FSMImpl creates commands
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMCommands::test_transition_command_created -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMCommands::test_transition_command_executes -v
      4. Assert: Test passes (PASSED in output)
      5. Run: pytest tests/core/test_fsm.py::TestFSMCommands::test_command_provenance_includes_audit_data -v
      6. Assert: Test passes (PASSED in output)
      7. Run: pytest tests/core/test_fsm.py::TestFSMCommands::test_command_history_accessible -v
      8. Assert: Test passes (PASSED in output)
    Expected Result: FSM creates TransitionCommands with provenance tracking for audit, command history accessible
    Failure Indicators: Tests fail with command creation errors or missing provenance data
    Evidence: pytest output showing all command tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all command tests

  **Commit**: YES (groups with 4, 5, 6, 8, 9)
  - Message: `feat(core): integrate Command-based transitions with audit logging`
  - Files: dawn_kestrel/core/fsm.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMCommands`

- [x] 8. Integrate State Entry/Exit Hooks with Error Handling

  **What to do**:
  - Update FSMBuilder to store entry/exit hooks by state (from with_entry_hook, with_exit_hook)
  - Update FSMImpl to accept hooks dict in constructor
  - Execute exit hook before state change in transition_to()
  - Execute entry hook after state change applied in transition_to()
  - Handle hook exceptions: log error (log and continue on error per user decision)
  - Pass FSMContext to hooks (state, fsm_id, metadata)
  - Use Result pattern for hook execution (Ok/Err returns, but continue on error per user decision)
  - Follow existing hook patterns from codebase if any

  **Must NOT do**:
  - Block transitions on hook failure (log and continue only)
  - Allow hooks to persist state (use Repository integration)
  - Allow hooks to publish events (use Mediator integration)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Hook integration requires careful error handling and Result pattern usage
  - **Skills**: None needed
    - No external skills required for this hook integration task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6, 7, 9)
  - **Blocked By**: Task 2 (needs FSMImpl core implementation)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/decorators.py:log_function` (lines 870-904) - Logging decorator pattern for error handling
  - `dawn_kestrel/core/result.py:Result, Ok, Err` (lines 1-50) - Result pattern for hook execution results

  **Test References** (testing patterns to follow):
  - `tests/core/test_decorators.py:TestLoggingDecorator::test_decorator_wraps_function` (lines ...-...) - Test patterns for error handling

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:11. Decorator/Proxy Pattern` (lines 852-943) - Error handling patterns (hooks are similar)

  **WHY Each Reference Matters** (explain the relevance):
  - Logging decorator shows error handling patterns to follow for hook exception handling
  - Result pattern shows how to return errors from hook execution

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test covers: Entry hook executes on state entry, exit hook executes on state exit, hook exception logged and continues
  - [ ] pytest tests/core/test_fsm.py::TestFSMHooks::test_entry_hook_executes → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMHooks::test_exit_hook_executes → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMHooks::test_hook_failure_logs_and_continues → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSM executes state entry/exit hooks with error handling
    Tool: Bash (pytest)
    Preconditions: FSMImpl integrated with entry/exit hooks
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMHooks::test_entry_hook_executes -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMHooks::test_exit_hook_executes -v
      4. Assert: Test passes (PASSED in output)
      5. Run: pytest tests/core/test_fsm.py::TestFSMHooks::test_hook_failure_logs_and_continues -v
      6. Assert: Test passes (PASSED in output)
    Expected Result: FSM executes entry/exit hooks on state changes, logs hook errors, continues execution
    Failure Indicators: Tests fail with hooks not executing or blocking transitions on error
    Evidence: pytest output showing all hook tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all hook tests

  **Commit**: YES (groups with 4, 5, 6, 7, 9)
  - Message: `feat(core): integrate state entry/exit hooks with error handling`
  - Files: dawn_kestrel/core/fsm.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMHooks`

- [x] 9. Integrate Guard Conditions for Transition Validation

  **What to do**:
  - Update FSMBuilder to store guards by transition (from with_guard)
  - Update FSMImpl to accept guards dict in constructor
  - Execute guard before transition validation in transition_to()
  - Guard function signature: guard(from_state, to_state, context) -> Result[bool]
  - If guard returns Err, return Err from transition_to() (guard blocks transition)
  - If guard returns Ok(False), return Err with "Guard condition failed"
  - If guard returns Ok(True), continue with transition validation
  - Pass FSMContext to guards (state, fsm_id, metadata)
  - Use Result pattern for guard execution (Ok/Err returns)
  - Follow existing validation patterns from FSMImpl

  **Must NOT do**:
  - Allow guards with side effects (document as pure functions)
  - Execute guards after transition (execute before)
  - Skip guard execution for any transitions

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Guard integration requires careful validation logic and Result pattern usage
  - **Skills**: None needed
    - No external skills required for this guard integration task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6, 7, 8)
  - **Blocked By**: Task 2 (needs FSMImpl core implementation)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/agent_fsm.py:AgentFSMImpl.is_transition_valid` (lines 139-151) - Transition validation pattern to follow
  - `dawn_kestrel/core/result.py:Result, Ok, Err` (lines 1-50) - Result pattern for guard results

  **Test References** (testing patterns to follow):
  - `tests/core/test_agent_fsm.py:TestAgentFSMTransition::test_transition_to_valid_state` (lines ...-...) - Test patterns for transitions

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:15. State (FSM) Pattern` (lines 1169-1208) - FSM pattern with validation

  **WHY Each Reference Matters** (explain the relevance):
  - Transition validation shows existing guard/condition checking patterns to follow
  - Result pattern shows how guards return Ok/Err for validation results

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test covers: Guard validates before transition, guard blocks invalid transition, guard allows valid transition, guard receives context
  - [ ] pytest tests/core/test_fsm.py::TestFSMGuards::test_guard_validates_before_transition → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMGuards::test_guard_blocks_invalid_transition → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMGuards::test_guard_allows_valid_transition → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMGuards::test_guard_receives_context → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSM validates guard conditions before allowing transitions
    Tool: Bash (pytest)
    Preconditions: FSMImpl integrated with guard conditions
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMGuards::test_guard_validates_before_transition -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMGuards::test_guard_blocks_invalid_transition -v
      4. Assert: Test passes (PASSED in output)
      5. Run: pytest tests/core/test_fsm.py::TestFSMGuards::test_guard_allows_valid_transition -v
      6. Assert: Test passes (PASSED in output)
      7. Run: pytest tests/core/test_fsm.py::TestFSMGuards::test_guard_receives_context -v
      8. Assert: Test passes (PASSED in output)
    Expected Result: FSM validates guards before transitions, guards block invalid transitions, allow valid transitions
    Failure Indicators: Tests fail with guards not executing or incorrect validation
    Evidence: pytest output showing all guard tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all guard tests

  **Commit**: YES (groups with 4, 5, 6, 7, 8)
  - Message: `feat(core): integrate guard conditions for transition validation`
  - Files: dawn_kestrel/core/fsm.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMGuards`

 - [x] 10. Integrate Reliability Wrappers (Circuit Breaker, Retry, Rate Limiter, Bulkhead)

  **What to do**:
  - Import reliability patterns: CircuitBreaker, RetryExecutor, RateLimiter, Bulkhead
  - Add optional reliability_config to FSMBuilder (with_reliability)
  - Add reliability_config to FSMImpl constructor
  - Wrap external action callbacks in FSM with reliability wrappers:
    - CircuitBreaker: Check circuit state before external action, open on failures
    - RetryExecutor: Wrap external actions with retry and backoff (ExponentialBackoff)
    - RateLimiter: Check rate limit before external action, consume token on success
    - Bulkhead: Limit concurrent external actions per resource with semaphore
  - Do NOT wrap FSM internal operations (transitions, state queries) in reliability
  - Use existing reliability implementations from dawn_kestrel.llm.*
  - Follow existing reliability pattern usage from codebase

  **Must NOT do**:
  - Wrap FSM internal operations (transitions, get_state, is_transition_valid) in reliability
  - Allow reliability configuration for internal FSM operations
  - Reimplement reliability patterns (use existing ones)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Reliability integration requires understanding of CircuitBreaker, Retry, RateLimiter, Bulkhead patterns
  - **Skills**: None needed
    - No external skills required for this reliability integration task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 12)
  - **Blocked By**: Tasks 3, 4, 5, 6, 7, 8, 9 (need FSMBuilder and integrations complete)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/llm/circuit_breaker.py:CircuitBreaker` (lines 231-256) - CircuitBreaker protocol to use
  - `dawn_kestrel/llm/circuit_breaker.py:CircuitBreakerImpl` (lines 237-281) - CircuitBreaker implementation pattern
  - `dawn_kestrel/llm/retry.py:RetryExecutor` (lines 367-400) - RetryExecutor implementation pattern
  - `dawn_kestrel/llm/retry.py:ExponentialBackoff` (lines 384-395) - ExponentialBackoff strategy
  - `dawn_kestrel/llm/rate_limiter.py:RateLimiter` (lines 441-466) - RateLimiter protocol
  - `dawn_kestrel/llm/bulkhead.py:Bulkhead` (lines 319-327) - Bulkhead protocol

  **Test References** (testing patterns to follow):
  - `tests/llm/test_circuit_breaker.py::TestCircuitBreaker::test_circuit_opens_on_failure` (lines ...-...) - Test patterns for reliability
  - `tests/llm/test_retry.py::TestRetryExecutor::test_retry_retries_on_failure` (lines ...-...) - Test patterns for retry
  - `tests/llm/test_rate_limiter.py::TestRateLimiter::test_rate_limiter_limits_requests` (lines ...-...) - Test patterns for rate limiting

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:16. Circuit Breaker Pattern` (lines 1231-1301) - Circuit Breaker specification
  - `docs/patterns.md:18. Retry + Backoff Pattern` (lines 1367-1437) - Retry pattern specification
  - `docs/patterns.md:19. Rate Limiter Pattern` (lines 1439-1510) - Rate Limiter specification
  - `docs/patterns.md:17. Bulkhead Pattern` (lines 1303-1365) - Bulkhead specification

  **WHY Each Reference Matters** (explain the relevance):
  - Reliability patterns show existing implementations and API to use for external action wrapping
  - Test patterns show how to verify reliability wrapper behavior

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test covers: FSM wraps external actions in CircuitBreaker, FSM wraps in RetryExecutor, FSM wraps in RateLimiter, FSM wraps in Bulkhead
  - [ ] pytest tests/core/test_fsm.py::TestFSMReliability::test_fsm_wraps_external_actions_in_circuit_breaker → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMReliability::test_fsm_wraps_external_actions_in_retry → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMReliability::test_fsm_wraps_external_actions_in_rate_limiter → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMReliability::test_fsm_wraps_external_actions_in_bulkhead → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSM wraps external actions in reliability wrappers (Circuit Breaker, Retry, Rate Limiter, Bulkhead)
    Tool: Bash (pytest)
    Preconditions: FSMImpl integrated with reliability wrappers
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMReliability::test_fsm_wraps_external_actions_in_circuit_breaker -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMReliability::test_fsm_wraps_external_actions_in_retry -v
      4. Assert: Test passes (PASSED in output)
      5. Run: pytest tests/core/test_fsm.py::TestFSMReliability::test_fsm_wraps_external_actions_in_rate_limiter -v
      6. Assert: Test passes (PASSED in output)
      7. Run: pytest tests/core/test_fsm.py::TestFSMReliability::test_fsm_wraps_external_actions_in_bulkhead -v
      8. Assert: Test passes (PASSED in output)
    Expected Result: FSM wraps external actions in all reliability wrappers, FSM internal ops not wrapped
    Failure Indicators: Tests fail with reliability wrappers not applied or applied incorrectly
    Evidence: pytest output showing all reliability tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all reliability tests

  **Commit**: YES (groups with 11, 12)
  - Message: `feat(core): integrate reliability wrappers for external actions`
  - Files: dawn_kestrel/core/fsm.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMReliability`

 - [x] 11. Implement FSMStateRepository for Persistence

  **What to do**:
  - Create dawn_kestrel/core/fsm_state_repository.py module
  - Define FSMStateRepository protocol with get_state(fsm_id), set_state(fsm_id, state) methods
  - Create FSMStateRepositoryImpl wrapping SessionStorage (or new FSM-specific storage)
  - Store state as key-value: f"fsm:{fsm_id}" -> state string
  - Use Result pattern for all operations (Ok/Err returns)
  - Import SessionStorage from dawn_kestrel.storage.store
  - Follow existing repository patterns from dawn_kestrel/core/repositories.py
  - Add docstrings for public API

  **Must NOT do**:
  - Store full state history (only current state)
  - Use Unit of Work (Repository pattern requested)
  - Add complex query methods (only get/set state)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Repository implementation requires understanding of storage layer and Result pattern
  - **Skills**: None needed
    - No external skills required for this repository implementation task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10, 12)
  - **Blocked By**: Task 3 (needs FSMBuilder for integration points)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/repositories.py:SessionRepository` (lines 309-367) - Repository protocol to follow
  - `dawn_kestrel/core/repositories.py:SessionRepositoryImpl` (lines 353-...) - Repository implementation pattern
  - `dawn_kestrel/storage/store.py:SessionStorage` (lines 1-...) - Storage layer for repository to wrap

  **Test References** (testing patterns to follow):
  - `tests/core/test_repositories.py:TestSessionRepository::test_create_returns_session` (lines ...-...) - Test patterns for repository operations

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:4. Repository Pattern` (lines 309-401) - Repository pattern specification

  **WHY Each Reference Matters** (explain the relevance):
  - SessionRepository shows existing repository protocol and implementation patterns to follow
  - Storage layer shows how to wrap storage in repository pattern

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Repository module created: dawn_kestrel/core/fsm_state_repository.py
  - [ ] Test covers: get_state returns stored state, set_state saves state, Result pattern for errors
  - [ ] pytest tests/core/test_fsm.py::TestFSMStateRepository::test_get_state_returns_stored_state → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMStateRepository::test_set_state_saves_state → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMStateRepository::test_repository_returns_result_on_error → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSMStateRepository persists and retrieves FSM state
    Tool: Bash (pytest)
    Preconditions: FSMStateRepository implemented in dawn_kestrel/core/fsm_state_repository.py
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMStateRepository::test_get_state_returns_stored_state -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMStateRepository::test_set_state_saves_state -v
      4. Assert: Test passes (PASSED in output)
      5. Run: pytest tests/core/test_fsm.py::TestFSMStateRepository::test_repository_returns_result_on_error -v
      6. Assert: Test passes (PASSED in output)
    Expected Result: FSMStateRepository correctly persists and retrieves FSM state, returns Result for errors
    Failure Indicators: Tests fail with state not persisted or Result not used
    Evidence: pytest output showing all FSMStateRepository tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all FSMStateRepository tests

  **Commit**: YES (groups with 10, 12)
  - Message: `feat(core): implement FSMStateRepository for persistence`
  - Files: dawn_kestrel/core/fsm_state_repository.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMStateRepository`

 - [x] 12. Integrate FSM with DI Container

  **What to do**:
  - Import Container from dawn_kestrel.core.di_container
  - Add FSM provider to Container using providers.Factory
  - Configure FSM provider with dependencies (storage_dir, storage, repository if available)
  - Follow existing DI patterns from dawn_kestrel/core/di_container.py
  - Enable lazy initialization (fsm created only when first accessed)
  - Add FSM-related providers to Container class

  **Must NOT do**:
  - Modify existing providers or break DI configuration
  - Create new container class (extend existing one)
  - Add FSM provider with all features enabled by default (use builder for configuration)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: DI integration requires understanding of providers.Factory and container patterns
  - **Skills**: None needed
    - No external skills required for this DI integration task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10, 11)
  - **Blocked By**: Task 3 (needs FSMBuilder for DI provider configuration)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/di_container.py:Container` (lines 79-99) - Container class to extend
  - `dawn_kestrel/core/di_container.py:providers.Factory` (lines ...-...) - Factory provider pattern for FSM

  **Test References** (testing patterns to follow):
  - `tests/core/test_di_container.py:TestDIContainer::test_container_resolves_services` (lines ...-...) - Test patterns for DI

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:1. Dependency Injection Container` (lines 61-134) - DI Container specification

  **WHY Each Reference Matters** (explain the relevance):
  - Container shows existing provider patterns and configuration to follow
  - Factory provider shows how to add FSM to DI container with lazy initialization

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test covers: FSM provider registered in DI container, FSM instance accessible, dependencies injected
  - [ ] pytest tests/core/test_fsm.py::TestFSMDIIntegration::test_fsm_provider_in_di_container → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMDIIntegration::test_fsm_injects_dependencies → PASS
  - [ ] pytest tests/core/test_fsm.py::TestFSMDIIntegration::test_fsm_lazy_initialization → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: FSM integrated with DI Container, dependencies injected correctly
    Tool: Bash (pytest)
    Preconditions: FSM provider added to dawn_kestrel/core/di_container.py
    Steps:
      1. Run: pytest tests/core/test_fsm.py::TestFSMDIIntegration::test_fsm_provider_in_di_container -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py::TestFSMDIIntegration::test_fsm_injects_dependencies -v
      4. Assert: Test passes (PASSED in output)
      5. Run: pytest tests/core/test_fsm.py::TestFSMDIIntegration::test_fsm_lazy_initialization -v
      6. Assert: Test passes (PASSED in output)
    Expected Result: FSM provider in DI container creates FSMs with injected dependencies, lazy initialization
    Failure Indicators: Tests fail with FSM not in container or dependencies not injected
    Evidence: pytest output showing all DI integration tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all DI integration tests

  **Commit**: YES (groups with 10, 11)
  - Message: `feat(core): integrate FSM with DI Container`
  - Files: dawn_kestrel/core/di_container.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestFSMDIIntegration`

 - [x] 13. Comprehensive Test Suite (tests/core/test_fsm.py)

  **What to do**:
  - Create tests/core/test_fsm.py with comprehensive test coverage
  - Add test classes: TestFSMProtocol, TestFSMImpl, TestFSMBuilder, TestFSMPersistence, TestFSMEvents, TestFSMObserver, TestFSMCommands, TestFSMHooks, TestFSMGuards, TestFSMReliability, TestFSMStateRepository, TestFSMDIIntegration
  - Each test class should cover happy path and error cases
  - Use pytest.mark.asyncio for async tests
  - Use Result pattern assertions (assert result.is_ok(), assert result.error contains)
  - Aim for 80%+ code coverage
  - Follow existing test patterns from tests/core/test_agent_fsm.py
  - Add docstrings to test classes and test methods

  **Must NOT do**:
  - Add manual test instructions or comments
  - Create test runner scripts (use pytest directly)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Test suite creation is straightforward, follows existing patterns
  - **Skills**: None needed
    - No external skills required for this test suite creation task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 14)
  - **Blocked By**: Tasks 10, 11, 12 (need all integrations complete for coverage)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Test References** (existing code to follow):
  - `tests/core/test_agent_fsm.py:TestAgentFSMInitialization` (lines 7-46) - Test patterns for FSM initialization
  - `tests/core/test_agent_fsm.py:TestAgentFSMStateQuery` (lines 49-...) - Test patterns for state queries
  - `tests/core/test_agent_fsm.py:TestAgentFSMTransition` (lines ...-...) - Test patterns for transitions

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:Testing` (lines 1687-1703) - Testing conventions

  **WHY Each Reference Matters** (explain the relevance):
  - Existing test patterns show testing conventions, pytest usage, and Result-based assertions to follow

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test suite created: tests/core/test_fsm.py
  - [ ] Test coverage: 80%+ for dawn_kestrel/core/fsm.py
  - [ ] pytest tests/core/test_fsm.py → All tests PASS
  - [ ] pytest tests/core/test_fsm.py --cov=dawn_kestrel/core/fsm.py --cov-report=term-missing → Coverage 80%+

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: Comprehensive test suite covers all FSM features with 80%+ coverage
    Tool: Bash (pytest)
    Preconditions: tests/core/test_fsm.py created with all test classes
    Steps:
      1. Run: pytest tests/core/test_fsm.py -v
      2. Assert: All tests pass (PASSED in output)
      3. Run: pytest tests/core/test_fsm.py --cov=dawn_kestrel/core/fsm.py --cov-report=term-missing
      4. Assert: Coverage is 80%+ (coverage report shows percentage)
    Expected Result: Test suite covers all FSM features, coverage 80%+ achieved
    Failure Indicators: Tests fail or coverage below 80%
    Evidence: pytest output showing all tests pass, coverage report showing 80%+
  ```

  **Evidence to Capture:**
  - [ ] pytest test results (all tests PASS)
  - [ ] Coverage report (80%+ coverage)

  **Commit**: YES
  - Message: `test(core): add comprehensive test suite for FSM`
  - Files: tests/core/test_fsm.py
  - Pre-commit: `pytest tests/core/test_fsm.py`

 - [x] 14. Integrate FSM with Facade Pattern

  **What to do**:
  - Import Facade protocol from dawn_kestrel.core.facade
  - Add FSM-related methods to Facade protocol (get_fsm_state, create_fsm)
  - Implement methods in FacadeImpl using DI container to get FSM instance
  - Follow existing Facade patterns from dawn_kestrel/core/facade.py
  - Use Result pattern for all facade methods (Ok/Err returns)
  - Add docstrings for public API methods

  **Must NOT do**:
  - Modify existing Facade methods
  - Add FSM visualization or debugging to Facade
  - Directly instantiate FSM (use DI container)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Facade integration is straightforward, follows existing patterns
  - **Skills**: None needed
    - No external skills required for this facade integration task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 13)
  - **Blocked By**: Task 12 (need DI integration for FSM provider)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/facade.py:Facade` (lines 578-589) - Facade protocol to extend
  - `dawn_kestrel/core/facade.py:FacadeImpl` (lines 591-...) - Facade implementation pattern

  **Test References** (testing patterns to follow):
  - `tests/core/test_facade.py:TestFacade::test_facade_simplifies_api` (lines ...-...) - Test patterns for facade

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:7. Facade Pattern` (lines 564-628) - Facade pattern specification

  **WHY Each Reference Matters** (explain the relevance):
  - Facade protocol shows required methods and pattern to follow for FSM integration
  - FacadeImpl shows how to wrap DI container in facade

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Test covers: Facade has FSM methods, FacadeImpl resolves FSM from DI, methods return Result
  - [ ] pytest tests/core/test_facade.py::TestFacade::test_facade_has_fsm_methods → PASS
  - [ ] pytest tests/core/test_facade.py::TestFacade::test_facade_resolves_fsm_from_di → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: Facade exposes FSM operations with simplified API
    Tool: Bash (pytest)
    Preconditions: FSM methods added to Facade protocol and FacadeImpl
    Steps:
      1. Run: pytest tests/core/test_facade.py::TestFacade::test_facade_has_fsm_methods -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/core/test_facade.py::TestFacade::test_facade_resolves_fsm_from_di -v
      4. Assert: Test passes (PASSED in output)
    Expected Result: Facade exposes FSM operations, resolves FSM from DI container
    Failure Indicators: Tests fail with facade methods not available or FSM not resolved
    Evidence: pytest output showing all facade tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all facade tests

  **Commit**: YES (groups with 13, 15)
  - Message: `feat(core): integrate FSM with Facade pattern`
  - Files: dawn_kestrel/core/facade.py
  - Pre-commit: `pytest tests/core/test_facade.py::TestFacade`

 - [x] 15. Migrate AgentRuntime to Use New FSM

  **What to do**:
  - Import FSMBuilder from dawn_kestrel.core.fsm
  - Update AgentRuntime to use FSMBuilder instead of create_agent_fsm()
  - Create FSM via builder with required features:
    - States: idle, running, paused, completed, failed, cancelled
    - Transitions: from VALID_TRANSITIONS in AgentFSMImpl
    - Persistence: via FSMStateRepository
    - Events: via EventMediator
    - Observers: for lifecycle tracking
  - Replace AgentFSMImpl usage in AgentRuntime with new FSM
  - Follow existing AgentRuntime patterns
  - Test AgentRuntime with new FSM (existing tests should still pass)

  **Must NOT do**:
  - Modify FSM protocol or builder (use existing ones)
  - Add new features to AgentRuntime (only migrate FSM usage)
  - Break AgentRuntime API

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Migration requires understanding of AgentRuntime and FSM integration patterns
  - **Skills**: None needed
    - No external skills required for this migration task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Task 16)
  - **Blocked By**: Task 13 (need test suite to verify migration)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/agents/runtime.py:AgentRuntime` (lines 1-...) - AgentRuntime to update
  - `dawn_kestrel/core/agent_fsm.py:create_agent_fsm` (lines 182-199) - Factory function to replace with builder

  **Test References** (testing patterns to follow):
  - `tests/test_agent_runtime.py:TestAgentRuntime::test_agent_transitions_state` (lines ...-...) - Test patterns for AgentRuntime

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:15. State (FSM) Pattern` (lines 1154-1226) - FSM specification for migration

  **WHY Each Reference Matters** (explain the relevance):
  - AgentRuntime shows how FSMs are currently used and need to be migrated
  - create_agent_fsm shows current FSM creation pattern to replace

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] AgentRuntime updated: dawn_kestrel/agents/runtime.py
  - [ ] AgentRuntime uses FSMBuilder instead of create_agent_fsm()
  - [ ] pytest tests/test_agent_runtime.py::TestAgentRuntime::test_agent_transitions_state → PASS
  - [ ] All existing AgentRuntime tests pass with new FSM

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: AgentRuntime migrated to use new FSM, all existing tests pass
    Tool: Bash (pytest)
    Preconditions: AgentRuntime updated to use FSMBuilder
    Steps:
      1. Run: pytest tests/test_agent_runtime.py::TestAgentRuntime::test_agent_transitions_state -v
      2. Assert: Test passes (PASSED in output)
      3. Run: pytest tests/test_agent_runtime.py -v
      4. Assert: All AgentRuntime tests pass (PASSED in output)
    Expected Result: AgentRuntime uses new FSM, all existing tests still pass
    Failure Indicators: Tests fail with migration errors or broken functionality
    Evidence: pytest output showing all AgentRuntime tests pass
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all AgentRuntime tests

  **Commit**: YES (groups with 16, 17)
  - Message: `refactor(agents): migrate AgentRuntime to use new FSM`
  - Files: dawn_kestrel/agents/runtime.py
  - Pre-commit: `pytest tests/test_agent_runtime.py`

 - [x] 16. Deprecate or Remove AgentFSMImpl and ReviewFSMImpl

  **What to do**:
  - Add deprecation warning to AgentFSMImpl.__init__ if keeping (use @deprecated decorator)
  - Add deprecation warning to create_agent_fsm() factory function
  - Add deprecation warning to ReviewFSMImpl in dawn_kestrel/agents/review/fsm_security.py
  - Update import statements to recommend new FSM from dawn_kestrel.core.fsm
  - Document deprecation in docstrings (Use FSMBuilder instead)
  - OR: Remove AgentFSMImpl and ReviewFSMImpl if no existing code depends on them

  **Must NOT do**:
  - Remove tests for deprecated FSMs (if deprecating, tests can remain)
  - Modify deprecated FSMs except adding deprecation warnings
  - Create migration guide (deprecation warnings in docstrings only)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Deprecation is straightforward code addition
  - **Skills**: None needed
    - No external skills required for this deprecation task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Task 15)
  - **Blocked By**: Task 15 (need AgentRuntime migration first)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/agent_fsm.py:AgentFSMImpl` (lines 72-200) - FSM to deprecate
  - `dawn_kestrel/agents/review/fsm_security.py:ReviewFSMImpl` (lines 46-91) - FSM to deprecate
  - `dawn_kestrel/core/decorators.py:log_function` (lines 870-904) - Logging decorator for deprecation warnings

  **Test References** (testing patterns to follow):
  - `tests/core/test_agent_fsm.py:TestAgentFSMInitialization` (lines 7-46) - Test patterns for deprecated FSM

  **Documentation References** (specs and requirements):
  - `docs/patterns.md:Migration Notes` (lines 1651-1686) - Migration patterns

  **WHY Each Reference Matters** (explain the relevance):
  - Existing FSMs show what code needs deprecation warnings
  - Logging decorator shows how to add deprecation warnings

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Deprecation warnings added to AgentFSMImpl and ReviewFSMImpl
  - [ ] Deprecation warning recommends new FSM from dawn_kestrel.core.fsm
  - [ ] pytest tests/core/test_agent_fsm.py::TestDeprecation::test_deprecation_warning_shown → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: AgentFSMImpl and ReviewFSMImpl deprecated with warnings pointing to new FSM
    Tool: Bash (pytest)
    Preconditions: Deprecation warnings added to AgentFSMImpl and ReviewFSMImpl
    Steps:
      1. Run: pytest tests/core/test_agent_fsm.py::TestDeprecation::test_deprecation_warning_shown -v
      2. Assert: Test passes (PASSED in output)
      3. Run: python -c "from dawn_kestrel.core.agent_fsm import AgentFSMImpl; fsm = AgentFSMImpl('idle')"
      4. Assert: DeprecationWarning emitted in output
    Expected Result: AgentFSMImpl and ReviewFSMImpl show deprecation warnings, recommend new FSM
    Failure Indicators: Tests fail or no deprecation warning shown
    Evidence: pytest output showing deprecation tests pass, deprecation warning in stderr
  ```

  **Evidence to Capture:**
  - [ ] pytest test results for all deprecation tests
  - [ ] Deprecation warning output

  **Commit**: YES (groups with 15, 17)
  - Message: `refactor(core): deprecate AgentFSMImpl and ReviewFSMImpl`
  - Files: dawn_kestrel/core/agent_fsm.py, dawn_kestrel/agents/review/fsm_security.py
  - Pre-commit: `pytest tests/core/test_fsm.py::TestDeprecation`

 - [x] 17. Update Documentation (docs/patterns.md)

  **What to do**:
  - Add new section 22: FSM Builder Pattern to docs/patterns.md
  - Document FSM protocol, FSMImpl, FSMBuilder API
  - Document pattern integration (Result, Command, Mediator, Observer, Repository, Reliability, DI, Facade)
  - Add code examples for FSMBuilder usage
  - Document the workflow FSM phases + sub-loop: `intake → plan → act → synthesize → check → done`
  - Document that `plan/act/synthesize/check` loop until stop conditions or intent met; each phase is an LLM prompt
  - (If still applicable) Document migration from AgentFSMImpl to new FSM
  - Add diagram showing FSM Builder pattern
  - Follow existing documentation patterns from docs/patterns.md
  - Update Table of Contents to include new section

  **Must NOT do**:
  - Add tutorial or guide beyond code examples
  - Add migration guide (docstring deprecation only)
  - Add external links or references beyond codebase

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Documentation update is straightforward, follows existing patterns
  - **Skills**: None needed
    - No external skills required for this documentation update task

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final task)
  - **Blocks**: None (can run after all implementation complete)
  - **Blocked By**: Tasks 1-16 (all implementation tasks must complete)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Documentation References** (existing code to follow):
  - `docs/patterns.md:Table of Contents` (lines 5-37) - TOC to update
  - `docs/patterns.md:15. State (FSM) Pattern` (lines 1154-1226) - Section to reference for migration

  **WHY Each Reference Matters** (explain the relevance):
  - TOC shows pattern section structure to follow for new section
  - FSM Pattern section shows existing documentation format to follow

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **TDD (tests enabled):**
  - [ ] Documentation updated: docs/patterns.md
  - [ ] Section 22 added: FSM Builder Pattern
  - [ ] TOC updated to include section 22
  - [ ] Code examples present and correct
  - [ ] Workflow phases documented: `intake → plan → act → synthesize → check → done`
  - [ ] Loop + stop conditions documented (success, stagnation, budgets, human-required, risk)

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: docs/patterns.md updated with FSM Builder Pattern section, TOC updated
    Tool: Bash
    Preconditions: docs/patterns.md updated with FSM Builder Pattern
    Steps:
      1. Run: grep -n "22. FSM Builder Pattern" docs/patterns.md
      2. Assert: Section 22 exists (grep output shows line number)
      3. Run: grep -n "## 22. FSM Builder Pattern" docs/patterns.md
      4. Assert: Section heading exists (grep output shows heading)
      5. Run: grep -n "Table of Contents" docs/patterns.md | head -20
      6. Assert: TOC includes section 22 reference
    Expected Result: docs/patterns.md has FSM Builder Pattern section with code examples, TOC updated
    Failure Indicators: grep fails to find new section or TOC not updated
    Evidence: grep output showing new section exists, TOC line with section 22
  ```

  **Evidence to Capture:**
  - [ ] grep output showing new section exists
  - [ ] grep output showing TOC includes section 22

  **Commit**: YES
  - Message: `docs(patterns): add FSM Builder Pattern documentation`
  - Files: docs/patterns.md
  - Pre-commit: None

 - [x] 18. Add Workflow Phase Contracts (LLM Prompt Outputs)

  **What to do**:
  - Create Pydantic models for each workflow phase output (mirroring `dawn_kestrel/agents/review/contracts.py` style):
    - `IntakeOutput`: intent, constraints, initial evidence snapshot
    - `PlanOutput`: prioritized todo list (create/modify/prioritize), plus rationale
    - `ActOutput`: actions attempted, tool results summary, artifacts/evidence references
    - `SynthesizeOutput`: merged findings + updated todos/statuses
    - `CheckOutput`: `should_continue`, `stop_reason`, `confidence`, `budget_consumed`, `blocking_question` (optional)
  - Provide `get_*_schema()` helpers that return strict JSON schema strings for prompt inclusion (as in `get_review_output_schema()`)
  - Ensure outputs align to canonical stop/loop policy in `docs/planning-agent-orchestration.md` (budgets + stagnation + stop_reason values)
  - Ensure models use `extra="forbid"` (or equivalent) so invalid LLM output fails fast

  **Must NOT do**:
  - Allow unstructured free-text outputs for these phases (must be machine-parseable)
  - Encode prompts in a way that requires human verification

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Contracts define the orchestration API between LLM phases and runtime logic
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: After Tasks 1-3 (can start once FSM module location is settled)
  - **Blocks**: Task 19 (workflow FSM runner depends on contracts)
  - **Blocked By**: Task 1 (core types decisions)

  **References**:
  - `dawn_kestrel/agents/review/contracts.py:ReviewOutput` - Pydantic contract patterns + schema helper function
  - `docs/planning-agent-orchestration.md:Stop Conditions` - stop reasons + budget fields to include
  - `dawn_kestrel/agents/builtin.py:PLAN_ORCHESTRATION_CONTROLS` - canonical stop_reason vocabulary

  **Acceptance Criteria**:
  - [ ] New workflow contract module exists (path decided in implementation)
  - [ ] Schema helpers exist for all five loop phases + intake
  - [ ] pytest includes validation tests ensuring extra fields are rejected and required fields enforced

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Workflow contracts reject invalid LLM output
    Tool: Bash (pytest)
    Preconditions: Workflow Pydantic models + schema helpers implemented
    Steps:
      1. Run: pytest -k "workflow_contract" -v
      2. Assert: All tests pass
    Expected Result: Invalid JSON (missing fields / extra fields) fails validation deterministically
    Evidence: pytest output
  ```

 - [x] 19. Implement Workflow FSM Loop (Intake/Plan/Act/Synthesize/Check/Done)

  **What to do**:
  - Implement a concrete workflow FSM whose states are exactly:
    - `intake`, `plan`, `act`, `synthesize`, `check`, `done`
  - Encode transitions:
    - `intake → plan → act → synthesize → check → plan` (loop)
    - `check → done` when stop conditions hit or intent met
  - Implement the sub-loop controller:
    - In `check`, evaluate stop conditions (success, stagnation, budget, human-required, risk)
    - Enforce hard budgets in code regardless of LLM output
  - Ensure **each phase is an LLM prompt** driven through `AgentRuntime.execute_agent()`:
    - `intake`: prompt extracts intent/constraints
    - `plan`: prompt generates/modifies/prioritizes todos
    - `act`: prompt performs tool-using work against prioritized todos
    - `synthesize`: prompt merges results + updates todo statuses
    - `check`: prompt proposes stop/continue, but runtime enforces budgets
  - Store workflow context across iterations: todos, evidence, iteration count, budgets, last novelty signature
  - Use existing task model (`dawn_kestrel/core/agent_task.py:AgentTask`) as the "todo" substrate (priority can live in `metadata`)
  - Integrate optional delegation via `dawn_kestrel/agents/orchestrator.py:AgentOrchestrator` for parallel Act execution (if desired)

  **Must NOT do**:
  - Build a second tool-execution system; Act must reuse existing tool execution via AgentRuntime/AISession
  - Allow unbounded loops without budget/stagnation guards

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: This is core orchestration logic with stop conditions and phase contracts
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Future integration work and E2E scenarios
  - **Blocked By**: Task 18 (contracts), plus Tasks 1-3 (FSM framework)

  **References**:
  - `dawn_kestrel/agents/runtime.py:AgentRuntime.execute_agent` - canonical way to run an LLM prompt with tools/skills
  - `dawn_kestrel/agents/orchestrator.py:AgentOrchestrator.delegate_task` - optional parallel delegation pattern
  - `dawn_kestrel/core/agent_task.py:AgentTask` - task/todo model to generate/prioritize/track
  - `dawn_kestrel/agents/review/README.md` - existing documented harness loop (Intake/Plan/Act/Synthesize/Evaluate)
  - `docs/planning-agent-orchestration.md` - stop conditions + stagnation detection + budget gates

  **Acceptance Criteria**:
  - [ ] Workflow FSM state machine exists with explicit phase states and valid transitions
  - [ ] `plan/act/synthesize/check` sub-loop repeats until `done`
  - [ ] Budgets enforced: loop stops with `budget_exhausted` when thresholds reached
  - [ ] Stagnation enforced: loop stops or strategy-switch after stagnation thresholds
  - [ ] Deterministic unit tests exist using mocked `AgentRuntime.execute_agent()` phase outputs
  - [ ] `pytest -k "workflow_fsm" -v` passes

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Workflow FSM completes when intent met
    Tool: Bash (pytest)
    Preconditions: Workflow FSM implemented, AgentRuntime mocked to return structured phase outputs
    Steps:
      1. Run: pytest -k "workflow_fsm and success" -v
      2. Assert: Test passes
    Expected Result: Loop enters done with stop_reason=success
    Evidence: pytest output

  Scenario: Workflow FSM stops on budget exhaustion
    Tool: Bash (pytest)
    Preconditions: Budgets configured (max_iterations=2)
    Steps:
      1. Run: pytest -k "workflow_fsm and budget" -v
      2. Assert: Test passes
    Expected Result: Loop enters done with stop_reason=budget_exhausted
    Evidence: pytest output
  ```

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1, 2, 3 | feat(core): add FSM protocol, FSMImpl core, FSMBuilder | dawn_kestrel/core/fsm.py | pytest tests/core/test_fsm.py::TestFSMProtocol + ::TestFSMImpl + ::TestFSMBuilder |
| 4 | feat(core): integrate state persistence via Repository pattern | dawn_kestrel/core/fsm.py, dawn_kestrel/core/fsm_state_repository.py | pytest tests/core/test_fsm.py::TestFSMPersistence |
| 5 | feat(core): integrate event publishing via Mediator pattern | dawn_kestrel/core/fsm.py | pytest tests/core/test_fsm.py::TestFSMEvents |
| 6 | feat(core): integrate Observer pattern for state changes | dawn_kestrel/core/fsm.py | pytest tests/core/test_fsm.py::TestFSMObserver |
| 7 | feat(core): integrate Command-based transitions with audit logging | dawn_kestrel/core/fsm.py | pytest tests/core/test_fsm.py::TestFSMCommands |
| 8 | feat(core): integrate state entry/exit hooks with error handling | dawn_kestrel/core/fsm.py | pytest tests/core/test_fsm.py::TestFSMHooks |
| 9 | feat(core): integrate guard conditions for transition validation | dawn_kestrel/core/fsm.py | pytest tests/core/test_fsm.py::TestFSMGuards |
| 10 | feat(core): integrate reliability wrappers for external actions | dawn_kestrel/core/fsm.py | pytest tests/core/test_fsm.py::TestFSMReliability |
| 11 | feat(core): implement FSMStateRepository for persistence | dawn_kestrel/core/fsm_state_repository.py | pytest tests/core/test_fsm.py::TestFSMStateRepository |
| 12 | feat(core): integrate FSM with DI Container | dawn_kestrel/core/di_container.py | pytest tests/core/test_fsm.py::TestFSMDIIntegration |
| 13 | test(core): add comprehensive test suite for FSM | tests/core/test_fsm.py | pytest tests/core/test_fsm.py (coverage 80%+) |
| 14 | feat(core): integrate FSM with Facade pattern | dawn_kestrel/core/facade.py | pytest tests/core/test_facade.py::TestFacade |
| 15 | refactor(agents): migrate AgentRuntime to use new FSM | dawn_kestrel/agents/runtime.py | pytest tests/test_agent_runtime.py |
| 16 | refactor(core): deprecate AgentFSMImpl and ReviewFSMImpl | dawn_kestrel/core/agent_fsm.py, dawn_kestrel/agents/review/fsm_security.py | pytest tests/core/test_fsm.py::TestDeprecation |
| 17 | docs(patterns): add FSM Builder Pattern documentation | docs/patterns.md | grep docs/patterns.md for new section |
| 18 | feat(workflow): add workflow phase contracts | dawn_kestrel/agents/workflow/contracts.py | pytest -k workflow_contract -v |
| 19 | feat(workflow): implement workflow FSM loop phases | dawn_kestrel/agents/workflow/fsm.py | pytest -k workflow_fsm -v |

---

## Success Criteria

### Verification Commands
```bash
# Run all FSM tests
pytest tests/core/test_fsm.py -v

# Check test coverage
pytest tests/core/test_fsm.py --cov=dawn_kestrel/core/fsm.py --cov-report=term-missing

# Run AgentRuntime tests (verify migration)
pytest tests/test_agent_runtime.py -v

# Run Facade tests
pytest tests/core/test_facade.py::TestFacade -v

# Run workflow loop contract + FSM tests
pytest -k "workflow_contract" -v
pytest -k "workflow_fsm" -v

# Verify documentation updated
grep -n "22. FSM Builder Pattern" docs/patterns.md
grep -n "## 22. FSM Builder Pattern" docs/patterns.md
grep -n "intake" docs/patterns.md
```

### Final Checklist
- [x] FSM protocol and FSMImpl with all requested features implemented
- [x] FSMBuilder with fluent API (10-15 methods) implemented
- [x] State persistence via FSMStateRepository integrated
- [x] Event publishing via EventMediator integrated
- [x] Observer support integrated
- [x] Command-based transitions with audit logging integrated
- [x] State entry/exit hooks integrated (log and continue on error)
- [x] Guard conditions integrated
- [x] Reliability wrappers (Circuit Breaker, Retry, Rate Limiter, Bulkhead) for external actions integrated
- [x] FSM integrated with DI Container
- [x] FSM integrated with Facade pattern
- [x] AgentRuntime migrated to use new FSM
- [x] AgentFSMImpl and ReviewFSMImpl deprecated
- [x] Workflow FSM implemented with explicit phase states: `intake`, `plan`, `act`, `synthesize`, `check`, `done`
- [x] Workflow sub-loop implemented: `plan → act → synthesize → check` repeats until stop conditions or intent met
- [x] Each workflow phase executed via LLM prompt; Act is tool-using phase
- [x] Workflow stop conditions enforced (success, stagnation, budgets, human-required, risk)
- [x] All tests passing (pytest tests/core/test_fsm.py, tests/test_agent_runtime.py, tests/core/test_facade.py)
- [x] Test coverage 80%+ for dawn_kestrel/core/fsm.py
- [x] Documentation updated (docs/patterns.md section 22)
- [x] Workflow FSM documented: `intake → plan → act → synthesize → check → done` + sub-loop semantics
- [x] All 12 relevant patterns integrated (Result, Command, Mediator, Observer, Repository, Circuit Breaker, Retry, Rate Limiter, Bulkhead, Facade, DI Container)
- [x] NO thread safety added (matches existing patterns)
- [x] NO hierarchical states, visualization, debugging tools added
- [x] NO undo/redo capability (audit logging only)
- [x] Builder has 10-15 methods max
- [x] Flat state model with string identifiers
