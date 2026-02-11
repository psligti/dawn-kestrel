"""FSM state repository protocol and implementation.

This module defines FSM state repository protocol and implementation that wraps
storage layer and returns Result types for explicit error handling.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dawn_kestrel.core.result import Ok, Err, Result
from dawn_kestrel.storage.store import SessionStorage


@runtime_checkable
class FSMStateRepository(Protocol):
    """Protocol for FSM state persistence.

    Repository pattern provides abstraction over storage with explicit error handling
    via Result types instead of raising exceptions. Only current state is persisted,
    not full state history.
    """

    async def get_state(self, fsm_id: str) -> Result[str]:
        """Get current state for FSM by ID.

        Args:
            fsm_id: Unique identifier for FSM instance.

        Returns:
            Result[str]: Ok(state) if found, Err with error message if not found or error occurs.
        """
        ...

    async def set_state(self, fsm_id: str, state: str) -> Result[None]:
        """Persist current state for FSM.

        Args:
            fsm_id: Unique identifier for FSM instance.
            state: Current state to persist.

        Returns:
            Result[None]: Ok on success, Err with error message on failure.
        """
        ...


class FSMStateRepositoryImpl:
    """FSM state repository implementation using SessionStorage.

    Wraps SessionStorage and returns Result types for explicit error handling.
    FSM states are stored under "fsm_state/{fsm_id}" keys.
    """

    def __init__(self, storage: SessionStorage):
        """Initialize repository with storage backend.

        Args:
            storage: SessionStorage instance to use for data persistence.
        """
        self._storage = storage

    async def get_state(self, fsm_id: str) -> Result[str]:
        """Get current state for FSM by ID."""
        try:
            # Use SessionStorage.read() to get FSM state
            key = ["fsm_state", fsm_id]
            data = await self._storage.read(key)
            if data is None:
                return Err(f"FSM state not found: {fsm_id}", code="NOT_FOUND")
            state = data.get("state")
            if state is None:
                return Err(f"Invalid FSM state data: {fsm_id}", code="INVALID_DATA")
            return Ok(state)
        except Exception as e:
            return Err(f"Failed to get FSM state: {e}", code="STORAGE_ERROR")

    async def set_state(self, fsm_id: str, state: str) -> Result[None]:
        """Persist current state for FSM."""
        try:
            # Use SessionStorage.write() to persist FSM state
            key = ["fsm_state", fsm_id]
            data = {"state": state}
            await self._storage.write(key, data)
            return Ok(None)
        except Exception as e:
            return Err(f"Failed to persist FSM state: {e}", code="STORAGE_ERROR")
