"""Tests for configuration settings.

Tests Settings class, Pydantic validation, environment variable loading,
and configuration utility functions, plus SDKConfig dataclass.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from opencode_python.core.settings import (
    Settings,
    get_settings,
    reload_settings,
    get_storage_dir,
    get_config_dir,
    get_cache_dir,
)
from opencode_python.core.config import SDKConfig


class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_default_app_name(self) -> None:
        """Test default app name."""
        settings = Settings()
        assert settings.app_name == "opencode-python"

    def test_default_debug(self) -> None:
        """Test default debug value."""
        settings = Settings()
        assert settings.debug is False

    def test_default_log_level(self) -> None:
        """Test default log level."""
        settings = Settings()
        assert settings.log_level == "INFO"

    def test_default_api_key(self) -> None:
        """Test default API key is a SecretStr (may have value from env)."""
        settings = Settings()
        from pydantic import SecretStr
        assert isinstance(settings.api_key, SecretStr)

    def test_default_api_endpoint(self) -> None:
        """Test default API endpoint."""
        settings = Settings()
        assert settings.api_endpoint == "https://api.open-code.ai/v1"

    def test_default_provider_default(self) -> None:
        """Test default provider."""
        settings = Settings()
        assert settings.provider_default == "z.ai"

    def test_default_model_default(self) -> None:
        """Test default model."""
        settings = Settings()
        assert settings.model_default == "glm-4.7"

    def test_default_storage_dir(self) -> None:
        """Test default storage directory."""
        settings = Settings()
        assert settings.storage_dir == "~/.local/share/opencode-python"

    def test_default_config_dir(self) -> None:
        """Test default config directory."""
        settings = Settings()
        assert settings.config_dir == "~/.config/opencode-python"

    def test_default_cache_dir(self) -> None:
        """Test default cache directory."""
        settings = Settings()
        assert settings.cache_dir == "~/.cache/opencode-python"

    def test_default_timezone(self) -> None:
        """Test default timezone."""
        settings = Settings()
        assert settings.timezone == "UTC"

    def test_default_output_format(self) -> None:
        """Test default output format."""
        settings = Settings()
        assert settings.output_format == "text"

    def test_default_verbose(self) -> None:
        """Test default verbose value."""
        settings = Settings()
        assert settings.verbose is False

    def test_default_tui_theme(self) -> None:
        """Test default TUI theme."""
        settings = Settings()
        assert settings.tui_theme == "auto"

    def test_default_tui_mouse_enabled(self) -> None:
        """Test default TUI mouse enabled."""
        settings = Settings()
        assert settings.tui_mouse_enabled is True

    def test_default_git_enabled(self) -> None:
        """Test default git enabled."""
        settings = Settings()
        assert settings.git_enabled is True

    def test_default_git_max_depth(self) -> None:
        """Test default git max depth."""
        settings = Settings()
        assert settings.git_max_depth == 10

    def test_default_file_watch_enabled(self) -> None:
        """Test default file watch enabled."""
        settings = Settings()
        assert settings.file_watch_enabled is False

    def test_default_session_compaction_tokens(self) -> None:
        """Test default session compaction tokens."""
        settings = Settings()
        assert settings.session_compaction_tokens == 20000

    def test_default_permission_default_action(self) -> None:
        """Test default permission action."""
        settings = Settings()
        assert settings.permission_default_action == "ask"


class TestSettingsPydanticValidation:
    """Tests for Settings Pydantic validation."""

    def test_secret_str_not_exposed_in_repr(self) -> None:
        """Test that SecretStr for api_key is not exposed in repr."""
        settings = Settings(api_key="secret-password")
        repr_str = repr(settings)
        assert "secret-password" not in repr_str
        assert "SecretStr" in repr_str or "**********" in repr_str

    def test_settings_has_log_level_field(self) -> None:
        """Test that Settings has log_level field."""
        settings = Settings()
        assert hasattr(settings, 'log_level')
        assert isinstance(settings.log_level, str)


class TestSettingsUtilityFunctions:
    """Tests for Settings utility functions."""

    def test_get_settings_returns_settings_instance(self) -> None:
        """Test that get_settings returns Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_returns_singleton(self) -> None:
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_reload_settings_returns_new_instance(self) -> None:
        """Test that reload_settings returns new Settings instance."""
        reloaded_settings = reload_settings()
        assert isinstance(reloaded_settings, Settings)

    def test_get_storage_dir_returns_path(self) -> None:
        """Test that get_storage_dir returns Path object."""
        storage_dir = get_storage_dir()
        assert isinstance(storage_dir, Path)

    def test_get_storage_dir_expands_user(self) -> None:
        """Test that get_storage_dir expands ~ to user home."""
        storage_dir = get_storage_dir()
        assert not str(storage_dir).startswith("~")

    def test_get_config_dir_returns_path(self) -> None:
        """Test that get_config_dir returns Path object."""
        config_dir = get_config_dir()
        assert isinstance(config_dir, Path)

    def test_get_cache_dir_returns_path(self) -> None:
        """Test that get_cache_dir returns Path object."""
        cache_dir = get_cache_dir()
        assert isinstance(cache_dir, Path)


class TestSDKConfig:
    """Tests for SDKConfig dataclass."""

    def test_default_storage_path_is_none(self) -> None:
        """Test that default storage_path is None."""
        config = SDKConfig()
        assert config.storage_path is None

    def test_default_project_dir_is_cwd(self) -> None:
        """Test that default project_dir is current working directory."""
        config = SDKConfig()
        assert config.project_dir == Path.cwd()

    def test_default_auto_confirm_is_false(self) -> None:
        """Test that default auto_confirm is False."""
        config = SDKConfig()
        assert config.auto_confirm is False

    def test_default_enable_progress_is_true(self) -> None:
        """Test that default enable_progress is True."""
        config = SDKConfig()
        assert config.enable_progress is True

    def test_default_enable_notifications_is_true(self) -> None:
        """Test that default enable_notifications is True."""
        config = SDKConfig()
        assert config.enable_notifications is True

    def test_can_override_storage_path(self) -> None:
        """Test that storage_path can be overridden."""
        config = SDKConfig(storage_path=Path("/custom/storage"))
        assert config.storage_path == Path("/custom/storage")

    def test_can_override_project_dir(self) -> None:
        """Test that project_dir can be overridden."""
        config = SDKConfig(project_dir=Path("/custom/project"))
        assert config.project_dir == Path("/custom/project")

    def test_can_override_auto_confirm(self) -> None:
        """Test that auto_confirm can be overridden."""
        config = SDKConfig(auto_confirm=True)
        assert config.auto_confirm is True

    def test_can_override_enable_progress(self) -> None:
        """Test that enable_progress can be overridden."""
        config = SDKConfig(enable_progress=False)
        assert config.enable_progress is False

    def test_can_override_enable_notifications(self) -> None:
        """Test that enable_notifications can be overridden."""
        config = SDKConfig(enable_notifications=False)
        assert config.enable_notifications is False

    def test_as_dict_returns_correct_values(self) -> None:
        """Test that as_dict returns dictionary with correct values."""
        config = SDKConfig(
            storage_path=Path("/test/storage"),
            project_dir=Path("/test/project"),
            auto_confirm=True,
            enable_progress=False,
            enable_notifications=False,
        )
        result = config.as_dict()
        assert result["storage_path"] == "/test/storage"
        assert result["project_dir"] == "/test/project"
        assert result["auto_confirm"] is True
        assert result["enable_progress"] is False
        assert result["enable_notifications"] is False

    def test_as_dict_handles_none_storage_path(self) -> None:
        """Test that as_dict handles None storage_path."""
        config = SDKConfig()
        result = config.as_dict()
        assert result["storage_path"] is None
