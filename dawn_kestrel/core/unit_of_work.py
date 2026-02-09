"""Unit of Work pattern for transactional consistency.

This module defines the UnitOfWork protocol and implementation for managing
transactions across multiple repositories. The Unit of Work pattern ensures
that multi-write operations are either all succeed or all fail, maintaining
data consistency.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dawn_kestrel.core.models import Session, Message, Part
from dawn_kestrel.core.result import Ok, Err, Result


@runtime_checkable
class UnitOfWork(Protocol):
    """Protocol for transactional consistency across repositories.

    Unit of Work pattern ensures that multi-write operations are
    either all succeed or all fail, maintaining data consistency.

    This protocol enables runtime type checking and supports multiple
    implementations (e.g., in-memory, database, distributed).
    """

    async def begin(self) -> Result[None]:
        """Begin a new transaction.

        Starts a new transaction context for tracking pending operations.
        Any entities registered after begin() will be part of this transaction.

        Returns:
            Result[None]: Ok(None) on success, Err if transaction already in progress.
        """
        ...

    async def commit(self) -> Result[None]:
        """Commit all pending changes.

        Atomically commits all registered entities to their respective repositories.
        If any repository operation fails, the commit is aborted and the error is returned.

        Returns:
            Result[None]: Ok(None) on success, Err if no transaction in progress or commit fails.
        """
        ...

    async def rollback(self) -> Result[None]:
        """Rollback all pending changes.

        Clears all pending operations without modifying any repositories.
        This is an in-memory operation and does not affect persisted data.

        Returns:
            Result[None]: Ok(None) on success, Err if no transaction in progress.
        """
        ...

    async def register_session(self, session: Session) -> Result[Session]:
        """Register session for creation/update in transaction.

        Adds the session to the pending list for commit. The session will be
        created when commit() is called.

        Args:
            session: Session entity to register.

        Returns:
            Result[Session]: Ok(session) on success, Err if no transaction in progress.
        """
        ...

    async def register_message(self, message: Message) -> Result[Message]:
        """Register message for creation in transaction.

        Adds the message to the pending list for commit. The message will be
        created when commit() is called.

        Args:
            message: Message entity to register.

        Returns:
            Result[Message]: Ok(message) on success, Err if no transaction in progress.
        """
        ...

    async def register_part(self, message_id: str, part: Part) -> Result[Part]:
        """Register part for creation in transaction.

        Adds the part to the pending list for commit. The part will be created
        when commit() is called.

        Args:
            message_id: ID of the message this part belongs to.
            part: Part entity to register.

        Returns:
            Result[Part]: Ok(part) on success, Err if no transaction in progress.
        """
        ...


class UnitOfWorkImpl:
    """Unit of Work implementation using repositories.

    Tracks pending operations and commits/rolls back as atomic unit.
    Uses simple in-memory tracking (suitable for single-process use).

    This implementation provides transactional semantics by collecting entities
    in memory and applying all changes atomically during commit. If any
    repository operation fails during commit, the entire transaction fails
    and no partial changes are persisted.

    Thread Safety:
        This implementation is not thread-safe. For concurrent access, use
        synchronization primitives or a thread-safe implementation.

    Example:
        ```python
        async def create_session_with_message(uow: UnitOfWork):
            await uow.begin()
            await uow.register_session(session)
            await uow.register_message(message)
            result = await uow.commit()
            if result.is_err():
                await uow.rollback()
            return result
        ```
    """

    def __init__(
        self,
        session_repo: Any,
        message_repo: Any,
        part_repo: Any,
    ):
        """Initialize UnitOfWork with repositories.

        Args:
            session_repo: SessionRepository for session operations.
            message_repo: MessageRepository for message operations.
            part_repo: PartRepository for part operations.
        """
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._part_repo = part_repo
        self._in_transaction = False
        self._pending_sessions: list[Session] = []
        self._pending_messages: list[Message] = []
        self._pending_parts: list[tuple[str, Part]] = []  # (message_id, part)

    async def begin(self) -> Result[None]:
        """Begin a new transaction."""
        if self._in_transaction:
            return Err("Transaction already in progress", code="TRANSACTION_ERROR")

        self._in_transaction = True
        self._pending_sessions.clear()
        self._pending_messages.clear()
        self._pending_parts.clear()
        return Ok(None)

    async def commit(self) -> Result[None]:
        """Commit all pending changes."""
        if not self._in_transaction:
            return Err("No transaction in progress", code="TRANSACTION_ERROR")

        # Commit all pending entities
        for session in self._pending_sessions:
            result = await self._session_repo.create(session)
            if result.is_err():
                return result

        for message in self._pending_messages:
            result = await self._message_repo.create(message)
            if result.is_err():
                return result

        for message_id, part in self._pending_parts:
            result = await self._part_repo.create(message_id, part)
            if result.is_err():
                return result

        # Clear pending state
        self._in_transaction = False
        self._pending_sessions.clear()
        self._pending_messages.clear()
        self._pending_parts.clear()
        return Ok(None)

    async def rollback(self) -> Result[None]:
        """Rollback all pending changes."""
        if not self._in_transaction:
            return Err("No transaction in progress", code="TRANSACTION_ERROR")

        # Just clear pending state (in-memory tracking)
        self._in_transaction = False
        self._pending_sessions.clear()
        self._pending_messages.clear()
        self._pending_parts.clear()
        return Ok(None)

    async def register_session(self, session: Session) -> Result[Session]:
        """Register session for creation."""
        if not self._in_transaction:
            return Err("No transaction in progress", code="TRANSACTION_ERROR")

        self._pending_sessions.append(session)
        return Ok(session)

    async def register_message(self, message: Message) -> Result[Message]:
        """Register message for creation."""
        if not self._in_transaction:
            return Err("No transaction in progress", code="TRANSACTION_ERROR")

        self._pending_messages.append(message)
        return Ok(message)

    async def register_part(self, message_id: str, part: Part) -> Result[Part]:
        """Register part for creation."""
        if not self._in_transaction:
            return Err("No transaction in progress", code="TRANSACTION_ERROR")

        self._pending_parts.append((message_id, part))
        return Ok(part)


# Note: SessionRepository, MessageRepository, PartRepository protocols are defined
# in dawn_kestrel.core.repositories. We reference them here for type checking.
# The actual implementations are passed to UnitOfWorkImpl at runtime.
