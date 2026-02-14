# Delegation Engine Design

## Overview

A convergence-aware delegation engine that enables agents to spawn subagents with guaranteed termination. Supports both breadth-first (parallel) and depth-first (sequential) delegation strategies with configurable boundaries.

## Key Requirements

1. **Convergence Guarantee** - Prevents infinite agent spawning through multiple mechanisms
2. **Traversal Strategies** - BFS (parallel) and DFS (sequential) execution modes
3. **Boundary Enforcement** - Hard limits on depth, breadth, time, and resources
4. **Integration** - Works with existing `AgentRuntime`, `AgentRegistry`, and `AgentTask`

## Synthesis of Codebase Patterns

### Existing Convergence Patterns (from `workflow_fsm.py`)

```python
# StopReason enum defines canonical termination causes
class StopReason(str, Enum):
    SUCCESS = "recommendation_ready"
    BUDGET_EXHAUSTED = "budget_exhausted"
    STAGNATION = "stagnation"
    HUMAN_REQUIRED = "human_required"
    BLOCKING_QUESTION = "blocking_question"

# Budget limits enforced as hard constraints
@dataclass
class WorkflowBudget:
    max_iterations: int = 10
    max_tool_calls: int = 100
    max_wall_time_seconds: float = 600.0
    max_subagent_calls: int = 20

# Novelty detection for stagnation
def compute_novelty_signature(self, evidence: List[str]) -> str:
    evidence_str = "|".join(sorted(evidence))
    return hashlib.sha256(evidence_str.encode()).hexdigest()

def update_evidence(self, new_evidence: List[str]) -> bool:
    signature = self.compute_novelty_signature(new_evidence + self.evidence)
    if signature == self.last_novelty_signature:
        self.stagnation_count += 1
        return False  # No new information
    self.evidence.extend(new_evidence)
    self.last_novelty_signature = signature
    self.stagnation_count = 0
    return True  # Novelty detected
```

### Existing Delegation Patterns (from `orchestrator.py`)

```python
# Parallel delegation via asyncio.gather
async def run_parallel(
    self,
    tasks: List[AgentTask],
    session_id: str,
    user_messages: List[str],
    session_manager: SessionManagerLike,
    tools_list,
    session,
) -> List[str]:
    coroutines = [
        self.delegate_task(task=tasks[i], ...)
        for i in range(len(tasks))
    ]
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    return task_ids

# Single task delegation
async def delegate_task(
    self,
    task: AgentTask,
    session_id: str,
    user_message: str,
    session_manager: SessionManagerLike,
    tools: Optional[ToolRegistry],
    session: Session,
) -> str:
    # Creates agent, executes, tracks result
```

### Existing Boundary Patterns (from `bulkhead.py`)

```python
# Concurrency limiting via semaphores
class BulkheadImpl:
    def set_limit(self, resource: str, max_concurrent: int) -> None:
        self._limits[resource] = max_concurrent
        self._semaphores[resource] = asyncio.Semaphore(max_concurrent)
    
    async def try_execute(
        self,
        resource: str,
        func: Callable[..., Any],
        max_concurrent: int | None = None,
    ) -> Result[Any]:
        # Acquire semaphore, execute, release
```

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DelegationEngine                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Config    │  │  Context    │  │  ConvergenceTracker │ │
│  │ - mode      │  │ - depth     │  │ - novelty_signature │ │
│  │ - budget    │  │ - breadth   │  │ - stagnation_count  │ │
│  │ - policy    │  │ - results   │  │ - evidence_hash     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Strategy (BFS/DFS/Adaptive)              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │   BFS      │  │    DFS     │  │    Adaptive    │  │  │
│  │  │ (parallel) │  │ (sequential│  │  (hybrid)      │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  Boundary Enforcer                    │  │
│  │  - max_depth: int                                      │  │
│  │  - max_breadth: int (concurrent agents)               │  │
│  │  - max_total_agents: int (cumulative spawn limit)     │  │
│  │  - max_wall_time: float (timeout)                     │  │
│  │  - stagnation_threshold: int                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   AgentRuntime/Registry                      │
│  (existing infrastructure - no modifications needed)         │
└─────────────────────────────────────────────────────────────┘
```

## Core Interfaces

```python
from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict, Any, Callable, Awaitable
from enum import Enum
import hashlib
import asyncio
from datetime import datetime

class TraversalMode(str, Enum):
    BFS = "breadth_first"  # Parallel execution
    DFS = "depth_first"    # Sequential execution
    ADAPTIVE = "adaptive"  # Hybrid based on context


class DelegationStopReason(str, Enum):
    COMPLETED = "completed"           # All tasks finished
    CONVERGED = "converged"           # Results stabilized
    BUDGET_EXHAUSTED = "budget"       # Hit resource limits
    STAGNATION = "stagnation"         # No new information
    DEPTH_LIMIT = "depth_limit"       # Max recursion depth
    BREADTH_LIMIT = "breadth_limit"   # Max concurrent agents
    TIMEOUT = "timeout"               # Wall time exceeded
    ERROR = "error"                   # Unrecoverable error


@dataclass
class DelegationBudget:
    """Hard limits enforced by the engine."""
    max_depth: int = 3
    """Maximum delegation depth (root=0, children=1, grandchildren=2...)."""
    
    max_breadth: int = 5
    """Maximum concurrent agents at any level."""
    
    max_total_agents: int = 20
    """Cumulative agent spawn limit across entire delegation tree."""
    
    max_wall_time_seconds: float = 300.0
    """Maximum total execution time."""
    
    max_iterations: int = 10
    """Maximum delegation cycles before forced stop."""
    
    stagnation_threshold: int = 3
    """Consecutive iterations without novelty before convergence declared."""


@dataclass
class DelegationConfig:
    """Configuration for a delegation engine instance."""
    mode: TraversalMode = TraversalMode.BFS
    budget: DelegationBudget = field(default_factory=DelegationBudget)
    
    # Convergence settings
    check_convergence: bool = True
    """Whether to check for convergence (novelty detection)."""
    
    evidence_keys: List[str] = field(default_factory=lambda: ["result", "findings"])
    """Keys to extract from agent results for novelty detection."""
    
    # Callbacks
    on_agent_spawn: Optional[Callable[[str, int], Awaitable[None]]] = None
    """Called when an agent is spawned (agent_id, depth)."""
    
    on_agent_complete: Optional[Callable[[str, Any], Awaitable[None]]] = None
    """Called when an agent completes (agent_id, result)."""
    
    on_convergence_check: Optional[Callable[[List[Any]], Awaitable[bool]]] = None
    """Custom convergence check function."""


@dataclass
class DelegationContext:
    """Runtime context for an active delegation."""
    root_task_id: str
    current_depth: int = 0
    total_agents_spawned: int = 0
    active_agents: int = 0
    completed_agents: int = 0
    results: List[Any] = field(default_factory=list)
    errors: List[Exception] = field(default_factory=list)
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    iteration_count: int = 0
    
    # Convergence tracking
    novelty_signatures: List[str] = field(default_factory=list)
    stagnation_count: int = 0
    
    def elapsed_seconds(self) -> float:
        return datetime.now().timestamp() - self.start_time


@dataclass
class DelegationResult:
    """Final result from a delegation."""
    success: bool
    stop_reason: DelegationStopReason
    results: List[Any]
    errors: List[Exception]
    
    # Statistics
    total_agents: int
    max_depth_reached: int
    elapsed_seconds: float
    iterations: int
    
    # Convergence info
    converged: bool
    stagnation_detected: bool
    final_novelty_signature: Optional[str] = None


class ConvergenceTracker:
    """Tracks evidence for convergence detection."""
    
    def __init__(self, evidence_keys: List[str]):
        self.evidence_keys = evidence_keys
        self.signatures: List[str] = []
        self.stagnation_count = 0
    
    def compute_signature(self, results: List[Any]) -> str:
        """Compute hash signature from results for novelty detection."""
        evidence_parts = []
        for result in results:
            if isinstance(result, dict):
                for key in self.evidence_keys:
                    if key in result:
                        value = result[key]
                        if isinstance(value, (list, dict)):
                            evidence_parts.append(str(sorted(value) if isinstance(value, list) else value))
                        else:
                            evidence_parts.append(str(value))
            else:
                evidence_parts.append(str(result))
        
        evidence_str = "|".join(sorted(evidence_parts))
        return hashlib.sha256(evidence_str.encode()).hexdigest()
    
    def check_novelty(self, results: List[Any]) -> bool:
        """Check if results contain new information.
        
        Returns:
            True if novel (new information), False if stagnant.
        """
        if not results:
            return False
            
        new_signature = self.compute_signature(results)
        
        if self.signatures and new_signature == self.signatures[-1]:
            self.stagnation_count += 1
            return False
        
        self.signatures.append(new_signature)
        self.stagnation_count = 0
        return True
    
    def is_converged(self, threshold: int) -> bool:
        """Check if convergence has been achieved."""
        return self.stagnation_count >= threshold
```

## Delegation Engine Implementation

```python
from dawn_kestrel.agents.runtime import AgentRuntime
from dawn_kestrel.agents.registry import AgentRegistry
from dawn_kestrel.core.result import Result, Ok, Err
from dawn_kestrel.agents.orchestrator import AgentOrchestrator

class DelegationEngine:
    """Convergence-aware delegation engine with BFS/DFS strategies."""
    
    def __init__(
        self,
        config: DelegationConfig,
        agent_runtime: AgentRuntime,
        agent_registry: AgentRegistry,
    ):
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
        session_manager: "SessionManagerLike",
        tools: Optional["ToolRegistry"] = None,
        children: Optional[List[Dict[str, Any]]] = None,
    ) -> Result[DelegationResult]:
        """Execute a delegation tree starting from the given agent.
        
        Args:
            agent_name: Name of the root agent to execute
            prompt: Initial prompt for the agent
            session_id: Session ID for execution
            session_manager: Session manager for message handling
            tools: Tool registry for the agent
            children: Optional list of child delegations to spawn
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
        session_manager: "SessionManagerLike",
        tools: Optional["ToolRegistry"],
        children: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Breadth-first execution: spawn all children in parallel."""
        
        # Check boundaries before proceeding
        boundary_check = self._check_boundaries()
        if boundary_check:
            return  # Stop delegation
        
        # Execute root agent
        root_result = await self._execute_agent(
            agent_name, prompt, session_id, session_manager, tools
        )
        
        if not children:
            return  # No children to delegate to
        
        # Check breadth limit
        if len(children) > self.config.budget.max_breadth:
            children = children[:self.config.budget.max_breadth]
        
        # Check depth limit
        if self._context.current_depth >= self.config.budget.max_depth:
            return  # Depth limit reached
        
        # Increment depth for children
        self._context.current_depth += 1
        
        # Spawn all children in parallel
        tasks = []
        for child in children:
            if self._context.total_agents_spawned >= self.config.budget.max_total_agents:
                break
            
            child_name = child.get("agent", "general")
            child_prompt = child.get("prompt", "")
            
            tasks.append(self._execute_agent(
                child_name, child_prompt, session_id, session_manager, tools
            ))
        
        # Execute all in parallel with exception handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                self._context.errors.append(result)
            else:
                self._context.results.append(result)
        
        # Check convergence
        if self.config.check_convergence:
            self._convergence.check_novelty(self._context.results)
            if self._convergence.is_converged(self.config.budget.stagnation_threshold):
                return  # Converged
    
    async def _execute_dfs(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: "SessionManagerLike",
        tools: Optional["ToolRegistry"],
        children: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Depth-first execution: fully explore each branch before siblings."""
        
        # Check boundaries
        boundary_check = self._check_boundaries()
        if boundary_check:
            return
        
        # Execute root agent
        root_result = await self._execute_agent(
            agent_name, prompt, session_id, session_manager, tools
        )
        
        if not children:
            return
        
        # Check depth limit
        if self._context.current_depth >= self.config.budget.max_depth:
            return
        
        # Increment depth for children
        self._context.current_depth += 1
        
        # Execute children sequentially
        for child in children:
            if self._context.total_agents_spawned >= self.config.budget.max_total_agents:
                break
            
            child_name = child.get("agent", "general")
            child_prompt = child.get("prompt", "")
            child_children = child.get("children")
            
            try:
                result = await self._execute_agent(
                    child_name, child_prompt, session_id, session_manager, tools
                )
                self._context.results.append(result)
                
                # Recursively delegate to grandchildren
                if child_children:
                    await self._execute_dfs(
                        child_name, child_prompt, session_id, 
                        session_manager, tools, child_children
                    )
                
                # Check convergence after each branch
                if self.config.check_convergence:
                    self._convergence.check_novelty(self._context.results)
                    if self._convergence.is_converged(self.config.budget.stagnation_threshold):
                        return  # Early termination on convergence
                        
            except Exception as e:
                self._context.errors.append(e)
        
        # Decrement depth when returning
        self._context.current_depth -= 1
    
    async def _execute_adaptive(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        session_manager: "SessionManagerLike",
        tools: Optional["ToolRegistry"],
        children: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Adaptive execution: BFS for shallow, DFS for deep exploration.
        
        Strategy:
        - Use BFS at depth 0-1 (parallel exploration)
        - Use DFS at depth 2+ (focused deep-dive)
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
        session_manager: "SessionManagerLike",
        tools: Optional["ToolRegistry"],
    ) -> Any:
        """Execute a single agent and track metrics."""
        
        self._context.total_agents_spawned += 1
        self._context.active_agents += 1
        
        agent_id = f"{agent_name}_{self._context.total_agents_spawned}"
        
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
        """Build final delegation result."""
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
            final_novelty_signature=self._convergence.signatures[-1] if self._convergence.signatures else None,
        )
```

## Integration Points

### With Existing AgentRuntime

```python
# The delegation engine uses AgentRuntime.execute_agent() directly
# No modifications needed to existing runtime

engine = DelegationEngine(
    config=DelegationConfig(
        mode=TraversalMode.BFS,
        budget=DelegationBudget(max_depth=3, max_breadth=5),
    ),
    agent_runtime=runtime,  # Existing AgentRuntime instance
    agent_registry=registry,  # Existing AgentRegistry instance
)

result = await engine.delegate(
    agent_name="orchestrator",
    prompt="Analyze the codebase for security issues",
    session_id=session.id,
    session_manager=session_manager,
    children=[
        {"agent": "explore", "prompt": "Find auth patterns"},
        {"agent": "explore", "prompt": "Find crypto usage"},
        {"agent": "librarian", "prompt": "Research OWASP guidelines"},
    ],
)
```

### As a Tool

```python
# dawn_kestrel/tools/delegation.py

class DelegateTool(Tool):
    id = "delegate"
    description = "Spawn and coordinate subagents with convergence guarantees"
    
    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        mode = args.get("mode", "breadth_first")
        children = args.get("children", [])
        
        engine = self._get_or_create_engine(ctx, mode)
        
        result = await engine.delegate(
            agent_name=args.get("agent", "general"),
            prompt=args.get("prompt", ""),
            session_id=ctx.session_id,
            session_manager=ctx.session_manager,
            children=children,
        )
        
        if result.is_ok():
            return ToolResult(
                title="Delegation complete",
                output=f"Spawned {result.value.total_agents} agents, "
                       f"converged: {result.value.converged}",
                metadata=result.value.__dict__,
            )
        else:
            return ToolResult(
                title="Delegation failed",
                output=f"Error: {result.error}",
                metadata={"error": result.error},
            )
```

## Usage Examples

### Example 1: Parallel Security Scan (BFS)

```python
config = DelegationConfig(
    mode=TraversalMode.BFS,
    budget=DelegationBudget(
        max_depth=2,  # Only one level of children
        max_breadth=10,  # Up to 10 parallel agents
        max_total_agents=15,
    ),
)

engine = DelegationEngine(config, runtime, registry)

result = await engine.delegate(
    agent_name="security_orchestrator",
    prompt="Perform comprehensive security review",
    session_id=session.id,
    session_manager=session_manager,
    children=[
        {"agent": "secrets_scanner", "prompt": "Scan for hardcoded secrets"},
        {"agent": "injection_scanner", "prompt": "Check for injection vulnerabilities"},
        {"agent": "auth_reviewer", "prompt": "Review authentication patterns"},
        {"agent": "crypto_auditor", "prompt": "Audit cryptographic usage"},
        {"agent": "config_scanner", "prompt": "Check for misconfigurations"},
    ],
)

print(f"Converged: {result.converged}")
print(f"Total agents: {result.total_agents}")
print(f"Findings: {len(result.results)}")
```

### Example 2: Deep Code Exploration (DFS)

```python
config = DelegationConfig(
    mode=TraversalMode.DFS,
    budget=DelegationBudget(
        max_depth=4,  # Deep exploration
        max_breadth=3,  # Limited branching
        stagnation_threshold=2,  # Quick convergence
    ),
    check_convergence=True,
)

engine = DelegationEngine(config, runtime, registry)

result = await engine.delegate(
    agent_name="code_explorer",
    prompt="Trace the authentication flow",
    session_id=session.id,
    session_manager=session_manager,
    children=[
        {
            "agent": "trace",
            "prompt": "Follow auth flow",
            "children": [
                {"agent": "trace", "prompt": "Trace token validation"},
                {"agent": "trace", "prompt": "Trace session management"},
            ]
        }
    ],
)
```

### Example 3: Adaptive Hybrid Mode

```python
config = DelegationConfig(
    mode=TraversalMode.ADAPTIVE,
    budget=DelegationBudget(
        max_depth=3,
        max_breadth=5,
        max_total_agents=25,
    ),
)

# Will use BFS for initial broad exploration, then DFS for deep dives
result = await engine.delegate(
    agent_name="research_orchestrator",
    prompt="Research best practices for microservices",
    session_id=session.id,
    session_manager=session_manager,
    children=[
        {"agent": "librarian", "prompt": "Find service mesh patterns"},
        {"agent": "librarian", "prompt": "Find circuit breaker patterns"},
        {"agent": "explore", "prompt": "Find examples in codebase"},
    ],
)
```

## Testing Convergence Guarantees

```python
import pytest
import asyncio

class TestDelegationConvergence:
    """Tests to ensure convergence guarantees hold."""
    
    @pytest.mark.asyncio
    async def test_max_depth_enforced(self, engine, session_manager):
        """Delegation must stop at max_depth even with more children."""
        config = DelegationConfig(
            budget=DelegationBudget(max_depth=2)
        )
        engine = DelegationEngine(config, ...)
        
        # Tree with depth 5
        deep_tree = {
            "children": [{
                "children": [{
                    "children": [{
                        "children": [{"agent": "test"}]
                    }]
                }]
            }]
        }
        
        result = await engine.delegate(..., children=deep_tree["children"])
        
        assert result.max_depth_reached <= 2
        assert result.stop_reason in [
            DelegationStopReason.DEPTH_LIMIT,
            DelegationStopReason.COMPLETED,
        ]
    
    @pytest.mark.asyncio
    async def test_stagnation_causes_convergence(self, engine, session_manager):
        """Repeated identical results should trigger convergence."""
        config = DelegationConfig(
            budget=DelegationBudget(stagnation_threshold=2),
            check_convergence=True,
        )
        engine = DelegationEngine(config, ...)
        
        # Agents that return identical results
        result = await engine.delegate(...)
        
        assert result.stagnation_detected
        assert result.converged
    
    @pytest.mark.asyncio
    async def test_timeout_prevents_infinite_loops(self, engine, session_manager):
        """Wall time limit must be enforced."""
        config = DelegationConfig(
            budget=DelegationBudget(max_wall_time_seconds=5.0)
        )
        engine = DelegationEngine(config, ...)
        
        start = time.time()
        result = await engine.delegate(...)
        elapsed = time.time() - start
        
        assert elapsed < 10.0  # Some margin for cleanup
        assert result.stop_reason == DelegationStopReason.TIMEOUT
    
    @pytest.mark.asyncio
    async def test_max_agents_prevents_spawn_bomb(self, engine, session_manager):
        """Total agent limit must be enforced."""
        config = DelegationConfig(
            budget=DelegationBudget(max_total_agents=5)
        )
        engine = DelegationEngine(config, ...)
        
        # Request 100 children
        children = [{"agent": "test", "prompt": str(i)} for i in range(100)]
        
        result = await engine.delegate(..., children=children)
        
        assert result.total_agents <= 5
```

## Next Steps

1. **Implement core interfaces** - `DelegationConfig`, `DelegationBudget`, `DelegationResult`
2. **Implement ConvergenceTracker** - Novelty detection with signature hashing
3. **Implement DelegationEngine** - BFS, DFS, Adaptive strategies
4. **Add DelegateTool** - Expose as a tool for agents to use
5. **Write convergence tests** - Ensure guarantees hold under all conditions
6. **Create Python skill** - Document best practices for using delegation
