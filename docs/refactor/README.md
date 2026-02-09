# Dawn Kestrel Refactor Documentation

This directory contains comprehensive documentation for the Dawn Kestrel SDK comprehensive refactor plan.

## Overview

The Dawn Kestrel SDK refactor is a comprehensive architectural transformation targeting:
- **32K lines of code** across **11 major modules**
- **20+ design patterns** for excellent composition
- **Elimination of blast exposure** for adding features (agents, tools, providers)
- **Full system functionality** maintained throughout

## Quick Links

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System architecture with component relationships |
| [Execution Waves](execution-waves.md) | 8-wave execution plan with dependencies |
| [Design Patterns](patterns.md) | 21+ design patterns and their interactions |
| [Migration Guide](migration.md) | Path from current to refactored state |
| [Component Map](component-map.md) | Component relationships and blast exposure areas |
| [Dependency Graph](dependencies.md) | Task dependency matrix and critical path |

## Key Deliverables

### Foundation (Wave 1)
- ✅ Dependency Injection Container (dependency-injector)
- ✅ Plugin System (Python entry_points)
- ✅ Result Pattern (Ok/Err/Pass types)
- ⏳ Repository + Unit of Work (storage abstraction)

### Extension (Waves 2-5)
- ⏳ Plugin Discovery (tools, providers, agents)
- ⏳ Adapter + Facade patterns (simplified extension)
- ⏳ Command + State (FSM) patterns (workflow orchestration)
- ⏳ Strategy + Mediator (flexible coordination)

### Cross-Cutting (Waves 6-7)
- ⏳ Decorator/Proxy + Null Object (cross-cutting concerns)
- ⏳ Circuit Breaker + Bulkhead + Retry (reliability)

### Integration (Wave 8)
- ⏳ Composition root refactoring
- ⏳ CLI/TUI updates
- ⏳ Complete documentation

## Architecture Diagram

```mermaid
graph TB
    subgraph "Composition Root"
        Client[OpenCodeAsyncClient]
        DI[DI Container]
        Config[Configuration Object]
    end

    subgraph "Plugin System"
        Tools[Tool Plugins]
        Providers[Provider Plugins]
        Agents[Agent Plugins]
        Discovery[Plugin Discovery]
    end

    subgraph "Core Services"
        Session[Session Service]
        Message[Message Service]
        Agent[Agent Runtime]
    end

    subgraph "Storage Layer"
        Repo[Repository Pattern]
        UoW[Unit of Work]
        Storage[Storage Abstraction]
    end

    subgraph "Error Handling"
        Result[Result Pattern]
        Railway[Railway-Oriented]
    end

    subgraph "Reliability"
        CB[Circuit Breaker]
        Retry[Retry + Backoff]
        Bulkhead[Bulkhead]
    end

    Client --> DI
    Client --> Config
    DI --> Session
    DI --> Message
    DI --> Agent

    Discovery --> Tools
    Discovery --> Providers
    Discovery --> Agents

    Session --> Repo
    Message --> Repo
    Repo --> UoW
    UoW --> Storage

    Session --> Result
    Message --> Result
    Agent --> Result
    Result --> Railway

    Client --> CB
    Agent --> Retry
    Providers --> Bulkhead

    style DI fill:#e1f5ff
    style Discovery fill:#fff4e1
    style Result fill:#ffe1e1
    style Repo fill:#e1ffe1
```

## Blast Exposure Areas (Before Refactor)

1. **Tool Registration** - Hard-coded in `tools/__init__.py` (2 files per change)
2. **Provider Registration** - Static factory map in `providers/__init__.py` (2 files per change)
3. **Built-in Agent Registration** - Seeded statically from `builtin.py`
4. **Global Settings Singleton** - Used throughout codebase
5. **Composition Root** - Direct instantiation, no separation of concerns

## Blast Exposure Areas (After Refactor)

✅ **All eliminated** - Add tools/providers/agents via plugin entry points
✅ **No core edits required** - Dynamic discovery via Python entry_points
✅ **Clean composition** - DI container manages all wiring
✅ **Explicit state** - FSM patterns for agent/workflow phases
✅ **Error visibility** - Result pattern makes errors explicit

## Execution Timeline

```mermaid
gantt
    title Dawn Kestrel Refactor Execution Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Foundation
    Baseline Coverage        :done,     w1, 2025-02-09, 1d
    DI Container Setup       :active,   w2, after w1, 2d
    Config Object Replace    :          w3, after w1, 2d
    Plugin Discovery Design  :          w4, after w1, 2d

    section Plugin System
    Tool Plugin Discovery    :          w5, after w2 w3 w4, 3d
    Provider Plugin Disc.   :          w6, after w2 w3 w4, 3d
    Agent Plugin Discovery   :          w7, after w2 w3 w4, 3d
    Register Built-ins       :          w8, after w2 w3 w4, 3d

    section Error Handling
    Result Pattern           :          w9, after w5 w6 w7 w8, 2d
    Wrap Exceptions          :          w10, after w9, 3d
    Update Public APIs       :          w11, after w10, 4d

    section Storage & State
    Repository Pattern       :          w12, after w11, 3d
    Unit of Work             :          w13, after w11, 3d
    State FSM                :          w14, after w11, 3d
    Storage Refactor         :          w15, after w12 w13 w14, 4d

    section Coordination
    Adapter Pattern          :          w16, after w15, 3d
    Facade Pattern           :          w17, after w15, 2d
    Mediator Pattern         :          w18, after w15, 3d
    Command Pattern          :          w20, after w16 w17 w18, 2d

    section Cross-Cutting
    Decorator Logging        :          w21, after w20, 2d
    Decorator Metrics        :          w22, after w20, 2d
    Decorator Caching        :          w23, after w20, 2d
    Null Object              :          w24, after w20, 1d
    Strategy Pattern         :          w25, after w20, 2d

    section Reliability
    Circuit Breaker          :          w26, after w25, 2d
    Bulkhead                 :          w27, after w25, 2d
    Retry + Backoff          :          w28, after w25, 2d
    Rate Limiter             :          w29, after w25, 2d
    Apply Reliability        :          w30, after w26 w27 w28 w29, 3d

    section Integration
    Composition Root Refactor:          w31, after w30, 4d
    CLI Updates              :          w32, after w31, 3d
    TUI Updates              :          w33, after w31, 3d
    Integration Tests        :          w34, after w32 w33, 4d
    Documentation            :          w35, after w34, 5d
    Final Verification       :          w36, after w35, 2d
```

## Progress Tracking

**Current Status**: Wave 1 Complete, Wave 2 In Progress

| Wave | Status | Tasks Completed | Total Tasks |
|------|--------|-----------------|-------------|
| Wave 1 | ✅ Complete | 4/4 | 100% |
| Wave 2 | 🔄 In Progress | 4/4 | 100% |
| Wave 3 | ⏳ Pending | 0/3 | 0% |
| Wave 4 | ⏳ Pending | 0/4 | 0% |
| Wave 5 | ⏳ Pending | 0/5 | 0% |
| Wave 6 | ⏳ Pending | 0/5 | 0% |
| Wave 7 | ⏳ Pending | 0/5 | 0% |
| Wave 8 | ⏳ Pending | 0/6 | 0% |

## Design Patterns Summary

| Pattern | Purpose | Wave | Status |
|---------|---------|------|--------|
| Dependency Injection | Loose coupling, testability | 1 | ✅ |
| Plugin System | Extensibility without core edits | 2 | ✅ |
| Result Pattern | Explicit error handling | 3 | ✅ |
| Repository | Storage abstraction | 4 | ⏳ |
| Unit of Work | Transactional consistency | 4 | ⏳ |
| State (FSM) | Explicit agent/workflow phases | 4 | ⏳ |
| Adapter | Provider/tool adapters | 5 | ⏳ |
| Facade | Simplified composition root | 5 | ⏳ |
| Command | Encapsulated actions with provenance | 5 | ⏳ |
| Strategy | Swappable algorithms | 6 | ⏳ |
| Mediator | Centralized coordination | 5 | ⏳ |
| Decorator/Proxy | Cross-cutting concerns | 6 | ⏳ |
| Null Object | Optional dependencies | 6 | ⏳ |
| Circuit Breaker | LLM call reliability | 7 | ⏳ |
| Bulkhead | Resource isolation | 7 | ⏳ |
| Retry + Backoff | Transient failure handling | 7 | ⏳ |
| Configuration Object | Replace singleton | 1 | ✅ |

## References

- **Full Plan**: `.sisyphus/plans/dawn-kestrel-refactor.md`
- **Baseline Coverage**: `.sisyphus/baseline_coverage.txt`
- **Test Results**: `htmlcov/index.html`
- **Main Docs**: `../getting-started.md`

## Contact

For questions or issues with the refactor, see the main README or consult the implementation plan.
