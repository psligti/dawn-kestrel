"""Tests for ToolPermissionFilter allowlist/denylist functionality.

This module tests the explicit tool allowlist and denylist features:
- allowed_tools: List of tool patterns that are explicitly allowed
- denied_tools: List of tool patterns that are explicitly denied
- Deny takes precedence over allow (if in both, deny wins)
- Support glob patterns for tool names (e.g., "read*", "*_file")
"""

import pytest

from dawn_kestrel.agents.builtin import Agent
from dawn_kestrel.tools.framework import ToolRegistry
from dawn_kestrel.tools.permission_filter import ToolPermissionFilter


class TestToolAllowlist:
    """Test explicit allowlist functionality."""

    def test_allowed_tools_permits_only_matching_tools(self) -> None:
        """Verify allowed_tools only permits tools matching the patterns."""
        filter_instance = ToolPermissionFilter(allowed_tools=["read", "bash", "glob"])

        tool_ids = {"read", "bash", "glob", "write", "edit"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        assert result == {"read", "bash", "glob"}

    def test_allowed_tools_with_glob_patterns(self) -> None:
        """Verify allowed_tools supports glob patterns."""
        filter_instance = ToolPermissionFilter(allowed_tools=["read*", "*_file", "bash"])

        tool_ids = {"read", "read_file", "write_file", "bash", "edit"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        # read* matches read and read_file
        # *_file matches read_file and write_file
        # bash matches bash
        assert result == {"read", "read_file", "write_file", "bash"}

    def test_allowed_tools_empty_list_denies_all(self) -> None:
        """Verify empty allowed_tools denies all tools."""
        filter_instance = ToolPermissionFilter(allowed_tools=[])

        tool_ids = {"read", "bash", "glob"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        assert result == set()

    def test_allowed_tools_none_uses_permission_rules(self) -> None:
        """Verify None allowed_tools falls back to permission rules."""
        permissions = [
            {"permission": "read", "pattern": "*", "action": "allow"},
            {"permission": "bash", "pattern": "*", "action": "allow"},
        ]
        filter_instance = ToolPermissionFilter(permissions=permissions)

        tool_ids = {"read", "bash", "write"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        assert result == {"read", "bash"}


class TestToolDenylist:
    """Test explicit denylist functionality."""

    def test_denied_tools_removes_matching_tools(self) -> None:
        """Verify denied_tools removes tools matching the patterns."""
        filter_instance = ToolPermissionFilter(
            permissions=[
                {"permission": "*", "pattern": "*", "action": "allow"},
            ],
            denied_tools=["write", "edit"],
        )

        tool_ids = {"read", "bash", "write", "edit"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        assert result == {"read", "bash"}

    def test_denied_tools_with_glob_patterns(self) -> None:
        """Verify denied_tools supports glob patterns."""
        filter_instance = ToolPermissionFilter(
            permissions=[
                {"permission": "*", "pattern": "*", "action": "allow"},
            ],
            denied_tools=["write*", "*_file"],
        )

        tool_ids = {"read", "write", "write_file", "bash", "edit_file"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        # write* matches write and write_file
        # *_file matches write_file and edit_file
        assert result == {"read", "bash"}

    def test_denied_tools_empty_list_allows_all(self) -> None:
        """Verify empty denied_tools allows all tools (if permissions allow)."""
        filter_instance = ToolPermissionFilter(
            permissions=[
                {"permission": "*", "pattern": "*", "action": "allow"},
            ],
            denied_tools=[],
        )

        tool_ids = {"read", "bash", "glob"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        assert result == {"read", "bash", "glob"}


class TestDenyPrecedence:
    """Test that deny takes precedence over allow."""

    def test_deny_overrides_allow_when_in_both_lists(self) -> None:
        """Verify a tool in both allowed and denied is denied."""
        filter_instance = ToolPermissionFilter(
            allowed_tools=["read", "write"], denied_tools=["write"]
        )

        tool_ids = {"read", "write", "bash"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        # write is in both lists, so it's denied
        assert result == {"read"}

    def test_deny_glob_overrides_allow_exact(self) -> None:
        """Verify a deny glob pattern overrides an exact allow."""
        filter_instance = ToolPermissionFilter(allowed_tools=["read_file"], denied_tools=["read*"])

        tool_ids = {"read", "read_file"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        # read* matches both, deny wins
        assert result == set()

    def test_deny_exact_overrides_allow_glob(self) -> None:
        """Verify an exact deny overrides an allow glob."""
        filter_instance = ToolPermissionFilter(allowed_tools=["read*"], denied_tools=["read_file"])

        tool_ids = {"read", "read_file", "read_dir"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        # read* allows all, but read_file is explicitly denied
        assert result == {"read", "read_dir"}


class TestCombinedAllowDenyWithPermissions:
    """Test combined usage of allowlist, denylist, and permission rules."""

    def test_allowlist_overrides_permission_deny(self) -> None:
        """Verify allowlist takes precedence over permission-based deny."""
        permissions = [
            {"permission": "*", "pattern": "*", "action": "deny"},
            {"permission": "read", "pattern": "*", "action": "allow"},
        ]
        filter_instance = ToolPermissionFilter(permissions=permissions, allowed_tools=["bash"])

        tool_ids = {"read", "bash", "write"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        # permissions allow read, allowlist adds bash
        assert result == {"read", "bash"}

    def test_denylist_applied_after_permission_allow(self) -> None:
        """Verify denylist is applied after permission evaluation."""
        permissions = [
            {"permission": "*", "pattern": "*", "action": "allow"},
        ]
        filter_instance = ToolPermissionFilter(permissions=permissions, denied_tools=["write"])

        tool_ids = {"read", "write", "bash"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        assert result == {"read", "bash"}

    def test_full_workflow_with_all_mechanisms(self) -> None:
        """Test complete workflow with permissions, allowlist, and denylist."""
        permissions = [
            {"permission": "*", "pattern": "*", "action": "deny"},
            {"permission": "read", "pattern": "*", "action": "allow"},
            {"permission": "bash", "pattern": "*", "action": "allow"},
        ]
        filter_instance = ToolPermissionFilter(
            permissions=permissions,
            allowed_tools=["glob"],  # Add glob via allowlist
            denied_tools=["bash"],  # Remove bash via denylist
        )

        tool_ids = {"read", "bash", "glob", "write", "edit"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        # read: allowed by permissions
        # bash: allowed by permissions but denied by denylist
        # glob: allowed by allowlist
        # write, edit: denied by default (permissions)
        assert result == {"read", "glob"}


class TestIsToolAllowed:
    """Test is_tool_allowed method with allowlist/denylist."""

    def test_is_tool_allowed_with_allowlist(self) -> None:
        """Verify is_tool_allowed respects allowlist."""
        filter_instance = ToolPermissionFilter(allowed_tools=["read", "bash"])

        assert filter_instance.is_tool_allowed("read") is True
        assert filter_instance.is_tool_allowed("bash") is True
        assert filter_instance.is_tool_allowed("write") is False

    def test_is_tool_allowed_with_denylist(self) -> None:
        """Verify is_tool_allowed respects denylist."""
        filter_instance = ToolPermissionFilter(
            permissions=[
                {"permission": "*", "pattern": "*", "action": "allow"},
            ],
            denied_tools=["write"],
        )

        assert filter_instance.is_tool_allowed("read") is True
        assert filter_instance.is_tool_allowed("write") is False

    def test_is_tool_allowed_deny_precedence(self) -> None:
        """Verify is_tool_allowed respects deny precedence."""
        filter_instance = ToolPermissionFilter(
            allowed_tools=["read", "write"], denied_tools=["write"]
        )

        assert filter_instance.is_tool_allowed("read") is True
        assert filter_instance.is_tool_allowed("write") is False


class TestGlobPatternMatching:
    """Test glob pattern matching for tool names."""

    def test_prefix_glob_matches_tools(self) -> None:
        """Verify prefix glob patterns match correctly."""
        filter_instance = ToolPermissionFilter(allowed_tools=["read*"])

        tool_ids = {"read", "read_file", "read_dir", "write"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        assert result == {"read", "read_file", "read_dir"}

    def test_suffix_glob_matches_tools(self) -> None:
        """Verify suffix glob patterns match correctly."""
        filter_instance = ToolPermissionFilter(allowed_tools=["*_file"])

        tool_ids = {"read_file", "write_file", "read", "write"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        assert result == {"read_file", "write_file"}

    def test_wildcard_matches_all(self) -> None:
        """Verify * matches all tools."""
        filter_instance = ToolPermissionFilter(allowed_tools=["*"], denied_tools=["write"])

        tool_ids = {"read", "write", "bash", "glob"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        assert result == {"read", "bash", "glob"}


class TestAgentIntegration:
    """Test integration with Agent configuration."""

    def test_agent_with_allowed_tools(self) -> None:
        """Verify Agent can be created with allowed_tools."""
        agent = Agent(
            name="restricted-agent",
            description="Agent with restricted tools",
            mode="subagent",
            permission=[],
            allowed_tools=["read", "glob"],
        )

        assert agent.allowed_tools == ["read", "glob"]

    def test_agent_with_denied_tools(self) -> None:
        """Verify Agent can be created with denied_tools."""
        agent = Agent(
            name="safe-agent",
            description="Agent without dangerous tools",
            mode="subagent",
            permission=[],
            denied_tools=["write", "edit", "bash"],
        )

        assert agent.denied_tools == ["write", "edit", "bash"]

    def test_agent_allowed_tools_defaults_to_none(self) -> None:
        """Verify allowed_tools defaults to None."""
        agent = Agent(
            name="default-agent",
            description="Default agent",
            mode="subagent",
            permission=[],
        )

        assert agent.allowed_tools is None

    def test_filter_from_agent_allowed_tools(self) -> None:
        """Verify ToolPermissionFilter can use agent's allowed_tools."""
        agent = Agent(
            name="restricted-agent",
            description="Agent with restricted tools",
            mode="subagent",
            permission=[],
            allowed_tools=["read", "bash"],
        )

        filter_instance = ToolPermissionFilter(
            permissions=agent.permission,
            allowed_tools=agent.allowed_tools,
        )

        tool_ids = {"read", "bash", "write"}
        result = filter_instance.get_filtered_tool_ids(tool_ids)

        assert result == {"read", "bash"}
