"""OpenCode Python - Core data models with Pydantic"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal, Union

import pydantic as pd

logger = logging.getLogger(__name__)


class ToolState(pd.BaseModel):
    """Tool execution state"""

    status: Literal["pending", "running", "completed", "error"]
    input: dict[str, Any] = pd.Field(default_factory=dict)
    output: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = pd.Field(default_factory=dict)
    time_start: float | None = None
    time_end: float | None = None
    error: str | None = None


class FileInfo(pd.BaseModel):
    """File information"""

    path: str
    mime: str
    filename: str | None = None
    size: int = 0
    last_modified: float | None = None


class TextPart(pd.BaseModel):
    """Text content part"""

    id: str
    session_id: str
    message_id: str
    part_type: Literal["text"]
    text: str
    time: dict[str, Any] = {}
    metadata: dict[str, Any] | None = None
    synthetic: bool | None = None
    ignored: bool | None = None


class FilePart(pd.BaseModel):
    """File attachment part"""

    id: str
    session_id: str
    message_id: str
    part_type: Literal["file"]
    url: str
    mime: str
    filename: str | None = None
    source: dict[str, Any] | None = None


class ToolPart(pd.BaseModel):
    """Tool execution part"""

    id: str
    session_id: str
    message_id: str
    part_type: Literal["tool"]
    tool: str
    call_id: str | None = None
    state: ToolState
    source: dict[str, Any] | None = None


class ReasoningPart(pd.BaseModel):
    """LLM reasoning/thinking part"""

    id: str
    session_id: str
    message_id: str
    part_type: Literal["reasoning"]
    text: str
    time: dict[str, Any] = {}
    metadata: dict[str, Any] | None = None


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
    files: list[str]


class AgentPart(pd.BaseModel):
    """Agent delegation part"""

    id: str
    session_id: str
    message_id: str
    part_type: Literal["agent"]
    name: str
    source: dict[str, Any] | None = None


class SubtaskPart(pd.BaseModel):
    """Subtask invocation part"""

    id: str
    session_id: str
    message_id: str
    part_type: Literal["subtask"]
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
    cache_read: int = 0
    cache_write: int = 0


class Message(pd.BaseModel):
    """Message model - container for parts"""

    id: str
    session_id: str
    role: Literal["user", "assistant", "system"]
    time: dict[str, Any] = pd.Field(default_factory=dict)
    text: str = ""
    parts: list[
        TextPart
        | FilePart
        | ToolPart
        | ReasoningPart
        | SnapshotPart
        | PatchPart
        | AgentPart
        | SubtaskPart
        | RetryPart
        | CompactionPart
    ] = []
    summary: MessageSummary | None = None
    token_usage: TokenUsage | None = None
    metadata: dict[str, Any] = pd.Field(default_factory=dict)

    model_config = pd.ConfigDict(extra="forbid")


class MessageSummary(pd.BaseModel):
    """Message summary info"""

    title: str | None = None
    body: str | None = None
    diffs: list[dict[str, Any]] | None = None


class UserMessage(Message):
    """User message - alias for Message with role='user'"""

    pass


class AssistantMessage(Message):
    """Assistant message - alias for Message with role='assistant'"""

    finish: str | None = None
    """Message summary info"""
    title: str | None = None
    body: str | None = None
    diffs: list[dict[str, Any]] | None = None


class SessionShare(pd.BaseModel):
    """Session share metadata"""

    url: str | None = None


class SessionRevert(pd.BaseModel):
    """Session revert state"""

    message_id: str
    part_id: str | None = None
    snapshot: str
    diff: str | None = None


class Session(pd.BaseModel):
    """Session model"""

    id: str
    slug: str
    project_id: str
    directory: str
    parent_id: str | None = None
    title: str
    version: str
    summary: MessageSummary | None = None
    share: SessionShare | None = None
    permission: list[dict[str, Any]] | None = None
    revert: SessionRevert | None = None
    time_created: float = pd.Field(default_factory=lambda: datetime.now().timestamp())
    time_updated: float = pd.Field(default_factory=lambda: datetime.now().timestamp())
    time_compacting: float | None = None
    time_archived: float | None = None
    message_counter: int = pd.Field(default=0, description="Counter for generated message IDs")
    message_count: int = pd.Field(default=0, description="Total number of messages in session")
    total_cost: float = pd.Field(default=0.0, description="Total cost of session in USD")
    metadata: dict[str, Any] = pd.Field(default_factory=dict)

    model_config = pd.ConfigDict(extra="forbid")


class Memory(pd.BaseModel):
    """Memory model - stores agent memories with embeddings"""

    id: str
    session_id: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = pd.Field(default_factory=dict)
    created: float = pd.Field(default_factory=lambda: datetime.now().timestamp())

    model_config = pd.ConfigDict(extra="forbid")


class MemorySummary(pd.BaseModel):
    """Memory summary model for compressed conversation history"""

    session_id: str
    summary: str = ""
    key_points: list[str] = pd.Field(default_factory=list)
    original_token_count: int = 0
    compressed_token_count: int = 0
    compression_ratio: float = 1.0
    timestamp: float = pd.Field(default_factory=lambda: datetime.now().timestamp())

    @pd.computed_field
    @property
    def target_compression(self) -> float:
        """Target compression ratio (0.5 = 50% reduction)"""
        return 0.5

    model_config = pd.ConfigDict(extra="forbid")
