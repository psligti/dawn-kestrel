"""OpenCode Python - LLM Module

Provider-agnostic LLM client with policy-driven execution controls.
"""

from .bulkhead import (
    Bulkhead,
    BulkheadImpl,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerImpl,
    CircuitState,
)
from .client import (
    LLMClient,
    LLMProviderProtocol,
    LLMRequestOptions,
    LLMResponse,
    RetryPolicy,
    with_logging,
    with_retry,
    with_timeout,
)
from .provider_limits import (
    LocalRateLimitTracker,
    ProviderRateLimit,
    RateLimitTracker,
    create_rate_limit_tracker,
    get_provider_limit,
)
from .rate_limiter import (
    RateLimiter,
    RateLimiterImpl,
    TokenBucket,
)
from .reliability import (
    LLMReliability,
    LLMReliabilityImpl,
)
from .retry import (
    BackoffStrategy,
    ExponentialBackoff,
    RetryExecutor,
    RetryExecutorImpl,
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
    "ProviderRateLimit",
    "get_provider_limit",
    "RateLimitTracker",
    "LocalRateLimitTracker",
    "create_rate_limit_tracker",
]
