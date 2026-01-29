"""OpenCode Python - Configuration system with Pydantic Settings"""
from __future__ import annotations
from typing import Optional, Dict
from pathlib import Path
import pydantic_settings
from pydantic import Field, SecretStr
from pydantic_settings import SettingsConfigDict


__all__ = ["Settings", "get_settings", "settings"]


class Settings(pydantic_settings.BaseSettings):
    """Application settings with type-safe validation"""

    # Application settings
    app_name: str = Field(default="opencode-python", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # API credentials (secrets)
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""), alias="API_KEY")
    api_keys: Dict[str, SecretStr] = Field(default_factory=dict, alias="API_KEYS")
    api_endpoint: str = Field(
        default="https://api.open-code.ai/v1",
        alias="API_ENDPOINT"
    )

    # Provider settings
    provider_default: str = Field(default="anthropic", alias="PROVIDER_DEFAULT")
    model_default: str = Field(default="claude-3-5-sonnet-20241022", alias="MODEL_DEFAULT")

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
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OPENCODE_PYTHON_",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get singleton settings instance

    Lazily loads settings once and caches the instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


settings: Settings = get_settings()


def reload_settings() -> Settings:
    """Reload settings from environment and config files

    Useful for testing or when settings need to be refreshed.
    """
    global _settings
    _settings = Settings()
    return _settings


def get_storage_dir() -> Path:
    """Get resolved storage directory path"""
    return Path(get_settings().storage_dir).expanduser()


def get_config_dir() -> Path:
    """Get resolved config directory path"""
    return Path(get_settings().config_dir).expanduser()


def get_cache_dir() -> Path:
    """Get resolved cache directory path"""
    return Path(get_settings().cache_dir).expanduser()
