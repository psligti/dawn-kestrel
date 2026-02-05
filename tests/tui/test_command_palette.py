"""Command Palette Dialog Tests - TDD phase tests"""
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, Label, Static

from opencode_python.tui.dialogs import CommandPaletteDialog


class TestCommandPaletteDialog:
    """CommandPaletteDialog lifecycle tests"""

    @pytest.mark.asyncio
    async def test_command_palette_dialog_exists(self):
        """CommandPaletteDialog should be importable"""
        assert CommandPaletteDialog is not None

    @pytest.mark.asyncio
    async def test_command_palette_dialog_has_title(self):
        """CommandPaletteDialog should have a title property"""
        dialog = CommandPaletteDialog()
        assert dialog.title == "Command Palette"

    @pytest.mark.asyncio
    async def test_command_palette_dialog_shows_search_input(self):
        """CommandPaletteDialog should show search input field"""
        class TestApp(App):
            pass

        app = TestApp()
        dialog = CommandPaletteDialog()

        async with app.run_test() as pilot:
            app.push_screen(dialog)
            await pilot.pause()

            # Verify dialog contains search input
            inputs = dialog.query(Input)
            assert len(inputs) >= 1

    @pytest.mark.asyncio
    async def test_command_palette_dialog_shows_commands(self):
        """CommandPaletteDialog should display available commands"""
        class TestApp(App):
            pass

        app = TestApp()
        dialog = CommandPaletteDialog()

        async with app.run_test() as pilot:
            app.push_screen(dialog)
            await pilot.pause()

            # Dialog should render command list
            statics = dialog.query(Static)
            # Should show at least some static content (commands)
            assert len(statics) >= 3  # header + at least 2 commands

    @pytest.mark.asyncio
    async def test_command_palette_has_essential_commands(self):
        """CommandPaletteDialog should have essential commands"""
        dialog = CommandPaletteDialog()

        # Check that essential commands are available
        assert dialog.commands is not None
        assert len(dialog.commands) >= 4  # session-list, model-select, theme-select, quit

    @pytest.mark.asyncio
    async def test_command_palette_search_filters_commands(self):
        """CommandPaletteDialog should filter commands by search query"""
        class TestApp(App):
            pass

        app = TestApp()
        dialog = CommandPaletteDialog()

        async with app.run_test() as pilot:
            app.push_screen(dialog)
            await pilot.pause()

            # Simulate typing "session" - should filter to show session-list
            dialog.filter_commands("session")

        # Check filtered results
        assert dialog.filtered_commands is not None

    @pytest.mark.asyncio
    async def test_command_palette_search_empty_string(self):
        """CommandPaletteDialog should show all commands when search is empty"""
        dialog = CommandPaletteDialog()
        original_count = len(dialog.commands)

        # Clear filter
        dialog.filter_commands("")

        # Should return all commands
        assert len(dialog.filtered_commands) == original_count

    @pytest.mark.asyncio
    async def test_command_palette_select_command(self):
        """CommandPaletteDialog should select a command and return it"""
        dialog = CommandPaletteDialog()

        # Select the quit command
        selected = dialog.select_command("quit")

        assert selected == "quit"

    @pytest.mark.asyncio
    async def test_command_palette_default_selection(self):
        """CommandPaletteDialog should have default selection"""
        dialog = CommandPaletteDialog()

        # Should have at least first command selected
        assert dialog.selected_command_index >= 0

    @pytest.mark.asyncio
    async def test_command_palette_close_dialog(self):
        """CommandPaletteDialog should close and return result"""
        dialog = CommandPaletteDialog()

        dialog.close_dialog("model-select")

        assert dialog.get_result() == "model-select"
        assert dialog.is_closed() is True

    @pytest.mark.asyncio
    async def test_command_palette_default_close(self):
        """CommandPaletteDialog should close without selection when no option selected"""
        dialog = CommandPaletteDialog()

        dialog.close_dialog(None)

        assert dialog.get_result() is None
        assert dialog.is_closed() is True

    @pytest.mark.asyncio
    async def test_command_palette_shows_command_description(self):
        """CommandPaletteDialog should display command title and description"""
        class TestApp(App):
            pass

        app = TestApp()
        dialog = CommandPaletteDialog()

        async with app.run_test() as pilot:
            app.push_screen(dialog)
            await pilot.pause()

            # Should show command titles
            labels = dialog.query(Label)
            assert len(labels) > 0

    @pytest.mark.asyncio
    async def test_command_palette_action_enter_selects_command(self):
        """CommandPaletteDialog should select and close on Enter"""
        class TestApp(App):
            pass

        app = TestApp()
        dialog = CommandPaletteDialog()

        async with app.run_test() as pilot:
            app.push_screen(dialog)
            await pilot.pause()

            # Simulate selecting command and pressing Enter
            dialog.action_enter()

            assert dialog.is_closed() is True
            assert dialog.get_result() is not None

    @pytest.mark.asyncio
    async def test_command_palette_action_escape_cancels(self):
        """CommandPaletteDialog should cancel and close on Escape"""
        class TestApp(App):
            pass

        app = TestApp()
        dialog = CommandPaletteDialog()

        async with app.run_test() as pilot:
            app.push_screen(dialog)
            await pilot.pause()

            # Simulate pressing Escape
            dialog.action_escape()

            assert dialog.is_closed() is True
            assert dialog.get_result() is None
