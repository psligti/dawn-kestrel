"""REACT-enhanced Workflow Framework.

This package provides a general-purpose finite state machine framework
with structured thinking traces and REACT pattern support.

REACT Pattern:
    Reason: Generate thinking about what to do
    Act: Execute tools or take action
    Observe: Review results and update understanding

The framework enables:
- Structured thinking traces (ThinkingStep, ThinkingFrame)
- REACT cycles within each state
- Console and JSON logging
- Evidence references to artifacts
- Dynamic thinking (not static strings)

Visualization:
    See diagrams.md for Mermaid diagrams showing:
    - FSM state transitions and flow
    - REACT pattern within states
    - Architecture and data flow
    - Example execution sequences

Note:
    The FSM functionality has been consolidated into dawn_kestrel.core.fsm.
    Use WorkflowFSMBuilder from dawn_kestrel.core.fsm for workflow state machines.

Example usage:
    >>> from dawn_kestrel.core.fsm import WorkflowFSMBuilder
    >>> builder = WorkflowFSMBuilder()
    >>> result = builder.build()
"""

from dawn_kestrel.core.fsm import (
    WORKFLOW_STATES,
    WORKFLOW_TRANSITIONS,
    WorkflowFSMBuilder,
)
from dawn_kestrel.core.result import Err, Ok, Result
from dawn_kestrel.workflow.loggers import ConsoleLogger, JsonLogger


WORKFLOW_FSM_TRANSITIONS: dict[str, set[str]] = {
    "intake": {"plan", "failed"},
    "plan": {"act", "failed"},
    "act": {"synthesize", "failed"},
    "synthesize": {"evaluate", "failed"},
    "evaluate": {"done", "plan", "failed"},
    "done": {"intake"},
    "failed": {"intake"},
}


def assert_transition(from_state: str, to_state: str) -> Result[str]:
    if from_state not in WORKFLOW_FSM_TRANSITIONS:
        return Err(
            f"Invalid from_state: {from_state}. Valid states: {sorted(WORKFLOW_FSM_TRANSITIONS.keys())}",
            code="INVALID_FROM_STATE",
        )

    if to_state not in WORKFLOW_FSM_TRANSITIONS[from_state]:
        return Err(
            (
                f"Invalid state transition: {from_state} -> {to_state}. "
                f"Valid transitions from {from_state}: {sorted(WORKFLOW_FSM_TRANSITIONS[from_state])}"
            ),
            code="INVALID_TRANSITION",
        )

    return Ok(to_state)


__all__ = [
    # FSM (from core.fsm)
    "WORKFLOW_STATES",
    "WORKFLOW_TRANSITIONS",
    "WORKFLOW_FSM_TRANSITIONS",
    "assert_transition",
    "WorkflowFSMBuilder",
    # Loggers
    "ConsoleLogger",
    "JsonLogger",
]

from dawn_kestrel.workflow.multi_agent import (
    AggregationSpec,
    AggregationStrategy,
    AgentExecutionResult,
    AgentExecutor,
    AgentSpec,
    ConflictResolution,
    ExecutionMode,
    ExecutionStatus,
    FindingsAggregator,
    MultiAgentWorkflow,
    ResultAggregator,
    WorkflowResult,
)
