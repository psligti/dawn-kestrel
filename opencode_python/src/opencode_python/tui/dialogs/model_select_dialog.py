"""Model selection dialog for TUI using ModelInfo objects."""

from typing import Any, Dict, List, Optional, Callable

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import ListView, ListItem, Static, Label

from opencode_python.providers.base import ModelInfo
from opencode_python.core.settings import settings


class ModelSelectDialog(ModalScreen[ModelInfo]):
    """Dialog for selecting AI models from available providers.

    Args:
        title: Dialog title.
        models: List of ModelInfo objects to display.
        on_select: Optional callback called when a model is selected.
    """

    DEFAULT_CSS = """
    ModelSelectDialog {
        height: auto;
        width: 80;
        align: center top;
        border: thick panel;
        padding: 1;
    }

    ModelSelectDialog > Vertical {
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
        title: str = "Select Model",
        models: Optional[List[ModelInfo]] = None,
        on_select: Optional[Callable[[ModelInfo], None]] = None
    ):
        super().__init__()
        self.title = title
        self.models = models or []
        self.on_select = on_select
        self._result: Optional[ModelInfo] = None
        self._selected_index: int = 0

        # Generate options from models
        self.options = self._generate_options()

    def _generate_options(self) -> List[Dict[str, Any]]:
        """Generate select options from ModelInfo objects.

        Returns:
            List of option dictionaries with value, title, description.
        """
        options = []
        for model in self.models:
            options.append({
                "value": model,
                "title": model.name,
                "description": model.provider_id.value
            })
        return options

    def compose(self) -> ComposeResult:
        """Compose dialog widgets."""
        if self.title:
            yield Label(self.title)

        yield ListView(id="model_list")
        for option in self.options:
            yield ListItem(
                Static(f"{option['title']} ({option['description']})")
            )

        yield Static("Press Enter to select, Escape to cancel")

    async def on_mount(self) -> None:
        """Called when dialog is mounted."""
        list_view = self.query_one(ListView)
        list_view.focus()
        list_view.highlighted = 0

    def select_option(self, model: ModelInfo) -> None:
        """Select a model by ModelInfo object.

        Args:
            model: ModelInfo to select.
        """
        for idx, option in enumerate(self.options):
            if option["value"] == model:
                self._selected_index = idx
                self._result = model
                try:
                    list_view = self.query_one(ListView)
                    if list_view.highlighted != idx:
                        list_view.highlighted = idx
                except Exception:
                    pass
                # Call on_select callback if provided
                if self.on_select:
                    self.on_select(model)
                return

    def close_dialog(self, value: Optional[ModelInfo] = None) -> None:
        """Close dialog and return selected model.

        Args:
            value: Selected ModelInfo or None if cancelled.
        """
        if value is None:
            self._result = None
        else:
            self._result = value
        self.dismiss()

    def get_result(self) -> Optional[ModelInfo]:
        """Get dialog result.

        Returns:
            Selected ModelInfo or None.
        """
        return self._result

    def _persist_to_settings(self, model: ModelInfo) -> None:
        """Persist selected model to settings.

        Args:
            model: ModelInfo to persist.
        """
        settings.model_default = model.id
        settings.provider_default = model.provider_id.value

    def action_enter(self) -> None:
        """Handle Enter key - select current model and close."""
        if self.options and self._selected_index < len(self.options):
            model = self.options[self._selected_index]["value"]
            if self.on_select:
                self.on_select(model)
            # Persist to settings
            self._persist_to_settings(model)
        self.close_dialog(self._result)

    def action_escape(self) -> None:
        """Handle Escape key - close without selection."""
        self.close_dialog(None)
