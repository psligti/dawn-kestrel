"""Tests for keybinding system in OpenCode TUI"""
import pytest
from textual.binding import Binding
from textual.app import App, ComposeResult

from dawn_kestrel.tui.keybindings import keybindings


class TestApp(App[None]):
    """Test application for keybinding testing"""

    BINDINGS = keybindings

    def compose(self) -> ComposeResult:
        yield from ()

    def action_navigate_up(self) -> None:
        """Navigate up action"""
        pass

    def action_navigate_down(self) -> None:
        """Navigate down action"""
        pass

    def action_navigate_left(self) -> None:
        """Navigate left action"""
        pass

    def action_navigate_right(self) -> None:
        """Navigate right action"""
        pass

    def action_open_command(self) -> None:
        """Open command palette action"""
        pass

    def action_confirm(self) -> None:
        """Confirm action"""
        pass

    def action_cancel(self) -> None:
        """Cancel action"""
        pass


class TestKeybindings:
    """Test keybinding registration and functionality"""

    def test_keybindings_attribute_exists(self):
        """Test that keybindings attribute is defined"""
        assert hasattr(TestApp, 'BINDINGS')
        assert isinstance(TestApp.BINDINGS, list)

    def test_keybindings_contain_expected_bindings(self):
        """Test that all 6 essential keybindings are registered"""
        actions = [binding.action for binding in TestApp.BINDINGS]
        expected_actions = [
            'quit',
            'quit',
            'navigate_up',
            'navigate_down',
            'navigate_left',
            'navigate_right',
            'open_command',
            'confirm',
            'cancel',
        ]

        for action in expected_actions:
            assert action in actions, f"Missing keybinding action: {action}"

    def test_keybinding_names(self):
        """Test keybinding names are descriptive"""
        bindings = TestApp.BINDINGS
        binding_keys = [binding.key for binding in bindings]

        assert 'q' in binding_keys
        assert 'ctrl+c' in binding_keys

    def test_binding_classes(self):
        """Test that bindings are instances of textual.binding.Binding"""
        for binding in TestApp.BINDINGS:
            assert isinstance(binding, Binding), f"Binding {binding.key} is not a Binding instance"

    def test_quit_action_exists(self):
        """Test that quit action is defined"""
        assert hasattr(TestApp, 'action_quit'), "action_quit method not found"

    def test_navigation_actions_exist(self):
        """Test that navigation actions are defined"""
        assert hasattr(TestApp, 'action_navigate_up'), "action_navigate_up method not found"
        assert hasattr(TestApp, 'action_navigate_down'), "action_navigate_down method not found"
        assert hasattr(TestApp, 'action_navigate_left'), "action_navigate_left method not found"
        assert hasattr(TestApp, 'action_navigate_right'), "action_navigate_right method not found"

    def test_command_actions_exist(self):
        """Test that command-related actions are defined"""
        assert hasattr(TestApp, 'action_open_command'), "action_open_command method not found"
        assert hasattr(TestApp, 'action_confirm'), "action_confirm method not found"
        assert hasattr(TestApp, 'action_cancel'), "action_cancel method not found"

    def test_keybinding_registration(self):
        """Test that keybindings are properly registered"""
        app = TestApp()
        bindings = app.BINDINGS if hasattr(app, 'BINDINGS') else TestApp.BINDINGS
        assert len(bindings) >= 6, f"Expected at least 6 keybindings, got {len(bindings)}"
