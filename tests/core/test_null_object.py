"""Tests for Null Object pattern for optional dependencies.

This module tests the Null Object pattern which provides safe defaults
for optional handler dependencies, eliminating null checks.
"""

import asyncio
import pytest

from dawn_kestrel.interfaces.io import (
    IOHandler,
    ProgressHandler,
    NotificationHandler,
    Notification,
    NotificationType,
)


# ============ NullIOHandler Tests ============


@pytest.mark.asyncio
async def test_null_io_prompt_returns_default_string():
    """Test that NullIOHandler.prompt returns default string."""
    from dawn_kestrel.core.null_object import NullIOHandler

    handler = NullIOHandler()
    result = await handler.prompt("Enter value:", default="default_value")

    assert result == "default_value"


@pytest.mark.asyncio
async def test_null_io_prompt_returns_empty_string_when_no_default():
    """Test that NullIOHandler.prompt returns empty string when no default."""
    from dawn_kestrel.core.null_object import NullIOHandler

    handler = NullIOHandler()
    result = await handler.prompt("Enter value:")

    assert result == ""


@pytest.mark.asyncio
async def test_null_io_confirm_returns_true_with_default():
    """Test that NullIOHandler.confirm returns True with default=True."""
    from dawn_kestrel.core.null_object import NullIOHandler

    handler = NullIOHandler()
    result = await handler.confirm("Continue?", default=True)

    assert result is True


@pytest.mark.asyncio
async def test_null_io_confirm_returns_false_with_default():
    """Test that NullIOHandler.confirm returns False with default=False."""
    from dawn_kestrel.core.null_object import NullIOHandler

    handler = NullIOHandler()
    result = await handler.confirm("Continue?", default=False)

    assert result is False


@pytest.mark.asyncio
async def test_null_io_select_returns_first_option():
    """Test that NullIOHandler.select returns first option."""
    from dawn_kestrel.core.null_object import NullIOHandler

    handler = NullIOHandler()
    result = await handler.select("Choose:", options=["A", "B", "C"])

    assert result == "A"


@pytest.mark.asyncio
async def test_null_io_select_returns_empty_string_when_no_options():
    """Test that NullIOHandler.select returns empty string when no options."""
    from dawn_kestrel.core.null_object import NullIOHandler

    handler = NullIOHandler()
    result = await handler.select("Choose:", options=[])

    assert result == ""


@pytest.mark.asyncio
async def test_null_io_multi_select_returns_empty_list():
    """Test that NullIOHandler.multi_select returns empty list."""
    from dawn_kestrel.core.null_object import NullIOHandler

    handler = NullIOHandler()
    result = await handler.multi_select("Choose:", options=["A", "B", "C"])

    assert result == []


# ============ NullProgressHandler Tests ============


def test_null_progress_start_is_noop():
    """Test that NullProgressHandler.start is a no-op."""
    from dawn_kestrel.core.null_object import NullProgressHandler

    handler = NullProgressHandler()
    # Should not raise any exception
    handler.start("Creating session", 100)


def test_null_progress_update_is_noop():
    """Test that NullProgressHandler.update is a no-op."""
    from dawn_kestrel.core.null_object import NullProgressHandler

    handler = NullProgressHandler()
    # Should not raise any exception
    handler.update(50, "Halfway there")


def test_null_progress_complete_is_noop():
    """Test that NullProgressHandler.complete is a no-op."""
    from dawn_kestrel.core.null_object import NullProgressHandler

    handler = NullProgressHandler()
    # Should not raise any exception
    handler.complete("Done!")


# ============ NullNotificationHandler Tests ============


def test_null_notification_show_is_noop():
    """Test that NullNotificationHandler.show is a no-op."""
    from dawn_kestrel.core.null_object import NullNotificationHandler

    handler = NullNotificationHandler()
    notification = Notification(
        notification_type=NotificationType.SUCCESS,
        message="Test notification",
    )
    # Should not raise any exception
    handler.show(notification)


# ============ get_null_handler Tests ============


@pytest.mark.asyncio
async def test_get_null_handler_io_returns_existing():
    """Test that get_null_handler returns existing IO handler."""
    from dawn_kestrel.core.null_object import get_null_handler, NullIOHandler

    existing = NullIOHandler()
    result = get_null_handler("io", existing)

    assert result is existing
    assert isinstance(result, IOHandler)


@pytest.mark.asyncio
async def test_get_null_handler_progress_returns_existing():
    """Test that get_null_handler returns existing Progress handler."""
    from dawn_kestrel.core.null_object import get_null_handler, NullProgressHandler

    existing = NullProgressHandler()
    result = get_null_handler("progress", existing)

    assert result is existing
    assert isinstance(result, ProgressHandler)


@pytest.mark.asyncio
async def test_get_null_handler_notification_returns_existing():
    """Test that get_null_handler returns existing Notification handler."""
    from dawn_kestrel.core.null_object import get_null_handler, NullNotificationHandler

    existing = NullNotificationHandler()
    result = get_null_handler("notification", existing)

    assert result is existing
    assert isinstance(result, NotificationHandler)


@pytest.mark.asyncio
async def test_get_null_handler_io_none_returns_null_io():
    """Test that get_null_handler returns NullIOHandler when None passed."""
    from dawn_kestrel.core.null_object import get_null_handler, NullIOHandler

    result = get_null_handler("io", None)

    assert isinstance(result, NullIOHandler)
    assert isinstance(result, IOHandler)


@pytest.mark.asyncio
async def test_get_null_handler_progress_none_returns_null_progress():
    """Test that get_null_handler returns NullProgressHandler when None passed."""
    from dawn_kestrel.core.null_object import get_null_handler, NullProgressHandler

    result = get_null_handler("progress", None)

    assert isinstance(result, NullProgressHandler)
    assert isinstance(result, ProgressHandler)


@pytest.mark.asyncio
async def test_get_null_handler_notification_none_returns_null_notification():
    """Test that get_null_handler returns NullNotificationHandler when None passed."""
    from dawn_kestrel.core.null_object import get_null_handler, NullNotificationHandler

    result = get_null_handler("notification", None)

    assert isinstance(result, NullNotificationHandler)
    assert isinstance(result, NotificationHandler)


def test_get_null_handler_unknown_type_raises_valueerror():
    """Test that get_null_handler raises ValueError for unknown type."""
    from dawn_kestrel.core.null_object import get_null_handler

    with pytest.raises(ValueError, match="Unknown handler type"):
        get_null_handler("unknown", None)


# ============ Protocol Compliance Tests ============


def test_null_io_handler_implements_protocol():
    """Test that NullIOHandler implements IOHandler protocol."""
    from dawn_kestrel.core.null_object import NullIOHandler

    handler = NullIOHandler()
    assert isinstance(handler, IOHandler)


def test_null_progress_handler_implements_protocol():
    """Test that NullProgressHandler implements ProgressHandler protocol."""
    from dawn_kestrel.core.null_object import NullProgressHandler

    handler = NullProgressHandler()
    assert isinstance(handler, ProgressHandler)


def test_null_notification_handler_implements_protocol():
    """Test that NullNotificationHandler implements NotificationHandler protocol."""
    from dawn_kestrel.core.null_object import NullNotificationHandler

    handler = NullNotificationHandler()
    assert isinstance(handler, NotificationHandler)


# ============ Integration Tests ============


@pytest.mark.asyncio
async def test_null_handlers_with_existing_code_work():
    """Test that null handlers work with existing code patterns."""
    from dawn_kestrel.core.null_object import (
        NullIOHandler,
        NullProgressHandler,
        NullNotificationHandler,
    )

    # Simulate existing code pattern from session_service.py
    io_handler = NullIOHandler()
    progress_handler = NullProgressHandler()
    notification_handler = NullNotificationHandler()

    # Use confirm (from existing code)
    use_parent = await io_handler.confirm(
        "Create this session as a child of an existing session?", default=False
    )
    assert use_parent is False

    # Use progress (from existing code)
    progress_handler.start("Creating session", 100)
    progress_handler.update(50, "Initializing...")
    progress_handler.update(100, "Session created")
    progress_handler.complete("Done")

    # Use notification (from existing code)
    notification_handler.show(
        Notification(
            notification_type=NotificationType.SUCCESS,
            message=f"Session created",
        )
    )

    # No exceptions raised = success
    assert True
