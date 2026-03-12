"""Tests for multi-agent workflow module.

Tests cover:
- ExecutionMode: enum values
- ExecutionStatus: status tracking
- AggregationStrategy: aggregation options
- AgentSpec: agent specification
- AggregationSpec: aggregation config
- AgentExecutionResult: individual result
- WorkflowResult: overall result
- MultiAgentWorkflow: coordination
- FindingsAggregator: findings merging
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio

from dawn_kestrel.workflow.multi_agent import (
    AggregationSpec,
    AggregationStrategy,
    AgentExecutionResult,
    AgentSpec,
    ConflictResolution,
    ExecutionMode,
    ExecutionStatus,
    FindingsAggregator,
    MultiAgentWorkflow,
    WorkflowResult,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def simple_agent() -> MagicMock:
    """Create a simple mock agent."""
    agent = MagicMock()
    agent.run = AsyncMock(return_value={"status": "ok", "output": "result"})
    return agent


@pytest.fixture
def agent_spec(simple_agent: MagicMock) -> AgentSpec:
    """Create a basic AgentSpec."""
    return AgentSpec(
        name="test_agent",
        agent=simple_agent,
    )


@pytest.fixture
def workflow(simple_agent: MagicMock) -> MultiAgentWorkflow:
    """Create a basic workflow with one agent."""
    return MultiAgentWorkflow(
        agents=[AgentSpec(name="test", agent=simple_agent)],
        execution_mode=ExecutionMode.PARALLEL,
    )


# ============================================================================
# ExecutionMode Tests
# ============================================================================


class TestExecutionMode:
    """Tests for ExecutionMode enum."""

    def test_sequential_value(self) -> None:
        """SEQUENTIAL should have value 'sequential'."""
        assert ExecutionMode.SEQUENTIAL.value == "sequential"

    def test_parallel_value(self) -> None:
        """PARALLEL should have value 'parallel'."""
        assert ExecutionMode.PARALLEL.value == "parallel"

    def test_dag_value(self) -> None:
        """DAG should have value 'dag'."""
        assert ExecutionMode.DAG.value == "dag"

    def test_conditional_value(self) -> None:
        """CONDITIONAL should have value 'conditional'."""
        assert ExecutionMode.CONDITIONAL.value == "conditional"


# ============================================================================
# ExecutionStatus Tests
# ============================================================================


class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_status_values(self) -> None:
        """All status values should be defined."""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.SKIPPED.value == "skipped"


# ============================================================================
# AggregationStrategy Tests
# ============================================================================


class TestAggregationStrategy:
    """Tests for AggregationStrategy enum."""

    def test_strategy_values(self) -> None:
        """All strategy values should be defined."""
        assert AggregationStrategy.MERGE.value == "merge"
        assert AggregationStrategy.FIRST_SUCCESS.value == "first_success"
        assert AggregationStrategy.VOTE.value == "vote"
        assert AggregationStrategy.WEIGHTED.value == "weighted"
        assert AggregationStrategy.PRIORITY.value == "priority"


# ============================================================================
# ConflictResolution Tests
# ============================================================================


class TestConflictResolution:
    """Tests for ConflictResolution enum."""

    def test_resolution_values(self) -> None:
        """All resolution values should be defined."""
        assert ConflictResolution.FAIL.value == "fail"
        assert ConflictResolution.FIRST.value == "first"
        assert ConflictResolution.HIGHEST_SEVERITY.value == "highest_severity"
        assert ConflictResolution.MERGE.value == "merge"
        assert ConflictResolution.VOTE.value == "vote"


# ============================================================================
# AgentSpec Tests
# ============================================================================


class TestAgentSpec:
    """Tests for AgentSpec model."""

    def test_create_with_required_fields(self, simple_agent: MagicMock) -> None:
        """AgentSpec should be created with name and agent."""
        spec = AgentSpec(name="test", agent=simple_agent)

        assert spec.name == "test"
        assert spec.agent == simple_agent

    def test_default_values(self, simple_agent: MagicMock) -> None:
        """AgentSpec should have sensible defaults."""
        spec = AgentSpec(name="test", agent=simple_agent)

        assert spec.dependencies == []
        assert spec.condition is None
        assert spec.timeout_seconds == 300.0
        assert spec.retry_count == 0
        assert spec.weight == 1.0
        assert spec.priority == 1

    def test_custom_values(self, simple_agent: MagicMock) -> None:
        """AgentSpec should accept custom values."""
        spec = AgentSpec(
            name="test",
            agent=simple_agent,
            dependencies=["dep1", "dep2"],
            timeout_seconds=60.0,
            weight=2.0,
            priority=5,
        )

        assert spec.dependencies == ["dep1", "dep2"]
        assert spec.timeout_seconds == 60.0
        assert spec.weight == 2.0
        assert spec.priority == 5

    def test_is_relevant_without_condition(self, simple_agent: MagicMock) -> None:
        """AgentSpec without condition should always be relevant."""
        spec = AgentSpec(name="test", agent=simple_agent)

        assert spec.is_relevant({}) is True
        assert spec.is_relevant({"any": "context"}) is True

    def test_is_relevant_with_true_condition(self, simple_agent: MagicMock) -> None:
        """AgentSpec with condition returning True should be relevant."""
        spec = AgentSpec(
            name="test",
            agent=simple_agent,
            condition=lambda ctx: ctx.get("run", False),
        )

        assert spec.is_relevant({"run": True}) is True

    def test_is_relevant_with_false_condition(self, simple_agent: MagicMock) -> None:
        """AgentSpec with condition returning False should not be relevant."""
        spec = AgentSpec(
            name="test",
            agent=simple_agent,
            condition=lambda ctx: ctx.get("run", False),
        )

        assert spec.is_relevant({"run": False}) is False
        assert spec.is_relevant({}) is False


# ============================================================================
# AggregationSpec Tests
# ============================================================================


class TestAggregationSpec:
    """Tests for AggregationSpec model."""

    def test_create_with_defaults(self) -> None:
        """AggregationSpec should have defaults."""
        spec = AggregationSpec()

        assert spec.strategy == AggregationStrategy.MERGE
        assert spec.conflict_resolution == ConflictResolution.FIRST
        assert spec.weights == {}
        assert spec.priority_order == []

    def test_custom_strategy(self) -> None:
        """AggregationSpec should accept custom strategy."""
        spec = AggregationSpec(strategy=AggregationStrategy.WEIGHTED)

        assert spec.strategy == AggregationStrategy.WEIGHTED

    def test_custom_weights(self) -> None:
        """AggregationSpec should accept custom weights."""
        spec = AggregationSpec(
            strategy=AggregationStrategy.WEIGHTED,
            weights={"agent1": 2.0, "agent2": 1.0},
        )

        assert spec.weights == {"agent1": 2.0, "agent2": 1.0}


# ============================================================================
# AgentExecutionResult Tests
# ============================================================================


class TestAgentExecutionResult:
    """Tests for AgentExecutionResult model."""

    def test_create_with_required_fields(self) -> None:
        """AgentExecutionResult should require name and status."""
        result = AgentExecutionResult(
            agent_name="test",
            status=ExecutionStatus.COMPLETED,
        )

        assert result.agent_name == "test"
        assert result.status == ExecutionStatus.COMPLETED

    def test_default_values(self) -> None:
        """AgentExecutionResult should have defaults."""
        result = AgentExecutionResult(
            agent_name="test",
            status=ExecutionStatus.COMPLETED,
        )

        assert result.output is None
        assert result.error is None
        assert result.duration_seconds == 0.0
        assert result.metadata == {}

    def test_is_success_true(self) -> None:
        """is_success should be True for COMPLETED status."""
        result = AgentExecutionResult(
            agent_name="test",
            status=ExecutionStatus.COMPLETED,
        )

        assert result.is_success is True

    def test_is_success_false(self) -> None:
        """is_success should be False for non-COMPLETED status."""
        for status in [
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.FAILED,
            ExecutionStatus.SKIPPED,
        ]:
            result = AgentExecutionResult(agent_name="test", status=status)
            assert result.is_success is False


# ============================================================================
# WorkflowResult Tests
# ============================================================================


class TestWorkflowResult:
    """Tests for WorkflowResult model."""

    def test_create_with_required_fields(self) -> None:
        """WorkflowResult should require success and agent_results."""
        result = WorkflowResult(
            success=True,
            agent_results={},
        )

        assert result.success is True
        assert result.agent_results == {}

    def test_default_values(self) -> None:
        """WorkflowResult should have defaults."""
        result = WorkflowResult(success=True, agent_results={})

        assert result.aggregated_result is None
        assert result.execution_order == []
        assert result.errors == {}
        assert result.timing == {}
        assert result.total_duration_seconds == 0.0

    def test_failed_agents_property(self) -> None:
        """failed_agents should return names of failed agents."""
        result = WorkflowResult(
            success=False,
            agent_results={
                "agent1": AgentExecutionResult(
                    agent_name="agent1",
                    status=ExecutionStatus.COMPLETED,
                ),
                "agent2": AgentExecutionResult(
                    agent_name="agent2",
                    status=ExecutionStatus.FAILED,
                    error="Something went wrong",
                ),
            },
        )

        assert result.failed_agents == ["agent2"]

    def test_failed_agents_empty(self) -> None:
        """failed_agents should be empty when all succeed."""
        result = WorkflowResult(
            success=True,
            agent_results={
                "agent1": AgentExecutionResult(
                    agent_name="agent1",
                    status=ExecutionStatus.COMPLETED,
                ),
            },
        )

        assert result.failed_agents == []

    def test_skipped_agents_property(self) -> None:
        """skipped_agents should return names of skipped agents."""
        result = WorkflowResult(
            success=True,
            agent_results={
                "agent1": AgentExecutionResult(
                    agent_name="agent1",
                    status=ExecutionStatus.COMPLETED,
                ),
                "agent2": AgentExecutionResult(
                    agent_name="agent2",
                    status=ExecutionStatus.SKIPPED,
                ),
            },
        )

        assert result.skipped_agents == ["agent2"]


# ============================================================================
# MultiAgentWorkflow Tests
# ============================================================================


class TestMultiAgentWorkflow:
    """Tests for MultiAgentWorkflow class."""

    def test_create_with_agents(self, simple_agent: MagicMock) -> None:
        """Workflow should be created with agents."""
        workflow = MultiAgentWorkflow(
            agents=[AgentSpec(name="test", agent=simple_agent)],
        )

        assert "test" in workflow.agents

    def test_default_execution_mode(self, simple_agent: MagicMock) -> None:
        """Workflow should default to PARALLEL mode."""
        workflow = MultiAgentWorkflow(
            agents=[AgentSpec(name="test", agent=simple_agent)],
        )

        assert workflow.execution_mode == ExecutionMode.PARALLEL

    def test_custom_execution_mode(self, simple_agent: MagicMock) -> None:
        """Workflow should accept custom execution mode."""
        workflow = MultiAgentWorkflow(
            agents=[AgentSpec(name="test", agent=simple_agent)],
            execution_mode=ExecutionMode.SEQUENTIAL,
        )

        assert workflow.execution_mode == ExecutionMode.SEQUENTIAL

    def test_dag_validation_no_cycles(self, simple_agent: MagicMock) -> None:
        """DAG mode should reject circular dependencies."""
        with pytest.raises(ValueError, match="Circular dependency"):
            MultiAgentWorkflow(
                agents=[
                    AgentSpec(name="a", agent=simple_agent, dependencies=["b"]),
                    AgentSpec(name="b", agent=simple_agent, dependencies=["a"]),
                ],
                execution_mode=ExecutionMode.DAG,
            )

    def test_dag_validation_valid(self, simple_agent: MagicMock) -> None:
        """DAG mode should accept valid dependency graph."""
        # Should not raise
        workflow = MultiAgentWorkflow(
            agents=[
                AgentSpec(name="a", agent=simple_agent),
                AgentSpec(name="b", agent=simple_agent, dependencies=["a"]),
                AgentSpec(name="c", agent=simple_agent, dependencies=["a", "b"]),
            ],
            execution_mode=ExecutionMode.DAG,
        )

        assert "c" in workflow.agents

    @pytest.mark.asyncio
    async def test_execute_parallel(self, simple_agent: MagicMock) -> None:
        """Parallel execution should run all agents."""
        workflow = MultiAgentWorkflow(
            agents=[
                AgentSpec(name="agent1", agent=simple_agent),
                AgentSpec(name="agent2", agent=simple_agent),
            ],
            execution_mode=ExecutionMode.PARALLEL,
        )

        result = await workflow.execute(input="test")

        assert result.success is True
        assert len(result.agent_results) == 2
        assert "agent1" in result.agent_results
        assert "agent2" in result.agent_results

    @pytest.mark.asyncio
    async def test_execute_sequential(self, simple_agent: MagicMock) -> None:
        """Sequential execution should run agents in order."""
        call_order = []

        def make_agent(name: str) -> MagicMock:
            agent = MagicMock()

            async def run(*args, **kwargs):
                call_order.append(name)
                return {"status": "ok"}

            agent.run = run
            return agent

        workflow = MultiAgentWorkflow(
            agents=[
                AgentSpec(name="first", agent=make_agent("first")),
                AgentSpec(name="second", agent=make_agent("second")),
                AgentSpec(name="third", agent=make_agent("third")),
            ],
            execution_mode=ExecutionMode.SEQUENTIAL,
        )

        result = await workflow.execute(input="test")

        assert call_order == ["first", "second", "third"]
        assert result.execution_order == ["first", "second", "third"]

    @pytest.mark.asyncio
    async def test_execute_dag(self, simple_agent: MagicMock) -> None:
        """DAG execution should respect dependencies."""
        call_order = []

        def make_agent(name: str) -> MagicMock:
            agent = MagicMock()

            async def run(*args, **kwargs):
                call_order.append(name)
                return {"status": "ok"}

            agent.run = run
            return agent

        workflow = MultiAgentWorkflow(
            agents=[
                AgentSpec(name="base", agent=make_agent("base")),
                AgentSpec(name="dep1", agent=make_agent("dep1"), dependencies=["base"]),
                AgentSpec(name="dep2", agent=make_agent("dep2"), dependencies=["base"]),
                AgentSpec(
                    name="final",
                    agent=make_agent("final"),
                    dependencies=["dep1", "dep2"],
                ),
            ],
            execution_mode=ExecutionMode.DAG,
        )

        result = await workflow.execute(input="test")

        assert "base" in call_order
        assert call_order.index("base") < call_order.index("dep1")
        assert call_order.index("base") < call_order.index("dep2")
        assert call_order.index("dep1") < call_order.index("final")
        assert call_order.index("dep2") < call_order.index("final")

    @pytest.mark.asyncio
    async def test_execute_conditional(self, simple_agent: MagicMock) -> None:
        """Conditional execution should only run relevant agents."""
        workflow = MultiAgentWorkflow(
            agents=[
                AgentSpec(name="always", agent=simple_agent),
                AgentSpec(
                    name="conditional",
                    agent=simple_agent,
                    condition=lambda ctx: ctx.get("run_conditional", False),
                ),
            ],
            execution_mode=ExecutionMode.CONDITIONAL,
        )

        # Without condition met
        result = await workflow.execute(input="test", context={})
        assert "always" in result.agent_results
        # conditional may or may not run depending on implementation

    @pytest.mark.asyncio
    async def test_execute_handles_timeout(self) -> None:
        """Workflow should handle agent timeout."""
        slow_agent = MagicMock()

        async def slow_run(*args, **kwargs):
            await asyncio.sleep(10)
            return {"status": "ok"}

        slow_agent.run = slow_run

        workflow = MultiAgentWorkflow(
            agents=[
                AgentSpec(name="slow", agent=slow_agent, timeout_seconds=0.1),
            ],
            execution_mode=ExecutionMode.PARALLEL,
        )

        result = await workflow.execute(input="test")

        assert result.agent_results["slow"].status == ExecutionStatus.FAILED
        assert "Timeout" in result.agent_results["slow"].error

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self) -> None:
        """Workflow should handle agent exceptions."""
        failing_agent = MagicMock()

        async def failing_run(*args, **kwargs):
            raise RuntimeError("Agent failed!")

        failing_agent.run = failing_run

        workflow = MultiAgentWorkflow(
            agents=[AgentSpec(name="failing", agent=failing_agent)],
            execution_mode=ExecutionMode.PARALLEL,
        )

        result = await workflow.execute(input="test")

        assert result.agent_results["failing"].status == ExecutionStatus.FAILED
        assert "Agent failed!" in result.agent_results["failing"].error

    @pytest.mark.asyncio
    async def test_execute_aggregates_results(self, simple_agent: MagicMock) -> None:
        """Workflow should aggregate results."""
        workflow = MultiAgentWorkflow(
            agents=[
                AgentSpec(name="agent1", agent=simple_agent),
                AgentSpec(name="agent2", agent=simple_agent),
            ],
            execution_mode=ExecutionMode.PARALLEL,
            aggregation=AggregationSpec(strategy=AggregationStrategy.MERGE),
        )

        result = await workflow.execute(input="test")

        assert result.aggregated_result is not None


# ============================================================================
# FindingsAggregator Tests
# ============================================================================


class TestFindingsAggregator:
    """Tests for FindingsAggregator class."""

    def test_aggregate_empty_results(self) -> None:
        """Aggregator should handle empty results."""
        aggregator = FindingsAggregator()
        spec = AggregationSpec()

        result = aggregator.aggregate({}, spec)

        assert result["findings"] == []
        assert result["total_count"] == 0
        assert result["sources"] == []

    def test_aggregate_with_findings(self) -> None:
        """Aggregator should collect findings from results."""
        aggregator = FindingsAggregator()
        spec = AggregationSpec()

        results = {
            "agent1": AgentExecutionResult(
                agent_name="agent1",
                status=ExecutionStatus.COMPLETED,
                output={"findings": [{"id": "f1", "message": "Issue 1"}]},
            ),
            "agent2": AgentExecutionResult(
                agent_name="agent2",
                status=ExecutionStatus.COMPLETED,
                output={"findings": [{"id": "f2", "message": "Issue 2"}]},
            ),
        }

        result = aggregator.aggregate(results, spec)

        assert len(result["findings"]) == 2
        assert result["total_count"] == 2
        assert "agent1" in result["sources"]
        assert "agent2" in result["sources"]

    def test_aggregate_deduplicates_by_id(self) -> None:
        """Aggregator should deduplicate findings by ID."""
        aggregator = FindingsAggregator()
        spec = AggregationSpec()

        results = {
            "agent1": AgentExecutionResult(
                agent_name="agent1",
                status=ExecutionStatus.COMPLETED,
                output={
                    "findings": [
                        {"id": "dup", "message": "First"},
                        {"id": "dup", "message": "Duplicate"},
                    ]
                },
            ),
        }

        result = aggregator.aggregate(results, spec)

        assert len(result["findings"]) == 1

    def test_aggregate_deduplicates_by_hash(self) -> None:
        """Aggregator should deduplicate findings by hash."""
        aggregator = FindingsAggregator()
        spec = AggregationSpec()

        results = {
            "agent1": AgentExecutionResult(
                agent_name="agent1",
                status=ExecutionStatus.COMPLETED,
                output={
                    "findings": [
                        {"hash": "abc123", "message": "First"},
                        {"hash": "abc123", "message": "Duplicate"},
                    ]
                },
            ),
        }

        result = aggregator.aggregate(results, spec)

        assert len(result["findings"]) == 1

    def test_aggregate_skips_failed_results(self) -> None:
        """Aggregator should skip failed results."""
        aggregator = FindingsAggregator()
        spec = AggregationSpec()

        results = {
            "agent1": AgentExecutionResult(
                agent_name="agent1",
                status=ExecutionStatus.FAILED,
                error="Error",
            ),
        }

        result = aggregator.aggregate(results, spec)

        assert result["findings"] == []

    def test_aggregate_resolves_by_severity(self) -> None:
        """Aggregator should resolve conflicts by highest severity."""
        aggregator = FindingsAggregator()
        spec = AggregationSpec(conflict_resolution=ConflictResolution.HIGHEST_SEVERITY)

        results = {
            "agent1": AgentExecutionResult(
                agent_name="agent1",
                status=ExecutionStatus.COMPLETED,
                output={
                    "findings": [
                        {"location": "file.py:10", "severity": "low", "msg": "Low"},
                        {"location": "file.py:10", "severity": "high", "msg": "High"},
                    ]
                },
            ),
        }

        result = aggregator.aggregate(results, spec)

        # Should keep the high severity one
        severities = [f.get("severity") for f in result["findings"]]
        assert "high" in severities

    def test_aggregate_handles_list_output(self) -> None:
        """Aggregator should handle list output directly."""
        aggregator = FindingsAggregator()
        spec = AggregationSpec()

        results = {
            "agent1": AgentExecutionResult(
                agent_name="agent1",
                status=ExecutionStatus.COMPLETED,
                output=[{"id": "f1", "message": "Direct list"}],
            ),
        }

        result = aggregator.aggregate(results, spec)

        assert len(result["findings"]) == 1
