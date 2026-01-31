"""Dialog system for TUI using Textual ModalScreen."""

from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, TypeVar

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static, Input, DataTable, Footer

from opencode_python.core.settings import Settings, get_settings

T = TypeVar("T")

from .model_select_dialog import ModelSelectDialog


class BaseDialog(ModalScreen[T]):
    """Base dialog class extending Textual ModalScreen.

    Args:
        title: Dialog title to display.
        body: Widget content for the dialog body.
    """

    DEFAULT_CSS = """
    BaseDialog {
        height: auto;
        width: 80;
        align: center top;
        border: thick panel;
        padding: 1;
    }
    """

    def __init__(
        self,
        title: str = "",
        body: Optional[ComposeResult] = None,
    ) -> None:
        """Initialize base dialog."""
        super().__init__()
        self.title = title
        self.body_content = body
        self._result: Optional[T] = None
        self._closed = False

    def compose(self) -> ComposeResult:
        """Compose dialog widgets."""
        if self.title:
            yield Label(self.title)

        if self.body_content:
            yield from self.body_content

        yield Vertical()

    async def on_mount(self) -> None:
        """Called when dialog is mounted."""
        pass

    def close_dialog(self, result: str = "") -> None:
        """Close dialog and return result.

        Args:
            result: Value to return from dialog.
        """
        self._result = result
        self._closed = True
        self.dismiss()

    def get_result(self) -> Optional[T]:
        """Get dialog result.

        Returns:
            Dialog result or None if not closed.
        """
        return self._result

    def is_closed(self) -> bool:
        """Check if dialog was closed.

        Returns:
            True if dialog was closed.
        """
        return self._closed


class SelectDialog(ModalScreen[T]):
    """Selection dialog for choosing from options.

    Args:
        title: Dialog title.
        options: List of option dictionaries with value and title.
        placeholder: Placeholder text for search/filter.
        on_select: Callback when option is selected.
    """

    DEFAULT_CSS = """
    SelectDialog {
        height: auto;
        width: 80;
        align: center top;
        border: thick panel;
        padding: 1;
    }

    SelectDialog > Vertical {
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

    def __init__(
        self,
        title: str,
        options: List[Dict[str, Any]],
        placeholder: str = "Search...",
        on_select: Optional[Callable[[T], None]] = None,
    ):
        super().__init__()
        self.title = title
        self.options = options
        self.placeholder = placeholder
        self.on_select = on_select
        self._result: Optional[T] = None
        self._selected_index: int = 0

    def compose(self) -> ComposeResult:
        """Compose select dialog widgets."""
        if self.title:
            yield Label(self.title)

        yield Input(placeholder=self.placeholder, id="select_filter")

        yield ListView(id="select_list")
        for option in self.options:
            yield ListItem(
                Static(option.get("title", str(option.get("value", ""))))
            )

        yield Static("Press Enter to select, Escape to cancel")

    async def on_mount(self) -> None:
        """Called when dialog is mounted."""
        list_view = self.query_one(ListView)
        list_view.focus()
        list_view.index = 0

    def select_option(self, value: T) -> None:
        """Select an option by value.

        Args:
            value: Option value to select.
        """
        for idx, option in enumerate(self.options):
            if option.get("value") == value:
                self._selected_index = idx
                self._result = value
                try:
                    list_view = self.query_one(ListView)
                    if list_view.index != idx:
                        list_view.index = idx
                except Exception:
                    pass
                return

    def close_dialog(self, value: Optional[T] = None) -> None:
        """Close dialog and return selected value.

        Args:
            value: Selected value (defaults to first option or None).
        """
        if value is None:
            if self.options and self._selected_index < len(self.options):
                value = self.options[self._selected_index].get("value")
        self._result = value
        self.dismiss()

    def get_result(self) -> Optional[T]:
        """Get dialog result.

        Returns:
            Selected value or None.
        """
        return self._result

    def action_enter(self) -> None:
        """Handle Enter key - select current option and close."""
        if self.options and self._selected_index < len(self.options):
            value = self.options[self._selected_index].get("value")
            if self.on_select:
                self.on_select(value)  # type: ignore[arg-type]
        self.close_dialog(value)

    def action_escape(self) -> None:
        """Handle Escape key - close without selection."""
        super().close_dialog(None)


class ConfirmDialog(BaseDialog[bool]):
    """Confirmation dialog with confirm/cancel buttons.

    Args:
        title: Dialog title.
        message: Confirmation message.
        on_confirm: Callback when confirmed.
        on_cancel: Callback when cancelled.
    """

    DEFAULT_CSS = """
    ConfirmDialog {
        height: auto;
        width: 80;
        align: center top;
        border: thick panel;
        padding: 1;
    }

    ConfirmDialog > Vertical {
        height: auto;
        width: 100%;
    }

    Button.-confirm {
        margin-right: 1;
    }
    """

    def __init__(
        self,
        title: str,
        message: str = "",
        on_confirm: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
    ):
        super().__init__(title=title)
        self.message = message
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self._result = False

    def compose(self) -> ComposeResult:
        """Compose confirmation dialog widgets."""
        yield Vertical()

        if self.title:
            yield Label(self.title)

        if self.message:
            yield Static(self.message)

        yield Horizontal(
            Button("Cancel", id="btn_cancel", variant="default"),
            Button("Confirm", id="btn_confirm", variant="success"),
            id="confirm_buttons"
        )

        yield Vertical()  # End Vertical container

    async def on_mount(self) -> None:
        """Called when dialog is mounted."""
        buttons = self.query_one("#confirm_buttons", Horizontal)
        first_button = buttons.query_one(Button)
        first_button.focus()

    def action_enter(self) -> None:
        """Handle Enter key - default to confirm."""
        self.action_confirm()

    def action_confirm(self) -> None:
        """Handle confirm action."""
        if self.on_confirm:
            self.on_confirm()
        self._result = True
        self.dismiss()

    def action_cancel(self) -> None:
        """Handle cancel action."""
        if self.on_cancel:
            self.on_cancel()
        self._result = False
        self.dismiss()

    def action_escape(self) -> None:
        """Handle Escape key - cancel."""
        self.action_cancel()

    def get_result(self) -> bool:
        """Get dialog result.

        Returns:
            True if confirmed, False if cancelled.
        """
        return self._result


class PromptDialog(ModalScreen[str]):
    """Text input prompt dialog.

    Args:
        title: Dialog title.
        placeholder: Placeholder text for input.
        on_submit: Callback when form is submitted.
    """

    DEFAULT_CSS = """
    PromptDialog {
        height: auto;
        width: 80;
        align: center top;
        border: thick panel;
        padding: 1;
    }

    PromptDialog > Vertical {
        height: auto;
        width: 100%;
    }

    TextInput {
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        title: str,
        placeholder: str = "",
        initial_value: str = "",
        on_submit: Optional[Callable[[str], None]] = None,
    ):
        super().__init__()
        self.title = title
        self.placeholder = placeholder
        self.initial_value = initial_value
        self.on_submit = on_submit
        self._result: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose prompt dialog widgets."""
        yield Vertical()

        if self.title:
            yield Label(self.title)

        yield Input(
            placeholder=self.placeholder,
            value=self.initial_value,
            id="prompt_input"
        )

        yield Static("Press Enter to submit, Escape to cancel")

        yield Vertical()  # End Vertical container

    async def on_mount(self) -> None:
        """Called when dialog is mounted."""
        input_field = self.query_one("#prompt_input", Input)
        input_field.focus()
        input_field.value = self.initial_value

    def action_enter(self) -> None:
        """Handle Enter key - submit input."""
        input_field = self.query_one("#prompt_input", Input)
        value = input_field.value
        if self.on_submit:
            self.on_submit(value)
        self._result = value
        self.dismiss()

    def action_escape(self) -> None:
        """Handle Escape key - cancel."""
        self._result = ""
        self.dismiss()

    def get_result(self) -> Optional[str]:
        """Get dialog result.

        Returns:
            Input value or empty string if cancelled.
        """
        return self._result


from .model_select_dialog import ModelSelectDialog
from .theme_select_dialog import ThemeSelectDialog
from .command_palette_dialog import CommandPaletteDialog
