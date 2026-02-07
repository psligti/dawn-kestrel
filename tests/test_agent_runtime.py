"""
Integration tests for AgentRuntime.

Tests the complete agent execution pipeline:
- Agent fetching from AgentRegistry
- Session loading from SessionManager
- Tool filtering via ToolPermissionFilter
- Context building via ContextBuilder
- AISession execution with lifecycle events
- AgentResult with complete metadata
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, MagicMock, patch

from dawn_kestrel.agents.runtime import AgentRuntime, create_agent_runtime
from dawn_kestrel.agents.registry import AgentRegistry, create_agent_registry
from dawn_kestrel.agents.builtin import Agent
from dawn_kestrel.core.models import Session, Message, TokenUsage, TextPart, ToolPart, ToolState
from dawn_kestrel.core.agent_types import AgentResult
from dawn_kestrel.tools.framework import ToolRegistry, ToolContext
from dawn_kestrel.tools import create_builtin_registry
from dawn_kestrel.skills.loader import Skill, SkillLoader


@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    return Session(
        id="test-session-123",
        slug="test-session",
        project_id="test-project",
        directory="/tmp/test-project",
        title="Test Session",
        version="1.0.0",
    )


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    return Agent(
        name="build",
        description="Build agent",
        mode="build",
        permission=[
            {"permission": "*", "pattern": "*", "action": "allow"},
        ],
        native=True,
        hidden=False,
        temperature=0.7,
        top_p=0.9,
        color="blue",
        model={"model": "claude-sonnet-4-20250514"},
        prompt="You are a helpful build assistant.",
        options={},
        steps=[],
    )


@pytest.fixture
def builtin_registry():
    """Create a built-in tool registry."""
    return create_builtin_registry()


@pytest.fixture
def agent_registry(mock_agent):
    """Create an agent registry with test agent."""
    registry = create_agent_registry(persistence_enabled=False)
    return registry


@pytest.fixture
def mock_session_manager(mock_session):
    """Create a mock session manager."""
    manager = AsyncMock()
    manager.get_session = AsyncMock(return_value=mock_session)
    manager.list_messages = AsyncMock(return_value=[])
    manager.add_message = AsyncMock(return_value="msg-123")
    manager.add_part = AsyncMock(return_value="part-123")
    return manager


@pytest.fixture
def agent_runtime(agent_registry, tmp_path):
    """Create an AgentRuntime instance for testing."""
    return create_agent_runtime(
        agent_registry=agent_registry,
        base_dir=tmp_path,
        skill_max_char_budget=10000,
    )


class TestAgentRuntimeInitialization:
    """Tests for AgentRuntime initialization."""

    def test_create_agent_runtime(self, agent_registry, tmp_path):
        """Test creating AgentRuntime via factory function."""
        runtime = create_agent_runtime(
            agent_registry=agent_registry,
            base_dir=tmp_path,
            skill_max_char_budget=5000,
        )
        
        assert isinstance(runtime, AgentRuntime)
        assert runtime.agent_registry is agent_registry
        assert runtime.context_builder is not None

    def test_agent_runtime_init_directly(self, agent_registry, tmp_path):
        """Test creating AgentRuntime directly."""
        runtime = AgentRuntime(
            agent_registry=agent_registry,
            base_dir=tmp_path,
            skill_max_char_budget=None,
        )
        
        assert isinstance(runtime, AgentRuntime)
        assert runtime.agent_registry is agent_registry


class TestAgentRuntimeExecutionHappyPath:
    """Tests for happy path agent execution."""

    @pytest.mark.asyncio
    async def test_execute_agent_success(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test successful agent execution."""
        mock_ai_session = AsyncMock()
        
        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="This is a test response.",
            parts=[
                TextPart(
                    id="part-1",
                    session_id=mock_session.id,
                    message_id="response-123",
                    part_type="text",
                    text="This is a test response.",
                ),
            ],
            metadata={
                "tokens": {"input": 10, "output": 20, "reasoning": 0, "cache_read": 0, "cache_write": 0},
                "model_id": "claude-sonnet-4-20250514",
            },
        )
        
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)
        
        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Hello, build agent!",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert isinstance(result, AgentResult)
        assert result.agent_name == "build"
        assert result.response == "This is a test response."
        assert result.error is None
        assert result.duration > 0
        assert result.tokens_used is not None
        assert result.tokens_used.input == 10
        assert result.tokens_used.output == 20
        assert len(result.tools_used) == 0

    @pytest.mark.asyncio
    async def test_execute_agent_with_tool_usage(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test agent execution that uses tools."""
        mock_ai_session = AsyncMock()
        
        mock_tool_part = ToolPart(
            id="tool-part-1",
            session_id=mock_session.id,
            message_id="response-123",
            part_type="tool",
            tool="bash",
            call_id="call-123",
            state=ToolState(
                status="completed",
                input={"command": "echo hello"},
                output="hello",
            ),
        )
        
        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="I executed a command.",
            parts=[
                TextPart(
                    id="part-1",
                    session_id=mock_session.id,
                    message_id="response-123",
                    part_type="text",
                    text="I executed a command.",
                ),
                mock_tool_part,
            ],
            metadata={
                "tokens": {"input": 20, "output": 30, "reasoning": 0, "cache_read": 0, "cache_write": 0},
            },
        )
        
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)
        
        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Run echo hello",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert "bash" in result.tools_used
        assert len(result.tools_used) == 1


class TestAgentRuntimeExecutionErrorScenarios:
    """Tests for error scenarios in agent execution."""

    @pytest.mark.asyncio
    async def test_execute_agent_not_found(
        self,
        agent_runtime,
        mock_session_manager,
        builtin_registry,
    ):
        """Test execution with non-existent agent."""
        with pytest.raises(ValueError) as exc_info:
            await agent_runtime.execute_agent(
                agent_name="nonexistent",
                session_id="session-123",
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert "Agent not found: nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_agent_session_not_found(
        self,
        agent_runtime,
        mock_session_manager,
        builtin_registry,
    ):
        """Test execution with non-existent session."""
        mock_session_manager.get_session = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError) as exc_info:
            await agent_runtime.execute_agent(
                agent_name="build",
                session_id="nonexistent-session",
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert "Session not found: nonexistent-session" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_agent_invalid_session_metadata(
        self,
        agent_runtime,
        mock_session_manager,
        builtin_registry,
    ):
        """Test execution with invalid session metadata."""
        invalid_session = Session(
            id="invalid-123",
            slug="invalid",
            project_id="",  # Empty - should fail
            directory="/tmp/test",
            title="Test",
            version="1.0.0",
        )
        
        mock_session_manager.get_session = AsyncMock(return_value=invalid_session)
        
        with pytest.raises(ValueError) as exc_info:
            await agent_runtime.execute_agent(
                agent_name="build",
                session_id="invalid-123",
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert "has empty project_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_agent_exception_handling(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test exception handling during execution."""
        mock_ai_session = AsyncMock()
        mock_ai_session.process_message = AsyncMock(side_effect=Exception("AI provider error"))
        
        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert isinstance(result, AgentResult)
        assert result.error is not None
        assert "AI provider error" in result.error
        assert result.duration > 0


class TestAgentRuntimeLifecycleEvents:
    """Tests for AgentManager lifecycle event emission."""

    @pytest.mark.asyncio
    async def test_emits_agent_initialized_event(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test AGENT_INITIALIZED event emission."""
        from dawn_kestrel.core.event_bus import bus, Events
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event.name)
        
        await bus.subscribe(Events.AGENT_INITIALIZED, capture_event)
        
        mock_ai_session = AsyncMock()
        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)
        
        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert Events.AGENT_INITIALIZED in events_received
        await bus.clear_subscriptions(Events.AGENT_INITIALIZED)

    @pytest.mark.asyncio
    async def test_emits_agent_ready_event(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test AGENT_READY event emission."""
        from dawn_kestrel.core.event_bus import bus, Events
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event.name)
        
        await bus.subscribe(Events.AGENT_READY, capture_event)
        
        mock_ai_session = AsyncMock()
        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)
        
        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert Events.AGENT_READY in events_received
        await bus.clear_subscriptions(Events.AGENT_READY)

    @pytest.mark.asyncio
    async def test_emits_agent_executing_event(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test AGENT_EXECUTING event emission."""
        from dawn_kestrel.core.event_bus import bus, Events
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event.name)
        
        await bus.subscribe(Events.AGENT_EXECUTING, capture_event)
        
        mock_ai_session = AsyncMock()
        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)
        
        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert Events.AGENT_EXECUTING in events_received
        await bus.clear_subscriptions(Events.AGENT_EXECUTING)

    @pytest.mark.asyncio
    async def test_emits_agent_cleanup_event(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test AGENT_CLEANUP event emission."""
        from dawn_kestrel.core.event_bus import bus, Events
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event.name)
        
        await bus.subscribe(Events.AGENT_CLEANUP, capture_event)
        
        mock_ai_session = AsyncMock()
        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)
        
        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert Events.AGENT_CLEANUP in events_received
        await bus.clear_subscriptions(Events.AGENT_CLEANUP)

    @pytest.mark.asyncio
    async def test_emits_agent_error_event_on_failure(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test AGENT_ERROR event emission on failure."""
        from dawn_kestrel.core.event_bus import bus, Events
        
        events_received = []
        
        async def capture_event(event):
            events_received.append(event.name)
        
        await bus.subscribe(Events.AGENT_ERROR, capture_event)
        
        mock_ai_session = AsyncMock()
        mock_ai_session.process_message = AsyncMock(side_effect=Exception("Test error"))
        
        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert Events.AGENT_ERROR in events_received
        await bus.clear_subscriptions(Events.AGENT_ERROR)


class TestAgentRuntimeToolFiltering:
    """Tests for tool permission filtering."""

    @pytest.mark.asyncio
    async def test_tool_filtering_plan_agent(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test tool filtering for PLAN agent (denies edit/write)."""
        from dawn_kestrel.agents.builtin import PLAN_AGENT
        
        with patch.object(
            agent_runtime.agent_registry,
            "get_agent",
            return_value=PLAN_AGENT,
        ):
            mock_ai_session = AsyncMock()
            
            mock_response = Message(
                id="response-123",
                session_id=mock_session.id,
                role="assistant",
                text="Response",
                parts=[TextPart(
                    id="part-1",
                    session_id=mock_session.id,
                    message_id="response-123",
                    part_type="text",
                    text="Response",
                )],
                metadata={},
            )
            
            mock_ai_session.process_message = AsyncMock(return_value=mock_response)
            
            with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session) as mock_ai_class:
                await agent_runtime.execute_agent(
                    agent_name="plan",
                    session_id=mock_session.id,
                    user_message="Test",
                    session_manager=mock_session_manager,
                    tools=builtin_registry,
                    skills=[],
                    options={},
                )
                
                call_kwargs = mock_ai_class.call_args[1]
                filtered_registry = call_kwargs["tool_registry"]
                
                assert "edit" not in filtered_registry.tools
                assert "write" not in filtered_registry.tools

    @pytest.mark.asyncio
    async def test_tool_filtering_build_agent_allows_all(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test tool filtering for BUILD agent (allows all tools)."""
        mock_ai_session = AsyncMock()
        
        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Response",
            parts=[TextPart(
                id="part-1",
                session_id=mock_session.id,
                message_id="response-123",
                part_type="text",
                text="Response",
            )],
            metadata={},
        )
        
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)
        
        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session) as mock_ai_class:
            await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
            
            call_kwargs = mock_ai_class.call_args[1]
            filtered_registry = call_kwargs["tool_registry"]
            
            assert len(filtered_registry.tools) == len(builtin_registry.tools)


class TestAgentRuntimeResultFields:
    """Tests for AgentResult field completeness."""

    @pytest.mark.asyncio
    async def test_result_has_all_required_fields(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Test AgentResult contains all required fields."""
        mock_ai_session = AsyncMock()
        
        mock_response = Message(
            id="response-123",
            session_id=mock_session.id,
            role="assistant",
            text="Test response",
            parts=[
                TextPart(
                    id="part-1",
                    session_id=mock_session.id,
                    message_id="response-123",
                    part_type="text",
                    text="Test response",
                ),
                ToolPart(
                    id="tool-part-1",
                    session_id=mock_session.id,
                    message_id="response-123",
                    part_type="tool",
                    tool="bash",
                    call_id="call-123",
                    state=ToolState(
                        status="completed",
                        input={},
                        output="output",
                    ),
                ),
            ],
            metadata={
                "tokens": {
                    "input": 10,
                    "output": 20,
                    "reasoning": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                },
                "model_id": "claude-sonnet-4-20250514",
            },
        )
        
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)
        
        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="build",
                session_id=mock_session.id,
                user_message="Test",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )
        
        assert hasattr(result, "agent_name")
        assert hasattr(result, "response")
        assert hasattr(result, "parts")
        assert hasattr(result, "metadata")
        assert hasattr(result, "tools_used")
        assert hasattr(result, "tokens_used")
        assert hasattr(result, "duration")
        assert hasattr(result, "error")
        
        assert result.agent_name == "build"
        assert result.response == "Test response"
        assert len(result.parts) == 2
        assert result.tokens_used is not None
        assert result.duration > 0
        assert "bash" in result.tools_used
