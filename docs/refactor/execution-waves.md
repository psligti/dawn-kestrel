# Execution Waves

The Dawn Kestrel refactor is organized into 8 execution waves to maximize parallelization while respecting dependencies. Each wave contains related tasks that can be executed in parallel.

## Wave Overview

```mermaid
gantt
    title 8-Wave Execution Plan
    dateFormat  YYYY-MM-DD
    axisFormat  Wave %W

    section Foundation
    Wave 1: Foundation            :milestone, w1, 2025-02-09, 0d
    section Plugin System
    Wave 2: Plugin System        :milestone, w2, after w1, 0d
    section Error Handling
    Wave 3: Error Handling       :milestone, w3, after w2, 0d
    section Storage & State
    Wave 4: Storage & State      :milestone, w4, after w3, 0d
    section Coordination
    Wave 5: Coordination         :milestone, w5, after w4, 0d
    section Cross-Cutting
    Wave 6: Cross-Cutting        :milestone, w6, after w5, 0d
    section Reliability
    Wave 7: Reliability           :milestone, w7, after w6, 0d
    section Integration
    Wave 8: Integration           :milestone, w8, after w7, 0d
```

## Wave 1: Foundation

**Goal**: Establish foundational infrastructure for all subsequent waves

**Tasks** (4 total):
1. ✅ Establish baseline test coverage
2. ✅ Setup DI container (dependency-injector)
3. ✅ Replace Settings singleton with Configuration Object
4. ✅ Design plugin discovery system (entry_points)

**Parallelization**: Tasks 2, 3, 4 can run in parallel after Task 1 completes

**Blocks**: All subsequent waves (2-8)

```mermaid
graph LR
    subgraph Wave 1
        T1[T1: Baseline Coverage]
        T2[T2: DI Container]
        T3[T3: Config Object]
        T4[T4: Plugin Discovery]
    end

    T1 --> T2
    T1 --> T3
    T1 --> T4

    T2 -.-> Wave2[Wave 2]
    T3 -.-> Wave2
    T4 -.-> Wave2

    style T1 fill:#e1ffe1
    style T2 fill:#e1ffe1
    style T3 fill:#e1ffe1
    style T4 fill:#e1ffe1
```

**Acceptance Criteria**:
- ✅ Baseline coverage report saved to `.sisyphus/baseline_coverage.txt`
- ✅ DI container resolves SessionStorage and DefaultSessionService
- ✅ Configuration object provides storage_dir, config_dir, cache_dir
- ✅ Entry points groups defined in pyproject.toml

## Wave 2: Plugin System

**Goal**: Enable dynamic discovery and loading of tools, providers, and agents

**Tasks** (4 total):
5. ✅ Implement tool plugin discovery
6. ✅ Implement provider plugin discovery
7. ✅ Implement agent plugin discovery
8. ✅ Register all built-in tools/providers/agents as plugins

**Parallelization**: Tasks 5, 6, 7, 8 can run in parallel

**Blocks**: Wave 3 (Error Handling)

```mermaid
graph LR
    subgraph Wave 2
        T5[T5: Tool Plugins]
        T6[T6: Provider Plugins]
        T7[T7: Agent Plugins]
        T8[T8: Register Built-ins]
    end

    T5 -.-> Wave3[Wave 3]
    T6 -.-> Wave3
    T7 -.-> Wave3
    T8 -.-> Wave3

    style T5 fill:#fff4e1
    style T6 fill:#fff4e1
    style T7 fill:#fff4e1
    style T8 fill:#fff4e1
```

**Acceptance Criteria**:
- ✅ All 22 tools discovered via plugins
- ✅ All 4 providers discovered via plugins
- ✅ All built-in agents discovered via plugins
- ✅ Entry point decorators added to all components
- ✅ Backward compatibility maintained for direct imports

## Wave 3: Error Handling

**Goal**: Replace exception-based error handling with explicit Result pattern

**Tasks** (3 total):
9. ✅ Implement Result pattern (Ok/Err/Pass)
10. ⏳ Wrap existing exceptions with Result types
11. ⏳ Update all public APIs to return Results

**Parallelization**: Sequential (Task 10 depends on Task 9, Task 11 depends on Task 10)

**Blocks**: Wave 4 (Storage & State)

```mermaid
graph LR
    subgraph Wave 3
        T9[T9: Result Pattern]
        T10[T10: Wrap Exceptions]
        T11[T11: Update Public APIs]
    end

    T9 --> T10
    T10 --> T11

    T11 -.-> Wave4[Wave 4]

    style T9 fill:#ffe1e1
    style T10 fill:#ffe1e1
    style T11 fill:#ffe1e1
```

**Acceptance Criteria**:
- ✅ Result types (Ok, Err, Pass) created with bind/map/fold
- ⏳ All domain functions return Results (not raise exceptions)
- ⏳ SDK client methods return Results
- ⏳ CLI commands handle Results correctly
- ⏳ TUI displays Result errors

## Wave 4: Storage & State

**Goal**: Abstract storage with Repository pattern and manage agent state with FSM

**Tasks** (4 total):
12. ⏳ Implement Repository pattern (session/message/part)
13. ⏳ Implement Unit of Work for transactions
14. ⏳ Implement State (FSM) for agent lifecycle
15. ⏳ Refactor storage layer to use Repository

**Parallelization**: Tasks 12, 13, 14 can run in parallel; Task 15 waits for all three

**Blocks**: Wave 5 (Coordination)

```mermaid
graph LR
    subgraph Wave 4
        T12[T12: Repository]
        T13[T13: Unit of Work]
        T14[T14: State FSM]
        T15[T15: Storage Refactor]
    end

    T12 --> T15
    T13 --> T15
    T14 --> T15

    T15 -.-> Wave5[Wave 5]

    style T12 fill:#e1ffe1
    style T13 fill:#e1ffe1
    style T14 fill:#f5e1ff
    style T15 fill:#e1ffe1
```

**Acceptance Criteria**:
- ⏳ Repository interfaces defined for session/message/part
- ⏳ Unit of Work provides transactional consistency
- ⏳ Agent lifecycle states explicitly defined with valid transitions
- ⏳ All storage operations go through Repository abstraction

## Wave 5: Coordination & Extension

**Goal**: Simplify extension and centralize coordination with design patterns

**Tasks** (5 total):
16. ⏳ Implement Adapter pattern for providers
17. ⏳ Implement Adapter pattern for tools
18. ⏳ Implement Facade for composition root
19. ⏳ Implement Mediator for event coordination
20. ⏳ Implement Command pattern for actions

**Parallelization**: Tasks 16, 17, 18, 19 can run in parallel; Task 20 waits for 16, 17, 18

**Blocks**: Wave 6 (Cross-Cutting)

```mermaid
graph LR
    subgraph Wave 5
        T16[T16: Provider Adapters]
        T17[T17: Tool Adapters]
        T18[T18: Facade]
        T19[T19: Mediator]
        T20[T20: Command Pattern]
    end

    T16 --> T20
    T17 --> T20
    T18 -.-> T20
    T19 -.-> T20

    T20 -.-> Wave6[Wave 6]

    style T16 fill:#f5e1ff
    style T17 fill:#f5e1ff
    style T18 fill:#f5e1ff
    style T19 fill:#f5e1ff
    style T20 fill:#f5e1ff
```

**Acceptance Criteria**:
- ⏳ Provider adapters enable extension without core edits
- ⏳ Tool adapters enable extension without core edits
- ⏳ Facade simplifies composition root initialization
- ⏳ Mediator coordinates component interactions
- ⏳ Commands encapsulate actions with provenance

## Wave 6: Cross-Cutting

**Goal**: Apply cross-cutting concerns uniformly via decorators and patterns

**Tasks** (5 total):
21. ⏳ Implement Decorator/Proxy for logging
22. ⏳ Implement Decorator/Proxy for metrics
23. ⏳ Implement Decorator/Proxy for caching
24. ⏳ Implement Null Object for optional deps
25. ⏳ Implement Strategy pattern for swappable algos

**Parallelization**: All tasks can run in parallel

**Blocks**: Wave 7 (Reliability)

```mermaid
graph LR
    subgraph Wave 6
        T21[T21: Logging Decorator]
        T22[T22: Metrics Decorator]
        T23[T23: Caching Decorator]
        T24[T24: Null Object]
        T25[T25: Strategy Pattern]
    end

    T21 -.-> Wave7[Wave 7]
    T22 -.-> Wave7
    T23 -.-> Wave7
    T24 -.-> Wave7
    T25 -.-> Wave7

    style T21 fill:#e1f5ff
    style T22 fill:#e1f5ff
    style T23 fill:#e1f5ff
    style T24 fill:#e1f5ff
    style T25 fill:#f5e1ff
```

**Acceptance Criteria**:
- ⏳ Logging applied uniformly to all services
- ⏳ Metrics collected for all operations
- ⏳ Caching applied to expensive operations
- ⏳ Null Object eliminates None checks for optional deps
- ⏳ Strategy pattern enables swapping storage backends, routing, retry policies

## Wave 7: Reliability

**Goal**: Add resilience patterns for LLM calls and external dependencies

**Tasks** (5 total):
26. ✅ Implement Circuit Breaker for LLM calls
27. ⏳ Implement Bulkhead for resource isolation
28. ⏳ Implement Retry + Backoff for transient failures
29. ⏳ Implement Rate Limiter for API calls
30. ⏳ Apply reliability patterns uniformly

**Parallelization**: Tasks 26, 27, 28, 29 can run in parallel; Task 30 waits for all four

**Blocks**: Wave 8 (Integration)

```mermaid
graph LR
    subgraph Wave 7
        T26[T26: Circuit Breaker]
        T27[T27: Bulkhead]
        T28[T28: Retry + Backoff]
        T29[T29: Rate Limiter]
        T30[T30: Apply Uniformly]
    end

    T26 --> T30
    T27 --> T30
    T28 --> T30
    T29 --> T30

    T30 -.-> Wave8[Wave 8]

    style T26 fill:#ffe1e1
    style T27 fill:#ffe1e1
    style T28 fill:#ffe1e1
    style T29 fill:#ffe1e1
    style T30 fill:#ffe1e1
```

**Acceptance Criteria**:
- ✅ Circuit breaker prevents cascading failures
- ⏳ Bulkhead isolates resource pools
- ⏳ Retry with exponential backoff handles transient failures
- ⏳ Rate limiter prevents API throttling
- ⏳ All reliability patterns applied consistently

## Wave 8: Final Integration

**Goal**: Integrate all patterns and complete documentation

**Tasks** (6 total):
31. ⏳ Refactor composition root to use DI container
32. ⏳ Update CLI to use new APIs
33. ⏳ Update TUI to use new APIs
34. ⏳ Comprehensive integration tests
35. ⏳ Documentation (patterns + migration)
36. ⏳ Final verification and cleanup

**Parallelization**: Tasks 32 and 33 can run in parallel after Task 31; Task 34 waits for 32 and 33

**Blocks**: None (final wave)

```mermaid
graph LR
    subgraph Wave 8
        T31[T31: Composition Root]
        T32[T32: CLI Updates]
        T33[T33: TUI Updates]
        T34[T34: Integration Tests]
        T35[T35: Documentation]
        T36[T36: Final Verification]
    end

    T31 --> T32
    T31 --> T33
    T32 --> T34
    T33 --> T34
    T34 --> T35
    T35 --> T36

    style T31 fill:#e1f5ff
    style T32 fill:#e1f5ff
    style T33 fill:#e1f5ff
    style T34 fill:#e1ffe1
    style T35 fill:#fff4e1
    style T36 fill:#e1ffe1
```

**Acceptance Criteria**:
- ⏳ Composition root uses DI container exclusively
- ⏳ CLI handles Results and new APIs correctly
- ⏳ TUI displays Results and uses new APIs correctly
- ⏳ All integration tests pass
- ⏳ All patterns documented in docs/patterns.md
- ⏳ Migration guide (MIGRATION.md) complete
- ⏳ Full test suite passes with coverage >= baseline

## Wave Dependency Graph

```mermaid
graph TB
    subgraph "Wave 1: Foundation"
        W1[W1]
    end

    subgraph "Wave 2: Plugin System"
        W2[W2]
    end

    subgraph "Wave 3: Error Handling"
        W3[W3]
    end

    subgraph "Wave 4: Storage & State"
        W4[W4]
    end

    subgraph "Wave 5: Coordination"
        W5[W5]
    end

    subgraph "Wave 6: Cross-Cutting"
        W6[W6]
    end

    subgraph "Wave 7: Reliability"
        W7[W7]
    end

    subgraph "Wave 8: Integration"
        W8[W8]
    end

    W1 --> W2
    W2 --> W3
    W3 --> W4
    W4 --> W5
    W5 --> W6
    W6 --> W7
    W7 --> W8

    style W1 fill:#e1ffe1
    style W2 fill:#fff4e1
    style W3 fill:#ffe1e1
    style W4 fill:#e1ffe1
    style W5 fill:#f5e1ff
    style W6 fill:#e1f5ff
    style W7 fill:#ffe1e1
    style W8 fill:#e1ffe1
```

## Parallelization Strategy

### Within-Wave Parallelization

| Wave | Parallel Tasks | Speedup |
|------|---------------|---------|
| Wave 1 | 3 (Tasks 2, 3, 4) | 3x |
| Wave 2 | 4 (Tasks 5, 6, 7, 8) | 4x |
| Wave 3 | 0 (sequential) | 1x |
| Wave 4 | 3 (Tasks 12, 13, 14) | 3x |
| Wave 5 | 4 (Tasks 16, 17, 18, 19) | 4x |
| Wave 6 | 5 (Tasks 21-25) | 5x |
| Wave 7 | 4 (Tasks 26-29) | 4x |
| Wave 8 | 2 (Tasks 32, 33) | 2x |

### Overall Parallelization Speedup

**Estimated speedup: ~40% faster than sequential execution**

This is achieved by:
- Within-wave parallelization (average 3x)
- Wave pipeline (later waves start as soon as dependencies complete)
- Independent task execution within parallel tasks

## Critical Path

```
Wave 1 → Wave 2 → Wave 3 → Wave 4 → Wave 5 → Wave 6 → Wave 7 → Wave 8
```

Tasks on critical path:
- Task 1: Baseline (must start first)
- Task 2: DI Container (foundational)
- Task 3: Config Object (foundational)
- Task 4: Plugin Discovery (foundational)
- Task 8: Register Built-ins (enables all plugin-based loading)
- Task 9: Result Pattern (foundational for error handling)
- Task 11: Update Public APIs (exposes Results to users)
- Task 15: Storage Refactor (enables Repository pattern)
- Task 20: Command Pattern (foundational for orchestration)
- Task 25: Strategy Pattern (foundational for reliability)
- Task 30: Apply Reliability (enables final integration)
- Task 31: Composition Root (final wiring)
- Task 34: Integration Tests (verifies everything)
- Task 35: Documentation (final deliverable)
- Task 36: Final Verification (sign-off)

## Rollback Strategy

Each wave has checkpoints that enable rollback if issues arise:

| Wave | Checkpoint | Rollback Mechanism |
|------|------------|-------------------|
| Wave 1 | Task 4 completion | git revert to pre-refactor |
| Wave 2 | Task 8 completion | Disable entry_points, use fallback registry |
| Wave 3 | Task 11 completion | Keep Result types, wrap with exception adapters |
| Wave 4 | Task 15 completion | Keep Repository facade, revert implementation |
| Wave 5 | Task 20 completion | Keep Adapter interfaces, revert to direct calls |
| Wave 6 | Task 25 completion | Remove decorators, keep Null Object shims |
| Wave 7 | Task 30 completion | Disable reliability wrappers |
| Wave 8 | Task 36 completion | Final rollback to Wave 7 checkpoint |

See [dependencies.md](dependencies.md) for full task dependency matrix.
