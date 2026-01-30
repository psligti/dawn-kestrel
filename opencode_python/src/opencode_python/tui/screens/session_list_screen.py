"""OpenCode Python - Session List Screen for TUI

Provides a session list screen with DataTable for browsing and selecting sessions:
- Displays sessions in DataTable with ID, Title, and Time columns
- Supports navigation with arrow keys
- Enter key opens selected session in MessageScreen
- Create Session button to create new sessions
- Switch between sessions by selecting and pressing Enter
"""

from typing import List, Optional
import logging

from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.widgets import DataTable, Button, Footer
from textual.app import ComposeResult
from textual.binding import Binding

from opencode_python.core.models import Session
from opencode_python.tui.dialogs import PromptDialog


logger = logging.getLogger(__name__)


class SessionListScreen(Screen):
    """Session list screen for browsing and selecting sessions"""

    BINDINGS = [
        ("escape", "pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
        ("enter", "open_selected_session", "Open"),
        ("n", "create_new_session", "New Session"),
    ]

    sessions: List[Session]

    def __init__(self, sessions: List[Session], **kwargs):
        """Initialize SessionListScreen with session list"""
        super().__init__(**kwargs)
        self.sessions = sessions

    def compose(self) -> ComposeResult:
        """Build the session list screen UI"""
        with Vertical(id="session-list-screen"):
            with Horizontal(id="toolbar"):
                yield Button("Create Session", id="btn_create_session", variant="primary")
            yield DataTable(id="session-table")
            yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted - populate DataTable"""
        data_table = self.query_one(DataTable)

        # Add columns
        data_table.add_column("ID", width=15)
        data_table.add_column("Title", width=40)
        data_table.add_column("Time", width=20)

        # Add rows for each session
        for session in self.sessions:
            data_table.add_row(
                session.id,
                session.title,
                self._format_time(session.time_updated),
                key=session.id,
            )

        # Set cursor type to row for better selection
        data_table.cursor_type = "row"

    def _format_time(self, timestamp: float) -> str:
        """Format timestamp for display"""
        from datetime import datetime

        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return "Unknown"

    def action_open_selected_session(self) -> None:
        """Handle Enter key to open selected session"""
        data_table = self.query_one(DataTable)

        if len(self.sessions) == 0:
            logger.warning("No sessions available")
            return

        # Default to first session
        selected_session = self.sessions[0]

        # Try to get cursor coordinate and use selected session
        try:
            cursor_coordinate = data_table.cursor_coordinate
            row_key, _ = data_table.coordinate_to_cell_key(cursor_coordinate)
            if row_key is not None:
                session_id = str(row_key)
                found_session = self._find_session_by_id(session_id)
                if found_session is not None:
                    selected_session = found_session
        except Exception:
            pass

        logger.info(f"Opening session: {selected_session.title} ({selected_session.id})")

        # Import here to avoid circular dependency
        from opencode_python.tui.screens.message_screen import MessageScreen

        self.app.push_screen(MessageScreen(selected_session))

    async def action_create_new_session(self) -> None:
        """Handle 'n' key to create new session"""
        await self._prompt_create_session()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn_create_session":
            await self._prompt_create_session()

    async def _prompt_create_session(self) -> None:
        """Prompt user for session title and create new session"""
        def on_submit(title: str) -> None:
            if not title or not title.strip():
                logger.warning("Empty session title, not creating session")
                return
            self._create_session(title.strip())

        await self.app.push_screen(
            PromptDialog(title="Create New Session", placeholder="Enter session title"),
            on_submit
        )

    def _create_session(self, title: str) -> None:
        """Create a new session with the given title

        Args:
            title: Session title
        """
        async def create_and_refresh() -> None:
            try:
                session_manager = getattr(self.app, "session_manager", None)
                if not session_manager:
                    logger.error("Session manager not available")
                    return

                from opencode_python.core.settings import get_settings
                settings = get_settings()

                new_session = await session_manager.create(title=title)
                updated_session = await session_manager.update_session(
                    new_session.id,
                    agent=settings.agent_default
                )

                logger.info(f"Created new session: {updated_session.id} ({title})")

                self.sessions.append(updated_session)
                self._refresh_session_list()

            except Exception as e:
                logger.error(f"Failed to create session: {e}")

        self.call_later(create_and_refresh)

    def _refresh_session_list(self) -> None:
        """Refresh the DataTable with current sessions"""
        data_table = self.query_one(DataTable)

        data_table.clear()

        for session in self.sessions:
            data_table.add_row(
                session.id,
                session.title,
                self._format_time(session.time_updated),
                key=session.id,
            )

    def _find_session_by_id(self, session_id: str) -> Session | None:
        """Find session by ID from the session list"""
        for session in self.sessions:
            if session.id == session_id:
                return session
        return None
