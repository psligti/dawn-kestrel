"""
ContextBuilder - Build agent execution context

Assembles provider-ready request inputs including system prompt, tool definitions,
and conversation history with provider compatibility for Anthropic and OpenAI.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from opencode_python.core.agent_types import AgentContext
from opencode_python.core.models import Session, Message, TextPart, ToolPart
from opencode_python.skills.injector import SkillInjector
from opencode_python.tools.framework import ToolRegistry
from opencode_python.core.agent_types import SessionManagerLike


class ContextBuilder:
    """Build agent execution context for provider calls.

    Coordinates:
    - System prompt via SkillInjector
    - Tool schemas from filtered registry
    - Message history via SessionManager
    - Provider-specific formatting (Anthropic vs OpenAI)
    """

    def __init__(
        self,
        base_dir: Path,
        skill_max_char_budget: Optional[int] = None,
    ):
        """
        Initialize context builder.

        Args:
            base_dir: Base directory for skill discovery
            skill_max_char_budget: Optional maximum characters for injected skills
        """
        self.skill_injector = SkillInjector(
            base_dir=base_dir,
            max_char_budget=skill_max_char_budget,
        )

    async def build_agent_context(
        self,
        session: Session,
        agent: Dict[str, Any],
        tools: ToolRegistry,
        skills: List[str],
        memories: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentContext:
        """
        Build complete agent execution context.

        Args:
            session: Session metadata and configuration
            agent: Agent configuration (name, permissions, prompt, etc.)
            tools: Registry of available tools (filtered by permissions)
            skills: List of skill names to inject
            memories: Agent memories or context snippets

        Returns:
            AgentContext with all components for execution
        """
        # Build system prompt from agent + skills
        system_prompt = self._build_system_prompt(agent, skills)

        # Load message history
        messages = await self._build_message_history(session)

        # Determine model from agent or use default
        model = "gpt-4o-mini"
        if agent.get("model"):
            model_config = agent["model"]
            if isinstance(model_config, dict):
                # provider/model format
                model = model_config.get("model", model)

        return AgentContext(
            system_prompt=system_prompt,
            tools=tools,
            messages=messages,
            memories=memories or [],
            session=session,
            agent=agent,
            model=model,
        )

    def _build_system_prompt(
        self,
        agent: Dict[str, Any],
        skills: List[str],
    ) -> str:
        """
        Build system prompt from agent configuration and skills.

        Args:
            agent: Agent configuration with optional custom prompt
            skills: List of skill names to inject

        Returns:
            System instruction string with skills injected before base prompt
        """
        # Get agent base prompt (or use default)
        agent_prompt = agent.get("prompt") or "You are a helpful assistant."

        # Build agent prompt with injected skills
        return self.skill_injector.build_agent_prompt(
            agent_prompt=agent_prompt,
            skill_names=skills,
            default_prompt="You are a helpful assistant.",
        )

    def build_provider_context(
        self,
        context: AgentContext,
        provider_id: str,
    ) -> Dict[str, Any]:
        """
        Build provider-specific context for API call.

        Converts AgentContext to provider-specific format:
        - Anthropic: dedicated `system` field + tool list
        - OpenAI: `system` role message + tool list

        Args:
            context: Agent context to convert
            provider_id: Provider identifier (anthropic, openai, etc.)

        Returns:
            Dict with keys: system, messages, tools for provider call
        """
        # Build message history for provider
        messages = self._build_llm_messages(context.messages)

        # Build tool schemas for provider
        tools = self._build_tool_schemas(context.tools)

        # Provider-specific formatting
        if provider_id == "anthropic":
            # Anthropic uses dedicated system field
            return {
                "system": context.system_prompt,
                "messages": messages,
                "tools": tools,
            }
        else:
            # OpenAI uses system role message
            system_message = {
                "role": "system",
                "content": context.system_prompt,
            }
            all_messages = [system_message] + messages

            return {
                "system": None,  # OpenAI uses role message instead
                "messages": all_messages,
                "tools": tools,
            }

    def _build_tool_schemas(
        self,
        tools: ToolRegistry,
    ) -> List[Dict[str, Any]]:
        """
        Build tool schemas from tool registry for provider call.

        Converts Tool objects to provider-compatible format.

        Args:
            tools: Tool registry with available tools

        Returns:
            List of tool definitions in provider format
        """
        tool_definitions = []

        for tool_id, tool in tools.tools.items():
            # Build tool definition in provider format
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool.id,
                    "description": tool.description,
                    "parameters": tool.parameters(),
                }
            }
            tool_definitions.append(tool_def)

        return tool_definitions

    async def _build_message_history(
        self,
        session: Session,
    ) -> List[Message]:
        """
        Load message history from session.

        Note: This is a placeholder. In a full implementation,
        this would use SessionManager.list_messages() to load
        the conversation history from storage.

        Args:
            session: Session to load messages from

        Returns:
            List of messages from the session
        """
        # For now, return empty list
        # This will be integrated with SessionManager in AgentRuntime
        return []

    def _build_llm_messages(
        self,
        messages: List[Message],
    ) -> List[Dict[str, Any]]:
        """
        Build LLM-format messages from OpenCode messages.

        Extracted/generalized from AISession._build_llm_messages().

        Converts OpenCode Message objects (with Parts) to provider format:
        - user: text from message.text
        - assistant: concatenated text from TextParts

        Args:
            messages: List of OpenCode Message objects

        Returns:
            List of provider-format messages
        """
        llm_messages = []

        for msg in messages:
            if msg.role == "user":
                # User message: use text directly
                content = msg.text or ""
                llm_messages.append({"role": "user", "content": content})

            elif msg.role == "assistant":
                # Assistant message: concatenate text from parts
                content: str = ""
                for part in msg.parts:
                    if isinstance(part, TextPart) and hasattr(part, "text"):
                        content += part.text
                llm_messages.append({"role": "assistant", "content": content})

        return llm_messages
