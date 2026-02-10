# Decisions Log: Security Agent Improvement Execution Plan

This file tracks architectural choices and decisions made during execution.

---

## [2026-02-10T18:51:40Z] Session Init

Defaults Applied (from plan):
- Diff chunk budget: 5000 characters per subagent prompt segment
- Parallel scanner cap: 4 concurrent subagent tasks maximum
- Confidence threshold: 0.50 default inclusion threshold
- Error strategy: malformed finding payloads are rejected and logged

Awaiting implementation decisions from Wave 1...

---

## [2026-02-10T11:55:00Z] Task 1: Baseline Contract Locking

### Decisions Confirmed

1. **Default Values Finalized**
   - **diff_chunk_size: 5000 characters**
     - Rationale: ~800-1000 tokens, fits typical LLM context windows
     - Allows ~150-200 lines of diff context per subagent
     - Applied in: `_build_subagent_prompt()` (TD-004)

   - **max_parallel_subagents: 4 concurrent tasks**
     - Rationale: Balances throughput with API rate limits
     - Prevents resource exhaustion from massive subagent pools
     - Applied in: `_delegate_investigation_tasks()` with asyncio.Semaphore (TD-017)

   - **confidence_threshold: 0.50 (50%)**
     - Rationale: Balanced filter (not too strict, not too permissive)
     - Allows medium+ confidence findings in final report
     - Applied in: Final assessment filtering (TD-018)

   - **error_strategy: "reject and log"**
     - Rationale: Strict validation prevents cascading errors
     - Logging enables debugging of subagent output issues
     - Applied in: `_review_investigation_results()` (current behavior, TD-010 will enhance)

2. **Backward Compatibility Strategy**
   - **No field removals or renames in existing schemas**
     - `ReviewOutput` fields remain unchanged
     - `Finding` fields remain unchanged
     - Guarantees existing code continues to work

   - **New fields are optional with defaults**
     - Can add `confidence_score: float | None = None` to Finding
     - Can add `processed: bool = False` to SubagentTask
     - Backward compatible because Pydantic allows omitted optional fields

   - **Schema extensions via new fields only**
     - No changes to field types (e.g., severity Literal values)
     - No changes to validation rules (extra="forbid" maintained)
     - Extension points identified: confidence_score, diff_context, tracking flags

3. **Success Gates Are Measurable**
   - **Accuracy**: `len(findings_with_valid_files) / len(findings) * 100`
     - Target: 100% (all findings reference changed files)
     - Verification: Cross-reference `file_path` against `context.changed_files`

   - **No Duplicates**: `1 - (len(unique_ids) / len(findings)) * 100`
     - Target: 0% (no duplicate finding IDs)
     - Verification: Set-based deduplication in `_review_investigation_results()`

   - **Evidence Quality**: `len(findings_with_evidence) / len(findings) * 100`
     - Target: 100% (all findings have non-empty evidence field)
     - Verification: Filter on `f.evidence and f.evidence.strip()`

   - **Coverage**: `len(files_with_findings) / len(changed_files) * 100`
     - Target: 100% (all changed files have findings or are skipped)
     - Verification: Check each changed file appears in findings or skips

   - **Performance**: `end_time - start_time` for review execution
     - Target: <= 300 seconds (5 minutes) for 100-file PR
     - Verification: Timer from `run_review()` start to assessment return

   - **False Positive Rate**: `false_positives / total_findings * 100`
     - Target: < 5% on clean diffs
     - Verification: Requires human-labeled test dataset (TD-013)

4. **Critical Path Established**
   - **TD-001 → TD-002 → TD-003 → TD-004** (must be sequential)
     - Reason: Fixes must precede real analysis implementation
     - TD-001 (finding dedup) needed before TD-009 (validation)
     - TD-002 (task tracking) needed before TD-004 (pass diff)
     - TD-003 (todo tracking) fixes log confusion before integration tests

   - **TD-004 is linchpin**
     - Enables TD-005, TD-006, TD-007, TD-008 (all real analysis)
     - Without diff context, subagents cannot analyze actual code
     - Must complete before Wave 2 (parallelizable analysis tasks)

5. **Validation Strategy**
   - **Strict rejection of malformed payloads**
     - Pydantic validation errors are caught in base.py:351-376
     - Returns `ReviewOutput` with `severity="critical"` and `decision="needs_changes"`
     - Does NOT append invalid findings to `self.findings`

   - **Graceful degradation is NOT the goal**
     - Malformed findings should fail explicitly, not be silently corrected
     - Enables debugging of subagent output format issues
     - Subagent can retry with corrected prompt

### No Decisions Deferred

- All defaults are now explicit and documented
- No unresolved ambiguities remain for Wave 1
- Ready to proceed with implementation
