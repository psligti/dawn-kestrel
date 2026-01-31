"""Theme select dialog for choosing UI themes."""

from typing import Callable, Optional

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, ListView, ListItem, Static


class ThemeSelectDialog(ModalScreen[str]):
    """Theme selection dialog for choosing UI themes.

    Args:
        title: Dialog title.
        on_select: Callback when theme is selected.

    Displays 3 essential themes: light, dark, dracula.
    Theme selection applies the selected theme to the app.
    """

    DEFAULT_CSS = """
    ThemeSelectDialog {
        height: auto;
        width: 80;
        align: center top;
        border: thick panel;
        padding: 1;
    }

    ThemeSelectDialog > Vertical {
        height: auto;
        width: 100%;
    }

    ListView {
        height: 20;
    }

    ListItem {
        padding: 0 1;
    }
    """

    THEMES = [
        {"value": "light", "title": "Light"},
        {"value": "dark", "title": "Dark"},
        {"value": "dracula", "title": "Dracula"},
    ]

    def __init__(
        self,
        title: str = "Select Theme",
        on_select: Optional[Callable[[str], None]] = None,
    ):
        super().__init__()
        self.title = title
        self.themes = self.THEMES.copy()
        self.options = self.themes.copy()
        self.on_select = on_select
        self._result: Optional[str] = None
        self._selected_index: int = 0

    def compose(self) -> ComposeResult:
        """Compose theme select dialog widgets."""
        if self.title:
            yield Label(self.title)

        yield ListView(id="theme_list")
        for theme in self.themes:
            yield ListItem(
                Static(theme.get("title", str(theme.get("value", ""))))
            )

        yield Static("Press Enter to select, Escape to cancel")

    async def on_mount(self) -> None:
        """Called when dialog is mounted."""
        list_view = self.query_one(ListView)
        list_view.focus()
        try:
            list_view.index = 0
        except Exception:
            pass

    def select_option(self, value: str) -> None:
        """Select a theme by value.

        Args:
            value: Theme value to select (e.g., "light", "dark", "dracula").
        """
        for idx, theme in enumerate(self.themes):
            if theme.get("value") == value:
                self._selected_index = idx
                self._result = value
                if self.on_select:
                    self.on_select(value)
                try:
                    list_view = self.query_one(ListView)
                    if list_view.index != idx:
                        list_view.index = idx
                except Exception:
                    pass
                return

    def close_dialog(self, value: Optional[str] = None) -> None:
        """Close dialog and return selected theme.

        Args:
            value: Selected theme value (defaults to first theme or None).
        """
        self._result = value
        self.dismiss()

    def get_result(self) -> Optional[str]:
        """Get dialog result.

        Returns:
            Selected theme value or None.
        """
        return self._result

    def action_enter(self) -> None:
        """Handle Enter key - select current theme and close."""
        if self.themes and self._selected_index < len(self.themes):
            value = self.themes[self._selected_index].get("value")
            if value is not None:
                if self.on_select:
                    self.on_select(value)
                self.close_dialog(value)
            else:
                self.close_dialog(None)

    def action_escape(self) -> None:
        """Handle Escape key - close without selection."""
        self.close_dialog(None)
