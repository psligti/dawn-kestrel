"""
Phase 1 agent execution types and contracts.

Defines the core data models and protocols for agent execution,
including AgentResult, AgentContext, and protocol interfaces.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable, List, Dict, Any, Optional
from dataclasses import dataclass, field

from opencode_python.core.models import (
    Session,
    Message,
    Part,
    TokenUsage,
)
from opencode_python.tools.framework import ToolRegistry


@runtime_checkable
class SessionManagerLike(Protocol):
    """
    Protocol for session management operations.

    Defines the minimal interface required for agent execution
    to interact with session storage and message history.
    """

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        ...

    async def list_messages(self, session_id: str) -> List[Message]:
        """List all messages for a session"""
        ...

    async def add_message(self, message: Message) -> str:
        """Add a message to a session, returns message ID"""
        ...

    async def add_part(self, part: Part) -> str:
        """Add a part to a message, returns part ID"""
        ...


@runtime_checkable
class ProviderLike(Protocol):
    """
    Protocol for AI provider operations.

    Defines the minimal interface required for agent execution
    to interact with AI providers (OpenAI, Anthropic, etc.).
    """

    async def stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        **options: Any,
    ):
        """
        Stream a response from the AI provider.

        Yields streaming events for tokens, tool calls, etc.
        """
        ...

    async def generate(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        **options: Any,
    ) -> Dict[str, Any]:
        """
        Generate a complete response from the AI provider.

        Returns a dict with response, tool_calls, token_usage, etc.
        """
        ...


@dataclass
class AgentResult:
    """
    Result from an agent execution.

    Captures the output and metadata from a single agent run,
    including response text, generated parts, tools used, token usage,
    and execution duration.
    """

    agent_name: str
    """Name of the agent that was executed"""

    response: str
    """Text response from the agent"""

    parts: List[Part] = field(default_factory=list)
    """Parts generated during execution (text, tool, reasoning, etc.)"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional execution metadata"""

    tools_used: List[str] = field(default_factory=list)
    """List of tool IDs used during execution"""

    tokens_used: Optional[TokenUsage] = None
    """Token usage statistics for the execution"""

    duration: float = 0.0
    """Execution duration in seconds"""

    error: Optional[str] = None
    """Error message if execution failed"""

    task_id: Optional[str] = None
    """Task ID if agent was invoked via task tool"""

    model_config = {"extra": "forbid"}


@dataclass
class AgentContext:
    """
    Context for agent execution.

    Bundles all the information needed to execute an agent,
    including system prompt, available tools, conversation history,
    session info, and agent configuration.
    """

    system_prompt: str
    """System prompt for the agent"""

    tools: ToolRegistry
    """Registry of available tools (filtered by permissions)"""

    messages: List[Message]
    """Conversation history for the session"""

    memories: List[Dict[str, Any]] = field(default_factory=list)
    """Agent memories or context snippets"""

    session: Optional[Session] = None
    """Session metadata and configuration"""

    agent: Optional[Dict[str, Any]] = None
    """Agent configuration (name, permissions, etc.)"""

    model: str = "gpt-4o-mini"
    """Model identifier to use for execution"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional context metadata"""

    model_config = {"extra": "forbid"}
