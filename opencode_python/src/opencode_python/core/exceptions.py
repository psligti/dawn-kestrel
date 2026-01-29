"""Domain-specific exceptions for opencode_python.

This module defines the exception hierarchy for domain-specific errors
that occur during session management, message handling, and I/O operations.
"""


class OpenCodeError(Exception):
    """Base exception for all opencode_python errors.

    All domain-specific exceptions should inherit from this class.
    """


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
