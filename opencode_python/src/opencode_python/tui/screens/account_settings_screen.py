"""Account settings screen for managing accounts"""
from typing import List
import logging

from textual.screen import Screen
from textual.containers import Vertical
from textual.widgets import DataTable, Button, Static
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from opencode_python.providers_mgmt import Provider, Account, ProvidersStorage
from opencode_python.tui.dialogs.account_edit_dialog import AccountEditDialog


logger = logging.getLogger(__name__)


class AccountSettingsScreen(Screen):
    """Account settings screen for managing accounts"""

    BINDINGS = [
        ("escape", "pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
        ("a", "add_account", "Add"),
        ("e", "edit_account", "Edit"),
        ("d", "delete_account", "Delete"),
        ("s", "set_active", "Set Active"),
    ]

    def __init__(self, storage: ProvidersStorage, provider: Provider, **kwargs):
        """Initialize AccountSettingsScreen with storage and provider"""
        super().__init__(**kwargs)
        self.storage = storage
        self.provider = provider
        self.accounts: List[Account] = []

    def compose(self) -> ComposeResult:
        """Build the account settings screen UI"""
        with Vertical(id="account-settings-screen"):
            yield Static(f"Accounts for {self.provider.name}", id="title")
            yield DataTable(id="account-table")
            yield Vertical(
                Button("Add Account (A)", id="btn-add", variant="primary"),
                Button("Edit (E)", id="btn-edit", variant="default"),
                Button("Delete (D)", id="btn-delete", variant="error"),
                Button("Set Active (S)", id="btn-set-active", variant="default"),
                id="button-row"
            )
            yield Footer()

    async def on_mount(self) -> None:
        """Called when screen is mounted - populate DataTable"""
        await self._load_accounts()

    async def _load_accounts(self) -> None:
        """Load accounts from storage and populate DataTable"""
        self.accounts = await self.storage.list_accounts(self.provider.id)
        data_table = self.query_one(DataTable)

        data_table.clear(columns=True)
        data_table.clear()

        data_table.add_column("ID", width=15)
        data_table.add_column("Name", width=20)
        data_table.add_column("Active", width=8)
        data_table.add_column("API Key", width=25)

        for account in self.accounts:
            active_marker = "✓" if account.is_active else " "
            masked_key = account.api_key_hash[:8] + "..." if len(account.api_key_hash) > 8 else "***"

            data_table.add_row(
                account.id,
                account.name,
                active_marker,
                masked_key,
                key=account.id,
            )

        data_table.cursor_type = "row"

    def _get_selected_account_id(self) -> str | None:
        """Get selected account ID from DataTable"""
        try:
            data_table = self.query_one(DataTable)
            cursor_coordinate = data_table.cursor_coordinate
            if len(self.accounts) == 0:
                return None
            row_key, _ = data_table.coordinate_to_cell_key(cursor_coordinate)
            if row_key is not None:
                return str(row_key)
            return None
        except Exception:
            return None

    async def action_add_account(self) -> None:
        """Handle 'a' key - Add new account"""
        async def on_save(account: Account | None):
            if account:
                await self.storage.create_account(account)
                await self._load_accounts()

        self.app.push_screen(AccountEditDialog(provider_id=self.provider.id, on_save=on_save))

    async def action_edit_account(self) -> None:
        """Handle 'e' key - Edit selected account"""
        account_id = self._get_selected_account_id()
        if not account_id:
            logger.warning("No account selected")
            return

        account = await self.storage.get_account(account_id, self.provider.id)
        if not account:
            logger.warning(f"Account not found: {account_id}")
            return

        async def on_save(updated_account: Account | None):
            if updated_account:
                await self.storage.update_account(updated_account)
                await self._load_accounts()

        self.app.push_screen(
            AccountEditDialog(
                provider_id=self.provider.id,
                account=account,
                on_save=on_save
            )
        )

    async def action_delete_account(self) -> None:
        """Handle 'd' key - Delete selected account"""
        account_id = self._get_selected_account_id()
        if not account_id:
            logger.warning("No account selected")
            return

        success = await self.storage.delete_account(account_id, self.provider.id)
        if success:
            logger.info(f"Account deleted: {account_id}")
            await self._load_accounts()
        else:
            logger.warning(f"Failed to delete account: {account_id}")

    async def action_set_active(self) -> None:
        """Handle 's' key - Set selected account as active"""
        account_id = self._get_selected_account_id()
        if not account_id:
            logger.warning("No account selected")
            return

        account = await self.storage.set_active_account(account_id, self.provider.id)
        if account:
            logger.info(f"Account set as active: {account_id}")
            self.app.notify(f"Account {account.name} set as active", severity="information")
            await self._load_accounts()
        else:
            logger.warning(f"Failed to set account as active: {account_id}")
            self.app.notify("Failed to set account as active", severity="error")
