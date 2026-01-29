"""
Complete tool registry with all built-in and additional tools.

Includes all 22 tools: 5 original + 17 additional.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, cast

from opencode_python.tools.framework import ToolRegistry as TR, Tool
from opencode_python.tools.builtin import (
    BashTool,
    ReadTool,
    WriteTool,
    GrepTool,
    GlobTool
)
from opencode_python.tools.additional import (
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
    PlanEnterTool,
    PlanExitTool,
    BatchTool,
    CompactionTool
)


logger = logging.getLogger(__name__)


async def create_builtin_registry() -> TR:
    """Create tool registry with all built-in tools"""
    registry = TR()

    original_tools = [
        {"id": "bash", "tool": BashTool()},
        {"id": "read", "tool": ReadTool()},
        {"id": "write", "tool": WriteTool()},
        {"id": "grep", "tool": GrepTool()},
        {"id": "glob", "tool": GlobTool()},
    ]

    additional_tools = [
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
        {"id": "plan_enter", "tool": PlanEnterTool()},
        {"id": "plan_exit", "tool": PlanExitTool()},
        {"id": "batch", "tool": BatchTool()},
        {"id": "compact", "tool": CompactionTool()},
    ]

    for tool_info in original_tools:
        tool = cast(Tool, tool_info["tool"])
        tool_id = cast(str, tool_info["id"])
        await registry.register(tool, tool_id)

    for tool_info in additional_tools:
        tool = cast(Tool, tool_info["tool"])
        tool_id = cast(str, tool_info["id"])
        await registry.register(tool, tool_id)

    logger.info(f"Registered {len(original_tools) + len(additional_tools)} built-in tools")

    return registry


async def get_all_tools() -> Dict[str, Any]:
    """Get all available tools"""
    registry = await create_builtin_registry()
    return await registry.get_all()
