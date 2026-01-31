"""Theme models using Pydantic for validation and serialization."""

from __future__ import annotations

from typing import Literal, Dict, Optional, Any
from pathlib import Path
from enum import Enum

from pydantic import BaseModel, Field


class DensityMode(str, Enum):
    """Layout density modes for UI spacing."""

    COMPACT = "compact"
    NORMAL = "normal"
    EXPANDED = "expanded"


class ThemeMetadata(BaseModel):
    """Metadata about a theme."""

    name: str = Field(..., description="Display name of the theme")
    slug: str = Field(..., description="Unique identifier for the theme")
    description: str = Field(default="", description="Theme description")
    author: str = Field(default="OpenCode", description="Theme author")
    version: str = Field(default="1.0.0", description="Theme version")
    preview_colors: Dict[str, str] = Field(
        default_factory=dict,
        description="Color palette for preview (bg, fg, accent)",
    )


class Theme(BaseModel):
    """Theme definition with colors and styling."""

    metadata: ThemeMetadata = Field(..., description="Theme metadata")

    # Primary colors
    primary: str = Field(default="#56b6c2", description="Primary accent color")
    secondary: str = Field(default="#5c9cf5", description="Secondary accent color")
    accent: str = Field(default="#9d7cd8", description="Emphasis color")

    # Status colors
    error: str = Field(default="#e06c75", description="Error color")
    warning: str = Field(default="#f5a742", description="Warning color")
    success: str = Field(default="#7fd88f", description="Success color")
    info: str = Field(default="#56b6c2", description="Info color")

    # Text colors
    text: str = Field(default="#f5f5f5", description="Main text color")
    text_muted: str = Field(default="#a0a0a0", description="Muted text color")
    text_selection: str = Field(default="#2968c3", description="Selection background")

    # Background colors
    background: str = Field(default="#0a0a0a", description="Main background")
    background_panel: str = Field(default="#141414", description="Panel background")
    background_element: str = Field(default="#1e1e1e", description="Element background")
    background_menu: str = Field(default="#1e1e1e", description="Menu background")

    # Border colors
    border: str = Field(default="#484848", description="Border color")
    border_active: str = Field(default="#606060", description="Active border color")
    border_subtle: str = Field(default="#3c3c3c", description="Subtle border color")

    # Font and spacing
    font_family: str = Field(default="monospace", description="Font family")
    font_size: int = Field(default=14, description="Font size")
    line_height: float = Field(default=1.4, description="Line height")

    # Motion settings
    animations_enabled: bool = Field(default=True, description="Enable animations")
    reduced_motion: bool = Field(default=False, description="Reduced motion mode")

    # CSS path (for Textual .tcss files)
    css_path: Optional[Path] = Field(
        default=None,
        description="Path to .tcss file for Textual theme",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {Path: str}

    def to_css_dict(self) -> Dict[str, str]:
        """Convert theme to CSS variable dictionary.

        Returns:
            Dictionary of CSS variable names to values.
        """
        return {
            "$primary": self.primary,
            "$secondary": self.secondary,
            "$accent": self.accent,
            "$error": self.error,
            "$warning": self.warning,
            "$success": self.success,
            "$info": self.info,
            "$text": self.text,
            "$text-muted": self.text_muted,
            "$text-selection": self.text_selection,
            "$background": self.background,
            "$background-panel": self.background_panel,
            "$background-element": self.background_element,
            "$background-menu": self.background_menu,
            "$border": self.border,
            "$border-active": self.border_active,
            "$border-subtle": self.border_subtle,
        }

    @staticmethod
    def get_theme_settings() -> ThemeSettings:
        """Get default theme settings.

        Returns:
            Default ThemeSettings instance with normal density and motion enabled.
        """
        return ThemeSettings()


class ThemeSettings(BaseModel):
    """User theme preferences and settings."""

    theme_slug: str = Field(default="dark", description="Current theme slug")
    density: DensityMode = Field(default=DensityMode.NORMAL, description="UI density mode")
    reduced_motion: bool = Field(default=False, description="Reduced motion toggle")
    custom_css: str = Field(default="", description="Custom CSS overrides")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True

    def apply_to_theme(self, theme: Theme) -> Theme:
        """Apply settings to a theme.

        Args:
            theme: Theme to modify.

        Returns:
            Modified theme with settings applied.
        """
        theme.reduced_motion = self.reduced_motion
        return theme
