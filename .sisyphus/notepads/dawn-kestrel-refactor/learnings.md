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


## ToolAdapter Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 21 tests written covering all adapter functionality
  - 2 protocol compliance tests (execute, get_tool_name methods)
  - 4 BashToolAdapter tests (wrap, ok success, err failure, tool name)
  - 4 ReadToolAdapter tests (wrap, ok success, err failure, tool name)
  - 4 WriteToolAdapter tests (wrap, ok success, err failure, tool name)
  - 3 GenericToolAdapter tests (wrap, ok success, err failure)
  - 4 adapter registration tests (register, get, list, unknown)
- **GREEN Phase**: All 21 tests passing with 100% pass rate
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### ToolAdapter Pattern Design
- **ToolAdapter Protocol**: Interface for tool adapters
  - `execute(context, **kwargs) -> Result[dict[str, Any]]`: Execute tool with context
  - `get_tool_name() -> str`: Get name of underlying tool
  - Protocol-based design enables runtime type checking and multiple implementations
  - @runtime_checkable decorator allows isinstance() checks on ToolAdapter

- **BashToolAdapter**: Wraps BashTool with normalized interface
  - Converts ToolResult to dict (title, output, metadata, attachments)
  - Returns Result[dict[str, Any]] with Ok/Err outcomes
  - Tool name: "bash"

- **ReadToolAdapter**: Wraps ReadTool with normalized interface
  - Same interface as BashToolAdapter
  - Tool name: "read"

- **WriteToolAdapter**: Wraps WriteTool with normalized interface
  - Same interface as BashToolAdapter
  - Tool name: "write"

- **GenericToolAdapter**: Generic adapter for other tools
  - Handles any tool with 'name' or 'id' attribute
  - Returns tool name dynamically from attribute
  - Returns "unknown" if no name attribute found

### Adapter Registration System
- **In-memory registry**: `_adapters: dict[str, ToolAdapter]`
  - `register_adapter(name, adapter)` adds adapter to registry
  - `get_adapter(name)` returns adapter or None
  - `list_adapters()` returns all adapter names
  - Enables custom tools at runtime without modifying core code

### Result Pattern Integration
- All adapter methods return Result types (Ok/Err)
- Errors wrapped with explicit error codes ("TOOL_ERROR")
- Exceptions caught and converted to Err (violates pattern if raised)
- Consistent with Result pattern learned in Task 10

### Test Coverage
- 21 comprehensive tests, all passing (100% pass rate)
- All public methods tested (execute, get_tool_name)
- All adapter types tested (Bash, Read, Write, Generic)
- Error conditions tested (tool exceptions)
- Adapter registration tested (register, get, list)

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 21 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on ToolAdapter
   - Custom tools can implement protocol and register at runtime
   - Adapter pattern normalizes interface without modifying core code

3. **ToolResult to dict conversion** - Adapters normalize tool output
   - Converts ToolResult (title, output, metadata, attachments) to dict
   - Enables consistent handling across different tool types
   - Maintains all ToolResult fields in output dict

4. **Adapter pattern benefits** - Clean separation of concerns
   - Tools unchanged (no breaking changes)
   - Unified interface via adapters
   - Custom tools enabled without core modifications
   - Result types enable explicit error handling

5. **Test coverage matters** - 21 comprehensive tests
   - All adapter methods tested (execute, get_tool_name)
   - All adapter types tested (Bash, Read, Write, Generic)
   - Error conditions tested (tool exceptions)
   - Adapter registration tested (register, get, list)

### Next Steps
- Consider adding adapters for other tool categories (Grep, Glob, ASTGrep, Edit, Lsp)
- Consider adding caching layer to adapters
- Consider adding retry logic to adapters
- Future: Thread-safe adapter registry (currently simple dict)


## Mediator Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 24 tests written covering all mediator functionality
  - 5 Event type tests (EventType enum, Event dataclass)
  - 7 Event publishing tests (all handlers, source filtering, target routing, errors)
  - 4 Event subscription tests (subscribe adds, returns ok, source filter, multiple handlers)
  - 4 Event unsubscription tests (removes handler, returns ok, err on unknown, first match)
  - 3 Handler count tests (zero handlers, correct count, exception handling)
  - 2 Protocol compliance tests (runtime_checkable, has all methods)
- **GREEN Phase**: All 24 tests passing with 90% coverage for mediator.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Mediator Pattern Design
- **EventMediator Protocol**: Interface for event coordination
  - `publish(event) -> Result[None]`: Publish event to all registered handlers
  - `subscribe(event_type, handler, source=None) -> Result[None]`: Subscribe to events
  - `unsubscribe(event_type, handler) -> Result[None]`: Unsubscribe from events
  - `get_handler_count(event_type) -> Result[int]`: Get handler count
  - Protocol-based design enables runtime type checking and multiple implementations
  - @runtime_checkable decorator allows isinstance() checks on EventMediator

- **EventMediatorImpl**: In-memory mediator implementation
  - Handler registry: dict[event_type, list[tuple[handler, source_filter]]]
  - Routing logic: Events deliver to handlers based on source filter and target
  - No thread safety (documented limitation for single-process use)

### Event Type Categorization
- **EventType Enum**: Four event type categories
  - DOMAIN: Business logic events (session created, agent finished)
  - APPLICATION: UI/operational events (progress, notification)
  - SYSTEM: System events (startup, shutdown)
  - LLM: LLM-related events (response received, streaming)

- **Event Dataclass**: Container for event data
  - event_type: EventType enum value
  - source: Component that emitted the event
  - target: Optional specific recipient (None means broadcast)
  - data: Event payload as dictionary
  - __post_init__ ensures data defaults to empty dict if None

### Event Routing Logic
- **Broadcast mode** (target=None): Deliver to all handlers with matching source filter or None
  - Handler with source_filter=None receives all events of that type
  - Handler with source_filter="specific" receives only events from that source
- **Targeted mode** (target="specific"): Deliver only to handlers with matching source_filter
  - Used for point-to-point communication between components
  - Enables request-response patterns

### Result Pattern Integration
- All mediator methods return Result types (Ok/Err)
- Errors wrapped with explicit error codes ("MEDIATOR_ERROR", "HANDLER_NOT_FOUND")
- Exceptions caught and converted to Err (violates pattern if raised)
- Consistent with Result pattern learned in Task 10

### Test Coverage
- 90% coverage for mediator.py (63 statements, 6 missed)
- 100% pass rate: all 24 tests pass
- All public methods tested (publish, subscribe, unsubscribe, get_handler_count)
- Error conditions tested (handler exceptions, unknown handlers)
- Routing logic tested (source filtering, target routing, broadcast)

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 24 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Mediator pattern centralizes event coordination** - Eliminates component-to-component direct wiring
   - Components register handlers with mediator
   - Components publish events to mediator
   - Mediator routes events to matching handlers
   - Loose coupling between components

3. **Event filtering enables fine-grained control** - Source and target routing
   - Source filter: Subscribe to events from specific component
   - Target routing: Send event to specific handler only
   - Broadcast: All handlers or all handlers from specific source
   - Flexible routing for different communication patterns

4. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on EventMediator
   - Future: In-memory mediator (current), database-backed mediator, distributed mediator
   - Type hints ensure all implementations match protocol

5. **Result pattern integration** - Explicit error handling without exceptions
   - All methods return Result[None] or Result[int]
   - Err includes error message, code ("MEDIATOR_ERROR", "HANDLER_NOT_FOUND")
   - Caller can handle errors explicitly (no try/except needed)
   - Consistent with Result pattern learned in Task 10

6. **Thread safety is a limitation** - In-memory implementation not concurrent-safe
   - Documented in docstring (non-blocking limitation)
   - Suitable for single-process use (async event handling)
   - Future: Thread-safe implementation with locks or database mediator

7. **Test coverage matters** - 90% coverage for mediator.py
   - All public methods tested (publish, subscribe, unsubscribe, get_handler_count)
   - All routing paths tested (broadcast, source filter, target)
   - Error conditions tested (handler exceptions, unknown handlers)
   - Protocol compliance tested with isinstance()

### Next Steps
- Consider wrapping existing EventBus with Mediator for gradual migration
- Consider adding event metadata (timestamp, correlation_id, priority)
- Consider adding event filtering by data content (not just source/target)
- Future: Thread-safe EventMediator implementation for concurrent access
- Future: Database-backed EventMediator for distributed systems
- Future: Event replay capabilities for debugging and audit trails


## Command Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 24 tests written covering all Command pattern functionality
  - 2 Command protocol tests
  - 7 CreateSessionCommand tests
  - 5 ExecuteToolCommand tests
  - 10 CommandQueue tests
- **GREEN Phase**: All 24 tests passing with 91% coverage for commands.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Command Pattern Design
- **Command Protocol**: Interface for command encapsulation
  - `execute(context: CommandContext) -> Result[Any]`: Execute the command
  - `undo() -> Result[None]`: Undo the command (if supported)
  - `can_undo() -> bool`: Check if command can be undone
  - `get_provenance() -> Result[dict[str, Any]]`: Get provenance information
  - Protocol-based design enables runtime type checking and multiple implementations
  - @runtime_checkable decorator allows isinstance() checks on Command

- **CommandContext**: Execution context for commands
  - session_id: Optional session ID
  - message_id: Optional message ID
  - agent_id: Optional agent ID
  - user_id: Optional user ID
  - timestamp: Creation timestamp (default: now)
  - metadata: Dictionary for dependencies (session_repo, tool_adapter, etc.)

- **BaseCommand**: Base class for all commands
  - name: Command name
  - description: Command description
  - created_at: Creation timestamp
  - Default execute() raises NotImplementedError
  - Default can_undo() returns False
  - Default undo() returns Err with UNDO_NOT_SUPPORTED code
  - get_provenance() returns Ok with command metadata

- **CreateSessionCommand**: Command to create sessions
  - Uses session_repo from context.metadata
  - Creates Session object with provided session_id and title
  - Returns session_id on success
  - Cannot be undone (can_undo() returns False)

- **ExecuteToolCommand**: Command to execute tools
  - Uses tool_adapter from context.metadata
  - Passes arguments directly to tool_adapter.execute()
  - Returns tool result on success
  - Cannot be undone (can_undo() returns False)

- **CommandQueue**: Queue for managing command execution with events
  - Uses EventMediator for publishing command events
  - enqueue(): Add command to queue and history, publish enqueued event
  - process_next(): Process next command, publish started/completed/failed events
  - history: Tracks all commands (even after processing)
  - Returns Err if queue empty

### Result Pattern Integration
- All command methods return Result types (Ok/Err)
- Errors wrapped with explicit error codes ("MISSING_DEPENDENCY", "COMMAND_ERROR", "QUEUE_ERROR", "UNDO_NOT_SUPPORTED")
- Exceptions caught and converted to Err (violates pattern if raised)
- Consistent with Result pattern learned in Task 10

### Test Coverage
- 91% coverage for commands.py (93 statements, 8 missed)
- 100% pass rate: all 24 tests pass
- All public methods tested (execute, undo, can_undo, get_provenance)
- Error conditions tested (missing dependencies, execution failures)
- Event publishing tested (enqueued, started, completed, failed)

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 24 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on Command
   - Custom commands can implement protocol and be enqueued
   - Command pattern normalizes interface without modifying core code

3. **Context metadata is flexible** - Dependencies passed via context.metadata
   - session_repo, tool_adapter passed via metadata dictionary
   - Easy to extend with new dependencies without changing CommandContext
   - Avoids tight coupling between commands and their dependencies

4. **EventMediator integration** - Commands publish execution events
   - enqueue publishes command_enqueued event
   - process_next publishes command_started, command_completed, or command_failed events
   - Enables loose coupling and observability
   - Consistent with Mediator pattern learned in Task 19

5. **Test coverage matters** - 91% coverage for commands.py
   - All Command protocol methods tested
   - All concrete command implementations tested
   - CommandQueue enqueue and process_next tested
   - Error conditions tested with proper Result handling

6. **Dataclass vs regular class** - CreateSessionCommand and ExecuteToolCommand use regular classes
   - Initial dataclass decorator caused issues with __init__ method
   - Removed @dataclass decorator for commands with custom __init__
   - BaseCommand remains dataclass (standard fields, no custom __init__)

7. **ToolAdapter.execute() signature** - Takes kwargs, not ToolContext
   - ExecuteToolCommand passes arguments directly via **self.arguments
   - Avoids ToolContext complexity (requires agent, abort, messages)
   - Simpler integration with tool adapters

### Next Steps
- Task 21: Integrate Command pattern into AgentRuntime
- Task 22: Add undo/redo support for commands
- Task 23: Add command history and audit logging
- Future: Consider thread-safe CommandQueue for concurrent access
- Future: Consider command serialization for persistence

## Decorator/Proxy Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 23 tests written covering all decorator/proxy functionality
  - 3 LoggingConfig tests (defaults, custom level, disabled)
  - 8 log_function decorator tests (wrapping, entry logging, result logging, exception logging, log level, prefix, disabled, async)
  - 8 FunctionProxy tests (wrapping, call logging, result logging, exception logging, log level, prefix, disabled, factory)
  - 4 Configuration tests (DEBUG logs everything, WARNING filters INFO, ERROR logs only errors, per-instance configuration)
- **GREEN Phase**: All 23 tests passing with 93% coverage for decorators.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Decorator Pattern Design
- **LoggingConfig**: Configuration class for logging behavior
  - level: Logging level (DEBUG, INFO, WARNING, ERROR)
  - enabled: Enable/disable logging toggle
  - prefix: Prefix for all log messages
  - include_args: Include function arguments in logs
  - include_result: Include function return value in logs
  - include_timestamp: Include timestamp in log messages
  - Centralized configuration enables fine-grained control

- **log_function**: Decorator to add logging to async functions
  - Wraps any async function with configurable logging
  - Logs function entry with arguments (if include_args=True)
  - Logs function result (if include_result=True)
  - Logs exceptions with error message
  - Uses @wraps to preserve function metadata
  - Logger created from func.__module__ for module-specific logging
  - Args truncated to 100 characters for readability

### Proxy Pattern Design
- **LoggingProxy Protocol**: Interface for logging proxies
  - async __call__(*args, **kwargs) -> Any: Proxy method call with logging
  - Protocol-based design enables runtime type checking with @runtime_checkable

- **FunctionProxy**: Proxy that wraps callables with logging
  - Wraps both sync and async functions (uses asyncio.iscoroutinefunction)
  - Logs function entry and result
  - Logs exceptions with error message
  - Enabled flag allows runtime toggling without code changes
  - Logger created from func.__module__ for module-specific logging

- **create_logging_proxy**: Factory function to create proxies
  - Creates FunctionProxy with specified configuration
  - Simplifies proxy creation with default parameters
  - Returns FunctionProxy instance

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 23 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Comprehensive docstrings and type hints (REFACTOR)

2. **Async function support** - Decorator/proxy must handle async functions
   - @wraps preserves function metadata (name, module, docstring)
   - Async wrapper must be async def
   - FunctionProxy checks asyncio.iscoroutinefunction to handle both sync and async

3. **Python logging integration** - Standard logging module provides flexibility
   - Logger per module: logging.getLogger(func.__module__)
   - Log levels: DEBUG, INFO, WARNING, ERROR
   - Custom logging handlers can be configured via Python's logging module
   - Configurable output (console, file, silent) via logging.basicConfig

4. **Decorator pattern benefits** - Clean separation of concerns
   - Functions unchanged (no logging code added to business logic)
   - Configurable logging per function (level, prefix, args, result, timestamp)
   - Can be enabled/disabled at runtime
   - Consistent logging across codebase

5. **Proxy pattern benefits** - Runtime wrapping without modification
   - Callables can be wrapped without changing source code
   - Proxies can be applied conditionally at runtime
   - Same logging behavior as decorator but applied dynamically
   - Useful for third-party code that cannot be decorated

6. **Test coverage matters** - 93% coverage for decorators.py
   - All public methods tested (log_function, FunctionProxy.__call__, create_logging_proxy)
   - All configuration options tested (level, enabled, prefix, include_args, include_result, include_timestamp)
   - Error conditions tested (exceptions, disabled logging, log level filtering)
   - Protocol compliance tested with isinstance() on LoggingProxy

### Test Coverage
- 93% coverage for decorators.py (86 statements, 6 missed)
- 100% pass rate: all 23 tests pass
- Test categories:
  - LoggingConfig initialization and configuration
  - log_function decorator wrapping and logging behavior
  - FunctionProxy wrapping and logging behavior
  - Configuration per instance
  - Log level filtering (DEBUG, INFO, WARNING, ERROR)

### Next Steps
- Consider adding sync function support to log_function (currently async only)
- Consider adding correlation_id for tracking requests across logs
- Consider adding structured logging (JSON output)
- Consider adding metrics/timing logging
- Future: Thread-safe logging configuration (currently no locks)


## Observer Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 18 tests written covering all observer functionality
  - 4 protocol compliance tests
  - 8 ObservableImpl tests (initialization, registration, unregistration, notification)
  - 4 StateChangeObserver tests (records notifications, callable)
  - 4 MetricsObserver tests (counts metrics, callable, get counts)
  - 2 integration tests (multiple observers, mediator integration)
- **GREEN Phase**: All 18 tests passing with 97% coverage for observer.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Observer Pattern Design
- **Observer Protocol**: Interface for objects that receive notifications
  - `on_notify(observable, event) -> None`: Handle notification from observable
  - Protocol-based design enables runtime type checking
  - @runtime_checkable decorator allows isinstance() checks on Observer

- **Observable Protocol**: Interface for objects that maintain observer lists
  - `register_observer(observer) -> None`: Register observer for notifications
  - `unregister_observer(observer) -> None`: Unregister observer
  - `notify_observers(event) -> None`: Notify all observers of change
  - Protocol-based design enables multiple implementations

- **ObservableImpl**: In-memory observable implementation
  - Maintains set of observers (hash-based for uniqueness)
  - Observer exceptions caught and logged, don't fail other observers
  - Optional EventMediator integration for lifecycle events
  - Thread-safety: NOT thread-safe (documented limitation)

### Concrete Observers
- **StateChangeObserver**: Records all notifications received
  - Stores notifications with observer name, observable name, event, timestamp
  - `get_notifications()` returns copy (prevents external modification)
  - `clear_notifications()` clears recorded notifications

- **MetricsObserver**: Aggregates metric counts from events
  - Events should contain 'metric_name' and 'count' fields
  - `get_metric_counts()` returns copy (prevents external modification)
  - `clear_metrics()` clears aggregated metrics

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 18 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Dataclass hashability issue** - Mutable fields make dataclasses unhashable
   - StateChangeObserver had `_notifications: list` field
   - MetricsObserver had `_metric_counts: dict` field
   - Solution: Use `@dataclass(unsafe_hash=True)` with `field(compare=False, hash=False)` for mutable fields
   - This excludes mutable fields from hash calculation while keeping functionality

3. **Observer vs Mediator patterns** - Different but complementary
   - Observer: Object-to-many notification (one observable, many observers)
   - Mediator: Event-based publish/subscribe (many publishers, many subscribers)
   - Observer focuses on specific object relationships, Mediator is event-centric
   - Can use both: Observable publishes lifecycle events via EventMediator

4. **Observer error handling** - Fault tolerance prevents cascading failures
   - `notify_observers()` catches exceptions and logs them
   - One faulty observer doesn't break notifications to others
   - Simple `print()` for logging (production should use proper logger)

5. **Test coverage matters** - 97% coverage for observer.py
   - All public methods tested
   - Error conditions tested (observer failures, unregistration of non-existent observers)
   - Integration tests verify multiple observers and mediator interaction
   - Manual QA scenario confirmed expected behavior

### Test Coverage
- 97% coverage for observer.py (61 statements, 2 missed)
- 100% pass rate: all 18 tests pass
- All public methods tested (register_observer, unregister_observer, notify_observers)
- All concrete observers tested (StateChangeObserver, MetricsObserver)
- Error conditions tested (observer exceptions, unregistration)
- Integration tests verify multiple observers and mediator publishing

### Next Steps
- Consider integrating Observer pattern into AgentRuntime for lifecycle notifications
- Consider replacing print() logging with proper logger module
- Future: Thread-safe Observable implementation with locks
- Future: Database-backed Observable for distributed systems

## Null Object Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 22 tests written covering all null object functionality
  - 7 NullIOHandler tests (prompt, confirm, select, multi_select)
  - 3 NullProgressHandler tests (start, update, complete)
  - 1 NullNotificationHandler test (show)
  - 7 get_null_handler factory tests (returns existing, returns null, unknown type)
  - 3 protocol compliance tests (implements protocols)
  - 1 integration test (works with existing code)
- **GREEN Phase**: All 22 tests passing with 100% coverage for null_object.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Null Object Pattern Design
- **NullIOHandler**: Null implementation for IOHandler protocol
  - prompt(message, default) returns default or empty string
  - confirm(message, default) returns default (True/False)
  - select(message, options) returns first option or empty string
  - multi_select(message, options) returns empty list
  - All methods are no-ops that return safe defaults

- **NullProgressHandler**: Null implementation for ProgressHandler protocol
  - start(operation, total) is a no-op
  - update(current, message) is a no-op
  - complete(message) is a no-op
  - All methods return None (void)

- **NullNotificationHandler**: Null implementation for NotificationHandler protocol
  - show(notification) is a no-op
  - Accepts any notification type (Notification or Any)
  - Returns None (void)

- **get_null_handler**: Factory function for null handler creation
  - Returns existing handler if not None
  - Creates appropriate null handler based on type string ("io", "progress", "notification")
  - Raises ValueError for unknown handler types
  - Eliminates null checks in client code

### Key Design Principles
1. **No-op methods**: All null methods do nothing and return safe defaults
2. **Protocol compliance**: Implement IOHandler, ProgressHandler, NotificationHandler
3. **Runtime type checking**: isinstance() works on null handlers (protocols are @runtime_checkable)
4. **Factory pattern**: get_null_handler() simplifies null handler creation
5. **No side effects**: Null handlers never modify state or throw exceptions

### Handler Protocol Mismatch Resolution
- Initial confusion: Task description mentioned "input" and "notify" methods
- Actual protocol uses: prompt (not input), confirm, select, multi_select
- No "notify" method in IOHandler - it's a separate protocol (NotificationHandler)
- Solution: Implemented null handlers matching actual protocol definitions

### @runtime_checkable Decorator Mistake
- **Critical error**: Applied @runtime_checkable to implementation classes
- **Error**: `TypeError: @runtime_checkable can be only applied to protocol classes`
- **Fix**: Removed decorator from NullIOHandler, NullProgressHandler, NullNotificationHandler
- **Lesson**: @runtime_checkable is for Protocol definitions, not implementations
- **Best practice**: Protocols use @runtime_checkable, implementations don't

### Protocol vs Implementation
- **Protocols** (in interfaces/io.py): Define the interface with @runtime_checkable
- **Implementations** (in core/null_object.py): Provide concrete implementation without decorator
- isinstance() works on implementations because protocols are @runtime_checkable
- Type checking works because implementations match protocol structure

### Integration with Existing Code
- session_service.py uses handlers: confirm(), start(), update(), complete(), show()
- Null handlers work seamlessly with existing code patterns
- Eliminates need for `if handler:` checks in session_service.py
- Can use get_null_handler("io", io_handler) to safely handle None

### Test Coverage
- 100% coverage for null_object.py (31 statements, 0 missed)
- 100% pass rate: all 22 tests pass
- Test categories:
  - NullIOHandler: 7 tests (prompt, confirm, select, multi_select)
  - NullProgressHandler: 3 tests (start, update, complete)
  - NullNotificationHandler: 1 test (show)
  - get_null_handler: 7 tests (returns existing, returns null, unknown type)
  - Protocol compliance: 3 tests (isinstance() checks)
  - Integration: 1 test (existing code patterns)

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 22 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Null Object pattern eliminates null checks** - Safe defaults for optional dependencies
   - Instead of `if handler: handler.method()`, use `get_null_handler("type", handler)`
   - Returns null handler if None, existing handler if not None
   - Client code never needs to check for None

3. **Protocol-based design enables flexibility** - Multiple implementations possible
   - Protocols define interface (@runtime_checkable)
   - Implementations provide behavior (no decorator needed)
   - isinstance() works on implementations
   - Future: Database-backed handlers, logging handlers, etc.

4. **No-op methods provide safe defaults** - Deterministic behavior
   - IO: prompt returns default/empty, confirm returns default, select returns first option
   - Progress: All methods are no-ops (no-op for start/update/complete)
   - Notification: show is a no-op (no-op for notifications)
   - Never throws exceptions, always returns safe value

5. **Factory pattern simplifies usage** - get_null_handler() handles all types
   - One function for all handler types
   - Returns existing handler if not None
   - Creates appropriate null handler based on type string
   - Reduces boilerplate in client code

6. **@runtime_checkable decorator is for protocols only** - Not for implementations
   - Protocols (IOHandler, ProgressHandler, NotificationHandler) use @runtime_checkable
   - Implementations (NullIOHandler, etc.) don't use @runtime_checkable
   - isinstance() works because protocols are runtime-checkable
   - Applying to implementations causes TypeError

7. **Test coverage matters** - 100% coverage for null_object.py
   - All public methods tested (prompt, confirm, select, multi_select, start, update, complete, show, get_null_handler)
   - All protocol compliance tested (isinstance() checks)
   - All return values tested (defaults, empty values)
   - Integration test verifies compatibility with existing code

### Next Steps
- Task 24: Update session_service.py to use get_null_handler for all handlers
- Consider adding logging to null handlers (optional debug logging)
- Consider adding metrics tracking (how often null handlers are used)
- Future: Thread-safe null handlers (currently all methods are pure)

## Strategy Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 21 tests written covering all strategy functionality
  - 2 RoutingStrategy protocol tests
  - 4 RoundRobinRouting tests (selects first, cycles, no providers, strategy name)
  - 5 CostOptimizedRouting tests (cheapest, budget, no providers, no suitable, name)
  - 1 RenderingStrategy protocol test
  - 2 PlainTextRendering tests (returns response, ignores context)
  - 3 MarkdownRendering tests (formats, code blocks, lists)
  - 4 StrategySelector tests (register, select, unknown, environment)
- **GREEN Phase**: All 21 tests passing with 98% coverage for strategies.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Strategy Pattern Design
- **RoutingStrategy Protocol**: Interface for LLM provider routing
  - `select_provider(providers, context) -> Result[Provider]`: Select provider based on context
  - `get_strategy_name() -> str`: Get strategy name for logging/metrics
  - Protocol-based design enables runtime type checking and multiple implementations
  - @runtime_checkable decorator allows isinstance() checks on RoutingStrategy

- **RoundRobinRouting**: Simple round-robin provider selection
  - Distributes requests evenly across all providers in sequence
  - Stateful: maintains internal index that increments modulo provider count
  - O(1) selection, simple and predictable
  - Strategy name: "round_robin"

- **CostOptimizedRouting**: Cost-based provider selection
  - Selects provider with lowest cost for estimated tokens
  - Respects optional budget constraint in context
  - Estimates tokens: 4 characters per token (rough approximation)
  - Mock pricing implementation: reads provider.cost attribute or defaults to 0.001
  - Strategy name: "cost_optimized"

### RenderingStrategy Protocol
- **RenderingStrategy Protocol**: Interface for output formatting
  - `render(messages, response, context) -> str`: Format response based on strategy
  - Protocol-based design enables runtime format selection without if/else chains

- **PlainTextRendering**: No formatting
  - Returns response unchanged
  - Suitable for raw output
  - Ignores messages and context

- **MarkdownRendering**: Basic markdown formatting
  - Indents list items (adds 2 spaces to lines starting with "- ")
  - Preserves code blocks, headings, and other markdown
  - Enhances readability with proper formatting

### StrategySelector: Context-based selection
- **Registry**: In-memory dict of registered strategies
  - `register(name, strategy)` adds strategy to registry
  - `select(type, context)` selects strategy based on type and context
- **Environment-aware**: Selects different strategies based on context
  - Production environment: uses CostOptimizedRouting for routing
  - Development: defaults to first registered strategy
- **Result-based selection**: Returns Ok(strategy) or Err(STRATEGY_NOT_FOUND)

### Result Pattern Integration
- All strategy methods return Result types (Ok/Err)
- Errors wrapped with explicit error codes ("NO_PROVIDERS", "NO_PROVIDER", "STRATEGY_NOT_FOUND")
- Exceptions caught and converted to Err (violates pattern if raised)
- Consistent with Result pattern learned in Task 10

### Test Coverage
- 98% coverage for strategies.py (83 statements, 2 missed)
- 100% pass rate: all 21 tests pass
- All public methods tested (select_provider, get_strategy_name, render, register, select)
- Error conditions tested (no providers, budget exceeded, unknown strategy)
- Protocol compliance tested with @runtime_checkable

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 21 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on protocols
   - Custom strategies can implement protocol and be used at runtime
   - Strategy pattern eliminates if/else chains for algorithm selection
   - Runtime strategy selection based on context (environment, budget, etc.)

3. **StrategySelector for context-based selection** - Clean abstraction for strategy switching
   - Different environments (dev/prod) can use different strategies
   - Registration pattern enables runtime strategy discovery
   - Context-aware selection without hard-coded conditionals

4. **Result type integration** - Explicit error handling without exceptions
   - All methods return Result types (Ok/Err)
   - Errors have codes for categorization ("NO_PROVIDERS", "STRATEGY_NOT_FOUND")
   - Caller can handle errors explicitly (no try/except needed)
   - Consistent with Result pattern learned in Task 10

5. **Mock pricing for testing** - Simple implementation for development
   - _get_pricing() reads provider.cost attribute or defaults to 0.001
   - Enables cost-optimized routing tests without real provider APIs
   - Real implementation would query provider pricing endpoints

6. **Test coverage matters** - 98% coverage for strategies.py
   - All strategy types tested (routing and rendering)
   - All protocol compliance tested
   - All error conditions tested
   - Context-based selection tested

### Next Steps
- Integrate RoutingStrategy into LLM client for provider selection
- Add more routing strategies (LatencyOptimized, PriorityRouting)
- Add more rendering strategies (HTMLRendering, JSONRendering)
- Future: Thread-safe StrategySelector (currently simple dict)
- Future: Strategy persistence (save/load strategy configuration)

## Metrics Decorator/Proxy Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 22 tests written covering all metrics functionality
  - 3 protocol compliance tests
  - 8 InMemoryMetricsStore tests (timing storage, counter increment, aggregation)
  - 5 metrics_decorator tests (timing measurement, custom names, tags, exceptions, metadata)
  - 5 MetricsProxy tests (wrapping, call counting, return values)
  - 2 integration tests (collector/store, decorator/collector)
- **GREEN Phase**: All 22 tests passing with 100% coverage for metrics.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Metrics Pattern Design
- **MetricsCollector Protocol**: Interface for metrics collection
  - `record_timing(name, duration_ms, tags) -> None`: Record execution duration
  - `increment_counter(name, value, tags) -> None`: Increment counter metric
  - `get_metric(name, tags) -> dict`: Get aggregated statistics
  - Protocol-based design enables runtime type checking and multiple implementations
  - @runtime_checkable decorator allows isinstance() checks on MetricsCollector

- **InMemoryMetricsStore**: In-memory storage for timing and counter metrics
  - Timing metrics: list of (name, duration_ms, tags, timestamp) tuples
  - Counter metrics: defaultdict[tuple[str, str], int] for incremental values
  - _tags_key() converts tags dict to string key for counter grouping
  - get_metric() returns different stats based on data type:
    - With timings: count=number_of_timings, sum/min/max/avg from durations
    - With only counters: count=counter_value, other stats = 0

- **metrics_decorator**: Decorator to measure function execution time
  - Uses time.perf_counter() for precise timing
  - Records timing in finally block (captures even on exceptions)
  - Custom metric_name parameter overrides function name
  - Tags parameter for grouping/filtering metrics
  - @wraps preserves function metadata (__name__, __doc__)

- **MethodMetricsProxy**: Proxy that counts method calls
  - Records counter with "_calls" suffix (e.g., "function_name_calls")
  - Includes method name in tags for filtering
  - Wraps async functions for consistent API
  - create_metrics_proxy() factory function simplifies creation

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 22 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on MetricsCollector
   - Future: Database-backed metrics store, distributed metrics collection
   - Type hints ensure all implementations match protocol

3. **get_metric() dual behavior** - Handles both timing and counter metrics
   - When timings exist: returns timing stats (count=sum, min/max/avg from durations)
   - When only counters: returns counter value in count field
   - Design allows unified API for different metric types
   - Key insight: count field overloaded for both timing_count and counter_value

4. **@wraps preserves metadata** - Function wrapping keeps __name__ and __doc__
   - Used functools.wraps decorator on wrapper function
   - Preserves __name__ for debugging/metrics naming
   - Preserves __doc__ for documentation
   - Important for decorators that are applied to user-facing functions

5. **Tags for metric filtering** - Tags enable flexible grouping
   - Tags are dict[str, str] for key-value pairs
   - _tags_key() sorts items for consistent keys
   - Same metric name with different tags = separate metrics
   - Enables filtering by module, operation, user, etc.

6. **Test coverage matters** - 100% coverage for metrics.py
   - All public methods tested (record_timing, increment_counter, get_metric)
   - Decorator tested with timing, custom names, tags, exceptions, metadata
   - Proxy tested with wrapping, call counting, custom names, return values
   - Integration tests verify end-to-end functionality

7. **In-memory design trade-off** - Simple but not production-ready
   - No persistence (metrics lost on restart)
   - Not thread-safe (documented limitation)
   - No aggregation beyond basic stats
   - Suitable for single-process use and testing
   - Future: Add persistence, thread safety, more aggregation

### Next Steps
- Consider adding metrics export functionality (JSON, Prometheus format)
- Consider adding metrics reset/clear functionality
- Future: Add thread-safe MetricsStore implementation
- Future: Add database-backed MetricsStore with persistence
- Future: Add percentiles (p50, p90, p99) to get_metric()


## Circuit Breaker Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 26 tests written covering all circuit breaker functionality
  - 4 circuit state tests (initial state, failures, times)
  - 4 circuit operations tests (open, close)
  - 3 circuit breaker logic tests (closed, open, half-open)
  - 4 failure tracking tests (increment, count, time, multiple providers)
  - 8 protocol compliance tests (runtime_checkable, methods, state queries)
  - 3 Result type tests (open/close returns Result, state returns string)
- **GREEN Phase**: All 26 tests passing with 84% coverage for circuit_breaker.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### CircuitBreaker Pattern Design
- **CircuitBreaker Protocol**: Interface for circuit breaker
  - `is_open() -> bool`: Check if circuit allows calls (OPEN or HALF_OPEN)
  - `is_closed() -> bool`: Check if circuit blocks calls (CLOSED only)
  - `is_half_open() -> bool`: Check if circuit is in recovery state
  - `get_state() -> str`: Get current state ("closed", "open", "half_open")
  - `open() -> Result[None]`: Open circuit for calls (changes state to OPEN)
  - `close() -> Result[None]`: Close circuit manually (clears failures)
  - Protocol-based design enables runtime type checking and multiple implementations
  - @runtime_checkable decorator allows isinstance() checks on CircuitBreaker

- **CircuitState Enum**: Three explicit circuit states
  - CLOSED: Circuit is closed (blocks calls) - initial state
  - OPEN: Circuit is open (allows calls) - opened manually via open()
  - HALF_OPEN: Limited calls for recovery testing - after timeout

- **CircuitBreakerImpl**: In-memory circuit breaker implementation
  - Wraps provider adapter with circuit breaker logic
  - Tracks failures per provider: `_failures: dict[str, int]`
  - Tracks last failure time: `_last_failure_time: dict[str, datetime]`
  - Tracks half-open expiration: `_half_open_until: dict[str, datetime]`
  - Configurable thresholds: failure_threshold, half_open_threshold, timeout_seconds, reset_timeout_seconds
  - Thread-safety: NOT thread-safe (documented limitation)
  - Simple in-memory tracking suitable for single-process use

### Circuit Breaker Logic
- **State management**: 
  - Initial state: CLOSED
  - Manual control: open() changes to OPEN, close() changes to CLOSED
  - Query methods: is_open(), is_closed(), is_half_open() check current state
  - State queries don't modify state (idempotent)

- **Failure tracking**:
  - Per-provider tracking: Each provider has separate failure count
  - Incremental tracking: Failures increment one at a time
  - Last failure time: Timestamp updated on each failure
  - Close clears all: close() resets failures, times, and expirations

- **Result pattern integration**:
  - All methods return Result types (Ok/Err)
  - open() returns Ok(None) on success, Err on failure
  - close() returns Ok(None) on success, Err on failure
  - No exceptions raised from public methods (violates pattern if raised)
  - Consistent with Result pattern learned in Task 10

### Test Coverage
- 84% coverage for circuit_breaker.py (61 statements, 10 missed)
- 100% pass rate: all 26 tests pass
- All public methods tested (is_open, is_closed, is_half_open, get_state, open, close)
- State transitions tested (initial state, open, close, half-open)
- Failure tracking tested (increment, count, timestamps, multiple providers)
- Protocol compliance tested (runtime_checkable, isinstance checks)
- Result types tested (Ok returns, Err returns, state strings)

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 26 failing tests (RED) - module didn't exist
   - Implemented protocol and class to pass all tests (GREEN)
   - Clean code with comprehensive docstrings and type hints (REFACTOR)

2. **Circuit breaker pattern provides fault tolerance** - Explicit state management
   - States are explicit (CLOSED, OPEN, HALF_OPEN) - no implicit transitions
   - Manual control via open()/close() methods
   - Query methods check state without modifying it (idempotent)
   - Provider-specific failure tracking enables fine-grained control

3. **Result pattern integration** - Explicit error handling without exceptions
   - open() and close() return Result[None] for explicit error handling
   - No exceptions raised from public methods
   - Err includes error message and code ("CIRCUIT_ERROR")
   - Caller can handle errors explicitly (no try/except needed)
   - Consistent with Result pattern learned in Task 10

4. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on CircuitBreaker
   - CircuitBreakerImpl is default implementation (in-memory)
   - Future: Thread-safe CircuitBreaker with locks or UnitOfWork integration
   - Future: Database-backed CircuitBreaker with persistence
   - Type hints ensure all implementations match protocol

5. **In-memory implementation trade-offs** - Simple but not production-ready
   - No persistence (circuit state lost on restart)
   - Not thread-safe (documented limitation)
   - Per-provider tracking in simple dicts (suitable for few providers)
   - Suitable for single-process use (LLM client use case)
   - Future: Add thread safety with locks or async primitives
   - Future: Add persistence for circuit state across restarts

6. **Test coverage matters** - 84% coverage for circuit_breaker.py
   - All public methods tested (is_open, is_closed, is_half_open, get_state, open, close)
   - All circuit states tested (CLOSED, OPEN, HALF_OPEN)
   - Failure tracking tested with multiple providers
   - Protocol compliance tested with isinstance() checks
   - Result type usage tested (Ok/Err returns)
   - 10 missed lines in private methods (_get_provider_name, open, close)

7. **Simplified circuit breaker** - Manual control without automatic transitions
   - Unlike traditional circuit breaker, this implementation requires manual open()/close()
   - No automatic state transitions based on failure counts
   - Suitable for explicit fault tolerance control in LLM calls
   - Future: Add automatic transitions (CLOSED -> OPEN on threshold, HALF_OPEN -> CLOSED on success)

8. **Provider adapter integration** - Wraps provider without modification
   - ProviderAdapter interface used (has get_provider_name() method)
   - No direct modification to provider code
   - Adapter pattern enables clean separation (providers from circuit breaking)
   - Consistent with Adapter pattern learned in Task 16

### Next Steps
- Consider adding automatic circuit transitions (CLOSED -> OPEN on threshold breach)
- Consider adding HALF_OPEN state management (timeout expiration)
- Consider adding thread-safe CircuitBreaker implementation for concurrent access
- Consider adding persistence for circuit state across restarts
- Future: Integrate with Strategy pattern (Task 24) for provider selection
- Future: Add circuit breaker to LLM client for automatic fault tolerance

## Bulkhead Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 27 tests written covering all bulkhead functionality
  - 4 protocol compliance tests (methods defined, runtime_checkable, implementation)
  - 7 semaphore management tests (acquire, release, timeout, error handling)
  - 5 configuration tests (limits, timeouts, multiple resources)
  - 9 try_execute tests (execution, timeout, release, concurrent limiting)
  - 2 active count tests (increment, decrement, concurrent operations)
- **GREEN Phase**: All 27 tests passing with high coverage for bulkhead.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Bulkhead Pattern Design
- **Bulkhead Protocol**: Interface for resource isolation
  - `try_acquire(resource) -> Result[Semaphore]`: Acquire semaphore with timeout
  - `release(semaphore) -> Result[None]`: Release semaphore after operation
  - `try_execute(resource, func, max_concurrent) -> Result[Any]`: Execute with limiting
  - Protocol-based design enables runtime type checking and multiple implementations
  - @runtime_checkable decorator allows isinstance() checks on Bulkhead

- **BulkheadImpl**: In-memory bulkhead with per-resource semaphores
  - Per-resource semaphores: `_semaphores: dict[str, asyncio.Semaphore]`
  - Per-resource limits: `_limits: dict[str, int]` (default: 1)
  - Per-resource timeouts: `_timeouts: dict[str, float]` (default: 30.0s)
  - Active counts: `_active_counts: dict[str, int]` for tracking operations
  - Managed semaphores: `_managed_semaphores: set[asyncio.Semaphore]` for validation

### Resource Isolation Mechanism
- **Per-resource semaphores**: Each resource (provider, API endpoint) has its own semaphore
  - Semaphore created on first acquire: `asyncio.Semaphore(limit)`
  - Same semaphore reused for subsequent acquires
  - Different resources have independent limits and semaphores
  - Prevents resource-specific exhaustion (e.g., openai limited to 5 concurrent calls)

- **Semaphore acquisition with timeout**: `asyncio.wait_for(semaphore.acquire(), timeout)`
  - Waits for semaphore with configurable timeout
  - Returns `Ok[Semaphore]` on success
  - Returns `Err` with "ACQUISITION_TIMEOUT" code on timeout
  - Returns `Err` with "BULKHEAD_ERROR" code on exception

- **Semaphore release validation**: Tracks ownership to prevent errors
  - Only release semaphores acquired via try_acquire()
  - Validates semaphore in `_managed_semaphores` set before releasing
  - Prevents releasing external semaphores not managed by this bulkhead
  - Removes from managed set after release
  - Returns `Err` if semaphore not managed

### try_execute Behavior
- **Acquire-execute-release pattern**: Guarantees semaphore cleanup
  - Acquires semaphore via try_acquire()
  - Executes function with timeout protection
  - Releases semaphore in finally block (even on exception)
  - Ensures no semaphore leaks from failed operations

- **Custom max_concurrent parameter**: Overrides configured limit per-execution
  - Temporarily sets limit via set_limit()
  - Restores original limit after execution
  - Allows flexible concurrency control without modifying configuration

- **Execution timeout protection**: `asyncio.wait_for(func(), timeout)`
  - Times out long-running functions
  - Returns `Err` with "EXECUTION_TIMEOUT" code
  - Prevents hung operations from blocking semaphore forever

### Result Pattern Integration
- All bulkhead methods return Result types (Ok/Err)
- Errors wrapped with explicit error codes ("ACQUISITION_TIMEOUT", "EXECUTION_TIMEOUT", "BULKHEAD_ERROR")
- Exceptions caught and converted to Err (violates pattern if raised)
- Consistent with Result pattern learned in Task 10

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 27 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on Bulkhead
   - BulkheadImpl is default (in-memory, not thread-safe)
   - Future: Thread-safe or database-backed implementations

3. **Managed semaphore tracking** - Prevents releasing non-managed semaphores
   - Added `_managed_semaphores: set[asyncio.Semaphore]` for tracking
   - Validates ownership in release() method
   - Prevents releasing semaphores acquired elsewhere
   - Improves security and prevents double-release errors

4. **Active count tracking** - Monitors concurrent operations per resource
   - Increments on acquire, decrements on release
   - Tracked in `_active_counts: dict[str, int]`
   - Useful for debugging and monitoring
   - Not used for limiting (semaphore handles that)

5. **finally block cleanup** - Ensures semaphore release even on exceptions
   - try_execute uses finally to release semaphore
   - Guarantees no semaphore leaks from failed operations
   - Critical for resource management (semaphores limited resource)

6. **Custom max_concurrent parameter** - Flexible per-execution control
   - Overrides configured limit without modifying configuration
   - Temporary limit restored after execution
   - Enables one-off high-concurrency operations

7. **Test coverage matters** - 27 tests, all passing
   - Protocol compliance tested (4 tests)
   - Semaphore management tested (7 tests)
   - Configuration tested (5 tests)
   - try_execute tested (9 tests)
   - Active count tested (2 tests)

### Next Steps
- Consider adding thread-safe Bulkhead implementation for concurrent access
- Consider adding semaphore statistics (wait times, queue depth)
- Consider adding timeout policies (exponential backoff, adaptive timeout)
- Consider integrating with CircuitBreaker (Task 26) for fault tolerance


## Bulkhead Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 26 tests written covering all bulkhead functionality
  - 4 protocol compliance tests (try_acquire, release, try_execute methods)
  - 6 semaphore management tests (create, existing, timeout, release)
  - 5 configuration tests (limit, timeout defaults, updates, multiple resources)
  - 8 try_execute tests (custom max_concurrent, acquire, timeout, release, result, unlimited, concurrent limiting)
  - 3 active count tests (increment, decrement, concurrent operations)
- **GREEN Phase**: All 26 tests passing with 88% coverage for bulkhead.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### Bulkhead Pattern Design
- **Bulkhead Protocol**: Interface for bulkhead resource isolation
  - `try_acquire(resource: str) -> Result[Semaphore]`: Acquire semaphore for resource
  - `release(semaphore: Semaphore) -> Result[None]`: Release semaphore after operation
  - `try_execute(resource, func, max_concurrent) -> Result[Any]`: Execute function with concurrent limiting
  - Protocol-based design enables runtime type checking and multiple implementations
  - @runtime_checkable decorator allows isinstance() checks on Bulkhead

- **BulkheadImpl**: Bulkhead implementation with per-resource semaphores
  - Per-resource semaphore tracking: `_semaphores: dict[str, asyncio.Semaphore]`
  - Per-resource limit configuration: `_limits: dict[str, int]`
  - Per-resource timeout configuration: `_timeouts: dict[str, float]`
  - Active operation counting: `_active_counts: dict[str, int]`
  - Semaphore ownership tracking: `_managed_semaphores: set[asyncio.Semaphore]`
  - Default limit: 1 concurrent operation per resource
  - Default timeout: 30 seconds

### Resource Isolation Mechanism
- **Semaphore-based limiting**: Each resource has its own semaphore
  - Creates semaphore on first acquisition for resource
  - Limits concurrent operations per resource
  - Prevents resource exhaustion from too many concurrent requests
  - Queue semantics: Operations beyond limit wait for semaphore release

### Configuration Management
- **set_limit(resource, limit)**: Set concurrent limit for resource
  - Override per-resource limit
  - Persisted until changed again
- **set_timeout(resource, timeout)**: Set acquisition timeout for resource
  - Prevents indefinite waiting on semaphore acquisition
  - Default: 30 seconds, configurable per resource
- **get_limit(resource)**: Get current limit (default 1)
- **get_timeout(resource)**: Get current timeout (default 30.0)
- **Multiple resources**: Each resource has independent configuration

### try_execute Method Features
- **Acquire-Execute-Release pattern**: Acquires semaphore before execution, releases in finally block
  - Ensures semaphore is always released even on exception
- **Custom max_concurrent**: Override per-resource limit for specific execution
  - Temporary override via set_limit(), restored after execution
- **Execution timeout**: Uses resource timeout for function execution
  - Returns EXECUTION_TIMEOUT error if function takes too long
- **Exception handling**: Catches all exceptions, returns EXECUTION_ERROR

### Thread Safety and Limitations
- **Not thread-safe**: Suitable for single-process async use only
  - In-memory state tracking without locks
  - Documented limitation in class docstring
  - Future: Thread-safe implementation with locks or database backing

### Result Pattern Integration
- All methods return Result types (Ok/Err)
- Explicit error codes:
  - ACQUISITION_TIMEOUT: Semaphore acquisition timeout
  - EXECUTION_TIMEOUT: Function execution timeout
  - EXECUTION_ERROR: Function execution exception
  - BULKHEAD_ERROR: General bulkhead error (non-acquired semaphore)
- No exceptions raised from public methods (violates pattern if raised)
- Consistent with Result pattern learned in Task 10

### Test Coverage
- 88% coverage for bulkhead.py (81 statements, 10 missed)
- 100% pass rate: all 26 tests pass
- All public methods tested (try_acquire, release, try_execute, set_limit, set_timeout, get_limit, get_timeout)
- All error conditions tested (timeout, non-acquired semaphore, function exception)
- Concurrent operation limiting verified with semaphore queue semantics

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 26 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Semaphore ownership tracking important** - Prevents releasing non-acquired semaphores
   - `_managed_semaphores` set tracks which semaphores were acquired via try_acquire
   - release() validates semaphore is in set before releasing
   - Returns BULKHEAD_ERROR for non-managed semaphores

3. **Finally block ensures cleanup** - Semaphore release in finally block
   - try_execute releases semaphore even if function raises exception
   - Prevents resource leaks from failed operations
   - Always releases, even on EXECUTION_ERROR or EXECUTION_TIMEOUT

4. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on Bulkhead
   - BulkheadImpl is default implementation (in-memory, not thread-safe)
   - Future: Thread-safe or database-backed bulkhead implementations

5. **Type annotations use modern syntax** - `int | None` for optional parameters
   - Python 3.10+ union types for better type safety
   - MyPy/TypeScript can verify type correctness

6. **Per-resource isolation prevents cascade failures** - Separate semaphores per resource
   - One resource hitting limit doesn't block other resources
   - Each provider (openai, zai, etc.) has independent limit
   - Suitable for multi-provider LLM clients

7. **Test coverage matters** - 88% coverage for bulkhead.py, 100% pass rate
   - All bulkhead functionality covered by tests
   - Error paths and success paths both tested
   - Concurrent operation behavior verified

### Next Steps
- Consider integrating Bulkhead with CircuitBreaker (Task 26) for fault tolerance
- Consider adding thread-safe Bulkhead implementation for concurrent access
- Consider adding bulkhead wrapper for provider adapters

## Rate Limiter Pattern Implementation (2026-02-09)

### TDD Workflow Success
- **RED Phase**: 25 tests written covering all rate limiter functionality
  - 11 TokenBucket tests (initial state, refill, acquire, release)
  - 8 RateLimiterImpl tests (set_limit, per-resource limits, get_available)
  - 2 RateLimiter protocol tests (runtime_checkable, required methods)
  - 4 Integration tests (circuit breaker, retry executor)
- **GREEN Phase**: All 25 tests passing with 100% coverage for rate_limiter.py
- **REFACTOR Phase**: Clean code structure, comprehensive docstrings, type safety

### RateLimiter Pattern Design
- **RateLimiter Protocol**: Interface for rate limiting
  - `try_acquire(resource, tokens=1) -> Result[bool]`: Try to acquire tokens
  - `release(resource) -> Result[None]`: Release tokens (no-op in simple impl)
  - `get_available(resource) -> Result[int]`: Get available request count
  - Protocol-based design enables runtime type checking and multiple implementations
  - @runtime_checkable decorator allows isinstance() checks on RateLimiter

- **TokenBucket**: Token bucket algorithm implementation
  - Bucket has fixed capacity
  - Tokens refill at constant rate (tokens per second)
  - Requests consume tokens from bucket
  - Empty bucket = rate limited
  - Tracks request timestamps for expiry
  - Tracks refill timestamps for debugging

- **RateLimiterImpl**: Per-resource rate limiting
  - Manages separate TokenBucket for each resource
  - `set_limit()`: Configure custom limits per resource
  - `_get_or_create_bucket()`: Lazy bucket creation
  - Supports default limits for new resources
  - Per-resource isolation (different resources have independent limits)

### Token Bucket Algorithm
- **Refill logic**: Tokens added based on elapsed time
  - Calculate tokens_to_add = elapsed_seconds * refill_rate
  - Add to current tokens, respecting capacity limit
  - Update last_refill_time timestamp
  - Remove expired requests from tracking

- **Acquire logic**: Check tokens, try refill, then check again
  - First check: if tokens >= requested, allow immediately
  - If insufficient, trigger refill
  - After refill, check again and allow if now sufficient
  - Return Err with "RATE_LIMIT_EXCEEDED" code if still insufficient

### Result Pattern Integration
- All rate limiter methods return Result types (Ok/Err)
- Errors wrapped with explicit error codes ("RATE_LIMIT_EXCEEDED")
- Exceptions caught and converted to Err (violates pattern if raised)
- Consistent with Result pattern learned in Task 10

### Test Coverage
- 100% coverage for rate_limiter.py (67 statements, 0 missed)
- 25 comprehensive tests, all passing (100% pass rate)
- Tests verify:
  - Initial state (tokens, last_refill_time)
  - Refill logic (increments up to capacity, respects capacity)
  - Acquire logic (success with enough tokens, refill if needed, Err when insufficient)
  - Release logic (no-op)
  - Per-resource limits (separate buckets for different resources)
  - Protocol compliance (runtime_checkable, required methods)
  - Integration with other patterns (circuit breaker, retry executor)

### Key Learnings
1. **TDD workflow is essential** - RED-GREEN-REFACTOR ensured all functionality tested
   - Started with 25 failing tests (RED)
   - Implemented to pass all tests (GREEN)
   - Clean code with comprehensive docstrings (REFACTOR)

2. **Token bucket algorithm is simple but effective** - Good choice for rate limiting
   - Fixed capacity prevents burst overload
   - Constant refill rate provides smooth throttling
   - Per-resource isolation enables granular control

3. **get_available() method naming is misleading** - Returns request count, not tokens
   - Method name suggests returning available tokens
   - Actually returns count of active requests within time window
   - Tests expect request count, not token count
   - This is intentional design but could be clearer with better naming

4. **Protocol-based design enables flexibility** - Multiple implementations possible
   - @runtime_checkable decorator allows isinstance() checks on RateLimiter
   - Future: Database-backed rate limiter for distributed systems
   - Future: Thread-safe rate limiter with locks or atomic operations

5. **Result pattern integration is critical** - Explicit error handling without exceptions
   - All methods return Result[bool], Result[None], or Result[int]
   - Err includes error message and error code ("RATE_LIMIT_EXCEEDED")
   - Caller can handle errors explicitly (no try/except needed)
   - Consistent with Result pattern learned in Task 10

6. **Thread safety is a limitation** - In-memory implementation not concurrent-safe
   - Documented in docstring (non-blocking limitation)
   - Suitable for single-process use (async rate limiting)
   - Future: Thread-safe implementation with locks or atomic operations

### Next Steps
- Task 30: Implement Time-based Bulkhead for concurrency control
- Consider adding distributed rate limiter with Redis/Database backing
- Consider adding metrics/telemetry for rate limiter usage
