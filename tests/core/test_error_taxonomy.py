"""Tests for error taxonomy (categories and codes).

Tests verify that exceptions provide:
- ErrorCategory enum for classification
- error_code field for specific error identification
- category field for observability use cases
- Backward compatibility with existing exceptions
"""

import pytest


class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_error_category_is_str_enum(self):
        """ErrorCategory is a StrEnum for easy serialization."""
        from dawn_kestrel.core.exceptions import ErrorCategory

        assert isinstance(ErrorCategory.RATE_LIMIT.value, str)

    def test_error_category_has_required_values(self):
        """ErrorCategory has all required category values."""
        from dawn_kestrel.core.exceptions import ErrorCategory

        assert ErrorCategory.RATE_LIMIT.value == "RATE_LIMIT"
        assert ErrorCategory.TIMEOUT.value == "TIMEOUT"
        assert ErrorCategory.TOOL_ERROR.value == "TOOL_ERROR"
        assert ErrorCategory.INVALID_CONTEXT.value == "INVALID_CONTEXT"
        assert ErrorCategory.ASSERTION_FAIL.value == "ASSERTION_FAIL"
        assert ErrorCategory.SECURITY_VIOLATION.value == "SECURITY_VIOLATION"

    def test_error_category_has_unknown_default(self):
        """ErrorCategory has UNKNOWN for unclassified errors."""
        from dawn_kestrel.core.exceptions import ErrorCategory

        assert ErrorCategory.UNKNOWN.value == "UNKNOWN"

    def test_error_category_string_serialization(self):
        """ErrorCategory can be serialized to string easily."""
        from dawn_kestrel.core.exceptions import ErrorCategory

        category = ErrorCategory.RATE_LIMIT
        assert str(category) == "RATE_LIMIT"
        assert f"{category}" == "RATE_LIMIT"


class TestOpenCodeErrorCategory:
    """Test category field on OpenCodeError base class."""

    def test_open_code_error_has_category_field(self):
        """OpenCodeError has a category field."""
        from dawn_kestrel.core.exceptions import ErrorCategory, OpenCodeError

        error = OpenCodeError("test error")
        assert hasattr(error, "category")
        assert error.category == ErrorCategory.UNKNOWN

    def test_open_code_error_category_can_be_set(self):
        """OpenCodeError category can be specified."""
        from dawn_kestrel.core.exceptions import ErrorCategory, OpenCodeError

        error = OpenCodeError("rate limited", category=ErrorCategory.RATE_LIMIT)
        assert error.category == ErrorCategory.RATE_LIMIT

    def test_open_code_error_has_error_code_field(self):
        """OpenCodeError has an error_code field."""
        from dawn_kestrel.core.exceptions import OpenCodeError

        error = OpenCodeError("test error")
        assert hasattr(error, "error_code")
        assert error.error_code is None

    def test_open_code_error_code_can_be_set(self):
        """OpenCodeError error_code can be specified."""
        from dawn_kestrel.core.exceptions import OpenCodeError

        error = OpenCodeError("specific error", error_code="ERR_001")
        assert error.error_code == "ERR_001"

    def test_open_code_error_with_both_fields(self):
        """OpenCodeError can have both category and error_code."""
        from dawn_kestrel.core.exceptions import ErrorCategory, OpenCodeError

        error = OpenCodeError(
            "timeout error",
            category=ErrorCategory.TIMEOUT,
            error_code="TIMEOUT_001",
        )
        assert error.category == ErrorCategory.TIMEOUT
        assert error.error_code == "TIMEOUT_001"


class TestSubclassCompatibility:
    """Test that existing exception subclasses work with new fields."""

    def test_session_error_with_category(self):
        """SessionError can have category set."""
        from dawn_kestrel.core.exceptions import ErrorCategory, SessionError

        error = SessionError("session not found", category=ErrorCategory.INVALID_CONTEXT)
        assert error.category == ErrorCategory.INVALID_CONTEXT
        assert isinstance(error, SessionError)

    def test_message_error_with_error_code(self):
        """MessageError can have error_code set."""
        from dawn_kestrel.core.exceptions import MessageError

        error = MessageError("invalid message", error_code="MSG_001")
        assert error.error_code == "MSG_001"
        assert isinstance(error, MessageError)

    def test_tool_execution_error_with_both(self):
        """ToolExecutionError can have both fields."""
        from dawn_kestrel.core.exceptions import ErrorCategory, ToolExecutionError

        error = ToolExecutionError(
            "tool failed",
            category=ErrorCategory.TOOL_ERROR,
            error_code="TOOL_EXEC_001",
        )
        assert error.category == ErrorCategory.TOOL_ERROR
        assert error.error_code == "TOOL_EXEC_001"

    def test_subclass_default_category_is_unknown(self):
        """Subclasses default to UNKNOWN category."""
        from dawn_kestrel.core.exceptions import ErrorCategory, SessionError

        error = SessionError("error")
        assert error.category == ErrorCategory.UNKNOWN

    def test_backward_compatibility_no_args(self):
        """Existing code without new fields still works."""
        from dawn_kestrel.core.exceptions import (
            IOHandlerError,
            MessageError,
            NotificationError,
            OpenCodeError,
            PromptError,
            SessionError,
            ToolExecutionError,
        )

        # All existing exceptions should work without new fields
        errors = [
            OpenCodeError("base error"),
            SessionError("session error"),
            MessageError("message error"),
            ToolExecutionError("tool error"),
            IOHandlerError("io error"),
            PromptError("prompt error"),
            NotificationError("notification error"),
        ]

        for error in errors:
            assert str(error) is not None


class TestErrorStrRepresentation:
    """Test string representation of errors with new fields."""

    def test_error_str_includes_message(self):
        """Error string includes the message."""
        from dawn_kestrel.core.exceptions import OpenCodeError

        error = OpenCodeError("test error message")
        assert "test error message" in str(error)

    def test_error_repr_includes_category_when_set(self):
        """Error repr includes category when not UNKNOWN."""
        from dawn_kestrel.core.exceptions import ErrorCategory, OpenCodeError

        error = OpenCodeError("error", category=ErrorCategory.RATE_LIMIT)
        repr_str = repr(error)
        assert "RATE_LIMIT" in repr_str

    def test_error_repr_includes_error_code_when_set(self):
        """Error repr includes error_code when set."""
        from dawn_kestrel.core.exceptions import OpenCodeError

        error = OpenCodeError("error", error_code="ERR_001")
        repr_str = repr(error)
        assert "ERR_001" in repr_str


class TestCategoryMapping:
    """Test error category mapping for observability."""

    def test_category_to_string_for_metrics(self):
        """Category can be used as metric label."""
        from dawn_kestrel.core.exceptions import ErrorCategory

        category = ErrorCategory.TIMEOUT
        metric_label = str(category).lower()
        assert metric_label == "timeout"

    def test_error_code_pattern_matches_result(self):
        """Error codes align with Result.Err code pattern."""
        from dawn_kestrel.core.exceptions import OpenCodeError
        from dawn_kestrel.core.result import Err

        # Both should support error codes as strings
        exception = OpenCodeError("error", error_code="ERR_001")
        result_err = Err("error", code="ERR_001")

        assert exception.error_code == result_err.code

    def test_categories_for_different_error_types(self):
        """Different error types map to appropriate categories."""
        from dawn_kestrel.core.exceptions import (
            ErrorCategory,
            MessageError,
            NotificationError,
            PromptError,
            SessionError,
            ToolExecutionError,
        )

        # Typical category mappings
        assert (
            SessionError("...", category=ErrorCategory.INVALID_CONTEXT).category
            == ErrorCategory.INVALID_CONTEXT
        )
        assert (
            ToolExecutionError("...", category=ErrorCategory.TOOL_ERROR).category
            == ErrorCategory.TOOL_ERROR
        )
        assert (
            MessageError("...", category=ErrorCategory.RATE_LIMIT).category
            == ErrorCategory.RATE_LIMIT
        )

        # I/O errors might use TIMEOUT
        assert PromptError("...", category=ErrorCategory.TIMEOUT).category == ErrorCategory.TIMEOUT
        assert (
            NotificationError("...", category=ErrorCategory.TIMEOUT).category
            == ErrorCategory.TIMEOUT
        )
