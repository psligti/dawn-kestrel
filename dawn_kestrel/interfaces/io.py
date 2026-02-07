"""I/O handler protocols for session management.

This module defines the protocols for I/O, progress, and notification
handlers that are used by the SessionService.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Optional, Any
from dataclasses import dataclass
from enum import Enum


class NotificationType(str, Enum):
    """Types of notifications for user feedback."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


class ProgressType(str, Enum):
    """Types of progress operations."""

    SESSION_CREATE = "session_create"
    MESSAGE_CREATE = "message_create"
    TOOL_EXEC = "tool_execution"
    AI_RESPONSE = "ai_response"
    EXPORT = "export"
    IMPORT = "import"


@dataclass
class ProgressUpdate:
    """Progress update data structure.

    Attributes:
        progress_type: The type of progress operation.
        current: Current progress value.
        total: Total progress value.
        message: Optional status message.
    """

    progress_type: ProgressType
    current: int
    total: int
    message: str | None = None


@dataclass
class Notification:
    """Notification data structure.

    Attributes:
        notification_type: The type of notification.
        message: The notification message text.
        details: Optional dictionary of additional details.
        duration: Seconds for TUI (ignored for CLI/SDK).
    """

    notification_type: NotificationType
    message: str
    details: dict[str, Any] | None = None
    duration: int = 3


@runtime_checkable
class IOHandler(Protocol):
    """Protocol for I/O operations.

    This protocol defines the interface for user interaction handlers
    that handle prompts, confirmations, and selections.
    """

    async def prompt(self, message: str, default: str | None = None) -> str:
        """Prompt user for text input.

        Args:
            message: The prompt message to display.
            default: Optional default value.

        Returns:
            The user's input string.
        """
        ...

    async def confirm(self, message: str, default: bool = False) -> bool:
        """Ask user for yes/no confirmation.

        Args:
            message: The confirmation message.
            default: Default value.

        Returns:
            True if user confirms, False otherwise.
        """
        ...

    async def select(self, message: str, options: list[str]) -> str:
        """Prompt user to select from a numbered list of options.

        Args:
            message: The prompt message.
            options: List of available options.

        Returns:
            The selected option string.
        """
        ...

    async def multi_select(self, message: str, options: list[str]) -> list[str]:
        """Prompt user to select multiple options from a numbered list.

        Args:
            message: The prompt message.
            options: List of available options.

        Returns:
            List of selected option strings.
        """
        ...


@runtime_checkable
class ProgressHandler(Protocol):
    """Protocol for progress tracking.

    This protocol defines the interface for progress handlers that
    display operation progress to users.
    """

    def start(self, operation: str, total: int) -> None:
        """Start a new progress operation.

        Args:
            operation: Description of the operation.
            total: Total number of items/steps.
        """
        ...

    def update(self, current: int, message: str | None = None) -> None:
        """Update progress for current operation.

        Args:
            current: Current progress value.
            message: Optional status message.
        """
        ...

    def complete(self, message: str | None = None) -> None:
        """Mark the current operation as complete.

        Args:
            message: Optional completion message.
        """
        ...


@runtime_checkable
class NotificationHandler(Protocol):
    """Protocol for notification display.

    This protocol defines the interface for notification handlers that
    display user feedback and notifications.
    """

    def show(self, notification: Notification) -> None:
        """Display a notification.

        Args:
            notification: The Notification object to display.
        """
        ...


@runtime_checkable
class StateHandler(Protocol):
    """Protocol for UI state management.

    This protocol defines the interface for state handlers that
    manage UI state like current session and working directory.
    """

    def get_current_session_id(self) -> str | None:
        """Get currently selected session ID.

        Returns:
            Session ID string or None if no session selected.
        """
        ...

    def set_current_session_id(self, session_id: str) -> None:
        """Set currently selected session ID.

        Args:
            session_id: Session ID string to set as current.

        Note:
            Should trigger UI update to reflect new selection.
        """
        ...

    def get_work_directory(self) -> str:
        """Get current working directory.

        Returns:
            Current working directory path.
        """
        ...


class QuietIOHandler(IOHandler):
    """No-op I/O handler for headless mode."""

    async def prompt(self, message: str, default: str | None = None) -> str:
        return default if default is not None else ""

    async def confirm(self, message: str, default: bool = False) -> bool:
        return default

    async def select(self, message: str, options: list[str]) -> str:
        return options[0] if options else ""

    async def multi_select(self, message: str, options: list[str]) -> list[str]:
        return []


class NoOpProgressHandler(ProgressHandler):
    """No-op progress handler for silent mode."""

    def start(self, operation: str, total: int) -> None:
        pass

    def update(self, current: int, message: str | None = None) -> None:
        pass

    def complete(self, message: str | None = None) -> None:
        pass


class NoOpNotificationHandler(NotificationHandler):
    """No-op notification handler for silent mode."""

    def show(self, notification: Notification) -> None:
        pass
