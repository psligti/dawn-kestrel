"""OpenCode Python - Message Screen for TUI

Provides a complete message display screen with:
- Scrollable message timeline
- Different styling for user/assistant/system messages
- Auto-scroll to newest message
- User input with submit handler
- Real-time AI streaming integration
- Support for all Part types
"""

from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Input, Button, Markdown
from textual.app import ComposeResult
from textual.reactive import reactive
from typing import Optional, List, Dict, Any, Union
import asyncio
import logging
import pendulum
from pydantic import SecretStr

from opencode_python.core.models import (
    Message, Part, TextPart, ToolPart, FilePart, ReasoningPart,
    SnapshotPart, PatchPart, AgentPart, SubtaskPart, RetryPart, CompactionPart,
    ToolState, Session
)
from opencode_python.tui.message_view import MessageView, MessagePartView
from opencode_python.ai_session import AISession
from opencode_python.providers import get_provider, ProviderID
from opencode_python.providers.base import StreamEvent
from opencode_python.core.settings import get_settings


logger = logging.getLogger(__name__)


class MessageScreen(Screen):
    """Message display and input screen for OpenCode TUI"""

    CSS = """
    #message-screen {
        layout: vertical;
    }
    
    #messages-area {
        height: 1fr;
        overflow-y: auto;
    }
    
    #input-area {
        height: 5;
        dock: bottom;
    }
    
    MessageView.user {
        border-left: thick green;
        padding-left: 1;
        margin-bottom: 1;
    }
    
    MessageView.assistant {
        border-left: thick blue;
        padding-left: 1;
        margin-bottom: 1;
    }
    
    MessageView.system {
        border-left: thick gray;
        padding-left: 1;
        margin-bottom: 1;
    }
    
    #message-input {
        width: 1fr;
    }
    
    #send-button {
        width: 10;
    }
    
    #typing-indicator {
        height: 1;
        margin-top: 1;
    }
    
    .timestamp {
        color: $text-muted;
        text-style: dim;
    }
    
    .role-badge {
        padding: 0 1;
        border: solid;
        border-radius: 1;
    }
    
    .role-badge.user {
        border: green;
        color: green;
    }
    
    .role-badge.assistant {
        border: blue;
        color: blue;
    }
    
    .role-badge.system {
        border: gray;
        color: gray;
    }
    """

    BINDINGS = [
        ("escape", "pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
    ]

    messages: reactive[List[Message]] = reactive([])
    session: Session
    ai_session: Optional[AISession] = None
    is_streaming: reactive[bool] = reactive(False)
    messages_container: ScrollableContainer
    _current_assistant_message: Optional[Message]
    _current_text_part: Optional[TextPart]
    _current_assistant_view: Optional[MessageView]

    def __init__(self, session: Session, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self._current_assistant_message = None
        self._current_text_part = None
        self._current_assistant_view = None

    def compose(self) -> ComposeResult:
        """Build the message screen UI"""
        with Vertical(id="message-screen"):
            messages_container = ScrollableContainer(id="messages-area")
            self.messages_container = messages_container
            yield messages_container

            yield Static("", id="typing-indicator")

            with Horizontal(id="input-area"):
                yield Input(
                    placeholder="Type your message...",
                    id="message-input",
                )
                yield Button("Send", variant="primary", id="send-button")

    def on_mount(self) -> None:
        """Called when screen is mounted"""
        assert self.session is not None, "Session must be set when screen is mounted"
        logger.info(f"MessageScreen mounted for session {self.session.id}")
        self.app.title = f"OpenCode - {self.session.title}"
        asyncio.create_task(self._load_messages())

    async def _load_messages(self) -> None:
        """Load existing messages for the session"""
        from opencode_python.core.session import SessionManager
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir
        from pathlib import Path

        try:
            storage_dir = get_storage_dir()
            storage = SessionStorage(storage_dir)
            work_dir = Path.cwd()
            manager = SessionManager(storage, work_dir)
            
            messages = await manager.list_messages(self.session.id)
            self.messages = messages
            
            for message in messages:
                await self._display_message(message)

            self._scroll_to_bottom()

        except Exception as e:
            logger.error(f"Error loading messages: {e}")
            self.notify(f"[red]Error loading messages: {e}[/red]")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle message input submission"""
        text = event.value.strip()
        if text:
            asyncio.create_task(self._handle_user_message(text))
            event.input.value = ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "send-button":
            input_widget = self.query_one("#message-input", Input)
            text = input_widget.value.strip()
            if text:
                asyncio.create_task(self._handle_user_message(text))
                input_widget.value = ""

    async def _handle_user_message(self, text: str) -> None:
        """Handle user message submission and trigger AI response"""
        user_message = await self._create_user_message(text)
        await self._display_message(user_message)
        await self._start_ai_stream(user_message)

    async def _create_user_message(self, text: str) -> Message:
        """Create a user message"""
        from opencode_python.core.session import SessionManager
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir
        from pathlib import Path
        import uuid

        message_id = str(uuid.uuid4())
        timestamp = pendulum.now().timestamp()

        text_part = TextPart(
            id=f"{message_id}_text",
            session_id=self.session.id,
            message_id=message_id,
            part_type="text",
            text=text,
            time={"created": timestamp},
        )

        message = Message(
            id=message_id,
            session_id=self.session.id,
            role="user",
            time={"created": timestamp},
            text=text,
            parts=[text_part],
        )

        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)
        work_dir = Path.cwd()
        manager = SessionManager(storage, work_dir)
        await manager.create_message(
            session_id=self.session.id,
            role="user",
            text=text,
        )

        self.messages = self.messages + [message]
        return message

    async def _start_ai_stream(self, user_message: Message) -> None:
        """Start AI streaming and display response in real-time"""
        try:
            typing_indicator = self.query_one("#typing-indicator", Static)
            typing_indicator.update("[cyan]●[/cyan] [dim]AI is thinking...[/dim]")
            self.is_streaming = True

            self._current_assistant_message = Message(
                id=f"{self.session.id}_assistant_{len(self.messages)}",
                session_id=self.session.id,
                role="assistant",
                time={"created": pendulum.now().timestamp()},
                text="",
                parts=[],
            )

            await self._display_message(self._current_assistant_message, is_streaming=True)
            self._scroll_to_bottom()

            settings = get_settings()

            provider_id = ProviderID.ANTHROPIC
            model = "claude-sonnet-4-20250514"
            api_key_str = settings.api_keys.get("anthropic")
            if api_key_str is None:
                raise ValueError("Anthropic API key not found in settings")
            api_key = api_key_str.get_secret_value() if hasattr(api_key_str, "get_secret_value") else str(api_key_str)

            if not self.session:
                raise ValueError("Session is not set")

            self.ai_session = AISession(
                session=self.session,
                provider_id=provider_id,
                model=model,
                api_key=api_key,
            )

            message_history = self._build_message_history()

            provider = get_provider(provider_id, api_key)
            if not provider:
                raise ValueError(f"Provider not found: {provider_id}")

            models = await provider.get_models()
            model_info = None
            for m in models:
                if m.api_id == model:
                    model_info = m
                    break
            
            if not model_info:
                raise ValueError(f"Model not found: {model}")

            stream = provider.stream(
                model=model_info,
                messages=message_history,
                tools={"enabled": True},
                options=None,
            )

            await self._process_stream_events(stream)

        except Exception as e:
            logger.error(f"Error during AI stream: {e}")
            self.notify(f"[red]Error: {e}[/red]")
            
            if self._current_assistant_message:
                assert self._current_assistant_message is not None
                error_part = TextPart(
                    id=f"{self._current_assistant_message.id}_error",
                    session_id=self.session.id,
                    message_id=self._current_assistant_message.id,
                    part_type="text",
                    text=f"\n\n[red]Error: {e}[/red]",
                    time={"created": pendulum.now().timestamp()},
                )
                self._current_assistant_message.parts.append(error_part)
                self._current_assistant_message.text += f"\n\nError: {e}"
                await self._update_assistant_display()

        finally:
            typing_indicator = self.query_one("#typing-indicator", Static)
            typing_indicator.update("")
            self.is_streaming = False
            
            if self._current_assistant_message:
                await self._save_assistant_message()

            self._scroll_to_bottom()

    def _build_message_history(self) -> List[Dict[str, Any]]:
        """Build message history for AI API"""
        history = []

        for msg in self.messages:
            if msg.role == "user":
                history.append({
                    "role": "user",
                    "content": msg.text or self._parts_to_text(msg.parts),
                })
            elif msg.role == "assistant":
                content = []
                for part in msg.parts:
                    if isinstance(part, TextPart):
                        content.append({"type": "text", "text": part.text})
                    elif isinstance(part, ToolPart):
                        content.append({
                            "type": "tool_result",
                            "tool_use_id": part.call_id or "",
                            "content": part.state.output or "",
                        })

                history.append({
                    "role": "assistant",
                    "content": content,
                })

        return history

    def _parts_to_text(self, parts: List[Part]) -> str:
        """Convert parts list to text string"""
        text_parts = []
        for part in parts:
            if isinstance(part, TextPart):
                text_parts.append(part.text)
        return "\n".join(text_parts)

    async def _process_stream_events(self, stream: Any) -> None:
        """Process streaming events from AI provider"""
        assert self._current_assistant_message is not None, "Current assistant message must be set"
        async for event in stream:
            if isinstance(event, StreamEvent) and event.event_type == "text-delta":
                delta = event.data.get("delta", "")

                if not self._current_text_part:
                    self._current_text_part = TextPart(
                        id=f"{self._current_assistant_message.id}_text_{len(self._current_assistant_message.parts)}",
                        session_id=self.session.id,
                        message_id=self._current_assistant_message.id,
                        part_type="text",
                        text=delta,
                        time={"created": event.timestamp or pendulum.now().timestamp()},
                    )
                    self._current_assistant_message.parts.append(self._current_text_part)
                else:
                    self._current_text_part.text += delta
                    self._current_text_part.time = {"updated": event.timestamp or pendulum.now().timestamp()}

                self._current_assistant_message.text += delta
                await self._update_assistant_display()

            elif isinstance(event, StreamEvent) and event.event_type == "tool-call":
                await self._handle_tool_call(event)

            elif isinstance(event, StreamEvent) and event.event_type == "finish":
                finish_reason = event.data.get("finish_reason", "")
                logger.info(f"Stream finished: {finish_reason}")

                if finish_reason == "tool-calls":
                    assert self.ai_session is not None, "AI session must be set"
                    agent_part = AgentPart(
                        id=f"{self._current_assistant_message.id}_agent",
                        session_id=self.session.id,
                        message_id=self._current_assistant_message.id,
                        part_type="agent",
                        name=str(self.ai_session.provider_id),
                    )
                    self._current_assistant_message.parts.append(agent_part)
                    await self._update_assistant_display()

    async def _handle_tool_call(self, event: StreamEvent) -> None:
        """Handle tool call event"""
        tool_name = event.data.get("tool", "")
        tool_input = event.data.get("input", {})
        tool_call_id = event.data.get("call_id", "")

        assert self._current_assistant_message is not None, "Current assistant message must be set"
        assert self.ai_session is not None, "AI session must be set"

        tool_state = ToolState(
            status="running",
            input=tool_input,
            output=None,
        )

        tool_part = ToolPart(
            id=f"{self._current_assistant_message.id}_tool_{len(self._current_assistant_message.parts)}",
            session_id=self.session.id,
            message_id=self._current_assistant_message.id,
            part_type="tool",
            tool=tool_name,
            call_id=tool_call_id,
            state=tool_state,
        )
        self._current_assistant_message.parts.append(tool_part)
        await self._update_assistant_display()

        try:
            from opencode_python.ai.tool_execution import ToolExecutionManager
            tool_manager = ToolExecutionManager(self.session.id)

            result = await tool_manager.execute_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_call_id=tool_call_id,
                message_id=self._current_assistant_message.id,
                agent=str(self.ai_session.provider_id),
                model=self.ai_session.model,
            )

            result_part = getattr(result, 'part', None)
            if isinstance(result_part, ToolPart):
                tool_part.state = result_part.state
            await self._update_assistant_display()

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            tool_part.state.status = "error"
            tool_part.state.output = str(e)
            await self._update_assistant_display()

    async def _display_message(self, message: Message, is_streaming: bool = False) -> None:
        """Display a message in the timeline"""
        parts_data: List[Dict[str, Any]] = []
        for p in message.parts:
            if isinstance(p, (TextPart, ToolPart, FilePart, ReasoningPart,
                            SnapshotPart, PatchPart, AgentPart, SubtaskPart,
                            RetryPart, CompactionPart)):
                parts_data.append(p.model_dump())
            else:
                parts_data.append(p)
        
        message_view = MessageView(
            message_data={
                "role": message.role,
                "time": message.time,
                "parts": parts_data,
                "is_streaming": is_streaming,
            }
        )
        
        message_view.set_class(True, message.role)
        
        await self.messages_container.mount(message_view)
        
        if message.role == "assistant" and is_streaming:
            self._current_assistant_view = message_view

    async def _update_assistant_display(self) -> None:
        """Update the currently streaming assistant message display"""
        if self._current_assistant_view and self._current_assistant_message:
            parts_data: List[Dict[str, Any]] = []
            for p in self._current_assistant_message.parts:
                if isinstance(p, (TextPart, ToolPart, FilePart, ReasoningPart,
                                SnapshotPart, PatchPart, AgentPart, SubtaskPart,
                                RetryPart, CompactionPart)):
                    parts_data.append(p.model_dump())
                else:
                    parts_data.append(p)

            self._current_assistant_view.message_data = {
                "role": "assistant",
                "time": self._current_assistant_message.time,
                "parts": parts_data,
                "is_streaming": self.is_streaming,
            }
            self._current_assistant_view.remove_children()
            for child in self._current_assistant_view._compose_content():
                await self._current_assistant_view.mount(child)
            self._scroll_to_bottom()

    async def _save_assistant_message(self) -> None:
        """Save the assistant message to storage"""
        from opencode_python.core.session import SessionManager
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir
        from pathlib import Path

        assert self._current_assistant_message is not None, "Current assistant message must be set"

        try:
            storage_dir = get_storage_dir()
            storage = SessionStorage(storage_dir)
            work_dir = Path.cwd()
            manager = SessionManager(storage, work_dir)

            await manager.create_message(
                session_id=self.session.id,
                role="assistant",
                text=self._current_assistant_message.text,
            )

            self.messages = self.messages + [self._current_assistant_message]

            logger.info(f"Saved assistant message: {self._current_assistant_message.id}")

        except Exception as e:
            logger.error(f"Error saving assistant message: {e}")

    def _scroll_to_bottom(self) -> None:
        """Scroll messages to bottom"""
        self.messages_container.scroll_end(animate=False)
