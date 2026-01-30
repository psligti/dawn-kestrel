"""Theme settings screen for comprehensive theme configuration."""

from __future__ import annotations

from typing import Callable, Optional

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import (
    Label,
    ListView,
    ListItem,
    Static,
    Button,
    Switch,
)
from textual.containers import Vertical, Horizontal

from opencode_python.core.settings import get_settings, Settings
from opencode_python.themes import (
    ThemeLoader,
    get_theme_loader,
    ThemeChangeEvent,
    LayoutToggleEvent,
)


class ThemeSettingsScreen(ModalScreen[dict]):
    """Theme settings screen for theme selection, density, and accessibility.

    Provides:
    - Theme selection with live preview
    - Density toggle (compact/normal/expanded)
    - Reduced motion toggle
    - Immediate application of changes
    """

    DEFAULT_CSS = """
    ThemeSettingsScreen {
        height: auto;
        width: 100;
        align: center top;
        border: thick panel;
        padding: 1;
    }

    Vertical {
        height: auto;
        width: 100%;
    }

    .section-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .setting-row {
        margin-bottom: 1;
    }

    .help-text {
        text-style: dim italic;
        margin-top: 1;
    }

    Button {
        margin-left: 1;
    }

    #theme_list {
        height: 15;
    }

    #density_list {
        height: 8;
    }
    """

    DENSITY_OPTIONS = [
        {"value": "compact", "title": "Compact - Minimal spacing"},
        {"value": "normal", "title": "Normal - Default spacing"},
        {"value": "expanded", "title": "Expanded - More spacing"},
    ]

    def __init__(
        self,
        on_apply: Optional[Callable[[dict], None]] = None,
    ):
        """Initialize theme settings screen.

        Args:
            on_apply: Callback when settings are applied.
        """
        super().__init__()
        self.on_apply = on_apply
        self._result: Optional[dict] = None
        self._settings: Optional[Settings] = None
        self._theme_loader: Optional[ThemeLoader] = None

        self._selected_theme: Optional[str] = None
        self._selected_density: Optional[str] = None
        self._reduced_motion: bool = False

    def compose(self) -> ComposeResult:
        """Compose theme settings screen widgets."""
        yield Label("Theme Settings", classes="section-title")

        # Theme selection
        yield Label("Theme", classes="section-title")
        yield ListView(id="theme_list")

        # Density selection
        yield Label("Layout Density", classes="section-title")
        yield ListView(id="density_list")

        # Reduced motion toggle
        with Horizontal(classes="setting-row"):
            yield Label("Reduced Motion")
            yield Switch(id="reduced_motion_switch")

        # Help text
        yield Static("Press Enter to apply, Escape to cancel", classes="help-text")

        # Action buttons
        with Horizontal(id="button_bar"):
            yield Button("Apply", variant="primary", id="apply_button")
            yield Button("Cancel", id="cancel_button")

    async def on_mount(self) -> None:
        """Called when screen is mounted."""
        self._settings = get_settings()
        self._theme_loader = get_theme_loader()

        # Set initial values from settings
        self._selected_theme = self._settings.tui_theme or "dark"
        self._selected_density = self._settings.tui_density or "normal"
        self._reduced_motion = self._settings.tui_reduced_motion or False

        # Populate theme list
        theme_list = self.query_one("#theme_list", ListView)
        theme_list.remove_children()
        for theme_metadata in self._theme_loader.list_themes():
            title = f"{theme_metadata.name} - {theme_metadata.description}"
            yield ListItem(Static(title))
        await theme_list.mount_all(
            [
                ListItem(Static(f"{tm.name} - {tm.description}"))
                for tm in self._theme_loader.list_themes()
            ]
        )

        # Set initial theme highlight
        try:
            theme_index = self._find_theme_index(self._selected_theme)
            theme_list.highlighted = theme_index
        except Exception:
            theme_list.highlighted = 0

        # Populate density list
        density_list = self.query_one("#density_list", ListView)
        density_list.remove_children()
        for option in self.DENSITY_OPTIONS:
            yield ListItem(Static(option.get("title", "")))
        await density_list.mount_all(
            [ListItem(Static(opt.get("title", ""))) for opt in self.DENSITY_OPTIONS]
        )

        # Set initial density highlight
        try:
            density_index = self._find_density_index(self._selected_density)
            density_list.highlighted = density_index
        except Exception:
            density_list.highlighted = 1  # Default to normal

        # Set reduced motion switch
        reduced_motion_switch = self.query_one("#reduced_motion_switch", Switch)
        reduced_motion_switch.value = self._reduced_motion

        # Focus theme list
        theme_list.focus()

    def _find_theme_index(self, theme_slug: str) -> int:
        """Find theme index by slug.

        Args:
            theme_slug: Theme slug to find.

        Returns:
            Index of theme in list.
        """
        themes = self._theme_loader.list_themes()
        for idx, theme in enumerate(themes):
            if theme.slug == theme_slug:
                return idx
        return 0

    def _find_density_index(self, density: str) -> int:
        """Find density index by value.

        Args:
            density: Density value.

        Returns:
            Index of density option.
        """
        for idx, option in enumerate(self.DENSITY_OPTIONS):
            if option.get("value") == density:
                return idx
        return 1  # Default to normal

    def on_list_view_highlighted(
        self, event: ListView.Highlighted
    ) -> None:
        """Handle list item highlight for live preview.

        Args:
            event: Highlight event.
        """
        list_view = event.list_view

        if list_view.id == "theme_list":
            themes = self._theme_loader.list_themes()
            if event.index < len(themes):
                self._selected_theme = themes[event.index].slug
                self._apply_theme_preview()

        elif list_view.id == "density_list":
            if event.index < len(self.DENSITY_OPTIONS):
                self._selected_density = self.DENSITY_OPTIONS[event.index].get("value")

    def _apply_theme_preview(self) -> None:
        """Apply theme preview to current app."""
        if not self._selected_theme:
            return

        try:
            css_path = self._theme_loader.get_css_path(self._selected_theme)
            if css_path:
                self.app.theme = self._selected_theme
        except Exception:
            pass

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle reduced motion switch change.

        Args:
            event: Switch changed event.
        """
        if event.switch.id == "reduced_motion_switch":
            self._reduced_motion = event.value

    def action_enter(self) -> None:
        """Handle Enter key - apply settings and close."""
        self._apply_settings()

    def action_escape(self) -> None:
        """Handle Escape key - close without applying."""
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button pressed event.
        """
        if event.button.id == "apply_button":
            self._apply_settings()
        elif event.button.id == "cancel_button":
            self.dismiss(None)

    def _apply_settings(self) -> None:
        """Apply selected settings and close.

        Updates settings, emits events, and closes the screen.
        """
        if not self._settings:
            return

        self._settings.tui_theme = self._selected_theme or "dark"
        self._settings.tui_density = self._selected_density or "normal"
        self._settings.tui_reduced_motion = self._reduced_motion

        result = {
            "theme": self._selected_theme,
            "density": self._selected_density,
            "reduced_motion": self._reduced_motion,
        }

        # Apply theme to app
        try:
            self.app.theme = self._settings.tui_theme
        except Exception:
            pass

        # Emit events
        self.app.post_message(
            ThemeChangeEvent(
                theme_slug=self._selected_theme,
                density=self._selected_density,
                reduced_motion=self._reduced_motion,
            )
        )

        if self._selected_density:
            self.app.post_message(
                LayoutToggleEvent(density=self._selected_density)
            )

        # Call callback
        if self.on_apply:
            self.on_apply(result)

        self.dismiss(result)
