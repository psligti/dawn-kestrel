# Dawn Kestrel Architecture

## Overview

Dawn Kestrel is an **async/sync AI agent SDK** with FSM-based workflow orchestration, session management, and pluggable UI integration. It provides:

- **Thread-safe state machine** with hierarchical composition
- **Dual execution paths** (sync + async)
- **Agent orchestration** with parallel execution support
- **Session lifecycle management** via OpenCodeClient
- **Result-based error handling** throughout
- **REACT-enhanced traceability** with ThinkingFrame/ReactStep

**Target Users**: Developers building agentic systems, AI-powered code review tools, workflow automation engines.

---

## Core Components

### 1. Finite State Machine (FSM)

**Location:** `dawn_kestrel/workflow/fsm.py`

**Purpose:** Thread-safe state machine with REACT traceability and hierarchical composition support.

**Key Features:**

| Feature | Implementation | Details |
|---------|----------------|---------|
| **Thread Safety** | `threading.RLock` + `asyncio.Lock` | Sync mutations use RLock; async uses asyncio.Lock |
| **State Transitions** | `assert_transition()` + `transition_to()` | Validates allowed transitions via `WORKFLOW_FSM_TRANSITIONS` dict |
| **Result Pattern** | Returns `Ok[T]` / `Err[T]` | Never raises exceptions for invalid transitions |
| **Sync/Async Paths** | `run_fsm()` + `run_fsm_async()` | Dual execution paths with shared transition logic |
| **Hierarchical Composition** | `register_sub_fsm()` / `remove_sub_fsm()` | FSMs can embed other FSMs for complex workflows |
| **REACT Tracing** | `StructuredContext.log` + `ThinkingFrame` | Captures reasoning traces, decisions, context per transition |

**State Map:**
```python
WORKFLOW_FSM_TRANSITIONS = {
    "intake": {"plan", "failed"},
    "plan": {"act", "failed"},
    "act": {"synthesize", "evaluate", "done", "failed"},
    "synthesize": {"evaluate", "failed"},
    "evaluate": {"done", "failed"},
}
```

**State Handlers:**
```python
STATE_HANDLERS = {
    "intake": intake_handler,
    "plan": plan_handler,
    "act": act_handler,
    "synthesize": synthesize_handler,
    "evaluate": evaluate_handler,
}
```

**Key Methods:**
- `__init__(initial_state, changed_files)` - Initialize FSM with context
- `transition_to(next_state)` - Synchronous state transition (with RLock)
- `_transition_to_async(next_state)` - Asynchronous state transition (with asyncio.Lock)
- `run()` - Execute FSM until "done" state (sync)
- `run_fsm_async()` - Execute FSM until "done" state (async)
- `register_sub_fsm(name, sub_fsm)` - Embed sub-FSM for hierarchical workflows
- `remove_sub_fsm(name)` - Remove sub-FSM
- `add_todo(todo)`, `update_todo_status(id, status)` - Context mutations (locked)

**Thread Safety Pattern:**
```python
class FSM:
    def __init__(self, initial_state: str, changed_files: list[str]):
        self._state_lock = threading.RLock()  # Sync mutations
        self._async_state_lock = None  # Lazy-initialized for async path
        self._sub_fsms = {}
        self._context = StructuredContext(
            state=initial_state,
            changed_files=changed_files,
        )

    def transition_to(self, next_state: str) -> Result[str]:
        with self._state_lock:  # Protect state mutations
            transition_result = assert_transition(self._context.state, next_state)
            if transition_result.is_ok():
                self._context.state = next_state
            return transition_result
```

**Async Execution Pattern:**
```python
async def _transition_to_async(self, next_state: str) -> Result[str]:
    if self._async_state_lock is None:
        self._async_state_lock = asyncio.Lock()
    async with self._async_state_lock:  # Protect async mutations
        transition_result = assert_transition(self._context.state, next_state)
        if transition_result.is_ok():
            self._context.state = next_state
        return transition_result
```

**Integration Points:**
- **StructuredContext** (`dawn_kestrel/workflow/models.py`) - Central data container
- **STATE_HANDLERS** - Module-level dict mapping states to handler functions
- **Result** (`dawn_kestrel/core/result.py`) - Error handling pattern

---

### 2. SDK Client (OpenCodeClient)

**Location:** `dawn_kestrel/sdk/client.py`

**Purpose:** Primary API surface for session management, agent execution, and provider configuration.

**Components:**

| Class | Purpose | Execution Model |
|-------|---------|-----------------|
| **OpenCodeAsyncClient** | Async-first API | Async/await throughout |
| **OpenCodeSyncClient** | Sync wrapper around async client | Blocks on async calls |

**Key Capabilities:**

**Session Management:**
```python
async def create_session(title: str, version: str = "1.0.0") -> Result[Session]
async def get_session(session_id: str) -> Result[Session | None]
async def list_sessions() -> Result[list[Session]]
async def delete_session(session_id: str) -> Result[bool]
```

**Agent Operations:**
```python
async def register_agent(agent) -> Result[Any]
async def get_agent(name: str) -> Result[Optional[Any]]
async def execute_agent(agent_name: str, session_id: str,
                    user_message: str, options: Optional[Dict]) -> Result[AgentResult]
```

**Provider Management:**
```python
async def register_provider(name, provider_id, model,
                       api_key=None, is_default=False) -> Result[ProviderConfig]
async def get_provider(name: str) -> Result[Optional[ProviderConfig]]
async def list_providers() -> Result[list[Dict[str, Any]]]
async def remove_provider(name: str) -> Result[bool]
async def update_provider(name, provider_id, model, api_key=None) -> Result[ProviderConfig]
```

**Messaging:**
```python
async def add_message(session_id: str, role: str, content: str) -> Result[str]
```

**Callbacks / Hooks:**
```python
def on_progress(callback: Callable[[int, Optional[str]], None]) -> None
def on_notification(callback: Callable[[Notification], None]) -> None
def on_session_created(callback) -> None
def on_session_updated(callback) -> None
def on_message_added(callback) -> None
def on_session_archived(callback) -> None
```

**Integration Architecture:**

```
OpenCodeAsyncClient
├── DI Container
│   ├── SessionService (session storage/retrieval)
│   ├── AgentRuntime (agent execution engine)
│   └── ProviderRegistry (LLM provider management)
├── Callback Handlers
│   ├── Progress Handler
│   ├── Notification Handler
│   └── Lifecycle Hooks (session_created, updated, etc.)
└── Client Methods
    ├── Session CRUD (create, get, list, delete)
    ├── Agent Operations (register, get, execute)
    ├── Provider Management (register, get, list, remove, update)
    └── Messaging (add_message)
```

**Dependency Injection Pattern:**
```python
class OpenCodeAsyncClient:
    def __init__(self, config: Optional[SDKConfig] = None, ...):
        self._container = build_di_container(config)  # Build DI graph
        self._service = self._container.get_service()
        self._runtime = self._container.get_runtime()
        self._lifecycle = self._container.get_lifecycle()
```

---

### 3. Agent Orchestrator

**Location:** `dawn_kestrel/agents/orchestrator.py`

**Purpose:** Coordinate multiple agents with parallel execution, task lifecycle, and event emission.

**Key Methods:**

| Method | Purpose | Returns |
|--------|---------|---------|
| `delegate_task(task, session_id, user_message, ...)` | Spawn single task | Task ID |
| `execute_task_via_task(...)` | Execute task via AgentRuntime | AgentResult |
| `run_parallel_agents(tasks, ...)` | Spawn multiple agents in parallel | List of Task IDs |
| `cancel_tasks(task_ids)` | Cancel running tasks | Success/failure |
| `get_status(task_id)` | Check task status | TaskStatus |
| `get_result(task_id)` | Retrieve task output | AgentResult |
| `list_tasks(status_filter)` | Query tasks | List[Task] |
| `clear_completed_tasks()` | Cleanup finished tasks | Success/failure |

**Orchestration Flow:**

```
Request
    ↓
AgentOrchestrator.delegate_task()
    ↓
Create Task + Task ID
    ↓
AgentRuntime.execute_agent()
    ├── ContextBuilder (assemble AgentContext)
    ├── ToolPermissionFilter (security gate)
    ├── AISession (provider connection)
    ├── Agent execution (LLM call)
    └── Event emission (AGENT_EXECUTING, AGENT_COMPLETE, etc.)
    ↓
AgentResult returned
    ↓
Store in task registry
    ↓
Poll for completion or wait on events
```

**Parallel Execution Pattern:**
```python
async def run_parallel_agents(self, tasks, session_id, ...):
    task_ids = []
    for task in tasks:
        task_id = await self.delegate_task(task, session_id, ...)
        task_ids.append(task_id)

    # Wait for all tasks to complete
    results = await asyncio.gather(
        *[self._wait_for_completion(tid) for tid in task_ids]
    )

    return results
```

---

### 4. Agent Runtime

**Location:** `dawn_kestrel/agents/runtime.py`

**Purpose:** Execute agents with context building, tool filtering, and session lifecycle integration.

**Execution Flow:**

```python
async def execute_agent(self, agent_name, session_id, user_message, options):
    # 1. Fetch and validate agent
    agent = await self._agent_registry.get_agent(agent_name)
    if not agent:
        return Err(f"Agent {agent_name} not found")

    # 2. Validate session
    session = await self._session_service.get_session(session_id)
    if not session:
        return Err(f"Session {session_id} not found")

    # 3. Build context with ContextBuilder
    context = ContextBuilder() \
        .with_session(session) \
        .with_agent(agent) \
        .with_user_message(user_message) \
        .build()

    # 4. Filter tools (security)
    filtered_tools = ToolPermissionFilter(agent.tools, options.permissions)

    # 5. Construct AISession
    ai_session = AISession(
        provider=self._provider_registry.get_default(),
        context=context,
        tools=filtered_tools,
    )

    # 6. Emit events
    self._event_bus.emit(AGENT_EXECUTING, agent_name, session_id)

    # 7. Execute via provider
    try:
        result = await ai_session.execute()
        self._event_bus.emit(AGENT_COMPLETE, agent_name, session_id, result)
        return Ok(result)
    except Exception as e:
        self._event_bus.emit(AGENT_FAILED, agent_name, session_id, str(e))
        return Err(str(e))
```

**Integration Points:**
- **AgentRegistry** - Look up agent definitions by name
- **SessionService** - Retrieve session context
- **ContextBuilder** - Assemble AgentContext from multiple sources
- **ToolPermissionFilter** - Security gate for tool access
- **ProviderRegistry** - Get LLM provider configuration
- **Event Bus** - Emit lifecycle events

---

### 5. Review Agent Runner

**Location:** `dawn_kestrel/core/harness/runner.py`

**Purpose:** Lightweight runner for review agents using LLM client without full harness.

**Class:** `SimpleReviewAgentRunner`

**Key Methods:**

```python
async def run(self, system_prompt: str, formatted_context: str) -> str
async def run_with_retry(self, system_prompt: str, formatted_context: str) -> str
```

**Usage Pattern:**

```python
runner = SimpleReviewAgentRunner(
    agent_name="security_reviewer",
    allowed_tools=["grep", "read_file"],
    temperature=0.3,
    max_retries=2,
)

result = await runner.run(
    system_prompt="Review for security issues...",
    formatted_context=json.dumps(context),
)

# Returns raw LLM response as string
```

**Use Case:** Isolated review tasks where full harness ContextBuilder is overkill.

---

### 6. Data Models

**Location:** `dawn_kestrel/workflow/models.py`

**Core Models:**

| Model | Purpose | Fields |
|-------|---------|---------|
| **StructuredContext** | Central FSM context container | state, changed_files, todos, subagent_results, consolidated, evaluation, log, user_data |
| **RunLog** | Execution history / REACT traces | frames (list of ThinkingFrame), metadata |
| **ThinkingFrame** | Per-state reasoning trace | state, goals, react_cycles, steps, decision, decision_type |
| **ReactCycle** | REACT reasoning step | observation, reasoning, action |
| **ReactStep** | Individual REACT action | action_type, content, metadata |

**StructuredContext Example:**
```python
@dataclass
class StructuredContext:
    state: str  # Current FSM state
    changed_files: list[str]  # Files modified in workflow
    todos: list[Todo]  # Work items
    subagent_results: dict[str, Any]  # Results from delegated agents
    consolidated: Optional[str]  # Consolidated output
    evaluation: Optional[Evaluation]  # Evaluation metrics
    log: RunLog  # REACT trace history
    user_data: dict[str, Any]  # Arbitrary user data
```

**ThinkingFrame Example:**
```python
@dataclass
class ThinkingFrame:
    state: str  # FSM state that generated this frame
    goals: list[str]  # Goals for this state
    react_cycles: list[ReactCycle]  # REACT reasoning cycles
    steps: list[ThinkingStep]  # Execution steps
    decision: str  # Decision made
    decision_type: DecisionType  # Type of decision (TRANSITION, DELEGATE, etc.)
```

---

### 7. Result Pattern

**Location:** `dawn_kestrel/core/result.py`

**Purpose:** Type-safe error handling without exceptions.

**Pattern:**
```python
@dataclass
class Result[T]:
    value: Optional[T] = None
    error: Optional[Error] = None
    code: Optional[str] = None

    def is_ok(self) -> bool:
        return self.error is None

    def is_err(self) -> bool:
        return self.error is not None

    def unwrap(self) -> T:
        if self.is_err():
            raise ValueError(f"Cannot unwrap Err result: {self.error}")
        return self.value

def Ok[T](value: T) -> Result[T]:
    return Result(value=value, error=None)

def Err[T](error: str, code: Optional[str] = None) -> Result[T]:
    return Result(value=None, error=Error(message=error, code=code), code=code)
```

**Usage Throughout Codebase:**
- FSM transitions: `assert_transition()` returns `Ok(state)` or `Err(error)`
- SDK operations: `create_session()`, `execute_agent()` all return `Result[T]`
- AgentRuntime: `execute_agent()` returns `Result[AgentResult]`

---

## Integration Patterns

### Pattern 1: FSM-Driven Workflow

**How FSM orchestrates workflows:**

```python
fsm = FSM(initial_state="intake", changed_files=modified_files)

# FSM runs through state handlers, each returning next state
result = fsm.run()
if result.is_err():
    print(f"Workflow failed: {result.error}")
else:
    print(f"Workflow completed: {result.value}")
```

**State Handler Pattern:**

```python
def intake_handler(ctx: StructuredContext) -> str:
    frame = ThinkingFrame(state="intake")
    frame.goals = ["Analyze changed files", "Identify review scope"]

    # REACT cycle
    react_cycle = ReactCycle(
        observation=f"Found {len(ctx.changed_files)} changed files",
        reasoning="Need to analyze each file for review relevance",
        action="Categorize files by type and complexity",
    )
    frame.add_react_cycle(react_cycle)

    # Add thinking step
    step = ThinkingStep(
        action_type=ActionType.ANALYZE,
        content=f"Processing {ctx.changed_files}",
    )
    frame.add_step(step)

    # Decision
    frame.decision = "Plan todos for each file"
    frame.decision_type = DecisionType.TRANSITION

    ctx.add_frame(frame)
    return "plan"  # Next state
```

---

### Pattern 2: SDK Client + Agent Execution

**How OpenCodeClient executes agents:**

```python
client = OpenCodeAsyncClient()

# 1. Create session
session_result = await client.create_session(title="PR Review")
if session_result.is_err():
    print(f"Failed to create session: {session_result.error}")
    return

session = session_result.unwrap()

# 2. Execute agent
agent_result = await client.execute_agent(
    agent_name="security_reviewer",
    session_id=session.id,
    user_message="Review this PR for security issues",
    options={"permissions": ["read_file", "grep"]},
)

if agent_result.is_err():
    print(f"Agent failed: {agent_result.error}")
else:
    print(f"Agent output: {agent_result.value.output}")
```

---

### Pattern 3: Orchestrator + Parallel Execution

**How AgentOrchestrator runs parallel agents:**

```python
orchestrator = AgentOrchestrator()

tasks = [
    AgentTask(name="security_reviewer", message="Review for security"),
    AgentTask(name="performance_reviewer", message="Review for performance"),
    AgentTask(name="style_reviewer", message="Review for code style"),
]

# Run all tasks in parallel
task_ids = await orchestrator.run_parallel_agents(
    tasks=tasks,
    session_id=session.id,
    user_messages=[t.message for t in tasks],
    ...,
)

# Wait for completion
results = []
for tid in task_ids:
    result = await orchestrator.get_result(tid)
    results.append(result.unwrap())

# Aggregate results
consolidated = consolidate_results(results)
```

---

### Pattern 4: Context Building + Tool Filtering

**How ContextBuilder assembles AgentContext:**

```python
context = (
    ContextBuilder()
    .with_session(session)  # Add session data
    .with_agent(agent)  # Add agent configuration
    .with_user_message(user_message)  # Add user input
    .with_metadata({"review_type": "security"})  # Add arbitrary metadata
    .build()
)

# Result: AgentContext with all needed data for agent execution
```

**Tool Permission Filtering:**

```python
from dawn_kestrel.core.security import ToolPermissionFilter

filtered_tools = ToolPermissionFilter(
    agent_tools=agent.tools,
    permissions=options.get("permissions", []),
)

# Result: Only tools that match allowed permissions are exposed
```

---

### Pattern 5: Bridge Pattern (SDK ↔ UI)

**How SDK separates from UI components:**

```
┌─────────────────────────────────────────────────┐
│         Dawn Kestrel SDK                │
│  ┌──────────────┐ ┌──────────────┐ │
│  │ FSM          │ │ OpenCodeClient│ │
│  └──────────────┘ └──────────────┘ │
│         ↓                                   │
│  Event Bus (lifecycle events)              │
└─────────────┬─────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│         UI Layer                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │ CLI      │ │  TUI      │ │  Custom   ││
│  │ Click    │ │ Textual   │ │  React   ││
│  └──────────┘ └──────────┘ └──────────┘│
└─────────────────────────────────────────────────┘
```

**Benefits:**
- SDK doesn't depend on any UI framework
- UI components can swap implementations
- Event bus enables reactive UI updates

---

## Data Flow Examples

### Flow 1: Complete Agent Workflow

```
User Request (CLI/TUI/Custom UI)
    ↓
OpenCodeClient.create_session()
    ↓
FSM.run() (or FSM.run_fsm_async())
    ↓
State Handler (e.g., intake_handler)
    ├── Create ThinkingFrame
    ├── Add REACT cycles to RunLog
    ├── Add steps to RunLog
    └── Return next state
    ↓
AgentOrchestrator.delegate_task() (if state requires delegation)
    ↓
AgentRuntime.execute_agent()
    ├── ContextBuilder.assemble()
    ├── ToolPermissionFilter.filter()
    ├── AISession.execute()
    └── Event Bus.emit()
    ↓
AgentResult returned
    ↓
FSM.transition_to() (next state)
    ↓
Repeat until state == "done"
    ↓
FSM completes → Return final result
```

---

### Flow 2: Parallel Agent Review

```
PR Review Request
    ↓
OpenCodeClient.create_session(title="PR #123 Review")
    ↓
AgentOrchestrator.run_parallel_agents()
    ├── Task 1: Security Review → AgentRuntime.execute_agent()
    ├── Task 2: Performance Review → AgentRuntime.execute_agent()
    ├── Task 3: Style Review → AgentRuntime.execute_agent()
    └── Task 4: Documentation Review → AgentRuntime.execute_agent()
    ↓
Event Bus (events: AGENT_EXECUTING, AGENT_COMPLETE, AGENT_FAILED)
    ↓
UI Layer updates in real-time (progress bars, status indicators)
    ↓
All tasks complete → Consolidate results
    ↓
OpenCodeClient.add_message() (store consolidated review)
    ↓
Return final review to user
```

---

## Testing Strategy

### Test Structure

```
dawn_kestrel/
├── tests/
│   ├── core/
│   │   └── test_fsm.py           # Core FSM behavior
│   ├── workflow/
│   │   └── test_workflow_fsm.py  # End-to-end workflows
│   ├── sdk/
│   │   └── test_sdk_async_client.py  # SDK API tests
│   ├── integration/
│   │   └── test_end_to_end_workflows.py  # Full system tests
│   └── review/
│       └── agents/
│           ├── test_security_reviewer.py    # Security agent tests
│           └── test_unit_tests_reviewer.py  # Review runner tests
```

### Test Patterns

**1. FSM Tests:**
- State transitions (valid/invalid)
- Thread safety (concurrent transitions)
- Async execution (async state machine)
- Hierarchical composition (sub-FSMs)

**2. SDK Tests:**
- Session CRUD (create, get, list, delete)
- Agent execution (execute_agent)
- Provider management (register, get, list, remove, update)
- Callbacks (on_progress, on_notification)

**3. Integration Tests:**
- End-to-end workflows (FSM + Orchestrator + SDK)
- Parallel agent execution
- Event emission and handling

---

## File Structure

```
dawn_kestrel/
├── workflow/
│   ├── fsm.py              # Core FSM implementation
│   └── models.py            # Data models (StructuredContext, RunLog, etc.)
├── sdk/
│   └── client.py            # OpenCodeAsyncClient / OpenCodeSyncClient
├── agents/
│   ├── orchestrator.py      # AgentOrchestrator
│   ├── runtime.py           # AgentRuntime
│   └── agent_registry.py    # Agent definitions
├── core/
│   ├── result.py           # Result pattern (Ok/Err)
│   ├── harness/
│   │   └── runner.py        # SimpleReviewAgentRunner
│   └── security/
│       └── permissions.py    # ToolPermissionFilter
├── event_bus/
│   └── bus.py              # Event emission and subscription
└── di/
    └── container.py        # Dependency injection setup
```

---

## Key Architectural Decisions

### 1. Result Pattern Over Exceptions

**Why:** Type-safe error handling without try/catch everywhere.

**Trade-off:** More verbose than exceptions, but safer and explicit.

---

### 2. Thread Safety With RLock + asyncio.Lock

**Why:** Support both sync and async execution paths without race conditions.

**Trade-off:** Slightly more complex than single lock, but enables dual execution models.

---

### 3. Bridge Pattern (SDK ↔ UI)

**Why:** SDK is framework-agnostic, enabling CLI, TUI, web UI, etc.

**Trade-off:** Additional abstraction layer, but maximum flexibility.

---

### 4. Event-Driven Architecture

**Why:** Decouple components via events (AgentRuntime emits, UI listens).

**Trade-off:** Event bus complexity, but enables real-time updates and loose coupling.

---

### 5. Hierarchical FSM Composition

**Why:** Support complex workflows (e.g., security review with sub-phases).

**Trade-off:** More complex FSM API, but enables sub-workflows.

---

## Performance Characteristics

| Component | Typical Latency | Notes |
|------------|-----------------|--------|
| FSM transition | < 5ms | Lock acquisition + state update |
| Agent execution | 1-10s | Depends on LLM provider and prompt size |
| Session storage | < 50ms | In-memory (SessionService) |
| Parallel agents | ~max(task_time) | Executes in parallel, bound by slowest task |

---

## Security Considerations

### Tool Permission Filtering

**Purpose:** Prevent agents from accessing unauthorized tools/files.

**Implementation:** `ToolPermissionFilter` in `dawn_kestrel/core/security/permissions.py`

**Usage:**
```python
filtered_tools = ToolPermissionFilter(
    agent_tools=agent.tools,
    permissions=options.get("permissions", []),
)

# Only expose tools that match allowed permissions
```

---

## Extensibility Points

### Adding New Agent Types

**Location:** `dawn_kestrel/agents/agent_registry.py`

**Pattern:**
```python
@register_agent("my_custom_agent")
class MyCustomAgent(BaseAgent):
    tools = ["grep", "read_file"]
    system_prompt = "You are a custom agent for..."
```

### Adding New FSM States

**Location:** `dawn_kestrel/workflow/fsm.py`

**Pattern:**
```python
# 1. Add to transition map
WORKFLOW_FSM_TRANSITIONS["existing_state"].add("new_state")

# 2. Create handler
def new_state_handler(ctx: StructuredContext) -> str:
    frame = ThinkingFrame(state="new_state")
    # ... handler logic
    ctx.add_frame(frame)
    return "next_state"

# 3. Register handler
STATE_HANDLERS["new_state"] = new_state_handler
```

### Custom UI Integration

**Location:** Your own UI layer

**Pattern:**
```python
from dawn_kestrel.sdk import OpenCodeAsyncClient

client = OpenCodeAsyncClient()

# Subscribe to events
client.on_agent_executing(lambda name: update_progress(name))
client.on_agent_complete(lambda name, result: show_result(name, result))

# Execute agents
result = await client.execute_agent(...)
```

---

## Versioning and Compatibility

**Current Version:** 1.0.0

**API Stability:**
- **Stable:** FSM, SDK client, orchestrator core APIs
- **Evolving:** Agent registry, tool definitions, event schema

**Deprecation Policy:**
- Features marked `@deprecated` for 2 versions before removal
- Migration guides provided for breaking changes

---

## Future Enhancements

### Potential Improvements

1. **Distributed Execution** - Run agents across multiple machines
2. **Streaming Responses** - Stream LLM outputs in real-time
3. **Adaptive Orchestration** - Dynamically adjust agent parallelism based on load
4. **Enhanced Tracing** - OpenTelemetry integration for distributed tracing
5. **State Persistence** - Save/resume FSM state across sessions

---

## Glossary

| Term | Definition |
|-------|-----------|
| **FSM** | Finite State Machine |
| **REACT** | Reasoning pattern: Reason, Observe, Act, (Think) |
| **ThinkingFrame** | Per-state reasoning trace with REACT cycles |
| **Result Pattern** | `Ok[T]` / `Err[T]` error handling without exceptions |
| **AgentRuntime** | Engine that executes agents with context building |
| **AgentOrchestrator** | Coordinates multiple agents with parallel execution |
| **OpenCodeClient** | SDK API surface for session/agent operations |
| **Bridge Pattern** | Separates SDK from UI components for flexibility |

---

## References

- **Getting Started:** `docs/getting-started.md`
- **Examples:** `docs/examples/`
- **API Reference:** See docstrings in source files
- **Test Coverage:** Run `pytest dawn_kestrel/tests/ --cov=dawn_kestrel`
