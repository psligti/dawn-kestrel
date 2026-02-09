"""Session service with handler injection.

This module provides session service protocol and default implementation
that uses SessionManager for core logic and injected handlers for I/O.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable, List, Dict, Any, Optional
import warnings

from dawn_kestrel.storage.store import SessionStorage
from dawn_kestrel.core.session import SessionManager
from dawn_kestrel.core.models import Session, Message
from dawn_kestrel.core.repositories import (
    SessionRepository,
    MessageRepository,
    PartRepository,
    SessionRepositoryImpl,
    MessageRepositoryImpl,
    PartRepositoryImpl,
)
from dawn_kestrel.interfaces.io import (
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
from dawn_kestrel.core.exceptions import (
    OpenCodeError,
    SessionError,
    IOHandlerError,
)
from dawn_kestrel.core.result import Result, Ok, Err


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
        session_repo: SessionRepository | None = None,
        message_repo: MessageRepository | None = None,
        part_repo: PartRepository | None = None,
        storage: SessionStorage | None = None,  # Deprecated: for backward compatibility
        project_dir: Path | None = None,
        io_handler: IOHandler | None = None,
        progress_handler: ProgressHandler | None = None,
        notification_handler: NotificationHandler | None = None,
    ):
        """Initialize session service with handlers and repositories.

        Args:
            session_repo: SessionRepository instance for session data access.
            message_repo: MessageRepository instance for message data access.
            part_repo: Optional PartRepository instance for part data access.
            storage: SessionStorage instance for persistence (deprecated, use repositories).
            project_dir: Project directory path (optional, defaults to cwd).
            io_handler: Optional I/O handler for user interaction.
            progress_handler: Optional progress handler for operations.
            notification_handler: Optional notification handler for feedback.
        """
        if storage is not None:
            # Backward compatibility: create repositories from storage
            from dawn_kestrel.storage.store import SessionStorage, MessageStorage, PartStorage

            if isinstance(storage, SessionStorage):
                self._session_repo = SessionRepositoryImpl(storage)
                self._message_repo = MessageRepositoryImpl(MessageStorage(storage.base_dir))
                self._part_repo = PartRepositoryImpl(PartStorage(storage.base_dir))
                warnings.warn(
                    "Passing 'storage' is deprecated. Use 'session_repo', 'message_repo' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
        else:
            # Use provided repositories
            if session_repo is None or message_repo is None:
                raise ValueError(
                    "session_repo and message_repo are required (or provide storage for backward compatibility)"
                )
            self._session_repo = session_repo
            self._message_repo = message_repo
            self._part_repo = part_repo

        self.storage = storage  # Keep for backward compatibility
        self.project_dir = project_dir or Path.cwd()

        if io_handler is None:
            warnings.warn(
                "io_handler is required in version 0.2.0. "
                "Pass QuietIOHandler() for headless mode. "
                "Direct I/O will be deprecated in Phase 4.",
                DeprecationWarning,
                stacklevel=2,
            )
        if progress_handler is None:
            warnings.warn(
                "progress_handler is required in version 0.2.0. "
                "Pass NoOpProgressHandler() for silent mode. "
                "Direct progress will be deprecated in Phase 4.",
                DeprecationWarning,
                stacklevel=2,
            )
        if notification_handler is None:
            warnings.warn(
                "notification_handler is required in version 0.2.0. "
                "Pass NoOpNotificationHandler() for silent mode. "
                "Direct notifications will be deprecated in Phase 4.",
                DeprecationWarning,
                stacklevel=2,
            )

        self._io_handler = io_handler or QuietIOHandler()
        self._progress_handler = progress_handler or NoOpProgressHandler()
        self._notification_handler = notification_handler or NoOpNotificationHandler()

        # Keep SessionManager for backward compatibility (will be removed in future)
        if storage is not None:
            self._manager = SessionManager(storage, self.project_dir)
        else:
            # Create a mock storage for SessionManager compatibility
            # Note: This will be deprecated in future versions
            self._manager = None

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
                    "Create this session as a child of an existing session?", default=False
                )
            else:
                use_parent = False

            if self._progress_handler:
                self._progress_handler.start("Creating session", 100)
                self._progress_handler.update(50, "Initializing...")

            # Generate session ID and slug
            import uuid
            import re

            session_id = str(uuid.uuid4())
            slug = re.sub(r"\s+", "-", title.lower().replace(" ", "-"))
            slug = re.sub(r"[^a-z0-9_-]", "", slug)[:100]

            # Create session using repository
            from datetime import datetime

            now = datetime.now().timestamp()
            session = Session(
                id=session_id,
                slug=slug,
                project_id=self.project_dir.name,
                directory=str(self.project_dir),
                parent_id=None if not use_parent else "",
                title=title,
                version="1.0.0",
                summary=None,
                time_created=now,
                time_updated=now,
            )

            result = await self._session_repo.create(session)
            if result.is_err():
                raise SessionError(f"Failed to create session: {result.error}")

            session = result.unwrap()

            if self._progress_handler:
                self._progress_handler.update(100, "Session created")
                self._progress_handler.complete(f"Created session: {session.title}")

            if self._notification_handler:
                self._notification_handler.show(
                    Notification(
                        notification_type=NotificationType.SUCCESS,
                        message=f"Session created: {session.title}",
                    )
                )

            return session

        except Exception as e:
            raise SessionError(f"Failed to create session: {e}") from e

    async def create_session_result(self, title: str) -> Result[Session]:
        """Create a new session, returning Result.

        Args:
            title: The session title.

        Returns:
            Result with Session on success, or Err on failure.
        """
        try:
            if self._io_handler:
                use_parent = await self._io_handler.confirm(
                    "Create this session as a child of an existing session?", default=False
                )
            else:
                use_parent = False

            if self._progress_handler:
                self._progress_handler.start("Creating session", 100)
                self._progress_handler.update(50, "Initializing...")

            # Generate session ID and slug
            import uuid
            import re

            session_id = str(uuid.uuid4())
            slug = re.sub(r"\s+", "-", title.lower().replace(" ", "-"))
            slug = re.sub(r"[^a-z0-9_-]", "", slug)[:100]

            # Create session using repository
            from datetime import datetime

            now = datetime.now().timestamp()
            session = Session(
                id=session_id,
                slug=slug,
                project_id=self.project_dir.name,
                directory=str(self.project_dir),
                parent_id=None if not use_parent else "",
                title=title,
                version="1.0.0",
                summary=None,
                time_created=now,
                time_updated=now,
            )

            result = await self._session_repo.create(session)
            if result.is_err():
                return Err(f"Failed to create session: {result.error}")

            session = result.unwrap()

            if self._progress_handler:
                self._progress_handler.update(100, "Session created")
                self._progress_handler.complete(f"Created session: {session.title}")

            if self._notification_handler:
                self._notification_handler.show(
                    Notification(
                        notification_type=NotificationType.SUCCESS,
                        message=f"Session created: {session.title}",
                    )
                )

            return Ok(session)

        except Exception as e:
            return Err(f"Failed to create session: {e}", code="SessionError")

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

            result = await self._session_repo.delete(session_id)
            if result.is_err():
                raise SessionError(f"Failed to delete session: {result.error}")

            deleted = result.unwrap()

            if deleted:
                if self._progress_handler:
                    self._progress_handler.update(100, "Session deleted")
                    self._progress_handler.complete(f"Deleted session: {session_id}")

                if self._notification_handler:
                    self._notification_handler.show(
                        Notification(
                            notification_type=NotificationType.SUCCESS,
                            message=f"Session {session_id} deleted",
                        )
                    )

            return deleted

        except Exception as e:
            raise SessionError(f"Failed to delete session: {e}") from e

    async def delete_session_result(self, session_id: str) -> Result[bool]:
        """Delete a session by ID, returning Result.

        Args:
            session_id: The session ID to delete.

        Returns:
            Result with bool (True if deleted, False if not found) on success,
            or Err on failure.
        """
        try:
            if self._progress_handler:
                self._progress_handler.start("Deleting session", 100)
                self._progress_handler.update(50, f"Deleting {session_id}...")

            result = await self._session_repo.delete(session_id)
            if result.is_err():
                return Err(f"Failed to delete session: {result.error}")

            deleted = result.unwrap()

            if deleted:
                if self._progress_handler:
                    self._progress_handler.update(100, "Session deleted")
                    self._progress_handler.complete(f"Deleted session: {session_id}")

                if self._notification_handler:
                    self._notification_handler.show(
                        Notification(
                            notification_type=NotificationType.SUCCESS,
                            message=f"Session {session_id} deleted",
                        )
                    )

            return Ok(deleted)

        except Exception as e:
            return Err(f"Failed to delete session: {e}", code="SessionError")

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

            # Generate message ID
            import uuid
            from datetime import datetime

            message_id = str(uuid.uuid4())
            now = datetime.now().timestamp()

            # Create message
            message = Message(
                id=message_id,
                session_id=session_id,
                role=role,  # type: ignore
                time={"created": now},
                text=text,
            )

            # Use message repository
            result = await self._message_repo.create(message)
            if result.is_err():
                raise SessionError(f"Failed to add message: {result.error}")

            created_message = result.unwrap()

            if self._progress_handler:
                self._progress_handler.update(100, "Message added")
                self._progress_handler.complete(f"Added message to session {session_id}")

            if self._notification_handler:
                self._notification_handler.show(
                    Notification(
                        notification_type=NotificationType.SUCCESS,
                        message=f"Message added to session {session_id}",
                    )
                )

            return created_message.id

        except Exception as e:
            raise SessionError(f"Failed to add message: {e}") from e

    async def add_message_result(self, session_id: str, role: str, text: str) -> Result[str]:
        """Add a message to a session, returning Result.

        Args:
            session_id: The session ID.
            role: The message role (user, assistant, system).
            text: The message text.

        Returns:
            Result with message ID on success, or Err on failure.
        """
        try:
            if self._progress_handler:
                self._progress_handler.start("Adding message", 100)
                self._progress_handler.update(50, "Creating message...")

            # Generate message ID
            import uuid
            from datetime import datetime

            message_id = str(uuid.uuid4())
            now = datetime.now().timestamp()

            # Create message
            message = Message(
                id=message_id,
                session_id=session_id,
                role=role,  # type: ignore
                time={"created": now},
                text=text,
            )

            # Use message repository
            result = await self._message_repo.create(message)
            if result.is_err():
                return Err(f"Failed to add message: {result.error}")

            created_message = result.unwrap()

            if self._progress_handler:
                self._progress_handler.update(100, "Message added")
                self._progress_handler.complete(f"Added message to session {session_id}")

            if self._notification_handler:
                self._notification_handler.show(
                    Notification(
                        notification_type=NotificationType.SUCCESS,
                        message=f"Message added to session {session_id}",
                    )
                )

            return Ok(created_message.id)

        except Exception as e:
            return Err(f"Failed to add message: {e}", code="SessionError")

    async def list_sessions(self) -> list[Session]:
        """List all sessions.

        Returns:
            List of Session objects.
        """
        # Fall back to SessionManager if available (backward compatibility)
        if self._manager is not None:
            sessions = await self._manager.list_sessions()
        else:
            # Use repository
            result = await self._session_repo.list_by_project(self.project_dir.name)
            if result.is_err():
                raise SessionError(f"Failed to list sessions: {result.error}")
            sessions = result.unwrap()
        return sessions

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: The session ID.

        Returns:
            Session object or None if not found.
        """
        # Fall back to SessionManager if available (backward compatibility)
        if self._manager is not None:
            session = await self._manager.get_session(session_id)
        else:
            # Use repository
            result = await self._session_repo.get_by_id(session_id)
            if result.is_err():
                return None
            session = result.unwrap()
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

        # Fall back to SessionManager if available (backward compatibility)
        if self._manager is not None:
            export_data = await self._manager.get_export_data(session_id)
        else:
            # Use repositories
            # Get session
            session_result = await self._session_repo.get_by_id(session_id)
            if session_result.is_err():
                raise SessionError(f"Session not found: {session_id}")
            session = session_result.unwrap()

            # Get all messages
            messages_result = await self._message_repo.list_by_session(session_id, reverse=True)
            if messages_result.is_err():
                raise SessionError(f"Failed to list messages: {messages_result.error}")
            messages = messages_result.unwrap()

            # Build export data
            export_data = {
                "session": session.model_dump(mode="json"),
                "messages": [msg.model_dump(mode="json", exclude_none=True) for msg in messages],
            }

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

        # Fall back to SessionManager if available (backward compatibility)
        if self._manager is not None:
            session = await self._manager.import_data(session_data, project_id)
        else:
            # Use repositories
            session_dict = session_data.get("session", {})
            messages_data = session_data.get("messages", [])

            # Validate required fields
            if not session_dict.get("id") or not session_dict.get("title"):
                raise ValueError("Session data missing required fields: id, title")

            # Create or update session
            existing_result = await self._session_repo.get_by_id(session_dict["id"])
            from datetime import datetime

            if existing_result.is_ok():
                # Update existing session
                session = existing_result.unwrap()
                session.title = session_dict.get("title", session.title)
                session.summary = session_dict.get("summary", session.summary)
                session.time_updated = datetime.now().timestamp()
                result = await self._session_repo.update(session)
                if result.is_err():
                    raise SessionError(f"Failed to update session: {result.error}")
                session = result.unwrap()
            else:
                # Create new session
                import uuid
                import re

                now = datetime.now().timestamp()
                title = session_dict.get("title", "Imported Session")
                slug = re.sub(r"\s+", "-", title.lower().replace(" ", "-"))
                slug = re.sub(r"[^a-z0-9_-]", "", slug)[:100]

                session = Session(
                    id=session_dict["id"],
                    slug=slug,
                    project_id=project_id or self.project_dir.name,
                    directory=str(self.project_dir),
                    parent_id=session_dict.get("parent_id"),
                    title=title,
                    version=session_dict.get("version", "1.0.0"),
                    summary=session_dict.get("summary"),
                    time_created=now,
                    time_updated=now,
                )
                result = await self._session_repo.create(session)
                if result.is_err():
                    raise SessionError(f"Failed to create session: {result.error}")
                session = result.unwrap()

            # Import messages
            for msg_data in messages_data:
                message = Message(**msg_data)
                message.session_id = session.id
                result = await self._message_repo.create(message)
                if result.is_err():
                    # Continue with other messages if one fails
                    pass

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
