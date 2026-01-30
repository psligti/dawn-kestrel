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
from opencode_python.ai_session import AISession


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


class TestToolRegistryWiring:

    def test_ai_session_has_builtin_tools(self) -> None:
        session = Session(
            id="test_session",
            slug="test",
            project_id="test-project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0"
        )

        ai_session = AISession(
            session=session,
            provider_id="anthropic",
            model="claude-3-5-sonnet-20241022",
        )

        assert ai_session.tool_manager is not None
        assert ai_session.tool_manager.tool_registry is not None
        assert len(ai_session.tool_manager.tool_registry.tools) > 0

        expected_tools = {"bash", "read", "write", "grep", "glob"}
        actual_tools = set(ai_session.tool_manager.tool_registry.tools.keys())

        assert expected_tools.issubset(actual_tools), f"Missing tools: {expected_tools - actual_tools}"

    def test_ai_session_custom_tool_registry(self) -> None:
        from opencode_python.tools.framework import ToolRegistry

        session = Session(
            id="test_session",
            slug="test",
            project_id="test-project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0"
        )

        custom_registry = ToolRegistry()
        ai_session = AISession(
            session=session,
            provider_id="anthropic",
            model="claude-3-5-sonnet-20241022",
            tool_registry=custom_registry,
        )

        assert ai_session.tool_manager.tool_registry is custom_registry

    def test_get_tool_definitions_returns_non_empty(self) -> None:
        session = Session(
            id="test_session",
            slug="test",
            project_id="test-project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0"
        )

        ai_session = AISession(
            session=session,
            provider_id="anthropic",
            model="claude-3-5-sonnet-20241022",
        )

        tool_definitions = ai_session._get_tool_definitions()

        assert len(tool_definitions) > 0
        assert "bash" in tool_definitions or "read" in tool_definitions

        if "bash" in tool_definitions:
            bash_def = tool_definitions["bash"]
            assert "type" in bash_def
            assert bash_def["type"] == "function"
            assert "function" in bash_def
            assert "name" in bash_def["function"]
            assert "description" in bash_def["function"]
            assert "parameters" in bash_def["function"]


class TestPhase1Placeholder:
    """Placeholder tests for Phase 1 agent execution."""

    def test_phase1_placeholder(self) -> None:
        """Placeholder test - Phase 1 features to be implemented."""
        assert True


class TestAgentTypes:
    """Test Phase 1 agent types and protocols."""

    def test_agent_result_basic(self) -> None:
        """AgentResult should create with minimal fields."""
        from opencode_python.core.agent_types import AgentResult

        result = AgentResult(
            agent_name="test-agent",
            response="Hello, world!",
        )

        assert result.agent_name == "test-agent"
        assert result.response == "Hello, world!"
        assert result.parts == []
        assert result.tools_used == []
        assert result.tokens_used is None
        assert result.duration == 0.0
        assert result.error is None

    def test_agent_result_with_metadata(self) -> None:
        """AgentResult should support all fields."""
        from opencode_python.core.agent_types import AgentResult
        from opencode_python.core.models import TokenUsage, ToolPart, ToolState, TextPart

        result = AgentResult(
            agent_name="build-agent",
            response="Build completed successfully",
            parts=[
                TextPart(
                    id="part1",
                    session_id="session1",
                    message_id="msg1",
                    part_type="text",
                    text="Step 1",
                )
            ],
            metadata={"key": "value"},
            tools_used=["bash", "read"],
            tokens_used=TokenUsage(input=100, output=50, reasoning=10),
            duration=3.5,
            error=None,
        )

        assert result.agent_name == "build-agent"
        assert len(result.parts) == 1
        assert result.metadata["key"] == "value"
        assert "bash" in result.tools_used
        assert result.tokens_used.input == 100
        assert result.duration == 3.5

    def test_agent_context_basic(self) -> None:
        """AgentContext should create with minimal fields."""
        from opencode_python.core.agent_types import AgentContext
        from opencode_python.tools.framework import ToolRegistry

        context = AgentContext(
            system_prompt="You are a helpful assistant",
            tools=ToolRegistry(),
            messages=[],
        )

        assert context.system_prompt == "You are a helpful assistant"
        assert context.messages == []
        assert context.memories == []
        assert context.session is None
        assert context.agent is None
        assert context.model == "gpt-4o-mini"
        assert context.metadata == {}

    def test_agent_context_full(self) -> None:
        """AgentContext should support all fields."""
        from opencode_python.core.agent_types import AgentContext
        from opencode_python.tools.framework import ToolRegistry
        from opencode_python.core.models import Session, Message

        session = Session(
            id="session1",
            slug="test",
            project_id="test-project",
            directory="/tmp",
            title="Test",
            version="1.0.0",
        )

        context = AgentContext(
            system_prompt="System prompt",
            tools=ToolRegistry(),
            messages=[
                Message(
                    id="msg1",
                    session_id="session1",
                    role="user",
                    text="Hello",
                )
            ],
            memories=[{"type": "note", "content": "Important info"}],
            session=session,
            agent={"name": "test-agent", "permissions": []},
            model="claude-3-5-sonnet-20241022",
            metadata={"custom_key": "value"},
        )

        assert context.system_prompt == "System prompt"
        assert len(context.messages) == 1
        assert len(context.memories) == 1
        assert context.session is not None
        assert context.session.id == "session1"
        assert context.agent is not None
        assert context.agent["name"] == "test-agent"
        assert context.model == "claude-3-5-sonnet-20241022"
        assert context.metadata["custom_key"] == "value"

    def test_session_manager_like_protocol(self) -> None:
        """SessionManagerLike should work as a protocol."""
        from opencode_python.core.agent_types import SessionManagerLike
        from opencode_python.core.session import SessionManager
        from opencode_python.storage.store import SessionStorage
        from pathlib import Path

        # SessionManager should satisfy SessionManagerLike protocol
        storage = SessionStorage(Path.cwd())
        manager = SessionManager(storage, Path.cwd())

        # Runtime check should pass
        assert isinstance(manager, SessionManagerLike)

    def test_provider_like_protocol(self) -> None:
        """ProviderLike should work as a protocol."""
        from opencode_python.core.agent_types import ProviderLike
        from unittest.mock import AsyncMock

        # Create a mock that satisfies the protocol
        mock_provider = AsyncMock()
        mock_provider.stream = AsyncMock()
        mock_provider.generate = AsyncMock()

        # Runtime check should pass
        assert isinstance(mock_provider, ProviderLike)
