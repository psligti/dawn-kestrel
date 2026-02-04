"""OpenCode Python - Configuration system with Pydantic Settings"""

from __future__ import annotations
from typing import Optional, Dict
from pathlib import Path
import os
import pydantic_settings
from pydantic import Field, SecretStr
from pydantic_settings.main import SettingsConfigDict


__all__ = [
    "Settings",
    "settings",
    "get_settings",
    "reload_settings",
    "get_storage_dir",
    "get_config_dir",
    "get_cache_dir",
]

from opencode_python.providers import ProviderID
from opencode_python.core.provider_settings import AccountConfig


class Settings(pydantic_settings.BaseSettings):
    """Application settings with type-safe validation"""

    # Application settings
    app_name: str = Field(default="opencode-python", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # API credentials (secrets)
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    api_endpoint: str = Field(default="https://api.open-code.ai/v1", alias="API_ENDPOINT")

    # Multi-account provider settings
    accounts: Dict[str, AccountConfig] = Field(default_factory=dict)

    # Provider settings
    provider_default: str = Field(
        default=os.getenv("OPENCODE_PYTHON_PROVIDER_DEFAULT", "z.ai"), alias="PROVIDER_DEFAULT"
    )
    model_default: str = Field(
        default=os.getenv("OPENCODE_PYTHON_MODEL_DEFAULT", "glm-4.7"), alias="MODEL_DEFAULT"
    )

    # Filesystem paths
    storage_dir: str = Field(default="~/.local/share/opencode-python", alias="STORAGE_DIR")
    config_dir: str = Field(default="~/.config/opencode-python", alias="CONFIG_DIR")
    cache_dir: str = Field(default="~/.cache/opencode-python", alias="CACHE_DIR")

    # Time-related settings
    timezone: str = Field(default="UTC", alias="TIMEZONE")

    # CLI defaults
    output_format: str = Field(default="text", alias="OUTPUT_FORMAT")
    verbose: bool = Field(default=False, alias="VERBOSE")

    # TUI settings
    tui_theme: str = Field(default="auto", alias="TUI_THEME")
    tui_mouse_enabled: bool = Field(default=True, alias="TUI_MOUSE")

    # Git/Repository settings
    git_enabled: bool = Field(default=True, alias="GIT_ENABLED")
    git_max_depth: int = Field(default=10, alias="GIT_MAX_DEPTH")

    # File watching
    file_watch_enabled: bool = Field(default=False, alias="FILE_WATCH_ENABLED")

    # Session settings
    session_compaction_tokens: int = Field(default=20000, alias="SESSION_COMPACTION_TOKENS")
    session_compaction_protected_tokens: int = Field(
        default=40000, alias="SESSION_COMPACTION_PROTECTED_TOKENS"
    )

    # Permission settings
    permission_default_action: str = Field(default="ask", alias="PERMISSION_DEFAULT_ACTION")

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).parent.parent.parent.parent / ".env",
            Path.home() / ".config" / "opencode-python" / ".env",
        ),
        env_file_encoding="utf-8",
        env_prefix="OPENCODE_PYTHON_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    def get_account(self, account_name: str) -> Optional[AccountConfig]:
        """
        Retrieve an account configuration by name.

        Args:
            account_name: The name of the account to retrieve.

        Returns:
            The AccountConfig if found, None otherwise.
        """
        return self.accounts.get(account_name)

    def get_accounts_by_provider(self, provider_id: ProviderID) -> Dict[str, AccountConfig]:
        """
        Retrieve all account configurations for a specific provider.

        Args:
            provider_id: The provider ID to filter accounts by.

        Returns:
            A dictionary mapping account names to AccountConfig objects
            for the specified provider. Returns empty dict if no matches.
        """
        return {
            name: account
            for name, account in self.accounts.items()
            if account.provider_id == provider_id
        }

    def get_default_account(self) -> Optional[AccountConfig]:
        """
        Retrieve the default account configuration.

        Returns:
            The AccountConfig with is_default=True, or None if no default
            account is found.
        """
        for account in self.accounts.values():
            if account.is_default:
                return account
        return None

    def get_api_key_for_provider(self, provider_id: ProviderID | str) -> Optional[SecretStr]:
        """
        Retrieve API key for a specific provider from accounts.

        Args:
            provider_id: The provider ID to get API key for (ProviderID enum or string).

        Returns:
            The API key SecretStr if found, None otherwise.
        """
        # Convert string to ProviderID enum if needed
        provider_enum = ProviderID(provider_id) if isinstance(provider_id, str) else provider_id

        # Try to get from default account first
        default_account = self.get_default_account()
        if default_account and default_account.provider_id == provider_enum:
            return default_account.api_key

        # Try to get any account for this provider
        accounts_by_provider = self.get_accounts_by_provider(provider_enum)
        if accounts_by_provider:
            # Return API key from first account for this provider
            return list(accounts_by_provider.values())[0].api_key

        return None


settings: Settings = Settings()


def get_settings() -> Settings:
    """
    Get the global settings singleton instance.

    Returns:
        The global Settings instance.
    """
    return settings


def reload_settings() -> Settings:
    """
    Reload settings by creating a new Settings instance.

    Returns:
        A new Settings instance with current environment values.
    """
    return Settings()


def get_storage_dir() -> Path:
    """
    Get the storage directory path from settings.

    Returns:
        The storage directory path as a Path object with ~ expanded.
    """
    return Path(settings.storage_dir).expanduser()


def get_config_dir() -> Path:
    """
    Get the config directory path from settings.

    Returns:
        The config directory path as a Path object with ~ expanded.
    """
    return Path(settings.config_dir).expanduser()


def get_cache_dir() -> Path:
    """
    Get the cache directory path from settings.

    Returns:
        The cache directory path as a Path object with ~ expanded.
    """
    return Path(settings.cache_dir).expanduser()
