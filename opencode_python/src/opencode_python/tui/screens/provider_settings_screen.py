"""Provider settings screen for managing providers"""
from typing import List
import logging

from textual.screen import Screen
from textual.containers import Vertical
from textual.widgets import DataTable, Button, Static
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from opencode_python.providers_mgmt import Provider, ProvidersStorage
from opencode_python.tui.dialogs.provider_edit_dialog import ProviderEditDialog


logger = logging.getLogger(__name__)


class ProviderSettingsScreen(Screen):
    """Provider settings screen for managing providers"""

    BINDINGS = [
        ("escape", "pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
        ("a", "add_provider", "Add"),
        ("e", "edit_provider", "Edit"),
        ("d", "delete_provider", "Delete"),
        ("t", "test_connection", "Test"),
        ("enter", "view_accounts", "Accounts"),
    ]

    def __init__(self, storage: ProvidersStorage, **kwargs):
        """Initialize ProviderSettingsScreen with storage"""
        super().__init__(**kwargs)
        self.storage = storage
        self.providers: List[Provider] = []

    def compose(self) -> ComposeResult:
        """Build the provider settings screen UI"""
        with Vertical(id="provider-settings-screen"):
            yield Static("Providers", id="title")
            yield DataTable(id="provider-table")
            yield Vertical(
                Button("Add Provider (A)", id="btn-add", variant="primary"),
                Button("Edit (E)", id="btn-edit", variant="default"),
                Button("Delete (D)", id="btn-delete", variant="error"),
                Button("Test Connection (T)", id="btn-test", variant="default"),
                Button("View Accounts (Enter)", id="btn-accounts", variant="default"),
                id="button-row"
            )
            yield Footer()

    async def on_mount(self) -> None:
        """Called when screen is mounted - populate DataTable"""
        await self._load_providers()

    async def _load_providers(self) -> None:
        """Load providers from storage and populate DataTable"""
        self.providers = await self.storage.list_providers()
        data_table = self.query_one(DataTable)

        data_table.clear(columns=True)
        data_table.clear()

        data_table.add_column("ID", width=15)
        data_table.add_column("Name", width=20)
        data_table.add_column("Base URL", width=30)
        data_table.add_column("Models", width=10)

        for provider in self.providers:
            data_table.add_row(
                provider.id,
                provider.name,
                provider.base_url,
                str(len(provider.models)),
                key=provider.id,
            )

        # Set cursor type to row for better selection
        data_table.cursor_type = "row"

    def _get_selected_provider_id(self) -> str | None:
        """Get selected provider ID from DataTable"""
        try:
            data_table = self.query_one(DataTable)
            cursor_coordinate = data_table.cursor_coordinate
            if len(self.providers) == 0:
                return None
            row_key, _ = data_table.coordinate_to_cell_key(cursor_coordinate)
            if row_key is not None:
                return str(row_key)
            return None
        except Exception:
            return None

    async def action_add_provider(self) -> None:
        """Handle 'a' key - Add new provider"""
        async def on_save(provider: Provider | None):
            if provider:
                await self.storage.create_provider(provider)
                await self._load_providers()

        self.app.push_screen(ProviderEditDialog(on_save=on_save))

    async def action_edit_provider(self) -> None:
        """Handle 'e' key - Edit selected provider"""
        provider_id = self._get_selected_provider_id()
        if not provider_id:
            logger.warning("No provider selected")
            return

        provider = await self.storage.get_provider(provider_id)
        if not provider:
            logger.warning(f"Provider not found: {provider_id}")
            return

        async def on_save(updated_provider: Provider | None):
            if updated_provider:
                await self.storage.update_provider(updated_provider)
                await self._load_providers()

        self.app.push_screen(ProviderEditDialog(provider=provider, on_save=on_save))

    async def action_delete_provider(self) -> None:
        """Handle 'd' key - Delete selected provider"""
        provider_id = self._get_selected_provider_id()
        if not provider_id:
            logger.warning("No provider selected")
            return

        success = await self.storage.delete_provider(provider_id)
        if success:
            logger.info(f"Provider deleted: {provider_id}")
            await self._load_providers()
        else:
            logger.warning(f"Failed to delete provider: {provider_id}")

    def action_test_connection(self) -> None:
        """Handle 't' key - Test connection to selected provider"""
        provider_id = self._get_selected_provider_id()
        if not provider_id:
            logger.warning("No provider selected")
            return

        logger.info(f"Testing connection to provider: {provider_id}")
        result = await self.storage.test_provider_connection(provider_id)

        if result.success:
            self.app.notify(f"Connection successful: {result.message}", severity="information")
        else:
            self.app.notify(f"Connection failed: {result.message}", severity="error")

    async def action_view_accounts(self) -> None:
        """Handle Enter key - View accounts for selected provider"""
        provider_id = self._get_selected_provider_id()
        if not provider_id:
            logger.warning("No provider selected")
            return

        provider = await self.storage.get_provider(provider_id)
        if not provider:
            logger.warning(f"Provider not found: {provider_id}")
            return

        from opencode_python.tui.screens.account_settings_screen import AccountSettingsScreen
        self.app.push_screen(AccountSettingsScreen(storage=self.storage, provider=provider))
