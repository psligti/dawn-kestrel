"""OpenCode Python - LLM Client Abstraction.

Provider-agnostic LLM client with explicit runtime policies for retry,
timeout, and logging.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable, Coroutine
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from typing import (
    Any,
    TypeVar,
    cast,
)

import httpx
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from dawn_kestrel.providers import get_provider
from dawn_kestrel.providers.base import (
    ModelInfo,
    ProviderID,
    StreamEvent,
    TokenUsage,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Global Rate Limiter
# =============================================================================

from dawn_kestrel.llm.evidence_sharing import (
    EvidenceSharingStrategy,
    NoOpEvidenceSharingStrategy,
    create_request_fingerprint,
)
from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

_global_rate_limiter: RateLimiterImpl | None = None
_global_concurrency_semaphore: asyncio.Semaphore | None = None


def configure_global_rate_limiter(
    capacity: int = 10,
    refill_rate: float = 0.5,
    window_seconds: int = 1,
) -> RateLimiterImpl:
    """Configure the global rate limiter for all LLM calls.

    This should be called once at application startup. All LLMClient instances
    will share this rate limiter to prevent API overload.

    Args:
        capacity: Maximum tokens in the bucket (default: 10 concurrent requests)
        refill_rate: Tokens added per window (default: 0.5, meaning 1 token every 2 seconds)
        window_seconds: Time window for refill (default: 1.0 second)

    Returns:
        The configured rate limiter instance

    Example:
        # At application startup
        from dawn_kestrel.llm.client import configure_global_rate_limiter
        configure_global_rate_limiter(capacity=5, refill_rate=0.5)
    """
    global _global_rate_limiter, _global_concurrency_semaphore
    _global_rate_limiter = RateLimiterImpl(
        default_capacity=capacity,
        default_refill_rate=refill_rate,
        default_window_seconds=window_seconds,
    )
    _global_concurrency_semaphore = asyncio.Semaphore(capacity)
    logger.info(f"Global rate limiter configured: capacity={capacity}, refill_rate={refill_rate}/s")
    return _global_rate_limiter


def get_global_rate_limiter() -> RateLimiterImpl | None:
    """Get the global rate limiter instance."""
    return _global_rate_limiter


def with_logging(
    log_args: bool = False,
    log_result: bool = False,
    log_exceptions: bool = True,
    log_level: int = logging.INFO,
):
    """Decorator for logging function calls.

    Args:
        log_args: Whether to log function arguments
        log_result: Whether to log function results
        log_exceptions: Whether to log exception details
        log_level: Logging level for normal messages

    Returns:
        Decorated function with logging logic

    Example:
        @with_logging(log_args=True, log_result=True)
        async def process_request(request):
            ...
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            module_name = getattr(func, "__module__", "unknown")
            attr_name = getattr(func, "__name__", "unknown")
            func_name = f"{module_name}.{attr_name}"

            logger.log(log_level, f"Calling {func_name}")
            if log_args:
                logger.debug(f"  Args: {args}")
                logger.debug(f"  Kwargs: {kwargs}")

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time

                logger.log(log_level, f"{func_name} completed in {elapsed:.2f}s")
                if log_result:
                    logger.debug(f"  Result: {result}")

                return result
            except Exception as e:
                elapsed = time.time() - start_time

                if log_exceptions:
                    logger.error(f"{func_name} failed after {elapsed:.2f}s: {e}", exc_info=True)
                else:
                    logger.error(f"{func_name} failed after {elapsed:.2f}s: {e}")

                raise

        return wrapper

    return decorator


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
):
    """Decorator for retrying async operations with exponential backoff."""

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:  # pragma: no cover - re-raised below
                    last_error = exc
                    if attempt >= max_attempts:
                        break

                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    await asyncio.sleep(delay)

            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


def with_timeout(timeout_seconds: float):
    """Decorator that enforces an asyncio timeout for async operations."""

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except TimeoutError as exc:
                func_name = getattr(func, "__name__", "operation")
                raise TimeoutError(f"{func_name} exceeded timeout of {timeout_seconds}s") from exc

        return wrapper

    return decorator


@dataclass
class LLMRequestOptions:
    """Options for LLM requests."""

    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    response_format: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, filtering out None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class LLMResponse:
    """Response from LLM provider.

    Attributes:
        text: The text content of the response.
        usage: Token usage statistics.
        model_info: Information about the model used.
        finish_reason: Why the response finished (stop, tool_use, etc.).
        cost: Cost of the request in USD.
        tool_calls: List of tool calls made during the response.
        messages: Full message history for the response (for eval transcript capture).
    """

    text: str
    usage: TokenUsage
    model_info: ModelInfo | None = None
    finish_reason: str = "stop"
    cost: Decimal = Decimal("0")
    tool_calls: list[dict[str, Any]] | None = None
    messages: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for LLM calls."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0


class LLMProviderProtocol(ABC):
    """Protocol defining the interface for LLM providers.

    This protocol abstracts provider-specific details and allows
    different providers (Anthropic, OpenAI, etc.) to be used
    interchangeably.
    """

    @abstractmethod
    async def get_models(self) -> list[ModelInfo]:
        """Get available models.

        Returns:
            List of ModelInfo objects
        """
        pass

    @abstractmethod
    async def stream(
        self,
        model: ModelInfo,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        options: dict[str, Any],
    ) -> AsyncIterator[StreamEvent]:
        """Stream LLM response.

        Args:
            model: ModelInfo object
            messages: List of message dictionaries
            tools: Tool definitions
            options: Additional options (temperature, etc.)

        Yields:
            StreamEvent objects

        Raises:
            httpx.HTTPError: If API call fails
        """
        pass

    @abstractmethod
    def calculate_cost(self, usage: TokenUsage, model: ModelInfo) -> Decimal:
        """Calculate cost for token usage.

        Args:
            usage: Token usage data
            model: ModelInfo object

        Returns:
            Cost in USD
        """
        pass


class LLMClient:
    """Provider-agnostic LLM client with policy-driven retry, timeout, and logging.

    This client provides a unified interface for calling different LLM providers
    while handling retries, timeouts, and observability through decorators.

    The client is designed to be compatible with existing AISession
    semantics and provider system.

    Example:
        client = LLMClient(
            provider_id=ProviderID.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            api_key="your-api-key",
        )

        response = await client.complete(
            messages=[{"role": "user", "content": "Hello"}],
            options=LLMRequestOptions(temperature=0.7),
        )
    """

    def __init__(
        self,
        provider_id: str | ProviderID,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        timeout_seconds: float = 120.0,
        evidence_sharing_strategy: EvidenceSharingStrategy | None = None,
    ):
        """Initialize LLM client.

        Args:
            provider_id: Provider identifier (anthropic, openai, etc.)
            model: Model identifier
            api_key: API key for the provider
            base_url: Custom base URL (optional)
            max_retries: Maximum number of retry attempts
            timeout_seconds: Request timeout in seconds
        """
        self.provider_id = ProviderID(provider_id)
        self.model = model
        self.api_key = api_key or ""
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.retry_policy = RetryPolicy(max_attempts=max_retries)
        self._evidence_sharing_strategy = evidence_sharing_strategy or NoOpEvidenceSharingStrategy()

        self._provider = get_provider(self.provider_id, self.api_key)
        self._model_info: ModelInfo | None = None

        if self._provider is None:
            raise ValueError(f"Unsupported provider: {self.provider_id}")

    @property
    def provider(self) -> Any:
        """Get the underlying provider instance."""
        if self._provider is None:
            raise ValueError("Provider not initialized")
        return self._provider

    async def _ensure_model_info(self) -> ModelInfo:
        """Ensure model_info is loaded."""
        if self._model_info is None:
            models = await self.provider.get_models()
            for model_info in models:
                if model_info.api_id == self.model:
                    self._model_info = model_info
                    break

            if self._model_info is None:
                raise ValueError(f"Model {self.model} not found for provider {self.provider_id}")

        assert self._model_info is not None
        return self._model_info

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        options: LLMRequestOptions | dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream LLM response with built-in retry, timeout, and logging.

        Args:
            messages: List of message dictionaries
            tools: List of tool definitions (optional)
            options: Request options (temperature, etc.)

        Yields:
            StreamEvent objects

        Raises:
            TimeoutError: If request exceeds timeout
            httpx.HTTPError: If API call fails after retries
        """
        model_info = await self._ensure_model_info()

        if isinstance(options, LLMRequestOptions):
            options_dict = options.to_dict()
        else:
            options_dict = options or {}

        timeout_task = asyncio.create_task(self._generate_timeout(self.timeout_seconds))
        stream_task = asyncio.create_task(
            self._collect_stream_events_with_retry(model_info, messages, tools, options_dict)
        )

        done, pending = await asyncio.wait(
            {timeout_task, stream_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        if timeout_task in done:
            raise TimeoutError(f"LLM stream exceeded timeout of {self.timeout_seconds}s")

        events = stream_task.result()
        for event in events:
            yield event

    async def stream_realtime(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        options: LLMRequestOptions | dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream LLM response in real-time WITHOUT buffering.

        Unlike stream() which collects all events before yielding,
        this method yields each event as it arrives from the provider.
        This enables real-time streaming output for interactive use.

        Args:
            messages: List of message dictionaries
            tools: List of tool definitions (optional)
            options: Request options (temperature, etc.)

        Yields:
            StreamEvent objects as they arrive
        """
        model_info = await self._ensure_model_info()

        if isinstance(options, LLMRequestOptions):
            options_dict = options.to_dict()
        else:
            options_dict = options or {}

        # Yield events directly from provider without buffering
        async for event in self.provider.stream(
            model=model_info,
            messages=messages,
            tools=tools,
            options=options_dict,
        ):
            yield event
    async def _generate_timeout(self, timeout_seconds: float):
        await asyncio.sleep(timeout_seconds)

    @with_logging(log_args=False, log_result=False, log_level=logging.INFO)
    async def _collect_stream_events_once(
        self,
        model_info: ModelInfo,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        options: dict[str, Any],
    ) -> list[StreamEvent]:
        async def collect() -> list[StreamEvent]:
            events: list[StreamEvent] = []
            async for event in self.provider.stream(
                model=model_info,
                messages=messages,
                tools=tools,
                options=options,
            ):
                events.append(event)
            return events

        return await asyncio.wait_for(collect(), timeout=self.timeout_seconds)

    async def _collect_stream_events_with_retry(
        self,
        model_info: ModelInfo,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        options: dict[str, Any],
    ) -> list[StreamEvent]:
        """Collect stream events with tenacity retry and concurrency limit."""

        transient_exceptions: tuple[type[BaseException], ...] = (
            httpx.RemoteProtocolError,
            httpx.NetworkError,
            httpx.TimeoutException,
            TimeoutError,
        )

        async def refresh_provider() -> None:
            self._provider = get_provider(self.provider_id, self.api_key)
            if self._provider is None:
                raise ValueError(f"Unsupported provider: {self.provider_id}")
            self._model_info = None

        async def acquire_rate_limit():
            if _global_rate_limiter is None:
                return
            while True:
                acquire_result = await _global_rate_limiter.try_acquire(
                    resource=str(self.provider_id),
                    tokens=1,
                )
                if acquire_result.is_ok():
                    return
                backoff = 1.0
                logger.debug("Rate limit wait for %s, waiting %.1fs...", self.provider_id, backoff)
                await asyncio.sleep(backoff)

        async def execute_with_limits():
            if _global_concurrency_semaphore is not None:
                async with _global_concurrency_semaphore:
                    await acquire_rate_limit()
                    return await self._collect_stream_events_once(
                        model_info=model_info,
                        messages=messages,
                        tools=tools,
                        options=options,
                    )
            else:
                await acquire_rate_limit()
                return await self._collect_stream_events_once(
                    model_info=model_info,
                    messages=messages,
                    tools=tools,
                    options=options,
                )

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.retry_policy.max_attempts),
            wait=wait_random_exponential(
                multiplier=self.retry_policy.base_delay,
                max=self.retry_policy.max_delay,
            ),
            retry=retry_if_exception_type(transient_exceptions),
            reraise=True,
            before_sleep=before_sleep_log(cast(Any, logger), logging.WARNING),
        ):
            with attempt:
                try:
                    return await execute_with_limits()
                except transient_exceptions:
                    await refresh_provider()
                    raise

        raise Exception("Should not reach here")

    @with_logging(log_args=False, log_result=False, log_level=logging.INFO)
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        options: LLMRequestOptions | dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Get complete LLM response (non-streaming) with built-in retry, timeout, and logging.

        This method collects all streaming events into a single response.

        Args:
            messages: List of message dictionaries
            tools: List of tool definitions (optional)
            options: Request options (temperature, etc.)

        Returns:
            LLMResponse object with text, usage, and metadata

        Raises:
            TimeoutError: If request exceeds timeout
            httpx.HTTPError: If API call fails after retries
        """
        request_fingerprint = create_request_fingerprint(
            provider_id=str(self.provider_id),
            model=self.model,
            messages=messages,
            tools=tools,
            options=options,
        )
        cached_response = await self._evidence_sharing_strategy.get(request_fingerprint)
        if cached_response is not None:
            return deepcopy(cached_response)

        model_info = await self._ensure_model_info()

        text_parts: list[str] = []
        usage = TokenUsage(input=0, output=0, reasoning=0, cache_read=0, cache_write=0)
        finish_reason = "stop"
        tool_calls: list[dict[str, Any]] = []

        events = await self._collect_stream_events_with_retry(
            model_info,
            messages,
            tools,
            options.to_dict() if isinstance(options, LLMRequestOptions) else (options or {}),
        )

        for event in events:
            if event.event_type == "text-delta":
                delta = event.data.get("delta", "")
                text_parts.append(delta)
            elif event.event_type == "tool-call":
                # Capture tool calls for eval transcript
                tool_calls.append(
                    {
                        "tool": event.data.get("tool"),
                        "input": event.data.get("input"),
                    }
                )
            elif event.event_type == "finish":
                usage_data = event.data.get("usage", {})
                if usage_data:
                    usage = TokenUsage(
                        input=usage_data.get("prompt_tokens", 0),
                        output=usage_data.get("completion_tokens", 0),
                        reasoning=usage_data.get("reasoning_tokens", 0),
                        cache_read=usage_data.get("cache_read_tokens", 0),
                        cache_write=usage_data.get("cache_write_tokens", 0),
                    )
                finish_reason = event.data.get("finish_reason", "stop")
                break

        cost = self.provider.calculate_cost(usage, model_info)

        response = LLMResponse(
            text="".join(text_parts),
            usage=usage,
            model_info=model_info,
            finish_reason=finish_reason,
            cost=cost,
            tool_calls=tool_calls if tool_calls else None,
            messages=messages,  # Pass through for eval transcript capture
        )
        await self._evidence_sharing_strategy.set(request_fingerprint, response)
        return response

    async def clear_evidence_cache(self) -> None:
        await self._evidence_sharing_strategy.clear()

    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: dict[str, str] | None = None,
    ) -> str:
        """Convenience method for simple chat completion.

        This method provides backward compatibility with the original LLMClient API.

        Args:
            system_prompt: System prompt for LLM
            user_message: User message to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            response_format: Optional format specification

        Returns:
            Response text from LLM

        Raises:
            TimeoutError: If request exceeds timeout
            httpx.HTTPError: If API call fails after retries
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        options = LLMRequestOptions(
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

        response = await self.complete(messages, options=options)
        return response.text
