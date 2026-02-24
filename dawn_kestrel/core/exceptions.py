"""Domain-specific exceptions for dawn_kestrel.

This module defines the exception hierarchy for domain-specific errors
that occur during session management, message handling, and I/O operations.
"""

from enum import StrEnum


class ErrorCategory(StrEnum):
    """Classification categories for errors.

    Categories map to observability use cases (metrics, logging, tracing).
    Each error has a category for high-level classification and an
    error_code for specific identification.
    """

    UNKNOWN = "UNKNOWN"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    TOOL_ERROR = "TOOL_ERROR"
    INVALID_CONTEXT = "INVALID_CONTEXT"
    ASSERTION_FAIL = "ASSERTION_FAIL"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"


class OpenCodeError(Exception):
    """Base exception for all dawn_kestrel errors.

    All domain-specific exceptions should inherit from this class.

    Args:
        message: Error description.
        category: High-level error classification for observability.
        error_code: Specific error identifier for detailed categorization.
    """

    def __init__(
        self,
        message: str,
        *,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.error_code = error_code

    def __repr__(self) -> str:
        parts = [f"{self.__class__.__name__}({self.args[0]!r}"]
        if self.category != ErrorCategory.UNKNOWN:
            parts.append(f", category={self.category}")
        if self.error_code is not None:
            parts.append(f", error_code={self.error_code!r}")
        parts.append(")")
        return "".join(parts)


class SessionError(OpenCodeError):
    """Exception raised when session operations fail.

    This includes errors when creating, retrieving, updating,
    or deleting sessions.
    """


class MessageError(OpenCodeError):
    """Exception raised when message operations fail.

    This includes errors when creating, updating, or
    deleting messages within sessions.
    """


class ToolExecutionError(OpenCodeError):
    """Exception raised when tool execution fails.

    This includes errors when invoking tools, handling tool
    responses, or processing tool outputs.
    """


class IOHandlerError(OpenCodeError):
    """Base exception for I/O handler errors.

    This is a parent class for errors that occur during
    I/O operations through handlers.
    """


class PromptError(IOHandlerError):
    """Exception raised when prompt operations fail.

    This includes errors when prompting for input,
    confirming actions, or selecting options.
    """


class NotificationError(IOHandlerError):
    """Exception raised when notification operations fail.

    This includes errors when displaying notifications
    or handling notification events.
    """
