"""Tests for queue/worker interfaces.

These tests verify the protocol definitions and Task model
without requiring concrete implementations.
"""

from datetime import datetime, timezone
from typing import Any

import pytest

from dawn_kestrel.core.result import Err, Ok, Result
from dawn_kestrel.reliability.queue_worker import Task, TaskQueue, TaskStatus, Worker


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self) -> None:
        """TaskStatus should have expected values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"

    def test_task_status_count(self) -> None:
        """TaskStatus should have exactly 4 values."""
        assert len(TaskStatus) == 4


class TestTask:
    """Tests for Task model."""

    def test_task_creation_minimal(self) -> None:
        """Task can be created with required fields."""
        task = Task(
            id="task-001",
            type="email",
            payload={"to": "user@example.com"},
        )
        assert task.id == "task-001"
        assert task.type == "email"
        assert task.payload == {"to": "user@example.com"}
        assert task.status == TaskStatus.PENDING
        assert task.priority == 0

    def test_task_creation_with_all_fields(self) -> None:
        """Task can be created with all fields."""
        created_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        task = Task(
            id="task-002",
            type="export",
            payload={"format": "pdf"},
            status=TaskStatus.RUNNING,
            priority=10,
            created_at=created_at,
        )
        assert task.id == "task-002"
        assert task.type == "export"
        assert task.payload == {"format": "pdf"}
        assert task.status == TaskStatus.RUNNING
        assert task.priority == 10
        assert task.created_at == created_at

    def test_task_default_status(self) -> None:
        """Task defaults to PENDING status."""
        task = Task(id="t1", type="test", payload={})
        assert task.status == TaskStatus.PENDING

    def test_task_default_priority(self) -> None:
        """Task defaults to priority 0."""
        task = Task(id="t1", type="test", payload={})
        assert task.priority == 0

    def test_task_created_at_auto_generated(self) -> None:
        """Task auto-generates created_at if not provided."""
        task = Task(id="t1", type="test", payload={})
        assert task.created_at is not None
        assert isinstance(task.created_at, datetime)

    def test_task_payload_can_be_any_dict(self) -> None:
        """Task payload accepts any dict structure."""
        task = Task(
            id="t1",
            type="complex",
            payload={
                "nested": {"deep": {"value": 123}},
                "list": [1, 2, 3],
                "string": "hello",
            },
        )
        assert task.payload["nested"]["deep"]["value"] == 123

    def test_task_is_pydantic_model(self) -> None:
        """Task is a Pydantic model with validation."""
        task = Task(id="t1", type="test", payload={"key": "value"})
        # Pydantic models have model_dump method
        data = task.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "t1"


class TestTaskQueueProtocol:
    """Tests for TaskQueue protocol definition."""

    def test_task_queue_is_protocol(self) -> None:
        """TaskQueue is a Protocol with runtime_checkable."""
        from typing import Protocol

        assert issubclass(TaskQueue, Protocol)
        assert TaskQueue._is_protocol

    def test_task_queue_has_enqueue(self) -> None:
        """TaskQueue protocol has enqueue method."""
        assert hasattr(TaskQueue, "enqueue")

    def test_task_queue_has_dequeue(self) -> None:
        """TaskQueue protocol has dequeue method."""
        assert hasattr(TaskQueue, "dequeue")

    def test_task_queue_has_peek(self) -> None:
        """TaskQueue protocol has peek method."""
        assert hasattr(TaskQueue, "peek")

    def test_task_queue_has_size(self) -> None:
        """TaskQueue protocol has size method."""
        assert hasattr(TaskQueue, "size")


class TestWorkerProtocol:
    """Tests for Worker protocol definition."""

    def test_worker_is_protocol(self) -> None:
        """Worker is a Protocol with runtime_checkable."""
        from typing import Protocol

        assert issubclass(Worker, Protocol)

    def test_worker_has_process(self) -> None:
        """Worker protocol has process method."""
        assert hasattr(Worker, "process")

    def test_worker_has_start(self) -> None:
        """Worker protocol has start method."""
        assert hasattr(Worker, "start")

    def test_worker_has_stop(self) -> None:
        """Worker protocol has stop method."""
        assert hasattr(Worker, "stop")


class MockTaskQueue:
    """Mock implementation of TaskQueue for testing protocol compliance."""

    async def enqueue(self, task: Task) -> Result[Task]:
        """Add task to queue."""
        return Ok(task)

    async def dequeue(self) -> Result[Task | None]:
        """Remove and return next task."""
        return Ok(None)

    async def peek(self) -> Result[Task | None]:
        """Return next task without removing."""
        return Ok(None)

    async def size(self) -> Result[int]:
        """Return queue size."""
        return Ok(0)


class MockWorker:
    """Mock implementation of Worker for testing protocol compliance."""

    async def process(self, task: Task) -> Result[Any]:
        """Process a task."""
        return Ok({"result": "success"})

    async def start(self) -> Result[None]:
        """Start the worker."""
        return Ok(None)

    async def stop(self) -> Result[None]:
        """Stop the worker."""
        return Ok(None)


class TestProtocolCompliance:
    """Tests verifying mock implementations satisfy protocols."""

    @pytest.mark.asyncio
    async def test_mock_queue_satisfies_protocol(self) -> None:
        """MockTaskQueue satisfies TaskQueue protocol."""
        queue: TaskQueue = MockTaskQueue()
        task = Task(id="t1", type="test", payload={})

        result = await queue.enqueue(task)
        assert result.is_ok()

        result = await queue.dequeue()
        assert result.is_ok()

        result = await queue.peek()
        assert result.is_ok()

        result = await queue.size()
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_mock_worker_satisfies_protocol(self) -> None:
        """MockWorker satisfies Worker protocol."""
        worker: Worker = MockWorker()
        task = Task(id="t1", type="test", payload={})

        result = await worker.process(task)
        assert result.is_ok()

        result = await worker.start()
        assert result.is_ok()

        result = await worker.stop()
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_queue_returns_result_types(self) -> None:
        """TaskQueue methods return Result types."""
        queue = MockTaskQueue()
        task = Task(id="t1", type="test", payload={})

        enqueue_result = await queue.enqueue(task)
        assert isinstance(enqueue_result, Ok)

        dequeue_result = await queue.dequeue()
        assert isinstance(dequeue_result, Ok)

        peek_result = await queue.peek()
        assert isinstance(peek_result, Ok)

        size_result = await queue.size()
        assert isinstance(size_result, Ok)

    @pytest.mark.asyncio
    async def test_worker_returns_result_types(self) -> None:
        """Worker methods return Result types."""
        worker = MockWorker()
        task = Task(id="t1", type="test", payload={})

        process_result = await worker.process(task)
        assert isinstance(process_result, Ok)

        start_result = await worker.start()
        assert isinstance(start_result, Ok)

        stop_result = await worker.stop()
        assert isinstance(stop_result, Ok)


class TestResultTypes:
    """Tests verifying Result type usage patterns."""

    @pytest.mark.asyncio
    async def test_enqueue_returns_task_on_success(self) -> None:
        """enqueue returns Ok[Task] on success."""
        queue = MockTaskQueue()
        task = Task(id="t1", type="test", payload={})

        result = await queue.enqueue(task)

        assert result.is_ok()
        assert isinstance(result.unwrap(), Task)

    @pytest.mark.asyncio
    async def test_dequeue_returns_optional_task(self) -> None:
        """dequeue returns Ok[Task | None]."""
        queue = MockTaskQueue()

        result = await queue.dequeue()

        assert result.is_ok()
        # Can be None or Task
        value = result.unwrap()
        assert value is None or isinstance(value, Task)

    @pytest.mark.asyncio
    async def test_size_returns_int(self) -> None:
        """size returns Ok[int]."""
        queue = MockTaskQueue()

        result = await queue.size()

        assert result.is_ok()
        assert isinstance(result.unwrap(), int)

    @pytest.mark.asyncio
    async def test_process_returns_any(self) -> None:
        """process returns Ok[Any] with result data."""
        worker = MockWorker()
        task = Task(id="t1", type="test", payload={})

        result = await worker.process(task)

        assert result.is_ok()
        # Result can be any type
        _ = result.unwrap()
