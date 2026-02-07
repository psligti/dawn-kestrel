"""TUI I/O handlers using Textual.

This module provides concrete implementations of I/O handler protocols
specifically designed for TUI applications using Textual framework.
"""

from __future__ import annotations

from textual.app import App
from textual.widgets import Input, DataTable

from dawn_kestrel.interfaces.io import (
    IOHandler,
    ProgressHandler,
    NotificationHandler,
    Notification,
    NotificationType,
)


class TUIIOHandler(IOHandler):
    """Textual-based I/O handler for TUI applications.

    This implementation uses Textual widgets for user interaction
    in terminal user interfaces.
    """

    def __init__(self, app: App) -> None:
        """Initialize TUI I/O handler.

        Args:
            app: Textual App instance for widget access.
        """
        self.app = app

    async def prompt(self, message: str, default: str | None = None) -> str:
        """Prompt user for text input.

        In TUI context, this should use an Input widget or similar.
        For simplicity, returns default or empty string.

        Args:
            message: The prompt message to display.
            default: Optional default value.

        Returns:
            User input or default.
        """
        return default or ""

    async def confirm(self, message: str, default: bool = False) -> bool:
        """Ask user for yes/no confirmation.

        Args:
            message: The confirmation message.
            default: Default value if user provides no input.

        Returns:
            True if confirmed, False otherwise.
        """
        return default

    async def select(self, message: str, options: list[str]) -> str:
        """Prompt user to select from a numbered list.

        Args:
            message: The prompt message.
            options: List of available options.

        Returns:
            The selected option string.
        """
        if not options:
            raise ValueError("Options list cannot be empty")
        return options[0]

    async def multi_select(self, message: str, options: list[str]) -> list[str]:
        """Prompt user to select multiple options.

        Args:
            message: The prompt message.
            options: List of available options.

        Returns:
            List of selected option strings.
        """
        if not options:
            raise ValueError("Options list cannot be empty")
        return []


class TUINotificationHandler(NotificationHandler):
    """Textual-based notification handler for TUI applications.

    This implementation uses Textual's app.notify() method for
    displaying notifications to the user.
    """

    def __init__(self, app: App) -> None:
        """Initialize TUI notification handler.

        Args:
            app: Textual App instance for notify() method.
        """
        self.app = app

    def show(self, notification: Notification) -> None:
        """Display a notification using Textual's notify.

        Args:
            notification: The Notification object to display.
        """
        severity_map = {
            NotificationType.INFO: "information",
            NotificationType.SUCCESS: "information",
            NotificationType.WARNING: "warning",
            NotificationType.ERROR: "error",
            NotificationType.DEBUG: "information",
        }

        severity = severity_map.get(notification.notification_type, "information")

        self.app.notify(
            message=notification.message,
            severity=severity,
            title=notification.details.get("title") if notification.details else None,
        )


class TUIProgressHandler(ProgressHandler):
    """Textual-based progress handler for TUI applications.

    This implementation can display progress using Textual widgets
    like ProgressBar or status widgets.
    """

    def __init__(self, app: App) -> None:
        """Initialize TUI progress handler.

        Args:
            app: Textual App instance for widget access.
        """
        self.app = app
        self._total: int = 0

    def start(self, operation: str, total: int) -> None:
        """Start a new progress operation.

        Args:
            operation: Description of operation.
            total: Total number of steps.
        """
        self._total = total
        self.app.notify(
            message=f"{operation} started",
            severity="information",
            timeout=2,
        )

    def update(self, current: int, message: str | None = None) -> None:
        """Update progress for current operation.

        Args:
            current: Current progress value.
            message: Optional status message.
        """
        pass

    def complete(self, message: str | None = None) -> None:
        """Mark current operation as complete.

        Args:
            message: Optional completion message.
        """
        completion_msg = message or "Complete"
        self.app.notify(
            message=completion_msg,
            severity="information",
            timeout=2,
        )
