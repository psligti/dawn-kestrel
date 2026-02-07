# Task 1 - Planning Integration Surface Map and Scope Lock

## Baseline

- Date: 2026-02-06
- Plan reference: `.sisyphus/plans/planning-agent-initial-conversation-orchestration.md`
- Note: `.sisyphus/drafts/planning-agent-initial-conversation-orchestration.md` is currently absent; active plan exists under `.sisyphus/plans/`.

## Integration Surface Map

| Surface | Source File | Consuming Module | Runtime Impact | Migration Risk | Notes |
|---|---|---|---|---|---|
| Plan-mode entry contract text | `opencode_python/src/opencode_python/tools/prompts/plan_enter.txt` | Intended for `plan_enter` tool UX; current loader is `opencode_python/src/opencode_python/tools/prompts/__init__.py` | Low direct runtime impact today (text exists but is not wired into `PlanEnterTool.description`) | Medium | Prompt file is authoritative text candidate but currently disconnected from tool description path.
| Plan-mode exit contract text | `opencode_python/src/opencode_python/tools/prompts/plan_exit.txt` | Intended for `plan_exit` tool UX; current loader is `opencode_python/src/opencode_python/tools/prompts/__init__.py` | Low direct runtime impact today (text exists but is not wired into `PlanExitTool.description`) | Medium | Same disconnect as plan_enter; drift risk if text is updated without code binding.
| Plan mode tool behavior stubs | `opencode_python/src/opencode_python/tools/additional.py` (`PlanEnterTool`, `PlanExitTool`) | Tool execution pipeline via tool registry and agent runtime | Medium: returns `agent_mode` metadata and user-facing output, but does not actually switch active runtime agent state | High | Behavior indicates intent; implementation comments explicitly mark missing real state transition.
| Plan tool registration surface | `opencode_python/src/opencode_python/tools/registry.py` | Runtime tool availability (`ToolRegistry`) | Medium: plan tools become callable surface in sessions | Medium | IDs are registered as `planenter`/`planexit` keys while tool IDs are `plan_enter`/`plan_exit`; requires careful compatibility checks during migration.
| Plan/build permission policy (authoritative runtime gate) | `opencode_python/src/opencode_python/agents/builtin.py` | `AgentRuntime` tool filtering and all agent execution paths | High: actual safety semantics (deny edit/write in plan agent) enforced here | High | This is the primary runtime safety contract today, independent of prompt prose.
| Global default permission fallback | `opencode_python/src/opencode_python/permissions/evaluate.py` | Permission evaluator defaults before/alongside agent rules | Medium: default denies `plan_enter`/`plan_exit` unless agent-specific allow overrides | Medium | Migration must preserve precedence interactions with agent rules.
| Runtime context assembly entry point | `opencode_python/src/opencode_python/agents/runtime.py` | `AgentRuntime.execute_agent()` | High: builds context and invokes model with filtered tools | High | Runtime behavior changes here are code changes and out of scope for Task 1.
| Prompt composition logic | `opencode_python/src/opencode_python/context/builder.py` | `ContextBuilder.build_agent_context()` and `_build_system_prompt()` | High: determines system prompt ordering and final instruction payload | High | Planning prompt integration for future tasks must pass through this composition path.
| Skill instruction injection | `opencode_python/src/opencode_python/skills/injector.py` | `ContextBuilder` prompt assembly | Medium: prepends skill content to base prompt; can overshadow planning instructions if ordering is not controlled | Medium | Current order is `skills section` + `agent prompt`; plan policy text placement must respect this.
| Planning/orchestration reference documentation | `opencode_python/src/opencode_python/agents/review/README.md` | Human-maintained guidance only (not loaded by runtime) | None today | Low | Contains useful FSM/orchestration concepts but is not canonical runtime instruction source.

## Scope Lock (Task 1)

### Runtime behavior changes (NOT allowed in this task)

Changes are considered runtime behavior changes if they modify executable code paths, including:

- Agent permission rules in `opencode_python/src/opencode_python/agents/builtin.py`
- Permission evaluation defaults/logic in `opencode_python/src/opencode_python/permissions/evaluate.py`
- Tool execution implementations in `opencode_python/src/opencode_python/tools/additional.py`
- Tool registration wiring in `opencode_python/src/opencode_python/tools/registry.py`
- Prompt assembly/runtime execution in `opencode_python/src/opencode_python/context/builder.py` and `opencode_python/src/opencode_python/agents/runtime.py`

### Prompt/docs-only changes (allowed in this task)

- Mapping/spec documentation under `.sisyphus/`
- Inventory and analysis of planning prompt surfaces
- Evidence files under `.sisyphus/evidence/`

## Canonical Instruction Text Location Decision

- Canonical source for rewritten planning policy (Task 2+) should live in docs (recommended path: `docs/planning-agent-orchestration.md`).
- Runtime mirror surfaces should remain in prompt files under `opencode_python/src/opencode_python/tools/prompts/` (`plan_enter.txt`, `plan_exit.txt`) and any future planning-agent prompt pack files.
- Skills folder should only mirror planning policy if runtime actually injects that skill for planning mode; no such binding exists in current baseline.

## Gaps Identified

1. Prompt files for plan enter/exit exist, but `PlanEnterTool` and `PlanExitTool` currently use hard-coded descriptions instead of `get_prompt(...)` content.
2. Plan enter/exit tools advertise mode switching but currently return metadata-only success stubs; no explicit runtime mode switch operation is executed there.
3. Planning orchestration guidance in `agents/review/README.md` is rich but non-authoritative for runtime behavior and not connected to context assembly.
4. No single canonical planning-policy doc currently exists under `opencode_python/docs/`; policy is fragmented across tool prompt text, agent permissions, and plan notes.

## Breakage Guardrail Check

- Task 1 introduces no runtime code edits by design.
- Existing plan-mode safety behavior remains defined by `PLAN_AGENT` deny rules and runtime tool filtering path.

## Task 3 Completion Notes - Runtime Prompt Surface Integration

- Date: 2026-02-06
- Task: Integrate canonical planning orchestration controls into runtime-facing prompt surfaces

### Changes Applied

1. Prompt contracts updated:
   - `opencode_python/src/opencode_python/tools/prompts/plan_enter.txt`
   - `opencode_python/src/opencode_python/tools/prompts/plan_exit.txt`

   Added measurable directives for:
   - explicit planning budgets
   - stagnation triggers
   - forced strategy-switch behavior on stagnation
   - deterministic stop reasons and required stop output evidence

2. Planning-agent system prompt + controls wired via agent definition:
   - `opencode_python/src/opencode_python/agents/builtin.py`
   - `PLAN_AGENT.prompt` now references canonical spec path
   - `PLAN_AGENT.options.planning_orchestration_controls` carries runtime-injected control block

3. Context prompt assembly order clarified and implemented:
   - `opencode_python/src/opencode_python/context/builder.py`
   - `_build_system_prompt()` now injects planning orchestration controls before skills and base prompt
   - Effective order: `memories -> planning controls -> skills section -> base agent prompt`

### Canonical Location Correction

- Canonical planning orchestration policy is now explicitly treated as:
- `docs/planning-agent-orchestration.md`
- `.sisyphus/integration-map.md` remains an implementation map and migration ledger, not the canonical policy source.

### Safety and Scope Guardrails Preserved

- No changes to `AgentRuntime`, `AgentExecutor`, or agent type system.
- PLAN_AGENT tool gating semantics preserved:
  - edit/write deny rules unchanged in `opencode_python/src/opencode_python/agents/builtin.py`
  - plan-mode permission filtering behavior remains intact.

## Task 4 Test Coverage Notes

- Added `opencode_python/tests/test_planning_prompt_contract.py` to assert canonical planning contract sections, stagnation switch triggers, budget exhaustion escalation, and anti-pattern guardrails (`Evidence Theater`, `Over-Interviewing`).
- Added `opencode_python/tests/test_planning_docs_migration.py` to verify migration/precedence surfaces stay coherent across canonical doc and integration map.
- Validation strategy is clause-based (required headings and policy assertions) to avoid brittle full-text snapshots while still enforcing orchestration controls.

---

## Task 5 - Rollout and Migration Documentation

### Completion Date

- Date: 2026-02-06
- Status: ✅ Complete

### Deliverables

| Artifact | Location | Purpose |
|----------|----------|---------|
| Rollout and Migration Guide | `opencode_python/docs/planning-agent-rollout-and-migration.md` | Authoritative guide for safe rollout of planning-agent orchestration policy |
| Task 5 Completion Notes | (this section) | Documents integration map updates for Task 5 |

### Rollout Guide Key Sections

The rollout and migration guide includes the following required sections:

1. **Rollout Steps** (Phases 0-4)
   - Phase 0: Pre-rollout verification
   - Phase 1: Documentation rollout (non-breaking)
   - Phase 2: Context assembly integration (runtime hook)
   - Phase 3: Budget enforcement (optional enforcement layer)
   - Phase 4: Stagnation detection (optional runtime signals)

2. **Rollback Triggers**
   - When to rollback (immediate triggers)
   - Level 1: Prompt-only rollback (instant)
   - Level 2: Context assembly rollback (fast)
   - Level 3: Full rollback (safe)

3. **Default Behavior**
   - Budget defaults (max iterations, subagent calls, wall time)
   - Stagnation threshold defaults (repeated failure, no new files, confidence plateau)
   - Strategy switch defaults
   - Escalation defaults
   - Stop condition defaults

4. **Override Points**
   - Session-level override (user-specified budget)
   - Environment variable override (global enforcement)
   - Agent configuration override (default budget adjustment)
   - Prompt-level override (via plan_enter.txt)
   - Runtime hook override (custom budget logic)
   - Override precedence (highest to lowest)

5. **Budget Knobs**
   - Primary knobs (core execution bounds)
   - Secondary knobs (strategy switch budgets)
   - Tertiary knobs (quality gates)
   - Configuration examples (quick planning, deep planning, research-heavy)
   - Anti-patterns (what not to do)

6. **Stagnation Thresholds**
   - Stagnation detection parameters
   - Stagnation trigger behaviors (repeated failure, no new files, confidence plateau, redundant queries)
   - Configuration examples (aggressive, lenient, sensitive)
   - Anti-patterns

### Migration Risk Assessment

The rollout guide documents the following migration risks:

| Risk | Scenario | Impact | Mitigation |
|------|----------|--------|------------|
| Runtime-Prompt Drift | Canonical spec changes but prompt surfaces not updated | Inconsistency between guidance and actual behavior | Establish sync process, CI checks, version tags |
| Agent Configuration Drift | Agent config changes without spec update | Documentation shows outdated defaults | Make spec source of truth, derive config from spec |
| Stagnation Logic Drift | Stagnation thresholds change but runtime not updated | Mismatch between documented and actual behavior | Derive thresholds from spec, single source of truth |
| Rollback Incompatibility | Rollback breaks due to new controls | Cannot cleanly revert to previous behavior | Design additive controls, test rollback path |

### Rollout Validation

The guide includes:

- Post-rollout verification steps (bash commands for validation)
- Troubleshooting guide (common issues and resolutions)
- Reference commands (rollout verification, rollback, environment variables)
- Migration validation checklist

### Integration Map Updates

This section (Task 5 - Rollout and Migration Documentation) documents the completion of Task 5 and references the new rollout and migration guide. The integration map now provides:

- Clear path from canonical spec (`planning-agent-orchestration.md`) to rollout guide
- Reference to runtime prompt surfaces (`plan_enter.txt`, `plan_exit.txt`)
- Migration risk assessment tied to integration map surfaces
- Rollout procedures aligned with scope lock (preserving existing safety semantics)

### Rollout Philosophy (Preserved from Integration Map)

The rollout guide preserves the following principles from the original integration map:

1. **Additive Integration**: Orchestration controls are added to existing planning behavior, not replacing it
2. **Backward Compatible**: Existing planning sessions continue to work even if new controls are not enforced
3. **Reversible**: Rollback to previous behavior is always possible via configuration
4. **Surface-Aware**: Runtime prompt surfaces (`plan_enter.txt`, `plan_exit.txt`) mirror canonical spec without breaking existing patterns

### Next Steps (Beyond Task 5)

The rollout guide provides the foundation for:

- Phase 1: Prompt file updates to reflect canonical orchestration policy
- Phase 2: Context assembly integration via `ContextBuilder._build_system_prompt()`
- Phase 3: Optional budget enforcement via environment variables
- Phase 4: Optional stagnation detection signals

Each phase includes verification steps and rollback procedures.

### References

- Rollout guide: `opencode_python/docs/planning-agent-rollout-and-migration.md`
- Canonical spec: `docs/planning-agent-orchestration.md`
- Original plan: `.sisyphus/plans/planning-agent-initial-conversation-orchestration.md`
