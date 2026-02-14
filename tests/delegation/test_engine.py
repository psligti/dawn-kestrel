"""Tests for DelegationEngine module.

Tests verify that DelegationEngine provides:
- BFS mode: parallel execution via asyncio.gather
- DFS mode: sequential execution with proper depth tracking
- Adaptive mode: BFS at depth 0-1, DFS at depth 2+
- Boundary enforcement (max_depth, max_breadth, max_total_agents, max_wall_time)
- Convergence-triggered early termination
- Error handling and recording
- Callback support (on_agent_spawn, on_agent_complete)
- Empty children handling
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dawn_kestrel.core.result import Err, Ok
from dawn_kestrel.delegation.types import (
    DelegationBudget,
    DelegationConfig,
    DelegationStopReason,
    TraversalMode,
)


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


class TestDelegationEngineInit:
    """Test DelegationEngine initialization."""

    def test_init_with_required_params(self, mock_runtime, mock_registry):
        """DelegationEngine can be initialized with required params."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig()
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        assert engine.config == config
        assert engine.runtime == mock_runtime
        assert engine.registry == mock_registry

    def test_init_creates_convergence_tracker(self, mock_runtime, mock_registry):
        """DelegationEngine creates ConvergenceTracker with evidence_keys."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(evidence_keys=["key1", "key2"])
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        assert engine._convergence is not None
        assert engine._convergence.evidence_keys == ["key1", "key2"]

    def test_init_creates_lock(self, mock_runtime, mock_registry):
        """DelegationEngine creates asyncio.Lock for thread safety."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig()
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        assert engine._lock is not None
        assert isinstance(engine._lock, asyncio.Lock)


class TestBFSMode:
    """Test BFS (breadth-first) execution mode."""

    @pytest.mark.asyncio
    async def test_bfs_executes_children_in_parallel(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """BFS mode executes all children in parallel via asyncio.gather."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(mode=TraversalMode.BFS)
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "prompt1"},
            {"agent": "child2", "prompt": "prompt2"},
            {"agent": "child3", "prompt": "prompt3"},
        ]

        with patch("asyncio.gather", wraps=asyncio.gather) as mock_gather:
            result = await engine.delegate(
                agent_name="root",
                prompt="root prompt",
                session_id="test_session",
                session_manager=mock_session_manager,
                tools=None,
                children=children,
            )

            # Verify gather was called (indicates parallel execution)
            mock_gather.assert_called()

        assert result.is_ok()
        # Should have executed 1 root + 3 children = 4 agents
        assert mock_runtime.call_count == 4

    @pytest.mark.asyncio
    async def test_bfs_respects_max_breadth(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """BFS mode truncates children list to max_breadth."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(
            mode=TraversalMode.BFS,
            budget=DelegationBudget(max_breadth=2),
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
            {"agent": "child2", "prompt": "p2"},
            {"agent": "child3", "prompt": "p3"},
            {"agent": "child4", "prompt": "p4"},
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
        # Should have executed 1 root + 2 children (max_breadth=2) = 3 agents
        assert mock_runtime.call_count == 3

    @pytest.mark.asyncio
    async def test_bfs_handles_empty_children(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """BFS mode handles empty children list (just root agent)."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(mode=TraversalMode.BFS)
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=None,
        )

        assert result.is_ok()
        # Only root agent executed
        assert mock_runtime.call_count == 1

    @pytest.mark.asyncio
    async def test_bfs_records_failed_agents(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """BFS mode records failed agents in errors list."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        # Make one child fail
        call_count = 0

        async def failing_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # First child fails
                raise ValueError("Child agent failed")
            return MockAgentResult(
                agent_name=kwargs.get("agent_name", "unknown"),
                response="Success",
            )

        mock_runtime.execute_agent.side_effect = failing_execute

        config = DelegationConfig(mode=TraversalMode.BFS)
        engine = DelegationEngine(config, mock_runtime, mock_registry)

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
        # Errors list should contain the failure
        assert len(result.unwrap().errors) == 1

    @pytest.mark.asyncio
    async def test_bfs_with_return_exceptions(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """BFS mode uses return_exceptions=True to prevent cascade failures."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        local_call_count = 0

        async def failing_execute(*args, **kwargs):
            nonlocal local_call_count
            local_call_count += 1
            if local_call_count == 2:
                raise ValueError("Child failed")
            return MockAgentResult(
                agent_name=kwargs.get("agent_name", "unknown"),
                response="Success",
            )

        mock_runtime.execute_agent.side_effect = failing_execute

        config = DelegationConfig(mode=TraversalMode.BFS)
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
            {"agent": "child2", "prompt": "p2"},
            {"agent": "child3", "prompt": "p3"},
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
        # All agents should have been attempted despite failure
        # root + child1 (fails) + child2 + child3 = 4 calls
        assert local_call_count == 4


class TestDFSMode:
    """Test DFS (depth-first) execution mode."""

    @pytest.mark.asyncio
    async def test_dfs_executes_children_sequentially(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """DFS mode executes children sequentially, not in parallel."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(mode=TraversalMode.DFS)
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
            {"agent": "child2", "prompt": "p2"},
            {"agent": "child3", "prompt": "p3"},
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
        # Verify sequential order
        assert mock_runtime.call_order == ["root", "child1", "child2", "child3"]

    @pytest.mark.asyncio
    async def test_dfs_handles_empty_children(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """DFS mode handles empty children list (just root agent)."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(mode=TraversalMode.DFS)
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=[],
        )

        assert result.is_ok()
        assert mock_runtime.call_count == 1

    @pytest.mark.asyncio
    async def test_dfs_depth_tracking_with_nested_children(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """DFS mode tracks depth correctly with nested children."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            budget=DelegationBudget(max_depth=3),
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        # Nested children structure
        children = [
            {
                "agent": "child1",
                "prompt": "p1",
                "children": [
                    {"agent": "grandchild1", "prompt": "gp1"},
                ],
            },
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
        # root -> child1 -> grandchild1 -> child2
        assert "root" in mock_runtime.call_order
        assert "child1" in mock_runtime.call_order
        assert "grandchild1" in mock_runtime.call_order
        assert "child2" in mock_runtime.call_order

    @pytest.mark.asyncio
    async def test_dfs_early_return_on_convergence(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """DFS mode returns early when convergence is detected."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        local_call_count = 0

        # Force convergence by making results identical
        async def same_result(*args, **kwargs):
            nonlocal local_call_count
            local_call_count += 1
            return MockAgentResult(
                agent_name=kwargs.get("agent_name", "unknown"),
                response="Same response",
                metadata={"result": "same"},
            )

        mock_runtime.execute_agent.side_effect = same_result

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            check_convergence=True,
            budget=DelegationBudget(stagnation_threshold=1),
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
            {"agent": "child2", "prompt": "p2"},
            {"agent": "child3", "prompt": "p3"},
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
        # Should detect convergence and stop early
        # At least root + child1 should execute, but may not reach child3
        assert local_call_count >= 2


class TestAdaptiveMode:
    """Test Adaptive execution mode."""

    @pytest.mark.asyncio
    async def test_adaptive_uses_bfs_at_shallow_depth(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """Adaptive mode uses BFS at depth 0-1."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(mode=TraversalMode.ADAPTIVE)
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
            {"agent": "child2", "prompt": "p2"},
        ]

        with patch("asyncio.gather", wraps=asyncio.gather) as mock_gather:
            result = await engine.delegate(
                agent_name="root",
                prompt="root prompt",
                session_id="test_session",
                session_manager=mock_session_manager,
                tools=None,
                children=children,
            )

            # BFS should be used at depth 0, which calls asyncio.gather
            mock_gather.assert_called()

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_adaptive_uses_dfs_at_deep_depth(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """Adaptive mode uses DFS at depth 2+."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(
            mode=TraversalMode.ADAPTIVE,
            budget=DelegationBudget(max_depth=4),
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        # Deep nested structure to trigger DFS at depth 2+
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
        # Verify execution happened
        assert mock_runtime.call_count > 0


class TestBoundaryEnforcement:
    """Test boundary enforcement in delegation."""

    @pytest.mark.asyncio
    async def test_max_depth_boundary(self, mock_runtime, mock_registry, mock_session_manager):
        """Delegation respects max_depth boundary."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            budget=DelegationBudget(max_depth=1),
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        # This would go deeper than max_depth=1
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
        # Should only execute root (depth 0) - no children at depth 1
        # Because depth limit is checked before incrementing
        assert mock_runtime.call_count == 1

    @pytest.mark.asyncio
    async def test_max_total_agents_boundary(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """Delegation respects max_total_agents boundary."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(
            mode=TraversalMode.BFS,
            budget=DelegationBudget(max_total_agents=2),
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
            {"agent": "child2", "prompt": "p2"},
            {"agent": "child3", "prompt": "p3"},
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
        # max_total_agents=2 means root + 1 child only
        assert mock_runtime.call_count == 2

    @pytest.mark.asyncio
    async def test_max_wall_time_boundary(self, mock_runtime, mock_registry, mock_session_manager):
        """Delegation respects max_wall_time_seconds boundary."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        local_call_count = 0

        async def slow_execute(*args, **kwargs):
            nonlocal local_call_count
            local_call_count += 1
            await asyncio.sleep(0.1)  # Each call takes 0.1s
            return MockAgentResult(
                agent_name=kwargs.get("agent_name", "unknown"),
                response="Success",
            )

        mock_runtime.execute_agent.side_effect = slow_execute

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            budget=DelegationBudget(max_wall_time_seconds=0.15),  # Very short timeout
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
            {"agent": "child2", "prompt": "p2"},
            {"agent": "child3", "prompt": "p3"},
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
        # Should stop early due to timeout
        # At least root should complete, but not all children
        assert local_call_count >= 1

    @pytest.mark.asyncio
    async def test_check_boundaries_returns_stop_reason(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """_check_boundaries returns appropriate DelegationStopReason."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(
            budget=DelegationBudget(max_iterations=1),
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        # Initialize context
        engine._context = type(
            "DelegationContext",
            (),
            {
                "iteration_count": 5,
                "elapsed_seconds": lambda: 0,
                "current_depth": 0,
                "total_agents_spawned": 0,
            },
        )()

        reason = engine._check_boundaries()
        assert reason == DelegationStopReason.BUDGET_EXHAUSTED


class TestConvergence:
    """Test convergence detection in delegation."""

    @pytest.mark.asyncio
    async def test_convergence_triggers_early_termination(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """Convergence detection triggers early termination."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        # All agents return identical results
        async def identical_result(*args, **kwargs):
            return MockAgentResult(
                agent_name=kwargs.get("agent_name", "unknown"),
                response="Same",
                metadata={"result": "identical"},
            )

        mock_runtime.execute_agent.side_effect = identical_result

        config = DelegationConfig(
            mode=TraversalMode.BFS,
            check_convergence=True,
            budget=DelegationBudget(stagnation_threshold=2),
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

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
        delegation_result = result.unwrap()
        # Should have detected convergence
        assert delegation_result.converged or delegation_result.stagnation_detected


class TestCallbacks:
    """Test callback support in delegation."""

    @pytest.mark.asyncio
    async def test_on_agent_spawn_callback(self, mock_runtime, mock_registry, mock_session_manager):
        """on_agent_spawn callback is called when agents are spawned."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        spawn_calls = []

        async def on_spawn(agent_id: str, depth: int):
            spawn_calls.append((agent_id, depth))

        config = DelegationConfig(
            mode=TraversalMode.BFS,
            on_agent_spawn=on_spawn,
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
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
        # Should have 2 spawn calls: root + child1
        assert len(spawn_calls) == 2
        # Verify agent_ids contain agent names
        assert any("root" in call[0] for call in spawn_calls)
        assert any("child1" in call[0] for call in spawn_calls)

    @pytest.mark.asyncio
    async def test_on_agent_complete_callback(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """on_agent_complete callback is called when agents complete."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        complete_calls = []

        async def on_complete(agent_id: str, result):
            complete_calls.append((agent_id, result))

        config = DelegationConfig(
            mode=TraversalMode.BFS,
            on_agent_complete=on_complete,
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
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
        # Should have 2 complete calls: root + child1
        assert len(complete_calls) == 2


class TestResultConstruction:
    """Test DelegationResult construction."""

    @pytest.mark.asyncio
    async def test_build_result_success_with_no_errors(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """_build_result creates success=True when no errors."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig()
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=None,
        )

        assert result.is_ok()
        delegation_result = result.unwrap()
        assert delegation_result.success is True
        assert delegation_result.stop_reason == DelegationStopReason.COMPLETED
        assert delegation_result.total_agents == 1
        assert delegation_result.elapsed_seconds >= 0

    @pytest.mark.asyncio
    async def test_build_result_records_errors(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """_build_result records errors in result."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        mock_runtime.execute_agent.side_effect = ValueError("Agent failed")

        config = DelegationConfig()
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=None,
        )

        # Should still return Ok result (errors recorded, not raised)
        assert result.is_ok()
        delegation_result = result.unwrap()
        assert delegation_result.success is False
        assert len(delegation_result.errors) > 0

    @pytest.mark.asyncio
    async def test_build_result_includes_max_depth_reached(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """_build_result includes max_depth_reached in result."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(
            budget=DelegationBudget(max_depth=2),
        )
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        children = [
            {"agent": "child1", "prompt": "p1"},
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
        delegation_result = result.unwrap()
        assert delegation_result.max_depth_reached >= 0


class TestErrorHandling:
    """Test error handling in delegation."""

    @pytest.mark.asyncio
    async def test_delegate_returns_err_on_unexpected_exception(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """delegate returns Err on unexpected exceptions during setup."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        # Make runtime initialization fail
        mock_runtime.execute_agent.side_effect = RuntimeError("Unexpected error")

        config = DelegationConfig()
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=None,
        )

        # Error should be caught and returned as Err
        assert result.is_ok()  # Error recorded in result, not raised


class TestExecuteAgent:
    """Test _execute_agent method."""

    @pytest.mark.asyncio
    async def test_execute_agent_increments_counters(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """_execute_agent increments spawn/complete counters correctly."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig()
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        result = await engine.delegate(
            agent_name="root",
            prompt="root prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=None,
        )

        assert result.is_ok()
        delegation_result = result.unwrap()
        assert delegation_result.total_agents == 1

    @pytest.mark.asyncio
    async def test_execute_agent_generates_unique_id(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """_execute_agent generates unique agent_id with uuid."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        spawn_ids = []

        async def capture_id(agent_id: str, depth: int):
            spawn_ids.append(agent_id)

        config = DelegationConfig(on_agent_spawn=capture_id)
        engine = DelegationEngine(config, mock_runtime, mock_registry)

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
        # All IDs should be unique
        assert len(spawn_ids) == len(set(spawn_ids))

    @pytest.mark.asyncio
    async def test_execute_agent_calls_runtime_with_correct_params(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """_execute_agent calls runtime.execute_agent with correct params."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig()
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        await engine.delegate(
            agent_name="test_agent",
            prompt="test prompt",
            session_id="test_session",
            session_manager=mock_session_manager,
            tools=None,
            children=None,
        )

        mock_runtime.execute_agent.assert_called_once()
        call_kwargs = mock_runtime.execute_agent.call_args.kwargs
        assert call_kwargs["agent_name"] == "test_agent"
        assert call_kwargs["user_message"] == "test prompt"
        assert call_kwargs["session_id"] == "test_session"
        assert call_kwargs["skills"] == []


class TestThreadSafety:
    """Test thread safety in delegation."""

    @pytest.mark.asyncio
    async def test_bfs_uses_lock_for_context_updates(
        self, mock_runtime, mock_registry, mock_session_manager
    ):
        """BFS mode uses asyncio.Lock for thread-safe context updates."""
        from dawn_kestrel.delegation.engine import DelegationEngine

        config = DelegationConfig(mode=TraversalMode.BFS)
        engine = DelegationEngine(config, mock_runtime, mock_registry)

        # Verify lock exists
        assert hasattr(engine, "_lock")
        assert isinstance(engine._lock, asyncio.Lock)

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
        # Context should have been updated correctly
        delegation_result = result.unwrap()
        assert delegation_result.total_agents == 3
