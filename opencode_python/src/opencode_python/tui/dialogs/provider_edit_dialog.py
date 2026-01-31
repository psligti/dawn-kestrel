"""Provider edit dialog for adding/editing providers"""
from typing import Optional, Callable
import logging
from uuid import uuid4

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Input, Label, Button, TextArea, Footer
from textual.binding import Binding

from opencode_python.providers_mgmt import Provider


logger = logging.getLogger(__name__)


class ProviderEditDialog(ModalScreen[Optional[Provider]]):
    """Dialog for adding or editing a provider"""

    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
        ("enter", "save", "Save"),
    ]

    def __init__(
        self,
        provider: Optional[Provider] = None,
        on_save: Optional[Callable[[Optional[Provider]], None]] = None,
    ):
        """Initialize provider edit dialog

        Args:
            provider: Provider to edit (None for new provider)
            on_save: Callback when provider is saved
        """
        super().__init__()
        self.provider = provider
        self.on_save = on_save
        self._is_editing = provider is not None

        if provider:
            self.id_value = provider.id
            self.name_value = provider.name
            self.base_url_value = provider.base_url
            self.models_value = ",".join(provider.models)
            self.description_value = provider.description or ""
        else:
            self.id_value = str(uuid4())[:8]
            self.name_value = ""
            self.base_url_value = ""
            self.models_value = ""
            self.description_value = ""

    def compose(self) -> ComposeResult:
        """Compose provider edit dialog widgets"""
        if self._is_editing:
            yield Label("Edit Provider", id="title")
        else:
            yield Label("Add Provider", id="title")

        yield Label("ID (auto-generated):")
        yield Input(placeholder="Provider ID", id="input-id", value=self.id_value, disabled=True)

        yield Label("Name:")
        yield Input(placeholder="e.g., OpenAI", id="input-name", value=self.name_value)

        yield Label("Base URL:")
        yield Input(placeholder="e.g., https://api.openai.com/v1", id="input-base-url", value=self.base_url_value)

        yield Label("Models (comma-separated):")
        yield TextArea(placeholder="e.g., gpt-4,gpt-3.5-turbo", id="input-models", text=self.models_value)

        yield Label("Description (optional):")
        yield TextArea(placeholder="Provider description", id="input-description", text=self.description_value)

        yield Vertical(
            Button("Save (Enter)", id="btn-save", variant="primary"),
            Button("Cancel (Esc)", id="btn-cancel", variant="default"),
            id="button-row"
        )
        yield Footer()

    def action_save(self) -> None:
        """Handle Enter key - Save provider"""
        try:
            name_input = self.query_one("#input-name", Input)
            base_url_input = self.query_one("#input-base-url", Input)
            models_input = self.query_one("#input-models", TextArea)
            description_input = self.query_one("#input-description", TextArea)

            name = name_input.value.strip()
            base_url = base_url_input.value.strip()
            models_text = models_input.text.strip()
            description = description_input.text.strip()

            if not name:
                self.app.notify("Name is required", severity="error")
                return

            if not base_url:
                self.app.notify("Base URL is required", severity="error")
                return

            if not models_text:
                self.app.notify("At least one model is required", severity="error")
                return

            models = [m.strip() for m in models_text.split(",") if m.strip()]
            if not models:
                self.app.notify("At least one model is required", severity="error")
                return

            provider = Provider(
                id=self.id_value,
                name=name,
                base_url=base_url,
                models=models,
                description=description if description else None,
            )

            if self.on_save:
                self.on_save(provider)

            self.dismiss(provider)

        except Exception as e:
            logger.error(f"Error saving provider: {e}")
            self.app.notify(f"Error: {str(e)}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.dismiss(None)
