# Dawn Kestrel SDK Evolution - Product Requirements Document

**Version:** 1.0
**Date:** 2026-03-06
**Status:** Draft
**Author:** SDK Evolution Analysis

---

## 1. Executive Summary

Dawn-kestrel is the foundational AI agent SDK that enables multiple agent projects (bolt-merlin, vox-jay, iron-rook, ash-hawk). This PRD defines requirements for evolving dawn-kestrel into a world-class agent development platform that is **magnitudes bigger, faster, and more capable**.

### Vision Statement

> Dawn-kestrel should be the **definitive SDK for building production AI agents** - providing every primitive needed for delegation, evaluation, learning, and reliability out of the box.

---

## 2. Problem Statement

### Current State

Each agent project has independently developed:
- **bolt-merlin**: Delegation engine, tool memory, CLI harness, skills system
- **vox-jay**: Policy-based decisions, source registry, channel system
- **iron-rook**: Transcript system, budget tracking, circuit breaker, checkpoint/resume
- **ash-hawk**: Grading framework, evaluation runner, policy enforcement

### Pain Points

1. **Duplication**: Similar patterns reimplemented across projects
2. **Inconsistency**: Different interfaces for the same concepts
3. **Missing Primitives**: Some projects lack features others have
4. **Integration Friction**: Each project must build its own SDK adapter
5. **No Learning**: Insights from one project don't benefit others

---

## 3. Goals & Success Metrics

### Primary Goals

| Goal | Metric | Target |
|------|--------|--------|
| Reduce boilerplate | Lines of code per agent | -60% |
| Improve reliability | Agent execution success rate | 99.5% |
| Enable evaluation | % agents with eval suites | 100% |
| Accelerate development | Time to new agent MVP | <2 days |
| Share learning | Cross-project skill reuse | >10 skills |

### Success Criteria

- [ ] New agent project scaffold in <30 minutes
- [ ] Built-in evaluation from day one
- [ ] Delegation works out of the box
- [ ] Budget/cost control is automatic
- [ ] Learning persists across sessions

---

## 4. Feature Requirements

### P0: Core Primitives (Critical)

#### 4.1 Delegation Engine

**Requirement**: Multi-agent delegation with BFS/DFS/Adaptive traversal

**User Stories**:
- As an agent developer, I want to delegate subtasks to specialized agents
- As an agent developer, I want automatic convergence detection to avoid infinite loops
- As an agent developer, I want budget enforcement (depth, breadth, time, cost)

**Acceptance Criteria**:
- [ ] `DelegationEngine` class with configurable traversal modes
- [ ] Automatic convergence detection via SHA-256 hashing
- [ ] Budget enforcement with configurable limits
- [ ] Callbacks for progress tracking
- [ ] Graceful degradation on partial failures

**Source**: bolt-merlin `delegation/engine.py`

---

#### 4.2 Evaluation Grading Framework

**Requirement**: Standardized grading interface with multi-layer support

**User Stories**:
- As an agent developer, I want to evaluate my agents with multiple graders
- As an agent developer, I want LLM-based judging with rubric support
- As an agent developer, I want weighted aggregation of grader results

**Acceptance Criteria**:
- [ ] Abstract `Grader` protocol with `grade()` method
- [ ] Deterministic graders: string_match, test_runner, static_analysis
- [ ] LLM grader: llm_judge with rubric support
- [ ] Composite grader: weighted aggregation
- [ ] Grader registry with entry point discovery

**Source**: ash-hawk `graders/`

---

#### 4.3 Policy Engine

**Requirement**: Composable policy system for agent decision-making

**User Stories**:
- As an agent developer, I want to define policies that control agent behavior
- As an agent developer, I want to compose multiple policies
- As an agent developer, I want budget-aware policy decisions

**Acceptance Criteria**:
- [ ] `Policy` protocol with `propose()` method
- [ ] `PolicyChain` for composing policies
- [ ] `PolicyInput`/`PolicyOutput` typed contracts
- [ ] Budget integration
- [ ] Explainable rationales

**Source**: vox-jay `policies/`, dawn-kestrel `policy/`

---

#### 4.4 Transcript/Trace Capture

**Requirement**: Complete execution capture for evaluation and debugging

**User Stories**:
- As an agent developer, I want to capture complete transcripts for evaluation
- As an agent developer, I want to track tool calls with inputs/outputs
- As an agent developer, I want timing and cost metrics

**Acceptance Criteria**:
- [ ] `Transcript` model with embedded messages
- [ ] Tool call tracking with timing
- [ ] Phase/event tracking
- [ ] Token usage and cost tracking
- [ ] Two-stream output (NDJSON + pretty report)

**Source**: iron-rook `transcript/`, dawn-kestrel `evaluation/models.py`

---

#### 4.5 Skill System

**Requirement**: Extensible skill discovery and registration

**User Stories**:
- As an agent developer, I want to create reusable skills
- As an agent developer, I want automatic skill discovery from paths
- As an agent developer, I want to share skills across projects

**Acceptance Criteria**:
- [ ] `Skill` protocol with `execute()` method
- [ ] `SkillLoader` for file-based discovery
- [ ] `SkillRegistry` for registration
- [ ] Entry point support for package skills
- [ ] Trigger phrase matching

**Source**: bolt-merlin `skills/`

---

### P1: Advanced Capabilities (High Priority)

#### 4.6 Tool Memory / Experiential Learning

**Requirement**: Learning from tool usage patterns

**Acceptance Criteria**:
- [ ] `ToolMemoryManager` for recording events
- [ ] Pattern learning from successful usage
- [ ] Anti-pattern tracking
- [ ] Context-aware usage hints
- [ ] Per-tool memory isolation

**Source**: bolt-merlin `tool_memory/`

---

#### 4.7 Budget Tracking

**Requirement**: Comprehensive resource tracking

**Acceptance Criteria**:
- [ ] Token counting per phase
- [ ] Dollar cost estimation
- [ ] Time tracking
- [ ] Budget thresholds with callbacks
- [ ] Per-TODO budget isolation

**Source**: iron-rook `transcript/budget.py`

---

#### 4.8 Circuit Breaker

**Requirement**: Resilience pattern for external calls

**Acceptance Criteria**:
- [ ] CLOSED/OPEN/HALF_OPEN states
- [ ] Sliding window failure counting
- [ ] Async-safe implementation
- [ ] Per-agent isolation

**Source**: iron-rook `review/utils/circuit_breaker.py`

---

#### 4.9 Checkpoint/Resume

**Requirement**: Recovery from interruption

**Acceptance Criteria**:
- [ ] Atomic checkpoint writes
- [ ] Input hashing for validation
- [ ] Resume from checkpoint
- [ ] Automatic cleanup

**Source**: iron-rook `review/utils/checkpoint.py`

---

#### 4.10 FSM + Subagent Pattern

**Requirement**: ReAct-style agent base class

**Acceptance Criteria**:
- [ ] 5-phase ReAct loop: INTAKE → PLAN → ACT → SYNTHESIZE → DONE
- [ ] Stagnation detection
- [ ] Evidence accumulation
- [ ] Stop condition logic

**Source**: iron-rook `review/subagents/base_subagent.py`

---

#### 4.11 Judge Normalization

**Requirement**: Consistent LLM judge scoring

**Acceptance Criteria**:
- [ ] Score normalization to [0, 1]
- [ ] Multi-judge consensus (mean, median, min, all_must_pass)
- [ ] Calibration support

**Source**: ash-hawk, iron-rook `graders/judge_normalizer.py`

---

### P2: Developer Experience (Medium Priority)

#### 4.12 CLI Framework

**Requirement**: Standard CLI commands for agents

**Acceptance Criteria**:
- [ ] Profile, map, search, summarize, plan, apply, run commands
- [ ] Metrics collection and export
- [ ] Working memory management

**Source**: bolt-merlin `cli/`

---

#### 4.13 Source Registry

**Requirement**: Plugin-based data source system

**Acceptance Criteria**:
- [ ] `BaseSource` ABC with `fetch()` method
- [ ] `SourceRegistry` for parallel fetching
- [ ] Timeout and error handling

**Source**: vox-jay `sources/`

---

#### 4.14 Channel System

**Requirement**: Pluggable output channels

**Acceptance Criteria**:
- [ ] `OutputChannel` protocol
- [ ] Obsidian vault integration
- [ ] Webhook support (Slack, Discord)

**Source**: vox-jay `channels/`

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Requirement |
|--------|-------------|
| Delegation overhead | <5ms per agent spawn |
| Transcript capture | <1ms per event |
| Grading latency | <100ms for deterministic, <5s for LLM |
| Memory footprint | <100MB base SDK |

### 5.2 Reliability

- All primitives must use Result types (no exception-based control flow)
- Graceful degradation on partial failures
- Automatic retries with exponential backoff
- Circuit breakers for external calls

### 5.3 Extensibility

- Protocol-based design (not inheritance)
- Entry point discovery for plugins
- Configuration-driven behavior
- Hook system for customization

### 5.4 Observability

- Structured logging with timing
- Event bus for cross-component communication
- Transcript capture for debugging
- Metrics export (JSON, Prometheus)

---

## 6. Integration with ash-hawk Evaluation

### Required SDK Hooks

```python
# SDK must provide these hooks for evaluation:

class EvaluationHooks:
    """Hooks that ash-hawk can attach to."""
    
    on_transcript_ready: Callable[[Transcript], None]
    on_tool_call: Callable[[ToolCall], None]
    on_phase_complete: Callable[[Phase], None]
    on_budget_threshold: Callable[[float], None]
```

### Integration Pattern

```python
# How ash-hawk consumes dawn-kestrel:

from dawn_kestrel.evaluation import Transcript, Outcome
from dawn_kestrel.agents import AgentRunner

async def run_trial(task: EvalTask) -> tuple[Transcript, Outcome]:
    runner = AgentRunner.from_config(task.agent_config)
    
    # SDK handles transcript capture
    transcript = await runner.run_with_transcript(
        prompt=task.input,
        policy=task.policy,
        budget=task.budget,
    )
    
    # SDK provides outcome
    outcome = Outcome(
        success=not transcript.has_errors,
        artifacts=transcript.artifacts,
    )
    
    return transcript, outcome
```

---

## 7. Migration Path

### Phase 1: Foundation (Weeks 1-3)

1. Extract DelegationEngine to `dawn_kestrel.delegation`
2. Standardize Grader interface in `dawn_kestrel.evaluation.graders`
3. Formalize Policy system in `dawn_kestrel.policy`
4. Enhance Transcript with phase tracking

### Phase 2: Advanced (Weeks 4-6)

1. Add Tool Memory as optional plugin
2. Implement Budget Tracking
3. Add Circuit Breaker
4. Add Checkpoint/Resume

### Phase 3: DX (Weeks 7-8)

1. Create CLI framework module
2. Add Source Registry
3. Add Channel System

### Phase 4: Consumer Migration

1. Update bolt-merlin to use SDK primitives
2. Update iron-rook to use SDK primitives
3. Update vox-jay to use SDK primitives
4. Ensure ash-hawk integration works

---

## 8. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking changes | High | Medium | Deprecation warnings, migration guides |
| Performance regression | High | Low | Benchmarks, profiling |
| Scope creep | Medium | High | Strict prioritization, cut features |
| Integration complexity | Medium | Medium | Incremental migration, compatibility shims |

---

## 9. Success Metrics Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│ DAWN-KESTREL SDK HEALTH                                      │
├─────────────────────────────────────────────────────────────┤
│ Projects using SDK:        4 → 10+                          │
│ Test coverage:             85% → 95%                        │
│ Lines of code per agent:   2000 → 800                       │
│ Time to new agent MVP:     2 weeks → 2 days                 │
│ Evaluation adoption:       50% → 100%                       │
│ Cross-project skill reuse: 0 → 15 skills                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Tech Lead | | | Pending |
| Architect | | | Pending |
| Product | | | Pending |

---

## Appendix A: Source File Mapping

| Feature | Source Project | Source Path |
|---------|---------------|-------------|
| Delegation Engine | bolt-merlin | `bolt_merlin/delegation/engine.py` |
| Grading Framework | ash-hawk | `ash_hawk/graders/` |
| Policy Engine | vox-jay | `vox_jay/policies/` |
| Transcript System | iron-rook | `iron_rook/transcript/` |
| Tool Memory | bolt-merlin | `bolt_merlin/tool_memory/` |
| Budget Tracking | iron-rook | `iron_rook/transcript/budget.py` |
| Circuit Breaker | iron-rook | `iron_rook/review/utils/circuit_breaker.py` |
| Checkpoint | iron-rook | `iron_rook/review/utils/checkpoint.py` |
| FSM Subagent | iron-rook | `iron_rook/review/subagents/base_subagent.py` |
| Skills | bolt-merlin | `bolt_merlin/skills/` |
| CLI Framework | bolt-merlin | `bolt_merlin/cli/` |
| Source Registry | vox-jay | `vox_jay/sources/` |
| Channels | vox-jay | `vox_jay/channels/` |
