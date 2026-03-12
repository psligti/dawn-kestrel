# Dawn Kestrel SDK - Feature Options & Descriptions

**Version:** 1.0
**Date:** 2026-03-06

This document describes each feature option, design alternatives, and recommendations.

---

## 1. Delegation Engine

### Description

Multi-agent delegation system that orchestrates task distribution across specialized agents with configurable traversal strategies and convergence detection.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Unified Engine** | Single `DelegationEngine` class with mode parameter | Simple API, less flexibility per mode |
| **B. Strategy Pattern** | `DelegationStrategy` protocol with BFS/DFS/Adaptive implementations | More flexible, more code |
| **C. Functional** | Pure functions `delegate_bfs()`, `delegate_dfs()`, `delegate_adaptive()` | Simplest, no state management |

### Recommendation: Option A (Unified Engine)

**Rationale**:
- Single class easier to configure and test
- Mode switching at runtime (useful for adaptive)
- Shared convergence logic across modes
- Consistent callback interface

### Configuration

```python
# Simple
engine = DelegationEngine(
    mode=TraversalMode.ADAPTIVE,
)

# Full
engine = DelegationEngine(
    mode=TraversalMode.ADAPTIVE,
    budget=DelegationBudget(
        max_depth=5,
        max_breadth=10,
        max_total_agents=50,
        max_wall_time_seconds=300,
    ),
    check_convergence=True,
    max_concurrency=4,
    on_agent_spawn=log_spawn,
    on_agent_complete=log_complete,
)
```

---

## 2. Evaluation Grading Framework

### Description

Standardized grading interface for evaluating agent outputs with multi-layer support (deterministic → LLM → composite).

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Registry-based** | `GraderRegistry` with entry point discovery | Extensible, requires registration |
| **B. Decorator-based** | `@grader("type")` decorator on functions | Simple authoring, less structure |
| **C. Class-only** | Only classes implementing `Grader` | Type-safe, more boilerplate |

### Recommendation: Option A (Registry-based)

**Rationale**:
- Consistent with tool/provider patterns
- Entry points enable package distribution
- Runtime registration for testing
- Clear separation of concerns

### Grader Types

```
Layer 1: Deterministic (fast, no cost)
├── string_match     # Exact/contains/regex matching
├── test_runner      # Execute pytest/unittest
├── static_analysis  # Run linters
├── tool_call        # Verify tool call patterns
└── trace_assertions # Verify event sequences

Layer 2: LLM-Based (flexible, costs money)
├── llm_judge        # Quality assessment via LLM
└── code_review      # Code quality evaluation

Layer 3: Composite (aggregation)
├── composite        # Weighted combination
└── aggregation      # Statistical aggregation
```

### Configuration

```yaml
# In eval suite YAML
grader_specs:
  - grader_type: test_runner
    config:
      test_file: ./tests/test_func.py
    weight: 0.5
    
  - grader_type: llm_judge
    config:
      rubric: code_quality
      pass_threshold: 0.7
      n_judges: 2
    weight: 0.5
```

---

## 3. Policy Engine

### Description

Composable policy system for controlling agent behavior through proposal/validation cycles.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Protocol-based** | `Policy` protocol with `propose()` method | Flexible, requires implementation |
| **B. Rule Engine** | YAML/JSON rule definitions | Declarative, less expressive |
| **C. FSM-based** | State machine per policy | Visual, complex to compose |

### Recommendation: Option A (Protocol-based)

**Rationale**:
- Maximum flexibility for domain-specific logic
- Composable via `PolicyChain`
- Type-safe with Pydantic contracts
- Testable in isolation

### Policy Chain Pattern

```
Input → RankingPolicy → EngagementPolicy → StrategyPolicy → Output
            ↓                  ↓                  ↓
        Score items      Propose actions    Validate against strategy
```

### Example Policies

```python
# Ranking: Score items by multiple dimensions
class RankingPolicy:
    def propose(self, input: PolicyInput) -> PolicyOutput:
        for item in input.items:
            item.score = (
                item.relevance * 0.25 +
                item.novelty * 0.20 +
                item.proof * 0.20 +
                item.relationship * 0.20 +
                item.distribution * 0.15
            )
        return PolicyOutput(items=sorted(input.items, key=lambda x: -x.score))

# Engagement: Decide action types
class EngagementPolicy:
    def propose(self, input: PolicyInput) -> PolicyOutput:
        actions = []
        for item in input.items:
            if item.score > 0.8:
                actions.append(Action(type="reply", item=item))
            elif item.score > 0.5:
                actions.append(Action(type="like", item=item))
        return PolicyOutput(actions=actions)

# Strategy: Validate against constraints
class StrategyPolicy:
    def propose(self, input: PolicyInput) -> PolicyOutput:
        valid = []
        for action in input.proposed_actions:
            if not self._violates_strategy(action):
                valid.append(action)
        return PolicyOutput(actions=valid)
```

---

## 4. Transcript/Trace Capture

### Description

Complete execution capture for evaluation, debugging, and replay.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Embedded** | All data in Transcript model | Portable, memory-intensive |
| **B. Streaming** | Events written to file during execution | Low memory, requires file access |
| **C. Hybrid** | Embedded messages, streaming events | Balanced complexity |

### Recommendation: Option C (Hybrid)

**Rationale**:
- Messages are typically small (embed for portability)
- Tool calls can be large (stream for performance)
- Two-stream output (NDJSON + pretty report)

### Output Formats

```
.ndjson     Machine-readable, one event per line
.json       Complete transcript in one file
.md         Human-readable report
.html       Interactive visualization (optional)
```

### Hooks for Evaluation

```python
# SDK provides hooks that evaluation can attach to
session.on_transcript_ready(lambda t: evaluator.record(t))
session.on_tool_call(lambda c: evaluator.track_tool(c))
session.on_phase_complete(lambda p: evaluator.record_phase(p))
```

---

## 5. Skill System

### Description

Extensible capability system with automatic discovery and registration.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. File-based** | Skills in `.dawn-kestrel/skills/` | Simple, no packaging |
| **B. Entry Points** | Skills via `dawn_kestrel.skills` group | Package-friendly, requires install |
| **C. Both** | File discovery + entry points | Maximum flexibility |

### Recommendation: Option C (Both)

**Rationale**:
- Local development: file-based (no install)
- Distribution: entry points (proper packaging)
- Matches tool/provider patterns

### Discovery Order

```
1. ./skills/                    # Project-specific
2. ~/.dawn-kestrel/skills/      # User-level
3. Entry points                  # Installed packages
```

### Skill Structure

```
skills/
└── my_skill/
    ├── __init__.py      # Skill class
    ├── skill.md         # Documentation/prompt
    └── templates/       # Optional resources
```

---

## 6. Tool Memory / Experiential Learning

### Description

Learning system that captures tool usage patterns and provides context-aware hints.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. JSON Files** | `.tool_memory/{tool}/memory.json` | Simple, git-friendly |
| **B. SQLite** | Single database for all tools | Queryable, migration needed |
| **C. Vector DB** | Embedding-based similarity | Smart retrieval, complexity |

### Recommendation: Option A (JSON Files)

**Rationale**:
- Easiest to implement and debug
- Git-friendly (can version control)
- Easy to delete/clear
- Sufficient for current use cases

### Storage Structure

```
.tool_memory/
├── task/
│   └── memory.json
├── read/
│   └── memory.json
└── librarian/
    └── memory.json
```

### Memory Contents

```json
{
  "tool_name": "task",
  "events": [
    {
      "trigger": "External library docs",
      "args": {"subagent_type": "librarian"},
      "outcome": "success",
      "duration_ms": 3400,
      "context_signals": ["external_lib", "docs"]
    }
  ],
  "patterns": [
    {
      "trigger_pattern": "external_lib",
      "suggested_args": {"subagent_type": "librarian", "run_in_background": true},
      "success_rate": 0.85
    }
  ],
  "anti_patterns": [
    {
      "trigger_pattern": "simple typo",
      "problem": "Overkill for trivial issues",
      "better_alternative": "Use edit tool directly"
    }
  ]
}
```

---

## 7. Budget Tracking

### Description

Comprehensive resource tracking with threshold alerts and enforcement.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Global Only** | Single budget per session | Simple, less control |
| **B. Hierarchical** | Budget per agent/delegation level | Fine-grained, complex |
| **C. Tag-based** | Budgets tagged by category | Flexible, requires planning |

### Recommendation: Option B (Hierarchical)

**Rationale**:
- Matches delegation hierarchy
- Per-agent isolation
- Rollup aggregation for totals

### Budget Dimensions

```
- Iterations: Number of reasoning cycles
- Tool calls: Total tool invocations
- Tokens: Input + output + reasoning
- Cost: USD based on token pricing
- Time: Wall-clock seconds
```

### Enforcement Points

```python
# Check before tool call
if not budget.can_make_tool_call():
    return Err("Budget exceeded: tool calls")

# Check after LLM response
budget.record_tokens(usage.input_tokens, usage.output_tokens)
if budget.is_cost_exceeded():
    raise BudgetExceededError(f"Cost: ${budget.cost_usd:.2f}")
```

---

## 8. Circuit Breaker

### Description

Resilience pattern for external calls with automatic recovery.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Fixed Window** | Reset failures after time window | Simple, can miss bursts |
| **B. Sliding Window** | Only count recent failures | More accurate, slightly complex |
| **C. Token Bucket** | Allow burst before opening | Smooth, harder to tune |

### Recommendation: Option B (Sliding Window)

**Rationale**:
- Most accurate failure detection
- Handles burst failures correctly
- Async-safe implementation (asyncio.Lock)

### State Transitions

```
         failures >= threshold
    CLOSED ─────────────────────► OPEN
        ▲                            │
        │                            │ recovery timeout
        │                            ▼
        └────────────────────── HALF_OPEN
          success                       │
                                       │ failure
                                       └──────► OPEN
```

---

## 9. Checkpoint/Resume

### Description

Atomic state persistence for recovery from interruption.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Full State** | Serialize entire execution state | Complete recovery, large files |
| **B. Phase Snapshots** | Snapshot at phase boundaries | Smaller, coarser recovery |
| **C. Input Hash** | Only cache results, re-run on miss | Simplest, may waste work |

### Recommendation: Option B (Phase Snapshots)

**Rationale**:
- Natural boundaries in FSM phases
- Reasonable file sizes
- Clear recovery points

### Implementation

```python
# Atomic write pattern
with tempfile.NamedTemporaryFile(delete=False) as f:
    f.write(json.dumps(checkpoint))
    temp_path = Path(f.name)

temp_path.rename(final_path)  # Atomic on POSIX
```

---

## 10. FSM + Subagent Pattern

### Description

ReAct-style base class for iterative reasoning agents.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Fixed Phases** | INTAKE → PLAN → ACT → SYNTHESIZE → DONE | Simple, less flexible |
| **B. Configurable** | Phases defined in config | Flexible, harder to reason about |
| **C. Graph-based** | Arbitrary phase graph | Maximum flexibility, complexity |

### Recommendation: Option A (Fixed Phases)

**Rationale**:
- Proven pattern from iron-rook
- Clear mental model
- Easier to debug
- Convergence logic well-understood

### Phase Responsibilities

| Phase | Responsibility | Output |
|-------|---------------|--------|
| INTAKE | Understand input, set goals | Goals, constraints, evidence |
| PLAN | Decide next action | Todo list or action |
| ACT | Execute tool or delegate | Results, new evidence |
| SYNTHESIZE | Process results | Updated understanding |
| DONE | Final state | Final output |

### Stagnation Detection

```python
# Stop if:
# 1. Zero findings for N iterations (stuck)
# 2. Same findings for M iterations (converged)
# 3. Budget exceeded
# 4. Max iterations reached

def should_stop(self) -> bool:
    if len(self.recent_findings) == 0:
        self.stagnation_count += 1
        if self.stagnation_count >= self.stagnation_threshold:
            return True
    return False
```

---

## 11. Judge Normalization

### Description

Consistent LLM judge scoring across different models and rubrics.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Scale Mapping** | Map model outputs to [0, 1] | Simple, model-specific tuning |
| **B. Calibration** | Fit to ground truth data | Accurate, requires labeled data |
| **C. Ranking** | Relative ranking vs absolute scores | Avoids scale issues, less info |

### Recommendation: Option A (Scale Mapping)

**Rationale**:
- Quick to implement
- Model-specific config
- Good enough for most use cases

### Normalization Config

```python
NORMALIZATION_CONFIGS = {
    "claude-3-opus": {
        "min_score": 1,
        "max_score": 10,
        "pass_threshold": 7,
    },
    "gpt-4": {
        "min_score": 0,
        "max_score": 100,
        "pass_threshold": 70,
    },
}

def normalize(score: float, model: str) -> float:
    config = NORMALIZATION_CONFIGS[model]
    return (score - config["min_score"]) / (config["max_score"] - config["min_score"])
```

### Multi-Judge Consensus

```python
def aggregate(scores: list[float], method: str) -> float:
    if method == "mean":
        return statistics.mean(scores)
    elif method == "median":
        return statistics.median(scores)
    elif method == "min":
        return min(scores)
    elif method == "all_must_pass":
        return min(scores)  # But fail if any < threshold
```

---

## 12. CLI Framework

### Description

Standard CLI commands for agent projects.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Click** | Use Click framework | Simple, widely used |
| **B. Typer** | Use Typer (Click wrapper) | Type hints, less control |
| **C. Rich CLI** | Use Rich for all output | Beautiful, larger dependency |

### Recommendation: Option A (Click) + Rich (for output)

**Rationale**:
- Click for structure (proven, stable)
- Rich for output formatting
- Matches existing dawn-kestrel patterns

### Standard Commands

```
dawn-kestrel
├── profile    # Repository profiling
├── map        # Code map generation
├── search     # Pattern search
├── summarize  # File/directory summarization
├── plan       # Implementation planning
├── apply      # Patch application
├── run        # Test/build execution
├── memory     # Working memory management
├── sandbox    # Environment management
└── metrics    # Execution metrics
```

---

## 13. Source Registry

### Description

Plugin-based data source system with async parallel fetching.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. Sync Only** | All sources sync | Simple, blocking |
| **B. Async Only** | All sources async | Fast, requires async |
| **C. Both** | Support both sync and async | Flexible, more code |

### Recommendation: Option B (Async Only)

**Rationale**:
- Parallel fetching is key benefit
- Use `asyncio.to_thread()` for sync sources
- Consistent interface

### Source Protocol

```python
class BaseSource(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    async def fetch(self, limit: int) -> list[Item]: ...
    
    async def health_check(self) -> bool:
        try:
            await self.fetch(limit=1)
            return True
        except:
            return False
```

---

## 14. Channel System

### Description

Pluggable output channels for publishing results.

### Feature Options

| Option | Description | Trade-offs |
|--------|-------------|------------|
| **A. File-based** | Only file outputs | Simple, limited |
| **B. Webhook-based** | Only HTTP webhooks | Real-time, network dependency |
| **C. Both** | Files + webhooks + custom | Maximum flexibility |

### Recommendation: Option C (Both)

**Rationale**:
- Local dev needs file output
- CI/CD needs webhooks
- Custom channels for special cases

### Built-in Channels

```
channels/
├── file.py        # Write to file system
├── obsidian.py    # Obsidian vault integration
├── slack.py       # Slack webhook
├── discord.py     # Discord webhook
└── stdout.py      # Console output
```

---

## Summary: Recommended Configuration

| Feature | Recommended Option | Key Rationale |
|---------|-------------------|---------------|
| Delegation | Unified Engine | Simple API, shared convergence |
| Grading | Registry-based | Extensible, entry points |
| Policy | Protocol-based | Maximum flexibility |
| Transcript | Hybrid | Balance portability/performance |
| Skills | Both (files + entry points) | Dev + distribution |
| Tool Memory | JSON Files | Simple, git-friendly |
| Budget | Hierarchical | Matches delegation structure |
| Circuit Breaker | Sliding Window | Accurate failure detection |
| Checkpoint | Phase Snapshots | Natural boundaries |
| FSM Subagent | Fixed Phases | Proven pattern |
| Judge Normalization | Scale Mapping | Quick, effective |
| CLI | Click + Rich | Proven, beautiful |
| Source Registry | Async Only | Parallel fetching |
| Channels | Both | Flexibility |

---

## Implementation Priority

### Phase 1 (Weeks 1-3)
1. Delegation Engine
2. Grading Framework
3. Policy Engine
4. Transcript Capture

### Phase 2 (Weeks 4-6)
5. Tool Memory
6. Budget Tracking
7. Circuit Breaker
8. Checkpoint/Resume

### Phase 3 (Weeks 7-8)
9. FSM Subagent Base
10. Skill System
11. Judge Normalization

### Phase 4 (Weeks 9-10)
12. CLI Framework
13. Source Registry
14. Channel System
