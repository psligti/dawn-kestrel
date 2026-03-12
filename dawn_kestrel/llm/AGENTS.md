# LLM LAYER

**Scope:** dawn_kestrel/llm/ - Provider abstraction with resilience patterns

## OVERVIEW

LLM client layer implements reliability patterns for fault-tolerant API calls.
Token bucket rate limiting, circuit breaker state machine, retry with backoff.
Composable via LLMReliability wrapper or standalone protocols.

## RELIABILITY PATTERNS

| Pattern | File | Key Config | Purpose |
|---------|------|------------|---------|
| RateLimiter | rate_limiter.py | `capacity`, `refill_rate`, `window_seconds` | Token bucket, per-resource buckets |
| CircuitBreaker | circuit_breaker.py | `failure_threshold=5`, `timeout_seconds=300`, `reset_timeout_seconds=600` | CLOSED/OPEN/HALF_OPEN states |
| RetryExecutor | retry.py | `max_attempts=3`, `ExponentialBackoff(base_delay_ms=100)` | Exponential/linear/fixed backoff, jitter |
| Bulkhead | bulkhead.py | `max_concurrent`, `timeout=30.0` | Semaphore-based concurrency limiting |
| LLMReliability | reliability.py | Combines all above | Unified wrapper with stats tracking |

## PATTERN ORDER

```
Request → Rate Limit → Circuit Breaker → Retry → Provider
                ↓              ↓           ↓
           429 error     circuit open   backoff/retry
```

1. **Rate Limit** - Prevent overload, fast fail (no retry on 429)
2. **Circuit Breaker** - Fail fast if provider failing
3. **Retry** - Handle transient errors with backoff

## BACKOFF STRATEGIES

| Strategy | Formula | Use Case |
|----------|---------|----------|
| ExponentialBackoff | `base * (2^attempt)` | Default, handles varying load |
| LinearBackoff | `base * (attempt + 1)` | Predictable delays |
| FixedBackoff | `delay_ms` constant | Simple throttling |

## DISTRIBUTED LIMITER

`distributed_limiter.py` - Redis-backed rate limiting for multi-instance deployments.

- Lua script for atomic token bucket ops
- Falls back to `_LocalFallbackTracker` on Redis error
- `fallback_on_error=True` (default) ensures resilience
- Optional: requires `redis[hiredis]`

```python
tracker = RedisRateLimitTracker(
    redis_url="redis://localhost:6379/0",
    provider_limits=PROVIDER_LIMITS,
)
result = await tracker.check_allowed("openai", cost=1)
# Returns Ok((allowed: bool, wait_seconds: float))
```

## PROVIDER LIMITS

`provider_limits.py` - Pre-configured rate limits:

| Provider | req/min | tokens/min | concurrent |
|----------|---------|------------|------------|
| openai | 500 | 200,000 | 10 |
| anthropic | 60 | 100,000 | 5 |
| zai | 60 | 100,000 | 5 |
| zai_coding_plan | 60 | 100,000 | 3 |
| github_copilot | 100 | 50,000 | 5 |

Factory: `create_rate_limit_tracker(backend="local"|"redis")`

## FILES

| File | Purpose |
|------|---------|
| client.py | LLM client implementation |
| rate_limiter.py | Token bucket rate limiting |
| circuit_breaker.py | Circuit breaker state machine |
| retry.py | Retry with backoff strategies |
| bulkhead.py | Concurrency limiting |
| reliability.py | Combined resilience wrapper |
| distributed_limiter.py | Redis-backed distributed limiting |
| provider_limits.py | Provider rate limit configs |
| evidence_sharing.py | Evidence sharing between agents |

## NOTES

- All patterns use `Result` types (no exception flow)
- Not thread-safe (async single-process design)
- Circuit breaker: CLOSED=normal, OPEN=fail-fast, HALF_OPEN=recovery test
- 429 tracking triggers circuit breaker warning at 3+ consecutive
