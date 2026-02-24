"""Plugins module for Dawn Kestrel.

This module provides plugin infrastructure including:
- Tool adapters for wrapping external tools
- Entry point discovery for plugin loading
"""

from dawn_kestrel.plugins.tool_adapter import (
    ExternalToolAdapter,
    ToolAdapter,
    discover_adapters,
    get_external_adapter,
    list_external_adapters,
    register_external_adapter,
)

__all__ = [
    "ToolAdapter",
    "ExternalToolAdapter",
    "discover_adapters",
    "register_external_adapter",
    "get_external_adapter",
    "list_external_adapters",
]
