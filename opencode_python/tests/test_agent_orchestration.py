"""
Phase 3: Multi-Agent Orchestration - AgentOrchestrator Tests.

Comprehensive tests for orchestration logic including delegation,
parallel execution, task status tracking, and error handling.
"""
from __future__ import annotations

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from opencode_python.core.agent_task import AgentTask, TaskStatus, create_agent_task
from opencode_python.core.agent_types import AgentResult, Session, Message
from opencode_python.agents.orchestrator import AgentOrchestrator, TaskResult, create_agent_orchestrator
from opencode_python.agents.runtime import AgentRuntime
from opencode_python.agents.registry import AgentRegistry
from opencode_python.agents.builtin import Agent
from opencode_python.tools.framework import ToolRegistry
from opencode_python.tools import create_builtin_registry


@pytest.fixture
def agent_registry():
    """Create AgentRegistry with built-in agents."""
    return AgentRegistry()


@pytest.fixture
def agent_runtime(agent_registry):
    """Create AgentRuntime for testing."""
    from pathlib import Path
    return AgentRuntime(agent_registry=agent_registry, base_dir=Path("/tmp"))


@pytest.fixture
def orchestrator(agent_runtime):
    """Create AgentOrchestrator for testing."""
    return create_agent_orchestrator(agent_runtime=agent_runtime)


@pytest.fixture
def mock_session():
    """Create mock Session object."""
    return Session(
        id="test-session-id",
        slug="test-session",
        title="Test Session",
        project_id="test-project",
        directory="/tmp/test",
        version="1.0",
        time_created=0.0,
        time_updated=0.0,
    )


@pytest.fixture
def mock_session_manager():
    """Create mock SessionManager."""
    manager = AsyncMock()
    manager.get_session = AsyncMock(return_value=None)
    manager.list_messages = AsyncMock(return_value=[])
    manager.add_message = AsyncMock(return_value="msg-id")
    manager.add_part = AsyncMock(return_value="part-id")
    return manager


@pytest.fixture
def mock_tool_registry():
    """Create mock ToolRegistry."""
    return create_builtin_registry()


class TestAgentTask:
    """Tests for AgentTask model."""

    def test_create_agent_task(self):
        """Test creating a basic task."""
        task = create_agent_task(
            agent_name="test-agent",
            description="Test task description",
        )

        assert task.agent_name == "test-agent"
        assert task.description == "Test task description"
        assert task.status == TaskStatus.PENDING
        assert task.task_id
        assert isinstance(task.task_id, str)

    def test_create_agent_task_with_options(self):
        """Test creating task with options."""
        task = create_agent_task(
            agent_name="test-agent",
            description="Test task",
            tool_ids=["tool1", "tool2"],
            skill_names=["skill1"],
            options={"model": "gpt-4", "temperature": 0.7},
        )

        assert task.tool_ids == ["tool1", "tool2"]
        assert task.skill_names == ["skill1"]
        assert task.options == {"model": "gpt-4", "temperature": 0.7}

    def test_create_agent_task_with_parent(self):
        """Test creating sub-task with parent."""
        parent_task = create_agent_task(
            agent_name="parent-agent",
            description="Parent task",
        )

        child_task = create_agent_task(
            agent_name="child-agent",
            description="Child task",
            parent_id=parent_task.task_id,
        )

        assert child_task.parent_id == parent_task.task_id
        assert child_task.has_dependencies()
        assert not parent_task.has_dependencies()

    def test_task_status_methods(self):
        """Test task status helper methods."""
        task = create_agent_task("test-agent", "Test")

        assert task.is_active()
        assert task.can_start()
        assert not task.is_complete()

        task.status = TaskStatus.RUNNING
        assert task.is_active()
        assert not task.can_start()
        assert not task.is_complete()

        task.status = TaskStatus.COMPLETED
        assert not task.is_active()
        assert not task.can_start()
        assert task.is_complete()

        task.status = TaskStatus.FAILED
        assert not task.is_active()
        assert not task.can_start()
        assert task.is_complete()

        task.status = TaskStatus.CANCELLED
        assert not task.is_active()
        assert not task.can_start()
        assert task.is_complete()


class TestTaskResult:
    """Tests for TaskResult wrapper."""

    def test_task_result_creation(self):
        """Test creating TaskResult."""
        task = create_agent_task("test-agent", "Test")
        result = TaskResult(
            task=task,
            result=None,
            error=None,
            started_at=100.0,
            completed_at=105.0,
        )

        assert result.task == task
        assert result.started_at == 100.0
        assert result.completed_at == 105.0

    def test_task_result_with_agent_result(self):
        """Test TaskResult with successful AgentResult."""
        task = create_agent_task("test-agent", "Test")
        agent_result = AgentResult(
            agent_name="test-agent",
            response="Test response",
            parts=[],
            metadata={},
            tools_used=[],
            tokens_used=None,
            duration=1.5,
            error=None,
        )

        result = TaskResult(
            task=task,
            result=agent_result,
            started_at=0.0,
            completed_at=0.0,
        )

        assert result.result == agent_result
        assert result.error is None

    def test_task_result_with_error(self):
        """Test TaskResult with error."""
        task = create_agent_task("test-agent", "Test")
        task.status = TaskStatus.FAILED

        result = TaskResult(
            task=task,
            result=None,
            error="Test error",
            started_at=0.0,
            completed_at=0.0,
        )

        assert result.result is None
        assert result.error == "Test error"


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, agent_runtime):
        """Test orchestrator initialization."""
        orchestrator = AgentOrchestrator(agent_runtime=agent_runtime)

        assert orchestrator.agent_runtime == agent_runtime
        assert len(orchestrator._tasks) == 0
        assert len(orchestrator._results) == 0

    @pytest.mark.asyncio
    async def test_delegate_task_success(
        self, orchestrator, mock_session_manager, mock_session, mock_tool_registry
    ):
        """Test successful task delegation."""
        mock_session_manager.get_session = AsyncMock(return_value=mock_session)

        task = create_agent_task(
            agent_name="explore",
            description="Test exploration",
        )

        with patch.object(orchestrator.agent_runtime, 'execute_agent', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AgentResult(
                agent_name="explore",
                response="Test response",
                parts=[],
                metadata={},
                tools_used=[],
                tokens_used=None,
                duration=0.5,
                error=None,
            )

            result_id = await orchestrator.delegate_task(
                task=task,
                session_id="test-session",
                user_message="Test message",
                session_manager=mock_session_manager,
                tools=mock_tool_registry,
                session=mock_session,
            )

            assert result_id == task.task_id
            assert task.status == TaskStatus.COMPLETED
            assert task.result_id == task.task_id

            result = orchestrator.get_result(result_id)
            assert result is not None
            assert result.result.agent_name == "explore"

    @pytest.mark.asyncio
    async def test_delegate_task_failure(
        self, orchestrator, mock_session_manager, mock_session, mock_tool_registry
    ):
        """Test task delegation with execution failure."""
        mock_session_manager.get_session = AsyncMock(return_value=mock_session)

        task = create_agent_task(
            agent_name="explore",
            description="Test task",
        )

        with patch.object(orchestrator.agent_runtime, 'execute_agent', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Agent execution failed")

            with pytest.raises(Exception, match="Agent execution failed"):
                await orchestrator.delegate_task(
                    task=task,
                    session_id="test-session",
                    user_message="Test message",
                    session_manager=mock_session_manager,
                    tools=mock_tool_registry,
                    session=mock_session,
                )

            assert task.status == TaskStatus.FAILED
            assert task.error == "Agent execution failed"

            result = orchestrator.get_result(task.task_id)
            assert result is not None
            assert result.error == "Agent execution failed"
            assert result.result is None

    @pytest.mark.asyncio
    async def test_delegate_task_invalid_status(self, orchestrator):
        """Test that non-pending tasks cannot be delegated."""
        task = create_agent_task("test-agent", "Test")
        task.status = TaskStatus.RUNNING

        with pytest.raises(ValueError, match="is not pending"):
            await orchestrator.delegate_task(
                task=task,
                session_id="test-session",
                user_message="Test",
                session_manager=AsyncMock(),
                tools=mock_tool_registry,
                session=Session(
                    id="test", slug="test", title="Test", project_id="p",
                    directory="/tmp", version="1.0",
                    time_created=0.0, time_updated=0.0
                ),
            )

    @pytest.mark.asyncio
    async def test_get_task_status(self, orchestrator):
        """Test getting task status."""
        task = create_agent_task("test-agent", "Test")
        task.task_id = "test-task-id"

        with orchestrator._task_lock:
            orchestrator._tasks["test-task-id"] = task

        status = orchestrator.get_status("test-task-id")
        assert status == TaskStatus.PENDING

        unknown_status = orchestrator.get_status("unknown-id")
        assert unknown_status is None

    @pytest.mark.asyncio
    async def test_get_task_result(self, orchestrator):
        """Test getting task result."""
        task = create_agent_task("test-agent", "Test")

        result = TaskResult(
            task=task,
            result=None,
            error=None,
            started_at=0.0,
            completed_at=0.0,
        )

        with orchestrator._task_lock:
            orchestrator._results[task.task_id] = result

        retrieved = orchestrator.get_result(task.task_id)
        assert retrieved == result

        unknown_result = orchestrator.get_result("unknown-id")
        assert unknown_result is None

    @pytest.mark.asyncio
    async def test_get_active_tasks(self, orchestrator):
        """Test getting active tasks."""
        task1 = create_agent_task("agent1", "Task 1")
        task2 = create_agent_task("agent2", "Task 2")
        task3 = create_agent_task("agent3", "Task 3")

        task1.status = TaskStatus.PENDING
        task2.status = TaskStatus.RUNNING
        task3.status = TaskStatus.COMPLETED

        with orchestrator._task_lock:
            orchestrator._tasks[task1.task_id] = task1
            orchestrator._tasks[task2.task_id] = task2
            orchestrator._tasks[task3.task_id] = task3

        active = orchestrator.get_active_tasks()
        assert len(active) == 2
        assert task1 in active
        assert task2 in active
        assert task3 not in active

    @pytest.mark.asyncio
    async def test_get_child_tasks(self, orchestrator):
        """Test getting child tasks."""
        parent = create_agent_task("parent", "Parent task")
        child1 = create_agent_task("child1", "Child 1", parent_id=parent.task_id)
        child2 = create_agent_task("child2", "Child 2", parent_id=parent.task_id)
        unrelated = create_agent_task("unrelated", "Unrelated task")

        with orchestrator._task_lock:
            orchestrator._tasks[parent.task_id] = parent
            orchestrator._tasks[child1.task_id] = child1
            orchestrator._tasks[child2.task_id] = child2
            orchestrator._tasks[unrelated.task_id] = unrelated

        children = orchestrator.get_child_tasks(parent.task_id)
        assert len(children) == 2
        assert child1 in children
        assert child2 in children
        assert unrelated not in children

    @pytest.mark.asyncio
    async def test_list_tasks(self, orchestrator):
        """Test listing tasks."""
        task1 = create_agent_task("agent1", "Task 1")
        task2 = create_agent_task("agent2", "Task 2")
        task3 = create_agent_task("agent3", "Task 3")

        task1.status = TaskStatus.PENDING
        task2.status = TaskStatus.COMPLETED
        task3.status = TaskStatus.PENDING

        with orchestrator._task_lock:
            orchestrator._tasks[task1.task_id] = task1
            orchestrator._tasks[task2.task_id] = task2
            orchestrator._tasks[task3.task_id] = task3

        all_tasks = orchestrator.list_tasks()
        assert len(all_tasks) == 3

        pending_tasks = orchestrator.list_tasks(status_filter=TaskStatus.PENDING)
        assert len(pending_tasks) == 2
        assert task1 in pending_tasks
        assert task3 in pending_tasks
        assert task2 not in pending_tasks

    @pytest.mark.asyncio
    async def test_list_results(self, orchestrator):
        """Test listing all results."""
        task1 = create_agent_task("agent1", "Task 1")
        task2 = create_agent_task("agent2", "Task 2")

        result1 = TaskResult(task=task1, result=None, error=None, started_at=0.0, completed_at=0.0)
        result2 = TaskResult(task=task2, result=None, error=None, started_at=0.0, completed_at=0.0)

        with orchestrator._task_lock:
            orchestrator._results[task1.task_id] = result1
            orchestrator._results[task2.task_id] = result2

        results = orchestrator.list_results()
        assert len(results) == 2
        assert result1 in results
        assert result2 in results

    @pytest.mark.asyncio
    async def test_clear_completed_tasks(self, orchestrator):
        """Test clearing completed tasks."""
        task1 = create_agent_task("agent1", "Task 1")
        task2 = create_agent_task("agent2", "Task 2")
        task3 = create_agent_task("agent3", "Task 3")

        task1.status = TaskStatus.PENDING
        task2.status = TaskStatus.COMPLETED
        task3.status = TaskStatus.RUNNING

        with orchestrator._task_lock:
            orchestrator._tasks[task1.task_id] = task1
            orchestrator._tasks[task2.task_id] = task2
            orchestrator._tasks[task3.task_id] = task3
            orchestrator._results[task1.task_id] = TaskResult(
                task=task1, result=None, error=None, started_at=0.0, completed_at=0.0
            )
            orchestrator._results[task2.task_id] = TaskResult(
                task=task2, result=None, error=None, started_at=0.0, completed_at=0.0
            )

        cleared = orchestrator.clear_completed_tasks()
        assert cleared == 1

        assert task1.task_id in orchestrator._tasks
        assert task3.task_id in orchestrator._tasks
        assert task2.task_id not in orchestrator._tasks

    @pytest.mark.asyncio
    async def test_cancel_tasks(self, orchestrator):
        """Test cancelling tasks."""
        task1 = create_agent_task("agent1", "Task 1")
        task2 = create_agent_task("agent2", "Task 2")
        task3 = create_agent_task("agent3", "Task 3")

        task1.status = TaskStatus.PENDING
        task2.status = TaskStatus.RUNNING
        task3.status = TaskStatus.COMPLETED

        with orchestrator._task_lock:
            orchestrator._tasks[task1.task_id] = task1
            orchestrator._tasks[task2.task_id] = task2
            orchestrator._tasks[task3.task_id] = task3

        cancelled = await orchestrator.cancel_tasks([task1.task_id, task2.task_id, task3.task_id])
        assert cancelled == 2

        assert task1.status == TaskStatus.CANCELLED
        assert task2.status == TaskStatus.CANCELLED
        assert task3.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_thread_safety(self, orchestrator):
        """Test thread-safe operations."""
        tasks = [
            create_agent_task(f"agent{i}", f"Task {i}")
            for i in range(10)
        ]

        async def add_task(task):
            with orchestrator._task_lock:
                orchestrator._tasks[task.task_id] = task

        await asyncio.gather(*[add_task(t) for t in tasks])

        with orchestrator._task_lock:
            assert len(orchestrator._tasks) == 10
