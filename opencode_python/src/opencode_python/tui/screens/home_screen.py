"""OpenCode Python - Home Screen for TUI

Home screen showing provider/account, recent sessions, and quick actions:
- Displays active provider and account (placeholder for Epic 2)
- Shows recent sessions from SessionStorage
- Quick action buttons: New Session, Resume Session, Settings
- Supports session selection and resume
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static
from textual.binding import Binding
from textual.message import Message

from opencode_python.core.models import Session


class ScreenChanged(Message):
    """Emitted when a screen change occurs."""
    pass


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


class HomeScreen(Screen):
    """Home screen for quick access to sessions and actions"""

    BINDINGS = [
        Binding("escape", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+p", "palette_open", "Command Palette"),
    ]

    def __init__(self, provider: str = "OpenAI", account: str = "Default", **kwargs):
        """Initialize HomeScreen with provider and account info.

        Args:
            provider: Active provider name (placeholder for Epic 2)
            account: Active account name (placeholder for Epic 2)
        """
        super().__init__(**kwargs)
        self.provider = provider
        self.account = account
        self.recent_sessions: List[Session] = []
        self.sessions_loaded = False
        self._on_command_execute = None

    def compose(self) -> ComposeResult:
        """Build the home screen UI with provider info, sessions, and actions."""
        # Header section with provider/account info
        with Container(id="home-header"):
            yield Static(
                f"[bold cyan]OpenCode Python[/bold cyan] | "
                f"[dim]Provider:[/dim] [yellow]{self.provider}[/yellow] | "
                f"[dim]Account:[/dim] [yellow]{self.account}[/yellow]",
                id="provider-info"
            )

        # Main content area
        with Vertical(id="home-content"):
            # Recent sessions section
            with Vertical(id="recent-sessions-section"):
                yield Static("[bold]Recent Sessions[/bold]", id="sessions-title")
                yield DataTable(id="sessions-table")

            # Quick actions section
            with Horizontal(id="quick-actions"):
                yield Button("New Session", variant="primary", id="new-session-btn")
                yield Button("Resume Session", id="resume-session-btn")
                yield Button("Settings", id="settings-btn")

    def on_mount(self) -> None:
        """Called when screen is mounted - load sessions."""
        asyncio.create_task(self._load_sessions())

    async def _load_sessions(self) -> None:
        """Load recent sessions from SessionStorage."""
        try:
            from opencode_python.storage.store import SessionStorage
            from opencode_python.core.settings import get_storage_dir

            storage_dir = get_storage_dir()
            storage = SessionStorage(storage_dir)

            # Get sessions for current project (use "default" as project_id for now)
            sessions = await storage.list_sessions("default")
            self.recent_sessions = sessions[:10]  # Show last 10 sessions

            # Populate table
            table = self.query_one("#sessions-table", DataTable)
            if table:
                table.clear()
                table.add_column("Title", width=40)
                table.add_column("Last Updated", width=20)

                for session in self.recent_sessions:
                    table.add_row(
                        session.title,
                        self._format_time(session.time_updated),
                        key=session.id,
                    )

                # Set cursor type to row
                table.cursor_type = "row"
                self.sessions_loaded = True

                logger.info(f"Loaded {len(self.recent_sessions)} recent sessions")

                # Emit screen:change event
                self.post_message(ScreenChanged())
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
            table = self.query_one("#sessions-table", DataTable)
            if table:
                table.clear()
                table.add_column("Title", width=40)
                table.add_column("Last Updated", width=20)
                table.add_row("[dim]No sessions found[/dim]")

    def _format_time(self, timestamp: float) -> str:
        """Format timestamp for display.

        Args:
            timestamp: Unix timestamp.

        Returns:
            Formatted time string.
        """
        try:
            dt = datetime.fromtimestamp(timestamp)
            now = datetime.now()
            delta = now - dt

            if delta.days == 0:
                if delta.seconds < 3600:
                    minutes = delta.seconds // 60
                    return f"{minutes}m ago"
                else:
                    hours = delta.seconds // 3600
                    return f"{hours}h ago"
            elif delta.days == 1:
                return "Yesterday"
            elif delta.days < 7:
                return f"{delta.days}d ago"
            else:
                return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return "Unknown"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses for quick actions.

        Args:
            event: Button.Pressed event.
        """
        button_id = event.button.id

        if button_id == "new-session-btn":
            # Emit command:execute event for "new session"
            self.post_message(
                CommandExecute(
                    action="new_session",
                    data={}
                )
            )
            self.notify("[cyan]New Session action triggered[/cyan]")
            # Epic 3 will handle actual session creation

        elif button_id == "resume-session-btn":
            if not self.recent_sessions:
                self.notify("[yellow]No recent sessions to resume[/yellow]")
                return

            # Resume most recent session
            session = self.recent_sessions[0]
            self._open_session(session)

        elif button_id == "settings-btn":
            self.notify("[cyan]Settings screen coming soon (Epic 2)[/cyan]")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle session row selection.

        Args:
            event: DataTable.RowSelected event.
        """
        if not self.recent_sessions:
            return

        row_key = event.row_key
        if row_key is not None:
            session = self._find_session_by_id(str(row_key))
            if session:
                self._open_session(session)

    def _find_session_by_id(self, session_id: str) -> Optional[Session]:
        """Find session by ID from recent sessions.

        Args:
            session_id: Session ID to find.

        Returns:
            Session if found, None otherwise.
        """
        for session in self.recent_sessions:
            if session.id == session_id:
                return session
        return None

    def _open_session(self, session: Session) -> None:
        """Open session in MessageScreen.

        Args:
            session: Session to open.
        """
        logger.info(f"Opening session: {session.title} ({session.id})")

        # Import here to avoid circular dependency
        from opencode_python.tui.screens.message_screen import MessageScreen

        # Emit screen:change event
        self.post_message(ScreenChanged())

        # Call handler if set
        if self._on_command_execute:
            self._on_command_execute(CommandExecute(action="open_session", data={"session_id": session.id}))

        # Push session screen
        self.app.push_screen(MessageScreen(session))

    def action_palette_open(self) -> None:
        """Open command palette."""
        # Emit palette:open event
        self.post_message(PaletteOpen())

        from opencode_python.tui.dialogs import CommandPaletteDialog

        def handle_command(command_value: str) -> None:
            """Handle selected command.

            Args:
                command_value: Value of selected command.
            """
            self.app.post_message(
                self.app.CommandExecute(
                    action=command_value,
                    data={}
                )
            )

        self.app.push_screen(CommandPaletteDialog(on_command=handle_command))
