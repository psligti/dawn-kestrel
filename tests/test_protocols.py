"""Tests for I/O handler protocols.

Tests protocol definitions and no-op implementations for IOHandler,
ProgressHandler, NotificationHandler, and StateHandler.
"""

import pytest

from dawn_kestrel.interfaces.io import (
    IOHandler,
    ProgressHandler,
    NotificationHandler,
    StateHandler,
    ProgressType,
    ProgressUpdate,
    Notification,
    NotificationType,
    QuietIOHandler,
    NoOpProgressHandler,
    NoOpNotificationHandler,
)


class TestIOHandlerProtocol:
    """Tests for IOHandler protocol."""

    def test_io_handler_protocol_has_prompt_method(self) -> None:
        """Test that IOHandler protocol defines prompt method."""
        assert hasattr(IOHandler, 'prompt')
        assert callable(IOHandler.prompt)

    def test_io_handler_protocol_has_confirm_method(self) -> None:
        """Test that IOHandler protocol defines confirm method."""
        assert hasattr(IOHandler, 'confirm')
        assert callable(IOHandler.confirm)

    def test_io_handler_protocol_has_select_method(self) -> None:
        """Test that IOHandler protocol defines select method."""
        assert hasattr(IOHandler, 'select')
        assert callable(IOHandler.select)

    def test_io_handler_protocol_has_multi_select_method(self) -> None:
        """Test that IOHandler protocol defines multi_select method."""
        assert hasattr(IOHandler, 'multi_select')
        assert callable(IOHandler.multi_select)


class TestProgressHandlerProtocol:
    """Tests for ProgressHandler protocol."""

    def test_progress_handler_protocol_has_start_method(self) -> None:
        """Test that ProgressHandler protocol defines start method."""
        assert hasattr(ProgressHandler, 'start')
        assert callable(ProgressHandler.start)

    def test_progress_handler_protocol_has_update_method(self) -> None:
        """Test that ProgressHandler protocol defines update method."""
        assert hasattr(ProgressHandler, 'update')
        assert callable(ProgressHandler.update)

    def test_progress_handler_protocol_has_complete_method(self) -> None:
        """Test that ProgressHandler protocol defines complete method."""
        assert hasattr(ProgressHandler, 'complete')
        assert callable(ProgressHandler.complete)


class TestNotificationHandlerProtocol:
    """Tests for NotificationHandler protocol."""

    def test_notification_handler_protocol_has_show_method(self) -> None:
        """Test that NotificationHandler protocol defines show method."""
        assert hasattr(NotificationHandler, 'show')
        assert callable(NotificationHandler.show)


class TestStateHandlerProtocol:
    """Tests for StateHandler protocol."""

    def test_state_handler_protocol_has_get_current_session_id_method(self) -> None:
        """Test that StateHandler protocol defines get_current_session_id method."""
        assert hasattr(StateHandler, 'get_current_session_id')
        assert callable(StateHandler.get_current_session_id)

    def test_state_handler_protocol_has_set_current_session_id_method(self) -> None:
        """Test that StateHandler protocol defines set_current_session_id method."""
        assert hasattr(StateHandler, 'set_current_session_id')
        assert callable(StateHandler.set_current_session_id)

    def test_state_handler_protocol_has_get_work_directory_method(self) -> None:
        """Test that StateHandler protocol defines get_work_directory method."""
        assert hasattr(StateHandler, 'get_work_directory')
        assert callable(StateHandler.get_work_directory)


class TestProgressTypeEnum:
    """Tests for ProgressType enum."""

    def test_progress_type_has_session_create(self) -> None:
        """Test that ProgressType has SESSION_CREATE value."""
        assert hasattr(ProgressType, 'SESSION_CREATE')
        assert ProgressType.SESSION_CREATE.value == "session_create"

    def test_progress_type_has_message_create(self) -> None:
        """Test that ProgressType has MESSAGE_CREATE value."""
        assert hasattr(ProgressType, 'MESSAGE_CREATE')
        assert ProgressType.MESSAGE_CREATE.value == "message_create"

    def test_progress_type_has_tool_exec(self) -> None:
        """Test that ProgressType has TOOL_EXEC value."""
        assert hasattr(ProgressType, 'TOOL_EXEC')
        assert ProgressType.TOOL_EXEC.value == "tool_execution"

    def test_progress_type_has_ai_response(self) -> None:
        """Test that ProgressType has AI_RESPONSE value."""
        assert hasattr(ProgressType, 'AI_RESPONSE')
        assert ProgressType.AI_RESPONSE.value == "ai_response"

    def test_progress_type_has_export(self) -> None:
        """Test that ProgressType has EXPORT value."""
        assert hasattr(ProgressType, 'EXPORT')
        assert ProgressType.EXPORT.value == "export"

    def test_progress_type_has_import(self) -> None:
        """Test that ProgressType has IMPORT value."""
        assert hasattr(ProgressType, 'IMPORT')
        assert ProgressType.IMPORT.value == "import"


class TestProgressUpdateDataclass:
    """Tests for ProgressUpdate dataclass."""

    def test_progress_update_has_required_fields(self) -> None:
        """Test that ProgressUpdate has required fields."""
        update = ProgressUpdate(
            progress_type=ProgressType.SESSION_CREATE,
            current=50,
            total=100,
        )
        assert update.progress_type == ProgressType.SESSION_CREATE
        assert update.current == 50
        assert update.total == 100
        assert update.message is None

    def test_progress_update_has_optional_message(self) -> None:
        """Test that ProgressUpdate has optional message field."""
        update = ProgressUpdate(
            progress_type=ProgressType.MESSAGE_CREATE,
            current=10,
            total=20,
            message="Halfway done",
        )
        assert update.message == "Halfway done"


class TestQuietIOHandler:
    """Tests for QuietIOHandler implementation."""

    @pytest.fixture
    def io_handler(self) -> QuietIOHandler:
        """Create QuietIOHandler instance."""
        return QuietIOHandler()

    @pytest.mark.asyncio
    async def test_prompt_returns_default_when_provided(self, io_handler: QuietIOHandler) -> None:
        """Test that prompt returns default value when provided."""
        result = await io_handler.prompt("Enter value", default="test_default")
        assert result == "test_default"

    @pytest.mark.asyncio
    async def test_prompt_returns_empty_string_without_default(self, io_handler: QuietIOHandler) -> None:
        """Test that prompt returns empty string when no default provided."""
        result = await io_handler.prompt("Enter value")
        assert result == ""

    @pytest.mark.asyncio
    async def test_confirm_returns_default_true(self, io_handler: QuietIOHandler) -> None:
        """Test that confirm returns True when default is True."""
        result = await io_handler.confirm("Continue?", default=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_confirm_returns_default_false(self, io_handler: QuietIOHandler) -> None:
        """Test that confirm returns False when default is False."""
        result = await io_handler.confirm("Continue?", default=False)
        assert result is False

    @pytest.mark.asyncio
    async def test_select_returns_first_option(self, io_handler: QuietIOHandler) -> None:
        """Test that select returns first option from list."""
        options = ["option1", "option2", "option3"]
        result = await io_handler.select("Choose one", options)
        assert result == "option1"

    @pytest.mark.asyncio
    async def test_select_returns_empty_string_for_empty_options(self, io_handler: QuietIOHandler) -> None:
        """Test that select returns empty string when options list is empty."""
        result = await io_handler.select("Choose one", [])
        assert result == ""

    @pytest.mark.asyncio
    async def test_multi_select_returns_empty_list(self, io_handler: QuietIOHandler) -> None:
        """Test that multi_select returns empty list."""
        options = ["option1", "option2", "option3"]
        result = await io_handler.multi_select("Choose multiple", options)
        assert result == []


class TestNoOpProgressHandler:
    """Tests for NoOpProgressHandler implementation."""

    @pytest.fixture
    def progress_handler(self) -> NoOpProgressHandler:
        """Create NoOpProgressHandler instance."""
        return NoOpProgressHandler()

    def test_start_does_nothing(self, progress_handler: NoOpProgressHandler) -> None:
        """Test that start method does nothing."""
        # Should not raise any exceptions
        progress_handler.start("Test operation", 100)

    def test_update_does_nothing(self, progress_handler: NoOpProgressHandler) -> None:
        """Test that update method does nothing."""
        # Should not raise any exceptions
        progress_handler.update(50, "Halfway there")

    def test_update_without_message_does_nothing(self, progress_handler: NoOpProgressHandler) -> None:
        """Test that update method without message does nothing."""
        # Should not raise any exceptions
        progress_handler.update(75)

    def test_complete_does_nothing(self, progress_handler: NoOpProgressHandler) -> None:
        """Test that complete method does nothing."""
        # Should not raise any exceptions
        progress_handler.complete("All done!")

    def test_complete_without_message_does_nothing(self, progress_handler: NoOpProgressHandler) -> None:
        """Test that complete method without message does nothing."""
        # Should not raise any exceptions
        progress_handler.complete()


class TestNoOpNotificationHandler:
    """Tests for NoOpNotificationHandler implementation."""

    @pytest.fixture
    def notification_handler(self) -> NoOpNotificationHandler:
        """Create NoOpNotificationHandler instance."""
        return NoOpNotificationHandler()

    def test_show_does_nothing(self, notification_handler: NoOpNotificationHandler) -> None:
        """Test that show method does nothing."""
        notification = Notification(
            notification_type=NotificationType.INFO,
            message="Test notification",
        )
        # Should not raise any exceptions
        notification_handler.show(notification)

    def test_show_with_details_does_nothing(self, notification_handler: NoOpNotificationHandler) -> None:
        """Test that show method with details does nothing."""
        notification = Notification(
            notification_type=NotificationType.ERROR,
            message="Error occurred",
            details={"title": "Error Title", "code": 500},
        )
        # Should not raise any exceptions
        notification_handler.show(notification)
