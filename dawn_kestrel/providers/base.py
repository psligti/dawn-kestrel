from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
from decimal import Decimal


class ProviderID(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    Z_AI = "z.ai"
    Z_AI_CODING_PLAN = "zai-coding-plan"
    GOOGLE = "google"
    GOOGLE_VERTEX = "google-vertex"
    AMAZON_BEDROCK = "amazon-bedrock"
    AZURE = "azure"
    VERCEL = "vercel"
    OPENROUTER = "openrouter"
    XAI = "xai"
    MISTRAL = "mistral"
    GROQ = "groq"
    DEEPINFRA = "deepinfra"
    CEREBRAS = "cerebras"
    COHERE = "cohere"
    TOGETHERAI = "togetherai"
    PERPLEXITY = "perplexity"
    GITLAB = "gitlab"
    GITHUB_COPILOT = "github-copilot"

@dataclass
class ModelCapabilities:
    temperature: bool = True
    reasoning: bool = False
    attachment: bool = False
    toolcall: bool = False
    input: Optional[Dict[str, bool]] = None
    output: Optional[Dict[str, bool]] = None
    interleaved: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.input is None:
            self.input = {"text": True}
        if self.output is None:
            self.output = {"text": True}


@dataclass
class ModelCost:
    input: Decimal
    output: Decimal
    cache: Optional[Dict[str, Decimal]] = None

    def __post_init__(self) -> None:
        if self.cache is None:
            self.cache = {"read": Decimal("0"), "write": Decimal("0")}


@dataclass
class ModelLimits:
    context: int
    input: Optional[int] = None
    output: Optional[int] = None

    def __post_init__(self) -> None:
        if self.input is None:
            self.input = self.context - self.output if self.output else self.context


@dataclass
class ModelInfo:
    id: str
    provider_id: ProviderID
    api_id: str
    api_url: str
    name: str
    family: str
    capabilities: ModelCapabilities
    cost: ModelCost
    limit: ModelLimits
    status: str
    options: Dict[str, Any]
    headers: Dict[str, str]
    variants: Optional[Dict[str, Dict[str, Any]]] = None


@dataclass
class TokenUsage:
    input: int
    output: int
    reasoning: int = 0
    cache_read: int = 0
    cache_write: int = 0

    @property
    def total(self) -> int:
        return self.input + self.output + self.reasoning

    @property
    def billable(self) -> int:
        return self.input + self.output + self.reasoning


@dataclass
class StreamEvent:
    event_type: str
    data: Dict[str, Any]
    timestamp: Optional[float] = None
