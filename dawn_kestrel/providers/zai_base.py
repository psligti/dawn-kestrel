"""
Z.AI Base Provider implementation.

Shared logic for Z.AI providers, base URL is set by subclasses.

Streaming support, token counting, and cost calculation.
"""

import httpx
import json
import logging
from decimal import Decimal
from typing import AsyncIterator, Dict, Any, Optional
from abc import ABC, abstractmethod

from .base import (
    ModelInfo,
    ModelCapabilities,
    ModelCost,
    ModelLimits,
    TokenUsage,
    StreamEvent,
    ProviderID,
)
from ..core.http_client import HTTPClientWrapper


logger = logging.getLogger(__name__)


class ZAIBaseProvider(ABC):
    """Base provider for Z.AI with shared implementation.

    Subclasses must set self.base_url in __init__.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url: str = ""  # Must be set by subclass
        self.http_client = HTTPClientWrapper(base_timeout=600.0, max_retries=3)

    @abstractmethod
    async def get_models(self) -> list[ModelInfo]:
        """Return list of available models for this provider."""
        pass

    async def stream(
        self,
        model: ModelInfo,
        messages: list,
        tools: list,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream chat completion from Z.AI API."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        if options:
            org_id = options.get("organization_id")
            if org_id:
                headers["ZAI-Organization"] = org_id

        url = f"{self.base_url}/chat/completions"
        temperature = options.get("temperature") if options else None
        top_p = options.get("top_p") if options else None

        payload = {
            "model": model.api_id,
            "messages": messages,
            "stream": True,
            "temperature": temperature if temperature is not None else 1.0,
            "top_p": top_p if top_p is not None else 1.0,
            "reasoning_effort": options.get("reasoning_effort", "medium") if options else "medium",
        }
        if options and options.get("response_format"):
            payload["response_format"] = options["response_format"]
        if tools:
            payload["tools"] = tools

        yield StreamEvent(event_type="start", data={"model": model.id}, timestamp=0)

        stream_iterator = await self.http_client.stream(
            method="POST", url=url, json=payload, headers=headers, timeout=600.0
        )

        async for response_stream_context in stream_iterator:
            async with response_stream_context as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    data_str = None
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            continue
                    elif line.startswith("{"):
                        data_str = line

                    if not data_str:
                        continue

                    try:
                        chunk = json.loads(data_str)
                        if "error" in chunk:
                            error_msg = chunk.get("error", "Unknown error")
                            logger.error(f"Z.AI error: {error_msg}")
                            raise Exception(f"Z.AI API error: {error_msg}")

                        choice = chunk.get("choices", [{}])[0]
                        delta = choice.get("delta", {})
                        finish_reason = choice.get("finish_reason")
                        content = delta.get("content")

                        if isinstance(content, str) and content:
                            yield StreamEvent(
                                event_type="text-delta", data={"delta": content}, timestamp=0
                            )

                        tool_calls = delta.get("tool_calls", [])
                        if tool_calls:
                            for tool_call in tool_calls:
                                function = tool_call.get("function", {})
                                tool_name = function.get("name", "")
                                arguments = function.get("arguments", "{}")
                                tool_input = (
                                    json.loads(arguments)
                                    if isinstance(arguments, str)
                                    else arguments
                                )
                                yield StreamEvent(
                                    event_type="tool-call",
                                    data={"tool": tool_name, "input": tool_input},
                                    timestamp=0,
                                )

                        if finish_reason:
                            yield StreamEvent(
                                event_type="finish",
                                data={"finish_reason": finish_reason},
                                timestamp=0,
                            )
                            break
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse chunk: {e}")

    def count_tokens(self, response: dict) -> TokenUsage:
        """Count tokens from API response."""
        usage = response.get("usage", {})
        return TokenUsage(
            input=usage.get("prompt_tokens", 0),
            output=usage.get("completion_tokens", 0),
            cache_read=usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            cache_write=0,
        )

    def calculate_cost(self, usage: TokenUsage, model: ModelInfo) -> Decimal:
        """Calculate cost from token usage."""
        cost = (usage.input * model.cost.input) / Decimal("1000000")
        cost = cost + (usage.output * model.cost.output) / Decimal("1000000")
        if usage.cache_read and model.cost.cache:
            cache_read_cost = model.cost.cache.get("read", Decimal("0"))
            cost = cost + (usage.cache_read * cache_read_cost) / Decimal("1000000")
        return cost
