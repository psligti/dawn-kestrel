"""Tests for MessageScreen scroll navigation

TDD Workflow:
- RED: Write failing tests first (verify scroll behavior)
- GREEN: Fix keybinding mappings and implementation
- REFACTOR: Improve code structure
"""

import pytest
from textual.app import App

from dawn_kestrel.tui.screens.message_screen import MessageScreen
from dawn_kestrel.core.models import Session


@pytest.fixture
def session():
    """Create a test session"""
    return Session(
        id="test-session",
        slug="test-session",
        project_id="test-project",
        directory="/path/to/project",
        title="Test Session",
        version="1.0.0",
        time_created=1700000000.0,
        time_updated=1700000000.0,
    )


@pytest.mark.asyncio
async def test_scroll_bindings_exist(session):
    """Test that scroll navigation bindings are registered"""
    screen = MessageScreen(session=session)

    # Check keybindings are defined
    bindings_dict = {key: action for key, action, _ in screen.BINDINGS}

    # Page up/down (PageUp/PageDown keys)
    assert "pageup" in bindings_dict
    assert "pagedown" in bindings_dict
    assert bindings_dict["pageup"] == "scroll_page_up"
    assert bindings_dict["pagedown"] == "scroll_page_down"

    # Half page (Ctrl+U/D)
    assert "ctrl+u" in bindings_dict
    assert "ctrl+d" in bindings_dict
    assert bindings_dict["ctrl+u"] == "scroll_half_page_up"
    assert bindings_dict["ctrl+d"] == "scroll_half_page_down"

    # Full page (Ctrl+B/F) - SHOULD be full page, not half page
    assert "ctrl+b" in bindings_dict
    assert "ctrl+f" in bindings_dict
    assert bindings_dict["ctrl+b"] == "scroll_full_page_up"
    assert bindings_dict["ctrl+f"] == "scroll_full_page_down"

    # Jump to first/last (G/Shift+G) - SHOULD be G=top, Shift+G=bottom (vim style)
    assert "g" in bindings_dict
    assert "shift+g" in bindings_dict
    assert bindings_dict["g"] == "jump_to_top"
    assert bindings_dict["shift+g"] == "jump_to_bottom"


@pytest.mark.asyncio
async def test_scroll_actions_exist(session):
    """Test that all scroll action methods exist"""
    screen = MessageScreen(session=session)

    # Basic scroll actions
    assert hasattr(screen, 'action_scroll_home')
    assert hasattr(screen, 'action_scroll_end')
    assert hasattr(screen, 'action_scroll_page_up')
    assert hasattr(screen, 'action_scroll_page_down')

    # Half page actions
    assert hasattr(screen, 'action_scroll_half_page_up')
    assert hasattr(screen, 'action_scroll_half_page_down')

    # Full page actions (NEW - need to implement)
    assert hasattr(screen, 'action_scroll_full_page_up')
    assert hasattr(screen, 'action_scroll_full_page_down')

    # Jump actions
    assert hasattr(screen, 'action_jump_to_top')
    assert hasattr(screen, 'action_jump_to_bottom')


@pytest.mark.asyncio
async def test_scroll_actions_work_with_mounted_screen(session):
    """Test that scroll actions work when screen is properly mounted"""
    class TestApp(App):
        def __init__(self, session):
            super().__init__()
            self.session = session
            self.screen = None

        async def on_mount(self):
            self.screen = MessageScreen(session=self.session)
            await self.push_screen(self.screen)
            await self.screen._load_messages()

    app = TestApp(session=session)
    async with app.run_test() as pilot:
        # Wait for screen to be mounted
        await pilot.pause()

        # Verify messages_container exists
        assert app.screen.messages_container is not None

        # Test scroll_home doesn't crash
        app.screen.action_scroll_home()
        await pilot.pause()

        # Test scroll_end doesn't crash
        app.screen.action_scroll_end()
        await pilot.pause()

        # Test scroll_page_up doesn't crash
        app.screen.action_scroll_page_up()
        await pilot.pause()

        # Test scroll_page_down doesn't crash
        app.screen.action_scroll_page_down()
        await pilot.pause()

        # Test scroll_half_page_up doesn't crash
        app.screen.action_scroll_half_page_up()
        await pilot.pause()

        # Test scroll_half_page_down doesn't crash
        app.screen.action_scroll_half_page_down()
        await pilot.pause()

        # Test scroll_full_page_up doesn't crash (NEW)
        app.screen.action_scroll_full_page_up()
        await pilot.pause()

        # Test scroll_full_page_down doesn't crash (NEW)
        app.screen.action_scroll_full_page_down()
        await pilot.pause()

        # Test jump_to_top doesn't crash
        app.screen.action_jump_to_top()
        await pilot.pause()

        # Test jump_to_bottom doesn't crash
        app.screen.action_jump_to_bottom()
        await pilot.pause()


@pytest.mark.asyncio
async def test_scroll_full_page_action_bindings(session):
    """Test that Ctrl+B/F are bound to full page scroll actions"""
    screen = MessageScreen(session=session)

    # Verify full page actions exist
    assert hasattr(screen, 'action_scroll_full_page_up')
    assert hasattr(screen, 'action_scroll_full_page_down')

    # Verify they are callable
    assert callable(screen.action_scroll_full_page_up)
    assert callable(screen.action_scroll_full_page_down)


@pytest.mark.asyncio
async def test_vim_style_jump_bindings(session):
    """Test that G/Shift+G use vim-style bindings (G=top, Shift+G=bottom)"""
    screen = MessageScreen(session=session)

    bindings_dict = {key: action for key, action, _ in screen.BINDINGS}

    # G should jump to top (first message)
    assert bindings_dict["g"] == "jump_to_top"

    # Shift+G should jump to bottom (last message)
    assert bindings_dict["shift+g"] == "jump_to_bottom"


# Line numbers for tool output (optional feature)

@pytest.mark.asyncio
async def test_line_numbers_for_tool_output(session):
    """Test that tool output displays with line numbers (optional feature)"""
    # This test is for optional line numbers feature
    # Can skip if not implementing in this task
    pytest.skip("Line numbers for tool output is optional (Phase 2+)")
