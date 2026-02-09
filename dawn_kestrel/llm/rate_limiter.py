"""RateLimiter pattern for API throttling.

Rate limiter prevents API overload using token bucket algorithm.

The token bucket algorithm works as follows:
- Bucket has a fixed capacity (maximum tokens)
- Tokens refill at a constant rate over time
- Each request consumes tokens from the bucket
- If bucket is empty, request is rate limited

This module provides:
- RateLimiter protocol for rate limiter interface
- TokenBucket implementation using token bucket algorithm
- RateLimiterImpl with per-resource limits
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Protocol, runtime_checkable

from dawn_kestrel.core.result import Err, Ok, Result


logger = logging.getLogger(__name__)


# =============================================================================
# RateLimiter Protocol
# =============================================================================


@runtime_checkable
class RateLimiter(Protocol):
    """Protocol for rate limiter.

    Rate limiter prevents API overload using token bucket algorithm.
    Each resource (e.g., API endpoint, provider) has its own
    token bucket with configurable capacity and refill rate.

    Example:
        limiter = RateLimiterImpl(
            default_capacity=10,
            default_refill_rate=0.166667,  # 10 tokens per minute
            default_window_seconds=60,
        )

        # Try to acquire token
        result = await limiter.try_acquire('openai_api', tokens=1)
        if result.is_ok():
            # Make API call
            pass
        else:
            # Rate limited, wait and retry
            pass
    """

    async def try_acquire(
        self,
        resource: str,
        tokens: int = 1,
    ) -> Result[bool]:
        """Try to acquire token from bucket.

        Args:
            resource: Resource identifier (e.g., API endpoint, provider).
            tokens: Number of tokens needed.

        Returns:
            Result[bool]: Ok(True) if tokens available, Err if not.
        """
        ...

    async def release(self, resource: str) -> Result[None]:
        """Release used token back to bucket (no-op for simple impl).

        Args:
            resource: Resource identifier.

        Returns:
            Result[None]: Ok on success.
        """
        ...

    async def get_available(self, resource: str) -> Result[int]:
        """Get available tokens for resource.

        Args:
            resource: Resource identifier.

        Returns:
            Result[int]: Ok with token count, Err on failure.
        """
        ...


# =============================================================================
# TokenBucket
# =============================================================================


class TokenBucket:
    """Token bucket for rate limiting.

    Implements token bucket algorithm:
    - Bucket has fixed capacity
    - Tokens refill at constant rate
    - Requests consume tokens
    - Empty bucket = rate limited

    Thread safety:
        NOT thread-safe (documented limitation).
        Suitable for single-process use (async rate limiting).

    Example:
        bucket = TokenBucket(
            capacity=10,  # 10 tokens
            refill_rate=0.166667,  # 10 tokens per minute
            window_seconds=60,  # 60 second window
        )

        # Try to acquire token
        result = await bucket.try_acquire('api_endpoint', tokens=1)
    """

    def __init__(
        self,
        capacity: int = 10,
        refill_rate: float = 1,
        window_seconds: int = 60,
    ):
        """Initialize token bucket.

        Args:
            capacity: Maximum tokens in bucket.
            refill_rate: Tokens added per second.
            window_seconds: Time window for request tracking.
        """
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._window_seconds = window_seconds
        self._tokens: int = capacity  # Start with full bucket
        self._last_refill_time = datetime.now()
        self._request_times: List[datetime] = []  # Track request timestamps
        self._refills: List[datetime] = []  # Track refills

    async def _refill_tokens(self) -> None:
        """Refill tokens based on time elapsed.

        Calculates elapsed time since last refill and adds
        tokens proportionally, respecting capacity limit.
        """
        now = datetime.now()
        elapsed = (now - self._last_refill_time).total_seconds()

        # Calculate tokens to add
        tokens_to_add = int(elapsed * self._refill_rate)

        # Add tokens, respecting capacity
        self._tokens = min(self._tokens + tokens_to_add, self._capacity)
        self._last_refill_time = now
        self._refills.append(now)

        # Remove expired requests from tracking
        self._request_times = [
            t for t in self._request_times if (now - t).total_seconds() < self._window_seconds
        ]

    async def try_acquire(
        self,
        resource: str,
        tokens: int = 1,
    ) -> Result[bool]:
        """Try to acquire tokens from bucket.

        Args:
            resource: Resource identifier (for tracking).
            tokens: Number of tokens needed.

        Returns:
            Result[bool]: Ok(True) if tokens available, Err if not.
        """
        # Check if enough tokens available
        if self._tokens >= tokens:
            # Record request timestamp
            self._request_times.append(datetime.now())

            # Deduct tokens
            self._tokens -= tokens
            return Ok(True)

        # Try refill first
        await self._refill_tokens()

        # Check again after refill
        if self._tokens >= tokens:
            # Record request timestamp
            self._request_times.append(datetime.now())

            # Deduct tokens
            self._tokens -= tokens
            return Ok(True)

        return Err(
            f"Not enough tokens for {resource}: need {tokens}, have {self._tokens}",
            code="RATE_LIMIT_EXCEEDED",
        )

    async def release(self, resource: str) -> Result[None]:
        """Release tokens back to bucket (no-op for simple impl).

        For simple implementation, tokens are not returned.
        Tokens only decrease on acquire.

        Args:
            resource: Resource identifier.

        Returns:
            Result[None]: Ok on success.
        """
        # For simple implementation, tokens are not returned
        # Tokens only decrease on acquire
        return Ok(None)

    async def get_available(self, resource: str) -> Result[int]:
        """Get available tokens for resource.

        Returns count of active requests (not token count).

        Args:
            resource: Resource identifier.

        Returns:
            Result[int]: Ok with request count.
        """
        # Remove expired requests from tracking
        now = datetime.now()
        self._request_times = [
            t for t in self._request_times if (now - t).total_seconds() < self._window_seconds
        ]

        return Ok(len(self._request_times))


# =============================================================================
# RateLimiterImpl
# =============================================================================


class RateLimiterImpl:
    """Rate limiter with per-resource token buckets.

    Manages separate token buckets for each resource (API endpoint,
    provider, etc.) with configurable limits per resource.

    Thread safety:
        NOT thread-safe (documented limitation).
        Suitable for single-process use (async rate limiting).

    Example:
        limiter = RateLimiterImpl(
            default_capacity=10,
            default_refill_rate=0.166667,  # 10 tokens per minute
            default_window_seconds=60,
        )

        # Set custom limit for specific resource
        limiter.set_limit('openai', capacity=100, refill_rate=1.666667, window_seconds=60)

        # Try to acquire token
        result = await limiter.try_acquire('openai', tokens=1)
        if result.is_ok():
            # Make API call
            pass
    """

    def __init__(
        self,
        default_capacity: int = 10,
        default_refill_rate: float = 1,
        default_window_seconds: int = 60,
    ):
        """Initialize rate limiter.

        Args:
            default_capacity: Default bucket capacity for new resources.
            default_refill_rate: Default refill rate (tokens/second) for new resources.
            default_window_seconds: Default time window for new resources.
        """
        self._buckets: Dict[str, TokenBucket] = {}
        self._default_capacity = default_capacity
        self._default_refill_rate = default_refill_rate
        self._default_window_seconds = default_window_seconds

    def set_limit(
        self,
        resource: str,
        capacity: int,
        refill_rate: float,
        window_seconds: int,
    ) -> None:
        """Set rate limit for a resource.

        Creates or updates token bucket for resource with
        specified capacity and refill rate.

        Args:
            resource: Resource identifier.
            capacity: Bucket capacity (maximum tokens).
            refill_rate: Refill rate (tokens/second).
            window_seconds: Time window for request tracking.
        """
        self._buckets[resource] = TokenBucket(
            capacity=capacity,
            refill_rate=refill_rate,
            window_seconds=window_seconds,
        )

    def _get_or_create_bucket(self, resource: str) -> TokenBucket:
        """Get existing bucket or create new one.

        Args:
            resource: Resource identifier.

        Returns:
            TokenBucket instance for resource.
        """
        if resource not in self._buckets:
            self._buckets[resource] = TokenBucket(
                capacity=self._default_capacity,
                refill_rate=self._default_refill_rate,
                window_seconds=self._default_window_seconds,
            )
        return self._buckets[resource]

    async def try_acquire(
        self,
        resource: str,
        tokens: int = 1,
    ) -> Result[bool]:
        """Try to acquire tokens for resource.

        Args:
            resource: Resource identifier.
            tokens: Number of tokens needed.

        Returns:
            Result[bool]: Ok(True) if tokens available, Err if not.
        """
        bucket = self._get_or_create_bucket(resource)
        return await bucket.try_acquire(resource, tokens)

    async def release(self, resource: str) -> Result[None]:
        """Release tokens for resource.

        Args:
            resource: Resource identifier.

        Returns:
            Result[None]: Ok on success.
        """
        bucket = self._get_or_create_bucket(resource)
        return await bucket.release(resource)

    async def get_available(self, resource: str) -> Result[int]:
        """Get available tokens for resource.

        Args:
            resource: Resource identifier.

        Returns:
            Result[int]: Ok with token count, Err on failure.
        """
        bucket = self._get_or_create_bucket(resource)
        return await bucket.get_available(resource)


# =============================================================================
# Public API
# =============================================================================

    async def reset(self, resource: str) -> Result[None]:
        """Reset token bucket for resource.

        Args:
            resource: Resource identifier.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        try:
            if resource in self._buckets:
                self._buckets[resource] = {
                    "tokens": float(self._default_capacity),
                    "last_refill": datetime.now(),
                }
            else:
                self._buckets[resource] = {
                    "tokens": float(self._default_capacity),
                    "last_refill": datetime.now(),
                }
            return Ok(None)
        except Exception as e:
            logger.error(f"Failed to reset rate limiter for {resource}: {e}", exc_info=True)
            return Err(f"Failed to reset rate limiter: {e}", code="RATE_LIMITER_ERROR")

__all__ = [
    "RateLimiter",
    "TokenBucket",
    "RateLimiterImpl",
]
