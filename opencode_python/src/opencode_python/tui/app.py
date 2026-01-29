"""OpenCode Python - Main TUI Application"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List, Literal

import asyncio
import logging
import pendulum
import uuid

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer, Vertical
from textual.reactive import reactive, Reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Static,
    TabPane,
    Tabs,
)

from opencode_python.tui.message_view import MessageView
from opencode_python.core.models import Message, TextPart
from opencode_python.tui.screens.message_screen import MessageScreen


logger = logging.getLogger(__name__)


class OpenCodeTUI(App[None]):
    """OpenCode Textual TUI application"""

    CSS = """
    Screen {
        background: $primary;
    }
    Header {
        text-style: bold;
        background: $secondary;
    }
    .active-tab {
        text-style: bold underline;
        color: cyan;
    }
    Button.-primary {
        background: $primary;
    }
    DataTable {
        border: thick green;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    session_table: DataTable[str]
    header_widget: Static
    messages_container: ScrollableContainer

    show_sidebar = reactive(True)
    current_session_id = reactive("")
    command_history: Reactive[List[str]] = reactive([])
    messages: Reactive[List[Message]] = reactive([])

    def compose(self) -> ComposeResult:
        """Build TUI UI"""
        yield Header()

        with Container(id="main-container"):
            # Sidebar with session list and context
            if self.show_sidebar:
                with Vertical(id="sidebar"):
                    yield Static("[bold]Sessions[/bold]")
                    self.session_table: DataTable[str] = DataTable()
                    self.session_table.add_column("ID", width=15)
                    self.session_table.add_column("Title", width=30)
                    self.session_table.add_column("Time", width=20)
                    yield self.session_table

            # Main content area
            with Vertical(id="content"):
                # Session header with context info
                self.header_widget = Static(
                    f"[bold]{self._get_session_title()}[/bold]\n"
                    f"[dim]Context: {self._get_context_info()}[/dim]"
                )
                yield self.header_widget

                # Tabs for different views
                yield Tabs(
                    "Messages",
                    "Context",
                    "Actions",
                    id="main-tabs",
                )

                # Messages pane with message timeline
                with TabPane("Messages", id="messages-pane"):
                    self.messages_container = ScrollableContainer(id="messages-timeline")
                    yield self.messages_container

                # Context pane with file tree
                with TabPane("Context", id="context-pane"):
                    yield Static("[dim]File context will appear here[/dim]")

                # Actions pane with input and buttons
                with TabPane("Actions", id="actions-pane"):
                    yield Button("Open Chat", variant="primary", id="chat-btn")
                    yield Button("List Sessions", id="list-btn")

        yield Footer()

    def on_mount(self) -> None:
        """Called when TUI starts"""
        self.app.title = "OpenCode Python"
        logger.info("TUI mounted")
        
        # Load sessions
        asyncio.create_task(self._load_sessions())

    async def _load_sessions(self) -> None:
        """Load sessions into table"""
        from opencode_python.core.session import SessionManager
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir
        
        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)
        work_dir = Path.cwd()
        
        manager = SessionManager(storage, work_dir)
        sessions = await manager.list_sessions()
        
        self.session_table.clear()
        
        for session in sessions:
            self.session_table.add_row(
                session.id,
                session.title,
                pendulum.from_timestamp(session.time_created).format("YYYY-MM-DD HH:mm"),
            )

    def _get_session_title(self) -> str:
        """Get current session title"""
        if not self.current_session_id:
            return "No active session"
        return self.current_session_id

    def _get_context_info(self) -> str:
        """Get context usage info"""
        # TODO: Calculate actual token usage
        return "0 tokens / 0% used"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "run-btn":
            self._handle_run_command()
        elif event.button.id == "list-btn":
            asyncio.create_task(self._load_sessions())
        elif event.button.id == "chat-btn":
            self._open_message_screen()

    def on_data_table_row_selected(self, event: Any) -> None:
        """Handle session row selection"""
        if not hasattr(event, 'row_key'):
            return
        row_key = event.row_key
        if row_key is not None:
            self.current_session_id = str(row_key)
            self._open_message_screen()

    def _open_message_screen(self) -> None:
        """Open message screen for current session"""
        if not self.current_session_id:
            self.notify("[yellow]No session selected[/yellow]")
            return
        
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir
        
        try:
            storage_dir = get_storage_dir()
            storage = SessionStorage(storage_dir)

            session = asyncio.run(storage.get_session(self.current_session_id))
            if session:
                self.push_screen(MessageScreen(session))
            else:
                self.notify(f"[red]Session not found: {self.current_session_id}[/red]")
        except Exception as e:
            logger.error(f"Error opening message screen: {e}")
            self.notify(f"[red]Error: {e}[/red]")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input"""
        command = event.value
        self.command_history = self.command_history + [command]
        self._handle_run_command(command)

    def _handle_run_command(self, command: str | None = None) -> None:
        """Handle run command"""
        if command:
            # Get from input widget
            input_widget = self.query_one(Input)
            final_command = input_widget.value if input_widget else command
            
            self.notify(f"[cyan]Would run:[/cyan] {final_command}")
        else:
            input_widget = self.query_one(Input)
            if input_widget:
                self.notify(f"[cyan]Would run:[/cyan] {input_widget.value}")

    async def _add_message(self, role: Literal["user", "assistant", "system"], text: str) -> None:
        """Add a message to the timeline"""
        from opencode_python.core.models import Message

        message_id = str(uuid.uuid4())
        session_id = self.current_session_id or ""

        text_part = TextPart(
            id=str(uuid.uuid4()),
            message_id=message_id,
            session_id=session_id,
            part_type="text",
            text=text,
        )

        message = Message(
            id=message_id,
            session_id=session_id,
            role=role,
            time={"created": self._now()},
            parts=[text_part],
        )

        self.messages = self.messages + [message]

        text_part_dict = text_part.model_dump() if hasattr(text_part, 'model_dump') else dict(text_part)
        message_view = MessageView(message_data={"role": role, "time": message.time, "parts": [text_part_dict]})
        await self.messages_container.mount(message_view)

    def _now(self) -> int:
        """Get current timestamp in milliseconds"""
        return int(pendulum.now().timestamp() * 1000)

    async def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()
        logger.info("TUI exited")
