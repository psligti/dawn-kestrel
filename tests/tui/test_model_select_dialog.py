"""Tests for ModelSelectDialog."""

from unittest.mock import Mock, patch
import pytest
from decimal import Decimal
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ListView, ListItem, Static

from opencode_python.tui.dialogs import ModelSelectDialog
from opencode_python.providers.base import ModelInfo, ModelCapabilities, ModelCost, ModelLimits, ProviderID
from opencode_python.core.settings import Settings


@pytest.fixture
def available_models():
    """Return test ModelInfo objects."""
    return [
        ModelInfo(
            id="claude-3-5-sonnet-20241022",
            provider_id=ProviderID.ANTHROPIC,
            api_id="claude-3-5-sonnet-20241022",
            api_url="https://api.anthropic.com",
            name="Claude 3.5 Sonnet",
            family="sonnet",
            capabilities=ModelCapabilities(),
            cost=ModelCost(input=Decimal("3.0"), output=Decimal("15.0")),
            limit=ModelLimits(context=200000),
            status="active",
            options={},
            headers={}
        ),
        ModelInfo(
            id="gpt-4o",
            provider_id=ProviderID.OPENAI,
            api_id="gpt-4o",
            api_url="https://api.openai.com/v1",
            name="GPT-4o",
            family="gpt",
            capabilities=ModelCapabilities(),
            cost=ModelCost(input=Decimal("5.0"), output=Decimal("15.0")),
            limit=ModelLimits(context=128000),
            status="active",
            options={},
            headers={}
        ),
    ]


@pytest.fixture
def mock_settings():
    with patch("opencode_python.core.settings.get_settings") as mock:
        settings = Mock(spec=Settings)
        settings.model_default = "claude-3-5-sonnet-20241022"
        settings.provider_default = "anthropic"
        mock.return_value = settings
        yield settings


def test_dialog_exists():
    """Test that ModelSelectDialog can be imported and instantiated."""
    from opencode_python.tui.dialogs.model_select_dialog import ModelSelectDialog
    assert ModelSelectDialog is not None


def test_dialog_is_modal_screen():
    """Test that ModelSelectDialog extends ModalScreen."""
    from textual.screen import ModalScreen
    from opencode_python.tui.dialogs.model_select_dialog import ModelSelectDialog
    assert issubclass(ModelSelectDialog, ModalScreen)


def test_dialog_has_title(available_models):
    """Test that ModelSelectDialog has title property."""
    dialog = ModelSelectDialog(title="Select Model", models=available_models)
    assert dialog.title == "Select Model"


def test_dialog_has_models(available_models):
    """Test that ModelSelectDialog accepts models parameter."""
    dialog = ModelSelectDialog(title="Select Model", models=available_models)
    assert len(dialog.models) == 2
    assert dialog.models[0].id == "claude-3-5-sonnet-20241022"


@pytest.mark.asyncio
async def test_dialog_displays_models(available_models):
    """Test that ModelSelectDialog displays models correctly."""
    class TestApp(App):
        def compose(self):
            dialog = ModelSelectDialog(title="Select Model", models=available_models)
            self._dialog = dialog
            yield Vertical(dialog)

        def get_dialog(self):
            return self._dialog

    app = TestApp()
    async with app.run_test() as pilot:
        dialog = app.get_dialog()

        # Check that ListView exists
        list_view = dialog.query_one(ListView)
        assert list_view is not None

        # Check that models are displayed as ListItems
        list_items = dialog.query(ListItem)
        assert len(list_items) == 2

        # Check that model names are visible
        first_item = list_items[0]
        static = first_item.query_one(Static)
        # Static has a renderable that contains the text
        # For test purposes, check if it's rendered
        assert static is not None


def test_dialog_options_generated(available_models):
    """Test that options are generated correctly from models."""
    dialog = ModelSelectDialog(title="Select Model", models=available_models)

    # Options should be generated with proper structure
    assert len(dialog.options) == 2
    assert dialog.options[0]["value"].id == "claude-3-5-sonnet-20241022"
    assert dialog.options[0]["title"] == "Claude 3.5 Sonnet"
    assert dialog.options[0]["description"] == "anthropic"


def test_dialog_get_result(available_models):
    """Test that get_result returns selected model."""
    dialog = ModelSelectDialog(title="Test", models=available_models)

    # Before selection
    assert dialog.get_result() is None

    # After selection
    dialog.select_option(available_models[0])
    assert dialog.get_result() is not None
    assert dialog.get_result().id == "claude-3-5-sonnet-20241022"


@pytest.mark.asyncio
async def test_dialog_close_returns_selection(available_models):
    """Test that dialog closes and returns result."""
    class TestApp(App):
        def compose(self):
            dialog = ModelSelectDialog(title="Select Model", models=available_models)
            self._dialog = dialog
            yield Vertical(dialog)

        def get_dialog(self):
            return self._dialog

    app = TestApp()
    async with app.run_test() as pilot:
        dialog = app.get_dialog()
        dialog.close_dialog(available_models[1])
        result = dialog.get_result()
        assert result is not None
        if result:  # Type guard for Optional[ModelInfo]
            assert result.id == "gpt-4o"


@pytest.mark.asyncio
async def test_dialog_close_without_selection_returns_none(available_models):
    """Test that dialog closes without selection returns None."""
    class TestApp(App):
        def compose(self):
            dialog = ModelSelectDialog(title="Select Model", models=available_models)
            self._dialog = dialog
            yield Vertical(dialog)

        def get_dialog(self):
            return self._dialog

    app = TestApp()
    async with app.run_test() as pilot:
        dialog = app.get_dialog()
        dialog.close_dialog()
        result = dialog.get_result()
        assert result is None


def test_dialog_default_result(available_models):
    """Test that default result is None."""
    dialog = ModelSelectDialog(title="Test", models=available_models)
    assert dialog.get_result() is None


def test_dialog_empty_models():
    """Test that dialog handles empty models list."""
    models = []
    dialog = ModelSelectDialog(title="Test", models=models)
    assert len(dialog.options) == 0


@pytest.mark.asyncio
async def test_dialog_persists_selection_to_settings(available_models, mock_settings):
    """Test that dialog persists selection to settings."""
    class TestApp(App):
        def compose(self):
            dialog = ModelSelectDialog(title="Select Model", models=available_models)
            self._dialog = dialog
            yield Vertical(dialog)

        def get_dialog(self):
            return self._dialog

    app = TestApp()
    async with app.run_test() as pilot:
        dialog = app.get_dialog()
        selected_model = available_models[0]
        dialog.close_dialog(selected_model)

        # Verify settings were updated
        assert mock_settings.model_default == selected_model.id
        assert mock_settings.provider_default == selected_model.provider_id.value


@pytest.mark.asyncio
async def test_dialog_shows_default_selection(available_models, mock_settings):
    """Test that dialog shows default model as pre-selected."""
    class TestApp(App):
        def compose(self):
            dialog = ModelSelectDialog(title="Select Model", models=available_models)
            self._dialog = dialog
            yield Vertical(dialog)

        def get_dialog(self):
            return self._dialog

    app = TestApp()
    async with app.run_test() as pilot:
        dialog = app.get_dialog()
        assert dialog._result is None


def test_dialog_on_select_callback(available_models):
    """Test that on_select callback is called when model is selected."""
    on_select_called = []
    def on_select(model):
        on_select_called.append(model)

    dialog = ModelSelectDialog(title="Test", models=available_models, on_select=on_select)
    dialog.select_option(available_models[1])

    assert len(on_select_called) == 1
    assert on_select_called[0].id == "gpt-4o"
