"""OpenCode Python - Session List Screen for TUI

Provides a session list screen with DataTable for browsing and selecting sessions:
- Displays sessions in DataTable with ID, Title, and Time columns
- Supports navigation with arrow keys
- Enter key opens selected session in MessageScreen
"""

from typing import List
import logging

from textual.screen import Screen
from textual.containers import Vertical
from textual.widgets import DataTable
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from dawn_kestrel.core.models import Session


logger = logging.getLogger(__name__)


class SessionListScreen(Screen):
    """Session list screen for browsing and selecting sessions"""

    BINDINGS = [
        ("escape", "pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
        ("enter", "open_selected_session", "Open"),
    ]

    sessions: List[Session]

    def __init__(self, sessions: List[Session], **kwargs):
        """Initialize SessionListScreen with session list"""
        super().__init__(**kwargs)
        self.sessions = sessions

    def compose(self) -> ComposeResult:
        """Build the session list screen UI"""
        with Vertical(id="session-list-screen"):
            yield DataTable(id="session-table")

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
        from dawn_kestrel.tui.screens.message_screen import MessageScreen

        self.app.push_screen(MessageScreen(selected_session))

    def _find_session_by_id(self, session_id: str) -> Session | None:
        """Find session by ID from the session list"""
        for session in self.sessions:
            if session.id == session_id:
                return session
        return None
