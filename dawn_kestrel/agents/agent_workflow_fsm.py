"""Simple workflow FSM for agent orchestration.

This is a simplified FSM that defines the states and transitions for
agent-based workflow orchestration, without any LLM execution logic.

States: intake → plan → act → synthesize → check → (plan or done)
- intake: Extract intent/constraints/evidence
- plan: Generate/modify/prioritize todos
- act: Perform tool-using work against prioritized todos
- synthesize: Merge results and update todo statuses
- check: Decide whether to continue loop or stop
- done: Workflow completed

The key feature is the LOOP:
- check → plan: Continue iteration
- check → done: Exit when stop conditions met

Reset: done → intake (reset for next task)
"""

import logging
from typing import Callable

from dawn_kestrel.core.fsm import FSM, FSMBuilder, FSMContext
from dawn_kestrel.core.result import Result, Ok

logger = logging.getLogger(__name__)


# State constants
INTAKE = "intake"
PLAN = "plan"
ACT = "act"
SYNTHESIZE = "synthesize"
CHECK = "check"
DONE = "done"


def _create_entry_hook(state_name: str) -> Callable[[FSMContext], Result[None]]:
    """Create a simple logging entry hook for a state.

    Args:
        state_name: Name of the state for logging purposes.

    Returns:
        Entry hook function that logs state entry.
    """

    def hook(ctx: FSMContext) -> Result[None]:
        logger.info(f"Entering state: {state_name}")
        return Ok(None)

    return hook


def create_workflow_fsm() -> Result[FSM]:
    """Factory function to create a simple workflow FSM.

    Creates an FSM with states: intake, plan, act, synthesize, check, done
    and transitions:
    - intake → plan
    - plan → act
    - act → synthesize
    - synthesize → check
    - check → plan (loop - continue iteration)
    - check → done (exit - stop conditions met)
    - done → intake (reset for next task)

    Each state has a simple logging entry hook.

    Returns:
        Result[FSM]: Ok with FSM instance starting at "intake", Err if build fails.
    """
    builder = (
        FSMBuilder()
        # Define all states
        .with_state(INTAKE)
        .with_state(PLAN)
        .with_state(ACT)
        .with_state(SYNTHESIZE)
        .with_state(CHECK)
        .with_state(DONE)
        # Define linear flow transitions
        .with_transition(INTAKE, PLAN)
        .with_transition(PLAN, ACT)
        .with_transition(ACT, SYNTHESIZE)
        .with_transition(SYNTHESIZE, CHECK)
        # Define loop transition (continue iteration)
        .with_transition(CHECK, PLAN)
        # Define exit transition (stop conditions met)
        .with_transition(CHECK, DONE)
        # Define reset transition
        .with_transition(DONE, INTAKE)
    )

    # Add simple logging entry hooks for each state
    for state in [INTAKE, PLAN, ACT, SYNTHESIZE, CHECK, DONE]:
        builder = builder.with_entry_hook(state, _create_entry_hook(state))

    # Build the FSM with initial state
    return builder.build(initial_state=INTAKE)
