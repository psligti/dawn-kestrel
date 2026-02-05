"""Pytest configuration for TUI tests"""
import pytest

from opencode_python.tui.app import OpenCodeTUI


@pytest.fixture
def app() -> OpenCodeTUI:
    """
    Fixture to provide a Textual app instance for testing.
    The test should handle running the app in a testing context.
    """
    return OpenCodeTUI()
