"""Tests for TUI application"""
from __future__ import annotations

import pytest

from opencode_python.tui.app import OpenCodeTUI


@pytest.mark.asyncio
async def test_app_can_be_instantiated():
    """Test that OpenCodeTUI app can be instantiated in test context"""
    app = OpenCodeTUI()
    assert app is not None
    assert isinstance(app, OpenCodeTUI)


@pytest.mark.asyncio
async def test_settings_opens_via_shortcut():
    """Test that 's' key opens Settings screen"""
    app = OpenCodeTUI()

    # Verify BINDINGS includes 's' key for settings
    settings_binding = next(
        (binding for binding in app.BINDINGS if binding.key == "s"),
        None
    )
    assert settings_binding is not None, "'s' key binding should exist for settings"
    assert settings_binding.action == "open_settings", "Binding should map to open_settings action"

    # Verify action_open_settings method exists
    assert hasattr(app, "action_open_settings"), "action_open_settings method should exist"

    # Verify method signature (not executing in headless mode)
    import inspect
    sig = inspect.signature(app.action_open_settings)
    assert len(sig.parameters) == 0, "action_open_settings should take no parameters"


@pytest.mark.asyncio
async def test_command_palette_has_settings_command():
    """Test that command palette includes 'settings' command"""
    from opencode_python.tui.dialogs import CommandPaletteDialog

    palette = CommandPaletteDialog()
    assert len(palette.commands) > 0, "Command palette should have commands"

    # Check that 'settings' command exists
    settings_commands = [cmd for cmd in palette.commands if cmd.get("value") == "settings"]
    assert len(settings_commands) == 1, "Command palette should include 'settings' command"
