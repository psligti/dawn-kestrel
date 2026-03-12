"""Delegation Engine module for multi-agent task delegation.

Provides the DelegationEngine class for executing delegation trees with
BFS (breadth-first), DFS (depth-first), or adaptive traversal strategies.
Includes boundary enforcement, convergence detection, and callback support.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING, Any

from dawn_kestrel.core.result import Err, Ok, Result
from dawn_kestrel.reliability.queue_worker import (
    InMemoryTaskQueue,
    Task,
    WorkerPool,
)

from .convergence import ConvergenceTracker
from .types import (
    DelegationConfig,
    DelegationContext,
    DelegationResult,
    DelegationStopReason,
    TraversalMode,
)

if TYPE_CHECKING:
    from dawn_kestrel.agents.registry import AgentRegistry
    from dawn_kestrel.agents.runtime import AgentRuntime
    from dawn_kestrel.policy.delegation import DelegationPolicy


class DelegationEngine:
    """Convergence-aware delegation engine with BFS/DFS strategies.

    Executes multi-agent delegation trees with configurable traversal modes,
    boundary enforcement, and convergence detection.

    Attributes:
        config: Delegation configuration (mode, budget, callbacks).
        runtime: Agent runtime for executing agents.
        registry: Agent registry for fetching agent definitions.
        _context: Current delegation context (state tracking).
        _convergence: Convergence tracker for novelty detection.
        _lock: asyncio.Lock for thread-safe context updates in BFS.
    """

    def __init__(
        self,
        config: DelegationConfig,
        agent_runtime: "AgentRuntime",
        agent_registry: "AgentRegistry",
        policy: "DelegationPolicy | None" = None,
    ):
        """Initialize the delegation engine.

        Args:
            config: Delegation configuration.
            agent_runtime: Runtime for executing agents.
            agent_registry: Registry for fetching agent definitions.
        """
        self.config = config
        self.runtime = agent_runtime
        self.registry = agent_registry
        self.policy = policy
        self._context: DelegationContext | None = None
        self._convergence = ConvergenceTracker(config.evidence_keys)
        self._lock = asyncio.Lock()

    def _get_context(self) -> DelegationContext:
        """Get the current delegation context, asserting it is initialized."""
        assert self._context is not None, "Context not initialized - call delegate() first"
        return self._context
    async def delegate(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: Any,
        tools: Any | None = None,
        children: list[dict[str, Any]] | None = None,
    ) -> Result[DelegationResult]:
        """Execute a delegation tree starting from the given agent.

        Args:
            agent_name: Name of the root agent to execute.
            prompt: Initial prompt for the agent.
            session_id: Session ID for execution.
            session_manager: Session manager for message handling.
            tools: Tool registry for the agent.
            children: Optional list of child delegations to spawn.
                     [{"agent": "explore", "prompt": "..."}, ...]

        Returns:
            Result containing DelegationResult or error.
        """
        async with self._lock:
            self._context = DelegationContext(root_task_id=str(uuid.uuid4()))

        try:
            # Execute based on traversal mode
            if self.config.mode == TraversalMode.BFS:
                await self._execute_bfs(
                    agent_name, prompt, session_id, session_manager, tools, children
                )
            elif self.config.mode == TraversalMode.DFS:
                await self._execute_dfs(
                    agent_name, prompt, session_id, session_manager, tools, children
                )
            else:  # ADAPTIVE
                await self._execute_adaptive(
                    agent_name, prompt, session_id, session_manager, tools, children
                )
        except Exception as e:
            return Err(error=str(e), code="DELEGATION_ERROR")

        return Ok(self._build_result(DelegationStopReason.COMPLETED))

    async def _execute_bfs(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: Any,
        tools: Any | None,
        children: list[dict[str, Any]] | None,
    ) -> None:
        """Breadth-first execution with queue-based concurrency control.

        Uses a queue and worker pool to limit concurrent subtask executions,
        preventing provider timeout issues from too many parallel requests.

        Args:
            agent_name: Name of the agent to execute.
            prompt: Prompt for the agent.
            session_id: Session ID for execution.
            session_manager: Session manager.
            tools: Tool registry.
            children: List of child delegations.
        """
        root_result = await self._execute_agent(
            agent_name, prompt, session_id, session_manager, tools
        )

        if isinstance(root_result, Exception):
            self._get_context().errors.append(root_result)
        else:
            self._get_context().results.append(root_result)
            if self.config.check_convergence:
                self._convergence.check_novelty([root_result])

        boundary_check = self._check_boundaries()
        if boundary_check:
            return

        if not children:
            return

        if len(children) > self.config.budget.max_breadth:
            children = children[: self.config.budget.max_breadth]

        if self._get_context().current_depth + 1 >= self.config.budget.max_depth:
            return

        self._get_context().current_depth += 1

        agents_remaining = self.config.budget.max_total_agents - self._get_context().total_agents_spawned
        if agents_remaining <= 0:
            return
        children = children[:agents_remaining]

        # Queue-based execution with limited concurrency
        await self._execute_children_queued(children, session_id, session_manager, tools)

    async def _execute_children_queued(
        self,
        children: list[dict[str, Any]],
        session_id: str,
        session_manager: Any,
        tools: Any | None,
    ) -> None:
        """Execute children using queue/worker pattern with concurrency limit.

        This prevents provider timeout issues by limiting how many subtasks
        run concurrently. Tasks wait in queue until a worker slot is available.

        Args:
            children: List of child delegation specs.
            session_id: Session ID for execution.
            session_manager: Session manager.
            tools: Tool registry.
        """
        queue = InMemoryTaskQueue()
        results_map: dict[str, Any] = {}
        results_lock = asyncio.Lock()

        async def process_child_task(task: Task) -> Result[Any]:
            child_spec = task.payload["child_spec"]
            child_name = child_spec.get("agent", "general")
            child_prompt = child_spec.get("prompt", "")

            result = await self._execute_agent(
                child_name, child_prompt, session_id, session_manager, tools
            )

            async with results_lock:
                results_map[task.id] = result

            if isinstance(result, Exception):
                return Err(str(result), code="AGENT_ERROR")
            return Ok(result)

        # Create worker pool with limited concurrency
        max_workers = self.config.budget.max_concurrent
        pool = WorkerPool(
            queue=queue,
            processor=process_child_task,
            num_workers=max_workers,
            poll_interval=0.05,
        )

        # Enqueue all children
        for child in children:
            child_task = Task(
                id=f"child_{uuid.uuid4().hex[:8]}",
                type="delegation_child",
                payload={"child_spec": child},
            )
            await queue.enqueue(child_task)

        # Start pool, wait for completion, then stop
        await pool.start()

        try:
            await pool.wait_for_completion(timeout=self.config.budget.max_wall_time_seconds)
        finally:
            await pool.stop()

        # Collect results
        for task_id, result in results_map.items():
            if isinstance(result, Exception):
                self._get_context().errors.append(result)
            else:
                self._get_context().results.append(result)
                if self.config.check_convergence:
                    self._convergence.check_novelty([result])

        if self.config.check_convergence:
            if self._convergence.is_converged(self.config.budget.stagnation_threshold):
                return

    async def _execute_dfs(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: Any,
        tools: Any | None,
        children: list[dict[str, Any]] | None,
    ) -> None:
        """Depth-first execution: fully explore each branch before siblings.

        Args:
            agent_name: Name of the agent to execute.
            prompt: Prompt for the agent.
            session_id: Session ID for execution.
            session_manager: Session manager.
            tools: Tool registry.
            children: List of child delegations.
        """
        # Execute root/current agent first (don't check boundaries before any work)
        root_result = await self._execute_agent(
            agent_name, prompt, session_id, session_manager, tools
        )

        if isinstance(root_result, Exception):
            self._get_context().errors.append(root_result)
        else:
            self._get_context().results.append(root_result)
            # Check novelty for this result
            if self.config.check_convergence:
                self._convergence.check_novelty([root_result])

        # Check boundaries after execution
        boundary_check = self._check_boundaries()
        if boundary_check:
            return

        if not children:
            return

        # Check depth limit BEFORE incrementing - can we go deeper?
        if self._get_context().current_depth + 1 >= self.config.budget.max_depth:
            return

        # Increment depth for children
        self._get_context().current_depth += 1

        try:
            # Execute children sequentially
            for child in children:
                # Check if we've hit the agent limit
                if self._get_context().total_agents_spawned >= self.config.budget.max_total_agents:
                    break

                # Check boundaries before each child
                boundary_check = self._check_boundaries()
                if boundary_check:
                    return

                child_name = child.get("agent", "general")
                child_prompt = child.get("prompt", "")
                child_children = child.get("children")

                try:
                    result = await self._execute_agent(
                        child_name, child_prompt, session_id, session_manager, tools
                    )

                    if isinstance(result, Exception):
                        self._get_context().errors.append(result)
                    else:
                        self._get_context().results.append(result)
                        # Check novelty for this result
                        if self.config.check_convergence:
                            self._convergence.check_novelty([result])

                    # Recursively delegate to grandchildren
                    if child_children:
                        await self._execute_dfs(
                            child_name,
                            child_prompt,
                            session_id,
                            session_manager,
                            tools,
                            child_children,
                        )

                    # Check convergence after each branch
                    if self.config.check_convergence:
                        if self._convergence.is_converged(self.config.budget.stagnation_threshold):
                            return  # Early termination on convergence

                except Exception as e:
                    self._get_context().errors.append(e)
        finally:
            # Decrement depth when returning
            self._get_context().current_depth -= 1

    async def _execute_adaptive(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: Any,
        tools: Any | None,
        children: list[dict[str, Any]] | None,
    ) -> None:
        """Adaptive execution: BFS for shallow, DFS for deep exploration.

        Strategy:
        - Use BFS at depth 0-1 (parallel exploration)
        - Use DFS at depth 2+ (focused deep-dive)

        Args:
            agent_name: Name of the agent to execute.
            prompt: Prompt for the agent.
            session_id: Session ID for execution.
            session_manager: Session manager.
            tools: Tool registry.
            children: List of child delegations.
        """
        if self._get_context().current_depth < 2:
            await self._execute_bfs(
                agent_name, prompt, session_id, session_manager, tools, children
            )
        else:
            await self._execute_dfs(
                agent_name, prompt, session_id, session_manager, tools, children
            )

    async def _execute_agent(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: Any,
        tools: Any | None,
    ) -> Any:
        """Execute a single agent and track metrics.

        Args:
            agent_name: Name of the agent to execute.
            prompt: Prompt for the agent.
            session_id: Session ID for execution.
            session_manager: Session manager.
            tools: Tool registry.

        Returns:
            The agent execution result or exception.
        """
        self._get_context().total_agents_spawned += 1
        self._get_context().active_agents += 1

        agent_id = f"{agent_name}_{self._get_context().total_agents_spawned}_{uuid.uuid4().hex[:8]}"

        if self.config.on_agent_spawn:
            await self.config.on_agent_spawn(agent_id, self._get_context().current_depth)

        try:
            result = await self.runtime.execute_agent(
                agent_name=agent_name,
                session_id=session_id,
                user_message=prompt,
                session_manager=session_manager,
                tools=tools,
                skills=[],
            )

            if self.config.on_agent_complete:
                await self.config.on_agent_complete(agent_id, result)

            return result

        except Exception as e:
            # Record exception and return it
            return e
        finally:
            self._get_context().active_agents -= 1
            self._get_context().completed_agents += 1

    def _check_boundaries(self) -> DelegationStopReason | None:
        """Check if any boundary has been exceeded.

        Returns:
            StopReason if boundary exceeded, None if OK to continue.
        """
        budget = self.config.budget

        if self._get_context().iteration_count >= budget.max_iterations:
            return DelegationStopReason.BUDGET_EXHAUSTED

        if self._get_context().elapsed_seconds() >= budget.max_wall_time_seconds:
            return DelegationStopReason.TIMEOUT

        if self._get_context().current_depth >= budget.max_depth:
            return DelegationStopReason.DEPTH_LIMIT

        if self._get_context().total_agents_spawned >= budget.max_total_agents:
            return DelegationStopReason.BREADTH_LIMIT

        if self._convergence.is_converged(budget.stagnation_threshold):
            return DelegationStopReason.CONVERGED

        return None

    def _build_result(self, stop_reason: DelegationStopReason) -> DelegationResult:
        """Build final delegation result.

        Args:
            stop_reason: Reason for stopping delegation.

        Returns:
            DelegationResult with execution summary.
        """
        return DelegationResult(
            success=len(self._get_context().errors) == 0,
            stop_reason=stop_reason,
            results=self._get_context().results,
            errors=self._get_context().errors,
            total_agents=self._get_context().total_agents_spawned,
            max_depth_reached=self._get_context().current_depth,
            elapsed_seconds=self._get_context().elapsed_seconds(),
            iterations=self._get_context().iteration_count,
            converged=self._convergence.is_converged(self.config.budget.stagnation_threshold),
            stagnation_detected=self._convergence.stagnation_count > 0,
            final_novelty_signature=self._convergence.signatures[-1]
            if self._convergence.signatures
            else None,
        )

    async def delegate_with_policy(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: Any,
        tools: Any | None = None,
        policy: "DelegationPolicy | None" = None,
    ) -> Result[DelegationResult]:
        """Execute delegation using policy-driven decisions.

        This method uses a DelegationPolicy to decide:
        - When to create subtasks
        - Which agents to delegate to
        - When to stop delegating

        Args:
            agent_name: Name of the root agent.
            prompt: Initial prompt for the agent.
            session_id: Session ID for execution.
            session_manager: Session manager for message handling.
            tools: Tool registry for the agent.
            policy: Optional policy override (uses self.policy if None).

        Returns:
            Result containing DelegationResult or error.
        """
        from dawn_kestrel.policy.delegation import (
            DelegationContext as PolicyContext,
            DelegationDecision,
            DelegationOutput,
        )

        active_policy = policy or self.policy
        if active_policy is None:
            return Err(
                error="No policy configured - pass policy to constructor or delegate_with_policy()",
                code="POLICY_REQUIRED",
            )

        async with self._lock:
            self._context = DelegationContext(root_task_id=str(uuid.uuid4()))

        policy_ctx = PolicyContext(
            current_agent=agent_name,
            current_depth=0,
            max_depth=self.config.budget.max_depth,
            max_iterations=self.config.budget.max_iterations,
            max_cost_usd=1.0,
            max_seconds=self.config.budget.max_wall_time_seconds,
            stagnation_threshold=self.config.budget.stagnation_threshold,
        )

        try:
            iteration = 0
            while True:
                output: DelegationOutput = active_policy.evaluate(policy_ctx)

                if output.decision == DelegationDecision.DONE:
                    break

                elif output.decision == DelegationDecision.CONTINUE:
                    result = await self._execute_agent(
                        agent_name, prompt, session_id, session_manager, tools
                    )
                    if isinstance(result, Exception):
                        self._get_context().errors.append(result)
                    else:
                        self._get_context().results.append(result)

                elif output.decision == DelegationDecision.DELEGATE:
                    for subtask in output.subtasks:
                        if policy_ctx.current_depth >= policy_ctx.max_depth:
                            break
                        child_result = await self._execute_agent(
                            subtask.agent, subtask.prompt, session_id, session_manager, tools
                        )
                        if isinstance(child_result, Exception):
                            self._get_context().errors.append(child_result)
                        else:
                            self._get_context().results.append(child_result)
                            policy_ctx.accumulated_results.append(child_result)

                    policy_ctx.current_depth += 1

                elif output.decision == DelegationDecision.SYNTHESIZE:
                    pass

                policy_ctx.iteration_count = iteration
                iteration += 1

                if iteration >= self.config.budget.max_iterations:
                    break

        except Exception as e:
            return Err(error=str(e), code="DELEGATION_ERROR")

        return Ok(self._build_result(DelegationStopReason.COMPLETED))
