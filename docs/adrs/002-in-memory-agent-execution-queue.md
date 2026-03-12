# ADR 002: In-Memory Async Queue For Parallel Agent Execution

- Status: Accepted
- Date: 2026-02-24

## Context

Parallel agent execution previously used `asyncio.gather()` directly in `AgentOrchestrator.run_parallel_agents()`. That approach started all tasks immediately and had no explicit in-memory queue boundary for scheduling. We need bounded asynchronous execution that can be tuned without changing call sites.

## Decision

Introduce an explicit in-memory queue execution component:

- New module: `dawn_kestrel/agents/execution_queue.py`
- New types:
  - `AgentExecutionJob`
  - `AgentExecutionBatchResult`
  - `InMemoryAgentExecutionQueue`
- Implementation uses existing reliability primitives:
  - `InMemoryTaskQueue`
  - `WorkerPool`

`AgentOrchestrator.run_parallel_agents()` now schedules jobs through `InMemoryAgentExecutionQueue` and returns completed task IDs while logging per-job failures.

## Consequences

### Positive

- Explicit queue boundary for parallel execution.
- Bounded worker concurrency (`max_parallel_workers`).
- Reuses existing queue/worker reliability components.
- Cleaner path for future features (priority, fairness, backpressure).

### Negative

- Extra scheduling layer vs direct `gather()`.
- Slight overhead for small batches.

### Follow-up

- Add queue-level metrics (`queue_depth`, `job_wait_ms`, `worker_utilization`).
- Add retry policy per queued job.
- Add optional cancellation propagation for in-flight worker tasks.
