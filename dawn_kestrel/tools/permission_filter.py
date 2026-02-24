"""Tool permission filter for filtering tools based on agent permissions."""

from dataclasses import dataclass
from typing import Any

from .framework import ToolRegistry


@dataclass
class PermissionRule:
    """Single permission rule from agent configuration."""

    permission: str  # Tool ID or wildcard (e.g., "bash", "read", "*")
    pattern: str  # Reserved for future sub-scoping (e.g., file paths)
    action: str  # "allow" or "deny"


class ToolPermissionFilter:
    """Filter tools based on agent permission rules.

    Rules are evaluated in order, with the last matching rule winning.
    This matches the TypeScript OpenCode behavior.

    Supports explicit allowlists and denylists:
    - allowed_tools: List of glob patterns for tools that are allowed
    - denied_tools: List of glob patterns for tools that are denied
    - Deny takes precedence over allow (if a tool matches both, it's denied)
    """

    def __init__(
        self,
        permissions: list[dict[str, Any]] | None = None,
        tool_registry: ToolRegistry | None = None,
        allowed_tools: list[str] | None = None,
        denied_tools: list[str] | None = None,
    ) -> None:
        """Initialize the filter.

        Args:
            permissions: Agent permission rules (list of dicts with permission, pattern, action)
            tool_registry: ToolRegistry to filter
            allowed_tools: List of glob patterns for explicitly allowed tools
            denied_tools: List of glob patterns for explicitly denied tools
        """
        self._rules: list[PermissionRule] = []
        self._tool_registry: ToolRegistry | None = tool_registry
        self._allowed_tools: list[str] | None = allowed_tools
        self._denied_tools: list[str] | None = denied_tools

        if permissions:
            self._parse_permissions(permissions)

    def _parse_permissions(self, permissions: list[dict[str, Any]]) -> None:
        """Parse permission rules from agent configuration.

        Args:
            permissions: List of permission rule dictionaries
        """
        for rule_dict in permissions:
            if not isinstance(rule_dict, dict):
                continue

            permission = rule_dict.get("permission", "")
            pattern = rule_dict.get("pattern", "")
            action = rule_dict.get("action", "")

            if not permission or not action:
                continue

            self._rules.append(
                PermissionRule(permission=permission, pattern=pattern, action=action)
            )

    def _matches_pattern(self, needle: str, pattern: str) -> bool:
        """Check if needle matches a glob pattern.

        Args:
            needle: String to match (e.g., tool ID)
            pattern: Glob pattern (e.g., "*", "bash", "read*")

        Returns:
            True if needle matches pattern
        """
        # Handle wildcard
        if pattern == "*":
            return True

        # Handle exact match
        if needle == pattern:
            return True

        # Handle prefix match (e.g., "read*" matches "read")
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return needle.startswith(prefix)

        # Handle suffix match (e.g., "*Tool" matches "BashTool")
        if pattern.startswith("*"):
            suffix = pattern[1:]
            return needle.endswith(suffix)

        return False

    def _evaluate_permission(self, tool_id: str) -> str | None:
        """Evaluate permission for a tool ID.

        Rules are evaluated in order, with the last matching rule winning.

        Args:
            tool_id: Tool ID to check

        Returns:
            "allow", "deny", or None if no match found
        """
        last_action: str | None = None

        for rule in self._rules:
            if self._matches_pattern(tool_id, rule.permission):
                last_action = rule.action

        return last_action

    def _matches_tool_list(self, tool_id: str, patterns: list[str]) -> bool:
        """Check if tool_id matches any pattern in the list.

        Args:
            tool_id: Tool ID to check
            patterns: List of glob patterns

        Returns:
            True if tool_id matches any pattern
        """
        for pattern in patterns:
            if self._matches_pattern(tool_id, pattern):
                return True
        return False

    def _is_explicitly_denied(self, tool_id: str) -> bool:
        """Check if tool is explicitly denied via denylist.

        Args:
            tool_id: Tool ID to check

        Returns:
            True if tool matches denylist patterns
        """
        if self._denied_tools is None:
            return False
        return self._matches_tool_list(tool_id, self._denied_tools)

    def _is_explicitly_allowed(self, tool_id: str) -> bool:
        """Check if tool is explicitly allowed via allowlist.

        Args:
            tool_id: Tool ID to check

        Returns:
            True if tool matches allowlist patterns
        """
        if self._allowed_tools is None:
            return False
        return self._matches_tool_list(tool_id, self._allowed_tools)

    def get_filtered_tool_ids(self, tool_ids: set[str] | None = None) -> set[str]:
        """Get filtered tool IDs based on permissions.

        Evaluation order (deny takes precedence):
        1. If tool matches denylist -> DENY
        2. If tool matches allowlist -> ALLOW
        3. If permission rules allow -> ALLOW
        4. Default -> DENY

        Args:
            tool_ids: Set of tool IDs to filter. If None, uses all tools from registry.

        Returns:
            Set of allowed tool IDs
        """
        if tool_ids is None and self._tool_registry:
            tool_ids = set(self._tool_registry.tools.keys())
        elif tool_ids is None:
            tool_ids = set()

        if not tool_ids:
            return set()

        allowed: set[str] = set()

        for tool_id in tool_ids:
            if self._is_explicitly_denied(tool_id):
                continue

            if self._is_explicitly_allowed(tool_id):
                allowed.add(tool_id)
                continue

            action = self._evaluate_permission(tool_id)
            if action == "allow":
                allowed.add(tool_id)

        return allowed

    def get_filtered_registry(self) -> ToolRegistry | None:
        """Get a new ToolRegistry with only allowed tools.

        Returns:
            New ToolRegistry with filtered tools, or None if no registry available
        """
        if self._tool_registry is None:
            return None

        allowed_ids = self.get_filtered_tool_ids()

        if not allowed_ids:
            return ToolRegistry()

        filtered_registry = ToolRegistry()

        for tool_id in allowed_ids:
            tool = self._tool_registry.get(tool_id)
            if tool:
                # Direct assignment since ToolRegistry.tools is public
                filtered_registry.tools[tool_id] = tool

                # Copy metadata if present
                metadata = self._tool_registry.get_metadata(tool_id)
                if metadata:
                    filtered_registry.tool_metadata[tool_id] = metadata

        return filtered_registry

    def is_tool_allowed(self, tool_id: str) -> bool:
        """Check if a specific tool is allowed.

        Evaluation order (deny takes precedence):
        1. If tool matches denylist -> DENY
        2. If tool matches allowlist -> ALLOW
        3. If permission rules allow -> ALLOW
        4. Default -> DENY

        Args:
            tool_id: Tool ID to check

        Returns:
            True if tool is allowed, False otherwise
        """
        if self._is_explicitly_denied(tool_id):
            return False

        if self._is_explicitly_allowed(tool_id):
            return True

        action = self._evaluate_permission(tool_id)
        return action == "allow"
