"""Session Header Widget for OpenCode TUI"""
from __future__ import annotations

from typing import Optional

from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class SessionHeader(Static):
    """Header widget displaying session information with breadcrumbs and model display

    Displays:
    - Session title (bold)
    - Breadcrumb navigation to parent session (if applicable)
    - Model information (if provided)
    - Agent information (if provided)

    All content is read-only - no interactive elements.
    """

    # Reactive properties for updates
    session_title: reactive[str] = reactive("")
    parent_session_id: reactive[Optional[str]] = reactive(None)
    model: reactive[Optional[str]] = reactive(None)
    agent: reactive[Optional[str]] = reactive(None)

    DEFAULT_CSS = """
    SessionHeader {
        dock: top;
        height: auto;
        padding: 1 2;
        background: $secondary;
        text-align: left;
    }

    SessionHeader .title {
        text-style: bold;
    }

    SessionHeader .breadcrumb {
        color: $text-muted;
    }

    SessionHeader .model {
        color: $accent;
    }

    SessionHeader .agent {
        color: $success;
    }
    """

    def __init__(
        self,
        session_title: str = "",
        parent_session_id: Optional[str] = None,
        model: Optional[str] = None,
        agent: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialize SessionHeader

        Args:
            session_title: Title of the current session
            parent_session_id: ID of parent session (if this is a subagent session)
            model: Model name being used
            agent: Agent name being used
            **kwargs: Additional Static widget arguments
        """
        super().__init__(**kwargs)
        self._session_title = session_title
        self._parent_session_id = parent_session_id
        self._model = model
        self._agent = agent
        # Initialize reactive properties
        self.session_title = session_title
        self.parent_session_id = parent_session_id
        self.model = model
        self.agent = agent
        self._update_content()

    def _update_content(self) -> None:
        """Update the header content based on current properties"""
        content_parts = []

        # Add session title
        if self.session_title:
            content_parts.append(f"[title]#{self.session_title}[/title]")

        # Add breadcrumb if parent session exists
        if self.parent_session_id:
            content_parts.append(
                f"[breadcrumb]Subagent session (Parent: {self.parent_session_id})[/breadcrumb]"
            )

        # Add model if provided
        if self.model:
            content_parts.append(f"[model]Model: {self.model}[/model]")

        # Add agent if provided
        if self.agent:
            content_parts.append(f"[agent]Agent: {self.agent}[/agent]")

        # Update display
        self.update("\n".join(content_parts) if content_parts else "")

    def watch_session_title(self, old_value: str, new_value: str) -> None:
        """Called when session_title changes"""
        self._session_title = new_value
        self._update_content()

    def watch_parent_session_id(
        self, old_value: Optional[str], new_value: Optional[str]
    ) -> None:
        """Called when parent_session_id changes"""
        self._parent_session_id = new_value
        self._update_content()

    def watch_model(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """Called when model changes"""
        self._model = new_value
        self._update_content()

    def watch_agent(self, old_value: Optional[str], new_value: Optional[str]) -> None:
        """Called when agent changes"""
        self._agent = new_value
        self._update_content()

    # Property accessors for backward compatibility
    @property
    def session_title_value(self) -> str:
        """Get current session title"""
        return self._session_title

    @property
    def parent_session_id_value(self) -> Optional[str]:
        """Get current parent session ID"""
        return self._parent_session_id

    @property
    def model_value(self) -> Optional[str]:
        """Get current model"""
        return self._model

    @property
    def agent_value(self) -> Optional[str]:
        """Get current agent"""
        return self._agent
