# Learning Log: Security Agent Improvement Execution Plan

This file tracks patterns, conventions, and learnings discovered during execution.

---

## [2026-02-10T18:51:40Z] Session Init

Plan Analysis:
- 14 tasks organized in 6 execution waves
- Critical path: 1 → 2 → 3 → 4 → 6 → 8 → 14
- Key deliverable: deterministic, diff-aware security review pipeline

Notepad initialized. Beginning Wave 1...

---

## [2026-02-10T11:55:00Z] Task 1: Lock Baseline Contracts

Learnings from baseline contract analysis:

### Contract Structure Patterns

1. **Pydantic Validation is Ubiquitous**
   - `ReviewOutput` and `Finding` use `extra="forbid"` to reject malformed payloads
   - Literal types enforce allowed values (e.g., `Literal["merge", "warning", "critical", "blocking"]`)
   - Validation errors from `pd.ValidationError` are caught in `_execute_review_with_runner()` (base.py:351-376)

2. **FSM Enforces State Machine Correctness**
   - `VALID_TRANSITIONS` dict maps each state to allowed next states (fsm_security.py:223-240)
   - Invalid transitions log error and return `False` (lines 287-292)
   - State transitions are logged: `[FSM transitioned: {from} -> {to}]` (line 303)

3. **Dataclass vs BaseModel Split**
   - FSM uses `@dataclass` for internal state (SecurityFinding, SecurityTodo, SubagentTask)
   - Contracts use `pd.BaseModel` for external interfaces (ReviewOutput, Finding)
   - Reason: Dataclasses are simpler for internal state, Pydantic for validation

### Ambiguity Discovery

1. **No Finding ID Uniqueness Enforcement**
   - `_review_investigation_results()` appends findings without checking ID existence
   - `total_findings` is simply `len(self.findings)` which includes duplicates
   - Finding IDs can collide across subagents (e.g., both return "sec_001")

2. **Mock Analysis Hardcoded**
   - `_simulate_subagent_execution()` returns static mock findings (lines 740-891)
   - No actual diff analysis or code scanning
   - Findings reference fake files (config.py, api.py) not from actual PR

3. **No Task State Persistence**
   - `_wait_for_investigation_tasks()` waits for ALL tasks each iteration (lines 896-908)
   - No tracking of which tasks were already processed in prior iterations
   - Completed tasks are re-delegated when FSM loops back to DELEGATING_INVESTIGATION

4. **Diff Context Missing from Subagent Prompts**
   - `_build_subagent_prompt()` only includes file names and diff size (lines 684-735)
   - Actual diff content is NOT passed to subagents
   - Prompt shows: "Changed files: file1.py, file2.py\n- Total diff size: 5000 characters"
   - But no actual code to analyze

### Schema Extension Points Identified

1. **Finding Schema Can Add Confidence Scores**
   - Current `Finding` has no confidence field
   - Can add `confidence_score: float` (0.0-1.0) without breaking existing code
   - Enables TD-018: Add finding confidence scores

2. **SubagentTask Schema Can Track Processed State**
   - Current fields: `task_id`, `todo_id`, `description`, `agent_name`, `prompt`, `tools`, `status`, `result`, `error`
   - Can add `processed: bool = False` flag to track across iterations
   - Enables TD-002: Track processed subagent tasks

3. **SecurityFinding Schema Can Validate Against Changed Files**
   - Current `SecurityFinding` has `file_path: Optional[str]` but no validation
   - Can add validation in `_review_investigation_results()` to check against `self.context.changed_files`
   - Enables TD-009: Validate findings against changed files

### Success Gates Implementation Strategy

1. **Accuracy Gate (100% of findings reference changed files)**
   ```python
   changed_file_set = set(self.context.changed_files)
   valid_findings = [f for f in self.findings if f.file_path in changed_file_set]
   accuracy = len(valid_findings) / len(self.findings) * 100
   ```

2. **No Duplicates Gate (0% duplicate findings)**
   ```python
   unique_ids = set(f.id for f in self.findings)
   duplicate_count = len(self.findings) - len(unique_ids)
   duplicate_rate = duplicate_count / len(self.findings) * 100
   ```

3. **Evidence Quality Gate (100% of findings have evidence)**
   ```python
   findings_with_evidence = [f for f in self.findings if f.evidence and f.evidence.strip()]
   evidence_quality = len(findings_with_evidence) / len(self.findings) * 100
   ```

### Backward Compatibility Confirmed

1. **Schema Extensions Are Safe**
   - Adding optional fields with defaults does NOT break existing code
   - Pydantic validation allows extra fields in input but rejects them in output if `extra="forbid"`
   - `ReviewOutput` and `Finding` contracts are stable (no field removals planned)

2. **No Breaking Changes to FSM**
   - State enum values are strings (str, Enum) - safe to add states
   - VALID_TRANSITIONS dict can be extended without breaking existing transitions
   - State transition logic (`_transition_to()`) validates against dict, so new states work automatically

### Performance Baseline

1. **Current Execution is Sequential**
   - Subagent tasks are executed in `_wait_for_investigation_tasks()` sequentially
   - Each task waits 0.5 seconds in `_simulate_subagent_execution()` (line 738)
   - No asyncio.gather() or semaphore-based parallel execution
   - Performance target: 5 minutes for 100-file PR (TD-017 will add parallel execution)

2. **Diff Size is Not Limited**
   - Current implementation includes entire diff in `_build_subagent_prompt()` (not actually passed, but would be if it were)
   - No chunking or truncation logic
   - Default 5000 char budget will be applied in TD-004

### Key Insights

1. **FSM Architecture is Sound**
   - State machine design prevents invalid transitions
   - Review loop is well-structured (EXPLORATION → DELEGATING → REVIEWING → CREATING → ASSESSMENT)
   - Hard max iterations (5) prevents infinite loops

2. **Contracts Are Well-Defined**
   - Pydantic models enforce structure at subagent output boundaries
   - Merge policy (PriorityMergePolicy) provides consistent merge decisions
   - Review context (ReviewContext) encapsulates all needed metadata

3. **Implementation Gaps Are Clear**
   - All 18 tasks map to specific code locations
   - Known issues are documented in plan with line number references
   - Success gates are measurable and achievable

### Documentation Completeness

- ✅ All dataclass fields documented (SecurityFinding, SecurityTodo, SubagentTask, SecurityAssessment)
- ✅ All Pydantic model fields documented (ReviewOutput, Finding, Scope, Check, Skip, MergeGate)
- ✅ All FSM states and transitions documented (8 states, 13 transitions)
- ✅ All defaults specified (diff_chunk_size, max_parallel_subagents, confidence_threshold, error_strategy)
- ✅ All success gates defined (accuracy, no_duplicates, evidence_quality, coverage, performance, false_positive_rate)

Baseline locked successfully. Ready to proceed with Wave 1 implementation.

---

## [2026-02-10T12:00:00Z] Task 10: Documentation Updates (TD-015)

### Documentation Created

**Files Created:**
1. `docs/adr/security-review-diff-context-validation-dedup.md` - Complete ADR note with all chosen defaults and rationale

**Files Updated:**
1. `docs/reviewers/security_reviewer.md` - Comprehensive documentation update with:
   - Real Analysis Mode (Historical Transition) section
   - Deduplication Strategy section
   - Validation Gates section (Changed-Files Scope, Evidence Quality, Uniqueness)
   - Changed-Files-Only Finding Example
   - Configuration section with tunable defaults
   - Logging section

### Documentation Structure Insights

**YAML Frontmatter Pattern Confirmed:**
- Reviewer docs use YAML frontmatter for agent patterns (agent, agent_type, version, patterns, heuristics)
- Markdown documentation follows YAML frontmatter (--- delimiter)

**Documentation Sections Added:**
- Historical transition explanation (Mock mode DEPRECATED)
- Real analysis mode description with diff-aware subagent prompts
- Deduplication strategy: ID-based + content signature-based
- Idempotent task processing explanation with multi-iteration example
- Three validation gates: Changed-Files, Evidence Quality, Uniqueness
- Complete changed-files-only finding example with validation checklist
- Configuration defaults table and environment-specific tuning examples
- Structured logging format with deduplication and validation examples

### Mock-Mode References Removed
- [x] Security reviewer docs now document historical mock behavior as "DEPRECATED"
- [x] All sections describe current real analysis implementation
- [x] No stale instructions about `simulate_subagent_execution only` remain in reviewer docs

### Documentation Verification Completed

**Required Sections Present ✅**
- [x] Deduplication - Complete with ID-based and content signature methods
- [x] Diff Context - Complete with chunking strategy and propagation rules
- [x] Validation Gates - Complete with changed-files, evidence, and uniqueness checks
- [x] Changed-files-only finding example - Complete with validation checklist

**No Contradictions ✅**
- [x] ADR defaults (5000 chars, 4 concurrent, 0.50 confidence) match security_reviewer.md configuration
- [x] Deduplication strategy consistent across ADR and reviewer docs
- [x] Validation gates align with finding schema in contracts.py
- [x] Finding example includes all required fields and passes validation

### Key Decisions Made

1. **ADR Format:** Standalone ADR document (not embedded in plan file)
   - Rationale: ADRs need to be independent artifacts for reference
   - Location: `docs/adr/` directory for discoverability

2. **Documentation Updates:** Appended to existing security_reviewer.md
   - Rationale: Preserve existing YAML frontmatter and agent patterns
   - Approach: Added comprehensive markdown sections after YAML frontmatter

3. **Finding Example: Concrete changed-files-only scenario
   - AWS access key in config.py (realistic production vulnerability)
   - Full JSON with all required fields: id, title, severity, confidence, owner, estimate, evidence, risk, recommendation
   - Validation checklist showing all gates pass

4. **Default Documentation:** All defaults documented with rationale
   - Diff chunking: 5000 characters - balances context vs token budget
   - Concurrency: 4 tasks - prevents resource exhaustion while providing parallelism
   - Confidence: 0.50 - filters low-signal findings while retaining valid ones
   - Error strategy: Log and continue - partial results vs all-or-nothing

