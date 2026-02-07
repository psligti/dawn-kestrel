"""Unit tests for LLM client abstraction and decorators."""

import pytest
import asyncio
import logging
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from dawn_kestrel.llm import (
    LLMClient,
    LLMProviderProtocol,
    LLMRequestOptions,
    LLMResponse,
    with_retry,
    with_timeout,
    with_logging,
)
from dawn_kestrel.providers.base import (
    ModelInfo,
    ProviderID,
    StreamEvent,
    TokenUsage,
    ModelCapabilities,
    ModelCost,
    ModelLimits,
)


class TestRetryDecorator:
    """Tests for the with_retry decorator."""

    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test that successful call completes without retries."""

        @with_retry(max_attempts=3, base_delay=0.01)
        async def succeed_immediately():
            return "success"

        result = await succeed_immediately()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_retries(self):
        """Test that retry logic works when function fails initially."""

        attempt_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        async def fail_twice_then_succeed():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError(f"Attempt {attempt_count} failed")
            return f"success on attempt {attempt_count}"

        result = await fail_twice_then_succeed()
        assert result == "success on attempt 3"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_retry_fails_after_max_attempts(self):
        """Test that function raises exception after max attempts."""

        @with_retry(max_attempts=2, base_delay=0.01)
        async def always_fail():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await always_fail()

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self):
        """Test that retry delay increases exponentially."""

        delays = []

        @with_retry(max_attempts=4, base_delay=1.0, exponential_base=2.0)
        async def fail_three_times():
            raise ValueError("Fail")

        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda delay: delays.append(delay)

            with pytest.raises(ValueError):
                await fail_three_times()

            # Delays should be: 1.0, 2.0, 4.0 (exponential: 2^0, 2^1, 2^2)
            assert delays == [1.0, 2.0, 4.0]

    @pytest.mark.asyncio
    async def test_retry_max_delay_cap(self):
        """Test that retry delay is capped at max_delay."""

        delays = []

        @with_retry(max_attempts=5, base_delay=1.0, exponential_base=10.0, max_delay=5.0)
        async def fail_four_times():
            raise ValueError("Fail")

        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda delay: delays.append(delay)

            with pytest.raises(ValueError):
                await fail_four_times()

            # Delays should be capped at 5.0: 1.0, 5.0, 5.0, 5.0
            assert delays == [1.0, 5.0, 5.0, 5.0]


class TestTimeoutDecorator:
    """Tests for the with_timeout decorator."""

    @pytest.mark.asyncio
    async def test_timeout_completes_before_limit(self):
        """Test that function completes before timeout."""

        @with_timeout(timeout_seconds=1.0)
        async def quick_function():
            await asyncio.sleep(0.1)
            return "completed"

        result = await quick_function()
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_timeout_raises_on_exceed(self):
        """Test that timeout exception is raised when limit exceeded."""

        @with_timeout(timeout_seconds=0.1)
        async def slow_function():
            await asyncio.sleep(1.0)
            return "never reached"

        with pytest.raises(TimeoutError, match="exceeded timeout"):
            await slow_function()


class TestLoggingDecorator:
    """Tests for the with_logging decorator."""

    @pytest.mark.asyncio
    async def test_logging_success(self, caplog):
        """Test that successful calls are logged."""

        @with_logging(log_args=True, log_result=True, log_level=logging.INFO)
        async def logged_function(x, y):
            return x + y

        with caplog.at_level(logging.INFO):
            result = await logged_function(2, 3)

        assert result == 5
        assert any("logged_function completed" in record.message for record in caplog.records)
        function_logs = [record for record in caplog.records if "logged_function" in record.message]
        assert function_logs
        assert all(record.name.startswith("dawn_kestrel") for record in function_logs)

    @pytest.mark.asyncio
    async def test_logging_failure(self, caplog):
        """Test that failed calls are logged."""

        @with_logging(log_exceptions=True, log_level=logging.INFO)
        async def failing_function():
            raise ValueError("Test error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                await failing_function()

        assert any("failing_function failed" in record.message for record in caplog.records)
        function_logs = [
            record for record in caplog.records if "failing_function" in record.message
        ]
        assert function_logs
        assert all(record.name.startswith("dawn_kestrel") for record in function_logs)


class TestLLMRequestOptions:
    """Tests for LLMRequestOptions dataclass."""

    def test_to_dict_filters_none_values(self):
        """Test that to_dict filters out None values."""
        options = LLMRequestOptions(
            temperature=0.7,
            max_tokens=1024,
            top_p=None,
            response_format=None,
        )

        result = options.to_dict()

        assert result == {
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        assert "top_p" not in result
        assert "response_format" not in result

    def test_to_dict_with_all_values(self):
        """Test that to_dict includes all non-None values."""
        options = LLMRequestOptions(
            temperature=0.7,
            top_p=0.9,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        result = options.to_dict()

        assert result == {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        }


class TestLLMClient:
    """Tests for LLMClient class."""

    @pytest.fixture
    def mock_model_info(self):
        """Fixture providing a mock ModelInfo."""
        return ModelInfo(
            id="test-model",
            provider_id=ProviderID.ANTHROPIC,
            api_id="claude-sonnet-4-20250514",
            api_url="https://api.test.com",
            name="Test Model",
            family="test",
            capabilities=ModelCapabilities(),
            cost=ModelCost(input=Decimal("3.0"), output=Decimal("15.0")),
            limit=ModelLimits(context=200000),
            status="active",
            options={},
            headers={},
        )

    @pytest.fixture
    def mock_provider(self, mock_model_info):
        """Fixture providing a mock provider."""
        provider = MagicMock(spec=LLMProviderProtocol)
        provider.get_models = AsyncMock(return_value=[mock_model_info])
        provider.stream = AsyncMock()
        provider.calculate_cost = MagicMock(return_value=Decimal("0.01"))
        return provider

    def test_client_initialization(self, mock_provider):
        """Test LLMClient initialization."""
        with patch("dawn_kestrel.llm.client.get_provider", return_value=mock_provider):
            client = LLMClient(
                provider_id=ProviderID.ANTHROPIC,
                model="claude-sonnet-4-20250514",
                api_key="test-key",
            )

            assert client.provider_id == ProviderID.ANTHROPIC
            assert client.model == "claude-sonnet-4-20250514"
            assert client.api_key == "test-key"
            assert client._provider == mock_provider

    def test_client_raises_on_unsupported_provider(self):
        """Test that LLMClient raises ValueError for unsupported provider."""
        with patch("dawn_kestrel.llm.client.get_provider", return_value=None):
            with pytest.raises(ValueError, match="Unsupported provider"):
                LLMClient(
                    provider_id=ProviderID.ANTHROPIC,
                    model="test-model",
                )

    @pytest.mark.asyncio
    async def test_ensure_model_info_caches_result(self, mock_provider, mock_model_info):
        """Test that _ensure_model_info caches model info."""
        with patch("dawn_kestrel.llm.client.get_provider", return_value=mock_provider):
            client = LLMClient(
                provider_id=ProviderID.ANTHROPIC,
                model="claude-sonnet-4-20250514",
            )

            # First call should fetch
            model_info_1 = await client._ensure_model_info()
            assert model_info_1 == mock_model_info

            # Second call should use cache
            model_info_2 = await client._ensure_model_info()
            assert model_info_2 == mock_model_info

            # get_models should only be called once
            assert mock_provider.get_models.call_count == 1

    @pytest.mark.asyncio
    async def test_ensure_model_info_raises_on_not_found(self, mock_provider):
        """Test that _ensure_model_info raises ValueError when model not found."""
        mock_provider.get_models = AsyncMock(return_value=[])

        with patch("dawn_kestrel.llm.client.get_provider", return_value=mock_provider):
            client = LLMClient(
                provider_id=ProviderID.ANTHROPIC,
                model="nonexistent-model",
            )

            with pytest.raises(ValueError, match="Model nonexistent-model not found"):
                await client._ensure_model_info()

    @pytest.mark.asyncio
    async def test_complete_success(self, mock_provider, mock_model_info):
        """Test that complete() successfully collects response."""
        # Mock streaming events
        stream_events_list = [
            StreamEvent(event_type="text-delta", data={"delta": "Hello "}),
            StreamEvent(event_type="text-delta", data={"delta": "world"}),
            StreamEvent(
                event_type="finish",
                data={
                    "finish_reason": "stop",
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                    },
                },
            ),
        ]

        async def stream_generator(model, messages, tools, options):
            for event in stream_events_list:
                yield event

        mock_provider.stream = stream_generator

        with patch("dawn_kestrel.llm.client.get_provider", return_value=mock_provider):
            client = LLMClient(
                provider_id=ProviderID.ANTHROPIC,
                model="claude-sonnet-4-20250514",
            )

            messages = [{"role": "user", "content": "Say hello"}]
            response = await client.complete(messages)

            assert response.text == "Hello world"
            assert response.usage.input == 10
            assert response.usage.output == 5
            assert response.model_info == mock_model_info
            assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_stream_yields_events(self, mock_provider, mock_model_info):
        """Test that stream() yields events correctly."""
        stream_events_list = [
            StreamEvent(event_type="start", data={}),
            StreamEvent(event_type="text-delta", data={"delta": "Hello"}),
        ]

        async def stream_generator(model, messages, tools, options):
            for event in stream_events_list:
                yield event

        mock_provider.stream = stream_generator

        with patch("dawn_kestrel.llm.client.get_provider", return_value=mock_provider):
            client = LLMClient(
                provider_id=ProviderID.ANTHROPIC,
                model="claude-sonnet-4-20250514",
            )

            messages = [{"role": "user", "content": "Say hello"}]
            events = []

            async for event in client.stream(messages):
                events.append(event)

            assert len(events) == 2
            assert events[0].event_type == "start"
            assert events[1].event_type == "text-delta"
            assert events[1].data["delta"] == "Hello"

    @pytest.mark.asyncio
    async def test_chat_completion_convenience_method(self, mock_provider, mock_model_info):
        """Test that chat_completion() provides backward-compatible API."""
        stream_events_list = [
            StreamEvent(event_type="text-delta", data={"delta": "Response"}),
            StreamEvent(
                event_type="finish",
                data={
                    "finish_reason": "stop",
                    "usage": {"prompt_tokens": 5, "completion_tokens": 3},
                },
            ),
        ]

        async def stream_generator(model, messages, tools, options):
            for event in stream_events_list:
                yield event

        stream_mock = Mock(side_effect=lambda *args, **kwargs: stream_generator(*args, **kwargs))
        mock_provider.stream = stream_mock

        with patch("dawn_kestrel.llm.client.get_provider", return_value=mock_provider):
            client = LLMClient(
                provider_id=ProviderID.ANTHROPIC,
                model="claude-sonnet-4-20250514",
            )

            result = await client.chat_completion(
                system_prompt="You are a helpful assistant",
                user_message="Say hi",
                temperature=0.7,
            )

            assert result == "Response"

            # Verify messages were constructed correctly
            call_args = mock_provider.stream.call_args
            messages_arg = call_args[1]["messages"]
            assert len(messages_arg) == 2
            assert messages_arg[0]["role"] == "system"
            assert messages_arg[0]["content"] == "You are a helpful assistant"
            assert messages_arg[1]["role"] == "user"
            assert messages_arg[1]["content"] == "Say hi"


async def aiter(items):
    """Helper to create async iterator from list."""
    for item in items:
        yield item
