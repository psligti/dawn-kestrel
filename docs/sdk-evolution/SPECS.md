# Dawn Kestrel SDK - Technical Specifications

**Version:** 1.0
**Date:** 2026-03-06

---

## 1. Delegation Engine Specification

### 1.1 Module Structure

```
dawn_kestrel/delegation/
├── __init__.py
├── engine.py           # DelegationEngine
├── types.py            # TraversalMode, DelegationBudget, etc.
├── convergence.py      # ConvergenceTracker
├── queue.py            # ExecutionQueue (moved from agents/)
└── contracts.py        # DelegationRequest, DelegationResult
```

### 1.2 Core Protocol

```python
from typing import Protocol, Any, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field

class TraversalMode(str, Enum):
    """Delegation traversal strategy."""
    BFS = "bfs"           # Breadth-first: parallel children
    DFS = "dfs"           # Depth-first: sequential deep-dive
    ADAPTIVE = "adaptive" # BFS at depth 0-1, DFS at depth 2+


@dataclass(frozen=True)
class DelegationBudget:
    """Budget constraints for delegation tree execution."""
    max_depth: int = 5
    max_breadth: int = 10
    max_total_agents: int = 50
    max_wall_time_seconds: float = 300.0
    max_iterations: int = 100
    stagnation_threshold: int = 3  # Iterations with no new evidence
    
    def __post_init__(self):
        if self.max_depth < 1:
            raise ValueError("max_depth must be >= 1")
        if self.max_breadth < 1:
            raise ValueError("max_breadth must be >= 1")


@dataclass
class DelegationConfig:
    """Configuration for DelegationEngine."""
    mode: TraversalMode = TraversalMode.ADAPTIVE
    budget: DelegationBudget = field(default_factory=DelegationBudget)
    check_convergence: bool = True
    evidence_keys: list[str] = field(default_factory=lambda: ["findings"])
    max_concurrency: int = 4
    
    # Callbacks
    on_agent_spawn: Callable[[str, int], Awaitable[None]] | None = None
    on_agent_complete: Callable[[str, Any], Awaitable[None]] | None = None
    on_convergence: Callable[[str], Awaitable[None]] | None = None


@dataclass
class ChildDelegation:
    """A child delegation request."""
    agent: str
    prompt: str
    children: list["ChildDelegation"] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegationResult:
    """Result of a delegation tree execution."""
    success: bool
    stop_reason: str  # COMPLETED, CONVERGED, BUDGET_EXHAUSTED, TIMEOUT, etc.
    results: list[Any]
    errors: list[Exception]
    total_agents: int
    max_depth_reached: int
    elapsed_seconds: float
    iterations: int
    converged: bool
    stagnation_detected: bool


class DelegationEngine:
    """Convergence-aware delegation engine with BFS/DFS strategies.
    
    Usage:
        config = DelegationConfig(
            mode=TraversalMode.ADAPTIVE,
            budget=DelegationBudget(max_depth=5, max_total_agents=30),
        )
        engine = DelegationEngine(config, runtime, registry)
        
        result = await engine.delegate(
            agent_name="orchestrator",
            prompt="Analyze the codebase",
            session_id="session-123",
            children=[
                ChildDelegation(agent="security", prompt="Find vulnerabilities"),
                ChildDelegation(agent="performance", prompt="Find bottlenecks"),
            ],
        )
    """
    
    def __init__(
        self,
        config: DelegationConfig,
        runtime: "AgentRuntime",
        registry: "AgentRegistry",
    ): ...
    
    async def delegate(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        children: list[ChildDelegation] | None = None,
        tools: "ToolRegistry | None" = None,
    ) -> Result[DelegationResult]: ...
```

### 1.3 Convergence Detection

```python
import hashlib
from dataclasses import dataclass, field

@dataclass
class ConvergenceTracker:
    """Detects convergence via SHA-256 content hashing.
    
    When results become similar (same hash), we detect stagnation
    and can terminate early.
    """
    evidence_keys: list[str]
    signatures: list[str] = field(default_factory=list)
    stagnation_count: int = 0
    
    def check_novelty(self, results: list[Any]) -> bool:
        """Check if results contain novel evidence.
        
        Returns:
            True if novel (not seen before), False if duplicate.
        """
        evidence = self._extract_evidence(results)
        signature = hashlib.sha256(str(evidence).encode()).hexdigest()
        
        if signature in self.signatures:
            self.stagnation_count += 1
            return False
        
        self.signatures.append(signature)
        return True
    
    def is_converged(self, threshold: int) -> bool:
        """Check if we've reached stagnation threshold."""
        return self.stagnation_count >= threshold
```

---

## 2. Grading Framework Specification

### 2.1 Module Structure

```
dawn_kestrel/evaluation/graders/
├── __init__.py
├── base.py             # Grader protocol
├── registry.py         # GraderRegistry
├── deterministic.py    # StringMatch, TestRunner, StaticAnalysis
├── llm.py              # LLMJudge
├── composite.py        # Composite, Aggregation
└── rubrics/            # Built-in rubrics
    ├── code_quality.md
    ├── correctness.md
    └── safety.md
```

### 2.2 Core Protocol

```python
from abc import ABC, abstractmethod
from typing import Protocol
from pydantic import BaseModel

class GraderSpec(BaseModel):
    """Specification for a grader invocation."""
    grader_type: str
    config: dict[str, Any] = {}
    weight: float = 1.0
    required: bool = True


class GraderResult(BaseModel):
    """Result from a grader."""
    grader_type: str
    score: float  # 0.0 to 1.0
    passed: bool
    details: dict[str, Any] = {}
    confidence: float | None = None
    error: str | None = None


class EvalTranscript(BaseModel):
    """Complete execution transcript for grading."""
    messages: list["Message"]
    tool_calls: list["ToolCallRecord"]
    artifacts: dict[str, str]  # file_path -> content
    timing: dict[str, float]
    token_usage: dict[str, int]
    

class Grader(ABC):
    """Abstract base class for all graders.
    
    Graders are stateless - they should not maintain state between calls.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this grader type."""
        ...
    
    @abstractmethod
    async def grade(
        self,
        transcript: EvalTranscript,
        spec: GraderSpec,
    ) -> GraderResult:
        """Evaluate a transcript against criteria.
        
        Args:
            transcript: Complete execution transcript
            spec: Grader configuration
            
        Returns:
            GraderResult with score (0-1) and pass/fail
        """
        ...
```

### 2.3 Deterministic Graders

```python
class StringMatchGrader(Grader):
    """Match output against expected string.
    
    Config:
        expected: Expected string
        mode: "exact" | "contains" | "regex"
        case_sensitive: bool
    """
    
    @property
    def name(self) -> str:
        return "string_match"


class TestRunnerGrader(Grader):
    """Run tests and report results.
    
    Config:
        test_file: Path to test file
        test_function: Optional specific test
        pass_threshold: Fraction of tests that must pass
        timeout_seconds: Test timeout
    """
    
    @property
    def name(self) -> str:
        return "test_runner"


class StaticAnalysisGrader(Grader):
    """Run static analysis tools.
    
    Config:
        tools: ["ruff", "mypy", "pyright"]
        max_issues: Maximum allowed issues
        fail_on_error: Treat errors as failure
    """
    
    @property
    def name(self) -> str:
        return "static_analysis"


class ToolCallGrader(Grader):
    """Verify expected tool calls were made.
    
    Config:
        expected_calls: [{"tool": "read", "min_count": 1}]
        require_all: bool
        partial_credit: bool
    """
    
    @property
    def name(self) -> str:
        return "tool_call"
```

### 2.4 LLM Judge Grader

```python
class LLMJudgeGrader(Grader):
    """Use LLM as judge for quality assessment.
    
    Config:
        rubric: Rubric name or "custom"
        custom_prompt_path: Path to custom rubric (if rubric="custom")
        criteria: ["correctness", "quality", "safety"]
        pass_threshold: Minimum score to pass
        n_judges: Number of independent judges
        consensus: "mean" | "median" | "min" | "all_must_pass"
        judge_provider: Provider for judge LLM
        judge_model: Model for judge LLM
    """
    
    @property
    def name(self) -> str:
        return "llm_judge"
    
    async def grade(
        self,
        transcript: EvalTranscript,
        spec: GraderSpec,
    ) -> GraderResult:
        # 1. Load rubric
        rubric = self._load_rubric(spec.config)
        
        # 2. Format prompt with transcript
        prompt = self._format_judge_prompt(rubric, transcript)
        
        # 3. Run N judges in parallel
        scores = await self._run_judges(prompt, spec.config.get("n_judges", 1))
        
        # 4. Aggregate with consensus method
        final_score = self._aggregate(scores, spec.config.get("consensus", "mean"))
        
        # 5. Normalize to [0, 1]
        normalized = self._normalize(final_score)
        
        return GraderResult(
            grader_type=self.name,
            score=normalized,
            passed=normalized >= spec.config.get("pass_threshold", 0.7),
            confidence=self._calculate_confidence(scores),
        )
```

### 2.5 Composite Grader

```python
class CompositeGrader(Grader):
    """Combine multiple graders with weights.
    
    Config:
        graders: List of GraderSpec objects
        aggregation: "weighted_average" | "all_or_nothing" | "threshold"
        pass_threshold: Overall threshold
    """
    
    @property
    def name(self) -> str:
        return "composite"
    
    async def grade(
        self,
        transcript: EvalTranscript,
        spec: GraderSpec,
    ) -> GraderResult:
        results = []
        total_weight = 0.0
        
        for grader_spec in spec.config.get("graders", []):
            grader = registry.get(grader_spec.grader_type)
            result = await grader.grade(transcript, grader_spec)
            results.append((result, grader_spec.weight))
            total_weight += grader_spec.weight
        
        # Weighted average
        weighted_score = sum(r.score * w for r, w in results) / total_weight
        
        return GraderResult(
            grader_type=self.name,
            score=weighted_score,
            passed=weighted_score >= spec.config.get("pass_threshold", 0.7),
            details={"individual_results": [r.model_dump() for r, _ in results]},
        )
```

---

## 3. Policy Engine Specification

### 3.1 Module Structure

```
dawn_kestrel/policy/
├── __init__.py
├── engine.py           # PolicyEngine protocol
├── contracts.py        # PolicyInput, PolicyOutput, ActionProposal
├── chain.py            # PolicyChain for composition
├── builtin/            # Built-in policies
│   ├── ranking.py
│   ├── budget.py
│   └── strategy.py
└── validators/         # Policy validators
```

### 3.2 Core Protocol

```python
from typing import Protocol
from enum import Enum
from pydantic import BaseModel

class Priority(str, Enum):
    P0 = "p0"  # Critical
    P1 = "p1"  # High
    P2 = "p2"  # Medium
    P3 = "p3"  # Low


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PolicyInput:
    """Input to a policy engine."""
    context: dict[str, Any]
    proposals: list["ActionProposal"]
    budget: "BudgetInfo"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionProposal:
    """A proposed action from a policy."""
    action_type: str
    priority: Priority
    score: float
    rationale: str
    confidence: float
    risk_level: RiskLevel
    violations: list[str] = field(default_factory=list)


@dataclass
class PolicyOutput:
    """Output from a policy engine."""
    actions: list[ActionProposal]
    rationale: str
    confidence: float
    constraints_checked: list[str] = field(default_factory=list)


class PolicyEngine(Protocol):
    """Protocol for policy-based decision engines."""
    
    def propose(self, input: PolicyInput) -> PolicyOutput:
        """Generate action proposals from input context."""
        ...
    
    def validate(self, proposal: ActionProposal) -> bool:
        """Validate a proposal against policy constraints."""
        ...
```

### 3.3 Policy Chain

```python
class PolicyChain:
    """Compose multiple policies into a pipeline.
    
    Usage:
        chain = PolicyChain([
            RankingPolicy(),
            BudgetPolicy(max_actions=10),
            StrategyPolicy(strategy_file="strategy.md"),
        ])
        
        output = chain.propose(input)
    """
    
    def __init__(self, policies: list[PolicyEngine]):
        self.policies = policies
    
    def propose(self, input: PolicyInput) -> PolicyOutput:
        current = input
        
        for policy in self.policies:
            output = policy.propose(current)
            current = PolicyInput(
                context=current.context,
                proposals=output.actions,
                budget=current.budget,
                metadata={"rationale": output.rationale},
            )
        
        return output
```

---

## 4. Transcript System Specification

### 4.1 Module Structure

```
dawn_kestrel/evaluation/transcript/
├── __init__.py
├── models.py           # Transcript, Phase, Event types
├── builder.py          # TranscriptBuilder
├── events.py           # Event types
├── budget.py           # Budget tracking
└── serialization.py    # NDJSON, pretty report
```

### 4.2 Core Models

```python
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class EventType(str, Enum):
    STATE_TRANSITION = "STATE_TRANSITION"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    MODEL_MESSAGE = "MODEL_MESSAGE"
    DELEGATION = "DELEGATION"
    ERROR = "ERROR"
    BUDGET_THRESHOLD = "BUDGET_THRESHOLD"


class TranscriptEvent(BaseModel):
    """A single event in the transcript."""
    id: str
    type: EventType
    timestamp: float
    phase: str | None = None
    data: dict[str, Any]
    duration_ms: float | None = None


class ToolCallRecord(BaseModel):
    """Record of a tool call."""
    tool: str
    input: dict[str, Any]
    output: Any
    success: bool
    duration_ms: float
    error: str | None = None


class PhaseRecord(BaseModel):
    """Record of an FSM phase."""
    name: str
    started_at: float
    ended_at: float | None = None
    events: list[TranscriptEvent] = []
    tokens_used: int = 0


class Transcript(BaseModel):
    """Complete execution transcript.
    
    Designed for portability - all data is embedded,
    no external references needed.
    """
    id: str
    session_id: str
    agent_name: str
    started_at: float
    ended_at: float | None = None
    
    # Embedded data
    messages: list["Message"]
    phases: list[PhaseRecord]
    tool_calls: list[ToolCallRecord]
    delegations: list["DelegationRecord"]
    errors: list[str]
    
    # Metrics
    timing: dict[str, float] = {}
    token_usage: dict[str, int] = {}
    cost_usd: float | None = None
    
    # Artifacts (file_path -> content)
    artifacts: dict[str, str] = {}
    
    def write_ndjson(self, path: Path) -> None:
        """Write as newline-delimited JSON for ML pipelines."""
        ...
    
    def write_pretty_report(self, path: Path) -> None:
        """Write as human-readable markdown report."""
        ...
```

### 4.3 Budget Tracking

```python
@dataclass
class BudgetUsage:
    """Current budget consumption."""
    iterations: int = 0
    tool_calls: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    elapsed_seconds: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "iterations": self.iterations,
            "tool_calls": self.tool_calls,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "elapsed_seconds": self.elapsed_seconds,
        }


class BudgetPolicy(BaseModel):
    """Budget constraints for execution."""
    max_iterations: int = 10
    max_tool_calls: int = 50
    max_tokens: int = 100_000
    max_cost_usd: float = 1.0
    max_seconds: float = 300.0
    
    def check(self, usage: BudgetUsage) -> list[str]:
        """Check if budget is exceeded, return list of violations."""
        violations = []
        if usage.iterations >= self.max_iterations:
            violations.append(f"iterations: {usage.iterations}/{self.max_iterations}")
        if usage.tool_calls >= self.max_tool_calls:
            violations.append(f"tool_calls: {usage.tool_calls}/{self.max_tool_calls}")
        if usage.tokens_used >= self.max_tokens:
            violations.append(f"tokens: {usage.tokens_used}/{self.max_tokens}")
        if usage.cost_usd >= self.max_cost_usd:
            violations.append(f"cost: ${usage.cost_usd:.2f}/${self.max_cost_usd:.2f}")
        if usage.elapsed_seconds >= self.max_seconds:
            violations.append(f"time: {usage.elapsed_seconds:.1f}s/{self.max_seconds:.1f}s")
        return violations
```

---

## 5. Tool Memory Specification

### 5.1 Module Structure

```
dawn_kestrel/learning/tool_memory/
├── __init__.py
├── manager.py          # ToolMemoryManager
├── models.py           # ToolMemory, ToolUsageEvent, etc.
└── storage.py          # JSON file storage
```

### 5.2 Core Models

```python
from enum import Enum
from pydantic import BaseModel

class OutcomeType(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    ABORTED = "aborted"


class ToolUsageEvent(BaseModel):
    """Record of a tool usage."""
    id: str
    tool_name: str
    timestamp: float
    trigger: str
    args: dict[str, Any]
    outcome: OutcomeType
    duration_ms: float
    context_signals: list[str] = []
    result_summary: str | None = None
    user_feedback: str | None = None
    session_id: str | None = None


class LearnedPattern(BaseModel):
    """A learned successful pattern."""
    pattern_id: str
    tool_name: str
    trigger_pattern: str
    suggested_args: dict[str, Any]
    success_rate: float
    sample_size: int
    avg_duration_ms: float
    notes: list[str] = []


class AntiPattern(BaseModel):
    """A pattern to avoid."""
    tool_name: str
    trigger_pattern: str
    problem: str
    better_alternative: str
    occurrences: int = 1


class ToolMemory(BaseModel):
    """Memory for a specific tool."""
    tool_name: str
    events: list[ToolUsageEvent] = []
    patterns: list[LearnedPattern] = []
    anti_patterns: list[AntiPattern] = []
```

### 5.3 Manager API

```python
class ToolMemoryManager:
    """Manages experiential learning for tools.
    
    Storage: .tool_memory/{tool_name}/memory.json
    
    Usage:
        manager = ToolMemoryManager()
        
        # Record usage
        await manager.record_event(
            tool_name="task",
            trigger="External library documentation",
            args={"subagent_type": "librarian"},
            outcome=OutcomeType.SUCCESS,
            duration_ms=3400,
            context_signals=["external_lib", "docs"],
        )
        
        # Get hints
        hints = manager.get_usage_hints("task", ["external_lib"])
        # ["For external_lib: use args {...} (85% success rate)"]
    """
    
    async def record_event(
        self,
        tool_name: str,
        trigger: str,
        args: dict[str, Any],
        outcome: OutcomeType,
        duration_ms: float,
        context_signals: list[str] | None = None,
        result_summary: str | None = None,
    ) -> Result[ToolUsageEvent]: ...
    
    def get_usage_hints(
        self,
        tool_name: str,
        context_signals: list[str],
    ) -> Result[list[str]]: ...
    
    async def add_pattern(
        self,
        tool_name: str,
        trigger_pattern: str,
        suggested_args: dict[str, Any],
        success_rate: float,
    ) -> Result[LearnedPattern]: ...
    
    async def add_anti_pattern(
        self,
        tool_name: str,
        trigger_pattern: str,
        problem: str,
        better_alternative: str,
    ) -> Result[AntiPattern]: ...
```

---

## 6. Circuit Breaker Specification

```python
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import time

class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject all calls
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    window_seconds: float = 60.0
    recovery_timeout_seconds: float = 30.0
    half_open_max_calls: int = 3


class CircuitBreaker:
    """Async-safe circuit breaker with sliding window.
    
    Usage:
        breaker = CircuitBreaker(CircuitBreakerConfig())
        
        async def safe_call():
            if not await breaker.can_execute():
                raise CircuitOpenError("Circuit is open")
            
            try:
                result = await risky_operation()
                await breaker.record_success()
                return result
            except Exception as e:
                await breaker.record_failure()
                raise
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self._state = CircuitState.CLOSED
        self._failures: list[float] = []
        self._half_open_calls = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()
    
    async def can_execute(self) -> bool:
        """Check if execution is allowed."""
        async with self._lock:
            await self._maybe_transition()
            
            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.OPEN:
                return False
            else:  # HALF_OPEN
                return self._half_open_calls < self.config.half_open_max_calls
    
    async def record_success(self) -> None:
        """Record successful execution."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failures.clear()
                self._half_open_calls = 0
    
    async def record_failure(self) -> None:
        """Record failed execution."""
        async with self._lock:
            now = time.monotonic()
            self._failures.append(now)
            self._last_failure_time = now
            
            # Sliding window: remove old failures
            cutoff = now - self.config.window_seconds
            self._failures = [t for t in self._failures if t > cutoff]
            
            if len(self._failures) >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
    
    async def _maybe_transition(self) -> None:
        """Check for state transitions."""
        now = time.monotonic()
        
        if (self._state == CircuitState.OPEN and 
            self._last_failure_time and
            now - self._last_failure_time >= self.config.recovery_timeout_seconds):
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0
```

---

## 7. Checkpoint/Resume Specification

```python
from pathlib import Path
from pydantic import BaseModel
import hashlib
import json
import tempfile

class CheckpointData(BaseModel):
    """Data to persist for checkpoint."""
    inputs_hash: str
    state: dict[str, Any]
    results: list[Any]
    metadata: dict[str, Any] = {}


class CheckpointManager:
    """Atomic checkpoint save/load.
    
    Usage:
        manager = CheckpointManager(Path(".checkpoints"))
        
        # Compute hash of inputs
        inputs_hash = manager.compute_inputs_hash(changed_files, diff)
        
        # Check for existing checkpoint
        existing = manager.load(inputs_hash)
        if existing:
            return existing  # Resume
        
        # ... do work ...
        
        # Save checkpoint
        manager.save(CheckpointData(
            inputs_hash=inputs_hash,
            state={"phase": "complete"},
            results=[...],
        ))
    """
    
    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def compute_inputs_hash(self, *inputs: Any) -> str:
        """Compute SHA-256 hash of inputs."""
        content = json.dumps(inputs, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def save(self, checkpoint: CheckpointData) -> Path:
        """Save checkpoint atomically (temp file + rename)."""
        path = self.checkpoint_dir / f"{checkpoint.inputs_hash}.json"
        
        # Atomic write: write to temp, then rename
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=self.checkpoint_dir,
            delete=False,
            suffix='.tmp'
        ) as f:
            f.write(checkpoint.model_dump_json(indent=2))
            temp_path = Path(f.name)
        
        temp_path.rename(path)
        return path
    
    def load(self, inputs_hash: str) -> CheckpointData | None:
        """Load checkpoint if exists."""
        path = self.checkpoint_dir / f"{inputs_hash}.json"
        
        if not path.exists():
            return None
        
        content = path.read_text()
        return CheckpointData.model_validate_json(content)
    
    def delete(self, inputs_hash: str) -> None:
        """Delete checkpoint."""
        path = self.checkpoint_dir / f"{inputs_hash}.json"
        if path.exists():
            path.unlink()
```

---

## 8. Skill System Specification

### 8.1 Module Structure

```
dawn_kestrel/skills/
├── __init__.py
├── base.py             # Skill protocol
├── loader.py           # SkillLoader
├── registry.py         # SkillRegistry
├── builtin/            # Built-in skills
│   ├── council/
│   ├── git_master/
│   └── playwright/
└── entry_points.py     # Entry point discovery
```

### 8.2 Core Protocol

```python
from typing import Protocol, Any
from pydantic import BaseModel

class SkillContext(BaseModel):
    """Context passed to skill execution."""
    runtime: "AgentRuntime"
    session_id: str
    tools: "ToolRegistry"
    params: dict[str, Any] = {}
    signals: set[str] = set()


class SkillResult(BaseModel):
    """Result from skill execution."""
    success: bool
    output: Any = None
    error: str | None = None
    suggestions: list[str] = []
    metadata: dict[str, Any] = {}


class Skill(Protocol):
    """Protocol for reusable skills.
    
    Skills are discovered from:
    - ./skills/
    - ~/.dawn-kestrel/skills/
    - Entry points (dawn_kestrel.skills)
    """
    
    @property
    def name(self) -> str:
        """Unique skill identifier."""
        ...
    
    @property
    def description(self) -> str:
        """Brief description of what this skill does."""
        ...
    
    @property
    def triggers(self) -> list[str]:
        """Keywords/phrases that suggest this skill."""
        ...
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute the skill."""
        ...


class SkillLoader:
    """Discover and load skills from filesystem.
    
    Usage:
        loader = SkillLoader()
        skills = loader.discover([
            Path("./skills"),
            Path.home() / ".dawn-kestrel" / "skills",
        ])
    """
    
    def discover(self, paths: list[Path]) -> list[Skill]:
        """Find all skills in given paths."""
        skills = []
        for base_path in paths:
            if not base_path.exists():
                continue
            for skill_dir in base_path.iterdir():
                if skill_dir.is_dir():
                    skill = self._load_skill(skill_dir)
                    if skill:
                        skills.append(skill)
        return skills
    
    def _load_skill(self, skill_dir: Path) -> Skill | None:
        """Load a skill from directory."""
        init_file = skill_dir / "__init__.py"
        if not init_file.exists():
            return None
        
        # Import and instantiate
        module = import_module_from_path(skill_dir)
        skill_class = getattr(module, "Skill", None)
        if skill_class:
            return skill_class()
        return None


class SkillRegistry:
    """Registry for skill lookup and execution.
    
    Usage:
        registry = SkillRegistry()
        registry.discover_and_register()
        
        # Find skill by trigger
        skill = registry.find_for_trigger("consult multiple agents")
        
        # Execute
        result = await skill.execute(context)
    """
    
    def __init__(self):
        self._skills: dict[str, Skill] = {}
    
    def register(self, skill: Skill) -> None:
        """Register a skill."""
        self._skills[skill.name] = skill
    
    def discover_and_register(self) -> int:
        """Discover skills from paths and entry points."""
        count = 0
        
        # Filesystem discovery
        loader = SkillLoader()
        for skill in loader.discover(self._get_search_paths()):
            self.register(skill)
            count += 1
        
        # Entry point discovery
        for entry_point in importlib.metadata.entry_points(
            group="dawn_kestrel.skills"
        ):
            skill_class = entry_point.load()
            self.register(skill_class())
            count += 1
        
        return count
    
    def find_for_trigger(self, text: str) -> Skill | None:
        """Find skill matching trigger phrase."""
        text_lower = text.lower()
        for skill in self._skills.values():
            for trigger in skill.triggers:
                if trigger.lower() in text_lower:
                    return skill
        return None
```

---

## 9. Entry Points

```toml
# pyproject.toml

[project.entry-points."dawn_kestrel.delegation_modes"]
bfs = "dawn_kestrel.delegation:BFSMode"
dfs = "dawn_kestrel.delegation:DFSMode"
adaptive = "dawn_kestrel.delegation:AdaptiveMode"

[project.entry-points."dawn_kestrel.graders"]
string_match = "dawn_kestrel.evaluation.graders.deterministic:StringMatchGrader"
test_runner = "dawn_kestrel.evaluation.graders.deterministic:TestRunnerGrader"
static_analysis = "dawn_kestrel.evaluation.graders.deterministic:StaticAnalysisGrader"
tool_call = "dawn_kestrel.evaluation.graders.deterministic:ToolCallGrader"
llm_judge = "dawn_kestrel.evaluation.graders.llm:LLMJudgeGrader"
composite = "dawn_kestrel.evaluation.graders.composite:CompositeGrader"

[project.entry-points."dawn_kestrel.skills"]
council = "dawn_kestrel.skills.builtin.council:CouncilSkill"
git_master = "dawn_kestrel.skills.builtin.git_master:GitMasterSkill"
playwright = "dawn_kestrel.skills.builtin.playwright:PlaywrightSkill"

[project.entry-points."dawn_kestrel.policies"]
ranking = "dawn_kestrel.policy.builtin.ranking:RankingPolicy"
budget = "dawn_kestrel.policy.builtin.budget:BudgetPolicy"
strategy = "dawn_kestrel.policy.builtin.strategy:StrategyPolicy"
```
