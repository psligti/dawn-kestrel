"""Pytest configuration for TUI tests"""

import pytest

try:
    from dawn_kestrel.tui.app import OpenCodeTUI

    has_textual = True
except ImportError:
    has_textual = False
    OpenCodeTUI = None


@pytest.fixture
def app():
    """
    Fixture to provide a Textual app instance for testing.
    The test should handle running the app in a testing context.
    """
    if not has_textual:
        pytest.skip("textual module not available")
    return OpenCodeTUI()
