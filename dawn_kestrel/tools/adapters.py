"""ToolAdapter pattern for tool extension.

Adapter pattern normalizes tool interface, enabling custom tools
without modifying core code.

This module provides:
- ToolAdapter protocol for adapter interface
- BashToolAdapter, ReadToolAdapter, WriteToolAdapter implementations
- GenericToolAdapter for other tools
- Adapter registration system for custom tools
"""

from __future__ import annotations

import logging
import asyncio
from typing import Protocol, runtime_checkable, Optional, Dict, Any

from dawn_kestrel.core.result import Ok, Err, Result
from dawn_kestrel.tools.framework import ToolContext, ToolResult

logger = logging.getLogger(__name__)


# =============================================================================
# Adapter Registry (private module state)
# =============================================================================

_adapters: dict[str, ToolAdapter] = {}
"""Registry for custom tool adapters.

Adapters can be registered via register_adapter() and retrieved
via get_adapter() or listed via list_adapters().
"""


# =============================================================================
# ToolAdapter Protocol
# =============================================================================


@runtime_checkable
class ToolAdapter(Protocol):
    """Protocol for tool adapter.

    Adapter pattern normalizes tool interface, enabling
    custom tools without modifying core code.

    The adapter wraps a tool instance and provides a normalized
    interface for executing tools with Result types.

    Example:
        adapter = BashToolAdapter(tool)
        result = await adapter.execute(context, command="echo hello")
        if result.is_ok():
            output = result.unwrap()
    """

    async def execute(
        self,
        context: ToolContext,
        **kwargs,
    ) -> Result[dict[str, Any]]:
        """Execute tool with given context.

        Args:
            context: Tool execution context.
            **kwargs: Additional tool-specific parameters.

        Returns:
            Result[dict[str, Any]]: Tool output on success, Err on failure.
        """
        ...

    async def get_tool_name(self) -> str:
        """Get the name of the underlying tool."""
        ...


# =============================================================================
# BashToolAdapter
# =============================================================================


class BashToolAdapter:
    """Adapter for BashTool.

    Wraps BashTool to provide normalized interface with Result types.
    Converts ToolResult to dict and wraps exceptions in Err.

    Example:
        from dawn_kestrel.tools.builtin import BashTool
        tool = BashTool()
        adapter = BashToolAdapter(tool)
        result = await adapter.execute(context, command="echo hello")
    """

    def __init__(self, tool):
        """Initialize Bash adapter.

        Args:
            tool: BashTool instance or compatible tool.
        """
        self._tool = tool

    async def execute(
        self,
        context: ToolContext,
        **kwargs,
    ) -> Result[dict[str, Any]]:
        """Execute bash tool.

        Args:
            context: Tool execution context.
            **kwargs: Tool parameters (command, description, workdir).

        Returns:
            Result[dict[str, Any]]: Tool output dict on success, Err on failure.
        """
        try:
            # Execute tool and convert ToolResult to dict
            result = await self._tool.execute(kwargs, context)
            output_dict = {
                "title": result.title,
                "output": result.output,
                "metadata": result.metadata,
            }
            if result.attachments:
                output_dict["attachments"] = result.attachments
            return Ok(output_dict)
        except Exception as e:
            logger.error(f"Bash tool error: {e}", exc_info=True)
            return Err(f"Bash tool error: {e}", code="TOOL_ERROR")

    async def get_tool_name(self) -> str:
        """Get the name of the underlying tool."""
        return "bash"


# =============================================================================
# ReadToolAdapter
# =============================================================================


class ReadToolAdapter:
    """Adapter for ReadTool.

    Wraps ReadTool to provide normalized interface with Result types.
    Converts ToolResult to dict and wraps exceptions in Err.

    Example:
        from dawn_kestrel.tools.builtin import ReadTool
        tool = ReadTool()
        adapter = ReadToolAdapter(tool)
        result = await adapter.execute(context, filePath="test.txt")
    """

    def __init__(self, tool):
        """Initialize Read adapter.

        Args:
            tool: ReadTool instance or compatible tool.
        """
        self._tool = tool

    async def execute(
        self,
        context: ToolContext,
        **kwargs,
    ) -> Result[dict[str, Any]]:
        """Execute read tool.

        Args:
            context: Tool execution context.
            **kwargs: Tool parameters (filePath, limit, offset).

        Returns:
            Result[dict[str, Any]]: Tool output dict on success, Err on failure.
        """
        try:
            # Execute tool and convert ToolResult to dict
            result = await self._tool.execute(kwargs, context)
            output_dict = {
                "title": result.title,
                "output": result.output,
                "metadata": result.metadata,
            }
            if result.attachments:
                output_dict["attachments"] = result.attachments
            return Ok(output_dict)
        except Exception as e:
            logger.error(f"Read tool error: {e}", exc_info=True)
            return Err(f"Read tool error: {e}", code="TOOL_ERROR")

    async def get_tool_name(self) -> str:
        """Get the name of the underlying tool."""
        return "read"


# =============================================================================
# WriteToolAdapter
# =============================================================================


class WriteToolAdapter:
    """Adapter for WriteTool.

    Wraps WriteTool to provide normalized interface with Result types.
    Converts ToolResult to dict and wraps exceptions in Err.

    Example:
        from dawn_kestrel.tools.builtin import WriteTool
        tool = WriteTool()
        adapter = WriteToolAdapter(tool)
        result = await adapter.execute(context, filePath="test.txt", content="Hello")
    """

    def __init__(self, tool):
        """Initialize Write adapter.

        Args:
            tool: WriteTool instance or compatible tool.
        """
        self._tool = tool

    async def execute(
        self,
        context: ToolContext,
        **kwargs,
    ) -> Result[dict[str, Any]]:
        """Execute write tool.

        Args:
            context: Tool execution context.
            **kwargs: Tool parameters (filePath, content, create).

        Returns:
            Result[dict[str, Any]]: Tool output dict on success, Err on failure.
        """
        try:
            # Execute tool and convert ToolResult to dict
            result = await self._tool.execute(kwargs, context)
            output_dict = {
                "title": result.title,
                "output": result.output,
                "metadata": result.metadata,
            }
            if result.attachments:
                output_dict["attachments"] = result.attachments
            return Ok(output_dict)
        except Exception as e:
            logger.error(f"Write tool error: {e}", exc_info=True)
            return Err(f"Write tool error: {e}", code="TOOL_ERROR")

    async def get_tool_name(self) -> str:
        """Get the name of the underlying tool."""
        return "write"


# =============================================================================
# GenericToolAdapter
# =============================================================================


class GenericToolAdapter:
    """Generic adapter for tools that don't need special wrapping.

    Wraps any tool to provide normalized interface with Result types.
    Converts ToolResult to dict and wraps exceptions in Err.

    Example:
        from dawn_kestrel.tools.additional import GrepTool
        tool = GrepTool()
        adapter = GenericToolAdapter(tool)
        result = await adapter.execute(context, pattern="test")
    """

    def __init__(self, tool):
        """Initialize generic adapter.

        Args:
            tool: Tool instance with 'name' attribute.
        """
        self._tool = tool

    async def execute(
        self,
        context: ToolContext,
        **kwargs,
    ) -> Result[dict[str, Any]]:
        """Execute tool generically.

        Args:
            context: Tool execution context.
            **kwargs: Tool-specific parameters.

        Returns:
            Result[dict[str, Any]]: Tool output dict on success, Err on failure.
        """
        try:
            # Execute tool and convert ToolResult to dict
            result = await self._tool.execute(kwargs, context)
            output_dict = {
                "title": result.title,
                "output": result.output,
                "metadata": result.metadata,
            }
            if result.attachments:
                output_dict["attachments"] = result.attachments
            return Ok(output_dict)
        except Exception as e:
            logger.error(f"Tool error: {e}", exc_info=True)
            return Err(f"Tool error: {e}", code="TOOL_ERROR")

    async def get_tool_name(self) -> str:
        """Get the name of the underlying tool."""
        # Try to get name from tool attribute
        if hasattr(self._tool, "id"):
            return self._tool.id
        if hasattr(self._tool, "name"):
            return str(self._tool.name).lower()
        return "unknown"


# =============================================================================
# Adapter Registration Functions
# =============================================================================


def register_adapter(name: str, adapter: ToolAdapter) -> None:
    """Register a custom tool adapter.

    Enables custom tools to be registered at runtime without
    modifying core code.

    Args:
        name: Adapter name/identifier.
        adapter: Adapter instance implementing ToolAdapter.

    Example:
        class CustomAdapter:
            async def execute(self, context, **kwargs):
                return Ok({"output": "success"})
            async def get_tool_name(self):
                return "custom"

        register_adapter("my-tool", CustomAdapter())
    """
    _adapters[name] = adapter
    logger.info(f"Registered tool adapter: {name}")


def get_adapter(name: str) -> Optional[ToolAdapter]:
    """Get registered adapter by name.

    Args:
        name: Adapter name/identifier.

    Returns:
        Adapter instance or None if not found.
    """
    return _adapters.get(name)


def list_adapters() -> list[str]:
    """List all registered adapter names.

    Returns:
        List of adapter names.
    """
    return list(_adapters.keys())


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "ToolAdapter",
    "BashToolAdapter",
    "ReadToolAdapter",
    "WriteToolAdapter",
    "GenericToolAdapter",
    "register_adapter",
    "get_adapter",
    "list_adapters",
]
