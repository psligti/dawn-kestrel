"""OpenCode Python - Agent management and lifecycle"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import asyncio
import logging

from .builtin import Agent, get_all_agents, get_agent_by_name
from opencode_python.core.event_bus import Events, bus
from opencode_python.core.models import Session


logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Track agent lifecycle state"""

    session_id: str
    agent_name: str
    status: str
    time_started: Optional[float] = None
    time_finished: Optional[float] = None
    error: Optional[str] = None
    messages_count: int = 0
    tools_used: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.tools_used is None:
            self.tools_used = []


class AgentManager:
    """Manages agent lifecycle and execution"""

    def __init__(self, session_storage=None, config=None):
        self.session_storage = session_storage
        self.config = config or {}
        self._active_sessions: Dict[str, AgentState] = {}
        self._agent_states: Dict[str, AgentState] = {}

    async def initialize_agent(
        self,
        agent: Agent,
        session: Session
    ) -> AgentState:
        """Initialize an agent for a session"""
        agent_state = AgentState(
            session_id=session.id,
            agent_name=agent.name,
            status="initializing",
            time_started=None,
            time_finished=None,
            error=None,
            messages_count=0,
            tools_used=[]
        )

        self._agent_states[session.id] = agent_state

        await bus.publish(Events.AGENT_INITIALIZED, {
            "session_id": session.id,
            "agent_name": agent.name,
            "agent_mode": agent.mode
        })

        logger.info(f"Agent {agent.name} initialized for session {session.id}")

        return agent_state

    async def set_agent_ready(self, session_id: str) -> None:
        """Mark agent as ready"""
        if session_id in self._agent_states:
            state = self._agent_states[session_id]
            state.status = "ready"
            state.time_started = state.time_started or self._now()

            await bus.publish(Events.AGENT_READY, {
                "session_id": session_id,
                "agent_name": state.agent_name
            })

    async def set_agent_executing(self, session_id: str) -> None:
        """Mark agent as executing"""
        if session_id in self._agent_states:
            state = self._agent_states[session_id]
            state.status = "executing"

            await bus.publish(Events.AGENT_EXECUTING, {
                "session_id": session_id,
                "agent_name": state.agent_name
            })

    async def set_agent_error(self, session_id: str, error: str) -> None:
        """Mark agent as having error"""
        if session_id in self._agent_states:
            state = self._agent_states[session_id]
            state.status = "error"
            state.error = error
            state.time_finished = self._now()

            await bus.publish(Events.AGENT_ERROR, {
                "session_id": session_id,
                "agent_name": state.agent_name,
                "error": error
            })

    async def cleanup_agent(self, session_id: str) -> None:
        """Cleanup agent state"""
        if session_id in self._agent_states:
            state = self._agent_states[session_id]
            state.status = "cleanup"
            state.time_finished = self._now()

            await bus.publish(Events.AGENT_CLEANUP, {
                "session_id": session_id,
                "agent_name": state.agent_name,
                "messages_count": state.messages_count,
                "tools_used": state.tools_used
            })

            del self._agent_states[session_id]

    def get_agent_state(self, session_id: str) -> Optional[AgentState]:
        """Get current agent state for session"""
        return self._agent_states.get(session_id)

    async def get_all_agents(self) -> List[Agent]:
        """Get all available agents"""
        return get_all_agents()

    async def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get an agent by name"""
        return get_agent_by_name(name)

    def get_active_sessions(self) -> List[AgentState]:
        """Get all active agent sessions"""
        return list(self._agent_states.values())

    def _now(self) -> float:
        """Get current timestamp"""
        import time
        return time.time()


def create_agent_manager(session_storage=None, config=None) -> AgentManager:
    """Factory function to create agent manager"""
    return AgentManager(session_storage=session_storage, config=config)


class AgentExecutor:
    """Agent execution engine"""

    def __init__(
        self,
        agent_manager: AgentManager,
        tool_manager,
        session_manager=None
    ):
        self.agent_manager = agent_manager
        self.tool_manager = tool_manager
        self.session_manager = session_manager
        self._active_executions: Dict[str, asyncio.Task] = {}

    async def execute_agent(
        self,
        agent_name: str,
        user_message: str,
        session_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute an agent for a user message

        Args:
            agent_name: Name of agent to execute
            user_message: User's message
            session_id: Session ID
            options: Additional execution options

        Returns:
            Dict with response and metadata
        """
        agent = await self.agent_manager.get_agent_by_name(agent_name)
        if not agent:
            raise ValueError(f"Agent {agent_name} not found")

        if not self.session_manager:
            raise ValueError(
                f"AgentExecutor requires session_manager to fetch session {session_id}. "
                "Please provide a SessionManager instance."
            )

        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(
                f"Session not found: {session_id}. "
                "Ensure the session exists and is accessible."
            )

        if not session.project_id:
            raise ValueError(f"Session {session_id} has empty project_id")
        if not session.directory:
            raise ValueError(f"Session {session_id} has empty directory")
        if not session.title:
            raise ValueError(f"Session {session_id} has empty title")

        await self.agent_manager.initialize_agent(agent, session)
        await self.agent_manager.set_agent_ready(session_id)

        logger.info(f"Executing agent {agent_name} for session {session_id}")

        result = await self._run_agent_logic(agent, user_message, session, options)

        await self.agent_manager.cleanup_agent(session_id)

        return result

    async def _run_agent_logic(
        self,
        agent,
        user_message: str,
        session: Session,
        options: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Run the core agent logic

        Filters tools based on agent permissions, handles tool execution,
        and returns response with metadata.
        """
        await self.agent_manager.set_agent_executing(session.id)

        tools = self._filter_tools_for_agent(agent)

        try:
            from opencode_python.ai_session import AISession

            ai_session = AISession(
                session=session,
                provider_id=options.get("provider", "anthropic") if options else "anthropic",
                model=options.get("model", "claude-sonnet-4-20250514") if options else "claude-sonnet-4-20250514",
                session_manager=self.session_manager
            )

            response = await ai_session.process_message(
                user_message=user_message,
                options={
                    "temperature": agent.temperature,
                    "top_p": agent.top_p
                }
            )

            return {
                "response": response.text or "",
                "parts": response.parts or [],
                "agent": agent.name,
                "status": "completed",
                "metadata": response.metadata or {}
            }

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            await self.agent_manager.set_agent_error(session.id, str(e))

            return {
                "response": f"Error: {str(e)}",
                "parts": [],
                "agent": agent.name,
                "status": "error",
                "metadata": {"error": str(e)}
            }

    def _filter_tools_for_agent(self, agent) -> List[str]:
        """Filter available tools based on agent permissions

        Args:
            agent: Agent with permission rules

        Returns:
            List of tool names allowed for this agent
        """
        if not self.tool_manager:
            return []

        all_tools = self.tool_manager.tool_registry.tools.keys()

        allowed_tools = []
        for tool_name in all_tools:
            if self._is_tool_allowed(tool_name, agent.permission):
                allowed_tools.append(tool_name)

        return allowed_tools

    def _is_tool_allowed(self, tool_name: str, permissions: List[Dict[str, Any]]) -> bool:
        """Check if a tool is allowed by agent permissions

        Args:
            tool_name: Name of the tool
            permissions: Agent permission rules

        Returns:
            True if tool is allowed, False otherwise
        """
        import fnmatch
        from opencode_python.tools.framework import ToolContext, Tool

        tool = self.tool_manager.tool_registry.get(tool_name)
        if not tool:
            return False

        for rule in permissions:
            permission_type = rule.get("permission", "")
            pattern = rule.get("pattern", "")
            action = rule.get("action", "")

            if action == "deny":
                if fnmatch.fnmatch(tool_name, pattern):
                    return False
            elif action == "allow":
                if fnmatch.fnmatch(tool_name, pattern):
                    return True

        return True

    async def cancel_execution(self, session_id: str) -> bool:
        """Cancel active agent execution for session

        Args:
            session_id: Session ID to cancel

        Returns:
            True if cancelled, False otherwise
        """
        if session_id in self._active_executions:
            task = self._active_executions[session_id]
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled agent execution for session {session_id}")
                return True

        return False
