"""OpenCode Python - Configuration system with Pydantic Settings"""
from __future__ import annotations
from typing import Optional, Dict
from pathlib import Path
import os
import pydantic_settings
from pydantic import Field, SecretStr
from pydantic_settings.main import SettingsConfigDict


__all__ = ["Settings", "settings"]

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
    api_keys: Dict[str, SecretStr] = Field(default_factory=dict)
    api_keys_coding: Dict[str, SecretStr] = Field(default_factory=dict)
    api_endpoint: str = Field(
        default="https://api.open-code.ai/v1",
        alias="API_ENDPOINT"
    )

    # Multi-account provider settings
    accounts: Dict[str, AccountConfig] = Field(default_factory=dict)

    # Provider settings
    provider_default: str = Field(default=os.getenv("OPENCODE_PYTHON_PROVIDER_DEFAULT", "z.ai"), alias="PROVIDER_DEFAULT")
    model_default: str = Field(default=os.getenv("OPENCODE_PYTHON_MODEL_DEFAULT", "glm-4.7"), alias="MODEL_DEFAULT")

    # Filesystem paths
    storage_dir: str = Field(
        default="~/.local/share/opencode-python",
        alias="STORAGE_DIR"
    )
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
        default=40000,
        alias="SESSION_COMPACTION_PROTECTED_TOKENS"
    )

    # Permission settings
    permission_default_action: str = Field(default="ask", alias="PERMISSION_DEFAULT_ACTION")

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).parent.parent.parent.parent / '.env',
            Path.home() / '.config' / 'opencode-python' / '.env',
        ),
        env_file_encoding="utf-8",
        env_prefix="OPENCODE_PYTHON_",
        env_nested_delimiter='__',
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


settings: Settings = Settings()
