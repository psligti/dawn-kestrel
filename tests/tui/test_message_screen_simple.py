"""Tests for MessageScreen scroll navigation

Verifies that scroll navigation methods work correctly.
"""

import pytest
from dawn_kestrel.tui.screens.message_screen import MessageScreen
from dawn_kestrel.tui.app import OpenCodeTUI
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
async def test_action_scroll_home(app):
    """Test that action_scroll_home scrolls to top"""
    screen = MessageScreen(session=session())
    await app.run_for(0.1)

    # Scroll to end by adding a message
    await screen._add_message("Hello, this is a test message", "user")
    await screen._add_message("Hello, this is a test message", "user")
    await screen._add_message("Hello, this is a test message", "user")

    # Scroll to top
    screen.action_scroll_home()
    await app.run_for(0.1)

    # Verify we're at the top (first message visible)
    messages = screen.messages
    assert len(messages) == 3
    assert messages[0].text == "Hello, this is a test message"


@pytest.mark.asyncio
async def test_action_scroll_end(app):
    """Test that action_scroll_end scrolls to bottom"""
    screen = MessageScreen(session=session())
    await app.run_for(0.1)

    # Scroll to top
    await screen.action_scroll_home()
    await app.run_for(0.1)

    # Scroll to end
    screen.action_scroll_end()
    await app.run_for(0.1)

    # Verify we're at the bottom (last message visible)
    messages = screen.messages
    assert len(messages) == 3
    assert messages[2].text == "Hello, this is a test message"


@pytest.mark.asyncio
async def test_action_scroll_page_up(app):
    """Test action_scroll_page_up scrolls up one page"""
    screen = MessageScreen(session=session())
    await app.run_for(0.1)

    # Add messages to test page scrolling
    for i in range(20):
        await screen._add_message(f"Message {i}", "user")
    await screen.action_scroll_home()
    await app.run_for(0.1)

    # Save initial message
    initial_message = screen.messages[-1]

    # Scroll up one page
    screen.action_scroll_page_up()
    await app.run_for(0.1)

    # Verify we scrolled up (fewer messages shown)
    messages = screen.messages
    assert len(messages) < 20
    assert messages[0].text != initial_message.text


@pytest.mark.asyncio
async def test_action_scroll_page_down(app):
    """Test action_scroll_page_down scrolls down one page"""
    screen = MessageScreen(session=session())
    await app.run_for(0.1)

    # Add messages and scroll to top
    for i in range(20):
        await screen._add_message(f"Message {i}", "user")
    await screen.action_scroll_home()
    await app.run_for(0.1)

    # Save initial message
    initial_message = screen.messages[-1]

    # Scroll down one page
    screen.action_scroll_page_down()
    await app.run_for(0.1)

    # Verify we scrolled down (more messages shown)
    messages = screen.messages
    assert len(messages) > 20
    assert messages[0].text != initial_message.text


@pytest.mark.asyncio
async def test_action_scroll_to_top(app):
    """Test action_scroll_to_top scrolls to top"""
    screen = MessageScreen(session=session())
    await app.run_for(0.1)

    # Add messages and scroll to end
    for i in range(10):
        await screen._add_message(f"Message {i}", "user")
    await screen.action_scroll_home()
    await app.run_for(0.1)

    # Save last message
    last_message = screen.messages[-1]

    # Scroll to end
    screen.action_scroll_end()
    await app.run_for(0.1)

    # Scroll to top
    screen.action_scroll_to_top()
    await app.run_for(0.1)

    # Verify we're at the top (first message visible)
    messages = screen.messages
    assert len(messages) == 10
    assert messages[0].text == "Message 0"


@pytest.mark.asyncio
async def test_action_scroll_to_bottom(app):
    """Test action_scroll_to_bottom scrolls to bottom"""
    screen = MessageScreen(session=session())
    await app.run_for(0.1)

    # Add messages
    for i in range(5):
        await screen._add_message(f"Message {i}", "user")
    await screen.action_scroll_home()
    await app.run_for(0.1)

    # Scroll to end
    screen.action_scroll_to_bottom()
    await app.run_for(0.1)

    # Verify we're at the bottom (last message visible)
    messages = screen.messages
    assert len(messages) == 5
    assert messages[-1].text == "Message 4"