# Dawn Kestrel SDK Feature Analysis

**Generated:** 2026-03-06
**Projects Analyzed:** bolt-merlin, vox-jay, iron-rook, ash-hawk
**Purpose:** Identify features for SDK extraction to enable better agent projects

---

## Executive Summary

Analysis of four agent projects reveals **23 distinct features** that could be extracted into dawn-kestrel as SDK primitives. Features are categorized by criticality and impact on the agent ecosystem.

### Priority Matrix

| Priority | Features | Est. Effort | Impact |
|----------|----------|-------------|--------|
| **P0 Critical** | 6 | 3-4 weeks | Enables core evaluation, delegation, learning |
| **P1 High** | 8 | 4-6 weeks | Unlocks advanced patterns, cross-project reuse |
| **P2 Medium** | 6 | 3-4 weeks | Improves DX, reduces boilerplate |
| **P3 Nice-to-have** | 3 | 2-3 weeks | Quality of life improvements |

---

## Critical Features (P0)

### 1. Multi-Agent Delegation Engine

**Source:** bolt-merlin (`delegation/engine.py`)
**Criticality:** P0 - Core orchestration primitive

**What it does:**
- Executes delegation trees with BFS/DFS/Adaptive traversal strategies
- Budget enforcement (depth, breadth, time, agent count)
- Convergence detection for early termination
- Callback hooks for progress tracking

**Why it belongs in SDK:**
- Every multi-agent project needs delegation
- Pattern is identical across bolt-merlin, iron-rook, future projects
- Complex logic that shouldn't be reimplemented

**Current Implementation:**
```python
class DelegationEngine:
    """Convergence-aware delegation engine with BFS/DFS strategies."""
    
    async def delegate(
        self,
        agent_name: str,
        prompt: str,
        session_id: str,
        children: Optional[List[Dict[str, Any]]] = None,
    ) -> Result[DelegationResult]:
        if self.config.mode == TraversalMode.BFS:
            await self._execute_bfs(...)
        elif self.config.mode == TraversalMode.DFS:
            await self._execute_dfs(...)
        else:  # ADAPTIVE
            await self._execute_adaptive(...)
```

**SDK Integration:**
```python
from dawn_kestrel.delegation import DelegationEngine, DelegationConfig, TraversalMode

config = DelegationConfig(
    mode=TraversalMode.ADAPTIVE,
    budget=DelegationBudget(
        max_depth=5,
        max_breadth=10,
        max_total_agents=50,
        max_wall_time_seconds=300,
    ),
    check_convergence=True,
    on_agent_spawn=my_callback,
)

engine = DelegationEngine(config, runtime, registry)
result = await engine.delegate("orchestrator", prompt, session_id, children=children)
```

---

### 2. Evaluation Grading Framework

**Source:** ash-hawk (`graders/`)
**Criticality:** P0 - Foundation for all evaluation

**What it does:**
- Abstract grader interface with standardized `grade()` method
- Multi-layer grading: deterministic → LLM → composite
- Weighted aggregation of multiple grader results
- Rubric guards and normalization

**Why it belongs in SDK:**
- All agent projects need evaluation
- Grader interface should be standardized
- Allows projects to share grader implementations

**Current Implementation:**
```python
class Grader(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    async def grade(
        self,
        trial: EvalTrial,
        transcript: EvalTranscript,
        spec: GraderSpec,
    ) -> GraderResult: ...
```

**SDK Integration:**
```python
from dawn_kestrel.evaluation.graders import Grader, GraderResult, GraderSpec

class MyCustomGrader(Grader):
    @property
    def name(self) -> str:
        return "my_custom"
    
    async def grade(self, trial, transcript, spec) -> GraderResult:
        # Custom grading logic
        return GraderResult(
            grader_type=self.name,
            score=0.85,
            passed=True,
            details={"reason": "..."}
        )
```

---

### 3. Policy Engine

**Source:** vox-jay (`policies/`), dawn-kestrel (`policy/`)
**Criticality:** P0 - Decision making layer

**What it does:**
- Composable policy chain for action decisions
- Master policy orchestration of sub-policies
- Budget constraints and strategy validation
- Action proposal → validation → approval pipeline

**Why it belongs in SDK:**
- Policy patterns are universal for agent behavior
- Separates decision logic from execution
- Enables pluggable agent behaviors

**Current Implementation:**
```python
class MasterPolicy:
    """Master orchestration policy that coordinates all sub-policies."""
    
    def propose(self, input: PolicyInput) -> PolicyOutput:
        # Step 1: Score with RankingPolicy
        ranking_output = self.ranking_policy.score(input)
        
        # Step 2: Get action proposals from EngagementPolicy
        engagement_output = self.engagement_policy.propose(ranked_input)
        
        # Step 3: Validate with StrategyPolicy
        validation_output = self.strategy_policy.validate(validation_input)
        
        # Step 4: Filter by budget
        final_actions = self._apply_budget(approved_actions, input)
        
        return PolicyOutput(actions=final_actions, ...)
```

**SDK Integration:**
```python
from dawn_kestrel.policy import Policy, PolicyChain, PolicyInput, PolicyOutput

class MyPolicy(Policy):
    async def propose(self, input: PolicyInput) -> PolicyOutput:
        ...

chain = PolicyChain([
    RankingPolicy(),
    EngagementPolicy(),
    StrategyPolicy(),
])
result = await chain.propose(context)
```

---

### 4. Transcript/Trace Capture

**Source:** dawn-kestrel (`evaluation/models.py`), ash-hawk
**Criticality:** P0 - Evaluation requires full traces

**What it does:**
- Captures complete conversation transcripts
- Embeds messages for portability
- Tracks timing, tool calls, phases
- Enables replay and analysis

**Why it belongs in SDK:**
- All evaluation requires transcript data
- Must be captured at SDK level, not agent level
- Enables debugging, analysis, grading

**Current Implementation:**
```python
class Transcript(BaseModel):
    id: str
    session_id: str
    messages: list[Message]  # Embedded for portability
    timing: dict[str, float] = Field(default_factory=dict)
```

**SDK Integration:**
- Already partially in SDK
- Needs: phase tracking, tool call extraction, event stream

---

### 5. Agent Execution Queue

**Source:** bolt-merlin (uses dawn-kestrel's `InMemoryAgentExecutionQueue`)
**Criticality:** P0 - Parallel execution foundation

**What it does:**
- Manages concurrent agent execution
- Timeout handling per-job
- Error isolation between jobs
- Batch result collection

**Why it belongs in SDK:**
- Parallel delegation requires queue
- Concurrency control is complex
- Already partially implemented

**Current Implementation:**
```python
class InMemoryAgentExecutionQueue:
    async def run_jobs(
        self,
        jobs: list[AgentExecutionJob],
        execute: Callable[[AgentExecutionJob], Awaitable[str]]
    ) -> BatchResult:
        # Execute with concurrency control
        ...
```

**SDK Integration:**
- Already in SDK, needs enhancement
- Add: priority queues, retry policies, cancellation

---

### 6. Skill System

**Source:** bolt-merlin (`skills/`)
**Criticality:** P0 - Extensibility mechanism

**What it does:**
- File-based skill discovery
- Registry for skill lookup
- Entry point registration
- Council skill for multi-agent consultation

**Why it belongs in SDK:**
- Skills are universal extension mechanism
- Discovery should be standardized
- Enables cross-project skill sharing

**Current Implementation:**
```python
class SkillLoader:
    """File-based skill discovery."""
    
    def discover_skills(self, paths: list[Path]) -> list[Skill]:
        # Search .bolt_merlin/skills/, .opencode/skill/, .claude/skills/
        ...
```

**SDK Integration:**
```python
from dawn_kestrel.skills import SkillLoader, SkillRegistry

loader = SkillLoader()
skills = loader.discover(["./skills", "~/.dawn-kestrel/skills"])
registry = SkillRegistry(skills)

skill = registry.get("council")
await skill.execute(context)
```

---

## High Priority Features (P1)

### 7. Tool Memory / Experiential Learning

**Source:** bolt-merlin (`tool_memory/`)
**Criticality:** P1 - Learning from experience

**What it does:**
- Records tool usage events with context
- Learns successful patterns
- Tracks anti-patterns to avoid
- Provides context-aware hints

**Why it belongs in SDK:**
- Learning should persist across sessions
- All agents benefit from experience
- Reduces repeated mistakes

**Current Implementation:**
```python
class ToolMemoryManager:
    async def record_event(
        self,
        tool_name: str,
        trigger: str,
        args: Dict[str, Any],
        outcome: OutcomeType,
        duration_ms: float,
        context_signals: Optional[List[str]] = None,
    ) -> Result[ToolUsageEvent]:
        ...
    
    def get_usage_hints(
        self,
        tool_name: str,
        context_signals: List[str],
    ) -> Result[List[str]]:
        ...
```

---

### 8. Convergence Detection

**Source:** bolt-merlin (`delegation/convergence.py`)
**Criticality:** P1 - Prevent infinite loops

**What it does:**
- Tracks result novelty via signature hashing
- Detects stagnation (repeated similar results)
- Enables early termination

**Why it belongs in SDK:**
- All delegation needs convergence detection
- Prevents runaway agent execution
- Saves cost and time

---

### 9. Agent Harness CLI Framework

**Source:** bolt-merlin (`cli/`)
**Criticality:** P1 - Developer experience

**What it does:**
- 10 CLI commands: profile, map, search, summarize, plan, apply, run, memory, sandbox, metrics
- Metrics collection and export
- Working memory management
- Sandbox environment management

**Why it belongs in SDK:**
- All agent projects need similar CLI
- Reduces boilerplate
- Standardizes repository interaction

---

### 10. FSM + Subagent Pattern

**Source:** iron-rook (`review/agents/`)
**Criticality:** P1 - Complex agent orchestration

**What it does:**
- FSM-driven state transitions
- Subagent delegation per phase
- Phase-specific budgeting
- Checkpoint/recovery

**Why it belongs in SDK:**
- Complex agents need FSM patterns
- Subagent delegation is common
- State management is hard

---

### 11. Budget Tracking

**Source:** iron-rook, bolt-merlin
**Criticality:** P1 - Cost control

**What it does:**
- Token counting per phase
- Dollar cost estimation
- Budget thresholds and alerts
- Graceful degradation on budget exhaustion

**Why it belongs in SDK:**
- All LLM usage needs budget control
- Prevents runaway costs
- Enables SLA guarantees

---

### 12. Review Workflow System

**Source:** iron-rook (`review/`)
**Criticality:** P1 - Code review agents

**What it does:**
- Multi-reviewer orchestration
- Finding aggregation
- Merge decision logic
- Streaming output

**Why it belongs in SDK:**
- Code review is a major agent use case
- Pattern is reusable across projects

---

### 13. Judge Normalization

**Source:** ash-hawk, iron-rook (`graders/judge_normalizer.py`)
**Criticality:** P1 - Evaluation reliability

**What it does:**
- Normalizes LLM judge scores to [0, 1]
- Handles different rubric scales
- Provides consistent grading

**Why it belongs in SDK:**
- All evaluation needs normalized scores
- LLM judges are inconsistent
- Enables fair comparison

---

### 14. Circuit Breaker

**Source:** iron-rook, dawn-kestrel
**Criticality:** P1 - Reliability

**What it does:**
- Prevents cascade failures
- Automatic recovery
- Configurable thresholds

**Why it belongs in SDK:**
- All external calls need protection
- Already partially implemented
- Critical for reliability

---

## Medium Priority Features (P2)

### 15. Source Registry Pattern

**Source:** vox-jay (`sources/`)
**Criticality:** P2 - Data ingestion

**What it does:**
- Plugin-based data source system
- Standardized fetch interface
- Source discovery and registration

**Why useful:** Enables agents to pull from multiple data sources

---

### 16. Channel System

**Source:** vox-jay (`channels/`)
**Criticality:** P2 - Output routing

**What it does:**
- Obsidian vault integration
- Webhook output (Slack, Discord)
- Formatters (Markdown, JSON)

**Why useful:** Agents need to output to multiple destinations

---

### 17. Stress Test Fixtures

**Source:** iron-rook (`eval/fixtures/stress/`)
**Criticality:** P2 - Testing edge cases

**What it does:**
- Massive files, deep nesting, unicode chaos
- Timeout scenarios, resource exhaustion
- False positive traps

**Why useful:** Shared test fixtures for all agent projects

---

### 18. Phase Logger

**Source:** iron-rook
**Criticality:** P2 - Debugging

**What it does:**
- Structured logging per FSM phase
- Timing capture
- Event correlation

**Why useful:** Debugging complex agent flows

---

### 19. Evidence Cache

**Source:** iron-rook
**Criticality:** P2 - Performance

**What it does:**
- Caches analysis results
- Reuses evidence across subagents
- Reduces redundant work

**Why useful:** Speeds up repeated analysis

---

### 20. Calibration Metrics

**Source:** ash-hawk (`calibration/`)
**Criticality:** P2 - Evaluation quality

**What it does:**
- Expected Calibration Error (ECE)
- Brier score
- Reliability diagrams

**Why useful:** Ensures evaluation confidence is meaningful

---

## Nice-to-Have Features (P3)

### 21. Working Memory

**Source:** bolt-merlin (`cli/memory/`)
**Criticality:** P3 - Session persistence

**What it does:**
- JSON-based context storage
- Run ID tracking
- Decision history

---

### 22. Repository Profile

**Source:** bolt-merlin (`cli/profile/`)
**Criticality:** P3 - Codebase understanding

**What it does:**
- Language detection
- Build system identification
- Structure mapping

---

### 23. Obsidian Review Workflow

**Source:** vox-jay (`harness/review.py`)
**Criticality:** P3 - Human-in-the-loop

**What it does:**
- Inbox notes for human review
- Draft extraction
- Feedback collection

---

## Integration with ash-hawk Evaluation

Dawn-kestrel should provide **evaluation hooks** that ash-hawk can consume:

### Required SDK Primitives

1. **Transcript Capture Hook**
   ```python
   # SDK provides:
   session.on_transcript_ready(lambda t: evaluator.record(t))
   ```

2. **Tool Call Logging**
   ```python
   # SDK provides:
   session.on_tool_call(lambda call: evaluator.track_tool(call))
   ```

3. **Phase Transitions**
   ```python
   # SDK provides:
   fsm.on_phase_complete(lambda phase: evaluator.record_phase(phase))
   ```

4. **Budget Events**
   ```python
   # SDK provides:
   budget.on_threshold(lambda pct: evaluator.check_budget(pct))
   ```

### Evaluation Pipeline

```
Agent Execution → SDK Hooks → Transcript → Graders → Results
                      ↓
                ash-hawk consumes
```

---

## Recommendations

### Immediate Actions (P0)

1. **Extract DelegationEngine** to `dawn_kestrel.delegation`
2. **Standardize Grader interface** in `dawn_kestrel.evaluation.graders`
3. **Formalize Policy system** in `dawn_kestrel.policy`
4. **Enhance Transcript capture** with phase tracking
5. **Improve Execution Queue** with priority/cancellation
6. **Move Skill discovery** to SDK core

### Next Phase (P1)

1. Add Tool Memory as optional plugin
2. Enhance convergence detection
3. Create CLI framework module
4. Formalize FSM + Subagent pattern
5. Improve budget tracking
6. Extract Review workflow primitives
7. Standardize judge normalization
8. Formalize circuit breaker

### Documentation Needs

- `skills.md` - Skill authoring guide
- `specs/` - Technical specifications per feature
- `prd/` - Product requirements documents
- `feature-options.md` - Design alternatives

---

## File Reference

| Feature | Source Files | Target Location |
|---------|-------------|-----------------|
| Delegation | `bolt-merlin/delegation/` | `dawn_kestrel/delegation/` |
| Grading | `ash-hawk/graders/` | `dawn_kestrel/evaluation/graders/` |
| Policy | `vox-jay/policies/`, `dawn_kestrel/policy/` | `dawn_kestrel/policy/` |
| Tool Memory | `bolt-merlin/tool_memory/` | `dawn_kestrel/learning/` |
| Skills | `bolt-merlin/skills/` | `dawn_kestrel/skills/` |
| CLI | `bolt-merlin/cli/` | `dawn_kestrel/cli/framework/` |
| Review | `iron-rook/review/` | `dawn_kestrel/review/` |
