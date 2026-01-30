"""
Integration tests for agent orchestration with task tool.

Tests end-to-end integration between:
- AgentRuntime with task_id parameter
- AgentOrchestrator task delegation
- AgentResult.task_id field population
- Task lifecycle events emission
- Orchestrator task tracking
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, MagicMock, patch
import asyncio

from opencode_python.agents.runtime import AgentRuntime, create_agent_runtime
from opencode_python.agents.orchestrator import AgentOrchestrator, create_agent_orchestrator
from opencode_python.agents.registry import AgentRegistry, create_agent_registry
from opencode_python.agents.builtin import Agent
from opencode_python.core.models import Session, Message, TokenUsage, TextPart
from opencode_python.core.agent_types import AgentResult, SessionManagerLike
from opencode_python.core.agent_task import AgentTask, TaskStatus
from opencode_python.core.event_bus import bus, Events
from opencode_python.tools.framework import ToolRegistry, ToolContext, ToolResult
from opencode_python.tools import create_builtin_registry


@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    return Session(
        id="test-session-123",
        slug="test-session",
        project_id="test-project",
        directory="/tmp/test-project",
        title="Test Session",
        version="1.0.0",
    )


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    return Agent(
        name="build",
        description="Build agent",
        mode="build",
        permission=[
            {"permission": "*", "pattern": "*", "action": "allow"},
        ],
        native=True,
        hidden=False,
        temperature=0.7,
        top_p=0.9,
        color="blue",
        model={"model": "claude-sonnet-4-20250514"},
        prompt="You are a helpful build assistant.",
        options={},
        steps=[],
    )


@pytest.fixture
def builtin_registry():
    """Create a built-in tool registry."""
    return create_builtin_registry()


@pytest.fixture
def agent_registry(mock_agent):
    """Create an agent registry with test agent."""
    registry = create_agent_registry(persistence_enabled=False)
    return registry


@pytest.fixture
def mock_session_manager(mock_session):
    """Create a mock session manager."""
    manager = AsyncMock()
    manager.get_session = AsyncMock(return_value=mock_session)
    manager.list_messages = AsyncMock(return_value=[])
    manager.add_message = AsyncMock(return_value="msg-123")
    manager.add_part = AsyncMock(return_value="part-123")
    return manager


@pytest.fixture
def agent_runtime(agent_registry, tmp_path):
    """Create an AgentRuntime instance for testing."""
    return create_agent_runtime(
        agent_registry=agent_registry,
        base_dir=tmp_path,
        skill_max_char_budget=10000,
    )


@pytest.fixture
def agent_orchestrator(agent_runtime):
    """Create an AgentOrchestrator instance for testing."""
    return create_agent_orchestrator(agent_runtime=agent_runtime)


class TestAgentRuntimeTaskIntegration:
    """Tests for AgentRuntime task_id integration."""

    @pytest.mark.asyncio
    async def test_execute_agent_with_task_id(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test agent execution with task_id parameter."""
        mock_ai_session = AsyncMock()

        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Task response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Task response",
            )],
            metadata={
                "tokens": {"input": 10, "output": 20, "reasoning": 0, "cache_read": 0, "cache_write": 0},
            },
        )

        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("opencode_python.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Execute task",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
                task_id="task-123",
            )

        assert isinstance(result, AgentResult)
        assert result.agent_name == "build"
        assert result.task_id == "task-123"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_agent_without_task_id(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test agent execution without task_id parameter."""
        mock_ai_session = AsyncMock()

        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Direct response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Direct response",
            )],
            metadata={},
        )

        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("opencode_python.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Direct execution",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert isinstance(result, AgentResult)
        assert result.agent_name == "build"
        assert result.task_id is None

    @pytest.mark.asyncio
    async def test_execute_agent_emits_task_events(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test that agent events include task_id when provided."""
        mock_ai_session = AsyncMock()

        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )

        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        # Subscribe to events
        events_received = {}

        async def capture_event(event):
            if hasattr(event, 'data') and 'task_id' in event.data:
                events_received[event.name] = event.data['task_id']

        await bus.subscribe(Events.AGENT_INITIALIZED, capture_event)
        await bus.subscribe(Events.AGENT_READY, capture_event)
        await bus.subscribe(Events.AGENT_EXECUTING, capture_event)

        try:
            with patch("opencode_python.agents.runtime.AISession", return_value=mock_ai_session):
                await agent_runtime.execute_agent(
                    agent_name="build",
                    session_id=mock_session.id,
                    user_message="Task",
                    session_manager=mock_session_manager,
                    tools=builtin_registry,
                    skills=[],
                    options={},
                    task_id="task-event-123",
                )

            assert Events.AGENT_INITIALIZED in events_received
            assert Events.AGENT_READY in events_received
            assert Events.AGENT_EXECUTING in events_received
            assert events_received[Events.AGENT_INITIALIZED] == "task-event-123"
            assert events_received[Events.AGENT_READY] == "task-event-123"
            assert events_received[Events.AGENT_EXECUTING] == "task-event-123"

        finally:
            await bus.clear_subscriptions(Events.AGENT_INITIALIZED)
            await bus.clear_subscriptions(Events.AGENT_READY)
            await bus.clear_subscriptions(Events.AGENT_EXECUTING)


class TestAgentOrchestratorTaskIntegration:
    """Tests for AgentOrchestrator task execution integration."""

    @pytest.mark.asyncio
    async def test_execute_task_via_task_success(
        self,
        agent_orchestrator,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test execute_task_via_task creates task and executes via runtime."""
        mock_ai_session = AsyncMock()

        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Task executed",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Task executed",
            )],
            metadata={
                "tokens": {"input": 10, "output": 20, "reasoning": 0, "cache_read": 0, "cache_write": 0},
            },
        )

        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("opencode_python.agents.runtime.AISession", return_value=mock_ai_session):
            task_result = await agent_orchestrator.execute_task_via_task(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Execute task via orchestrator",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert task_result.task is not None
        assert task_result.task.status == TaskStatus.COMPLETED
        assert task_result.result is not None
        assert task_result.result.task_id == task_result.task.task_id
        assert task_result.result.agent_name == "build"

    @pytest.mark.asyncio
    async def test_orchestrator_tracks_tasks(
        self,
        agent_orchestrator,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test that orchestrator tracks active tasks."""
        mock_ai_session = AsyncMock()

        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )

        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("opencode_python.agents.runtime.AISession", return_value=mock_ai_session):
            task_result = await agent_orchestrator.execute_task_via_task(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Task",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        # Check task is tracked
        active_tasks = agent_orchestrator.get_active_tasks()
        assert len(active_tasks) == 0  # Completed tasks are not active

        # Check result is stored
        result = agent_orchestrator.get_result(task_result.task.task_id)
        assert result is not None
        assert result.task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_orchestrator_emits_task_events(
        self,
        agent_orchestrator,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test that orchestrator emits task lifecycle events."""
        mock_ai_session = AsyncMock()

        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )

        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        # Subscribe to events
        events_received = []

        async def capture_event(event):
            if hasattr(event, 'data') and 'task_id' in event.data:
                events_received.append(event.name)

        await bus.subscribe(Events.TASK_STARTED, capture_event)
        await bus.subscribe(Events.TASK_COMPLETED, capture_event)

        try:
            with patch("opencode_python.agents.runtime.AISession", return_value=mock_ai_session):
                await agent_orchestrator.execute_task_via_task(
                    agent_name="build",
                    session_id=mock_session.id,
                    user_message="Task",
                    session_manager=mock_session_manager,
                    tools=builtin_registry,
                    skills=[],
                    options={},
                )

            assert Events.TASK_STARTED in events_received
            assert Events.TASK_COMPLETED in events_received

        finally:
            await bus.clear_subscriptions(Events.TASK_STARTED)
            await bus.clear_subscriptions(Events.TASK_COMPLETED)

    @pytest.mark.asyncio
    async def test_orchestrator_handles_parent_id(
        self,
        agent_orchestrator,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test that orchestrator supports hierarchical tasks with parent_id."""
        mock_ai_session = AsyncMock()

        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )

        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("opencode_python.agents.runtime.AISession", return_value=mock_ai_session):
            task_result = await agent_orchestrator.execute_task_via_task(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Child task",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
                parent_id="parent-task-123",
            )

        assert task_result.task.parent_id == "parent-task-123"
        assert task_result.task.status == TaskStatus.COMPLETED


class TestAgentResultTaskIdField:
    """Tests for AgentResult.task_id field."""

    @pytest.mark.asyncio
    async def test_agent_result_has_task_id_field(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test that AgentResult has task_id field."""
        mock_ai_session = AsyncMock()

        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )

        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("opencode_python.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Task",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
                task_id="test-task-456",
            )

        assert hasattr(result, "task_id")
        assert result.task_id == "test-task-456"

    @pytest.mark.asyncio
    async def test_agent_result_task_id_default_none(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test that AgentResult.task_id defaults to None."""
        mock_ai_session = AsyncMock()

        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )

        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("opencode_python.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Direct execution",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result.task_id is None
