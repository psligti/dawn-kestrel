"""OpenCode Python - Permission model"""
from __future__ import annotations
from typing import Literal, List
from dataclasses import dataclass


@dataclass
class PermissionRule:
    """Single permission rule"""
    permission: str
    pattern: str  # Glob pattern
    action: Literal["allow", "deny", "ask"]


def matches_pattern(needle: str, pattern: str) -> bool:
    """Check if needle matches a glob pattern"""
    # Simple glob matching - handles * and ?
    pattern_parts = pattern.split("*")
    needle_parts = needle.split("*")

    if len(pattern_parts) != len(needle_parts):
        return False

    for pattern_part, needle_part in zip(pattern_parts, needle_parts):
        if pattern_part != "*" and pattern_part != needle_part:
            return False

    return True


class PermissionEvaluator:
    """Permission evaluation system"""

    @staticmethod
    def evaluate(
        permission: str,
        pattern: str,
        rulesets: List[List[PermissionRule]],
    ) -> PermissionRule:
        """Evaluate a permission against multiple rulesets

        Args:
            permission: The permission being checked (e.g., "bash", "read")
            pattern: The pattern being matched (e.g., "*", "*.env")
            rulesets: List of rulesets to check, in priority order

        Returns:
            The matching rule with highest priority (last match wins)
        """
        # Search through all rulesets in reverse (last match wins)
        for ruleset in reversed(rulesets):
            for rule in reversed(ruleset):
                if (
                    matches_pattern(permission, rule.permission)
                    and matches_pattern(pattern, rule.pattern)
                ):
                    return rule

        # Default if no match
        return PermissionRule(permission="*", pattern="*", action="ask")


# Default permission rules
DEFAULT_RULES = [
    PermissionRule(permission="*", pattern="*", action="allow"),
    PermissionRule(permission="doom_loop", pattern="*", action="ask"),
    PermissionRule(
        permission="external_directory",
        pattern="*",
        action="ask",
    ),
    PermissionRule(permission="question", pattern="*", action="deny"),
    PermissionRule(
        permission="plan_enter",
        pattern="*",
        action="deny",
    ),
    PermissionRule(
        permission="plan_exit",
        pattern="*",
        action="deny",
    ),
]


def get_default_rulesets() -> List[List[PermissionRule]]:
    """Get all default rulesets"""
    return [DEFAULT_RULES]
