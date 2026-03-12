# Dawn Kestrel SDK - Push the Envelope Investigation & Implementation

**Version:** 1.0
**Date:** 2026-03-07
**Status:** Investigation Complete

---

## Executive Summary

This document defines how to make dawn-kestrel **magnitudes bigger, faster, and more capable** by:
1. Replacing FSM-driven delegation with **policy-driven subtask creation**
2. Creating **multi-agent workflow primitives** for complex orchestration
3. Establishing clean **SDK/evaluation separation** between dawn-kestrel and ash-hawk

### Key Architecture Shifts

| Current Pattern | New Pattern | Benefit |
|-----------------|-------------|---------|
| FSM state transitions | Policy-driven decisions | Deterministic, explainable, composable |
| Hardcoded subagent delegation | Policy-controlled subtasking | Flexible, configurable, testable |
| Embedded evaluation | SDK hooks for ash-hawk | Clean separation, pluggable evaluation |

---

## Part 1: Architecture Refinements

### 1.1 Feature Distribution

Based on analysis, features are distributed as follows:

#### dawn-kestrel (SDK Core)

| Feature | Description | Rationale |
|---------|-------------|-----------|
| Delegation Engine | Multi-agent traversal (BFS/DFS/Adaptive) | Core orchestration primitive |
| **Policy-Driven Subtasks** | NEW: Policy controls subtask creation | Replaces FSM-driven delegation |
| **Multi-Agent Workflow** | NEW: Coordinator pattern for N agents | Generalizes review orchestrator |
| Transcript Capture | Execution traces with hooks | Required for evaluation |
| Skill System | Capability discovery/registration | Extensibility |
| Tool Memory | Experiential learning | Cross-session learning |
| Budget Tracking | Resource limits | Cost control |
| Circuit Breaker | Resilience pattern | Reliability |
| Checkpoint/Resume | State persistence | Recovery |

#### ash-hawk (Evaluation)

| Feature | Description | Rationale |
|---------|-------------|-----------|
| **Grading Framework** | Grader protocol, registry, layers | Evaluation domain |
| **Judge Normalization** | Score normalization, multi-judge consensus | Evaluation domain |
| Evaluation Runner | Trial execution, metrics aggregation | Evaluation domain |
| Calibration | Ground truth comparison | Evaluation domain |
| Rubrics | Quality criteria definitions | Evaluation domain |

### 1.2 Separation Principle

```
┌─────────────────────────────────────────────────────────────────┐
│                         ash-hawk                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Graders    │  │   Judge     │  │   Evaluation Runner     │  │
│  │  (Layer 1-3)│  │ Normalizer  │  │   (Trials, Metrics)     │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INTEGRATION LAYER                            │
│  Transcript Hook  │  Tool Call Hook  │  Phase Complete Hook     │
└─────────────────────────────────────────────────────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                       dawn-kestrel                               │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  Policy     │  │ Multi-Agent     │  │   Delegation        │  │
│  │  Engine     │  │ Workflow        │  │   Engine            │  │
│  └─────────────┘  └─────────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ Transcript  │  │ Skill System    │  │   Tool Memory       │  │
│  │ Capture     │  │                 │  │                     │  │
│  └─────────────┘  └─────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Policy-Driven Subtask Creation

### 2.1 Problem Statement

**Current (FSM-driven):**
```python
# iron-rook's BaseDynamicSubagent
class BaseDynamicSubagent:
    FSM_TRANSITIONS = {
        "intake": ["plan"],
        "plan": ["act"],
        "act": ["synthesize"],
        "synthesize": ["plan", "done"],  # FSM decides
        "done": [],
    }
    
    async def _run_subagent_fsm(self, context):
        while self._current_phase != "done":
            if self._current_phase == "synthesize":
                output = await self._run_synthesize_phase(context)
                next_phase = output.get("next_phase_request", "done")
                if self._should_stop():  # Hardcoded stop logic
                    next_phase = "done"
```

**Problems:**
- FSM transitions are hardcoded
- Stop conditions are embedded in code
- No way to configure delegation behavior
- Difficult to test delegation logic independently

**Desired (Policy-driven):**
```python
# Policy decides subtask creation
delegation_policy = DelegationPolicy(
    subtask_policy=SubtaskCreationPolicy(
        max_depth=3,
        create_subtasks_when=lambda ctx: ctx.complexity > 0.7,
        subtask_for_domain={
            "security": "security_subagent",
            "performance": "performance_subagent",
        },
    ),
    stop_policy=StopPolicy(
        stagnation_threshold=2,
        budget_aware=True,
    ),
)
```

### 2.2 Design: Policy-Driven Delegation

#### Core Protocol

```python
# dawn_kestrel/policy/delegation.py

from typing import Protocol, Any
from pydantic import BaseModel
from enum import Enum

class DelegationDecision(str, Enum):
    """What to do next in delegation."""
    CONTINUE = "continue"           # Continue with current agent
    DELEGATE = "delegate"           # Create subtasks
    SYNTHESIZE = "synthesize"       # Aggregate results
    DONE = "done"                   # Stop delegation


class DelegationContext(BaseModel):
    """Context for delegation decisions."""
    # Current state
    current_agent: str
    current_depth: int
    iteration_count: int
    
    # Results so far
    accumulated_results: list[Any]
    accumulated_evidence: list[Any]
    findings_count: int
    findings_per_iteration: list[int]
    
    # Budget
    tokens_used: int
    cost_usd: float
    elapsed_seconds: float
    
    # Input analysis
    task_complexity: float  # 0.0 - 1.0
    domains_detected: list[str]
    
    # Budget limits
    budget: "DelegationBudget"


class SubtaskProposal(BaseModel):
    """A proposed subtask to delegate."""
    agent: str
    prompt: str
    domain: str
    priority: int = 1
    metadata: dict[str, Any] = {}


class DelegationOutput(BaseModel):
    """Output from delegation policy."""
    decision: DelegationDecision
    rationale: str
    confidence: float
    
    # If DELEGATE
    subtasks: list[SubtaskProposal] = []
    
    # If CONTINUE
    continue_with: str | None = None
    
    # Budget consumed this decision
    budget_consumed: dict[str, Any] = {}


class DelegationPolicy(Protocol):
    """Protocol for policy-driven delegation decisions.
    
    This replaces FSM-based delegation logic with configurable
    policy objects that decide:
    - When to create subtasks
    - Which agents to delegate to
    - When to stop delegating
    """
    
    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        """Evaluate delegation context and decide next action.
        
        Args:
            context: Current delegation state and results
            
        Returns:
            DelegationOutput with decision and optional subtasks
        """
        ...
```

#### Built-in Policies

```python
# dawn_kestrel/policy/builtin/delegation.py

class ComplexityBasedDelegationPolicy:
    """Delegate based on task complexity analysis.
    
    - Low complexity (0-0.3): Single agent, no delegation
    - Medium complexity (0.3-0.7): Limited delegation (1-2 subtasks)
    - High complexity (0.7+): Full delegation (3+ subtasks)
    """
    
    def __init__(
        self,
        complexity_threshold: float = 0.5,
        max_subtasks: int = 5,
        domain_agents: dict[str, str] = None,
    ):
        self.complexity_threshold = complexity_threshold
        self.max_subtasks = max_subtasks
        self.domain_agents = domain_agents or {}
    
    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        # Check stop conditions first
        if self._should_stop(context):
            return DelegationOutput(
                decision=DelegationDecision.DONE,
                rationale="Stop conditions met",
                confidence=0.9,
            )
        
        # Check if we should delegate
        if context.task_complexity >= self.complexity_threshold:
            subtasks = self._create_subtasks(context)
            if subtasks:
                return DelegationOutput(
                    decision=DelegationDecision.DELEGATE,
                    rationale=f"Task complexity {context.task_complexity:.2f} exceeds threshold",
                    confidence=0.8,
                    subtasks=subtasks,
                )
        
        # Continue with current agent
        return DelegationOutput(
            decision=DelegationDecision.CONTINUE,
            rationale="No delegation needed",
            confidence=0.7,
        )


class BudgetAwareDelegationPolicy:
    """Delegate with budget awareness.
    
    Wraps another policy and enforces budget constraints.
    """
    
    def __init__(
        self,
        inner_policy: DelegationPolicy,
        budget: DelegationBudget,
    ):
        self.inner_policy = inner_policy
        self.budget = budget
    
    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        # Check budget before delegation
        if context.cost_usd >= self.budget.max_cost_usd:
            return DelegationOutput(
                decision=DelegationDecision.DONE,
                rationale="Budget exhausted: cost",
                confidence=1.0,
            )
        
        if context.elapsed_seconds >= self.budget.max_seconds:
            return DelegationOutput(
                decision=DelegationDecision.DONE,
                rationale="Budget exhausted: time",
                confidence=1.0,
            )
        
        if context.current_depth >= self.budget.max_depth:
            return DelegationOutput(
                decision=DelegationDecision.SYNTHESIZE,
                rationale="Max depth reached, synthesizing",
                confidence=0.9,
            )
        
        # Delegate to inner policy
        return self.inner_policy.evaluate(context)


class StagnationAwarePolicy:
    """Stop when progress stagnates.
    
    Detects when results stop improving and triggers early termination.
    """
    
    def __init__(
        self,
        inner_policy: DelegationPolicy,
        stagnation_threshold: int = 2,
    ):
        self.inner_policy = inner_policy
        self.stagnation_threshold = stagnation_threshold
    
    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        # Check for stagnation
        if len(context.findings_per_iteration) >= self.stagnation_threshold:
            recent = context.findings_per_iteration[-self.stagnation_threshold:]
            if all(count == 0 for count in recent):
                return DelegationOutput(
                    decision=DelegationDecision.DONE,
                    rationale=f"Stagnation: {self.stagnation_threshold} iterations with no findings",
                    confidence=0.85,
                )
        
        return self.inner_policy.evaluate(context)
```

#### Integration with DelegationEngine

```python
# dawn_kestrel/delegation/engine.py (updated)

class DelegationEngine:
    """Policy-driven delegation engine.
    
    Usage:
        policy = ComplexityBasedDelegationPolicy(
            complexity_threshold=0.5,
            domain_agents={
                "security": "security_subagent",
                "performance": "performance_subagent",
            },
        )
        
        engine = DelegationEngine(
            policy=policy,
            runtime=agent_runtime,
            registry=agent_registry,
        )
        
        result = await engine.delegate(
            agent_name="orchestrator",
            prompt="Analyze this codebase",
            session_id="session-123",
        )
    """
    
    def __init__(
        self,
        policy: DelegationPolicy,
        runtime: "AgentRuntime",
        registry: "AgentRegistry",
    ):
        self.policy = policy
        self.runtime = runtime
        self.registry = registry
    
    async def delegate(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
    ) -> Result[DelegationResult]:
        """Execute policy-driven delegation."""
        context = DelegationContext(
            current_agent=agent_name,
            current_depth=0,
            iteration_count=0,
            # ... initial state
        )
        
        while True:
            # Ask policy what to do
            output = self.policy.evaluate(context)
            
            if output.decision == DelegationDecision.DONE:
                break
            
            elif output.decision == DelegationDecision.DELEGATE:
                # Create and execute subtasks
                for subtask in output.subtasks:
                    result = await self._execute_agent(
                        subtask.agent,
                        subtask.prompt,
                        session_id,
                    )
                    context.accumulated_results.append(result)
                context.current_depth += 1
            
            elif output.decision == DelegationDecision.CONTINUE:
                # Execute current agent again
                result = await self._execute_agent(
                    context.current_agent,
                    prompt,
                    session_id,
                )
                context.accumulated_results.append(result)
            
            elif output.decision == DelegationDecision.SYNTHESIZE:
                # Aggregate results
                synthesized = self._synthesize(context.accumulated_results)
                context.accumulated_results = [synthesized]
            
            context.iteration_count += 1
        
        return Ok(self._build_result(context))
```

### 2.3 Migration from FSM

```python
# Before (iron-rook FSM)
class SecuritySubagent(BaseDynamicSubagent):
    async def _run_synthesize_phase(self, context):
        # LLM decides next phase
        output = await self._llm_decide_next_phase()
        if output.get("goal_achieved"):
            return {"next_phase_request": "done"}
        return {"next_phase_request": "plan"}

# After (Policy-driven)
class SecuritySubagentV2:
    def __init__(self):
        self.delegation_policy = BudgetAwareDelegationPolicy(
            inner_policy=StagnationAwarePolicy(
                inner_policy=DomainBasedDelegationPolicy(
                    domain_agents={
                        "auth": "auth_subagent",
                        "injection": "injection_subagent",
                        "secrets": "secrets_subagent",
                    },
                ),
                stagnation_threshold=2,
            ),
            budget=DelegationBudget(
                max_depth=3,
                max_iterations=5,
                max_cost_usd=0.50,
            ),
        )
    
    async def analyze(self, context: ReviewContext) -> ReviewOutput:
        engine = DelegationEngine(
            policy=self.delegation_policy,
            runtime=self.runtime,
            registry=self.registry,
        )
        
        result = await engine.delegate(
            agent_name="security",
            prompt=f"Analyze security of {context.changed_files}",
            session_id=context.session_id,
        )
        
        return self._build_output(result)
```

---

## Part 3: Multi-Agent Workflow Primitive

### 3.1 Problem Statement

**Current (iron-rook orchestrator):**
```python
class PRReviewOrchestrator:
    """Coordinates 11 specialized reviewers."""
    
    def __init__(self, subagents: list[BaseReviewerAgent]):
        self.subagents = subagents
    
    async def run_review(self, inputs: ReviewInputs) -> ReviewOutput:
        # Hardcoded coordination logic
        results = []
        for subagent in self.subagents:
            result = await subagent.run(inputs)
            results.append(result)
        
        # Hardcoded aggregation
        return self._aggregate(results)
```

**Problems:**
- Coordination logic is hardcoded
- No support for parallel execution with dependencies
- Aggregation logic is domain-specific
- No standard interface for multi-agent workflows

**Desired:**
```python
# Generic multi-agent workflow
workflow = MultiAgentWorkflow(
    agents=[
        AgentSpec(name="security", agent=security_agent),
        AgentSpec(name="architecture", agent=arch_agent),
        AgentSpec(name="performance", agent=perf_agent),
    ],
    execution_mode=ExecutionMode.PARALLEL,  # or SEQUENTIAL, DAG
    aggregation=AggregationSpec(
        strategy="merge_findings",
        conflict_resolution="highest_severity",
    ),
)

result = await workflow.execute(context)
```

### 3.2 Design: Multi-Agent Workflow

```python
# dawn_kestrel/workflow/multi_agent.py

from typing import Protocol, Any, Callable
from pydantic import BaseModel
from enum import Enum

class ExecutionMode(str, Enum):
    """How to execute agents."""
    SEQUENTIAL = "sequential"  # One at a time
    PARALLEL = "parallel"      # All at once
    DAG = "dag"                # Dependency-based
    ADAPTIVE = "adaptive"      # Based on results


class AgentSpec(BaseModel):
    """Specification for an agent in a workflow."""
    name: str
    agent: Any  # Agent or agent factory
    dependencies: list[str] = []  # Names of agents that must complete first
    condition: Callable[[dict], bool] | None = None  # Run condition
    timeout_seconds: float = 300.0
    retry_count: int = 0


class AggregationSpec(BaseModel):
    """How to aggregate results from multiple agents."""
    strategy: str  # "merge_findings", "first_success", "vote", "weighted"
    conflict_resolution: str = "fail"  # "fail", "first", "highest_severity", "merge"
    weights: dict[str, float] = {}  # Agent name -> weight


class WorkflowResult(BaseModel):
    """Result from multi-agent workflow execution."""
    success: bool
    agent_results: dict[str, Any]
    aggregated_result: Any
    execution_order: list[str]
    errors: dict[str, str]
    timing: dict[str, float]


class MultiAgentWorkflow:
    """Generic multi-agent workflow coordinator.
    
    This generalizes iron-rook's PRReviewOrchestrator to work
    with any multi-agent coordination pattern.
    
    Usage:
        workflow = MultiAgentWorkflow(
            agents=[
                AgentSpec(name="security", agent=security_agent),
                AgentSpec(name="architecture", agent=arch_agent, dependencies=["security"]),
                AgentSpec(name="docs", agent=docs_agent),
            ],
            execution_mode=ExecutionMode.DAG,
            aggregation=AggregationSpec(
                strategy="merge_findings",
                conflict_resolution="highest_severity",
            ),
        )
        
        result = await workflow.execute(context)
    """
    
    def __init__(
        self,
        agents: list[AgentSpec],
        execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
        aggregation: AggregationSpec | None = None,
    ):
        self.agents = {a.name: a for a in agents}
        self.execution_mode = execution_mode
        self.aggregation = aggregation or AggregationSpec(strategy="merge")
        
        # Validate DAG
        if execution_mode == ExecutionMode.DAG:
            self._validate_dag()
    
    async def execute(self, context: Any) -> WorkflowResult:
        """Execute the multi-agent workflow."""
        results: dict[str, Any] = {}
        errors: dict[str, str] = {}
        timing: dict[str, float] = {}
        execution_order: list[str] = []
        
        if self.execution_mode == ExecutionMode.SEQUENTIAL:
            execution_order = list(self.agents.keys())
            for name in execution_order:
                result = await self._execute_agent(name, context, results)
                if result.is_ok():
                    results[name] = result.unwrap()
                else:
                    errors[name] = result.error
        
        elif self.execution_mode == ExecutionMode.PARALLEL:
            execution_order = list(self.agents.keys())
            tasks = [
                self._execute_agent(name, context, {})
                for name in execution_order
            ]
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            for name, outcome in zip(execution_order, outcomes):
                if isinstance(outcome, Exception):
                    errors[name] = str(outcome)
                elif outcome.is_ok():
                    results[name] = outcome.unwrap()
                else:
                    errors[name] = outcome.error
        
        elif self.execution_mode == ExecutionMode.DAG:
            execution_order = await self._execute_dag(context, results, errors)
        
        # Aggregate results
        aggregated = self._aggregate_results(results)
        
        return WorkflowResult(
            success=len(errors) == 0,
            agent_results=results,
            aggregated_result=aggregated,
            execution_order=execution_order,
            errors=errors,
            timing=timing,
        )
    
    async def _execute_dag(
        self,
        context: Any,
        results: dict[str, Any],
        errors: dict[str, str],
    ) -> list[str]:
        """Execute agents in DAG order."""
        completed: set[str] = set()
        execution_order: list[str] = []
        
        while len(completed) < len(self.agents):
            # Find agents ready to execute
            ready = [
                name for name, spec in self.agents.items()
                if name not in completed
                and all(dep in completed for dep in spec.dependencies)
                and (spec.condition is None or spec.condition(results))
            ]
            
            if not ready:
                # Deadlock or circular dependency
                remaining = set(self.agents.keys()) - completed
                for name in remaining:
                    errors[name] = "Dependency not satisfied"
                break
            
            # Execute ready agents in parallel
            tasks = [self._execute_agent(name, context, results) for name in ready]
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            
            for name, outcome in zip(ready, outcomes):
                completed.add(name)
                execution_order.append(name)
                if isinstance(outcome, Exception):
                    errors[name] = str(outcome)
                elif outcome.is_ok():
                    results[name] = outcome.unwrap()
                else:
                    errors[name] = outcome.error
        
        return execution_order
    
    def _aggregate_results(self, results: dict[str, Any]) -> Any:
        """Aggregate results based on strategy."""
        if self.aggregation.strategy == "merge_findings":
            return self._merge_findings(results)
        elif self.aggregation.strategy == "first_success":
            return self._first_success(results)
        elif self.aggregation.strategy == "vote":
            return self._vote(results)
        elif self.aggregation.strategy == "weighted":
            return self._weighted(results)
        return results
    
    def _merge_findings(self, results: dict[str, Any]) -> dict[str, Any]:
        """Merge findings from all agents."""
        all_findings = []
        for name, result in results.items():
            if hasattr(result, 'findings'):
                all_findings.extend(result.findings)
        
        # Deduplicate and resolve conflicts
        unique_findings = self._deduplicate_findings(all_findings)
        
        return {"findings": unique_findings, "total": len(unique_findings)}
```

### 3.3 Review Workflow as Specialization

```python
# dawn_kestrel/workflow/review.py

class ReviewWorkflow(MultiAgentWorkflow):
    """Multi-agent workflow specialized for code review.
    
    Usage:
        workflow = ReviewWorkflow(
            reviewers=[
                "security", "architecture", "documentation",
                "telemetry", "linting", "unit_tests",
                "diff_scoper", "requirements", "performance",
                "dependencies", "changelog",
            ],
            mode=ExecutionMode.PARALLEL,
        )
        
        result = await workflow.review(pr_context)
    """
    
    def __init__(
        self,
        reviewers: list[str],
        mode: ExecutionMode = ExecutionMode.PARALLEL,
    ):
        agents = [
            AgentSpec(
                name=reviewer,
                agent=self._create_reviewer(reviewer),
            )
            for reviewer in reviewers
        ]
        
        super().__init__(
            agents=agents,
            execution_mode=mode,
            aggregation=AggregationSpec(
                strategy="merge_findings",
                conflict_resolution="highest_severity",
            ),
        )
    
    async def review(self, context: ReviewContext) -> ReviewOutput:
        result = await self.execute(context)
        
        return ReviewOutput(
            findings=result.aggregated_result.get("findings", []),
            merge_decision=self._compute_merge_decision(result),
            confidence=self._compute_confidence(result),
        )
```

---

## Part 4: ash-hawk Integration Hooks

### 4.1 What ash-hawk Provides

Based on analysis of ash-hawk, the following should remain in ash-hawk:

```
ash-hawk/
├── graders/
│   ├── base.py              # Grader protocol
│   ├── deterministic.py     # string_match, test_runner, static_analysis
│   ├── llm.py               # llm_judge
│   ├── composite.py         # weighted aggregation
│   └── judge_normalizer.py  # Score normalization
├── execution/
│   ├── runner.py            # EvalRunner
│   ├── trial.py             # TrialExecutor
│   └── fixtures.py          # FixtureResolver
├── calibration/
│   ├── ece.py               # Expected Calibration Error
│   └── brier.py             # Brier score
└── reporting/
    ├── json.py              # JSON reports
    └── html.py              # HTML reports
```

### 4.2 What dawn-kestrel Must Provide

dawn-kestrel must provide hooks that ash-hawk can attach to:

```python
# dawn_kestrel/evaluation/hooks.py

from typing import Callable, Any, Protocol
from pydantic import BaseModel

class TranscriptHook(Protocol):
    """Hook called when transcript is ready."""
    def __call__(self, transcript: "Transcript") -> None: ...


class ToolCallHook(Protocol):
    """Hook called on each tool call."""
    def __call__(self, tool: str, input: dict, output: Any) -> None: ...


class PhaseHook(Protocol):
    """Hook called when a phase completes."""
    def __call__(self, phase: str, output: dict) -> None: ...


class BudgetHook(Protocol):
    """Hook called when budget threshold is reached."""
    def __call__(self, usage: "BudgetUsage", threshold: float) -> None: ...


class EvaluationHooks:
    """Hooks that ash-hawk can attach to for evaluation.
    
    Usage:
        # In ash-hawk
        hooks = EvaluationHooks()
        hooks.on_transcript_ready = lambda t: evaluator.record(t)
        hooks.on_tool_call = lambda t, i, o: evaluator.track_tool(t, i, o)
        
        # In dawn-kestrel
        session = Session(hooks=hooks)
        await session.run(prompt)
    """
    
    on_transcript_ready: TranscriptHook | None = None
    on_tool_call: ToolCallHook | None = None
    on_phase_complete: PhaseHook | None = None
    on_budget_threshold: BudgetHook | None = None
    
    # Event emission
    def emit_transcript(self, transcript: "Transcript") -> None:
        if self.on_transcript_ready:
            self.on_transcript_ready(transcript)
    
    def emit_tool_call(self, tool: str, input: dict, output: Any) -> None:
        if self.on_tool_call:
            self.on_tool_call(tool, input, output)
    
    def emit_phase(self, phase: str, output: dict) -> None:
        if self.on_phase_complete:
            self.on_phase_complete(phase, output)
    
    def emit_budget(self, usage: "BudgetUsage", threshold: float) -> None:
        if self.on_budget_threshold:
            self.on_budget_threshold(usage, threshold)
```

### 4.3 Integration Example

```python
# In ash-hawk: scenario/adapters/sdk_dawn_kestrel.py

from dawn_kestrel.evaluation import EvaluationHooks, Transcript

class AshHawkIntegration:
    """Integrate ash-hawk evaluation with dawn-kestrel SDK."""
    
    def __init__(self, eval_runner: "EvalRunner"):
        self.eval_runner = eval_runner
        self.hooks = self._create_hooks()
    
    def _create_hooks(self) -> EvaluationHooks:
        hooks = EvaluationHooks()
        
        # Hook: Record transcript for grading
        hooks.on_transcript_ready = self._record_transcript
        
        # Hook: Track tool calls for tool_call grader
        hooks.on_tool_call = self._track_tool_call
        
        # Hook: Record phase for trace_assertions grader
        hooks.on_phase_complete = self._record_phase
        
        return hooks
    
    def _record_transcript(self, transcript: Transcript) -> None:
        """Record transcript for evaluation."""
        self.eval_runner.record_trial_transcript(transcript)
    
    def _track_tool_call(self, tool: str, input: dict, output: Any) -> None:
        """Track tool calls for graders."""
        self.eval_runner.track_tool_call(tool, input, output)
    
    def _record_phase(self, phase: str, output: dict) -> None:
        """Record phase completion."""
        self.eval_runner.record_phase(phase, output)
```

---

## Part 5: Implementation Roadmap

### Phase 1: Policy-Driven Delegation (Weeks 1-2)

**Deliverables:**
- [ ] `dawn_kestrel/policy/delegation.py` - Core protocols
- [ ] `dawn_kestrel/policy/builtin/delegation.py` - Built-in policies
- [ ] Update `DelegationEngine` to use policies
- [ ] Tests for all policy implementations

**Success Criteria:**
- Policy-driven delegation works end-to-end
- Can configure delegation behavior without code changes
- Tests pass for all policy types

### Phase 2: Multi-Agent Workflow (Weeks 3-4)

**Deliverables:**
- [ ] `dawn_kestrel/workflow/multi_agent.py` - Core workflow
- [ ] `dawn_kestrel/workflow/review.py` - Review specialization
- [ ] DAG execution support
- [ ] Aggregation strategies

**Success Criteria:**
- Can define multi-agent workflows declaratively
- DAG execution respects dependencies
- Review workflow coordinates 11 agents

### Phase 3: Evaluation Hooks (Week 5)

**Deliverables:**
- [ ] `dawn_kestrel/evaluation/hooks.py` - Hook system
- [ ] Update `Session` and `AgentRuntime` to emit events
- [ ] Integration tests with ash-hawk

**Success Criteria:**
- Hooks fire at correct times
- ash-hawk can capture all needed data
- No performance regression

### Phase 4: Migration & Documentation (Week 6)

**Deliverables:**
- [ ] Migrate iron-rook to policy-driven delegation
- [ ] Update bolt-merlin to use new workflow
- [ ] Documentation for all new features
- [ ] Migration guide from FSM patterns

---

## Part 6: Metrics for Success

### Capability Metrics

| Metric | Current | Target | How |
|--------|---------|--------|-----|
| Delegation modes | 3 (BFS/DFS/Adaptive) | Unlimited policies | Policy-driven system |
| Subtask creation | FSM hardcoded | Policy configurable | DelegationPolicy |
| Multi-agent coordination | Per-project | Generic primitive | MultiAgentWorkflow |
| Evaluation integration | Custom per-project | Standard hooks | EvaluationHooks |

### Developer Experience Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Lines to define delegation | ~100 | ~10 |
| Lines to define workflow | ~200 | ~20 |
| Test coverage for delegation | 60% | 95% |
| Time to new workflow | 2 days | 2 hours |

### Reliability Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Infinite loop prevention | Hardcoded | Policy-enforced |
| Budget enforcement | Per-project | SDK-wide |
| Recovery from failures | Per-project | Checkpoint/resume |

---

## Appendix A: Code Examples

### Example 1: Policy-Driven Security Review

```python
from dawn_kestrel.policy import DelegationPolicy, DelegationContext
from dawn_kestrel.delegation import DelegationEngine

# Define custom policy
class SecurityReviewPolicy(DelegationPolicy):
    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        # Always delegate to specialized subagents
        if context.current_depth == 0:
            return DelegationOutput(
                decision=DelegationDecision.DELEGATE,
                rationale="Initial security analysis",
                confidence=0.9,
                subtasks=[
                    SubtaskProposal(agent="auth_subagent", prompt="Analyze auth", domain="auth"),
                    SubtaskProposal(agent="injection_subagent", prompt="Find injections", domain="injection"),
                    SubtaskProposal(agent="secrets_subagent", prompt="Find secrets", domain="secrets"),
                ],
            )
        
        # After subagent results, synthesize
        if context.current_depth == 1:
            return DelegationOutput(
                decision=DelegationDecision.SYNTHESIZE,
                rationale="Synthesizing subagent results",
                confidence=0.8,
            )
        
        # Done
        return DelegationOutput(
            decision=DelegationDecision.DONE,
            rationale="Review complete",
            confidence=0.9,
        )

# Use policy
policy = SecurityReviewPolicy()
engine = DelegationEngine(policy=policy, runtime=runtime, registry=registry)
result = await engine.delegate("security", "Review this PR", session_id)
```

### Example 2: Multi-Agent Workflow

```python
from dawn_kestrel.workflow import MultiAgentWorkflow, AgentSpec, ExecutionMode

# Define workflow
workflow = MultiAgentWorkflow(
    agents=[
        AgentSpec(name="security", agent=security_agent),
        AgentSpec(name="architecture", agent=arch_agent, dependencies=["security"]),
        AgentSpec(name="docs", agent=docs_agent),
        AgentSpec(name="tests", agent=tests_agent, dependencies=["architecture"]),
        AgentSpec(name="performance", agent=perf_agent, dependencies=["tests"]),
    ],
    execution_mode=ExecutionMode.DAG,
    aggregation=AggregationSpec(
        strategy="merge_findings",
        conflict_resolution="highest_severity",
    ),
)

# Execute
result = await workflow.execute(review_context)
print(f"Total findings: {len(result.aggregated_result['findings'])}")
print(f"Execution order: {result.execution_order}")
```

### Example 3: ash-hawk Integration

```python
from dawn_kestrel.evaluation import EvaluationHooks
from ash_hawk.execution import EvalRunner

# Create evaluation runner
eval_runner = EvalRunner(suite=my_suite)

# Set up hooks
hooks = EvaluationHooks()
hooks.on_transcript_ready = eval_runner.record_transcript
hooks.on_tool_call = eval_runner.track_tool_call
hooks.on_phase_complete = eval_runner.record_phase

# Run with hooks
session = Session(hooks=hooks)
result = await session.run(agent_name="my_agent", prompt="Do work")

# Get evaluation results
summary = await eval_runner.get_summary()
print(f"Pass rate: {summary.pass_rate:.1%}")
```

---

## Appendix B: File Structure

```
dawn_kestrel/
├── policy/
│   ├── __init__.py
│   ├── delegation.py          # NEW: DelegationPolicy protocols
│   ├── builtin/
│   │   ├── __init__.py
│   │   └── delegation.py      # NEW: Built-in delegation policies
│   └── ...
├── workflow/
│   ├── __init__.py
│   ├── multi_agent.py         # NEW: MultiAgentWorkflow
│   └── review.py              # NEW: ReviewWorkflow specialization
├── evaluation/
│   ├── __init__.py
│   ├── hooks.py               # NEW: EvaluationHooks
│   ├── models.py              # Existing: Transcript, etc.
│   └── ...
├── delegation/
│   ├── __init__.py
│   ├── engine.py              # UPDATED: Uses DelegationPolicy
│   ├── types.py
│   └── ...
└── ...

ash-hawk/                      # Separate project
├── graders/
│   ├── base.py               # Grader protocol
│   ├── deterministic.py      # Built-in graders
│   ├── llm.py                # LLM judge
│   ├── composite.py          # Aggregation
│   └── judge_normalizer.py   # Score normalization
├── execution/
│   └── runner.py             # EvalRunner
├── calibration/
│   └── ...
└── scenario/
    └── adapters/
        └── sdk_dawn_kestrel.py  # Uses EvaluationHooks
```
