"""
Phase 1 agent execution types and contracts.

Defines the core data models and protocols for agent execution,
including AgentResult, AgentContext, and protocol interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from dawn_kestrel.core.models import (
    Message,
    Part,
    Session,
    TokenUsage,
)
from dawn_kestrel.tools.framework import ToolRegistry


@runtime_checkable
class SessionManagerLike(Protocol):
    """
    Protocol for session management operations.

    Defines the minimal interface required for agent execution
    to interact with session storage and message history.
    """

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID"""
        ...

    async def list_messages(self, session_id: str) -> list[Message]:
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
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
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
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        **options: Any,
    ) -> dict[str, Any]:
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

    parts: list[Part] = field(default_factory=list)
    """Parts generated during execution (text, tool, reasoning, etc.)"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional execution metadata"""

    tools_used: list[str] = field(default_factory=list)
    """List of tool IDs used during execution"""

    tokens_used: TokenUsage | None = None
    """Token usage statistics for the execution"""

    duration: float = 0.0
    """Execution duration in seconds"""

    error: str | None = None
    """Error message if execution failed"""

    task_id: str | None = None
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

    messages: list[Message]
    """Conversation history for the session"""

    memories: list[dict[str, Any]] = field(default_factory=list)
    """Agent memories or context snippets"""

    session: Session | None = None
    """Session metadata and configuration"""

    agent: dict[str, Any] | None = None
    """Agent configuration (name, permissions, etc.)"""

    model: str = "gpt-4o-mini"
    """Model identifier to use for execution"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional context metadata"""

    workspace_id: str | None = None
    """Workspace identifier for isolation (e.g., multi-tenant)"""

    credential_scope: str | None = None
    """Credential scope for per-repo/per-org credential resolution"""

    config_overrides: dict[str, Any] = field(default_factory=dict)
    """Session-specific configuration overrides"""

    model_config = {"extra": "forbid"}
