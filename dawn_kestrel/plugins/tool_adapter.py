"""ToolAdapter protocol for wrapping external tools.

Provides adapters that wrap external tools (discovered via entry points)
to make them compatible with the Tool interface.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, cast, runtime_checkable

from dawn_kestrel.tools.framework import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

_external_adapters: dict[str, ToolAdapter] = {}


@runtime_checkable
class ToolAdapter(Protocol):
    """Protocol for adapters that wrap external tools.

    Adapters convert external tools to Tool instances, enabling
    integration with the tool execution framework.

    Example:
        class MyAdapter:
            async def wrap(self, external_tool):
                return WrappedTool(external_tool)
    """

    async def wrap(self, external_tool: Any) -> Tool:
        """Wrap an external tool to return a Tool instance.

        Args:
            external_tool: External tool to wrap.

        Returns:
            Tool instance compatible with the framework.
        """
        ...


class WrappedExternalTool(Tool):
    """Tool wrapper for external tools."""

    def __init__(self, external_tool: Any) -> None:
        self._external = external_tool
        self.id = getattr(external_tool, "id", "unknown_tool")
        self.description = getattr(external_tool, "description", "")

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        result = await self._external.execute(args, ctx)
        if isinstance(result, ToolResult):
            return result
        if isinstance(result, dict):
            result_dict = cast(dict[str, Any], result)
            return ToolResult(
                title=str(result_dict.get("title", "External Tool")),
                output=str(result_dict.get("output", "")),
                metadata=dict(result_dict.get("metadata", {})),
                attachments=result_dict.get("attachments"),
            )
        return ToolResult(
            title="External Tool Result",
            output=str(result),
            metadata={},
        )

    def parameters(self) -> dict[str, Any]:
        if hasattr(self._external, "parameters"):
            params = self._external.parameters()
            if isinstance(params, dict):
                return cast(dict[str, Any], params)
        return {}


class ExternalToolAdapter:
    """Adapter for wrapping external tools.

    Converts external tools (from entry points) to Tool instances.
    """

    async def wrap(self, external_tool: Any) -> Tool:
        return WrappedExternalTool(external_tool)


def register_external_adapter(name: str, adapter: ToolAdapter) -> None:
    _external_adapters[name] = adapter
    logger.info(f"Registered external tool adapter: {name}")


def get_external_adapter(name: str) -> ToolAdapter | None:
    return _external_adapters.get(name)


def list_external_adapters() -> list[str]:
    return list(_external_adapters.keys())


async def discover_adapters() -> dict[str, ToolAdapter]:
    from dawn_kestrel.core.plugin_discovery import load_tools

    tools = await load_tools()
    default_adapter = ExternalToolAdapter()

    for name in tools:
        if name not in _external_adapters:
            _external_adapters[name] = default_adapter

    logger.info(f"Discovered {len(tools)} tools for adapter wrapping")
    return _external_adapters.copy()


__all__ = [
    "ToolAdapter",
    "ExternalToolAdapter",
    "WrappedExternalTool",
    "register_external_adapter",
    "get_external_adapter",
    "list_external_adapters",
    "discover_adapters",
]
