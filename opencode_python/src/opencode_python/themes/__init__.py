"""OpenCode Python - Theme System Package

This package provides a comprehensive theme system for the TUI,
including theme models, loaders, and event management.
"""

from opencode_python.themes.models import (
    Theme,
    ThemeMetadata,
    ThemeSettings,
    DensityMode,
)

from opencode_python.themes.loader import (
    ThemeLoader,
    get_theme_loader,
)

from opencode_python.themes.events import (
    ThemeChangeEvent,
    KeybindingUpdateEvent,
    LayoutToggleEvent,
)

from opencode_python.themes.registry import ThemeRegistry, get_registry

__all__ = [
    # Models
    "Theme",
    "ThemeMetadata",
    "ThemeSettings",
    "DensityMode",
    # Loader
    "ThemeLoader",
    "get_theme_loader",
    # Registry
    "ThemeRegistry",
    "get_registry",
    # Events
    "ThemeChangeEvent",
    "KeybindingUpdateEvent",
    "LayoutToggleEvent",
]
