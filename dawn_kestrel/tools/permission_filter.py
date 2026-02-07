"""Tool permission filter for filtering tools based on agent permissions."""
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass

from .framework import ToolRegistry, Tool


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
    """

    def __init__(
        self,
        permissions: Optional[List[Dict[str, Any]]] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        """Initialize the filter.

        Args:
            permissions: Agent permission rules (list of dicts with permission, pattern, action)
            tool_registry: ToolRegistry to filter
        """
        self._rules: List[PermissionRule] = []
        self._tool_registry: Optional[ToolRegistry] = tool_registry

        if permissions:
            self._parse_permissions(permissions)

    def _parse_permissions(self, permissions: List[Dict[str, Any]]) -> None:
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

            self._rules.append(PermissionRule(
                permission=permission,
                pattern=pattern,
                action=action
            ))

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

    def _evaluate_permission(self, tool_id: str) -> Optional[str]:
        """Evaluate permission for a tool ID.

        Rules are evaluated in order, with the last matching rule winning.

        Args:
            tool_id: Tool ID to check

        Returns:
            "allow", "deny", or None if no match found
        """
        last_action: Optional[str] = None

        for rule in self._rules:
            if self._matches_pattern(tool_id, rule.permission):
                last_action = rule.action

        return last_action

    def get_filtered_tool_ids(self, tool_ids: Optional[Set[str]] = None) -> Set[str]:
        """Get filtered tool IDs based on permissions.

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

        allowed_tools: Set[str] = set()

        for tool_id in tool_ids:
            action = self._evaluate_permission(tool_id)

            # If no rules match, default to deny
            if action is None:
                continue

            if action == "allow":
                allowed_tools.add(tool_id)

        return allowed_tools

    def get_filtered_registry(self) -> Optional[ToolRegistry]:
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

        Args:
            tool_id: Tool ID to check

        Returns:
            True if tool is allowed, False otherwise
        """
        action = self._evaluate_permission(tool_id)

        # Default to deny if no rules match
        if action is None:
            return False

        return action == "allow"
