"""OpenCode Python - Vertical Stack TUI Application

Main TUI application with vertical stack layout:
- TopBar (fixed at top)
- ConversationHistory (scrollable, 1fr height)
- PromptArea (auto-expanding input)
- StatusBar (fixed at bottom)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any, Optional

import asyncio
import logging

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.message import Message

from opencode_python.tui.widgets.header import SessionHeader
from opencode_python.tui.widgets.conversation_history import ConversationHistory, EventType
from opencode_python.tui.widgets.prompt_area import PromptArea
from opencode_python.tui.widgets.status_bar import StatusBar
from opencode_python.tui.context_manager import ContextManager, RunState
from opencode_python.tui.palette.enhanced_command_palette import EnhancedCommandPalette, EnhancedCommandExecute
from opencode_python.core.event_bus import bus, Events, Event

logger = logging.getLogger(__name__)


class PromptSubmitted(Message):
    """Event emitted when prompt is submitted"""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class VerticalStackApp(App[None]):
    """OpenCode Textual TUI application with vertical stack layout"""

    CSS_PATH = Path(__file__).parent / "opencode.css"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+p", "open_command_palette", "Command Palette"),
        Binding("ctrl+z", "undo_context", "Undo Last Switch"),
    ]

    # Widget references
    top_bar: SessionHeader
    conversation_history: ConversationHistory
    prompt_area: PromptArea
    status_bar: StatusBar

    # Context manager
    context_manager: ContextManager

    # Session state
    session_title: str = "OpenCode Session"
    current_model: str = "gpt-4"
    current_agent: str = "assistant"

    # Metrics
    message_count: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0

    def __init__(self, **kwargs):
        """Initialize VerticalStackApp"""
        super().__init__(**kwargs)
        self.context_manager = ContextManager()
        self._initialize_context()

    def _initialize_context(self) -> None:
        """Initialize default context"""
        self.context_manager.provider_id = "openai"
        self.context_manager.account_id = "default"
        self.context_manager.model_id = self.current_model
        self.context_manager.agent = self.current_agent
        self.context_manager.session_id = "session-001"

    def compose(self) -> ComposeResult:
        yield SessionHeader(
            session_title=self.session_title,
            model=self.current_model,
            agent=self.current_agent,
            id="top-bar"
        )

        yield ConversationHistory(id="conversation-history")

        yield PromptArea(
            placeholder="Type your message... (Enter to send, Shift+Enter for new line)",
            id="prompt-area"
        )

        yield StatusBar(id="status-bar")

    async def on_mount(self) -> None:
        """Called when TUI starts"""
        self.app.title = "OpenCode Python"
        logger.info("Vertical Stack TUI mounted")

        self.top_bar = self.query_one("#top-bar", SessionHeader)
        self.conversation_history = self.query_one("#conversation-history", ConversationHistory)
        self.prompt_area = self.query_one("#prompt-area", PromptArea)
        self.status_bar = self.query_one("#status-bar", StatusBar)

        await self._subscribe_to_events()
        self._update_metrics_display()

        self.conversation_history.add_system_event(
            EventType.INFO,
            "Welcome to OpenCode! Press Ctrl+P for commands."
        )

    async def _subscribe_to_events(self) -> None:
        """Subscribe to event bus events"""
        await bus.subscribe(Events.MESSAGE_CREATED, self._on_message_created)

        if hasattr(Events, "COST_UPDATED"):
            await bus.subscribe(Events.COST_UPDATED, self._on_cost_updated)

    async def _on_message_created(self, event: Event) -> None:
        """Handle MESSAGE_CREATED event

        Args:
            event: Event object with message data
        """
        data = event.data
        self.message_count += 1

        if "cost" in data:
            self.total_cost += data["cost"]
        if "tokens" in data:
            self.total_tokens += data["tokens"]

        self._update_metrics_display()

    async def _on_cost_updated(self, event: Event) -> None:
        """Handle COST_UPDATED event

        Args:
            event: Event object with cost data
        """
        data = event.data
        if "cost" in data:
            self.total_cost = data["cost"]
        if "tokens" in data:
            self.total_tokens = data["tokens"]
        if "message_count" in data:
            self.message_count = data["message_count"]

        self._update_metrics_display()

    def _update_metrics_display(self) -> None:
        """Update metrics display in status bar"""
        if self.status_bar:
            self.status_bar.message_count = self.message_count
            self.status_bar.cost = self.total_cost
            self.status_bar.tokens = self.total_tokens

    def on_prompt_area_submitted(self, event: PromptArea.Submitted) -> None:
        """Handle prompt submission from PromptArea

        Args:
            event: PromptArea.Submitted event with prompt text
        """
        prompt_text = event.text

        self.conversation_history.add_message("user", prompt_text)

        self.context_manager.run_state = RunState.RUNNING

        if self.context_manager.session_id != "session-001":
            self.conversation_history.add_system_event(
                EventType.CONTEXT_SWITCH,
                f"Switched to session: {self.context_manager.session_id}"
            )

        asyncio.create_task(self._handle_ai_response(prompt_text))

    async def _handle_ai_response(self, prompt_text: str) -> None:
        """Handle AI response generation

        Args:
            prompt_text: The user's prompt text
        """
        await asyncio.sleep(0.5)

        response_text = f"I received your message: {prompt_text}"
        self.conversation_history.add_message("assistant", response_text)

        self.message_count += 1
        self.total_tokens += len(prompt_text.split()) + len(response_text.split())
        self._update_metrics_display()

        self.context_manager.run_state = RunState.IDLE

    def on_enhanced_command_execute(self, event: EnhancedCommandExecute) -> None:
        self._handle_enhanced_command(event.scope, event.item_id)

    def action_open_command_palette(self) -> None:
        storage_path = Path.home() / ".opencode" / "recents.json"

        providers = self._get_sample_providers()
        accounts = self._get_sample_accounts()
        models = self._get_sample_models()
        agents = self._get_sample_agents()
        sessions = self._get_sample_sessions()

        palette = EnhancedCommandPalette(
            storage_path=storage_path,
            providers=providers,
            accounts=accounts,
            models=models,
            agents=agents,
            sessions=sessions,
            on_execute=self._handle_enhanced_command
        )
        self.push_screen(palette)

    def _get_sample_providers(self):
        from opencode_python.providers_mgmt.models import Provider
        from opencode_python.providers.base import ProviderID
        
        return [
            Provider(
                id=ProviderID.OPENAI,
                name="OpenAI",
                description="OpenAI API provider",
                base_url="https://api.openai.com/v1"
            ),
        ]
    
    def _get_sample_accounts(self):
        from opencode_python.providers_mgmt.models import Account
        
        return [
            Account(
                id="default",
                name="Default Account",
                description="Default OpenAI account",
                provider_id="openai",
                is_active=True
            ),
        ]
    
    def _get_sample_models(self):
        from opencode_python.providers.base import ModelInfo, ProviderID
        
        return [
            ModelInfo(
                id="gpt-4",
                name="GPT-4",
                family="gpt-4",
                provider_id=ProviderID.OPENAI,
                api_id="gpt-4"
            ),
            ModelInfo(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                family="gpt-3.5",
                provider_id=ProviderID.OPENAI,
                api_id="gpt-3.5-turbo"
            ),
        ]
    
    def _get_sample_agents(self):
        from opencode_python.agents.profiles import AgentProfile
        
        return [
            AgentProfile(
                id="assistant",
                name="Assistant",
                description="General purpose AI assistant",
                category="general",
                tags=["chat", "general"]
            ),
            AgentProfile(
                id="coder",
                name="Coder",
                description="Code-focused AI assistant",
                category="development",
                tags=["code", "programming"]
            ),
        ]
    
    def _get_sample_sessions(self):
        return [
            {
                "id": "session-001",
                "meta": {
                    "objective": "Build a web application"
                }
            },
            {
                "id": "session-002",
                "meta": {
                    "objective": "Debug production issue"
                }
            },
        ]

    def _handle_enhanced_command(self, scope: str, item_id: str) -> None:
        """Handle EnhancedCommandPalette command execution

        Args:
            scope: The scope of the selected item (providers, accounts, models, agents, sessions)
            item_id: The ID of the selected item
        """
        logger.info(f"Enhanced command executed: scope={scope}, item_id={item_id}")

        if scope == "providers":
            self.context_manager.switch_provider(item_id)
            self._update_context_display()
            self.conversation_history.add_system_event(
                EventType.CONTEXT_SWITCH,
                f"Switched provider to: {item_id}"
            )

        elif scope == "accounts":
            self.context_manager.switch_account(item_id)
            self.conversation_history.add_system_event(
                EventType.CONTEXT_SWITCH,
                f"Switched account to: {item_id}"
            )

        elif scope == "models":
            self.context_manager.switch_model(item_id)
            self.current_model = item_id
            self.top_bar.model = item_id
            self.conversation_history.add_system_event(
                EventType.CONTEXT_SWITCH,
                f"Switched model to: {item_id}"
            )

        elif scope == "agents":
            self.context_manager.switch_agent(item_id)
            self.current_agent = item_id
            self.top_bar.agent = item_id
            self.conversation_history.add_system_event(
                EventType.CONTEXT_SWITCH,
                f"Switched agent to: {item_id}"
            )

        elif scope == "sessions":
            old_session = self.context_manager.session_id
            self.context_manager.switch_session(item_id)
            self.conversation_history.add_system_event(
                EventType.CONTEXT_SWITCH,
                f"Switched session: {old_session} -> {item_id}"
            )

    def action_undo_context(self) -> None:
        """Undo last context switch (Ctrl+Z)"""
        undo_info = self.context_manager.undo_last()

        if undo_info:
            context_type, old_value, new_value = undo_info

            if context_type == "provider":
                self.context_manager.provider_id = old_value
            elif context_type == "account":
                self.context_manager.account_id = old_value
            elif context_type == "model":
                self.context_manager.model_id = old_value
                self.current_model = old_value
                self.top_bar.model = old_value
            elif context_type == "agent":
                self.context_manager.agent = old_value
                self.current_agent = old_value
                self.top_bar.agent = old_value
            elif context_type == "session":
                self.context_manager.session_id = old_value

            self.conversation_history.add_system_event(
                EventType.INFO,
                f"Undid {context_type} switch: {new_value} -> {old_value}"
            )
        else:
            self.conversation_history.add_system_event(
                EventType.ERROR,
                "Nothing to undo"
            )

    def _update_context_display(self) -> None:
        """Update TopBar and StatusBar when context changes"""
        if self.top_bar:
            self.top_bar.model = self.context_manager.model_id
            self.top_bar.agent = self.context_manager.agent

    async def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()
        logger.info("Vertical Stack TUI exited")


# Factory function for creating the app
def create_vertical_stack_app() -> VerticalStackApp:
    """Factory function to create and configure the VerticalStackApp

    Returns:
        Configured VerticalStackApp instance
    """
    app = VerticalStackApp()
    return app
