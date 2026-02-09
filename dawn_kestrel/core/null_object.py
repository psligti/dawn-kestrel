"""Null Object pattern for optional dependencies.

This module provides null implementations for I/O, progress, and notification
handlers that eliminate null checks in client code.
"""

from typing import Any

from dawn_kestrel.interfaces.io import (
    IOHandler,
    ProgressHandler,
    NotificationHandler,
)


class NullIOHandler(IOHandler):
    """Null object for IOHandler.

    Provides safe default when IO handler is None.
    All methods are no-ops that return default values.
    """

    async def prompt(self, message: str, default: str | None = None) -> str:
        """Prompt user for text input.

        Args:
            message: The prompt message to display.
            default: Optional default value.

        Returns:
            The default value or empty string.
        """
        return default if default is not None else ""

    async def confirm(self, message: str, default: bool = False) -> bool:
        """Ask user for yes/no confirmation.

        Args:
            message: The confirmation message.
            default: Default value.

        Returns:
            The default value.
        """
        return default

    async def select(self, message: str, options: list[str]) -> str:
        """Prompt user to select from a numbered list of options.

        Args:
            message: The prompt message.
            options: List of available options.

        Returns:
            The first option or empty string if no options.
        """
        return options[0] if options else ""

    async def multi_select(self, message: str, options: list[str]) -> list[str]:
        """Prompt user to select multiple options from a numbered list.

        Args:
            message: The prompt message.
            options: List of available options.

        Returns:
            Empty list (no selections).
        """
        return []


class NullProgressHandler(ProgressHandler):
    """Null object for ProgressHandler.

    Provides safe default when progress handler is None.
    All methods are no-ops.
    """

    def start(self, operation: str, total: int) -> None:
        """Start a new progress operation.

        Args:
            operation: Description of the operation.
            total: Total number of items/steps.
        """
        pass

    def update(self, current: int, message: str | None = None) -> None:
        """Update progress for current operation.

        Args:
            current: Current progress value.
            message: Optional status message.
        """
        pass

    def complete(self, message: str | None = None) -> None:
        """Mark the current operation as complete.

        Args:
            message: Optional completion message.
        """
        pass


class NullNotificationHandler(NotificationHandler):
    """Null object for NotificationHandler.

    Provides safe default when notification handler is None.
    All methods are no-ops.
    """

    def show(self, notification: Any) -> None:
        """Display a notification.

        Args:
            notification: The Notification object to display.
        """
        pass


def get_null_handler(
    handler_type: str,
    handler: IOHandler | ProgressHandler | NotificationHandler | None,
) -> IOHandler | ProgressHandler | NotificationHandler:
    """Get null handler for type, returning existing handler if not None.

    This factory function provides a convenient way to get a null handler
    when the handler parameter is None, or return the existing handler
    if one is provided.

    Args:
        handler_type: Type of handler ("io", "progress", "notification").
        handler: Existing handler or None.

    Returns:
        Null handler or existing handler.

    Raises:
        ValueError: If handler_type is unknown.

    Examples:
        >>> # Get null IO handler
        >>> handler = get_null_handler("io", None)
        >>> # Use existing handler
        >>> handler = get_null_handler("io", existing_handler)
    """
    if handler is not None:
        return handler

    if handler_type == "io":
        return NullIOHandler()
    elif handler_type == "progress":
        return NullProgressHandler()
    elif handler_type == "notification":
        return NullNotificationHandler()
    else:
        raise ValueError(f"Unknown handler type: {handler_type}")
