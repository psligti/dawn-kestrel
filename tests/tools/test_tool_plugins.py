"""Tests for tool plugin discovery via entry points."""

import pytest

from dawn_kestrel.core.plugin_discovery import load_tools
from dawn_kestrel.tools.framework import Tool


class TestToolPluginDiscovery:
    """Test tool discovery and loading via entry points."""

    def test_load_tools_discovers_all_tools(self):
        """Verify load_tools() discovers 20 tools from entry points."""
        tools = load_tools()

        # Should discover all 20 tools from pyproject.toml entry points
        expected_tools = {
            "bash",
            "read",
            "write",
            "grep",
            "glob",
            "ast_grep_search",
            "edit",
            "list",
            "task",
            "question",
            "todoread",
            "todowrite",
            "webfetch",
            "websearch",
            "multiedit",
            "codesearch",
            "lsp",
            "skill",
            "externaldirectory",
            "compact",
        }

        # Check we got exactly the expected tools
        assert len(tools) == len(expected_tools), (
            f"Expected {len(expected_tools)} tools, got {len(tools)}"
        )
        assert set(tools.keys()) == expected_tools, (
            f"Tool mismatch: expected {expected_tools}, got {set(tools.keys())}"
        )

        # Check that all loaded items are Tool classes or instances
        for tool_name, tool in tools.items():
            # Entry points can return classes or instances
            # Check if it's a Tool class (inherits from Tool)
            # or if it's an instance (has Tool as base class)
            try:
                # Try to check if it's a class or instance of Tool
                if isinstance(tool, type):
                    assert issubclass(tool, Tool), f"{tool_name} is not a Tool subclass"
                else:
                    assert isinstance(tool, Tool), f"{tool_name} is not a Tool instance"
            except (TypeError, AssertionError) as e:
                pytest.fail(f"Tool '{tool_name}' is not a valid Tool: {e}")

    def test_backward_compatibility_direct_imports(self):
        """Verify backward compatibility: direct tool imports still work."""
        from dawn_kestrel.tools.builtin import (
            BashTool,
            ReadTool,
            WriteTool,
            GrepTool,
            GlobTool,
            ASTGrepTool,
        )
        from dawn_kestrel.tools.additional import (
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

        # Verify all builtin tools are importable
        assert BashTool is not None
        assert ReadTool is not None
        assert WriteTool is not None
        assert GrepTool is not None
        assert GlobTool is not None
        assert ASTGrepTool is not None

        # Verify all additional tools are importable
        assert EditTool is not None
        assert ListTool is not None
        assert TaskTool is not None
        assert QuestionTool is not None
        assert TodoTool is not None
        assert TodowriteTool is not None
        assert WebFetchTool is not None
        assert WebSearchTool is not None
        assert MultiEditTool is not None
        assert CodeSearchTool is not None
        assert LspTool is not None
        assert SkillTool is not None
        assert ExternalDirectoryTool is not None
        assert CompactionTool is not None

        # Verify tools have required attributes
        for tool_class in [
            BashTool,
            ReadTool,
            WriteTool,
            EditTool,
            TaskTool,
            CompactionTool,
        ]:
            assert hasattr(tool_class, "id"), f"{tool_class.__name__} missing 'id' attribute"
            assert hasattr(tool_class, "description"), (
                f"{tool_class.__name__} missing 'description' attribute"
            )

    @pytest.mark.asyncio
    async def test_get_all_tools_uses_plugin_discovery(self):
        """Verify get_all_tools() works with plugin discovery."""
        from dawn_kestrel.tools import get_all_tools

        tools = await get_all_tools()

        # Should return all 20 tools
        assert len(tools) == 20, f"Expected 20 tools, got {len(tools)}"

        # Verify expected tool IDs
        expected_tool_ids = {
            "bash",
            "read",
            "write",
            "grep",
            "glob",
            "ast_grep_search",
            "edit",
            "list",
            "task",
            "question",
            "todoread",
            "todowrite",
            "webfetch",
            "websearch",
            "multiedit",
            "codesearch",
            "lsp",
            "skill",
            "externaldirectory",
            "compact",
        }

        assert set(tools.keys()) == expected_tool_ids, f"Tool IDs mismatch"

    def test_tool_instances_have_required_attributes(self):
        """Verify loaded tools have required attributes."""
        tools = load_tools()

        for tool_name, tool in tools.items():
            # Get actual tool instance or class
            if isinstance(tool, type):
                tool_instance = tool()
            else:
                tool_instance = tool

            # Verify required attributes
            assert hasattr(tool_instance, "id"), f"Tool '{tool_name}' missing 'id' attribute"
            assert hasattr(tool_instance, "description"), (
                f"Tool '{tool_name}' missing 'description' attribute"
            )
            assert tool_instance.id == tool_name, (
                f"Tool ID mismatch: expected '{tool_name}', got '{tool_instance.id}'"
            )

    @pytest.mark.asyncio
    async def test_builtin_tools_subset(self):
        """Verify builtin tools are a subset of all tools."""
        from dawn_kestrel.tools import get_builtin_tools

        builtin_tools = await get_builtin_tools()

        # Should have exactly 6 builtin tools
        assert len(builtin_tools) == 6, f"Expected 6 builtin tools, got {len(builtin_tools)}"

        expected_builtins = {"bash", "read", "write", "grep", "glob", "ast_grep_search"}
        assert set(builtin_tools.keys()) == expected_builtins

    def test_load_tools_idempotent(self):
        """Verify load_tools() returns consistent results across calls."""
        tools1 = load_tools()
        tools2 = load_tools()

        # Same tool IDs
        assert set(tools1.keys()) == set(tools2.keys())

        # Same number of tools
        assert len(tools1) == len(tools2)

        # Same tool types
        for tool_id in tools1.keys():
            assert type(tools1[tool_id]) == type(tools2[tool_id]), (
                f"Tool '{tool_id}' type differs between calls"
            )
            assert tools1[tool_id].id == tools2[tool_id].id, (
                f"Tool '{tool_id}' ID differs between calls"
            )
