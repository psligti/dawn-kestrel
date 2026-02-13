from .base import (
    ModelInfo,
    ModelCapabilities,
    ModelCost,
    ModelLimits,
    ProviderID,
    StreamEvent,
    TokenUsage,
)
from .zai_base import ZAIBaseProvider
from .zai import ZAIProvider
from .zai_coding_plan import ZAICodingPlanProvider
from typing import AsyncIterator, Optional, List, Dict, Any, Union, Callable
from decimal import Decimal
import httpx
import json
import logging
from ..core.plugin_discovery import load_providers


logger = logging.getLogger(__name__)


ProviderFactory = Callable[
    [str],
    Union[
        "AnthropicProvider",
        "OpenAIProvider",
        "ZAIProvider",
        "ZAICodingPlanProvider",
    ],
]


def _get_provider_factories() -> Dict[ProviderID, ProviderFactory]:
    """Get provider factories from plugin discovery.

    Built-in providers are loaded from entry points via load_providers().
    Custom providers should be registered via entry points in pyproject.toml.

    Returns:
        Dictionary mapping ProviderID to provider factory functions/classes
    """
    providers = load_providers()

    # Map entry point names to ProviderID enum values
    factories: Dict[ProviderID, ProviderFactory] = {}

    # Built-in providers from entry points
    name_to_id: Dict[str, ProviderID] = {
        "anthropic": ProviderID.ANTHROPIC,
        "openai": ProviderID.OPENAI,
        "zai": ProviderID.Z_AI,
        "zai_coding_plan": ProviderID.Z_AI_CODING_PLAN,
    }

    for name, provider_class in providers.items():
        if name in name_to_id:
            factories[name_to_id[name]] = provider_class

    return factories


_provider_factories_cache: Optional[Dict[ProviderID, ProviderFactory]] = None


__all__ = [
    # Base types
    "ModelInfo",
    "ModelCapabilities",
    "ModelCost",
    "ModelLimits",
    "ProviderID",
    "StreamEvent",
    "TokenUsage",
    # Base provider
    "ZAIBaseProvider",
    # Provider classes
    "AnthropicProvider",
    "OpenAIProvider",
    "ZAIProvider",
    "ZAICodingPlanProvider",
    # Provider functions
    "get_provider",
    "get_available_models",
]


class AnthropicProvider:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com"

    async def get_models(self) -> List[ModelInfo]:
        models = []
        if self.api_key:
            models.append(
                ModelInfo(
                    id="claude-sonnet-4-20250514",
                    provider_id=ProviderID.ANTHROPIC,
                    api_id="claude-sonnet-4-20250514",
                    api_url=self.base_url,
                    name="Claude Sonnet 4",
                    family="sonnet",
                    capabilities=ModelCapabilities(
                        temperature=True,
                        reasoning=True,
                        attachment=True,
                        toolcall=True,
                        input={"text": True, "image": True},
                    ),
                    cost=ModelCost(
                        input=Decimal("3.00"),
                        output=Decimal("15.00"),
                        cache={"read": Decimal("0.30"), "write": Decimal("3.75")},
                    ),
                    limit=ModelLimits(context=200000, input=200000, output=8192),
                    status="active",
                    options={},
                    headers={},
                    variants={
                        "high": {"thinking": {"type": "enabled", "budget_tokens": 16000}},
                        "max": {"thinking": {"type": "enabled", "budget_tokens": 32000}},
                    },
                )
            )
        return models

    async def stream(
        self,
        model: ModelInfo,
        messages: List[Dict[str, Any]],
        tools: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[StreamEvent]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        if options:
            beta_headers = options.get("beta_headers", [])
            if beta_headers:
                headers["anthropic-beta"] = ",".join(beta_headers)

        url = f"{self.base_url}/messages"

        async with httpx.AsyncClient(timeout=600.0) as client:
            payload = {
                "model": model.api_id,
                "max_tokens": 8192,
                "messages": messages,
                "stream": True,
            }

            if tools:
                payload["tools"] = tools

            if options:
                if "temperature" in options:
                    payload["temperature"] = options["temperature"]
                if "top_p" in options:
                    payload["top_p"] = options["top_p"]

            yield StreamEvent(event_type="start", data={"model": model.id}, timestamp=0)

            async with client.stream("POST", url=url, json=payload, headers=headers) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]

                        if data_str == "[DONE]":
                            continue

                        try:
                            chunk = json.loads(data_str)
                            event_type = chunk.get("type")

                            if event_type == "message_start":
                                yield StreamEvent(event_type="start", data={}, timestamp=0)

                            elif event_type == "content_block_start":
                                block_type = chunk.get("content_block", {}).get("type")

                            elif event_type == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    if text:
                                        yield StreamEvent(
                                            event_type="text-delta",
                                            data={"delta": text},
                                            timestamp=0,
                                        )

                            elif event_type == "content_block_stop":
                                pass

                            elif event_type == "message_delta":
                                delta = chunk.get("delta", {})
                                stop_reason = delta.get("stop_reason")
                                if stop_reason:
                                    yield StreamEvent(
                                        event_type="finish",
                                        data={"finish_reason": stop_reason},
                                        timestamp=0,
                                    )
                                    break

                            elif event_type == "message_stop":
                                yield StreamEvent(
                                    event_type="finish", data={"finish_reason": "stop"}, timestamp=0
                                )
                                break

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse Anthropic chunk: {e}")

    def count_tokens(self, response: Dict[str, Any]) -> TokenUsage:
        return TokenUsage(
            input=response.get("input_tokens", 0),
            output=response.get("output_tokens", 0),
            cache_read=response.get("cache_read_input_tokens", 0),
            cache_write=response.get("cache_creation_input_tokens", 0),
        )

    def calculate_cost(self, usage: TokenUsage, model: ModelInfo) -> Decimal:
        cost = (usage.input * model.cost.input) / Decimal("1000000")
        cost = cost + (usage.output * model.cost.output) / Decimal("1000000")
        if usage.cache_read and model.cost.cache is not None:
            cost = cost + (usage.cache_read * model.cost.cache.get("read", Decimal("0")))
        if usage.cache_write and model.cost.cache is not None:
            cost = cost + (usage.cache_write * model.cost.cache.get("write", Decimal("0")))
        return cost


class OpenAIProvider:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    async def get_models(self) -> List[ModelInfo]:
        models = []
        if self.api_key:
            models.append(
                ModelInfo(
                    id="gpt-5",
                    provider_id=ProviderID.OPENAI,
                    api_id="gpt-5",
                    api_url=self.base_url,
                    name="GPT-5",
                    family="gpt",
                    capabilities=ModelCapabilities(
                        temperature=True, reasoning=True, toolcall=True, input={"text": True}
                    ),
                    cost=ModelCost(input=Decimal("15.00"), output=Decimal("150.00"), cache={}),
                    limit=ModelLimits(context=1000000, input=1000000, output=100000),
                    status="active",
                    options={},
                    headers={},
                )
            )
        return models

    async def stream(
        self,
        model: ModelInfo,
        messages: List[Dict[str, Any]],
        tools: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(event_type="start", data={"model": model.id}, timestamp=0)
        yield StreamEvent(
            event_type="text-delta",
            data={"delta": "Hello, this is a test stream from OpenAI."},
            timestamp=1,
        )
        yield StreamEvent(event_type="text-end", data={}, timestamp=2)
        yield StreamEvent(event_type="finish", data={"finish_reason": "stop"}, timestamp=3)

    def count_tokens(self, response: Dict[str, Any]) -> TokenUsage:
        return TokenUsage(
            input=response.get("prompt_tokens", 0),
            output=response.get("completion_tokens", 0),
            cache_read=response.get("prompt_tokens_details", {}).get("cached_tokens", 0),
        )

    def calculate_cost(self, usage: TokenUsage, model: ModelInfo) -> Decimal:
        cost = (usage.input * model.cost.input) / Decimal("1000000")
        cost = cost + (usage.output * model.cost.output) / Decimal("1000000")
        return cost


def get_provider(
    provider_id: ProviderID, api_key: str
) -> Union[AnthropicProvider, OpenAIProvider, ZAIProvider, ZAICodingPlanProvider, None]:
    """Get a provider instance by ID.

    Uses plugin discovery for built-in providers.

    Args:
        provider_id: ProviderID enum value
        api_key: API key for the provider

    Returns:
        Provider instance or None if not found
    """
    global _provider_factories_cache

    # Load factories (with caching) - ensure we get actual provider instances
    if _provider_factories_cache is None:
        factories = _get_provider_factories()
    else:
        factories = _provider_factories_cache

    factory = factories.get(provider_id)
    if factory is None:
        return None

    # Factory is a callable that returns a provider instance
    provider = factory(api_key)

    # Validate result is actually a provider instance, not a coroutine
    import inspect

    if inspect.iscoroutine(provider):
        # If somehow we still got a coroutine, unwrap it
        raise ValueError(
            f"get_provider returned coroutine instead of provider instance: {provider}"
        )

    return provider


async def get_available_models(provider_id: ProviderID, api_key: str) -> List[ModelInfo]:
    provider = get_provider(provider_id, api_key)
    if provider:
        return await provider.get_models()
    return []
