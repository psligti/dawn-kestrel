"""TUI I/O handlers using Textual.

This module provides concrete implementations of I/O handler protocols
specifically designed for TUI applications using Textual framework.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Input, DataTable, Static, Button, OptionList
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.containers import Container

from opencode_python.interfaces.io import (
    IOHandler,
    ProgressHandler,
    NotificationHandler,
    Notification,
    NotificationType,
)


class TUIIOHandler(IOHandler):
    """Textual-based I/O handler for TUI applications.

    This implementation uses Textual widgets for user interaction
    in terminal user interfaces.
    """

    def __init__(self, app: App) -> None:
        """Initialize TUI I/O handler.

        Args:
            app: Textual App instance for widget access.
        """
        self.app = app

    async def prompt(self, message: str, default: str | None = None) -> str:
        """Prompt user for text input via modal dialog."""
        result = await self.app.push_screen(self.PromptModal(message, default))
        return result or default or ""

    class PromptModal(ModalScreen[str]):
        """Modal dialog for user input."""

        BINDINGS = [("escape", "dismiss", "Close")]

        def __init__(self, message: str, default: str | None = None) -> None:
            super().__init__()
            self._message = message
            self._default = default

        def compose(self) -> ComposeResult:
            with Container(classes="panel prompt-modal"):
                yield Static(self._message, classes="legend-header title")
                yield Input(value=self._default, placeholder="Enter text...", id="prompt_input", classes="control")

        def on_mount(self) -> None:
            self.query_one("#prompt_input", Input).focus()

        def on_input_submitted(self, event: Input.Submitted) -> None:
            self.dismiss(event.value)

        def on_button_pressed(self, event: Button.Pressed) -> None:
            input_widget = self.query_one("#prompt_input", Input)
            if input_widget.value:
                self.dismiss(input_widget.value)

    async def confirm(self, message: str, default: bool = False) -> bool:
        """Ask user for yes/no confirmation.

        Args:
            message: The confirmation message.
            default: Default value if user provides no input.

        Returns:
            True if confirmed, False otherwise.
        """
        result = await self.app.push_screen(self.ConfirmModal(message, default))
        return result

    class ConfirmModal(ModalScreen[bool]):
        """Modal dialog for yes/no confirmation."""

        BINDINGS = [("escape", "dismiss_default", "Close")]

        def __init__(self, message: str, default: bool = False) -> None:
            super().__init__()
            self._message = message
            self._default = default

        def compose(self) -> ComposeResult:
            with Container(classes="panel confirm-modal"):
                yield Static(self._message, classes="legend-header title")
                with Horizontal(classes="button-row"):
                    yield Button("Yes", id="yes", variant="primary")
                    yield Button("No", id="no")

        def on_mount(self) -> None:
            self.query_one("#yes" if self._default else "#no", Button).focus()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "yes":
                self.dismiss(True)
            elif event.button.id == "no":
                self.dismiss(False)

        def action_dismiss_default(self) -> None:
            """Handle escape key to dismiss with default value."""
            self.dismiss(self._default)

    async def select(self, message: str, options: list[str]) -> str:
        """Prompt user to select from a numbered list.

        Args:
            message: The prompt message.
            options: List of available options.

        Returns:
            The selected option string.
        """
        if not options:
            raise ValueError("Options list cannot be empty")
        result = await self.app.push_screen(self.SelectModal(message, options))
        return result or options[0]

    class SelectModal(ModalScreen[str]):
        """Modal dialog for selecting from a numbered list."""

        BINDINGS = [("escape", "dismiss_first", "Close")]

        def __init__(self, message: str, options: list[str]) -> None:
            super().__init__()
            self._message = message
            self._options = options
            self._option_mapping: dict[str, str] = {}  # Maps option index to original option

        def compose(self) -> ComposeResult:
            with Container(classes="panel select-modal"):
                yield Static(self._message, classes="legend-header title")
                yield OptionList(id="select_list", classes="control")

        def on_mount(self) -> None:
            option_list = self.query_one("#select_list", OptionList)
            option_list.focus()
            if self._options:
                option_list.highlighted = 0
                for idx, option in enumerate(self._options):
                    display_text = f"{idx + 1}. {option}"
                    option_list.add_option(display_text, id=str(idx))

        def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
            """Handle option selection."""
            option_index = event.option_index
            if 0 <= option_index < len(self._options):
                selected_option = self._options[option_index]
                self.dismiss(selected_option)

        def action_dismiss_first(self) -> None:
            """Handle escape key to dismiss with first option."""
            if self._options:
                self.dismiss(self._options[0])

    class MultiSelectModal(ModalScreen[list[str]]):
        """Modal dialog for selecting multiple options."""

        BINDINGS = [
            ("escape", "dismiss_empty", "Cancel"),
            ("enter", "confirm", "Confirm"),
        ]

        def __init__(self, message: str, options: list[str]) -> None:
            super().__init__()
            self._message = message
            self._options = options
            self._option_mapping: dict[str, str] = {}  # Maps option index to original option

        def compose(self) -> ComposeResult:
            with Container(classes="panel multi-select-modal"):
                yield Static(self._message, classes="legend-header title")
                yield OptionList(id="multi_select_list", classes="control")

        def on_mount(self) -> None:
            option_list = self.query_one("#multi_select_list", OptionList)
            option_list.focus()
            if self._options:
                for idx, option in enumerate(self._options):
                    display_text = f"{idx + 1}. {option}"
                    option_list.add_option(display_text, id=str(idx))

        def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
            """Handle option selection - toggle selection on Space key."""
            option_index = event.option_index
            if 0 <= option_index < len(self._options):
                option_list = self.query_one("#multi_select_list", OptionList)
                if not option_list.selected:
                    option_list.select_index(option_index)

        def action_confirm(self) -> None:
            """Handle Enter key to confirm selections."""
            option_list = self.query_one("#multi_select_list", OptionList)
            selected_indices = option_list.selected
            selected_options = [self._options[idx] for idx in selected_indices]
            self.dismiss(selected_options)

        def action_dismiss_empty(self) -> None:
            """Handle escape key to dismiss with empty list."""
            self.dismiss([])

    async def multi_select(self, message: str, options: list[str]) -> list[str]:
        """Prompt user to select multiple options.

        Args:
            message: The prompt message.
            options: List of available options.

        Returns:
            List of selected option strings.
        """
        if not options:
            raise ValueError("Options list cannot be empty")
        result = await self.app.push_screen(self.MultiSelectModal(message, options))
        return result or []


class TUINotificationHandler(NotificationHandler):
    """Textual-based notification handler for TUI applications.

    This implementation uses Textual's app.notify() method for
    displaying notifications to the user.
    """

    def __init__(self, app: App) -> None:
        """Initialize TUI notification handler.

        Args:
            app: Textual App instance for notify() method.
        """
        self.app = app

    def show(self, notification: Notification) -> None:
        """Display a notification using Textual's notify.

        Args:
            notification: The Notification object to display.
        """
        severity_map = {
            NotificationType.INFO: "information",
            NotificationType.SUCCESS: "information",
            NotificationType.WARNING: "warning",
            NotificationType.ERROR: "error",
            NotificationType.DEBUG: "information",
        }

        severity = severity_map.get(notification.notification_type, "information")

        self.app.notify(
            message=notification.message,
            severity=severity,
            title=notification.details.get("title") if notification.details else None,
        )


class TUIProgressHandler(ProgressHandler):
    """Textual-based progress handler for TUI applications.

    This implementation can display progress using Textual widgets
    like ProgressBar or status widgets.
    """

    def __init__(self, app: App) -> None:
        """Initialize TUI progress handler.

        Args:
            app: Textual App instance for widget access.
        """
        self.app = app
        self._total: int = 0

    def start(self, operation: str, total: int) -> None:
        """Start a new progress operation.

        Args:
            operation: Description of operation.
            total: Total number of steps.
        """
        self._total = total
        self.app.notify(
            message=f"{operation} started",
            severity="information",
            timeout=2,
        )

    def update(self, current: int, message: str | None = None) -> None:
        """Update progress for current operation.

        Args:
            current: Current progress value.
            message: Optional status message.
        """
        pass

    def complete(self, message: str | None = None) -> None:
        """Mark current operation as complete.

        Args:
            message: Optional completion message.
        """
        completion_msg = message or "Complete"
        self.app.notify(
            message=completion_msg,
            severity="information",
            timeout=2,
        )
