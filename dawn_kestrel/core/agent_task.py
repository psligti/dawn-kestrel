"""
Phase 3: Multi-Agent Orchestration - AgentTask Model.

Defines tasks for agent execution in multi-agent workflows.
Supports dependencies, hierarchical sub-tasks, and result tracking.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
import uuid


class TaskStatus(str, Enum):
    """Status of a task in the execution lifecycle."""

    PENDING = "pending"
    """Task is queued, waiting to start"""

    RUNNING = "running"
    """Task is currently executing"""

    COMPLETED = "completed"
    """Task completed successfully"""

    FAILED = "failed"
    """Task execution failed"""

    CANCELLED = "cancelled"
    """Task was cancelled before completion"""


@dataclass
class AgentTask:
    """
    Define a task for agent execution.

    Represents a unit of work that can be delegated to an agent,
    with support for dependencies and hierarchical task chains.

    Attributes:
        task_id: Unique identifier for this task
        parent_id: Optional parent task ID (for hierarchical sub-tasks)
        agent_name: Name of the agent to execute this task
        description: Human-readable description of the task
        tool_ids: List of tool IDs available to the agent
        skill_names: List of skill names to inject into context
        options: Additional execution options (model, temperature, etc.)
        status: Current task status
        result_id: ID of the AgentResult from execution (if completed)
        result_agent_name: Name of the agent that produced the result
        error: Error message if task failed
        metadata: Additional task metadata
    """

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique identifier for this task"""

    parent_id: Optional[str] = None
    """Optional parent task ID (for hierarchical sub-tasks)"""

    agent_name: str = ""
    """Name of the agent to execute this task"""

    description: str = ""
    """Human-readable description of the task"""

    tool_ids: List[str] = field(default_factory=list)
    """List of tool IDs available to the agent"""

    skill_names: List[str] = field(default_factory=list)
    """List of skill names to inject into context"""

    options: Dict[str, Any] = field(default_factory=dict)
    """Additional execution options (model, temperature, etc.)"""

    status: TaskStatus = TaskStatus.PENDING
    """Current task status"""

    result_id: Optional[str] = None
    """ID of the AgentResult from execution (if completed)"""

    result_agent_name: Optional[str] = None
    """Name of the agent that produced the result"""

    error: Optional[str] = None
    """Error message if task failed"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional task metadata"""

    model_config = {"extra": "forbid"}

    def has_dependencies(self) -> bool:
        """Check if this task has a parent (dependency)."""
        return self.parent_id is not None

    def is_complete(self) -> bool:
        """Check if task is in a terminal state (completed, failed, or cancelled)."""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def is_active(self) -> bool:
        """Check if task is currently running or pending."""
        return self.status in (TaskStatus.PENDING, TaskStatus.RUNNING)

    def can_start(self) -> bool:
        """Check if task is ready to start (pending status)."""
        return self.status == TaskStatus.PENDING


def create_agent_task(
    agent_name: str,
    description: str,
    tool_ids: Optional[List[str]] = None,
    skill_names: Optional[List[str]] = None,
    options: Optional[Dict[str, Any]] = None,
    parent_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AgentTask:
    """
    Factory function to create an AgentTask.

    Args:
        agent_name: Name of the agent to execute this task
        description: Human-readable description of the task
        tool_ids: Optional list of tool IDs available to the agent
        skill_names: Optional list of skill names to inject into context
        options: Optional additional execution options
        parent_id: Optional parent task ID (for hierarchical sub-tasks)
        metadata: Optional additional task metadata

    Returns:
        New AgentTask instance
    """
    return AgentTask(
        agent_name=agent_name,
        description=description,
        tool_ids=tool_ids or [],
        skill_names=skill_names or [],
        options=options or {},
        parent_id=parent_id,
        metadata=metadata or {},
    )
