"""Tests for DelegateTool module.

Tests verify that DelegateTool provides:
- Tool interface for DelegationEngine
- Correct parameter schema
- Success/failure handling
- Factory function for dependency injection
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from dawn_kestrel.delegation.tool import DelegateTool, create_delegation_tool
from dawn_kestrel.delegation.types import (
    DelegationBudget,
    DelegationConfig,
    DelegationResult,
    DelegationStopReason,
    TraversalMode,
)
from dawn_kestrel.tools.framework import ToolContext, ToolResult


# Mock AgentResult for testing
@dataclass
class MockAgentResult:
    """Mock AgentResult for testing."""

    agent_name: str
    response: str
    parts: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tools_used: List[str] = field(default_factory=list)
    error: Optional[str] = None


class MockAgentRuntime:
    """Mock AgentRuntime for testing."""

    def __init__(self):
        self.execute_agent = AsyncMock()
        self.call_count = 0
        self.call_order: List[str] = []

    async def execute_agent_impl(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        session_manager,
        tools,
        skills,
        options=None,
        task_id=None,
        session_lifecycle=None,
    ):
        """Track execution order and return mock result."""
        self.call_count += 1
        self.call_order.append(agent_name)
        return MockAgentResult(
            agent_name=agent_name,
            response=f"Response from {agent_name}",
            metadata={"result": f"result_{agent_name}"},
        )


class MockAgentRegistry:
    """Mock AgentRegistry for testing."""

    def __init__(self):
        self.agents = {}

    async def get_agent(self, name: str):
        return self.agents.get(name)


class MockSessionManager:
    """Mock SessionManager for testing."""

    async def get_session(self, session_id: str):
        return MagicMock(id=session_id, project_id="test_project")


@pytest.fixture
def mock_runtime():
    """Create a mock AgentRuntime."""
    runtime = MockAgentRuntime()
    runtime.execute_agent.side_effect = runtime.execute_agent_impl
    return runtime


@pytest.fixture
def mock_registry():
    """Create a mock AgentRegistry."""
    return MockAgentRegistry()


@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager."""
    return MockSessionManager()


@pytest.fixture
def tool_context():
    """Create a ToolContext for testing."""
    return ToolContext(
        session_id="test_session",
        message_id="test_message",
        agent="test_agent",
        abort=MagicMock(),
        messages=[],
    )


class TestDelegateToolInit:
    """Test DelegateTool initialization."""

    def test_init_with_dependencies(self, mock_runtime, mock_registry, mock_session_manager):
        """DelegateTool can be initialized with dependencies."""
        tool = DelegateTool(
            runtime=mock_runtime,
            registry=mock_registry,
            session_manager=mock_session_manager,
        )

        assert tool._runtime == mock_runtime
        assert tool._registry == mock_registry
        assert tool._session_manager == mock_session_manager

    def test_init_without_dependencies(self):
        """DelegateTool can be initialized without dependencies."""
        tool = DelegateTool()

        assert tool._runtime is None
        assert tool._registry is None
        assert tool._session_manager is None

    def test_tool_metadata(self):
        """DelegateTool has correct metadata."""
        tool = DelegateTool()

        assert tool.id == "delegate"
        assert "subagent" in tool.description.lower()
        assert tool.category == "delegation"
        assert "agent" in tool.tags


class TestDelegateToolParameters:
    """Test DelegateTool parameter schema."""

    def test_parameters_returns_schema(self):
        """parameters() returns JSON schema."""
        tool = DelegateTool()
        schema = tool.parameters()

        assert schema["type"] == "object"
        assert "agent" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "mode" in schema["properties"]
        assert "children" in schema["properties"]
        assert "budget" in schema["properties"]

    def test_parameters_required_fields(self):
        """parameters() specifies required fields."""
        tool = DelegateTool()
        schema = tool.parameters()

        assert "agent" in schema["required"]
        assert "prompt" in schema["required"]

    def test_parameters_mode_enum(self):
        """parameters() includes mode enum values."""
        tool = DelegateTool()
        schema = tool.parameters()

        mode_prop = schema["properties"]["mode"]
        assert "breadth_first" in mode_prop["enum"]
        assert "depth_first" in mode_prop["enum"]
        assert "adaptive" in mode_prop["enum"]


class TestDelegateToolExecute:
    """Test DelegateTool execute method."""

    @pytest.mark.asyncio
    async def test_execute_returns_tool_result(
        self, mock_runtime, mock_registry, mock_session_manager, tool_context
    ):
        """execute() returns ToolResult."""
        tool = DelegateTool(
            runtime=mock_runtime,
            registry=mock_registry,
            session_manager=mock_session_manager,
        )

        args = {
            "agent": "test_agent",
            "prompt": "test prompt",
        }

        result = await tool.execute(args, tool_context)

        assert isinstance(result, ToolResult)
        assert "Delegation complete" in result.title

    @pytest.mark.asyncio
    async def test_execute_calls_engine_delegate(
        self, mock_runtime, mock_registry, mock_session_manager, tool_context
    ):
        """execute() calls DelegationEngine.delegate with correct params."""
        tool = DelegateTool(
            runtime=mock_runtime,
            registry=mock_registry,
            session_manager=mock_session_manager,
        )

        args = {
            "agent": "test_agent",
            "prompt": "test prompt",
            "mode": "depth_first",
        }

        result = await tool.execute(args, tool_context)

        assert "Delegation" in result.title
        # Engine should have executed the agent
        assert mock_runtime.call_count >= 1

    @pytest.mark.asyncio
    async def test_execute_with_children(
        self, mock_runtime, mock_registry, mock_session_manager, tool_context
    ):
        """execute() handles children parameter."""
        tool = DelegateTool(
            runtime=mock_runtime,
            registry=mock_registry,
            session_manager=mock_session_manager,
        )

        args = {
            "agent": "root_agent",
            "prompt": "root prompt",
            "children": [
                {"agent": "child1", "prompt": "child prompt 1"},
                {"agent": "child2", "prompt": "child prompt 2"},
            ],
        }

        result = await tool.execute(args, tool_context)

        # Root + 2 children = 3 agents
        assert mock_runtime.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_budget(
        self, mock_runtime, mock_registry, mock_session_manager, tool_context
    ):
        """execute() respects budget parameter."""
        tool = DelegateTool(
            runtime=mock_runtime,
            registry=mock_registry,
            session_manager=mock_session_manager,
        )

        args = {
            "agent": "root_agent",
            "prompt": "root prompt",
            "children": [
                {"agent": "child1", "prompt": "p1"},
                {"agent": "child2", "prompt": "p2"},
                {"agent": "child3", "prompt": "p3"},
            ],
            "budget": {"max_total_agents": 2},
        }

        result = await tool.execute(args, tool_context)

        # Only root + 1 child = 2 agents (max_total_agents=2)
        assert mock_runtime.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_handles_mode_bfs(
        self, mock_runtime, mock_registry, mock_session_manager, tool_context
    ):
        """execute() handles BFS mode."""
        tool = DelegateTool(
            runtime=mock_runtime,
            registry=mock_registry,
            session_manager=mock_session_manager,
        )

        args = {
            "agent": "root_agent",
            "prompt": "root prompt",
            "mode": "breadth_first",
            "children": [
                {"agent": "child1", "prompt": "p1"},
            ],
        }

        result = await tool.execute(args, tool_context)
        assert "Delegation" in result.title

    @pytest.mark.asyncio
    async def test_execute_handles_mode_dfs(
        self, mock_runtime, mock_registry, mock_session_manager, tool_context
    ):
        """execute() handles DFS mode."""
        tool = DelegateTool(
            runtime=mock_runtime,
            registry=mock_registry,
            session_manager=mock_session_manager,
        )

        args = {
            "agent": "root_agent",
            "prompt": "root prompt",
            "mode": "depth_first",
            "children": [
                {"agent": "child1", "prompt": "p1"},
            ],
        }

        result = await tool.execute(args, tool_context)
        assert "Delegation" in result.title

    @pytest.mark.asyncio
    async def test_execute_handles_mode_adaptive(
        self, mock_runtime, mock_registry, mock_session_manager, tool_context
    ):
        """execute() handles Adaptive mode."""
        tool = DelegateTool(
            runtime=mock_runtime,
            registry=mock_registry,
            session_manager=mock_session_manager,
        )

        args = {
            "agent": "root_agent",
            "prompt": "root prompt",
            "mode": "adaptive",
            "children": [
                {"agent": "child1", "prompt": "p1"},
            ],
        }

        result = await tool.execute(args, tool_context)
        assert "Delegation" in result.title

    @pytest.mark.asyncio
    async def test_execute_result_metadata(
        self, mock_runtime, mock_registry, mock_session_manager, tool_context
    ):
        """execute() returns metadata in ToolResult."""
        tool = DelegateTool(
            runtime=mock_runtime,
            registry=mock_registry,
            session_manager=mock_session_manager,
        )

        args = {
            "agent": "test_agent",
            "prompt": "test prompt",
        }

        result = await tool.execute(args, tool_context)

        assert "total_agents" in result.metadata
        assert "converged" in result.metadata
        assert "success" in result.metadata


class TestCreateDelegationTool:
    """Test factory function."""

    def test_factory_creates_tool(self, mock_runtime, mock_registry):
        """create_delegation_tool creates a DelegateTool."""
        tool = create_delegation_tool(mock_runtime, mock_registry)

        assert isinstance(tool, DelegateTool)
        assert tool._runtime == mock_runtime
        assert tool._registry == mock_registry

    def test_factory_with_session_manager(self, mock_runtime, mock_registry, mock_session_manager):
        """create_delegation_tool accepts session_manager."""
        tool = create_delegation_tool(
            mock_runtime, mock_registry, session_manager=mock_session_manager
        )

        assert tool._session_manager == mock_session_manager

    def test_factory_returns_same_type(self, mock_runtime, mock_registry):
        """create_delegation_tool returns DelegateTool instance."""
        tool = create_delegation_tool(mock_runtime, mock_registry)

        assert type(tool).__name__ == "DelegateTool"
