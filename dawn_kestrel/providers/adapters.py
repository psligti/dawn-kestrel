"""ProviderAdapter pattern for provider extension.

Adapter pattern normalizes provider interface, enabling custom providers
without modifying core code.

This module provides:
- ProviderAdapter protocol for adapter interface
- OpenAIAdapter and ZAIAdapter implementations
- Adapter registration system for custom providers
"""

from __future__ import annotations

import logging
import asyncio
from typing import Protocol, runtime_checkable, Optional

from dawn_kestrel.core.result import Ok, Err, Result
from dawn_kestrel.core.models import Message
from dawn_kestrel.providers.base import ModelInfo, StreamEvent


logger = logging.getLogger(__name__)


# =============================================================================
# Adapter Registry (private module state)
# =============================================================================

_adapters: dict[str, ProviderAdapter] = {}
"""Registry for custom provider adapters.

Adapters can be registered via register_adapter() and retrieved
via get_adapter() or listed via list_adapters().
"""


# =============================================================================
# ProviderAdapter Protocol
# =============================================================================


@runtime_checkable
class ProviderAdapter(Protocol):
    """Protocol for provider adapter.

    Adapter pattern normalizes provider interface, enabling
    custom providers without modifying core code.

    The adapter wraps a provider instance and provides a normalized
    interface for generating responses.

    Example:
        adapter = OpenAIAdapter(provider)
        result = await adapter.generate_response(messages, "gpt-5")
        if result.is_ok():
            response = result.unwrap()
    """

    async def generate_response(
        self, messages: list[Message], model: str, **kwargs
    ) -> Result[Message]:
        """Generate response using provider.

        Args:
            messages: List of messages for context.
            model: Model identifier.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Result[Message]: Response message on success, Err on failure.
        """
        ...

    async def get_provider_name(self) -> str:
        """Get the name of the underlying provider."""
        ...


# =============================================================================
# OpenAIAdapter
# =============================================================================


class OpenAIAdapter:
    """Adapter for OpenAI provider.

    Wraps OpenAIProvider to provide normalized interface with Result types.
    Converts Message models to provider format and collects stream events.

    Example:
        from dawn_kestrel.providers import OpenAIProvider
        provider = OpenAIProvider(api_key="sk-...")
        adapter = OpenAIAdapter(provider)
        result = await adapter.generate_response(messages, "gpt-5")
    """

    def __init__(self, provider):
        """Initialize OpenAI adapter.

        Args:
            provider: OpenAIProvider instance or compatible provider.
        """
        self._provider = provider

    async def generate_response(
        self, messages: list[Message], model: str, **kwargs
    ) -> Result[Message]:
        """Generate response using OpenAI provider.

        Converts Message models to list format expected by provider,
        collects stream events, and returns Result[Message].

        Args:
            messages: List of Message objects.
            model: Model identifier (e.g., "gpt-5").
            **kwargs: Additional provider options.

        Returns:
            Result[Message]: Response message on success, Err on failure.
        """
        try:
            # Get model info from provider
            models = await self._provider.get_models()
            model_info = None
            for m in models:
                if m.api_id == model:
                    model_info = m
                    break

            if model_info is None:
                return Err(f"Model {model} not found in provider", code="MODEL_NOT_FOUND")

            # Convert Message models to provider format
            provider_messages = [{"role": msg.role, "content": msg.text or ""} for msg in messages]

            # Collect stream events
            text_parts = []
            finish_reason = "stop"

            async for event in self._provider.stream(
                model=model_info, messages=provider_messages, tools=[], options=kwargs
            ):
                if event.event_type == "text-delta":
                    delta = event.data.get("delta", "")
                    if delta:
                        text_parts.append(delta)
                elif event.event_type == "finish":
                    finish_reason = event.data.get("finish_reason", "stop")
                    break

            # Create response Message
            response = Message(
                id=f"openai-{asyncio.get_event_loop().time()}",
                session_id=messages[0].session_id if messages else "unknown",
                role="assistant",
                text="".join(text_parts),
            )

            return Ok(response)

        except Exception as e:
            logger.error(f"OpenAI provider error: {e}", exc_info=True)
            return Err(f"OpenAI provider error: {e}", code="PROVIDER_ERROR")

    async def get_provider_name(self) -> str:
        """Get the name of the underlying provider."""
        return "openai"


# =============================================================================
# ZAIAdapter
# =============================================================================


class ZAIAdapter:
    """Adapter for Z.AI provider.

    Wraps ZAIProvider to provide normalized interface with Result types.
    Converts Message models to provider format and collects stream events.

    Example:
        from dawn_kestrel.providers import ZAIProvider
        provider = ZAIProvider(api_key="sk-...")
        adapter = ZAIAdapter(provider)
        result = await adapter.generate_response(messages, "glm-4.7")
    """

    def __init__(self, provider):
        """Initialize ZAI adapter.

        Args:
            provider: ZAIProvider instance or compatible provider.
        """
        self._provider = provider

    async def generate_response(
        self, messages: list[Message], model: str, **kwargs
    ) -> Result[Message]:
        """Generate response using Z.AI provider.

        Converts Message models to list format expected by provider,
        collects stream events, and returns Result[Message].

        Args:
            messages: List of Message objects.
            model: Model identifier (e.g., "glm-4.7").
            **kwargs: Additional provider options.

        Returns:
            Result[Message]: Response message on success, Err on failure.
        """
        try:
            # Get model info from provider
            models = await self._provider.get_models()
            model_info = None
            for m in models:
                if m.api_id == model:
                    model_info = m
                    break

            if model_info is None:
                return Err(f"Model {model} not found in provider", code="MODEL_NOT_FOUND")

            # Convert Message models to provider format
            provider_messages = [{"role": msg.role, "content": msg.text or ""} for msg in messages]

            # Collect stream events
            text_parts = []
            finish_reason = "stop"

            async for event in self._provider.stream(
                model=model_info, messages=provider_messages, tools=[], options=kwargs
            ):
                if event.event_type == "text-delta":
                    delta = event.data.get("delta", "")
                    if delta:
                        text_parts.append(delta)
                elif event.event_type == "finish":
                    finish_reason = event.data.get("finish_reason", "stop")
                    break

            # Create response Message
            response = Message(
                id=f"zai-{asyncio.get_event_loop().time()}",
                session_id=messages[0].session_id if messages else "unknown",
                role="assistant",
                text="".join(text_parts),
            )

            return Ok(response)

        except Exception as e:
            logger.error(f"ZAI provider error: {e}", exc_info=True)
            return Err(f"ZAI provider error: {e}", code="PROVIDER_ERROR")

    async def get_provider_name(self) -> str:
        """Get the name of the underlying provider."""
        return "zai"


# =============================================================================
# Adapter Registration Functions
# =============================================================================


def register_adapter(name: str, adapter: ProviderAdapter) -> None:
    """Register a custom provider adapter.

    Enables custom providers to be registered at runtime without
    modifying core code.

    Args:
        name: Adapter name/identifier.
        adapter: Adapter instance implementing ProviderAdapter.

    Example:
        class CustomAdapter:
            async def generate_response(self, messages, model, **kwargs):
                return Ok(Message(...))
            async def get_provider_name(self):
                return "custom"

        register_adapter("my-provider", CustomAdapter())
    """
    _adapters[name] = adapter
    logger.info(f"Registered adapter: {name}")


def get_adapter(name: str) -> Optional[ProviderAdapter]:
    """Get registered adapter by name.

    Args:
        name: Adapter name/identifier.

    Returns:
        Adapter instance or None if not found.
    """
    return _adapters.get(name)


def list_adapters() -> list[str]:
    """List all registered adapter names.

    Returns:
        List of adapter names.
    """
    return list(_adapters.keys())


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "ProviderAdapter",
    "OpenAIAdapter",
    "ZAIAdapter",
    "register_adapter",
    "get_adapter",
    "list_adapters",
]
