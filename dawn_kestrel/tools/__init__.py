"""
Complete tool registry with compaction tool.

Includes all 23 tools (5 builtin + 18 additional) with session compaction.
"""

from typing import Dict, Type, cast
import logging

from .framework import ToolRegistry, Tool
from .builtin import (
    BashTool,
    ReadTool,
    WriteTool,
    GrepTool,
    GlobTool,
    ASTGrepTool
)
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


async def create_complete_registry() -> ToolRegistry:
    """Create tool registry with all 23 tools"""
    registry = ToolRegistry()

    builtin_tools = [
        {"id": "bash", "tool": BashTool()},
        {"id": "read", "tool": ReadTool()},
        {"id": "write", "tool": WriteTool()},
        {"id": "grep", "tool": GrepTool()},
        {"id": "glob", "tool": GlobTool()},
        {"id": "ast_grep_search", "tool": ASTGrepTool()},
        {"id": "edit", "tool": EditTool()},
        {"id": "list", "tool": ListTool()},
        {"id": "task", "tool": TaskTool()},
        {"id": "question", "tool": QuestionTool()},
        {"id": "todoread", "tool": TodoTool()},
        {"id": "todowrite", "tool": TodowriteTool()},
        {"id": "webfetch", "tool": WebFetchTool()},
        {"id": "websearch", "tool": WebSearchTool()},
        {"id": "multiedit", "tool": MultiEditTool()},
        {"id": "codesearch", "tool": CodeSearchTool()},
        {"id": "lsp", "tool": LspTool()},
        {"id": "skill", "tool": SkillTool()},
        {"id": "externaldirectory", "tool": ExternalDirectoryTool()},
        {"id": "compact", "tool": CompactionTool()},
    ]

    for tool_info in builtin_tools:
        tool = cast(Tool, tool_info["tool"])
        tool_id = cast(str, tool_info["id"])
        await registry.register(tool, tool_id)

    logger.info(f"Registered {len(builtin_tools)} tools (including compaction)")

    return registry


async def get_all_tools() -> Dict[str, "Tool"]:
    """Get all available tools"""
    registry = await create_complete_registry()
    return await registry.get_all()


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
    "create_complete_registry",
    "create_builtin_registry",
    "get_all_tools",
    "get_builtin_tools",
]
