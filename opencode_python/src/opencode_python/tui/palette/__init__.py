"""OpenCode Python TUI Palette Module

Provides command palette with action registration, permissions, and event handling.
"""

from opencode_python.tui.palette.command_palette import (
    CommandAction,
    CommandPalette,
    CommandPaletteManager,
    manager,
    register_default_actions,
)

__all__ = [
    "CommandAction",
    "CommandPalette",
    "CommandPaletteManager",
    "manager",
    "register_default_actions",
]
