"""Policy engine contracts for agent decision-making.

This module defines the typed data models for the pluggable policy engine
that governs agent behavior at runtime. These contracts enable:

- Clear separation between policy evaluation and execution
- Structured validation of agent proposals before action execution
- Type-safe communication between runtime and policy components
- Extensibility for custom policy implementations

Key components:
- PolicyInput: Runtime state snapshot provided to policy evaluators
- StepProposal: Agent's proposed next step with actions and risk assessment
- Action variants: Typed command objects for each action type
- TodoCompletionClaim: Evidence-based claims for TODO completion
- ContextRequest: Typed requests for context retrieval

All models enforce strict Pydantic validation with extra="forbid" to ensure
schema compliance and catch invalid proposals early.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union

import pydantic as pd
from pydantic import Field


# StrEnum compatibility for Python < 3.11
class RiskLevel(str, Enum):
    """Risk level for step proposals.

    Used by agents and policy evaluators to assess the potential impact
    of proposed actions. Higher risk levels may require additional
    validation or approval gates.

    Values:
        LOW: Routine operations with minimal impact (e.g., read file, list directory)
        MED: Operations with moderate impact (e.g., edit file, run tests)
        HIGH: Operations with significant impact (e.g., git push, delete files)
    """

    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"



# =============================================================================
# Action Types - Discriminated Union via ActionType literal
# =============================================================================


class ReadFileAction(pd.BaseModel):
    """Action to read file contents.

    Attributes:
        action_type: Discriminator, always "READ_FILE"
        path: Path to the file to read
        offset: Optional starting line number (1-indexed)
        limit: Optional maximum number of lines to read
    """

    action_type: Literal["READ_FILE"] = "READ_FILE"

    path: str = Field(description="Path to the file to read")
    offset: int | None = Field(default=None, description="Starting line number (1-indexed)")
    limit: int | None = Field(default=None, description="Maximum lines to read")

    model_config = pd.ConfigDict(extra="forbid")


class SearchRepoAction(pd.BaseModel):
    """Action to search repository contents.

    Attributes:
        action_type: Discriminator, always "SEARCH_REPO"
        pattern: Regex or glob pattern to search for
        file_pattern: Optional glob pattern to filter files
        max_results: Maximum number of results to return
    """

    action_type: Literal["SEARCH_REPO"] = "SEARCH_REPO"

    pattern: str = Field(description="Pattern to search for (regex or literal)")
    file_pattern: str | None = Field(default=None, description="Glob pattern to filter files")
    max_results: int = Field(default=100, description="Maximum results to return")

    model_config = pd.ConfigDict(extra="forbid")


class EditFileAction(pd.BaseModel):
    """Action to edit a file.

    Attributes:
        action_type: Discriminator, always "EDIT_FILE"
        path: Path to the file to edit
        operation: Type of edit operation
        content: Content for the edit (meaning depends on operation)
        line_start: Starting line for line-based operations
        line_end: Ending line for line-based operations
    """

    action_type: Literal["EDIT_FILE"] = "EDIT_FILE"

    path: str = Field(description="Path to the file to edit")
    operation: Literal["replace", "insert", "append", "delete"] = Field(
        default="replace", description="Type of edit operation"
    )
    content: str | None = Field(default=None, description="Content for the edit")
    line_start: int | None = Field(default=None, description="Starting line (1-indexed)")
    line_end: int | None = Field(default=None, description="Ending line (1-indexed)")

    model_config = pd.ConfigDict(extra="forbid")


class RunTestsAction(pd.BaseModel):
    """Action to run tests.

    Attributes:
        action_type: Discriminator, always "RUN_TESTS"
        test_path: Path to test file or directory
        filter_pattern: Optional pattern to filter tests
        extra_args: Additional arguments for test runner
    """

    action_type: Literal["RUN_TESTS"] = "RUN_TESTS"

    test_path: str = Field(description="Path to test file or directory")
    filter_pattern: str | None = Field(default=None, description="Pattern to filter tests")
    extra_args: list[str] = Field(default_factory=list, description="Additional test runner args")

    model_config = pd.ConfigDict(extra="forbid")


class UpsertTodosAction(pd.BaseModel):
    """Action to create, update, or delete todos.

    Attributes:
        action_type: Discriminator, always "UPSERT_TODOS"
        todos: List of todo items to upsert
        delete_ids: List of todo IDs to delete
    """

    action_type: Literal["UPSERT_TODOS"] = "UPSERT_TODOS"

    todos: list[dict[str, Any]] = Field(
        default_factory=list, description="Todo items to create or update"
    )
    delete_ids: list[str] = Field(default_factory=list, description="Todo IDs to delete")

    model_config = pd.ConfigDict(extra="forbid")


class RequestApprovalAction(pd.BaseModel):
    """Action to request human approval.

    Attributes:
        action_type: Discriminator, always "REQUEST_APPROVAL"
        message: Message to display to the user
        options: Available options for approval
        timeout_seconds: Optional timeout for approval request
    """

    action_type: Literal["REQUEST_APPROVAL"] = "REQUEST_APPROVAL"

    message: str = Field(description="Message to display to the user")
    options: list[str] = Field(
        default_factory=lambda: ["approve", "reject"],
        description="Available approval options",
    )
    timeout_seconds: float | None = Field(default=None, description="Approval timeout")

    model_config = pd.ConfigDict(extra="forbid")


class SummarizeAction(pd.BaseModel):
    """Action to summarize information.

    Attributes:
        action_type: Discriminator, always "SUMMARIZE"
        content: Content to summarize
        max_length: Maximum summary length in characters
        focus_areas: Specific areas to focus the summary on
    """

    action_type: Literal["SUMMARIZE"] = "SUMMARIZE"

    content: str = Field(description="Content to summarize")
    max_length: int = Field(default=500, description="Maximum summary length")
    focus_areas: list[str] = Field(default_factory=list, description="Areas to focus summary on")

    model_config = pd.ConfigDict(extra="forbid")


# Union type for all actions using discriminator
Action = Annotated[
    Union[
        ReadFileAction,
        SearchRepoAction,
        EditFileAction,
        RunTestsAction,
        UpsertTodosAction,
        RequestApprovalAction,
        SummarizeAction,
    ],
    pd.Field(discriminator="action_type"),
]


# =============================================================================
# Context Request
# =============================================================================


class ContextRequest(pd.BaseModel):
    """Typed request for context retrieval.

    Used by agents to request additional context that may be needed
    for decision-making. Policy evaluators use this to understand
    what information the agent is seeking.

    Attributes:
        request_type: Type of context being requested
        query: Query string or pattern for context retrieval
        scope: Optional scope limitation (e.g., file paths, modules)
        priority: Priority of this context request
        rationale: Why this context is needed
    """

    request_type: Literal["file", "symbol", "search", "dependency", "history", "custom"] = Field(
        description="Type of context being requested"
    )
    query: str = Field(description="Query string or pattern for context retrieval")
    scope: list[str] = Field(
        default_factory=list, description="Scope limitation (paths, modules, etc.)"
    )
    priority: Literal["high", "medium", "low"] = Field(
        default="medium", description="Priority of this request"
    )
    rationale: str = Field(default="", description="Why this context is needed")

    model_config = pd.ConfigDict(extra="forbid")


# =============================================================================
# Todo Completion Claim
# =============================================================================


class TodoCompletionClaim(pd.BaseModel):
    """Structured claim for TODO completion with evidence.

    Agents submit completion claims to assert that specific TODOs
    have been completed. Policy evaluators validate these claims
    against available evidence before accepting them.

    Attributes:
        todo_id: ID of the TODO item being claimed complete
        evidence_type: Type of evidence supporting the claim
        evidence_summary: Human-readable summary of evidence
        evidence_refs: References to specific evidence (file paths, line numbers, etc.)
        confidence: Confidence level in the claim (0.0 to 1.0)
        verification_hints: Optional hints for how to verify the claim
    """

    todo_id: str = Field(description="ID of the TODO item being claimed complete")
    evidence_type: Literal[
        "file_modified", "test_passed", "build_succeeded", "manual_review", "inference", "other"
    ] = Field(description="Type of evidence supporting the claim")
    evidence_summary: str = Field(description="Human-readable summary of evidence")
    evidence_refs: list[str] = Field(
        default_factory=list, description="References to evidence (paths, lines, etc.)"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in claim (0.0-1.0)"
    )
    verification_hints: str = Field(default="", description="Hints for how to verify the claim")

    model_config = pd.ConfigDict(extra="forbid")


# =============================================================================
# Policy Input
# =============================================================================


class TodoItem(pd.BaseModel):
    """A single TODO item in policy input.

    Attributes:
        id: Unique identifier for this TODO
        description: What needs to be done
        status: Current status
        priority: Priority level
        dependencies: IDs of TODOs this depends on
    """

    id: str = Field(description="Unique identifier for this TODO")
    description: str = Field(description="What needs to be done")
    status: Literal["pending", "in_progress", "completed", "blocked", "skipped"] = Field(
        default="pending", description="Current status"
    )
    priority: Literal["high", "medium", "low"] = Field(
        default="medium", description="Priority level"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="IDs of TODOs this depends on"
    )

    model_config = pd.ConfigDict(extra="forbid")


class EventSummary(pd.BaseModel):
    """Summary of a recent event in policy input.

    Attributes:
        event_type: Type of event that occurred
        timestamp: When the event occurred (ISO 8601 string)
        summary: Brief description of the event
        outcome: Result of the event
    """

    event_type: str = Field(description="Type of event")
    timestamp: str = Field(description="When event occurred (ISO 8601)")
    summary: str = Field(description="Brief description of the event")
    outcome: Literal["success", "failure", "pending", "skipped"] = Field(
        default="success", description="Result of the event"
    )

    model_config = pd.ConfigDict(extra="forbid")


class BudgetInfo(pd.BaseModel):
    """Budget constraints and consumption.

    Attributes:
        max_iterations: Maximum allowed iterations
        max_tool_calls: Maximum allowed tool calls
        max_wall_time_seconds: Maximum wall-clock time
        max_subagent_calls: Maximum subagent calls allowed
        iterations_consumed: Iterations used so far
        tool_calls_consumed: Tool calls used so far
        wall_time_consumed: Wall-clock time used so far
        subagent_calls_consumed: Subagent calls used so far
    """

    max_iterations: int = Field(default=100, description="Maximum allowed iterations")
    max_tool_calls: int = Field(default=1000, description="Maximum allowed tool calls")
    max_wall_time_seconds: float = Field(default=3600.0, description="Maximum wall-clock time")
    max_subagent_calls: int = Field(default=50, description="Maximum subagent calls")

    iterations_consumed: int = Field(default=0, description="Iterations used so far")
    tool_calls_consumed: int = Field(default=0, description="Tool calls used so far")
    wall_time_consumed: float = Field(default=0.0, description="Wall-clock time used")
    subagent_calls_consumed: int = Field(default=0, description="Subagent calls used")

    model_config = pd.ConfigDict(extra="forbid")


class Constraint(pd.BaseModel):
    """A constraint on agent behavior.

    Attributes:
        constraint_type: Type of constraint
        value: Constraint value or pattern
        description: Human-readable description
        severity: How strictly this must be enforced
    """

    constraint_type: Literal[
        "permission", "tool_restriction", "file_pattern", "time_limit", "custom"
    ] = Field(description="Type of constraint")
    value: str = Field(description="Constraint value or pattern")
    description: str = Field(default="", description="Human-readable description")
    severity: Literal["hard", "soft"] = Field(default="hard", description="How strictly to enforce")

    model_config = pd.ConfigDict(extra="forbid")


class PolicyInput(pd.BaseModel):
    """Runtime state snapshot provided to policy evaluators.

    This is the complete context that policy evaluators use to make
    decisions about proposed actions. It captures the agent's current
    state including goals, progress, constraints, and available resources.

    Attributes:
        goal: The primary goal the agent is working toward
        active_todos: List of active TODO items
        last_events: Summary of recent events/actions
        granted_context: Context that has already been retrieved/granted
        budgets: Budget constraints and consumption status
        constraints: Active constraints on agent behavior

    Example:
        >>> input_data = PolicyInput(
        ...     goal="Implement user authentication",
        ...     active_todos=[
        ...         TodoItem(id="1", description="Create login form", status="in_progress")
        ...     ],
        ...     last_events=[
        ...         EventSummary(event_type="file_read", summary="Read auth.py", outcome="success")
        ...     ],
        ...     budgets=BudgetInfo(max_iterations=50),
        ... )
    """

    goal: str = Field(description="Primary goal the agent is working toward")
    active_todos: list[TodoItem] = Field(default_factory=list, description="Active TODO items")
    last_events: list[EventSummary] = Field(
        default_factory=list, description="Recent events/actions"
    )
    granted_context: dict[str, Any] = Field(
        default_factory=dict, description="Already retrieved context"
    )
    budgets: BudgetInfo = Field(
        default_factory=BudgetInfo, description="Budget constraints and consumption"
    )
    constraints: list[Constraint] = Field(
        default_factory=list, description="Active behavioral constraints"
    )

    model_config = pd.ConfigDict(extra="forbid")

    @classmethod
    def from_trial(cls, goal: str, todos: list[dict[str, Any]], **kwargs: Any) -> PolicyInput:
        """Factory method to create PolicyInput from trial state.

        Convenience method for constructing PolicyInput from runtime
        state that may be in dictionary form.

        Args:
            goal: The primary goal
            todos: List of TODO dictionaries
            **kwargs: Additional fields to pass to constructor

        Returns:
            PolicyInput instance with converted todos
        """
        todo_items = [TodoItem(**t) if isinstance(t, dict) else t for t in todos]
        return cls(goal=goal, active_todos=todo_items, **kwargs)


# =============================================================================
# Step Proposal
# =============================================================================


class StepProposal(pd.BaseModel):
    """Agent's proposed next step with actions and risk assessment.

    This is the primary output from agents to the policy engine.
    Agents propose what they want to do next, and the policy engine
    evaluates whether to approve, modify, or reject the proposal.

    Attributes:
        intent: High-level description of what the agent intends to accomplish
        target_todo_ids: IDs of TODOs this step targets
        requested_context: Context requests for information needed
        actions: List of actions to execute if approved
        completion_claims: Claims about TODOs this step completes
        risk_level: Assessed risk level of this proposal
        notes: Additional notes or rationale

    Example:
        >>> proposal = StepProposal(
        ...     intent="Read authentication module to understand current implementation",
        ...     target_todo_ids=["todo-1"],
        ...     actions=[ReadFileAction(path="auth.py")],
        ...     risk_level=RiskLevel.LOW,
        ... )
    """

    intent: str = Field(description="High-level description of intent")
    target_todo_ids: list[str] = Field(
        default_factory=list, description="IDs of TODOs this step targets"
    )
    requested_context: list[ContextRequest] = Field(
        default_factory=list, description="Context requests"
    )
    actions: list[Action] = Field(
        default_factory=list, description="Actions to execute if approved"
    )
    completion_claims: list[TodoCompletionClaim] = Field(
        default_factory=list, description="Claims about TODO completion"
    )
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Assessed risk level")
    notes: str = Field(default="", description="Additional notes or rationale")

    model_config = pd.ConfigDict(extra="forbid")

    def get_action_types(self) -> list[str]:
        """Get list of action types in this proposal.

        Returns:
            List of action_type strings for all actions
        """
        return [action.action_type for action in self.actions]

    def has_high_risk_actions(self) -> bool:
        """Check if proposal contains any high-risk actions.

        Returns:
            True if any action is considered high-risk
        """
        high_risk_types = {"EDIT_FILE", "RUN_TESTS", "REQUEST_APPROVAL"}
        return any(action.action_type in high_risk_types for action in self.actions)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Enums
    "RiskLevel",
    # Actions
    "Action",
    "ReadFileAction",
    "SearchRepoAction",
    "EditFileAction",
    "RunTestsAction",
    "UpsertTodosAction",
    "RequestApprovalAction",
    "SummarizeAction",
    # Context and Claims
    "ContextRequest",
    "TodoCompletionClaim",
    # Policy types
    "TodoItem",
    "EventSummary",
    "BudgetInfo",
    "Constraint",
    "PolicyInput",
    "StepProposal",
]
