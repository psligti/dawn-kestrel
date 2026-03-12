"""SpawnSubtaskAction for policy-driven delegation.

This module defines the action that allows policies to create subtasks
dynamically. This replaces FSM-based delegation with policy-driven decisions.
"""

from __future__ import annotations

from typing import Any, Literal

import pydantic as pd


class SpawnSubtaskAction(pd.BaseModel):
    action_type: Literal["SPAWN_SUBTASK"] = "SPAWN_SUBTASK"

    agent: str = pd.Field(description="Agent name to delegate to")
    prompt: str = pd.Field(description="Prompt for subagent")
    domain: str = pd.Field(default="general", description="Domain classification")
    traversal_mode: Literal["breadth_first", "depth_first", "adaptive"] = pd.Field(
        default="breadth_first", description="How to traverse subtasks"
    )
    children: list[dict[str, Any]] = pd.Field(
        default_factory=list, description="Child subtasks to create"
    )

    model_config = pd.ConfigDict(extra="forbid")


__all__ = ["SpawnSubtaskAction"]
