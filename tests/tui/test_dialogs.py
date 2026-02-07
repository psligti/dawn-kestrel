"""Tests for dialog system using TDD approach."""

import pytest
from textual.screen import ModalScreen

from dawn_kestrel.tui.dialogs import (
    BaseDialog,
    SelectDialog,
    ConfirmDialog,
    PromptDialog,
)


class TestBaseDialog:
    """Test BaseDialog lifecycle."""

    def test_base_dialog_is_modal_screen(self):
        """BaseDialog should extend ModalScreen."""
        assert issubclass(BaseDialog, ModalScreen)


class TestSelectDialog:
    """Test SelectDialog functionality."""

    def test_select_dialog_has_options(self):
        """SelectDialog should accept options."""
        options = [
            {"value": "opt1", "title": "Option 1"},
            {"value": "opt2", "title": "Option 2"},
        ]
        dialog = SelectDialog("Select Something", options)
        assert dialog.options == options

    def test_select_dialog_initially_no_selection(self):
        """SelectDialog should not have a default selection."""
        options = [{"value": "opt1", "title": "Option 1"}]
        dialog = SelectDialog("Select Something", options)
        assert dialog.get_result() is None

    def test_select_dialog_selects_option(self):
        """SelectDialog should allow selecting an option."""
        options = [
            {"value": "opt1", "title": "Option 1"},
            {"value": "opt2", "title": "Option 2"},
        ]
        dialog = SelectDialog("Select Something", options)
        dialog.select_option("opt2")
        assert dialog.get_result() == "opt2"


class TestConfirmDialog:
    """Test ConfirmDialog functionality."""

    def test_confirm_dialog_shows_title(self):
        """ConfirmDialog should display its title."""
        dialog = ConfirmDialog("Confirm Action")
        assert dialog.title == "Confirm Action"

    def test_confirm_dialog_shows_message(self):
        """ConfirmDialog should display its message."""
        dialog = ConfirmDialog("Confirm Action", "Are you sure?")
        assert dialog.message == "Are you sure?"

    def test_confirm_dialog_has_on_confirm_callback(self):
        """ConfirmDialog should accept on_confirm callback."""
        callback_called = False

        def on_confirm():
            nonlocal callback_called
            callback_called = True

        dialog = ConfirmDialog("Confirm Action", on_confirm=on_confirm)
        assert dialog.on_confirm == on_confirm

        # Test callback is callable
        dialog.on_confirm()
        assert callback_called

    def test_confirm_dialog_has_on_cancel_callback(self):
        """ConfirmDialog should accept on_cancel callback."""
        callback_called = False

        def on_cancel():
            nonlocal callback_called
            callback_called = True

        dialog = ConfirmDialog("Confirm Action", on_cancel=on_cancel)
        assert dialog.on_cancel == on_cancel

        # Test callback is callable
        dialog.on_cancel()
        assert callback_called


class TestPromptDialog:
    """Test PromptDialog functionality."""

    def test_prompt_dialog_shows_title(self):
        """PromptDialog should display its title."""
        dialog = PromptDialog("Enter Name")
        assert dialog.title == "Enter Name"

    def test_prompt_dialog_has_on_submit_callback(self):
        """PromptDialog should accept on_submit callback."""
        callback_called = False

        def on_submit(value):
            nonlocal callback_called
            callback_called = True

        dialog = PromptDialog("Enter Name", on_submit=on_submit)
        assert dialog.on_submit == on_submit

        # Test callback is callable (without mounting)
        dialog.on_submit("test")
        assert callback_called
