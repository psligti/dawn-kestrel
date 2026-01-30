"""OpenCode Python - Command Palette Manager for TUI

Manages command palette with action registration, permissions, and event handling.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Set

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static, ListView, ListItem
from textual.containers import Vertical
from textual.message import Message


class CommandExecute(Message):
    """Emitted when a command should be executed."""

    def __init__(self, action: str, data: dict) -> None:
        super().__init__()
        self.action = action
        self.data = data


class PaletteOpen(Message):
    """Emitted when command palette is opened."""
    pass


logger = logging.getLogger(__name__)


class CommandAction:
    """Represents a single command action."""

    def __init__(
        self,
        value: str,
        title: str,
        description: str,
        permissions: Optional[Set[str]] = None,
        category: str = "general",
    ):
        """Initialize command action.

        Args:
            value: Unique command identifier.
            title: Display title for command.
            description: Command description.
            permissions: Required permissions to show this command.
            category: Command category for grouping.
        """
        self.value = value
        self.title = title
        self.description = description
        self.permissions = permissions or set()
        self.category = category

    def matches(self, query: str) -> bool:
        """Check if command matches search query.

        Args:
            query: Search query string.

        Returns:
            True if command matches query.
        """
        query = query.lower()
        return query in self.title.lower() or query in self.description.lower()

    def has_permission(self, user_permissions: Set[str]) -> bool:
        """Check if user has required permissions.

        Args:
            user_permissions: User's permission set.

        Returns:
            True if user has all required permissions.
        """
        return self.permissions.issubset(user_permissions)


class CommandPalette(ModalScreen[str]):
    """Enhanced command palette with permissions and action management."""

    def __init__(
        self,
        actions: Optional[List[CommandAction]] = None,
        user_permissions: Optional[Set[str]] = None,
        on_execute: Optional[Callable[[str], None]] = None,
    ):
        """Initialize command palette.

        Args:
            actions: List of available command actions.
            user_permissions: User's permission set for filtering.
            on_execute: Callback when action is executed.
        """
        super().__init__()
        self.actions = actions or []
        self.user_permissions = user_permissions or set()
        self.on_execute = on_execute
        self._result: Optional[str] = None
        self._filtered_actions: List[CommandAction] = []
        self._selected_index: int = 0

    def compose(self) -> ComposeResult:
        """Compose command palette UI."""
        yield Label("Command Palette")

        yield Input(placeholder="Type to search...", id="palette_search")

        yield ListView(id="palette_list")

        yield Static("Press Enter to execute, Escape to cancel")

    def on_mount(self) -> None:
        """Called when palette is mounted."""
        self._filter_actions("")

        list_view = self.query_one(ListView)
        list_view.focus()

        # Focus search input
        search_input = self.query_one(Input)
        search_input.focus()

        # Emit palette:open event
        self.post_message(PaletteOpen(self))

    def _filter_actions(self, query: str) -> None:
        """Filter actions by search query and permissions.

        Args:
            query: Search query string.
        """
        self._filtered_actions = [
            action
            for action in self.actions
            if action.matches(query) and action.has_permission(self.user_permissions)
        ]

        # Rebuild list view
        list_view = self.query_one(ListView)
        list_view.clear()

        for action in self._filtered_actions:
            list_view.append(
                ListItem(
                    Static(f"[bold]{action.title}[/bold]\n[dim]{action.description}[/dim]")
                )
            )

        self._selected_index = 0
        if self._filtered_actions and list_view.children:
            list_view.index = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for filtering.

        Args:
            event: Input.Changed event.
        """
        self._filter_actions(event.value)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list selection.

        Args:
            event: ListView.Selected event.
        """
        if self._filtered_actions:
            self._selected_index = event.list_view.index
            self._execute_action()

    def _execute_action(self) -> None:
        """Execute selected action."""
        if not self._filtered_actions or self._selected_index >= len(self._filtered_actions):
            return

        action = self._filtered_actions[self._selected_index]

        # Emit command:execute event
        self.post_message(
            CommandExecute(
                action=action.value,
                data={"title": action.title}
            )
        )

        # Call callback
        if self.on_execute:
            self.on_execute(action.value)

        self.dismiss(action.value)

    def action_enter(self) -> None:
        """Handle Enter key - execute selected action."""
        self._execute_action()

    def action_escape(self) -> None:
        """Handle Escape key - close without execution."""
        self.dismiss(None)


class CommandPaletteManager:
    """Manages command palette actions and state."""

    def __init__(self):
        """Initialize command palette manager."""
        self._actions: Dict[str, CommandAction] = {}
        self._categories: Dict[str, List[str]] = {}

    def register_action(
        self,
        value: str,
        title: str,
        description: str,
        permissions: Optional[Set[str]] = None,
        category: str = "general",
    ) -> CommandAction:
        """Register a new command action.

        Args:
            value: Unique command identifier.
            title: Display title.
            description: Command description.
            permissions: Required permissions.
            category: Command category.

        Returns:
            Registered CommandAction.
        """
        action = CommandAction(value, title, description, permissions, category)
        self._actions[value] = action

        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(value)

        logger.debug(f"Registered action: {value} ({title})")
        return action

    def unregister_action(self, value: str) -> bool:
        """Unregister a command action.

        Args:
            value: Command identifier to unregister.

        Returns:
            True if action was removed, False if not found.
        """
        if value in self._actions:
            action = self._actions[value]
            category = action.category

            del self._actions[value]

            if category in self._categories and value in self._categories[category]:
                self._categories[category].remove(value)

            logger.debug(f"Unregistered action: {value}")
            return True
        return False

    def get_action(self, value: str) -> Optional[CommandAction]:
        """Get action by value.

        Args:
            value: Command identifier.

        Returns:
            CommandAction if found, None otherwise.
        """
        return self._actions.get(value)

    def get_all_actions(self) -> List[CommandAction]:
        """Get all registered actions.

        Returns:
            List of all CommandAction objects.
        """
        return list(self._actions.values())

    def get_actions_by_category(self, category: str) -> List[CommandAction]:
        """Get actions by category.

        Args:
            category: Category name.

        Returns:
            List of CommandAction objects in category.
        """
        if category not in self._categories:
            return []

        return [
            self._actions[value]
            for value in self._categories[category]
            if value in self._actions
        ]

    def filter_actions(
        self,
        query: str = "",
        user_permissions: Optional[set] = None,
    ) -> List[CommandAction]:
        """Filter actions by query and permissions.

        Args:
            query: Search query string.
            user_permissions: User's permission set.

        Returns:
            Filtered list of CommandAction objects.
        """
        permissions = user_permissions or set()

        return [
            action
            for action in self._actions.values()
            if action.matches(query) and action.has_permission(permissions)
        ]


# Global command palette manager instance
manager = CommandPaletteManager()


def register_default_actions() -> None:
    """Register default command palette actions."""
    # Session actions
    manager.register_action(
        "new_session",
        "New Session",
        "Create a new session",
        category="sessions"
    )

    manager.register_action(
        "list_sessions",
        "List Sessions",
        "View all sessions",
        category="sessions"
    )

    # Settings actions
    manager.register_action(
        "settings",
        "Settings",
        "Open application settings",
        category="settings"
    )

    manager.register_action(
        "providers",
        "Providers",
        "Manage AI providers",
        category="settings"
    )

    # Theme actions
    manager.register_action(
        "theme",
        "Select Theme",
        "Change visual theme",
        category="settings"
    )

    # Quit
    manager.register_action(
        "quit",
        "Quit",
        "Exit the application",
        category="general"
    )
