"""Tests for keybinding management."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
import tempfile

from opencode_python.tui.keybindings import (
    KeybindingManager,
    KeybindingEntry,
    KeybindingConflict,
    DEFAULT_KEYBINDINGS,
)


class TestKeybindingEntry:
    """Test keybinding entry dataclass."""

    def test_keybinding_entry_creation(self):
        """Test creating keybinding entry."""
        entry = KeybindingEntry(
            action="test_action",
            key="ctrl+t",
            description="Test action",
            show=True,
            default=True,
        )

        assert entry.action == "test_action"
        assert entry.key == "ctrl+t"
        assert entry.description == "Test action"
        assert entry.show is True
        assert entry.default is True


class TestKeybindingManager:
    """Test keybinding manager."""

    def test_manager_initialization(self, tmp_path):
        """Test initializing keybinding manager."""
        settings_dir = tmp_path / "settings"
        settings_dir.mkdir(parents=True)

        manager = KeybindingManager(settings_dir=settings_dir)

        assert manager is not None

    def test_get_bindings(self):
        """Test getting bindings as Textual Binding objects."""
        manager = KeybindingManager(settings_dir=None)
        bindings = manager.get_bindings()

        assert len(bindings) > 0

        actions = [b.action for b in bindings]
        assert "quit" in actions
        assert "navigate_up" in actions

    def test_get_entries(self):
        """Test getting keybinding entries."""
        manager = KeybindingManager(settings_dir=None)
        entries = manager.get_entries()

        assert len(entries) > 0

        # Check default keybindings exist
        actions = [e.action for e in entries]
        assert "quit" in actions
        assert "navigate_up" in actions
        assert "navigate_down" in actions

    def test_detect_conflicts(self):
        """Test conflict detection."""
        manager = KeybindingManager(settings_dir=None)

        # Test detecting conflict with existing binding
        conflicts = manager.detect_conflicts("q", skip_action="quit")

        # q is not used in defaults, so no conflicts
        assert len(conflicts) == 0

        # Test detecting actual conflict
        conflicts = manager.detect_conflicts("arrow_up", skip_action="navigate_up")
        assert len(conflicts) > 0

    def test_rebind_success(self):
        """Test rebinding an action."""
        manager = KeybindingManager(settings_dir=None)
        entries_before = manager.get_entries()

        success, conflicts = manager.rebind("quit", "ctrl+z", "q")

        assert success is True
        assert len(conflicts) == 0

        entries_after = manager.get_entries()
        quit_entry = next((e for e in entries_after if e.action == "quit"), None)
        assert quit_entry is not None
        assert quit_entry.key == "ctrl+z"
        assert quit_entry.default is False

    def test_rebind_with_conflict(self):
        """Test rebinding with conflict detection."""
        manager = KeybindingManager(settings_dir=None)

        # Try to rebind to an existing key
        success, conflicts = manager.rebind("quit", "arrow_up", "q")

        assert success is False
        assert len(conflicts) > 0

        # Check that original binding is preserved
        entries = manager.get_entries()
        quit_entry = next((e for e in entries if e.action == "quit"), None)
        assert quit_entry is not None
        assert quit_entry.key == "q"  # Should remain unchanged

    def test_restore_defaults(self, tmp_path):
        """Test restoring default keybindings."""
        settings_dir = tmp_path / "settings"
        settings_dir.mkdir(parents=True)

        manager = KeybindingManager(settings_dir=settings_dir)

        # Rebind some keys
        manager.rebind("quit", "ctrl+z", "q")
        manager.rebind("navigate_up", "w", "arrow_up")

        entries_before = manager.get_entries()
        quit_entry = next((e for e in entries_before if e.action == "quit"), None)
        assert quit_entry.key == "ctrl+z"
        assert quit_entry.default is False

        # Restore defaults
        manager.restore_defaults()

        entries_after = manager.get_entries()
        quit_entry = next((e for e in entries_after if e.action == "quit"), None)
        assert quit_entry.default is True

    def test_get_binding(self):
        """Test getting a specific keybinding."""
        manager = KeybindingManager(settings_dir=None)

        key = manager.get_binding("quit")
        assert key is not None
        assert key == "q"

        key = manager.get_binding("nonexistent")
        assert key is None

    def test_list_actions(self):
        """Test listing all actions."""
        manager = KeybindingManager(settings_dir=None)

        actions = manager.list_actions()

        assert len(actions) > 0
        assert "quit" in actions
        assert "navigate_up" in actions


class TestKeybindingPersistence:
    """Test keybinding persistence to disk."""

    def test_save_and_load_custom_bindings(self, tmp_path):
        """Test saving and loading custom bindings."""
        settings_dir = tmp_path / "settings"
        settings_dir.mkdir(parents=True)

        # Create manager and rebind
        manager1 = KeybindingManager(settings_dir=settings_dir)
        manager1.rebind("quit", "ctrl+z", "q")

        # Check file was created
        bindings_file = settings_dir / "keybindings.json"
        assert bindings_file.exists()

        # Load in new manager
        manager2 = KeybindingManager(settings_dir=settings_dir)
        entries = manager2.get_entries()

        quit_entry = next((e for e in entries if e.action == "quit"), None)
        assert quit_entry is not None
        assert quit_entry.key == "ctrl+z"

    def test_persistence_json_structure(self, tmp_path):
        """Test that JSON file has correct structure."""
        settings_dir = tmp_path / "settings"
        settings_dir.mkdir(parents=True)

        manager = KeybindingManager(settings_dir=settings_dir)
        manager.rebind("quit", "ctrl+z", "q")

        bindings_file = settings_dir / "keybindings.json"
        content = bindings_file.read_text()
        data = json.loads(content)

        assert "quit" in data
        assert data["quit"] == "ctrl+z"


class TestDefaultKeybindings:
    """Test default keybindings."""

    def test_default_keybindings_exist(self):
        """Test that default keybindings are defined."""
        assert len(DEFAULT_KEYBINDINGS) > 0

        actions = [kb.action for kb in DEFAULT_KEYBINDINGS]
        assert "quit" in actions
        assert "navigate_up" in actions
        assert "navigate_down" in actions
        assert "navigate_left" in actions
        assert "navigate_right" in actions
        assert "open_command" in actions
        assert "confirm" in actions
        assert "cancel" in actions

    def test_default_keybindings_have_descriptions(self):
        """Test that all default keybindings have descriptions."""
        for kb in DEFAULT_KEYBINDINGS:
            assert kb.description != ""
            assert len(kb.description) > 0

    def test_default_keybindings_have_valid_keys(self):
        """Test that all default keybindings have valid keys."""
        for kb in DEFAULT_KEYBINDINGS:
            assert kb.key != ""
            assert kb.key is not None


class TestKeybindingConflicts:
    """Test keybinding conflict dataclass."""

    def test_conflict_creation(self):
        """Test creating conflict object."""
        conflict = KeybindingConflict(
            action="new_action",
            key="ctrl+q",
            existing_action="quit",
        )

        assert conflict.action == "new_action"
        assert conflict.key == "ctrl+q"
        assert conflict.existing_action == "quit"
