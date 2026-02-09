# Draft: Dawn Kestrel SDK Refactoring

## Request

Refactor dawn_kestrel SDK to ensure:
- Excellent composition of objects and variables
- Limits blast exposure when changes happen
- Apply all relevant design patterns for easy feature addition
- **Most importantly: ensure it works**

## Design Patterns Reference

User provided a comprehensive pattern catalog:
- Core patterns: Strategy, Command, Chain of Responsibility, Ports & Adapters, Result (Railway)
- Persistence: Repository, Unit of Work
- Workflows: State (FSM), Composite, Template Method, Mediator
- Integration: Adapter, Facade, Decorator, Proxy, Bridge
- Construction: Builder, Factory, Registry/Plugin, DI
- Configuration: Configuration Object, Null Object
- Reliability: Circuit Breaker, Bulkhead, Retry + Backoff, Rate Limiter
- Domain: Specification/Rules Engine, Visitor

## Initial Observations

- SDK is in Python
- Key modules: agents, providers, tools, storage, session, context, LLM integration
- Entry points: SDK client, CLI, TUI
- Has existing review/verifier agents

## Test Infrastructure Analysis (Completed)

**Framework**: PyTest with pytest-asyncio
- Config: pyproject.toml with testpaths=["tests"], coverage enabled
- Location: tests/ directory with subfolders for packages

**Current Testing Patterns**:
- Heavy use of unittest.mock.patch, Mock, AsyncMock
- Async testing with @pytest.mark.asyncio
- UI fixtures in conftest.py
- Separation of unit tests (mock-based) and integration tests (orchestrator with mocks)

**Coverage Assessment**:
- Well-covered: SDK clients, core models, agent lifecycle, UI/TUI, integration tests
- Potentially weaker: dawn_kestrel.tools internals, utilities

**Test Doubles**:
- Mocks and AsyncMock pervasive
- patch() for dependency substitution
- Fixtures for reusable test context

**Implication for Refactor**:
- Solid test foundation to support comprehensive refactor
- Need to maintain dependency injection points for test stability
- Consider expanding coverage for under-tested modules

## Architecture Analysis (Completed)

**Module Structure**:
- **dawn_kestrel/sdk/**: High-level client wrappers (OpenCodeAsyncClient, OpenCodeSyncClient)
- **dawn_kestrel/cli/**: CLI commands and entry points
- **dawn_kestrel/tui/**: Textual-based TUI
- **dawn_kestrel/core/**: Data models, event bus, session management, settings
- **dawn_kestrel/llm/**: LLM client abstractions and provider integration
- **dawn_kestrel/providers/**: Provider adapters and registry
- **dawn_kestrel/storage/**: Storage layer (JSON file-based, in-memory)
- **dawn_kestrel/session/**: Session logic, export/import
- **dawn_kestrel/context/**: Context building and pipeline
- **dawn_kestrel/skills/**: Skill discovery and injection
- **dawn_kestrel/tools/**: Tool framework and built-in tools
- **dawn_kestrel/agents/**: Agent orchestration and registry

**Entry Points**:
- SDK: OpenCodeAsyncClient/OpenCodeSyncClient (sdk/client.py)
- CLI: main.py aggregates commands
- TUI: app.py built on Textual

**Current Design Patterns**:
- Partial DI (IO/Progress/Notification handlers injected)
- Registry/Factory (ProviderRegistry, ToolRegistry)
- Builder (ContextBuilder)
- Event-driven (event_bus)
- Bridge/Adapter (SDK bridges session lifecycle to LLM providers)

**Coupling Issues**:
- CLI/TUI both depend on DefaultSessionService and sometimes instantiate concrete storage
- Storage layer is JSON-file-based (simple but may be bottleneck)
- Code paths sometimes construct concrete storage rather than receiving abstractions
- Potential circular event flows in event bus system

**External Dependencies**:
- LLM providers: OpenAI, ZAI, ZAICodingPlan
- Storage: JSON file-based, in-memory
- CLI: Click + Rich
- TUI: Textual
- Skills: frontmatter parsing
- Tools: LSP integration

## Composition Analysis (Completed)

**Composition Root**: OpenCodeAsyncClient (sdk/client.py)
- Directly instantiates: SessionStorage, DefaultSessionService, ProviderRegistry, AgentRegistry, AgentRuntime, SessionLifecycle
- Wires registries together in __init__ (lines 64-89)
- Creates storage_dir, project_dir, and all dependencies

**Dependency Injection**:
- Partial DI via constructor parameters (io_handler, progress_handler, notification_handler)
- Factory functions used: create_agent_registry, create_provider_registry, create_agent_runtime
- NO formal DI container - dependencies wired imperatively in bootstrap
- Global Settings singleton used across modules

**Adding New Agent Type**:
- Built-in agents: Edit dawn_kestrel/agents/builtin.py + update get_all_agents()
- Runtime agents: Use client.register_agent() (calls AgentRegistry.register_agent)
- Persistence: Optional JSON storage under storage/agent/{name}.json

**Adding New Tool**:
- Built-in tools: Add to dawn_kestrel/tools/builtin.py OR additional.py
- MUST edit dawn_kestrel/tools/__init__.py to register
- Update create_complete_registry() and __all__ exports
- Tools hard-coded in ToolRegistry initialization (22 tools listed explicitly)

**Adding New LLM Provider**:
- Implement provider class in dawn_kestrel/providers/
- MUST edit PROVIDER_FACTORIES map in dawn_kestrel/providers/__init__.py
- Update get_provider() function to handle new provider_id

**Blast Exposure - HIGH AREAS**:

1. **Tool Registration** (highest blast)
   - Adding tool: Edit tool file + edit tools/__init__.py (2 files)
   - Removing tool: Edit tools/__init__.py (1 file)
   - Impact: Every tool change touches central registry file

2. **Provider Registration** (high blast)
   - Adding provider: Implement provider + edit providers/__init__.py (2 files)
   - Static factory map must be updated
   - No plugin mechanism for discovery

3. **Built-in Agent Registration** (medium blast)
   - Adding built-in agent: Edit builtin.py (1 file)
   - get_all_agents() returns list - automatically seeded

4. **Global Settings Singleton** (medium blast)
   - Used by all modules via get_storage_dir(), get_config_dir(), get_cache_dir()
   - Changes ripple through entire codebase

5. **Composition Root** (low blast, high impact)
   - OpenCodeAsyncClient directly instantiates everything
   - Changing wiring requires editing client bootstrap code
   - No separation of concerns in bootstrap

**Hardcoded Dependencies**:
- SessionStorage instantiated directly in OpenCodeAsyncClient.__init__
- Tool registry initialization hard-codes all 22 tools
- Provider factory map is static dictionary
- Storage paths derived from global settings

**No Discovery/Plugin Mechanisms**:
- Agents: Static seeding from get_all_agents()
- Tools: Hard-coded registration
- Providers: Static factory map
- No entry points or dynamic discovery

## User Decisions

**Blast Exposure Areas:**
- Adding new agent types
- Adding new tools
- Adding new LLM providers
- **All three** need to be made easier

**Verification Strategy:**
- Regression tests (comprehensive unit/integration)
- Integration tests (end-to-end)
- Manual verification plan
- Test infrastructure setup first, then TDD refactor

**API Compatibility:**
- Breaking changes are acceptable
- **Requirement**: Document upgrade paths for users

**Development Workflow:**
- Comprehensive refactor (entire SDK at once)
- Single cohesive work plan

## Final User Decisions

**Refactor Phasing**:
- **One massive plan** - Complete comprehensive refactor in single work plan

**Pattern Priority**:
- **ALL patterns** - Apply all relevant design patterns from catalog to SDK
  - DI Container (formal dependency injection)
  - Plugin/Registry (dynamic discovery for agents, tools, providers)
  - Result/Railway (explicit Ok/Err/Pass for error handling)
  - Adapter (provider/tool extension without touching core)
  - Facade (simplified composition root)
  - Command (encapsulated actions with provenance)
  - State (FSM) for agent/workflow phases
  - Strategy (swappable algorithms/policies)
  - Repository (storage abstraction)
  - Unit of Work (transactional consistency)
  - Mediator (centralized coordination)
  - Decorator/Proxy (cross-cutting concerns)
  - Null Object (optional dependencies)
  - Circuit Breaker, Bulkhead, Retry (reliability)
  - Configuration Object (centralized settings)
  - Registry/Plugin (extensibility)
  - Observer (event handling)
  - Composite (plan trees)

**DI Approach**:
- **Use existing library** - dependency-injector, injector, or similar

**Plugin Discovery**:
- **Python entry_points** - Standard packaging mechanism for plugin discovery

## Current Issues Identified

**Composition Problems**:
- Single composition root (OpenCodeAsyncClient) creates everything directly
- No formal DI container - dependencies wired imperatively
- Global Settings singleton used everywhere
- No separation of concerns in bootstrap

**Blast Exposure Areas** (high to low):
1. Tool Registration - 2 files to edit for every tool change
2. Provider Registration - static factory map in providers/__init__.py
3. Agent Registration - built-ins seeded statically
4. Global Settings - single point of failure
5. Composition Root - changing wiring requires editing bootstrap

**Missing Design Patterns**:
- No Plugin/Registry pattern for dynamic discovery
- No Adapter pattern for provider/tool extension
- No Facade for simplified composition
- No Builder for complex object construction
- No Strategy pattern for pluggable algorithms
- No Result pattern for explicit error handling
- No Repository pattern for storage abstraction
- No Unit of Work for transactional consistency
- No Command pattern for encapsulated actions
- No State (FSM) for workflow phases
- No Mediator for centralized coordination
- No Decorator/Proxy for cross-cutting concerns
- No Null Object for optional dependencies
- No Circuit Breaker/Bulkhead/Retry for reliability
- No Configuration Object pattern (replaced with singleton)
