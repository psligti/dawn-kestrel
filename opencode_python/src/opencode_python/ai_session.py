"""
AI Session runner with tool execution integration.

Coordinates streaming requests to AI providers, processes responses,
creates messages/parts, executes tools, manages tokens and costs.
"""

import logging
from typing import AsyncIterator, Optional, Dict, Any, List
from decimal import Decimal

from .core.models import Session, Message, Part, TextPart, ToolPart
from .core.event_bus import bus, Events
from .core.settings import settings
from .providers import (
    get_provider,
    ModelInfo,
    TokenUsage,
    StreamEvent
)
from .ai.tool_execution import ToolExecutionManager
from .tools.framework import ToolResult


logger = logging.getLogger(__name__)


class AISession:
    def __init__(self, session: Session, provider_id: str, model: str, api_key: Optional[str] = None):
        self.session = session
        self.provider_id = provider_id
        self.model = model
        self.api_key = api_key or settings.api_keys.get(provider_id)
        self.provider = get_provider(provider_id, self.api_key)
        self.model_info = self._get_model_info(model)
        self.tool_manager = ToolExecutionManager(session.id, session.directory)

    async def _get_model_info(self, model: str) -> ModelInfo:
        models = await self.provider.get_models()
        for model_info in models:
            if model_info.api_id == model:
                return model_info
        raise ValueError(f"Model {model} not found for provider {self.provider_id}")

    async def process_stream(self, events: AsyncIterator[StreamEvent]) -> List[Part]:
        """Process stream events and create message parts"""
        parts: List[Part] = []
        tool_input: Optional[Dict[str, Any]] = None
        total_cost = Decimal("0")

        async for event in events:
            if event.event_type == "text-delta":
                if parts:
                    parts[-1] = TextPart(
                        **parts[-1].dict(),
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
                    tool_input=tool_input,
                    tool_call_id=tool_call_id,
                    message_id=self.session.id,
                    agent=self.provider_id.value,
                    model=self.model
                )

                parts.append(result.part)
                total_cost += result.metadata.get("cost", Decimal("0"))

            elif event.event_type == "finish":
                finish_reason = event.data.get("finish_reason", "")

                logger.info(f"Stream finished: {finish_reason}")

                if finish_reason == "tool-calls":
                    agent_part = Part(
                        id=f"{self.session.id}_{len(parts)}",
                        session_id=self.session.id,
                        message_id=self.session.id,
                        part_type="agent",
                        agent=self.provider_id.value,
                        time={"created": event.timestamp}
                    )
                    parts.append(agent_part)

        return parts

    async def create_assistant_message(
        self,
        user_message_id: str,
        parts: List[Part],
        tokens: TokenUsage,
        cost: Decimal
    ) -> Message:
        assistant_message = Message(
            id=f"{self.session.id}_{self.session.message_counter}",
            session_id=self.session.id,
            role="assistant",
            parent_id=user_message_id,
            model_id=self.model_info.id,
            provider_id=self.provider_id.value,
            agent=self.provider_id.value,
            path={"root": str(self.session.directory), "cwd": str(self.session.directory)},
            cost=float(cost),
            tokens={"input": tokens.input, "output": tokens.output},
            time={"created": parts[0].time.get("created") if parts else None}
        )

        message_id = await self.session.add_message(assistant_message)

        for part in parts:
            part.message_id = message_id
            await self.session.add_part(part)

        self.session.message_counter += 1
        await bus.publish(Events.MESSAGE_CREATED, {"info": assistant_message.dict()})

        return assistant_message
