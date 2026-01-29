"""
OpenAI Provider implementation.

Streaming support, token counting, and cost calculation.
"""

import httpx
import json
import logging
from decimal import Decimal
from typing import AsyncIterator, Dict, Any, Optional

from .base import (
    ModelInfo,
    ModelCapabilities,
    ModelCost,
    ModelLimits,
    TokenUsage,
    StreamEvent,
    ProviderID
)


logger = logging.getLogger(__name__)


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
                    input=Decimal("0.10"),
                    output=Decimal("0.40"),
                    cache=None
                ),
                limit=ModelLimits(
                    context=1000000,
                    input=1000000,
                    output=100000
                ),
                status="active",
                options={},
                headers={}
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
                    cache=None
                ),
                limit=ModelLimits(
                    context=1000000,
                    input=1000000,
                    output=3000
                ),
                status="active",
                options={},
                headers={}
            )
        ]

    async def stream(self, model: ModelInfo, messages: list, tools: dict, options: Optional[Dict[str, Any]] = None) -> AsyncIterator[StreamEvent]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if options:
            org_id = options.get("organization_id")
            project_id = options.get("project_id")
            if org_id:
                headers["OpenAI-Organization"] = org_id
            if project_id:
                headers["OpenAI-Project"] = project_id

        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient() as client:
            payload = {
                "model": model.api_id,
                "messages": messages,
                "tools": tools,
                "stream": True,
                "temperature": options.get("temperature", 1.0) if options else 1.0,
                "top_p": options.get("top_p", 1.0) if options else 1.0,
                "reasoning_effort": options.get("reasoning_effort", "medium") if options else "medium",
            }

            yield StreamEvent(
                event_type="start",
                data={"model": model.id},
                timestamp=0
            )

            async with client.stream("POST", url=url, json=payload, timeout=600.0) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                continue
                            
                            try:
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
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse chunk: {e}")

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
        if usage.cache_read and model.cost.cache:
            cache_read_cost = model.cost.cache.get("read", Decimal("0"))
            cost += (usage.cache_read * cache_read_cost) / 1000000
        return float(cost)
