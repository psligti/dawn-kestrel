# Draft: Smarter Security Review Agent + Todo Orchestration Skill

## Requirements (confirmed)
- User wants a plan to evolve `dawn_kestrel/agents/review/agents/security.py` from a prescriptive checklist into a more expert, self-directing security reviewer.
- User wants the approach aligned with "thin harness + model-driven control" (Bitter Lesson framing) while preserving practical reliability.
- User wants a new skill for agents focused on todo creation, progress tracking, and parallelization guidance.
- User explicitly requested exhaustive research and context gathering before planning.

## Technical Decisions
- Keep deterministic controls (budgets, allowlists, stable merge ordering) in orchestrator/runtime, while shifting security prompt toward goals, risk reasoning, and dynamic check/delegation proposals.
- Use phased rollout to reduce risk: shadow mode first, then controlled delegate execution, then full synthesis.
- Treat delegation requests from security reviewer as untrusted suggestions validated by orchestrator policy.
- Default integration strategy for todo skill: start with an ephemeral ledger behavior first, then add durable persistence once storage stubs are implemented.

## Research Findings
- Existing review framework already has reusable prompt patterns and a shared runner flow in `dawn_kestrel/agents/review/base.py` and `dawn_kestrel/core/harness/runner.py`.
- Review orchestration already supports parallel subagent execution in `dawn_kestrel/agents/review/orchestrator.py`.
- General agent orchestration supports delegation and parallel task execution in `dawn_kestrel/agents/orchestrator.py`.
- Task launching infrastructure exists in `dawn_kestrel/tools/additional.py` (`TaskTool`).
- Todo tooling surface exists (`todoread`/`todowrite`) but persistence is stubbed in `dawn_kestrel/core/session.py` (`get_todos`/`update_todos` TODO/no-op).
- Plan-mode orchestration controls and constraints are codified in `dawn_kestrel/agents/builtin.py`.
- External benchmark patterns support: multi-phase review, confidence thresholds, false-positive filtering, and structured outputs.

## Scope Boundaries
- INCLUDE:
  - Security reviewer prompt/behavior redesign plan
  - New todo/progress/parallelization skill plan
  - Orchestrator guardrails for safe dynamic delegation
  - Verification and rollout strategy
- EXCLUDE:
  - Immediate implementation code changes
  - Broad rewrite of all review agents
  - Unbounded autonomous delegation without policy caps

## Test Strategy Decision
- Infrastructure exists: YES (pytest-based project test setup found)
- Automated tests: [DECISION NEEDED]
- Candidate default: tests-after for initial refactor, then targeted TDD for new orchestration contracts
- Agent-executed QA scenarios: required in final plan

## Open Questions
- Should this plan use **TDD**, **tests-after**, or **no new automated tests** for the security-agent redesign and new todo skill?
