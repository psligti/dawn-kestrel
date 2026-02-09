"""OpenCode Python - LLM Module

Provider-agnostic LLM client with policy-driven execution controls.
"""

from .client import (
    LLMClient,
    LLMProviderProtocol,
    LLMRequestOptions,
    LLMResponse,
    RetryPolicy,
    with_retry,
    with_timeout,
    with_logging,
)
from .rate_limiter import (
    RateLimiter,
    RateLimiterImpl,
    TokenBucket,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerImpl,
    CircuitState,
)
from .retry import (
    RetryExecutor,
    RetryExecutorImpl,
    BackoffStrategy,
    ExponentialBackoff,
)
from .reliability import (
    LLMReliability,
    LLMReliabilityImpl,
)
from .bulkhead import (
    Bulkhead,
    BulkheadImpl,
)

__all__ = [
    "LLMClient",
    "LLMProviderProtocol",
    "LLMRequestOptions",
    "LLMResponse",
    "RetryPolicy",
    "with_retry",
    "with_timeout",
    "with_logging",
    "RateLimiter",
    "RateLimiterImpl",
    "TokenBucket",
    "CircuitBreaker",
    "CircuitBreakerImpl",
    "CircuitState",
    "RetryExecutor",
    "RetryExecutorImpl",
    "BackoffStrategy",
    "ExponentialBackoff",
    "LLMReliability",
    "LLMReliabilityImpl",
    "Bulkhead",
    "BulkheadImpl",
]
