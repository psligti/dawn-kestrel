"""Data models for REACT-enhanced thinking framework.

This module defines the core data models for capturing structured reasoning
traces with REACT pattern (Reason-Act) support within FSM states.

REACT Pattern Integration:
- Each ThinkingStep can be a reasoning, action, or observation step
- Frames can contain multiple REACT cycles (reason → act → observe)
- Evidence links connect reasoning to concrete artifacts

Models:
- Confidence: Confidence levels for decisions
- ActionType: REACT step types (reason, act, observe)
- DecisionType: Decision categories
- ThinkingStep: Single reasoning/action step with evidence
- ReactStep: REACT-specific step with observation feedback
- ThinkingFrame: Complete thinking trace for a state
- RunLog: Collection of frames with JSON export
- Todo: Task tracking with evidence
- StructuredContext: Workflow state with context
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class Confidence(str, Enum):
    """Confidence levels for decisions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    """REACT step types - core of Reason-Act-Observe pattern.

    REACT Pattern:
        Reason: Generate thinking about what to do
        Act: Execute a tool or take action
        Observe: Review the result and update understanding
    """

    REASON = "reason"  # Thinking/planning step
    ACT = "act"  # Tool execution or action
    OBSERVE = "observe"  # Result analysis


class DecisionType(str, Enum):
    """Decision categories for FSM transitions."""

    TRANSITION = "transition"  # Move to next state
    TOOL = "tool"  # Execute a tool
    DELEGATE = "delegate"  # Delegate to subagent
    GATE = "gate"  # Conditional check
    STOP = "stop"  # Terminate workflow


class ThinkingStep(BaseModel):
    """Single reasoning step within a ThinkingFrame.

    Can represent a REACT step (reason, act, observe) or a traditional
    decision step with evidence links.

    Attributes:
        kind: Step type (action type)
        why: Reasoning or motivation
        evidence: Concrete evidence references (file paths, tool outputs)
        next: Next action or state
        confidence: Confidence in this step
        action_result: Optional result of act steps
    """

    kind: ActionType = Field(
        default=ActionType.REASON,
        description="Type of step (reason, act, observe)",
    )
    why: str = Field(
        ...,
        description="Reasoning or motivation for this step",
        min_length=1,
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Concrete evidence references (e.g., 'diff:file1.py', 'tool:grep#2')",
    )
    next: str = Field(
        default="",
        description="Next action or state transition",
    )
    confidence: Confidence = Field(
        default=Confidence.MEDIUM,
        description="Confidence in this step",
    )
    action_result: Optional[str] = Field(
        default=None,
        description="Result from act step (if applicable)",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "kind": self.kind.value,
            "why": self.why,
            "evidence": self.evidence,
            "next": self.next,
            "confidence": self.confidence.value,
            "action_result": self.action_result,
        }


class ReactStep(BaseModel):
    """Complete REACT cycle: Reason → Act → Observe.

    A REACT step represents a full reasoning-action-observation cycle
    within a single state. This allows tracking iterative refinement
    within states.

    Attributes:
        reasoning: What the agent is thinking
        action: What the agent decides to do
        observation: What happened as a result
        tools_used: List of tools called in this cycle
        evidence: Evidence references
    """

    reasoning: str = Field(
        ...,
        description="What the agent is thinking/planning",
        min_length=1,
    )
    action: str = Field(
        ...,
        description="What the agent decides to do",
        min_length=1,
    )
    observation: str = Field(
        ...,
        description="What happened as a result of the action",
        min_length=1,
    )
    tools_used: list[str] = Field(
        default_factory=list,
        description="Tools called in this REACT cycle",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence references",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "reasoning": self.reasoning,
            "action": self.action,
            "observation": self.observation,
            "tools_used": self.tools_used,
            "evidence": self.evidence,
        }


class ThinkingFrame(BaseModel):
    """Complete thinking trace for a single FSM state.

    Captures all reasoning, actions, and decisions made during
    execution of a single state. Supports both traditional thinking
    steps and REACT cycles.

    Attributes:
        state: Current FSM state
        ts: Timestamp of this frame
        goals: List of goals for this state
        checks: Precondition checks performed
        risks: Risks identified
        steps: List of ThinkingStep or ReactStep
        decision: Final decision made
        react_cycles: Optional list of complete REACT cycles
    """

    state: str = Field(
        ...,
        description="Current FSM state",
        min_length=1,
    )
    ts: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of this frame",
    )
    goals: list[str] = Field(
        default_factory=list,
        description="Goals for this state",
    )
    checks: list[str] = Field(
        default_factory=list,
        description="Precondition checks performed",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Risks identified",
    )
    steps: list[ThinkingStep] = Field(
        default_factory=list,
        description="Reasoning/action steps taken",
    )
    decision: str = Field(
        default="",
        description="Final decision made",
    )
    decision_type: DecisionType = Field(
        default=DecisionType.TRANSITION,
        description="Type of decision made",
    )
    react_cycles: list[ReactStep] = Field(
        default_factory=list,
        description="Complete REACT cycles (if using REACT pattern)",
    )

    def add_step(self, step: ThinkingStep) -> None:
        """Add a thinking step to this frame."""
        self.steps.append(step)

    def add_react_cycle(self, cycle: ReactStep) -> None:
        """Add a complete REACT cycle to this frame."""
        self.react_cycles.append(cycle)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "state": self.state,
            "ts": self.ts.isoformat(),
            "goals": self.goals,
            "checks": self.checks,
            "risks": self.risks,
            "steps": [step.to_dict() for step in self.steps],
            "decision": self.decision,
            "decision_type": self.decision_type.value,
            "react_cycles": [cycle.to_dict() for cycle in self.react_cycles],
        }

    @field_validator("steps", mode="before")
    @classmethod
    def validate_steps(cls, v: Any) -> list[ThinkingStep]:
        """Validate steps are ThinkingStep instances."""
        if v is None:
            return []
        if isinstance(v, list):
            # Convert dicts to ThinkingStep if needed
            return [ThinkingStep(**s) if isinstance(s, dict) else s for s in v]
        return []


class RunLog(BaseModel):
    """Collection of ThinkingFrames with JSON export.

    Maintains a complete trace of the workflow execution,
    including all thinking frames across all states.

    Attributes:
        frames: List of ThinkingFrame objects
        start_time: When the workflow started
        end_time: When the workflow ended
    """

    frames: list[ThinkingFrame] = Field(
        default_factory=list,
        description="List of thinking frames",
    )
    start_time: Optional[datetime] = Field(
        default=None,
        description="Workflow start time",
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="Workflow end time",
    )

    def add(self, frame: ThinkingFrame) -> None:
        """Add a thinking frame to the log."""
        self.frames.append(frame)

    def to_json(self, indent: int = 2) -> str:
        """Export log to JSON string.

        Args:
            indent: Number of spaces for JSON indentation (default: 2)

        Returns:
            JSON string representation of the run log
        """
        return json.dumps(
            {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "frames": [frame.to_dict() for frame in self.frames],
            },
            indent=indent,
        )

    def get_frames_for_state(self, state: str) -> list[ThinkingFrame]:
        """Get all frames for a specific state."""
        return [f for f in self.frames if f.state == state]

    @property
    def frame_count(self) -> int:
        """Get total number of frames."""
        return len(self.frames)


class Todo(BaseModel):
    """Task tracking with evidence links.

    Attributes:
        id: Unique identifier
        title: Task title
        rationale: Why this task is needed
        evidence: Evidence references
        status: Current status
        priority: Priority level
    """

    id: str = Field(..., description="Unique identifier", min_length=1)
    title: str = Field(..., description="Task title", min_length=1)
    rationale: str = Field(..., description="Why this task is needed", min_length=1)
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence references",
    )
    status: str = Field(default="pending", description="Current status")
    priority: str = Field(default="medium", description="Priority level")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "status": self.status,
            "priority": self.priority,
        }


class StructuredContext(BaseModel):
    """Workflow state with context data.

    Maintains the current state of a workflow, including
    changed files, todos, subagent results, and the thinking log.

    Attributes:
        state: Current FSM state (default: "intake")
        changed_files: List of changed files
        todos: Dictionary of todos (id → Todo)
        subagent_results: Results from subagent tasks
        consolidated: Consolidated findings
        evaluation: Final evaluation
        log: RunLog with thinking traces
        user_data: Additional user data
    """

    state: str = Field(
        default="intake",
        description="Current FSM state",
    )
    changed_files: list[str] = Field(
        default_factory=list,
        description="List of changed files",
    )
    todos: dict[str, Todo] = Field(
        default_factory=dict,
        description="Todo items (id → Todo)",
    )
    subagent_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Results from subagent tasks",
    )
    consolidated: dict[str, Any] = Field(
        default_factory=dict,
        description="Consolidated findings",
    )
    evaluation: dict[str, Any] = Field(
        default_factory=dict,
        description="Final evaluation",
    )
    log: RunLog = Field(
        default_factory=RunLog,
        description="RunLog with thinking traces",
    )
    user_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional user data",
    )

    def add_todo(self, todo: Todo) -> None:
        """Add a todo to the context."""
        self.todos[todo.id] = todo

    def get_todo(self, todo_id: str) -> Optional[Todo]:
        """Get a todo by ID."""
        return self.todos.get(todo_id)

    def add_subagent_result(self, task_id: str, result: Any) -> None:
        """Add a subagent result."""
        self.subagent_results[task_id] = result

    def add_frame(self, frame: ThinkingFrame) -> None:
        """Add a thinking frame to the log."""
        self.log.add(frame)

    @property
    def todo_count(self) -> int:
        """Get total number of todos."""
        return len(self.todos)

    @property
    def pending_todos(self) -> list[Todo]:
        """Get pending todos."""
        return [t for t in self.todos.values() if t.status == "pending"]
