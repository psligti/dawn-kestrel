"""Agent Finite State Machine (FSM) for agent lifecycle management.

This module implements the State Machine pattern for managing agent lifecycle
states and transitions. The FSM ensures that agents only transition through
valid state changes, providing explicit lifecycle management.

Valid agent lifecycle states:
- idle: Agent waiting for task
- running: Agent processing task
- paused: Agent temporarily stopped (may resume)
- completed: Agent finished task successfully
- failed: Agent encountered error
- cancelled: Agent was cancelled by user

State Machine Design:
- Explicit state representation with immutable state values
- Valid transitions defined in VALID_TRANSITIONS
- All transitions return Result types (Ok/Err) for explicit error handling
- Protocol-based design enables multiple implementations

DEPRECATED:
    The AgentFSMImpl class is deprecated. Use Facade.create_fsm() instead.
    See Facade class for creating FSM instances.
"""

from __future__ import annotations

import warnings
from typing import Protocol, runtime_checkable

from dawn_kestrel.core.result import Result, Ok, Err


@runtime_checkable
class AgentFSM(Protocol):
    """Protocol for agent finite state machine.

    State machine manages agent lifecycle with valid transitions,
    ensuring agents only change state through approved paths.

    The protocol defines the interface for state management, allowing
    multiple implementations (in-memory, database-backed, etc.).
    """

    async def get_state(self) -> str:
        """Get current state of agent.

        Returns:
            str: Current state of the agent.
        """
        ...

    async def transition_to(self, new_state: str) -> Result[None]:
        """Transition agent to new state.

        Args:
            new_state: Target state to transition to.

        Returns:
            Result[None]: Ok on successful transition, Err if transition invalid.
        """
        ...

    async def is_transition_valid(self, from_state: str, to_state: str) -> bool:
        """Check if transition from one state to another is valid.

        Args:
            from_state: Current state of agent.
            to_state: Desired next state.

        Returns:
            bool: True if transition is valid, False otherwise.
        """
        ...


class AgentFSMImpl:
    """Agent finite state machine implementation.

    DEPRECATED: This class is deprecated. Use Facade.create_fsm() instead.
    See dawn_kestrel.core.facade.Facade for creating FSM instances.

    Manages agent lifecycle with explicit state transitions
    and validation to prevent invalid state changes.

    The FSM maintains an internal state and validates all transitions
    against the VALID_TRANSITIONS mapping. All transitions return
    Result types for explicit error handling without exceptions.

    Thread Safety:
        This implementation is NOT thread-safe. For concurrent access,
        use a thread-safe implementation with locks or consider a
        database-backed UnitOfWork pattern.

    Example:
        >>> fsm = AgentFSMImpl("idle")
        >>> await fsm.transition_to("running")
        Ok(None)
        >>> await fsm.get_state()
        'running'
    """

    # Define valid agent states
    VALID_STATES = {
        "idle",  # Agent waiting for task
        "running",  # Agent processing task
        "paused",  # Agent temporarily stopped
        "completed",  # Agent finished successfully
        "failed",  # Agent encountered error
        "cancelled",  # Agent was cancelled
    }

    # Define valid state transitions (from_state: set of valid to_states)
    VALID_TRANSITIONS: dict[str, set[str]] = {
        "idle": {"running", "cancelled"},
        "running": {"paused", "completed", "failed", "cancelled"},
        "paused": {"running", "cancelled"},
        "completed": {"idle"},  # Can restart after completion
        "failed": {"idle", "cancelled"},
        "cancelled": {"idle"},
    }

    def __init__(self, initial_state: str = "idle"):
        """Initialize FSM with starting state.

        Args:
            initial_state: Starting state (default: "idle").

        Raises:
            ValueError: If initial_state is not in VALID_STATES.
        """
        warnings.warn(
            "AgentFSMImpl is deprecated. Use Facade.create_fsm() instead. "
            "See dawn_kestrel.core.facade.Facade for creating FSM instances.",
            DeprecationWarning,
            stacklevel=2,
        )
        if initial_state not in self.VALID_STATES:
            raise ValueError(
                f"Invalid initial state: {initial_state}. "
                f"Valid states are: {sorted(self.VALID_STATES)}"
            )
        self._state = initial_state

    async def get_state(self) -> str:
        """Get current state of agent.

        Returns:
            str: Current state of the agent.
        """
        return self._state

    async def is_transition_valid(self, from_state: str, to_state: str) -> bool:
        """Check if transition from one state to another is valid.

        Args:
            from_state: Current state of agent.
            to_state: Desired next state.

        Returns:
            bool: True if transition is valid, False otherwise.
        """
        if from_state not in self.VALID_TRANSITIONS:
            return False
        return to_state in self.VALID_TRANSITIONS[from_state]

    async def transition_to(self, new_state: str) -> Result[None]:
        """Transition agent to new state.

        Args:
            new_state: Target state to transition to.

        Returns:
            Result[None]: Ok on successful transition, Err if transition invalid.

        Example:
            >>> fsm = AgentFSMImpl("idle")
            >>> result = await fsm.transition_to("running")
            >>> if result.is_ok():
            ...     print("Transition successful")
            Transition successful
        """
        # Validate transition
        if not await self.is_transition_valid(self._state, new_state):
            return Err(
                f"Invalid state transition: {self._state} -> {new_state}. "
                f"Valid transitions from {self._state}: {sorted(self.VALID_TRANSITIONS.get(self._state, set()))}",
                code="INVALID_TRANSITION",
            )

        # Apply transition
        self._state = new_state
        return Ok(None)


def create_agent_fsm(initial_state: str = "idle") -> AgentFSMImpl:
    """Factory function to create AgentFSM implementation.

    Args:
        initial_state: Starting state (default: "idle").

    Returns:
        AgentFSMImpl: New FSM instance with specified initial state.

    Raises:
        ValueError: If initial_state is not in VALID_STATES.

    Example:
        >>> fsm = create_agent_fsm("idle")
        >>> await fsm.transition_to("running")
        Ok(None)
    """
    return AgentFSMImpl(initial_state)
