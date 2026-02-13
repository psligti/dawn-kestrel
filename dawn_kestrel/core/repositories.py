"""Repository pattern implementation for session/message/part data access.

This module defines repository protocols and implementations that wrap the storage
layer and return Result types for explicit error handling without exceptions.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, List, Any

from dawn_kestrel.core.models import (
    Session,
    Message,
    Part,
    TextPart,
    FilePart,
    ToolPart,
    ReasoningPart,
    SnapshotPart,
    PatchPart,
    AgentPart,
    SubtaskPart,
    RetryPart,
    CompactionPart,
)
from dawn_kestrel.core.result import Ok, Err, Result
from dawn_kestrel.storage.store import SessionStorage, MessageStorage, PartStorage


def _dict_to_part(data: dict[str, Any]) -> Part:
    part_type = data.get("part_type")
    if part_type == "text":
        return TextPart(**data)
    elif part_type == "file":
        return FilePart(**data)
    elif part_type == "tool":
        return ToolPart(**data)
    elif part_type == "reasoning":
        return ReasoningPart(**data)
    elif part_type == "snapshot":
        return SnapshotPart(**data)
    elif part_type == "patch":
        return PatchPart(**data)
    elif part_type == "agent":
        return AgentPart(**data)
    elif part_type == "subtask":
        return SubtaskPart(**data)
    elif part_type == "retry":
        return RetryPart(**data)
    elif part_type == "compaction":
        return CompactionPart(**data)
    else:
        raise ValueError(f"Unknown part_type: {part_type}")


@runtime_checkable
class SessionRepository(Protocol):
    """Protocol for session data access.

    Repository pattern provides abstraction over storage with explicit error handling
    via Result types instead of raising exceptions.
    """

    async def get_by_id(self, session_id: str) -> Result[Session]:
        """Get session by ID.

        Returns:
            Result[Session]: Ok(session) if found, Err with error message if not found or error occurs.
        """
        ...

    async def create(self, session: Session) -> Result[Session]:
        """Create new session.

        Returns:
            Result[Session]: Ok(created_session) on success, Err with error message on failure.
        """
        ...

    async def update(self, session: Session) -> Result[Session]:
        """Update existing session.

        Returns:
            Result[Session]: Ok(updated_session) on success, Err with error message on failure.
        """
        ...

    async def delete(self, session_id: str) -> Result[bool]:
        """Delete session by ID.

        Returns:
            Result[bool]: Ok(True) if deleted, Ok(False) if not found, Err on failure.
        """
        ...

    async def list_by_project(self, project_id: str) -> Result[List[Session]]:
        """List all sessions for a project.

        Returns:
            Result[List[Session]]: Ok(list of sessions) on success, Err with error message on failure.
        """
        ...


@runtime_checkable
class MessageRepository(Protocol):
    """Protocol for message data access.

    Repository pattern provides abstraction over storage with explicit error handling
    via Result types instead of raising exceptions.
    """

    async def get_by_id(self, session_id: str, message_id: str) -> Result[Message]:
        """Get message by ID.

        Args:
            session_id: Session ID to search within.
            message_id: Message ID to retrieve.

        Returns:
            Result[Message]: Ok(message) if found, Err with error message if not found or error occurs.
        """
        ...

    async def create(self, message: Message) -> Result[Message]:
        """Create new message.

        Returns:
            Result[Message]: Ok(created_message) on success, Err with error message on failure.
        """
        ...

    async def list_by_session(self, session_id: str, reverse: bool = True) -> Result[List[Message]]:
        """List all messages for a session.

        Args:
            session_id: Session ID to retrieve messages for.
            reverse: Sort order (True = newest first, False = oldest first).

        Returns:
            Result[List[Message]]: Ok(list of messages) on success, Err with error message on failure.
        """
        ...


@runtime_checkable
class PartRepository(Protocol):
    """Protocol for part data access.

    Repository pattern provides abstraction over storage with explicit error handling
    via Result types instead of raising exceptions.
    """

    async def get_by_id(self, message_id: str, part_id: str) -> Result[Part]:
        """Get part by ID.

        Args:
            message_id: Message ID to search within.
            part_id: Part ID to retrieve.

        Returns:
            Result[Part]: Ok(part) if found, Err with error message if not found or error occurs.
        """
        ...

    async def create(self, message_id: str, part: Part) -> Result[Part]:
        """Create new part.

        Args:
            message_id: Message ID to associate the part with.
            part: Part to create.

        Returns:
            Result[Part]: Ok(created_part) on success, Err with error message on failure.
        """
        ...

    async def update(self, message_id: str, part: Part) -> Result[Part]:
        """Update existing part.

        Args:
            message_id: Message ID the part belongs to.
            part: Part to update.

        Returns:
            Result[Part]: Ok(updated_part) on success, Err with error message on failure.
        """
        ...

    async def list_by_message(self, message_id: str) -> Result[List[Part]]:
        """List all parts for a message.

        Args:
            message_id: Message ID to retrieve parts for.

        Returns:
            Result[List[Part]]: Ok(list of parts) on success, Err with error message on failure.
        """
        ...


class SessionRepositoryImpl:
    """Session repository implementation using SessionStorage.

    Wraps SessionStorage and returns Result types for explicit error handling.
    """

    def __init__(self, storage: SessionStorage, project_id: str):
        """Initialize repository with storage backend.

        Args:
            storage: SessionStorage instance to use for data persistence.
            project_id: Project ID for session operations.
        """
        self._storage = storage
        self._project_id = project_id

    async def get_by_id(self, session_id: str) -> Result[Session]:
        """Get session by ID."""
        try:
            session = await self._storage.get_session(session_id, self._project_id)
            if session is None:
                return Err(f"Session not found: {session_id}", code="NOT_FOUND")
            return Ok(session)
        except Exception as e:
            return Err(f"Failed to get session: {e}", code="STORAGE_ERROR")

    async def create(self, session: Session) -> Result[Session]:
        """Create new session."""
        try:
            created = await self._storage.create_session(session)
            return Ok(created)
        except Exception as e:
            return Err(f"Failed to create session: {e}", code="STORAGE_ERROR")

    async def update(self, session: Session) -> Result[Session]:
        """Update existing session."""
        try:
            updated = await self._storage.update_session(session)
            return Ok(updated)
        except Exception as e:
            return Err(f"Failed to update session: {e}", code="STORAGE_ERROR")

    async def delete(self, session_id: str) -> Result[bool]:
        """Delete session by ID."""
        try:
            deleted = await self._storage.delete_session(session_id, self._project_id)
            return Ok(deleted)
        except Exception as e:
            return Err(f"Failed to delete session: {e}", code="STORAGE_ERROR")

    async def list_by_project(self, project_id: str) -> Result[List[Session]]:
        """List all sessions for a project."""
        try:
            sessions = await self._storage.list_sessions(project_id)
            return Ok(sessions)
        except Exception as e:
            return Err(f"Failed to list sessions: {e}", code="STORAGE_ERROR")


class MessageRepositoryImpl:
    """Message repository implementation using MessageStorage.

    Wraps MessageStorage and returns Result types for explicit error handling.
    Note: MessageStorage returns Dict[str, Any] and must be converted to Message objects.
    """

    def __init__(self, storage: MessageStorage):
        """Initialize repository with storage backend.

        Args:
            storage: MessageStorage instance to use for data persistence.
        """
        self._storage = storage

    async def get_by_id(self, session_id: str, message_id: str) -> Result[Message]:
        """Get message by ID."""
        try:
            data = await self._storage.get_message(session_id, message_id)
            if data is None:
                return Err(f"Message not found: {message_id}", code="NOT_FOUND")
            # Convert Dict to Message object
            message = Message(**data)
            return Ok(message)
        except Exception as e:
            return Err(f"Failed to get message: {e}", code="STORAGE_ERROR")

    async def create(self, message: Message) -> Result[Message]:
        """Create new message."""
        try:
            created = await self._storage.create_message(message.session_id, message)
            return Ok(created)
        except Exception as e:
            return Err(f"Failed to create message: {e}", code="STORAGE_ERROR")

    async def list_by_session(self, session_id: str, reverse: bool = True) -> Result[List[Message]]:
        """List all messages for a session."""
        try:
            data_list = await self._storage.list_messages(session_id, reverse)
            # Convert List[Dict] to List[Message]
            messages = [Message(**data) for data in data_list]
            return Ok(messages)
        except Exception as e:
            return Err(f"Failed to list messages: {e}", code="STORAGE_ERROR")


class PartRepositoryImpl:
    """Part repository implementation using PartStorage.

    Wraps PartStorage and returns Result types for explicit error handling.
    Note: PartStorage returns Dict[str, Any] and must be converted to Part objects.
    """

    def __init__(self, storage: PartStorage):
        """Initialize repository with storage backend.

        Args:
            storage: PartStorage instance to use for data persistence.
        """
        self._storage = storage

    async def get_by_id(self, message_id: str, part_id: str) -> Result[Part]:
        """Get part by ID."""
        try:
            data = await self._storage.get_part(message_id, part_id)
            if data is None:
                return Err(f"Part not found: {part_id}", code="NOT_FOUND")
            part = _dict_to_part(data)
            return Ok(part)
        except Exception as e:
            return Err(f"Failed to get part: {e}", code="STORAGE_ERROR")

    async def create(self, message_id: str, part: Part) -> Result[Part]:
        """Create new part."""
        try:
            created = await self._storage.create_part(message_id, part)
            return Ok(created)
        except Exception as e:
            return Err(f"Failed to create part: {e}", code="STORAGE_ERROR")

    async def update(self, message_id: str, part: Part) -> Result[Part]:
        """Update existing part."""
        try:
            updated = await self._storage.update_part(message_id, part)
            return Ok(updated)
        except Exception as e:
            return Err(f"Failed to update part: {e}", code="STORAGE_ERROR")

    async def list_by_message(self, message_id: str) -> Result[List[Part]]:
        """List all parts for a message."""
        try:
            data_list = await self._storage.list_parts(message_id)
            parts = [_dict_to_part(data) for data in data_list]
            return Ok(parts)
        except Exception as e:
            return Err(f"Failed to list parts: {e}", code="STORAGE_ERROR")
