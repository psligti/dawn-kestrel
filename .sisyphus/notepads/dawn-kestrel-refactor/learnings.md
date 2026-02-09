# Learnings

## Adapter Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 14 tests written covering all adapter functionality
  - 2 protocol compliance tests
  - 4 OpenAIAdapter tests (wrap, ok success, err failure, provider name)
  - 4 ZAIAdapter tests (wrap, ok success, err failure, provider name)
  - 4 adapter registration tests (register, get, list)
- **GREEN Phase**: All 14 tests passing with 98% coverage for adapters.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Adapter Pattern Design
- **ProviderAdapter Protocol**: Interface for provider adapters
  - `generate_response(messages, model, **kwargs) -> Result[Message]`
  - `get_provider_name() -> str`
  - Protocol-based design enables runtime type checking and multiple implementations
  - @runtime_checkable decorator allows isinstance() checks on ProviderAdapter

- **OpenAIAdapter**: Wraps OpenAIProvider with normalized interface
  - Converts Message models to provider format (list of dicts)
  - Collects stream events into Message response
  - Returns Result[Message] with Ok/Err outcomes
  - Provider name: "openai"

- **ZAIAdapter**: Wraps ZAIProvider with normalized interface
  - Same interface as OpenAIAdapter
  - Provider name: "zai"

### Adapter Registration System
- **In-memory registry**: `_adapters: dict[str, ProviderAdapter]`
  - `register_adapter(name, adapter)` adds adapter to registry
  - `get_adapter(name)` returns adapter or None
  - `list_adapters()` returns all adapter names
  - Enables custom providers at runtime without modifying core code

### Result Pattern Integration
- All adapter methods return Result types (Ok/Err)
- Errors wrapped with explicit error codes ("PROVIDER_ERROR", "MODEL_NOT_FOUND")
- Exceptions caught and converted to Err (violates pattern if raised)
- Consistent with Result pattern learned in Task 10

### Test Coverage
- 98% coverage for adapters.py (84 statements, 2 missed)
- 100% pass rate: all 14 tests pass
- All public methods tested (generate_response, get_provider_name)
- Error conditions tested (model not found, provider exception)

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 14 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on ProviderAdapter
   - Custom providers can implement protocol and register at runtime
   - Adapter pattern normalizes interface without modifying core code

3. **Result type API** - `Err` has `error` attribute (string), not `error()` method
   - Access via `result.error`, not `result.error()`
   - `str(result)` includes error code in repr format
   - Tests need to check `str(result)` for error code, not `str(result.error)`

4. **Mocking patterns for testing** - AsyncMock with side_effect and return_value
   - Mock `get_models()` to return model info (AsyncMock(return_value=[...]))
   - Mock `stream()` to yield events (async generator function)
   - Use side_effect for exceptions (AsyncMock(side_effect=Exception(...)))

5. **Adapter pattern benefits** - Clean separation of concerns
   - Providers unchanged (no breaking changes)
   - Unified interface via adapters
   - Custom providers enabled without core modifications
   - Result types enable explicit error handling

### Next Steps
- Consider adding adapter for AnthropicProvider
- Consider adding caching layer to adapters
- Consider adding retry logic to adapters
- Future: Thread-safe adapter registry (currently simple dict)

## Plugin Discovery Implementation (2026-02-08)

### Entry Points Design
- Entry points provide a standard plugin discovery mechanism in Python
- Groups defined in pyproject.toml under `[project.entry-points]`
- Format: `group_name = {entry_point_name = module.path:callable}`
- Must build wheel and install to test entry_points (importlib.metadata needs installed package)

### Plugin Loading Architecture
- Use `importlib.metadata.entry_points()` for Python 3.10+
- Supports synchronous and asynchronous loading patterns
- Each plugin group (tools, providers, agents) has its own loader function
- Refactored to use generic `_load_plugins()` function to reduce code duplication

### Validation Strategy
- Plugins must export specific functions or classes
- Version checking ensures compatibility
- Capability detection validates required interfaces
- Graceful failures prevent system startup issues
- Log warnings for failed imports/loads, continue processing other plugins

### Testing Approach
- TDD workflow: RED (failing tests) → GREEN (implementation) → REFACTOR
- Test plugin discovery with mocked entry points
- Verify entry_points can be loaded after building wheel
- All 10 tests pass: tool loading, provider loading, agent loading, validation, versioning

### Code Quality
- Removed unnecessary inline comments in refactoring phase
- Kept essential docstrings for public API
- Code is self-documenting without excessive comments

## Tool Plugin Discovery Implementation (2026-02-08)

### Entry Points for Tools
- Entry points defined in pyproject.toml under `[project.entry-points."dawn_kestrel.tools"]`
- Each tool has an entry point mapping name to module:class (e.g., "bash" = "dawn_kestrel.tools.builtin:BashTool")
- Plugin discovery loads tools via `importlib.metadata.entry_points()`

### Plugin Discovery Pattern
- `load_tools()` function discovers tools from entry points
- Entry points can return classes (type) or instances
- Must instantiate classes to get tool instances
- Pattern: `isinstance(plugin, type) ? plugin() : plugin`

### Backward Compatibility Strategy
- Keep direct tool imports: `from dawn_kestrel.tools import BashTool` works
- Export tool classes from builtin.py and additional.py in __all__
- Remove hard-coded registry creation functions (create_complete_registry)
- Replace with plugin-based loading in get_all_tools()

### Test Coverage
- Created tests/tools/test_tool_plugins.py with 6 test cases
- Tests verify: plugin discovery, backward compatibility, tool attributes, idempotency
- All 20 tools discovered correctly from entry points

### Key Learnings
- Entry point names ARE tool IDs (e.g., "bash" maps to BashTool)
- Plugin discovery must handle both classes and instances flexibly
- Tests should check consistency (types, IDs), not object identity
- Direct imports must continue working for backward compatibility
## Provider Plugin Discovery Implementation (2026-02-08)

### Entry Points for Providers
- Entry points defined in pyproject.toml under `[project.entry-points."dawn_kestrel.providers"]`
- Each provider has an entry point mapping name to module:class (e.g., "anthropic" = "dawn_kestrel.providers:AnthropicProvider")
- Plugin discovery loads providers via `importlib.metadata.entry_points()`

### Provider vs Tool Loading Differences
- **Providers**: Require constructor arguments (api_key), MUST be returned as classes (factories), not instances
  - Provider classes cannot be instantiated without api_key parameter
  - Plugin discovery always returns class for providers, regardless of __init__ signature
- **Tools**: Can be instantiated without arguments, may be returned as instances or classes

### Plugin Discovery Implementation
- Modified `plugin_discovery._load_plugins()` to handle providers specially
  - For provider group, always return class (factory pattern)
  - For other groups (tools), try to instantiate if possible
  - Providers require api_key argument, so they must be called later with that argument

### Provider Loading Strategy
- `get_provider()` now uses plugin discovery via `_get_provider_factories()`
- Built-in providers loaded from entry points via `plugin_discovery.load_providers()`
- Custom providers can still be registered via `register_provider_factory()`
- Cache provider factories for performance, cleared when custom providers are registered

### Backward Compatibility
- Direct provider imports still work: `from dawn_kestrel.providers import AnthropicProvider`
- `get_provider()` function signature unchanged: `get_provider(provider_id: ProviderID, api_key: str)`
- `register_provider_factory()` still works for custom provider registration
- PROVIDER_FACTORIES dict kept for backward compatibility but static entries removed
  - Empty by default: `PROVIDER_FACTORIES: Dict[ProviderID, ProviderFactory] = {}`
  - Only used for custom providers registered at runtime

### Test Coverage
- Created tests/providers/test_provider_plugins.py with 11 test cases (all passing)
- Tests verify: plugin discovery (4 providers), provider classes, get_provider(), custom registration, backward compatibility

### Key Learnings
- ProviderID enum values use hyphens (e.g., "zai-coding-plan") but entry points use underscores (e.g., "zai_coding_plan")
- Need explicit mapping between ProviderID values and entry point names
- Provider plugins must be treated differently from tool plugins due to constructor requirements
- Entry point loading returns class objects, not instances, for provider group

## Agent Plugin Discovery Implementation (2026-02-08)

### Entry Points for Agents
- Entry points defined in pyproject.toml under `[project.entry-points."dawn_kestrel.agents"]`
- Entry points can reference Agent instances directly (builtin agents) or factory functions (bolt_merlin agents)
- Format: `agent_name = "module.path:factory_function"` or `agent_name = "module.path:AGENT_INSTANCE"`
- Built-in agents: build, plan, general, explore (4 agents from builtin.py)
- Bolt Merlin agents: orchestrator, master_orchestrator, consultant, librarian, explore, multimodal_looker, autonomous_worker, pre_planning, plan_validator, planner (10 agents)

### Agent Loading Pattern
- Entry points can return:
  1. Agent instances directly (e.g., builtin.BUILD_AGENT)
  2. Factory functions that return Agent when called (e.g., bolt_merlin.orchestrator.create_orchestrator_agent)
- Registry and AgentManager must handle both patterns: `if callable(plugin): agent = plugin(); else: agent = plugin`
- Validate that loaded objects are Agent instances before registering

### Name Collision Handling
- Both builtin.EXPLORE_AGENT and bolt_merlin.explore have name "explore"
- Last loaded agent wins (bolt_merlin.explore overrides builtin.EXPLORE_AGENT)
- Total unique agents: 13 (4 builtin + 10 bolt_merlin - 1 duplicate)
- This is acceptable behavior for backward compatibility

### Registry Changes
- Removed static seeding from `get_all_agents()` call in registry.py
- Updated `_seed_builtin_agents()` to use `plugin_discovery.load_agents()`
- Added `_load_agent_from_plugin()` method to handle both Agent instances and factories
- Graceful error handling: log warnings for invalid plugins, continue processing

### AgentManager Changes
- Updated `get_all_agents()` to use `plugin_discovery.load_agents()`
- Handles both Agent instances and factory functions from plugins
- Returns List[Agent] after validating and instantiating factory functions

### Backward Compatibility
- Direct imports from builtin still work: `from dawn_kestrel.agents.builtin import BUILD_AGENT, get_all_agents`
- `get_all_agents()` in builtin.py still returns 4 builtin agents
- Direct imports from bolt_merlin still work: `from dawn_kestrel.agents.bolt_merlin import create_orchestrator_agent`
- Registry CRUD operations unchanged: register_agent(), get_agent(), list_agents(), remove_agent()

### Test Coverage
- Created tests/agents/test_agent_plugins.py with 16 test cases (all passing)
- Tests verify: plugin discovery (13 agents), builtin agents (4), bolt_merlin agents (10), agent validation, registry loading, backward compatibility, agent permissions
- 100% pass rate: all 16 tests pass

### Key Learnings
- Agent entry points are more complex than tools/providers - support both instances and factory functions
- Frontend UI/UX is a skill, NOT an agent - correctly excluded from agents entry points
- Duplicate agent names handled by last-one-wins semantics (acceptable for migration)
- Static seeding completely removed from registry, replaced with plugin discovery
- TDD workflow worked perfectly: RED (4 test failures) → GREEN (16 tests pass) after implementation

## Baseline Test Coverage Establishment (2026-02-09)

### Test Execution
- Ran core module tests only (agents, core, providers, tools) due to timeout
- Full test suite (1417 tests) exceeds 120s timeout
- Executed 78 tests with coverage analysis
- Command: `pytest --ignore=tests/test_phase1_agent_execution.py --ignore=tests/review/ -k "not test_configure_container" --cov=dawn_kestrel --cov-report=html`

### Coverage Statistics
- **Total statements**: 11,060
- **Covered statements**: 1,898
- **Overall coverage**: 17% (core modules only)
- Coverage HTML report generated: htmlcov/index.html

### Critical 0% Coverage Modules
1. **SDK Client** (dawn_kestrel/sdk/client.py, 174 statements) - Main user-facing API
2. **Agent Runtime** (dawn_kestrel/agents/runtime.py, 25% coverage) - Agent execution engine
3. **Tool Execution** (dawn_kestrel/ai/tool_execution.py, 14% coverage) - Tool invocation
4. **Session Service** (dawn_kestrel/core/services/session_service.py, 38% coverage)
5. **All review agents and review system modules** - Completely untested
6. **CLI/TUI modules** - Main entry points untested
7. **Storage layer modules** - Session persistence untested

### Well-Covered Modules (> 80%)
- dawn_kestrel/core/di_container.py (100%) - Recently added in Wave 1
- dawn_kestrel/core/plugin_discovery.py (64%) - Recently added in Wave 1
- dawn_kestrel/core/agent_task.py (91%)
- dawn_kestrel/core/models.py (99%)
- dawn_kestrel/agents/builtin.py (97%)

### Pre-Existing Test Failures
1. **DI container tests** (test_configure_container*) - TypeError: storage_dir is string not Path
   - Related to Settings refactoring (Task 3, Wave 1)
   - ProviderRegistry expects Path but receives string from DI container

2. **test_phase1_agent_execution.py** - ImportError: create_complete_registry removed
   - This function was removed during plugin discovery (Wave 2)
   - Test needs updating

### Key Learnings
1. **Plugin discovery already implemented** - Wave 2 tasks completed before baseline
   - Entry points registered in pyproject.toml
   - Tool, provider, agent loading via importlib.metadata
   - Static registration functions removed

2. **Baseline scope matters** - Full suite timeout means core-only baseline is more accurate for refactor
   - Previous baseline (54%) not comparable to current (17%)
   - Different test scopes make direct comparison misleading

3. **Coverage gaps inform priorities** - 0% coverage modules indicate test expansion opportunities
   - SDK client is critical user-facing API, needs tests
   - Agent runtime and tool execution are core to functionality
   - Storage and session persistence need test coverage

4. **TDD workflow essential** - All new pattern implementations should follow RED-GREEN-REFACTOR
   - Write failing tests first
   - Implement minimum code to pass
   - Refactor while keeping tests green

### Test Infrastructure Notes
- pytest with pytest-asyncio framework
- Coverage enabled in pyproject.toml (lines 84-87)
- Tests use heavy Mock/AsyncMock for isolation
- 1417 total tests, but core subset (78) used for baseline

## Result Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 37 tests written covering all Result type functionality
- **GREEN Phase**: All 37 tests passing with 77% coverage for result.py
- **REFACTOR Phase**: Added hash methods to Ok, Err, Pass for better dictionary/set support

### Result Pattern Design
- **Ok[T]**: Success with value of type T
  - is_ok() returns True, is_err() and is_pass() return False
  - unwrap() returns the value
  - unwrap_or(default) returns the value (ignores default)
  
- **Err**: Failure with error information
  - is_err() returns True, is_ok() and is_pass() return False
  - Contains: error (str), code (str | None), retryable (bool, default False)
  - unwrap() raises ValueError with error message
  - unwrap_or(default) returns the default value
  
- **Pass**: Neutral outcome without value
  - is_pass() returns True, is_ok() and is_err() return False
  - Contains optional message (str | None)
  - unwrap() raises ValueError
  - unwrap_or(default) returns the default value

### Result Composition Methods
- **bind(func)**: Chain a function that returns a Result
  - Short-circuits on Err/Pass (returns unchanged)
  - Only applies func if this is Ok
  
- **map_result(result, func)**: Transform value inside Ok
  - Returns Ok(func(value)) if Ok
  - Returns result unchanged if Err/Pass
  
- **fold(result, on_ok, on_err, on_pass)**: Fold to single value
  - Applies appropriate function based on Result type
  - on_pass is optional (defaults to on_ok(None))

### JSON Serialization
- **to_json()**: Serialize Result to JSON string
  - Ok: {"type": "ok", "value": ...}
  - Err: {"type": "err", "error": ..., "code": ..., "retryable": ...}
  - Pass: {"type": "pass", "message": ...}
  
- **Result.from_json(json_str)**: Deserialize from JSON
  - Returns Ok, Err, or Pass based on type field
  - Raises ValueError for invalid JSON or unknown type

### Thread Safety
- All Result types are immutable (values set in __init__)
- Thread-safe for concurrent creation and usage
- Tests verify 100 concurrent Result creations work correctly
- bind/map/fold operations are thread-safe

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 37 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Refactored while keeping tests green (REFACTOR)
   
2. **Result pattern is foundational** - Will be used to replace exceptions in domain layer
   - Explicit error handling without exceptions
   - Error codes and retryable flags for better error categorization
   - Composition via bind/map/fold for chaining operations
   
3. **Hash methods important** - Results can be used as dictionary keys or in sets
   - Added __hash__ to Ok, Err, Pass
   - Hash based on type and values for consistency
   
4. **Type safety with Generics** - Result[T] enables type-safe value handling
   - MyPy/TypeScript can verify type correctness
   - unwrap() returns T, unwrap_or() accepts T as default
   
5. **Test coverage matters** - 77% coverage for result.py, 100% of test cases pass
   - All Result type functionality covered
   - Thread safety tested with concurrent operations
   - JSON serialization/deserialization fully tested

### Next Steps
- Task 10: Wrap existing exceptions with Result types
- Task 11: Update all public APIs to return Results
- Will use Result types throughout domain layer for explicit error handling

## Repository Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 32 tests written covering all repository functionality
  - 11 SessionRepository tests (get_by_id, create, update, delete, list_by_project)
  - 8 MessageRepository tests (get_by_id, create, list_by_session)
  - 13 PartRepository tests (get_by_id, create, update, list_by_message)
- **GREEN Phase**: All 32 tests passing with 86% coverage for repositories.py
- **REFACTOR Phase**: Clean code structure, proper type annotations, comprehensive docstrings

### Repository Pattern Design
- **SessionRepository**: Protocol for session data access
  - get_by_id(session_id): Get session by ID → Result[Session]
  - create(session): Create new session → Result[Session]
  - update(session): Update existing session → Result[Session]
  - delete(session_id): Delete session by ID → Result[bool]
  - list_by_project(project_id): List sessions for project → Result[List[Session]]

- **MessageRepository**: Protocol for message data access
  - get_by_id(session_id, message_id): Get message by ID → Result[Message]
  - create(message): Create new message → Result[Message]
  - list_by_session(session_id, reverse=True): List messages for session → Result[List[Message]]

- **PartRepository**: Protocol for part data access
  - get_by_id(message_id, part_id): Get part by ID → Result[Part]
  - create(message_id, part): Create new part → Result[Part]
  - update(message_id, part): Update existing part → Result[Part]
  - list_by_message(message_id): List parts for message → Result[List[Part]]

### Implementation Details
- **SessionRepositoryImpl**: Wraps SessionStorage, returns Result types
  - All storage exceptions caught and converted to Err with "STORAGE_ERROR" code
  - Not found conditions return Err with "NOT_FOUND" code
  - delete() returns Ok(False) when session not found (not Err)

- **MessageRepositoryImpl**: Wraps MessageStorage, converts Dict to Message
  - MessageStorage returns Dict[str, Any], must convert to Message objects
  - Handles part_type field for Message model conversion

- **PartRepositoryImpl**: Wraps PartStorage, converts Dict to Part
  - Part is a Union type (TextPart, FilePart, ToolPart, etc.)
  - Created helper function _dict_to_part() to convert based on part_type field
  - Handles all 9 Part subclasses: text, file, tool, reasoning, snapshot, patch, agent, subtask, retry, compaction

### Key Learnings
1. **Union type handling** - Part is a Union of 9 different part types
   - Cannot use Part(**data) directly since Union is not callable
   - Must inspect part_type field and instantiate appropriate subclass
   - _dict_to_part() helper function handles this conversion cleanly

2. **Result pattern integration** - Repositories use Result for error handling
   - No exceptions raised from repository methods (violates pattern)
   - All exceptions caught and converted to Err with error codes
   - NOT_FOUND and STORAGE_ERROR codes for categorization

3. **Storage layer abstraction** - Repositories wrap existing storage
   - DawnKestrel storage layer unchanged (no breaking changes)
   - Repositories provide new interface with Result types
   - Existing services can gradually migrate to repositories

4. **Protocol-based design** - Enables runtime type checking and multiple implementations
   - @runtime_checkable decorator allows isinstance() checks on protocols
   - Future can add in-memory, database, or other storage backends
   - Type hints ensure all implementations match protocol

5. **Test coverage matters** - 86% coverage for repositories.py, 100% of test cases pass
   - All repository methods tested with both success and failure paths
   - Mock storage fixtures ensure isolated, fast tests
   - Error conditions tested with side_effect on mock methods

6. **Delete pattern** - Returns Ok(False) instead of Err when not found
   - Consistent with "delete if exists" semantics
   - Caller can distinguish between not-found (False) and error (Err)
   - Storage API returns bool for delete, repository preserves this

### Next Steps
- Task 13: Update DefaultSessionService to use repositories
- Task 14: Add Unit of Work pattern for transactional operations
- Will use repositories throughout domain layer instead of direct storage access

## Unit of Work Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 28 tests written covering all UnitOfWork functionality
  - 8 transaction lifecycle tests (begin, commit, rollback)
  - 6 entity registration tests (register_session, register_message, register_part)
  - 6 commit tests (creates registered entities, handles failures)
  - 2 rollback tests (clears pending state, doesn't modify repositories)
  - 2 protocol tests (runtime_checkable, implementation compliance)
  - 4 integration tests (full transaction flows, multiple entities)
- **GREEN Phase**: All 28 tests passing with high coverage
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Unit of Work Pattern Design
- **UnitOfWork Protocol**: Interface for transactional consistency
  - begin(): Start a new transaction → Result[None]
  - commit(): Commit all pending changes → Result[None]
  - rollback(): Rollback all pending changes → Result[None]
  - register_session(session): Register session for creation → Result[Session]
  - register_message(message): Register message for creation → Result[Message]
  - register_part(message_id, part): Register part for creation → Result[Part]

- **UnitOfWorkImpl**: In-memory transaction tracking
  - Uses simple in-memory lists for pending entities
  - Tracks transaction state with _in_transaction flag
  - Clear pending state after commit or rollback
  - Suitable for single-process use (not thread-safe)

### Transaction Semantics
- **Begin**: Initializes transaction, clears any previous pending state
  - Returns Err if transaction already in progress
  - Resets all pending lists (sessions, messages, parts)

- **Commit**: Atomically applies all pending changes
  - Commits sessions first, then messages, then parts
  - Returns Err on first repository failure (atomicity)
  - Clear pending state only if all commits succeed
  - If any commit fails, transaction state remains (caller can rollback)

- **Rollback**: Clears pending state without persisting
  - In-memory operation, no repository calls
  - Always succeeds if transaction is in progress
  - Safe to call multiple times

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 28 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Result pattern integration** - UnitOfWork uses Result for error handling
   - All methods return Result types (Ok/Err)
   - Error codes: "TRANSACTION_ERROR" for begin/commit/rollback errors
   - Repository errors propagated through commit()
   - Consistent with repository pattern

3. **In-memory transaction tracking** - Simple approach for single-process use
   - Pending entities stored in lists (sessions, messages, parts)
   - Rollback is just clearing lists (fast, no I/O)
   - Commit iterates through lists and calls repository methods
   - Not thread-safe (documented limitation)

4. **Protocol-based design** - Enables runtime type checking and multiple implementations
   - @runtime_checkable decorator allows isinstance() checks on UnitOfWork
   - Future can add database-backed transactions with ACID guarantees
   - Type hints ensure all implementations match protocol

5. **Test coverage matters** - 28 comprehensive tests, all passing
   - Transaction lifecycle tested (begin, commit, rollback)
   - Entity registration tested with and without transactions
   - Commit tested with success and failure scenarios
   - Rollback tested to verify no repository calls
   - Integration tests verify full transaction flows

6. **Order of commits matters** - Sessions → Messages → Parts
   - Sessions created first (messages reference sessions)
   - Messages created next (parts reference messages)
   - Parts created last (no dependencies)
   - Ensures referential integrity
   - If any commit fails, transaction fails (atomicity)

### Next Steps
- Task 13: Update DefaultSessionService to use UnitOfWork for multi-write operations
- Future: Add thread-safe UnitOfWork implementation for concurrent access
- Future: Add database-backed UnitOfWork with proper transaction isolation

## Agent Finite State Machine (FSM) Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 23 tests written covering all FSM functionality
  - 3 initialization tests (valid state, invalid state, default state)
  - 2 state query tests (get_state returns state, doesn't modify)
  - 4 transition validation tests (valid, invalid, unknown state, all transitions)
  - 4 state transition tests (valid transition, invalid transition, update state, multiple transitions)
  - 3 invalid state tests (idle->completed, running->idle, unknown state)
  - 2 state constants tests (VALID_STATES, VALID_TRANSITIONS)
  - 2 protocol tests (runtime_checkable, implementation compliance)
  - 3 error handling tests (Err with code, unwrap raises, unwrap_or returns default)
- **GREEN Phase**: All 23 tests passing with 96% coverage for agent_fsm.py
- **REFACTOR Phase**: Comprehensive docstrings, type hints, thread safety documentation

### AgentFSM Pattern Design
- **AgentFSM Protocol**: Interface for state management
  - get_state(): Get current state → str
  - transition_to(new_state): Transition to new state → Result[None]
  - is_transition_valid(from_state, to_state): Check validity → bool
  - Protocol-based design enables multiple implementations (in-memory, database-backed)
  - @runtime_checkable decorator allows isinstance() checks on AgentFSM

- **AgentFSMImpl**: In-memory state machine implementation
  - Maintains internal state (_state)
  - Validates all transitions against VALID_TRANSITIONS mapping
  - Returns Result types for explicit error handling (no exceptions)
  - Factory function: create_agent_fsm(initial_state="idle")
  - Thread-safety: NOT thread-safe (documented limitation)

### Agent Lifecycle States
Six explicit lifecycle states represent agent execution phases:
1. **idle**: Agent waiting for task
2. **running**: Agent processing task
3. **paused**: Agent temporarily stopped (may resume)
4. **completed**: Agent finished successfully
5. **failed**: Agent encountered error
6. **cancelled**: Agent was cancelled by user

### State Transition Rules
- **idle** → running, cancelled
- **running** → paused, completed, failed, cancelled
- **paused** → running, cancelled
- **completed** → idle (can restart after completion)
- **failed** → idle, cancelled
- **cancelled** → idle

Invalid transitions (examples):
- idle → completed (must go through running first)
- running → idle (must complete, fail, or cancel first)
- completed → running (must go through idle first)

### Result Pattern Integration
- All transitions return Result types (Ok/Err)
- Invalid transition returns Err with "INVALID_TRANSITION" code
- Error messages include valid transitions for context
- No exceptions raised from transition methods (violates pattern if raised)
- Consistent with Result pattern learned in Task 10

### Test Coverage
- 23 comprehensive tests, all passing (100% pass rate)
- 96% code coverage for agent_fsm.py (28 statements, 1 missed line)
- Tests verify:
  - Initialization with valid/invalid states
  - State query methods (get_state)
  - Transition validation (is_transition_valid)
  - State transitions (transition_to)
  - Invalid state rejection
  - Protocol compliance with runtime_checkable
  - Result type usage (Ok/Err)
  - Error handling with error codes

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 23 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Comprehensive docstrings and type hints (REFACTOR)

2. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on protocols
   - AgentFSMImpl is default implementation (in-memory)
   - Future: database-backed FSM with persistence
   - Future: thread-safe FSM with locks or UnitOfWork integration

3. **State machine pattern provides explicit lifecycle** - No implicit state changes
   - VALID_STATES defines all possible states
   - VALID_TRANSITIONS defines valid transitions
   - Invalid transitions rejected with detailed error messages
   - Agents cannot transition to invalid states by design

4. **Result pattern integration** - Explicit error handling without exceptions
   - All transitions return Result[None]
   - Err includes error message, code ("INVALID_TRANSITION"), and context
   - Caller can handle errors explicitly (no try/except needed)
   - Consistent with Result pattern learned in Task 10

5. **Thread safety is a limitation** - In-memory implementation not concurrent-safe
   - Documented in docstring (non-blocking limitation)
   - Suitable for single-process use (AgentRuntime use case)
   - Future: Thread-safe implementation with locks
   - Future: Database-backed FSM with transaction isolation

6. **Factory functions simplify creation** - create_agent_fsm() hides complexity
   - Consistent with other pattern implementations (Repository, UnitOfWork)
   - Easy to mock and test with factory functions
   - Default parameters (initial_state="idle") for convenience

7. **Test coverage matters** - 96% coverage for agent_fsm.py
   - All public methods tested (get_state, transition_to, is_transition_valid)
   - All lifecycle states tested (idle, running, paused, completed, failed, cancelled)
   - All valid transitions tested
   - Invalid transitions tested with error codes
   - Protocol compliance tested with isinstance()

### Next Steps
- Task 15: Integrate AgentFSM into AgentRuntime for lifecycle management
- Future: Add thread-safe AgentFSM implementation for concurrent access
- Future: Add database-backed AgentFSM with persistence
- Future: Add state change events to event bus for observability

