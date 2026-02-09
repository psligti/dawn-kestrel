"""Command pattern for encapsulated actions.

This module implements the Command pattern to encapsulate requests as objects,
enabling undo/redo, provenance tracking, and execution events.

Key concepts:
- Command Protocol: Interface for command execution
- CommandContext: Execution context with runtime information
- BaseCommand: Base class for all commands
- CreateSessionCommand: Command to create sessions
- ExecuteToolCommand: Command to execute tools
- CommandQueue: Queue for managing command execution with events
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from dawn_kestrel.core.mediator import Event, EventMediator, EventType
from dawn_kestrel.core.result import Err, Ok, Result


@runtime_checkable
class Command(Protocol):
    """Protocol for command encapsulation.

    Commands encapsulate actions as objects, enabling
    undo/redo, provenance tracking, and execution events.
    """

    async def execute(self, context: CommandContext) -> Result[Any]:
        """Execute the command with given context.

        Args:
            context: Execution context with runtime information.

        Returns:
            Result[Any]: Result of command execution.
        """
        ...

    async def undo(self) -> Result[None]:
        """Undo the command (if supported).

        Returns:
            Result[None]: Ok on success, Err if undo not supported.
        """
        ...

    def can_undo(self) -> bool:
        """Check if command can be undone."""
        ...

    async def get_provenance(self) -> Result[dict[str, Any]]:
        """Get provenance information about the command.

        Returns:
            Result[dict[str, Any]]: Provenance dict with metadata.
        """
        ...


@dataclass
class CommandContext:
    """Execution context for commands.

    Provides runtime information for command execution,
    including session context and dependencies.
    """

    session_id: str | None = None
    message_id: str | None = None
    agent_id: str | None = None
    user_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BaseCommand:
    """Base class for all commands.

    Provides common functionality for all commands:
    - Name and description
    - Creation timestamp
    - Default undo behavior (not supported)
    - Provenance information
    """

    name: str
    description: str
    created_at: datetime = field(default_factory=datetime.now)

    async def execute(self, context: CommandContext) -> Result[Any]:
        """Execute the command (abstract, must be overridden).

        Args:
            context: Execution context with runtime information.

        Returns:
            Result[Any]: Result of command execution.

        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError(f"{self.name} command does not implement execute")

    def can_undo(self) -> bool:
        """Check if command can be undone.

        Default implementation returns False.
        Subclasses can override to support undo.
        """
        return False

    async def get_provenance(self) -> Result[dict[str, Any]]:
        """Get provenance information about the command.

        Returns:
            Result[dict[str, Any]]: Provenance dict with metadata.
        """
        return Ok(
            {
                "command": self.name,
                "description": self.description,
                "created_at": self.created_at.isoformat(),
                "can_undo": self.can_undo(),
            }
        )

    async def undo(self) -> Result[None]:
        """Undo the command.

        Default implementation returns Err (not supported).
        Subclasses can override to support undo.

        Returns:
            Result[None]: Err with undo not supported message.
        """
        return Err(f"Command {self.name} does not support undo", code="UNDO_NOT_SUPPORTED")


class CreateSessionCommand(BaseCommand):
    """Command to create a session.

    Uses session_repo from context to create a new session
    with the provided session_id and title.
    """

    def __init__(self, session_id: str, title: str):
        """Initialize CreateSessionCommand.

        Args:
            session_id: Unique identifier for the session.
            title: Display title for the session.
        """
        super().__init__(
            name="create_session",
            description=f"Create session: {title}",
        )
        self.session_id = session_id
        self.title = title

    async def execute(self, context: CommandContext) -> Result[str]:
        """Execute the command to create a session.

        Args:
            context: Command execution context with session_repo.

        Returns:
            Result[str]: Session ID on success, Err on failure.
        """
        try:
            # Use session_repo from context to create session
            session_repo = context.metadata.get("session_repo") if context.metadata else None
            if not session_repo:
                return Err("session_repo not in context", code="MISSING_DEPENDENCY")

            # Create session object
            from dawn_kestrel.core.models import Session

            session = Session(
                id=self.session_id,
                slug="session",
                project_id=context.metadata.get("project_id", "") if context.metadata else "",
                directory=context.metadata.get("project_dir", "") if context.metadata else "",
                title=self.title,
                version="1.0.0",
            )

            # Create session via repository
            result = await session_repo.create(session)

            # Return session_id on success
            if result.is_ok():
                return Ok(self.session_id)

            # Wrap repository errors
            return Err(f"Failed to create session: {result.error}", code="COMMAND_ERROR")

        except Exception as e:
            return Err(f"Failed to create session: {e}", code="COMMAND_ERROR")


class ExecuteToolCommand(BaseCommand):
    """Command to execute a tool.

    Uses tool_adapter from context to execute a tool with
    the provided arguments.
    """

    def __init__(self, tool_name: str, arguments: dict[str, Any]):
        """Initialize ExecuteToolCommand.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Arguments to pass to the tool.
        """
        super().__init__(
            name="execute_tool",
            description=f"Execute tool: {tool_name}",
        )
        self.tool_name = tool_name
        self.arguments = arguments

    async def execute(self, context: CommandContext) -> Result[dict[str, Any]]:
        """Execute the command to run a tool.

        Args:
            context: Command execution context with tool_adapter.

        Returns:
            Result[dict[str, Any]]: Tool result on success, Err on failure.
        """
        try:
            # Use tool_adapter from context to execute tool
            tool_adapter = context.metadata.get("tool_adapter") if context.metadata else None
            if not tool_adapter:
                return Err("tool_adapter not in context", code="MISSING_DEPENDENCY")

            # Execute tool via adapter with arguments
            result = await tool_adapter.execute(**self.arguments)

            return result

        except Exception as e:
            return Err(f"Failed to execute tool: {e}", code="COMMAND_ERROR")


class CommandQueue:
    """Queue for managing command execution with events.

    Commands are enqueued and processed sequentially, with events
    published for each phase of command execution.
    """

    def __init__(self, mediator: EventMediator):
        """Initialize CommandQueue.

        Args:
            mediator: EventMediator for publishing command events.
        """
        self._mediator = mediator
        self._queue: deque[Command] = deque()
        self._history: list[Command] = []

    async def enqueue(self, command: Command) -> Result[None]:
        """Add command to queue and publish enqueued event.

        Args:
            command: Command to enqueue.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        try:
            self._queue.append(command)
            self._history.append(command)

            event = Event(
                event_type=EventType.APPLICATION,
                source="command_queue",
                data={
                    "action": "command_enqueued",
                    "command": command.name,
                },
            )

            await self._mediator.publish(event)
            return Ok(None)

        except Exception as e:
            return Err(f"Failed to enqueue command: {e}", code="QUEUE_ERROR")

    async def process_next(self) -> Result[Any]:
        """Process next command from queue and publish events.

        Executes the next command in the queue, publishing
        command_started, command_completed, or command_failed events.

        Returns:
            Result[Any]: Command result on success, Err if queue empty.
        """
        if not self._queue:
            return Err("No commands in queue", code="QUEUE_EMPTY")

        command = self._queue.popleft()
        context = CommandContext(timestamp=datetime.now())

        # Publish execution started event
        await self._mediator.publish(
            Event(
                event_type=EventType.APPLICATION,
                source="command_queue",
                data={"action": "command_started", "command": command.name},
            )
        )

        # Execute command
        result = await command.execute(context)

        if result.is_ok():
            # Publish completion event
            await self._mediator.publish(
                Event(
                    event_type=EventType.APPLICATION,
                    source="command_queue",
                    data={"action": "command_completed", "command": command.name},
                )
            )
        else:
            # Publish error event
            await self._mediator.publish(
                Event(
                    event_type=EventType.APPLICATION,
                    source="command_queue",
                    data={
                        "action": "command_failed",
                        "command": command.name,
                        "error": str(result),
                    },
                )
            )

        return result
