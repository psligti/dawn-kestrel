"""Agent Lifecycle FSM for managing agent lifecycle states.

This module provides a finite state machine for managing agent lifecycle
with states: idle, running, paused, completed, failed, cancelled.
"""

import logging
from dawn_kestrel.core.fsm import FSM, FSMBuilder, FSMContext
from dawn_kestrel.core.result import Result, Ok


logger = logging.getLogger(__name__)


VALID_LIFECYCLE_STATES = {
    "idle",
    "running",
    "paused",
    "completed",
    "failed",
    "cancelled",
}


VALID_LIFECYCLE_TRANSITIONS: dict[str, set[str]] = {
    "idle": {"running", "cancelled"},
    "running": {"paused", "completed", "failed", "cancelled"},
    "paused": {"running", "cancelled"},
    "completed": {"idle"},
    "failed": {"idle"},
    "cancelled": {"idle"},
}


def _create_entry_hook(state: str):
    """Create an entry hook for logging state transitions.

    Args:
        state: The state name for logging.

    Returns:
        Entry hook callable.
    """

    def entry_hook(ctx: FSMContext) -> Result[None]:
        """Log entry into state."""
        logger.info(f"Entering state: {state}")
        return Ok(None)

    return entry_hook


def create_lifecycle_fsm() -> Result[FSM]:
    """Factory function to create an agent lifecycle FSM.

    Creates an FSM with states: idle, running, paused, completed, failed, cancelled
    and transitions:
    - idle → running (start task)
    - idle → cancelled (cancel before start)
    - running → paused (pause task)
    - running → completed (task finished successfully)
    - running → failed (task encountered error)
    - running → cancelled (cancel task)
    - paused → running (resume task)
    - paused → cancelled (cancel paused task)
    - completed → idle (reset after completion)
    - failed → idle (reset after failure)
    - cancelled → idle (reset after cancellation)

    Each state has a simple logging entry hook.

    Returns:
        Result[FSM]: Ok with FSM instance starting at "idle", Err if build fails.
    """
    builder = FSMBuilder()

    for state in VALID_LIFECYCLE_STATES:
        builder.with_state(state)
        builder.with_entry_hook(state, _create_entry_hook(state))

    for from_state, to_states in VALID_LIFECYCLE_TRANSITIONS.items():
        for to_state in to_states:
            builder.with_transition(from_state, to_state)

    return builder.build(initial_state="idle")
