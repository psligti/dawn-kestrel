# Dawn Kestrel SDK Evolution - Documentation Index

**Generated:** 2026-03-06
**Status:** Analysis Complete

---

## Overview

This documentation package provides a comprehensive analysis of features to extract into dawn-kestrel SDK from four agent projects: bolt-merlin, vox-jay, iron-rook, and ash-hawk.

## Documents

| Document | Purpose | Audience |
|----------|---------|----------|
| [FEATURE_ANALYSIS.md](./FEATURE_ANALYSIS.md) | Comprehensive feature catalog with priorities | Tech leads, architects |
| [PRD.md](./PRD.md) | Product requirements document | Product managers, stakeholders |
| [SPECS.md](./SPECS.md) | Technical specifications for each feature | Engineers |
| [FEATURE_OPTIONS.md](./FEATURE_OPTIONS.md) | Design alternatives and recommendations | Architects, engineers |
| [SKILLS.md](./SKILLS.md) | Skill authoring guide | Agent developers |

---

## Quick Reference

### Features by Priority

#### P0 Critical (6 features)
1. **Delegation Engine** - Multi-agent orchestration with BFS/DFS/Adaptive
2. **Evaluation Grading** - Multi-layer grading framework
3. **Policy Engine** - Composable decision policies
4. **Transcript Capture** - Complete execution traces
5. **Execution Queue** - Parallel agent execution
6. **Skill System** - Extensible capabilities

#### P1 High (8 features)
7. **Tool Memory** - Experiential learning
8. **Convergence Detection** - Early termination
9. **Budget Tracking** - Resource limits
10. **FSM + Subagent** - ReAct-style agents
11. **Circuit Breaker** - Resilience
12. **Checkpoint/Resume** - Recovery
13. **Judge Normalization** - Consistent scoring
14. **Review Workflow** - Multi-reviewer orchestration

#### P2 Medium (6 features)
15. Source Registry
16. Channel System
17. Stress Test Fixtures
18. Phase Logger
19. Evidence Cache
20. Calibration Metrics

#### P3 Nice-to-Have (3 features)
21. Working Memory
22. Repository Profile
23. Obsidian Review Workflow

---

## Source Project Summary

| Project | Domain | Key Contributions |
|---------|--------|-------------------|
| **bolt-merlin** | General agents | Delegation engine, tool memory, skills, CLI |
| **vox-jay** | Social media | Policy engine, source registry, channels |
| **iron-rook** | Code review | Transcript system, budget, circuit breaker, checkpoint |
| **ash-hawk** | Evaluation | Grading framework, evaluation runner |

---

## Implementation Timeline

```
Weeks 1-3:  P0 Core Primitives
            ├── Delegation Engine
            ├── Grading Framework
            ├── Policy Engine
            └── Transcript Capture

Weeks 4-6:  P1 Advanced Capabilities
            ├── Tool Memory
            ├── Budget Tracking
            ├── Circuit Breaker
            └── Checkpoint/Resume

Weeks 7-8:  P1 Continued + P2 Start
            ├── FSM Subagent
            ├── Skill System
            └── Judge Normalization

Weeks 9-10: P2/P3 Developer Experience
            ├── CLI Framework
            ├── Source Registry
            └── Channel System
```

---

## Key Architecture Decisions

### 1. Protocol-First Design
All major components use `Protocol` for interfaces, not inheritance. This enables:
- Multiple implementations
- Easy mocking in tests
- Decoupled packages

### 2. Result Types
No exception-based control flow. Use `Result[T]` with `Ok`/`Err` for all fallible operations.

### 3. Entry Point Discovery
Plugins (graders, skills, policies) discovered via Python entry points for proper packaging.

### 4. Hierarchical Budgets
Budget tracking at multiple levels: session → delegation → agent → tool.

### 5. Two-Stream Output
Transcripts written in two formats: NDJSON (ML pipelines) + Markdown (humans).

---

## Integration with ash-hawk Evaluation

Dawn-kestrel must provide these hooks for ash-hawk:

```python
# Hook interface
session.on_transcript_ready(callback)
session.on_tool_call(callback)
session.on_phase_complete(callback)
session.on_budget_threshold(callback)
```

Ash-hawk flow:
```
EvalSuite → EvalRunner → TrialExecutor → AgentRunner → Transcript → Graders → Results
                              ↓
                        dawn-kestrel SDK
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Projects using SDK | 4 | 10+ |
| Lines of code per agent | ~2000 | <800 |
| Time to new agent MVP | 2 weeks | 2 days |
| Evaluation adoption | 50% | 100% |
| Cross-project skill reuse | 0 | 15+ |

---

## Next Steps

1. **Review** this documentation with team
2. **Prioritize** Phase 1 features
3. **Create** feature branches in dawn-kestrel
4. **Extract** core primitives from source projects
5. **Port** tests from source projects
6. **Update** consumer projects to use SDK
7. **Document** migration guides

---

## File Locations

### In dawn-kestrel
```
docs/sdk-evolution/
├── README.md              (this file)
├── FEATURE_ANALYSIS.md
├── PRD.md
├── SPECS.md
├── FEATURE_OPTIONS.md
└── SKILLS.md
```

### New SDK Modules
```
dawn_kestrel/
├── delegation/           # Delegation engine
├── evaluation/
│   ├── graders/         # Grading framework
│   └── transcript/      # Transcript capture
├── policy/              # Policy engine
├── skills/              # Skill system
├── learning/            # Tool memory
└── reliability/         # Circuit breaker, retry
```

---

## Questions?

Contact: SDK Evolution Team
Last Updated: 2026-03-06
