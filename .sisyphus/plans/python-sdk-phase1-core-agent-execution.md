# Python SDK: Critical Bugfixes + Phase 1 (Core Agent Execution)

## Context

User request: implement the SDK improvements described in `SDK_GAPS_AND_NEXT_STEPS.md`, starting with the 3 critical bugs, then Phase 1 (Core Agent Execution), with explicit dependencies + parallelization, and per-task delegation recommendations.

Key repo findings (validated against current code):
- `SessionStorage` requires `base_dir` (`opencode_python/src/opencode_python/storage/store.py`). Current `OpenCodeAsyncClient` already passes a storage dir (`opencode_python/src/opencode_python/sdk/client.py`). Treat “Bug #1” as: verify all call-sites and add a regression test.
- `AgentExecutor` currently fabricates a `Session` with empty fields (`opencode_python/src/opencode_python/agents/__init__.py`).
- Subagent execution path in `TaskTool` passes `session_manager=self.agent_manager.session_storage` (a `SessionStorage`), but `AISession` expects a `SessionManager`-like interface with `list_messages/add_message/add_part` (`opencode_python/src/opencode_python/ai_session.py`, `opencode_python/src/opencode_python/core/session.py`). This is a concrete integration break.
- Tool registry is effectively empty for AI sessions: `ToolExecutionManager` constructs `ToolRegistry()` from `opencode_python.tools.framework` (empty until registered), but no registration occurs in `ToolExecutionManager` or `AISession` (`opencode_python/src/opencode_python/ai/tool_execution.py`, `opencode_python/src/opencode_python/ai_session.py`). A complete registry factory exists (`opencode_python/src/opencode_python/tools/__init__.py:create_complete_registry`) and an eager registry also exists (`opencode_python/src/opencode_python/tools/registry.py`).
- Current provider streaming does not emit tool-call events for Anthropic and does not include a system prompt field; Phase 1 “tools + skills injection” requires closing that gap (at least enough for tests with a stub provider).

Assumptions / defaults (override if you disagree):
- Tests: use existing `pytest` + `pytest-asyncio` (configured in `opencode_python/pyproject.toml`). Also run `ruff` + `mypy` as CI gate.
- AgentRegistry persistence: default to in-memory + optional JSON persistence under `storage/agent/` (off by default unless configured), to avoid breaking existing SDK behavior.
- Skill injection: inject full `SKILL.md` content into a “system” instruction block (with name + description headers), with a max total character budget (configurable) to avoid runaway context.

Non-goals (explicitly OUT of this plan):
- Phase 2+ deliverables (Memory system, multi-agent orchestration, provider registry, etc.) except where required to make Phase 1 functional.


## Task Dependency Graph

| Task | Depends On | Reason |
|------|------------|--------|
| 1 | None | Establish baseline verification commands + add guardrail tests before refactors |
| 2 | 1 | Fix + lock in SessionStorage initialization behavior via tests |
| 3 | 1 | Fix AgentExecutor session handling; foundational for all agent execution |
| 4 | 1 | Fix tool registry wiring; foundational for tool permission filtering and runtime |
| 5 | 2, 3, 4 | Build Phase 1 API on top of corrected storage/session/tool plumbing |
| 6 | 5 | AgentRegistry requires stable execution & storage boundaries |
| 7 | 5 | ToolPermissionFilter depends on tool registry model + agent permission rules |
| 8 | 5 | SkillInjector depends on skill loader + prompt conventions |
| 9 | 7, 8 | ContextBuilder needs tool filtering output + skill injection output |
| 10 | 6, 9 | AgentRuntime composes registry + context builder + AI session execution |
| 11 | 10 | SDK client surface area depends on runtime |
| 12 | 10, 11 | Integration tests validate end-to-end behavior |


## Parallel Execution Graph

Wave 1 (start immediately):
├── Task 1: Baseline verification scaffolding
└── Task 2: Bug #1 regression test (SessionStorage base_dir wiring)

Wave 2 (after Wave 1):
├── Task 3: Bug #2 fix (real Session usage in AgentExecutor)
└── Task 4: Bug #3 fix (tool registry wiring / exposure)

Wave 3 (after Wave 2):
├── Task 6: AgentRegistry
├── Task 7: ToolPermissionFilter
└── Task 8: SkillInjector

Wave 4 (after Wave 3):
└── Task 9: ContextBuilder

Wave 5 (after Wave 4):
├── Task 10: AgentRuntime
└── Task 11: SDK client API wiring

Wave 6 (after Wave 5):
└── Task 12: End-to-end integration tests + docs/example refresh

Critical Path: Task 1 → Task 3 → Task 4 → Task 9 → Task 10 → Task 12
Estimated Parallel Speedup: ~30-45% vs purely sequential (Wave 3 parallelizes cleanly)


## Tasks

### Task 1: Baseline verification scaffolding
**Description**: Establish the verification commands and add a minimal “agent execution” test harness entrypoint for Phase 1 work.

**Priority**: HIGH

**Delegation Recommendation:**
- Category: `unspecified-low` - straightforward repo plumbing + test harness setup
- Skills: [`python-programmer`, `git-master`] - Python changes + clean atomic commits

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`: primary implementation language
- ✅ INCLUDED `git-master`: ensure safe, atomic changes while touching core runtime
- ❌ OMITTED `typescript-programmer`, `svelte-programmer`, `golang-tui-programmer`: no TS/Svelte/Go scope
- ❌ OMITTED `frontend-ui-ux`, `agent-browser`, `dev-browser`: no UI/browser automation required
- ❌ OMITTED `python-debugger`, `data-scientist`, `prompt-engineer`: not needed for scaffolding

**Depends On**: None

**Acceptance Criteria**:
- `python -m pytest -q` runs (may fail initially, but executes collection without crashes)
- `python -m ruff check opencode_python` runs
- `python -m mypy opencode_python/src/opencode_python` runs


### Task 2: Bug #1 (CRITICAL): SessionStorage base_dir wiring regression
**Description**: Confirm all `SessionStorage(...)` call sites pass `base_dir` and add a regression test ensuring `OpenCodeAsyncClient()` initializes without raising due to missing args.

**Priority**: CRITICAL

**Delegation Recommendation:**
- Category: `quick` - narrow change: tests + small inspection
- Skills: [`python-programmer`, `git-master`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`: implement regression test
- ✅ INCLUDED `git-master`: keep commit focused
- ❌ OMITTED all others: not relevant

**Depends On**: Task 1

**References**:
- `opencode_python/src/opencode_python/storage/store.py` - `Storage.__init__(base_dir)` contract
- `opencode_python/src/opencode_python/sdk/client.py` - current SDK client wiring
- `opencode_python/src/opencode_python/core/settings.py` - `get_storage_dir()` default

**Acceptance Criteria**:
- New/updated test asserts `OpenCodeAsyncClient()` constructs without `TypeError` for SessionStorage
- `python -m pytest -q opencode_python/tests/test_sdk_async_client.py` → PASS


### Task 3: Bug #2 (HIGH): AgentExecutor uses real Session instead of fake
**Description**: Remove “fake Session” construction in `AgentExecutor` and require/fetch a real `Session` via a real session manager (expected: `SessionManager`). Ensure session metadata (project_id, directory, title) is preserved.

**Priority**: HIGH

**Delegation Recommendation:**
- Category: `unspecified-high` - touches core execution path + APIs used by tools
- Skills: [`python-programmer`, `git-master`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`: core refactor
- ✅ INCLUDED `git-master`: safe incremental commits
- ❌ OMITTED all others: not relevant

**Depends On**: Task 1

**References**:
- `opencode_python/src/opencode_python/agents/__init__.py` - `AgentExecutor.execute_agent` + `_run_agent_logic`
- `opencode_python/src/opencode_python/core/session.py` - `SessionManager.get_session/list_messages/add_message/add_part`
- `opencode_python/src/opencode_python/tools/additional.py` - `TaskTool` constructs and wires `AgentExecutor`

**Acceptance Criteria**:
- `AgentExecutor.execute_agent(...)` no longer creates placeholder `Session(project_id="", directory="", ...)`
- When `session_manager` is provided, execution path uses `await session_manager.get_session(session_id)` and fails fast with a clear error if missing
- Unit/integration test added/updated to validate non-empty session metadata is available during execution


### Task 4: Bug #3 (HIGH): ToolExecutionManager uses a populated ToolRegistry and exposes it
**Description**: Ensure `ToolExecutionManager.tool_registry` is (a) present and (b) contains the full tool set by default, so permission filtering and `AISession._get_tool_definitions()` work.

**Priority**: HIGH

**Delegation Recommendation:**
- Category: `unspecified-high` - impacts tool execution across SDK/CLI/TUI
- Skills: [`python-programmer`, `git-master`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`
- ✅ INCLUDED `git-master`
- ❌ OMITTED all others: not relevant

**Depends On**: Task 1

**References**:
- `opencode_python/src/opencode_python/ai/tool_execution.py` - `ToolExecutionManager.__init__` currently uses empty `ToolRegistry()`
- `opencode_python/src/opencode_python/tools/__init__.py` - `create_complete_registry()` populates tools
- `opencode_python/src/opencode_python/tools/registry.py` - eager-populated registry alternative
- `opencode_python/src/opencode_python/ai_session.py` - `_get_tool_definitions()` reads `self.tool_manager.tool_registry.tools`

**Acceptance Criteria**:
- `ToolExecutionManager.tool_registry.tools` contains expected builtins (at least `bash/read/write/grep/glob`) in a fresh session
- `AISession._get_tool_definitions()` returns non-empty definitions without additional setup
- Targeted test asserts tool definitions include at least one known tool id


### Task 5: Phase 1 foundation: define Phase 1 public contracts (types + interfaces)
**Description**: Create the minimal data models and protocols used across Phase 1 so downstream tasks can compile independently.

This includes:
- `AgentResult` (dataclass / pydantic model)
- `AgentContext` (system prompt, tools, messages, session, agent)
- Small protocols for `SessionManagerLike` and `ProviderLike` as needed

**Priority**: HIGH

**Delegation Recommendation:**
- Category: `unspecified-high` - contracts affect multiple modules
- Skills: [`python-programmer`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`
- ❌ OMITTED `git-master`: optional for contract drafting; can be added later for commit
- ❌ OMITTED all others: not relevant

**Depends On**: Tasks 2, 3, 4

**Acceptance Criteria**:
- New types are importable and mypy-clean for their modules
- No runtime behavior changes yet (pure type/contract addition)


### Task 6: AgentRegistry (register/retrieve custom agents)
**Description**: Implement `AgentRegistry` with CRUD operations, seeded with built-in agents.

Default design:
- In-memory registry seeded from `opencode_python.agents.builtin.get_all_agents()`
- Optional persistence via JSON files under `storage/agent/{agent_name}.json` (guarded by config flag)

**Priority**: HIGH

**Delegation Recommendation:**
- Category: `unspecified-high`
- Skills: [`python-programmer`, `git-master`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`, `git-master`
- ❌ OMITTED all others: not relevant

**Depends On**: Task 5

**References**:
- `opencode_python/src/opencode_python/agents/builtin.py` - built-in agent model + default agents
- `opencode_python/src/opencode_python/storage/store.py` - storage patterns to reuse for persistence

**Acceptance Criteria**:
- Can `register_agent()` and retrieve it by name (case-insensitive)
- `list_agents()` returns built-ins + customs
- Tests cover register/get/remove and persistence flag behavior


### Task 7: ToolPermissionFilter (filter tools based on agent permissions)
**Description**: Implement a deterministic tool filtering layer that takes:
- Agent permission rules (from `Agent.permission`)
- A tool registry (complete registry)
and produces:
- Allowed tool ids
- A filtered registry or tool definitions suitable for provider call

Default semantics:
- Rules are evaluated in order, last matching rule wins
- `permission` in rules matches tool id (e.g., `bash`, `read`, `*`)
- `pattern` is reserved for tool-specific sub-scoping (e.g., file patterns for `read/write`); Phase 1 will only use it for future-proofing (accept but do not enforce at tool-id filter stage)

**Priority**: HIGH

**Delegation Recommendation:**
- Category: `unspecified-high`
- Skills: [`python-programmer`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`
- ❌ OMITTED all others: not relevant

**Depends On**: Task 5

**References**:
- `opencode_python/src/opencode_python/agents/builtin.py` - permission rule shape used today
- `opencode_python/src/opencode_python/tools/__init__.py` - canonical tool ids
- `opencode_python/src/opencode_python/tools/framework.py` - registry shape (`tools: Dict[str, Tool]`)

**Acceptance Criteria**:
- Given PLAN agent rules, filtered set excludes `edit` and `write` and any other explicitly denied tools
- Given BUILD agent rules, filtered set includes all tools
- Unit tests cover allow/deny ordering and wildcard behavior


### Task 8: SkillInjector (inject skills into agent prompts)
**Description**: Implement `SkillInjector` that merges:
- Agent base prompt (agent.prompt or default)
- Selected skills loaded via `SkillLoader(base_dir).get_skill_by_name(...)`
into a single system instruction string with stable formatting.

**Priority**: MEDIUM (but required for Phase 1 completeness)

**Delegation Recommendation:**
- Category: `unspecified-low`
- Skills: [`python-programmer`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`
- ❌ OMITTED all others: not relevant

**Depends On**: Task 5

**References**:
- `opencode_python/src/opencode_python/skills/loader.py` - skill discovery and loading
- `SDK_GAPS_AND_NEXT_STEPS.md` - expected injection format

**Acceptance Criteria**:
- Given 0 skills, output == base prompt (no extra headers)
- Given N skills, output includes each skill name + description + content
- Unit test asserts deterministic formatting and truncation behavior (if enabled)


### Task 9: ContextBuilder (build agent execution context)
**Description**: Implement `ContextBuilder` to assemble provider-ready request inputs:
- System prompt (via SkillInjector)
- Tool definitions (from filtered registry)
- Conversation history (via SessionManager.list_messages)

Also introduce a provider-compat adapter layer:
- Anthropic: support a dedicated `system` field and correct tool schema shape
- OpenAI: support a `system` role message if needed

**Priority**: HIGH

**Delegation Recommendation:**
- Category: `unspecified-high` - touches provider boundary + message formatting
- Skills: [`python-programmer`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`
- ❌ OMITTED `prompt-engineer`: formatting is deterministic engineering, not prompt optimization
- ❌ OMITTED others: not relevant

**Depends On**: Tasks 7, 8

**References**:
- `opencode_python/src/opencode_python/ai_session.py` - existing `_build_llm_messages` to extract/generalize
- `opencode_python/src/opencode_python/providers/__init__.py` - provider `stream(model, messages, tools, options)` API
- `opencode_python/src/opencode_python/core/session.py` - source of messages

**Acceptance Criteria**:
- Unit tests cover: (a) empty history, (b) text-only history, (c) assistant parts to text concatenation
- Tools output is stable and matches provider expectations (documented in tests)
- System prompt is applied in provider call path (verified via provider stub)


### Task 10: AgentRuntime (execute agents with tools)
**Description**: Implement `AgentRuntime` as the single execution entrypoint:
- Inputs: agent (by name), real Session (by id), user message, selected skills, optional provider/model overrides
- Steps: fetch agent from AgentRegistry → load session from SessionManager → build filtered tool registry → build context → run AISession (or a runtime wrapper) → emit AgentManager lifecycle events → return AgentResult

**Priority**: HIGH

**Delegation Recommendation:**
- Category: `ultrabrain` - integration-heavy: concurrency, lifecycle events, provider boundary
- Skills: [`python-programmer`, `git-master`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`, `git-master`
- ❌ OMITTED all others: not relevant

**Depends On**: Tasks 6, 9

**References**:
- `opencode_python/src/opencode_python/agents/__init__.py` - existing `AgentManager` lifecycle events to reuse
- `opencode_python/src/opencode_python/ai_session.py` - current execution runner
- `opencode_python/src/opencode_python/ai/tool_execution.py` - tool execution manager

**Acceptance Criteria**:
- Happy-path execution returns `AgentResult` with response text and metadata
- Tool filtering is enforced before provider call (verified via test stubs)
- AgentManager transitions: initialized → ready → executing → cleanup (or error)


### Task 11: SDK Client API wiring (Phase 1 surface)
**Description**: Expose Phase 1 features from `OpenCodeAsyncClient` (and sync wrapper as needed):
- `register_agent(agent)`
- `get_agent(name)`
- `execute_agent(agent_name, session_id, user_message, options)`

**Priority**: HIGH

**Delegation Recommendation:**
- Category: `unspecified-high`
- Skills: [`python-programmer`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`
- ❌ OMITTED all others: not relevant

**Depends On**: Task 10

**References**:
- `opencode_python/src/opencode_python/sdk/client.py` - current SDK client patterns + error handling

**Acceptance Criteria**:
- Public client methods exist and are documented via docstrings
- Sync client exposes equivalent methods (or explicitly documents omission)
- Tests validate the new methods are callable and integrate with runtime stub


### Task 12: End-to-end integration tests + example update
**Description**: Add/extend an integration test that exercises:
- Create session
- Register custom agent
- Execute agent with filtered tools and injected skills (using a stub provider to avoid network)

Update/add an example under `opencode_python/docs/examples/` if appropriate.

**Priority**: HIGH

**Delegation Recommendation:**
- Category: `unspecified-high`
- Skills: [`python-programmer`]

**Skills Evaluation**:
- ✅ INCLUDED `python-programmer`
- ❌ OMITTED `agent-browser`, `dev-browser`: not needed (non-UI)
- ❌ OMITTED all others: not relevant

**Depends On**: Tasks 10, 11

**Acceptance Criteria**:
- `python -m pytest -q` → PASS
- `python -m ruff check opencode_python` → PASS
- `python -m mypy opencode_python/src/opencode_python` → PASS
- Integration test verifies: (a) agent registered, (b) tool set filtered per agent, (c) system prompt contains injected skills


## Commit Strategy

Recommended atomic commits (in order):
1. `test(sdk): add regression coverage for SessionStorage base_dir` (Task 2)
2. `fix(agents): stop fabricating Session in AgentExecutor` (Task 3)
3. `fix(ai): initialize ToolExecutionManager with complete tool registry` (Task 4)
4. `feat(agents): introduce phase1 contracts (AgentResult/AgentContext)` (Task 5)
5. `feat(agents): add AgentRegistry` (Task 6)
6. `feat(tools): add ToolPermissionFilter` (Task 7)
7. `feat(skills): add SkillInjector` (Task 8)
8. `feat(agents): add ContextBuilder` (Task 9)
9. `feat(agents): add AgentRuntime` (Task 10)
10. `feat(sdk): expose agent APIs on client` (Task 11)
11. `test(agents): add end-to-end runtime integration test` (Task 12)


## Success Criteria

Functional:
- A custom agent can be registered and executed against a real session.
- The tool set exposed to the provider is filtered by agent permissions.
- Skills can be loaded from disk and are injected into the system prompt used for execution.

Verification:
- `python -m pytest -q`
- `python -m ruff check opencode_python`
- `python -m mypy opencode_python/src/opencode_python`
