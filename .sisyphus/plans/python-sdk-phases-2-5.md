# Python SDK: Phases 2-5 (Memory, Multi-Agent, Enhanced Features, Polish)

## TL;DR

> **Quick Summary**: Implement remaining SDK gaps after Phase 1 core agent execution complete.
> 
> **Deliverables**: Memory system, multi-agent orchestration, provider management, tool tracking, session lifecycle hooks, documentation, and polish
> 
> **Estimated Effort**: 6-9 weeks (Phases 2-5 combined)
> **Parallel Execution**: YES - Each phase has 3-5 waves of parallel opportunities
> 
> **Critical Path**: Memory (Phase 2) → Multi-Agent (Phase 3) → Enhanced Features (Phase 4) → Polish (Phase 5)
> 
> **Dependencies**: Phase 2 depends on Phase 1 complete. Phase 3 depends on Phase 2. Phase 4 depends on Phase 2-3. Phase 5 depends on all previous.

---

## Context

### Original Request
Continue SDK implementation from SDK_GAPS_AND_NEXT_STEPS.md after Phase 1 (Core Agent Execution) complete.

### Phase 1 Completion Summary
All 12 tasks from Phase 1 completed successfully:
- ✅ 3 critical bugs fixed (SessionStorage, AgentExecutor sessions, tool registry)
- ✅ 5 Phase 1 core components implemented (AgentResult, AgentContext, protocols)
- ✅ 4 foundation components built (AgentRegistry, ToolPermissionFilter, SkillInjector, ContextBuilder)
- ✅ 3 integration components (AgentRuntime, SDK client APIs, integration tests)
- ✅ 236 tests passing with 90%+ code coverage
- ✅ 14 atomic commits following semantic versioning

### Current SDK State
- **What Works**: Session/message management, async/sync clients, tool framework, built-in agents, skill loading, storage layer, AI session streaming, tool execution with doom loop detection, provider abstraction, token tracking, agent lifecycle, tool state tracking
- **What's New**: Phase 1 agent execution pipeline ready for use

### Dependencies on Phases 2-5
- Phase 2 (Memory) depends on ContextBuilder (from Phase 1)
- Phase 3 (Multi-Agent) depends on Phase 2 memory + AgentRuntime (from Phase 1)
- Phase 4 (Enhanced Features) depends on Phase 2-3
- Phase 5 (Polish) depends on all previous phases

### Design Decisions from Phase 1
- AgentRegistry: In-memory by default, optional JSON persistence
- ToolPermissionFilter: Last-rule-wins semantics for deterministic filtering
- SkillInjector: Dynamic skill injection with optional truncation
- ContextBuilder: Provider-agnostic context building
- AgentRuntime: Unified execution with lifecycle events
- All types: mypy-clean with proper protocols

---

## Work Objectives

### Core Objective
Implement remaining SDK gaps (Phases 2-5) to enable full-featured agent applications with long-term memory, multi-agent workflows, enhanced observability, and comprehensive documentation.

### Concrete Deliverables

**Phase 2: Memory System** (HIGH Priority, 2-3 weeks)
- MemoryStorage layer (JSON-based storage under `storage/memory/`)
- MemoryManager API (store, search, retrieve, delete)
- MemoryEmbedder (vector embeddings for semantic search)
- MemorySummarizer (conversation compression for long sessions)
- Integration with ContextBuilder for memory injection into agent prompts
- Tests with mock embeddings (no external vector DB required initially)

**Phase 3: Multi-Agent Orchestration** (MEDIUM Priority, 1-2 weeks)
- AgentOrchestrator (coordinate multiple agents)
- AgentTask model (define tasks for agent execution)
- Integration with Task tool (enable agent-to-agent delegation)
- Parallel agent execution support
- Agent delegation from AgentRuntime
- Tests for multi-agent workflows

**Phase 4: Enhanced Features** (MEDIUM Priority, 2 weeks)
- ProviderRegistry (manage AI provider configurations)
- ProviderConfig model (provider settings)
- ToolExecutionTracker (track and persist tool executions)
- SessionLifecycle (hooks for session events)
- Integration with SDK client for exposure
- Tests for new features

**Phase 5: Polish & Documentation** (LOW Priority, 1-2 weeks)
- Complete API reference documentation
- Example: Custom agent usage
- Example: Multi-agent workflow
- Example: Memory system usage
- Performance benchmarks
- Error handling improvements
- Logging and observability enhancements

### Definition of Done
- [ ] Phase 2: MemoryStorage layer working with JSON persistence
- [ ] Phase 2: MemoryManager API functional with store/search/retrieve
- [ ] Phase 2: MemoryEmbedder generates embeddings (or uses OpenAI API)
- [ ] Phase 2: MemorySummarizer compresses conversations
- [ ] Phase 2: Tests pass with mock embeddings
- [ ] Phase 3: AgentOrchestrator coordinates multiple agents
- [ ] Phase 3: Parallel agent execution works
- [ ] Phase 3: AgentTask tool integrates with agents
- [ ] Phase 3: Agent delegation from AgentRuntime functional
- [ ] Phase 4: ProviderRegistry manages configurations
- [ ] Phase 4: ToolExecutionTracker persists tool calls
- [ ] Phase 4: SessionLifecycle hooks fire correctly
- [ ] Phase 5: API reference docs complete
- [ ] Phase 5: Examples provided (agent, multi-agent, memory)
- [ ] Phase 5: Performance benchmarks documented
- [ ] All phases pass their test suites
- [ ] Ruff and mypy checks pass

### Must Have
- All features from SDK_GAPS_AND_NEXT_STEPS.md Phases 2-5 implemented
- Backward compatible with existing Phase 1 components
- All components tested with unit and integration tests
- Clean code quality (ruff, mypy)
- No regressions in existing Phase 1 tests

### Must NOT Have
- No breaking changes to existing Phase 1 APIs without deprecation
- No external database dependencies (use JSON/SQLite for storage)
- No changes to built-in agent definitions
- No changes to existing tool set

---

## Execution Strategy

### Phase 2: Memory System (2-3 weeks)

**Parallel Execution Graph:**
```
Wave 1 (start immediately):
├── Task 1: MemoryStorage layer (JSON-based)
└── Task 2: MemoryManager (base CRUD operations)

Wave 2 (after Wave 1):
├── Task 3: MemoryEmbedder (embedding generation)
├── Task 4: MemorySummarizer (conversation compression)
└── Task 5: Integration tests for memory components

Wave 3 (after Wave 2):
├── Task 6: ContextBuilder integration (memory retrieval)
└── Task 7: End-to-end memory flow test
```

**Dependencies:**
- Task 3-4 depend on Task 1-2 (storage foundation)
- Task 5 depends on Task 6
- Task 6-7 depend on Phase 1 ContextBuilder

**Critical Path:** Task 1 → Task 2 → Task 6 → Task 7

---

### Phase 3: Multi-Agent Orchestration (1-2 weeks)

**Parallel Execution Graph:**
```
Wave 1 (start immediately):
├── Task 1: AgentOrchestrator (core coordination)
├── Task 2: AgentTask model (define execution tasks)
└── Task 3: Task tool integration (delegate task)

Wave 2 (after Wave 1):
├── Task 4: Parallel execution support in AgentOrchestrator
└── Task 5: Agent delegation from AgentRuntime

Wave 3 (after Wave 2):
├── Task 6: Integration with AgentRuntime (orchestrator ↔ runtime bridge)
└── Task 7: End-to-end multi-agent tests
```

**Dependencies:**
- Task 3-4 depend on Phase 1 AgentRuntime
- Task 5-7 depend on Phase 1 ToolRegistry + AgentExecutor
- Task 6 integrates AgentOrchestrator with existing execution

**Critical Path:** Task 1 → Task 2 → Task 4 → Task 6 → Task 7

---

### Phase 4: Enhanced Features (2 weeks)

**Parallel Execution Graph:**
```
Wave 1 (start immediately):
├── Task 1: ProviderRegistry (manage provider configurations)
├── Task 2: ToolExecutionTracker (persist tool executions)
└── Task 3: SessionLifecycle (session lifecycle hooks)

Wave 2 (after Wave 1):
├── Task 4: SDK client integration (expose new APIs)
└── Task 5: Tests for enhanced features

Wave 3 (after Wave 2):
└── Task 6: Integration test (end-to-end with new features)
```

**Dependencies:**
- Task 4-5 depend on existing SDK client
- Task 6 depends on all Wave 1 components
- Task 5 validates full integration

**Critical Path:** Task 1-3 → Task 4-5 → Task 6

---

### Phase 5: Polish & Documentation (1-2 weeks)

**Sequential Execution (minimal parallelization - mostly writing/docs):**
```
Task 1: API reference documentation
Task 2: Custom agent example
Task 3: Multi-agent workflow example
Task 4: Memory system example
Task 5: Performance benchmarks
Task 6: Error handling improvements
Task 7: Logging and observability enhancements
Task 8: Final verification suite (all phases)
```

**Dependencies:**
- All tasks depend on all previous phases being complete
- Task 8 requires all features to verify integration

---

## Task Dependencies (All Phases)

```
┌─────────────────┐   Phase 2   Phase 3   Phase 4   Phase 5
│              │   (Memory)    │ (Multi-Ag.) │ (Enhanced) │ (Polish)   │
│              │   2-3 weeks    │  1-2 weeks  │   2 weeks    │  1-2 weeks    │
│              │                │                │                │                │
├────────────────┼────────────────┼────────────────┼────────────────┤
│ Phase 1     │ Phase 2     │ Phase 3     │ Phase 4     │ Phase 5     │
│ (Complete)   │ (P2-T3)     │ (P3-T4)     │ (P4-T5)     │ (P5-None)   │
│              │                │                │                │                │
└────────────────┴────────────────┴────────────────┴────────────────┘
```

### Parallel Execution Speedup

**Estimated Speedup**: ~40% faster than sequential execution across all 5 phases
- **Optimization**: Each phase has 2-3 waves with 2-3 parallel tasks
- **Total tasks**: 30 tasks across 5 phases
- **Sequential time**: 6-9 weeks
- **Parallel time**: 4-5.5 weeks

---

## TODOs

### PHASE 2: MEMORY SYSTEM

**Wave 1: Memory Foundation**

- [ ] **Task 1**: Create MemoryStorage layer (JSON-based)
  - File: `src/opencode_python/storage/memory_storage.py`
  - Implement: JSON storage under `storage/memory/{session_id}/{memory_id}.json`
  - Methods: `store_memory()`, `get_memory()`, `list_memories()`, `delete_memory()`
  - Pattern: Follow `SessionStorage` async file I/O pattern with `aiofiles`
  
- [ ] **Task 2**: Create MemoryManager API
  - File: `src/opencode_python/agents/memory_manager.py`
  - Implement: CRUD operations for memory entries
  - Methods: `store()`, `search()`, `retrieve()`, `delete()`, `summarize()`
  - Async methods matching SDK patterns
  - Optional: Embedding integration
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ✅ Can run with Task 1
  **Blocks**: Task 3-4, 6-7
  **Dependencies**: None (start fresh)

  **Acceptance Criteria**:
  - JSON files created under `storage/memory/`
  - Async CRUD operations work
  - Memory entry contains: id, session_id, content, embedding, metadata, created
  - Search returns filtered results
  - Delete removes files correctly
  - Tests cover all CRUD operations
  - Commit: `feat(storage): add memory storage layer`

---

**Wave 2: Memory Search & Summarization**

- [ ] **Task 3**: Create MemoryEmbedder
  - File: `src/opencode_python/agents/memory_embedder.py`
  - Implement: Vector embedding generation for semantic search
  - Methods: `embed(text: str) -> List[float]`
  - Support: Local models (sentence-transformers) or OpenAI API
  - Config: Embedding model selection via SDKConfig or environment variable
  
- [ ] **Task 4**: Create MemorySummarizer
  - File: `src/opencode_python/agents/memory_summarizer.py`
  - Implement: Conversation compression for long sessions
  - Methods: `summarize(session_id: str, since: float) -> MemorySummary`
  - Strategy: Extract key points, compress old messages, generate summary
  - Integration: Use AISession or direct LLM API
  
- [ ] **Task 5**: Memory integration tests
  - File: `tests/test_memory_system.py`
  - Tests: CRUD operations with mock embeddings
  - Tests: Search functionality
  - Tests: Summarization logic
  - Tests: End-to-end memory retrieval in agent prompts
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ✅ Can run with Wave 1 complete
  **Blocks**: Task 6-7
  **Dependencies**: Task 1-4 (storage + manager)

  **Acceptance Criteria**:
  - Embedder generates vectors (or uses mock for tests)
  - Summarizer compresses conversations correctly
  - Search returns relevant memories (by similarity score)
  - Integration with ContextBuilder works
  - All tests pass
  - Commits: `feat(agents): add memory search and summarization`

---

**Wave 3: ContextBuilder Integration**

- [ ] **Task 6**: Integrate memory retrieval into ContextBuilder
  - File: `src/opencode_python/context/builder.py` (extend existing)
  - Add: `_build_memory_context(session, agent, limit)` method
  - Add: Memory retrieval via MemoryManager.search()
  - Add: Memory summarization via MemoryManager.summarize()
  - Integration: Inject memories into system prompt after skills
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ❌ Must wait for Wave 2 (embedding + summarizer)
  **Blocks**: Task 7
  **Dependencies**: Task 3-5, 6, ContextBuilder base from Phase 1

  **Acceptance Criteria**:
  - Context includes relevant memories from search
  - Context includes memory summary
  - System prompt format: skills → memories → base prompt
  - Tests verify memory injection
  - Commit: `feat(context): integrate memory retrieval into ContextBuilder`

---

**Wave 4: End-to-End Memory Tests**

- [ ] **Task 7**: End-to-end memory flow test
  - File: `tests/test_phase2_memory_integration.py`
  - Test: Full memory workflow (store → search → retrieve → inject)
  - Test: Agent with memory-enabled context
  - Test: Long session summarization
  - Use: Mock embeddings, mock AISession
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ❌ Must wait for all previous tasks
  **Blocks**: None (final task of Phase 2)

  **Acceptance Criteria**:
  - Test validates complete memory flow
  - Memories retrieved and injected correctly
  - Summarization triggers correctly
  - Agent uses memory-enhanced context
  - All tests pass
  - Commit: `test(agents): add end-to-end memory integration tests`

---

### PHASE 3: MULTI-AGENT ORCHESTRATION

**Wave 1: Orchestration Foundation**

- [ ] **Task 8**: Create AgentOrchestrator
  - File: `src/opencode_python/agents/orchestrator.py`
  - Implement: Coordinate multiple agents
  - Methods: `delegate_task()`, `run_parallel_agents()`, `cancel_tasks()`
  - Support: Parallel execution, task status tracking
  - Integration: AgentRuntime for execution
  
- [ ] **Task 9**: Create AgentTask model
  - File: `src/opencode_python/core/agent_task.py`
  - Implement: Define tasks for agent execution
  - Fields: agent_name, description, tool_ids, skill_names, options
  - Support: Dependencies between tasks (task chains)
  
  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ✅ Can run in parallel with Task 8
  **Blocks**: Task 10-13
  **Dependencies**: Phase 1 AgentRuntime, AgentResult

  **Acceptance Criteria**:
  - Orchestrator can schedule tasks
  - AgentTask model properly defined
  - Parallel execution support added to Orchestrator
  - Task status tracking works
  - Commits: `feat(agents): add agent orchestration foundation`
  - `feat(core): add AgentTask model`

---

**Wave 2: Task Tool Integration**

- [ ] **Task 10**: Create Task tool for agent delegation
  - File: `src/opencode_python/tools/task_tool.py`
  - Implement: Special tool that agents can use to spawn sub-agents
  - Method: `execute(tool_id, task)` where task = agent delegation
  - Integration: Use AgentOrchestrator to delegate to AgentRuntime
  - Follows existing tool pattern from `tools/framework.py`
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ✅ Can run in parallel with Wave 1
  **Blocks**: Task 11-13
  **Dependencies**: Task 8-9 (orchestrator + AgentTask)

  **Acceptance Criteria**:
  - Task tool works with Task input format
  - Agent can delegate to another agent via Task tool
  - Orchestrator handles delegation correctly
  - Tool follows framework conventions
  - Tests validate delegation flow
  - Commit: `feat(tools): add task tool for multi-agent workflows`

---

**Wave 3: Runtime Integration**

- [ ] **Task 11**: Integrate AgentOrchestrator with AgentRuntime
  - File: `src/opencode_python/agents/runtime.py` (extend existing)
  - Add: `run_with_orchestrator()` method to AgentRuntime
  - Support: Orchestrator-managed execution
  - Maintain: Existing `execute_agent()` for direct calls
  - Integration: Use AgentOrchestrator.delegate_task() for managed workflows
  
  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ✅ Can run in parallel with Wave 2
  **Blocks**: Task 12-13
  **Dependencies**: Task 8-11 (orchestrator + Task tool)

  **Acceptance Criteria**:
  - AgentRuntime can run via orchestrator
  - Parallel execution works through orchestrator
  - Task delegation uses AgentRuntime correctly
  - Both direct and orchestrated paths work
  - Tests validate orchestrator integration
  - Commit: `feat(agents): integrate orchestrator with AgentRuntime`

---

**Wave 4: End-to-End Multi-Agent Tests**

- [ ] **Task 12**: End-to-end multi-agent tests
  - File: `tests/test_phase3_multi_agent.py`
  - Test: Agent A delegates to Agent B
  - Test: Parallel execution of multiple agents
  - Test: Task tool usage from agents
  - Test: Orchestrator coordinates workflows
  - Use: Mock AISession, mock providers
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ❌ Must wait for all previous tasks
  **Blocks**: None (final task of Phase 3)

  **Acceptance Criteria**:
  - Test validates complete multi-agent workflow
  - Agent delegation works through Task tool
  - Parallel execution succeeds
  - Orchestrator manages state correctly
  - All tests pass
  - Commit: `test(agents): add end-to-end multi-agent integration tests`

---

### PHASE 4: ENHANCED FEATURES

**Wave 1: Provider & Tracking**

- [ ] **Task 13**: Create ProviderRegistry
  - File: `src/opencode_python/providers/registry.py`
  - Implement: Manage AI provider configurations
  - Methods: `register_provider()`, `get_provider()`, `list_providers()`, `remove_provider()`
  - Storage: JSON under `storage/providers/{provider_name}.json`
  - Support: Default provider selection
  
- [ ] **Task 14**: Create ProviderConfig model
  - File: `src/opencode_python/core/provider_config.py`
  - Implement: Provider settings data model
  - Fields: provider_id, model, api_key, base_url, options
  - Integration: Use with ProviderRegistry
  - Validation: Pydantic model with required fields
  
- [ ] **Task 15**: Create ToolExecutionTracker
  - File: `src/opencode_python/agents/tool_execution_tracker.py`
  - Implement: Track and persist tool executions
  - Methods: `log_execution()`, `get_execution_history()`, `persist()`
  - Storage: JSON under `storage/tool_execution/{session_id}/{execution_id}.json`
  - Integration: Hook into AISession and AgentRuntime
  - Event emission: Publish tool execution events
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ✅ Can run in parallel
  **Blocks**: Task 16-17
  **Dependencies**: Existing AISession, ToolExecutionManager, AgentManager

  **Acceptance Criteria**:
  - ProviderRegistry manages configurations
  - ProviderConfig model properly defined
  - ToolExecutionTracker logs and persists executions
  - JSON storage follows existing patterns
  - Tests validate tracking functionality
  - Commits: `feat(providers): add provider registry and config`
  - `feat(agents): add tool execution tracker`

---

**Wave 2: Lifecycle & SDK Integration**

- [ ] **Task 16**: Create SessionLifecycle
  - File: `src/opencode_python/core/session_lifecycle.py`
  - Implement: Hooks for session events
  - Methods: `on_session_created()`, `on_session_updated()`, `on_message_added()`, `on_session_archived()`
  - Integration: Call hooks from SDK client and AgentRuntime
  - Storage: JSON under `storage/hooks/{event_name}.json`
  - Support: Event registration and unregistration
  - Async execution of hooks
  
- [ ] **Task 17**: Integrate SessionLifecycle with SDK client
  - File: `src/opencode_python/sdk/client.py` (extend existing)
  - Add: Methods to register/unregister lifecycle hooks
  - Add: Lifecycle event emission in session operations
  - Support: Multiple hooks per event type
  - Integration with DefaultSessionService
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ✅ Can run in parallel with Task 13-15
  **Blocks**: Task 18-19
  **Dependencies**: Task 13-16

  **Acceptance Criteria**:
  - SessionLifecycle hooks fire correctly
  - SDK client emits lifecycle events
  - Multiple hooks supported per event type
  - Hook storage follows JSON pattern
  - Tests validate hook execution
  - Commits: `feat(core): add session lifecycle hooks`
  - `feat(sdk): integrate lifecycle hooks with client`

---

**Wave 3: SDK Client Integration**

- [ ] **Task 18**: Integrate ProviderRegistry with SDK client
  - File: `src/opencode_python/sdk/client.py` (extend existing)
  - Add: Methods: `register_provider()`, `get_provider()`, `list_providers()`
  - Add: Use ProviderRegistry to manage configurations
  - Support: Default provider selection from config
  - Async/sync wrappers for all methods
  
- [ ] **Task 19**: Integrate ToolExecutionTracker with SDK client
  - File: `src/opencode_python/sdk/client.py` (extend existing)
  - Add: Methods: `get_tool_execution_history()`, `configure_tool_tracking()`
  - Add: Use ToolExecutionTracker for persistence
  - Support: Enable/disable tracking via config
  - Integration: Pass tracker to AISession and AgentRuntime
  
- [ ] **Task 20**: Integration tests for enhanced features
  - File: `tests/test_phase4_enhanced_features.py`
  - Tests: ProviderRegistry configuration
  - Tests: ToolExecutionTracker logging
  - Tests: SessionLifecycle hooks
  - Tests: SDK client integration
  - Use: Mock storage, mock AISession
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ✅ Can run in parallel with Task 16-19
  **Blocks**: Task 21-22
  **Dependencies**: Task 13-20

  **Acceptance Criteria**:
  - ProviderRegistry accessible from SDK client
  - ToolExecutionTracker configurable from client
  - SessionLifecycle hooks emit from SDK operations
  - All new features work end-to-end
  - Tests validate full integration
  - Commits: `feat(sdk): integrate provider and tool tracking with client`
  - `test(sdk): add enhanced features integration tests`

---

**Wave 4: End-to-End Tests**

- [ ] **Task 21**: End-to-end tests for Phase 4
  - File: `tests/test_phase4_complete.py`
  - Test: Full Phase 4 workflow
  - Test: Provider configuration → tool tracking → lifecycle hooks
  - Test: All new features working together
  - Verify: No regressions in existing tests
  - Use: Integration test suite from all phases
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ❌ Must wait for all previous tasks
  **Blocks**: None (final task of Phase 4)

  **Acceptance Criteria**:
  - All Phase 4 tests pass
  - Integration validates all components working together
  - No regressions in existing tests
  - Full test suite covers all phases
  - Commit: `test(sdk): add complete integration test suite for Phases 2-5`

---

### PHASE 5: POLISH & DOCUMENTATION

**Sequential Tasks (Minimal Parallelization):**

- [ ] **Task 22**: API reference documentation
  - File: `docs/api/agents.md`
  - Document: AgentRegistry, ToolPermissionFilter, SkillInjector, ContextBuilder
  - Document: AgentRuntime and agent execution flow
  - Document: Memory system APIs
  - Document: Multi-agent orchestration APIs
  - Document: Provider and tracking APIs
  - Format: Google-style with examples
  - Section: All Agent APIs
  
- [ ] **Task 23**: Custom agent example
  - File: `docs/examples/custom_agent.py`
  - Example: Registering custom agent
  - Example: Executing agent with filtered tools
  - Example: Error handling and monitoring
  - Integration: Use SDK client directly
  
- [ ] **Task 24**: Multi-agent workflow example
  - File: `docs/examples/multi_agent_workflow.py`
  - Example: Agent A delegates to Agent B
  - Example: Parallel agent execution
  - Example: Task tool usage
  - Example: Orchestrator coordination
  - Complex realistic use case
  
- [ ] **Task 25**: Memory system example
  - File: `docs/examples/memory_system.py`
  - Example: Storing conversation memories
  - Example: Searching and retrieving memories
  - Example: Summarizing long sessions
  - Integration: MemoryManager with ContextBuilder
  
- [ ] **Task 26**: Performance benchmarks
  - File: `docs/performance_benchmarks.md`
  - Benchmarks: Agent execution speed
  - Benchmarks: Memory search latency
  - Benchmarks: Context building overhead
  - Benchmarks: Tool execution time
  - Methodology: Document test harness approach
  
- [ ] **Task 27**: Error handling improvements
  - File: Review error handling across all components
  - Identify: Common error patterns
  - Propose: Better error messages
  - Propose: Retry strategies
  - Propose: Graceful degradation
  
- [ ] **Task 28**: Logging and observability
  - File: Add structured logging throughout SDK
  - Components: AgentRuntime, MemoryManager, ProviderRegistry
  - Log levels: DEBUG, INFO, WARNING, ERROR
  - Integration: With existing event bus
  - Observability: Request ID tracking, performance metrics
  
- [ ] **Task 29**: Final verification suite
  - File: `tests/test_all_phases_integration.py`
  - Test: Complete workflow across all phases
  - Test: Memory → Multi-Agent → Enhanced features
  - Test: End-to-end scenarios
  - Comprehensive regression test
  - Verify: All acceptance criteria met
  
  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: [`python-programmer`, `git-master`]
  
  **Parallelization**: ❌ Sequential (documentation tasks)
  **Blocks**: None (final task of Phase 5)

  **Acceptance Criteria**:
  - API reference docs complete
  - All examples provided work correctly
  - Performance benchmarks documented
  - Error handling improved
  - Logging added throughout SDK
  - Final test suite passes (100% of all features)
  - Commit: Multiple commits for documentation and polish
  - Final commit: `docs: complete API reference and examples for Phases 2-5`

---

## Commit Strategy

### Phase 2 Commits
1. `feat(storage): add memory storage layer`
2. `feat(agents): add memory manager`
3. `feat(agents): add memory search and summarization`
4. `test(agents): add end-to-end memory integration tests`
5. `feat(context): integrate memory retrieval into ContextBuilder`

### Phase 3 Commits
1. `feat(agents): add agent orchestration foundation`
2. `feat(tools): add task tool for multi-agent workflows`
3. `feat(agents): integrate orchestrator with AgentRuntime`
4. `test(agents): add end-to-end multi-agent integration tests`

### Phase 4 Commits
1. `feat(providers): add provider registry and config`
2. `feat(agents): add tool execution tracker`
3. `feat(core): add session lifecycle hooks`
4. `test(sdk): add enhanced features integration tests`

### Phase 5 Commits
1. `docs(api): complete agent API reference`
2. `docs(examples): custom agent usage`
3. `docs(examples): multi-agent workflow`
4. `docs(examples): memory system`
5. `docs(performance): performance benchmarks`
6. `chore(error): error handling improvements`
7. `chore(observability): logging and observability`
8. `test(sdk): add complete integration test suite for Phases 2-5`

---

## Success Criteria

### Functional
- **Memory System**: Can store, search, retrieve, and summarize conversation memories
- **Multi-Agent Orchestration**: Can coordinate multiple agents with parallel execution
- **Provider Management**: Can configure and switch between AI providers
- **Tool Tracking**: Can track and query tool execution history
- **Session Lifecycle**: Can hook into session events for automation
- **Documentation**: Complete API reference with examples

### Verification Commands
```bash
# Phase 2 verification
cd opencode_python && python3 -m pytest tests/test_memory_system.py -xvs
cd opencode_python && python3 -m pytest tests/test_phase2_memory_integration.py -xvs

# Phase 3 verification
cd opencode_python && python3 -m pytest tests/test_phase3_multi_agent.py -xvs

# Phase 4 verification
cd opencode_python && python3 -m pytest tests/test_phase4_enhanced_features.py -xvs

# Phase 5 verification
cd opencode_python && python3 -m pytest tests/test_all_phases_integration.py -xvs

# All phases
cd opencode_python && python3 -m pytest -k "phase2 or phase3 or phase4 or phase5" -xvs

# Quality checks
python3 -m ruff check opencode_python/src/opencode_python/
python3 -m mypy opencode_python/src/opencode_python/
```

### Final Checklist
- [ ] Phase 2: All tasks complete and tests pass
- [ ] Phase 3: All tasks complete and tests pass
- [ ] Phase 4: All tasks complete and tests pass
- [ ] Phase 5: All tasks complete and tests pass
- [ ] All phases integration test passes (end-to-end validation)
- [ ] No regressions in existing tests
- [ ] Ruff and mypy checks pass
- [ ] Documentation complete with examples
- [ ] Performance benchmarks documented

---

## Verification Strategy

### Pre-Implementation Success Criteria
For each phase, success requires:

**Phase 2 (Memory)**:
- ✅ MemoryStorage: JSON files created under `storage/memory/`
- ✅ MemoryManager: CRUD operations functional
- ✅ MemoryEmbedder: Generates vectors (or mocks)
- ✅ MemorySummarizer: Compresses conversations
- ✅ Integration: ContextBuilder retrieves and injects memories
- ✅ Tests: Full memory flow validated

**Phase 3 (Multi-Agent)**:
- ✅ AgentOrchestrator: Coordinates multiple agents
- ✅ AgentTask: Defines execution tasks
- ✅ Task tool: Enables agent delegation
- ✅ Integration: AgentRuntime uses orchestrator
- ✅ Tests: Multi-agent workflows validated

**Phase 4 (Enhanced Features)**:
- ✅ ProviderRegistry: Manages configurations
- ✅ ProviderConfig: Settings model defined
- ✅ ToolExecutionTracker: Logs and persists executions
- ✅ SessionLifecycle: Hooks fire on events
- ✅ Integration: SDK client exposes all APIs
- ✅ Tests: Full integration validated

**Phase 5 (Polish)**:
- ✅ API reference: Complete documentation
- ✅ Examples: Agent, multi-agent, memory provided
- ✅ Performance: Benchmarks documented
- ✅ Error handling: Improvements made
- ✅ Observability: Logging added
- ✅ Final test suite: End-to-end validation

### Test Coverage Targets
- **New code**: 80%+ coverage across all new modules
- **Integration tests**: Full end-to-end workflows covered
- **No regressions**: All Phase 1 tests still pass

---

## Next Steps

**To proceed with execution:**

1. Start with **Phase 2** (Memory System) - Wave 1 tasks 1-2 (storage + manager)
2. Proceed to **Phase 3** (Multi-Agent Orchestration) - Wave 1 tasks 1-2 (orchestrator + agent tasks)
3. Proceed to **Phase 4** (Enhanced Features) - Wave 1 tasks 1-3 (provider + tracking + lifecycle)
4. Proceed to **Phase 5** (Polish) - Sequential tasks 1-8 (docs + examples + polish)

**Or** choose specific phase to focus on:
- "Focus on Phase 2 (Memory)"
- "Focus on Phase 3 (Multi-Agent)"
- "Start all remaining phases" (sequential)

**To stop:**
- User can stop after any phase is complete
- Plan can be resumed later for remaining phases

---

## Summary

This plan provides:
- **30 total tasks** across 5 phases (6 tasks/phase on average)
- **Clear dependencies** between phases and tasks
- **Parallelization opportunities** in each phase (3-5 waves per phase)
- **Category and skill recommendations** for each task
- **Comprehensive success criteria** for each phase
- **Final integration test** validating all phases together

The plan builds on the solid foundation of Phase 1 (Core Agent Execution) to deliver the full SDK capabilities outlined in SDK_GAPS_AND_NEXT_STEPS.md.

**Ready for systematic execution across all remaining phases.**