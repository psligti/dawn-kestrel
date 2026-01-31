"""OpenCode Python - Session Settings Screen for TUI

Provides a screen for configuring agent settings per session:
- Override model, temperature, budget
- View audit trail of config changes
- Emit events on configuration updates
"""

from typing import Optional
import logging

from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Button, Static, Label
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message

from opencode_python.agents import AgentConfig, AgentConfigStorage, AgentProfile
from opencode_python.core.event_bus import bus


logger = logging.getLogger(__name__)


class ConfigUpdated(Message):
    """Event emitted when agent configuration is updated"""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        super().__init__()


class SessionSettingsScreen(Screen):
    """Session settings screen for agent configuration"""

    BINDINGS = [
        ("escape", "pop_screen", "Cancel"),
        ("ctrl+c", "quit", "Quit"),
        ("f10", "save_config", "Save"),
    ]

    def __init__(
        self,
        session_id: str,
        agent_config: Optional[AgentConfig] = None,
        agent_profile: Optional[AgentProfile] = None,
        config_storage: Optional[AgentConfigStorage] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.config = agent_config
        self.profile = agent_profile
        self.config_storage = config_storage

        self.model_input: reactive[str] = reactive(
            agent_config.model if agent_config and agent_config.model
            else (agent_profile.default_model if agent_profile else "")
        )

        self.temp_input: reactive[float] = reactive(
            agent_config.temperature if agent_config and agent_config.temperature is not None
            else (agent_profile.default_temperature if agent_profile else 0.7)
        )

        self.budget_input: reactive[Optional[int]] = reactive(
            agent_config.budget if agent_config and agent_config.budget is not None
            else (agent_profile.default_budget if agent_profile else None)
        )

    def compose(self) -> ComposeResult:
        with Vertical(id="session-settings-screen"):
            with Vertical(id="settings-form"):
                with Horizontal(id="model-setting"):
                    yield Label("Model:", id="model-label")
                    yield Input(
                        id="model-input",
                        value=self.model_input,
                        placeholder="e.g., claude-3-5-sonnet-20241022"
                    )

                with Horizontal(id="temperature-setting"):
                    yield Label("Temperature:", id="temperature-label")
                    yield Input(
                        id="temperature-input",
                        value=str(self.temp_input),
                        placeholder="0.0 - 2.0"
                    )

                with Horizontal(id="budget-setting"):
                    yield Label("Budget (tokens):", id="budget-label")
                    yield Input(
                        id="budget-input",
                        value=str(self.budget_input) if self.budget_input else "",
                        placeholder="Optional token limit"
                    )

            with Vertical(id="audit-trail-panel"):
                yield Static("Configuration Audit Trail", id="audit-trail-title")
                yield Static("No changes yet", id="audit-trail-content")

            with Horizontal(id="settings-actions"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Save", id="btn-save", variant="primary")

    def on_mount(self) -> None:
        self._update_audit_trail_display()

    def on_input_changed(self, event) -> None:
        input_id = event.input.id

        if input_id == "model-input":
            self.model_input = event.value
        elif input_id == "temperature-input":
            try:
                temp_val = float(event.value)
                if 0.0 <= temp_val <= 2.0:
                    self.temp_input = temp_val
            except ValueError:
                pass
        elif input_id == "budget-input":
            try:
                budget_val = int(event.value) if event.value else None
                self.budget_input = budget_val
            except ValueError:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.app.pop_screen()
        elif event.button.id == "btn-save":
            self._save_configuration()

    def action_save_config(self) -> None:
        self._save_configuration()

    def _save_configuration(self) -> None:
        if not self.config_storage:
            logger.error("No config storage available")
            return

        model = self.query_one("#model-input", Input).value
        temp_str = self.query_one("#temperature-input", Input).value
        budget_str = self.query_one("#budget-input", Input).value

        try:
            temp = float(temp_str) if temp_str else None
        except ValueError:
            self.app.notify("Invalid temperature value", severity="error")
            return

        try:
            budget = int(budget_str) if budget_str else None
        except ValueError:
            self.app.notify("Invalid budget value", severity="error")
            return

        config = self.config_storage.load(self.session_id)

        if not config:
            config = AgentConfig(
                session_id=self.session_id,
                agent_profile_id=self.profile.id if self.profile else "unknown"
            )

        if model != config.model:
            config.update_field("model", model, "user")

        if temp is not None and temp != config.temperature:
            config.update_field("temperature", temp, "user")

        if budget != config.budget:
            config.update_field("budget", budget, "user")

        self.config_storage.save(config)

        self.post_message(ConfigUpdated(config))

        logger.info(f"Saved agent config for session {self.session_id}")
        self.app.notify("Configuration saved", severity="success")
        self.app.pop_screen()

    def _update_audit_trail_display(self) -> None:
        if not self.config:
            return

        audit_widget = self.query_one("#audit-trail-content", Static)
        summary = self.config.get_audit_summary()

        if not summary:
            audit_widget.update("No changes yet")
            return

        lines = []
        for entry in summary[-10:]:
            lines.append(f"[dim]{entry['timestamp']}[/dim]")
            lines.append(f"  Field: {entry['field']}")
            lines.append(f"  {entry['old_value'] or 'None'} → {entry['new_value'] or 'None'}")
            lines.append(f"  Source: {entry['action_source']}")
            if entry.get('reason'):
                lines.append(f"  Reason: {entry['reason']}")
            lines.append("")

        audit_widget.update("\n".join(lines))
