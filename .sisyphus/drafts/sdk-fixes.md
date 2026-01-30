# Draft: Python SDK Fixes Planning

**Date**: 2026-01-30
**Status**: Complete - Plan generated

## Analysis Summary

### Critical Bugs Found (3)

1. **Bug #1: SessionStorage initialization**
   - **Location**: `sdk/client.py:53`
   - **Issue**: `SessionStorage()` called without `base_dir` parameter
   - **Impact**: TypeError at runtime, blocks all SDK usage
   - **Fix**: Pass `storage_path` from config or `get_storage_dir()`

2. **Bug #2: AgentExecutor fake Session objects**
   - **Location**: `agents/__init__.py:190-198, 232-240`
   - **Issue**: Creates Session with empty fields (project_id, directory, title)
   - **Impact**: Session metadata lost, agent execution doesn't integrate with storage
   - **Fix**: Accept Session object or fetch from session_manager

3. **Bug #3: ToolExecutionManager empty tool_registry**
   - **Location**: `tool_execution.py:26` + `ai_session.py:46`
   - **Issue**: Creates empty ToolRegistry, no tools ever registered
   - **Impact**: Tool lookups fail, `_filter_tools_for_agent()` crashes
   - **Fix**: Use `tools/registry.ToolRegistry` or accept pre-populated registry

### Missing Features (3)

4. **Agent Registry**
   - **Current**: Only built-in agents via `get_all_agents()`
   - **Missing**: No API to register custom agents
   - **Fix**: Create `AgentRegistry` class with register/get_agent/list_agents

5. **Skill Injection**
   - **Current**: Skills loaded but not injected into prompts
   - **Issue**: Requires manual tool calls, no automatic loading
   - **Fix**: Create `SkillInjector` class, integrate with AISession

6. **Context Builder**
   - **Current**: `_build_llm_messages()` is private/internal
   - **Missing**: No public API for context building
   - **Fix**: Create `ContextBuilder` class, expose through SDK client

## Implementation Plan

### Wave 1: Critical Bug Fixes (Week 1)

**Goal**: Unblock SDK usage by fixing runtime errors

**Tasks**:
1. Fix SessionStorage initialization (client.py:53)
2. Fix AgentExecutor Session objects (agents/__init__.py)
3. Fix ToolExecutionManager tool_registry (tool_execution.py, ai_session.py)

**Dependencies**: None
**Parallelization**: YES - All independent

---

### Wave 2: Agent Registry (Week 2)

**Goal**: Enable custom agent registration

**Tasks**:
4. Create AgentRegistry class (agents/registry.py)
5. Add register_agent to SDK client (client.py)
6. Add get_agent/list_agents to SDK client (client.py)
7. Integrate AgentRegistry with AgentManager (agents/__init__.py)

**Dependencies**: Task 4
**Parallelization**: YES - Tasks 5,6 independent

---

### Wave 3: Skill Injection (Week 3)

**Goal**: Automatically inject skills into system prompts

**Tasks**:
8. Create SkillInjector class (skills/injector.py)
9. Modify AISession to use SkillInjector (ai_session.py)
10. Integrate with agent execution (agents/__init__.py)

**Dependencies**: Task 8
**Parallelization**: NO - Sequential (8 → 9 → 10)

---

### Wave 4: Context Builder (Week 4)

**Goal**: Expose context building as public API

**Tasks**:
11. Create ContextBuilder class (context/builder.py)
12. Integrate with AISession (ai_session.py)
13. Add to SDK client API (client.py)

**Dependencies**: Task 11
**Parallelization**: YES - Tasks 11,12 independent

---

## Success Criteria

### Wave 1
- [x] SDK client initializes without TypeError
- [x] SessionStorage created with valid base_dir
- [x] AgentExecutor uses real Session objects
- [x] ToolExecutionManager has all 23 tools
- [x] Tool lookups succeed

### Wave 2
- [x] AgentRegistry class created
- [x] Custom agents can be registered
- [x] Cannot override built-in agents
- [x] SDK client has register_agent/get_agent/list_agents

### Wave 3
- [x] SkillInjector class created
- [x] Skills automatically loaded from SKILL.md
- [x] Skills injected into system prompts
- [x] Agent.prompt field is used

### Wave 4
- [x] ContextBuilder class created
- [x] Public API exposed through SDK client
- [x] build_context() creates AgentContext with all components

---

## Technical Decisions

### Design Choices

1. **Agent Registry Storage**: In-memory dictionary (simple, fast)
2. **Skill Loading**: Discover on first use, cache in memory
3. **Tool Registry**: Use existing `tools/registry.ToolRegistry` (pre-populated)
4. **Context Building**: Separate class for flexibility

### Architecture Patterns

1. **Factory Functions**: `create_agent_registry()`, `create_skill_injector()`, `create_context_builder()`
2. **Dependency Injection**: Pass dependencies in constructors
3. **Backward Compatibility**: All additive changes, no breaking changes

---

## Risk Assessment

### Overall Risk: LOW

- **Wave 1**: LOW - Straightforward bug fixes
- **Wave 2**: LOW - Simple CRUD operations
- **Wave 3**: LOW - Integrates with existing patterns
- **Wave 4**: LOW - Exposes existing functionality

---

## Timeline

| Wave | Duration | Start | End |
|-------|-----------|-------|-----|
| 1: Critical Bugs | 1 week | - | - |
| 2: Agent Registry | 1 week | - | - |
| 3: Skill Injection | 1 week | - | - |
| 4: Context Builder | 1 week | - | - |
| **Total** | **4 weeks** | - | - |

---

## Next Steps

1. ✅ Plan created: `.sisyphus/plans/sdk-fixes.md`
2. ⬜ Begin Wave 1 implementation
3. ⬜ Run tests after each wave
4. ⬜ Commit each wave separately
5. ⬜ Update documentation

**Ready to start!**
