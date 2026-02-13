"""
AgentRuntime - Execute agents with tool filtering and lifecycle management.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from pathlib import Path
import time
import logging

from dawn_kestrel.core.agent_types import (
    AgentResult,
    AgentContext,
    SessionManagerLike,
)
from dawn_kestrel.core.agent_task import AgentTask
from dawn_kestrel.core.models import Session, Message, TokenUsage
from dawn_kestrel.core.event_bus import bus, Events
from dawn_kestrel.ai_session import AISession
from dawn_kestrel.tools.framework import ToolRegistry
from dawn_kestrel.tools import create_builtin_registry
from dawn_kestrel.tools.permission_filter import ToolPermissionFilter
from dawn_kestrel.context.builder import ContextBuilder
from dawn_kestrel.agents.registry import AgentRegistry
from dawn_kestrel.agents.builtin import Agent
from dawn_kestrel.core.session_lifecycle import SessionLifecycle
from dawn_kestrel.core.settings import settings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dawn_kestrel.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Execute agents with tool filtering and lifecycle management."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        base_dir: Path,
        skill_max_char_budget: Optional[int] = None,
        session_lifecycle: Optional[SessionLifecycle] = None,
        provider_registry: Optional["ProviderRegistry"] = None,
    ):
        """Initialize AgentRuntime."""
        self.agent_registry = agent_registry
        self.session_lifecycle = session_lifecycle
        self.provider_registry = provider_registry
        self.context_builder = ContextBuilder(
            base_dir=base_dir,
            skill_max_char_budget=skill_max_char_budget,
        )

    async def execute_agent(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        session_manager: SessionManagerLike,
        tools: Optional[ToolRegistry],
        skills: List[str],
        options: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        session_lifecycle: Optional[SessionLifecycle] = None,
    ) -> AgentResult:
        """Execute an agent with tool filtering and lifecycle management."""
        start_time = time.time()
        options = options or {}

        # Step 1: Fetch agent from AgentRegistry
        agent = await self.agent_registry.get_agent(agent_name)
        if not agent:
            await bus.publish(
                Events.AGENT_ERROR,
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "error": f"Agent not found: {agent_name}",
                },
            )
            raise ValueError(f"Agent not found: {agent_name}")

        # Step 2: Load session from SessionManager
        session_or_result = await session_manager.get_session(session_id)

        # Handle both Result[Session | None] and Optional[Session] return types
        # SessionManagerLike protocol says Optional[Session] but DefaultSessionService returns Result
        if hasattr(session_or_result, "is_err"):
            result = session_or_result  # type: ignore[assignment]
            if result.is_err():  # type: ignore[union-attr]
                await bus.publish(
                    Events.AGENT_ERROR,
                    {
                        "session_id": session_id,
                        "agent_name": agent_name,
                        "error": f"Session lookup failed: {result.error}",  # type: ignore[union-attr]
                    },
                )
                raise ValueError(f"Session lookup failed for {session_id}: {result.error}")  # type: ignore[union-attr]
            session = result.unwrap()  # type: ignore[union-attr]
        else:
            session = session_or_result  # type: ignore[assignment]

        if not session:
            await bus.publish(
                Events.AGENT_ERROR,
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "error": f"Session not found: {session_id}",
                },
            )
            raise ValueError(f"Session not found: {session_id}")

        assert session is not None  # for type checker

        # Validate session metadata
        if not session.project_id:
            await bus.publish(
                Events.AGENT_ERROR,
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "error": f"Session {session_id} has empty project_id",
                },
            )
            raise ValueError(f"Session {session_id} has empty project_id")

        if not session.directory:
            await bus.publish(
                Events.AGENT_ERROR,
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "error": f"Session {session_id} has empty directory",
                },
            )
            raise ValueError(f"Session {session_id} has empty directory")

        if not session.title:
            await bus.publish(
                Events.AGENT_ERROR,
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "error": f"Session {session_id} has empty title",
                },
            )
            raise ValueError(f"Session {session_id} has empty title")

        # Emit AGENT_INITIALIZED event
        event_data = {
            "session_id": session_id,
            "agent_name": agent.name,
            "agent_mode": agent.mode,
        }
        if task_id:
            event_data["task_id"] = task_id
        await bus.publish(Events.AGENT_INITIALIZED, event_data)

        # Emit session lifecycle event
        lifecycle = session_lifecycle or self.session_lifecycle
        if lifecycle:
            await lifecycle.emit_session_updated(event_data)
        logger.info(
            f"Agent {agent.name} initialized for session {session_id}"
            + (f" (task: {task_id})" if task_id else "")
        )

        try:
            # Step 3: Filter tools via ToolPermissionFilter
            permission_filter = ToolPermissionFilter(
                permissions=agent.permission,
                tool_registry=tools or ToolRegistry(),
            )
            filtered_registry = permission_filter.get_filtered_registry() or ToolRegistry()
            allowed_tool_ids = set(filtered_registry.tools.keys())

            logger.debug(
                f"Filtered tools for {agent.name}: "
                f"{len(allowed_tool_ids)} allowed from {len(tools.tools) if tools else 0} total"
            )

            # Step 4: Build context via ContextBuilder
            agent_dict = {
                "name": agent.name,
                "description": agent.description,
                "mode": agent.mode,
                "permission": agent.permission,
                "prompt": agent.prompt,
                "temperature": agent.temperature,
                "top_p": agent.top_p,
                "model": agent.model,
                "options": agent.options,
                "steps": agent.steps,
            }

            context = await self.context_builder.build_agent_context(
                session=session,
                agent=agent_dict,
                tools=filtered_registry,
                skills=skills,
            )

            # Emit AGENT_READY event
            event_data = {
                "session_id": session_id,
                "agent_name": agent.name,
                "tools_available": len(allowed_tool_ids),
            }
            if task_id:
                event_data["task_id"] = task_id
            await bus.publish(Events.AGENT_READY, event_data)
            logger.info(f"Agent {agent.name} ready for execution")

            # Step 5: Create AISession with filtered tools
            provider_id = options.get("provider", "anthropic")
            model = options.get("model", "claude-sonnet-4-20250514")

            # Determine model from agent or options
            if agent.model and isinstance(agent.model, dict):
                model = agent.model.get("model", model)

            lifecycle = session_lifecycle or self.session_lifecycle

            # Get API key from provider registry or fall back to settings
            api_key = None
            if self.provider_registry:
                provider_config = await self.provider_registry.get_provider(provider_id)
                if provider_config and provider_config.api_key:
                    api_key = provider_config.api_key
                    if provider_config.model:
                        model = provider_config.model

            ai_session = AISession(
                session=session,
                provider_id=provider_id,
                model=model,
                api_key=api_key,
                session_manager=session_manager,
                tool_registry=filtered_registry,
                session_lifecycle=lifecycle,
            )

            # Emit AGENT_EXECUTING event
            event_data = {
                "session_id": session_id,
                "agent_name": agent.name,
                "model": model,
            }
            if task_id:
                event_data["task_id"] = task_id
            await bus.publish(Events.AGENT_EXECUTING, event_data)

            # Emit session lifecycle event
            lifecycle = session_lifecycle or self.session_lifecycle
            if lifecycle:
                await lifecycle.emit_session_updated(event_data)

            logger.info(
                f"Executing agent {agent.name} for session {session_id}"
                + (f" (task: {task_id})" if task_id else "")
            )

            # Step 6: Execute agent
            execution_options: Dict[str, Any] = {
                "temperature": agent.temperature,
                "top_p": agent.top_p,
            }
            execution_options.update(options)

            response_message = await ai_session.process_message(
                user_message=user_message,
                options=execution_options,
            )

            # Extract tool usage from parts
            tools_used = []
            for part in response_message.parts:
                if hasattr(part, "tool"):
                    tools_used.append(part.tool)

            # Extract token usage from metadata
            tokens_used = None
            if response_message.metadata and "tokens" in response_message.metadata:
                tokens_data = response_message.metadata["tokens"]
                tokens_used = TokenUsage(
                    input=tokens_data.get("input", 0),
                    output=tokens_data.get("output", 0),
                    reasoning=tokens_data.get("reasoning", 0),
                    cache_read=tokens_data.get("cache_read", 0),
                    cache_write=tokens_data.get("cache_write", 0),
                )

            duration = time.time() - start_time

            # Step 7: Emit AGENT_CLEANUP event
            event_data = {
                "session_id": session_id,
                "agent_name": agent.name,
                "messages_count": 1,
                "tools_used": tools_used,
                "duration": duration,
            }
            if task_id:
                event_data["task_id"] = task_id
            await bus.publish(Events.AGENT_CLEANUP, event_data)

            logger.info(
                f"Agent {agent.name} execution complete in {duration:.2f}s, "
                f"tokens: {tokens_used.input + tokens_used.output if tokens_used else 0}, "
                f"tools: {len(tools_used)}"
            )

            # Return AgentResult with task_id
            return AgentResult(
                agent_name=agent.name,
                response=response_message.text or "",
                parts=response_message.parts or [],
                metadata=response_message.metadata or {},
                tools_used=tools_used,
                tokens_used=tokens_used,
                duration=duration,
                error=None,
                task_id=task_id,
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)

            logger.error(f"Agent execution failed: {error_msg}")

            # Emit AGENT_ERROR event
            event_data = {
                "session_id": session_id,
                "agent_name": agent.name,
                "error": error_msg,
                "duration": duration,
            }
            if task_id:
                event_data["task_id"] = task_id
            await bus.publish(Events.AGENT_ERROR, event_data)

            # Return AgentResult with error and task_id
            return AgentResult(
                agent_name=agent.name,
                response=f"Error: {error_msg}",
                parts=[],
                metadata={"error": error_msg},
                tools_used=[],
                tokens_used=None,
                duration=duration,
                error=error_msg,
                task_id=task_id,
            )


def create_agent_runtime(
    agent_registry: AgentRegistry,
    base_dir: Path,
    skill_max_char_budget: Optional[int] = None,
    session_lifecycle: Optional[SessionLifecycle] = None,
    provider_registry: Optional["ProviderRegistry"] = None,
) -> AgentRuntime:
    """Factory function to create AgentRuntime."""
    return AgentRuntime(
        agent_registry=agent_registry,
        base_dir=base_dir,
        skill_max_char_budget=skill_max_char_budget,
        session_lifecycle=session_lifecycle,
        provider_registry=provider_registry,
    )
