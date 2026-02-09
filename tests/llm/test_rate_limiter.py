"""Tests for RateLimiter pattern for API throttling.

Tests follow TDD workflow: RED -> GREEN -> REFACTOR
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from dawn_kestrel.core.result import Err, Ok, Result


# =============================================================================
# TokenBucket Tests
# =============================================================================


class TestTokenBucket:
    """Tests for TokenBucket implementation."""

    async def test_initial_tokens_equal_capacity(self):
        """Test that initial tokens equals capacity."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1, window_seconds=60)
        assert bucket._tokens == 10

    async def test_initial_last_refill_time_is_now(self):
        """Test that initial last_refill_time is recent."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1, window_seconds=60)
        now = datetime.now()
        time_diff = abs((now - bucket._last_refill_time).total_seconds())
        assert time_diff < 1.0  # Should be within 1 second

    async def test_refill_tokens_increments_up_to_capacity(self):
        """Test that refill increments tokens up to capacity."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=2, window_seconds=60)
        bucket._tokens = 5
        bucket._last_refill_time = datetime.now() - timedelta(seconds=2)

        await bucket._refill_tokens()

        assert bucket._tokens == 9  # 5 + (2 * 2) = 9

    async def test_refill_tokens_respects_capacity(self):
        """Test that refill respects capacity limit."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=5, window_seconds=60)
        bucket._tokens = 8
        bucket._last_refill_time = datetime.now() - timedelta(seconds=2)

        await bucket._refill_tokens()

        assert bucket._tokens == 10  # Capped at capacity

    async def test_refill_updates_last_refill_time(self):
        """Test that refill updates last_refill_time."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1, window_seconds=60)
        old_time = bucket._last_refill_time

        await asyncio.sleep(0.1)  # Small delay
        await bucket._refill_tokens()

        assert bucket._last_refill_time > old_time

    async def test_refill_clears_expired_requests(self):
        """Test that refill clears expired requests."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1, window_seconds=60)

        # Add an old request
        old_time = datetime.now() - timedelta(seconds=70)
        bucket._request_times = [old_time]

        await bucket._refill_tokens()

        # Old request should be cleared
        assert old_time not in bucket._request_times

    async def test_try_acquire_succeeds_with_enough_tokens(self):
        """Test that try_acquire succeeds with enough tokens."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1, window_seconds=60)
        result = await bucket.try_acquire("test_resource", tokens=1)

        assert isinstance(result, Ok)
        assert result.unwrap() is True
        assert bucket._tokens == 9

    async def test_try_acquire_tries_refill_if_needed(self):
        """Test that try_acquire tries refill if needed."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=5, window_seconds=60)
        bucket._tokens = 0
        bucket._last_refill_time = datetime.now() - timedelta(seconds=2)

        result = await bucket.try_acquire("test_resource", tokens=1)

        assert isinstance(result, Ok)
        assert result.unwrap() is True

    async def test_try_acquire_returns_err_when_insufficient_tokens(self):
        """Test that try_acquire returns Err when insufficient tokens."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1, window_seconds=60)
        bucket._tokens = 0

        result = await bucket.try_acquire("test_resource", tokens=1)

        assert isinstance(result, Err)
        assert "Not enough tokens" in result.error
        assert result.code == "RATE_LIMIT_EXCEEDED"

    async def test_try_acquire_deducts_correct_token_count(self):
        """Test that try_acquire deducts correct token count."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1, window_seconds=60)
        result = await bucket.try_acquire("test_resource", tokens=3)

        assert isinstance(result, Ok)
        assert bucket._tokens == 7

    async def test_try_acquire_records_request_time(self):
        """Test that try_acquire records request timestamp."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1, window_seconds=60)
        now = datetime.now()

        await bucket.try_acquire("test_resource", tokens=1)

        assert len(bucket._request_times) == 1
        time_diff = abs((now - bucket._request_times[0]).total_seconds())
        assert time_diff < 1.0

    async def test_release_is_noop(self):
        """Test that release is a no-op."""
        from dawn_kestrel.llm.rate_limiter import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1, window_seconds=60)
        bucket._tokens = 5

        result = await bucket.release("test_resource")

        assert isinstance(result, Ok)
        assert result.unwrap() is None
        assert bucket._tokens == 5  # Unchanged


# =============================================================================
# RateLimiterImpl Tests
# =============================================================================


class TestRateLimiterImpl:
    """Tests for RateLimiterImpl implementation."""

    async def test_set_limit_creates_new_bucket(self):
        """Test that set_limit creates new bucket."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl()
        limiter.set_limit("test_resource", capacity=20, refill_rate=2, window_seconds=60)

        assert "test_resource" in limiter._buckets
        bucket = limiter._buckets["test_resource"]
        assert bucket._capacity == 20
        assert bucket._refill_rate == 2

    async def test_set_limit_updates_existing_bucket(self):
        """Test that set_limit updates existing bucket."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl()
        limiter.set_limit("test_resource", capacity=10, refill_rate=1, window_seconds=60)
        limiter.set_limit("test_resource", capacity=20, refill_rate=2, window_seconds=60)

        bucket = limiter._buckets["test_resource"]
        assert bucket._capacity == 20
        assert bucket._refill_rate == 2

    async def test_try_acquire_uses_correct_bucket(self):
        """Test that try_acquire uses correct bucket."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl()
        limiter.set_limit("resource_a", capacity=5, refill_rate=1, window_seconds=60)
        limiter.set_limit("resource_b", capacity=10, refill_rate=1, window_seconds=60)

        # Consume all tokens from resource_a
        for _ in range(5):
            await limiter.try_acquire("resource_a", tokens=1)

        # resource_b should still work
        result = await limiter.try_acquire("resource_b", tokens=1)
        assert isinstance(result, Ok)

        # resource_a should fail
        result = await limiter.try_acquire("resource_a", tokens=1)
        assert isinstance(result, Err)

    async def test_try_acquire_per_resource_limits(self):
        """Test that try_acquire enforces per-resource limits."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl(
            default_capacity=3, default_refill_rate=1, default_window_seconds=60
        )

        # Consume all tokens
        for _ in range(3):
            result = await limiter.try_acquire("test_resource", tokens=1)
            assert isinstance(result, Ok)

        # Next should fail
        result = await limiter.try_acquire("test_resource", tokens=1)
        assert isinstance(result, Err)
        assert result.code == "RATE_LIMIT_EXCEEDED"

    async def test_release_uses_correct_bucket(self):
        """Test that release uses correct bucket."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl()
        result = await limiter.release("test_resource")

        assert isinstance(result, Ok)

    async def test_get_available_returns_available_tokens(self):
        """Test that get_available returns available tokens."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl(
            default_capacity=10, default_refill_rate=1, default_window_seconds=60
        )

        # Make 5 requests
        for _ in range(5):
            await limiter.try_acquire("test_resource", tokens=1)

        result = await limiter.get_available("test_resource")
        assert isinstance(result, Ok)
        assert result.unwrap() == 5

    async def test_get_available_clears_expired_requests(self):
        """Test that get_available clears expired requests."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl(
            default_capacity=10, default_refill_rate=1, default_window_seconds=60
        )

        # Make a request
        await limiter.try_acquire("test_resource", tokens=1)

        # Manually add an old request
        bucket = limiter._buckets["test_resource"]
        old_time = datetime.now() - timedelta(seconds=70)
        bucket._request_times.append(old_time)

        # Get available should clear expired requests
        result = await limiter.get_available("test_resource")
        assert isinstance(result, Ok)
        # Only the recent request should count
        assert result.unwrap() == 1

    async def test_multiple_resources_have_separate_limits(self):
        """Test that multiple resources have separate limits."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl(
            default_capacity=2, default_refill_rate=1, default_window_seconds=60
        )

        # Consume all from resource_a
        for _ in range(2):
            await limiter.try_acquire("resource_a", tokens=1)

        # resource_b should still work
        result = await limiter.try_acquire("resource_b", tokens=1)
        assert isinstance(result, Ok)

        # resource_a should fail
        result = await limiter.try_acquire("resource_a", tokens=1)
        assert isinstance(result, Err)

    async def test_set_limit_with_invalid_capacity_throws(self):
        """Test that set_limit throws error with invalid capacity."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl()
        # Should work with valid values
        limiter.set_limit("test_resource", capacity=10, refill_rate=1, window_seconds=60)

        # Bucket should be created
        assert "test_resource" in limiter._buckets


# =============================================================================
# RateLimiter Protocol Tests
# =============================================================================


class TestRateLimiterProtocol:
    """Tests for RateLimiter protocol compliance."""

    async def test_protocol_is_runtime_checkable(self):
        """Test that RateLimiter protocol is runtime_checkable."""
        from dawn_kestrel.llm.rate_limiter import RateLimiter, RateLimiterImpl

        limiter = RateLimiterImpl()
        assert isinstance(limiter, RateLimiter)

    async def test_rate_limiter_has_required_methods(self):
        """Test that RateLimiter implementation has required methods."""
        from dawn_kestrel.llm.rate_limiter import RateLimiter, RateLimiterImpl

        limiter = RateLimiterImpl()

        # Check all required methods exist
        assert hasattr(limiter, "try_acquire")
        assert hasattr(limiter, "release")
        assert hasattr(limiter, "get_available")

        # Check they are callable
        assert callable(limiter.try_acquire)
        assert callable(limiter.release)
        assert callable(limiter.get_available)


# =============================================================================
# Integration Tests
# =============================================================================


class TestRateLimiterIntegration:
    """Integration tests for RateLimiter with other patterns."""

    async def test_rate_limiter_with_circuit_breaker(self):
        """Test RateLimiter integration with CircuitBreaker."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl(
            default_capacity=5, default_refill_rate=1, default_window_seconds=60
        )

        # Consume all tokens
        for _ in range(5):
            result = await limiter.try_acquire("test_api", tokens=1)
            assert isinstance(result, Ok)

        # Next should be rate limited
        result = await limiter.try_acquire("test_api", tokens=1)
        assert isinstance(result, Err)
        assert result.code == "RATE_LIMIT_EXCEEDED"

        # Check available
        available = await limiter.get_available("test_api")
        assert isinstance(available, Ok)
        assert available.unwrap() == 5

    async def test_rate_limiter_with_retry_executor(self):
        """Test RateLimiter integration with retry logic."""
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        limiter = RateLimiterImpl(
            default_capacity=3, default_refill_rate=1, default_window_seconds=60
        )

        # Make all 3 successful requests first
        for i in range(3):
            result = await limiter.try_acquire("test_api", tokens=1)
            assert isinstance(result, Ok)
            assert result.unwrap() is True

        # Next request should be rate limited
        result = await limiter.try_acquire("test_api", tokens=1)
        assert isinstance(result, Err)
        assert result.code == "RATE_LIMIT_EXCEEDED"

        # Simulate retry attempts (all should fail due to rate limit)
        retry_count = 0
        max_retries = 3

        for _ in range(max_retries):
            result = await limiter.try_acquire("test_api", tokens=1)
            if isinstance(result, Err) and result.code == "RATE_LIMIT_EXCEEDED":
                retry_count += 1
            else:
                # Should not succeed without waiting for refill
                break

        # All retries should fail
        assert retry_count == max_retries
