"""Theme loader for loading and managing themes from YAML and TCSS files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

from opencode_python.themes.models import Theme, ThemeMetadata, ThemeSettings

logger = logging.getLogger(__name__)


@dataclass
class ThemeEntry:
    """Entry representing a loaded theme."""

    theme: Theme
    source: str  # "yaml" or "tcss"
    path: Path


class ThemeLoader:
    """Loader for themes from YAML configuration and TCSS files.

    Supports both YAML-based theme definitions and Textual .tcss files.
    """

    def __init__(self, themes_dir: Optional[Path] = None):
        """Initialize theme loader.

        Args:
            themes_dir: Directory containing theme files. Defaults to tui/themes/.
        """
        if themes_dir is None:
            # Default to tui/themes directory
            import opencode_python.tui as tui_module
            base_path = Path(tui_module.__file__).parent
            themes_dir = base_path / "themes"

        self.themes_dir = Path(themes_dir)
        self._themes: Dict[str, ThemeEntry] = {}
        self._settings: Optional[ThemeSettings] = None

    def load_all(self) -> Dict[str, Theme]:
        """Load all available themes.

        Returns:
            Dictionary mapping theme slug to Theme objects.
        """
        self._themes.clear()

        # Load YAML themes
        for yaml_file in self.themes_dir.glob("*.yaml"):
            try:
                self._load_yaml_theme(yaml_file)
            except Exception as e:
                logger.warning(f"Failed to load theme from {yaml_file}: {e}")

        # Load TCSS themes (backward compatibility)
        for tcss_file in self.themes_dir.glob("*.tcss"):
            try:
                self._load_tcss_theme(tcss_file)
            except Exception as e:
                logger.warning(f"Failed to load TCSS theme from {tcss_file}: {e}")

        logger.info(f"Loaded {len(self._themes)} themes")
        return {slug: entry.theme for slug, entry in self._themes.items()}

    def _load_yaml_theme(self, yaml_path: Path) -> Theme:
        """Load theme from YAML file.

        Args:
            yaml_path: Path to YAML theme file.

        Returns:
            Loaded Theme object.
        """
        import yaml  # type: ignore

        data = yaml.safe_load(yaml_path.read_text())

        # Parse metadata
        metadata_data = data.get("metadata", {})
        metadata = ThemeMetadata(
            name=metadata_data.get("name", yaml_path.stem),
            slug=metadata_data.get("slug", yaml_path.stem),
            description=metadata_data.get("description", ""),
            author=metadata_data.get("author", "OpenCode"),
            version=metadata_data.get("version", "1.0.0"),
            preview_colors=metadata_data.get("preview_colors", {}),
        )

        # Parse theme colors
        theme = Theme(
            metadata=metadata,
            primary=data.get("primary", "#56b6c2"),
            secondary=data.get("secondary", "#5c9cf5"),
            accent=data.get("accent", "#9d7cd8"),
            error=data.get("error", "#e06c75"),
            warning=data.get("warning", "#f5a742"),
            success=data.get("success", "#7fd88f"),
            info=data.get("info", "#56b6c2"),
            text=data.get("text", "#f5f5f5"),
            text_muted=data.get("text_muted", "#a0a0a0"),
            text_selection=data.get("text_selection", "#2968c3"),
            background=data.get("background", "#0a0a0a"),
            background_panel=data.get("background_panel", "#141414"),
            background_element=data.get("background_element", "#1e1e1e"),
            background_menu=data.get("background_menu", "#1e1e1e"),
            border=data.get("border", "#484848"),
            border_active=data.get("border_active", "#606060"),
            border_subtle=data.get("border_subtle", "#3c3c3c"),
            font_family=data.get("font_family", "monospace"),
            font_size=data.get("font_size", 14),
            line_height=data.get("line_height", 1.4),
            animations_enabled=data.get("animations_enabled", True),
            reduced_motion=data.get("reduced_motion", False),
            css_path=None,  # YAML themes use inline colors
        )

        entry = ThemeEntry(theme=theme, source="yaml", path=yaml_path)
        self._themes[theme.metadata.slug] = entry
        return theme

    def _load_tcss_theme(self, tcss_path: Path) -> Theme:
        """Load theme from Textual .tcss file.

        Parses CSS variables from TCSS file to extract color palette.

        Args:
            tcss_path: Path to TCSS theme file.

        Returns:
            Loaded Theme object.
        """
        import re

        content = tcss_path.read_text()

        # Parse CSS variables
        color_pattern = r'\$(\w+(?:-\w+)*):\s*([^;]+);'
        colors: Dict[str, str] = {}

        for match in re.finditer(color_pattern, content):
            var_name = match.group(1)
            color_value = match.group(2).strip()
            colors[var_name] = color_value

        # Create theme from parsed colors
        theme = Theme(
            metadata=ThemeMetadata(
                name=tcss_path.stem.replace("-", " ").title(),
                slug=tcss_path.stem,
                description=f"Theme from {tcss_path.name}",
                author="OpenCode",
                version="1.0.0",
            ),
            primary=colors.get("primary", "#56b6c2"),
            secondary=colors.get("secondary", "#5c9cf5"),
            accent=colors.get("accent", "#9d7cd8"),
            error=colors.get("error", "#e06c75"),
            warning=colors.get("warning", "#f5a742"),
            success=colors.get("success", "#7fd88f"),
            info=colors.get("info", "#56b6c2"),
            text=colors.get("text", "#f5f5f5"),
            text_muted=colors.get("text-muted", "#a0a0a0"),
            text_selection=colors.get("text-selection", "#2968c3"),
            background=colors.get("background", "#0a0a0a"),
            background_panel=colors.get("background-panel", "#141414"),
            background_element=colors.get("background-element", "#1e1e1e"),
            background_menu=colors.get("background-menu", "#1e1e1e"),
            border=colors.get("border", "#484848"),
            border_active=colors.get("border-active", "#606060"),
            border_subtle=colors.get("border-subtle", "#3c3c3c"),
            css_path=tcss_path,
        )

        entry = ThemeEntry(theme=theme, source="tcss", path=tcss_path)
        self._themes[theme.metadata.slug] = entry
        return theme

    def get_theme(self, slug: str) -> Optional[Theme]:
        """Get theme by slug.

        Args:
            slug: Theme slug.

        Returns:
            Theme object or None if not found.
        """
        entry = self._themes.get(slug)
        return entry.theme if entry else None

    def list_themes(self) -> List[ThemeMetadata]:
        """List all available themes.

        Returns:
            List of theme metadata.
        """
        return [entry.theme.metadata for entry in self._themes.values()]

    def reload(self) -> Dict[str, Theme]:
        """Reload all themes from disk.

        Returns:
            Dictionary mapping theme slug to Theme objects.
        """
        return self.load_all()

    def apply_settings(self, settings: ThemeSettings) -> Theme:
        """Apply user settings to current theme.

        Args:
            settings: Theme settings to apply.

        Returns:
            Theme with settings applied.
        """
        self._settings = settings
        theme = self.get_theme(settings.theme_slug)
        if not theme:
            logger.warning(f"Theme {settings.theme_slug} not found, using dark")
            theme = self.get_theme("dark")

        if theme:
            return settings.apply_to_theme(theme)

        # Fallback to default theme
        return Theme(
            metadata=ThemeMetadata(
                name="Dark",
                slug="dark",
                description="Default dark theme",
            ),
        )

    def get_css_path(self, slug: str) -> Optional[Path]:
        """Get CSS file path for a theme.

        Args:
            slug: Theme slug.

        Returns:
            Path to TCSS file or None.
        """
        entry = self._themes.get(slug)
        if entry and entry.source == "tcss" and hasattr(entry, "css_path"):
            return entry.css_path if isinstance(entry.css_path, Path) else None
        return None


# Global theme loader instance
_theme_loader: Optional[ThemeLoader] = None


def get_theme_loader() -> ThemeLoader:
    """Get global theme loader instance.

    Returns:
        ThemeLoader instance.
    """
    global _theme_loader
    if _theme_loader is None:
        _theme_loader = ThemeLoader()
        _theme_loader.load_all()
    return _theme_loader
