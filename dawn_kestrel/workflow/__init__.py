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
from dawn_kestrel.workflow.loggers import (
    ConsoleLogger,
    JsonLogger,
)
from dawn_kestrel.workflow.models import (
    ActionType,
    Confidence,
    DecisionType,
    ReactStep,
    RunLog,
    StructuredContext,
    ThinkingFrame,
    ThinkingStep,
    Todo,
)

__all__ = [
    # Models
    "Confidence",
    "StructuredContext",
    "ThinkingFrame",
    "ThinkingStep",
    "Todo",
    "ActionType",
    "DecisionType",
    "ReactStep",
    "RunLog",
    # FSM (from core.fsm)
    "WORKFLOW_STATES",
    "WORKFLOW_TRANSITIONS",
    "WorkflowFSMBuilder",
    # Loggers
    "ConsoleLogger",
    "JsonLogger",
]
