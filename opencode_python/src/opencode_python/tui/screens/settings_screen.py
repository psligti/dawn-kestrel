"""Settings screen for TUI configuration."""

from typing import Callable, Optional, List, Dict, Any

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import (
    Label, ListView, ListItem, Static, Button, Header, Footer
)
from textual.containers import Vertical, Horizontal, Grid

from opencode_python.core.settings import get_settings, Settings
from opencode_python.providers.base import ModelInfo
from opencode_python.tui.dialogs.theme_select_dialog import ThemeSelectDialog
from opencode_python.tui.dialogs.model_select_dialog import ModelSelectDialog
from opencode_python.agents.builtin import get_all_agents


class SettingsScreen(ModalScreen[str]):
    """Settings screen for configuring TUI preferences.

    Provides theme, model, and agent selection with Save and Cancel buttons.
    """

    DEFAULT_CSS = """
    SettingsScreen {
        height: auto;
        width: 80;
        align: center top;
        border: thick panel;
        padding: 1;
    }

    Vertical {
        height: auto;
        width: 100%;
    }

    Header {
        background: $panel;
        border-bottom: thin $panel;
    }

    #settings_content {
        padding: 1;
    }

    ListView {
        height: 10;
    }

    ListItem {
        padding: 0 1;
    }

    .setting-section {
        margin-bottom: 1;
    }

    .setting-label {
        text-style: bold;
    }

    Button {
        margin-left: 1;
    }

    .primary-button {
        color: $accent;
    }
    """

    THEMES = [
        {"value": "light", "title": "Light"},
        {"value": "dark", "title": "Dark"},
        {"value": "dracula", "title": "Dracula"},
        {"value": "gruvbox", "title": "Gruvbox"},
        {"value": "catppuccin", "title": "Catppuccin"},
        {"value": "nord", "title": "Nord"},
        {"value": "tokyonight", "title": "Tokyo Night"},
        {"value": "onedarkpro", "title": "One Dark Pro"},
    ]

    def __init__(
        self,
        title: str = "Settings",
        on_save: Optional[Callable[[Settings], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None
    ):
        """Initialize settings screen.

        Args:
            title: Screen title.
            on_save: Callback when settings are saved.
            on_cancel: Callback when cancelled.
        """
        super().__init__()
        self.title = title
        self.themes = self.THEMES.copy()
        self.on_save = on_save
        self.on_cancel = on_cancel
        self._selected_theme: Optional[str] = None
        self._selected_model: Optional[ModelInfo] = None
        self._selected_agent: Optional[str] = None
        self._result: Optional[Dict[str, Any]] = None
        self._settings: Optional[Settings] = None

    def compose(self) -> ComposeResult:
        """Compose settings screen widgets."""
        if self.title:
            yield Header(id="settings_header", title=self.title)

        with Vertical(id="settings_content"):
            yield Label("Theme", classes="setting-label")
            yield ListView(id="theme_list")
            for theme in self.themes:
                yield ListItem(
                    Static(theme.get("title", str(theme.get("value", ""))))
                )

            yield Label("Model", classes="setting-label")
            yield ListView(id="model_list")
            yield Static("Press Enter to select, Escape to cancel")

            yield Label("Agent", classes="setting-label")
            yield ListView(id="agent_list")
            for agent in get_all_agents():
                yield ListItem(
                    Static(agent.name)
                )

            yield Static("Press Enter to select, Escape to cancel")

            yield Horizontal(id="button_bar", margin_top=1)
            yield Button("Save", variant="primary", id="save_button", classes="primary-button")
            yield Button("Cancel", id="cancel_button")

        yield Footer()

    async def on_mount(self) -> None:
        """Called when screen is mounted."""
        self._settings = get_settings()

        # Set initial selections from settings
        self._selected_theme = self._settings.tui_theme
        self._selected_model = self._find_model_by_id(self._settings.model_default)
        self._selected_agent = self._settings.agent_default

        # Set initial highlights
        theme_list = self.query_one("#theme_list", ListView)
        model_list = self.query_one("#model_list", ListView)
        agent_list = self.query_one("#agent_list", ListView)

        theme_list.focus()
        try:
            theme_list.index = self._find_theme_index(self._settings.tui_theme)
        except Exception:
            pass

        model_list.focus()
        try:
            model_list.index = self._find_model_index(self._settings.model_default)
        except Exception:
            pass

        agent_list.focus()
        try:
            agent_list.index = self._find_agent_index(self._settings.agent_default)
        except Exception:
            pass

    def _find_theme_index(self, theme_value: str) -> int:
        """Find theme index by value.

        Args:
            theme_value: Theme value to find.

        Returns:
            Index of theme, or 0 if not found.
        """
        for idx, theme in enumerate(self.themes):
            if theme.get("value") == theme_value:
                return idx
        return 0

    def _find_model_index(self, model_id: str) -> int:
        """Find model index by ID.

        Args:
            model_id: Model ID to find.

        Returns:
            Index of model, or 0 if not found.
        """
        return 0

    def _find_agent_index(self, agent_name: str) -> int:
        """Find agent index by name.

        Args:
            agent_name: Agent name to find.

        Returns:
            Index of agent, or 0 if not found.
        """
        agents = get_all_agents()
        for idx, agent in enumerate(agents):
            if agent.name.lower() == agent_name.lower():
                return idx
        return 0

    def _find_model_by_id(self, model_id: str) -> Optional[ModelInfo]:
        """Find model by ID.

        Args:
            model_id: Model ID to find.

        Returns:
            ModelInfo or None.
        """
        # For now, return None if model ID not found
        # This will be handled when models are loaded
        return None

    def select_theme(self, theme_value: str) -> None:
        """Select a theme by value.

        Args:
            theme_value: Theme value to select.
        """
        self._selected_theme = theme_value
        try:
            theme_list = self.query_one("#theme_list", ListView)
            theme_list.index = self._find_theme_index(theme_value)
        except Exception:
            pass

    def select_model(self, model: ModelInfo) -> None:
        """Select a model by ModelInfo object.

        Args:
            model: ModelInfo to select.
        """
        self._selected_model = model
        try:
            model_list = self.query_one("#model_list", ListView)
            model_list.index = self._find_model_index(model.id)
        except Exception:
            pass

    def select_agent(self, agent_name: str) -> None:
        """Select an agent by name.

        Args:
            agent_name: Agent name to select.
        """
        self._selected_agent = agent_name
        try:
            agent_list = self.query_one("#agent_list", ListView)
            agent_list.index = self._find_agent_index(agent_name)
        except Exception:
            pass

    def close_dialog(self, value: Optional[Dict[str, Any]] = None) -> None:
        """Close dialog and return settings.

        Args:
            value: Settings dictionary (or None if cancelled).
        """
        self._result = value
        self.dismiss()

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Get dialog result.

        Returns:
            Settings dictionary or None.
        """
        return self._result

    def action_enter(self) -> None:
        """Handle Enter key - select current item and close."""
        if self._selected_theme:
            self.save_settings()

    def action_escape(self) -> None:
        """Handle Escape key - close without saving."""
        self.close_dialog(None)

    def action_save(self) -> None:
        """Handle Save button - save settings and close."""
        self.save_settings()

    def action_cancel(self) -> None:
        """Handle Cancel button - close without saving."""
        self.close_dialog(None)

    def save_settings(self) -> None:
        """Save settings and return them.

        Returns:
            Dictionary containing theme, model, and agent selections.
        """
        settings = get_settings()

        if self._selected_theme and self._selected_theme != settings.tui_theme:
            try:
                self.app.theme = self._selected_theme
            except Exception:
                pass
            settings.tui_theme = self._selected_theme

        if self._selected_model:
            settings.model_default = self._selected_model.id

        if self._selected_agent:
            settings.agent_default = self._selected_agent

        self._result = {
            "theme": self._selected_theme,
            "model": self._selected_model,
            "agent": self._selected_agent
        }

        if self.on_save:
            self.on_save(settings)

        self.close_dialog(self._result)
