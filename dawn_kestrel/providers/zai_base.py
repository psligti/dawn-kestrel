"""
Z.AI Base Provider implementation.

Shared logic for Z.AI providers, base URL is set by subclasses.

Streaming support, token counting, and cost calculation.
"""

from __future__ import annotations

import json
import logging
import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from ..core.exceptions import ProviderRateLimitError
from ..core.http_client import HTTPClientWrapper
from .base import (
    ModelInfo,
    StreamEvent,
    TokenUsage,
)
from .base import (
    ModelInfo,
    StreamEvent,
    TokenUsage,
)

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
        messages: list[Any],
        tools: list[Any],
        options: dict[str, Any] | None = None,
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

        # Check rate limit via provider bus before making the request
        provider_key = str(model.provider_id).lower().replace("-", "_").replace(".", "_")
        # Lazy import to avoid circular dependency
        from ..llm.provider_bus import ProviderBus
        rate_tracker = ProviderBus.get_instance()._rate_tracker
        check_result = await rate_tracker.check_allowed(provider_key)
        if check_result.is_ok():
            allowed, wait_seconds = check_result.unwrap()
            if not allowed:
                logger.info(f"Rate limit reached for {provider_key}, waiting {wait_seconds:.2f}s")
                await asyncio.sleep(wait_seconds)

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
                            error_data = chunk["error"]
                            # Parse error structure - Z.AI returns {"error": {"code": N, "message": "..."}}
                            if isinstance(error_data, dict):
                                error_code = error_data.get("code")
                                error_msg = error_data.get("message", str(error_data))
                                retry_after = error_data.get("retry_after")
                            else:
                                # Fallback: error is a string, code might be at top level
                                error_code = chunk.get("code")
                                error_msg = str(error_data)
                                retry_after = chunk.get("retry_after")

                            logger.error(f"Z.AI error: code={error_code}, message={error_msg}")

                            # Z.AI rate limit error code is 1302
                            if error_code == 1302:
                                # Record 429 for tracking in provider bus
                                backoff = float(retry_after) if retry_after else 1.0
                                await rate_tracker.record_429(provider_key, backoff)
                                raise ProviderRateLimitError(
                                    error_msg,
                                    provider="z.ai",
                                    retry_after=backoff,
                                    error_code=error_code,
                                )
                            raise Exception(f"Z.AI API error (code={error_code}): {error_msg}")

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
                            # Extract usage data from the finish chunk
                            # OpenAI-compatible APIs may include usage at chunk level
                            usage_data = chunk.get("usage", {})
                            finish_data: dict[str, Any] = {"finish_reason": finish_reason}
                            if usage_data:
                                finish_data["usage"] = {
                                    "prompt_tokens": usage_data.get("prompt_tokens", 0),
                                    "completion_tokens": usage_data.get("completion_tokens", 0),
                                    "reasoning_tokens": usage_data.get(
                                        "completion_tokens_details", {}
                                    ).get("reasoning_tokens", 0),
                                    "cache_read_tokens": usage_data.get(
                                        "prompt_tokens_details", {}
                                    ).get("cached_tokens", 0),
                                    "cache_write_tokens": 0,
                                }
                            yield StreamEvent(
                                event_type="finish",
                                data=finish_data,
                                timestamp=0,
                            )
                            break
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse chunk: {e}")
                    except ProviderRateLimitError:
                        raise  # Re-raise rate limit errors without catching

    def count_tokens(self, response: dict[str, Any]) -> TokenUsage:
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
