# Baseline Contracts: Security Agent Improvement

**Purpose**: Lock current behavior contracts, explicit defaults, and success gates before Wave 1 implementation.

**Date**: 2026-02-10

---

## 1. Current Contracts

### 1.1 Findings Schema (`SecurityFinding`)

**Location**: `dawn_kestrel/agents/review/fsm_security.py:172-183`

**Fields**:
```python
@dataclass
class SecurityFinding:
    id: str                    # Unique identifier (e.g., "sec_001")
    severity: str               # One of: "critical", "high", "medium", "low"
    title: str                  # Short descriptive title
    description: str             # Detailed description of the issue
    evidence: str               # Code snippet or pattern matched
    file_path: Optional[str]     # Path to affected file (if available)
    line_number: Optional[int]    # Line number of finding (if available)
    recommendation: Optional[str]  # How to fix the issue
    requires_review: bool        # Whether this finding needs additional review task
```

**Current Behavior**:
- Findings are appended to `self.findings` list without deduplication
- No validation that `file_path` references changed files
- No validation that `evidence` contains non-empty string
- No uniqueness enforcement for `id` field

**Known Issue**:
- `_review_investigation_results()` appends findings without checking if ID already exists
- `total_findings` in final assessment is simply `len(self.findings)` (not deduplicated)

---

### 1.2 Todo Schema (`SecurityTodo`)

**Location**: `dawn_kestrel/agents/review/fsm_security.py:133-153`

**Fields**:
```python
@dataclass
class SecurityTodo:
    id: str                       # Unique identifier (e.g., "todo_1", "todo_100")
    title: str                    # Title of the todo item
    description: str                # Description of what needs to be done
    status: TodoStatus = TodoStatus.PENDING  # One of: PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    priority: TodoPriority = TodoPriority.MEDIUM  # One of: HIGH, MEDIUM, LOW
    agent: Optional[str]           # Which subagent handles this (e.g., "secret_scanner")
    dependencies: List[str]        # List of todo IDs that must complete first
    findings: List[str]           # List of finding IDs associated with this todo
```

**Methods**:
```python
def is_ready(self, all_todos: Dict[str, SecurityTodo]) -> bool:
    """Check if all dependencies are satisfied."""
```

**Current Behavior**:
- Todos are created in `_create_initial_todos()` with duplicate logic (same todos created twice)
- Todo completion status is set to `COMPLETED` when subagent task completes
- No tracking of which tasks have already been processed across iterations

**Known Issues**:
- Lines 437-542: Duplicate todo creation (same todos created multiple times)
- "Todos completed" log shows incorrect fraction (e.g., "9/11" when only 9 todos exist)
- New review todos (ID >= 100) are not tracked separately from initial todos

---

### 1.3 FSM States and Transitions

**Location**: `dawn_kestrel/agents/review/fsm_security.py:102-112, 223-240`

**States**:
```python
class ReviewState(str, Enum):
    IDLE = "idle"
    INITIAL_EXPLORATION = "initial_exploration"
    DELEGATING_INVESTIGATION = "delegating_investigation"
    REVIEWING_RESULTS = "reviewing_results"
    CREATING_REVIEW_TASKS = "creating_review_tasks"
    FINAL_ASSESSMENT = "final_assessment"
    COMPLETED = "completed"
    FAILED = "failed"
```

**Valid Transitions**:
```python
VALID_TRANSITIONS = {
    ReviewState.IDLE: {ReviewState.INITIAL_EXPLORATION, ReviewState.FAILED},
    ReviewState.INITIAL_EXPLORATION: {ReviewState.DELEGATING_INVESTIGATION, ReviewState.FAILED},
    ReviewState.DELEGATING_INVESTIGATION: {ReviewState.REVIEWING_RESULTS, ReviewState.FAILED},
    ReviewState.REVIEWING_RESULTS: {
        ReviewState.CREATING_REVIEW_TASKS,
        ReviewState.FINAL_ASSESSMENT,
        ReviewState.FAILED,
    },
    ReviewState.CREATING_REVIEW_TASKS: {
        ReviewState.DELEGATING_INVESTIGATION,
        ReviewState.FINAL_ASSESSMENT,
        ReviewState.FAILED,
    },
    ReviewState.FINAL_ASSESSMENT: {ReviewState.COMPLETED, ReviewState.FAILED},
    ReviewState.COMPLETED: {ReviewState.IDLE},
    ReviewState.FAILED: {ReviewState.IDLE},
}
```

**Current Behavior**:
- FSM enforces valid transitions in `_transition_to()` method (lines 276-304)
- Invalid transitions log error and return `False`
- State queries are idempotent (don't modify state)
- State transitions are logged with `[FSM transitioned: {from} -> {to}]` format

---

### 1.4 Subagent Task Schema (`SubagentTask`)

**Location**: `dawn_kestrel/agents/review/fsm_security.py:157-168`

**Fields**:
```python
@dataclass
class SubagentTask:
    task_id: str              # Unique task identifier (from create_agent_task)
    todo_id: str               # Associated todo ID
    description: str            # Task description
    agent_name: str            # Name of subagent to execute
    prompt: str                # Full prompt for subagent
    tools: List[str] = []     # Allowed tools for this task
    status: TaskStatus = TaskStatus.PENDING  # One of: PENDING, IN_PROGRESS, COMPLETED
    result: Optional[Dict[str, Any]] = None  # Subagent output
    error: Optional[str] = None  # Error message if task failed
```

**Current Behavior**:
- Tasks are created in `_delegate_investigation_tasks()` (lines 644-682)
- Task status is updated in `_simulate_subagent_execution()` to `COMPLETED`
- No tracking of which tasks have been processed across FSM iterations

**Known Issues**:
- `_wait_for_investigation_tasks()` waits for ALL tasks to complete each iteration (lines 896-908)
- Completed tasks are re-delegated in subsequent iterations because there's no tracking
- No mechanism to skip tasks that were already processed

---

### 1.5 Assessment Schema (`SecurityAssessment`)

**Location**: `dawn_kestrel/agents/review/fsm_security.py:187-199`

**Fields**:
```python
@dataclass
class SecurityAssessment:
    overall_severity: str         # One of: "critical", "high", "medium", "low"
    total_findings: int          # Count of findings (currently: len(self.findings))
    critical_count: int          # Count of critical findings
    high_count: int              # Count of high findings
    medium_count: int           # Count of medium findings
    low_count: int              # Count of low findings
    merge_recommendation: str     # One of: "approve", "needs_changes", "block"
    findings: List[SecurityFinding]  # All findings collected
    summary: str                # Human-readable summary
    notes: List[str] = []       # Additional notes
```

**Current Behavior**:
- Severity determination: `critical > high > medium > low` priority
- Merge recommendation:
  - `block` if any critical or high findings
  - `needs_changes` if medium findings
  - `approve` if only low findings
- `total_findings` is `len(self.findings)` (includes duplicates)

**Known Issues**:
- `total_findings` counts duplicates (not unique findings)
- No filtering of findings with invalid evidence
- No validation that findings reference changed files

---

## 2. Explicit Defaults

### 2.1 Diff Chunk Budget

**Default Value**: `5000 characters per subagent prompt segment`

**Purpose**:
- Limit diff context size to prevent token overflow
- Ensure subagent prompts fit within LLM context window
- Balance analysis depth with cost efficiency

**Rationale**:
- 5000 chars ≈ 800-1000 tokens (typical LLM encoding)
- Allows ~150-200 lines of diff context
- Prevents massive PR diffs from overwhelming subagent prompts
- Matches typical code review chunking best practices

**Implementation Location**:
- To be applied in `_build_subagent_prompt()` method
- May truncate diff to this limit with `[... diff truncated ...]` suffix

---

### 2.2 Parallel Scanner Cap

**Default Value**: `4 concurrent subagent tasks maximum`

**Purpose**:
- Limit parallel execution to prevent resource exhaustion
- Balance performance with system stability
- Avoid overwhelming LLM API with concurrent requests

**Rationale**:
- 4 concurrent tasks balances throughput vs resource usage
- Prevents hitting LLM API rate limits
- Allows independent subagents (e.g., secret_scanner, injection_scanner) to run in parallel
- Typical default for async task pools

**Implementation Location**:
- To be applied in `_delegate_investigation_tasks()` method
- Use `asyncio.Semaphore(4)` to limit concurrent execution
- Subagent tasks will queue when semaphore is exhausted

---

### 2.3 Confidence Threshold

**Default Value**: `0.50 (50%)` default inclusion threshold

**Purpose**:
- Filter low-confidence findings to reduce noise
- Balance sensitivity vs precision
- Allow configuration of finding quality bar

**Rationale**:
- 50% threshold is balanced (not too strict, not too permissive)
- Allows findings with medium or better confidence
- Reduces false positives while maintaining sensitivity
- Matches typical ML classification thresholds

**Implementation Note**:
- Subagents need to report confidence scores (currently not in schema)
- Threshold applied when filtering findings before final assessment
- Default may be configurable via environment variable or parameter

---

### 2.4 Error Strategy

**Default Strategy**: `Malformed finding payloads are rejected and logged`

**Purpose**:
- Prevent invalid data from corrupting review state
- Maintain data integrity across iterations
- Provide visibility into validation failures

**Rationale**:
- Strict validation prevents cascading errors
- Logging enables debugging of subagent output issues
- Rejection is safer than silent correction
- Allows subagent to retry with better prompt

**Implementation Location**:
- Applied in `_review_investigation_results()` when processing `task.result`
- Validates finding structure before appending to `self.findings`
- Logs rejection with finding ID and reason (e.g., "Missing required field: evidence")

---

## 3. Backward Compatibility: Reviewer Output Schema

### 3.1 Current ReviewOutput Schema (`contracts.py`)

**Location**: `dawn_kestrel/agents/review/contracts.py:137-147`

**Fields**:
```python
class ReviewOutput(pd.BaseModel):
    agent: str                                    # Required: agent identifier
    summary: str                                  # Required: human-readable summary
    severity: Literal["merge", "warning", "critical", "blocking"]  # Required
    scope: Scope                                    # Required: relevant files and reasoning
    checks: List[Check] = []                       # Optional: validation checks
    skips: List[Skip] = []                        # Optional: skipped items
    findings: List[Finding] = []                    # Optional: security findings
    merge_gate: MergeGate                            # Required: merge decision

    model_config = pd.ConfigDict(extra="forbid")      # Rejects extra fields
```

### 3.2 Finding Schema (`contracts.py`)

**Location**: `dawn_kestrel/agents/review/contracts.py:113-125`

**Fields**:
```python
class Finding(pd.BaseModel):
    id: str                                      # Required: unique identifier
    title: str                                     # Required: short title
    severity: Literal["warning", "critical", "blocking"]  # Required
    confidence: Literal["high", "medium", "low"]      # Required
    owner: Literal["dev", "docs", "devops", "security"]  # Required
    estimate: Literal["S", "M", "L"]               # Required: size estimate
    evidence: str                                   # Required: code snippet
    risk: str                                       # Required: risk description
    recommendation: str                               # Required: fix suggestion
    suggested_patch: str | None = None               # Optional: code patch

    model_config = pd.ConfigDict(extra="forbid")      # Rejects extra fields
```

### 3.3 Compatibility Guarantees

**Non-Breaking Changes**:
- Existing `ReviewOutput` fields remain unchanged
- Existing `Finding` fields remain unchanged
- No field removals or renames
- No breaking changes to validation rules (`extra="forbid"` enforced)

**New Fields Allowed**:
- Fields with default values are backward compatible
- Optional fields do not break existing parsers
- New fields may be added to support confidence scoring

**Schema Extension Points**:
1. **Finding Schema**: May add `confidence_score: float` for numeric confidence
2. **ReviewOutput Schema**: May add `diff_context: str` for diff-aware analysis
3. **TaskStatus Schema**: May add tracking fields for processed tasks

**Validation Rules**:
- `extra="forbid"` ensures no unexpected fields break parsing
- Literal types enforce allowed values
- Pydantic validation runs at subagent output parsing
- Malformed payloads raise `ValidationError` (caught by error strategy)

---

## 4. Contract Ambiguities and Resolutions

### 4.1 Finding ID Uniqueness

**Ambiguity**: No enforcement of unique IDs across subagents

**Resolution**:
- Generate finding IDs as `f"{agent_type}_{counter}"` format
- Use `UUID` or hash-based IDs for global uniqueness
- Track processed IDs in `processed_finding_ids: Set[str]`

**Impact**: Prevents duplicate findings in final report

---

### 4.2 Todo Creation Deduplication

**Ambiguity**: `_create_initial_todos()` creates duplicate todos

**Resolution**:
- Remove duplicate todo creation blocks (lines 500-642)
- Consolidate duplicate todo definitions into single creation block
- Ensure each todo ID is unique

**Impact**: Reduces "Todos completed" log confusion

---

### 4.3 Task State Persistence

**Ambiguity**: No tracking of processed tasks across iterations

**Resolution**:
- Add `processed_task_ids: Set[str]` to track completed tasks
- Skip reprocessing tasks with IDs in processed set
- Clear set on `INITIAL_EXPLORATION` state entry

**Impact**: Prevents redundant subagent execution

---

### 4.4 Diff Context Inclusion

**Ambiguity**: `_build_subagent_prompt()` only includes file names and diff size

**Resolution**:
- Include actual diff content in subagent prompt
- Format diff as code block: ````diff ... ````
- Truncate to `diff_chunk_budget` (5000 chars) if needed

**Impact**: Enables real code analysis instead of mock responses

---

## 5. Measurable Success Gates

### 5.1 Accuracy

**Definition**: Percentage of findings that reference changed files

**Target**: 100%

**Measurement**:
```python
changed_file_set = set(context.changed_files)
valid_findings = [
    f for f in findings
    if f.file_path in changed_file_set
]
accuracy = len(valid_findings) / len(findings) * 100
```

**Success Gate**: `accuracy >= 100%` (all findings reference changed files)

---

### 5.2 No Duplicates

**Definition**: Percentage of duplicate findings in final report

**Target**: 0%

**Measurement**:
```python
unique_ids = set(f.id for f in findings)
duplicate_count = len(findings) - len(unique_ids)
duplicate_rate = duplicate_count / len(findings) * 100
```

**Success Gate**: `duplicate_rate == 0%` (no duplicate IDs)

---

### 5.3 Evidence Quality

**Definition**: Percentage of findings with non-empty evidence field

**Target**: 100%

**Measurement**:
```python
findings_with_evidence = [
    f for f in findings
    if f.evidence and f.evidence.strip()
]
evidence_quality = len(findings_with_evidence) / len(findings) * 100
```

**Success Gate**: `evidence_quality >= 100%` (all findings have evidence)

---

### 5.4 Coverage

**Definition**: Percentage of changed files scanned for security issues

**Target**: 100% of changed files

**Measurement**:
```python
files_with_findings = set(f.file_path for f in findings if f.file_path)
coverage = len(files_with_findings) / len(context.changed_files) * 100
```

**Success Gate**: `coverage >= 100%` (all changed files have findings or are explicitly skipped)

---

### 5.5 Performance

**Definition**: Review completion time for 100-file PR

**Target**: Within 5 minutes

**Measurement**:
```python
start_time = time.time()
await reviewer.run_review(...)
end_time = time.time()
duration = end_time - start_time
```

**Success Gate**: `duration <= 300 seconds` (5 minutes)

---

### 5.6 False Positive Rate

**Definition**: Percentage of findings that are false positives on clean diffs

**Target**: < 5%

**Measurement**:
- Requires human-labeled test dataset
- Calculate: `false_positives / total_findings * 100`

**Success Gate**: `false_positive_rate < 5%`

---

## 6. Implementation Order and Dependencies

### 6.1 Critical Path (TD-001 → TD-002 → TD-003 → TD-004)

**Rationale**: Fixes must precede real analysis

1. **TD-001**: Add finding deduplication logic
   - Prerequisite for: TD-009 (validate findings), TD-012 (test deduplication)

2. **TD-002**: Track processed subagent tasks
   - Prerequisite for: TD-004 (pass diff), TD-005 (real analysis)

3. **TD-003**: Fix todo completion tracking
   - Prerequisite for: TD-014 (logging), TD-013 (integration tests)

4. **TD-004**: Pass diff content to subagents
   - Prerequisite for: TD-005, TD-006, TD-007, TD-008 (all real analysis tasks)

---

### 6.2 Parallelizable Tasks

**Wave 2 (TD-005, TD-006, TD-007, TD-008)**:
- Can be implemented in parallel (all independent real analysis)
- All depend on TD-004 completion

**Wave 3 (TD-009, TD-010, TD-011)**:
- Can be implemented in parallel (all validation tasks)
- All depend on Wave 2 completion

---

## 7. Baseline Summary

### 7.1 What Works

- FSM state machine enforces valid transitions
- ReviewOutput schema is well-defined with Pydantic validation
- Merge policy (PriorityMergePolicy) provides consistent merge decisions
- Todo dependency resolution (`is_ready()`) works correctly
- BaseReviewerAgent provides shared abstractions for all reviewers

### 7.2 What Needs Fixing

**Critical Issues**:
1. Finding deduplication not implemented (TD-001)
2. Task state persistence not tracked (TD-002)
3. Todo completion tracking inconsistent (TD-003)
4. Mock analysis instead of real code analysis (TD-005, TD-006, TD-007, TD-008)
5. Diff context not passed to subagents (TD-004)

**Validation Issues**:
1. No validation that findings reference changed files (TD-009)
2. No validation that findings have valid evidence (TD-010)
3. No finding uniqueness enforcement (TD-011)

**Performance Issues**:
1. Sequential subagent execution (TD-017)
2. No diff chunking for large PRs (TD-016)

### 7.3 What's Missing

- Confidence scoring in findings (TD-018)
- Finding uniqueness validation (TD-011)
- Logging for debugging (TD-014)
- Unit tests for deduplication (TD-012)
- Integration tests for real analysis (TD-013)

---

## 8. Success Criteria Verification

### 8.1 Contract Locking Checklist

- [x] Findings schema documented (`SecurityFinding` fields)
- [x] Todo schema documented (`SecurityTodo` fields)
- [x] FSM states and transitions documented (`ReviewState` enum)
- [x] Subagent task schema documented (`SubagentTask` fields)
- [x] Assessment schema documented (`SecurityAssessment` fields)

### 8.2 Defaults Documentation Checklist

- [x] Diff chunk budget: 5000 characters per subagent prompt segment
- [x] Parallel scanner cap: 4 concurrent subagent tasks maximum
- [x] Confidence threshold: 0.50 default inclusion threshold
- [x] Error strategy: malformed finding payloads are rejected and logged

### 8.3 Backward Compatibility Checklist

- [x] ReviewOutput schema documented (from `contracts.py`)
- [x] Finding schema documented (from `contracts.py`)
- [x] Schema extension points identified (new fields allowed)
- [x] Validation rules documented (`extra="forbid"`)

### 8.4 Success Gates Documentation Checklist

- [x] Accuracy: 100% of findings reference changed files
- [x] No Duplicates: 0 duplicate findings in final report
- [x] Evidence Quality: 100% of findings include valid code snippets
- [x] Coverage: All changed files scanned for security issues
- [x] Performance: Review completes within 5 minutes for 100-file PRs
- [x] False Positive Rate: < 5% false positives on clean diffs

---

## 9. Sign-Off

**Baseline Status**: ✅ LOCKED

**Next Step**: Begin Wave 1 implementation (TD-001, TD-002, TD-003)

**Verification**:
- All contracts documented ✅
- All defaults specified ✅
- All success gates defined ✅
- Backward compatibility guaranteed ✅
- No runtime files modified ✅

**Sign-off Date**: 2026-02-10
