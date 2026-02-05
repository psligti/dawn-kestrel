"""Session service with handler injection.

This module provides session service protocol and default implementation
that uses SessionManager for core logic and injected handlers for I/O.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable, List, Dict, Any, Optional
import warnings

from opencode_python.storage.store import SessionStorage
from opencode_python.core.session import SessionManager
from opencode_python.core.models import Session, Message
from opencode_python.interfaces.io import (
    IOHandler,
    ProgressHandler,
    NotificationHandler,
    StateHandler,
    QuietIOHandler,
    NoOpProgressHandler,
    NoOpNotificationHandler,
    Notification,
    NotificationType,
)
from opencode_python.core.exceptions import (
    OpenCodeError,
    SessionError,
    IOHandlerError,
)


@runtime_checkable
class SessionService(Protocol):
    """Protocol for session service with handler injection.

    This protocol defines the interface for session operations that
    use injected handlers for I/O, progress, and notifications.
    """

    async def create_session(self, title: str) -> Session:
        """Create a new session.

        Args:
            title: The session title.

        Returns:
            The created Session object.

        Raises:
            SessionError: If session creation fails.
        """
        ...

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            SessionError: If deletion fails.
        """
        ...

    async def add_message(self, session_id: str, role: str, text: str) -> str:
        """Add a message to a session.

        Args:
            session_id: The session ID.
            role: The message role (user, assistant, system).
            text: The message text.

        Returns:
            The created message ID.

        Raises:
            SessionError: If adding message fails.
        """
        ...

    async def list_sessions(self) -> list[Session]:
        """List all sessions.

        Returns:
            List of Session objects.
        """
        ...

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: The session ID.

        Returns:
            Session object or None if not found.
        """
        ...

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: The session ID.

        Returns:
            Session object or None if not found.
        """
        ...


class DefaultSessionService:
    """Default implementation of SessionService with handler injection.

    This service wraps SessionManager and uses injected handlers for
    user interaction, progress tracking, and notifications.
    """

    def __init__(
        self,
        storage: SessionStorage,
        project_dir: Path | None = None,
        io_handler: IOHandler | None = None,
        progress_handler: ProgressHandler | None = None,
        notification_handler: NotificationHandler | None = None,
    ):
        """Initialize session service with handlers.

        Args:
            storage: SessionStorage instance for persistence.
            project_dir: Project directory path (optional, defaults to cwd).
            io_handler: Optional I/O handler for user interaction.
            progress_handler: Optional progress handler for operations.
            notification_handler: Optional notification handler for feedback.
        """
        self.storage = storage
        self.project_dir = project_dir or Path.cwd()

        if io_handler is None:
            warnings.warn(
                "io_handler is required in version 0.2.0. "
                "Pass QuietIOHandler() for headless mode. "
                "Direct I/O will be deprecated in Phase 4.",
                DeprecationWarning,
                stacklevel=2
            )
        if progress_handler is None:
            warnings.warn(
                "progress_handler is required in version 0.2.0. "
                "Pass NoOpProgressHandler() for silent mode. "
                "Direct progress will be deprecated in Phase 4.",
                DeprecationWarning,
                stacklevel=2
            )
        if notification_handler is None:
            warnings.warn(
                "notification_handler is required in version 0.2.0. "
                "Pass NoOpNotificationHandler() for silent mode. "
                "Direct notifications will be deprecated in Phase 4.",
                DeprecationWarning,
                stacklevel=2
            )

        self._io_handler = io_handler or QuietIOHandler()
        self._progress_handler = progress_handler or NoOpProgressHandler()
        self._notification_handler = notification_handler or NoOpNotificationHandler()

        self._manager = SessionManager(storage, self.project_dir)

    async def create_session(self, title: str) -> Session:
        """Create a new session using injected handlers.

        Args:
            title: The session title.

        Returns:
            The created Session object.

        Raises:
            SessionError: If session creation fails.
        """
        try:
            if self._io_handler:
                use_parent = await self._io_handler.confirm(
                    "Create this session as a child of an existing session?",
                    default=False
                )
            else:
                use_parent = False

            if self._progress_handler:
                self._progress_handler.start("Creating session", 100)
                self._progress_handler.update(50, "Initializing...")

            parent_id = None if not use_parent else ""
            session = await self._manager.create(title, parent_id=parent_id)

            if self._progress_handler:
                self._progress_handler.update(100, "Session created")
                self._progress_handler.complete(f"Created session: {session.title}")

            if self._notification_handler:
                self._notification_handler.show(Notification(
                    notification_type=NotificationType.SUCCESS,
                    message=f"Session created: {session.title}",
                ))

            return session

        except Exception as e:
            raise SessionError(f"Failed to create session: {e}") from e

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session using injected handlers.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            SessionError: If deletion fails.
        """
        try:
            if self._progress_handler:
                self._progress_handler.start("Deleting session", 100)
                self._progress_handler.update(50, f"Deleting {session_id}...")

            deleted = await self._manager.delete_session(session_id)

            if deleted:
                if self._progress_handler:
                    self._progress_handler.update(100, "Session deleted")
                    self._progress_handler.complete(f"Deleted session: {session_id}")

                if self._notification_handler:
                    self._notification_handler.show(Notification(
                        notification_type=NotificationType.SUCCESS,
                        message=f"Session {session_id} deleted",
                    ))

            return deleted

        except Exception as e:
            raise SessionError(f"Failed to delete session: {e}") from e

    async def add_message(self, session_id: str, role: str, text: str) -> str:
        """Add a message to a session using injected handlers.

        Args:
            session_id: The session ID.
            role: The message role (user, assistant, system).
            text: The message text.

        Returns:
            The created message ID.

        Raises:
            SessionError: If adding message fails.
        """
        try:
            if self._progress_handler:
                self._progress_handler.start("Adding message", 100)
                self._progress_handler.update(50, "Creating message...")

            message_id = await self._manager.add_message(
                Message(
                    id="",
                    session_id=session_id,
                    role=role,
                    time={"created": 0},
                    text=text,
                )
            )

            if self._progress_handler:
                self._progress_handler.update(100, "Message added")
                self._progress_handler.complete(f"Added message to session {session_id}")

            if self._notification_handler:
                self._notification_handler.show(Notification(
                    notification_type=NotificationType.SUCCESS,
                    message=f"Message added to session {session_id}",
                ))

            return message_id

        except Exception as e:
            raise SessionError(f"Failed to add message: {e}") from e

    async def list_sessions(self) -> list[Session]:
        """List all sessions.

        Returns:
            List of Session objects.
        """
        sessions = await self._manager.list_sessions()
        return sessions

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: The session ID.

        Returns:
            Session object or None if not found.
        """
        session = await self._manager.get_session(session_id)
        return session

    async def get_export_data(self, session_id: str) -> Dict[str, Any]:
        """Get session data for export.

        Args:
            session_id: The session ID.

        Returns:
            Dictionary with session and messages data.
        """
        # Start progress
        self._progress_handler.start("Exporting session", 100)
        self._progress_handler.update(50, f"Loading session {session_id}")

        # Get export data from manager
        export_data = await self._manager.get_export_data(session_id)

        # Complete progress
        self._progress_handler.update(100, "Export complete")
        self._progress_handler.complete("Session exported successfully")

        # Show notification
        self._notification_handler.show(
            Notification(
                notification_type=NotificationType.SUCCESS,
                message=f"Session {session_id} exported",
                details={"message_count": len(export_data.get("messages", []))},
            )
        )

        return export_data

    async def import_session(
        self, session_data: Dict[str, Any], project_id: str | None = None
    ) -> Session:
        """Import session data.

        Args:
            session_data: Dictionary with session and messages data.
            project_id: Optional project ID for multi-project repos.

        Returns:
            The imported Session object.
        """
        # Start progress
        self._progress_handler.start("Importing session", 100)
        self._progress_handler.update(50, "Processing session data")

        # Import data via manager
        session = await self._manager.import_data(session_data, project_id)

        # Complete progress
        self._progress_handler.update(100, "Import complete")
        self._progress_handler.complete("Session imported successfully")

        # Show notification
        self._notification_handler.show(
            Notification(
                notification_type=NotificationType.SUCCESS,
                message=f"Session {session.id} imported",
                details={"title": session.title},
            )
        )

        return session
