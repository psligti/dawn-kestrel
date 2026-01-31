"""Drawer Widget for OpenCode TUI"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal, Optional

from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import Button, Static, Label

from opencode_python.core.event_bus import bus, Events
from opencode_python.core.focus_manager import FocusManager, get_focus_manager, FocusState

logger = logging.getLogger(__name__)


class TabButton(Button):
    """Tab button for drawer navigation

    Displays an icon and optional label for a drawer tab.
    Highlighted when active.
    """

    DEFAULT_CSS = """
    TabButton {
        width: 100%;
        height: 3;
        padding: 0 1;
        margin: 0 0 1 0;
        border: none;
        background: transparent;
        text-align: center;
        color: #f3f4f6;
    }

    TabButton:hover {
        background: #1a1d2e;
        color: #10b981;
    }

    TabButton.-active {
        background: #10b981;
        color: #1a1d2e;
        text-style: bold;
    }
    """

    def __init__(self, icon: str, label: Optional[str] = None, **kwargs):
        """Initialize TabButton

        Args:
            icon: Icon character to display
            label: Optional text label
            **kwargs: Additional Button widget arguments
        """
        content = f"{icon}"
        if label:
            content += f" {label}"
        super().__init__(content, **kwargs)


class TodoList(ScrollableContainer):
    """Todo list tab content

    Displays a list of todo items with completion status.
    Placeholder for now - will be connected to actual todo system.
    """

    DEFAULT_CSS = """
    TodoList {
        height: 1fr;
        background: #242838;
    }

    TodoList .todo-item {
        padding: 1 2;
        margin: 0 0 1 0;
        border-bottom: solid #6b7280;
        color: #f3f4f6;
    }

    TodoList .todo-item:hover {
        background: #1a1d2e;
    }

    TodoList .todo-completed {
        text-style: dim;
        color: #10b981;
    }
    """

    def compose(self):
        yield Static("[dim]No active todos[/dim]")


class SubagentList(ScrollableContainer):
    """Subagent list tab content

    Displays list of active subagent sessions with their status.
    Placeholder for now - will be connected to actual subagent system.
    """

    DEFAULT_CSS = """
    SubagentList {
        height: 1fr;
        background: #242838;
    }

    SubagentList .subagent-item {
        padding: 1 2;
        margin: 0 0 1 0;
        border-bottom: solid #6b7280;
        color: #f3f4f6;
    }

    SubagentList .subagent-item:hover {
        background: #1a1d2e;
    }

    SubagentList .status-running {
        color: #10b981;
    }

    SubagentList .status-pending {
        color: #f59e0b;
    }
    """

    def compose(self):
        yield Static("[dim]No active subagents[/dim]")


class NavigatorTimeline(ScrollableContainer):
    """Navigator timeline tab content

    Displays a timeline of session events and navigation history.
    Placeholder for now - will be connected to actual timeline system.
    """

    DEFAULT_CSS = """
    NavigatorTimeline {
        height: 1fr;
        background: #242838;
    }

    NavigatorTimeline .timeline-item {
        padding: 1 2;
        margin: 0 0 1 0;
        border-bottom: solid #6b7280;
        color: #f3f4f6;
    }

    NavigatorTimeline .timeline-item:hover {
        background: #1a1d2e;
    }

    NavigatorTimeline .timestamp {
        color: #9ca3af;
    }
    """

    def compose(self):
        yield Static("[dim]No timeline events[/dim]")


class SessionList(ScrollableContainer):
    """Session list tab content

    Displays session metadata, export options, and settings.
    Connected to actual session system via event bus.
    """

    DEFAULT_CSS = """
    SessionList {
        height: 1fr;
        background: #242838;
    }

    SessionList .session-header {
        padding: 1 2;
        background: #1a1d2e;
        text-style: bold;
        border-bottom: solid #a855f7;
        color: #f3f4f6;
        margin: 0 0 1 0;
    }

    SessionList .session-info {
        padding: 1 2;
        border-bottom: solid #6b7280;
        color: #f3f4f6;
        margin: 0 0 1 0;
    }

    SessionList .session-info-label {
        color: #9ca3af;
        text-style: dim;
    }

    SessionList .session-actions {
        padding: 1;
        border-bottom: solid #6b7280;
        background: #242838;
        margin: 0 0 1 0;
    }

    SessionList .settings-section {
        padding: 1;
        border-bottom: solid #6b7280;
        background: #242838;
        margin: 0 0 1 0;
    }

    SessionList .settings-toggle {
        padding: 0 1;
    }

    SessionList Label {
        color: #f3f4f6;
    }

    SessionList Static {
        color: #f3f4f6;
    }
    """

    session_data: reactive[Optional[dict]] = reactive(None)
    drawer_width: reactive[int] = reactive(35)
    reduced_motion: reactive[bool] = reactive(False)

    def compose(self):
        """Build session list UI"""
        yield Label("Session Information", classes="session-header")
        yield Label("No active session", classes="session-info", id="session-info")

        with Container(classes="session-actions"):
            yield Label("Actions", classes="session-info-label")
            yield Static("[dim]Export as JSON[/dim]", id="btn-export-json")
            yield Static("[dim]Export as Markdown[/dim]", id="btn-export-md")
            yield Static("[dim]Copy to Clipboard[/dim]", id="btn-copy")

        with Container(classes="settings-section"):
            yield Label("Drawer Settings", classes="session-info-label")
            yield Static(f"Width: {self.drawer_width}%", id="drawer-width-label")
            yield Static(f"Reduced Motion: {'On' if self.reduced_motion else 'Off'}", id="reduced-motion-label")

    def watch_session_data(self, old_value: Optional[dict], new_value: Optional[dict]) -> None:
        """Called when session data changes"""
        if new_value is None:
            self.query_one("#session-info", Static).update("[dim]No active session[/dim]")
            return

        created = datetime.fromtimestamp(new_value.get("time_created", 0)).strftime("%Y-%m-%d %H:%M")
        messages = new_value.get("message_count", 0)
        cost = new_value.get("total_cost", 0.0)

        info = (
            f"ID: {new_value.get('id', 'N/A')}\n"
            f"Created: {created}\n"
            f"Messages: {messages}\n"
            f"Total Cost: ${cost:.4f}\n"
            f"Agent: {new_value.get('agent', 'N/A')}"
        )
        self.query_one("#session-info", Static).update(info)

    def watch_drawer_width(self, old_value: int, new_value: int) -> None:
        """Called when drawer width changes"""
        if self.is_mounted:
            self.query_one("#drawer-width-label", Static).update(f"Width: {new_value}%")

    def watch_reduced_motion(self, old_value: bool, new_value: bool) -> None:
        """Called when reduced motion setting changes"""
        if self.is_mounted:
            state = "On" if new_value else "Off"
            self.query_one("#reduced-motion-label", Static).update(f"Reduced Motion: {state}")

    def update_session(self, session_data: dict) -> None:
        """Update session information display"""
        self.session_data = session_data


class DrawerWidget(Container):
    """Side drawer widget for accessing todos, subagents, navigator, and session

    Features:
    - 4 tabs: Todos (📋), Subagents (🤖), Navigator (🧭), Session (📝)
    - Slide animation when toggling visibility
    - Configurable width (30-45% of terminal)
    - Overlay mode - main content remains visible when open
    - Preserves tab state when hidden
    - FocusManager integration for keyboard navigation

    Default keyboard binding: Ctrl+B to toggle
    """

    visible: reactive[bool] = reactive(False)
    width_percent: reactive[int] = reactive(35)
    active_tab: reactive[Literal["todos", "subagents", "navigator", "session"]] = reactive("todos")
    has_focus: reactive[bool] = reactive(False)

    DEFAULT_CSS = """
    DrawerWidget {
        dock: left;
        height: 100%;
        width: 35;
        offset-x: -35;
        transition: offset-x 150ms;
        background: #242838;
        border: thick #6b7280;
        display: block;
    }

    DrawerWidget.-visible {
        offset-x: 0;
    }

    DrawerWidget > Vertical {
        height: 100%;
    }

    DrawerWidget .drawer-header {
        padding: 1 2;
        background: #1a1d2e;
        text-style: bold;
        text-align: center;
        color: #f3f4f6;
        border-bottom: solid #6b7280;
    }

    DrawerWidget .tab-buttons {
        height: 12;
        padding: 1;
        background: #242838;
        border-bottom: solid #6b7280;
    }

    DrawerWidget .tab-content {
        height: 1fr;
        background: #242838;
    }

    DrawerWidget ScrollableContainer {
        scrollbar-background: #1a1d2e;
        scrollbar-color: #10b981;
        scrollbar-color-hover: #d946ef;
        scrollbar-color-active: #a855f7;
    }
    """

    def __init__(
        self,
        width_percent: int = 35,
        **kwargs
    ) -> None:
        """Initialize DrawerWidget

        Args:
            width_percent: Width as percentage of terminal (30-45)
            **kwargs: Additional Container widget arguments
        """
        clamped_width = max(30, min(45, width_percent))
        self._width_percent = clamped_width
        super().__init__(**kwargs)
        self.width_percent = clamped_width

    def compose(self):
        with Vertical():
            yield Static("[bold]Drawer[/bold]", classes="drawer-header")

            with Horizontal(classes="tab-buttons"):
                self._btn_todos = TabButton("📋", "Todos", id="btn-todos")
                self._btn_subagents = TabButton("🤖", "Subagents", id="btn-subagents")
                self._btn_navigator = TabButton("🧭", "Navigator", id="btn-navigator")
                self._btn_session = TabButton("📝", "Session", id="btn-session")
                yield self._btn_todos
                yield self._btn_subagents
                yield self._btn_navigator
                yield self._btn_session

            with Container(classes="tab-content"):
                self._todo_list = TodoList(id="tab-todos")
                self._subagent_list = SubagentList(id="tab-subagents")
                self._navigator_timeline = NavigatorTimeline(id="tab-navigator")
                self._session_list = SessionList(id="tab-session")
                yield self._todo_list
                yield self._subagent_list
                yield self._navigator_timeline
                yield self._session_list

    def on_mount(self) -> None:
        import asyncio

        focus_manager = get_focus_manager()

        # Subscribe to focus changes
        async def on_focus_did_change(event):
            logger.debug(f"Focus changed: {event.target_widget}")
            self.has_focus = (event.target_widget == "drawer")

        asyncio.create_task(bus.subscribe(Events.FOCUS_DID_CHANGE, on_focus_did_change))

        # Sync initial state
        self.has_focus = (focus_manager.get_current_state() == FocusState.DRAWER_FOCUSED)

        logger.info("DrawerWidget mounted and integrated with FocusManager")
        self._update_active_tab()
        self._update_width()

    def _update_width(self) -> None:
        """Update drawer width based on width_percent"""
        if self.app is None:
            return

        terminal_width = self.app.size.width
        new_width = int(terminal_width * self._width_percent / 100)

        if not self.visible:
            self.styles.offset_x = (-1) * new_width

        self.styles.width = new_width

    def _update_active_tab(self) -> None:
        self._btn_todos.set_class(False, "-active")
        self._btn_subagents.set_class(False, "-active")
        self._btn_navigator.set_class(False, "-active")
        self._btn_session.set_class(False, "-active")

        if self.active_tab == "todos":
            self._btn_todos.set_class(True, "-active")
        elif self.active_tab == "subagents":
            self._btn_subagents.set_class(True, "-active")
        elif self.active_tab == "navigator":
            self._btn_navigator.set_class(True, "-active")
        elif self.active_tab == "session":
            self._btn_session.set_class(True, "-active")

        self._todo_list.display = (self.active_tab == "todos")
        self._subagent_list.display = (self.active_tab == "subagents")
        self._navigator_timeline.display = (self.active_tab == "navigator")
        self._session_list.display = (self.active_tab == "session")

    def watch_visible(self, old_value: bool, new_value: bool) -> None:
        """Called when visibility changes"""
        if new_value:
            self.set_class(True, "-visible")
        else:
            self.set_class(False, "-visible")

    def watch_width_percent(self, old_value: int, new_value: int) -> None:
        """Called when width_percent changes"""
        clamped = max(30, min(45, new_value))
        self._width_percent = clamped
        if self.is_mounted:
            self._update_width()

    def watch_active_tab(self, old_value: str, new_value: str) -> None:
        import asyncio

        if self.is_mounted:
            self._update_active_tab()
            # Emit DRAWER_TAB_CHANGED event
            asyncio.create_task(
                bus.publish(
                    Events.DRAWER_TAB_CHANGED,
                    {"old_tab": old_value, "new_tab": new_value}
                )
            )

    def watch_has_focus(self, old_value: bool, new_value: bool) -> None:
        """Called when focus state changes"""
        if new_value:
            self.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "btn-todos":
            self.switch_tab("todos")
        elif button_id == "btn-subagents":
            self.switch_tab("subagents")
        elif button_id == "btn-navigator":
            self.switch_tab("navigator")
        elif button_id == "btn-session":
            self.switch_tab("session")

    def toggle_visible(self) -> None:
        """Toggle drawer visibility

        When toggling on, drawer slides in from left.
        When toggling off, drawer slides out to left.
        Tab state is preserved when hidden.
        """
        self.visible = not self.visible

    def switch_tab(self, tab_id: Literal["todos", "subagents", "navigator", "session"]) -> None:
        valid_tabs = ["todos", "subagents", "navigator", "session"]

        if tab_id not in valid_tabs:
            raise ValueError(f"Invalid tab_id: {tab_id}. Must be one of {valid_tabs}")

        self.active_tab = tab_id

    def set_width_percent(self, width_percent: int) -> None:
        """Set drawer width as percentage of terminal

        Args:
            width_percent: Width percentage (30-45)

        Raises:
            ValueError: If width_percent is not in range 30-45
        """
        if width_percent < 30 or width_percent > 45:
            raise ValueError(f"width_percent must be between 30 and 45, got {width_percent}")

        self.width_percent = width_percent
