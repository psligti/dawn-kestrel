"""OpenCode Python - Main TUI Application"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import asyncio
import logging
import uuid

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer, Vertical
from textual.reactive import reactive, Reactive

from opencode_python.tui.widgets.header import SessionHeader
from opencode_python.tui.widgets.drawer import DrawerWidget
from opencode_python.core.focus_manager import get_focus_manager

from opencode_python.core.models import Message, TextPart
from opencode_python.tui.screens.message_screen import MessageScreen
from opencode_python.tui.palette.command_palette import CommandPalette

logger = logging.getLogger(__name__)


class OpenCodeTUI(App[None]):
    """OpenCode Textual TUI application"""

    CSS_PATH = Path(__file__).parent / "opencode.css"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+b", "toggle_drawer", "Toggle Drawer"),
        Binding("escape", "close_drawer", "Close Drawer"),
        Binding("tab", "next_drawer_tab", "Next Tab"),
        Binding("shift+tab", "prev_drawer_tab", "Previous Tab"),
        Binding("/", "open_command", "Open Command Palette"),
        Binding("s", "open_settings", "Settings"),
    ]

    messages_container: ScrollableContainer

    current_session_id = reactive("")
    messages: Reactive[List[Message]] = reactive([])

    def compose(self) -> ComposeResult:
        """Build TUI UI with modern drawer layout"""

        with Container(id="main-container"):
            # Main content area
            with Vertical(id="content"):
                # Session header with context info
                yield SessionHeader(
                    session_title=self._get_session_title(),
                    model="gpt-4"
                )

                # Messages pane with message timeline
                self.messages_container = ScrollableContainer(id="messages-timeline")
                yield self.messages_container

            # Right drawer with todos, subagents, navigator
            yield DrawerWidget(id="drawer")

    def on_mount(self) -> None:
        """Called when TUI starts"""
        self.app.title = "OpenCode Python"
        logger.info("TUI mounted")

        from opencode_python.tui.screens import HomeScreen
        self.push_screen(HomeScreen())

    def _get_session_title(self) -> str:
        """Get current session title"""
        if not self.current_session_id:
            return "No active session"
        return self.current_session_id

    async def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()
        logger.info("TUI exited")

    def action_open_command(self) -> None:
        """Open command palette dialog"""
        self.push_screen(CommandPalette(on_command=self._handle_command_palette_command))

    def _handle_command_palette_command(self, command_value: str) -> None:
        """Handle command palette command selection

        Args:
            command_value: The selected command value
        """
        if command_value == "settings":
            self.action_open_settings()

    def action_open_settings(self) -> None:
        """Open settings screen"""
        from opencode_python.tui.screens import SettingsScreen

        self.push_screen(SettingsScreen())

    def action_toggle_drawer(self) -> None:
        """Toggle drawer visibility"""
        drawer = self.query_one(DrawerWidget)
        drawer.toggle_visible()
        focus_manager = get_focus_manager()

        if drawer.visible:
            focus_manager.set_drawer_focused()
        else:
            focus_manager.set_main_focused()

        logger.info(f"Drawer toggled: visible={drawer.visible}")

    def action_close_drawer(self) -> None:
        """Close drawer and release focus"""
        drawer = self.query_one(DrawerWidget)
        focus_manager = get_focus_manager()

        if drawer.visible:
            drawer.visible = False
            focus_manager.set_main_focused()
            logger.info("Drawer closed via Escape")

    def action_next_drawer_tab(self) -> None:
        """Navigate to next drawer tab"""
        drawer = self.query_one(DrawerWidget)

        if not drawer.visible:
            return

        tabs = ["todos", "subagents", "navigator", "session"]
        current_index = tabs.index(drawer.active_tab)
        next_index = (current_index + 1) % len(tabs)
        drawer.switch_tab(tabs[next_index])

        focus_manager = get_focus_manager()
        focus_manager.set_drawer_focused()

        logger.info(f"Drawer tab: {drawer.active_tab}")

    def action_prev_drawer_tab(self) -> None:
        """Navigate to previous drawer tab"""
        drawer = self.query_one(DrawerWidget)

        if not drawer.visible:
            return

        tabs = ["todos", "subagents", "navigator", "session"]
        current_index = tabs.index(drawer.active_tab)
        prev_index = (current_index - 1) % len(tabs)
        drawer.switch_tab(tabs[prev_index])

        focus_manager = get_focus_manager()
        focus_manager.set_drawer_focused()

        logger.info(f"Drawer tab: {drawer.active_tab}")
