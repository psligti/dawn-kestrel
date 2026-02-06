"""
ContextBuilder - Build agent execution context

Assembles provider-ready request inputs including system prompt, tool definitions,
and conversation history with provider compatibility for Anthropic and OpenAI.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from pathlib import Path

from opencode_python.core.agent_types import AgentContext
from opencode_python.core.models import Session, Message, TextPart
from opencode_python.skills.injector import SkillInjector
from opencode_python.tools.framework import ToolRegistry


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
        # Build system prompt from agent + skills + memories
        system_prompt = self._build_system_prompt(agent, skills, memories)

        # Load message history
        messages = await self._build_message_history(session)

        # Determine model from agent or use default
        model: str = "gpt-4o-mini"
        if agent.get("model"):
            model_config = agent["model"]
            if isinstance(model_config, dict):
                # provider/model format
                model_value = model_config.get("model", model)
                if isinstance(model_value, str):
                    model = model_value

        return AgentContext(
            system_prompt=system_prompt,
            tools=tools,
            messages=messages,
            memories=memories or [],
            session=session,
            agent=agent,
            model=model,
        )

    def _format_memories_for_prompt(self, memories: List[Dict[str, Any]]) -> str:
        """
        Format memories for injection into system prompt.

        Creates a concise summary of memories with timestamps and content.

        Args:
            memories: List of memory entries to format

        Returns:
            Formatted memories section string
        """
        if not memories:
            return ""

        lines = ["Relevant memories from previous conversations:"]
        lines.append("")

        for i, memory in enumerate(memories, 1):
            content = memory.get("content", "")
            lines.append(f"{i}. {content}")

        return "\n".join(lines)

    async def _retrieve_memories(
        self,
        session_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for a session.

        This is a stub implementation. When MemoryManager is available,
        this will use MemoryManager.search() to retrieve relevant memories.

        Args:
            session_id: Session ID to retrieve memories for
            limit: Maximum number of memories to retrieve

        Returns:
            List of memory entries
        """
        # TODO: Integrate with MemoryManager.search() when available
        # For now, return empty list
        return []

    def _build_system_prompt(
        self,
        agent: Dict[str, Any],
        skills: List[str],
        memories: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Build system prompt from agent configuration, skills, and memories.

        Args:
            agent: Agent configuration with optional custom prompt
            skills: List of skill names to inject
            memories: Optional list of memory entries to inject

        Returns:
            System instruction string with memories → planning controls → skills → base prompt
        """
        # Format memories if provided (limit to 3-5 memories max)
        memory_section = ""
        if memories:
            memory_section = self._format_memories_for_prompt(memories[:5])

        # Optional planning orchestration controls (for PLAN_AGENT), injected
        # before the skills section and base prompt for deterministic guidance.
        controls_section = ""
        agent_options: Dict[str, Any] = {}
        raw_options = agent.get("options")
        if isinstance(raw_options, dict):
            agent_options = raw_options

        if isinstance(agent_options, dict):
            controls = agent_options.get("planning_orchestration_controls")
            if isinstance(controls, str) and controls.strip():
                controls_section = controls.strip()

        # Get agent base prompt (or use default)
        agent_prompt = agent.get("prompt") or "You are a helpful assistant."

        # Build agent prompt with injected skills
        skills_prompt = self.skill_injector.build_agent_prompt(
            agent_prompt=agent_prompt,
            skill_names=skills,
            default_prompt="You are a helpful assistant.",
        )

        composed_prompt = skills_prompt
        if controls_section:
            composed_prompt = f"{controls_section}\n\n{skills_prompt}"

        # Combine memories + (planning controls + skills + base prompt)
        if memory_section:
            return f"{memory_section}\n\n{composed_prompt}"
        return composed_prompt

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
        tool_definitions: List[Dict[str, Any]] = []

        for _, tool in tools.tools.items():
            # Build tool definition in provider format
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool.id,
                    "description": tool.description,
                    "parameters": tool.parameters(),
                },
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
        llm_messages: List[Dict[str, Any]] = []

        for msg in messages:
            if msg.role == "user":
                # User message: use text directly
                content = msg.text or ""
                llm_messages.append({"role": "user", "content": content})

            elif msg.role == "assistant":
                # Assistant message: concatenate text from parts
                assistant_content: str = ""
                for part in msg.parts:
                    if isinstance(part, TextPart) and hasattr(part, "text"):
                        part_text = part.text
                        if isinstance(part_text, str):
                            assistant_content += part_text
                llm_messages.append({"role": "assistant", "content": assistant_content})

        return llm_messages
