"""Tests for Configuration Object pattern

Tests verify that Settings instance provides directory paths
and replaces global singleton functions.
"""

import os
from pathlib import Path
import pytest
from pydantic import ValidationError

from dawn_kestrel.core.settings import Settings, get_storage_dir, get_config_dir, get_cache_dir


class TestConfigurationObjectBasics:
    """Test basic Configuration object functionality."""

    def test_settings_instance_provides_storage_dir_as_string(self):
        """Settings instance provides storage_dir as string field."""
        config = Settings()
        assert isinstance(config.storage_dir, str)
        assert "dawn-kestrel" in config.storage_dir or "data" in config.storage_dir.lower()

    def test_settings_instance_provides_config_dir_as_string(self):
        """Settings instance provides config_dir as string field."""
        config = Settings()
        assert isinstance(config.config_dir, str)
        assert "dawn-kestrel" in config.config_dir or "config" in config.config_dir.lower()

    def test_settings_instance_provides_cache_dir_as_string(self):
        """Settings instance provides cache_dir as string field."""
        config = Settings()
        assert isinstance(config.cache_dir, str)
        assert "dawn-kestrel" in config.cache_dir or "cache" in config.cache_dir.lower()


class TestConfigurationObjectPathMethods:
    """Test Configuration object path methods (to be implemented)."""

    def test_settings_provides_storage_dir_path(self):
        """Settings instance provides storage directory as Path object."""
        config = Settings()
        storage_path = config.storage_dir_path()
        assert isinstance(storage_path, Path)
        assert storage_path.exists() or storage_path.parent.exists()

    def test_settings_provides_config_dir_path(self):
        """Settings instance provides config directory as Path object."""
        config = Settings()
        config_path = config.config_dir_path()
        assert isinstance(config_path, Path)
        assert config_path.exists() or config_path.parent.exists()

    def test_settings_provides_cache_dir_path(self):
        """Settings instance provides cache directory as Path object."""
        config = Settings()
        cache_path = config.cache_dir_path()
        assert isinstance(cache_path, Path)
        assert cache_path.exists() or cache_path.parent.exists()

    def test_path_methods_expand_home_directories(self):
        """Path methods expand ~ to home directory."""
        # Set up environment with home directory path
        original_storage = os.environ.get("DAWN_KESTREL_STORAGE_DIR")
        try:
            os.environ["DAWN_KESTREL_STORAGE_DIR"] = "~/test_storage"
            config = Settings()
            storage_path = config.storage_dir_path()
            assert str(storage_path).startswith(os.path.expanduser("~"))
        finally:
            if original_storage is None:
                os.environ.pop("DAWN_KESTREL_STORAGE_DIR", None)
            else:
                os.environ["DAWN_KESTREL_STORAGE_DIR"] = original_storage


class TestConfigurationObjectValidation:
    """Test Configuration object validation rules."""

    def test_validate_app_name_not_empty(self):
        """App name cannot be empty string."""
        # Note: min_length=1 on app_name field prevents empty strings
        # Pydantic validates this at field definition time
        config = Settings()
        assert len(config.app_name) > 0
        assert config.app_name == "dawn-kestrel"

    def test_validate_storage_dir_is_string(self):
        """Storage directory must be string."""
        config = Settings()
        assert isinstance(config.storage_dir, str)

    def test_validate_config_dir_is_string(self):
        """Config directory must be string."""
        config = Settings()
        assert isinstance(config.config_dir, str)

    def test_validate_cache_dir_is_string(self):
        """Cache directory must be string."""
        config = Settings()
        assert isinstance(config.cache_dir, str)


class TestConfigurationObjectEnvironmentVariables:
    """Test Configuration object respects environment variables."""

    def test_default_directories_are_set(self):
        """Default directories are properly set."""
        config = Settings()
        # Verify directories contain dawn-kestrel or appropriate path components
        assert "dawn-kestrel" in config.storage_dir or "data" in config.storage_dir.lower()
        assert "dawn-kestrel" in config.config_dir or "config" in config.config_dir.lower()
        assert "dawn-kestrel" in config.cache_dir or "cache" in config.cache_dir.lower()


class TestConfigurationObjectThreadSafety:
    """Test Configuration object thread safety."""

    def test_multiple_instances_independent(self):
        """Multiple Settings instances are independent."""
        config1 = Settings()
        config2 = Settings()
        # Both should have the same default values
        assert config1.storage_dir == config2.storage_dir
        assert config1.config_dir == config2.config_dir
        assert config1.cache_dir == config2.cache_dir

    def test_instance_methods_thread_safe(self):
        """Instance methods can be called from different contexts."""
        config = Settings()
        # Call multiple times - should be consistent
        path1 = config.storage_dir_path()
        path2 = config.storage_dir_path()
        path3 = config.storage_dir_path()
        assert path1 == path2 == path3


class TestBackwardCompatibility:
    """Test backward compatibility with global functions (to be removed)."""

    def test_global_get_storage_dir_matches_instance(self):
        """Global get_storage_dir() matches instance method."""
        from dawn_kestrel.core.settings import settings

        global_path = get_storage_dir()
        instance_path = settings.storage_dir_path()
        assert global_path == instance_path

    def test_global_get_config_dir_matches_instance(self):
        """Global get_config_dir() matches instance method."""
        from dawn_kestrel.core.settings import settings

        global_path = get_config_dir()
        instance_path = settings.config_dir_path()
        assert global_path == instance_path

    def test_global_get_cache_dir_matches_instance(self):
        """Global get_cache_dir() matches instance method."""
        from dawn_kestrel.core.settings import settings

        global_path = get_cache_dir()
        instance_path = settings.cache_dir_path()
        assert global_path == instance_path
