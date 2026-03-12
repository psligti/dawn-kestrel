# DELEGATION ENGINE

Multi-agent task delegation with guaranteed termination via boundary enforcement and convergence detection.

## OVERVIEW

```
dawn_kestrel/delegation/
├── engine.py         # DelegationEngine: BFS/DFS/Adaptive execution
├── types.py          # TraversalMode, DelegationBudget, DelegationConfig
├── convergence.py    # ConvergenceTracker: SHA-256 novelty detection
├── tool.py           # DelegateTool: Tool wrapper for agent use
└── DESIGN.md         # Architecture documentation
```

## TRAVERSAL MODES

| Mode | Behavior | Use Case |
|------|----------|----------|
| BFS | Queue-based parallel children | Broad exploration, security scans |
| DFS | Sequential deep-dive per branch | Code tracing, dependency analysis |
| Adaptive | BFS depth 0-1, DFS depth 2+ | Hybrid research + deep-dive |

## BUDGET CONSTRAINTS

| Constraint | Default | Purpose |
|------------|---------|---------|
| max_depth | 3 | Prevent infinite recursion |
| max_breadth | 5 | Limit concurrent children per level |
| max_total_agents | 20 | Cumulative spawn cap |
| max_wall_time_seconds | 300.0 | Hard timeout |
| max_iterations | 10 | Delegation cycle limit |
| stagnation_threshold | 3 | Consecutive identical results |
| max_concurrent | 3 | Worker pool size for BFS |

## CONVERGENCE DETECTION

```python
# ConvergenceTracker uses SHA-256 hashes on evidence_keys
tracker = ConvergenceTracker(evidence_keys=["result", "findings"])
is_novel = tracker.check_novelty(results)  # Returns False if stagnant
is_converged = tracker.is_converged(threshold=3)
```

- Extracts `evidence_keys` from dict results or `AgentResult.metadata`
- Falls back to `result.response` or `str(result)`
- Stagnation = N consecutive identical signatures

## QUEUE EXECUTION (BFS)

```
InMemoryTaskQueue → WorkerPool(max_workers=max_concurrent) → process_child_task()
```

BFS uses queue/worker pattern instead of raw `asyncio.gather` to prevent provider timeouts from too many parallel requests. Tasks wait in queue until a worker slot opens.

## USAGE

```python
from dawn_kestrel.delegation import DelegationEngine, DelegationConfig, TraversalMode

config = DelegationConfig(mode=TraversalMode.BFS, budget=DelegationBudget(max_depth=2))
engine = DelegationEngine(config, runtime, registry)

result = await engine.delegate(
    agent_name="orchestrator",
    prompt="Analyze security",
    session_id=session.id,
    session_manager=session_manager,
    children=[{"agent": "explore", "prompt": "Find auth"}],
)
# result: DelegationResult(success, stop_reason, results, errors, total_agents, converged)
```

## STOP REASONS

`COMPLETED` | `CONVERGED` | `BUDGET_EXHAUSTED` | `STAGNATION` | `DEPTH_LIMIT` | `BREADTH_LIMIT` | `TIMEOUT` | `ERROR`
