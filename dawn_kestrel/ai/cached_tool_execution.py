"""Tool execution with caching support.

Extends the ToolExecutionManager to add LRU caching for tool results,
avoiding redundant tool calls when multiple agents request the same operation.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from dawn_kestrel.ai.tool_execution import (
    ToolExecutionManager,
    SessionLifecycleProtocol,
    ToolResult,
    ToolContext,
    create_tool_manager,
)
from dawn_kestrel.agents.tool_execution_tracker import ToolExecutionTracker
from dawn_kestrel.core.event_bus import Events, bus
from dawn_kestrel.core.models import ToolPart, ToolState
from dawn_kestrel.tools.cache import ToolResultCache
from dawn_kestrel.tools.framework import ToolRegistry

logger = logging.getLogger(__name__)


def create_cached_tool_manager(
    session_id: str,
    tool_registry: ToolRegistry | None = None,
    session_lifecycle: SessionLifecycleProtocol | None = None,
    tracker: ToolExecutionTracker | None = None,
    cache: ToolResultCache | None = None,
    cache_max_size: int = 500,
) -> ToolExecutionManager:
    """Factory function to create tool manager with caching.

    Args:
        session_id: Session identifier
        tool_registry: Tool registry (optional)
        session_lifecycle: Session lifecycle (optional)
        tracker: Tool execution tracker (optional)
        cache: Existing cache instance (optional)
        cache_max_size: Max cache size if creating new cache

    Returns:
        ToolExecutionManager with caching enabled
    """
    if cache is None:
        cache = ToolResultCache(max_size=cache_max_size)

    manager = ToolExecutionManager(
        session_id=session_id,
        tool_registry=tool_registry,
        session_lifecycle=session_lifecycle,
        tracker=tracker,
    )

    # Monkey-patch the execute_tool_call method to add caching
    original_execute = manager.execute_tool_call

    async def cached_execute_tool_call(
        tool_name: str,
        tool_input: dict[str, Any],
        tool_call_id: str,
        message_id: str,
        agent: str,
        model: str,
    ) -> ToolResult:
        """Execute tool call with caching."""

        # Check cache first
        cached = cache.get(tool_name, tool_input)
        if cached is not None:
            logger.info(f"[{session_id}] Cache HIT for tool: {tool_name}")

            # Emit cache hit event
            await bus.publish(
                Events.TOOL_CACHE_HIT,
                {
                    "session_id": session_id,
                    "tool": tool_name,
                    "cache_key": cache._make_fingerprint(tool_name, tool_input),
                    "agent": agent,
                    "timestamp": cached.cached_at,
                },
            )

            return ToolResult(
                title=cached.result_title,
                output=cached.result_output,
                metadata={**cached.result_metadata, "cache_hit": True},
                attachments=cached.result_attachments,
            )

        logger.debug(f"[{session_id}] Cache MISS for tool: {tool_name}")

        # Execute tool
        result = await original_execute(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call_id,
            message_id=message_id,
            agent=agent,
            model=model,
        )

        # Store in cache
        cache.set(tool_name, tool_input, result)
        logger.debug(f"[{session_id}] Cached result for tool: {tool_name}")

        return result

    manager.execute_tool_call = cached_execute_tool_call

    return manager
