# Planning Agent Rollout and Migration Guide

**Related Documents:**
- Canonical spec: `docs/planning-agent-orchestration.md`
- Integration map: `.sisyphus/integration-map.md`

---

## Overview

This guide covers the safe rollout of planning-agent orchestration policy into the OpenCode runtime, including rollback procedures, default behaviors, and migration considerations.

### Rollout Philosophy

1. **Additive Integration**: Orchestration controls are added to existing planning behavior, not replacing it
2. **Backward Compatible**: Existing planning sessions continue to work even if new controls are not enforced
3. **Reversible**: Rollback to previous behavior is always possible via configuration
4. **Surface-Aware**: Runtime prompt surfaces (`plan_enter.txt`, `plan_exit.txt`) mirror canonical spec without breaking existing patterns

---

## Rollout Steps

### Phase 0: Pre-Rollout Verification

**Before any rollout, verify:**

```bash
# 1. Confirm current planning behavior baseline
cat dawn_kestrel/tools/prompts/plan_enter.txt
cat dawn_kestrel/tools/prompts/plan_exit.txt

# 2. Check agent permission rules (PLAN_AGENT deny rules)
grep -A 10 "PLAN_AGENT" dawn_kestrel/agents/builtin.py

# 3. Verify no uncommitted changes to runtime behavior
git status
```

**Verification criteria:**
- Planning agent tools (`plan_enter`, `plan_exit`) exist and are registered
- PLAN_AGENT deny rules prevent edit/write operations in plan mode
- Prompt files exist but may not contain full orchestration spec content

---

### Phase 1: Documentation Rollout (Non-Breaking)

**Action**: Update runtime prompt surfaces to reflect canonical orchestration policy

**Files to update:**
- `dawn_kestrel/tools/prompts/plan_enter.txt`
- `dawn_kestrel/tools/prompts/plan_exit.txt`

**Integration points:**
- Entry contract: Subagent-first orchestration policy, budget allocation
- Exit contract: Stop conditions, escalation triggers, output format

**Verification:**
```bash
# Compare prompt files against canonical spec
diff <(grep -A 20 "Subagent-First" docs/planning-agent-orchestration.md) \
     <(grep -A 20 "Subagent-First" dawn_kestrel/tools/prompts/plan_enter.txt)
```

**Risk**: None (prompt-only change, no runtime code paths modified)

---

### Phase 2: Context Assembly Integration (Runtime Hook)

**Action**: Integrate orchestration policy into `ContextBuilder._build_system_prompt()`

**File**: `dawn_kestrel/context/builder.py`

**Integration pattern:**
```python
def _build_system_prompt(self, agent: Agent) -> str:
    """Build system prompt with orchestration controls for planning agent."""
    sections = []

    # 1. Agent base prompt
    sections.append(agent.prompt or "")

    # 2. Skills injection (existing)
    skill_content = self.skill_injector.get_skill_content(agent)
    if skill_content:
        sections.append(skill_content)

    # 3. Orchestration policy (NEW - for planning agent only)
    if agent.name == "plan":
        orchestration_policy = self._load_orchestration_policy()
        sections.append(orchestration_policy)

    return "\n\n".join(filter(None, sections))
```

**Verification:**
- Planning agent sessions include orchestration controls in system prompt
- Non-planning agents are unaffected (no orchestration policy injected)
- Prompt ordering preserved: base → skills → orchestration

**Risk**: Low (only affects planning agent, other agents unchanged)

---

### Phase 3: Budget Enforcement (Optional Enforcement Layer)

**Action**: Add optional runtime budget tracking for planning agent

**File**: `dawn_kestrel/agents/runtime.py`

**Implementation pattern (optional):**
```python
class AgentRuntime:
    def __init__(self):
        self.planning_budgets = {}  # session_id -> budget tracking

    def track_planning_iteration(self, session_id: str) -> bool:
        """Check if planning agent can continue. Returns True if within budget."""
        budget = self.planning_budgets.get(session_id, self._get_default_budget())
        budget["iterations"] += 1
        return budget["iterations"] <= budget["max_iterations"]
```

**Rollout mode**: Off by default, enabled via environment variable:
```bash
export PLAN_AGENT_BUDGET_ENFORCEMENT=1  # Enable enforcement
```

**Verification:**
- Default behavior: No enforcement (runtime does not stop iterations)
- With enforcement: Runtime prevents iteration exceeding max_iterations
- Rollback: Disable environment variable or remove enforcement logic

**Risk**: Medium (enforcement changes runtime behavior, but is opt-in)

---

### Phase 4: Stagnation Detection (Optional Runtime Signals)

**Action**: Add optional stagnation detection signals to planning agent output

**File**: `dawn_kestrel/tools/prompts/plan_exit.txt`

**Integration pattern:**
- Prompt planning agent to output stagnation indicators in exit message
- Format: YAML block with `stagnation_detected`, `trigger`, `strategy_switch`

**Verification:**
- Exit messages include stagnation indicators when detected
- No enforcement (agent is responsible for detection, runtime only signals)

**Risk**: Low (output-only change, no enforcement logic)

---

## Rollback Triggers

### When to Rollback

**Immediate rollback required if:**

1. **Planning sessions hang or fail to produce output**
   - Symptom: Agent continues indefinitely without stopping
   - Cause: Orchestration policy conflicts with existing behavior
   - Action: Remove orchestration policy injection from `ContextBuilder`

2. **Build/edit operations enabled in plan mode**
   - Symptom: Planning agent can write files despite PLAN_AGENT deny rules
   - Cause: Orchestration policy overrides permission rules
   - Action: Verify permission rules take precedence over orchestration guidance

3. **Existing planning workflows break**
   - Symptom: Previous working planning sessions now fail or produce unexpected output
   - Cause: Orchestration policy introduces new stopping conditions
   - Action: Disable new stopping conditions or adjust thresholds

4. **Performance regression (> 2x slowdown)**
   - Symptom: Planning sessions take significantly longer
   - Cause: Subagent-first policy increases overhead
   - Action: Revert to direct tool use for trivial tasks (fast-path exceptions)

### Rollback Procedures

#### Level 1: Prompt-Only Rollback (Instant)

**Action**: Revert prompt file changes

```bash
git checkout HEAD~1 -- dawn_kestrel/tools/prompts/plan_enter.txt
git checkout HEAD~1 -- dawn_kestrel/tools/prompts/plan_exit.txt
```

**Impact**: Removes orchestration policy from future planning sessions

---

#### Level 2: Context Assembly Rollback (Fast)

**Action**: Disable orchestration policy injection

**File**: `dawn_kestrel/context/builder.py`

```python
def _build_system_prompt(self, agent: Agent) -> str:
    sections = []

    # 1. Agent base prompt
    sections.append(agent.prompt or "")

    # 2. Skills injection
    skill_content = self.skill_injector.get_skill_content(agent)
    if skill_content:
        sections.append(skill_content)

    # 3. Orchestration policy (ROLLED BACK - disabled)
    # if agent.name == "plan":
    #     orchestration_policy = self._load_orchestration_policy()
    #     sections.append(orchestration_policy)

    return "\n\n".join(filter(None, sections))
```

**Impact**: Planning agent uses pre-rollout behavior (no orchestration controls)

---

#### Level 3: Full Rollback (Safe)

**Action**: Revert entire rollout commit

```bash
# Identify rollout commit
git log --oneline --grep="planning-agent rollout"

# Revert commit
git revert <rollout-commit-hash>

# Push revert (if previously pushed)
git push
```

**Impact**: All planning-agent orchestration changes removed

---

## Default Behavior

### What Happens When No Override Is Provided

#### Budget Defaults

| Budget | Default Value | Source | Enforcement |
|--------|---------------|--------|-------------|
| Max iterations | 5 | Canonical spec, Section "Layer 1: Hard Budgets" | Soft (prompt guidance only) |
| Max subagent calls | 8 | Canonical spec, Section "Layer 1: Hard Budgets" | Soft (prompt guidance only) |
| Max wall time | 5 minutes | Canonical spec, Section "Layer 1: Hard Budgets" | Soft (prompt guidance only) |

**Behavior without override:**
- Planning agent receives guidance to stay within these bounds
- Agent is expected to self-enforce via exit checks
- Runtime does not hard-stop unless `PLAN_AGENT_BUDGET_ENFORCEMENT=1`

#### Stagnation Threshold Defaults

| Threshold | Default Trigger | Source | Enforcement |
|-----------|-----------------|--------|-------------|
| Repeated failure | 3 times same error | Canonical spec, Section "Layer 3: Stagnation Detector" | Soft (agent detects, no runtime enforcement) |
| No new files | 2 iterations | Canonical spec, Section "Layer 3: Stagnation Detector" | Soft (agent detects, no runtime enforcement) |
| Confidence plateau | < 0.1 improvement for 2 iterations | Canonical spec, Section "Layer 3: Stagnation Detector" | Soft (agent detects, no runtime enforcement) |
| Redundant queries | Same info from different sources | Canonical spec, Section "Layer 3: Stagnation Detector" | Soft (agent detects, no runtime enforcement) |

**Behavior without override:**
- Planning agent monitors for these stagnation patterns
- Agent is expected to self-detect and switch strategy when triggered
- Runtime does not enforce stagnation detection

#### Strategy Switch Defaults

When stagnation is detected, default behavior:

```yaml
new_budget:
  max_iterations: 2
  max_subagent_calls: 3
hypothesis: <agent documents hypothesis for new strategy>
```

**Behavior without override:**
- Agent declares strategy switch in output
- Agent allocates reduced budget for new strategy
- No runtime validation of switch compliance

#### Escalation Defaults

| Condition | Default Action | Source |
|-----------|----------------|--------|
| Budget exhausted | Produce blocking question | Canonical spec, Section "Stop Conditions" |
| Stagnation after switch | Escalate to blocking question | Canonical spec, Section "Stop Conditions" |
| Missing info (unobtainable) | Escalate to blocking question | Canonical spec, Section "Next Best Question" |

**Behavior without override:**
- Agent formulates blocking question when escalation triggered
- Question must be singular, answerable, and blocking (per spec)
- No runtime validation of question quality

#### Stop Condition Defaults

| Condition | Default Action | Source |
|-----------|----------------|--------|
| Confidence >= 0.8 | Commit to recommendation | Canonical spec, Section "Quality Gate: Decision Point" |
| Uncertainty reduced >= 20% | Continue iteration | Canonical spec, Section "Quality Gate: Decision Point" |
| Uncertainty reduction < 20% (2 turns) | Escalate to blocking question | Canonical spec, Section "Decision Gate (Post-Novelty Check)" |

**Behavior without override:**
- Agent evaluates stop conditions after each iteration
- Agent commits, continues, or escalates based on defaults
- No runtime enforcement of stop logic

---

## Override Points

### Where and How to Override Defaults

#### 1. Session-Level Override (User-Specified Budget)

**Mechanism**: User provides budget in initial request

**Example**:
```
"Plan the migration to JWT auth, max 3 iterations, max 5 subagent calls"
```

**Parsing location**: `AgentRuntime.execute_agent()` extracts budget from request

**Application**:
- Budgets override canonical defaults for this session only
- Other defaults (stagnation thresholds, stop conditions) remain canonical

---

#### 2. Environment Variable Override (Global Enforcement)

**Mechanism**: Environment variables control enforcement levels

| Variable | Default | Purpose |
|----------|---------|---------|
| `PLAN_AGENT_BUDGET_ENFORCEMENT` | `0` (disabled) | Enable runtime budget enforcement |
| `PLAN_AGENT_STAGNATION_ENFORCEMENT` | `0` (disabled) | Enable runtime stagnation detection enforcement |
| `PLAN_AGENT_LOG_LEVEL` | `info` | Control orchestration policy logging |

**Application**:
- `PLAN_AGENT_BUDGET_ENFORCEMENT=1`: Runtime stops iterations exceeding max_iterations
- `PLAN_AGENT_STAGNATION_ENFORCEMENT=1`: Runtime stops agent when stagnation detected (if detection logic implemented)

**Example**:
```bash
export PLAN_AGENT_BUDGET_ENFORCEMENT=1
# Runtime now enforces max_iterations = 5
```

---

#### 3. Agent Configuration Override (Default Budget Adjustment)

**Mechanism**: Modify agent configuration to change defaults

**File**: `dawn_kestrel/agents/builtin.py`

**Example**:
```python
PLAN_AGENT = Agent(
    name="plan",
    # ... existing config ...
    planning_defaults={
        "max_iterations": 7,  # Override canonical default (5)
        "max_subagent_calls": 10,  # Override canonical default (8)
        "max_wall_time": 300  # 5 minutes (same as canonical)
    }
)
```

**Application**:
- New defaults apply to all future planning sessions
- Canonical spec documentation should be updated to reflect new defaults

---

#### 4. Prompt-Level Override (Via plan_enter.txt)

**Mechanism**: Embed override instructions in entry prompt

**File**: `dawn_kestrel/tools/prompts/plan_enter.txt`

**Example**:
```
Planning Agent Orchestration Policy:

[... canonical policy ...]

OVERRIDE: For this session, use max_iterations=3 (reduced budget for quick tasks)
```

**Application**:
- Override applies to planning agent when entering plan mode
- Agent is instructed via prompt to use overridden budget

---

#### 5. Runtime Hook Override (Custom Budget Logic)

**Mechanism**: Implement custom budget tracking in `AgentRuntime`

**File**: `dawn_kestrel/agents/runtime.py`

**Example**:
```python
class AgentRuntime:
    def _get_custom_budget(self, session_id: str) -> dict:
        """Load session-specific budget from external config."""
        # Load from config file, database, or external service
        return {
            "max_iterations": 10,
            "max_subagent_calls": 15,
            "max_wall_time": 600  # 10 minutes
        }
```

**Application**:
- Custom budget logic takes precedence over canonical defaults
- Enables dynamic budget adjustment based on session context

---

### Override Precedence

**Highest to lowest precedence:**

1. **Session-level override** (user-specified budget)
2. **Runtime hook override** (custom budget logic)
3. **Environment variable override** (enforcement level)
4. **Agent configuration override** (default budget adjustment)
5. **Prompt-level override** (via plan_enter.txt)
6. **Canonical defaults** (from spec)

**Rule**: More specific overrides take precedence. Session-level overrides are most specific; canonical defaults are least specific.

---

## Budget Knobs

### Adjustable Budget Parameters

#### Primary Knobs (Core Execution Bounds)

| Parameter | Default | Min | Max | Description |
|-----------|---------|-----|-----|-------------|
| `max_iterations` | 5 | 1 | 20 | Maximum number of planning iterations before forced stop |
| `max_subagent_calls` | 8 | 0 | 30 | Maximum number of subagent dispatches per session |
| `max_wall_time` | 300 (5 min) | 60 | 1800 (30 min) | Maximum wall clock time for planning session (seconds) |

**Adjustment guidance**:
- Reduce `max_iterations` (3-4) for quick planning tasks (e.g., small feature additions)
- Increase `max_iterations` (7-10) for complex planning tasks (e.g., architecture redesigns)
- Increase `max_subagent_calls` (12-15) for planning requiring extensive external research
- Reduce `max_subagent_calls` (2-3) for planning focused on internal codebase only
- Increase `max_wall_time` (600-900) for planning involving large file reads or web searches

---

#### Secondary Knobs (Strategy Switch Budgets)

| Parameter | Default | Min | Max | Description |
|-----------|---------|-----|-----|-------------|
| `strategy_switch_max_iterations` | 2 | 1 | 5 | Max iterations after forced strategy switch |
| `strategy_switch_max_subagent_calls` | 3 | 1 | 10 | Max subagent calls after forced strategy switch |

**Adjustment guidance**:
- Increase strategy switch budget (3 iterations, 5 calls) when first strategy is likely to fail due to fundamental assumptions
- Reduce strategy switch budget (1 iteration, 2 calls) when planning sessions are time-critical

---

#### Tertiary Knobs (Quality Gates)

| Parameter | Default | Min | Max | Description |
|-----------|---------|-----|-----|-------------|
| `commit_confidence_threshold` | 0.8 | 0.5 | 1.0 | Minimum confidence to commit to recommendation |
| `min_uncertainty_reduction` | 0.2 (20%) | 0.0 | 0.5 (50%) | Minimum uncertainty reduction to continue iteration |

**Adjustment guidance**:
- Lower `commit_confidence_threshold` (0.7) when planning tasks are low-risk (e.g., documentation updates)
- Raise `commit_confidence_threshold` (0.9) when planning tasks are high-risk (e.g., critical refactoring)
- Lower `min_uncertainty_reduction` (0.1) for early exploration phases
- Raise `min_uncertainty_reduction` (0.3) for final decision phases

---

### Budget Knob Configuration Examples

#### Configuration 1: Quick Planning (Fast Path)

```yaml
budget:
  max_iterations: 3
  max_subagent_calls: 2
  max_wall_time: 120  # 2 minutes
strategy_switch:
  max_iterations: 1
  max_subagent_calls: 1
quality:
  commit_confidence_threshold: 0.7  # Accept lower confidence for speed
  min_uncertainty_reduction: 0.1
```

**Use case**: Small feature additions, straightforward refactoring, bug fix planning

---

#### Configuration 2: Deep Planning (Comprehensive)

```yaml
budget:
  max_iterations: 10
  max_subagent_calls: 15
  max_wall_time: 900  # 15 minutes
strategy_switch:
  max_iterations: 4
  max_subagent_calls: 6
quality:
  commit_confidence_threshold: 0.9  # Require high confidence
  min_uncertainty_reduction: 0.25
```

**Use case**: Architecture redesigns, large-scale migrations, strategic planning

---

#### Configuration 3: Research-Heavy Planning (External Focus)

```yaml
budget:
  max_iterations: 7
  max_subagent_calls: 20  # High budget for librarian agent
  max_wall_time: 600  # 10 minutes
strategy_switch:
  max_iterations: 3
  max_subagent_calls: 5
quality:
  commit_confidence_threshold: 0.85
  min_uncertainty_reduction: 0.2
```

**Use case**: Technology selection, API integration planning, best practice research

---

### Knob Anti-Patterns (What Not To Do)

❌ **Do not** set `max_iterations = 0` (agent cannot run)
❌ **Do not** set `max_subagent_calls = 0` AND disable fast path (agent cannot gather evidence)
❌ **Do not** set `commit_confidence_threshold = 1.0` (agent will never commit)
❌ **Do not** set `min_uncertainty_reduction = 0.5` (agent will escalate prematurely)
❌ **Do not** increase all budgets simultaneously (leads to unbounded exploration)

---

## Stagnation Thresholds

### Stagnation Detection Parameters

| Threshold | Default | Adjust To | When to Adjust |
|-----------|---------|-----------|-----------------|
| `repeated_failure_count` | 3 | 2 (aggressive) / 5 (lenient) | Adjust based on error frequency in codebase |
| `no_new_files_iterations` | 2 | 1 (aggressive) / 3 (lenient) | Adjust based on file exploration patterns |
| `confidence_plateau_iterations` | 2 | 1 (aggressive) / 3 (lenient) | Adjust based on confidence tracking quality |
| `confidence_plateau_threshold` | 0.1 | 0.05 (sensitive) / 0.2 (tolerant) | Adjust based on confidence scoring granularity |

---

### Stagnation Trigger Behaviors

#### Repeated Failure Signature

**Default trigger**: Same error pattern appears 3 times

**Behavior**: Forced strategy switch

**Adjustment guidance**:
- Reduce threshold to 2 for error-prone codebases (faster adaptation)
- Increase threshold to 5 for stable codebases with occasional transient errors

**Example**:
```
Iteration 1: grep returns "no match" for pattern "auth"
Iteration 2: grep returns "no match" for pattern "auth"
Iteration 3: grep returns "no match" for pattern "auth"
-> STAGNATION TRIGGERED (repeated_failure)
-> Switch strategy from "grep-based" to "documentation-based"
```

---

#### No New Files

**Default trigger**: Last 2 iterations touched no new files

**Behavior**: Forced strategy switch

**Adjustment guidance**:
- Reduce threshold to 1 for fast-paced exploration (switch immediately when stuck)
- Increase threshold to 3 for deep file analysis (allow revisiting same files)

**Example**:
```
Iteration 1: Read src/auth/config.py
Iteration 2: Read src/auth/config.py (revisited)
Iteration 3: Read src/auth/config.py (revisited again)
-> STAGNATION TRIGGERED (no_new_files)
-> Switch strategy from "file reading" to "web search"
```

---

#### Confidence Plateau

**Default trigger**: Confidence score improvement < 0.1 for 2 iterations

**Behavior**: Forced strategy switch

**Adjustment guidance**:
- Reduce threshold to 0.05 for high-precision planning (detect slow progress)
- Increase threshold to 0.2 for noisy planning (allow gradual improvement)

**Example**:
```
Iteration 1: Confidence = 0.6
Iteration 2: Confidence = 0.65 (improvement = 0.05 < 0.1)
Iteration 3: Confidence = 0.70 (improvement = 0.05 < 0.1)
-> STAGNATION TRIGGERED (confidence_plateau)
-> Switch strategy to "reduce uncertainty via blocking question"
```

---

#### Redundant Queries

**Default trigger**: Same information requested from different sources

**Behavior**: Forced strategy switch

**Adjustment guidance**:
- This threshold is qualitative; adjust via prompt instruction tuning
- Add examples of "redundant query" patterns to plan_enter.txt

**Example**:
```
Iteration 1: Grep for "JWT auth implementation"
Iteration 2: Web search for "JWT auth implementation"
Iteration 3: Read test files for "JWT auth implementation"
-> STAGNATION TRIGGERED (redundant_queries)
-> Agent recognizes all queries target same information without synthesis
-> Switch strategy to "stop and ask blocking question about specific auth pattern"
```

---

### Stagnation Threshold Configuration Examples

#### Configuration 1: Aggressive Stagnation Detection (Fast Adaptation)

```yaml
stagnation:
  repeated_failure_count: 2
  no_new_files_iterations: 1
  confidence_plateau_iterations: 1
  confidence_plateau_threshold: 0.05
```

**Use case**: Fast-paced planning sessions, time-critical decisions

---

#### Configuration 2: Lenient Stagnation Detection (Deep Exploration)

```yaml
stagnation:
  repeated_failure_count: 5
  no_new_files_iterations: 3
  confidence_plateau_iterations: 3
  confidence_plateau_threshold: 0.15
```

**Use case**: Deep research tasks, complex codebases requiring thorough analysis

---

#### Configuration 3: Sensitive Confidence Tracking (Precision Planning)

```yaml
stagnation:
  repeated_failure_count: 3
  no_new_files_iterations: 2
  confidence_plateau_iterations: 2
  confidence_plateau_threshold: 0.05  # Detect slow confidence growth
```

**Use case**: High-stakes planning requiring precise confidence tracking

---

## Migration Risk Assessment

### What Could Break if Canonical Spec Changes Are Not Propagated

#### Risk 1: Runtime-Prompt Drift

**Scenario**: Canonical spec changes (e.g., new budget defaults), but runtime prompt surfaces (`plan_enter.txt`, `plan_exit.txt`) are not updated.

**Impact**:
- Planning agent follows canonical spec (if injected via ContextBuilder)
- But plan_enter.txt and plan_exit.txt may show outdated guidance
- Inconsistency between guidance and actual behavior

**Mitigation**:
- Establish sync process: canonical spec changes → prompt surface updates
- Use CI check: Verify prompt files contain key sections from spec
- Maintain version tags in spec and prompt files

---

#### Risk 2: Agent Configuration Drift

**Scenario**: Agent configuration (`builtin.py` PLANNING_AGENT defaults) changes without canonical spec update.

**Impact**:
- Runtime uses new defaults
- Documentation (canonical spec) shows outdated defaults
- User confusion about actual behavior

**Mitigation**:
- Make canonical spec the source of truth for defaults
- Derive agent config defaults from canonical spec via build process or script
- Include spec version in agent config metadata

---

#### Risk 3: Stagnation Detection Logic Drift

**Scenario**: Stagnation thresholds change in spec, but runtime detection logic (if implemented) is not updated.

**Impact**:
- Spec says: "no_new_files_iterations = 2"
- Runtime (if enforced): checks for 3 iterations
- Mismatch between documented and actual behavior

**Mitigation**:
- If runtime enforcement is added, derive thresholds directly from spec
- Use single source of truth for threshold values (e.g., config file)
- Add CI check: Compare spec thresholds with runtime enforcement thresholds

---

#### Risk 4: Rollback Incompatibility

**Scenario**: Rollback to previous version breaks because new orchestration controls are incompatible with old runtime behavior.

**Impact**:
- Planning sessions fail or produce unexpected output
- Cannot cleanly revert to previous behavior

**Mitigation**:
- Design orchestration controls as additive (not breaking)
- Ensure rollback removes new controls without breaking existing behavior
- Test rollback path in staging before production rollout

---

### Migration Validation Checklist

Before each rollout or spec update:

- [ ] Prompt files (`plan_enter.txt`, `plan_exit.txt`) reflect canonical spec
- [ ] Agent configuration defaults match canonical spec defaults
- [ ] Stagnation thresholds in runtime enforcement (if enabled) match spec
- [ ] Rollback procedure tested (verify prompt-only and context assembly rollback)
- [ ] Documentation version tags synchronized (spec, prompts, integration map)
- [ ] CI checks pass (prompt file content verification, threshold comparison)
- [ ] No drift between guidance and actual behavior (manual verification test)

---

## Rollout Validation

### Post-Rollout Verification Steps

After each rollout phase, verify:

```bash
# 1. Check prompt file content
grep -A 10 "Subagent-First" dawn_kestrel/tools/prompts/plan_enter.txt
grep -A 10 "Stop Conditions" dawn_kestrel/tools/prompts/plan_exit.txt

# 2. Verify ContextBuilder integration (if Phase 2 completed)
grep -A 10 "orchestration_policy" dawn_kestrel/context/builder.py

# 3. Check agent permissions unchanged
grep -A 10 "PLAN_AGENT" dawn_kestrel/agents/builtin.py

# 4. Test planning session (manual or automated)
# Trigger planning session and verify output includes orchestration controls

# 5. Verify rollback capability
# Test prompt-only and context assembly rollback procedures
```

---

## Troubleshooting

### Common Issues and Resolutions

#### Issue: Planning Agent Ignores Orchestration Policy

**Symptom**: Agent does not follow subagent-first policy or budget bounds

**Possible causes**:
1. Orchestration policy not injected into system prompt
2. Prompt ordering places orchestration policy after conflicting instructions
3. Agent base prompt overrides orchestration guidance

**Resolution**:
1. Verify `ContextBuilder._build_system_prompt()` injects orchestration policy for planning agent
2. Check prompt ordering: base → skills → orchestration (not reversed)
3. Ensure orchestration policy uses imperative language ("MUST", "DO NOT")

---

#### Issue: Planning Agent Stops Prematurely

**Symptom**: Agent escalates to blocking question with sufficient evidence available

**Possible causes**:
1. Budget thresholds too low
2. Stagnation detection too sensitive
3. Confidence scoring too conservative

**Resolution**:
1. Increase `max_iterations` or `max_subagent_calls` budget knobs
2. Adjust stagnation thresholds (increase counts or reduce thresholds)
3. Lower `commit_confidence_threshold` or `min_uncertainty_reduction`

---

#### Issue: Planning Agent Over-Interviews User

**Symptom**: Agent asks questions that could be answered via tools

**Possible causes**:
1. Fast-path exceptions not clearly defined
2. Subagent-first policy applied too aggressively
3. Missing guidance on when to use tools directly

**Resolution**:
1. Add explicit fast-path examples to plan_enter.txt
2. Clarify: "Dispatch subagent ONLY for non-trivial tasks"
3. Add guidance: "Use direct tool calls when answer requires 1-2 calls"

---

#### Issue: Rollback Does Not Restore Previous Behavior

**Symptom**: After rollback, planning agent still shows new orchestration behavior

**Possible causes**:
1. Prompt file changes not fully reverted
2. ContextBuilder still injects orchestration policy (if rollback incomplete)
3. Agent caching in runtime (restart required)

**Resolution**:
1. Verify prompt file content: `git diff` against pre-rollout version
2. Check ContextBuilder: ensure orchestration injection code is commented out or removed
3. Restart runtime or clear agent cache

---

## Appendix: Reference Commands

### Rollout Verification Commands

```bash
# Check prompt file sync with canonical spec
diff <(grep -A 20 "Subagent-First" docs/planning-agent-orchestration.md) \
     <(grep -A 20 "Subagent-First" dawn_kestrel/tools/prompts/plan_enter.txt)

grep -A 20 "PLAN_AGENT" dawn_kestrel/agents/builtin.py

grep -B 5 -A 15 "orchestration" dawn_kestrel/context/builder.py

ls -la dawn_kestrel/tools/prompts/plan_*.txt

grep "max_iterations" docs/planning-agent-orchestration.md
grep "max_iterations" dawn_kestrel/tools/prompts/plan_enter.txt
```

### Rollback Commands

```bash
grep "max_iterations" docs/planning-agent-orchestration.md
grep "max_iterations" dawn_kestrel/tools/prompts/plan_enter.txt
```

### Environment Variable Commands

```bash
# Enable budget enforcement
export PLAN_AGENT_BUDGET_ENFORCEMENT=1

# Disable budget enforcement (rollback to default)
unset PLAN_AGENT_BUDGET_ENFORCEMENT

# Enable stagnation enforcement
export PLAN_AGENT_STAGNATION_ENFORCEMENT=1

# Set logging level for orchestration policy
export PLAN_AGENT_LOG_LEVEL=debug
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-06 | Initial rollout and migration guide (Task 5) |

---

## References

- Canonical spec: `docs/planning-agent-orchestration.md`
- Integration map: `.sisyphus/integration-map.md`
- Original plan: `.sisyphus/plans/planning-agent-initial-conversation-orchestration.md`
