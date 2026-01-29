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
    GlobTool
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
