"""Account edit dialog for adding/editing accounts"""
from typing import Optional, Callable
import logging
from uuid import uuid4

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Input, Label, Button, TextArea, Password
from textual.binding import Binding

from opencode_python.providers_mgmt import Account, hash_api_key


logger = logging.getLogger(__name__)


class AccountEditDialog(ModalScreen[Optional[Account]]):
    """Dialog for adding or editing an account"""

    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
        ("enter", "save", "Save"),
    ]

    def __init__(
        self,
        provider_id: str,
        account: Optional[Account] = None,
        on_save: Optional[Callable[[Optional[Account]], None]] = None,
    ):
        """Initialize account edit dialog

        Args:
            provider_id: Provider ID for this account
            account: Account to edit (None for new account)
            on_save: Callback when account is saved
        """
        super().__init__()
        self.provider_id = provider_id
        self.account = account
        self.on_save = on_save
        self._is_editing = account is not None

        if account:
            self.id_value = account.id
            self.name_value = account.name
            self.description_value = account.description or ""
            self.is_active_value = account.is_active
            self.original_api_key_hash = account.api_key_hash
            self.api_key_value = ""
        else:
            self.id_value = str(uuid4())[:8]
            self.name_value = ""
            self.description_value = ""
            self.is_active_value = False
            self.original_api_key_hash = None
            self.api_key_value = ""

    def compose(self) -> ComposeResult:
        """Compose account edit dialog widgets"""
        if self._is_editing:
            yield Label("Edit Account", id="title")
        else:
            yield Label("Add Account", id="title")

        yield Label("ID (auto-generated):")
        yield Input(placeholder="Account ID", id="input-id", value=self.id_value, disabled=True)

        yield Label("Name:")
        yield Input(placeholder="e.g., Personal", id="input-name", value=self.name_value)

        yield Label("API Key:")
        if self._is_editing:
            yield Password(placeholder="Enter new API key (or leave empty to keep existing)", id="input-api-key", password=False)
            yield Label("(Leave empty to keep existing API key)", id="api-key-hint")
        else:
            yield Password(placeholder="Enter API key", id="input-api-key")

        yield Label("Description (optional):")
        yield TextArea(placeholder="Account description", id="input-description", value=self.description_value)

        yield Label("Active Account:")
        yield Vertical(
            Button("Yes", id="btn-active-yes", variant="primary" if self.is_active_value else "default"),
            Button("No", id="btn-active-no", variant="primary" if not self.is_active_value else "default"),
            id="active-button-row"
        )

        yield Vertical(
            Button("Save (Enter)", id="btn-save", variant="primary"),
            Button("Cancel (Esc)", id="btn-cancel", variant="default"),
            id="button-row"
        )

    def action_save(self) -> None:
        """Handle Enter key - Save account"""
        try:
            name_input = self.query_one("#input-name", Input)
            api_key_input = self.query_one("#input-api-key", Password)
            description_input = self.query_one("#input-description", TextArea)

            name = name_input.value.strip()
            api_key = api_key_input.value.strip()
            description = description_input.text.strip()

            if not name:
                self.app.notify("Name is required", severity="error")
                return

            if self._is_editing and not api_key:
                api_key_hash = self.original_api_key_hash
            else:
                if not api_key:
                    self.app.notify("API Key is required for new account", severity="error")
                    return
                api_key_hash = hash_api_key(api_key)

            account = Account(
                id=self.id_value,
                provider_id=self.provider_id,
                name=name,
                api_key_hash=api_key_hash,
                is_active=self.is_active_value,
                description=description if description else None,
            )

            if self.on_save:
                self.on_save(account)

            self.dismiss(account)

        except Exception as e:
            logger.error(f"Error saving account: {e}")
            self.app.notify(f"Error: {str(e)}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-active-yes":
            self.is_active_value = True
            self._refresh_active_buttons()
        elif event.button.id == "btn-active-no":
            self.is_active_value = False
            self._refresh_active_buttons()

    def _refresh_active_buttons(self) -> None:
        """Refresh active account button variants"""
        try:
            yes_btn = self.query_one("#btn-active-yes", Button)
            no_btn = self.query_one("#btn-active-no", Button)

            yes_btn.variant = "primary" if self.is_active_value else "default"
            no_btn.variant = "primary" if not self.is_active_value else "default"
        except Exception:
            pass
