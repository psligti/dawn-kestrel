"""Tests for delegation types module.

TDD RED phase - tests written first, implementation follows.
"""

import time
from enum import Enum

import pytest

from dawn_kestrel.delegation.types import (
    DelegationBudget,
    DelegationConfig,
    DelegationContext,
    DelegationResult,
    DelegationStopReason,
    TraversalMode,
)


class TestTraversalMode:
    """Tests for TraversalMode enum."""

    def test_traversal_mode_is_str_enum(self):
        """TraversalMode should inherit from str and Enum."""
        assert issubclass(TraversalMode, str)
        assert issubclass(TraversalMode, Enum)

    def test_traversal_mode_has_bfs(self):
        """TraversalMode should have BFS value."""
        assert TraversalMode.BFS.value == "breadth_first"

    def test_traversal_mode_has_dfs(self):
        """TraversalMode should have DFS value."""
        assert TraversalMode.DFS.value == "depth_first"

    def test_traversal_mode_has_adaptive(self):
        """TraversalMode should have ADAPTIVE value."""
        assert TraversalMode.ADAPTIVE.value == "adaptive"


class TestDelegationStopReason:
    """Tests for DelegationStopReason enum."""

    def test_stop_reason_is_str_enum(self):
        """DelegationStopReason should inherit from str and Enum."""
        assert issubclass(DelegationStopReason, str)
        assert issubclass(DelegationStopReason, Enum)

    def test_stop_reason_has_all_values(self):
        """DelegationStopReason should have all 8 required values."""
        expected_values = {
            "COMPLETED": "completed",
            "CONVERGED": "converged",
            "BUDGET_EXHAUSTED": "budget",
            "STAGNATION": "stagnation",
            "DEPTH_LIMIT": "depth_limit",
            "BREADTH_LIMIT": "breadth_limit",
            "TIMEOUT": "timeout",
            "ERROR": "error",
        }
        for attr_name, expected_value in expected_values.items():
            assert hasattr(DelegationStopReason, attr_name)
            assert getattr(DelegationStopReason, attr_name).value == expected_value


class TestDelegationBudget:
    """Tests for DelegationBudget dataclass."""

    def test_default_values(self):
        """DelegationBudget should have correct defaults."""
        budget = DelegationBudget()
        assert budget.max_depth == 3
        assert budget.max_breadth == 5
        assert budget.max_total_agents == 20
        assert budget.max_wall_time_seconds == 300.0
        assert budget.max_iterations == 10
        assert budget.stagnation_threshold == 3

    def test_custom_values(self):
        """DelegationBudget should accept custom values."""
        budget = DelegationBudget(
            max_depth=5,
            max_breadth=10,
            max_total_agents=50,
            max_wall_time_seconds=600.0,
            max_iterations=20,
            stagnation_threshold=5,
        )
        assert budget.max_depth == 5
        assert budget.max_breadth == 10
        assert budget.max_total_agents == 50
        assert budget.max_wall_time_seconds == 600.0
        assert budget.max_iterations == 20
        assert budget.stagnation_threshold == 5

    def test_rejects_negative_max_depth(self):
        """DelegationBudget should reject negative max_depth."""
        with pytest.raises(ValueError, match="max_depth"):
            DelegationBudget(max_depth=-1)

    def test_rejects_zero_max_depth(self):
        """DelegationBudget should reject zero max_depth."""
        with pytest.raises(ValueError, match="max_depth"):
            DelegationBudget(max_depth=0)

    def test_rejects_negative_max_breadth(self):
        """DelegationBudget should reject negative max_breadth."""
        with pytest.raises(ValueError, match="max_breadth"):
            DelegationBudget(max_breadth=-1)

    def test_rejects_negative_max_total_agents(self):
        """DelegationBudget should reject negative max_total_agents."""
        with pytest.raises(ValueError, match="max_total_agents"):
            DelegationBudget(max_total_agents=-1)

    def test_rejects_negative_max_wall_time(self):
        """DelegationBudget should reject negative max_wall_time_seconds."""
        with pytest.raises(ValueError, match="max_wall_time_seconds"):
            DelegationBudget(max_wall_time_seconds=-1.0)

    def test_rejects_zero_max_wall_time(self):
        """DelegationBudget should reject zero max_wall_time_seconds."""
        with pytest.raises(ValueError, match="max_wall_time_seconds"):
            DelegationBudget(max_wall_time_seconds=0.0)

    def test_rejects_negative_max_iterations(self):
        """DelegationBudget should reject negative max_iterations."""
        with pytest.raises(ValueError, match="max_iterations"):
            DelegationBudget(max_iterations=-1)

    def test_rejects_negative_stagnation_threshold(self):
        """DelegationBudget should reject negative stagnation_threshold."""
        with pytest.raises(ValueError, match="stagnation_threshold"):
            DelegationBudget(stagnation_threshold=-1)


class TestDelegationConfig:
    """Tests for DelegationConfig dataclass."""

    def test_default_values(self):
        """DelegationConfig should have correct defaults."""
        config = DelegationConfig()
        assert config.mode == TraversalMode.BFS
        assert isinstance(config.budget, DelegationBudget)
        assert config.check_convergence is True
        assert config.evidence_keys == ["result", "findings"]
        assert config.on_agent_spawn is None
        assert config.on_agent_complete is None
        assert config.on_convergence_check is None

    def test_custom_values(self):
        """DelegationConfig should accept custom values."""

        async def dummy_callback(*args):
            pass

        config = DelegationConfig(
            mode=TraversalMode.DFS,
            budget=DelegationBudget(max_depth=10),
            check_convergence=False,
            evidence_keys=["custom_key"],
            on_agent_spawn=dummy_callback,
            on_agent_complete=dummy_callback,
            on_convergence_check=dummy_callback,
        )
        assert config.mode == TraversalMode.DFS
        assert config.budget.max_depth == 10
        assert config.check_convergence is False
        assert config.evidence_keys == ["custom_key"]
        assert config.on_agent_spawn == dummy_callback


class TestDelegationContext:
    """Tests for DelegationContext dataclass."""

    def test_required_root_task_id(self):
        """DelegationContext should require root_task_id."""
        with pytest.raises(TypeError):
            DelegationContext()

    def test_default_values(self):
        """DelegationContext should have correct defaults."""
        context = DelegationContext(root_task_id="task-123")
        assert context.root_task_id == "task-123"
        assert context.current_depth == 0
        assert context.total_agents_spawned == 0
        assert context.active_agents == 0
        assert context.completed_agents == 0
        assert context.results == []
        assert context.errors == []
        assert context.iteration_count == 0
        assert context.novelty_signatures == []
        assert context.stagnation_count == 0

    def test_start_time_uses_time_time(self):
        """DelegationContext.start_time should use time.time()."""
        before = time.time()
        context = DelegationContext(root_task_id="task-123")
        after = time.time()
        assert before <= context.start_time <= after

    def test_elapsed_seconds(self):
        """DelegationContext.elapsed_seconds() should return correct duration."""
        context = DelegationContext(root_task_id="task-123")
        # Simulate some time passing
        context.start_time = time.time() - 5.0  # 5 seconds ago
        elapsed = context.elapsed_seconds()
        assert 4.9 <= elapsed <= 5.1  # Allow small tolerance


class TestDelegationResult:
    """Tests for DelegationResult dataclass."""

    def test_required_fields(self):
        """DelegationResult should require all fields."""
        result = DelegationResult(
            success=True,
            stop_reason=DelegationStopReason.COMPLETED,
            results=[{"data": "test"}],
            errors=[],
            total_agents=5,
            max_depth_reached=2,
            elapsed_seconds=10.5,
            iterations=3,
            converged=False,
            stagnation_detected=False,
        )
        assert result.success is True
        assert result.stop_reason == DelegationStopReason.COMPLETED
        assert result.results == [{"data": "test"}]
        assert result.errors == []
        assert result.total_agents == 5
        assert result.max_depth_reached == 2
        assert result.elapsed_seconds == 10.5
        assert result.iterations == 3
        assert result.converged is False
        assert result.stagnation_detected is False
        assert result.final_novelty_signature is None

    def test_optional_final_novelty_signature(self):
        """DelegationResult should allow optional final_novelty_signature."""
        result = DelegationResult(
            success=True,
            stop_reason=DelegationStopReason.CONVERGED,
            results=[],
            errors=[],
            total_agents=3,
            max_depth_reached=1,
            elapsed_seconds=5.0,
            iterations=2,
            converged=True,
            stagnation_detected=False,
            final_novelty_signature="abc123",
        )
        assert result.final_novelty_signature == "abc123"
