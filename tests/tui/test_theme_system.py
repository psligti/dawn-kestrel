"""Tests for theme system functionality."""

from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import json

from opencode_python.themes.models import (
    Theme,
    ThemeMetadata,
    ThemeSettings,
    DensityMode,
)
from opencode_python.themes.loader import ThemeLoader, get_theme_loader
from opencode_python.themes.events import (
    ThemeChangeEvent,
    KeybindingUpdateEvent,
    LayoutToggleEvent,
)


class TestThemeModels:
    """Test theme models."""

    def test_theme_metadata_creation(self):
        """Test creating theme metadata."""
        metadata = ThemeMetadata(
            name="Test Theme",
            slug="test-theme",
            description="A test theme",
            author="Test Author",
            version="1.0.0",
            preview_colors={"bg": "#000000", "fg": "#ffffff", "accent": "#56b6c2"},
        )

        assert metadata.name == "Test Theme"
        assert metadata.slug == "test-theme"
        assert metadata.preview_colors["bg"] == "#000000"

    def test_theme_creation(self):
        """Test creating a theme."""
        metadata = ThemeMetadata(
            name="Dark",
            slug="dark",
            description="Dark theme",
        )

        theme = Theme(
            metadata=metadata,
            primary="#56b6c2",
            secondary="#5c9cf5",
        )

        assert theme.metadata.slug == "dark"
        assert theme.primary == "#56b6c2"
        assert theme.reduced_motion is False

    def test_theme_to_css_dict(self):
        """Test converting theme to CSS dictionary."""
        theme = Theme(
            metadata=ThemeMetadata(name="Test", slug="test"),
            primary="#56b6c2",
            background="#0a0a0a",
        )

        css_dict = theme.to_css_dict()

        assert "$primary" in css_dict
        assert css_dict["$primary"] == "#56b6c2"
        assert css_dict["$background"] == "#0a0a0a"

    def test_theme_settings_creation(self):
        """Test creating theme settings."""
        settings = ThemeSettings(
            theme_slug="dark",
            density=DensityMode.NORMAL,
            reduced_motion=False,
        )

        assert settings.theme_slug == "dark"
        assert settings.density == DensityMode.NORMAL
        assert settings.reduced_motion is False

    def test_apply_settings_to_theme(self):
        """Test applying settings to theme."""
        theme = Theme(
            metadata=ThemeMetadata(name="Test", slug="test"),
        )

        settings = ThemeSettings(
            theme_slug="test",
            reduced_motion=True,
        )

        modified_theme = settings.apply_to_theme(theme)

        assert modified_theme.reduced_motion is True


class TestThemeLoader:
    """Test theme loader."""

    def test_theme_loader_initialization(self, tmp_path):
        """Test initializing theme loader."""
        # Create themes directory with YAML file
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir(parents=True)

        yaml_content = """
metadata:
  name: Test Theme
  slug: test
primary: "#56b6c2"
background: "#0a0a0a"
        """
        (themes_dir / "test.yaml").write_text(yaml_content)

        loader = ThemeLoader(themes_dir=themes_dir)
        loader.load_all()

        theme = loader.get_theme("test")
        assert theme is not None
        assert theme.primary == "#56b6c2"

    def test_load_tcss_theme(self, tmp_path):
        """Test loading TCSS theme."""
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir(parents=True)

        tcss_content = """
$primary: #56b6c2;
$secondary: #5c9cf5;
$background: #0a0a0a;
$text: #f5f5f5;
        """
        (themes_dir / "test.tcss").write_text(tcss_content)

        loader = ThemeLoader(themes_dir=themes_dir)
        loader.load_all()

        theme = loader.get_theme("test")
        assert theme is not None
        assert theme.primary == "#56b6c2"

    def test_get_css_path(self, tmp_path):
        """Test getting CSS path for TCSS theme."""
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir(parents=True)

        tcss_content = "$primary: #56b6c2;"
        (themes_dir / "test.tcss").write_text(tcss_content)

        loader = ThemeLoader(themes_dir=themes_dir)
        loader.load_all()

        css_path = loader.get_css_path("test")
        assert css_path is not None
        assert css_path == (themes_dir / "test.tcss")

    def test_list_themes(self, tmp_path):
        """Test listing all themes."""
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir(parents=True)

        (themes_dir / "test1.yaml").write_text("metadata:\n  name: Test1\nslug: test1\nprimary: #56b6c2")
        (themes_dir / "test2.yaml").write_text("metadata:\n  name: Test2\nslug: test2\nprimary: #5c9cf5")

        loader = ThemeLoader(themes_dir=themes_dir)
        loader.load_all()

        themes = loader.list_themes()
        assert len(themes) == 2

        slugs = [t.slug for t in themes]
        assert "test1" in slugs
        assert "test2" in slugs


class TestThemeEvents:
    """Test theme events."""

    def test_theme_change_event(self):
        """Test theme change event."""
        event = ThemeChangeEvent(
            theme_slug="dark",
            density="normal",
            reduced_motion=False,
        )

        assert event.theme_slug == "dark"
        assert event.density == "normal"
        assert event.reduced_motion is False

    def test_keybinding_update_event(self):
        """Test keybinding update event."""
        event = KeybindingUpdateEvent(
            action="quit",
            key="ctrl+q",
            old_key="q",
        )

        assert event.action == "quit"
        assert event.key == "ctrl+q"
        assert event.old_key == "q"

    def test_layout_toggle_event(self):
        """Test layout toggle event."""
        event = LayoutToggleEvent(density="compact")

        assert event.density == "compact"


class TestThemeLoaderHotReload:
    """Test theme hot reload functionality."""

    def test_reload_themes(self, tmp_path):
        """Test reloading themes."""
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir(parents=True)

        (themes_dir / "test.yaml").write_text("metadata:\n  name: Test\nslug: test\nprimary: #56b6c2")

        loader = ThemeLoader(themes_dir=themes_dir)
        loader.load_all()

        # Modify theme file
        (themes_dir / "test.yaml").write_text("metadata:\n  name: Updated\nslug: test\nprimary: #ff0000")

        # Reload
        loader.reload()

        theme = loader.get_theme("test")
        assert theme is not None
        # Theme should have updated color
        assert theme.primary == "#ff0000"
