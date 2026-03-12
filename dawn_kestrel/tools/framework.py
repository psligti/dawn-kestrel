from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from dawn_kestrel.core.event_bus import Events, bus
from dawn_kestrel.permissions.evaluate import PermissionEvaluator, get_default_rulesets


class ToolRegistry:
    """Registry for managing available tools

    Supports tool registration, filtering, auto-discovery, and metadata management.
    """

    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}
        self.tool_metadata: dict[str, dict[str, Any]] = {}

    async def register(self, tool: "Tool", tool_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Register a tool with optional metadata"""
        self.tools[tool_id] = tool

        if metadata:
            self.tool_metadata[tool_id] = metadata

    def get(self, tool_id: str) -> Optional["Tool"]:
        """Get a tool by ID"""
        return self.tools.get(tool_id)

    async def get_all(self) -> dict[str, "Tool"]:
        """Get all registered tools"""
        return self.tools

    def get_metadata(self, tool_id: str) -> dict[str, Any] | None:
        """Get metadata for a tool"""
        return self.tool_metadata.get(tool_id)


class Tool(ABC):
    """Abstract base class for all tools

    Mimics TypeScript Tool.define() factory pattern.
    """

    id: str
    description: str = ""

    @abstractmethod
    async def execute(
        self,
        args: dict[str, Any],
        ctx: "ToolContext",
    ) -> "ToolResult":
        """Execute tool with given arguments

        Args:
            args: Validated tool arguments
            ctx: Tool execution context

        Returns:
            ToolResult with title, output, metadata, and optional attachments
        """
        pass

    def parameters(self) -> dict[str, Any]:
        """Get JSON schema for tool parameters

        Returns:
            Pydantic model schema for LLM function calling
        """
        # Subclasses should override this to return their parameter schema
        return {}

    async def init(self, ctx: "ToolContext") -> None:
        """Initialize tool with context

        Called once before execute() to set up tool state.
        Optional override for tools that need initialization.
        """
        pass


@dataclass
class ToolContext:
    """Context passed to tool execution"""
    session_id: str
    message_id: str
    agent: str
    abort: asyncio.Event
    messages: list[dict[str, Any]]
    call_id: str | None = None
    time_created: float | None = None
    time_finished: float | None = None
    base_dir: Path | None = None  # Project base directory for file operations
    time_finished: float | None = None

    async def update_metadata(self, title: str, metadata: dict[str, Any] | None = None) -> None:
        """Update tool metadata during execution

        Emits tool metadata update event
        """
        await bus.publish(Events.TOOL_STARTED, {
            "session_id": self.session_id,
            "message_id": self.message_id,
            "title": title,
            "metadata": metadata or {},
        })

    async def ask(
        self,
        permission: str,
        pattern: str,
        always: list[str] | None = None,
    ) -> bool:
        """Request permission from user

        Args:
            permission: Permission to request (e.g., "bash", "read")
            pattern: Pattern to match (e.g., "*", "/etc/*")
            always: Patterns to always approve

        Returns:
            True if permission granted, False otherwise
        """
        from dawn_kestrel.core.event_bus import Events

        # Check permission via evaluator
        rulesets = get_default_rulesets()
        rule = PermissionEvaluator.evaluate(permission, pattern, rulesets)

        if rule.action == "deny":
            await bus.publish(Events.PERMISSION_DENIED, {
                "permission": permission,
                "pattern": pattern,
            })
            return False

        if rule.action == "allow":
            await bus.publish(Events.PERMISSION_GRANTED, {
                "permission": permission,
                "pattern": pattern,
                "always": always,
            })
            return True

        # Ask permission
        await bus.publish(Events.PERMISSION_ASKED, {
            "permission": permission,
            "pattern": pattern,
            "always": always,
        })

        # In CLI mode, this would prompt user
        # In TUI mode, this would show a dialog
        # For now, return True (assume approval in non-interactive mode)
        return True



@dataclass
class ToolResult:
    """Result from tool execution"""
    title: str
    output: str
    metadata: dict[str, Any] = field(default_factory=dict)
    attachments: list[dict[str, Any]] | None = None
