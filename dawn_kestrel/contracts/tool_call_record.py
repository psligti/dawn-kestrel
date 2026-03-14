"""Tool call record for tracking agent tool invocations."""

from __future__ import annotations

from typing import Any, Literal

import pydantic as pd


class ToolCallRecord(pd.BaseModel):
    """Record of a single tool invocation during agent execution.

    Captures the tool name, arguments, outcome, and any side effects
    for reproducibility and analysis.

    Attributes:
        tool_name: Name of the tool invoked.
        arguments: Arguments passed to the tool.
        outcome: Result status (success, failure, partial).
        duration_ms: Execution time in milliseconds.
        side_effects: List of side effect descriptions (files modified, etc.).
        error_message: Error details if outcome is failure.
        result_preview: Truncated preview of the result (for debugging).
    """

    tool_name: str = pd.Field(
        description="Name of the tool invoked",
    )
    arguments: dict[str, Any] = pd.Field(
        default_factory=dict,
        description="Arguments passed to the tool",
    )
    outcome: Literal["success", "failure", "partial"] = pd.Field(
        description="Result status of the tool call",
    )
    duration_ms: int | None = pd.Field(
        default=None,
        description="Execution time in milliseconds",
    )
    side_effects: list[str] = pd.Field(
        default_factory=list,
        description="List of side effect descriptions (files modified, network calls, etc.)",
    )
    error_message: str | None = pd.Field(
        default=None,
        description="Error details if outcome is failure",
    )
    result_preview: str | None = pd.Field(
        default=None,
        description="Truncated preview of the result (max 500 chars)",
    )

    model_config = pd.ConfigDict(extra="forbid")
