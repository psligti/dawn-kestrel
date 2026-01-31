"""Top Bar Widget for Vertical Stack TUI
Displays provider/account/model/agent/session, run state, and primary action.
"""

from __future__ import annotations
from textual.widget import Widget
from textual.reactive import reactive
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Button
from textual.message import Message
from enum import Enum


class RunState(Enum):
    """Run state enum"""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"


class ContextUpdated(Message):
    """Emitted when context changes"""
    pass


class TopBar(Widget):
    """Top bar widget displaying context and run state"""
    
    CSS = """
    TopBar {
        dock: top;
        height: auto;
        padding: 1 2;
        background: $secondary;
        border-bottom: solid $primary 40%;
    }
    
    TopBar .context-display {
        height: auto;
        content-align: center;
        text-align: center;
    }
    
    TopBar .context-item {
        padding: 0 1;
    }
    
    TopBar .separator {
        color: $text-muted;
    }
    
    TopBar .run-state {
        margin-left: 2;
    }
    
    TopBar .status-dot {
        width: 1;
        height: 1;
        background: $success;
        border-radius: 1;
    }
    
    TopBar .status-dot.running {
        background: $warning;
    }
    
    TopBar .status-dot.error {
        background: $error;
    }
    """
    
    # Reactive properties
    provider_id: reactive[str] = reactive("")
    account_id: reactive[str] = reactive("")
    model_id: reactive[str] = reactive("")
    agent: reactive[str] = reactive("")
    session_id: reactive[str] = reactive("")
    run_state: reactive[RunState] = reactive(RunState.IDLE)
    
    def __init__(self, **kwargs):
        """Initialize TopBar"""
        super().__init__(**kwargs)
        self._update_display()
    
    def _update_display(self) -> None:
        """Update widget content based on reactive properties"""
        # Build context items: provider | account | model | agent | session
        items = []
        
        if self.provider_id:
            items.append(Static(self.provider_id, classes="context-item"))
        else:
            items.append(Static("[dim]Provider[/dim]", classes="context-item"))
        
        if items:
            items.append(Static(" | ", classes="separator"))
        
        if self.account_id:
            items.append(Static(self.account_id, classes="context-item"))
        else:
            items.append(Static("[dim]Account[/dim]", classes="context-item"))
        
        if items:
            items.append(Static(" | ", classes="separator"))
        
        if self.model_id:
            items.append(Static(self.model_id, classes="context-item"))
        else:
            items.append(Static("[dim]Model[/dim]", classes="context-item"))
        
        if items:
            items.append(Static(" | ", classes="separator"))
        
        if self.agent:
            items.append(Static(self.agent, classes="context-item"))
        else:
            items.append(Static("[dim]Agent[/dim]", classes="context-item"))
        
        if items:
            items.append(Static(" | ", classes="separator"))
        
        if self.session_id:
            items.append(Static(self.session_id[:12] + "..." if len(self.session_id) > 12 else self.session_id, classes="context-item"))
        else:
            items.append(Static("[dim]Session[/dim]", classes="context-item"))
        
        # Build action section: status dot + button
        status_color = "status-dot"
        if self.run_state == RunState.RUNNING:
            status_color += " running"
        elif self.run_state == RunState.ERROR:
            status_color += " error"
        
        action_section = Horizontal()
        action_section.mount(Static(f"[{status_color}]●[/]", classes="status-dot"))
        action_section.mount(Static(f" {self.run_state.value.lower()}", classes="run-state"))
        action_section.mount(Button("Run" if self.run_state == RunState.IDLE else "Continue", classes="action-button"))
        
        with self.query_one("#context-display", Horizontal):
            self.query_one("#context-display").remove_children()
            for item in items:
                self.query_one("#context-display").mount(item)
    
    # Reactive watchers
    def watch_provider_id(self, old_value: str, new_value: str) -> None:
        self.provider_id = new_value
        self._update_display()
    
    def watch_account_id(self, old_value: str, new_value: str) -> None:
        self.account_id = new_value
        self._update_display()
    
    def watch_model_id(self, old_value: str, new_value: str) -> None:
        self.model_id = new_value
        self._update_display()
    
    def watch_agent(self, old_value: str, new_value: str) -> None:
        self.agent = new_value
        self._update_display()
    
    def watch_session_id(self, old_value: str, new_value: str) -> None:
        self.session_id = new_value
        self._update_display()
    
    def watch_run_state(self, old_value: RunState, new_value: RunState) -> None:
        self.run_state = new_value
        self._update_display()
