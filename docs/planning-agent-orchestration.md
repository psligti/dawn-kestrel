# Planning Agent Orchestration Specification

**Canonical Location**: `docs/planning-agent-orchestration.md`

This document defines the authoritative orchestration policy for the planning agent, including subagent usage, evaluation gates, stop conditions, and escalation behavior.

---

## Objective

The planning agent's primary purpose is to **produce actionable recommendations or precise blocking questions** within bounded iterations, while preventing evidence-theater and over-interviewing.

### Core Success Criteria

1. **Actionable Recommendation Path**: The agent terminates with either:
   - An actionable recommendation sufficient to proceed, OR
   - A single precise blocking question that cannot be resolved through further investigation

2. **Evidence-Driven Progress**: Every iteration must produce at least one of:
   - New evidence (tool output, file content, or external reference)
   - Reduced uncertainty area
   - Higher confidence in a specific approach
   - A falsified hypothesis

3. **Budget-Constrained Execution**: All work completes within explicit bounds:
   - Maximum iterations: 5 (default)
   - Maximum subagent calls: 8 (default)
   - Maximum wall time: 5 minutes (default)

### Anti-Patterns (FORBIDDEN)

- **Evidence Theater**: Superficial information gathering without synthesis or decision
- **Over-Interviewing**: Asking questions that could be answered by available tools
- **Unbounded Exploration**: Continuing research without diminishing uncertainty
- **Vague Directives**: Phrases like "explore more" without specific tool/skill assignment
- **Static Decomposition**: Hard-coded task breakdowns without evidence-based refinement

---

## Subagent Orchestration Plan

### Available Subagents

| Subagent | Purpose | Capabilities | When to Use |
|----------|---------|--------------|-------------|
| `explore` | Fast codebase exploration | `grep`, `glob`, `read`, `bash` | Find files, search code, answer "how does X work?" |
| `librarian` | Research and documentation | `websearch`, `webfetch`, `codesearch` | Look up APIs, best practices, external docs |

### Orchestration Strategy

**Policy: Subagent-First with Fast-Path Exceptions**

#### General Rule: Subagent-First

For non-trivial tasks, the planning agent MUST delegate to subagents rather than executing tools directly. This ensures:

1. Parallelism across independent exploration paths
2. Specialized tool access appropriate to the domain
3. Bounded subagent execution (automatic timeout and budget enforcement)

**When to dispatch subagents:**
- You need to search for files matching patterns (`*.py`, `**/test_*.py`)
- You need to grep code for keywords across multiple files
- You need to search the web or fetch documentation
- You need to answer questions about codebase structure or implementation

**Example dispatch:**
```
delegate_task(
  agent="explore",
  prompt="Find all API endpoint definitions in src/api/",
  run_in_background=true
)
```

#### Exception: Fast Path for Trivial Tasks

**DO NOT dispatch subagents when:**
- The task can be answered in 1-2 direct tool calls
- The information is in a known location
- The cost of subagent setup exceeds the work

**Example fast path (direct tool use):**
```
# Correct: Single read from known location
read("README.md")

# Incorrect: Subagent for single file read
delegate_task(agent="explore", prompt="Read the README")  # WASTEFUL
```

#### Parallel Dispatch Pattern

When multiple independent exploration paths exist, dispatch ALL subagents in parallel, then await and synthesize results.

**Example:**
```python
# Launch parallel exploration
delegate_task(agent="explore", prompt="Find test files for auth module", run_in_background=true)
delegate_task(agent="librarian", prompt="Find JWT authentication best practices", run_in_background=true)

# Collect and synthesize results
# (harness automatically notifies when complete)
```

### Evidence Synthesis Rules

After collecting subagent results, the planning agent MUST:

1. **Cross-Reference**: Identify contradictions between subagent outputs
2. **Triangulate**: Use multiple evidence sources to validate findings
3. **Prioritize**: Rank findings by relevance, confidence, and actionability
4. **Summarize**: Produce a condensed synthesis that reduces uncertainty

**Anti-Evidence-Theater Rule:**
> If subagent results do not advance understanding toward a decision, STOP and ask a blocking question instead of dispatching more subagents.

---

## Gates and Evaluation

### Layered Budget Gates

#### Layer 1: Hard Budgets (Enforce Immediately)

| Budget | Default | Escalation | Stop Action |
|--------|---------|------------|-------------|
| Max iterations | 5 | Double only on explicit user override | Produce current best recommendation + blocking question |
| Max subagent calls | 8 | +3 on strategy switch | Same as above |
| Max wall time | 5 min | +2 min on strategy switch | Same as above |

**Behavior on budget exhaustion:**
- DO NOT continue with reduced scope
- DO NOT silently truncate investigation
- MUST produce a blocking question explaining what remains uncertain

#### Layer 2: Deterministic Gates

**Pass Requirements (ALL must be met):**
1. **Triad Lock-In**: Goal, constraints, and initial evidence must be established by turn 2
2. **Evidence Novelty Check**: Each iteration must introduce new information not previously gathered
3. **Conflict Resolution**: Any contradictions between evidence sources must be addressed

**Fail Conditions (ANY triggers stop):**
1. Missing required file (e.g., README.md absent)
2. Test suite unavailable (no pytest, no tests/ directory)
3. Permission denied (cannot read required sources)

#### Layer 3: Stagnation Detector

**Stagnation Triggers (ANY triggers forced strategy switch):**
1. **Repeated Failure Signature**: Same error pattern appears 3 times
2. **No New Files**: Last 2 iterations touched no new files
3. **Confidence Plateau**: Confidence score improvement < 0.1 for 2 iterations
4. **Redundant Queries**: Same information requested from different sources

**Forced Strategy Switch:**
When stagnation is detected, the agent MUST:
1. Declare the current strategy failed
2. Switch to a fundamentally different approach (e.g., from code-based to documentation-based)
3. Set new budget: max_iterations = 2, max_subagent_calls = 3
4. Document the hypothesis being tested

**Example:**
```
Current strategy: Grep for authentication patterns
Status: Stagnated (no new files in 2 iterations)
Switching to: Read documentation and existing tests
New budget: 2 iterations, 3 subagent calls
Hypothesis: Auth logic is documented but not grep-able
```

### Quality Gate: Decision Point

At the end of each iteration, the planning agent evaluates:

**Proceed to next iteration IF:**
- Uncertainty reduced by at least 20%
- New actionable insight discovered
- Conflict resolved that blocked progress

**Escalate to blocking question IF:**
- Budget exhausted (any layer)
- Stagnation detected and switch failed
- Missing information cannot be obtained with available tools
- Risk threshold exceeded (unsafe operation requested)

**Commit to recommendation IF:**
- Sufficient evidence gathered (confidence >= 0.8)
- All known blockers addressed or documented
- Implementation path is clear

---

## Stop Conditions

### Good Stops (Preferred)

1. **Actionable Recommendation Ready**
   - Confidence >= 0.8
   - Implementation path defined
   - Known risks documented
   - No unanswered blocking questions

2. **Precision Blocking Question Identified**
   - Single question that cannot be answered via available tools
   - Question addresses fundamental ambiguity
   - Answer to question unblocks implementation

3. **Budget Exhausted with Best Effort**
   - Max iterations reached
   - Current recommendation is best possible with gathered evidence
   - Blocking question clearly states what remains uncertain

### Bad Stops (Avoid)

1. **Evidence Theater**
   - Multiple subagent calls without synthesis
   - Information gathered but not applied to decision

2. **Over-Interviewing**
   - Questioning user when tools could answer
   - Vague "need more info" without specific missing items

3. **Premature Commit**
   - Recommendation without sufficient evidence
   - Confidence < 0.7 but recommendation provided anyway

4. **Unbounded Loop**
   - Continuing without progress indicators
   - No clear stopping criteria met

### Stop Output Format

When stopping, the planning agent MUST output:

```yaml
stop_reason: <one of: recommendation_ready | blocking_question | budget_exhausted | stagnation | human_required>
confidence: <0.0-1.0>
evidence_summary:
  - <brief summary of gathered evidence>
  - <key sources consulted>
uncertainties_remaining:
  - <specific items still unknown>
next_actions:
  - <if recommendation_ready: implementation steps>
  - <if blocking_question: the precise question>
  - <if budget_exhausted: how to proceed with new budget>
budget_consumed:
  iterations: <N>/<max>
  subagent_calls: <N>/<max>
  wall_time: <N>/<max>
```

---

## Next Best Question (Escalation Path)

### When to Escalate

The planning agent escalates to a blocking question when:

1. **Information Gap**: Critical information is missing and cannot be obtained via available tools
2. **Ambiguity**: User request has multiple valid interpretations and context cannot resolve
3. **Permission**: Required access (secrets, external services) is not available
4. **Conflict**: Contradictory policies or requirements exist

### Question Quality Standards

A valid blocking question must:

1. **Be Singular**: One question, not a list
2. **Be Answerable**: The human can provide a factual answer
3. **Be Blocking**: The answer unblocks the next planning step
4. **Be Contextual**: Include necessary background information

**Examples:**

✓ **Good**: "The auth module supports both JWT and session-based auth. Which should we use for the new API endpoint?"  
✗ **Bad**: "How should authentication work?" (too vague)  
✗ **Bad**: "Should we use JWT or sessions, and what about OAuth?" (multiple questions)

### Escalation Process

1. **Document Evidence**: Summarize what has been gathered
2. **Identify Gap**: State exactly what information is missing
3. **Formulate Question**: Craft a single, precise question
4. **Contextualize**: Include background for the human to understand the context
5. **Stop**: Do not continue investigation until question is answered

### Re-Entry After Answer

After a blocking question is answered, the planning agent:

1. **Acknowledges Answer**: Confirm understanding of the provided information
2. **Re-evaluates Plan**: Adjust planning approach based on new input
3. **Resumes from Last State**: Continue from where the question was asked, not from scratch
4. **Updates Budget**: Reset iteration counter (question answered = new planning cycle)

---

## First 2-3 Turn UX Policies

### Turn 1: Triad Lock-In

**Required Output by End of Turn 1:**

```yaml
goal: <concise restatement of what the agent is trying to achieve>
constraints:
  - <known limitations (tools, permissions, time)>
  - <boundaries of scope>
initial_evidence:
  - <what is already known or assumed>
```

**Behavior Rules:**
- DO NOT start investigating before establishing goal/constraints/evidence triad
- DO confirm understanding with user if goal is ambiguous
- DO identify constraints early (e.g., "I cannot access external services")

**Example:**
```
Goal: Determine the best approach to add JWT authentication to the auth module
Constraints:
  - Only have read access to codebase (plan mode)
  - Cannot run external services or install dependencies
  - Must complete within 5 iterations
Initial Evidence:
  - Auth module exists at src/auth/
  - Current implementation uses session-based auth (from README)
```

### Turn 2: Budget-First Bounding Box

**Required Output by End of Turn 2:**

```yaml
exploration_plan:
  - <specific subagent dispatch or tool call>
  - <information expected from each action>
budget_allocation:
  max_iterations: <N>
  max_subagent_calls: <N>
  estimated_wall_time: <N minutes>
```

**Behavior Rules:**
- DO commit to specific investigation steps, not vague exploration
- DO allocate budget explicitly (use defaults unless user specified otherwise)
- DO NOT exceed budget without user override

**Example:**
```
Exploration Plan:
  1. Dispatch explore agent to find all auth-related files
  2. Dispatch librarian agent to research JWT best practices
Budget Allocation:
  - Max iterations: 5 (default)
  - Max subagent calls: 8 (default)
  - Estimated time: 3 minutes
```

### Turn 3: Novelty Checkpoint

**Required by End of Turn 3:**

```yaml
novelty_check:
  new_information: <yes|no>
  uncertainty_reduction: <percentage>
  confidence_level: <0.0-1.0>
continue_decision: <continue|switch|escalate|commit>
```

**Behavior Rules:**
- DO evaluate whether new information was gained
- DO quantify progress (uncertainty reduction, confidence)
- DO switch strategy if novelty is low (< 20% uncertainty reduction)
- DO escalate to blocking question if no progress

**Example:**
```
Novelty Check:
  - New Information: YES (found existing JWT integration tests)
  - Uncertainty Reduction: 40% (now know JWT patterns are supported)
  - Confidence Level: 0.6
  - Continue Decision: CONTINUE (need to verify JWT implementation is complete)
```

### Stagnation Tripwire

**Detection (after Turn 3):**
Monitor for stagnation on every subsequent turn. If detected:

```yaml
stagnation_detected: true
trigger: <one of: repeated_failure | no_new_files | confidence_plateau | redundant_queries>
current_strategy: <description of failed strategy>
switching_to:
  new_strategy: <fundamentally different approach>
  new_budget:
    max_iterations: 2
    max_subagent_calls: 3
  hypothesis: <what this new strategy tests>
```

### Decision Gate (Post-Novelty Check)

After novelty checkpoint, decide:

```
IF confidence >= 0.8:
  -> COMMIT to recommendation

ELIF stagnation detected:
  -> SWITCH strategy (with reduced budget)

ELIF uncertainty reduction < 20% for 2 turns:
  -> ESCALATE to blocking question

ELSE:
  -> CONTINUE next iteration
```

---

## Runtime Integration Notes

### Canonical Source

This document (`docs/planning-agent-orchestration.md`) is the **canonical source** for planning agent orchestration policy.

### Runtime Surfaces

Runtime prompt surfaces must reflect this spec:

- **Entry contract**: `dawn_kestrel/tools/prompts/plan_enter.txt`
- **Exit contract**: `dawn_kestrel/tools/prompts/plan_exit.txt`
- **Agent permissions**: `dawn_kestrel/agents/builtin.py` (PLAN_AGENT)

### Safety Guarantees (Preserved)

The planning agent maintains existing safety semantics:

- **Edit/write tools denied** in plan mode (enforced by permission rules)
- **Tool filtering** prevents file modification during planning
- **Exit to build mode** is required for implementation tasks

### Context Assembly Path

Runtime context assembly follows:
1. Agent base prompt (from agent definition)
2. Skills injection (via `SkillInjector`)
3. Planning orchestration policy (future integration point)

**Note**: Full orchestration policy integration into runtime context builder is deferred to future tasks. Current runtime uses stubs in `plan_enter.txt` and `plan_exit.txt`.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-06 | Initial canonical spec from Task 2 |

---

## References

- Integration map: `.orchestrator/integration-map.md`
- Original plan: `.orchestrator/plans/planning-agent-initial-conversation-orchestration.md`
- Review agent orchestration: `dawn_kestrel/agents/review/README.md`
- Agent PRD: `AGENTIC_REVIEW_PRD.md`
