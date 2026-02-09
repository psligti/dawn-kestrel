"""
Tool registry with plugin-based loading.

Includes all 20 tools (6 builtin + 14 additional) loaded via entry points.
"""

from typing import Dict
import logging

from .framework import ToolRegistry, Tool
from .builtin import BashTool, ReadTool, WriteTool, GrepTool, GlobTool, ASTGrepTool
from .additional import (
    EditTool,
    ListTool,
    TaskTool,
    QuestionTool,
    TodoTool,
    TodowriteTool,
    WebFetchTool,
    WebSearchTool,
    MultiEditTool,
    CodeSearchTool,
    LspTool,
    SkillTool,
    ExternalDirectoryTool,
    CompactionTool,
)

logger = logging.getLogger(__name__)


async def get_all_tools() -> Dict[str, "Tool"]:
    """Get all available tools via plugin discovery

    Returns:
        Dictionary of tool instances keyed by tool ID
    """
    from dawn_kestrel.core.plugin_discovery import load_tools

    tool_classes = load_tools()

    tools = {}
    for tool_id, tool_class in tool_classes.items():
        # Entry points can return classes or instances
        if isinstance(tool_class, type):
            tools[tool_id] = tool_class()
        else:
            tools[tool_id] = tool_class

    logger.info(f"Loaded {len(tools)} tools from plugin discovery")

    return tools


async def get_builtin_tools() -> Dict[str, "Tool"]:
    """Get only built-in tools (bash, read, write, grep, glob, ast_grep_search)

    Returns:
        Dictionary of built-in tool instances keyed by tool ID
    """
    from .builtin import BashTool, ReadTool, WriteTool, GrepTool, GlobTool, ASTGrepTool

    builtin_tools = {
        "bash": BashTool(),
        "read": ReadTool(),
        "write": WriteTool(),
        "grep": GrepTool(),
        "glob": GlobTool(),
        "ast_grep_search": ASTGrepTool(),
    }

    return builtin_tools


def create_builtin_registry() -> ToolRegistry:
    """Create tool registry with only built-in tools (synchronous)

    Returns:
        ToolRegistry populated with built-in tools (bash, read, write, grep, glob, ast_grep_search)
    """
    from .builtin import BashTool, ReadTool, WriteTool, GrepTool, GlobTool, ASTGrepTool

    registry = ToolRegistry()
    builtin_tools = [
        ("bash", BashTool()),
        ("read", ReadTool()),
        ("write", WriteTool()),
        ("grep", GrepTool()),
        ("glob", GlobTool()),
        ("ast_grep_search", ASTGrepTool()),
    ]

    for tool_id, tool in builtin_tools:
        registry.tools[tool_id] = tool

    return registry


__all__ = [
    # Framework
    "ToolRegistry",
    "Tool",
    # Builtin tools
    "BashTool",
    "ReadTool",
    "WriteTool",
    "GrepTool",
    "GlobTool",
    "ASTGrepTool",
    # Additional tools
    "EditTool",
    "ListTool",
    "TaskTool",
    "QuestionTool",
    "TodoTool",
    "TodowriteTool",
    "WebFetchTool",
    "WebSearchTool",
    "MultiEditTool",
    "CodeSearchTool",
    "LspTool",
    "SkillTool",
    "ExternalDirectoryTool",
    "CompactionTool",
    # Factory functions
    "create_builtin_registry",
    "get_all_tools",
    "get_builtin_tools",
]
