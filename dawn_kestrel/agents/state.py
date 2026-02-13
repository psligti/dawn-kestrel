"""State pattern implementation for agent lifecycle management.

This module provides AgentState enum and AgentStateMachine for managing
agent lifecycle transitions with explicit validation.
"""

from enum import Enum
from typing import Dict, Optional

from dawn_kestrel.core.result import Err, Ok, Result


class AgentState(Enum):
    """Agent lifecycle states.

    States represent the lifecycle phases of an agent during review execution:
    - IDLE: Agent is initialized but not yet started
    - INITIALIZING: Agent is setting up internal state
    - READY: Agent is ready to start processing
    - RUNNING: Agent is actively processing work
    - PAUSED: Agent execution is paused (can be resumed)
    - COMPLETED: Agent finished successfully
    - FAILED: Agent encountered an error

    Enum values are lowercase strings for consistency with dawn-kestrel conventions.
    """

    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# Default transition map: defines valid state transitions for a generic agent
# Individual agents can provide custom transition maps
FSM_TRANSITIONS: Dict[AgentState, set[AgentState]] = {
    AgentState.IDLE: {AgentState.INITIALIZING},
    AgentState.INITIALIZING: {AgentState.READY, AgentState.FAILED},
    AgentState.READY: {AgentState.RUNNING, AgentState.FAILED},
    AgentState.RUNNING: {AgentState.PAUSED, AgentState.COMPLETED, AgentState.FAILED},
    AgentState.PAUSED: {AgentState.RUNNING, AgentState.COMPLETED, AgentState.FAILED},
    AgentState.COMPLETED: set(),  # Terminal state
    AgentState.FAILED: set(),  # Terminal state
}


class AgentStateMachine:
    """Finite state machine for agent lifecycle management.

    Manages state transitions with validation against a transition map.
    Uses Result pattern for explicit error handling of invalid transitions.

    Attributes:
        current_state: The current AgentState of the machine.
        transitions: Transition map defining valid state changes.

    Example:
        >>> fsm = AgentStateMachine()
        >>> fsm.current_state
        <AgentState.IDLE: 'idle'>
        >>> result = fsm.transition_to(AgentState.INITIALIZING)
        >>> result.is_ok()
        True
        >>> fsm.current_state
        <AgentState.INITIALIZING: 'initializing'>
    """

    def __init__(self, transitions: Optional[Dict[AgentState, set[AgentState]]] = None):
        """Initialize state machine with IDLE as default state.

        Args:
            transitions: Optional custom transition map. Defaults to FSM_TRANSITIONS.
        """
        self._current_state = AgentState.IDLE
        self._transitions = transitions if transitions is not None else FSM_TRANSITIONS

    @property
    def current_state(self) -> AgentState:
        """Get the current state (read-only)."""
        return self._current_state

    @property
    def transitions(self) -> Dict[AgentState, set[AgentState]]:
        """Get the transition map (read-only)."""
        return self._transitions

    def transition_to(self, next_state: AgentState) -> Result[AgentState]:
        """Attempt to transition to a new state.

        Validates the transition against the transition map. Returns:
        - Ok(next_state): Transition was successful, state changed
        - Err(error): Invalid transition, state unchanged

        Args:
            next_state: The target state to transition to.

        Returns:
            Result[AgentState]: Ok with new state, or Err with error message.

        Example:
            >>> fsm = AgentStateMachine()
            >>> result = fsm.transition_to(AgentState.INITIALIZING)
            >>> result.is_ok()
            True
            >>> bad_result = fsm.transition_to(AgentState.COMPLETED)
            >>> bad_result.is_err()
            True
        """
        if self._is_valid_transition(self._current_state, next_state):
            self._current_state = next_state
            return Ok(next_state)

        error_msg = (
            f"Invalid transition: {self._current_state.value} -> {next_state.value}. "
            f"Valid transitions from {self._current_state.value}: "
            f"{[s.value for s in self._transitions.get(self._current_state, set())]}"
        )
        return Err(error=error_msg, code="INVALID_TRANSITION")

    def _is_valid_transition(self, from_state: AgentState, to_state: AgentState) -> bool:
        """Check if a transition is valid according to the transition map.

        Args:
            from_state: Source state.
            to_state: Target state.

        Returns:
            True if transition is valid, False otherwise.
        """
        valid_targets = self._transitions.get(from_state, set())
        return to_state in valid_targets

    def can_transition_to(self, next_state: AgentState) -> bool:
        """Check if a transition would be valid without changing state.

        Useful for preflight validation or UI state checking.

        Args:
            next_state: The target state to check.

        Returns:
            True if transition would be valid, False otherwise.
        """
        return self._is_valid_transition(self._current_state, next_state)

    def reset(self) -> None:
        """Reset the state machine to IDLE.

        This is a convenience method for testing or recovery scenarios.
        In production use, agents typically reach a terminal state (COMPLETED/FAILED).
        """
        self._current_state = AgentState.IDLE

    def __repr__(self) -> str:
        """String representation showing current state."""
        return f"AgentStateMachine(current_state={self._current_state.value})"
