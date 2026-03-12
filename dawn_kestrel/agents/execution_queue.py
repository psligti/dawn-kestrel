from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from dawn_kestrel.core.result import Err, Ok, Result
from dawn_kestrel.reliability.queue_worker import InMemoryTaskQueue, Task, WorkerPool


@dataclass
class AgentExecutionJob:
    index: int
    task_id: str


@dataclass
class AgentExecutionBatchResult:
    completed_task_ids: list[str]
    errors_by_index: dict[int, str]


class InMemoryAgentExecutionQueue:
    def __init__(
        self,
        max_workers: int = 4,
        poll_interval: float = 0.05,
        timeout_seconds: float = 300.0,
    ) -> None:
        self.max_workers = max(1, max_workers)
        self.poll_interval = poll_interval
        self.timeout_seconds = timeout_seconds

    async def run_jobs(
        self,
        jobs: list[AgentExecutionJob],
        execute: Callable[[AgentExecutionJob], Awaitable[str]],
    ) -> AgentExecutionBatchResult:
        queue = InMemoryTaskQueue()
        completed_by_index: list[str | None] = [None] * len(jobs)
        errors_by_index: dict[int, str] = {}
        results_lock = asyncio.Lock()

        async def process_task(task: Task) -> Result[Any]:
            index = int(task.payload["index"])
            job = jobs[index]

            try:
                result_task_id = await execute(job)
            except Exception as exc:
                async with results_lock:
                    errors_by_index[index] = str(exc)
                return Err(str(exc), code="AGENT_EXECUTION_FAILED")

            async with results_lock:
                completed_by_index[index] = result_task_id
            return Ok(result_task_id)

        for job in jobs:
            queue_task = Task(
                id=f"agent_exec_{uuid.uuid4().hex[:12]}",
                type="agent_execution",
                payload={"index": job.index},
            )
            enqueue_result = await queue.enqueue(queue_task)
            if enqueue_result.is_err():
                enqueue_err = enqueue_result
                if isinstance(enqueue_err, Err):
                    errors_by_index[job.index] = str(enqueue_err.error)
                else:
                    errors_by_index[job.index] = "failed to enqueue agent execution job"

        workers = min(self.max_workers, max(1, len(jobs)))
        pool = WorkerPool(
            queue=queue,
            processor=process_task,
            num_workers=workers,
            poll_interval=self.poll_interval,
        )

        await pool.start()
        try:
            completion = await pool.wait_for_completion(timeout=self.timeout_seconds)
            if completion.is_err():
                completion_error = (
                    str(completion.error)
                    if isinstance(completion, Err)
                    else "agent execution queue timed out"
                )
                for job in jobs:
                    if completed_by_index[job.index] is None and job.index not in errors_by_index:
                        errors_by_index[job.index] = completion_error
        finally:
            await pool.stop()

        completed_task_ids = [task_id for task_id in completed_by_index if task_id is not None]
        return AgentExecutionBatchResult(
            completed_task_ids=completed_task_ids,
            errors_by_index=errors_by_index,
        )
