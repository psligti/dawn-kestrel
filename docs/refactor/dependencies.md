# Dependency Graph

This document provides a detailed task dependency matrix and critical path analysis for the Dawn Kestrel refactor.

## Full Task Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2-36 | None (must start first) |
| 2 | 1 | 5-36 | 3, 4 |
| 3 | 1 | 4-36 | 2 |
| 4 | 1 | 5-36 | 2, 3 |
| 5 | 2, 3, 4 | 6-36 | 6, 7, 8 |
| 6 | 2, 3, 4 | 7-36 | 5, 7, 8 |
| 7 | 2, 3, 4 | 8-36 | 5, 6, 8 |
| 8 | 2, 3, 4 | 9-36 | 5, 6, 7 |
| 9 | 5, 6, 7, 8 | 10-36 | 10, 11 |
| 10 | 9 | 11-36 | 11 |
| 11 | 9, 10 | 12-36 | None (sequential) |
| 12 | 11 | 13-36 | 13, 14, 15 |
| 13 | 11 | 14-36 | 12, 14, 15 |
| 14 | 11 | 15-36 | 12, 13, 15 |
| 15 | 12, 13, 14 | 16-36 | None (sequential) |
| 16 | 15 | 17-36 | 17, 18, 19 |
| 17 | 15 | 18-36 | 16, 18, 19 |
| 18 | 15 | 19-36 | 16, 17, 19 |
| 19 | 15 | 20-36 | 16, 17, 18, 20 |
| 20 | 16, 17, 18, 19 | 21-36 | None (sequential) |
| 21 | 20 | 22-36 | 22, 23, 24, 25 |
| 22 | 20 | 23-36 | 21, 23, 24, 25 |
| 23 | 20 | 24-36 | 21, 22, 24, 25 |
| 24 | 20 | 25-36 | 21, 22, 23, 25 |
| 25 | 20 | 26-36 | 21, 22, 23, 24 |
| 26 | 25 | 27-36 | 27, 28, 29, 30 |
| 27 | 25 | 28-36 | 26, 28, 29, 30 |
| 28 | 25 | 29-36 | 26, 27, 29, 30 |
| 29 | 25 | 30-36 | 26, 27, 28, 30 |
| 30 | 25 | 31-36 | 26, 27, 28, 29 |
| 31 | 26, 27, 28, 29, 30 | 32-36 | 32, 33 |
| 32 | 31 | 34-36 | 33 |
| 33 | 31 | 34-36 | 32 |
| 34 | 32, 33 | 35-36 | 35 |
| 35 | 34 | 36 | None (sequential) |
| 36 | 35 | None | None (final task) |

## Critical Path Analysis

```mermaid
graph TB
    CP[Critical Path] --> T1[T1: Baseline]
    T1 --> T2[T2: DI Container]
    T2 --> T3[T3: Config Object]
    T3 --> T4[T4: Plugin Discovery]
    T4 --> T8[T8: Register Built-ins]
    T8 --> T9[T9: Result Pattern]
    T9 --> T10[T10: Wrap Exceptions]
    T10 --> T11[T11: Update Public APIs]
    T11 --> T15[T15: Storage Refactor]
    T15 --> T20[T20: Command Pattern]
    T20 --> T25[T25: Strategy Pattern]
    T25 --> T30[T30: Apply Reliability]
    T30 --> T31[T31: Composition Root]
    T31 --> T34[T34: Integration Tests]
    T34 --> T35[T35: Documentation]
    T35 --> T36[T36: Final Verification]

    style CP fill:#ffcccc
    style T1 fill:#ffcccc
    style T2 fill:#ffcccc
    style T4 fill:#ffcccc
    style T8 fill:#ffcccc
    style T9 fill:#ffcccc
    style T11 fill:#ffcccc
    style T15 fill:#ffcccc
    style T20 fill:#ffcccc
    style T25 fill:#ffcccc
    style T30 fill:#ffcccc
    style T31 fill:#ffcccc
    style T34 fill:#ffcccc
    style T35 fill:#ffcccc
    style T36 fill:#ffcccc
```

### Critical Path Tasks (15 tasks)

| Task | Name | Estimated Effort | Why Critical |
|------|------|-----------------|-------------|
| 1 | Baseline Coverage | 0.5d | Must establish before any changes |
| 2 | DI Container | 2d | Foundation for all DI-managed components |
| 3 | Config Object | 2d | Required by DI container |
| 4 | Plugin Discovery | 2d | Required by all plugin-based loading |
| 8 | Register Built-ins | 3d | Enables plugin-based loading of all components |
| 9 | Result Pattern | 2d | Foundation for error handling |
| 10 | Wrap Exceptions | 3d | Domain layer must use Results |
| 11 | Update Public APIs | 4d | Exposes Results to users (breaking change) |
| 15 | Storage Refactor | 4d | Enables Repository-based storage |
| 20 | Command Pattern | 2d | Foundation for orchestration |
| 25 | Strategy Pattern | 2d | Required for reliability patterns |
| 30 | Apply Reliability | 3d | All reliability must be applied |
| 31 | Composition Root | 4d | Final wiring with DI container |
| 34 | Integration Tests | 4d | Verifies all components work together |
| 35 | Documentation | 5d | Required deliverable |
| 36 | Final Verification | 2d | Sign-off task |

**Total Critical Path Effort**: ~44.5 days

### Non-Critical Tasks (21 tasks)

| Task | Name | Estimated Effort | Why Non-Critical |
|------|------|-----------------|------------------|
| 5 | Tool Plugin Discovery | 3d | Can run parallel to 6, 7, 8 |
| 6 | Provider Plugin Discovery | 3d | Can run parallel to 5, 7, 8 |
| 7 | Agent Plugin Discovery | 3d | Can run parallel to 5, 6, 8 |
| 12 | Repository Pattern | 3d | Can run parallel to 13, 14 |
| 13 | Unit of Work | 3d | Can run parallel to 12, 14 |
| 14 | State FSM | 3d | Can run parallel to 12, 13 |
| 16 | Provider Adapters | 3d | Can run parallel to 17, 18, 19 |
| 17 | Tool Adapters | 3d | Can run parallel to 16, 18, 19 |
| 18 | Facade | 2d | Can run parallel to 16, 17, 19 |
| 19 | Mediator | 3d | Can run parallel to 16, 17, 18, 20 |
| 21 | Logging Decorator | 2d | Can run parallel to 22, 23, 24, 25 |
| 22 | Metrics Decorator | 2d | Can run parallel to 21, 23, 24, 25 |
| 23 | Caching Decorator | 2d | Can run parallel to 21, 22, 24, 25 |
| 24 | Null Object | 1d | Can run parallel to 21, 22, 23, 25 |
| 26 | Circuit Breaker | 2d | Can run parallel to 27, 28, 29, 30 |
| 27 | Bulkhead | 2d | Can run parallel to 26, 28, 29, 30 |
| 28 | Retry + Backoff | 2d | Can run parallel to 26, 27, 29, 30 |
| 29 | Rate Limiter | 2d | Can run parallel to 26, 27, 28, 30 |
| 32 | CLI Updates | 3d | Can run parallel to 33 |
| 33 | TUI Updates | 3d | Can run parallel to 32 |

**Total Non-Critical Effort**: ~56 days

## Dependency Graph Visualization

```mermaid
graph TB
    subgraph "Wave 1: Foundation"
        T1[T1: Baseline]
        T2[T2: DI Container]
        T3[T3: Config Object]
        T4[T4: Plugin Discovery]
    end

    subgraph "Wave 2: Plugin System"
        T5[T5: Tool Plugins]
        T6[T6: Provider Plugins]
        T7[T7: Agent Plugins]
        T8[T8: Register Built-ins]
    end

    subgraph "Wave 3: Error Handling"
        T9[T9: Result Pattern]
        T10[T10: Wrap Exceptions]
        T11[T11: Update Public APIs]
    end

    subgraph "Wave 4: Storage & State"
        T12[T12: Repository]
        T13[T13: Unit of Work]
        T14[T14: State FSM]
        T15[T15: Storage Refactor]
    end

    subgraph "Wave 5: Coordination"
        T16[T16: Provider Adapters]
        T17[T17: Tool Adapters]
        T18[T18: Facade]
        T19[T19: Mediator]
        T20[T20: Command Pattern]
    end

    subgraph "Wave 6: Cross-Cutting"
        T21[T21: Logging Decorator]
        T22[T22: Metrics Decorator]
        T23[T23: Caching Decorator]
        T24[T24: Null Object]
        T25[T25: Strategy Pattern]
    end

    subgraph "Wave 7: Reliability"
        T26[T26: Circuit Breaker]
        T27[T27: Bulkhead]
        T28[T28: Retry + Backoff]
        T29[T29: Rate Limiter]
        T30[T30: Apply Reliability]
    end

    subgraph "Wave 8: Integration"
        T31[T31: Composition Root]
        T32[T32: CLI Updates]
        T33[T33: TUI Updates]
        T34[T34: Integration Tests]
        T35[T35: Documentation]
        T36[T36: Final Verification]
    end

    T1 --> T2
    T1 --> T3
    T1 --> T4

    T2 --> T5
    T2 --> T6
    T2 --> T7
    T2 --> T8

    T3 --> T5
    T3 --> T6
    T3 --> T7
    T3 --> T8

    T4 --> T5
    T4 --> T6
    T4 --> T7
    T4 --> T8

    T5 --> T9
    T6 --> T9
    T7 --> T9
    T8 --> T9

    T9 --> T10
    T10 --> T11

    T11 --> T12
    T11 --> T13
    T11 --> T14

    T12 --> T15
    T13 --> T15
    T14 --> T15

    T15 --> T16
    T15 --> T17
    T15 --> T18
    T15 --> T19

    T16 --> T20
    T17 --> T20

    T20 --> T21
    T20 --> T22
    T20 --> T23
    T20 --> T24
    T20 --> T25

    T25 --> T26
    T25 --> T27
    T25 --> T28
    T25 --> T29

    T26 --> T30
    T27 --> T30
    T28 --> T30
    T29 --> T30

    T30 --> T31
    T31 --> T32
    T31 --> T33

    T32 --> T34
    T33 --> T34

    T34 --> T35
    T35 --> T36

    style T1 fill:#e1ffe1
    style T2 fill:#ffcccc
    style T3 fill:#ffcccc
    style T4 fill:#ffcccc
    style T8 fill:#ffcccc
    style T9 fill:#ffcccc
    style T11 fill:#ffcccc
    style T15 fill:#ffcccc
    style T20 fill:#ffcccc
    style T25 fill:#ffcccc
    style T30 fill:#ffcccc
    style T31 fill:#ffcccc
    style T34 fill:#ffcccc
    style T35 fill:#ffcccc
    style T36 fill:#ffcccc
```

## Parallelization Opportunities

### Wave 1 Parallelization

```mermaid
graph LR
    T1[T1: Baseline] --> Done[Done]
    Done --> T2[T2: DI Container]
    Done --> T3[T3: Config Object]
    Done --> T4[T4: Plugin Discovery]

    T2 -.-> Wave2[Wave 2 Start]
    T3 -.-> Wave2
    T4 -.-> Wave2

    style T2 fill:#e1f5ff
    style T3 fill:#e1f5ff
    style T4 fill:#e1f5ff
```

**Parallel Tasks**: T2, T3, T4 (3 tasks)
**Speedup**: 3x (if unlimited parallel capacity)

### Wave 2 Parallelization

```mermaid
graph LR
    Wave1[Wave 1 Done] --> T5[T5: Tool Plugins]
    Wave1 --> T6[T6: Provider Plugins]
    Wave1 --> T7[T7: Agent Plugins]
    Wave1 --> T8[T8: Register Built-ins]

    T5 -.-> Wave3[Wave 3 Start]
    T6 -.-> Wave3
    T7 -.-> Wave3
    T8 -.-> Wave3

    style T5 fill:#fff4e1
    style T6 fill:#fff4e1
    style T7 fill:#fff4e1
    style T8 fill:#fff4e1
```

**Parallel Tasks**: T5, T6, T7, T8 (4 tasks)
**Speedup**: 4x (if unlimited parallel capacity)

### Wave 3 Parallelization

```mermaid
graph LR
    Wave2[Wave 2 Done] --> T9[T9: Result Pattern]
    T9 --> T10[T10: Wrap Exceptions]
    T10 --> T11[T11: Update Public APIs]

    T11 -.-> Wave4[Wave 4 Start]

    style T9 fill:#ffe1e1
    style T10 fill:#ffe1e1
    style T11 fill:#ffe1e1
```

**Parallel Tasks**: None (sequential)
**Speedup**: 1x

### Wave 4 Parallelization

```mermaid
graph LR
    Wave3[Wave 3 Done] --> T12[T12: Repository]
    Wave3 --> T13[T13: Unit of Work]
    Wave3 --> T14[T14: State FSM]

    T12 --> T15[T15: Storage Refactor]
    T13 --> T15
    T14 --> T15

    T15 -.-> Wave5[Wave 5 Start]

    style T12 fill:#e1ffe1
    style T13 fill:#e1ffe1
    style T14 fill:#e1ffe1
    style T15 fill:#e1ffe1
```

**Parallel Tasks**: T12, T13, T14 (3 tasks)
**Speedup**: 3x (if unlimited parallel capacity)

### Wave 5 Parallelization

```mermaid
graph LR
    Wave4[Wave 4 Done] --> T16[T16: Provider Adapters]
    Wave4 --> T17[T17: Tool Adapters]
    Wave4 --> T18[T18: Facade]
    Wave4 --> T19[T19: Mediator]

    T16 --> T20[T20: Command Pattern]
    T17 --> T20

    T20 -.-> Wave6[Wave 6 Start]

    style T16 fill:#f5e1ff
    style T17 fill:#f5e1ff
    style T18 fill:#f5e1ff
    style T19 fill:#f5e1ff
    style T20 fill:#f5e1ff
```

**Parallel Tasks**: T16, T17, T18, T19 (4 tasks)
**Speedup**: 4x (if unlimited parallel capacity)

### Wave 6 Parallelization

```mermaid
graph LR
    Wave5[Wave 5 Done] --> T21[T21: Logging Decorator]
    Wave5 --> T22[T22: Metrics Decorator]
    Wave5 --> T23[T23: Caching Decorator]
    Wave5 --> T24[T24: Null Object]
    Wave5 --> T25[T25: Strategy Pattern]

    T21 -.-> Wave7[Wave 7 Start]
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

**Parallel Tasks**: T21, T22, T23, T24, T25 (5 tasks)
**Speedup**: 5x (if unlimited parallel capacity)

### Wave 7 Parallelization

```mermaid
graph LR
    Wave6[Wave 6 Done] --> T26[T26: Circuit Breaker]
    Wave6 --> T27[T27: Bulkhead]
    Wave6 --> T28[T28: Retry + Backoff]
    Wave6 --> T29[T29: Rate Limiter]

    T26 --> T30[T30: Apply Reliability]
    T27 --> T30
    T28 --> T30
    T29 --> T30

    T30 -.-> Wave8[Wave 8 Start]

    style T26 fill:#ffe1e1
    style T27 fill:#ffe1e1
    style T28 fill:#ffe1e1
    style T29 fill:#ffe1e1
    style T30 fill:#ffe1e1
```

**Parallel Tasks**: T26, T27, T28, T29 (4 tasks)
**Speedup**: 4x (if unlimited parallel capacity)

### Wave 8 Parallelization

```mermaid
graph LR
    Wave7[Wave 7 Done] --> T31[T31: Composition Root]
    T31 --> T32[T32: CLI Updates]
    T31 --> T33[T33: TUI Updates]

    T32 --> T34[T34: Integration Tests]
    T33 --> T34

    T34 --> T35[T35: Documentation]
    T35 --> T36[T36: Final Verification]

    style T31 fill:#e1f5ff
    style T32 fill:#e1f5ff
    style T33 fill:#e1f5ff
    style T34 fill:#e1ffe1
    style T35 fill:#fff4e1
    style T36 fill:#e1ffe1
```

**Parallel Tasks**: T32, T33 (2 tasks)
**Speedup**: 2x (if unlimited parallel capacity)

## Task Complexity vs. Dependencies

```mermaid
graph LR
    X[Low Complexity<br/>High Dependencies]
    Y[High Complexity<br/>High Dependencies]
    Z[Low Complexity<br/>Low Dependencies]
    W[High Complexity<br/>Low Dependencies]

    T1[T1: Baseline] --> Z
    T5[T5: Tool Plugins] --> X
    T6[T6: Provider Plugins] --> X
    T7[T7: Agent Plugins] --> X
    T8[T8: Register Built-ins] --> W
    T9[T9: Result Pattern] --> X
    T10[T10: Wrap Exceptions] --> Y
    T11[T11: Update Public APIs] --> Y
    T15[T15: Storage Refactor] --> Y
    T20[T20: Command Pattern] --> W
    T25[T25: Strategy Pattern] --> W
    T30[T30: Apply Reliability] --> W
    T31[T31: Composition Root] --> Y
    T34[T34: Integration Tests] --> Y
    T35[T35: Documentation] --> W
    T36[T36: Final Verification] --> X

    style X fill:#ffe1e1
    style Y fill:#ffcccc
    style Z fill:#ccffcc
    style W fill:#ffffcc
```

## Resource Allocation Strategy

### Recommended Agent Allocation

| Wave | Tasks | Parallel Capacity | Recommended Agents |
|------|-------|------------------|-------------------|
| Wave 1 | 1-4 | 3 parallel | 2 agents (1 main + 1 helper) |
| Wave 2 | 5-8 | 4 parallel | 3 agents (1 main + 2 helpers) |
| Wave 3 | 9-11 | Sequential | 1 agent (main) |
| Wave 4 | 12-15 | 3 parallel | 2 agents (1 main + 1 helper) |
| Wave 5 | 16-20 | 4 parallel | 3 agents (1 main + 2 helpers) |
| Wave 6 | 21-25 | 5 parallel | 4 agents (1 main + 3 helpers) |
| Wave 7 | 26-30 | 4 parallel | 3 agents (1 main + 2 helpers) |
| Wave 8 | 31-36 | 2 parallel | 2 agents (1 main + 1 helper) |

**Peak Parallel Capacity**: 4-5 agents (Wave 6)
**Average Parallel Capacity**: 2-3 agents

### Task Prioritization

**High Priority** (on critical path):
- T1: Baseline (blocks all)
- T2: DI Container (blocks all DI-managed code)
- T4: Plugin Discovery (blocks all plugin loading)
- T9: Result Pattern (blocks error handling)
- T11: Update Public APIs (blocks user-facing changes)
- T15: Storage Refactor (blocks Repository pattern)
- T20: Command Pattern (blocks orchestration)
- T25: Strategy Pattern (blocks reliability)
- T31: Composition Root (blocks final integration)
- T34: Integration Tests (blocks completion)
- T35: Documentation (required deliverable)

**Medium Priority** (significant parallelization benefit):
- T5, T6, T7, T8: Plugin system (4x parallelization)
- T12, T13, T14: Storage patterns (3x parallelization)
- T16, T17, T18, T19: Coordination patterns (4x parallelization)
- T21, T22, T23, T24, T25: Cross-cutting patterns (5x parallelization)
- T26, T27, T28, T29: Reliability patterns (4x parallelization)

**Low Priority** (sequential or limited parallelization):
- T3: Config Object (1x speedup)
- T10: Wrap Exceptions (sequential)
- T32, T33: CLI/TUI updates (2x speedup)
- T36: Final verification (sequential)

## Risk Assessment

### High-Risk Tasks (high complexity, many dependencies)

| Task | Risk | Mitigation |
|------|------|------------|
| T10: Wrap Exceptions | May break existing functionality | Comprehensive test suite, incremental wrapping |
| T11: Update Public APIs | Breaking change for users | Clear migration guide, feature flags |
| T15: Storage Refactor | Data loss risk | Comprehensive testing, backup strategy |
| T31: Composition Root | System may not initialize | Incremental DI integration, fallback to old wiring |

### Medium-Risk Tasks (moderate complexity, some dependencies)

| Task | Risk | Mitigation |
|------|------|------------|
| T20: Command Pattern | May affect agent workflows | Extensive agent testing |
| T25: Strategy Pattern | May affect storage reliability | Multiple backend testing |
| T34: Integration Tests | May reveal hidden bugs | Parallel execution, detailed reporting |

### Low-Risk Tasks (low complexity, few dependencies)

| Task | Risk | Mitigation |
|------|------|------------|
| T1: Baseline | None (read-only) | None needed |
| T9: Result Pattern | Limited usage initially | Comprehensive unit tests |
| T21-24: Decorator Patterns | Can be disabled | Feature flags |

## Task Status Tracking

```mermaid
pie title Task Status by Wave
    "Wave 1 (Complete)" : 4
    "Wave 2 (Complete)" : 4
    "Wave 3 (In Progress)" : 1
    "Wave 3 (Pending)" : 2
    "Wave 4 (Pending)" : 4
    "Wave 5 (Pending)" : 5
    "Wave 6 (Pending)" : 5
    "Wave 7 (Pending)" : 5
    "Wave 8 (Pending)" : 6
```

## Completion Metrics

| Metric | Target | Current | Percentage |
|--------|--------|---------|------------|
| Total Tasks | 36 | 9 | 25% |
| Critical Path Tasks | 15 | 5 | 33% |
| Non-Critical Tasks | 21 | 4 | 19% |
| Waves Completed | 8 | 2 | 25% |
| Design Patterns Implemented | 21 | 6 | 29% |

See [execution-waves.md](execution-waves.md) for detailed wave execution plans.
