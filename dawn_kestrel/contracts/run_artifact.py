"""Run artifact - complete record of an agent execution for external evaluation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

import pydantic as pd

from dawn_kestrel.contracts.step_record import StepRecord
from dawn_kestrel.contracts.tool_call_record import ToolCallRecord


class RunArtifact(pd.BaseModel):
    """Complete record of an agent run for external evaluation.

    Produced by Dawn Kestrel and consumed by Ash Hawk for evaluation
    and improvement proposal generation.

    This contract provides a stable interface between execution and evaluation,
    enabling cross-agent improvement without coupling to agent internals.

    Attributes:
        run_id: Unique identifier for this run.
        agent_id: Identifier of the agent that executed (e.g., "iron-rook", "bolt-merlin").
        agent_version: Version of the agent (optional).
        task_type: Type of task performed (e.g., "pr_review", "code_change", "content_gen").
        input_summary: Summary of the input/prompt (truncated for storage).
        context_refs: References to context files/resources used.
        repo_refs: References to repositories involved (for multi-repo scenarios).
        steps: Ordered list of execution steps.
        tool_calls: List of all tool invocations.
        outputs: Final outputs produced by the agent.
        outcome: Overall run outcome (success, failure, partial).
        outcome_details: Additional details about the outcome.
        telemetry: Runtime telemetry (tokens, latency, costs).
        created_at: Timestamp when artifact was created.
        session_id: Dawn Kestrel session ID for traceability.
        metadata: Additional metadata for extensibility.
    """

    run_id: str = pd.Field(
        description="Unique identifier for this run",
    )
    agent_id: str = pd.Field(
        description="Identifier of the agent that executed",
    )
    agent_version: str | None = pd.Field(
        default=None,
        description="Version of the agent",
    )
    task_type: str = pd.Field(
        description="Type of task performed (e.g., 'pr_review', 'code_change', 'content_gen')",
    )
    input_summary: str = pd.Field(
        description="Summary of the input/prompt (truncated for storage)",
    )
    context_refs: list[str] = pd.Field(
        default_factory=list,
        description="References to context files/resources used",
    )
    repo_refs: list[str] = pd.Field(
        default_factory=list,
        description="References to repositories involved (for multi-repo scenarios)",
    )
    steps: list[StepRecord] = pd.Field(
        default_factory=list,
        description="Ordered list of execution steps",
    )
    tool_calls: list[ToolCallRecord] = pd.Field(
        default_factory=list,
        description="List of all tool invocations",
    )
    outputs: list[dict[str, Any]] = pd.Field(
        default_factory=list,
        description="Final outputs produced by the agent",
    )
    outcome: Literal["success", "failure", "partial"] = pd.Field(
        description="Overall run outcome",
    )
    outcome_details: str | None = pd.Field(
        default=None,
        description="Additional details about the outcome",
    )
    telemetry: dict[str, Any] = pd.Field(
        default_factory=dict,
        description="Runtime telemetry (tokens, latency, costs)",
    )
    created_at: datetime = pd.Field(
        description="Timestamp when artifact was created",
    )
    session_id: str | None = pd.Field(
        default=None,
        description="Dawn Kestrel session ID for traceability",
    )
    metadata: dict[str, Any] = pd.Field(
        default_factory=dict,
        description="Additional metadata for extensibility",
    )

    @pd.computed_field(return_type=int)
    def total_tool_calls(self) -> int:
        """Total number of tool calls in this run."""
        return len(self.tool_calls)

    @pd.computed_field(return_type=int)
    def total_steps(self) -> int:
        """Total number of steps in this run."""
        return len(self.steps)

    @pd.computed_field(return_type=int)
    def failed_tool_calls(self) -> int:
        """Number of failed tool calls."""
        return sum(1 for tc in self.tool_calls if tc.outcome == "failure")

    model_config = pd.ConfigDict(extra="forbid")
