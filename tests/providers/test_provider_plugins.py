"""Tests for provider plugin discovery system."""

import pytest
from unittest.mock import Mock, patch
from dawn_kestrel.providers.base import ProviderID
from dawn_kestrel.core.plugin_discovery import load_providers
from dawn_kestrel.providers import (
    AnthropicProvider,
    OpenAIProvider,
    ZAIProvider,
    ZAICodingPlanProvider,
    get_provider,
)


class TestProviderPluginDiscovery:
    """Test provider plugin discovery and loading."""

    def test_load_providers_returns_all_four_providers(self):
        """load_providers should return all 4 provider classes."""
        providers = load_providers()

        assert len(providers) == 4, f"Expected 4 providers, got {len(providers)}"
        assert "anthropic" in providers
        assert "openai" in providers
        assert "zai" in providers
        assert "zai_coding_plan" in providers

    def test_load_providers_returns_provider_classes(self):
        """load_providers should return callable provider classes."""
        providers = load_providers()

        for name, provider_class in providers.items():
            assert callable(provider_class), f"Provider '{name}' is not callable"
            assert hasattr(provider_class, "__init__"), f"Provider '{name}' has no __init__"

    def test_get_provider_with_plugin_discovery(self):
        """get_provider should use plugin discovery to instantiate providers."""
        # Test Anthropic
        anthropic = get_provider(ProviderID.ANTHROPIC, "test-key")
        assert anthropic is not None
        assert isinstance(anthropic, AnthropicProvider)
        assert anthropic.api_key == "test-key"

        # Test OpenAI
        openai = get_provider(ProviderID.OPENAI, "test-key")
        assert openai is not None
        assert isinstance(openai, OpenAIProvider)

        # Test ZAI
        zai = get_provider(ProviderID.Z_AI, "test-key")
        assert zai is not None
        assert isinstance(zai, ZAIProvider)

        # Test ZAI Coding Plan
        zai_cp = get_provider(ProviderID.Z_AI_CODING_PLAN, "test-key")
        assert zai_cp is not None
        assert isinstance(zai_cp, ZAICodingPlanProvider)

    def test_get_provider_returns_none_for_unknown(self):
        """get_provider should return None for unknown provider IDs."""
        unknown = get_provider(ProviderID.GOOGLE, "test-key")
        assert unknown is None

    def test_provider_classes_exported_directly(self):
        """Provider classes should be directly importable for backward compatibility."""
        from dawn_kestrel.providers import (
            AnthropicProvider,
            OpenAIProvider,
            ZAIProvider,
            ZAICodingPlanProvider,
        )

        assert AnthropicProvider is not None
        assert OpenAIProvider is not None
        assert ZAIProvider is not None
        assert ZAICodingPlanProvider is not None

    def test_providers_have_required_methods(self):
        """All loaded providers should have required methods."""
        providers = load_providers()

        for name, provider_class in providers.items():
            # Instantiate with fake API key
            provider = provider_class("test-key")

            assert hasattr(provider, "get_models"), f"Provider '{name}' missing get_models"
            assert hasattr(provider, "stream"), f"Provider '{name}' missing stream"
            assert hasattr(provider, "count_tokens"), f"Provider '{name}' missing count_tokens"
            assert hasattr(provider, "calculate_cost"), f"Provider '{name}' missing calculate_cost"


class TestProviderBackwardCompatibility:
    """Test backward compatibility with existing provider imports."""

    def test_anthropic_provider_importable(self):
        """AnthropicProvider should be directly importable."""
        from dawn_kestrel.providers import AnthropicProvider

        provider = AnthropicProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://api.anthropic.com"

    def test_openai_provider_importable(self):
        """OpenAIProvider should be directly importable."""
        from dawn_kestrel.providers import OpenAIProvider

        provider = OpenAIProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://api.openai.com/v1"

    def test_zai_provider_importable(self):
        """ZAIProvider should be directly importable."""
        from dawn_kestrel.providers import ZAIProvider

        provider = ZAIProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://api.z.ai/api/paas/v4"

    def test_zai_coding_plan_provider_importable(self):
        """ZAICodingPlanProvider should be directly importable."""
        from dawn_kestrel.providers import ZAICodingPlanProvider

        provider = ZAICodingPlanProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://api.z.ai/api/coding/paas/v4"

    def test_custom_provider_must_use_entry_points(self):
        """Custom providers should be added via entry points, not register_provider_factory.

        register_provider_factory has been removed to match tools pattern.
        Custom providers should be registered in pyproject.toml entry points.
        """
        # Verify register_provider_factory is not available
        try:
            from dawn_kestrel.providers import register_provider_factory

            assert False, "register_provider_factory should not be available"
        except ImportError:
            assert True, "register_provider_factory correctly removed"

        # Verify unknown providers return None
        provider = get_provider(ProviderID.GOOGLE, "custom-key")
        assert provider is None, "Unknown providers should return None"
