"""Tests for TUI I/O handlers.

Tests TUI-specific implementations of IOHandler, ProgressHandler,
and NotificationHandler protocols that integrate with Textual framework.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from textual.app import App

from opencode_python.interfaces.io import (
    IOHandler,
    ProgressHandler,
    NotificationHandler,
    Notification,
    NotificationType,
)
from opencode_python.tui.handlers import (
    TUIIOHandler,
    TUIProgressHandler,
    TUINotificationHandler,
)


class TestTUIIOHandler:
    """Tests for TUI I/O handler."""

    @pytest.fixture
    def mock_app(self) -> Mock:
        """Create mock Textual app."""
        return Mock(spec=App)

    @pytest.fixture
    def io_handler(self, mock_app: Mock) -> TUIIOHandler:
        """Create TUI IO handler."""
        return TUIIOHandler(mock_app)

    def test_tui_io_handler_implements_protocol(self, io_handler: TUIIOHandler) -> None:
        """Test that TUIIOHandler implements IOHandler protocol."""
        assert hasattr(io_handler, 'prompt')
        assert hasattr(io_handler, 'confirm')
        assert hasattr(io_handler, 'select')
        assert hasattr(io_handler, 'multi_select')
        assert callable(io_handler.prompt)
        assert callable(io_handler.confirm)
        assert callable(io_handler.select)
        assert callable(io_handler.multi_select)

    @pytest.mark.asyncio
    async def test_tui_io_handler_prompt_returns_input(self, io_handler: TUIIOHandler) -> None:
        """Test that prompt returns user input."""
        result = await io_handler.prompt("Enter value", default="test")
        assert result == "test"

    @pytest.mark.asyncio
    async def test_tui_io_handler_prompt_returns_empty_without_default(self, io_handler: TUIIOHandler) -> None:
        """Test that prompt returns empty string without default."""
        result = await io_handler.prompt("Enter value")
        assert result == ""

    @pytest.mark.asyncio
    async def test_tui_io_handler_confirm_returns_bool(self, io_handler: TUIIOHandler) -> None:
        """Test that confirm returns boolean."""
        result = await io_handler.confirm("Continue?", default=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_tui_io_handler_confirm_returns_false_by_default(self, io_handler: TUIIOHandler) -> None:
        """Test that confirm returns False when default is False."""
        result = await io_handler.confirm("Continue?", default=False)
        assert result is False

    @pytest.mark.asyncio
    async def test_tui_io_handler_select_returns_option(self, io_handler: TUIIOHandler) -> None:
        """Test that select returns selected option."""
        options = ["option1", "option2", "option3"]
        result = await io_handler.select("Choose one", options)
        assert result == "option1"

    @pytest.mark.asyncio
    async def test_tui_io_handler_select_raises_on_empty_options(self, io_handler: TUIIOHandler) -> None:
        """Test that select raises ValueError on empty options."""
        with pytest.raises(ValueError, match="Options list cannot be empty"):
            await io_handler.select("Choose one", [])

    @pytest.mark.asyncio
    async def test_tui_io_handler_multi_select_returns_list(self, io_handler: TUIIOHandler) -> None:
        """Test that multi_select returns list of options."""
        options = ["option1", "option2", "option3"]
        result = await io_handler.multi_select("Choose multiple", options)
        assert result == []

    @pytest.mark.asyncio
    async def test_tui_io_handler_multi_select_raises_on_empty_options(self, io_handler: TUIIOHandler) -> None:
        """Test that multi_select raises ValueError on empty options."""
        with pytest.raises(ValueError, match="Options list cannot be empty"):
            await io_handler.multi_select("Choose multiple", [])


class TestTUIProgressHandler:
    """Tests for TUI progress handler."""

    @pytest.fixture
    def mock_app(self) -> Mock:
        """Create mock Textual app."""
        mock = Mock(spec=App)
        mock.notify = Mock()
        return mock

    @pytest.fixture
    def progress_handler(self, mock_app: Mock) -> TUIProgressHandler:
        """Create TUI progress handler."""
        return TUIProgressHandler(mock_app)

    def test_tui_progress_handler_implements_protocol(self, progress_handler: TUIProgressHandler) -> None:
        """Test that TUIProgressHandler implements ProgressHandler protocol."""
        assert hasattr(progress_handler, 'start')
        assert hasattr(progress_handler, 'update')
        assert hasattr(progress_handler, 'complete')
        assert callable(progress_handler.start)
        assert callable(progress_handler.update)
        assert callable(progress_handler.complete)

    def test_tui_progress_handler_start_initializes_progress(self, progress_handler: TUIProgressHandler, mock_app: Mock) -> None:
        """Test that start initializes progress tracking."""
        progress_handler.start("Test operation", 100)
        assert progress_handler._total == 100
        mock_app.notify.assert_called_once_with(
            message="Test operation started",
            severity="information",
            timeout=2,
        )

    def test_tui_progress_handler_update_updates_progress(self, progress_handler: TUIProgressHandler) -> None:
        """Test that update updates progress."""
        progress_handler._total = 100
        progress_handler.update(50, "Halfway there")

    def test_tui_progress_handler_complete_finalizes_progress(self, progress_handler: TUIProgressHandler, mock_app: Mock) -> None:
        """Test that complete finalizes progress."""
        progress_handler.complete("All done!")
        mock_app.notify.assert_called_once_with(
            message="All done!",
            severity="information",
            timeout=2,
        )

    def test_tui_progress_handler_complete_without_message(self, progress_handler: TUIProgressHandler, mock_app: Mock) -> None:
        """Test that complete works without message."""
        progress_handler.complete()
        mock_app.notify.assert_called_once_with(
            message="Complete",
            severity="information",
            timeout=2,
        )


class TestTUINotificationHandler:
    """Tests for TUI notification handler."""

    @pytest.fixture
    def mock_app(self) -> Mock:
        """Create mock Textual app."""
        mock = Mock(spec=App)
        mock.notify = Mock()
        return mock

    @pytest.fixture
    def notification_handler(self, mock_app: Mock) -> TUINotificationHandler:
        """Create TUI notification handler."""
        return TUINotificationHandler(mock_app)

    def test_tui_notification_handler_implements_protocol(self, notification_handler: TUINotificationHandler) -> None:
        """Test that TUINotificationHandler implements NotificationHandler protocol."""
        assert hasattr(notification_handler, 'show')
        assert callable(notification_handler.show)

    def test_tui_notification_handler_shows_notification(self, notification_handler: TUINotificationHandler, mock_app: Mock) -> None:
        """Test that show displays notification."""
        notification = Notification(
            notification_type=NotificationType.INFO,
            message="Test notification",
        )
        notification_handler.show(notification)
        mock_app.notify.assert_called_once_with(
            message="Test notification",
            severity="information",
            title=None,
        )

    def test_tui_notification_handler_maps_notification_types(self, notification_handler: TUINotificationHandler, mock_app: Mock) -> None:
        """Test that notification types map to correct severity."""
        test_cases = [
            (NotificationType.INFO, "information"),
            (NotificationType.SUCCESS, "information"),
            (NotificationType.WARNING, "warning"),
            (NotificationType.ERROR, "error"),
            (NotificationType.DEBUG, "information"),
        ]

        for notification_type, expected_severity in test_cases:
            mock_app.reset_mock()
            notification = Notification(
                notification_type=notification_type,
                message=f"Test {notification_type}",
            )
            notification_handler.show(notification)
            mock_app.notify.assert_called_once()
            call_kwargs = mock_app.notify.call_args.kwargs
            assert call_kwargs["severity"] == expected_severity

    def test_tui_notification_handler_includes_title_from_details(self, notification_handler: TUINotificationHandler, mock_app: Mock) -> None:
        """Test that notification handler includes title from details."""
        notification = Notification(
            notification_type=NotificationType.INFO,
            message="Test notification",
            details={"title": "Test Title"},
        )
        notification_handler.show(notification)
        mock_app.notify.assert_called_once_with(
            message="Test notification",
            severity="information",
            title="Test Title",
        )
