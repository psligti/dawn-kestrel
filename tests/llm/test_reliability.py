"""Tests for LLMReliability combined resilience patterns.

Tests verify that LLMReliability wrapper correctly combines:
- Rate limiting (prevent API overload)
- Circuit breaking (isolate failing providers)
- Retry with backoff (handle transient failures)

Pattern ordering is critical: rate limit → circuit breaker → retry
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from dawn_kestrel.llm.reliability import (
    LLMReliability,
    LLMReliabilityImpl,
)
from dawn_kestrel.llm.rate_limiter import RateLimiterImpl
from dawn_kestrel.llm.circuit_breaker import CircuitBreakerImpl, CircuitState
from dawn_kestrel.llm.retry import RetryExecutorImpl, ExponentialBackoff
from dawn_kestrel.core.result import Ok, Err, Result
from dawn_kestrel.core.models import Message


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_messages():
    """Create sample message list."""
    return [
        Message(
            id="msg1",
            session_id="session1",
            role="user",
            text="Hello, how are you?",
        )
    ]


@pytest.fixture
def mock_provider():
    """Create mock provider adapter."""
    provider = AsyncMock()
    provider.generate_response = AsyncMock()
    provider.get_provider_name = AsyncMock(return_value="test_provider")
    return provider


@pytest.fixture
def mock_successful_response():
    """Create mock successful response."""
    return Message(
        id="response1",
        session_id="session1",
        role="assistant",
        text="I'm doing well, thank you!",
    )


@pytest.fixture
def rate_limiter():
    """Create rate limiter for testing."""
    return RateLimiterImpl(
        default_capacity=5,
        default_refill_rate=0.0833,  # 5 tokens per minute
        default_window_seconds=60,
    )()


@pytest.fixture
def circuit_breaker():
    """Create circuit breaker for testing."""
    # Note: CircuitBreakerImpl requires provider_adapter parameter
    # We'll mock it for testing
    mock_adapter = MagicMock()
    breaker = CircuitBreakerImpl(
        provider_adapter=mock_adapter,
        failure_threshold=5,
        half_open_threshold=3,
        timeout_seconds=300,
        reset_timeout_seconds=600,
    )
    # Open circuit to allow calls (starts CLOSED by default)
    asyncio.run(breaker.open())
    return breaker


@pytest.fixture
def retry_executor():
    """Create retry executor for testing."""
    return RetryExecutorImpl(
        max_attempts=3,
    )


@pytest.fixture
def reliability_wrapper(rate_limiter, circuit_breaker, retry_executor):
    """Create reliability wrapper with all patterns."""
    return LLMReliabilityImpl(
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        retry_executor=retry_executor,
    )


# =============================================================================
# LLMReliability Tests
# =============================================================================


class TestLLMReliabilityProtocol:
    """Tests for LLMReliability protocol."""

    def test_llm_reliability_is_protocol(self):
        """Verify LLMReliability is a protocol."""
        # Check for protocol-specific attributes
        assert hasattr(LLMReliability, "generate_with_resilience")
        assert hasattr(LLMReliability, "get_stats")

    def test_llm_reliability_has_generate_with_resilience(self):
        """Verify LLMReliability has generate_with_resilience method."""
        assert hasattr(LLMReliability, "generate_with_resilience")

    def test_llm_reliability_has_get_stats(self):
        """Verify LLMReliability has get_stats method."""
        assert hasattr(LLMReliability, "get_stats")


class TestLLMReliabilityImplInitialization:
    """Tests for LLMReliabilityImpl initialization."""

    def test_initialization_with_all_patterns(self, rate_limiter, circuit_breaker, retry_executor):
        """Verify initialization with all patterns."""
        wrapper = LLMReliabilityImpl(
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_executor=retry_executor,
        )
        assert wrapper._rate_limiter == rate_limiter
        assert wrapper._circuit_breaker == circuit_breaker
        assert wrapper._retry_executor == retry_executor

    def test_initialization_without_patterns(self):
        """Verify initialization without patterns (all optional)."""
        wrapper = LLMReliabilityImpl()
        assert wrapper._rate_limiter is None
        assert wrapper._circuit_breaker is None
        assert wrapper._retry_executor is None

    def test_stats_initialized(self, reliability_wrapper):
        """Verify statistics are initialized."""
        stats = asyncio.run(reliability_wrapper.get_stats())
        assert "total_calls" in stats
        assert "successful_calls" in stats
        assert "failed_calls" in stats
        assert "rate_limit_rejections" in stats
        assert "circuit_rejections" in stats
        assert "retry_attempts" in stats
        assert "errors_by_type" in stats


# =============================================================================
# Successful Generation Tests
# =============================================================================


class TestSuccessfulGeneration:
    """Tests for successful LLM generation."""

    @pytest.mark.asyncio
    async def test_generate_with_resilience_succeeds(
        self, reliability_wrapper, mock_provider, mock_successful_response
    ):
        """Verify successful generation works with all patterns."""
        # Setup
        mock_provider.generate_response.return_value = Ok(mock_successful_response)

        # Execute
        result = await reliability_wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            model="test-model",
            resource="test_provider",
        )

        # Verify
        assert result.is_ok()
        response = result.unwrap()
        assert response.text == mock_successful_response.text
        mock_provider.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_fails_on_closed_circuit(self, reliability_wrapper, mock_provider):
        """Verify generation fails when circuit is closed."""
        # Setup: Open circuit first, then close it
        await reliability_wrapper._circuit_breaker.close()

        # Execute
        result = await reliability_wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Verify
        assert result.is_err()
        assert result.code == "CIRCUIT_CLOSED"
        mock_provider.generate_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_stats_updated_on_circuit_rejection(self, reliability_wrapper, mock_provider):
        """Verify statistics updated on circuit rejection."""
        # Setup: Close circuit
        await reliability_wrapper._circuit_breaker.close()

        # Execute
        await reliability_wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Verify
        stats = await reliability_wrapper.get_stats()
        assert stats["circuit_rejections"] == 1
        assert stats["failed_calls"] == 1
        assert stats["errors_by_type"].get("circuit_breaker", 0) == 1


# =============================================================================
# Retry Tests
# =============================================================================


class TestRetry:
    """Tests for retry layer."""

    @pytest.mark.asyncio
    async def test_generate_retries_on_transient_failure(
        self, reliability_wrapper, mock_provider, mock_successful_response
    ):
        """Verify retry on transient failure."""
        # Setup: Fail twice, then succeed
        call_count = [0]

        async def side_effect(messages, model, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                return Err("Transient error", code="TRANSIENT_ERROR", retryable=True)
            return Ok(mock_successful_response)

        mock_provider.generate_response.side_effect = side_effect

        # Execute
        result = await reliability_wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Verify
        assert result.is_ok()
        assert call_count[0] == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_generate_returns_permanent_error(self, reliability_wrapper, mock_provider):
        """Verify permanent error returned without retry."""
        # Setup: Permanent error
        mock_provider.generate_response.return_value = Err(
            "Permanent error", code="PERMANENT_ERROR", retryable=False
        )

        # Execute
        result = await reliability_wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Verify
        assert result.is_err()
        assert result.code == "PERMANENT_ERROR"
        assert mock_provider.generate_response.call_count == 1  # No retry

    @pytest.mark.asyncio
    async def test_stats_updated_on_retry_attempts(
        self, reliability_wrapper, mock_provider, mock_successful_response
    ):
        """Verify statistics updated on retry attempts."""
        # Setup: Fail twice, then succeed
        call_count = [0]

        async def side_effect(messages, model, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                return Err("Transient error", code="TRANSIENT_ERROR", retryable=True)
            return Ok(mock_successful_response)

        mock_provider.generate_response.side_effect = side_effect

        # Execute
        await reliability_wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Verify
        stats = await reliability_wrapper.get_stats()
        assert stats["retry_attempts"] == 2  # 2 retries


# =============================================================================
# Pattern Ordering Tests
# =============================================================================


class TestPatternOrdering:
    """Tests for correct pattern ordering."""

    @pytest.mark.asyncio
    async def test_rate_limit_applies_before_circuit_breaker(
        self, reliability_wrapper, mock_provider
    ):
        """Verify rate limit checked before circuit breaker."""
        # Setup: Reset rate limiter and make 6 requests to hit rate limit
        await reliability_wrapper._rate_limiter.reset("test_provider")

        for i in range(6):
            mock_provider.generate_response.return_value = Ok(
                Message(id=f"r{i}", session_id="s1", role="assistant", text=f"R{i}")
            )

        # Execute: Should fail on rate limit, not circuit
        result = await reliability_wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Verify
        assert result.is_err()
        assert result.code == "RATE_LIMIT_EXCEEDED"  # Not CIRCUIT_CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_applies_after_rate_limit(
        self, rate_limiter, circuit_breaker, retry_executor, mock_provider
    ):
        """Verify circuit breaker checked after rate limit passes."""
        # Setup: Circuit closed, rate limit OK
        wrapper = LLMReliabilityImpl(
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_executor=retry_executor,
        )

        await wrapper._circuit_breaker.close()
        mock_provider.generate_response.return_value = Ok(
            Message(id="r1", session_id="s1", role="assistant", text="OK")
        )

        # Execute
        result = await wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Verify
        assert result.is_err()
        assert result.code == "CIRCUIT_CLOSED"

    @pytest.mark.asyncio
    async def test_retry_applies_after_circuit_breaker(
        self, rate_limiter, circuit_breaker, retry_executor, mock_provider
    ):
        """Verify retry applies after circuit breaker passes."""
        # Setup: Open circuit (allow calls), retryable failures
        await circuit_breaker.open()

        wrapper = LLMReliabilityImpl(
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_executor=retry_executor,
        )

        call_count = [0]

        async def side_effect(messages, model, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                return Err("Transient error", code="TRANSIENT_ERROR", retryable=True)
            return Ok(Message(id="r1", session_id="s1", role="assistant", text="Success"))

        mock_provider.generate_response.side_effect = side_effect

        # Execute
        result = await wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Verify: Should retry and succeed
        assert result.is_ok()
        assert call_count[0] == 3


# =============================================================================
# Graceful Degradation Tests
# =============================================================================


class TestGracefulDegradation:
    """Tests for graceful degradation behavior."""

    @pytest.mark.asyncio
    async def test_all_patterns_combined_rate_limit_first(self, reliability_wrapper, mock_provider):
        """Verify all patterns work together, rate limit checked first."""
        # Reset rate limiter for this test
        await reliability_wrapper._rate_limiter.reset("test_provider")

        # Make 6 requests: 5 allowed, 6th rate limited
        results = []
        for i in range(6):
            mock_provider.generate_response.return_value = Ok(
                Message(id=f"r{i}", session_id="s1", role="assistant", text=f"R{i}")
            )
            result = await reliability_wrapper.generate_with_resilience(
                provider_adapter=mock_provider,
                messages=[Message(id=f"m{i}", session_id="s1", role="user", text="Test")],
                resource="test_provider",
            )
            results.append(result)

        # Verify: First 5 succeed, 6th fails with rate limit
        assert sum(1 for r in results[:5] if r.is_ok()) == 5
        assert results[5].is_err()
        assert results[5].code == "RATE_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_all_patterns_combined_circuit_breaker_second(
        self, rate_limiter, circuit_breaker, retry_executor, mock_provider
    ):
        """Verify circuit breaker checked after rate limit."""
        # Setup: Circuit closed, rate limit OK
        await circuit_breaker.close()

        wrapper = LLMReliabilityImpl(
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_executor=retry_executor,
        )

        mock_provider.generate_response.return_value = Ok(
            Message(id="r1", session_id="s1", role="assistant", text="OK")
        )

        # Execute
        result = await wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Verify: Fails on circuit, not provider error
        assert result.is_err()
        assert result.code == "CIRCUIT_CLOSED"
        mock_provider.generate_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_patterns_combined_retry_third(
        self, rate_limiter, circuit_breaker, retry_executor, mock_provider
    ):
        """Verify retry applied after rate limit and circuit pass."""
        # Setup: Open circuit, rate limit OK, transient failures
        await circuit_breaker.open()

        wrapper = LLMReliabilityImpl(
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_executor=retry_executor,
        )

        call_count = [0]

        async def side_effect(messages, model, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                return Err("Transient error", code="TRANSIENT_ERROR", retryable=True)
            return Ok(Message(id="r1", session_id="s1", role="assistant", text="Success"))

        mock_provider.generate_response.side_effect = side_effect

        # Execute
        result = await wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Verify: Retries and succeeds
        assert result.is_ok()
        assert call_count[0] == 3


# =============================================================================
# Stats Tests
# =============================================================================


class TestStatistics:
    """Tests for reliability statistics."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_all_metrics(self, reliability_wrapper, mock_provider):
        """Verify get_stats returns all reliability metrics."""
        # Execute some calls
        mock_provider.generate_response.return_value = Ok(
            Message(id="r1", session_id="s1", role="assistant", text="OK")
        )
        await reliability_wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Get stats
        stats = await reliability_wrapper.get_stats()

        # Verify all keys present
        assert "total_calls" in stats
        assert "successful_calls" in stats
        assert "failed_calls" in stats
        assert "rate_limit_rejections" in stats
        assert "circuit_rejections" in stats
        assert "retry_attempts" in stats
        assert "errors_by_type" in stats

    @pytest.mark.asyncio
    async def test_stats_includes_pattern_specific_stats(self, reliability_wrapper, mock_provider):
        """Verify stats include pattern-specific metrics."""
        # Execute a call
        mock_provider.generate_response.return_value = Ok(
            Message(id="r1", session_id="s1", role="assistant", text="OK")
        )
        await reliability_wrapper.generate_with_resilience(
            provider_adapter=mock_provider,
            messages=[Message(id="m1", session_id="s1", role="user", text="Test")],
            resource="test_provider",
        )

        # Get stats
        stats = await reliability_wrapper.get_stats()

        # Verify pattern-specific stats included
        assert "retry_stats" in stats  # From retry_executor
        assert "circuit_state" in stats  # From circuit_breaker
