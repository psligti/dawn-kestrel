"""
Complete tool registry with all built-in and additional tools.

Includes all 22 tools: 5 original + 17 additional.
"""

from .framework import ToolRegistry
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
    WebFetchTool,
    WebSearchTool,
    MultiEditTool,
    CodeSearchTool,
    LspTool,
    SkillTool,
    ExternalDirectoryTool,
    PlanEnterTool,
    PlanExitTool,
    ApplyPatchTool,
    BatchTool,
    CompactionTool
)
from .tools.compaction import CompactionTool


logger = logging.getLogger(__name__)


async def create_builtin_registry() -> ToolRegistry:
    """Create tool registry with all built-in tools"""
    registry = ToolRegistry()
    
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
        {"id": "todoread", "tool": TodoradTool()},
        {"id": "todowrite", "tool": TodowriteTool()},
        {"id": "webfetch", "tool": WebFetchTool()},
        {"id": "websearch", "tool": WebSearchTool()},
    ]
    
    for tool_info in original_tools:
        await registry.register(tool_info["tool"], tool_info["id"])
    
    for tool_info in additional_tools:
        await registry.register(tool_info["tool"], tool_info["id"])
    
    logger.info(f"Registered {len(original_tools) + len(additional_tools)} built-in tools")
    
    return registry


async def get_all_tools() -> Dict[str, Any]:
    """Get all available tools"""
    registry = await create_builtin_registry()
    return await registry.get_all()
