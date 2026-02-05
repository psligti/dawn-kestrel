"""Essential keybindings for OpenCode TUI application

This module provides a centralized location for defining and managing
essential keybindings that are used throughout the application.
"""

from textual.binding import Binding


keybindings = [
    Binding("q", "quit", "Quit", show=True),
    Binding("ctrl+c", "quit", "Quit", show=False),
    Binding("arrow_up", "navigate_up", "Navigate Up", show=True),
    Binding("arrow_down", "navigate_down", "Navigate Down", show=True),
    Binding("arrow_left", "navigate_left", "Navigate Left", show=True),
    Binding("arrow_right", "navigate_right", "Navigate Right", show=True),
    Binding("/", "open_command", "Open Command Palette", show=True),
    Binding("enter", "confirm", "Confirm", show=True),
    Binding("escape", "cancel", "Cancel", show=True),
]


def get_keybindings() -> list[Binding]:
    """Get the keybindings list for use in apps"""
    return keybindings
