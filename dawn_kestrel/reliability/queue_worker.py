"""Queue and worker implementations for async task processing.

This module provides:
- Task/TaskStatus: Task model and status enum
- TaskQueue/Worker protocols: Interfaces for queue and worker
- InMemoryTaskQueue: asyncio.Queue-based task queue with status tracking
- AsyncWorker: Worker that processes tasks from queue
- WorkerPool: Pool of concurrent workers
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from dawn_kestrel.core.result import Err, Ok, Result

logger = logging.getLogger(__name__)


# =============================================================================
# Task Model and Status
# =============================================================================


class TaskStatus(str, Enum):
    """Status of a task in the processing pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """Task model representing a unit of work.

    Attributes:
        id: Unique identifier for the task.
        type: Type/category of the task (e.g., "email", "export").
        payload: Task-specific data as a dictionary.
        status: Current status of the task.
        priority: Task priority (higher = more important).
        created_at: Timestamp when task was created.
    """

    id: str
    type: str
    payload: dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    priority: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Protocols
# =============================================================================


@runtime_checkable
class TaskQueue(Protocol):
    """Protocol for task queue implementations.

    A task queue stores and manages tasks awaiting processing.
    Implementations should support FIFO ordering and status tracking.
    """

    async def enqueue(self, task: Task) -> Result[Task]:
        """Add a task to the queue.

        Args:
            task: Task to add to the queue.

        Returns:
            Result[Task]: Ok with the task, or Err on failure.
        """
        ...

    async def dequeue(self) -> Result[Task | None]:
        """Remove and return the next task from the queue.

        Returns:
            Result[Task | None]: Ok with task or None if empty, Err on failure.
        """
        ...

    async def peek(self) -> Result[Task | None]:
        """Return the next task without removing it.

        Returns:
            Result[Task | None]: Ok with task or None if empty, Err on failure.
        """
        ...

    async def size(self) -> Result[int]:
        """Return the number of tasks in the queue.

        Returns:
            Result[int]: Ok with count, Err on failure.
        """
        ...


@runtime_checkable
class Worker(Protocol):
    """Protocol for worker implementations.

    A worker processes tasks from a queue.
    """

    async def process(self, task: Task) -> Result[Any]:
        """Process a single task.

        Args:
            task: Task to process.

        Returns:
            Result[Any]: Ok with result, Err on failure.
        """
        ...

    async def start(self) -> Result[None]:
        """Start the worker.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        ...

    async def stop(self) -> Result[None]:
        """Stop the worker.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        ...


# =============================================================================
# InMemoryTaskQueue Implementation
# =============================================================================


class InMemoryTaskQueue:
    """In-memory task queue using asyncio.Queue.

    Provides FIFO ordering with task status tracking.
    All tasks are stored in memory with their status.

    Thread safety:
        NOT thread-safe (documented limitation).
        Suitable for single-process async use.

    Example:
        queue = InMemoryTaskQueue()

        # Enqueue task
        task = Task(id="t1", type="email", payload={"to": "user@example.com"})
        result = await queue.enqueue(task)

        # Dequeue task
        result = await queue.dequeue()
        if result.is_ok() and result.unwrap():
            task = result.unwrap()
            # Process task...
    """

    def __init__(self, maxsize: int = 0):
        """Initialize the queue.

        Args:
            maxsize: Maximum queue size (0 = unlimited).
        """
        self._queue: asyncio.Queue[Task] = asyncio.Queue(maxsize=maxsize)
        self._tasks: dict[str, Task] = {}  # Task ID -> Task mapping
        self._lock = asyncio.Lock()

    async def enqueue(self, task: Task) -> Result[Task]:
        """Add a task to the queue.

        Args:
            task: Task to add.

        Returns:
            Result[Task]: Ok with task, Err if queue is full.
        """
        try:
            async with self._lock:
                # Ensure task status is PENDING
                task.status = TaskStatus.PENDING
                self._tasks[task.id] = task

            await self._queue.put(task)
            logger.debug(f"Enqueued task {task.id}")
            return Ok(task)
        except asyncio.QueueFull:
            return Err("Queue is full", code="QUEUE_FULL")
        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}")
            return Err(f"Failed to enqueue task: {e}", code="ENQUEUE_ERROR")

    async def dequeue(self, timeout: float | None = None) -> Result[Task | None]:
        """Remove and return the next task.

        Args:
            timeout: Maximum time to wait for a task (None = no wait).

        Returns:
            Result[Task | None]: Ok with task, None if empty, Err on failure.
        """
        try:
            if timeout is not None and timeout > 0:
                task = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                # Non-blocking get
                try:
                    task = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    return Ok(None)
            logger.debug(f"Dequeued task {task.id}")
            return Ok(task)
        except asyncio.TimeoutError:
            return Ok(None)
        except Exception as e:
            logger.error(f"Failed to dequeue task: {e}")
            return Err(f"Failed to dequeue task: {e}", code="DEQUEUE_ERROR")

    async def peek(self) -> Result[Task | None]:
        """Return the next task without removing it.

        Returns:
            Result[Task | None]: Ok with task, None if empty, Err on failure.
        """
        try:
            # asyncio.Queue doesn't have peek, so we get and put back
            try:
                task = self._queue.get_nowait()
                # Put it back at the front
                temp_queue: asyncio.Queue[Task] = asyncio.Queue()
                await temp_queue.put(task)
                # Drain remaining to temp
                while not self._queue.empty():
                    await temp_queue.put(self._queue.get_nowait())
                # Move all back to main queue
                while not temp_queue.empty():
                    await self._queue.put(temp_queue.get_nowait())
                return Ok(task)
            except asyncio.QueueEmpty:
                return Ok(None)
        except Exception as e:
            logger.error(f"Failed to peek task: {e}")
            return Err(f"Failed to peek task: {e}", code="PEEK_ERROR")

    async def size(self) -> Result[int]:
        """Return the number of tasks in the queue.

        Returns:
            Result[int]: Ok with count.
        """
        return Ok(self._queue.qsize())

    async def get_task(self, task_id: str) -> Result[Task | None]:
        """Get a task by ID.

        Args:
            task_id: ID of the task to retrieve.

        Returns:
            Result[Task | None]: Ok with task, None if not found.
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            return Ok(task)

    async def update_status(self, task_id: str, status: TaskStatus) -> Result[Task]:
        """Update the status of a task.

        Args:
            task_id: ID of the task to update.
            status: New status.

        Returns:
            Result[Task]: Ok with updated task, Err if not found.
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return Err(f"Task not found: {task_id}", code="TASK_NOT_FOUND")
            task.status = status
            return Ok(task)


# =============================================================================
# AsyncWorker Implementation
# =============================================================================


class AsyncWorker:
    """Async worker that processes tasks from a queue.

    Continuously polls the queue for tasks and processes them
    using the provided processor function.

    Example:
        async def my_processor(task: Task) -> Result[dict]:
            # Process task
            return Ok({"result": "success"})

        worker = AsyncWorker(queue=queue, processor=my_processor)
        await worker.start()

        # Worker processes tasks...

        await worker.stop()
    """

    def __init__(
        self,
        queue: InMemoryTaskQueue,
        processor: Callable[[Task], Awaitable[Result[Any]]],
        worker_id: str | None = None,
        poll_interval: float = 0.1,
    ):
        """Initialize the worker.

        Args:
            queue: Task queue to consume from.
            processor: Async function to process each task.
            worker_id: Optional worker identifier (auto-generated if None).
            poll_interval: Time to wait between polling for tasks.
        """
        self._queue = queue
        self._processor = processor
        self._worker_id = worker_id or str(uuid.uuid4())[:8]
        self._poll_interval = poll_interval
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._stats: dict[str, Any] = {
            "processed_count": 0,
            "error_count": 0,
        }

    @property
    def worker_id(self) -> str:
        """Get the worker ID."""
        return self._worker_id

    @property
    def is_running(self) -> bool:
        """Check if the worker is running."""
        return self._running

    async def start(self) -> Result[None]:
        """Start the worker.

        Returns:
            Result[None]: Ok on success, Err if already running.
        """
        if self._running:
            return Err("Worker already running", code="ALREADY_RUNNING")

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Worker {self._worker_id} started")
        return Ok(None)

    async def stop(self) -> Result[None]:
        """Stop the worker.

        Returns:
            Result[None]: Ok on success.
        """
        if not self._running:
            return Ok(None)

        self._running = False

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info(f"Worker {self._worker_id} stopped")
        return Ok(None)

    async def _run_loop(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                result = await self._queue.dequeue(timeout=self._poll_interval)

                if result.is_err():
                    logger.error(f"Worker {self._worker_id} dequeue error: {result.error}")
                    continue

                task = result.unwrap()
                if task is None:
                    # No task available, continue polling
                    continue

                # Update task status to RUNNING
                await self._queue.update_status(task.id, TaskStatus.RUNNING)

                # Process the task
                try:
                    process_result = await self._processor(task)

                    if process_result.is_ok():
                        await self._queue.update_status(task.id, TaskStatus.COMPLETED)
                        self._stats["processed_count"] += 1
                        logger.debug(f"Worker {self._worker_id} completed task {task.id}")
                    else:
                        await self._queue.update_status(task.id, TaskStatus.FAILED)
                        self._stats["error_count"] += 1
                        logger.warning(
                            f"Worker {self._worker_id} task {task.id} failed: "
                            f"{process_result.error if hasattr(process_result, 'error') else 'unknown'}"
                        )
                except Exception as e:
                    await self._queue.update_status(task.id, TaskStatus.FAILED)
                    self._stats["error_count"] += 1
                    logger.error(f"Worker {self._worker_id} task {task.id} error: {e}")

            except asyncio.CancelledError:
                logger.debug(f"Worker {self._worker_id} cancelled")
                raise
            except Exception as e:
                logger.error(f"Worker {self._worker_id} error: {e}")

    async def get_stats(self) -> dict[str, Any]:
        """Get worker statistics.

        Returns:
            Dictionary with processed_count and error_count.
        """
        return self._stats.copy()


# =============================================================================
# WorkerPool Implementation
# =============================================================================


class WorkerPool:
    """Pool of concurrent workers.

    Manages multiple AsyncWorker instances for parallel task processing.

    Example:
        async def my_processor(task: Task) -> Result[dict]:
            return Ok({"processed": True})

        pool = WorkerPool(queue=queue, processor=my_processor, num_workers=4)

        async with pool:
            # Workers are running and processing tasks
            await pool.wait_for_completion()
    """

    def __init__(
        self,
        queue: InMemoryTaskQueue,
        processor: Callable[[Task], Awaitable[Result[Any]]],
        num_workers: int = 1,
        poll_interval: float = 0.1,
    ):
        """Initialize the worker pool.

        Args:
            queue: Task queue to consume from.
            processor: Async function to process each task.
            num_workers: Number of workers to create.
            poll_interval: Time to wait between polling for tasks.
        """
        self._queue = queue
        self._processor = processor
        self._num_workers = num_workers
        self._poll_interval = poll_interval
        self._workers: list[AsyncWorker] = []
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if the pool is running."""
        return self._running

    @property
    def running_count(self) -> int:
        """Get the number of running workers."""
        return sum(1 for w in self._workers if w.is_running)

    async def start(self) -> Result[None]:
        """Start all workers in the pool.

        Returns:
            Result[None]: Ok on success.
        """
        if self._running:
            return Ok(None)

        self._workers = []
        for i in range(self._num_workers):
            worker = AsyncWorker(
                queue=self._queue,
                processor=self._processor,
                worker_id=f"pool-worker-{i}",
                poll_interval=self._poll_interval,
            )
            await worker.start()
            self._workers.append(worker)

        self._running = True
        logger.info(f"Worker pool started with {self._num_workers} workers")
        return Ok(None)

    async def stop(self) -> Result[None]:
        """Stop all workers in the pool.

        Returns:
            Result[None]: Ok on success.
        """
        if not self._running:
            return Ok(None)

        # Stop all workers concurrently
        await asyncio.gather(*[w.stop() for w in self._workers], return_exceptions=True)

        self._workers = []
        self._running = False
        logger.info("Worker pool stopped")
        return Ok(None)

    async def resize(self, num_workers: int) -> Result[None]:
        """Resize the worker pool.

        Args:
            num_workers: New number of workers.

        Returns:
            Result[None]: Ok on success.
        """
        if num_workers < 1:
            return Err("num_workers must be at least 1", code="INVALID_SIZE")

        current_count = len(self._workers)

        if num_workers > current_count:
            # Add workers
            for i in range(current_count, num_workers):
                worker = AsyncWorker(
                    queue=self._queue,
                    processor=self._processor,
                    worker_id=f"pool-worker-{i}",
                    poll_interval=self._poll_interval,
                )
                await worker.start()
                self._workers.append(worker)
        elif num_workers < current_count:
            # Remove workers
            workers_to_stop = self._workers[num_workers:]
            self._workers = self._workers[:num_workers]
            await asyncio.gather(*[w.stop() for w in workers_to_stop], return_exceptions=True)

        self._num_workers = num_workers
        logger.info(f"Worker pool resized to {num_workers} workers")
        return Ok(None)

    async def get_stats(self) -> dict[str, Any]:
        """Get aggregated statistics from all workers.

        Returns:
            Dictionary with total_processed, total_errors, num_workers.
        """
        total_processed = 0
        total_errors = 0

        for worker in self._workers:
            stats = await worker.get_stats()
            total_processed += stats.get("processed_count", 0)
            total_errors += stats.get("error_count", 0)

        return {
            "total_processed": total_processed,
            "total_errors": total_errors,
            "num_workers": len(self._workers),
        }

    async def wait_for_completion(self, timeout: float | None = None) -> Result[None]:
        """Wait for all tasks in queue to be processed.

        Args:
            timeout: Maximum time to wait (None = no limit).

        Returns:
            Result[None]: Ok when complete, Err on timeout.
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            size_result = await self._queue.size()
            if size_result.is_ok() and size_result.unwrap() == 0:
                return Ok(None)

            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    return Err("Timeout waiting for completion", code="TIMEOUT")

            await asyncio.sleep(0.1)

    async def __aenter__(self) -> "WorkerPool":
        """Enter async context manager."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.stop()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "AsyncWorker",
    "InMemoryTaskQueue",
    "Task",
    "TaskQueue",
    "TaskStatus",
    "Worker",
    "WorkerPool",
]
