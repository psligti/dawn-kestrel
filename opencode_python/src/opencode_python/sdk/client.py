"""SDK clients for OpenCode Python

This module provides async and sync client implementations
that wrap SessionService with handler injection and callbacks.
"""

from __future__ import annotations

from typing import Optional, Callable, Any, Dict
from pathlib import Path
import asyncio

from opencode_python.core.config import SDKConfig
from opencode_python.core.services.session_service import DefaultSessionService
from opencode_python.storage.store import SessionStorage
from opencode_python.core.models import Session
from opencode_python.interfaces.io import Notification
from opencode_python.core.exceptions import OpenCodeError, SessionError
from opencode_python.core.settings import get_storage_dir
from opencode_python.agents.runtime import create_agent_runtime
from opencode_python.core.agent_types import AgentResult
from opencode_python.agents.registry import create_agent_registry
from opencode_python.tools import create_builtin_registry


class OpenCodeAsyncClient:
    """Async client for OpenCode SDK with handler injection.

    This client provides async methods for session and message operations,
    using injected handlers for I/O, progress, and notifications.

    Attributes:
        config: SDKConfig instance for client configuration.
        _service: SessionService instance for core operations.
        _runtime: AgentRuntime instance for agent execution.
        _on_progress: Optional callback for progress updates.
        _on_notification: Optional callback for notifications.
    """

    def __init__(
        self,
        config: Optional[SDKConfig] = None,
        io_handler: Optional[Any] = None,
        progress_handler: Optional[Any] = None,
        notification_handler: Optional[Any] = None,
    ):
        """Initialize async SDK client.

        Args:
            config: Optional SDKConfig for configuration.
            io_handler: Optional I/O handler for user interaction.
            progress_handler: Optional progress handler for operations.
            notification_handler: Optional notification handler for feedback.
        """
        self.config = config or SDKConfig()
        self._on_progress: Optional[Callable[[int, Optional[str]], None]] = None
        self._on_notification: Optional[Callable[[Notification], None]] = None

        storage_dir = self.config.storage_path or get_storage_dir()
        storage = SessionStorage(storage_dir)
        project_dir = self.config.project_dir or Path.cwd()

        self._service = DefaultSessionService(
            storage=storage,
            project_dir=project_dir,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        agent_registry = create_agent_registry(
            persistence_enabled=False,
            storage_dir=storage_dir,
        )
        self._runtime = create_agent_runtime(
            agent_registry=agent_registry,
            base_dir=project_dir,
        )

    def on_progress(self, callback: Optional[Callable[[int, Optional[str]], None]]) -> None:
        """Register progress callback.

        Args:
            callback: Callback function called with (current, message) during operations.
        """
        self._on_progress = callback

    def on_notification(self, callback: Optional[Callable[[Notification], None]]) -> None:
        """Register notification callback.

        Args:
            callback: Callback function called with Notification when events occur.
        """
        self._on_notification = callback

    async def create_session(
        self,
        title: str,
        version: str = "1.0.0",
    ) -> Session:
        """Create a new session.

        Args:
            title: Session title.
            version: Session version.

        Returns:
            Created Session object.

        Raises:
            SessionError: If session creation fails.
        """
        try:
            session = await self._service.create_session(title)
            return session
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to create session: {e}") from e

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.

        Args:
            session_id: Session ID to retrieve.

        Returns:
            Session object or None if not found.

        Raises:
            SessionError: If retrieval fails.
        """
        try:
            session = await self._service.get_session(session_id)
            return session
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to get session: {e}") from e

    async def list_sessions(self) -> list[Session]:
        """List all sessions.

        Returns:
            List of Session objects.

        Raises:
            SessionError: If listing fails.
        """
        try:
            sessions = await self._service.list_sessions()
            return sessions
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to list sessions: {e}") from e

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: Session ID to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            SessionError: If deletion fails.
        """
        try:
            deleted = await self._service.delete_session(session_id)
            return deleted
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to delete session: {e}") from e

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> str:
        """Add a message to a session.

        Args:
            session_id: Session ID.
            role: Message role (user, assistant, system).
            content: Message content.

        Returns:
            Created message ID.

        Raises:
            SessionError: If adding message fails.
        """
        try:
            message_id = await self._service.add_message(session_id, role, content)
            return message_id
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to add message: {e}") from e

    async def register_agent(self, agent: Any) -> Any:
        """Register a custom agent.

        Args:
            agent: Agent to register (Agent dataclass or dict with name, description, etc.)

        Returns:
            Registered agent

        Raises:
            ValueError: If agent with same name already exists
            SessionError: If registration fails

        Example:
            >>> custom_agent = Agent(
            ...     name="reviewer",
            ...     description="Code review agent",
            ...     mode="subagent",
            ...     permission=[{"permission": "*", "pattern": "*", "action": "allow"}]
            ... )
            >>> await client.register_agent(custom_agent)
        """
        try:
            return await self._runtime.agent_registry.register_agent(agent)
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise SessionError(f"Failed to register agent: {e}") from e

    async def get_agent(self, name: str) -> Optional[Any]:
        """Get an agent by name.

        Args:
            name: Agent name (case-insensitive)

        Returns:
            Agent if found, None otherwise

        Example:
            >>> agent = await client.get_agent("build")
            >>> if agent:
            ...     print(f"Found: {agent.description}")
        """
        try:
            return self._runtime.agent_registry.get_agent(name)
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise SessionError(f"Failed to get agent: {e}") from e

    async def execute_agent(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Execute an agent for a user message.

        Args:
            agent_name: Name of agent to execute (e.g., "build", "plan", "explore")
            session_id: Session ID to execute in
            user_message: User's message or request
            options: Optional execution parameters:
                - skills: List[str] - Skill names to inject into system prompt
                - provider: str - Provider ID ("anthropic", "openai")
                - model: str - Model ID (overrides agent default)

        Returns:
            AgentResult with response text, parts, metadata, tools used, duration, error

        Raises:
            ValueError: If agent not found, session not found, or missing required data
            SessionError: If execution fails

        Example:
            >>> result = await client.execute_agent(
            ...     agent_name="build",
            ...     session_id="ses_123",
            ...     user_message="Create a new user model"
            ... )
            >>> print(f"Response: {result.response}")
            >>> print(f"Tools used: {result.tools_used}")
        """
        options = options or {}

        skills = options.get("skills", [])
        tools = create_builtin_registry()

        try:
            return await self._runtime.execute_agent(
                agent_name=agent_name,
                session_id=session_id,
                user_message=user_message,
                session_manager=self._service,
                tools=tools,
                skills=skills,
                options=options,
            )
        except ValueError:
            raise
        except Exception as e:
            raise SessionError(f"Failed to execute agent: {e}") from e


class OpenCodeSyncClient:
    """Sync client for OpenCode SDK.

    This client provides sync methods that wrap async client operations.
    Trade-off: Simpler API for synchronous code, but blocks event loop.

    Attributes:
        _async_client: OpenCodeAsyncClient instance for actual operations.
    """

    def __init__(
        self,
        config: Optional[SDKConfig] = None,
        io_handler: Optional[Any] = None,
        progress_handler: Optional[Any] = None,
        notification_handler: Optional[Any] = None,
    ):
        """Initialize sync SDK client.

        Args:
            config: Optional SDKConfig for configuration.
            io_handler: Optional I/O handler for user interaction.
            progress_handler: Optional progress handler for operations.
            notification_handler: Optional notification handler for feedback.

        Note:
            This client runs async operations synchronously using asyncio.run().
            Consider using OpenCodeAsyncClient for async codebases.
        """
        self._async_client = OpenCodeAsyncClient(
            config=config,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

    def on_progress(self, callback: Optional[Callable[[int, Optional[str]], None]]) -> None:
        """Register progress callback.

        Args:
            callback: Callback function called with (current, message) during operations.
        """
        self._async_client.on_progress(callback)

    def on_notification(self, callback: Optional[Callable[[Notification], None]]) -> None:
        """Register notification callback.

        Args:
            callback: Callback function called with Notification when events occur.
        """
        self._async_client.on_notification(callback)

    def create_session(self, title: str, version: str = "1.0.0") -> Session:
        """Create a new session (sync).

        Args:
            title: Session title.
            version: Session version.

        Returns:
            Created Session object.

        Raises:
            SessionError: If session creation fails.

        Note:
            Blocks event loop. Consider async client for non-blocking operations.
        """
        return asyncio.run(self._async_client.create_session(title, version))

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID (sync).

        Args:
            session_id: Session ID to retrieve.

        Returns:
            Session object or None if not found.

        Raises:
            SessionError: If retrieval fails.

        Note:
            Blocks event loop. Consider async client for non-blocking operations.
        """
        return asyncio.run(self._async_client.get_session(session_id))

    def list_sessions(self) -> list[Session]:
        """List all sessions (sync).

        Returns:
            List of Session objects.

        Raises:
            SessionError: If listing fails.

        Note:
            Blocks event loop. Consider async client for non-blocking operations.
        """
        return asyncio.run(self._async_client.list_sessions())

    def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID (sync).

        Args:
            session_id: Session ID to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            SessionError: If deletion fails.

        Note:
            Blocks event loop. Consider async client for non-blocking operations.
        """
        return asyncio.run(self._async_client.delete_session(session_id))

    def add_message(self, session_id: str, role: str, content: str) -> str:
        """Add a message to a session (sync).

        Args:
            session_id: Session ID.
            role: Message role (user, assistant, system).
            content: Message content.

        Returns:
            Created message ID.

        Raises:
            SessionError: If adding message fails.

        Note:
            Blocks event loop. Consider async client for non-blocking operations.
        """
        return asyncio.run(self._async_client.add_message(session_id, role, content))
    def register_agent(self, agent: Any) -> Any:
        """Register a custom agent (sync)."""
        return asyncio.run(self._async_client.register_agent(agent))

    def get_agent(self, name: str) -> Optional[Any]:
        """Get an agent by name (sync)."""
        return asyncio.run(self._async_client.get_agent(name))

    def execute_agent(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Execute an agent for a user message (sync)."""
        return asyncio.run(self._async_client.execute_agent(agent_name, session_id, user_message, options))

