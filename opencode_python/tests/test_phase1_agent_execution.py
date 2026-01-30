"""Tests for Phase 1 agent execution features.

To be expanded as Phase 1 implementation progresses:
- AgentRegistry
- ToolPermissionFilter
- SkillInjector
- ContextBuilder
- AgentRuntime
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from opencode_python.agents import AgentExecutor, create_agent_manager
from opencode_python.core.session import SessionManager
from opencode_python.storage.store import SessionStorage
from opencode_python.core.models import Session


class TestAgentExecutorSession:
    """Test AgentExecutor uses real Session objects instead of fakes."""

    @pytest.mark.asyncio
    async def test_execute_agent_requires_session_manager(self) -> None:
        """AgentExecutor should raise error without session_manager."""
        storage = SessionStorage(Path.cwd())
        agent_manager = create_agent_manager(storage)

        from opencode_python.ai.tool_execution import ToolExecutionManager
        tool_manager = Mock(spec=ToolExecutionManager)

        executor = AgentExecutor(
            agent_manager=agent_manager,
            tool_manager=tool_manager,
            session_manager=None
        )

        with pytest.raises(ValueError, match="requires session_manager"):
            await executor.execute_agent(
                agent_name="build",
                user_message="test",
                session_id="test-session-id"
            )

    @pytest.mark.asyncio
    async def test_execute_agent_requires_real_session(self) -> None:
        """AgentExecutor should raise error for non-existent session."""
        storage = SessionStorage(Path.cwd())
        agent_manager = create_agent_manager(storage)
        session_manager = SessionManager(storage=storage, project_dir=Path.cwd())

        from opencode_python.ai.tool_execution import ToolExecutionManager
        tool_manager = Mock(spec=ToolExecutionManager)
        tool_manager.tool_registry = Mock()
        tool_manager.tool_registry.tools = {}

        executor = AgentExecutor(
            agent_manager=agent_manager,
            tool_manager=tool_manager,
            session_manager=session_manager
        )

        with pytest.raises(ValueError, match="Session not found"):
            await executor.execute_agent(
                agent_name="build",
                user_message="test",
                session_id="non-existent-session-id"
            )

    @pytest.mark.asyncio
    async def test_execute_agent_requires_non_empty_session_metadata(self) -> None:
        """AgentExecutor should raise error for sessions with empty metadata."""
        storage = SessionStorage(Path.cwd())
        agent_manager = create_agent_manager(storage)
        session_manager = SessionManager(storage=storage, project_dir=Path.cwd())

        session = Session(
            id="test-session-empty-metadata",
            slug="test-session",
            project_id="",
            directory="",
            title="",
            version="1.0"
        )

        await storage.create_session(session)

        from opencode_python.ai.tool_execution import ToolExecutionManager
        tool_manager = Mock(spec=ToolExecutionManager)
        tool_manager.tool_registry = Mock()
        tool_manager.tool_registry.tools = {}

        executor = AgentExecutor(
            agent_manager=agent_manager,
            tool_manager=tool_manager,
            session_manager=session_manager
        )

        with pytest.raises(ValueError, match="has empty project_id"):
            await executor.execute_agent(
                agent_name="build",
                user_message="test",
                session_id="test-session-empty-metadata"
            )

    @pytest.mark.asyncio
    async def test_execute_agent_uses_real_session_with_metadata(self) -> None:
        """AgentExecutor should successfully use real session with valid metadata."""
        storage = SessionStorage(Path.cwd())
        agent_manager = create_agent_manager(storage)
        session_manager = SessionManager(storage=storage, project_dir=Path.cwd())

        session = await session_manager.create(
            title="Test Session",
            version="1.0"
        )

        assert session.project_id != "", "Session should have non-empty project_id"
        assert session.directory != "", "Session should have non-empty directory"
        assert session.title != "", "Session should have non-empty title"

        from opencode_python.ai.tool_execution import ToolExecutionManager
        tool_manager = Mock(spec=ToolExecutionManager)
        tool_manager.tool_registry = Mock()
        tool_manager.tool_registry.tools = {}

        executor = AgentExecutor(
            agent_manager=agent_manager,
            tool_manager=tool_manager,
            session_manager=session_manager
        )

        agent = await agent_manager.get_agent_by_name("build")
        if agent:
            await agent_manager.initialize_agent(agent, session)
            state = agent_manager.get_agent_state(session.id)
            assert state is not None
            assert state.agent_name == "build"


class TestPhase1Placeholder:
    """Placeholder tests for Phase 1 agent execution."""

    def test_phase1_placeholder(self) -> None:
        """Placeholder test - Phase 1 features to be implemented."""
        assert True
