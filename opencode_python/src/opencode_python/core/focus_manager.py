"""Focus manager for tracking and managing focus state across TUI components."""

from __future__ import annotations

import logging
from typing import Optional, Dict, List, Callable
from enum import Enum

from opencode_python.core.event_bus import bus, Events
from opencode_python.core.focus_events import FocusWillChangeEvent, FocusDidChangeEvent
from opencode_python.themes.models import ThemeSettings

logger = logging.getLogger(__name__)


class FocusState(Enum):
    """Focus states for TUI components."""
    DRAWER_FOCUSED = "drawer_focused"
    MAIN_FOCUSED = "main_focused"
    PROMPT_FOCUSED = "prompt_focused"
    TOP_BAR_FOCUSED = "top_bar_focused"


class FocusModel:
    """Model for tracking focus state and history."""

    current_state: FocusState = FocusState.MAIN_FOCUSED
    history: List[FocusState] = []
    focus_stack: List[str] = []

    def __init__(self):
        """Initialize focus model."""
        self.history = [FocusState.MAIN_FOCUSED]

    def set_focus(self, state: FocusState, widget_id: Optional[str] = None) -> None:
        """Set current focus state.

        Args:
            state: New focus state.
            widget_id: Widget ID being focused (optional).
        """
        old_state = self.current_state
        self.current_state = state
        self.history.append(old_state)
        self.focus_stack = [widget_id] if widget_id else []

        logger.info(f"Focus changed: {old_state.value} -> {state.value} (widget: {widget_id})")

    def release_focus(self) -> FocusState:
        """Release current focus, return to previous state.

        Returns:
            Previous focus state from history.
        """
        if not self.history:
            logger.warning("No focus history to release, staying in MAIN_FOCUSED")
            return FocusState.MAIN_FOCUSED

        old_state = self.history.pop()
        self.current_state = old_state

        if self.focus_stack:
            self.focus_stack.pop()
            widget_id = self.focus_stack[-1] if self.focus_stack else None
        else:
            widget_id = None

        logger.info(f"Focus released: {old_state.value} -> {self.current_state.value} (widget: {widget_id})")
        return self.current_state

    def get_focus_history(self) -> List[FocusState]:
        """Get complete focus history."""
        return self.history.copy()

    def get_current_widget(self) -> Optional[str]:
        """Get current widget ID if any.

        Returns:
            Widget ID or None.
        """
        return self.focus_stack[-1] if self.focus_stack else None


class FocusManager:
    """Global focus manager for TUI application.

    Features:
    - Singleton pattern for global access
    - Request/release focus across components
    - Focus history tracking
    - Event bus integration (FOCUS_WILL_CHANGE, FOCUS_DID_CHANGE)
    - Settings integration for persistence
    """

    _instance: Optional["FocusManager"] = None

    def __init__(self):
        """Initialize focus manager."""
        self._model = FocusModel()

    @classmethod
    def get_instance(cls) -> "FocusManager":
        """Get singleton instance of FocusManager.

        Returns:
            FocusManager singleton instance.
        """
        if cls._instance is None:
            cls._instance = FocusManager()
        return cls._instance

    def request_focus(
        self,
        target_widget: str,
        target_id: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """Request focus for a target widget.

        Args:
            target_widget: Widget identifier (drawer, main, prompt, top_bar).
            target_id: Specific widget instance ID.
            force: If True, bypass focus validation.

        Raises:
            ValueError: If target_widget is invalid.
        """
        if target_widget not in ["drawer", "main", "prompt", "top_bar"]:
            raise ValueError(
                f"Invalid target_widget: {target_widget}. "
                f"Must be one of: drawer, main, prompt, top_bar"
            )

        # Emit event before changing state
        import asyncio
        asyncio.create_task(self._emit_will_change(target_widget, target_id, force))

        old_state = self._model.current_state
        self._model.set_focus(target_widget, target_id)

    def release_focus(self) -> FocusState:
        """Release current focus, return to previous state.

        Returns:
            Previous focus state from history.
        """
        old_state = self._model.current_state

        # Emit event before changing state
        import asyncio
        asyncio.create_task(self._emit_did_change())

        new_state = self._model.release_focus()

        logger.info(f"Focus released: {old_state.value} -> {new_state.value}")

        return new_state

    def get_current_state(self) -> FocusState:
        """Get current focus state.

        Returns:
            Current focus state.
        """
        return self._model.current_state

    def get_current_widget(self) -> Optional[str]:
        """Get current widget ID if any.

        Returns:
            Widget ID or None.
        """
        return self._model.get_current_widget()

    async def _emit_will_change(
        self,
        target_widget: str,
        target_id: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """Emit FOCUS_WILL_CHANGE event."""
        from opencode_python.core.focus_events import FocusWillChangeEvent

        await bus.publish(
            Events.FOCUS_WILL_CHANGE,
            FocusWillChangeEvent(
                target_widget=target_widget,
                target_id=target_id,
                force=force,
            )
        )
    
    async def _emit_did_change(self) -> None:
        """Emit FOCUS_DID_CHANGE event."""
        from opencode_python.core.focus_events import FocusDidChangeEvent

        await bus.publish(
            Events.FOCUS_DID_CHANGE,
            FocusDidChangeEvent(
                target_widget=self._model.current_state.value,
                target_id=self._model.get_current_widget(),
                previous_state=self._model.history[-1] if self._model.history else None,
            )
        )

    def set_drawer_focused(self) -> None:
        """Set drawer as focused."""
        self.request_focus("drawer", None)

    def set_main_focused(self) -> None:
        """Set main as focused."""
        self.request_focus("main", None)

    def set_prompt_focused(self) -> None:
        """Set prompt as focused."""
        self.request_focus("prompt", None)

    def set_top_bar_focused(self) -> None:
        """Set top bar as focused."""
        self.request_focus("top_bar", None)

    def request_focus_from_component(self, widget: str, widget_id: Optional[str] = None) -> None:
        """Convenience method for components to request focus.

        Args:
            widget: Widget type identifier.
            widget_id: Specific widget instance ID.
        """
        self.request_focus(widget, widget_id)


def get_focus_manager() -> FocusManager:
    """Get singleton instance of FocusManager.

    Convenience function for accessing the global FocusManager instance.

    Returns:
        FocusManager singleton instance.
    """
    return FocusManager.get_instance()
