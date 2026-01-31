"""Command Palette Dialog for TUI - Quick command execution"""

from typing import Any, Callable, Dict, List, Optional, TypeVar

from textual.app import ComposeResult
from textual.containers import Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static, Button

from opencode_python.themes.models import Theme, ThemeMetadata, ThemeSettings
from opencode_python.themes import get_theme_loader
from opencode_python.core.event_bus import bus, Events

T = TypeVar("T")


class CommandPaletteDialog(ModalScreen[T]):
    """Command palette dialog for quick command execution.

    Allows users to execute essential commands via keyboard shortcuts.
    Supports search/filtering of commands.

    Essential commands:
        - session-list: Open session list
        - model-select: Select AI model
        - theme-select: Select theme
        - quit: Exit TUI
    """

    def __init__(
        self,
        title: str = "Command Palette",
        on_command: Optional[Callable[[str], None]] = None,
    ):
        """Initialize command palette dialog.

        Args:
            title: Dialog title.
            on_command: Callback function when a command is selected.
        """
        super().__init__()
        self.title = title
        self.on_command = on_command
        self._result: Optional[str] = None
        self._closed = False
        self._selected_index: int = 0

        self.commands: List[Dict[str, Any]] = [
            {
                "value": "session-list",
                "title": "Open Session List",
                "description": "View and navigate sessions",
            },
            {
                "value": "create-session",
                "title": "Create Session",
                "description": "Create a new session",
            },
            {
                "value": "model-select",
                "title": "Select Model",
                "description": "Choose AI model to use",
            },
            {
                "value": "theme-select",
                "title": "Select Theme",
                "description": "Choose color theme",
            },
            {
                "value": "switch_theme",
                "title": "Switch Theme",
                "description": "Change active theme (live)",
            },
            {
                "value": "list_themes",
                "title": "List Themes",
                "description": "Show all available themes",
            },
            {
                "value": "preview_theme",
                "title": "Preview Theme",
                "description": "Preview theme colors",
            },
            {
                "value": "theme_settings",
                "title": "Theme Settings",
                "description": "Open theme settings screen",
            },
            {
                "value": "quit",
                "title": "Quit",
                "description": "Exit to TUI application",
            },
        ]

        self.filtered_commands: List[Dict[str, Any]] = list(self.commands)

    def compose(self) -> ComposeResult:
        """Compose command palette dialog widgets."""
        if self.title:
            yield Label(self.title)

        yield Input(placeholder="Search commands...", id="command_search")

        for command in self.filtered_commands:
            # Create command display
            title = command.get("title", "")
            desc = command.get("description", "")

            # Use Static widget for command items
            yield Static(f"  {title}  {desc}", id=f"cmd_{command['value']}")

        yield Static("Press Enter to execute, Escape to cancel")

    def action_enter(self) -> None:
        """Handle Enter key - execute selected command and close."""
        if self.filtered_commands and self._selected_index < len(self.filtered_commands):
            command = self.filtered_commands[self._selected_index]
            value = command.get("value")

            # Handle theme commands
            if value == "switch_theme":
                self._handle_switch_theme()
            elif value == "list_themes":
                self._handle_list_themes()
            elif value == "preview_theme":
                self._handle_preview_theme()
            elif value == "theme_settings":
                self._handle_theme_settings()
            else:
                if self.on_command:
                    self.on_command(value)  # type: ignore[arg-type]

            self.close_dialog(value)

    def _handle_switch_theme(self) -> None:
        """Handle switch_theme command - prompt for theme name."""
        from opencode_python.themes.registry import get_registry

        registry = get_registry()
        themes = registry.list_themes_metadata()

        if not themes:
            yield Static("No themes available")
            return

        theme_names = [tm.slug for tm in themes]

        yield Label("Enter theme name:")
        theme_input = Input(id="theme_name_input", placeholder="e.g., 'posting', 'dark', 'dracula'")

        async def on_submit():
            theme_name = theme_input.value.strip()
            if theme_name not in theme_names:
                yield Static(f"Theme '{theme_name}' not found. Available: {', '.join(theme_names)}")
                return

            await get_registry().set_active_theme(theme_name)
            self.close_dialog(theme_name)

        yield theme_input
        yield Button("Switch", id="theme_switch_button", on_press=on_submit)
        yield Button("Cancel", id="theme_cancel_button", on_press=self.action_escape)

    def _handle_list_themes(self) -> None:
        """Handle list_themes command - show theme selection dialog."""
        from opencode_python.themes.registry import get_registry
        from opencode_python.tui.screens.theme_settings_screen import ThemeSettingsScreen

        registry = get_registry()
        themes = registry.list_themes_metadata()

        if not themes:
            yield Static("No themes available")
            return

        def show_theme_selector():
            self.dismiss()
            result = ThemeSettingsScreen(
                title="Available Themes",
                on_apply=lambda settings: self.close_dialog(settings.get("theme"))
            )
            self.app.push_screen(result)

        yield Static("Press Enter to select")
        yield Button("Select", id="theme_select_button", on_press=show_theme_selector)

    def _handle_preview_theme(self) -> None:
        """Handle preview_theme command - show theme preview."""
        from opencode_python.themes.registry import get_registry

        registry = get_registry()
        themes = registry.list_themes_metadata()

        if not themes:
            yield Static("No themes available")
            return

        def show_theme_preview():
            self.dismiss()
            for tm in themes:
                yield Static(f"{tm.name}: {tm.preview_colors}")

        yield Static("Press Enter to close")
        yield Button("Close", id="theme_preview_button", on_press=self.action_escape)

    def _handle_theme_settings(self) -> None:
        """Handle theme_settings command - open theme settings screen."""
        from opencode_python.themes.registry import get_registry
        from opencode_python.tui.screens.theme_settings_screen import ThemeSettingsScreen

        self.dismiss()
        result = ThemeSettingsScreen(
            title="Theme Settings",
        )
        self.app.push_screen(result)

    def action_escape(self) -> None:
        """Handle Escape key - close without execution."""
        super().close_dialog(None)

    def action_up(self) -> None:
        """Handle Up key - navigate to previous command."""
        if self.filtered_commands:
            if self._selected_index > 0:
                self._selected_index -= 1

    def action_down(self) -> None:
        """Handle Down key - navigate to next command."""
        if self.filtered_commands:
            if self._selected_index < len(self.filtered_commands) - 1:
                self._selected_index += 1
