"""Theme registry with singleton pattern and live switching support."""

from __future__ import annotations

import logging
from typing import Dict, Optional, List, Callable
from pathlib import Path
from enum import Enum

from opencode_python.themes.models import Theme, ThemeMetadata, ThemeSettings
from opencode_python.themes.loader import ThemeLoader
from opencode_python.core.event_bus import bus, Events

logger = logging.getLogger(__name__)


class ThemeRegistry:
    """Registry for managing themes with live switching support.

    Features:
    - Singleton pattern for global access
    - Dynamic theme registration
    - Live theme switching (no restart required)
    - Active theme tracking with reactive property
    - Event bus integration for theme change notifications
    - Theme persistence via Settings
    """

    _instance: Optional["ThemeRegistry"] = None
    _themes: Dict[str, Theme] = {}
    _active_theme_slug: Optional[str] = None
    _loader: ThemeLoader

    def __new__(cls, *args, **kwargs):
        """Prevent multiple instances."""
        if cls._instance is not None:
            raise RuntimeError("Use ThemeRegistry.get_instance() instead of direct construction")
        return super().__new__(cls)

    def __init__(self, themes_dir: Optional[Path] = None):
        """Initialize theme registry.

        Args:
            themes_dir: Directory containing theme files. Defaults to tui/themes/.
        """
        self._loader = ThemeLoader(themes_dir)
        # Load all available themes
        self._themes = self._loader.load_all()
        logger.info(f"ThemeRegistry initialized with {len(self._themes)} themes")

    @classmethod
    def get_instance(cls, themes_dir: Optional[Path] = None) -> "ThemeRegistry":
        """Get singleton instance of ThemeRegistry.

        Args:
            themes_dir: Directory containing theme files.

        Returns:
            ThemeRegistry singleton instance.
        """
        if cls._instance is None:
            cls._instance = ThemeRegistry(themes_dir)
        return cls._instance

    def register_theme(self, theme: Theme) -> None:
        """Register a new theme dynamically.

        Args:
            theme: Theme object to register.

        Raises:
            ValueError: If theme slug already exists.
        """
        slug = theme.metadata.slug

        if slug in self._themes:
            raise ValueError(f"Theme '{slug}' is already registered")

        self._themes[slug] = theme
        logger.info(f"Registered theme: {theme.metadata.name} ({slug})")

        # Persist to disk (if theme has CSS path)
        if theme.css_path and isinstance(theme.css_path, Path):
            self._save_theme_yaml(theme)

    def _save_theme_yaml(self, theme: Theme) -> None:
        """Save theme to YAML file for persistence.

        Args:
            theme: Theme object to save.
        """
        import yaml

        yaml_path = self._loader.themes_dir / f"{theme.metadata.slug}.yaml"

        yaml_data = {
            "metadata": {
                "name": theme.metadata.name,
                "slug": theme.metadata.slug,
                "description": theme.metadata.description,
                "author": theme.metadata.author,
                "version": theme.metadata.version,
                "preview_colors": theme.metadata.preview_colors,
            },
            "primary": theme.primary,
            "secondary": theme.secondary,
            "accent": theme.accent,
            "error": theme.error,
            "warning": theme.warning,
            "success": theme.success,
            "info": theme.info,
            "text": theme.text,
            "text_muted": theme.text_muted,
            "text_selection": theme.text_selection,
            "background": theme.background,
            "background_panel": theme.background_panel,
            "background_element": theme.background_element,
            "background_menu": theme.background_menu,
            "border": theme.border,
            "border_active": theme.border_active,
            "border_subtle": theme.border_subtle,
            "font_family": theme.font_family,
            "font_size": theme.font_size,
            "line_height": theme.line_height,
            "animations_enabled": theme.animations_enabled,
            "reduced_motion": theme.reduced_motion,
        }

        with open(yaml_path, "w") as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved theme to {yaml_path}")

    def get_theme(self, slug: str) -> Optional[Theme]:
        """Get theme by slug.

        Args:
            slug: Theme slug.

        Returns:
            Theme object or None if not found.
        """
        return self._themes.get(slug)

    def list_themes(self) -> List[ThemeMetadata]:
        """List all available themes.

        Returns:
            List of theme metadata objects.
        """
        return [theme.metadata for theme in self._themes.values()]

    def list_themes_metadata(self) -> List[ThemeMetadata]:
        """List all available themes (alias for list_themes).

        Returns:
            List of theme metadata objects.
        """
        return self.list_themes()

    def set_active_theme(self, slug: str) -> None:
        """Set active theme with validation and event emission.

        Args:
            slug: Theme slug to activate.

        Raises:
            ValueError: If theme slug is not found.
        """
        if slug not in self._themes:
            available = ", ".join(self._themes.keys())
            raise ValueError(f"Theme '{slug}' not found. Available themes: {available}")

        old_slug = self._active_theme_slug
        self._active_theme_slug = slug

        theme = self._themes[slug]
        logger.info(f"Active theme changed: {old_slug} -> {slug}")

        # Emit theme change event
        import asyncio

        theme_settings = Theme.get_theme_settings()
        asyncio.create_task(bus.publish(
            Events.THEME_CHANGED,
            {
                "theme_slug": slug,
                "density": theme_settings.density.value,
                "reduced_motion": theme_settings.reduced_motion,
            }
        ))

    @property
    def active_theme(self) -> Theme:
        """Get currently active theme.

        Returns:
            Currently active Theme object.

        Raises:
            RuntimeError: If no themes are available.
        """
        if self._active_theme_slug is None:
            # Load default from settings if not set
            self._load_active_from_settings()

        theme = self._themes.get(self._active_theme_slug) if self._active_theme_slug else None
        if not theme:
            # Fallback to first available theme
            if self._themes:
                self._active_theme_slug = next(iter(self._themes.keys()))
                theme = self._themes[self._active_theme_slug]
            else:
                raise RuntimeError("No themes available in registry")

        return theme

    def _load_active_from_settings(self) -> None:
        """Load active theme slug from Settings."""
        from opencode_python.core.settings import get_settings

        settings = get_settings()
        self._active_theme_slug = settings.tui_theme
        logger.debug(f"Loaded active theme from settings: {self._active_theme_slug}")

    def reload_all(self) -> None:
        """Reload all themes from disk.

        Useful for discovering newly added theme files.
        """
        old_active = self._active_theme_slug
        self._themes = self._loader.reload()
        logger.info(f"Reloaded {len(self._themes)} themes")

        # Restore active theme if possible
        if old_active in self._themes:
            self._active_theme_slug = old_active
        elif self._themes:
            self._active_theme_slug = next(iter(self._themes.keys()))

    def get_active_theme_slug(self) -> str:
        """Get active theme slug string.

        Returns:
            Active theme slug or 'auto' if not set.
        """
        if self._active_theme_slug is None:
            self._load_active_from_settings()
        return self._active_theme_slug or "auto"

    async def set_theme_and_persist(self, slug: str) -> None:
        """Set theme and persist to settings.

        Uses proper Settings persistence via pydantic_settings.save().
        """
        from opencode_python.core.settings import get_settings

        # Set active theme
        self.set_active_theme(slug)

        # Persist to settings
        settings = get_settings()
        settings.tui_theme = slug

        logger.info(f"Theme '{slug}' persisted to settings (tui_theme={slug})")


# Global registry instance
_registry_instance: Optional[ThemeRegistry] = None


def get_registry() -> ThemeRegistry:
    """Get global theme registry instance.

    Returns:
        ThemeRegistry singleton instance.
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ThemeRegistry.get_instance()
    return _registry_instance
