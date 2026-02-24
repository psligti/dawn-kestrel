"""Distributed rate limiter with Redis backend.

Optional module - only available when redis[hiredis] is installed.
Provides distributed rate limiting for multi-process/multi-instance deployments.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import TYPE_CHECKING, Any

from dawn_kestrel.core.result import Err, Ok, Result
from dawn_kestrel.llm.provider_limits import (
    PROVIDER_LIMITS,
    ProviderRateLimit,
    RateLimitTracker,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

REDIS_AVAILABLE = False
try:
    import redis.asyncio as redis
    from redis.backoff import ExponentialWithJitterBackoff
    from redis.retry import Retry

    REDIS_AVAILABLE = True
except ImportError:
    pass


TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local requested = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
    tokens = capacity
    last_refill = now
end

local elapsed = now - last_refill
local tokens_to_add = elapsed * refill_rate
tokens = math.min(capacity, tokens + tokens_to_add)

local allowed = 0
local wait_time = 0

if tokens >= requested then
    tokens = tokens - requested
    allowed = 1
else
    local tokens_needed = requested - tokens
    wait_time = tokens_needed / refill_rate
end

redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
redis.call('EXPIRE', key, ttl)

return {allowed, tostring(wait_time), tostring(tokens)}
"""


class RedisRateLimitTracker:
    """Distributed rate limiter using Redis.

    Uses Lua scripts for atomic token bucket operations.
    Falls back to local tracking when Redis is unavailable.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        provider_limits: dict[str, ProviderRateLimit] | None = None,
        default_limit: ProviderRateLimit | None = None,
        key_prefix: str = "dk:ratelimit:",
        fallback_on_error: bool = True,
    ):
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package not installed. Install with: pip install redis[hiredis]"
            )

        self._limits = provider_limits or PROVIDER_LIMITS
        self._default = default_limit or ProviderRateLimit()
        self._key_prefix = key_prefix
        self._fallback_on_error = fallback_on_error

        self._pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=20,
            socket_timeout=5,
            socket_connect_timeout=3,
            retry=Retry(
                backoff=ExponentialWithJitterBackoff(base=1, cap=10),
                retries=3,
            ),
            health_check_interval=30,
        )
        self._redis: redis.Redis | None = None
        self._script_sha: str | None = None
        self._redis_available = True

        self._local_fallback = _LocalFallbackTracker(
            provider_limits=self._limits,
            default_limit=self._default,
        )

        self._429_counts: dict[str, int] = {}
        self._429_last_time: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def _get_limit(self, key: str) -> ProviderRateLimit:
        return self._limits.get(key, self._default)

    def _redis_key(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    async def _get_redis(self) -> redis.Redis | None:
        if self._redis is None:
            try:
                self._redis = redis.Redis(connection_pool=self._pool)
                await self._redis.ping()
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._redis_available = False
                return None
        return self._redis

    async def _load_script(self, client: redis.Redis) -> str | None:
        if self._script_sha is None:
            try:
                self._script_sha = await client.script_load(TOKEN_BUCKET_LUA)
            except Exception as e:
                logger.error(f"Failed to load Lua script: {e}")
                return None
        return self._script_sha

    async def check_allowed(self, key: str, cost: int = 1) -> Result[tuple[bool, float]]:
        """Check if request is allowed with distributed coordination."""
        if not self._redis_available or not self._fallback_on_error:
            return await self._local_fallback.check_allowed(key, cost)

        try:
            client = await self._get_redis()
            if client is None:
                return await self._local_fallback.check_allowed(key, cost)

            script_sha = await self._load_script(client)
            if script_sha is None:
                return await self._local_fallback.check_allowed(key, cost)

            limit = self._get_limit(key)
            redis_key = self._redis_key(key)
            now = time.time()
            refill_rate = limit.requests_per_minute / 60.0

            result = await client.evalsha(
                script_sha,
                1,
                redis_key,
                limit.requests_per_minute,
                refill_rate,
                cost,
                now,
                3600,
            )

            allowed = bool(int(result[0]))
            wait_time = float(result[1])

            if not allowed:
                jitter = random.uniform(*limit.jitter_range)
                wait_time += jitter

            return Ok((allowed, wait_time))

        except Exception as e:
            logger.warning(f"Redis error, falling back to local: {e}")
            self._redis_available = False
            return await self._local_fallback.check_allowed(key, cost)

    async def record_429(self, key: str, retry_after: float) -> None:
        """Record 429 for circuit breaker tracking."""
        async with self._lock:
            now = time.time()

            if key in self._429_last_time:
                if now - self._429_last_time[key] > 300:
                    self._429_counts[key] = 0

            self._429_counts[key] = self._429_counts.get(key, 0) + 1
            self._429_last_time[key] = now

            if self._429_counts[key] >= 3:
                logger.warning(f"Provider {key} returned 3+ 429s. Consider circuit breaker.")

    async def reset(self, key: str) -> None:
        """Reset rate limit state."""
        async with self._lock:
            self._429_counts.pop(key, None)
            self._429_last_time.pop(key, None)

        if self._redis_available:
            try:
                client = await self._get_redis()
                if client:
                    await client.delete(self._redis_key(key))
            except Exception:
                pass

        await self._local_fallback.reset(key)

    def get_429_count(self, key: str) -> int:
        """Get recent 429 count."""
        return self._429_counts.get(key, 0)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
        await self._pool.disconnect()


class _LocalFallbackTracker:
    """Local fallback tracker used when Redis is unavailable."""

    def __init__(
        self,
        provider_limits: dict[str, ProviderRateLimit],
        default_limit: ProviderRateLimit,
    ):
        self._limits = provider_limits
        self._default = default_limit
        self._buckets: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _get_limit(self, key: str) -> ProviderRateLimit:
        return self._limits.get(key, self._default)

    async def check_allowed(self, key: str, cost: int = 1) -> Result[tuple[bool, float]]:
        async with self._lock:
            now = time.time()
            limit = self._get_limit(key)

            if key not in self._buckets:
                self._buckets[key] = {
                    "tokens": limit.requests_per_minute,
                    "last_refill": now,
                    "refill_rate": limit.requests_per_minute / 60.0,
                    "capacity": limit.requests_per_minute,
                }

            bucket = self._buckets[key]
            elapsed = now - bucket["last_refill"]
            bucket["tokens"] = min(
                bucket["capacity"], bucket["tokens"] + elapsed * bucket["refill_rate"]
            )
            bucket["last_refill"] = now

            if bucket["tokens"] >= cost:
                bucket["tokens"] -= cost
                return Ok((True, 0.0))

            tokens_needed = cost - bucket["tokens"]
            wait_seconds = tokens_needed / bucket["refill_rate"]
            wait_with_jitter = wait_seconds + random.uniform(*limit.jitter_range)
            return Ok((False, wait_with_jitter))

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._buckets.pop(key, None)


__all__ = [
    "RedisRateLimitTracker",
    "REDIS_AVAILABLE",
]
