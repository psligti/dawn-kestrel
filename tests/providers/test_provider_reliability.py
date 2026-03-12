"""Tests for provider reliability patterns including rate limits, timeouts.

Tests verify that providers correctly handle:
- HTTP 429 with Retry-After headers
- Streaming-body rate limit payloads
- Timeout propagation through reliability layers
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dawn_kestrel.core.exceptions import ProviderRateLimitError
from dawn_kestrel.core.http_client import HTTPClientError, HTTPClientWrapper


# =============================================================================
# HTTPClientError Tests
# =============================================================================


class TestHTTPClientError:
    """Tests for HTTPClientError with retry_after support."""

    def test_http_client_error_inherits_from_provider_rate_limit_error(self):
        """Verify HTTPClientError inherits from ProviderRateLimitError."""
        assert issubclass(HTTPClientError, ProviderRateLimitError)

    def test_http_client_error_preserves_status_code(self):
        """Verify HTTPClientError preserves status_code field."""
        error = HTTPClientError(
            "Rate limit exceeded",
            status_code=429,
            retry_count=2,
        )
        assert error.status_code == 429
        assert error.retry_count == 2

    def test_http_client_error_preserves_retry_after(self):
        """Verify HTTPClientError preserves retry_after from HTTP 429."""
        error = HTTPClientError(
            "Rate limit exceeded. Retry after 60s",
            status_code=429,
            retry_after=60.0,
        )
        assert error.retry_after == 60.0

    def test_http_client_error_has_provider_field(self):
        """Verify HTTPClientError has provider field from parent."""
        error = HTTPClientError(
            "Rate limit exceeded",
            status_code=429,
            provider="openai",
        )
        assert error.provider == "openai"

    def test_http_client_error_default_provider_is_http_client(self):
        """Verify HTTPClientError defaults provider to 'http_client'."""
        error = HTTPClientError("Some error", status_code=500)
        assert error.provider == "http_client"

    def test_http_client_error_error_code_is_status_code(self):
        """Verify HTTPClientError sets error_code to status_code string."""
        error = HTTPClientError("Error", status_code=429)
        assert error.error_code == "429"

    def test_http_client_error_repr_includes_retry_after(self):
        """Verify repr includes retry_after when present."""
        error = HTTPClientError(
            "Rate limit exceeded",
            status_code=429,
            retry_after=30.0,
            provider="test",
        )
        repr_str = repr(error)
        assert "retry_after=30.0" in repr_str
        assert "provider='test'" in repr_str


# =============================================================================
# HTTPClientWrapper Rate Limit Tests
# =============================================================================


class TestHTTPClientWrapperRateLimit:
    """Tests for HTTPClientWrapper rate limit handling."""

    @pytest.mark.asyncio
    async def test_check_response_status_raises_on_429_with_retry_after(self):
        """Verify _check_response_status raises HTTPClientError on 429."""
        import httpx

        wrapper = HTTPClientWrapper()

        # Mock response with 429 status and Retry-After header
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        response.headers = {"Retry-After": "45"}

        with pytest.raises(HTTPClientError) as exc_info:
            wrapper._check_response_status(response)

        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 45.0

    @pytest.mark.asyncio
    async def test_check_response_status_defaults_retry_after_to_60(self):
        """Verify _check_response_status defaults retry_after to 60 if missing."""
        import httpx

        wrapper = HTTPClientWrapper()

        # Mock response with 429 status but no Retry-After header
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        response.headers = {}

        with pytest.raises(HTTPClientError) as exc_info:
            wrapper._check_response_status(response)

        assert exc_info.value.retry_after == 60.0

    @pytest.mark.asyncio
    async def test_check_response_status_handles_invalid_retry_after(self):
        """Verify _check_response_status handles invalid Retry-After values."""
        import httpx

        wrapper = HTTPClientWrapper()

        # Mock response with 429 status and invalid Retry-After header
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        response.headers = {"Retry-After": "invalid"}

        with pytest.raises(HTTPClientError) as exc_info:
            wrapper._check_response_status(response)

        # Should default to 60.0 when parsing fails
        assert exc_info.value.retry_after == 60.0


# =============================================================================
# ProviderRateLimitError Tests
# =============================================================================


class TestProviderRateLimitError:
    """Tests for ProviderRateLimitError exception."""

    def test_provider_rate_limit_error_has_retry_after(self):
        """Verify ProviderRateLimitError preserves retry_after field."""
        error = ProviderRateLimitError(
            "Rate limit exceeded",
            provider="z.ai",
            retry_after=120.0,
            error_code=1302,
        )
        assert error.retry_after == 120.0
        assert error.provider == "z.ai"
        assert error.error_code == "1302"

    def test_provider_rate_limit_error_retry_after_can_be_none(self):
        """Verify ProviderRateLimitError retry_after can be None."""
        error = ProviderRateLimitError(
            "Rate limit exceeded",
            provider="openai",
        )
        assert error.retry_after is None

    def test_provider_rate_limit_error_category_is_rate_limit(self):
        """Verify ProviderRateLimitError has RATE_LIMIT category."""
        from dawn_kestrel.core.exceptions import ErrorCategory

        error = ProviderRateLimitError("Rate limited", provider="test")
        assert error.category == ErrorCategory.RATE_LIMIT

    def test_provider_rate_limit_error_repr(self):
        """Verify ProviderRateLimitError repr includes all fields."""
        error = ProviderRateLimitError(
            "Rate limit exceeded",
            provider="z.ai",
            retry_after=30.0,
            error_code=1302,
        )
        repr_str = repr(error)
        assert "ProviderRateLimitError" in repr_str
        assert "provider='z.ai'" in repr_str
        assert "retry_after=30.0" in repr_str
        assert "error_code='1302'" in repr_str


# =============================================================================
# ZAI Base Provider Streaming Rate Limit Tests
# =============================================================================


class TestZAIBaseProviderStreamingRateLimit:
    """Tests for Z.AI provider streaming rate limit handling."""

    @pytest.mark.asyncio
    async def test_stream_raises_provider_rate_limit_error_on_code_1302(self):
        """Verify streaming raises ProviderRateLimitError on code 1302."""
        from dawn_kestrel.providers.zai_base import ZAIBaseProvider
        from dawn_kestrel.providers.base import (
            ModelInfo,
            ModelCapabilities,
            ModelCost,
            ModelLimits,
            ProviderID,
        )

        # Create a concrete implementation for testing
        class TestZAIBaseProvider(ZAIBaseProvider):
            async def get_models(self) -> list[ModelInfo]:
                return []

        provider = TestZAIBaseProvider(api_key="test-key")
        provider.base_url = "https://test.api"

        model = ModelInfo(
            id="test-model",
            provider_id=ProviderID.Z_AI,
            api_id="test-model",
            api_url="https://test.api",
            name="Test Model",
            family="test",
            capabilities=ModelCapabilities(
                temperature=True, reasoning=True, toolcall=True, input={"text": True}
            ),
            cost=ModelCost(input=0.01, output=0.03, cache=None),
            limit=ModelLimits(context=128000, input=128000, output=8192),
            status="active",
            options={},
            headers={},
        )

        # Mock the HTTP client to return rate limit error in stream
        async def mock_stream_generator():
            """Mock stream that yields rate limit error."""
            # Simulate rate limit error chunk in stream
            yield '{"error": {"code": 1302, "message": "Rate limit exceeded", "retry_after": 30}}'

        class MockResponse:
            """Mock response context manager."""

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def aiter_lines(self):
                async for line in mock_stream_generator():
                    yield f"data: {line}"

        async def mock_stream(*args, **kwargs):
            """Mock async generator that yields context managers."""
            yield MockResponse()

        # Patch the http_client.stream method
        with patch.object(provider.http_client, "stream", side_effect=mock_stream):
            with pytest.raises(ProviderRateLimitError) as exc_info:
                events = []
                async for event in provider.stream(model, [], []):
                    events.append(event)

            assert exc_info.value.error_code == "1302"
            assert exc_info.value.retry_after == 30.0
            assert exc_info.value.provider == "z.ai"

    @pytest.mark.asyncio
    async def test_stream_raises_provider_rate_limit_error_with_string_error(self):
        """Verify streaming handles error when error is a string."""
        from dawn_kestrel.providers.zai_base import ZAIBaseProvider
        from dawn_kestrel.providers.base import (
            ModelInfo,
            ModelCapabilities,
            ModelCost,
            ModelLimits,
            ProviderID,
        )

        class TestZAIBaseProvider(ZAIBaseProvider):
            async def get_models(self) -> list[ModelInfo]:
                return []

        provider = TestZAIBaseProvider(api_key="test-key")
        provider.base_url = "https://test.api"

        model = ModelInfo(
            id="test-model",
            provider_id=ProviderID.Z_AI,
            api_id="test-model",
            api_url="https://test.api",
            name="Test Model",
            family="test",
            capabilities=ModelCapabilities(
                temperature=True, reasoning=True, toolcall=True, input={"text": True}
            ),
            cost=ModelCost(input=0.01, output=0.03, cache=None),
            limit=ModelLimits(context=128000, input=128000, output=8192),
            status="active",
            options={},
            headers={},
        )

        # Mock stream with string error format
        async def mock_stream_generator():
            yield '{"error": "Rate limit exceeded", "code": 1302, "retry_after": 45}'

        class MockResponse:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def aiter_lines(self):
                async for line in mock_stream_generator():
                    yield f"data: {line}"

        async def mock_stream(*args, **kwargs):
            yield MockResponse()

        with patch.object(provider.http_client, "stream", side_effect=mock_stream):
            with pytest.raises(ProviderRateLimitError) as exc_info:
                events = []
                async for event in provider.stream(model, [], []):
                    events.append(event)

            assert exc_info.value.error_code == "1302"
            assert exc_info.value.retry_after == 45.0


# =============================================================================
# Timeout Propagation Tests
# =============================================================================


class TestTimeoutPropagation:
    """Tests for timeout propagation through reliability layers."""

    @pytest.mark.asyncio
    async def test_timeout_exception_is_propagated(self):
        """Verify timeout exceptions result in HTTPClientError after retries."""
        import httpx

        wrapper = HTTPClientWrapper(base_timeout=0.1, max_retries=0)

        # Mock the httpx client to raise TimeoutException
        with patch("dawn_kestrel.core.http_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.side_effect = httpx.TimeoutException("Connection timed out")

            with pytest.raises(HTTPClientError) as exc_info:
                await wrapper.post(
                    url="https://example.com/test",
                    timeout=0.1,
                )

            # Verify HTTPClientError with info about failure
            assert isinstance(exc_info.value, HTTPClientError)
            assert "Connection timed out" in str(exc_info.value)
            assert exc_info.value.retry_count == 0  # max_retries=0 means 1 attempt

    @pytest.mark.asyncio
    async def test_timeout_through_reliability_layer(self):
        """Verify timeout errors propagate through LLMReliability layer."""
        from dawn_kestrel.llm.reliability import LLMReliabilityImpl
        from dawn_kestrel.core.result import Err

        # Create reliability wrapper without rate limiter/circuit breaker
        reliability = LLMReliabilityImpl()

        # Create mock provider that raises HTTPClientError (timeout)
        mock_provider = AsyncMock()
        mock_provider.get_provider_name = AsyncMock(return_value="test_provider")

        # Simulate a timeout error
        async def failing_generate(*args, **kwargs):
            raise HTTPClientError(
                "Connection timed out",
                status_code=None,
                retry_count=3,
            )

        mock_provider.generate_response = failing_generate

        # Execute - HTTPClientError should bubble up through reliability
        with pytest.raises(HTTPClientError) as exc_info:
            await reliability.generate_with_resilience(
                provider_adapter=mock_provider,
                messages=[],
                resource="test",
            )

        assert "Connection timed out" in str(exc_info.value)


# =============================================================================
# ProviderRateLimitError Propagation Tests
# =============================================================================


class TestProviderRateLimitErrorPropagation:
    """Tests for ProviderRateLimitError propagation through retry layer."""

    @pytest.mark.asyncio
    async def test_retry_executor_re_raises_provider_rate_limit_error(self):
        """Verify RetryExecutorImpl re-raises ProviderRateLimitError to preserve retry_after."""
        from dawn_kestrel.llm.retry import RetryExecutorImpl
        from dawn_kestrel.core.result import Ok

        executor = RetryExecutorImpl(max_attempts=3)

        # Create a callable that raises ProviderRateLimitError
        async def failing_operation():
            raise ProviderRateLimitError(
                "Rate limit exceeded",
                provider="test_provider",
                retry_after=60.0,
                error_code=429,
            )

        # Execute - ProviderRateLimitError should bubble up without retry
        with pytest.raises(ProviderRateLimitError) as exc_info:
            await executor.execute(failing_operation)

        # Verify retry_after is preserved
        assert exc_info.value.retry_after == 60.0
        assert exc_info.value.provider == "test_provider"
        assert exc_info.value.error_code == "429"

        # Verify no retries occurred (would have been 3 attempts if retried)
        stats = await executor.get_stats()
        assert stats["last_attempt_count"] == 1  # Only 1 attempt, no retries

    @pytest.mark.asyncio
    async def test_reliability_layer_propagates_rate_limit_error(self):
        """Verify LLMReliability propagates ProviderRateLimitError with retry_after."""
        from dawn_kestrel.llm.reliability import LLMReliabilityImpl
        from dawn_kestrel.llm.rate_limiter import RateLimiterImpl
        from dawn_kestrel.llm.circuit_breaker import CircuitBreakerImpl
        from dawn_kestrel.llm.retry import RetryExecutorImpl

        # Create reliability wrapper with all layers
        rate_limiter = RateLimiterImpl(default_capacity=100)

        mock_adapter = MagicMock()
        circuit_breaker = CircuitBreakerImpl(
            provider_adapter=mock_adapter,
            failure_threshold=5,
        )
        # Open circuit to allow calls
        await circuit_breaker.open()

        retry_executor = RetryExecutorImpl(max_attempts=3)

        reliability = LLMReliabilityImpl(
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            retry_executor=retry_executor,
        )

        # Create mock provider that raises ProviderRateLimitError
        mock_provider = AsyncMock()
        mock_provider.get_provider_name = AsyncMock(return_value="test_provider")

        async def failing_generate(*args, **kwargs):
            raise ProviderRateLimitError(
                "Rate limit exceeded",
                provider="test_provider",
                retry_after=45.0,
                error_code=1302,
            )

        mock_provider.generate_response = failing_generate

        # Execute - ProviderRateLimitError should bubble up
        with pytest.raises(ProviderRateLimitError) as exc_info:
            await reliability.generate_with_resilience(
                provider_adapter=mock_provider,
                messages=[],
                resource="test_provider",
            )

        # Verify retry_after and error_code are preserved
        assert exc_info.value.retry_after == 45.0
        assert exc_info.value.provider == "test_provider"
        assert exc_info.value.error_code == "1302"
