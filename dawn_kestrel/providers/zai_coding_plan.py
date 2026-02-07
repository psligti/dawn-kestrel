"""
Z.AI Coding Plan Provider implementation for free coding endpoint.

Streaming support, token counting, and cost calculation.
"""

import logging
from decimal import Decimal

from .base import (
    ModelInfo,
    ModelCapabilities,
    ModelCost,
    ModelLimits,
    StreamEvent,
    ProviderID
)
from .zai_base import ZAIBaseProvider


logger = logging.getLogger(__name__)


class ZAICodingPlanProvider(ZAIBaseProvider):
    def __init__(self, api_key: str = ""):
        super().__init__(api_key)
        self.base_url = "https://api.z.ai/api/coding/paas/v4"

    async def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id="glm-4.7",
                provider_id=ProviderID.Z_AI_CODING_PLAN,
                api_id="glm-4.7",
                api_url=self.base_url,
                name="GLM-4.7 (Coding Plan - FREE)",
                family="glm",
                capabilities=ModelCapabilities(
                    temperature=True,
                    reasoning=True,
                    toolcall=True,
                    input={"text": True}
                ),
                cost=ModelCost(
                    input=Decimal("0.00"),
                    output=Decimal("0.00"),
                    cache=None
                ),
                limit=ModelLimits(
                    context=128000,
                    input=128000,
                    output=8192
                ),
                status="active",
                options={},
                headers={}
            ),
            ModelInfo(
                id="zai-gpt-4",
                provider_id=ProviderID.Z_AI_CODING_PLAN,
                api_id="zai-gpt-4",
                api_url=self.base_url,
                name="Z.AI GPT-4 (Coding Plan - FREE)",
                family="gpt",
                capabilities=ModelCapabilities(
                    temperature=True,
                    reasoning=True,
                    toolcall=True,
                    input={"text": True}
                ),
                cost=ModelCost(
                    input=Decimal("0.00"),
                    output=Decimal("0.00"),
                    cache=None
                ),
                limit=ModelLimits(
                    context=128000,
                    input=128000,
                    output=4000
                ),
                status="active",
                options={},
                headers={}
            ),
            ModelInfo(
                id="zai-gpt-4-turbo",
                provider_id=ProviderID.Z_AI_CODING_PLAN,
                api_id="zai-gpt-4-turbo",
                api_url=self.base_url,
                name="Z.AI GPT-4 Turbo (Coding Plan - FREE)",
                family="gpt",
                capabilities=ModelCapabilities(
                    temperature=True,
                    reasoning=True,
                    toolcall=True,
                    input={"text": True}
                ),
                cost=ModelCost(
                    input=Decimal("0.00"),
                    output=Decimal("0.00"),
                    cache=None
                ),
                limit=ModelLimits(
                    context=128000,
                    input=128000,
                    output=4000
                ),
                status="active",
                options={},
                headers={}
            )
        ]
