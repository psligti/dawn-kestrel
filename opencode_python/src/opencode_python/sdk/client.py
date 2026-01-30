"""SDK clients for OpenCode Python

This module provides async and sync client implementations
that wrap SessionService with handler injection and callbacks.
"""

from __future__ import annotations

from typing import Optional, Callable, Any
from pathlib import Path
import asyncio

from opencode_python.core.config import SDKConfig
from opencode_python.core.services.session_service import SessionService, DefaultSessionService
from opencode_python.storage.store import SessionStorage
from opencode_python.core.models import Session
from opencode_python.interfaces.io import Notification, NotificationType
from opencode_python.core.exceptions import OpenCodeError


class OpenCodeAsyncClient:
    """Async client for OpenCode SDK with handler injection.

    This client provides async methods for session and message operations,
    using injected handlers for I/O, progress, and notifications.

    Attributes:
        config: SDKConfig instance for client configuration.
        _service: SessionService instance for core operations.
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

        storage = SessionStorage()
        project_dir = self.config.project_dir or Path.cwd()

        self._service = DefaultSessionService(
            storage=storage,
            project_dir=project_dir,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
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
