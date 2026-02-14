"""Delegation Engine module for multi-agent task delegation.

Provides the DelegationEngine class for executing delegation trees with
BFS (breadth-first), DFS (depth-first), or adaptive traversal strategies.
Includes boundary enforcement, convergence detection, and callback support.
"""

import asyncio
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from dawn_kestrel.core.result import Err, Ok, Result

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
        self._context: Optional[DelegationContext] = None
        self._convergence = ConvergenceTracker(config.evidence_keys)
        self._lock = asyncio.Lock()

    async def delegate(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: Any,
        tools: Optional[Any] = None,
        children: Optional[List[Dict[str, Any]]] = None,
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
        tools: Optional[Any],
        children: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Breadth-first execution: spawn all children in parallel.

        Args:
            agent_name: Name of the agent to execute.
            prompt: Prompt for the agent.
            session_id: Session ID for execution.
            session_manager: Session manager.
            tools: Tool registry.
            children: List of child delegations.
        """
        # Execute root agent first (don't check timeout before any work is done)
        root_result = await self._execute_agent(
            agent_name, prompt, session_id, session_manager, tools
        )

        # Record root result
        if isinstance(root_result, Exception):
            self._context.errors.append(root_result)
        else:
            self._context.results.append(root_result)
            # Check novelty for root result to build stagnation tracking
            if self.config.check_convergence:
                self._convergence.check_novelty([root_result])

        # Check boundaries after root execution (timeout, etc.)
        boundary_check = self._check_boundaries()
        if boundary_check:
            return  # Stop delegation

        if not children:
            return  # No children to delegate to

        # Check breadth limit
        if len(children) > self.config.budget.max_breadth:
            children = children[: self.config.budget.max_breadth]

        # Check depth limit BEFORE incrementing - can we go deeper?
        if self._context.current_depth + 1 >= self.config.budget.max_depth:
            return  # Depth limit would be reached

        # Increment depth for children
        self._context.current_depth += 1

        # Calculate how many children we can spawn (pre-check to avoid over-spawning)
        # This is necessary because tasks are created synchronously before execution
        agents_remaining = self.config.budget.max_total_agents - self._context.total_agents_spawned
        if agents_remaining <= 0:
            return
        children = children[:agents_remaining]

        # Spawn all children in parallel
        tasks = []
        for child in children:
            child_name = child.get("agent", "general")
            child_prompt = child.get("prompt", "")

            tasks.append(
                self._execute_agent(child_name, child_prompt, session_id, session_manager, tools)
            )

        # Execute all in parallel with exception handling
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    self._context.errors.append(result)
                else:
                    self._context.results.append(result)
                    # Check novelty for each result individually to detect identical results
                    if self.config.check_convergence:
                        self._convergence.check_novelty([result])

            # Check convergence after all children complete
            if self.config.check_convergence:
                if self._convergence.is_converged(self.config.budget.stagnation_threshold):
                    return  # Converged

    async def _execute_dfs(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: Any,
        tools: Optional[Any],
        children: Optional[List[Dict[str, Any]]],
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
            self._context.errors.append(root_result)
        else:
            self._context.results.append(root_result)
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
        if self._context.current_depth + 1 >= self.config.budget.max_depth:
            return

        # Increment depth for children
        self._context.current_depth += 1

        try:
            # Execute children sequentially
            for child in children:
                # Check if we've hit the agent limit
                if self._context.total_agents_spawned >= self.config.budget.max_total_agents:
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
                        self._context.errors.append(result)
                    else:
                        self._context.results.append(result)
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
                    self._context.errors.append(e)
        finally:
            # Decrement depth when returning
            self._context.current_depth -= 1

    async def _execute_adaptive(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: Any,
        tools: Optional[Any],
        children: Optional[List[Dict[str, Any]]],
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
        if self._context.current_depth < 2:
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
        tools: Optional[Any],
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
        self._context.total_agents_spawned += 1
        self._context.active_agents += 1

        agent_id = f"{agent_name}_{self._context.total_agents_spawned}_{uuid.uuid4().hex[:8]}"

        if self.config.on_agent_spawn:
            await self.config.on_agent_spawn(agent_id, self._context.current_depth)

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
            self._context.active_agents -= 1
            self._context.completed_agents += 1

    def _check_boundaries(self) -> Optional[DelegationStopReason]:
        """Check if any boundary has been exceeded.

        Returns:
            StopReason if boundary exceeded, None if OK to continue.
        """
        budget = self.config.budget

        if self._context.iteration_count >= budget.max_iterations:
            return DelegationStopReason.BUDGET_EXHAUSTED

        if self._context.elapsed_seconds() >= budget.max_wall_time_seconds:
            return DelegationStopReason.TIMEOUT

        if self._context.current_depth >= budget.max_depth:
            return DelegationStopReason.DEPTH_LIMIT

        if self._context.total_agents_spawned >= budget.max_total_agents:
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
            success=len(self._context.errors) == 0,
            stop_reason=stop_reason,
            results=self._context.results,
            errors=self._context.errors,
            total_agents=self._context.total_agents_spawned,
            max_depth_reached=self._context.current_depth,
            elapsed_seconds=self._context.elapsed_seconds(),
            iterations=self._context.iteration_count,
            converged=self._convergence.is_converged(self.config.budget.stagnation_threshold),
            stagnation_detected=self._convergence.stagnation_count > 0,
            final_novelty_signature=self._convergence.signatures[-1]
            if self._convergence.signatures
            else None,
        )
