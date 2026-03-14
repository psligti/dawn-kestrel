"""Dawn Kestrel contracts for run artifacts and execution records.

These contracts define the stable interface between Dawn Kestrel (execution substrate)
and Ash Hawk (evaluation and improvement engine).

Key contracts:
- RunArtifact: Complete record of an agent run for external evaluation
- StepRecord: Single step in an agent's execution trajectory
- ToolCallRecord: Record of a tool invocation with outcome tracking
"""

from __future__ import annotations

from dawn_kestrel.contracts.run_artifact import RunArtifact
from dawn_kestrel.contracts.step_record import StepRecord
from dawn_kestrel.contracts.tool_call_record import ToolCallRecord

__all__ = [
    "RunArtifact",
    "StepRecord",
    "ToolCallRecord",
]
