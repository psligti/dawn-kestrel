"""Keybinding editor screen for customizing keybindings."""

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
    DataTable,
)
from textual.containers import Vertical, Horizontal

from opencode_python.tui.keybindings import (
    KeybindingManager,
    get_keybinding_manager,
)


class KeybindingEditorScreen(ModalScreen[dict]):
    """Keybinding editor screen for customizing keybindings.

    Provides:
    - List of all keybindings
    - Rebind functionality
    - Conflict detection
    - Restore defaults option
    """

    DEFAULT_CSS = """
    KeybindingEditorScreen {
        height: auto;
        width: 120;
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

    DataTable {
        height: 20;
    }

    .conflict-warning {
        color: $warning;
        text-style: bold;
    }

    .help-text {
        text-style: dim italic;
        margin-top: 1;
    }

    Button {
        margin-left: 1;
    }

    #keybinding_table {
        border: thick $border;
    }
    """

    def __init__(
        self,
        on_apply: Optional[Callable[[dict], None]] = None,
    ):
        """Initialize keybinding editor screen.

        Args:
            on_apply: Callback when keybindings are applied.
        """
        super().__init__()
        self.on_apply = on_apply
        self._result: Optional[dict] = None
        self._manager: Optional[KeybindingManager] = None
        self._selected_action: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose keybinding editor screen widgets."""
        yield Label("Keybindings", classes="section-title")

        yield DataTable(id="keybinding_table")
        yield Static("", id="conflict_text", classes="conflict-warning")

        yield Static("Press Enter to rebind, Escape to cancel", classes="help-text")

        with Horizontal(id="button_bar"):
            yield Button("Restore Defaults", variant="default", id="restore_button")
            yield Button("Done", variant="primary", id="done_button")

    async def on_mount(self) -> None:
        """Called when screen is mounted."""
        self._manager = get_keybinding_manager()

        table = self.query_one("#keybinding_table", DataTable)

        table.add_column("Action", width=30)
        table.add_column("Key", width=20)
        table.add_column("Default", width=20)
        table.add_column("Description", width=40)

        for entry in self._manager.get_entries():
            table.add_row(
                entry.action,
                entry.key,
                entry.key if entry.default else "",
                entry.description,
                    key=entry.action,
                )

            conflict_text = self.query_one("#conflict_text", Static)
            conflict_text = self.query_one("#conflict_text", Static)
            conflict_text.update("")

            self.notify(
                f"[green]Rebound {self._selected_action} to {new_key}[/green]"
            )

    def _restore_defaults(self) -> None:
        """Restore all keybindings to defaults."""
        from textual.screen import ModalScreen
        from textual.widgets import Label, Button
        from textual.containers import Vertical, Horizontal

        class ConfirmRestore(ModalScreen[bool]):
            def compose(self) -> ComposeResult:
                yield Label("Restore Defaults")
                yield Label("Are you sure you want to restore default keybindings?")
                with Horizontal():
                    yield Button("Yes", variant="error", id="yes_btn")
                    yield Button("No", variant="primary", id="no_btn")

            def on_button_pressed(self, event: Button.Pressed) -> None:
                if event.button.id == "yes_btn":
                    self.dismiss(True)
                else:
                    self.dismiss(False)

        self.push_screen(ConfirmRestore(), callback=self._on_restore_confirmed)

    def _on_restore_confirmed(self, confirmed: bool) -> None:
        """Handle restore defaults confirmation.

        Args:
            confirmed: Whether user confirmed restoration.
        """
        if confirmed:
            self._manager.restore_defaults()

            table = self.query_one("#keybinding_table", DataTable)
            table.clear()

            for entry in self._manager.get_entries():
                table.add_row(
                    entry.action,
                    entry.key,
                    entry.key if entry.default else "",
                    entry.description,
                    key=entry.action,
                )

            # Clear conflict warning
            conflict_text = self.query_one("#conflict_text", Static)
            conflict_text.update("")

            self.notify("[green]Restored default keybindings[/green]")
