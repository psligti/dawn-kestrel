"""Tests for TUI application"""
from __future__ import annotations

import pytest

from dawn_kestrel.tui.app import OpenCodeTUI


@pytest.mark.asyncio
async def test_app_can_be_instantiated():
    """Test that OpenCodeTUI app can be instantiated in test context"""
    app = OpenCodeTUI()
    assert app is not None
    assert isinstance(app, OpenCodeTUI)
