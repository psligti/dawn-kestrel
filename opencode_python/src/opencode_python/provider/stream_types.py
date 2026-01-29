"""OpenCode Python - Stream Types and Events"""
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Optional
from pydantic import BaseModel
from typing import Literal, Dict, Any, Optional, Union
import uuid
import logging


logger = logging.getLogger(__name__)



class StreamEvent(BaseModel):
    """Base class for all stream events"""
    id: Optional[str] = Field(default=None)



class TextStartEvent(StreamEvent):
    """Text content starts"""
    type: Literal["text-start"] = "text-start"
    id: str
    parent_id: Optional[str] = None



class TextDeltaEvent(StreamEvent):
    """Text content delta (incremental)"""
    type: Literal["text-delta"] = "text-delta"
    id: str
    text: str = Field(default="")



class TextEndEvent(StreamEvent):
    """Text content ends"""
    type: Literal["text-end"] = "text-end"
    id: str



class ReasoningStartEvent(StreamEvent):
    """Reasoning/thinking starts"""
    type: Literal["reasoning-start"] = "reasoning-start"
    id: str
    parent_id: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class ReasoningDeltaEvent(StreamEvent):
    """Reasoning/thinking delta"""
    type: Literal["reasoning-delta"] = "reasoning-delta"
    id: str
    text: str



class ReasoningEndEvent(StreamEvent):
    """Reasoning/thinking ends"""
    type: Literal["reasoning-end"] = "reasoning-end"
    id: str



class ToolInputStartEvent(StreamEvent):
    """Tool input starts"""
    type: Literal["tool-input-start"] = "tool-input-start"
    id: str
    tool_call_id: str
    tool: str
    input: Dict[str, Any]
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class ToolInputDeltaEvent(StreamEvent):
    """Tool input delta"""
    type: Literal["tool-input-delta"] = "tool-input-delta"
    id: str
    input_delta: Dict[str, Any]



class ToolInputEndEvent(StreamEvent):
    """Tool input ends"""
    type: Literal["tool-input-end"] = "tool-input-end"
    id: str



class ToolCallEvent(StreamEvent):
    """Tool is called"""
    type: Literal["tool-call"] = "tool-call"
    id: str
    tool_call_id: str
    tool_name: str
    input: Dict[str, Any]
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class ToolResultEvent(StreamEvent):
    """Tool execution result"""
    type: Literal["tool-result"] = "tool-result"
    id: str
    tool_call_id: str
    tool_name: str
    output: str
    error: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class ToolErrorEvent(StreamEvent):
    """Tool execution error"""
    type: Literal["tool-error"] = "tool-error"
    id: str
    tool_call_id: str
    tool_name: str
    error: str
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class FinishStepEvent(StreamEvent):
    """LLM turn completes"""
    type: Literal["finish-step"] = "finish-step"
    id: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = Field(default=None)
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)



class FinishEvent(StreamEvent):
    """Full response completes"""
    type: Literal["finish"] = "finish"
    id: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = Field(default=None)
    provider_metadata: Optional[Dict[str, Any]] = Field(default=None)


StreamEvent = (
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


def generate_id() -> str:
    """Generate unique ID"""
    return str(uuid.uuid4())
