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
    app_name: str = Field(default="dawn-kestrel", alias="APP_NAME")
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
        - ~/.config/opencode-python/.env

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


APP_DIR_NAME = "dawn-kestrel"
LEGACY_APP_DIR_NAMES = ("opencode-python", "opencode_python")


def _xdg_base_dir(env_var_name: str, fallback: Path) -> Path:
    env_value = os.getenv(env_var_name)
    if env_value:
        return Path(env_value).expanduser()
    return fallback


def _app_base_dirs(kind: str) -> tuple[Path, Path, Path]:
    home = Path.home()
    if kind == "config":
        base = _xdg_base_dir("XDG_CONFIG_HOME", home / ".config")
    elif kind == "data":
        base = _xdg_base_dir("XDG_DATA_HOME", home / ".local" / "share")
    elif kind == "cache":
        base = _xdg_base_dir("XDG_CACHE_HOME", home / ".cache")
    else:
        raise ValueError(f"Unsupported app dir kind: {kind}")

    return (
        base / APP_DIR_NAME,
        base / LEGACY_APP_DIR_NAMES[0],
        base / LEGACY_APP_DIR_NAMES[1],
    )


def _resolve_app_dir(kind: str) -> Path:
    canonical_dir, legacy_hyphen_dir, legacy_underscore_dir = _app_base_dirs(kind)
    if canonical_dir.exists():
        return canonical_dir
    if legacy_hyphen_dir.exists() or legacy_underscore_dir.exists():
        _warn_legacy_filename_conflicts(kind)
        if legacy_hyphen_dir.exists():
            return legacy_hyphen_dir
        return legacy_underscore_dir
    return canonical_dir


def _warn_legacy_filename_conflicts(kind: str) -> None:
    _, legacy_hyphen_dir, legacy_underscore_dir = _app_base_dirs(kind)
    if not legacy_hyphen_dir.exists() or not legacy_underscore_dir.exists():
        return

    legacy_hyphen_files: set[Path] = {
        file_path.relative_to(legacy_hyphen_dir)
        for file_path in legacy_hyphen_dir.rglob("*")
        if file_path.is_file()
    }
    legacy_underscore_files: set[Path] = {
        file_path.relative_to(legacy_underscore_dir)
        for file_path in legacy_underscore_dir.rglob("*")
        if file_path.is_file()
    }
    conflicting_files = sorted(legacy_hyphen_files.intersection(legacy_underscore_files))
    for conflicting_file in conflicting_files:
        warnings.warn(
            (
                f"Legacy filename conflict for {kind} '{conflicting_file}': "
                f"using '{LEGACY_APP_DIR_NAMES[0]}' over '{LEGACY_APP_DIR_NAMES[1]}'."
            ),
            UserWarning,
            stacklevel=3,
        )


def _dotenv_paths(settings_cls: type[pydantic_settings.BaseSettings]) -> tuple[Path | str, ...]:
    explicit_env_files = settings_cls.model_config.get("env_file")
    if explicit_env_files is not None:
        if isinstance(explicit_env_files, (str, Path)):
            return (explicit_env_files,)
        return tuple(explicit_env_files)

    config_canonical, config_legacy_hyphen, config_legacy_underscore = _app_base_dirs("config")
    env_files: list[Path | str] = [".env", config_canonical / ".env"]
    if config_legacy_hyphen.exists() and config_legacy_underscore.exists():
        if (
            not config_canonical.exists()
            and (config_legacy_hyphen / ".env").exists()
            and (config_legacy_underscore / ".env").exists()
        ):
            warnings.warn(
                (
                    "Legacy filename conflict for config '.env': "
                    "using 'opencode-python' over 'opencode_python'."
                ),
                UserWarning,
                stacklevel=3,
            )
            env_files.append(config_legacy_hyphen / ".env")
            return tuple(env_files)

    env_files.append(config_legacy_hyphen / ".env")
    env_files.append(config_legacy_underscore / ".env")
    return tuple(env_files)


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
