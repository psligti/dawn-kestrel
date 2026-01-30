"""
Provider configuration model for AI providers.

Defines the structure for provider settings including
provider ID, model selection, API keys, and custom options.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from pathlib import Path


@dataclass
class ProviderConfig:
    """
    Configuration for an AI provider.

    Attributes:
        provider_id: Provider identifier (e.g., "anthropic", "openai", "google")
        model: Model ID to use (e.g., "claude-sonnet-4-20250514", "gpt-4")
        api_key: API key for the provider (optional, can be loaded from settings)
        base_url: Custom base URL for the provider API (optional)
        options: Additional provider-specific options (optional)
        is_default: Whether this is the default provider configuration
        name: Human-readable name for this configuration (optional)
        description: Description of this configuration (optional)
    """

    provider_id: str
    """Provider identifier (e.g., "anthropic", "openai", "google")"""

    model: str = ""
    """Model ID to use (e.g., "claude-sonnet-4-20250514", "gpt-4")"""

    api_key: Optional[str] = None
    """API key for the provider (optional, can be loaded from settings)"""

    base_url: Optional[str] = None
    """Custom base URL for the provider API (optional)"""

    options: Dict[str, Any] = field(default_factory=dict)
    """Additional provider-specific options (optional)"""

    is_default: bool = False
    """Whether this is the default provider configuration"""

    name: Optional[str] = None
    """Human-readable name for this configuration (optional)"""

    description: Optional[str] = None
    """Description of this configuration (optional)"""

    def model_post_init(self, __context: Any) -> None:
        """Validate configuration after initialization."""
        if not self.provider_id:
            raise ValueError("provider_id is required")

    def as_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "provider_id": self.provider_id,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "options": self.options,
            "is_default": self.is_default,
            "name": self.name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderConfig":
        """
        Create ProviderConfig from dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            ProviderConfig instance.
        """
        return cls(
            provider_id=data.get("provider_id", ""),
            model=data.get("model", ""),
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            options=data.get("options", {}),
            is_default=data.get("is_default", False),
            name=data.get("name"),
            description=data.get("description"),
        )

    def with_model(self, model: str) -> "ProviderConfig":
        """
        Create a new configuration with a different model.

        Args:
            model: New model ID.

        Returns:
            New ProviderConfig instance with updated model.
        """
        return ProviderConfig(
            provider_id=self.provider_id,
            model=model,
            api_key=self.api_key,
            base_url=self.base_url,
            options=self.options.copy(),
            is_default=self.is_default,
            name=self.name,
            description=self.description,
        )


def create_provider_config(
    provider_id: str,
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    is_default: bool = False,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> ProviderConfig:
    """
    Factory function to create a ProviderConfig.

    Args:
        provider_id: Provider identifier (e.g., "anthropic", "openai", "google")
        model: Model ID to use (e.g., "claude-sonnet-4-20250514", "gpt-4")
        api_key: API key for the provider (optional)
        base_url: Custom base URL for the provider API (optional)
        options: Additional provider-specific options (optional)
        is_default: Whether this is the default provider configuration
        name: Human-readable name for this configuration (optional)
        description: Description of this configuration (optional)

    Returns:
        ProviderConfig instance.
    """
    return ProviderConfig(
        provider_id=provider_id,
        model=model,
        api_key=api_key,
        base_url=base_url,
        options=options or {},
        is_default=is_default,
        name=name,
        description=description,
    )
