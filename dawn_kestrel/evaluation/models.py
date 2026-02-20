"""Evaluation models for transcript capture and analysis.

This module provides models for capturing conversation transcripts during
evaluation scenarios. Transcripts embed messages directly for portability,
allowing evaluation data to be self-contained without requiring storage.
"""

from __future__ import annotations

from typing import Any

import pydantic as pd

from dawn_kestrel.core.models import Message
from dawn_kestrel.evaluation.grader_specs import GraderSpec


class Transcript(pd.BaseModel):
    """Transcript model for evaluation transcript capture.

    Captures a conversation transcript with embedded messages for portability.
    This allows evaluation data to be self-contained without requiring
    external storage references.

    Attributes:
        id: Unique identifier for this transcript.
        session_id: ID of the session this transcript captures.
        messages: List of messages embedded directly (not referenced by ID).
        timing: Optional timing metadata for performance analysis.

    Example:
        >>> transcript = Transcript(
        ...     id="tr-1",
        ...     session_id="s-1",
        ...     messages=[Message(id="m-1", session_id="s-1", role="user", text="Hello")]
        ... )
    """

    model_config = pd.ConfigDict(extra="forbid")

    id: str
    session_id: str
    messages: list[Message]  # EMBEDDED, not referenced by ID
    timing: dict[str, float] = pd.Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert transcript to dictionary representation.

        Returns:
            Dictionary with all transcript data including embedded messages.
        """
        return self.model_dump()


class Outcome(pd.BaseModel):
    """Evaluation outcome with success flag and metadata.

    Metadata namespace convention:
    - dk.* for dawn-kestrel SDK-produced metadata
    - ash_hawk.* for harness-produced metadata
    """

    model_config = pd.ConfigDict(extra="forbid")

    success: bool
    metadata: dict[str, Any] = pd.Field(default_factory=dict)
    error: str | None = None
    artifacts: list[str] = pd.Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class Task(pd.BaseModel):
    """Evaluation task with grader specifications.

    Defines an evaluation task with its associated graders, inputs,
    and metadata for tracking metrics and categorization.

    Attributes:
        id: Unique identifier for this task.
        description: Human-readable description of the task.
        graders: List of grader specifications for evaluating task results.
        inputs: Task-specific input parameters.
        tracked_metrics: List of metric names to track for this task.
        tags: Tags for categorization and filtering.

    Example:
        >>> task = Task(
        ...     id="task-1",
        ...     description="Test code generation",
        ...     graders=[GraderSpec(type="llm_rubric", name="quality", config={})],
        ...     tags=["code-gen"]
        ... )
    """

    model_config = pd.ConfigDict(extra="forbid")

    id: str
    description: str
    graders: list[GraderSpec] = pd.Field(default_factory=list)
    inputs: dict[str, Any] = pd.Field(default_factory=dict)
    tracked_metrics: list[str] = pd.Field(default_factory=list)
    tags: list[str] = pd.Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary representation.

        Returns:
            Dictionary with all task data including grader specs.
        """
        return self.model_dump()


class Trial(pd.BaseModel):
    """Evaluation trial with run grouping and embedded transcript."""

    model_config = pd.ConfigDict(extra="forbid")

    id: str
    task_id: str  # Reference to Task
    run_id: str  # Groups trials across model/policy comparisons
    attempt: int = 1  # Trial number within run
    session_id: str  # Reference to origin session
    transcript: Transcript | None = None  # Embedded transcript
    outcome: Outcome | None = None
    metrics: dict[str, Any] = pd.Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class Suite(pd.BaseModel):
    """Evaluation suite containing tasks or task references.

    A suite must have at least one of `tasks` (embedded) or `task_ids` (references).
    This allows suites to be portable (with embedded tasks) or lightweight (with references).

    Attributes:
        id: Unique identifier for this suite.
        name: Human-readable name for the suite.
        description: Optional description of the suite's purpose.
        tasks: List of embedded Task objects.
        task_ids: List of task IDs (references to external task registry).
        version: Version string for tracking suite changes.
        tags: Tags for categorization and filtering.

    Example:
        >>> suite = Suite(
        ...     id="security-suite",
        ...     name="Security Evaluation Suite",
        ...     task_ids=["task-1", "task-2"]
        ... )
    """

    model_config = pd.ConfigDict(extra="forbid")

    id: str
    name: str
    description: str | None = None
    tasks: list[Task] = pd.Field(default_factory=list)
    task_ids: list[str] = pd.Field(default_factory=list)
    version: str = "1.0.0"
    tags: list[str] = pd.Field(default_factory=list)

    @pd.model_validator(mode="after")
    def validate_tasks_or_ids(self) -> "Suite":
        """Ensure at least one of tasks or task_ids is provided."""
        if not self.tasks and not self.task_ids:
            raise ValueError("Suite must have at least one of 'tasks' or 'task_ids'")
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class SuiteRun(pd.BaseModel):
    """Run-level grouping for suite execution.

    Captures metadata about a specific execution of a suite, including
    the agent identity, model parameters, and timing information.

    Attributes:
        id: Run identifier (same as run_id used in Trial).
        suite_id: Reference to the Suite being executed.
        agent_identity: Identifier for the agent (e.g., "claude-3-opus").
        model_params: Model configuration snapshot (temperature, etc.).
        tool_policy: Tool policy configuration snapshot.
        config_snapshot: Sanitized configuration at run time.
        started_at: ISO timestamp when the run started.
        ended_at: ISO timestamp when the run completed.
    """

    model_config = pd.ConfigDict(extra="forbid")

    id: str  # The run_id
    suite_id: str  # Reference to Suite
    agent_identity: str | None = None  # e.g., "claude-3-opus"
    model_params: dict[str, Any] = pd.Field(default_factory=dict)
    tool_policy: dict[str, Any] = pd.Field(default_factory=dict)
    config_snapshot: dict[str, Any] = pd.Field(default_factory=dict)
    started_at: str | None = None  # ISO timestamp
    ended_at: str | None = None  # ISO timestamp

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
