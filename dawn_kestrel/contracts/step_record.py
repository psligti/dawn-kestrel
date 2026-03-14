"""Step record for tracking agent execution trajectory."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

import pydantic as pd


class StepRecord(pd.BaseModel):
    """Record of a single step in an agent's execution trajectory.

    Steps represent logical units of agent reasoning and action,
    capturing the agent's thought process and progress toward goals.

    Attributes:
        step_id: Unique identifier for this step.
        title: Human-readable title/summary of the step.
        status: Current status (pending, running, completed, failed, skipped).
        summary: Detailed description of what happened in this step.
        started_at: Timestamp when step started.
        finished_at: Timestamp when step completed.
        reasoning: Agent's reasoning for this step (optional).
        parent_step_id: Parent step ID if this is a sub-step.
    """

    step_id: str = pd.Field(
        description="Unique identifier for this step",
    )
    title: str = pd.Field(
        description="Human-readable title/summary of the step",
    )
    status: Literal["pending", "running", "completed", "failed", "skipped"] = pd.Field(
        description="Current status of the step",
    )
    summary: str | None = pd.Field(
        default=None,
        description="Detailed description of what happened in this step",
    )
    started_at: datetime | None = pd.Field(
        default=None,
        description="Timestamp when step started",
    )
    finished_at: datetime | None = pd.Field(
        default=None,
        description="Timestamp when step completed",
    )
    reasoning: str | None = pd.Field(
        default=None,
        description="Agent's reasoning for this step",
    )
    parent_step_id: str | None = pd.Field(
        default=None,
        description="Parent step ID if this is a sub-step",
    )

    @pd.computed_field(return_type=float)
    def duration_seconds(self) -> float | None:
        """Compute step duration in seconds if timestamps available."""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    model_config = pd.ConfigDict(extra="forbid")
