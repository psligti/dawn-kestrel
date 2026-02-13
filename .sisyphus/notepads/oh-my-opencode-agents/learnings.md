# Learnings: oh-my-opencode-agents

## AgentConfig Implementation (2026-02-12)

### TDD Approach
- Wrote failing test FIRST before implementing - confirmed import error `ModuleNotFoundError: No module named 'dawn_kestrel.agents.agent_config'`
- Test failure before implementation validated the TDD cycle correctly

### Implementation Patterns
- Used `@dataclass` with `field(default_factory=dict)` for mutable default arguments (metadata field)
- `from_agent()` factory method provides clean API for wrapping existing Agent instances
- Wrapper pattern (not modification) maintains backward compatibility with existing Agent dataclass

### Code Organization
- Module docstring clearly explains the wrapper pattern purpose
- Class docstring documents attributes and design intent
- Method docstring includes Args, Returns, and Example sections for public API

### Type Annotations
- `Optional[FSM]` for optional state machine references
- `dict[str, Any]` for metadata (explicit typing over bare `dict`)
- Import `Any` from typing for flexible metadata values

### Testing
- Created 4 comprehensive tests covering:
  1. Basic creation from Agent (default values)
  2. Creation with FSMs and metadata
  3. Metadata default to empty dict
  4. FSMs are optional (None by default)
- All tests passed successfully

### LSP Diagnostics
- Initial warnings about dict type arguments resolved by using `dict[str, Any]`
- Final state: No diagnostics on agent_config.py or test_agent_config.py

### Dependencies
- dawn_kestrel.agents.builtin.Agent - the dataclass being wrapped
- dawn_kestrel.core.fsm.FSM - protocol for state machine references
- dawn_kestrel.core.result.Result - pattern for type-safe returns (imported but not used directly in AgentConfig)


## AgentWorkflowFSM Implementation (2026-02-12)

### TDD Approach
- Wrote comprehensive failing tests FIRST before implementation
- Test failures validated TDD cycle correctly (import errors)
- Tests verified all 6 states and 7 transitions work correctly

### Implementation Patterns
- Used FSMBuilder fluent API to create FSM (no new FSM class needed)
- `_create_entry_hook()` helper creates logging functions with closure
- Simple state constants as strings (INTAKE, PLAN, ACT, SYNTHESIZE, CHECK, DONE)
- Factory function `create_workflow_fsm()` returns `Result[FSM]` from `builder.build()`

### Code Organization
- Module docstring explains FSM states, transitions, and the key LOOP feature
- Function docstrings document Args, Returns with clear examples
- State and transition comments in builder chain clarify structure

### FSM Transitions
- Linear flow: intake → plan → act → synthesize → check
- LOOP transition: check → plan (continue iteration)
- Exit transition: check → done (stop conditions met)
- Reset transition: done → intake (reset for next task)
- Invalid transitions fail as expected

### Type Checker Limitations
- Type checker doesn't understand flow analysis for `if result.is_err():`
- Accessing `result.error` after `is_err()` check causes type error
- Solution: Use `# type: ignore[unreachable]` comments in test code
- Pattern: `if result.is_err(): pytest.fail(f"...: {result.error}")  # type: ignore[unreachable]`

### Testing
- Created 9 comprehensive tests covering:
  1. All states defined and initial state is intake
  2. Linear flow works (intake → plan → act → synthesize → check)
  3. Loop transition works (check → plan)
  4. Exit transition works (check → done)
  5. Reset transition works (done → intake)
  6. Invalid transitions fail (tested from each actual state)
  7. Multiple iterations through workflow loop
  8. All valid transitions verified
  9. Entry hooks execute without errors
- All tests passed successfully

### LSP Diagnostics
- Initial errors from module not existing (expected during TDD)
- Type checker errors on `result.error` after flow analysis - resolved with type ignore comments
- Final state: No diagnostics on agent_workflow_fsm.py or test_agent_workflow_fsm.py

### Dependencies
- dawn_kestrel.core.fsm.FSMBuilder - fluent API builder
- dawn_kestrel.core.fsm.FSM - protocol for state machine
- dawn_kestrel.core.result.Result, Ok - pattern for type-safe returns
- logging - for entry hooks

### Key Difference from WorkflowFSM
- AgentWorkflowFSM is SIMPLE: just states and transitions, no LLM execution
- WorkflowFSM in workflow_fsm.py is FULL: includes LLM execution, budget tracking, etc.
- This simple FSM provides the foundation that WorkflowFSM builds upon

## AgentBuilder Implementation (2026-02-12)

### TDD Approach
- Wrote 6 failing tests FIRST before implementing AgentBuilder class
- Tests verified method chaining, validation, and defaults before implementation existed
- All 6 tests passed after implementation

### Implementation Patterns
- Followed FSMBuilder fluent API pattern from core/fsm.py
- Private fields with underscore prefix: `_name`, `_description`, etc.
- All fluent methods return `self` for method chaining
- `build()` validates required fields before creating AgentConfig
- Uses `# type: ignore[arg-type]` for validated Optional fields

### Fluent API Methods
- **Required fields**: `.with_name()`, `.with_description()`, `.with_mode()`, `.with_permission()`
- **Optional fields**: `.with_prompt()`, `.with_temperature()`, `.with_options()`, `.with_native()`
- All methods return `AgentBuilder` for chaining

### Validation
- Validates required fields in `build()` method
- Returns `Err` with descriptive error message listing missing fields
- Error code: `"MISSING_REQUIRED_FIELDS"`
- Clear error messages help debugging

### Type Safety Challenges
- Type checker doesn't follow control flow validation
- After `if self._name is None:` check, type checker still thinks it's Optional
- Solution: `# type: ignore[arg-type]` comments after validation
- Comment explains why type ignore is used (validated above)

### Testing Patterns
- **Method chaining test**: Verify each fluent method returns `self`
- **Full configuration test**: Verify AgentConfig has correct values
- **Required fields test**: Verify each required field individually causes error when missing
- **Defaults test**: Verify optional fields have correct Agent dataclass defaults
- **Permission test**: Verify multiple permission rules handled
- **Override test**: Verify default values can be overridden

### Test Coverage
- 6 comprehensive tests covering:
  1. Method chaining works
  2. Creates valid AgentConfig with all fields
  3. Fails without required fields (tested each individually)
  4. Optional fields have correct defaults
  5. Handles multiple permission rules
  6. Can override default field values

### Result Pattern Usage
- `build()` returns `Result[AgentConfig]`
- Success: `Ok(AgentConfig(agent=...))`
- Failure: `Err(error="...", code="MISSING_REQUIRED_FIELDS")`
- Tests use `result.is_ok()`, `result.is_err()`, `result.unwrap()`
- Accessing `result.error` requires `cast(Any, result)` for type checker

### Code Organization
- Module docstring explains builder purpose and fluent API
- Class docstring documents all builder methods and validation behavior
- Each method has Args, Returns, and Example sections
- Build method docstring includes validation rules

### Dependencies
- dawn_kestrel.agents.builtin.Agent - dataclass being wrapped
- dawn_kestrel.agents.agent_config.AgentConfig - wrapper class
- dawn_kestrel.core.result.Result, Ok, Err - pattern for type-safe returns

### Code Coverage
- AgentConfig now at 98% coverage (67 lines total, only 1 miss)
- AgentBuilder fully covered by 6 tests


## AgentBuilder FSM Integration (2026-02-12)

### TDD Approach
- Wrote 5 failing tests FIRST for FSM integration methods
- All tests failed with `AttributeError: 'AgentBuilder' object has no attribute 'with_lifecycle_fsm'`
- Confirmed TDD cycle: failing tests → implementation → all tests pass
- Test class: `TestAgentBuilderFSM` with 5 comprehensive tests

### Implementation Patterns
- Added private fields `_lifecycle_fsm` and `_workflow_fsm` to `AgentBuilder.__init__`
- All fluent methods return `self` for method chaining (consistent with existing API)
- `with_default_fsms()` creates FSMs using factory functions, returns `AgentBuilder` for chaining
- `build()` updated to pass FSMs to `AgentConfig` constructor
- Error handling in `with_default_fsms()` silently ignores creation failures (FSMs remain None)

### Fluent API Methods Added
- **`with_lifecycle_fsm(fsm: FSM)`** - Attach custom lifecycle FSM
- **`with_workflow_fsm(fsm: FSM)`** - Attach custom workflow FSM
- **`with_default_fsms()`** - Create and attach default lifecycle + workflow FSMs

### Error Handling Decision
- Initial design: `with_default_fsms()` should return `Result[AgentBuilder]` to propagate errors
- Final design: Returns `AgentBuilder` directly for fluent API consistency
- If FSM creation fails, FSM fields remain None (no error propagation from fluent method)
- This maintains the pattern where only `build()` returns `Result[T]`

### Testing
- Created 5 comprehensive tests:
  1. `test_with_lifecycle_fsm_attaches_fsm` - Verifies lifecycle FSM attachment
  2. `test_with_workflow_fsm_attaches_fsm` - Verifies workflow FSM attachment
  3. `test_with_default_fsms_creates_and_attaches_both_fsms` - Verifies default FSM creation
  4. `test_fsm_methods_support_chaining` - Verifies method chaining works
  5. `test_build_returns_agent_config_with_fsms_attached` - Verifies FSMs in final config
- All 5 new tests pass
- All 10 existing tests still pass (total 15 tests in test_agent_config.py)

### Code Coverage
- AgentConfig coverage increased from 65% → 100% (80 lines total, 0 misses)
- All new FSM methods fully covered by tests
- No LSP diagnostics on agent_config.py after implementation

### Dependencies
- dawn_kestrel.agents.agent_lifecycle_fsm.create_lifecycle_fsm - factory for lifecycle FSM
- dawn_kestrel.agents.agent_workflow_fsm.create_workflow_fsm - factory for workflow FSM
- dawn_kestrel.core.fsm.FSM - protocol for state machine references

### Key Design Decisions
- FSMs are optional (default to None) - maintains backward compatibility
- Factory functions imported locally in `with_default_fsms()` to avoid circular imports
- Error handling is minimal in fluent methods to maintain chaining
- All FSM attachment happens through the builder pattern, not directly in AgentConfig


## Planner Agent Update to AgentBuilder (2026-02-12)

### Task Overview
- Updated `dawn_kestrel/agents/bolt_merlin/planner/__init__.py` to use AgentBuilder
- Replaced direct `Agent()` instantiation with fluent AgentBuilder API
- Added `.with_default_fsms()` for FSM integration

### Implementation Changes

**Import Changes:**
- Old: `from dawn_kestrel.agents.builtin import Agent`
- New: `from dawn_kestrel.agents.agent_config import AgentBuilder, AgentConfig`

**Function Changes:**
- Old: `return Agent(name="planner", ...)`
- New: `return AgentBuilder().with_name("planner")... .build()`

**New Method Chain:**
- `.with_name("planner")`
- `.with_description(...)`
- `.with_mode("subagent")`
- `.with_permission([...])` (4 deny rules unchanged)
- `.with_native(True)` (explicitly set, was in Agent dataclass)
- `.with_default_fsms()` (NEW - creates both lifecycle and workflow FSMs)
- `.with_prompt(PLANNER_PROMPT)` (unchanged)
- `.with_temperature(0.2)` (unchanged)
- `.with_options({...})` (unchanged)
- `.build()` - returns `Result[AgentConfig]`

### Verification
- ✅ Function returns `Result[AgentConfig]` (type: `Ok`)
- ✅ `config.agent.name` = "planner"
- ✅ `config.agent.mode` = "subagent"
- ✅ `config.agent.native` = True
- ✅ `config.agent.temperature` = 0.2
- ✅ All 4 permission rules unchanged
- ✅ PLANNER_PROMPT content unchanged
- ✅ Lifecycle FSM attached (not None)
- ✅ Workflow FSM attached (not None)
- ✅ No LSP diagnostics on planner/__init__.py

### LSP Diagnostics
- Initial LSP warnings about import resolution (false positives)
- Python imports work correctly (`python3 -c` verification)
- Final state: No diagnostics on the modified file

### Patterns Observed
- AgentBuilder maintains exact same values as original Agent configuration
- `.with_native()` is required when original Agent had `native=True`
- `.with_default_fsms()` automatically creates and attaches both FSMs
- Fluent API chaining works cleanly without syntax errors
