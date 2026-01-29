"""Tests for HTTP client and domain exceptions.

Tests HTTPClientError initialization, string representation,
and exception raising/catching behavior, plus domain-specific
exceptions from opencode_python.core.exceptions.
"""

import pytest

from opencode_python.core.http_client import HTTPClientError
from opencode_python.core.exceptions import (
    OpenCodeError,
    SessionError,
    MessageError,
    ToolExecutionError,
    IOHandlerError,
    PromptError,
    NotificationError,
)


class TestHTTPClientError:
    """Tests for HTTPClientError exception."""

    def test_initialization_with_message_only(self) -> None:
        """Test HTTPClientError initialization with message only."""
        error = HTTPClientError("Test error message")
        assert error.message == "Test error message"
        assert error.status_code is None
        assert error.retry_count == 0

    def test_initialization_with_status_code(self) -> None:
        """Test HTTPClientError initialization with status code."""
        error = HTTPClientError("Not found", status_code=404)
        assert error.message == "Not found"
        assert error.status_code == 404
        assert error.retry_count == 0

    def test_initialization_with_retry_count(self) -> None:
        """Test HTTPClientError initialization with retry count."""
        error = HTTPClientError("Failed after retries", retry_count=3)
        assert error.message == "Failed after retries"
        assert error.status_code is None
        assert error.retry_count == 3

    def test_initialization_with_all_fields(self) -> None:
        """Test HTTPClientError initialization with all fields."""
        error = HTTPClientError(
            message="Server error",
            status_code=500,
            retry_count=2
        )
        assert error.message == "Server error"
        assert error.status_code == 500
        assert error.retry_count == 2

    def test_string_representation(self) -> None:
        """Test HTTPClientError string representation."""
        error = HTTPClientError("Test error")
        assert str(error) == "Test error"

    def test_exception_can_be_raised_and_caught(self) -> None:
        """Test that HTTPClientError can be raised and caught."""
        with pytest.raises(HTTPClientError) as exc_info:
            raise HTTPClientError("Raised error")

        assert str(exc_info.value) == "Raised error"
        assert exc_info.value.message == "Raised error"


class TestOpenCodeError:
    """Tests for OpenCodeError base exception."""

    def test_can_be_raised_with_message(self) -> None:
        """Test that OpenCodeError can be raised with message."""
        error = OpenCodeError("Base error")
        assert str(error) == "Base error"

    def test_can_be_caught_as_base_class(self) -> None:
        """Test that subclass exceptions can be caught as OpenCodeError."""
        with pytest.raises(OpenCodeError) as exc_info:
            raise SessionError("Session failed")

        assert isinstance(exc_info.value, OpenCodeError)


class TestSessionError:
    """Tests for SessionError exception."""

    def test_inherits_from_open_code_error(self) -> None:
        """Test that SessionError inherits from OpenCodeError."""
        error = SessionError("Session not found")
        assert isinstance(error, OpenCodeError)

    def test_can_be_raised_and_caught(self) -> None:
        """Test that SessionError can be raised and caught."""
        with pytest.raises(SessionError) as exc_info:
            raise SessionError("Session not found")

        assert str(exc_info.value) == "Session not found"


class TestMessageError:
    """Tests for MessageError exception."""

    def test_inherits_from_open_code_error(self) -> None:
        """Test that MessageError inherits from OpenCodeError."""
        error = MessageError("Message failed")
        assert isinstance(error, OpenCodeError)

    def test_can_be_raised_and_caught(self) -> None:
        """Test that MessageError can be raised and caught."""
        with pytest.raises(MessageError) as exc_info:
            raise MessageError("Message failed")

        assert str(exc_info.value) == "Message failed"


class TestToolExecutionError:
    """Tests for ToolExecutionError exception."""

    def test_inherits_from_open_code_error(self) -> None:
        """Test that ToolExecutionError inherits from OpenCodeError."""
        error = ToolExecutionError("Tool failed")
        assert isinstance(error, OpenCodeError)

    def test_can_be_raised_and_caught(self) -> None:
        """Test that ToolExecutionError can be raised and caught."""
        with pytest.raises(ToolExecutionError) as exc_info:
            raise ToolExecutionError("Tool failed")

        assert str(exc_info.value) == "Tool failed"


class TestIOHandlerError:
    """Tests for IOHandlerError exception."""

    def test_inherits_from_open_code_error(self) -> None:
        """Test that IOHandlerError inherits from OpenCodeError."""
        error = IOHandlerError("I/O failed")
        assert isinstance(error, OpenCodeError)

    def test_can_be_raised_and_caught(self) -> None:
        """Test that IOHandlerError can be raised and caught."""
        with pytest.raises(IOHandlerError) as exc_info:
            raise IOHandlerError("I/O failed")

        assert str(exc_info.value) == "I/O failed"


class TestPromptError:
    """Tests for PromptError exception."""

    def test_inherits_from_io_handler_error(self) -> None:
        """Test that PromptError inherits from IOHandlerError."""
        error = PromptError("Prompt failed")
        assert isinstance(error, IOHandlerError)

    def test_inherits_from_open_code_error(self) -> None:
        """Test that PromptError inherits from OpenCodeError."""
        error = PromptError("Prompt failed")
        assert isinstance(error, OpenCodeError)

    def test_can_be_raised_and_caught(self) -> None:
        """Test that PromptError can be raised and caught."""
        with pytest.raises(PromptError) as exc_info:
            raise PromptError("Prompt failed")

        assert str(exc_info.value) == "Prompt failed"


class TestNotificationError:
    """Tests for NotificationError exception."""

    def test_inherits_from_io_handler_error(self) -> None:
        """Test that NotificationError inherits from IOHandlerError."""
        error = NotificationError("Notification failed")
        assert isinstance(error, IOHandlerError)

    def test_inherits_from_open_code_error(self) -> None:
        """Test that NotificationError inherits from OpenCodeError."""
        error = NotificationError("Notification failed")
        assert isinstance(error, OpenCodeError)

    def test_can_be_raised_and_caught(self) -> None:
        """Test that NotificationError can be raised and caught."""
        with pytest.raises(NotificationError) as exc_info:
            raise NotificationError("Notification failed")

        assert str(exc_info.value) == "Notification failed"
