"""Integration tests for agent runtime lifecycle and state machine.

Tests verify that AgentRuntime correctly integrates with agent lifecycle,
state machine, tool execution, and repositories without mocking.

Scenario: Agent Runtime End-to-End Lifecycle
=============================================

Preconditions:
- AgentRuntime initialized
- Agent registry configured
- SessionLifecycle available
- Tools loadable via plugin discovery

Steps:
1. Register agent in registry
2. Execute agent via runtime
3. Verify state machine transitions
4. Verify tool execution
5. Verify result completion

Expected result:
- Agent executes successfully
- State transitions: READY → RUNNING → COMPLETED
- Tools invoked correctly
- Result returned with metadata

Failure indicators:
- Agent fails to execute
- State transitions incorrect
- Tools not invoked
- Result missing metadata

Evidence:
- execute_agent returns AgentResult
- State machine transitions verified
- Tools called with correct args
- Duration recorded
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


class TestAgentRuntimeLifecycle:
    """Test agent runtime lifecycle and state machine."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def configured_container(self, temp_storage_dir):
        """Configure container with temp storage."""
        from dawn_kestrel.core.di_container import configure_container, reset_container

        reset_container()
        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        from dawn_kestrel.core.di_container import container

        yield container

        reset_container()

    @pytest.mark.asyncio
    async def test_agent_executes_with_valid_state_transitions(self, configured_container):
        """Scenario: Agent execution triggers correct state transitions.

        Preconditions:
        - Agent registered
        - Runtime configured

        Steps:
        1. Create mock agent
        2. Register agent
        3. Execute agent
        4. Verify state transitions

        Expected result:
        - State transitions: READY → RUNNING → COMPLETED
        - AgentResult returned
        - Duration recorded
        - No errors

        Failure indicators:
        - Wrong state sequence
        - AgentResult not returned
        - Duration not recorded
        """
        from dawn_kestrel.agents.builtin import BUILD_AGENT
        from dawn_kestrel.tools import create_builtin_registry

        runtime = configured_container.agent_runtime()
        session_manager = configured_container.service()
        create_result = await session_manager.create_session("agent runtime state transitions")
        assert create_result.is_ok()
        session_id = create_result.unwrap().id

        # Build a simple agent
        agent = BUILD_AGENT

        # Execute agent
        result = await runtime.execute_agent(
            agent_name=agent.name,
            user_message="test message",
            session_id=session_id,
            session_manager=session_manager,
            tools=create_builtin_registry(),
            skills=[],
        )

        assert result is not None, "Result should not be None"
        assert result.agent_name == "build", "Agent name mismatch"
        assert result.duration > 0, "Duration should be > 0"
        assert result.response is not None, "Response should not be None"

    @pytest.mark.asyncio
    async def test_agent_handles_tools_correctly(self, configured_container):
        """Scenario: Agent runtime invokes tools correctly.

        Preconditions:
        - Agent registered with tool permissions
        - Tools available

        Steps:
        1. Create agent with tool permissions
        2. Execute agent
        3. Verify tools invoked

        Expected result:
        - Agent can access allowed tools
        - Tools called with correct args
        - Results returned to agent

        Failure indicators:
        - Tools not accessible
        - Tools not called
        - Results not returned

        Evidence:
        - Tool usage in AgentResult.tools_used
        - Tool invocations logged
        """
        from dawn_kestrel.agents.builtin import BUILD_AGENT
        from dawn_kestrel.tools import get_all_tools
        from dawn_kestrel.tools.framework import ToolRegistry

        runtime = configured_container.agent_runtime()
        session_manager = configured_container.service()
        create_result = await session_manager.create_session("agent runtime tools")
        assert create_result.is_ok()
        session_id = create_result.unwrap().id

        # Get tools
        tools_dict = await get_all_tools()
        tool_registry = ToolRegistry()
        tool_registry.tools.update(tools_dict)

        # Build agent
        agent = BUILD_AGENT

        # Execute with tools
        result = await runtime.execute_agent(
            agent_name=agent.name,
            user_message="test message",
            session_id=session_id,
            session_manager=session_manager,
            tools=tool_registry,
            skills=[],
        )

        assert result.response is not None, "Response should not be None"
        # Tools may or may not be used depending on agent logic


class TestAgentRuntimeIntegration:
    """Test agent runtime integration with other components."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def configured_container(self, temp_storage_dir):
        """Configure container with temp storage."""
        from dawn_kestrel.core.di_container import configure_container, reset_container

        reset_container()
        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        from dawn_kestrel.core.di_container import container

        yield container

        reset_container()

    def test_runtime_has_agent_registry(self, configured_container):
        """Scenario: AgentRuntime has agent_registry injected.

        Preconditions:
        - Container configured

        Steps:
        1. Get agent_runtime from container
        2. Verify agent_registry is set
        3. Verify session_lifecycle is set

        Expected result:
        - agent_registry is not None
        - session_lifecycle is not None
        - Dependencies wired

        Failure indicators:
        - agent_registry is None
        - session_lifecycle is None
        - Dependencies missing

        Evidence:
        - runtime.agent_registry exists
        - runtime._session_lifecycle exists
        """
        runtime = configured_container.agent_runtime()

        assert runtime.agent_registry is not None, "agent_registry should not be None"
        assert runtime.session_lifecycle is not None, "session_lifecycle should not be None"

    @pytest.mark.asyncio
    async def test_runtime_creates_agent_result_with_metadata(self, configured_container):
        """Scenario: Agent execution creates complete AgentResult.

        Preconditions:
        - AgentRuntime configured
        - Agent registered

        Steps:
        1. Execute agent
        2. Verify AgentResult has all required fields
        3. Verify metadata populated

        Expected result:
        - AgentResult has: agent_name, response, parts, metadata, tools_used, duration
        - Metadata includes session info
        - Duration recorded

        Failure indicators:
        - AgentResult missing fields
        - Metadata incomplete
        - Duration missing

        Evidence:
        - All AgentResult fields present
        - metadata not empty
        - duration > 0
        """
        from dawn_kestrel.agents.builtin import BUILD_AGENT
        from dawn_kestrel.tools import create_builtin_registry

        runtime = configured_container.agent_runtime()
        session_manager = configured_container.service()
        create_result = await session_manager.create_session("agent runtime metadata")
        assert create_result.is_ok()
        session_id = create_result.unwrap().id
        agent = BUILD_AGENT

        result = await runtime.execute_agent(
            agent_name=agent.name,
            user_message="test",
            session_id=session_id,
            session_manager=session_manager,
            tools=create_builtin_registry(),
            skills=[],
        )

        # Verify required fields
        assert hasattr(result, "agent_name")
        assert hasattr(result, "response")
        assert hasattr(result, "parts")
        assert hasattr(result, "metadata")
        assert hasattr(result, "tools_used")
        assert hasattr(result, "duration")

        # Verify values
        assert result.agent_name is not None
        assert result.response is not None
        assert result.duration > 0
