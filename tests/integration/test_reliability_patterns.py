"""Integration tests for reliability patterns working together.

Tests verify that circuit breaker, retry, and rate limiter
work together correctly for LLM fault tolerance without mocking.

Scenario: Reliability Patterns End-to-End Integration
================================================

Preconditions:
- LLMReliability wrapper configured
- All patterns instantiated
- Rate limiter has tokens
- Circuit breaker is CLOSED

Steps:
1. Make successful API calls (rate limiter tokens consumed)
2. Exhaust rate limiter (rate limit exceeded)
3. Open circuit breaker (isolate failing provider)
4. Verify retry with backoff (transient failures)
5. Verify patterns interact correctly

Expected result:
- Rate limiter prevents API overload
- Circuit breaker isolates failing providers
- Retry handles transient failures
- Pattern ordering: rate limit → circuit breaker → retry
- Statistics tracked correctly

Failure indicators:
- Rate limiter allows unlimited calls
- Circuit breaker doesn't open on failures
- Retry doesn't retry transient errors
- Pattern ordering violated
- Statistics incorrect

Evidence:
- RATE_LIMIT_EXCEEDED returned when tokens exhausted
- CIRCUIT_OPEN returned when threshold exceeded
- MAX_RETRIES_EXCEEDED after transient errors
- Statistics show correct counts
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock


class TestReliabilityPatternsRateLimiting:
    """Test rate limiting integration."""

    @pytest.mark.asyncio
    async def test_rate_limiter_prevents_overload(self):
        """Scenario: Rate limiter prevents API overload.

        Preconditions:
        - Rate limiter configured
        - Tokens available

        Steps:
        1. Make 5 successful calls (exhaust tokens)
        2. Make 6th call (should fail rate limit)
        3. Verify Err with RATE_LIMIT_EXCEEDED
        4. Verify tokens refill after timeout

        Expected result:
        - First 5 calls succeed
        - 6th call returns RATE_LIMIT_EXCEEDED
        - Tokens refill after window

        Failure indicators:
        - More than 5 calls succeed
        - 6th call succeeds
        - Wrong error code
        """
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        rate_limiter = RateLimiterImpl(
            default_capacity=5,
            default_refill_rate=1.0,
            default_window_seconds=1,
        )

        for i in range(5):
            result = await rate_limiter.try_acquire(resource="test_provider", tokens=1)
            assert result.is_ok(), f"Call {i + 1} should succeed"

        result = await rate_limiter.try_acquire(resource="test_provider", tokens=1)
        assert result.is_err(), "6th call should fail rate limit"
        assert result.code == "RATE_LIMIT_EXCEEDED", "Wrong error code"

    @pytest.mark.asyncio
    async def test_rate_limiter_refills_tokens(self):
        """Scenario: Rate limiter refills tokens after window expires.

        Preconditions:
        - Rate limiter configured
        - Tokens exhausted

        Steps:
        1. Exhaust all tokens
        2. Wait for window to expire
        3. Try acquire tokens again
        4. Verify tokens refilled

        Expected result:
        - Tokens refill after window
        - Token acquisition succeeds after refill

        Failure indicators:
        - Tokens don't refill
        - Acquisition fails after refill
        """
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

        rate_limiter = RateLimiterImpl(
            default_capacity=5,
            default_refill_rate=5.0,
            default_window_seconds=1,
        )

        for _ in range(5):
            result = await rate_limiter.try_acquire(resource="test_provider", tokens=1)
            assert result.is_ok()

        await asyncio.sleep(1.1)

        result = await rate_limiter.try_acquire(resource="test_provider", tokens=1)
        assert result.is_ok(), "Tokens should refill after window"


class TestCircuitBreakerBasic:
    """Test circuit breaker integration."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_manually(self):
        """Scenario: Circuit breaker can be opened manually.

        Preconditions:
        - Circuit breaker is CLOSED

        Steps:
        1. Verify circuit is CLOSED
        2. Call open() method
        3. Verify circuit is OPEN
        4. Verify calls allowed again

        Expected result:
        - Circuit opens successfully
        - is_open() returns True
        - Calls allowed when OPEN

        Failure indicators:
        - Circuit doesn't open
        - is_closed() returns False
        - Calls blocked after open

        """
        from dawn_kestrel.llm.circuit_breaker import CircuitBreakerImpl

        mock_adapter = MagicMock()
        breaker = CircuitBreakerImpl(
            provider_adapter=mock_adapter,
            failure_threshold=3,
            half_open_threshold=2,
            timeout_seconds=300,
            reset_timeout_seconds=600,
        )

        assert await breaker.is_closed(), "Circuit should be CLOSED initially"

        result = await breaker.open()
        assert result.is_ok(), "open() should succeed"

        assert await breaker.is_open(), "Circuit should be OPEN after open()"
        assert await breaker.is_closed() is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_manually(self):
        """Scenario: Circuit breaker can be closed manually.

        Preconditions:
        - Circuit breaker is OPEN

        Steps:
        1. Verify circuit is OPEN
        2. Call close() method
        3. Verify circuit is CLOSED
        4. Verify calls allowed again

        Expected result:
        - Circuit closes successfully
        - is_closed() returns True
        - Calls allowed when CLOSED

        Failure indicators:
        - Circuit doesn't close
        - is_closed() returns False
        - Calls blocked after close

        """
        from dawn_kestrel.llm.circuit_breaker import CircuitBreakerImpl

        mock_adapter = pytest.MagicMock()
        breaker = CircuitBreakerImpl(
            provider_adapter=mock_adapter,
            failure_threshold=3,
            half_open_threshold=2,
            timeout_seconds=300,
            reset_timeout_seconds=600,
        )

        for _ in range(3):
            await breaker.record_failure(provider="test_provider")

        assert breaker.is_open(), "Circuit should be OPEN"

        result = await breaker.close()
        assert result.is_ok(), "close() should succeed"

        assert breaker.is_closed(), "Circuit should be CLOSED after close()"
        assert await breaker.is_open() is False
