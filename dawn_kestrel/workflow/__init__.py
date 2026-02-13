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

Example usage:
    >>> from dawn_kestrel.workflow import run_workflow_fsm, ConsoleLogger
    >>> ctx = run_workflow_fsm(['file1.py', 'file2.py'])
    >>> ConsoleLogger.log_log(ctx.log)
    >>> print(f"Final state: {ctx.state}")
"""

from dawn_kestrel.workflow.models import (
    Confidence,
    StructuredContext,
    ThinkingFrame,
    ThinkingStep,
    Todo,
    ActionType,
    DecisionType,
    ReactStep,
    RunLog,
)
from dawn_kestrel.workflow.fsm import (
    assert_transition,
    run_workflow_fsm,
    STATE_HANDLERS,
    WORKFLOW_FSM_TRANSITIONS,
)
from dawn_kestrel.workflow.loggers import (
    ConsoleLogger,
    JsonLogger,
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
    # FSM
    "assert_transition",
    "run_workflow_fsm",
    "STATE_HANDLERS",
    "WORKFLOW_FSM_TRANSITIONS",
    # Loggers
    "ConsoleLogger",
    "JsonLogger",
]
