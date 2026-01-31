"""Prompt Area Widget for OpenCode TUI"""
from __future__ import annotations

from textual.message import Message
from textual.widgets import TextArea


class PromptArea(TextArea):
    """Multi-line text input for user prompts with auto-expansion

    Features:
    - Auto-expansion (height: auto, max-height: 50vh)
    - Submit on Enter (Shift+Enter for new line)
    - Emits PromptSubmitted message on submit

    The widget automatically expands its height as the user types,
    up to a maximum of 50vh (50% of viewport height), after which
    it scrolls internally.
    """

    DEFAULT_CSS = """
    PromptArea {
        height: auto;
        max-height: 50vh;
        border: solid #56b6c2 40%;
        padding: 0 1;
        background: #1e1e1e;
        min-height: 3;
    }

    PromptArea:focus {
        border: solid #9d7cd8;
        padding: 0 1;
    }
    """

    class Submitted(Message):
        """Event emitted when prompt is submitted via Enter key"""

        def __init__(self, text: str) -> None:
            """Initialize prompt submitted event

            Args:
                text: The prompt text that was submitted
            """
            super().__init__()
            self.text = text

    def __init__(self, placeholder: str = "", id: str | None = None, **kwargs) -> None:
        """Initialize PromptArea

        Args:
            placeholder: Placeholder text to display when empty
            id: Widget identifier
            **kwargs: Additional TextArea arguments
        """
        super().__init__(placeholder=placeholder, id=id, **kwargs)

    def on_key(self, event) -> None:
        """Handle key press events

        - Enter: Submit prompt (if not empty)
        - Shift+Enter: Insert newline (default behavior)

        Args:
            event: Key event from Textual
        """
        if event.key == "enter" and not event.shift_key:
            # Get current text
            text = self.text.strip()

            # Only submit if there's content
            if text:
                # Emit submitted event
                self.post_message(self.Submitted(text))
                # Clear the text area
                self.text = ""

            # Stop the event from propagating further
            event.stop()
