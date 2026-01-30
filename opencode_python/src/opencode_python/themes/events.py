"""Custom events for theme and layout changes."""

from __future__ import annotations

from typing import Optional

from textual.message import Message


class ThemeChangeEvent(Message):
    """Event emitted when theme changes."""

    def __init__(
        self,
        theme_slug: str,
        density: Optional[str] = None,
        reduced_motion: Optional[bool] = None,
    ) -> None:
        """Initialize theme change event.

        Args:
            theme_slug: New theme slug.
            density: New density mode (if changed).
            reduced_motion: New reduced motion setting (if changed).
        """
        super().__init__()
        self.theme_slug = theme_slug
        self.density = density
        self.reduced_motion = reduced_motion


class KeybindingUpdateEvent(Message):
    """Event emitted when keybindings are updated."""

    def __init__(
        self,
        action: str,
        key: str,
        old_key: Optional[str] = None,
    ) -> None:
        """Initialize keybinding update event.

        Args:
            action: Action that was rebound.
            key: New key binding.
            old_key: Previous key binding (if any).
        """
        super().__init__()
        self.action = action
        self.key = key
        self.old_key = old_key


class LayoutToggleEvent(Message):
    """Event emitted when layout density changes."""

    def __init__(
        self,
        density: str,
    ) -> None:
        """Initialize layout toggle event.

        Args:
            density: New density mode.
        """
        super().__init__()
        self.density = density
