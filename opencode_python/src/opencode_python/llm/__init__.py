"""OpenCode Python - LLM Module

Provider-agnostic LLM client with retry, timeout, and logging decorators.
Designed to work with the existing provider system.
"""

from .client import (
    LLMClient,
    LegacyLLMClient,
    LLMProviderProtocol,
    LLMRequestOptions,
    LLMResponse,
    with_retry,
    with_timeout,
    with_logging,
)

__all__ = [
    "LLMClient",
    "LegacyLLMClient",
    "LLMProviderProtocol",
    "LLMRequestOptions",
    "LLMResponse",
    "with_retry",
    "with_timeout",
    "with_logging",
]
