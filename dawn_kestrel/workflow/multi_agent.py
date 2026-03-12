"""Multi-agent workflow primitives.

This module provides generic primitives for coordinating multiple
specialized agents. It generalizes patterns from iron-rook's
PRReviewOrchestrator to work with any multi-agent coordination.

Key concepts:
- AgentSpec: Specification for an agent in a workflow
- ExecutionMode: How to execute agents (parallel, sequential, DAG)
- AggregationSpec: How to combine results from multiple agents
- MultiAgentWorkflow: The main coordinator class

Usage:
    from dawn_kestrel.workflow import MultiAgentWorkflow, AgentSpec, ExecutionMode

    workflow = MultiAgentWorkflow(
        agents=[
            AgentSpec(name="security", agent=security_agent),
            AgentSpec(name="architecture", agent=arch_agent, dependencies=["security"]),
            AgentSpec(name="docs", agent=docs_agent),
        ],
        execution_mode=ExecutionMode.DAG,
        aggregation=AggregationSpec(strategy="merge_findings"),
    )

    result = await workflow.execute(context)
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Protocol,
    TypeVar,
    runtime_checkable,
)

import pydantic as pd

if TYPE_CHECKING:
    from dawn_kestrel.core.result import Result

logger = logging.getLogger(__name__)

# Type variables for generic workflow
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
AgentResultT = TypeVar("AgentResultT")


class ExecutionMode(str, Enum):
    """How to execute agents in a workflow.

    SEQUENTIAL: Execute agents one at a time, in order
    PARALLEL: Execute all agents simultaneously
    DAG: Execute based on dependency graph (topological order)
    CONDITIONAL: Execute only agents whose conditions are met
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DAG = "dag"
    CONDITIONAL = "conditional"


class ExecutionStatus(str, Enum):
    """Status of agent execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AggregationStrategy(str, Enum):
    """How to aggregate results from multiple agents.

    MERGE: Merge all results (default for findins/workflows)
    FIRST_SUCCESS: Use first successful result
    VOTE: Majority voting on results
    WEIGHTED: Weighted average/combination
    PRIORITY: Use highest priority agent's result
    """

    MERGE = "merge"
    FIRST_SUCCESS = "first_success"
    VOTE = "vote"
    WEIGHTED = "weighted"
    PRIORITY = "priority"


class ConflictResolution(str, Enum):
    """How to resolve conflicts between agent results.

    FAIL: Raise error on conflict
    FIRST: Use first result
    HIGHEST_SEVERITY: Use result with highest severity
    MERGE: Attempt to merge conflicting results
    VOTE: Use majority result
    """

    FAIL = "fail"
    FIRST = "first"
    HIGHEST_SEVERITY = "highest_severity"
    MERGE = "merge"
    VOTE = "vote"


class AgentSpec(pd.BaseModel):
    """Specification for an agent in a workflow.

    Attributes:
        name: Unique identifier for this agent
        agent: The agent instance or factory function
        dependencies: Names of agents that must complete first (for DAG mode)
        condition: Optional function to determine if agent should run
        timeout_seconds: Maximum execution time
        retry_count: Number of retries on failure
        weight: Weight for weighted aggregation
        priority: Priority for priority-based aggregation (lower = higher priority)
    """

    name: str
    agent: AgentResultT  # Agent instance or factory
    dependencies: list[str] = pd.Field(default_factory=list)
    condition: Callable[[dict[str, Any]], bool] | None = None
    timeout_seconds: float = 300.0
    retry_count: int = 0
    weight: float = 1.0
    priority: int = 1

    model_config = pd.ConfigDict(arbitrary_types_allowed=True)

    def is_relevant(self, context: dict[str, Any]) -> bool:
        """Check if this agent should run based on condition."""
        if self.condition is None:
            return True
        return self.condition(context)


class AggregationSpec(pd.BaseModel):
    """How to aggregate results from multiple agents.

    Attributes:
        strategy: Aggregation strategy to use
        conflict_resolution: How to resolve conflicts
        weights: Agent name -> weight mapping for weighted aggregation
        priority_order: Order of agents for priority-based aggregation
    """

    strategy: AggregationStrategy = AggregationStrategy.MERGE
    conflict_resolution: ConflictResolution = ConflictResolution.FIRST
    weights: dict[str, float] = pd.Field(default_factory=dict)
    priority_order: list[str] = pd.Field(default_factory=list)

    model_config = pd.ConfigDict(extra="forbid")


class AgentExecutionResult(pd.BaseModel):
    """Result from executing a single agent.

    Attributes:
        agent_name: Name of the agent
        status: Execution status
        output: The agent's output (if successful)
        error: Error message (if failed)
        duration_seconds: Execution time
        metadata: Additional metadata
    """

    agent_name: str
    status: ExecutionStatus
    output: AgentResultT | None = None
    error: str | None = None
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = pd.Field(default_factory=dict)

    model_config = pd.ConfigDict(extra="forbid")

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.COMPLETED


class WorkflowResult(pd.BaseModel, Generic[OutputT]):
    """Result from multi-agent workflow execution.

    Attributes:
        success: Whether the workflow succeeded
        agent_results: Results from each agent
        aggregated_result: The aggregated final result
        execution_order: Order in which agents were executed
        errors: Errors by agent name
        timing: Timing information by agent
        total_duration_seconds: Total workflow duration
    """

    success: bool
    agent_results: dict[str, AgentExecutionResult]
    aggregated_result: OutputT | None = None
    execution_order: list[str] = pd.Field(default_factory=list)
    errors: dict[str, str] = pd.Field(default_factory=dict)
    timing: dict[str, float] = pd.Field(default_factory=dict)
    total_duration_seconds: float = 0.0

    model_config = pd.ConfigDict(extra="forbid")

    @property
    def failed_agents(self) -> list[str]:
        """Names of agents that failed."""
        return [
            name
            for name, result in self.agent_results.items()
            if result.status == ExecutionStatus.FAILED
        ]

    @property
    def skipped_agents(self) -> list[str]:
        """Names of agents that were skipped."""
        return [
            name
            for name, result in self.agent_results.items()
            if result.status == ExecutionStatus.SKIPPED
        ]


@runtime_checkable
class AgentExecutor(Protocol[InputT, OutputT]):
    async def execute(
        self,
        agent: Any,
        input: InputT,
        context: dict[str, Any],
    ) -> "Result[OutputT]":
        ...


@runtime_checkable
class ResultAggregator(Protocol[OutputT]):
    def aggregate(
        self,
        results: dict[str, AgentExecutionResult],
        spec: AggregationSpec,
    ) -> OutputT | None:
        ...


class MultiAgentWorkflow(Generic[InputT, OutputT]):
    """Generic multi-agent workflow coordinator.

    This generalizes iron-rook's PRReviewOrchestrator to work
    with any multi-agent coordination pattern.

    Features:
    - Multiple execution modes (parallel, sequential, DAG)
    - Configurable result aggregation
    - Error isolation between agents
    - Timeout handling
    - Conditional agent execution

    Example:
        workflow = MultiAgentWorkflow(
            agents=[
                AgentSpec(name="security", agent=security_agent),
                AgentSpec(name="architecture", agent=arch_agent, dependencies=["security"]),
            ],
            execution_mode=ExecutionMode.DAG,
            aggregation=AggregationSpec(strategy=AggregationStrategy.MERGE),
        )

        result = await workflow.execute(context)
    """

    def __init__(
        self,
        agents: list[AgentSpec],
        execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
        aggregation: AggregationSpec | None = None,
        executor: AgentExecutor[InputT, OutputT] | None = None,
        aggregator: ResultAggregator[OutputT] | None = None,
    ):
        """Initialize the multi-agent workflow.

        Args:
            agents: List of agent specifications
            execution_mode: How to execute agents
            aggregation: How to aggregate results
            executor: Custom agent executor (uses default if None)
            aggregator: Custom result aggregator (uses default if None)
        """
        self.agents = {a.name: a for a in agents}
        self.execution_mode = execution_mode
        self.aggregation = aggregation or AggregationSpec()
        self.executor = executor
        self.aggregator = aggregator

        # Validate DAG if using DAG mode
        if execution_mode == ExecutionMode.DAG:
            self._validate_dag()

    def _validate_dag(self) -> None:
        """Validate that agent dependencies form a valid DAG (no cycles)."""
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(name: str) -> bool:
            visited.add(name)
            rec_stack.add(name)

            agent = self.agents.get(name)
            if agent:
                for dep in agent.dependencies:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(name)
            return False

        for name in self.agents:
            if name not in visited:
                if has_cycle(name):
                    raise ValueError(f"Circular dependency detected involving agent: {name}")

    async def execute(
        self,
        input: InputT,
        context: dict[str, Any] | None = None,
    ) -> WorkflowResult[OutputT]:
        """Execute the multi-agent workflow.

        Args:
            input: Input data for agents
            context: Additional context for execution

        Returns:
            WorkflowResult with agent results and aggregated output
        """
        start_time = time.time()
        context = context or {}
        results: dict[str, AgentExecutionResult] = {}
        execution_order: list[str] = []

        if self.execution_mode == ExecutionMode.SEQUENTIAL:
            execution_order = list(self.agents.keys())
            for name in execution_order:
                result = await self._execute_agent(name, input, context, results)
                results[name] = result

        elif self.execution_mode == ExecutionMode.PARALLEL:
            execution_order = list(self.agents.keys())
            tasks = [self._execute_agent(name, input, context, {}) for name in execution_order]
            outputs = await asyncio.gather(*tasks, return_exceptions=True)
            for name, output in zip(execution_order, outputs):
                if isinstance(output, BaseException):
                    results[name] = AgentExecutionResult(
                        agent_name=name,
                        status=ExecutionStatus.FAILED,
                        error=str(output),
                    )
                else:
                    results[name] = output  # type: ignore[assignment]

        elif self.execution_mode == ExecutionMode.DAG:
            execution_order = await self._execute_dag(input, context, results)

        elif self.execution_mode == ExecutionMode.CONDITIONAL:
            execution_order = [
                name for name, spec in self.agents.items() if spec.is_relevant(context)
            ]
            tasks = [self._execute_agent(name, input, context, {}) for name in execution_order]
            outputs = await asyncio.gather(*tasks, return_exceptions=True)
            for name, output in zip(execution_order, outputs):
                if isinstance(output, BaseException):
                    results[name] = AgentExecutionResult(
                        agent_name=name,
                        status=ExecutionStatus.FAILED,
                        error=str(output),
                    )
                else:
                    results[name] = output  # type: ignore[assignment]

        # Aggregate results
        aggregated = self._aggregate_results(results)
        errors = {name: result.error for name, result in results.items() if result.error}
        timing = {name: result.duration_seconds for name, result in results.items()}

        return WorkflowResult(
            success=len(errors) == 0,
            agent_results=results,
            aggregated_result=aggregated,
            execution_order=execution_order,
            errors=errors,
            timing=timing,
            total_duration_seconds=time.time() - start_time,
        )

    async def _execute_agent(
        self,
        name: str,
        input: InputT,
        context: dict[str, Any],
        completed_results: dict[str, AgentExecutionResult],
    ) -> AgentExecutionResult:
        """Execute a single agent with timeout and error handling."""
        spec = self.agents[name]
        start_time = time.time()

        # Check condition
        if not spec.is_relevant(context):
            return AgentExecutionResult(
                agent_name=name,
                status=ExecutionStatus.SKIPPED,
                duration_seconds=0.0,
                metadata={"reason": "condition_not_met"},
            )

        try:
            # Execute with timeout
            if self.executor:
                result = await asyncio.wait_for(
                    self.executor.execute(spec.agent, input, context),
                    timeout=spec.timeout_seconds,
                )
                if result.is_ok():
                    output = result.unwrap()
                else:
                    from dawn_kestrel.core.result import Err
                    error_msg = result.error if isinstance(result, Err) else "Unknown error"
                    return AgentExecutionResult(
                        agent_name=name,
                        status=ExecutionStatus.FAILED,
                        error=error_msg,
                        duration_seconds=time.time() - start_time,
                    )
            else:
                # Default execution: call agent's run method
                output = await asyncio.wait_for(
                    spec.agent.run(input, context),
                    timeout=spec.timeout_seconds,
                )

            return AgentExecutionResult(
                agent_name=name,
                status=ExecutionStatus.COMPLETED,
                output=output,
                duration_seconds=time.time() - start_time,
            )

        except asyncio.TimeoutError:
            return AgentExecutionResult(
                agent_name=name,
                status=ExecutionStatus.FAILED,
                error=f"Timeout after {spec.timeout_seconds}s",
                duration_seconds=spec.timeout_seconds,
            )
        except Exception as e:
            logger.exception(f"Agent {name} failed")
            return AgentExecutionResult(
                agent_name=name,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    async def _execute_dag(
        self,
        input: InputT,
        context: dict[str, Any],
        results: dict[str, AgentExecutionResult],
    ) -> list[str]:
        """Execute agents in DAG order (topological sort).

        Agents with no dependencies run first, then agents that
        depend on them, and so on.
        """
        completed: set[str] = set()
        execution_order: list[str] = []

        while len(completed) < len(self.agents):
            # Find agents ready to execute (all dependencies satisfied)
            ready = [
                name
                for name, spec in self.agents.items()
                if name not in completed
                and all(dep in completed for dep in spec.dependencies)
                and spec.is_relevant(context)
            ]

            if not ready:
                # Deadlock or circular dependency (should be caught by validation)
                remaining = set(self.agents.keys()) - completed
                for name in remaining:
                    results[name] = AgentExecutionResult(
                        agent_name=name,
                        status=ExecutionStatus.SKIPPED,
                        metadata={"reason": "dependency_not_satisfied"},
                    )
                break

            # Execute ready agents in parallel
            tasks = [self._execute_agent(name, input, context, results) for name in ready]
            outputs = await asyncio.gather(*tasks, return_exceptions=True)

            for name, output in zip(ready, outputs):
                completed.add(name)
                execution_order.append(name)
                if isinstance(output, BaseException):
                    results[name] = AgentExecutionResult(
                        agent_name=name,
                        status=ExecutionStatus.FAILED,
                        error=str(output),
                    )
                else:
                    # Output is AgentExecutionResult, not raw output
                    results[name] = output  # type: ignore[assignment]
        return execution_order

    def _aggregate_results(
        self,
        results: dict[str, AgentExecutionResult],
    ) -> OutputT | None:
        """Aggregate results based on aggregation spec."""
        if self.aggregator:
            return self.aggregator.aggregate(results, self.aggregation)

        # Default aggregation strategies
        successful_results = {
            name: result.output
            for name, result in results.items()
            if result.is_success and result.output is not None
        }

        if not successful_results:
            return None

        if self.aggregation.strategy == AggregationStrategy.FIRST_SUCCESS:
            return next(iter(successful_results.values()))

        elif self.aggregation.strategy == AggregationStrategy.MERGE:
            # Merge all results into a dict
            # dict values are OutputT from each agent - heterogeneous
            return {"results": successful_results}  # type: ignore[return-value]
        elif self.aggregation.strategy == AggregationStrategy.WEIGHTED:
            # Return weighted combination
            weights = self.aggregation.weights
            total_weight = sum(weights.get(name, 1.0) for name in successful_results)
            return {
                "weighted_results": {
                    name: {"result": result, "weight": weights.get(name, 1.0) / total_weight}
                    for name, result in successful_results.items()
                }
            }  # type: ignore[return-value]
            # Heterogeneous dict output - structure depends on agents
        return {"results": successful_results}  # type: ignore[return-value]


class FindingsAggregator:
    """Aggregator specialized for merging findings from multiple agents.

    This implements the pattern from iron-rook's PRReviewOrchestrator:
    - Collect all findings
    - Deduplicate by hash
    - Resolve conflicts by severity
    """

    def aggregate(
        self,
        results: dict[str, AgentExecutionResult],
        spec: AggregationSpec,
    ) -> dict[str, Any]:
        """Aggregate findings from multiple agents."""
        all_findings: list[Any] = []

        for name, result in results.items():
            if result.is_success and result.output:
                output = result.output
                if isinstance(output, dict) and "findings" in output:
                    all_findings.extend(output["findings"])
                elif isinstance(output, list):
                    all_findings.extend(output)

        # Deduplicate findings (by hash if available)
        unique_findings = self._deduplicate_findings(all_findings)

        # Resolve conflicts
        if spec.conflict_resolution == ConflictResolution.HIGHEST_SEVERITY:
            unique_findings = self._resolve_by_severity(unique_findings)

        return {
            "findings": unique_findings,
            "total_count": len(unique_findings),
            "sources": list(results.keys()),
        }

    def _deduplicate_findings(self, findings: list[Any]) -> list[Any]:
        """Remove duplicate findings based on hash or ID."""
        seen: set[str] = set()
        unique: list[Any] = []

        for finding in findings:
            # Try to get a unique identifier
            if isinstance(finding, dict):
                identifier: str = (
                    finding.get("id")
                    or finding.get("hash")
                    or finding.get("fingerprint")
                    or str(finding)
                ) or str(finding)
            else:
                identifier = str(finding)

            if identifier not in seen:
                seen.add(identifier)
                unique.append(finding)

        return unique

    def _resolve_by_severity(self, findings: list[Any]) -> list[Any]:
        """Resolve conflicts by keeping highest severity."""
        # Group by location/code
        groups: dict[str, list[Any]] = {}
        for finding in findings:
            if isinstance(finding, dict):
                key = finding.get("location") or finding.get("code") or str(finding)
            else:
                key = str(finding)
            groups.setdefault(key, []).append(finding)

        # Keep highest severity from each group
        resolved: list[Any] = []
        severity_order = ["critical", "high", "medium", "low", "info"]

        for group_findings in groups.values():
            if len(group_findings) == 1:
                resolved.append(group_findings[0])
            else:
                # Sort by severity
                sorted_findings = sorted(
                    group_findings,
                    key=lambda f: (
                        severity_order.index(
                            f.get("severity", "info") if isinstance(f, dict) else "info"
                        )
                        if isinstance(f, dict)
                        else 99
                    ),
                )
                resolved.append(sorted_findings[0])

        return resolved


__all__ = [
    "ExecutionMode",
    "ExecutionStatus",
    "AggregationStrategy",
    "ConflictResolution",
    "AgentSpec",
    "AggregationSpec",
    "AgentExecutionResult",
    "WorkflowResult",
    "AgentExecutor",
    "ResultAggregator",
    "MultiAgentWorkflow",
    "FindingsAggregator",
]
