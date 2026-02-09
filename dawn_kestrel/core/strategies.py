"""Strategy pattern for algorithm selection.

This module implements Strategy pattern to define algorithm families
for runtime selection without if/else chains.

Key concepts:
- RoutingStrategy: Protocol for LLM provider routing
- RenderingStrategy: Protocol for output formatting
- StrategySelector: Context-based strategy selection
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dawn_kestrel.core.models import Message
from dawn_kestrel.core.result import Err, Ok, Result


# =============================================================================
# RoutingStrategy Protocol
# =============================================================================


@runtime_checkable
class RoutingStrategy(Protocol):
    """Protocol for LLM provider routing strategy.

    Strategy selects which provider to use for a request.
    Enables runtime provider selection without if/else chains.

    Example:
        async def route_request(providers, context):
            strategy = RoundRobinRouting()
            result = await strategy.select_provider(providers, context)
            if result.is_ok():
                provider = result.unwrap()
                await provider.generate_response(...)
    """

    async def select_provider(self, providers: list[Any], context: dict[str, Any]) -> Result[Any]:
        """Select provider from list based on context.

        Args:
            providers: List of available providers.
            context: Routing context (e.g., budget, latency, region).

        Returns:
            Result[Any]: Selected provider on success, Err on failure.
        """
        ...

    async def get_strategy_name(self) -> str:
        """Get strategy name for logging/metrics.

        Returns:
            str: Strategy name.
        """
        ...


# =============================================================================
# RoundRobinRouting
# =============================================================================


class RoundRobinRouting:
    """Round-robin provider selection.

    Distributes requests evenly across all providers in sequence.
    Simple, stateful strategy with O(1) selection.

    Example:
        strategy = RoundRobinRouting()
        result1 = await strategy.select_provider(providers, {})
        result2 = await strategy.select_provider(providers, {})
        # result1 and result2 select different providers (if 2+ available)
    """

    def __init__(self):
        """Initialize round-robin strategy."""
        self._index: int = 0

    async def select_provider(self, providers: list[Any], context: dict[str, Any]) -> Result[Any]:
        """Select provider using round-robin algorithm.

        Args:
            providers: List of available providers.
            context: Routing context (ignored by round-robin).

        Returns:
            Result[Any]: Selected provider on success, Err if no providers.
        """
        if not providers:
            return Err("No providers available", code="NO_PROVIDERS")

        provider = providers[self._index]
        self._index = (self._index + 1) % len(providers)

        return Ok(provider)

    async def get_strategy_name(self) -> str:
        """Get strategy name for logging/metrics.

        Returns:
            str: "round_robin"
        """
        return "round_robin"


# =============================================================================
# CostOptimizedRouting
# =============================================================================


class CostOptimizedRouting:
    """Cost-optimized provider selection.

    Selects provider with lowest cost for estimated tokens,
    optionally respecting budget constraints.

    Example:
        strategy = CostOptimizedRouting()
        result = await strategy.select_provider(
            providers,
            {"messages": messages, "budget": 0.01}
        )
    """

    def __init__(self):
        """Initialize cost-optimized strategy."""
        self._costs: dict[str, float] = {}

    def _estimate_tokens(self, messages: list[Message]) -> int:
        """Estimate token count from messages.

        Rough estimate: 4 characters per token.

        Args:
            messages: List of messages.

        Returns:
            int: Estimated token count.
        """
        total = 0
        for msg in messages:
            total += len(msg.text) // 4  # Rough estimate: 4 chars per token
        return total

    async def select_provider(self, providers: list[Any], context: dict[str, Any]) -> Result[Any]:
        """Select provider using cost optimization.

        Args:
            providers: List of available providers.
            context: Routing context with 'messages' and optional 'budget'.

        Returns:
            Result[Any]: Selected provider on success, Err if no suitable provider.
        """
        if not providers:
            return Err("No providers available", code="NO_PROVIDERS")

        messages = context.get("messages", [])
        budget = context.get("budget", None)

        # Find cheapest provider for estimated tokens
        estimated_tokens = self._estimate_tokens(messages)
        cheapest_provider = None
        cheapest_cost = float("inf")

        for provider in providers:
            # Get provider pricing (mock implementation)
            pricing = await self._get_pricing(provider)
            if pricing:
                cost = estimated_tokens * pricing.get("price_per_1k_tokens", 0.001)
                if cost < cheapest_cost and (budget is None or cost <= budget):
                    cheapest_cost = cost
                    cheapest_provider = provider

        if cheapest_provider:
            return Ok(cheapest_provider)
        return Err("No suitable provider found", code="NO_PROVIDER")

    async def _get_pricing(self, provider: Any) -> dict[str, float] | None:
        """Get pricing info from provider.

        In real implementation, would query provider API.
        For now, returns dummy pricing based on provider name.

        Args:
            provider: Provider instance.

        Returns:
            dict[str, float] | None: Pricing info with price_per_1k_tokens.
        """
        # In real implementation, would query provider API
        # For now, return dummy pricing based on provider name
        if hasattr(provider, "cost"):
            return {"price_per_1k_tokens": provider.cost}
        return {"price_per_1k_tokens": 0.001}

    async def get_strategy_name(self) -> str:
        """Get strategy name for logging/metrics.

        Returns:
            str: "cost_optimized"
        """
        return "cost_optimized"


# =============================================================================
# RenderingStrategy Protocol
# =============================================================================


@runtime_checkable
class RenderingStrategy(Protocol):
    """Protocol for output rendering strategy.

    Strategy formats response for different output types.
    Enables runtime format selection without if/else chains.

    Example:
        async def format_response(messages, response, context):
            strategy = MarkdownRendering()
            formatted = await strategy.render(messages, response, context)
            return formatted
    """

    async def render(self, messages: list[Message], response: str, context: dict[str, Any]) -> str:
        """Render output based on strategy.

        Args:
            messages: Input messages.
            response: LLM response.
            context: Rendering context (e.g., format, template).

        Returns:
            str: Rendered output string.
        """
        ...


# =============================================================================
# PlainTextRendering
# =============================================================================


class PlainTextRendering:
    """Plain text rendering (no formatting).

    Returns response unchanged, suitable for raw output.

    Example:
        strategy = PlainTextRendering()
        result = await strategy.render(messages, "Hello world", {})
        # result == "Hello world"
    """

    async def render(self, messages: list[Message], response: str, context: dict[str, Any]) -> str:
        """Render output as plain text (no formatting).

        Args:
            messages: Input messages (ignored by plain-text rendering).
            response: LLM response.
            context: Rendering context (ignored by plain-text rendering).

        Returns:
            str: Unchanged response.
        """
        return response


# =============================================================================
# MarkdownRendering
# =============================================================================


class MarkdownRendering:
    """Markdown rendering.

    Applies basic markdown formatting to response.
    Enhances readability with proper indentation.

    Example:
        strategy = MarkdownRendering()
        result = await strategy.render(
            messages,
            "- Item 1\n- Item 2",
            {}
        )
        # result includes indented list items
    """

    async def render(self, messages: list[Message], response: str, context: dict[str, Any]) -> str:
        """Render output with markdown formatting.

        Args:
            messages: Input messages (ignored by markdown rendering).
            response: LLM response.
            context: Rendering context (ignored by markdown rendering).

        Returns:
            str: Markdown-formatted output.
        """
        # Simple markdown conversion (add formatting)
        lines = response.split("\n")
        formatted = []

        for line in lines:
            if line.strip().startswith("- "):
                formatted.append(f"  {line}")
            elif line.strip().startswith("#"):
                formatted.append(f"{line}")
            else:
                formatted.append(line)

        return "\n".join(formatted)


# =============================================================================
# StrategySelector
# =============================================================================


class StrategySelector:
    """Context-based strategy selection.

    Enables runtime strategy selection based on context.
    Useful for switching between development and production strategies.

    Example:
        selector = StrategySelector()
        selector.register("routing", RoundRobinRouting())

        # Development: use round-robin
        result = await selector.select("routing", {"environment": "development"})

        # Production: use cost-optimized
        result = await selector.select("routing", {"environment": "production"})
    """

    def __init__(self):
        """Initialize strategy selector."""
        self._strategies: dict[str, Any] = {}

    def register(self, name: str, strategy: Any) -> None:
        """Register a strategy.

        Args:
            name: Strategy name.
            strategy: Strategy instance.
        """
        self._strategies[name] = strategy

    async def select(self, strategy_type: str, context: dict[str, Any]) -> Result[Any]:
        """Select strategy based on type and context.

        Args:
            strategy_type: Strategy type (e.g., "routing", "rendering").
            context: Context dict (e.g., {"environment": "production"}).

        Returns:
            Result[Any]: Selected strategy on success, Err if not found.
        """
        strategy = self._strategies.get(strategy_type)

        if not strategy:
            return Err(f"Strategy not found: {strategy_type}", code="STRATEGY_NOT_FOUND")

        # Use context to determine which implementation
        if context.get("environment") == "production":
            # In production, use cost-optimized routing
            if strategy_type == "routing":
                return Ok(CostOptimizedRouting())

        # Default to first registered strategy
        first_strategy_key = next(iter(self._strategies))
        first_strategy = self._strategies[first_strategy_key]
        return Ok(first_strategy)
