# Security Agent Enhancement Plan

## User Stories

### US-001: Finding Deduplication
**As a** security reviewer
**I want** findings to be deduplicated across iterations
**So that** I see an accurate count of unique security issues instead of duplicates

**Acceptance Criteria:**
- Findings are never reported more than once
- Total findings count reflects unique findings only
- Each finding has a unique ID across the entire review
- Iteration reports show cumulative unique findings, not additive

---

### US-002: Real Code Analysis
**As a** security reviewer
**I want** subagents to analyze actual code changes
**So that** findings are relevant to the PR being reviewed

**Acceptance Criteria:**
- Findings reference files that were actually changed in the PR
- Evidence snippets match real code from the diff
- No findings for files outside the changed file set
- Line numbers correspond to actual locations in changed files

---

### US-003: Diff-Aware Scanning
**As a** security reviewer
**I want** subagents to use diff context for targeted analysis
**So that** reviews focus on changed code, not the entire codebase

**Acceptance Criteria:**
- Subagents receive diff content in their prompts
- Secret scanning only examines added/modified lines
- Injection vulnerability checks focus on changed input handling
- Pattern matching uses diff context, not full file content

---

### US-004: Finding Uniqueness Tracking
**As a** security reviewer
**I want** the system to track which findings have been processed
**So that** iterations don't re-report the same issues

**Acceptance Criteria:**
- Processed finding IDs are tracked in a set
- Tasks marked as completed are not reprocessed
- Review loop skips already-analyzed findings
- Final report lists each finding exactly once

---

### US-005: Task State Management
**As a** security reviewer
**I want** subagent tasks to maintain correct state across iterations
**So that** completed tasks don't execute multiple times

**Acceptance Criteria:**
- Task status persists across FSM state transitions
- Delegated tasks are not re-delegated in subsequent iterations
- Todo completion status is accurate in logs
- "Todos completed" count matches actual completed todos

---

### US-006: Evidence-Based Findings
**As a** security reviewer
**I want** findings to include actual code snippets from changes
**So that** developers can immediately see the problematic code

**Acceptance Criteria:**
- Evidence field contains real code from the diff
- File paths match actual changed files
- Line numbers are accurate for the changed code
- Findings with no evidence are filtered out

---

## Gherkin Scenarios

### Feature: Finding Deduplication

```gherkin
Feature: Finding Deduplication
  As a security reviewer
  I want findings to be deduplicated across iterations
  So that I see an accurate count of unique security issues

  Scenario: Findings are not duplicated when reprocessing completed tasks
    Given a security review has completed iteration 1 with 5 findings
    And the FSM loops to iteration 2
    And the same subagent tasks are reviewed again
    When the review results are processed
    Then the total findings count should be 5
    And no finding ID should appear more than once
    And the findings list should contain exactly 5 unique items

  Scenario: New findings in subsequent iterations are added to existing ones
    Given a security review has completed iteration 1 with 3 findings
    And iteration 2 produces 2 new unique findings
    When the review results are processed
    Then the total findings count should be 5
    And all 3 findings from iteration 1 should be present
    And all 2 findings from iteration 2 should be present

  Scenario: Duplicate findings from different subagents are merged
    Given a secret scanner finding with ID "sec_001" was reported
    And another subagent reports the same finding with ID "sec_001"
    When the review results are processed
    Then only one instance of "sec_001" should appear in findings
    And the findings list should not contain duplicates
```

### Feature: Real Code Analysis

```gherkin
Feature: Real Code Analysis
  As a security reviewer
  I want subagents to analyze actual code changes
  So that findings are relevant to the PR being reviewed

  Scenario: Findings reference only changed files
    Given a PR has changed files ["auth.py", "config.py"]
    And the security review runs with diff content
    When the final assessment is generated
    Then all findings should reference files from changed_files
    And no findings should reference unchanged files like "utils.py"

  Scenario: Evidence snippets match actual diff content
    Given a PR contains the line "AWS_ACCESS_KEY_ID='AKIAIOSFODNN7EXAMPLE'" in config.py
    And the secret scanner subagent analyzes the diff
    When a secret finding is generated
    Then the evidence should contain "AWS_ACCESS_KEY_ID='AKIAIOSFODNN7EXAMPLE'"
    And the file path should be "config.py"
    And the line number should match the actual location in the diff

  Scenario: Findings are not generated for unchanged code
    Given a PR has changed files ["api.py"]
    And the file "utils.py" contains eval() but was not changed
    When the unsafe function scanner runs
    Then no finding should be reported for utils.py
    And findings should only reference api.py
```

### Feature: Diff-Aware Scanning

```gherkin
Feature: Diff-Aware Scanning
  As a security reviewer
  I want subagents to use diff context for targeted analysis
  So that reviews focus on changed code

  Scenario: Subagents receive diff in their prompts
    Given a security review is initialized
    And the diff contains 5000 characters of changed code
    When a subagent task is delegated
    Then the subagent prompt should include diff context
    And the prompt should specify the diff size
    And the prompt should list changed files

  Scenario: Secret scanning only examines added lines
    Given a PR adds a new line with an API key
    And removes 50 lines of old code
    When the secret scanner runs
    Then findings should only include the added API key
    And no findings should reference removed code

  Scenario: Injection checks focus on changed input handling
    Given a PR modifies a user input validation function
    And adds a new SQL query
    When the injection scanner runs
    Then findings should reference the new SQL query
    And findings should analyze the validation changes
```

### Feature: Task State Management

```gherkin
Feature: Task State Management
  As a security reviewer
  I want subagent tasks to maintain correct state across iterations
  So that completed tasks don't execute multiple times

  Scenario: Completed tasks are not reprocessed in subsequent iterations
    Given iteration 1 has completed 5 subagent tasks
    And all tasks have status COMPLETED
    When the FSM loops to iteration 2
    Then the 5 completed tasks should not be reprocessed
    And their findings should not be appended again
    And the task count should remain at 5

  Scenario: Task status persists across FSM state transitions
    Given a subagent task has status IN_PROGRESS
    When the FSM transitions to REVIEWING_RESULTS
    And then transitions to DELEGATING_INVESTIGATION again
    Then the task should still have status IN_PROGRESS
    And the task should not be redelegated

  Scenario: Todo completion status is accurate in logs
    Given 3 initial todos were created
    And all 3 have been completed
    When the review logs are printed
    Then the log should show "Todos completed: 3/3"
    And the log should not show incorrect fractions
```

### Feature: Evidence-Based Findings

```gherkin
Feature: Evidence-Based Findings
  As a security reviewer
  I want findings to include actual code snippets from changes
  So that developers can immediately see the problematic code

  Scenario: All findings contain valid evidence
    Given a security review produces 10 findings
    When the findings are reviewed
    Then every finding should have a non-empty evidence field
    And the evidence should be a code snippet
    And the evidence should match actual diff content

  Scenario: Findings without evidence are filtered out
    Given a subagent returns a finding with empty evidence
    When the review results are processed
    Then the finding should be rejected
    And the finding should not appear in the final list

  Scenario: Evidence includes surrounding context
    Given a secret is found at line 42 of config.py
    When the finding is generated
    Then the evidence should include lines 40-44 for context
    And the secret should be clearly highlighted
```

---

## Implementation Todos

### Phase 1: Critical Bug Fixes

- [ ] **TD-001: Add finding deduplication logic**
  - Add `processed_finding_ids: Set[str]` to `SecurityReviewerAgent.__init__`
  - Modify `_review_investigation_results()` to check for existing IDs before appending
  - Add unit tests for deduplication across multiple iterations
  - Verify `total_findings` count matches unique findings only

- [ ] **TD-002: Track processed subagent tasks**
  - Add `processed_task_ids: Set[str]` to `SecurityReviewerAgent.__init__`
  - Skip tasks that have already been processed in `_review_investigation_results()`
  - Ensure task status persists correctly across FSM transitions
  - Log which tasks are being skipped due to prior processing

- [ ] **TD-003: Fix todo completion tracking**
  - Verify todos are marked COMPLETED exactly once
  - Fix "Todos completed: 9/11" inconsistency (should be 9/9)
  - Ensure new review todos (ID >= 100) are properly tracked
  - Update todo count logic to account for dynamically added todos

### Phase 2: Real Analysis Implementation

- [ ] **TD-004: Pass diff content to subagents**
  - Modify `_build_subagent_prompt()` to include actual diff content
  - Format diff as a readable code block in the prompt
  - Limit diff size to avoid token limits (truncation if needed)
  - Include line number ranges for changed files

- [ ] **TD-005: Implement real secret scanning**
  - Replace mock data in `_simulate_subagent_execution()` with actual analysis
  - Use regex patterns for AWS keys, API keys, passwords, tokens
  - Scan only added/modified lines from diff
  - Match findings to actual file paths and line numbers from diff

- [ ] **TD-006: Implement real injection scanning**
  - Analyze diff for SQL injection patterns (f-strings with user input)
  - Detect XSS vulnerabilities (user input in HTML templates)
  - Identify command injection (user input in system/shell calls)
  - Map findings to actual changed lines in the diff

- [ ] **TD-007: Implement real unsafe function scanning**
  - Scan diff for `eval()`, `exec()`, `system()`, `shell_exec`
  - Check if user input flows into these functions
  - Identify dangerous imports (`pickle`, `subprocess`, `os.system`)
  - Report only if unsafe functions are in changed code

- [ ] **TD-008: Implement real crypto scanning**
  - Detect weak hash functions (MD5, SHA1) in diff
  - Identify hardcoded encryption keys
  - Check for insecure random number generation
  - Verify TLS/SSL configuration in changed code

### Phase 3: Validation and Quality

- [ ] **TD-009: Validate findings against changed files**
  - Cross-reference all finding file paths with `self.context.changed_files`
  - Filter out findings for unchanged files
  - Log warnings when findings reference files outside the PR
  - Include only valid findings in final assessment

- [ ] **TD-010: Ensure all findings have valid evidence**
  - Validate evidence field is non-empty string
  - Verify evidence matches diff content
  - Include surrounding code context (±2 lines) for better readability
  - Reject findings with missing or invalid evidence

- [ ] **TD-011: Add finding uniqueness validation**
  - Generate unique IDs for each finding (UUID or hash-based)
  - Prevent duplicate finding IDs across different subagents
  - Merge findings with same file/line/severity if they describe the same issue
  - Add deduplication based on content hash

### Phase 4: Testing and Documentation

- [ ] **TD-012: Write unit tests for deduplication logic**
  - Test multiple iterations don't duplicate findings
  - Test new findings are added correctly
  - Test mixed new/duplicate scenarios
  - Test finding ID tracking edge cases

- [ ] **TD-013: Write integration tests for real analysis**
  - Create test PR with known security issues
  - Verify subagents detect real issues from diff
  - Verify no false positives on clean diffs
  - Test with various diff sizes and file counts

- [ ] **TD-014: Add logging for debugging**
  - Log when findings are skipped due to deduplication
  - Log when tasks are skipped due to prior processing
  - Log diff size and changed files in each subagent call
  - Include finding IDs in all relevant log messages

- [ ] **TD-015: Update documentation**
  - Document the deduplication mechanism
  - Explain how real analysis works vs mock mode
  - Add examples of expected findings format
  - Document diff context handling in subagents

### Phase 5: Performance and Scalability

- [ ] **TD-016: Optimize diff handling for large PRs**
  - Implement diff chunking for very large changes
  - Add progress reporting for subagent analysis
  - Cache diff parsing results across subagents
  - Set reasonable limits on diff size per subagent

- [ ] **TD-017: Add parallel subagent execution**
  - Execute independent subagents concurrently instead of sequentially
  - Manage parallel execution limits
  - Aggregate results safely from concurrent tasks
  - Maintain proper state with concurrent updates

- [ ] **TD-018: Add finding confidence scores**
  - Allow subagents to report confidence levels
  - Filter low-confidence findings in final report
  - Include confidence in finding metadata
  - Enable confidence threshold configuration

---

## Priority Matrix

| ID | Priority | Phase | Complexity | Impact |
|----|----------|-------|------------|--------|
| TD-001 | P0 | 1 | Low | Critical |
| TD-002 | P0 | 1 | Low | Critical |
| TD-003 | P0 | 1 | Low | High |
| TD-004 | P1 | 2 | Medium | Critical |
| TD-005 | P1 | 2 | Medium | Critical |
| TD-006 | P1 | 2 | Medium | Critical |
| TD-007 | P1 | 2 | Medium | High |
| TD-008 | P1 | 2 | Medium | High |
| TD-009 | P2 | 3 | Low | High |
| TD-010 | P2 | 3 | Low | High |
| TD-011 | P2 | 3 | Medium | High |
| TD-012 | P3 | 4 | Medium | Medium |
| TD-013 | P3 | 4 | High | Medium |
| TD-014 | P3 | 4 | Low | Medium |
| TD-015 | P3 | 4 | Low | Low |
| TD-016 | P4 | 5 | High | Medium |
| TD-017 | P4 | 5 | High | Medium |
| TD-018 | P4 | 5 | Medium | Low |

## Success Metrics

- **Accuracy**: 100% of findings reference changed files
- **No Duplicates**: 0 duplicate findings in final report
- **Evidence Quality**: 100% of findings include valid code snippets from diff
- **Coverage**: All changed files scanned for security issues
- **Performance**: Review completes within 5 minutes for 100-file PRs
- **False Positive Rate**: < 5% false positives on clean diffs
