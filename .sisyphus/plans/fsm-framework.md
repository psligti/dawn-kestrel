# General-Purpose FSM Framework with Thinking Traces

## TL;DR

> **Quick Summary**: Create a reusable finite state machine framework in dawn_kestrel/workflow/ that emits structured "thinking traces" at each state transition, with both console and JSON output.
>
> **Deliverables**:
> - `dawn_kestrel/workflow/__init__.py` - Main exports
> - `dawn_kestrel/workflow/models.py` - ThinkingStep, ThinkingFrame, RunLog, StructuredContext
> - `dawn_kestrel/workflow/fsm.py` - State machine with transition validation
> - `dawn_kestrel/workflow/loggers.py` - Console and JSON loggers
> - `dawn_kestrel/workflow/example.py` - Example workflow with toy state handlers
> - `tests/workflow/` - Unit tests for all components
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: models → fsm → loggers → example + tests

---

## Context

### Original Request
Create a general-purpose finite state machine framework based on the security FSM example, with:
- States: intake → plan_todos → delegate → collect → consolidate → evaluate → done
- Structured thinking traces (ThinkingStep, ThinkingFrame, RunLog models)
- Console and JSON output for thinking logs
- Location: dawn_kestrel/workflow/
- Reusable for any workflow (not domain-specific)

### Interview Summary
**Key Discussions**:
- Use security FSM states (intake, plan_todos, delegate, collect, consolidate, evaluate, done)
- JSON output: Return value only (no file writing)
- Context model: StructuredContext as Pydantic BaseModel (typed, extensible)
- Include unit tests following dawn_kestrel patterns
- Framework should be general-purpose, domain-agnostic

**Research Findings**:
- Dawn Kestrel uses Pydantic extensively for data models
- Tests organized under tests/ with subdirectories matching dawn_kestrel structure
- Existing logging patterns in the codebase (event_bus, etc.)

---

## Work Objectives

### Core Objective
Create a reusable finite state machine framework that models multi-step workflows with structured thinking traces.

### Concrete Deliverables
- `dawn_kestrel/workflow/__init__.py` - Package initialization with exports
- `dawn_kestrel/workflow/models.py` - Pydantic models for thinking traces and context
- `dawn_kestrel/workflow/fsm.py` - State machine with transition validation and runner
- `dawn_kestrel/workflow/loggers.py` - Console and JSON loggers
- `dawn_kestrel/workflow/example.py` - Example workflow demonstrating usage
- `tests/workflow/test_models.py` - Unit tests for models
- `tests/workflow/test_fsm.py` - Unit tests for state machine
- `tests/workflow/test_loggers.py` - Unit tests for loggers

### Definition of Done
- [ ] All files created under dawn_kestrel/workflow/
- [ ] All tests pass: `pytest tests/workflow/ -v`
- [ ] Example runs with DYNAMIC thinking (not static strings)
- [ ] Thinking traces show TODO decisions, text synthesis, consolidation, user guidance
- [ ] Thinking includes concrete evidence references (file paths, tool outputs)
- [ ] JSON export captures full thinking with evidence links
- [ ] Type checking passes: `mypy dawn_kestrel/workflow/`
- [ ] Documentation in docstrings for public APIs
- [ ] Example demonstrates how thinking could be used for git commits or agent memory

### Must Have
- Pydantic models for ThinkingStep, ThinkingFrame, RunLog, StructuredContext
- State machine with transition validation (enforce allowed transitions)
- Console logger with human-readable format
- JSON logger that returns structured JSON string
- Example workflow with DYNAMIC handlers (not static strings)
  - Thinking reflects TODO list decisions, text synthesis, consolidation, user guidance
  - Evidence references are concrete (file paths, tool outputs, subagent IDs)
- Unit tests for all components
- Demonstration of how thinking could be captured for git commits or agent memory

### Must NOT Have (Guardrails)
- Domain-specific state handlers (example only, user creates their own)
- Static thinking strings (must be dynamic based on actual work)
- File writing for JSON logs (return value only)
- Over-engineering beyond example's simplicity
- Integration with specific dawn_kestrel components (keep it general)
- Long monologues in thinking steps (keep 1-3 brief steps per frame)
- Vague evidence references (must use concrete: file paths, tool outputs, subagent IDs)

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.

### Test Decision
- **Infrastructure exists**: YES (pytest framework in dawn_kestrel)
- **Automated tests**: YES (Tests-after - write tests after implementation)
- **Framework**: pytest

### Test Setup

Tests follow dawn_kestrel's existing patterns:
- Use `pytest` for test framework
- Place tests in `tests/workflow/` mirroring `dawn_kestrel/workflow/`
- Use `tests/conftest.py` patterns for fixtures if needed
- Verify with: `pytest tests/workflow/ -v`

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

**Scenario: Example workflow runs successfully with both loggers**
  Tool: Bash
  Preconditions: dawn_kestrel workflow module created
  Steps:
    1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
    2. python -c "from dawn_kestrel.workflow import run_workflow_fsm; ctx = run_workflow_fsm(['file1.py', 'file2.py']); print('State:', ctx.state); print('Frames:', len(ctx.log.frames))"
    3. Assert: exit code is 0
    4. Assert: output contains "State: done"
    5. Assert: output contains "Frames: 6" (or expected count)
    6. Assert: console output shows "== intake ==", "== plan_todos ==", etc.
  Expected Result: Workflow completes, shows console output for each state
  Evidence: Terminal output captured

**Scenario: JSON logger returns valid JSON**
  Tool: Bash
  Preconditions: dawn_kestrel workflow module created
  Steps:
    1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
    2. python -c "from dawn_kestrel.workflow import run_workflow_fsm; import json; ctx = run_workflow_fsm(['file1.py']); json_output = ctx.log.to_json(); parsed = json.loads(json_output); print('Keys:', list(parsed.keys())); print('Frame count:', len(parsed['frames']))"
    3. Assert: exit code is 0
    4. Assert: parsed is a dict
    5. Assert: parsed contains 'frames' key
    6. Assert: len(parsed['frames']) > 0
    7. Assert: each frame has 'state', 'ts', 'goals', 'steps', 'decision'
  Expected Result: JSON output is valid and contains expected structure
  Evidence: Terminal output captured

**Scenario: Invalid transition raises error**
  Tool: Bash
  Preconditions: dawn_kestrel workflow module created
  Steps:
    1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
    2. python -c "from dawn_kestrel.workflow import WorkflowContext, assert_transition; assert_transition('intake', 'evaluate')"
    3. Assert: exit code is 1 (or non-zero)
    4. Assert: stderr contains "Invalid transition"
  Expected Result: Invalid transition raises ValueError
  Evidence: Terminal output captured

**Scenario: All unit tests pass**
  Tool: Bash
  Preconditions: tests/workflow/ created
  Steps:
    1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
    2. pytest tests/workflow/ -v --tb=short
    3. Assert: exit code is 0
    4. Assert: output contains "passed"
    5. Assert: no failures or errors
  Expected Result: All tests pass
  Evidence: Terminal output captured

**Evidence to Capture:**
- [ ] Terminal output for all scenarios
- [ ] JSON output validation results

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Create models.py (thinking trace models + context)
└── Task 2: Create loggers.py (console + JSON loggers)

Wave 2 (After Wave 1):
├── Task 3: Create fsm.py (state machine + transition validation)
├── Task 4: Create example.py (demo workflow with toy handlers)
└── Task 5: Create __init__.py (package exports)

Wave 3 (After Wave 2):
├── Task 6: Create test_models.py (unit tests for models)
├── Task 7: Create test_fsm.py (unit tests for state machine)
└── Task 8: Create test_loggers.py (unit tests for loggers)

Critical Path: Task 1 → Task 3 → Task 4 → Tests
Parallel Speedup: ~30% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 3, 6 | 2 |
| 2 | None | 3, 8 | 1 |
| 3 | 1, 2 | 4, 7 | None (after Wave 1) |
| 4 | 3 | None (demo) | 5, 6, 7, 8 |
| 5 | 3 | None (exports) | 4, 6, 7, 8 |
| 6 | 1 | None | 7, 8 |
| 7 | 3 | None | 6, 8 |
| 8 | 2 | None | 6, 7 |

---

## TODOs

- [ ] 1. Create models.py with thinking trace and context models

  **What to do**:
  - Create `dawn_kestrel/workflow/models.py`
  - Define: `Confidence` Literal ("low", "medium", "high")
  - Define: `DecisionType` Literal ("transition", "tool", "delegate", "gate", "stop")
  - Define: `ThinkingStep` (kind, why, evidence, next, confidence)
  - Define: `ThinkingFrame` (state, ts, goals, checks, risks, steps, decision)
  - Define: `RunLog` (frames list with add() method and to_json() method)
  - Define: `Todo` (id, title, rationale, evidence)
  - Define: `StructuredContext` (state, changed_files, todos, subagent_results, consolidated, evaluation, log)
  - All models inherit from Pydantic BaseModel
  - Add docstrings for all public classes and methods

  **Must NOT do**:
  - Domain-specific fields beyond the example
  - Over-complicate models with unnecessary features

  **Recommended Agent Profile**:
  > - **Category**: `unspecified-low` (straightforward model definitions)
    - Reason: Simple Pydantic model creation, no complex logic
  - **Skills**: `[]` (no specialized skills needed)
  - **Skills Evaluated but Omitted**:
    - None - task is straightforward

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Tasks 3, 6
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/models.py` - Pydantic model patterns and structure
  - `dawn_kestrel/agents/review/fsm_security.py:1-100` - Example thinking trace models (if exists)

  **API/Type References** (contracts to implement against):
  - User's example code - models structure, field types, validation requirements

  **Test References** (testing patterns to follow):
  - `tests/core/test_models.py` - How to test Pydantic models

  **Documentation References** (specs and requirements):
  - User's example code - exact model structure from their specification

  **External References** (libraries and frameworks):
  - Pydantic docs: https://docs.pydantic.dev/ - BaseModel usage, field types

  **WHY Each Reference Matters** (explain the relevance):
  - `dawn_kestrel/core/models.py` - Shows how dawn_kestrel structures Pydantic models (imports, base classes, field patterns)
  - User's example - Exact contract to implement: field names, types, methods required

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  Scenario: Models import without errors
    Tool: Bash
    Preconditions: models.py created
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "from dawn_kestrel.workflow.models import ThinkingStep, ThinkingFrame, RunLog, Todo, StructuredContext; print('Import successful')"
      3. Assert: exit code is 0
      4. Assert: output contains "Import successful"
    Expected Result: All models import successfully
    Evidence: Terminal output captured

  Scenario: StructuredContext instantiates with default values
    Tool: Bash
    Preconditions: models.py created
    Steps:
      1. python -c "from dawn_kestrel.workflow.models import StructuredContext; ctx = StructuredContext(); print('State:', ctx.state); print('Log type:', type(ctx.log).__name__)"
      2. Assert: exit code is 0
      3. Assert: ctx.state equals "intake" (default)
      4. Assert: type(ctx.log).__name__ equals "RunLog"
    Expected Result: Context creates with proper defaults
    Evidence: Terminal output captured

  Scenario: ThinkingStep validates with required fields
    Tool: Bash
    Preconditions: models.py created
    Steps:
      1. python -c "from dawn_kestrel.workflow.models import ThinkingStep; step = ThinkingStep(kind='transition', why='Test reason', next='done'); print('Created:', step.kind, step.confidence)"
      2. Assert: exit code is 0
      3. Assert: step.kind equals "transition"
      4. Assert: step.confidence equals "medium" (default)
      5. python -c "from dawn_kestrel.workflow.models import ThinkingStep; step = ThinkingStep(); print(step)"
      6. Assert: exit code is 1 (validation error - missing required fields)
    Expected Result: Step validates required fields, uses sensible defaults
    Evidence: Terminal output captured

  Scenario: RunLog.to_json() returns valid JSON
    Tool: Bash
    Preconditions: models.py created
    Steps:
      1. python -c "from dawn_kestrel.workflow.models import ThinkingFrame, RunLog; import json; log = RunLog(); log.add(ThinkingFrame(state='test')); json_out = log.to_json(); parsed = json.loads(json_out); print('Valid JSON:', 'frames' in parsed)"
      2. Assert: exit code is 0
      3. Assert: parsed is a dict
      4. Assert: 'frames' in parsed
      5. Assert: len(parsed['frames']) == 1
    Expected Result: RunLog.to_json() returns valid JSON string
    Evidence: Terminal output captured

  **Evidence to Capture**:
  - [ ] Terminal output for all scenarios

  **Commit**: NO (wait for Wave 2 completion)

- [ ] 2. Create loggers.py with console and JSON loggers

  **What to do**:
  - Create `dawn_kestrel/workflow/loggers.py`
  - Define: `ConsoleLogger` class with `log_frame()` method
    - Format: "== {state} ==", each step with kind/why/next/confidence/evidence
  - Define: `JsonLogger` class (or use RunLog.to_json())
    - Return JSON string for the full log
  - Console logger should print human-readable output
  - JSON logger should return structured JSON (return value, no file write)
  - Add docstrings for logger classes and methods

  **Must NOT do**:
  - File writing for JSON logs (return value only)
  - Complex logging infrastructure beyond the example's simplicity

  **Recommended Agent Profile**:
  > - **Category**: `unspecified-low` (simple logger implementations)
    - Reason: Straightforward formatting and output, no complex logic
  - **Skills**: `[]` (no specialized skills needed)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Tasks 3, 8
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/observer.py` - Notification/output patterns if applicable
  - User's example - Console output format: "== {state} ==", step formatting

  **API/Type References** (contracts to implement against):
  - User's example: Console format from print statements in example runner

  **Test References** (testing patterns to follow):
  - `tests/core/test_observer.py` - How to test output/notification classes (if exists)

  **WHY Each Reference Matters**:
  - User's example shows exact console format needed
  - JSON requirement: return value only, not file write

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  Scenario: ConsoleLogger formats frame correctly
    Tool: Bash
    Preconditions: loggers.py created, models.py exists
    Steps:
      1. python -c "from dawn_kestrel.workflow.models import ThinkingFrame, ThinkingStep; from dawn_kestrel.workflow.loggers import ConsoleLogger; frame = ThinkingFrame(state='test', steps=[ThinkingStep(kind='transition', why='Test', next='done')]); ConsoleLogger().log_frame(frame)"
      2. Assert: exit code is 0
      3. Assert: stdout contains "== test =="
      4. Assert: stdout contains "[transition]"
      5. Assert: stdout contains "Test"
    Expected Result: Console output matches expected format
    Evidence: Terminal output captured

  Scenario: JsonLogger returns valid JSON string
    Tool: Bash
    Preconditions: loggers.py created, models.py exists
    Steps:
      1. python -c "from dawn_kestrel.workflow.models import ThinkingFrame, RunLog; from dawn_kestrel.workflow.loggers import JsonLogger; import json; log = RunLog(); log.add(ThinkingFrame(state='test')); json_out = JsonLogger().log(log); parsed = json.loads(json_out); print('Type:', type(parsed).__name__, 'Has frames:', 'frames' in parsed)"
      2. Assert: exit code is 0
      3. Assert: type(json_out).__name__ == 'str'
      4. Assert: parsed is a dict
      5. Assert: 'frames' in parsed
    Expected Result: JSON logger returns string, not writes to file
    Evidence: Terminal output captured

  **Evidence to Capture**:
  - [ ] Terminal output for all scenarios

  **Commit**: NO (wait for Wave 2 completion)

- [ ] 3. Create fsm.py with state machine and transition validation

  **What to do**:
  - Create `dawn_kestrel/workflow/fsm.py`
  - Define: `WORKFLOW_FSM_TRANSITIONS` dict (same as security example)
    - intake → plan_todos
    - plan_todos → delegate
    - delegate → collect, consolidate, evaluate, done
    - collect → consolidate
    - consolidate → evaluate
    - evaluate → done
  - Define: `assert_transition()` function (validates state transitions)
  - Define: State handler functions (intake, plan_todos, delegate, collect, consolidate, evaluate)
    - Each returns next state string
    - Each builds and adds ThinkingFrame to context
  - Define: `run_workflow_fsm()` function (runner, calls handlers in loop until done)
  - Add docstrings for all functions
  - Import models and loggers from workflow modules

   **Must NOT do**:
   - Add real business logic to handlers (but use dynamic thinking, not static strings)
   - Modify transition graph from the example

  **Recommended Agent Profile**:
  > - **Category**: `unspecified-low` (state machine logic)
    - Reason: Straightforward state machine with toy handlers
  - **Skills**: `[]` (no specialized skills needed)

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after Wave 1)
  - **Blocks**: Tasks 4, 7
  - **Blocked By**: Tasks 1, 2

  **References** (CRITICAL - Be Exhaustive):

   **Pattern References** (existing code to follow):
   - `dawn_kestrel/agents/review/fsm_security.py` - FSM implementation (if exists)
   - User's example - Exact state handler structure and logic
   - User's new requirement: State handlers must generate DYNAMIC thinking (not static strings)

   **API/Type References** (contracts to implement against):
   - User's example code - HANDLERS dict, assert_transition, run_security_fsm

   **WHY Each Reference Matters**:
   - User's example is the contract to implement exactly
   - Dynamic thinking requirement means state handlers analyze actual input and vary output accordingly

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  Scenario: assert_transition validates allowed transitions
    Tool: Bash
    Preconditions: fsm.py created
    Steps:
      1. python -c "from dawn_kestrel.workflow.fsm import assert_transition; assert_transition('intake', 'plan_todos'); print('Valid: OK')"
      2. Assert: exit code is 0
      3. Assert: output contains "Valid: OK"
      4. python -c "from dawn_kestrel.workflow.fsm import assert_transition; assert_transition('intake', 'done')"
      5. Assert: exit code is 1
      6. Assert: stderr contains "Invalid transition"
    Expected Result: Valid transitions pass, invalid raise error
    Evidence: Terminal output captured

  Scenario: run_workflow_fsm executes all states
    Tool: Bash
    Preconditions: fsm.py created
    Steps:
      1. python -c "from dawn_kestrel.workflow.fsm import run_workflow_fsm; ctx = run_workflow_fsm(['test.py']); print('Final state:', ctx.state); print('Frames:', len(ctx.log.frames))"
      2. Assert: exit code is 0
      3. Assert: ctx.state equals "done"
      4. Assert: len(ctx.log.frames) >= 5 (intake, plan_todos, delegate, collect, consolidate, evaluate)
      5. Assert: all(frame.state for frame in ctx.log.frames)
    Expected Result: FSM runs through all states to done
    Evidence: Terminal output captured

  Scenario: State handlers create thinking frames
    Tool: Bash
    Preconditions: fsm.py created
    Steps:
      1. python -c "from dawn_kestrel.workflow.fsm import run_workflow_fsm; ctx = run_workflow_fsm(['test.py']); first_frame = ctx.log.frames[0]; print('First state:', first_frame.state); print('Has goals:', len(first_frame.goals) > 0); print('Has steps:', len(first_frame.steps) > 0); print('Has decision:', len(first_frame.decision) > 0)"
      2. Assert: exit code is 0
      3. Assert: first_frame.state equals "intake"
      4. Assert: len(first_frame.goals) > 0
      5. Assert: len(first_frame.steps) > 0
      6. Assert: len(first_frame.decision) > 0
    Expected Result: Each state handler creates a proper ThinkingFrame
    Evidence: Terminal output captured

  **Evidence to Capture**:
  - [ ] Terminal output for all scenarios

  **Commit**: NO (wait for Wave 2 completion)

- [ ] 4. Create example.py with REAL dynamic thinking workflow

  **What to do**:
  - Create `dawn_kestrel/workflow/example.py`
  - Implement example workflow using `run_workflow_fsm()`
  - Add console logger integration to show thinking traces
  - Add JSON logger integration to show structured output
  - Include if __name__ == "__main__": block for direct execution
  - **CRITICAL**: State handlers must generate DYNAMIC thinking that reflects:
    - TODO list decisions (what was added, why, evidence links)
    - Text synthesis activities (what was read, what was concluded)
    - Consolidation process (combining findings, resolving conflicts)
    - User guidance (what to do next, what was completed)
    - User intention and next steps to take
  - Use concrete evidence references (file paths, tool outputs, subagent IDs)
  - Example should demonstrate:
    - Workflow running through all states with REAL thinking
    - Dynamic thinking that changes based on input (not static strings)
    - Console output for each state showing live reasoning
    - JSON export of full trace with evidence links
    - How thinking can be captured for git commits or agent memory
  - Add docstring explaining the example and dynamic thinking approach

  **Must NOT do**:
  - Use static pre-defined thinking strings (must be dynamic based on actual work)
  - Over-complicate the example, but keep it realistic

  **Recommended Agent Profile**:
  > - **Category**: `unspecified-low` (simple example)
    - Reason: Demonstration code, no complex logic
  - **Skills**: `[]` (no specialized skills needed)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7, 8)
  - **Blocks**: None (demo)
  - **Blocked By**: Tasks 1, 2, 3

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - User's example - Exact console output format from their if __name__ == "__main__": block
  - User's new requirement: Dynamic thinking with TODO decisions, text synthesis, consolidation, user guidance
  - Evidence reference format: "diff:file1", "tool:grep#2", "subagent:T1"

  **WHY Each Reference Matters**:
  - User's example shows the expected output format to replicate
  - Dynamic thinking requirement means state handlers must analyze actual input, not return static strings

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  Scenario: Example runs with DYNAMIC thinking
    Tool: Bash
    Preconditions: example.py created
    Steps:
      1. python dawn_kestrel/workflow/example.py
      2. Assert: exit code is 0
      3. Assert: stdout contains "== intake =="
      4. Assert: stdout contains "== plan_todos =="
      5. Assert: stdout contains "== delegate =="
      6. Assert: stdout contains "Decision:"
      7. Assert: stdout contains evidence references (file paths like "file1.py", or "diff:", or "tool:")
    Expected Result: Example runs with dynamic console thinking
    Evidence: Terminal output captured

  Scenario: Example shows JSON export with evidence
    Tool: Bash
    Preconditions: example.py created
    Steps:
      1. python -c "from dawn_kestrel.workflow.example import run_example; ctx = run_example(['test.py']); import json; json_out = ctx.log.to_json(); parsed = json.loads(json_out); first_frame = parsed['frames'][0]; print('Has steps:', 'steps' in first_frame); print('Has evidence:', any(s.get('evidence') for s in first_frame.get('steps', [])))"
      2. Assert: exit code is 0
      3. Assert: first_frame contains 'steps' key
      4. Assert: at least one step has 'evidence' field with references
    Expected Result: JSON export contains thinking with evidence links
    Evidence: Terminal output captured

  Scenario: Dynamic thinking varies based on input
    Tool: Bash
    Preconditions: example.py created
    Steps:
      1. python -c "from dawn_kestrel.workflow.example import run_example; ctx1 = run_example(['file1.py']); ctx2 = run_example(['file1.py', 'file2.py', 'file3.py']); print('Single file steps:', len(ctx1.log.frames[1].steps)); print('Multiple files steps:', len(ctx2.log.frames[1].steps))"
      2. Assert: exit code is 0
      3. Assert: len(ctx1.log.frames[1].steps) > 0
      4. Assert: len(ctx2.log.frames[1].steps) > 0
      5. Assert: thinking steps differ between single vs multiple files (check different evidence or counts)
    Expected Result: Thinking adapts to input (not static)
    Evidence: Terminal output captured

  **Evidence to Capture**:
  - [ ] Terminal output for all scenarios

  **Commit**: NO (wait for Wave 2 completion)

- [ ] 5. Create __init__.py with package exports

  **What to do**:
  - Create `dawn_kestrel/workflow/__init__.py`
  - Export main classes and functions:
    - From models: ThinkingStep, ThinkingFrame, RunLog, Todo, StructuredContext
    - From fsm: assert_transition, run_workflow_fsm, state handlers (if useful)
    - From loggers: ConsoleLogger, JsonLogger
  - Add package docstring explaining the workflow framework
  - Ensure imports are clean and don't cause circular deps

  **Must NOT do**:
  - Export internal/helper functions
  - Create complex initialization logic

  **Recommended Agent Profile**:
  > - **Category**: `unspecified-low` (simple package init)
    - Reason: Straightforward imports and exports
  - **Skills**: `[]` (no specialized skills needed)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6, 7, 8)
  - **Blocks**: None (exports)
  - **Blocked By**: Tasks 1, 2, 3

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/__init__.py` - Import/export patterns for dawn_kestrel package
  - `dawn_kestrel/core/__init__.py` - Core module export patterns

  **WHY Each Reference Matters**:
  - Shows how dawn_kestrel structures package exports

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  Scenario: Package imports work correctly
    Tool: Bash
    Preconditions: __init__.py created
    Steps:
      1. python -c "from dawn_kestrel.workflow import ThinkingStep, ThinkingFrame, RunLog, StructuredContext, assert_transition, run_workflow_fsm, ConsoleLogger, JsonLogger; print('All exports available')"
      2. Assert: exit code is 0
      3. Assert: output contains "All exports available"
    Expected Result: All public exports import correctly
    Evidence: Terminal output captured

  Scenario: Package docstring exists
    Tool: Bash
    Preconditions: __init__.py created
    Steps:
      1. python -c "import dawn_kestrel.workflow as wf; print('Has docstring:', wf.__doc__ is not None); print('Docstring length:', len(wf.__doc__) if wf.__doc__ else 0)"
      2. Assert: exit code is 0
      3. Assert: wf.__doc__ is not None
      4. Assert: len(wf.__doc__) > 20
    Expected Result: Package has descriptive docstring
    Evidence: Terminal output captured

  **Evidence to Capture**:
  - [ ] Terminal output for all scenarios

  **Commit**: NO (wait for all Wave 2 tasks, then commit together)

- [ ] 6. Create test_models.py for model unit tests

  **What to do**:
  - Create `tests/workflow/test_models.py`
  - Test ThinkingStep:
    - Validates required fields
    - Uses default values for optional fields
    - Serializes/deserializes correctly
  - Test ThinkingFrame:
    - Creates with all fields
    - Validates timestamp format
    - Serializes/deserializes correctly
  - Test RunLog:
    - add() method adds frames correctly
    - to_json() returns valid JSON
    - JSON contains all expected fields
  - Test StructuredContext:
    - Creates with default state="intake"
    - Initializes empty collections
    - Contains log instance
  - Use pytest fixtures for common test data
  - Follow dawn_kestrel test patterns

  **Must NOT do**:
  - Skip testing edge cases (empty fields, invalid types)
  - Over-test (focus on critical functionality)

  **Recommended Agent Profile**:
  > - **Category**: `unspecified-low` (unit tests for models)
    - Reason: Standard Pydantic model testing
  - **Skills**: `[]` (no specialized skills needed)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 7, 8)
  - **Blocks**: None (tests)
  - **Blocked By**: Task 1

  **References** (CRITICAL - Be Exhaustive):

  **Test References** (testing patterns to follow):
  - `tests/core/test_models.py` - How dawn_kestrel tests Pydantic models
  - `tests/conftest.py` - Fixture patterns

  **WHY Each Reference Matters**:
  - Shows dawn_kestrel's testing conventions

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  Scenario: All model tests pass
    Tool: Bash
    Preconditions: test_models.py created
    Steps:
      1. pytest tests/workflow/test_models.py -v
      2. Assert: exit code is 0
      3. Assert: output contains "passed"
      4. Assert: no failures or errors in output
    Expected Result: All model tests pass
    Evidence: Terminal output captured

  **Evidence to Capture**:
  - [ ] Terminal output for pytest run

  **Commit**: NO (wait for all Wave 3 tasks, then commit together)

- [ ] 7. Create test_fsm.py for state machine unit tests

  **What to do**:
  - Create `tests/workflow/test_fsm.py`
  - Test assert_transition():
    - Valid transitions pass
    - Invalid transitions raise ValueError with error message
  - Test individual state handlers:
    - Each returns correct next state
    - Each adds ThinkingFrame to context log
    - Frames have goals, steps, decision
  - Test run_workflow_fsm():
    - Runs through all states to "done"
    - Creates correct number of frames
    - Context state ends at "done"
  - Test edge cases:
    - Empty changed_files list
    - Single changed file
    - Multiple changed files
  - Use pytest fixtures for common test contexts

  **Must NOT do**:
  - Skip testing invalid transitions
  - Skip testing frame creation in handlers

  **Recommended Agent Profile**:
  > - **Category**: `unspecified-low` (unit tests for FSM)
    - Reason: Standard state machine testing
  - **Skills**: `[]` (no specialized skills needed)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6, 8)
  - **Blocks**: None (tests)
  - **Blocked By**: Task 3

  **References** (CRITICAL - Be Exhaustive):

  **Test References** (testing patterns to follow):
  - `tests/agents/` - FSM testing patterns if exists
  - `tests/core/test_commands.py` - State machine/command testing patterns

  **WHY Each Reference Matters**:
  - Shows dawn_kestrel's testing conventions for state machines

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  Scenario: All FSM tests pass
    Tool: Bash
    Preconditions: test_fsm.py created
    Steps:
      1. pytest tests/workflow/test_fsm.py -v
      2. Assert: exit code is 0
      3. Assert: output contains "passed"
      4. Assert: no failures or errors in output
    Expected Result: All FSM tests pass
    Evidence: Terminal output captured

  **Evidence to Capture**:
  - [ ] Terminal output for pytest run

  **Commit**: NO (wait for all Wave 3 tasks, then commit together)

- [ ] 8. Create test_loggers.py for logger unit tests

  **What to do**:
  - Create `tests/workflow/test_loggers.py`
  - Test ConsoleLogger:
    - log_frame() prints to stdout
    - Output contains state name
    - Output contains step details
  - Test JsonLogger:
    - log() returns JSON string (not writes file)
    - JSON is valid (json.loads() succeeds)
    - JSON contains all frame fields
  - Test with sample ThinkingFrame data
  - Use pytest fixtures for common test data
  - Use capsys or similar to capture stdout

  **Must NOT do**:
  - Test file writing (not required)
  - Skip testing JSON validity

  **Recommended Agent Profile**:
  > - **Category**: `unspecified-low` (unit tests for loggers)
    - Reason: Standard logger testing
  - **Skills**: `[]` (no specialized skills needed)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6, 7)
  - **Blocks**: None (tests)
  - **Blocked By**: Task 2

  **References** (CRITICAL - Be Exhaustive):

  **Test References** (testing patterns to follow):
  - `tests/core/test_observer.py` - How to test output/notification classes (if exists)
  - `tests/conftest.py` - Fixture patterns

  **WHY Each Reference Matters**:
  - Shows dawn_kestrel's testing conventions for output classes

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  Scenario: All logger tests pass
    Tool: Bash
    Preconditions: test_loggers.py created
    Steps:
      1. pytest tests/workflow/test_loggers.py -v
      2. Assert: exit code is 0
      3. Assert: output contains "passed"
      4. Assert: no failures or errors in output
    Expected Result: All logger tests pass
    Evidence: Terminal output captured

  **Evidence to Capture**:
  - [ ] Terminal output for pytest run

  **Commit**: NO (wait for all Wave 3 tasks, then commit together)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1-3 (Wave 1-2) | `feat(workflow): add FSM framework with thinking traces` | workflow/models.py, workflow/fsm.py, workflow/loggers.py | pytest tests/workflow/ |
| 4-5 (Wave 2) | `feat(workflow): add example and package exports` | workflow/example.py, workflow/__init__.py | python workflow/example.py |
| 6-8 (Wave 3) | `test(workflow): add unit tests for workflow framework` | tests/workflow/*.py | pytest tests/workflow/ |

---

## Success Criteria

### Verification Commands
```bash
# Run all workflow tests
pytest tests/workflow/ -v
# Expected: all pass

# Run example workflow
python dawn_kestrel/workflow/example.py
# Expected: shows console output for each state

# Import from package
python -c "from dawn_kestrel.workflow import run_workflow_fsm; ctx = run_workflow_fsm(['test.py']); print('Done:', ctx.state == 'done')"
# Expected: Done: True

# Type checking
mypy dawn_kestrel/workflow/
# Expected: no errors (or only non-blocking ones)
```

### Final Checklist
- [ ] All files created under dawn_kestrel/workflow/
- [ ] All files created under tests/workflow/
- [ ] All tests pass (pytest)
- [ ] Example runs with console output
- [ ] JSON export returns valid JSON string
- [ ] Package exports work correctly
- [ ] Type checking passes
- [ ] Documentation in docstrings
