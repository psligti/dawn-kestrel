from .base import ModelInfo, ModelCapabilities, ModelCost, ModelLimits, ProviderID, StreamEvent, TokenUsage
from typing import AsyncIterator, Optional
from decimal import Decimal


class AnthropicProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com"

    async def get_models(self) -> list[ModelInfo]:
        models = []
        if self.api_key:
            models.append(ModelInfo(
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
                    input={"text": True, "image": True}
                ),
                cost=ModelCost(
                    input=Decimal("3.00"),
                    output=Decimal("15.00"),
                    cache={"read": Decimal("0.30"), "write": Decimal("3.75")}
                ),
                limit=ModelLimits(
                    context=200000,
                    input=200000,
                    output=8192
                ),
                status="active",
                options={},
                headers={},
                variants={
                    "high": {"thinking": {"type": "enabled", "budget_tokens": 16000}},
                    "max": {"thinking": {"type": "enabled", "budget_tokens": 32000}}
                }
            ))
        return models

    async def stream(self, model: ModelInfo, messages: list, tools: dict, options: Optional[dict]) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(
            event_type="start",
            data={"model": model.id},
            timestamp=0
        )
        yield StreamEvent(
            event_type="text-delta",
            data={"delta": "Hello, this is a test stream from Anthropic."},
            timestamp=1
        )
        yield StreamEvent(
            event_type="text-end",
            data={},
            timestamp=2
        )
        yield StreamEvent(
            event_type="finish",
            data={"finish_reason": "stop"},
            timestamp=3
        )

    def count_tokens(self, response: dict) -> TokenUsage:
        return TokenUsage(
            input=response.get("input_tokens", 0),
            output=response.get("output_tokens", 0),
            cache_read=response.get("cache_read_input_tokens", 0),
            cache_write=response.get("cache_creation_input_tokens", 0)
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
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    async def get_models(self) -> list[ModelInfo]:
        models = []
        if self.api_key:
            models.append(ModelInfo(
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
                status="active",
                options={},
                headers={}
            ))
        return models

    async def stream(self, model: ModelInfo, messages: list, tools: dict, options: Optional[dict]) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(
            event_type="start",
            data={"model": model.id},
            timestamp=0
        )
        yield StreamEvent(
            event_type="text-delta",
            data={"delta": "Hello, this is a test stream from OpenAI."},
            timestamp=1
        )
        yield StreamEvent(
            event_type="text-end",
            data={},
            timestamp=2
        )
        yield StreamEvent(
            event_type="finish",
            data={"finish_reason": "stop"},
            timestamp=3
        )

    def count_tokens(self, response: dict) -> TokenUsage:
        return TokenUsage(
            input=response.get("prompt_tokens", 0),
            output=response.get("completion_tokens", 0),
            cache_read=response.get("prompt_tokens_details", {}).get("cached_tokens", 0)
        )

    def calculate_cost(self, usage: TokenUsage, model: ModelInfo) -> Decimal:
        cost = (usage.input * model.cost.input) / Decimal("1000000")
        cost = cost + (usage.output * model.cost.output) / Decimal("1000000")
        return cost


def get_provider(provider_id: ProviderID, api_key: str):
    providers = {
        ProviderID.ANTHROPIC: AnthropicProvider(api_key),
        ProviderID.OPENAI: OpenAIProvider(api_key)
    }
    return providers.get(provider_id)


async def get_available_models(provider_id: ProviderID, api_key: str):
    provider = get_provider(provider_id, api_key)
    if provider:
        return await provider.get_models()
    return []
