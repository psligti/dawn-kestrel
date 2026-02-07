"""Tests for ThemeSelectDialog."""

import pytest
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ListView, ListItem, Static


def test_dialog_exists():
    """Test that ThemeSelectDialog can be imported and instantiated."""
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog
    assert ThemeSelectDialog is not None


def test_dialog_is_modal_screen():
    """Test that ThemeSelectDialog extends ModalScreen."""
    from textual.screen import ModalScreen
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog
    assert issubclass(ThemeSelectDialog, ModalScreen)


def test_dialog_has_title():
    """Test that ThemeSelectDialog has title property."""
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog
    dialog = ThemeSelectDialog(title="Select Theme")
    assert dialog.title == "Select Theme"


def test_dialog_has_themes():
    """Test that ThemeSelectDialog has 3 themes (light, dark, dracula)."""
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog
    dialog = ThemeSelectDialog(title="Select Theme")
    assert len(dialog.themes) == 3
    theme_names = [t["value"] for t in dialog.themes]
    assert "light" in theme_names
    assert "dark" in theme_names
    assert "dracula" in theme_names


@pytest.mark.asyncio
async def test_dialog_displays_themes():
    """Test that ThemeSelectDialog displays themes correctly."""
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog

    class TestApp(App):
        def compose(self):
            dialog = ThemeSelectDialog(title="Select Theme")
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

        # Check that themes are displayed as ListItems
        list_items = dialog.query(ListItem)
        assert len(list_items) == 3

        # Check that theme names are visible
        first_item = list_items[0]
        static = first_item.query_one(Static)
        assert static is not None


def test_dialog_options_generated():
    """Test that options are generated correctly from themes."""
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog
    dialog = ThemeSelectDialog(title="Select Theme")

    # Options should be generated with proper structure
    assert len(dialog.options) == 3

    # Check that each option has value and title
    for option in dialog.options:
        assert "value" in option
        assert "title" in option
        # Check specific theme values and titles
        if option["value"] == "light":
            assert option["title"] == "Light"
        elif option["value"] == "dark":
            assert option["title"] == "Dark"
        elif option["value"] == "dracula":
            assert option["title"] == "Dracula"


def test_dialog_get_result():
    """Test that get_result returns selected theme."""
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog
    dialog = ThemeSelectDialog(title="Test")

    # Before selection
    assert dialog.get_result() is None

    # After selection
    dialog.select_option("dark")
    assert dialog.get_result() == "dark"


@pytest.mark.asyncio
async def test_dialog_close_returns_selection():
    """Test that dialog closes and returns result."""
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog

    class TestApp(App):
        def compose(self):
            dialog = ThemeSelectDialog(title="Select Theme")
            self._dialog = dialog
            yield Vertical(dialog)

        def get_dialog(self):
            return self._dialog

    app = TestApp()
    async with app.run_test() as pilot:
        dialog = app.get_dialog()
        dialog.close_dialog("dracula")
        result = dialog.get_result()
        assert result == "dracula"


@pytest.mark.asyncio
async def test_dialog_close_without_selection_returns_none():
    """Test that dialog closes without selection returns None."""
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog

    class TestApp(App):
        def compose(self):
            dialog = ThemeSelectDialog(title="Select Theme")
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


def test_dialog_default_result():
    """Test that default result is None."""
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog
    dialog = ThemeSelectDialog(title="Test")
    assert dialog.get_result() is None


def test_dialog_on_select_callback():
    """Test that on_select callback is called when theme is selected."""
    from dawn_kestrel.tui.dialogs.theme_select_dialog import ThemeSelectDialog

    on_select_called = []
    def on_select(theme):
        on_select_called.append(theme)

    dialog = ThemeSelectDialog(title="Test", on_select=on_select)
    dialog.select_option("light")

    assert len(on_select_called) == 1
    assert on_select_called[0] == "light"
