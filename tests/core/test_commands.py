"""Tests for Command pattern implementation.

Tests cover:
- Command protocol compliance
- BaseCommand functionality
- CreateSessionCommand execution
- ExecuteToolCommand execution
- CommandQueue management and event publishing
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from dawn_kestrel.core.commands import (
    Command,
    CommandContext,
    BaseCommand,
    CreateSessionCommand,
    ExecuteToolCommand,
    CommandQueue,
)
from dawn_kestrel.core.mediator import Event, EventMediatorImpl, EventType
from dawn_kestrel.core.result import Ok, Err, Result


class TestCommandProtocol:
    """Tests for Command protocol compliance."""

    def test_base_command_has_all_required_methods(self):
        """BaseCommand implements all Command protocol methods."""
        command = BaseCommand(name="test", description="Test command")
        assert hasattr(command, "execute")
        assert hasattr(command, "undo")
        assert hasattr(command, "can_undo")
        assert hasattr(command, "get_provenance")

    def test_base_command_defaults_are_set(self):
        """BaseCommand sets default values correctly."""
        command = BaseCommand(name="test", description="Test command")
        assert command.name == "test"
        assert command.description == "Test command"
        assert isinstance(command.created_at, datetime)
        assert not command.can_undo()


class TestCreateSessionCommand:
    """Tests for CreateSessionCommand."""

    @pytest.mark.asyncio
    async def test_create_session_command_executes_with_session_repo(self):
        """CreateSessionCommand executes using session_repo from context."""
        # Setup
        session_repo = AsyncMock()
        session_repo.create = AsyncMock(return_value=Ok("session_123"))

        command = CreateSessionCommand(session_id="session_123", title="Test Session")
        context = CommandContext(
            session_id="session_123",
            metadata={
                "project_id": "project_456",
                "project_dir": "/path/to/project",
                "session_repo": session_repo,
            },
        )

        # Execute
        result = await command.execute(context)

        # Verify
        assert result.is_ok()
        assert result.unwrap() == "session_123"
        session_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_command_returns_session_id(self):
        """CreateSessionCommand returns session_id on success."""
        session_repo = AsyncMock()
        session_repo.create = AsyncMock(return_value=Ok("session_xyz"))

        command = CreateSessionCommand(session_id="session_xyz", title="Test Session")
        context = CommandContext(
            metadata={
                "session_repo": session_repo,
                "project_id": "proj",
                "project_dir": "/dir",
            }
        )

        result = await command.execute(context)

        assert result.is_ok()
        assert result.unwrap() == "session_xyz"

    @pytest.mark.asyncio
    async def test_create_session_command_handles_missing_session_repo(self):
        """CreateSessionCommand returns Err when session_repo not in context."""
        command = CreateSessionCommand(session_id="session_123", title="Test Session")
        context = CommandContext()  # No session_repo

        result = await command.execute(context)

        assert result.is_err()
        assert "session_repo not in context" in str(result.error)
        assert result.code == "MISSING_DEPENDENCY"

    @pytest.mark.asyncio
    async def test_create_session_command_gets_provenance(self):
        """CreateSessionCommand returns provenance information."""
        command = CreateSessionCommand(session_id="session_123", title="Test Session")

        result = await command.get_provenance()

        assert result.is_ok()
        provenance = result.unwrap()
        assert provenance["command"] == "create_session"
        assert "Test Session" in provenance["description"]
        assert "created_at" in provenance
        assert not provenance["can_undo"]

    def test_create_session_command_cannot_undo(self):
        """CreateSessionCommand cannot be undone."""
        command = CreateSessionCommand(session_id="session_123", title="Test Session")
        assert not command.can_undo()

    @pytest.mark.asyncio
    async def test_create_session_command_undo_returns_err(self):
        """CreateSessionCommand.undo returns Err."""
        command = CreateSessionCommand(session_id="session_123", title="Test Session")

        result = await command.undo()

        assert result.is_err()


class TestExecuteToolCommand:
    """Tests for ExecuteToolCommand."""

    @pytest.mark.asyncio
    async def test_execute_tool_command_executes_with_tool_adapter(self):
        """ExecuteToolCommand executes using tool_adapter from context."""
        # Setup
        tool_adapter = AsyncMock()
        tool_adapter.execute = AsyncMock(return_value=Ok({"output": "test result"}))

        command = ExecuteToolCommand(tool_name="bash", arguments={"command": "ls"})
        context = CommandContext(
            session_id="session_123",
            message_id="msg_456",
            metadata={"tool_adapter": tool_adapter},
        )

        # Execute
        result = await command.execute(context)

        # Verify
        assert result.is_ok()
        assert result.unwrap() == {"output": "test result"}
        tool_adapter.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_command_passes_arguments_to_tool(self):
        """ExecuteToolCommand passes arguments to tool_adapter.execute."""
        tool_adapter = AsyncMock()
        tool_adapter.execute = AsyncMock(return_value=Ok({"result": "success"}))

        arguments = {"command": "echo hello", "timeout": 30}
        command = ExecuteToolCommand(tool_name="bash", arguments=arguments)
        context = CommandContext(metadata={"tool_adapter": tool_adapter})

        await command.execute(context)

        tool_adapter.execute.assert_called_once()
        call_args = tool_adapter.execute.call_args
        assert call_args[1] == arguments  # kwargs should match arguments

    @pytest.mark.asyncio
    async def test_execute_tool_command_returns_tool_result(self):
        """ExecuteToolCommand returns tool adapter result."""
        tool_adapter = AsyncMock()
        expected_result = {"output": "tool output", "exit_code": 0}
        tool_adapter.execute = AsyncMock(return_value=Ok(expected_result))

        command = ExecuteToolCommand(tool_name="read", arguments={"file_path": "/path"})
        context = CommandContext(metadata={"tool_adapter": tool_adapter})

        result = await command.execute(context)

        assert result.is_ok()
        assert result.unwrap() == expected_result

    @pytest.mark.asyncio
    async def test_execute_tool_command_handles_missing_tool_adapter(self):
        """ExecuteToolCommand returns Err when tool_adapter not in context."""
        command = ExecuteToolCommand(tool_name="bash", arguments={"command": "ls"})
        context = CommandContext()  # No tool_adapter

        result = await command.execute(context)

        assert result.is_err()
        assert "tool_adapter not in context" in str(result.error)
        assert result.code == "MISSING_DEPENDENCY"

    @pytest.mark.asyncio
    async def test_execute_tool_command_gets_provenance(self):
        """ExecuteToolCommand returns provenance information."""
        command = ExecuteToolCommand(tool_name="bash", arguments={"command": "ls"})

        result = await command.get_provenance()

        assert result.is_ok()
        provenance = result.unwrap()
        assert provenance["command"] == "execute_tool"
        assert "bash" in provenance["description"]
        assert "created_at" in provenance
        assert not provenance["can_undo"]


class TestCommandQueue:
    """Tests for CommandQueue."""

    def test_command_queue_initializes_empty(self):
        """CommandQueue initializes with empty queue and history."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        assert len(queue._queue) == 0
        assert len(queue._history) == 0

    @pytest.mark.asyncio
    async def test_enqueue_adds_command_and_publishes_event(self):
        """enqueue adds command to queue and publishes enqueued event."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        # Subscribe to capture events
        events = []

        async def handler(event):
            events.append(event)

        await mediator.subscribe(EventType.APPLICATION, handler)

        command = CreateSessionCommand(session_id="session_123", title="Test")
        result = await queue.enqueue(command)

        # Verify enqueue result
        assert result.is_ok()
        assert len(queue._queue) == 1
        assert queue._queue[0] == command

        # Verify event published
        assert len(events) == 1
        assert events[0].event_type == EventType.APPLICATION
        assert events[0].data["action"] == "command_enqueued"
        assert events[0].data["command"] == "create_session"

    @pytest.mark.asyncio
    async def test_enqueue_returns_ok_on_success(self):
        """enqueue returns Ok on successful enqueue."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        command = CreateSessionCommand(session_id="session_123", title="Test")
        result = await queue.enqueue(command)

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_enqueue_publishes_command_enqueued_event(self):
        """enqueue publishes command_enqueued event."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        events = []

        async def handler(event):
            events.append(event)

        await mediator.subscribe(EventType.APPLICATION, handler)

        command = ExecuteToolCommand(tool_name="bash", arguments={})
        await queue.enqueue(command)

        assert len(events) == 1
        assert events[0].data["action"] == "command_enqueued"
        assert events[0].source == "command_queue"

    @pytest.mark.asyncio
    async def test_process_next_removes_command_from_queue(self):
        """process_next removes command from queue after processing."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        command = BaseCommand(name="test", description="Test")
        await queue.enqueue(command)

        assert len(queue._queue) == 1

        # Mock execute to return Ok
        async def mock_execute(context):
            return Ok("result")

        command.execute = mock_execute

        await queue.process_next()

        assert len(queue._queue) == 0

    @pytest.mark.asyncio
    async def test_process_next_publishes_started_event(self):
        """process_next publishes command_started event."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        events = []

        async def handler(event):
            events.append(event)

        await mediator.subscribe(EventType.APPLICATION, handler)

        command = BaseCommand(name="test", description="Test")

        async def mock_execute(context):
            return Ok("result")

        command.execute = mock_execute

        await queue.enqueue(command)
        await queue.process_next()

        started_events = [e for e in events if e.data["action"] == "command_started"]
        assert len(started_events) == 1

    @pytest.mark.asyncio
    async def test_process_next_executes_command(self):
        """process_next executes command from queue."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        executed = False
        command = BaseCommand(name="test", description="Test")

        async def mock_execute(context):
            nonlocal executed
            executed = True
            return Ok("result")

        command.execute = mock_execute

        await queue.enqueue(command)
        await queue.process_next()

        assert executed

    @pytest.mark.asyncio
    async def test_process_next_publishes_completed_event(self):
        """process_next publishes command_completed event on success."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        events = []

        async def handler(event):
            events.append(event)

        await mediator.subscribe(EventType.APPLICATION, handler)

        command = BaseCommand(name="test", description="Test")

        async def mock_execute(context):
            return Ok("result")

        command.execute = mock_execute

        await queue.enqueue(command)
        await queue.process_next()

        completed_events = [e for e in events if e.data["action"] == "command_completed"]
        assert len(completed_events) == 1

    @pytest.mark.asyncio
    async def test_process_next_publishes_failed_event_on_error(self):
        """process_next publishes command_failed event on error."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        events = []

        async def handler(event):
            events.append(event)

        await mediator.subscribe(EventType.APPLICATION, handler)

        command = BaseCommand(name="test", description="Test")

        async def mock_execute(context):
            return Err("Command failed", code="TEST_ERROR")

        command.execute = mock_execute

        await queue.enqueue(command)
        await queue.process_next()

        failed_events = [e for e in events if e.data["action"] == "command_failed"]
        assert len(failed_events) == 1
        assert "error" in failed_events[0].data

    @pytest.mark.asyncio
    async def test_process_next_returns_error_when_queue_empty(self):
        """process_next returns Err when queue is empty."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        result = await queue.process_next()

        assert result.is_err()
        assert "No commands in queue" in str(result.error)
        assert result.code == "QUEUE_EMPTY"

    @pytest.mark.asyncio
    async def test_history_tracks_commands(self):
        """CommandQueue tracks all commands in history."""
        mediator = EventMediatorImpl()
        queue = CommandQueue(mediator)

        command1 = BaseCommand(name="cmd1", description="First")
        command2 = BaseCommand(name="cmd2", description="Second")

        # Mock execute
        async def mock_execute(context):
            return Ok("result")

        command1.execute = mock_execute
        command2.execute = mock_execute

        await queue.enqueue(command1)
        await queue.enqueue(command2)

        assert len(queue._history) == 2
        assert queue._history[0] == command1
        assert queue._history[1] == command2

        # Process and verify history persists
        await queue.process_next()
        await queue.process_next()

        assert len(queue._history) == 2
