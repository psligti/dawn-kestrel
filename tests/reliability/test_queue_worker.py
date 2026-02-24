"""Tests for InMemoryTaskQueue, AsyncWorker, and WorkerPool implementations.

These tests verify concrete implementations of queue/worker patterns:
- InMemoryTaskQueue: asyncio.Queue-based task queue
- AsyncWorker: processes tasks from queue
- WorkerPool: manages multiple workers
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock

import pytest

from dawn_kestrel.core.result import Err, Ok, Result
from dawn_kestrel.reliability.queue_worker import (
    AsyncWorker,
    InMemoryTaskQueue,
    Task,
    TaskStatus,
    WorkerPool,
)


class TestInMemoryTaskQueue:
    """Tests for InMemoryTaskQueue implementation."""

    @pytest.fixture
    def queue(self) -> InMemoryTaskQueue:
        """Create a fresh queue for each test."""
        return InMemoryTaskQueue()

    @pytest.mark.asyncio
    async def test_enqueue_single_task(self, queue: InMemoryTaskQueue) -> None:
        """Can enqueue a single task."""
        task = Task(id="t1", type="email", payload={"to": "user@example.com"})

        result = await queue.enqueue(task)

        assert result.is_ok()
        assert result.unwrap().id == "t1"

    @pytest.mark.asyncio
    async def test_enqueue_updates_task_status(self, queue: InMemoryTaskQueue) -> None:
        """Enqueued task has PENDING status."""
        task = Task(id="t1", type="email", payload={})

        result = await queue.enqueue(task)

        assert result.is_ok()
        assert result.unwrap().status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_dequeue_returns_enqueued_task(self, queue: InMemoryTaskQueue) -> None:
        """Dequeue returns the first enqueued task."""
        task = Task(id="t1", type="email", payload={"data": "test"})
        await queue.enqueue(task)

        result = await queue.dequeue()

        assert result.is_ok()
        dequeued = result.unwrap()
        assert dequeued is not None
        assert dequeued.id == "t1"
        assert dequeued.payload["data"] == "test"

    @pytest.mark.asyncio
    async def test_dequeue_returns_none_when_empty(self, queue: InMemoryTaskQueue) -> None:
        """Dequeue returns Ok(None) when queue is empty."""
        result = await queue.dequeue()

        assert result.is_ok()
        assert result.unwrap() is None

    @pytest.mark.asyncio
    async def test_dequeue_removes_task_from_queue(self, queue: InMemoryTaskQueue) -> None:
        """Dequeue removes task from queue (FIFO)."""
        task1 = Task(id="t1", type="email", payload={})
        task2 = Task(id="t2", type="email", payload={})
        await queue.enqueue(task1)
        await queue.enqueue(task2)

        result1 = await queue.dequeue()
        result2 = await queue.dequeue()

        assert result1.unwrap().id == "t1"
        assert result2.unwrap().id == "t2"

    @pytest.mark.asyncio
    async def test_peek_returns_task_without_removing(self, queue: InMemoryTaskQueue) -> None:
        """Peek returns next task without removing it."""
        task = Task(id="t1", type="email", payload={})
        await queue.enqueue(task)

        result = await queue.peek()

        assert result.is_ok()
        assert result.unwrap().id == "t1"

        # Task should still be in queue
        result2 = await queue.peek()
        assert result2.unwrap().id == "t1"

    @pytest.mark.asyncio
    async def test_peek_returns_none_when_empty(self, queue: InMemoryTaskQueue) -> None:
        """Peek returns Ok(None) when queue is empty."""
        result = await queue.peek()

        assert result.is_ok()
        assert result.unwrap() is None

    @pytest.mark.asyncio
    async def test_size_returns_correct_count(self, queue: InMemoryTaskQueue) -> None:
        """Size returns number of tasks in queue."""
        assert (await queue.size()).unwrap() == 0

        await queue.enqueue(Task(id="t1", type="email", payload={}))
        assert (await queue.size()).unwrap() == 1

        await queue.enqueue(Task(id="t2", type="email", payload={}))
        assert (await queue.size()).unwrap() == 2

        await queue.dequeue()
        assert (await queue.size()).unwrap() == 1

    @pytest.mark.asyncio
    async def test_get_task_returns_task_by_id(self, queue: InMemoryTaskQueue) -> None:
        """Can retrieve a task by ID."""
        task = Task(id="t1", type="email", payload={"key": "value"})
        await queue.enqueue(task)

        result = await queue.get_task("t1")

        assert result.is_ok()
        assert result.unwrap().id == "t1"
        assert result.unwrap().payload["key"] == "value"

    @pytest.mark.asyncio
    async def test_get_task_returns_none_if_not_found(self, queue: InMemoryTaskQueue) -> None:
        """get_task returns None for unknown task ID."""
        result = await queue.get_task("nonexistent")

        assert result.is_ok()
        assert result.unwrap() is None

    @pytest.mark.asyncio
    async def test_update_task_status(self, queue: InMemoryTaskQueue) -> None:
        """Can update task status."""
        task = Task(id="t1", type="email", payload={})
        await queue.enqueue(task)

        result = await queue.update_status("t1", TaskStatus.RUNNING)

        assert result.is_ok()
        assert (await queue.get_task("t1")).unwrap().status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_update_status_returns_error_if_not_found(self, queue: InMemoryTaskQueue) -> None:
        """update_status returns Err for unknown task ID."""
        result = await queue.update_status("nonexistent", TaskStatus.RUNNING)

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_fifo_order(self, queue: InMemoryTaskQueue) -> None:
        """Tasks are processed in FIFO order."""
        for i in range(5):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        for i in range(5):
            result = await queue.dequeue()
            assert result.unwrap().id == f"t{i}"

    @pytest.mark.asyncio
    async def test_dequeue_with_timeout(self, queue: InMemoryTaskQueue) -> None:
        """Dequeue can wait for task with timeout."""
        # Empty queue should return None with small timeout
        result = await queue.dequeue(timeout=0.01)
        assert result.is_ok()
        assert result.unwrap() is None

        # Enqueue after short delay
        async def delayed_enqueue() -> None:
            await asyncio.sleep(0.05)
            await queue.enqueue(Task(id="t1", type="test", payload={}))

        asyncio.create_task(delayed_enqueue())

        # Should get the task
        result = await queue.dequeue(timeout=0.2)
        assert result.is_ok()
        assert result.unwrap() is not None
        assert result.unwrap().id == "t1"


class TestAsyncWorker:
    """Tests for AsyncWorker implementation."""

    @pytest.fixture
    def queue(self) -> InMemoryTaskQueue:
        """Create a fresh queue."""
        return InMemoryTaskQueue()

    @pytest.fixture
    def processor(self) -> AsyncMock:
        """Create a mock processor function."""
        return AsyncMock(return_value=Ok({"processed": True}))

    @pytest.mark.asyncio
    async def test_worker_processes_task(
        self, queue: InMemoryTaskQueue, processor: AsyncMock
    ) -> None:
        """Worker processes enqueued task."""
        worker = AsyncWorker(queue=queue, processor=processor)

        task = Task(id="t1", type="email", payload={"to": "user@example.com"})
        await queue.enqueue(task)

        # Start worker and let it process one task
        await worker.start()
        await asyncio.sleep(0.1)  # Allow task processing
        await worker.stop()

        processor.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_updates_task_status_on_success(
        self, queue: InMemoryTaskQueue, processor: AsyncMock
    ) -> None:
        """Worker updates task status to COMPLETED on success."""
        worker = AsyncWorker(queue=queue, processor=processor)

        task = Task(id="t1", type="email", payload={})
        await queue.enqueue(task)

        await worker.start()
        await asyncio.sleep(0.1)
        await worker.stop()

        result = await queue.get_task("t1")
        assert result.unwrap().status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_worker_updates_task_status_on_failure(self, queue: InMemoryTaskQueue) -> None:
        """Worker updates task status to FAILED when processor fails."""
        failing_processor = AsyncMock(return_value=Err("Processing failed"))
        worker = AsyncWorker(queue=queue, processor=failing_processor)

        task = Task(id="t1", type="email", payload={})
        await queue.enqueue(task)

        await worker.start()
        await asyncio.sleep(0.1)
        await worker.stop()

        result = await queue.get_task("t1")
        assert result.unwrap().status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_worker_can_start_and_stop(
        self, queue: InMemoryTaskQueue, processor: AsyncMock
    ) -> None:
        """Worker can be started and stopped."""
        worker = AsyncWorker(queue=queue, processor=processor)

        start_result = await worker.start()
        assert start_result.is_ok()
        assert worker.is_running

        stop_result = await worker.stop()
        assert stop_result.is_ok()
        assert not worker.is_running

    @pytest.mark.asyncio
    async def test_worker_stops_gracefully(
        self, queue: InMemoryTaskQueue, processor: AsyncMock
    ) -> None:
        """Worker stops processing after stop() is called."""
        worker = AsyncWorker(queue=queue, processor=processor)

        await worker.start()
        await worker.stop()

        # Enqueue tasks after stop
        for i in range(3):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        await asyncio.sleep(0.1)

        # Processor should not have been called
        processor.assert_not_called()

    @pytest.mark.asyncio
    async def test_worker_handles_empty_queue(
        self, queue: InMemoryTaskQueue, processor: AsyncMock
    ) -> None:
        """Worker handles empty queue gracefully."""
        worker = AsyncWorker(queue=queue, processor=processor, poll_interval=0.01)

        await worker.start()
        await asyncio.sleep(0.05)  # Let it poll a few times
        await worker.stop()

        # Should not crash, processor never called
        processor.assert_not_called()

    @pytest.mark.asyncio
    async def test_worker_processes_multiple_tasks(
        self, queue: InMemoryTaskQueue, processor: AsyncMock
    ) -> None:
        """Worker processes multiple tasks in sequence."""
        worker = AsyncWorker(queue=queue, processor=processor, poll_interval=0.01)

        for i in range(5):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        await worker.start()
        await asyncio.sleep(0.2)  # Allow processing
        await worker.stop()

        assert processor.call_count == 5

    @pytest.mark.asyncio
    async def test_worker_id(self, queue: InMemoryTaskQueue, processor: AsyncMock) -> None:
        """Worker has an ID."""
        worker = AsyncWorker(queue=queue, processor=processor, worker_id="worker-1")

        assert worker.worker_id == "worker-1"

    @pytest.mark.asyncio
    async def test_worker_auto_generates_id(
        self, queue: InMemoryTaskQueue, processor: AsyncMock
    ) -> None:
        """Worker auto-generates ID if not provided."""
        worker = AsyncWorker(queue=queue, processor=processor)

        assert worker.worker_id is not None
        assert len(worker.worker_id) > 0

    @pytest.mark.asyncio
    async def test_worker_records_processed_count(
        self, queue: InMemoryTaskQueue, processor: AsyncMock
    ) -> None:
        """Worker tracks number of tasks processed."""
        worker = AsyncWorker(queue=queue, processor=processor, poll_interval=0.01)

        for i in range(3):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        await worker.start()
        await asyncio.sleep(0.15)
        await worker.stop()

        stats = await worker.get_stats()
        assert stats["processed_count"] == 3

    @pytest.mark.asyncio
    async def test_worker_records_error_count(self, queue: InMemoryTaskQueue) -> None:
        """Worker tracks number of failed tasks."""
        failing_processor = AsyncMock(return_value=Err("Failed"))
        worker = AsyncWorker(queue=queue, processor=failing_processor, poll_interval=0.01)

        for i in range(2):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        await worker.start()
        await asyncio.sleep(0.15)
        await worker.stop()

        stats = await worker.get_stats()
        assert stats["error_count"] == 2


class TestWorkerPool:
    """Tests for WorkerPool implementation."""

    @pytest.fixture
    def queue(self) -> InMemoryTaskQueue:
        """Create a fresh queue."""
        return InMemoryTaskQueue()

    @pytest.fixture
    def processor(self) -> Callable[[Task], Awaitable[Result[Any]]]:
        """Create a processor function that returns Ok results."""

        async def simple_processor(task: Task) -> Ok:
            return Ok({"task_id": task.id})

        return simple_processor

    @pytest.mark.asyncio
    async def test_pool_starts_workers(
        self, queue: InMemoryTaskQueue, processor: Callable[[Task], Awaitable[Result[Any]]]
    ) -> None:
        """Pool starts specified number of workers."""
        pool = WorkerPool(queue=queue, processor=processor, num_workers=3)

        await pool.start()

        assert pool.running_count == 3

        await pool.stop()

    @pytest.mark.asyncio
    async def test_pool_stops_all_workers(
        self, queue: InMemoryTaskQueue, processor: Callable[[Task], Awaitable[Result[Any]]]
    ) -> None:
        """Pool stops all workers on stop()."""
        pool = WorkerPool(queue=queue, processor=processor, num_workers=3)

        await pool.start()
        await pool.stop()

        assert pool.running_count == 0

    @pytest.mark.asyncio
    async def test_pool_processes_tasks_concurrently(self, queue: InMemoryTaskQueue) -> None:
        """Pool processes tasks with multiple workers concurrently."""
        processing_times: list[float] = []
        start_time = asyncio.get_event_loop().time()

        async def tracking_processor(task: Task) -> Ok:
            processing_times.append(asyncio.get_event_loop().time() - start_time)
            await asyncio.sleep(0.1)  # Simulate work
            return Ok({"task_id": task.id})

        pool = WorkerPool(queue=queue, processor=tracking_processor, num_workers=3)

        # Enqueue 3 tasks
        for i in range(3):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        await pool.start()
        await asyncio.sleep(0.3)  # Allow concurrent processing
        await pool.stop()

        # All 3 should have started processing roughly simultaneously
        assert len(processing_times) == 3
        # They should all start within a short window (concurrent)
        time_spread = max(processing_times) - min(processing_times)
        assert time_spread < 0.15  # All started within 150ms

    @pytest.mark.asyncio
    async def test_pool_default_num_workers(
        self, queue: InMemoryTaskQueue, processor: Callable[[Task], Awaitable[Result[Any]]]
    ) -> None:
        """Pool defaults to 1 worker if num_workers not specified."""
        pool = WorkerPool(queue=queue, processor=processor)

        await pool.start()
        assert pool.running_count == 1
        await pool.stop()

    @pytest.mark.asyncio
    async def test_pool_get_stats(
        self, queue: InMemoryTaskQueue, processor: Callable[[Task], Awaitable[Result[Any]]]
    ) -> None:
        """Pool aggregates stats from all workers."""
        pool = WorkerPool(queue=queue, processor=processor, num_workers=2, poll_interval=0.01)

        for i in range(4):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        await pool.start()
        # Wait for all tasks to be processed
        await pool.wait_for_completion(timeout=5.0)

        # Get stats BEFORE stopping (stop clears workers)
        stats = await pool.get_stats()
        await pool.stop()

        assert stats["total_processed"] == 4
        assert stats["num_workers"] == 2

    @pytest.mark.asyncio
    async def test_pool_handles_worker_failure_gracefully(self, queue: InMemoryTaskQueue) -> None:
        """Pool continues operating if a worker encounters an error."""
        call_count = 0

        async def failing_processor(task: Task) -> Ok:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Worker error")
            return Ok({"task_id": task.id})

        pool = WorkerPool(
            queue=queue, processor=failing_processor, num_workers=2, poll_interval=0.01
        )

        for i in range(3):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        await pool.start()
        # Wait for tasks to be processed
        await pool.wait_for_completion(timeout=5.0)

        # Get stats BEFORE stopping (stop clears workers)
        stats = await pool.get_stats()
        await pool.stop()

        # Should have processed all tasks despite one failure
        assert stats["total_processed"] >= 2  # At least 2 of 3 processed

    @pytest.mark.asyncio
    async def test_pool_is_running(
        self, queue: InMemoryTaskQueue, processor: Callable[[Task], Awaitable[Result[Any]]]
    ) -> None:
        """Pool reports running state correctly."""
        pool = WorkerPool(queue=queue, processor=processor, num_workers=2)

        assert not pool.is_running

        await pool.start()
        assert pool.is_running

        await pool.stop()
        assert not pool.is_running

    @pytest.mark.asyncio
    async def test_pool_resize_workers(
        self, queue: InMemoryTaskQueue, processor: Callable[[Task], Awaitable[Result[Any]]]
    ) -> None:
        """Pool can resize worker count while running."""
        pool = WorkerPool(queue=queue, processor=processor, num_workers=2)

        await pool.start()
        assert pool.running_count == 2

        await pool.resize(4)
        assert pool.running_count == 4

        await pool.resize(1)
        assert pool.running_count == 1

        await pool.stop()

    @pytest.mark.asyncio
    async def test_pool_wait_for_completion(
        self, queue: InMemoryTaskQueue, processor: Callable[[Task], Awaitable[Result[Any]]]
    ) -> None:
        """Pool can wait for all tasks to complete."""
        pool = WorkerPool(queue=queue, processor=processor, num_workers=2)

        for i in range(5):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        await pool.start()
        await pool.wait_for_completion(timeout=2.0)
        await pool.stop()

        # All tasks should be processed
        size = await queue.size()
        assert size.unwrap() == 0

    @pytest.mark.asyncio
    async def test_pool_context_manager(
        self, queue: InMemoryTaskQueue, processor: Callable[[Task], Awaitable[Result[Any]]]
    ) -> None:
        """Pool works as async context manager."""
        async with WorkerPool(queue=queue, processor=processor, num_workers=2) as pool:
            assert pool.is_running
            for i in range(3):
                await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))
            await asyncio.sleep(0.2)

        # Pool should be stopped after context exit
        assert not pool.is_running


class TestTaskStatusTransitions:
    """Tests for task status transitions through the pipeline."""

    @pytest.fixture
    def queue(self) -> InMemoryTaskQueue:
        """Create a fresh queue."""
        return InMemoryTaskQueue()

    @pytest.mark.asyncio
    async def test_task_status_pending_to_running(self, queue: InMemoryTaskQueue) -> None:
        """Task transitions from PENDING to RUNNING when dequeued."""
        processor = AsyncMock(return_value=Ok({"done": True}))
        worker = AsyncWorker(queue=queue, processor=processor, poll_interval=0.01)

        task = Task(id="t1", type="test", payload={})
        await queue.enqueue(task)

        # Status should be PENDING
        result = await queue.get_task("t1")
        assert result.unwrap().status == TaskStatus.PENDING

        await worker.start()
        await asyncio.sleep(0.05)
        await worker.stop()

        # After processing, should be COMPLETED
        result = await queue.get_task("t1")
        assert result.unwrap().status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_task_status_to_failed_on_error(self, queue: InMemoryTaskQueue) -> None:
        """Task transitions to FAILED when processor returns error."""
        failing_processor = AsyncMock(return_value=Err("Processing error"))
        worker = AsyncWorker(queue=queue, processor=failing_processor, poll_interval=0.01)

        task = Task(id="t1", type="test", payload={})
        await queue.enqueue(task)

        await worker.start()
        await asyncio.sleep(0.05)
        await worker.stop()

        result = await queue.get_task("t1")
        assert result.unwrap().status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_multiple_tasks_mixed_statuses(self, queue: InMemoryTaskQueue) -> None:
        """Multiple tasks can have different statuses."""
        call_count = 0

        async def mixed_processor(task: Task) -> Ok:
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                return Err("Even task fails")
            return Ok({"done": True})

        worker = AsyncWorker(queue=queue, processor=mixed_processor, poll_interval=0.01)

        for i in range(4):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        await worker.start()
        await asyncio.sleep(0.2)
        await worker.stop()

        # Check statuses: t0 (COMPLETED), t1 (FAILED), t2 (COMPLETED), t3 (FAILED)
        for i in range(4):
            result = await queue.get_task(f"t{i}")
            task = result.unwrap()
            if i % 2 == 0:
                assert task.status == TaskStatus.COMPLETED, f"Task {i} should be completed"
            else:
                assert task.status == TaskStatus.FAILED, f"Task {i} should be failed"


class TestCancellationHandling:
    """Tests for graceful cancellation handling."""

    @pytest.fixture
    def queue(self) -> InMemoryTaskQueue:
        """Create a fresh queue."""
        return InMemoryTaskQueue()

    @pytest.mark.asyncio
    async def test_worker_cancels_gracefully(self, queue: InMemoryTaskQueue) -> None:
        """Worker handles cancellation gracefully."""
        started_processing = asyncio.Event()

        async def slow_processor(task: Task) -> Ok:
            started_processing.set()
            await asyncio.sleep(10)  # Long task
            return Ok({"done": True})

        worker = AsyncWorker(queue=queue, processor=slow_processor, poll_interval=0.01)

        await queue.enqueue(Task(id="t1", type="test", payload={}))

        await worker.start()
        await asyncio.wait_for(started_processing.wait(), timeout=0.5)

        # Stop while task is in progress
        await worker.stop()

        # Worker should stop despite in-progress task
        assert not worker.is_running

    @pytest.mark.asyncio
    async def test_pool_cancels_all_workers(self, queue: InMemoryTaskQueue) -> None:
        """Pool cancels all workers on stop."""
        started_processing = asyncio.Event()

        async def slow_processor(task: Task) -> Ok:
            started_processing.set()
            await asyncio.sleep(10)
            return Ok({"done": True})

        pool = WorkerPool(queue=queue, processor=slow_processor, num_workers=3)

        for i in range(3):
            await queue.enqueue(Task(id=f"t{i}", type="test", payload={}))

        await pool.start()
        await asyncio.sleep(0.1)  # Let workers start

        await pool.stop()

        assert pool.running_count == 0
