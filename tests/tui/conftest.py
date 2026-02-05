"""Test utilities for TUI widgets"""
from __future__ import annotations

from typing import Any


async def assert_text_visible(widget: Any, text: str, timeout: float = 1.0) -> None:
    """Wait for text to appear in a widget and verify it's visible.
    
    Args:
        widget: Textual widget to check
        text: Text content to verify is visible
        timeout: Maximum time to wait for text (seconds)
    """
    from textual.app import App
    from textual.containers import Container
    
    # Create a temporary app to await the async operation
    async def _wait_for_text():
        if timeout > 0:
            # Wait for text to be present in widget
            await widget.wait_for(f"^{text}$", timeout=timeout, strict=False)
        # Verify text is actually in the widget
        assert text in widget.plain or text in widget.rich
        return True
    
    # Create minimal app context for async operation
    from textual.app import App
    async with App().run_test() as pilot:
        await _wait_for_text()


async def assert_widget_visible(widget: Any, timeout: float = 1.0) -> None:
    """Wait for widget to be visible in the UI.
    
    Args:
        widget: Textual widget to check
        timeout: Maximum time to wait (seconds)
    """
    from textual.app import App
    from textual.containers import Container
    
    async def _wait_for_visibility():
        if timeout > 0:
            await widget.when_mounted(timeout=timeout)
        assert widget.is_visible
        return True
    
    async with App().run_test() as pilot:
        await _wait_for_visibility()


async def assert_widget_disabled(widget: Any, timeout: float = 1.0) -> None:
    """Wait for widget to be disabled.
    
    Args:
        widget: Textual widget to check
        timeout: Maximum time to wait (seconds)
    """
    from textual.app import App
    
    async def _wait_for_disabled():
        if timeout > 0:
            await widget.when_mounted(timeout=timeout)
        await widget.wait_for(lambda: not widget.can_focus, timeout=timeout)
        return True
    
    async with App().run_test() as pilot:
        await _wait_for_disabled()
