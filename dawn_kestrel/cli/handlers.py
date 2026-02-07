"""CLI I/O handlers using Click and Rich.

This module provides concrete implementations of the I/O handler protocols
specifically designed for CLI applications using Click and Rich.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)

from dawn_kestrel.interfaces.io import (
    Notification,
    NotificationHandler,
    NotificationType,
    IOHandler,
    ProgressHandler,
)

if TYPE_CHECKING:
    from rich.progress import TaskID


class CLIIOHandler(IOHandler):
    """Click-based I/O handler for CLI applications.

    This implementation uses Click's prompt and confirm functions for
    user interaction in command-line interfaces.
    """

    def __init__(self) -> None:
        """Initialize CLI I/O handler with Rich Console."""
        self.console = Console()

    async def prompt(self, message: str, default: str | None = None) -> str:
        """Prompt user for text input using Click.

        Args:
            message: The prompt message to display.
            default: Optional default value if user provides no input.

        Returns:
            The user's input string.
        """
        return click.prompt(message, default=default, show_default=True)

    async def confirm(self, message: str, default: bool = False) -> bool:
        """Ask user for yes/no confirmation using Click.

        Args:
            message: The confirmation message.
            default: Default value if user provides no input.

        Returns:
            True if user confirms, False otherwise.
        """
        return click.confirm(message, default=default)

    async def select(self, message: str, options: list[str]) -> str:
        """Prompt user to select from a numbered list of options.

        Args:
            message: The prompt message.
            options: List of available options.

        Returns:
            The selected option string.
        """
        if not options:
            raise ValueError("Options list cannot be empty")

        self.console.print(f"\n{message}")
        for i, option in enumerate(options, start=1):
            self.console.print(f"  {i}. {option}")

        choice_input = click.prompt("Enter choice number", type=int)

        choice_index = int(choice_input)

        if not 1 <= choice_index <= len(options):
            raise ValueError(f"Choice must be between 1 and {len(options)}")

        return options[choice_index - 1]

    async def multi_select(self, message: str, options: list[str]) -> list[str]:
        """Prompt user to select multiple options from a numbered list.

        Args:
            message: The prompt message.
            options: List of available options.

        Returns:
            List of selected option strings.
        """
        if not options:
            raise ValueError("Options list cannot be empty")

        self.console.print(f"\n{message}")
        self.console.print("  0. all")
        for i, option in enumerate(options, start=1):
            self.console.print(f"  {i}. {option}")

        choices_input = click.prompt("Enter choice numbers")

        if choices_input.strip().lower() == "all" or choices_input.strip() == "0":
            return options.copy()

        try:
            choice_indices = [int(x.strip()) for x in choices_input.split(",")]
        except ValueError:
            raise ValueError("Invalid input. Enter numbers separated by commas.")

        for index in choice_indices:
            if not 1 <= index <= len(options):
                raise ValueError(f"Choice {index} must be between 1 and {len(options)}")

        return [options[i - 1] for i in choice_indices]


class CLINotificationHandler(NotificationHandler):
    """Rich-based notification handler for CLI applications.

    This implementation uses Rich Console to display notifications with
    color coding based on notification type.
    """

    def __init__(self) -> None:
        """Initialize CLI notification handler with Rich Console."""
        self.console = Console()

    def show(self, notification: Notification) -> None:
        """Display a notification with color coding.

        Args:
            notification: The Notification object to display.
        """
        color_map = {
            NotificationType.INFO: "cyan",
            NotificationType.SUCCESS: "green",
            NotificationType.WARNING: "yellow",
            NotificationType.ERROR: "red",
            NotificationType.DEBUG: "gray",
        }

        notification_type_str = (
            notification.notification_type.value
            if isinstance(notification.notification_type, NotificationType)
            else str(notification.notification_type)
        )

        color = color_map.get(notification.notification_type, "white")

        self.console.print(
            f"[{color}]{notification.message}[/{color}]",
        )

        if notification.details:
            for key, value in notification.details.items():
                self.console.print(f"  [dim]{key}: {value}[/dim]")


class CLIProgressHandler(ProgressHandler):
    """Rich-based progress handler for CLI applications.

    This implementation uses Rich Progress to display progress bars
    for long-running operations.
    """

    def __init__(self) -> None:
        """Initialize CLI progress handler."""
        self.progress: Progress | None = None
        self.task_id: TaskID | None = None
        self.console = Console()

    def start(self, operation: str, total: int) -> None:
        """Start a new progress operation.

        Args:
            operation: Description of the operation being tracked.
            total: Total number of items/steps to complete.
        """
        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0}%"),
            TimeRemainingColumn(),
            console=self.console,
        )

        self.progress.start()

        self.task_id = self.progress.add_task(operation, total=total)

    def update(self, current: int, message: str | None = None) -> None:
        """Update progress for current operation.

        Args:
            current: Current progress value.
            message: Optional status message to display.
        """
        if self.progress is None or self.task_id is None:
            return

        if message:
            self.progress.update(self.task_id, completed=current, description=message)
        else:
            self.progress.update(self.task_id, completed=current)

    def complete(self, message: str | None = None) -> None:
        """Mark the current operation as complete.

        Args:
            message: Optional completion message to display.
        """
        if self.progress is None:
            return

        self.progress.stop()
        self.progress = None

        if message:
            self.console.print(f"[green]✓ {message}[/green]")
        else:
            self.console.print("[green]✓ Complete[/green]")
