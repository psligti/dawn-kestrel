# Python SDK Gaps and Next Steps

This document outlines the gaps identified in the Python SDK based on the custom agent application example, and proposes a plan for addressing them.

## Executive Summary

The Python SDK provides a **surprisingly solid foundation** with:
- ✅ Session and message management
- ✅ Async/sync clients
- ✅ Tool framework and registry (`ToolRegistry`, `ToolExecutionManager`)
- ✅ Built-in agent definitions (4 agents)
- ✅ Skill loading from markdown files
- ✅ Basic storage layer (JSON-based)
- ✅ **AI Session runner** with streaming support (`AISession`)
- ✅ **Tool execution** with permission checking (`ToolExecutionManager`)
- ✅ **Provider abstraction** (`ProviderID`, provider implementations)
- ✅ **Token usage and cost tracking** (`TokenUsage`, cost calculation)
- ✅ **Agent lifecycle management** (`AgentManager`)
- ✅ **Tool state tracking** (`ToolState`, event bus)
- ✅ **Doom loop detection** for tools

However, several key features are **missing or incomplete** for building full-featured agent applications:

1. **No Memory Management System** - No dedicated memory storage, embeddings, or retrieval
2. **Agent Execution Integration Issues** - `AgentExecutor` exists but creates fake Session objects
3. **Missing Agent-Tool Permission Filtering** - `tool_manager` doesn't expose `tool_registry` attribute
4. **No Skill Injection** - Skills loaded but not injected into agent prompts
5. **No Custom Agent Registration API** - Cannot add custom agents beyond built-ins
6. **No Explicit Context Builder** - Message history building is internal to `AISession`
7. **No Multi-Agent Orchestration** - Cannot delegate between agents (skeleton code exists)
8. **No Tool Execution History Storage** - Tool state tracked in memory only, not persisted
9. **BUG: SessionStorage Constructor** - Missing `base_dir` parameter in SDK client
11. **BUG: SessionStorage Constructor** - `SessionStorage()` called without `base_dir` required parameter (line 53 in `sdk/client.py`)

---

## Detailed Gaps Analysis

### What Already Works ✅

Before diving into gaps, it's worth noting what the SDK **already does well**:

| Feature | Implementation | Status |
|----------|----------------|----------|
| **AI Session Management** | `AISession` class with streaming support | ✅ Complete |
| **Tool Execution** | `ToolExecutionManager` with permission checking | ✅ Complete |
| **Tool Framework** | `Tool` base class, `ToolRegistry` | ✅ Complete |
| **Built-in Tools** | 23 tools (bash, read, write, grep, glob, etc.) | ✅ Complete |
| **Agent Lifecycle** | `AgentManager` with state tracking and events | ✅ Complete |
| **Agent Definitions** | 4 built-in agents (build, plan, general, explore) | ✅ Complete |
| **Provider Abstraction** | `ProviderID`, provider implementations | ✅ Complete |
| **Token Usage Tracking** | `TokenUsage` model, cost calculation | ✅ Complete |
| **Tool State Tracking** | `ToolState`, event bus for state updates | ✅ Complete (in-memory) |
| **Skill Loading** | `SkillLoader` discovers SKILL.md files | ✅ Complete |
| **Session/Message Storage** | `SessionStorage`, `MessageStorage` with JSON persistence | ✅ Complete |
| **Message History** | Built into `AISession.process_message()` | ✅ Complete |
| **Event Bus** | Pub/sub for session, agent, tool events | ✅ Complete |
| **Doom Loop Detection** | `ToolExecutionManager.check_doom_loop()` | ✅ Complete |
| **SDK Client API** | `OpenCodeAsyncClient`, `OpenCodeSyncClient` | ⚠️ Has critical bug |

**Conclusion**: The SDK has a **surprisingly complete foundation**. The gaps are primarily:
1. **Integration issues** between components (AgentExecutor, ToolExecutionManager)
2. **Missing features** (memory, skill injection, custom agent registration)
3. **API gaps** (no public context builder, no agent registry)

---

### 1. Memory Management System ❌

**Current State**: Basic `SessionStorage` for sessions/messages only. No dedicated memory layer.

**Missing Features**:
```python
# What's needed:
class MemoryManager:
    async def store_memory(
        self,
        session_id: str,
        content: str,
        metadata: Dict[str, Any],
        embeddings: Optional[List[float]] = None
    ) -> str: ...

    async def search_memory(
        self,
        session_id: str,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]: ...

    async def summarize_memories(
        self,
        session_id: str,
        since: float
    ) -> MemorySummary: ...
```

**Impact**:
- Cannot maintain long-term conversation context
- No semantic search across past interactions
- No memory compression for long sessions
- No cross-session memory sharing

**Priority**: HIGH - Core agent capability

---

### 2. Agent Runtime and Execution Engine ⚠️ (Partial)

**Current State**: `AgentManager` tracks lifecycle. `AgentExecutor` exists but has integration issues (see Bug #2, #3). `AISession` provides full AI interaction with tools.

**Issues**:
- `AgentExecutor` creates fake `Session` objects with empty fields
- `AgentExecutor._filter_tools_for_agent()` fails because `tool_manager.tool_registry` doesn't exist
- No connection between `AgentExecutor` and real session storage

**What Works**:
- `AISession` handles AI streaming, tool execution, message creation
- `ToolExecutionManager` executes tools with permission checking
- Event bus publishes agent lifecycle events

**Missing Integration**:
```python
# What's needed for AgentExecutor to work correctly:
class AgentRuntime:
    """Unified agent runtime that connects AgentExecutor with AISession"""

    async def execute_agent(
        self,
        agent: Agent,
        session: Session,  # Real session, not session_id
        user_message: str,
        tools: ToolRegistry,  # Passed in, not from tool_manager
        skills: List[Skill]
    ) -> AgentResult:
        """
        Combines AgentExecutor with AISession:
        1. Get tools from registry, filter by agent permissions
        2. Inject skills into system prompt
        3. Create AISession with tools
        4. Execute and track with AgentManager
        """
        ...
```

**Impact**:
- Agent definitions are metadata only
- Cannot use custom agents (no execution path)
- `AgentExecutor` is broken (AttributeError when filtering tools)

**Priority**: HIGH - Core functionality broken

---

### 3. Agent-Tool Permission Integration ⚠️ (Broken by Bug #3)

**Current State**: `AgentExecutor._filter_tools_for_agent()` exists and implements permission logic. `ToolExecutionManager` has `tool_registry`. Integration broken.

**What Exists**:
```python
# AgentExecutor._filter_tools_for_agent() - Works correctly
def _filter_tools_for_agent(self, agent) -> List[str]:
    if not self.tool_manager:
        return []
    all_tools = self.tool_manager.tool_registry.tools.keys()  # ❌ BUG HERE
    allowed_tools = []
    for tool_name in all_tools:
        if self._is_tool_allowed(tool_name, agent.permission):
            allowed_tools.append(tool_name)
    return allowed_tools
```

**What's Missing**:
- `ToolExecutionManager` should accept external `ToolRegistry`
- `AISession` should pass tool registry to `ToolExecutionManager`
- Permission filtering should be applied before tools are passed to AI

**Impact**:
- Permission filtering fails with AttributeError
- All agents would get all tools (security risk)
- Agent-specific access controls don't work

**Priority**: HIGH - Security model broken

**Fix** (covered in Bug #3):

---

### 4. Skill Injection into Agent Prompts ❌

**Current State**: `SkillLoader` can discover skills. No mechanism to inject them into agent context.

**Missing Features**:
```python
# What's needed:
class SkillInjector:
    def build_agent_prompt(
        self,
        agent: Agent,
        skills: List[Skill],
        base_prompt: str
    ) -> str:
        """
        Inject loaded skills into agent system prompt.

        Format:
        ```
        You have access to the following skills:
        - skill-name: description
          content: [full skill content]

        [base prompt]
        ```
        """
        ...
```

**Impact**:
- Skills cannot be used by agents
- No way to extend agent capabilities dynamically
- Skill system is non-functional

**Priority**: MEDIUM - Feature enhancement

---

### 5. Custom Agent Registration ❌

**Current State**: Only built-in agents available. No API to register custom agents.

**Missing Features**:
```python
# What's needed:
class AgentRegistry:
    async def register_agent(self, agent: Agent) -> None: ...
    async def get_agent(self, name: str) -> Optional[Agent]: ...
    async def list_agents(self) -> List[Agent]: ...
    async def remove_agent(self, name: str) -> bool: ...
```

**Impact**:
- Cannot create application-specific agents
- Built-in agents only
- No agent discoverability

**Priority**: MEDIUM - Extensibility

---

### 6. Context Building Pipeline ⚠️ (Internal Implementation)

**Current State**: `AISession._build_llm_messages()` builds message history internally. No dedicated public context builder.

**What Exists**:
```python
# AISession._build_llm_messages() - Internal method
def _build_llm_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
    """Build LLM-format messages from OpenCode messages"""
    # Converts user/assistant messages to provider format
    # Handles text extraction from message parts
```

**Missing Public API**:
```python
# What's needed for external use:
class ContextBuilder:
    """Public API for building agent execution context"""

    async def build_agent_context(
        self,
        session: Session,
        agent: Agent,
        tools: Dict[str, Tool],
        skills: List[Skill],
        memories: Optional[List[MemoryEntry]] = None
    ) -> AgentContext:
        """
        Build complete context for agent execution.

        Includes:
        - System prompt (base + skills injected)
        - Tool definitions (JSON schema for LLM)
        - Conversation history (from session)
        - Relevant memories (retrieved and ranked)
        - Session metadata (project_id, directory, etc.)
        """
        system_prompt = self._build_system_prompt(agent, skills)
        tool_definitions = self._build_tool_schemas(tools)
        messages = await self._get_message_history(session)
        return AgentContext(...)

    async def _build_system_prompt(self, agent: Agent, skills: List[Skill]) -> str:
        """Inject skills into agent's base prompt"""
        ...
```

**Impact**:
- Context building is internal to `AISession`
- Cannot customize context for special use cases
- No skill injection mechanism (skills are loaded but not used)

**Priority**: MEDIUM - Feature enhancement (internal impl exists, just needs public API)

---

### 7. Multi-Agent Orchestration ❌

**Current State**: `AgentExecutor` has skeleton code but no actual delegation.

**Missing Features**:
```python
# What's needed:
class AgentOrchestrator:
    async def delegate_task(
        self,
        from_agent: Agent,
        to_agent_name: str,
        task: str,
        session_id: str,
        tool_ids: List[str],
        skill_names: List[str]
    ) -> AgentResult: ...

    async def run_parallel_agents(
        self,
        tasks: List[AgentTask],
        session_id: str
    ) -> List[AgentResult]: ...
```

**Impact**:
- No agent-to-agent collaboration
- No parallel execution
- Cannot build multi-agent workflows

**Priority**: MEDIUM - Advanced feature

---

### 8. Tool Execution State Tracking ❌

**Current State**: `ToolExecutionManager` tracks tool state in memory and emits events. No persistence.

**Missing Features**:
```python
# What's needed:
class ToolExecutionTracker:
    async def persist_execution(
        self,
        session_id: str,
        message_id: str,
        tool_id: str,
        execution: ToolState
    ) -> None: ...

    async def get_execution_history(
        self,
        session_id: str,
        limit: int = 100
    ) -> List[ToolState]: ...
```

**Impact**:
- Tool execution state is lost after session ends
- Cannot audit tool calls across sessions
- No historical debugging data

**Priority**: LOW - Debugging/Observability (state tracking exists, just needs persistence)

---

### 9. Provider/Model Abstraction Layer ✅ (Partially Implemented)

**Current State**: `ProviderID` enum and provider implementations exist in `providers/` module. `AISession` uses provider abstraction.

**Missing Features**:
```python
# What's needed:
class ProviderRegistry:
    """Manage multiple provider configurations"""
    async def list_providers(self) -> List[ProviderConfig]: ...
    async def get_default_provider(self) -> ProviderConfig: ...
    async def validate_provider(self, config: ProviderConfig) -> bool: ...
```

**Impact**:
- Can only use providers defined in code
- No runtime provider configuration
- Model selection is manual

**Priority**: LOW - Flexibility (core provider abstraction exists, just needs registry)

---

### 10. Session Lifecycle Hooks ❌

**Current State**: Basic create/delete. No lifecycle events or hooks.

**Missing Features**:
```python
# What's needed:
class SessionLifecycle:
    async def on_session_created(self, session: Session) -> None: ...
    async def on_session_updated(self, session: Session) -> None: ...
    async def on_message_added(self, session: Session, message: Message) -> None: ...
    async def on_session_archived(self, session: Session) -> None: ...
    async def on_session_compacted(self, session: Session) -> None: ...
```

**Impact**:
- Cannot hook into session events
- No triggers for automation
- Limited extensibility

**Priority**: LOW - Event system

---

## Proposed Implementation Plan

### Phase 1: Core Agent Execution (HIGH Priority)

**Goal**: Enable basic agent execution with tool support.

**Deliverables**:
1. `AgentRegistry` - Register and retrieve custom agents
2. `ToolPermissionFilter` - Filter tools based on agent permissions
3. `ContextBuilder` - Build agent context from components
4. `AgentRuntime` - Execute agents with tools
5. `SkillInjector` - Inject skills into agent prompts

**Estimated Effort**: 2-3 weeks

**Success Criteria**:
- Can register custom agent
- Agent can execute with filtered tools
- Skills are injected into agent prompt
- Basic agent-to-user interaction works

---

### Phase 2: Memory System (HIGH Priority)

**Goal**: Add long-term memory capabilities.

**Deliverables**:
1. `MemoryStorage` - Dedicated memory storage layer
2. `MemoryManager` - Store, search, and retrieve memories
3. `MemoryEmbedder` - Generate embeddings for semantic search
4. `MemorySummarizer` - Compress long conversations
5. Integration with `ContextBuilder` for memory injection

**Estimated Effort**: 2-3 weeks

**Dependencies**:
- Vector database (e.g., ChromaDB, FAISS, or simple SQLite with vectors)
- Embedding model (e.g., OpenAI embeddings, sentence-transformers)

**Success Criteria**:
- Can store conversation memories
- Can search memories semantically
- Memories are injected into agent context
- Long sessions can be summarized

---

### Phase 3: Multi-Agent Orchestration (MEDIUM Priority)

**Goal**: Enable agent delegation and parallel execution.

**Deliverables**:
1. `AgentOrchestrator` - Coordinate multiple agents
2. `AgentTask` - Define tasks for agent execution
3. `AgentResult` - Agent execution results
4. Integration with `ToolRegistry` for task tool

**Estimated Effort**: 1-2 weeks

**Success Criteria**:
- One agent can delegate to another
- Parallel agent execution works
- Task tool can spawn sub-agents

---

### Phase 4: Enhanced Features (MEDIUM Priority)

**Goal**: Add provider management and advanced features.

**Deliverables**:
1. `ProviderRegistry` - Manage AI providers
2. `ProviderConfig` - Provider configuration
3. `ToolExecutionTracker` - Track tool executions
4. `SessionLifecycle` - Session lifecycle hooks

**Estimated Effort**: 2 weeks

**Success Criteria**:
- Can configure multiple providers
- Tool executions are tracked
- Can hook into session events

---

### Phase 5: Polish and Documentation (LOW Priority)

**Goal**: Improve developer experience.

**Deliverables**:
1. Complete API reference docs
2. More examples (custom agents, tools, skills)
3. Performance benchmarks
4. Error handling improvements
5. Logging and observability

**Estimated Effort**: 1-2 weeks

---

## Data Model Changes Required

### New Models

```python
@dataclass
class AgentResult:
    """Result from agent execution"""
    agent_name: str
    response: str
    parts: List[Part]
    metadata: Dict[str, Any]
    tools_used: List[str]
    tokens_used: TokenUsage
    duration: float

@dataclass
class MemoryEntry:
    """Stored memory with embeddings"""
    id: str
    session_id: str
    content: str
    embedding: Optional[List[float]]
    metadata: Dict[str, Any]
    created: float
    relevance_score: float = 0.0

@dataclass
class AgentContext:
    """Complete context for agent execution"""
    system_prompt: str
    tools: Dict[str, Tool]
    messages: List[Message]
    memories: List[MemoryEntry]
    session: Session
    agent: Agent

@dataclass
class AgentTask:
    """Task for agent execution"""
    agent_name: str
    description: str
    tool_ids: List[str]
    skill_names: List[str]
    options: Dict[str, Any]
```

---

## Existing Bugs Found

### Bug #1: SessionStorage Missing base_dir Parameter

**Location**: `opencode_python/src/opencode_python/sdk/client.py:53`

**Issue**:
```python
storage = SessionStorage()  # ❌ Missing required base_dir parameter
```

**Expected**:
```python
storage = SessionStorage(base_dir=config.storage_path or Path.home() / ".local" / "share" / "opencode-python")
```

**Impact**:
- Code will fail at runtime
- SDK client cannot initialize properly

**Fix Priority**: CRITICAL - Blocks all SDK usage

**Recommended Fix**:
Update `OpenCodeAsyncClient.__init__()` to pass `base_dir` from `config.storage_path` or default to standard location.

---

### Bug #2: AgentExecutor Creates Fake Sessions

**Location**: `opencode_python/src/opencode_python/agents/__init__.py:190-198, 232-240`

**Issue**:
```python
session = Session(
    id=session_id,
    slug=session_id,
    project_id="",  # ❌ Empty
    directory="",   # ❌ Empty
    title="",      # ❌ Empty
    version="1.0",
    metadata={}
)
```

**Impact**:
- `AgentExecutor` doesn't use real session data
- Cannot integrate with actual session storage
- Session metadata (project_id, directory, title) is lost

**Fix Priority**: HIGH - Agent execution doesn't work correctly

**Recommended Fix**:
`AgentExecutor.execute_agent()` should accept a real `Session` object instead of just `session_id`, or fetch it from `session_manager`.

---

### Bug #3: ToolExecutionManager.tool_registry Not Exposed

**Location**: `opencode_python/src/opencode_python/agents/__init__.py:289`

**Issue**:
```python
all_tools = self.tool_manager.tool_registry.tools  # ❌ AttributeError
```

**Root Cause**:
`ToolExecutionManager.__init__()` creates a private `tool_registry`:
```python
class ToolExecutionManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.active_calls: Dict[str, ToolContext] = {}
        self.tool_registry = ToolRegistry()  # Creates empty registry
```

But `AgentExecutor` expects to access `tool_manager.tool_registry.tools`.

**Impact**:
- Cannot filter tools based on agent permissions
- `_filter_tools_for_agent()` fails

**Fix Priority**: HIGH - Agent execution broken

**Recommended Fix**:
1. `ToolExecutionManager` should accept a `ToolRegistry` in constructor
2. Or expose `tool_registry` as a public property
3. `AISession` should pass tools to `ToolExecutionManager`


---

## Storage Schema Changes

### New Storage Tables

```json
// storage/memory/{session_id}/{memory_id}.json
{
  "id": "mem_001",
  "session_id": "ses_123",
  "content": "User prefers dark mode",
  "embedding": [0.1, 0.2, ...],
  "metadata": {"type": "preference"},
  "created": 1234567890.0
}

// storage/agent/{agent_name}.json
{
  "name": "custom_agent",
  "description": "My custom agent",
  "mode": "subagent",
  "permission": [...],
  "native": false
}

// storage/tool_execution/{session_id}/{execution_id}.json
{
  "id": "exec_001",
  "session_id": "ses_123",
  "message_id": "msg_456",
  "tool": "calculator",
  "state": "completed",
  "args": {"operation": "add", "a": 5, "b": 3},
  "output": "8",
  "time_start": 1234567890.0,
  "time_end": 1234567891.0
}
```

---

## API Design Preview

### SDK Client Enhancements

```python
# Extended SDK client with agent support
class OpenCodeAsyncClient:
    # Existing methods...

    async def register_agent(self, agent: Agent) -> None:
        """Register a custom agent"""

    async def get_agent(self, name: str) -> Optional[Agent]:
        """Get agent by name"""

    async def execute_agent(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        options: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """Execute an agent"""

    async def store_memory(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a memory"""

    async def search_memory(
        self,
        session_id: str,
        query: str,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Search memories"""
```

### Usage Example (After Implementation)

```python
from opencode_python.sdk import OpenCodeAsyncClient
from opencode_python.agents import Agent

# Create custom agent
my_agent = Agent(
    name="calculator_bot",
    description="Helps with math calculations",
    mode="subagent",
    permission=[
        {"permission": "calculator", "pattern": "*", "action": "allow"},
    ]
)

# Register and use
client = OpenCodeAsyncClient()
await client.register_agent(my_agent)

session = await client.create_session("Math Help")

result = await client.execute_agent(
    agent_name="calculator_bot",
    session_id=session.id,
    user_message="What is 15 times 23?"
)

print(result.response)  # "15 * 23 = 345"

# Store memory
await client.store_memory(
    session_id=session.id,
    content="User is working on math homework",
    metadata={"type": "context"}
)
```

---

## Testing Strategy

### Unit Tests Required
- `AgentRegistry` tests
- `ToolPermissionFilter` tests (all permission patterns)
- `ContextBuilder` tests
- `MemoryManager` tests
- `AgentRuntime` tests
- `SkillInjector` tests

### Integration Tests Required
- End-to-end agent execution
- Multi-agent delegation
- Memory search and retrieval
- Tool execution with permissions
- Session lifecycle hooks

### Performance Tests Required
- Memory search latency
- Context building for long sessions
- Parallel agent execution
- Tool execution tracking overhead

---

## Dependencies to Consider

### New Python Packages
- `chromadb` or `faiss-cpu` - Vector storage for memory
- `sentence-transformers` - Local embeddings (optional)
- `openai` - Embeddings API (optional)
- `tenacity` - Retry logic for tool execution

### Existing Dependencies
- `aiofiles` - Async file I/O
- `pydantic` - Data validation
- `asyncio` - Async execution

---

## Open Questions

1. **Memory Backend**: Should we default to ChromaDB, FAISS, or implement a simple SQLite + vectors solution?

2. **Embeddings**: Should we require users to provide their own embedding model, or default to OpenAI embeddings?

3. **Agent Isolation**: Should agents run in separate processes/containers for isolation, or just separate async tasks?

4. **Tool Execution Limits**: Should we implement timeouts, rate limits, and resource quotas for tool execution?

5. **Memory Retention**: How long should memories be retained? What's the pruning strategy?

6. **Concurrent Sessions**: Should `AgentRuntime` support concurrent execution across multiple sessions?

---

## Conclusion

The Python SDK has a solid foundation but lacks several key components for building production agent applications. The proposed implementation plan addresses these gaps in a phased approach:

1. **Phase 1** (Core Agent Execution) - 2-3 weeks
2. **Phase 2** (Memory System) - 2-3 weeks
3. **Phase 3** (Multi-Agent Orchestration) - 1-2 weeks
4. **Phase 4** (Enhanced Features) - 2 weeks
5. **Phase 5** (Polish) - 1-2 weeks

**Total Estimated Effort**: 8-12 weeks for full implementation.

The example script (`custom_agent_app_example.py`) demonstrates the desired user experience. The gaps documented here represent the work needed to make that experience a reality.
