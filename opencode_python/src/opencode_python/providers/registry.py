"""
Provider registry for managing AI provider configurations.

Provides persistent storage and retrieval of provider configurations
with support for default provider selection.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging

from opencode_python.core.provider_config import ProviderConfig


logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Manage AI provider configurations.

    Stores and retrieves provider configurations with JSON persistence.
    Supports default provider selection.

    Attributes:
        storage_dir: Directory for provider configuration storage
        providers: Dictionary of provider configurations keyed by name
        default_provider: Name of default provider configuration
    """

    def __init__(self, storage_dir: Path):
        """
        Initialize ProviderRegistry.

        Args:
            storage_dir: Directory for provider configuration storage
        """
        self.storage_dir = storage_dir / "storage" / "providers"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.providers: Dict[str, ProviderConfig] = {}
        self.default_provider: Optional[str] = None

    async def register_provider(
        self,
        name: str,
        config: ProviderConfig,
        is_default: bool = False,
    ) -> ProviderConfig:
        """
        Register a provider configuration.

        Args:
            name: Name for this provider configuration
            config: Provider configuration
            is_default: Whether to set as default provider

        Returns:
            Registered ProviderConfig

        Raises:
            ValueError: If provider with same name already exists
        """
        if name in self.providers:
            raise ValueError(f"Provider already exists: {name}")

        self.providers[name] = config

        if is_default:
            self.default_provider = name

        await self.persist(config, name)

        logger.info(f"Registered provider: {name} (default: {is_default})")
        return config

    async def get_provider(self, name: str) -> Optional[ProviderConfig]:
        """
        Get a provider configuration by name.

        Args:
            name: Provider name

        Returns:
            ProviderConfig or None if not found
        """
        return self.providers.get(name)

    async def list_providers(self) -> List[Dict[str, Any]]:
        """
        List all provider configurations.

        Returns:
            List of provider configuration dictionaries
        """
        return [
            {
                "name": name,
                "config": config.as_dict(),
                "is_default": name == self.default_provider,
            }
            for name, config in self.providers.items()
        ]

    async def remove_provider(self, name: str) -> bool:
        """
        Remove a provider configuration.

        Args:
            name: Provider name

        Returns:
            True if removed, False if not found
        """
        if name not in self.providers:
            logger.warning(f"Provider not found: {name}")
            return False

        del self.providers[name]

        if self.default_provider == name:
            self.default_provider = None

        await self._remove_from_storage(name)

        logger.info(f"Removed provider: {name}")
        return True

    async def update_provider(
        self,
        name: str,
        config: ProviderConfig,
    ) -> ProviderConfig:
        """
        Update an existing provider configuration.

        Args:
            name: Provider name
            config: New provider configuration

        Returns:
            Updated ProviderConfig

        Raises:
            ValueError: If provider not found
        """
        if name not in self.providers:
            raise ValueError(f"Provider not found: {name}")

        self.providers[name] = config

        await self.persist(config, name)

        logger.info(f"Updated provider: {name}")
        return config

    async def get_default_provider(self) -> Optional[ProviderConfig]:
        """
        Get default provider configuration.

        Returns:
            Default ProviderConfig or None if not set
        """
        if not self.default_provider:
            return None

        return self.providers.get(self.default_provider)

    async def set_default_provider(self, name: str) -> bool:
        """
        Set default provider configuration.

        Args:
            name: Provider name

        Returns:
            True if set, False if provider not found
        """
        if name not in self.providers:
            logger.warning(f"Provider not found: {name}")
            return False

        self.default_provider = name
        logger.info(f"Set default provider: {name}")
        return True

    async def load_from_storage(self) -> None:
        """
        Load provider configurations from storage.
        """
        for provider_file in self.storage_dir.glob("*.json"):
            try:
                with open(provider_file, "r") as f:
                    data = json.load(f)

                config = ProviderConfig.from_dict(data)
                provider_name = provider_file.stem
                self.providers[provider_name] = config

                if config.is_default:
                    self.default_provider = provider_name

                logger.debug(f"Loaded provider: {provider_name}")

            except Exception as e:
                logger.error(f"Failed to load provider {provider_file}: {e}")

    async def persist(
        self,
        config: ProviderConfig,
        name: str,
    ) -> None:
        """
        Persist provider configuration to storage.

        Args:
            config: Provider configuration
            name: Provider name
        """
        provider_file = self.storage_dir / f"{name}.json"

        with open(provider_file, "w") as f:
            json.dump(config.as_dict(), f, indent=2)

        logger.debug(f"Persisted provider: {provider_file}")

    async def _remove_from_storage(self, name: str) -> None:
        """
        Remove provider configuration from storage.

        Args:
            name: Provider name
        """
        provider_file = self.storage_dir / f"{name}.json"

        if provider_file.exists():
            provider_file.unlink()
            logger.debug(f"Removed provider file: {provider_file}")


def create_provider_registry(storage_dir: Path) -> ProviderRegistry:
    """
    Factory function to create a ProviderRegistry.

    Args:
        storage_dir: Directory for provider configuration storage

    Returns:
        ProviderRegistry instance
    """
    return ProviderRegistry(storage_dir)
