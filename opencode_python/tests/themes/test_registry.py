"""Tests for ThemeRegistry singleton pattern and theme management."""

import pytest
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_python.themes.registry import ThemeRegistry, get_theme_registry as get_registry
from opencode_python.core.event_bus import bus, Events
from opencode_python.themes.events import ThemeChangeEvent
from opencode_python.themes.models import Theme, ThemeMetadata, ThemeSettings
from opencode_python.core.event_bus import bus, Events
from opencode_python.themes.events import ThemeChangeEvent


class TestThemeRegistryBasics:
    """Test basic ThemeRegistry functionality."""

    @pytest.fixture
    def registry(self, tmpdir):
        """Create a ThemeRegistry instance with temp directory."""
        return ThemeRegistry(themes_dir=tmpdir)

    @pytest.fixture
    def sample_theme(self):
        """Create a sample theme for testing."""
        return Theme(
            metadata=ThemeMetadata(
                name="Test Theme",
                slug="test",
                description="Test theme for unit tests",
                author="OpenCode",
                version="1.0.0",
            ),
            primary="#10b981",
            secondary="#5c9cf5",
            accent="#d946ef",
            error="#ef4444",
            warning="#f59e0b",
            success="#10b981",
            info="#10b981",
            text="#f3f4f6",
            text_muted="#9ca3af",
            text_selection="#2968c3",
            background="#1a1d2e",
            background_panel="#242838",
            background_element="#242838",
            background_menu="#242838",
            border="#6b7280",
            border_active="#a855f7",
            border_subtle="#6b7280",
            font_family="monospace",
            font_size=14,
            line_height=1.4,
            animations_enabled=True,
            reduced_motion=False,
        )

    def test_singleton_pattern(self, registry):
        """Test that ThemeRegistry follows singleton pattern."""
        import importlib
        import sys

        # Get same instance
        same_instance = ThemeRegistry.get_instance(themes_dir=registry._loader.themes_dir)

        # Try to create new instance
        with pytest.raises(RuntimeError, match="Use ThemeRegistry.get_instance"):
            ThemeRegistry(themes_dir=registry._loader.themes_dir)

    def test_register_theme(self, registry, sample_theme):
        """Test registering a new theme."""
        registry.register_theme(sample_theme)

        assert sample_theme.metadata.slug in registry.list_themes_metadata()
        assert registry.get_theme(sample_theme.metadata.slug) == sample_theme

    def test_register_duplicate_raises_error(self, registry, sample_theme):
        """Test that registering duplicate theme raises ValueError."""
        registry.register_theme(sample_theme)

        with pytest.raises(ValueError, match="already registered"):
            registry.register_theme(sample_theme)

    def test_get_theme(self, registry, sample_theme):
        """Test getting theme by slug."""
        registry.register_theme(sample_theme)

        assert registry.get_theme(sample_theme.metadata.slug) == sample_theme
        assert registry.get_theme("nonexistent") is None

    def test_list_themes(self, registry, sample_theme):
        """Test listing all themes."""
        registry.register_theme(sample_theme)

        themes = registry.list_themes()

        assert len(themes) == 1
        assert themes[0].name == "Test Theme"
        assert themes[0].slug == "test"

    def test_set_active_theme(self, registry, sample_theme):
        """Test setting active theme."""
        registry.register_theme(sample_theme)

        registry.set_active_theme(sample_theme.metadata.slug)

        assert registry.get_active_theme_slug() == sample_theme.metadata.slug
        assert registry.active_theme == sample_theme

    def test_set_active_theme_nonexistent_raises_error(self, registry, sample_theme):
        """Test setting nonexistent theme raises ValueError."""
        registry.register_theme(sample_theme)

        available = ", ".join([sample_theme.metadata.slug])
        with pytest.raises(ValueError, match=f"not found. Available themes: {available}"):
            registry.set_active_theme("nonexistent")

    def test_active_theme_property(self, registry, sample_theme):
        """Test active_theme property."""
        registry.register_theme(sample_theme)
        registry.set_active_theme(sample_theme.metadata.slug)

        assert registry.active_theme == sample_theme

    def test_get_active_theme_slug(self, registry, sample_theme):
        """Test getting active theme slug."""
        registry.register_theme(sample_theme)
        registry.set_active_theme(sample_theme.metadata.slug)

        assert registry.get_active_theme_slug() == sample_theme.metadata.slug


class TestThemeRegistryEventEmission:
    """Test theme registry event emission."""

    @pytest.fixture
    def registry(self, tmpdir):
        return ThemeRegistry(themes_dir=tmpdir)

    @pytest.fixture
    def sample_theme(self):
        return Theme(
            metadata=ThemeMetadata(
                name="Test Theme",
                slug="test",
                description="Test theme",
                author="OpenCode",
                version="1.0.0",
            ),
            primary="#10b981",
            secondary="#5c9cf5",
            accent="#d946ef",
            error="#ef4444",
            warning="#f59e0b",
            success="#10b981",
            info="#10b981",
            text="#f3f4f6",
            text_muted="#9ca3af",
            text_selection="#2968c3",
            background="#1a1d2e",
            background_panel="#242838",
            background_element="#242838",
            background_menu="#242838",
            border="#6b7280",
            border_active="#a855f7",
            border_subtle="#6b7280",
            font_family="monospace",
            font_size=14,
            line_height=1.4,
            animations_enabled=True,
            reduced_motion=False,
        )

    @pytest.mark.asyncio
    async def test_set_active_theme_emits_event(self, registry, sample_theme):
        """Test that setting active theme emits THEME_CHANGED event."""
        registry.register_theme(sample_theme)

        event_received = []

        async def capture_event(event):
            event_received.append(event)

        await bus.subscribe(Events.THEME_CHANGED, capture_event)
        registry.set_active_theme(sample_theme.metadata.slug)

        await asyncio.sleep(0.1)

        assert len(event_received) == 1
        assert isinstance(event_received[0], ThemeChangeEvent)
        assert event_received[0].theme_slug == sample_theme.metadata.slug


class TestThemeRegistryPersistence:
    """Test theme registry persistence operations."""

    @pytest.fixture
    def registry(self, tmpdir):
        return ThemeRegistry(themes_dir=tmpdir)

    @pytest.fixture
    def sample_theme(self):
        return Theme(
            metadata=ThemeMetadata(
                name="Test Theme",
                slug="test",
                description="Test theme",
                author="OpenCode",
                version="1.0.0",
            ),
            primary="#10b981",
            secondary="#5c9cf5",
            accent="#d946ef",
            error="#ef4444",
            warning="#f59e0b",
            success="#10b981",
            info="#10b981",
            text="#f3f4f6",
            text_muted="#9ca3af",
            text_selection="#2968c3",
            background="#1a1d2e",
            background_panel="#242838",
            background_element="#242838",
            background_menu="#242838",
            border="#6b7280",
            border_active="#a855f7",
            border_subtle="#6b7280",
            font_family="monospace",
            font_size=14,
            line_height=1.4,
            animations_enabled=True,
            reduced_motion=False,
        )

    def test_reload_all_discovers_new_themes(self, registry, sample_theme):
        """Test reloading themes from disk."""
        registry.register_theme(sample_theme)

        initial_count = len(registry.list_themes())

        registry.reload_all()

        final_count = len(registry.list_themes())

        assert final_count == initial_count

    @pytest.mark.asyncio
    async def test_set_theme_and_persist(self, registry, sample_theme):
        """Test setting theme and persisting to settings."""
        import os

        registry.register_theme(sample_theme)

        await registry.set_theme_and_persist(sample_theme.metadata.slug)

        assert registry.get_active_theme_slug() == sample_theme.metadata.slug

        os.environ["OPENCODE_PYTHON_TUI_THEME"] = sample_theme.metadata.slug

    def test_fallback_to_first_theme_if_none_set(self, registry):
        """Test that registry falls back to first available theme."""
        from opencode_python.themes.registry import _theme_registry_instance

        _theme_registry_instance._active_theme_slug = None
        _theme_registry_instance._themes = {}

        theme = registry.active_theme

        assert theme is not None
