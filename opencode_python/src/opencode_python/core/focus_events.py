"""Focus events for event bus."""

from textual.message import Message
from typing import Optional


class FocusWillChangeEvent(Message):
    """Event emitted before focus changes."""

    def __init__(
        self,
        target_widget: str,
        target_id: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """Initialize focus will change event.

        Args:
            target_widget: Widget being focused (drawer, main, prompt, top_bar).
            target_id: Specific widget instance ID.
            force: If True, bypass focus validation.

        Raises:
            ValueError: If target_widget is invalid.
        """
        super().__init__()
        self.target_widget = target_widget
        self.target_id = target_id
        self.force = force


class FocusDidChangeEvent(Message):
    """Event emitted after focus changes."""

    def __init__(
        self,
        target_widget: str,
        target_id: Optional[str] = None,
        previous_state: str = '',
    ) -> None:
        """Initialize focus did change event.

        Args:
            target_widget: Current focus state (drawer, main, prompt, top_bar).
            target_id: Current widget ID or None.
            previous_state: Previous focus state before change.
        """
        super().__init__()
        self.target_widget = target_widget
        self.target_id = target_id
        self.previous_state = previous_state


__all__ = [
    "FocusWillChangeEvent",
    "FocusDidChangeEvent",
]
