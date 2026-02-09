"""OpenCode Python - Configuration system with Pydantic Settings"""

from __future__ import annotations
from typing import Optional, Dict
from pathlib import Path
import os
import warnings
import pydantic_settings
from pydantic import Field, SecretStr
from pydantic_settings.main import SettingsConfigDict
from pydantic_settings import (
    PydanticBaseSettingsSource,
    EnvSettingsSource,
    DotEnvSettingsSource,
)

__all__ = [
    "Settings",
    "settings",
    "get_settings",
    "reload_settings",
    "get_storage_dir",
    "get_config_dir",
    "get_cache_dir",
]

from dawn_kestrel.providers import ProviderID
from dawn_kestrel.core.provider_settings import AccountConfig


class Settings(pydantic_settings.BaseSettings):
    """Application settings with type-safe validation"""

    # Application settings
    app_name: str = Field(default="dawn-kestrel", alias="APP_NAME", min_length=1)
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Multi-account provider settings
    accounts: Dict[str, AccountConfig] = Field(default_factory=dict)

    # Provider settings
    provider_default: str = Field(
        default="z.ai",
    )
    model_default: str = Field(
        default="glm-4.7",
    )

    # Filesystem paths
    storage_dir: str = Field(
        default_factory=lambda: str(_resolve_app_dir("data")), alias="STORAGE_DIR"
    )
    config_dir: str = Field(
        default_factory=lambda: str(_resolve_app_dir("config")), alias="CONFIG_DIR"
    )
    cache_dir: str = Field(
        default_factory=lambda: str(_resolve_app_dir("cache")), alias="CACHE_DIR"
    )

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
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[pydantic_settings.BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        del env_settings, dotenv_settings

        model_env_nested_delimiter = settings_cls.model_config.get("env_nested_delimiter")
        env_nested_delimiter = (
            model_env_nested_delimiter if isinstance(model_env_nested_delimiter, str) else None
        )
        model_case_sensitive = settings_cls.model_config.get("case_sensitive")
        case_sensitive = model_case_sensitive if isinstance(model_case_sensitive, bool) else None

        dotenv_paths = _dotenv_paths(settings_cls)
        return (
            init_settings,
            EnvSettingsSource(
                settings_cls,
                env_prefix="DAWN_KESTREL_",
                env_nested_delimiter=env_nested_delimiter,
                case_sensitive=case_sensitive,
            ),
            EnvSettingsSource(
                settings_cls,
                env_prefix="OPENCODE_PYTHON_",
                env_nested_delimiter=env_nested_delimiter,
                case_sensitive=case_sensitive,
            ),
            DotEnvSettingsSource(
                settings_cls,
                env_prefix="DAWN_KESTREL_",
                env_file=dotenv_paths,
                env_nested_delimiter=env_nested_delimiter,
                case_sensitive=case_sensitive,
            ),
            DotEnvSettingsSource(
                settings_cls,
                env_prefix="OPENCODE_PYTHON_",
                env_file=dotenv_paths,
                env_nested_delimiter=env_nested_delimiter,
                case_sensitive=case_sensitive,
            ),
            file_secret_settings,
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
            The AccountConfig with is_default=True when available.
            If accounts exist but none are marked default, returns the
            first account matching provider_default, then the first
            configured account as a final fallback.
            If no accounts are configured, synthesizes a default account
            from provider/model defaults and environment API key.
        """
        for account in self.accounts.values():
            if account.is_default:
                return account

        if self.accounts:
            provider_default = self._parse_provider_default()
            if provider_default is not None:
                accounts_by_provider = self.get_accounts_by_provider(provider_default)
                if accounts_by_provider:
                    return next(iter(accounts_by_provider.values()))
            return next(iter(self.accounts.values()))

        provider_default = self._parse_provider_default()
        if provider_default is None:
            return None

        api_key = self._get_api_key_from_env(provider_default)
        if api_key is None:
            return None

        return AccountConfig(
            account_name="default",
            provider_id=provider_default,
            api_key=api_key,
            model=self.model_default,
            is_default=True,
        )

    def _parse_provider_default(self) -> Optional[ProviderID]:
        """Parse provider_default and warn on invalid values."""
        try:
            return ProviderID(self.provider_default)
        except ValueError:
            warnings.warn(
                f"Invalid provider_default '{self.provider_default}'.",
                UserWarning,
                stacklevel=2,
            )
            return None

    def _get_api_key_from_env(self, provider_id: ProviderID) -> Optional[SecretStr]:
        """Retrieve provider API key from environment variables."""
        provider_name = provider_id.value.replace(".", "").replace("-", "_").upper()
        for prefix in ("DAWN_KESTREL_", "OPENCODE_PYTHON_"):
            env_var_with_prefix = f"{prefix}{provider_name}_API_KEY"
            env_key = os.getenv(env_var_with_prefix)
            if env_key:
                return SecretStr(env_key)

        env_var_without_prefix = f"{provider_name}_API_KEY"
        env_key = os.getenv(env_var_without_prefix)
        if env_key:
            return SecretStr(env_key)

        return None

    def get_default_provider(self) -> ProviderID:
        """
        Retrieve the default provider from accounts.

        Falls back to provider_default setting if no accounts are configured.

        Returns:
            The ProviderID for the default provider.
        """
        default_account = self.get_default_account()
        if default_account:
            return default_account.provider_id

        return ProviderID(self.provider_default)

    def get_default_model(self, provider_id: Optional[ProviderID | str] = None) -> str:
        """
        Retrieve the default model for a provider from accounts.

        Falls back to model_default setting if no accounts are configured.

        Args:
            provider_id: Optional provider ID to get model for. If None, uses default provider.

        Returns:
            The model ID string for the default model.
        """
        if provider_id is None:
            provider_id = self.get_default_provider()
        elif isinstance(provider_id, str):
            provider_id = ProviderID(provider_id)

        default_account = self.get_default_account()
        if default_account and default_account.provider_id == provider_id:
            return default_account.model

        accounts_by_provider = self.get_accounts_by_provider(provider_id)
        if accounts_by_provider:
            return list(accounts_by_provider.values())[0].model

        return self.model_default

    def get_api_key_for_provider(self, provider_id: ProviderID | str) -> Optional[SecretStr]:
        """
        Retrieve API key for a specific provider from accounts.

        Falls back to environment variables if accounts are not configured.

        Environment variables are loaded from:
        - Project root .env file
        - ~/.config/dawn-kestrel/.env

        Args:
            provider_id: The provider ID to get API key for (ProviderID enum or string).

        Returns:
            The API key SecretStr if found, None otherwise.
        """
        provider_enum = ProviderID(provider_id) if isinstance(provider_id, str) else provider_id

        default_account = self.get_default_account()
        if default_account and default_account.provider_id == provider_enum:
            return default_account.api_key

        accounts_by_provider = self.get_accounts_by_provider(provider_enum)
        if accounts_by_provider:
            return list(accounts_by_provider.values())[0].api_key

        return self._get_api_key_from_env(provider_enum)

    def storage_dir_path(self) -> Path:
        """
        Get the storage directory path as a Path object.

        Returns:
            The storage directory path as a Path object with ~ expanded.
        """
        return Path(self.storage_dir).expanduser()

    def config_dir_path(self) -> Path:
        """
        Get the config directory path as a Path object.

        Returns:
            The config directory path as a Path object with ~ expanded.
        """
        return Path(self.config_dir).expanduser()

    def cache_dir_path(self) -> Path:
        """
        Get the cache directory path as a Path object.

        Returns:
            The cache directory path as a Path object with ~ expanded.
        """
        return Path(self.cache_dir).expanduser()


APP_DIR_NAME = "dawn-kestrel"


def _xdg_base_dir(env_var_name: str, fallback: Path) -> Path:
    env_value = os.getenv(env_var_name)
    if env_value:
        return Path(env_value).expanduser()
    return fallback


def _app_base_dirs(kind: str) -> Path:
    home = Path.home()
    if kind == "config":
        base = _xdg_base_dir("XDG_CONFIG_HOME", home / ".config")
    elif kind == "data":
        base = _xdg_base_dir("XDG_DATA_HOME", home / ".local" / "share")
    elif kind == "cache":
        base = _xdg_base_dir("XDG_CACHE_HOME", home / ".cache")
    else:
        raise ValueError(f"Unsupported app dir kind: {kind}")

    return base / APP_DIR_NAME


def _resolve_app_dir(kind: str) -> Path:
    return _app_base_dirs(kind)


def _dotenv_paths(settings_cls: type[pydantic_settings.BaseSettings]) -> tuple[Path | str, ...]:
    explicit_env_files = settings_cls.model_config.get("env_file")
    if explicit_env_files is not None:
        if isinstance(explicit_env_files, (str, Path)):
            return (explicit_env_files,)
        return tuple(explicit_env_files)

    config_dir = _app_base_dirs("config")
    return (".env", config_dir / ".env")


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
    Get the storage directory path from global settings instance.

    Deprecated: Use Settings().storage_dir_path() instead.
    This function provides backward compatibility with existing code.

    Returns:
        The storage directory path as a Path object with ~ expanded.
    """
    return settings.storage_dir_path()


def get_config_dir() -> Path:
    """
    Get the config directory path from global settings instance.

    Deprecated: Use Settings().config_dir_path() instead.
    This function provides backward compatibility with existing code.

    Returns:
        The config directory path as a Path object with ~ expanded.
    """
    return settings.config_dir_path()


def get_cache_dir() -> Path:
    """
    Get the cache directory path from global settings instance.

    Deprecated: Use Settings().cache_dir_path() instead.
    This function provides backward compatibility with existing code.

    Returns:
        The cache directory path as a Path object with ~ expanded.
    """
    return settings.cache_dir_path()
