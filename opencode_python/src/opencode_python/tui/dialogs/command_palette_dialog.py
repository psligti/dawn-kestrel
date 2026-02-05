"""Command Palette Dialog for TUI - Quick command execution"""

from typing import Any, Callable, Dict, List, Optional, TypeVar

from textual.app import ComposeResult
from textual.containers import Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static

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

        # Define essential commands
        self.commands: List[Dict[str, Any]] = [
            {
                "value": "session-list",
                "title": "Open Session List",
                "description": "View and navigate sessions",
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
                "value": "quit",
                "title": "Quit",
                "description": "Exit the TUI application",
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

    def filter_commands(self, query: str) -> None:
        """Filter commands by search query.

        Args:
            query: Search string to filter commands by.
        """
        query = query.lower()

        if not query:
            self.filtered_commands = list(self.commands)
        else:
            self.filtered_commands = [
                cmd
                for cmd in self.commands
                if query in cmd.get("title", "").lower()
                or query in cmd.get("description", "").lower()
            ]

        self._selected_index = 0
        self._render_content()

    def select_command(self, value: str) -> Optional[str]:
        """Select a command by value.

        Args:
            value: Command value to select.

        Returns:
            The selected command value, or None if not found.
        """
        for idx, command in enumerate(self.filtered_commands):
            if command.get("value") == value:
                self._selected_index = idx
                return value
        return None

    def close_dialog(self, value: Optional[str] = None) -> None:
        """Close dialog and return selected value.

        Args:
            value: Selected command value (defaults to current selection).
        """
        if value is None:
            if self.filtered_commands and self._selected_index < len(
                self.filtered_commands
            ):
                value = self.filtered_commands[self._selected_index].get("value")

        self._result = value
        self._closed = True
        self.dismiss()

    def get_result(self) -> Optional[str]:
        """Get dialog result.

        Returns:
            Selected command value or None.
        """
        return self._result

    def is_closed(self) -> bool:
        """Check if dialog was closed.

        Returns:
            True if dialog was closed.
        """
        return self._closed

    def action_enter(self) -> None:
        """Handle Enter key - execute selected command and close."""
        if self.filtered_commands and self._selected_index < len(self.filtered_commands):
            command = self.filtered_commands[self._selected_index]
            value = command.get("value")

            if self.on_command:
                self.on_command(value)  # type: ignore[arg-type]

            self.close_dialog(value)

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
