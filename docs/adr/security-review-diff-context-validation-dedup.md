# ADR: Security Review Diff Context, Deduplication, and Validation Defaults

## Status
**Accepted** - 2026-02-10

## Context
The security reviewer agent enhancement requires explicit defaults for diff handling, concurrency, confidence thresholds, and error strategies. These defaults enable deterministic behavior across iterations while balancing performance, accuracy, and resource utilization.

## Decision

### 1. Diff Chunking Strategy

**Chosen Default:** 5000 characters per subagent prompt segment

**Rationale:**
- Balances context richness with token budget constraints
- Fits within typical LLM context windows (4k-8k tokens for diff content)
- Allows multiple hunks to be analyzed in parallel
- Deterministic ordering enables reproducible outputs

**Implementation:**
```python
DIFF_CHUNK_SIZE = 5000  # characters per subagent prompt
```

**Alternatives Considered:**
- 2000 chars: Too restrictive, misses cross-file context
- 10000 chars: Exceeds token budget for parallel execution
- Token-based: Too variable across models; character count more stable

### 2. Parallel Scanner Concurrency Cap

**Chosen Default:** 4 concurrent subagent tasks maximum

**Rationale:**
- Prevents resource exhaustion on LLM provider side
- Allows sufficient parallelism for performance benefit (~4x speedup)
- Fits within typical rate limits for production APIs
- Reduces chance of cascading failures

**Implementation:**
```python
MAX_CONCURRENT_SUBAGENTS = 4
```

**Alternatives Considered:**
- 2 concurrent: Too conservative, performance penalty
- 8 concurrent: Risks rate limit errors and timeout cascades
- Unbounded: Dangerous for production deployments

### 3. Confidence Threshold

**Chosen Default:** 0.50 default inclusion threshold

**Rationale:**
- Filters out speculative low-confidence findings
- Retains findings with meaningful evidence
- Balances false positive vs false negative tradeoff
- Provides clear, measurable threshold for tuning

**Implementation:**
```python
CONFIDENCE_THRESHOLD = 0.50  # include findings >= this confidence
```

**Configuration Options:**
- Higher threshold (0.70-0.80): Strict mode, fewer findings, higher precision
- Lower threshold (0.30-0.40): Permissive mode, more findings, higher recall

### 4. Error Strategy

**Chosen Default:** Malformed finding payloads are rejected and logged; review continues unless critical system failure occurs

**Rationale:**
- Prevents malformed outputs from breaking entire review
- Enables continued analysis of other scanners
- Logs provide audit trail for investigation
- Critical-only stop ensures partial results delivered

**Implementation:**
```python
# Malformed finding handling
try:
    finding = Finding.model_validate(finding_data)
except ValidationError as e:
    logger.warning(f"Rejected malformed finding: {e}")
    continue  # Skip this finding, continue with others
```

**Error Categories:**
- **Recoverable:** Malformed schema, missing fields, invalid enum values → log and skip
- **Critical:** LLM API failure, timeout exceeding budget, context missing → stop review

### 5. Deduplication Strategy

**Chosen Default:** Uniqueness by finding ID and content signature

**Rationale:**
- Prevents duplicate findings from multiple scanners
- Allows semantic duplicates to be merged
- Deterministic across iterations
- Enables idempotent result aggregation

**Implementation:**
```python
processed_finding_ids: Set[str] = set()
content_signatures: Set[str] = set()

def is_duplicate(finding: Finding) -> bool:
    if finding.id in processed_finding_ids:
        return True
    signature = f"{finding.file_path}:{finding.line_number}:{finding.severity}"
    if signature in content_signatures:
        return True
    return False
```

## Consequences

### Positive
- **Deterministic Behavior:** Same inputs produce same outputs across runs
- **Predictable Performance:** Known resource limits enable accurate SLA estimation
- **Debuggable:** Clear defaults make troubleshooting easier
- **Tunable:** Thresholds exposed as configuration for environment-specific tuning

### Negative
- **Fixed Limits:** May require tuning for edge cases (very large PRs, specialized codebases)
- **Conservative Defaults:** Thresholds prioritize correctness over recall; may miss low-signal findings

## Trade-offs

| Aspect | Choice | Trade-off |
|---------|--------|------------|
| Diff Chunking | 5000 chars | Loses some cross-file context vs token budget safety |
| Concurrency | 4 tasks | Limits parallelism vs rate limit safety |
| Confidence | 0.50 threshold | Filters weak findings vs risk of missing valid issues |
| Error Strategy | Log & continue | Partial results vs all-or-nothing outcomes |

## References
- [Security Agent Improvement Plan](../security-agent-improvement-plan.md)
- [Security Reviewer FSM Implementation](../../dawn_kestrel/agents/review/fsm_security.py)
- [Review Contracts](../../dawn_kestrel/agents/review/contracts.py)
- Task 10 in Execution Plan: "Update documentation and implementation notes"
