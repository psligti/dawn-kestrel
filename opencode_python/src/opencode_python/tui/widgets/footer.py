"""Footer Widget for OpenCode TUI"""
from __future__ import annotations

from typing import Optional

from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class SessionFooter(Static):
    """Footer widget displaying keyboard hints, status messages, and metadata

    Displays:
    - Keyboard shortcut hints (q, /, Enter, Escape)
    - Status messages (sync, pending messages)
    - Metadata (tokens, cost, model)

    All content is read-only - no interactive elements.
    """

    # Reactive properties for updates
    status: reactive[str] = reactive("")
    tokens: reactive[str] = reactive("")
    cost: reactive[str] = reactive("")
    model: reactive[Optional[str]] = reactive(None)

    DEFAULT_CSS = """
    SessionFooter {
        dock: bottom;
        height: auto;
        padding: 1 2;
        background: $secondary;
        text-align: left;
    }

    SessionFooter .hints {
        color: $text-muted;
    }

    SessionFooter .status {
        color: $primary;
        text-style: bold;
    }

    SessionFooter .metadata {
        color: $text-muted;
    }
    """

    def __init__(
        self,
        status: str = "",
        tokens: str = "",
        cost: str = "",
        model: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialize SessionFooter

        Args:
            status: Status message (sync, pending messages)
            tokens: Token usage information
            cost: Cost information
            model: Model name being used
            **kwargs: Additional Static widget arguments
        """
        super().__init__(**kwargs)
        self._status = status
        self._tokens = tokens
        self._cost = cost
        self._model = model
        # Initialize reactive properties
        self.status = status
        self.tokens = tokens
        self.cost = cost
        self.model = model
        self._update_content()

    def _update_content(self) -> None:
        """Update footer content based on current properties"""
        content_parts = []

        # Add keyboard hints
        hints = "[hints]q: quit | /: commands | Enter: confirm | Escape: cancel[/hints]"
        content_parts.append(hints)

        # Add status if provided
        if self.status:
            content_parts.append(f"[status] {self.status}[/status]")

        # Add metadata if provided
        metadata_parts = []
        if self.tokens:
            metadata_parts.append(f"{self.tokens} tokens")
        if self.cost:
            metadata_parts.append(f"{self.cost}")
        if self.model:
            metadata_parts.append(f"model: {self.model}")

        if metadata_parts:
            content_parts.append(f"[metadata]{' | '.join(metadata_parts)}[/metadata]")

        # Update display
        self.update(" | ".join(content_parts) if content_parts else "")

    def watch_status(self, old_value: str, new_value: str) -> None:
        """Called when status changes"""
        self._status = new_value
        self._update_content()

    def watch_tokens(self, old_value: str, new_value: str) -> None:
        """Called when tokens change"""
        self._tokens = new_value
        self._update_content()

    def watch_cost(self, old_value: str, new_value: str) -> None:
        """Called when cost changes"""
        self._cost = new_value
        self._update_content()

    def watch_model(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """Called when model changes"""
        self._model = new_value
        self._update_content()

    # Property accessors for backward compatibility
    @property
    def status_value(self) -> str:
        """Get current status"""
        return self._status

    @property
    def tokens_value(self) -> str:
        """Get current tokens"""
        return self._tokens

    @property
    def cost_value(self) -> str:
        """Get current cost"""
        return self._cost

    @property
    def model_value(self) -> Optional[str]:
        """Get current model"""
        return self._model
