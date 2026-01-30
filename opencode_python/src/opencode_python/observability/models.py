"""OpenCode Python - Observability models

Data models for timeline tracking, session status, and safety rails.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import pydantic as pd


class EventType(str, Enum):
    """Timeline event types for categorization"""
    PLAN = "plan"
    TOOL = "tool"
    CODE = "code"
    REVIEW = "review"
    FAILURE = "failure"
    INFO = "info"


class EventLabel(pd.BaseModel):
    """Color-coded label for timeline events"""
    event_type: EventType
    label: str
    color: str
    icon: str
    is_expandable: bool = False

    @classmethod
    def for_type(cls, event_type: EventType) -> "EventLabel":
        """Get label configuration for event type"""
        labels = {
            EventType.PLAN: cls(
                event_type=EventType.PLAN,
                label="Plan",
                color="blue",
                icon="📋",
                is_expandable=True,
            ),
            EventType.TOOL: cls(
                event_type=EventType.TOOL,
                label="Tool",
                color="yellow",
                icon="🔧",
                is_expandable=True,
            ),
            EventType.CODE: cls(
                event_type=EventType.CODE,
                label="Code",
                color="green",
                icon="💻",
                is_expandable=False,
            ),
            EventType.REVIEW: cls(
                event_type=EventType.REVIEW,
                label="Review",
                color="purple",
                icon="🔍",
                is_expandable=True,
            ),
            EventType.FAILURE: cls(
                event_type=EventType.FAILURE,
                label="Failure",
                color="red",
                icon="❌",
                is_expandable=True,
            ),
            EventType.INFO: cls(
                event_type=EventType.INFO,
                label="Info",
                color="gray",
                icon="ℹ️",
                is_expandable=False,
            ),
        }
        return labels[event_type]


class TimelineEvent(pd.BaseModel):
    """Timeline event with label and metadata"""
    id: str
    session_id: str
    event_type: EventType
    timestamp: float = pd.Field(default_factory=lambda: datetime.now().timestamp())
    details: Dict[str, Any] = pd.Field(default_factory=dict)
    is_expandable: bool = False
    error_details: Optional[str] = None

    @property
    def label(self) -> EventLabel:
        """Get label configuration for this event"""
        return EventLabel.for_type(self.event_type)


class SessionStatus(str, Enum):
    """Session status tracking"""
    DRAFT = "draft"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class Blocker(pd.BaseModel):
    """Information about why a session is blocked"""
    session_id: str
    reason: str
    next_steps: List[str] = pd.Field(default_factory=list)
    timestamp: float = pd.Field(default_factory=lambda: datetime.now().timestamp())
    is_resolved: bool = False


class DestructiveAction(str, Enum):
    """Destructive operation types that require confirmation"""
    FORCE_PUSH = "force_push"
    DELETE_BRANCH = "delete_branch"
    DELETE_FILES = "delete_files"
    MASS_REFACTOR = "mass_refactor"
    RESET_HARD = "reset_hard"
    REVERT_COMMIT = "revert_commit"


class DestructiveActionRequest(pd.BaseModel):
    """Request for destructive operation approval"""
    session_id: str
    action: DestructiveAction
    description: str
    impact: str
    timestamp: float = pd.Field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = pd.Field(default_factory=dict)
