"""TUI-specific model exports and utilities

This module provides the interface expected by TUI components,
re-exporting and adapting core models as needed.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Any
import pydantic as pd

from opencode_python.core.models import (
    ToolState,
    Part,
    Message,
)

MessageData = Message

class MessagePartType(Enum):
    TEXT = "text"
    TOOL = "tool"
    FILE = "file"
    REASONING = "reasoning"
    SNAPSHOT = "snapshot"
    PATCH = "patch"
    AGENT = "agent"
    SUBTASK = "subtask"
    RETRY = "retry"
    COMPACTION = "compaction"

MessagePart = Part
Timestamp = Dict[str, Any]

class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class EventType(str, Enum):
    INFO = "info"
    ERROR = "error"
    CONTEXT_SWITCH = "context_switch"

class SystemEvent(pd.BaseModel):
    event_type: EventType
    text: str
    time: Dict[str, Any] = pd.Field(default_factory=dict)


__all__ = [
    "MessageData",
    "MessagePart",
    "MessagePartType",
    "ToolState",
    "Timestamp",
]
