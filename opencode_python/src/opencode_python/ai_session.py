"""
AI Session runner with tool execution integration.

Coordinates streaming requests to AI providers, processes responses,
creates messages/parts, executes tools, manages tokens and costs.
"""

import logging
from typing import AsyncIterator, Optional, Dict, Any, List
from decimal import Decimal

from .core.models import Session, Message, Part, TextPart, ToolPart, AgentPart, ToolState
from .providers.base import ProviderID, ModelInfo
from .core.event_bus import bus, Events
from .core.settings import settings
from .providers import (
    get_provider,
    ModelInfo,
    TokenUsage,
    StreamEvent
)
from .ai.tool_execution import ToolExecutionManager


logger = logging.getLogger(__name__)


class AISession:
    def __init__(
        self,
        session: Session,
        provider_id: str,
        model: str,
        api_key: Optional[str] = None,
        session_manager=None
    ):
        self.session = session
        self.provider_id = provider_id
        self.model = model
        self.session_manager = session_manager
        api_key_value = api_key or settings.api_keys.get(provider_id)
        provider_enum = ProviderID(provider_id) if isinstance(provider_id, str) else provider_id
        get_secret_method = getattr(api_key_value, "get_secret_value", None)
        if api_key_value and get_secret_method:
            api_key_str = get_secret_method()
        else:
            api_key_str = str(api_key_value) if api_key_value else ""
        self.provider = get_provider(provider_enum, api_key_str)
        self.model_info: Optional[ModelInfo] = None
        self.tool_manager = ToolExecutionManager(session.id)

    async def _get_model_info(self, model: str) -> ModelInfo:
        if self.provider is None:
            raise ValueError(f"Provider not initialized for {self.provider_id}")

        models = await self.provider.get_models()
        for model_info in models:
            if model_info.api_id == model:
                return model_info
        raise ValueError(f"Model {model} not found for provider {self.provider_id}")

    async def _ensure_model_info(self) -> ModelInfo:
        """Ensure model_info is loaded"""
        if self.model_info is None:
            self.model_info = await self._get_model_info(self.model)
        return self.model_info

    async def process_stream(self, events: AsyncIterator[StreamEvent]) -> tuple[List[Part], TokenUsage]:
        """Process stream events and create message parts"""
        parts: List[Part] = []
        tool_input: Optional[Dict[str, Any]] = None
        total_cost = Decimal("0")
        usage = TokenUsage(input=0, output=0, reasoning=0, cache_read=0, cache_write=0)

        async for event in events:
            if event.event_type == "finish":
                usage_data = event.data.get("usage", {})
                if usage_data:
                    usage = TokenUsage(
                        input=usage_data.get("prompt_tokens", 0),
                        output=usage_data.get("completion_tokens", 0),
                        reasoning=usage_data.get("reasoning_tokens", 0),
                        cache_read=usage_data.get("cache_read_tokens", 0),
                        cache_write=usage_data.get("cache_write_tokens", 0)
                    )

            if event.event_type == "text-delta":
                if parts and isinstance(parts[-1], TextPart):
                    existing = parts[-1].model_dump()
                    existing.pop("text", None)
                    existing.pop("time", None)
                    parts[-1] = TextPart(
                        **existing,
                        text=parts[-1].text + event.data.get("delta", ""),
                        time={"updated": event.timestamp}
                    )
                else:
                    parts.append(TextPart(
                        id=f"{self.session.id}_{len(parts)}",
                        session_id=self.session.id,
                        message_id=self.session.id,
                        part_type="text",
                        text=event.data.get("delta", ""),
                        time={"created": event.timestamp}
                    ))

            elif event.event_type == "tool-call":
                tool_name = event.data.get("tool", "")
                tool_input = event.data.get("input", {})
                tool_call_id = event.data.get("call_id", f"{self.session.id}_{tool_name}_{len(parts)}")

                result = await self.tool_manager.execute_tool_call(
                    tool_name=tool_name,
                    tool_input=tool_input or {},
                    tool_call_id=tool_call_id,
                    message_id=self.session.id,
                    agent=str(self.provider_id),
                    model=self.model
                )

                # Create ToolPart from result
                tool_part = ToolPart(
                    id=f"{self.session.id}_{tool_call_id}",
                    session_id=self.session.id,
                    message_id=self.session.id,
                    part_type="tool",
                    tool=tool_name,
                    call_id=tool_call_id,
                    state=ToolState(status="completed", input=tool_input or {}, output=result.output),
                    source={"provider": self.model}
                )
                parts.append(tool_part)
                total_cost += result.metadata.get("cost", Decimal("0"))

            elif event.event_type == "finish":
                finish_reason = event.data.get("finish_reason", "")

                logger.info(f"Stream finished: {finish_reason}")

                if finish_reason == "tool-calls":
                    agent_part = AgentPart(
                        id=f"{self.session.id}_{len(parts)}",
                        session_id=self.session.id,
                        message_id=self.session.id,
                        part_type="agent",
                        name=str(self.provider_id),
                        source={"provider": self.model}
                    )
                    parts.append(agent_part)

        return parts, usage

    async def create_assistant_message(
        self,
        user_message_id: str,
        parts: List[Part],
        tokens: TokenUsage,
        cost: Decimal
    ) -> Message:
        await self._ensure_model_info()
        created_time = None
        if parts and isinstance(parts[0], TextPart):
            created_time = parts[0].time.get("created")

        assistant_text = ""
        for part in parts:
            if isinstance(part, TextPart) and part.text:
                assistant_text += part.text

        assistant_message = Message(
            id=f"{self.session.id}_{self.session.message_counter}",
            session_id=self.session.id,
            role="assistant",
            text=assistant_text,
            parts=parts,
            time={"created": created_time},
            metadata={
                "parent_id": user_message_id,
                "model_id": self.model_info.id if self.model_info else "",
                "provider_id": str(self.provider_id),
                "agent": str(self.provider_id),
                "path": {"root": str(self.session.directory), "cwd": str(self.session.directory)},
                "cost": float(cost),
                "tokens": {"input": tokens.input, "output": tokens.output},
            }
        )

        if self.session_manager:
            message_id = await self.session_manager.add_message(assistant_message)

            for part in parts:
                part.message_id = message_id
                await self.session_manager.add_part(part)
        else:
            message_id = assistant_message.id

        self.session.message_counter += 1
        await bus.publish(Events.MESSAGE_CREATED, {"info": assistant_message.model_dump()})

        return assistant_message

    async def process_message(
        self,
        user_message: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Process a user message through AI provider

        Args:
            user_message: The user's message text
            options: Additional options (temperature, top_p, etc.)

        Returns:
            The assistant's response message
        """
        logger.debug(f"[{self.session.slug}] Prompt to LLM ({len(user_message)} chars)")
        if options:
            logger.debug(f"[{self.session.slug}] LLM Options: {options}")

        # Create user message
        user_msg = Message(
            id=f"{self.session.id}_{self.session.message_counter}",
            session_id=self.session.id,
            role="user",
            time={"created": self._now()},
            text=user_message,
        )

        if self.session_manager:
            user_msg_id = await self.session_manager.add_message(user_msg)
            messages = await self.session_manager.list_messages(self.session.id)
        else:
            user_msg_id = user_msg.id
            messages = [user_msg]
        self.session.message_counter += 1

        # Build LLM messages (convert to provider format)
        llm_messages = self._build_llm_messages(messages)

        # Get tools available
        tools = self._get_tool_definitions()

        # Call provider stream
        if self.provider:
            model_info = await self._ensure_model_info()
            stream = self.provider.stream(
                model_info,
                llm_messages,
                tools,
                options or {}
            )

            # Process stream and create parts
            parts, tokens = await self.process_stream(stream)
        else:
            parts = []

        
        # Calculate cost
        if self.provider:
            model_info = await self._ensure_model_info()
            cost = self.provider.calculate_cost(tokens, model_info)
        else:
            cost = Decimal("0")

        # Create assistant message
        assistant_message = await self.create_assistant_message(
            user_msg_id,
            parts,
            tokens,
            cost
        )

        # Increment session message counter
        self.session.message_counter += 1

        logger.debug(f"[{self.session.slug}] Response from LLM ({len(assistant_message.text)} chars, {tokens.input}+{tokens.output} tokens)")

        return assistant_message

    def _now(self) -> int:
        """Get current timestamp in milliseconds"""
        import time
        return int(time.time() * 1000)

    def _build_llm_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Build LLM-format messages from OpenCode messages"""
        llm_messages = []

        for msg in messages:
            if msg.role == "user":
                content = msg.text or ""
                llm_messages.append({"role": "user", "content": content})
            elif msg.role == "assistant":
                # Extract text from parts
                content: str = ""
                for part in msg.parts:
                    if isinstance(part, TextPart) and hasattr(part, "text"):
                        content += part.text
                llm_messages.append({"role": "assistant", "content": content})

        return llm_messages

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for LLM"""
        tools = self.tool_manager.tool_registry.tools
        tool_definitions = []

        for tool_id, tool in tools.items():
            tool_definitions.append({
                "type": "function",
                "function": {
                    "name": tool.id,
                    "description": tool.description,
                    "parameters": tool.parameters()
                }
            })

        return tool_definitions
