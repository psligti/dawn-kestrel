"""OpenCode Python - Session Creation Screen"""
from __future__ import annotations

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    TextArea,
    Static,
)


class SessionCreationScreen(ModalScreen[str]):
    """Screen for creating a new session with repository context"""

    CSS = """
    SessionCreationScreen {
        align: center middle;
    }

    #session-form {
        width: 80;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2;
    }

    .form-row {
        height: auto;
        padding: 1;
    }

    .label {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    Input, TextArea {
        width: 1fr;
    }

    .error-message {
        color: $error;
        text-style: bold;
    }

    .button-row {
        height: 3;
        align: right middle;
        margin-top: 2;
    }

    Button {
        margin: 0 1;
    }

    Button.-primary {
        background: $primary;
    }

    Button.-default {
        background: $surface;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.repo_path_input: Input = Input(placeholder="/path/to/repo", id="repo-path")
        self.title_input: Input = Input(placeholder="Session title", id="session-title")
        self.objective_input: TextArea = TextArea(placeholder="What do you want to accomplish?", id="objective")
        self.constraints_input: TextArea = TextArea(placeholder="Any constraints or limitations?", id="constraints")
        self.error_message: Static = Static("", id="error-message", classes="error-message")

    def compose(self) -> ComposeResult:
        with Container(id="session-form"):
            yield Label("Create New Session", classes="label")
            yield self.error_message

            with Vertical(classes="form-row"):
                yield Label("Title:", classes="label")
                yield self.title_input

            with Vertical(classes="form-row"):
                yield Label("Repository Path:", classes="label")
                yield self.repo_path_input

            with Vertical(classes="form-row"):
                yield Label("Objective:", classes="label")
                yield self.objective_input

            with Vertical(classes="form-row"):
                yield Label("Constraints:", classes="label")
                yield self.constraints_input

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Create", variant="primary", id="create")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "create":
            self._create_session()

    def _create_session(self) -> None:
        title = self.title_input.value.strip()
        repo_path = self.repo_path_input.value.strip()
        objective = self.objective_input.text.strip()
        constraints = self.constraints_input.text.strip()

        if not title:
            self._show_error("Title is required")
            return

        if not repo_path:
            self._show_error("Repository path is required")
            return

        if not Path(repo_path).exists():
            self._show_error(f"Repository path does not exist: {repo_path}")
            return

        if not Path(repo_path).is_dir():
            self._show_error(f"Repository path is not a directory: {repo_path}")
            return

        result = {
            "title": title,
            "repo_path": repo_path,
            "objective": objective or None,
            "constraints": constraints or None,
        }

        self.dismiss(result)

    def _show_error(self, message: str) -> None:
        self.error_message.update(message)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in ("repo-path", "session-title"):
            pass
