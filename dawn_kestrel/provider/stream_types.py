"""OpenCode Python - Stream Types and Events"""
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Optional
import uuid
import logging


logger = logging.getLogger(__name__)


def generate_id() -> str:
    return str(uuid.uuid4())


class StreamEvent(BaseModel):
    """Base class for all stream events"""
    id: str = Field(default_factory=generate_id)



class TextStartEvent(StreamEvent):
    """Text content starts"""
    type: Literal["text-start"] = "text-start"
    parent_id: Optional[str] = None



class TextDeltaEvent(StreamEvent):
    """Text content delta (incremental)"""
    type: Literal["text-delta"] = "text-delta"
    text: str = Field(default="")



class TextEndEvent(StreamEvent):
    """Text content ends"""
    type: Literal["text-end"] = "text-end"



class ReasoningStartEvent(StreamEvent):
    """Reasoning/thinking starts"""
    type: Literal["reasoning-start"] = "reasoning-start"
    parent_id: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class ReasoningDeltaEvent(StreamEvent):
    """Reasoning/thinking delta"""
    type: Literal["reasoning-delta"] = "reasoning-delta"
    text: str



class ReasoningEndEvent(StreamEvent):
    """Reasoning/thinking ends"""
    type: Literal["reasoning-end"] = "reasoning-end"



class ToolInputStartEvent(StreamEvent):
    """Tool input starts"""
    type: Literal["tool-input-start"] = "tool-input-start"
    tool_call_id: str
    tool: str
    input: Dict[str, Any]
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class ToolInputDeltaEvent(StreamEvent):
    """Tool input delta"""
    type: Literal["tool-input-delta"] = "tool-input-delta"
    input_delta: Dict[str, Any]



class ToolInputEndEvent(StreamEvent):
    """Tool input ends"""
    type: Literal["tool-input-end"] = "tool-input-end"



class ToolCallEvent(StreamEvent):
    """Tool is called"""
    type: Literal["tool-call"] = "tool-call"
    tool_call_id: str
    tool_name: str
    input: Dict[str, Any]
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class ToolResultEvent(StreamEvent):
    """Tool execution result"""
    type: Literal["tool-result"] = "tool-result"
    tool_call_id: str
    tool_name: str
    output: str
    error: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class ToolErrorEvent(StreamEvent):
    """Tool execution error"""
    type: Literal["tool-error"] = "tool-error"
    tool_call_id: str
    tool_name: str
    error: str
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class FinishStepEvent(StreamEvent):
    """LLM turn completes"""
    type: Literal["finish-step"] = "finish-step"
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = Field(default=None)
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class FinishEvent(StreamEvent):
    """Full response completes"""
    type: Literal["finish"] = "finish"
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = Field(default=None)
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)


AnyStreamEvent = (
    TextStartEvent
    | TextDeltaEvent
    | TextEndEvent
    | ReasoningStartEvent
    | ReasoningDeltaEvent
    | ReasoningEndEvent
    | ToolInputStartEvent
    | ToolInputDeltaEvent
    | ToolInputEndEvent
    | ToolCallEvent
    | ToolResultEvent
    | ToolErrorEvent
    | FinishStepEvent
    | FinishEvent
)

