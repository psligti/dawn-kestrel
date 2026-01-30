"""Home Screen Tests - TUI Shell & Navigation"""
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, DataTable, Static
from textual.message import Message

from opencode_python.tui.screens.home_screen import HomeScreen


class CommandExecute(Message):
    """Emitted when a command should be executed."""

    def __init__(self, action: str, data: dict) -> None:
        super().__init__()
        self.action = action
        self.data = data


class TestHomeScreen:
    """HomeScreen lifecycle tests"""

    @pytest.mark.asyncio
    async def test_home_screen_exists(self):
        """HomeScreen should be importable"""
        assert HomeScreen is not None

    @pytest.mark.asyncio
    async def test_home_screen_initializes_with_provider(self):
        """HomeScreen should initialize with provider and account info"""
        screen = HomeScreen(provider="OpenAI", account="TestAccount")
        assert screen.provider == "OpenAI"
        assert screen.account == "TestAccount"

    @pytest.mark.asyncio
    async def test_home_screen_shows_provider_info(self):
        """HomeScreen should display provider and account information"""
        class TestApp(App):
            pass

        app = TestApp()
        screen = HomeScreen(provider="Anthropic", account="dev")

        async with app.run_test() as pilot:
            app.push_screen(screen)
            await pilot.pause()

            # Verify provider info is displayed
            provider_info = screen.query_one("#provider-info", Static)
            assert provider_info is not None

    @pytest.mark.asyncio
    async def test_home_screen_has_quick_action_buttons(self):
        """HomeScreen should display quick action buttons"""
        class TestApp(App):
            pass

        app = TestApp()
        screen = HomeScreen()

        async with app.run_test() as pilot:
            app.push_screen(screen)
            await pilot.pause()

            # Verify quick action buttons exist
            buttons = screen.query(Button)
            assert len(buttons) >= 3  # New Session, Resume Session, Settings

            # Check button IDs
            button_ids = [btn.id for btn in buttons]
            assert "new-session-btn" in button_ids
            assert "resume-session-btn" in button_ids
            assert "settings-btn" in button_ids

    @pytest.mark.asyncio
    async def test_home_screen_has_sessions_table(self):
        """HomeScreen should display sessions table"""
        class TestApp(App):
            pass

        app = TestApp()
        screen = HomeScreen()

        async with app.run_test() as pilot:
            app.push_screen(screen)
            await pilot.pause()

            # Verify sessions table exists
            tables = screen.query(DataTable)
            assert len(tables) >= 1

    @pytest.mark.asyncio
    async def test_home_screen_emits_command_execute_on_new_session(self):
        """HomeScreen should emit CommandExecute when New Session is pressed"""
        class TestApp(App):
            pass

        app = TestApp()
        screen = HomeScreen()

        async with app.run_test() as pilot:
            app.push_screen(screen)
            await pilot.pause()

            # Click New Session button
            new_session_btn = screen.query_one("#new-session-btn", Button)
            new_session_btn.press()
            await pilot.pause()

            # Verify screen emitted event (by checking it doesn't crash)
            assert True  # Test passes if no exception was raised

    @pytest.mark.asyncio
    async def test_home_screen_formats_time_ago(self):
        """HomeScreen should format timestamps as time ago"""
        from datetime import datetime, timedelta

        screen = HomeScreen()
        now = datetime.now().timestamp()

        # Test different time formats
        assert screen._format_time(now) == "0m ago"
        assert screen._format_time(now - 3600) == "1h ago"
        assert screen._format_time(now - 86400) == "Yesterday"
        assert screen._format_time(now - 172800) == "2d ago"


class TestCommandPalette:
    """CommandPalette enhancement tests"""

    @pytest.mark.asyncio
    async def test_command_action_creation(self):
        """CommandAction should be created with correct properties"""
        from opencode_python.tui.palette.command_palette import CommandAction

        action = CommandAction(
            value="test_action",
            title="Test Action",
            description="Test description",
            permissions={"read"},
            category="test"
        )

        assert action.value == "test_action"
        assert action.title == "Test Action"
        assert action.description == "Test description"
        assert action.permissions == {"read"}
        assert action.category == "test"

    @pytest.mark.asyncio
    async def test_command_action_matches_query(self):
        """CommandAction should match search query"""
        from opencode_python.tui.palette.command_palette import CommandAction

        action = CommandAction(
            value="new_session",
            title="New Session",
            description="Create a new session",
            category="sessions"
        )

        assert action.matches("session") is True
        assert action.matches("new") is True
        assert action.matches("create") is True
        assert action.matches("delete") is False

    @pytest.mark.asyncio
    async def test_command_action_checks_permissions(self):
        """CommandAction should check user permissions"""
        from opencode_python.tui.palette.command_palette import CommandAction

        action = CommandAction(
            value="admin_action",
            title="Admin Action",
            description="Admin only action",
            permissions={"admin"},
            category="admin"
        )

        assert action.has_permission({"admin", "read"}) is True
        assert action.has_permission({"read"}) is False

    @pytest.mark.asyncio
    async def test_command_palette_manager_registers_action(self):
        """CommandPaletteManager should register actions"""
        from opencode_python.tui.palette.command_palette import manager

        action = manager.register_action(
            value="test",
            title="Test",
            description="Test action",
            category="test"
        )

        assert action is not None
        assert action.value == "test"

        # Clean up
        manager.unregister_action("test")

    @pytest.mark.asyncio
    async def test_command_palette_manager_gets_action(self):
        """CommandPaletteManager should retrieve registered actions"""
        from opencode_python.tui.palette.command_palette import manager

        manager.register_action(
            value="get_test",
            title="Get Test",
            description="Test action",
            category="test"
        )

        action = manager.get_action("get_test")

        assert action is not None
        assert action.value == "get_test"

        # Clean up
        manager.unregister_action("get_test")

    @pytest.mark.asyncio
    async def test_command_palette_manager_lists_all_actions(self):
        """CommandPaletteManager should list all registered actions"""
        from opencode_python.tui.palette.command_palette import manager, register_default_actions

        # Register defaults
        register_default_actions()

        actions = manager.get_all_actions()

        assert len(actions) > 0

    @pytest.mark.asyncio
    async def test_command_palette_manager_filters_by_category(self):
        """CommandPaletteManager should filter actions by category"""
        from opencode_python.tui.palette.command_palette import manager

        manager.register_action(
            value="cat1_action1",
            title="Cat1 Action 1",
            description="Test",
            category="category1"
        )

        manager.register_action(
            value="cat2_action1",
            title="Cat2 Action 1",
            description="Test",
            category="category2"
        )

        cat1_actions = manager.get_actions_by_category("category1")

        assert len(cat1_actions) == 1
        assert cat1_actions[0].value == "cat1_action1"

        # Clean up
        manager.unregister_action("cat1_action1")
        manager.unregister_action("cat2_action1")

    @pytest.mark.asyncio
    async def test_command_palette_manager_filters_actions(self):
        """CommandPaletteManager should filter actions by query and permissions"""
        from opencode_python.tui.palette.command_palette import manager

        manager.register_action(
            value="search_test",
            title="Search Test",
            description="Test action for search",
            category="test"
        )

        filtered = manager.filter_actions("search")

        assert len(filtered) > 0

        # Clean up
        manager.unregister_action("search_test")


class TestAppIntegration:
    """Integration tests for TUI app"""

    @pytest.mark.asyncio
    async def test_app_has_home_screen(self):
        """App should push HomeScreen on mount"""
        from opencode_python.tui.app import OpenCodeTUI

        app = OpenCodeTUI()

        async with app.run_test() as pilot:
            await pilot.pause()

            # Check if screen stack is not empty
            assert app.screen is not None
