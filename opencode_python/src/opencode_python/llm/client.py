"""OpenCode Python - LLM Client Abstraction

Provider-agnostic LLM client with retry, timeout, and logging decorators.
Designed to work with existing provider system and maintain AISession compatibility.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import time
from decimal import Decimal
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    TypeVar,
    cast,
    ParamSpec,
)
from dataclasses import dataclass
from abc import ABC, abstractmethod

from opencode_python.providers.base import (
    ModelInfo,
    ProviderID,
    StreamEvent,
    TokenUsage,
)
from opencode_python.providers import get_provider


logger = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
):
    """Decorator for retrying async functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(max_attempts=3, base_delay=1.0)
        async def call_llm():
            ...
    """
    def decorator(func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt >= max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay,
                    )

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)

            raise cast(Exception, last_exception)

        return wrapper

    return decorator


def with_timeout(timeout_seconds: float):
    """Decorator for adding timeout to async functions.

    Args:
        timeout_seconds: Maximum execution time in seconds

    Returns:
        Decorated function with timeout logic

    Example:
        @with_timeout(timeout_seconds=120)
        async def long_running_call():
            ...
    """
    def decorator(func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {timeout_seconds}s")
                raise TimeoutError(
                    f"Function {func.__name__} exceeded timeout of {timeout_seconds}s"
                )

        return wrapper

    return decorator


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
    def decorator(func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            func_name = f"{func.__module__}.{func.__name__}"

            logger.log(log_level, f"Calling {func_name}")
            if log_args:
                logger.debug(f"  Args: {args}")
                logger.debug(f"  Kwargs: {kwargs}")

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time

                logger.log(
                    log_level,
                    f"{func_name} completed in {elapsed:.2f}s"
                )
                if log_result:
                    logger.debug(f"  Result: {result}")

                return result
            except Exception as e:
                elapsed = time.time() - start_time

                if log_exceptions:
                    logger.error(
                        f"{func_name} failed after {elapsed:.2f}s: {e}",
                        exc_info=True
                    )
                else:
                    logger.error(f"{func_name} failed after {elapsed:.2f}s: {e}")

                raise

        return wrapper

    return decorator


@dataclass
class LLMRequestOptions:
    """Options for LLM requests."""

    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, filtering out None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    text: str
    usage: TokenUsage
    model_info: Optional[ModelInfo] = None
    finish_reason: str = "stop"
    cost: Decimal = Decimal("0")


class LLMProviderProtocol(ABC):
    """Protocol defining the interface for LLM providers.

    This protocol abstracts provider-specific details and allows
    different providers (Anthropic, OpenAI, etc.) to be used
    interchangeably.
    """

    @abstractmethod
    async def get_models(self) -> List[ModelInfo]:
        """Get available models.

        Returns:
            List of ModelInfo objects
        """
        pass

    @abstractmethod
    async def stream(
        self,
        model: ModelInfo,
        messages: List[Dict[str, Any]],
        tools: Dict[str, Any],
        options: Dict[str, Any],
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
    """Provider-agnostic LLM client with built-in retry, timeout, and logging.

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
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        timeout_seconds: float = 120.0,
    ):
        """Initialize LLM client.

        Args:
            provider_id: Provider identifier (anthropic, openai, etc.)
            model: Model identifier
            api_key: API key for provider
            base_url: Custom base URL (optional)
            max_retries: Maximum number of retry attempts
            timeout_seconds: Request timeout in seconds
        """
        self.provider_id = ProviderID(provider_id) if isinstance(provider_id, str) else provider_id
        self.model = model
        self.api_key = api_key or ""
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

        self._provider = get_provider(self.provider_id, self.api_key)
        self._model_info: Optional[ModelInfo] = None

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

        return cast(ModelInfo, self._model_info)

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        options: Optional[LLMRequestOptions | Dict[str, Any]] = None,
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

        tools_dict = {} if tools is None else {"tools": tools}

        timeout_task = asyncio.create_task(
            self._generate_timeout(self.timeout_seconds)
        )
        stream_task = asyncio.create_task(
            self._collect_stream_events(
                model_info, messages, tools_dict, options_dict
            )
        )

        done, pending = await asyncio.wait(
            {timeout_task, stream_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        if timeout_task in done:
            raise TimeoutError(
                f"LLM stream exceeded timeout of {self.timeout_seconds}s"
            )

        events = stream_task.result()
        for event in events:
            yield event

    async def _generate_timeout(self, timeout_seconds: float):
        await asyncio.sleep(timeout_seconds)

    @with_retry(max_attempts=3, base_delay=1.0)
    @with_logging(log_args=False, log_result=False, log_level=logging.INFO)
    async def _collect_stream_events(
        self,
        model_info: ModelInfo,
        messages: List[Dict[str, Any]],
        tools: Dict[str, Any],
        options: Dict[str, Any],
    ) -> List[StreamEvent]:
        events = []
        async for event in self.provider.stream(
            model=model_info,
            messages=messages,
            tools=tools,
            options=options,
        ):
            events.append(event)
        return events

    @with_timeout(timeout_seconds=120.0)
    @with_logging(log_args=False, log_result=False, log_level=logging.INFO)
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        options: Optional[LLMRequestOptions | Dict[str, Any]] = None,
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
        model_info = await self._ensure_model_info()

        text_parts: List[str] = []
        usage = TokenUsage(input=0, output=0, reasoning=0, cache_read=0, cache_write=0)
        finish_reason = "stop"

        events = await self._collect_stream_events(
            model_info, messages,
            {} if tools is None else {"tools": tools},
            options.to_dict() if isinstance(options, LLMRequestOptions) else (options or {}),
        )

        for event in events:
            if event.event_type == "text-delta":
                delta = event.data.get("delta", "")
                text_parts.append(delta)
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

        return LLMResponse(
            text="".join(text_parts),
            usage=usage,
            model_info=model_info,
            finish_reason=finish_reason,
            cost=cost,
        )

    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
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


class LegacyLLMClient(LLMClient):
    """Legacy LLMClient for backward compatibility.

    This class maintains the original API of the first LLMClient implementation.
    New code should use LLMClient directly.
    """

    def __init__(
        self,
        provider_id: str = "z.ai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "glm-4.7",
    ):
        """Initialize legacy LLM client.

        Args:
            provider_id: Provider identifier (z.ai, zai-coding-plan, openai, anthropic)
            api_key: API key for provider
            base_url: Custom base URL (overrides default)
            model: Model identifier to use
        """
        super().__init__(
            provider_id=provider_id,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        logger.warning(
            "LegacyLLMClient is deprecated. Use LLMClient with proper provider_id instead."
        )
