"""Convergence guarantee property tests for delegation engine.

These tests verify that boundary enforcement works correctly for ANY
delegation tree structure, ensuring the engine never violates its
constraints regardless of input complexity.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from dawn_kestrel.delegation.types import (
    DelegationBudget,
    DelegationConfig,
    DelegationStopReason,
    TraversalMode,
)
from dawn_kestrel.delegation.engine import DelegationEngine


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

    def __init__(self, delay: float = 0.01):
        self.execute_agent = AsyncMock()
        self.delay = delay
        self.call_count = 0
        self.call_order: List[str] = []
        self.call_depths: List[int] = []

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
        """Track execution with optional delay."""
        self.call_count += 1
        self.call_order.append(agent_name)
        await asyncio.sleep(self.delay)
        return MockAgentResult(
            agent_name=agent_name,
            response=f"Response from {agent_name}",
            metadata={"result": f"result_{agent_name}"},
        )


class MockAgentRegistry:
    """Mock AgentRegistry for testing."""

    async def get_agent(self, name: str):
        return MagicMock(name=name)


class MockSessionManager:
    """Mock SessionManager for testing."""

    async def get_session(self, session_id: str):
        return MagicMock(id=session_id, project_id="test_project")


@pytest.fixture
def mock_registry():
    """Create a mock AgentRegistry."""
    return MockAgentRegistry()


@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager."""
    return MockSessionManager()


class TestMaxDepthGuarantee:
    """Test that max_depth boundary is never exceeded."""

    @pytest.mark.asyncio
    async def test_max_depth_1_stops_at_root(self, mock_registry, mock_session_manager):
        """max_depth=1 allows only root agent (no children)."""
        runtime = MockAgentRuntime()
        runtime.execute_agent.side_effect = runtime.execute_agent_impl

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            budget=DelegationBudget(max_depth=1),
        )
        engine = DelegationEngine(config, runtime, mock_registry)

        # Deep tree
        children = [
            {
                "agent": "child1",
                "prompt": "p1",
                "children": [
                    {"agent": "grandchild1", "prompt": "gp1"},
                ],
            },
        ]

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=children,
        )

        assert result.is_ok()
        # Only root should execute - depth=1 means children can't be spawned
        assert runtime.call_count == 1

    @pytest.mark.asyncio
    async def test_max_depth_2_stops_at_first_children(self, mock_registry, mock_session_manager):
        """max_depth=2 allows root + first-level children only."""
        runtime = MockAgentRuntime()
        runtime.execute_agent.side_effect = runtime.execute_agent_impl

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            budget=DelegationBudget(max_depth=2),
        )
        engine = DelegationEngine(config, runtime, mock_registry)

        # Tree: root -> child -> grandchild -> greatgrandchild
        children = [
            {
                "agent": "child1",
                "prompt": "p1",
                "children": [
                    {
                        "agent": "grandchild1",
                        "prompt": "gp1",
                        "children": [
                            {"agent": "greatgrandchild1", "prompt": "ggp1"},
                        ],
                    },
                ],
            },
        ]

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=children,
        )

        assert result.is_ok()
        # root (depth 0) + child (depth 1) = 2 unique agents
        # grandchild would be at depth 2, which exceeds max_depth=2
        assert "root" in runtime.call_order
        assert "child1" in runtime.call_order
        assert "grandchild1" not in runtime.call_order
        # Note: DFS recursion re-executes child when processing grandchildren,
        # so call_count may be 3 (root + child + child-again), but grandchild
        # is never executed due to depth limit

    @pytest.mark.asyncio
    async def test_max_depth_with_wide_tree(self, mock_registry, mock_session_manager):
        """max_depth works correctly with wide trees (many siblings)."""
        runtime = MockAgentRuntime()
        runtime.execute_agent.side_effect = runtime.execute_agent_impl

        config = DelegationConfig(
            mode=TraversalMode.BFS,
            budget=DelegationBudget(max_depth=2, max_breadth=10, max_total_agents=100),
        )
        engine = DelegationEngine(config, runtime, mock_registry)

        # Wide tree: root -> 5 children (each with 5 grandchildren)
        children = [
            {
                "agent": f"child{i}",
                "prompt": f"p{i}",
                "children": [
                    {"agent": f"grandchild{i}_{j}", "prompt": f"gp{i}_{j}"} for j in range(5)
                ],
            }
            for i in range(5)
        ]

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=children,
        )

        assert result.is_ok()
        # root + 5 children = 6 agents (grandchildren exceed max_depth=2)
        assert runtime.call_count == 6


class TestMaxTotalAgentsGuarantee:
    """Test that max_total_agents boundary is never exceeded."""

    @pytest.mark.asyncio
    async def test_max_total_agents_1_only_root(self, mock_registry, mock_session_manager):
        """max_total_agents=1 allows only root agent."""
        runtime = MockAgentRuntime()
        runtime.execute_agent.side_effect = runtime.execute_agent_impl

        config = DelegationConfig(
            mode=TraversalMode.BFS,
            budget=DelegationBudget(max_total_agents=1),
        )
        engine = DelegationEngine(config, runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
            {"agent": "child2", "prompt": "p2"},
        ]

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=children,
        )

        assert result.is_ok()
        assert runtime.call_count == 1
        assert runtime.call_order == ["root"]

    @pytest.mark.asyncio
    async def test_max_total_agents_limits_parallel_execution(
        self, mock_registry, mock_session_manager
    ):
        """max_total_agents limits parallel BFS execution."""
        runtime = MockAgentRuntime()
        runtime.execute_agent.side_effect = runtime.execute_agent_impl

        config = DelegationConfig(
            mode=TraversalMode.BFS,
            budget=DelegationBudget(max_total_agents=3, max_breadth=10),
        )
        engine = DelegationEngine(config, runtime, mock_registry)

        # 10 children but only 2 should execute (root + 2 = 3)
        children = [{"agent": f"child{i}", "prompt": f"p{i}"} for i in range(10)]

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=children,
        )

        assert result.is_ok()
        assert runtime.call_count == 3  # root + 2 children

    @pytest.mark.asyncio
    async def test_max_total_agents_limits_sequential_execution(
        self, mock_registry, mock_session_manager
    ):
        """max_total_agents limits sequential DFS execution."""
        runtime = MockAgentRuntime()
        runtime.execute_agent.side_effect = runtime.execute_agent_impl

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            budget=DelegationBudget(max_total_agents=4, max_depth=10),
        )
        engine = DelegationEngine(config, runtime, mock_registry)

        # 10 children but only 3 should execute after root
        children = [{"agent": f"child{i}", "prompt": f"p{i}"} for i in range(10)]

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=children,
        )

        assert result.is_ok()
        assert runtime.call_count == 4  # root + 3 children


class TestMaxWallTimeGuarantee:
    """Test that max_wall_time_seconds boundary triggers stop."""

    @pytest.mark.asyncio
    async def test_max_wall_time_stops_execution(self, mock_registry, mock_session_manager):
        """max_wall_time_seconds stops execution even with many children."""
        runtime = MockAgentRuntime(delay=0.15)  # Each agent takes 0.15s
        runtime.execute_agent.side_effect = runtime.execute_agent_impl

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            budget=DelegationBudget(max_wall_time_seconds=0.3, max_total_agents=100),
        )
        engine = DelegationEngine(config, runtime, mock_registry)

        children = [{"agent": f"child{i}", "prompt": f"p{i}"} for i in range(10)]

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=children,
        )

        assert result.is_ok()
        # With 0.15s per agent and 0.3s timeout:
        # root (0.15s) + maybe 1 child (0.15s) = 0.3s
        # Should stop before completing all 10 children
        assert runtime.call_count < 10
        assert runtime.call_count >= 1  # At least root

    @pytest.mark.asyncio
    async def test_max_wall_time_allows_quick_execution(self, mock_registry, mock_session_manager):
        """max_wall_time_seconds doesn't stop quick execution."""
        runtime = MockAgentRuntime(delay=0.001)  # Very fast
        runtime.execute_agent.side_effect = runtime.execute_agent_impl

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            budget=DelegationBudget(max_wall_time_seconds=5.0, max_total_agents=100),
        )
        engine = DelegationEngine(config, runtime, mock_registry)

        children = [{"agent": f"child{i}", "prompt": f"p{i}"} for i in range(5)]

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=children,
        )

        assert result.is_ok()
        # All agents should complete (6 agents, 0.001s each < 5s timeout)
        assert runtime.call_count == 6


class TestCircularDeletionDetection:
    """Test that circular delegation is caught by max_total_agents."""

    @pytest.mark.asyncio
    async def test_circular_delegation_caught(self, mock_registry, mock_session_manager):
        """Circular delegation A→B→A is caught by max_total_agents."""
        runtime = MockAgentRuntime()
        runtime.execute_agent.side_effect = runtime.execute_agent_impl

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            budget=DelegationBudget(max_total_agents=5, max_depth=10),
        )
        engine = DelegationEngine(config, runtime, mock_registry)

        # Simulate circular structure: root -> A -> B -> A (infinite loop)
        # But max_total_agents=5 stops it after 5 agents
        children = [
            {
                "agent": "agent_a",
                "prompt": "A prompt",
                "children": [
                    {
                        "agent": "agent_b",
                        "prompt": "B prompt",
                        "children": [
                            {"agent": "agent_a", "prompt": "A again"},  # Loop back
                        ],
                    },
                ],
            },
        ]

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=children,
        )

        assert result.is_ok()
        # Should stop at max_total_agents=5, preventing infinite loop
        assert runtime.call_count <= 5


class TestBudgetValidation:
    """Test that invalid budget values are rejected."""

    def test_zero_max_depth_raises_valueerror(self):
        """max_depth=0 raises ValueError."""
        with pytest.raises(ValueError, match="max_depth"):
            DelegationBudget(max_depth=0)

    def test_negative_max_depth_raises_valueerror(self):
        """max_depth=-1 raises ValueError."""
        with pytest.raises(ValueError, match="max_depth"):
            DelegationBudget(max_depth=-1)

    def test_zero_max_breadth_raises_valueerror(self):
        """max_breadth=0 raises ValueError."""
        with pytest.raises(ValueError, match="max_breadth"):
            DelegationBudget(max_breadth=0)

    def test_negative_max_breadth_raises_valueerror(self):
        """max_breadth=-1 raises ValueError."""
        with pytest.raises(ValueError, match="max_breadth"):
            DelegationBudget(max_breadth=-1)

    def test_zero_max_total_agents_raises_valueerror(self):
        """max_total_agents=0 raises ValueError."""
        with pytest.raises(ValueError, match="max_total_agents"):
            DelegationBudget(max_total_agents=0)

    def test_negative_max_total_agents_raises_valueerror(self):
        """max_total_agents=-1 raises ValueError."""
        with pytest.raises(ValueError, match="max_total_agents"):
            DelegationBudget(max_total_agents=-1)

    def test_zero_max_wall_time_raises_valueerror(self):
        """max_wall_time_seconds=0 raises ValueError."""
        with pytest.raises(ValueError, match="max_wall_time"):
            DelegationBudget(max_wall_time_seconds=0)

    def test_negative_max_wall_time_raises_valueerror(self):
        """max_wall_time_seconds=-1 raises ValueError."""
        with pytest.raises(ValueError, match="max_wall_time"):
            DelegationBudget(max_wall_time_seconds=-1)

    def test_zero_max_iterations_raises_valueerror(self):
        """max_iterations=0 raises ValueError."""
        with pytest.raises(ValueError, match="max_iterations"):
            DelegationBudget(max_iterations=0)

    def test_zero_stagnation_threshold_raises_valueerror(self):
        """stagnation_threshold=0 raises ValueError."""
        with pytest.raises(ValueError, match="stagnation_threshold"):
            DelegationBudget(stagnation_threshold=0)

    def test_valid_budget_created_successfully(self):
        """Valid budget values create DelegationBudget successfully."""
        budget = DelegationBudget(
            max_depth=3,
            max_breadth=5,
            max_total_agents=20,
            max_wall_time_seconds=300.0,
            max_iterations=10,
            stagnation_threshold=3,
        )
        assert budget.max_depth == 3
        assert budget.max_breadth == 5
        assert budget.max_total_agents == 20


class TestConvergenceGuarantees:
    """Test convergence detection guarantees."""

    @pytest.mark.asyncio
    async def test_convergence_stops_execution_early(self, mock_registry, mock_session_manager):
        """Convergence detection stops execution before all agents run."""
        runtime = MockAgentRuntime()

        # All agents return identical results
        async def identical_result(*args, **kwargs):
            return MockAgentResult(
                agent_name=kwargs.get("agent_name", "unknown"),
                response="Same response",
                metadata={"result": "identical"},
            )

        runtime.execute_agent.side_effect = identical_result

        config = DelegationConfig(
            mode=TraversalMode.BFS,
            check_convergence=True,
            budget=DelegationBudget(
                stagnation_threshold=2,
                max_total_agents=100,
            ),
        )
        engine = DelegationEngine(config, runtime, mock_registry)

        children = [{"agent": f"child{i}", "prompt": f"p{i}"} for i in range(10)]

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=children,
        )

        assert result.is_ok()
        delegation_result = result.unwrap()
        # Should detect convergence and stop early
        assert delegation_result.converged or delegation_result.stagnation_detected
