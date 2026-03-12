# Change Taxonomy & Ownership
*A practical guide for where to make changes (prompt vs policy vs harness vs adapter) and what to test.*

## Layers (who owns what)
- **Harness (code)**: invariants, safety, auditability, reproducibility, accounting, budgets.
- **Policy (agent decision engine)**: how to choose next steps (ReAct / plan-execute / BT / rules), exploration strategy.
- **Model Adapter**: provider quirks, parsing/repair, schema enforcement, retries, streaming, tool-call normalization.
- **Prompts (agent/skill/tool text)**: interface contracts, required artifacts, tone; not hard guarantees.
- **Model Overlay Prompts (last resort)**: small model-specific deltas for consistent formatting/tool-use gaps.

## Decision Rule (fast heuristic)
- If you can write a **deterministic test** for it -> put it in **Harness** (or **Adapter** if it is formatting/provider-specific).
- If it is about **choosing what to do next** -> **Policy**.
- If it is about **how to express/structure** outputs -> **Prompts + Prompt QA**.
- If only **one model** needs special wording -> **Overlay**, keep it tiny and measured.

---

## Change Matrix (examples, where to change, what to test)

### 1) Model change causes behavior drift
**Symptom:** new model skips tools, violates JSON, becomes verbose, ignores constraints.

**Primary change location**
- **Adapter:** stricter schema validation + repair + retry; tool-call normalization; truncation/continuation handling.
- **Harness:** enforce invariants so drift cannot violate "musts".

**Secondary**
- **Policy:** route tool-heavy tasks to a better model; switch policy for certain task classes.
- **Overlay prompt:** small compliance addendum only if required.

**Tests to add**
- Golden scenarios for schema compliance + tool-call correctness.
- Drift alert: prompt policy extraction diff should not soften MUST/NEVER.
- Trace grader: "DONE requires verification event".

---

### 2) Agent claims "done" with no evidence
**Change location**
- **Harness:** hard invariant: `DONE` blocked unless `TodoVerified` exists + verifier passed.
- **Verifier:** add/strengthen checks (tests/lint/file_contains).
- **Prompt:** require evidence refs in completion claim (nice-to-have).

**Tests**
- Trace ordering grader: verify-before-done.
- Evidence grader: every VERIFIED_DONE has evidence.

---

### 3) Too many tool retries / runaway loops
**Change location**
- **Harness:** retry budgets, exponential backoff, circuit breakers, max iterations.
- **Policy:** fallback strategy (BT works well), exploration depth cap ("chaos budget").
- **Prompt:** artifact requirement: "generate 2 options then pick 1".

**Tests**
- Budget grader: tool retries <= max.
- Liveness grader: progress signal every N steps.

---

### 4) Scope creep: edits too many files or wrong directories
**Change location**
- **Harness:** diff guardrails (allowed paths, max files, max LOC).
- **Policy:** chunk TODOs smaller; plan constraints.
- **Prompt:** declare intended touched files up front.

**Tests**
- Diff grader: touched files limited to allowlist.
- Repo invariant grader: no changes outside scope.

---

### 5) Picks wrong tool first (search vs repo read)
**Change location**
- **Policy:** tool preference strategy / scoring.
- **Prompt:** soft guidance for tool selection.
- **Harness:** only if it is a cost/safety boundary.

**Tests**
- Trace grader: for "repo-local tasks", first tool must be `read_file`/`grep` before `web_search` (if you want that rule).

---

### 6) Infinite replanning / plan churn
**Change location**
- **Harness:** max plan churn; require concrete progress signal.
- **Policy:** BT fallback ("if plan fails twice -> ask human / switch strategy").
- **Prompt:** require explicit stop conditions.

**Tests**
- Trace grader: plan updates <= max.
- Liveness: must complete or ask human within N iterations.

---

### 7) Ambiguous request: agent guesses instead of asking
**Change location**
- **Policy:** ambiguity detector -> ask clarifying question under threshold.
- **Harness:** enforce `ASK_HUMAN` for high-risk ambiguity.
- **Prompt:** definition of ambiguity + one-question rule.

**Tests**
- Scenario: "Make it faster" must ask for metric or propose measurable target + confirm.

---

### 8) JSON output invalid sometimes
**Change location**
- **Adapter:** schema validation + repair loop; constrained retry prompt.
- **Harness:** reject invalid output; return structured error to agent.
- **Prompt:** include schema and strict "no extra keys".

**Tests**
- JSON schema validator in CI + runtime.
- Golden scenario: invalid JSON must be repaired within N retries.

---

### 9) Tool output parsing breaks (format variability)
**Change location**
- **Adapter/Harness:** normalize tool outputs into typed `ToolResult`.
- **Context Builder:** give agent structured summaries, not raw logs.

**Tests**
- Parsing unit tests for tool output variants.
- Trace consistency checks: every tool call has normalized result event.

---

### 10) High-risk actions need approval (deploy/delete/post/spend)
**Change location**
- **Harness:** hard gate; block tool until `ApprovedByHuman` event.
- **Policy:** generate approval packet (plan, risk, rollback).
- **Prompt:** approval packet format.

**Tests**
- Trace grader: risky tool call must be preceded by approval event.

---

### 11) Add a new capability/tool ("summarize PR", "explain diff")
**Change location**
- **Command (Harness):** new action type with validation + logging.
- **Tool prompt:** strict I/O contract.
- **Evals:** golden scenarios for tool use.

**Tests**
- Schema checks for tool output.
- Trace grader: tool used when requested.

---

### 12) Enforce repo conventions (naming, structure, style)
**Change location**
- **Project memory:** `conventions.md` (source of truth).
- **Verifier:** lint/format/typecheck + custom naming checks.
- **Prompt:** reference conventions; do not hardcode all rules.

**Tests**
- Convention grader: naming rules satisfied.
- Lint/typecheck gates.

---

### 13) Wording/phrase preferences ("no 'as an AI'", concise tone)
**Change location**
- **Prompt QA:** banned phrases + required sections (deterministic lint).
- **Prompt:** minimal style guide.

**Tests**
- Prompt lint in CI.
- Optional rubric eval for tone.

---

### 14) "Chaotic but not too much" (controlled creativity)
**Change location**
- **Harness:** chaos budget (max retries, tool diversity, plan churn, edit radius).
- **Policy:** exploration strategy (2 candidates then pick 1; best-first).
- **Prompt:** require alternatives + chosen action + risk level.

**Tests**
- Budget graders across chaos dimensions.
- Trace grader: includes alternatives artifact.

---

### 15) Runs too slow / iteration is painful
**Change location**
- **Harness:** caching, batching, compaction/summaries, tool timeouts.
- **Policy:** cheap-first, early-stop thresholds.
- **Adapter:** streaming / token caps / smaller model for routing.

**Tests**
- Performance budgets: max runtime, max tool latency.
- Regression tracking across releases.

---

### 16) Multi-model routing (cheap for easy, strong for hard)
**Change location**
- **Policy:** router selects model by task complexity and tool needs.
- **Harness:** budgets + escalation rules.
- **Adapter:** unified interface.

**Tests**
- Routing eval: scenarios map to expected model class.
- Cost/perf telemetry assertions (soft).

---

### 17) One model is bad at tool use but good at writing
**Change location**
- **Policy:** capability-aware routing by task type.
- **Adapter:** detect non-compliant tool-call formats and repair.
- **Overlay:** small compliance addendum only if routing is not possible.

**Tests**
- Tool-call compliance golden suite.
- Comparative pass rate by model.

---

### 18) Agent forgets constraints mid-run
**Change location**
- **Harness/Context Builder:** inject compact "contract block" every turn.
- **Policy:** ensure contract is referenced in decisions.
- **Prompt:** keep constraints canonical (do not duplicate everywhere).

**Tests**
- Trace grader: constraints present in granted context each step.
- Invariant checks block violations.

---

### 19) Skill prompts drift and become inconsistent over time
**Change location**
- **Prompt QA:** policy extraction diff + lint + golden tests.
- **Harness:** prompt registry with versions and audit artifacts.

**Tests**
- Prompt lint + drift threshold gating merges.
- Golden skill scenarios.

---

### 20) Workflow change: add VERIFY after ACT always
**Change location**
- **Harness phase skeleton:** PLAN -> ACT -> VERIFY -> DONE.
- **Policy:** which verifiers to run and when.
- **Prompts:** minimal (do not micromanage).

**Tests**
- Ordering grader: VERIFY happens before DONE.
- Verifier coverage report.

---

## Model Change Strategy (recommended default)
When you change models:

1. **Keep core prompts stable** (agent/skill/tool contracts).
2. Tighten **Adapter** (schema validation/repair, tool-call normalization).
3. Tighten **Harness invariants** (verify-before-done, approval gates, diff constraints).
4. Adjust **Policy** (router or switch policy for certain scenarios).
5. Add **tiny model overlay** only if a specific model consistently needs it.

**Avoid:** rewriting all prompts to chase model quirks.

---

## What to Add When You Make a Change (test checklist)
- **Deterministic graders** first (trace, ordering, budgets, diff, schema).
- Then **golden scenarios** that reproduce the bug.
- Only then **LLM rubric** graders (tone/clarity), never as the only gate.

---

## Quick "where should this go?" prompts (for yourself)
- "Will I be angry if it violates this?" -> Harness invariant.
- "Is this formatting/provider-specific?" -> Adapter.
- "Is this choosing between valid options?" -> Policy.
- "Is this about communication or artifact structure?" -> Prompts + Prompt QA.
- "Is only one model struggling?" -> Tiny model overlay (plus eval coverage).
