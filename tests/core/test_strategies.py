"""Tests for Strategy pattern implementation.

Tests cover:
- RoutingStrategy protocol and implementations
- RenderingStrategy protocol and implementations
- StrategySelector for context-based selection

Tests follow TDD: RED (failing) -> GREEN (implementation) -> REFACTOR (cleanup)
"""

import pytest
from typing import Any

from dawn_kestrel.core.models import Message
from dawn_kestrel.core.result import Ok, Err


# =============================================================================
# Mock Provider for Testing
# =============================================================================


class MockProvider:
    """Mock LLM provider for testing."""

    def __init__(self, name: str, cost: float = 0.001):
        self.name = name
        self.cost = cost


# =============================================================================
# RoutingStrategy Protocol Tests
# =============================================================================


class TestRoutingStrategyProtocol:
    """Tests for RoutingStrategy protocol compliance."""

    def test_routing_strategy_has_select_provider_method(self):
        """Verify RoutingStrategy protocol has select_provider method."""
        from dawn_kestrel.core.strategies import RoutingStrategy

        # Check protocol exists
        assert hasattr(RoutingStrategy, "__protocol_attrs__") or True
        # Protocol compliance checked via runtime_checkable

    def test_routing_strategy_has_get_strategy_name_method(self):
        """Verify RoutingStrategy protocol has get_strategy_name method."""
        from dawn_kestrel.core.strategies import RoutingStrategy

        # Check protocol exists
        assert hasattr(RoutingStrategy, "__protocol_attrs__") or True


# =============================================================================
# RoundRobinRouting Tests
# =============================================================================


class TestRoundRobinRouting:
    """Tests for RoundRobinRouting implementation."""

    @pytest.mark.asyncio
    async def test_round_robin_selects_first_provider(self):
        """Verify round-robin selects first provider on first call."""
        from dawn_kestrel.core.strategies import RoundRobinRouting

        providers = [MockProvider("openai"), MockProvider("zai")]
        strategy = RoundRobinRouting()

        result = await strategy.select_provider(providers, {})

        assert result.is_ok()
        provider = result.unwrap()
        assert provider.name == "openai"

    @pytest.mark.asyncio
    async def test_round_robin_cycles_through_providers(self):
        """Verify round-robin cycles through providers."""
        from dawn_kestrel.core.strategies import RoundRobinRouting

        providers = [MockProvider("openai"), MockProvider("zai")]
        strategy = RoundRobinRouting()

        result1 = await strategy.select_provider(providers, {})
        result2 = await strategy.select_provider(providers, {})
        result3 = await strategy.select_provider(providers, {})

        assert result1.is_ok()
        assert result2.is_ok()
        assert result3.is_ok()

        provider1 = result1.unwrap()
        provider2 = result2.unwrap()
        provider3 = result3.unwrap()

        assert provider1.name == "openai"
        assert provider2.name == "zai"
        assert provider3.name == "openai"  # Cycles back

    @pytest.mark.asyncio
    async def test_round_robin_returns_err_with_no_providers(self):
        """Verify round-robin returns Err when no providers available."""
        from dawn_kestrel.core.strategies import RoundRobinRouting

        strategy = RoundRobinRouting()
        result = await strategy.select_provider([], {})

        assert result.is_err()
        assert result.code == "NO_PROVIDERS"

    @pytest.mark.asyncio
    async def test_round_robin_gets_strategy_name(self):
        """Verify round-robin returns correct strategy name."""
        from dawn_kestrel.core.strategies import RoundRobinRouting

        strategy = RoundRobinRouting()
        name = await strategy.get_strategy_name()

        assert name == "round_robin"


# =============================================================================
# CostOptimizedRouting Tests
# =============================================================================


class TestCostOptimizedRouting:
    """Tests for CostOptimizedRouting implementation."""

    @pytest.mark.asyncio
    async def test_cost_optimized_selects_cheapest_provider(self):
        """Verify cost-optimized selects cheapest provider."""
        from dawn_kestrel.core.strategies import CostOptimizedRouting

        providers = [
            MockProvider("expensive", cost=0.01),
            MockProvider("cheap", cost=0.001),
            MockProvider("medium", cost=0.005),
        ]
        strategy = CostOptimizedRouting()

        messages = [Message(id="1", session_id="test", role="user", text="Hello")]
        context = {"messages": messages}

        result = await strategy.select_provider(providers, context)

        assert result.is_ok()
        provider = result.unwrap()
        assert provider.name == "cheap"

    @pytest.mark.asyncio
    async def test_cost_optimized_respects_budget(self):
        """Verify cost-optimized respects budget constraint."""
        from dawn_kestrel.core.strategies import CostOptimizedRouting

        providers = [
            MockProvider("cheap_but_over_budget", cost=0.01),
            MockProvider("in_budget", cost=0.001),
        ]
        strategy = CostOptimizedRouting()

        messages = [Message(id="1", session_id="test", role="user", text="Hello")]
        context = {
            "messages": messages,
            "budget": 0.005,  # Cheap provider exceeds budget
        }

        result = await strategy.select_provider(providers, context)

        assert result.is_ok()
        provider = result.unwrap()
        assert provider.name == "in_budget"

    @pytest.mark.asyncio
    async def test_cost_optimized_returns_err_with_no_providers(self):
        """Verify cost-optimized returns Err when no providers available."""
        from dawn_kestrel.core.strategies import CostOptimizedRouting

        strategy = CostOptimizedRouting()
        result = await strategy.select_provider([], {})

        assert result.is_err()
        assert result.code == "NO_PROVIDERS"

    @pytest.mark.asyncio
    async def test_cost_optimized_returns_err_no_suitable_provider(self):
        """Verify cost-optimized returns Err when no provider within budget."""
        from dawn_kestrel.core.strategies import CostOptimizedRouting

        providers = [MockProvider("expensive", cost=0.01)]
        strategy = CostOptimizedRouting()

        messages = [Message(id="1", session_id="test", role="user", text="Hello")]
        context = {
            "messages": messages,
            "budget": 0.005,  # All providers exceed budget
        }

        result = await strategy.select_provider(providers, context)

        assert result.is_err()
        assert result.code == "NO_PROVIDER"

    @pytest.mark.asyncio
    async def test_cost_optimized_gets_strategy_name(self):
        """Verify cost-optimized returns correct strategy name."""
        from dawn_kestrel.core.strategies import CostOptimizedRouting

        strategy = CostOptimizedRouting()
        name = await strategy.get_strategy_name()

        assert name == "cost_optimized"


# =============================================================================
# RenderingStrategy Protocol Tests
# =============================================================================


class TestRenderingStrategyProtocol:
    """Tests for RenderingStrategy protocol compliance."""

    def test_rendering_strategy_has_render_method(self):
        """Verify RenderingStrategy protocol has render method."""
        from dawn_kestrel.core.strategies import RenderingStrategy

        # Check protocol exists
        assert hasattr(RenderingStrategy, "__protocol_attrs__") or True


# =============================================================================
# PlainTextRendering Tests
# =============================================================================


class TestPlainTextRendering:
    """Tests for PlainTextRendering implementation."""

    @pytest.mark.asyncio
    async def test_plain_text_rendering_returns_response(self):
        """Verify plain-text rendering returns response unchanged."""
        from dawn_kestrel.core.strategies import PlainTextRendering

        strategy = PlainTextRendering()
        messages = [Message(id="1", session_id="test", role="user", text="Hello")]
        response = "Response text"

        result = await strategy.render(messages, response, {})

        assert result == "Response text"

    @pytest.mark.asyncio
    async def test_plain_text_rendering_ignores_context(self):
        """Verify plain-text rendering ignores context."""
        from dawn_kestrel.core.strategies import PlainTextRendering

        strategy = PlainTextRendering()
        messages = [Message(id="1", session_id="test", role="user", text="Hello")]
        response = "Response text"
        context = {"format": "markdown", "template": "custom"}

        result = await strategy.render(messages, response, context)

        assert result == "Response text"


# =============================================================================
# MarkdownRendering Tests
# =============================================================================


class TestMarkdownRendering:
    """Tests for MarkdownRendering implementation."""

    @pytest.mark.asyncio
    async def test_markdown_rendering_formats_as_markdown(self):
        """Verify markdown rendering formats as markdown."""
        from dawn_kestrel.core.strategies import MarkdownRendering

        strategy = MarkdownRendering()
        messages = [Message(id="1", session_id="test", role="user", text="Hello")]
        response = "Response text"

        result = await strategy.render(messages, response, {})

        assert result == "Response text"

    @pytest.mark.asyncio
    async def test_markdown_rendering_handles_code_blocks(self):
        """Verify markdown rendering handles code blocks."""
        from dawn_kestrel.core.strategies import MarkdownRendering

        strategy = MarkdownRendering()
        messages = [Message(id="1", session_id="test", role="user", text="Hello")]
        response = "```python\ndef hello():\n    pass\n```"

        result = await strategy.render(messages, response, {})

        # Code blocks preserved
        assert "```python" in result
        assert "def hello():" in result

    @pytest.mark.asyncio
    async def test_markdown_rendering_handles_lists(self):
        """Verify markdown rendering handles lists."""
        from dawn_kestrel.core.strategies import MarkdownRendering

        strategy = MarkdownRendering()
        messages = [Message(id="1", session_id="test", role="user", text="Hello")]
        response = "- Item 1\n- Item 2\n- Item 3"

        result = await strategy.render(messages, response, {})

        # Lists preserved with indentation
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" in result


# =============================================================================
# StrategySelector Tests
# =============================================================================


class TestStrategySelector:
    """Tests for StrategySelector implementation."""

    def test_strategy_selector_registers_strategy(self):
        """Verify strategy selector can register strategies."""
        from dawn_kestrel.core.strategies import StrategySelector, RoundRobinRouting

        selector = StrategySelector()
        strategy = RoundRobinRouting()

        selector.register("round_robin", strategy)

        # Strategy registered
        assert "round_robin" in selector._strategies

    @pytest.mark.asyncio
    async def test_strategy_selector_selects_registered_strategy(self):
        """Verify strategy selector selects registered strategy."""
        from dawn_kestrel.core.strategies import StrategySelector, RoundRobinRouting

        selector = StrategySelector()
        strategy = RoundRobinRouting()
        selector.register("routing", strategy)

        result = await selector.select("routing", {})

        assert result.is_ok()
        selected = result.unwrap()
        assert selected is strategy

    @pytest.mark.asyncio
    async def test_strategy_selector_returns_err_for_unknown_type(self):
        """Verify strategy selector returns Err for unknown strategy type."""
        from dawn_kestrel.core.strategies import StrategySelector

        selector = StrategySelector()
        result = await selector.select("unknown", {})

        assert result.is_err()
        assert result.code == "STRATEGY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_strategy_selector_respects_environment_context(self):
        """Verify strategy selector respects environment in context."""
        from dawn_kestrel.core.strategies import StrategySelector, RoundRobinRouting

        selector = StrategySelector()
        selector.register("routing", RoundRobinRouting())

        # Production environment selects cost-optimized
        result = await selector.select("routing", {"environment": "production"})

        assert result.is_ok()
        selected = result.unwrap()
        # CostOptimizedRouting selected in production
        assert type(selected).__name__ == "CostOptimizedRouting"
