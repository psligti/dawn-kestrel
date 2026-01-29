"""OpenCode Python - Core data models with Pydantic"""
from __future__ import annotations
from typing import Literal, Optional, Union, Any, Dict, List
from datetime import datetime
from pathlib import Path
import logging
import pydantic as pd


logger = logging.getLogger(__name__)


class ToolState(pd.BaseModel):
    """Tool execution state"""
    status: Literal["pending", "running", "completed", "error"]
    input: Dict[str, Any] = pd.Field(default_factory=dict)
    output: Optional[str] = None
    title: Optional[str] = None
    metadata: Dict[str, Any] = pd.Field(default_factory=dict)
    time_start: Optional[float] = None
    time_end: Optional[float] = None
    error: Optional[str] = None


class FileInfo(pd.BaseModel):
    """File information"""
    path: str
    mime: str
    filename: Optional[str] = None
    size: int = 0
    last_modified: Optional[float] = None


class TextPart(pd.BaseModel):
    """Text content part"""
    id: str
    session_id: str
    message_id: str
    part_type: Literal["text"]
    text: str
    time: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None
    synthetic: Optional[bool] = None
    ignored: Optional[bool] = None


class FilePart(pd.BaseModel):
    """File attachment part"""
    id: str
    session_id: str
    message_id: str
    part_type: Literal["file"]
    url: str
    mime: str
    filename: Optional[str] = None
    source: Optional[Dict[str, Any]] = None


class ToolPart(pd.BaseModel):
    """Tool execution part"""
    id: str
    session_id: str
    message_id: str
    part_type: Literal["tool"]
    tool: str
    call_id: Optional[str] = None
    state: ToolState
    source: Optional[Dict[str, Any]] = None


class ReasoningPart(pd.BaseModel):
    """LLM reasoning/thinking part"""
    id: str
    session_id: str
    message_id: str
    part_type: Literal["reasoning"]
    text: str
    time: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None


class SnapshotPart(pd.BaseModel):
    """Git snapshot part"""
    id: str
    session_id: str
    message_id: str
    part_type: Literal["snapshot"]
    snapshot: str


class PatchPart(pd.BaseModel):
    """File patch summary part"""
    id: str
    session_id: str
    message_id: str
    part_type: Literal["patch"]
    hash: str
    files: List[str]


class AgentPart(pd.BaseModel):
    """Agent delegation part"""
    id: str
    session_id: str
    message_id: str
    part_type: Literal["agent"]
    name: str
    source: Optional[Dict[str, Any]] = None


class SubtaskPart(pd.BaseModel):
    """Subtask invocation part"""
    id: str
    session_id: str
    message_id: str
    part_type: Literal["subtask"]
    session_id: str
    category: str


class RetryPart(pd.BaseModel):
    """Retry attempt part"""
    id: str
    session_id: str
    message_id: str
    part_type: Literal["retry"]
    attempt: int


class CompactionPart(pd.BaseModel):
    """Session compaction marker part"""
    id: str
    session_id: str
    message_id: str
    part_type: Literal["compaction"]
    auto: bool


# Union type for all part types
Part = Union[
    TextPart,
    FilePart,
    ToolPart,
    ReasoningPart,
    SnapshotPart,
    PatchPart,
    AgentPart,
    SubtaskPart,
    RetryPart,
    CompactionPart,
]


class TokenUsage(pd.BaseModel):
    """Token usage tracking"""
    input: int = 0
    output: int = 0
    reasoning: int = 0
    cache: Dict[str, int] = {"read": 0, "write": 0}


class Message(pd.BaseModel):
    """Message model - container for parts"""
    id: str
    session_id: str
    role: Literal["user", "assistant", "system"]
    time: Dict[str, Any] = pd.Field(default_factory=dict)
    text: str = ""
    parts: List[Union[TextPart, FilePart, ToolPart, ReasoningPart, SnapshotPart, PatchPart, AgentPart, SubtaskPart, RetryPart, CompactionPart]] = []
    summary: Optional[MessageSummary] = None
    token_usage: Optional[TokenUsage] = None
    metadata: Dict[str, Any] = pd.Field(default_factory=dict)

    model_config = pd.ConfigDict(extra="forbid")


class MessageSummary(pd.BaseModel):
    """Message summary info"""
    title: Optional[str] = None
    body: Optional[str] = None
    diffs: Optional[List[Dict[str, Any]]] = None


class UserMessage(Message):
    """User message - alias for Message with role='user'"""
    pass


class AssistantMessage(Message):
    """Assistant message - alias for Message with role='assistant'"""
    """Message summary info"""
    title: Optional[str] = None
    body: Optional[str] = None
    diffs: Optional[List[Dict[str, Any]]] = None


class SessionShare(pd.BaseModel):
    """Session share metadata"""
    url: Optional[str] = None


class SessionRevert(pd.BaseModel):
    """Session revert state"""
    message_id: str
    part_id: Optional[str] = None
    snapshot: str
    diff: Optional[str] = None


class Session(pd.BaseModel):
    """Session model"""
    id: str
    slug: str
    project_id: str
    directory: str
    parent_id: Optional[str] = None
    title: str
    version: str
    summary: Optional[MessageSummary] = None
    share: Optional[SessionShare] = None
    permission: Optional[List[Dict[str, Any]]] = None
    revert: Optional[SessionRevert] = None
    time_created: float = pd.Field(default_factory=lambda: datetime.now().timestamp())
    time_updated: float = pd.Field(default_factory=lambda: datetime.now().timestamp())
    time_compacting: Optional[float] = None
    time_archived: Optional[float] = None
    permission: Optional[List[Dict[str, Any]]] = None
    revert: Optional[SessionRevert] = None

    model_config = pd.ConfigDict(
        extra="forbid"
    )
