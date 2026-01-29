"""
OpenAI Provider implementation.

Streaming support, token counting, and cost calculation.
"""

import asyncio
import httpx
from decimal import Decimal
from typing import AsyncIterator, Dict, Any

from .base import (
    ModelInfo,
    ModelCapabilities,
    ModelCost,
    ModelLimits,
    TokenUsage,
    StreamEvent,
    ProviderID
)


class OpenAIProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    async def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id="gpt-5",
                provider_id=ProviderID.OPENAI,
                api_id="gpt-5",
                api_url=self.base_url,
                name="GPT-5",
                family="gpt",
                capabilities=ModelCapabilities(
                    temperature=True,
                    reasoning=True,
                    toolcall=True,
                    input={"text": True}
                ),
                cost=ModelCost(
                    input=Decimal("15.00"),
                    output=Decimal("150.00"),
                    cache={}
                ),
                limit=ModelLimits(
                    context=1000000,
                    input=1000000,
                    output=100000
                ),
                status="active"
            ),
            ModelInfo(
                id="gpt-5-nano",
                provider_id=ProviderID.OPENAI,
                api_id="gpt-5-nano",
                api_url=self.base_url,
                name="GPT-5 Nano",
                family="gpt",
                capabilities=ModelCapabilities(
                    temperature=True,
                    reasoning=True,
                    toolcall=True,
                    input={"text": True}
                ),
                cost=ModelCost(
                    input=Decimal("0.15"),
                    output=Decimal("0.60"),
                    cache={}
                ),
                limit=ModelLimits(
                    context=1000000,
                    input=1000000,
                    output=3000
                ),
                status="active"
            )
        ]

    async def stream(self, model: ModelInfo, messages: list, tools: dict, options: Dict[str, Any] = None) -> AsyncIterator[StreamEvent]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if options:
            headers.update({
                "OpenAI-Organization": options.get("organization_id"),
                "OpenAI-Project": options.get("project_id")
            })

        async with httpx.AsyncClient(base_url=f"{self.base_url}/chat/completions", headers=headers) as client:
            payload = {
                "model": model.api_id,
                "messages": messages,
                "tools": tools,
                "stream": True,
                "temperature": options.get("temperature", 1.0),
                "top_p": options.get("top_p", 1.0),
                "reasoning_effort": options.get("reasoning_effort", "medium"),
            }

            yield StreamEvent(
                event_type="start",
                data={"model": model.id},
                timestamp=0
            )

            async with client.stream("POST", json=payload, timeout=600.0) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                continue
                            
                            try:
                                import json
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", {})
                                finish_reason = chunk.get("finish_reason")
                                tool_calls = chunk.get("tool_calls", [])
                                
                                if "content" in delta:
                                    yield StreamEvent(
                                        event_type="text-delta",
                                        data={"delta": content},
                                        timestamp=0
                                    )
                                    
                                if "tool_calls" in chunk:
                                    for tool_call in tool_calls:
                                        tool_name = tool_call.get("function", "")
                                        tool_input = tool_call.get("arguments", {})
                                        yield StreamEvent(
                                            event_type="tool-call",
                                            data={
                                                "tool": tool_name,
                                                "input": tool_input
                                            },
                                            timestamp=0
                                        )
                                        
                                    for tool_call in tool_calls:
                                        function = tool_call.get("function", "")
                                        result = tool_call.get("result")
                                        if result.get("type") == "tool_use":
                                            tool_output = result.get("content", "")
                                            yield StreamEvent(
                                                event_type="tool-result",
                                                data={
                                                    "output": tool_output
                                                },
                                                timestamp=0
                                            )
                                
                                if finish_reason in ["stop", "length", "content_filter"]:
                                    yield StreamEvent(
                                        event_type="finish",
                                        data={"finish_reason": finish_reason},
                                        timestamp=0
                                    )
                                    break

    def count_tokens(self, response: dict) -> TokenUsage:
        usage = response.get("usage", {})
        return TokenUsage(
            input=usage.get("prompt_tokens", 0),
            output=usage.get("completion_tokens", 0),
            cache_read=usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            cache_write=0
        )

    def calculate_cost(self, usage: TokenUsage, model: ModelInfo) -> float:
        cost = (usage.input * model.cost.input) / 1000000
        cost += (usage.output * model.cost.output) / 1000000
        if usage.cache_read:
            cost += (usage.cache_read * model.cost.cache.get("read", 0)) / 1000000
        return cost
