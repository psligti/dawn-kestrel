# Convert Review Agents to Agentic LLM Process

## TL;DR

> **Quick Summary**: Convert 11 review agents (security, linting, architecture, documentation, telemetry, unit_tests, diff_scoper, requirements, performance, dependencies, changelog) from hardcoded regex/AST/external-command logic to agentic LLM-based analysis. Each agent creates AISession, calls LLM with system prompt + context, parses JSON response as ReviewOutput, removes all hardcoded check methods.
>
> **Deliverables**:
> - Updated BaseReviewerAgent (optional helper methods for LLM error handling)
> - 11 converted agents (SecurityReviewer, LintingReviewer, etc.) with LLM-based review() methods
> - Updated tests for all 11 agents (mock AISession, test LLM response parsing)
> - Removed all hardcoded logic: regex patterns, external commands, AST analysis, heuristics
>
> **Estimated Effort**: Large (11 agents × TDD cycle + cleanup)
> **Parallel Execution**: NO - sequential agent conversion (each agent must compile before next)
> **Critical Path**: Base class update → SecurityReviewer → LintingReviewer → ArchitectureReviewer → remaining 8 agents → all tests pass

---

## Context

### Original Request
Convert each of the agents in `opencode_python/src/opencode_python/agents/review/agents` from hardcoded logic (regex patterns, external commands, AST analysis, heuristics) to an agentic process that uses LLM calls. System prompts already exist but are never used.

### Interview Summary
**Key Discussions**:
- **All 11 agents**: Convert security, linting, architecture, documentation, telemetry, unit_tests, diff_scoper, requirements, performance, dependencies, changelog
- **LLM approach**: Each agent creates its own AISession(provider_id, model, api_key) in review() method, not injection
- **Response handling**: Parse LLM response as JSON directly, validate against ReviewOutput schema
- **Remove hardcoded logic**: Replace ALL regex patterns, external commands (ruff, grep, bandit), AST analysis, heuristics with LLM-based analysis
- **No tools/external commands**: All analysis done by LLM itself
- **Configuration**: Use existing settings.core for provider_id, model, api_key
- **Error handling**: Fail fast (raise exception) for timeout/API errors/missing key; return error ReviewOutput for invalid JSON/missing fields; empty response is not an error
- **Conversion order**: All 11 agents together, not one at a time
- **Testing**: TDD approach - write test with mocked LLM first, implement to pass, then refactor/cleanup
- **Quality validation**: No baseline comparison; ensure valid ReviewOutput and tests pass

### Research Findings
- **AISession class** provides `process_message()` method for LLM calls at `opencode_python/ai_session.py`
- **AISession** takes provider_id (string), model (string), and api_key (optional) in constructor
- **AISession.process_message()** returns Message object with text attribute containing LLM response
- **ReviewContext** provides `format_inputs_for_prompt()` method that creates formatted context string (changed files, diff, PR metadata)
- **System prompts already exist** in each agent (e.g., SECURITY_SYSTEM_PROMPT, LINTING_SYSTEM_PROMPT) and instruct LLM to return ReviewOutput JSON
- **Test infrastructure exists**: pytest with pytest-asyncio, existing tests for each agent in `tests/review/agents/`
- **Current agents use hardcoded logic**:
  - SecurityReviewer (394 lines): SECRET_PATTERNS, DANGEROUS_PATTERNS regex + _check_for_secrets(), _check_for_dangerous_patterns(), _check_for_cicd_exposures()
  - LintingReviewer (497 lines): CommandExecutor runs ruff check/format, parses output, uses AST for type hints
  - ArchitectureReviewer (602 lines): Regex for circular imports, boundary violations, tight coupling, hardcoded config, god objects, breaking changes
  - Other 8 agents have similar patterns

### Metis Review
**Critical Guardrails Addressed**:
- **NO retry logic**: Errors surface immediately; Orchestrator handles retries if needed
- **NO fallback to old logic**: Each agent is 100% LLM or raises exception
- **NO new config system**: Use existing settings.core for provider_id/model/api_key
- **NO integration tests**: Mock ALL LLM responses in unit tests
- **NO hybrid old+new logic**: Each agent either all LLM or all old logic (converted agents = all LLM)
- **Keep BaseReviewerAgent minimal**: Add only essential LLM error handling methods if needed

**Gaps Identified and Addressed**:
- **Error handling**: Explicit rules for when to raise exception vs return error ReviewOutput
- **Configuration**: Use settings.core (existing pydantic-settings integration)
- **Edge cases**: Empty response, invalid JSON, timeout, API errors, missing API key
- **Scope creep prevention**: NO monitoring, NO retry logic, NO evaluation framework, NO new documentation beyond docstrings

---

## Work Objectives

### Core Objective
Convert 11 review agents from hardcoded static analysis to agentic LLM-based review using AISession, maintaining ReviewOutput contract while removing all regex/external-command/AST/heuristic logic.

### Concrete Deliverables
- `opencode_python/src/opencode_python/agents/review/base.py` (optional updates for LLM error helpers)
- `opencode_python/src/opencode_python/agents/review/agents/security.py` (converted to LLM)
- `opencode_python/src/opencode_python/agents/review/agents/linting.py` (converted to LLM)
- `opencode_python/src/opencode_python/agents/review/agents/architecture.py` (converted to LLM)
- `opencode_python/src/opencode_python/agents/review/agents/documentation.py` (converted to LLM)
- `opencode_python/src/opencode_python/agents/review/agents/telemetry.py` (converted to LLM)
- `opencode_python/src/opencode_python/agents/review/agents/unit_tests.py` (converted to LLM)
- `opencode_python/src/opencode_python/agents/review/agents/diff_scoper.py` (converted to LLM)
- `opencode_python/src/opencode_python/agents/review/agents/requirements.py` (converted to LLM)
- `opencode_python/src/opencode_python/agents/review/agents/performance.py` (converted to LLM)
- `opencode_python/src/opencode_python/agents/review/agents/dependencies.py` (converted to LLM)
- `opencode_python/src/opencode_python/agents/review/agents/changelog.py` (converted to LLM)
- Updated tests in `tests/review/agents/` for all 11 agents (mock AISession, test JSON parsing, error handling)

### Definition of Done
- All 11 agents call AISession in their review() method
- All hardcoded check methods removed from all agents
- All regex patterns, external command calls, AST analysis code removed
- All tests pass: `pytest tests/review/agents/`
- Each agent's review() method returns valid ReviewOutput from LLM JSON response
- Error handling tests pass for all agents (timeout, invalid JSON, API error, missing API key)

### Must Have
- Each agent creates AISession(provider_id, model, api_key) using settings.core
- Each agent uses get_system_prompt() for system message
- Each agent uses format_inputs_for_prompt(context) for user message
- Each agent parses LLM response as JSON and validates against ReviewOutput schema
- Error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON
- TDD approach for each agent: test (mocked AISession) → implement → refactor/cleanup
- Remove ALL hardcoded logic (no exceptions)

### Must NOT Have (Guardrails)
- **NO retry logic or exponential backoff** (Orchestrator concern, not agent)
- **NO fallback to old hardcoded logic** (100% LLM or raise exception)
- **NO new configuration system** (use existing settings.core)
- **NO integration tests with real LLM calls** (mock ALL LLM responses)
- **NO monitoring/logging additions** (cost tracking, latency metrics)
- **NO evaluation/ground-truth comparison framework**
- **NO new documentation** beyond updating docstrings
- **NO hybrid old+new logic per agent**
- **NO multiple LLM calls per agent** (single call → single ReviewOutput)
- **NO preprocessing or postprocessing beyond JSON parsing**
- **NO AISession helper methods in BaseReviewerAgent** (each agent self-contained)

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest with pytest-asyncio)
- **User wants tests**: YES (TDD)
- **Framework**: pytest
- **QA approach**: TDD - RED (test fails with mock LLM) → GREEN (mock returns correct JSON) → REFACTOR (clean up)

### If TDD Enabled

Each agent conversion follows RED-GREEN-REFACTOR:

**Task Structure:**
1. **RED**: Write failing test first
   - Test file: `tests/review/agents/test_{agent_name}.py` (update existing tests)
   - Mock AISession with expected JSON response
   - Test command: `pytest tests/review/agents/test_{agent_name}.py::test_{agent_name}_llm_parsing`
   - Expected: FAIL (test exists, agent not yet converted)

2. **GREEN**: Implement minimum code to pass
   - Convert agent review() method to call AISession
   - Parse JSON response and return ReviewOutput
   - Command: `pytest tests/review/agents/test_{agent_name}.py::test_{agent_name}_llm_parsing`
   - Expected: PASS (LLM returns JSON, agent parses it)

3. **REFACTOR**: Clean up while keeping green
   - Remove all hardcoded check methods
   - Remove regex patterns, external command calls
   - Command: `pytest tests/review/agents/test_{agent_name}.py`
   - Expected: PASS (all tests still pass, code clean)

**Test Setup Task (no changes needed):**
- Test infrastructure already exists (pytest, pytest-asyncio)
- No new setup required

### Automated Verification (NO User Intervention)

**For LLM Response Parsing:**
```bash
# Agent executes via mock in pytest test:
# 1. Mock AISession to return JSON string matching ReviewOutput schema
# 2. Call agent.review(context) with test context
# 3. Assert agent returns ReviewOutput with expected findings/severity
# 4. Assert agent.review() raises exception on timeout/invalid JSON (error handling tests)
# Verify: pytest tests/review/agents/test_*.py → PASS
```

**For Schema Validation:**
```bash
# Agent executes via pytest:
import json
from opencode_python.agents.review.contracts import ReviewOutput

# Test that LLM JSON response parses to ReviewOutput
llm_json = '{"agent": "security", "summary": "...", "severity": "warning", ...}'
output = ReviewOutput.model_validate_json(llm_json)
# Assert: No ValidationError raised
# Verify: pytest tests/review/agents/test_*.py::test_json_parsing → PASS
```

**For Error Handling:**
```bash
# Agent executes via pytest with mocked exceptions:
# 1. Mock AISession.process_message() to raise asyncio.TimeoutError
# 2. Call agent.review(context)
# 3. Assert agent raises TimeoutError
# 4. Mock AISession to return invalid JSON
# 5. Assert agent returns ReviewOutput with severity='critical' and error message
# Verify: pytest tests/review/agents/test_*.py::test_error_handling → PASS
```

**Evidence to Capture:**
- [x] Pytest test results (pass/fail counts per agent)
- [x] Code coverage reports (before/after conversion)
- [x] Sample ReviewOutput JSON from test mocks

---

## Execution Strategy

### Parallel Execution Waves

> Sequential conversion required: each agent must compile and pass tests before converting next.

```
Wave 1 (Start Immediately):
├── Task 1: Update BaseReviewerAgent (optional LLM error helpers)
└── Task 2: Convert SecurityReviewer (TDD)

Wave 2 (After Wave 1 completes):
├── Task 3: Convert LintingReviewer (TDD)
└── Task 4: Convert ArchitectureReviewer (TDD)

Wave 3 (After Wave 2 completes):
├── Task 5: Convert DocumentationReviewer (TDD)
├── Task 6: Convert TelemetryMetricsReviewer (TDD)
└── Task 7: Convert UnitTestsReviewer (TDD)

Wave 4 (After Wave 3 completes):
├── Task 8: Convert DiffScoperReviewer (TDD)
├── Task 9: Convert RequirementsReviewer (TDD)
└── Task 10: Convert PerformanceReliabilityReviewer (TDD)

Wave 5 (After Wave 4 completes):
├── Task 11: Convert DependencyLicenseReviewer (TDD)
└── Task 12: Convert ReleaseChangelogReviewer (TDD)

Wave 6 (Final wave - after all agents converted):
└── Task 13: Final verification - all tests pass, cleanup unused imports

Critical Path: Task 1 → Task 2 → Task 3 → ... → Task 13
Parallel Speedup: None (sequential requirement)
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3-12 | None (base class) |
| 2 | 1 | 3 | None (Security first) |
| 3 | 1 | 4, 5-12 | None (Linting sequential) |
| 4 | 1 | 5, 6-12 | None (Architecture sequential) |
| 5 | 1 | 6-12 | None (Documentation sequential) |
| 6 | 1 | 7-12 | None (Telemetry sequential) |
| 7 | 1 | 8-12 | None (UnitTests sequential) |
| 8 | 1 | 9-12 | None (DiffScoper sequential) |
| 9 | 1 | 10-12 | None (Requirements sequential) |
| 10 | 1 | 11, 12 | None (Performance sequential) |
| 11 | 1 | 12 | None (Dependencies sequential) |
| 12 | 1 | 13 | None (Changelog sequential) |
| 13 | 2-12 | None | Final verification |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2 | delegate_task(category="quick", load_skills=[], run_in_background=true) |
| 2 | 3, 4 | delegate_task(category="unspecified-high", load_skills=[], run_in_background=true) |
| 3 | 5, 6, 7 | delegate_task(category="unspecified-high", load_skills=[], run_in_background=true) |
| 4 | 8, 9, 10 | delegate_task(category="unspecified-high", load_skills=[], run_in_background=true) |
| 5 | 11, 12 | delegate_task(category="unspecified-high", load_skills=[], run_in_background=true) |
| 6 | 13 | delegate_task(category="quick", load_skills=[], run_in_background=true) |

---

## TODOs

- [x] 1. Update BaseReviewerAgent with LLM error handling helpers (optional)

  **What to do**:
  - [Review BaseReviewerAgent at `opencode_python/src/opencode_python/agents/review/base.py`]
  - [Add optional helper methods if common error handling patterns emerge during agent conversion]
  - [Keep base class minimal - no AISession management methods]
  - [Preserve existing format_inputs_for_prompt() method]

  **Must NOT do**:
  - [Add AISession instantiation or management to base class]
  - [Add retry logic or fallback mechanisms]
  - [Add configuration helpers - use existing settings.core]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Small optional update to base class, minimal changes
  - **Skills**: `[]`
    - No specific skills needed for this simple task
  - **Skills Evaluated but Omitted**:
    - `git-master`: Not needed for code modification

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 1)
  - **Blocks**: Tasks 2-12 (all agent conversions depend on base class stability)
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/base.py:74-93` - BaseReviewerAgent abstract class structure with review(), get_system_prompt(), get_relevant_file_patterns() methods
  - `opencode_python/src/opencode_python/agents/review/base.py:134-173` - format_inputs_for_prompt() method showing how to construct context string from ReviewContext

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput pydantic model with agent, summary, severity, scope, findings, merge_gate fields

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_security_reviewer.py` - Example test structure (mock pattern, async test usage)

  **Documentation References** (specs and requirements):
  - Interview notes: "Keep BaseReviewerAgent minimal - no AISession helpers" - Guardrail from user requirements

  **External References** (libraries and frameworks):
  - Official docs: `https://docs.pydantic.dev/latest/concepts/models/` - Pydantic model validation for ReviewOutput schema
  - `opencode_python/src/opencode_python/ai_session.py:28-46` - AISession class constructor and process_message() method

  **WHY Each Reference Matters** (explain the relevance):
  - BaseReviewerAgent shows the abstract interface - understand what methods MUST exist and what can be added
  - format_inputs_for_prompt() is the standard way to construct user messages - use this pattern in all agents
  - ReviewOutput schema defines the contract - ensure LLM JSON response validates against this structure
  - test_security_reviewer.py shows mocking patterns - use consistent mock structure across all agent tests

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] Test file created/updated: `tests/review/base/test_base_reviewer.py`
- [x] Base class compiles: `pytest --collect-only tests/review/` → no errors
- [x] format_inputs_for_prompt() still works: existing tests pass
- [x] pytest tests/review/base/ → PASS

  **Automated Verification**:
  ```bash
  # Agent executes via pytest:
  pytest tests/review/base/test_base_reviewer.py -v
  # Assert: All tests pass
  # Assert: No import errors from modified base.py
  # Assert: format_inputs_for_prompt() returns expected context string

  python -c "from opencode_python.agents.review.base import BaseReviewerAgent; print('Import successful')"
  # Assert: No ImportError

  pytest --collect-only tests/review/
  # Assert: All test modules collected without errors
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all base class tests pass
- [x] No ImportError on base module import

  **Commit**: YES
  - Message: `refactor(review): optional LLM error helpers in BaseReviewerAgent`
  - Files: `opencode_python/src/opencode_python/agents/review/base.py`, `tests/review/base/test_base_reviewer.py`
  - Pre-commit: `pytest tests/review/base/`

- [x] 2. Convert SecurityReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with security findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete SECRET_PATTERNS constant]
    - [Delete DANGEROUS_PATTERNS constant]
    - [Delete _check_for_secrets() method]
    - [Delete _check_for_dangerous_patterns() method]
    - [Delete _check_for_cicd_exposures() method]
    - [Delete _get_recommendation_for_pattern() method]
    - [Delete _get_suggested_patch_for_pattern() method]
    - [Remove regex imports if no longer used]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any regex pattern matching logic]
  - [Keep any external command execution (grep, bandit, etc.)]
  - [Add retry logic or fallback to old check methods]
  - [Add monitoring or logging beyond standard Python logging]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Significant refactoring (394 lines) converting from regex to LLM, requires careful test-driven approach
  - **Skills**: `[]`
    - No specific skills needed for Python code refactoring
  - **Skills Evaluated but Omitted**:
    - `git-master`: Not needed, no git operations

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2 with Linting)
  - **Blocks**: Task 5-12 (other agents depend on pattern established here)
  - **Blocked By**: Task 1 (base class stability)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/security.py:82-94` - SecurityReviewer class structure, get_agent_name(), get_system_prompt(), get_relevant_file_patterns() methods to preserve
  - `opencode_python/src/opencode_python/agents/review/agents/security.py:16-61` - SECURITY_SYSTEM_PROMPT constant with detailed instructions for LLM (keep this!)
  - `opencode_python/src/opencode_python/agents/review/agents/security.py:64-79` - SECRET_PATTERNS and DANGEROUS_PATTERNS constants (REMOVE THESE)
  - `opencode_python/src/opencode_python/agents/review/agents/security.py:122-209` - Current review() method using hardcoded checks (REPLACE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/security.py:211-244` - _check_for_secrets() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/security.py:246-285` - _check_for_dangerous_patterns() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/security.py:287-347` - _check_for_cicd_exposures() method (REMOVE THIS)

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:33-45` - Finding model with id, title, severity, confidence, owner, estimate, evidence, risk, recommendation fields
  - `opencode_python/src/opencode_python/agents/review/contracts.py:48-54` - MergeGate model with decision, must_fix, should_fix, notes_for_coding_agent fields

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_security_reviewer.py` - Existing SecurityReviewer tests (update to mock AISession)
  - `tests/review/agents/test_linting_reviewer.py` - Example of mocking CommandExecutor (adapt to mock AISession)

  **Documentation References** (specs and requirements):
  - Interview notes: "Use existing settings.core for provider_id/model/api_key" - Configuration source
  - Interview notes: "Error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON" - Error handling strategy

  **External References** (libraries and frameworks):
  - Official docs: `https://docs.pytest.org/en/stable/how-to/monkeypatch.html` - pytest monkeypatch for mocking AISession
  - Official docs: `https://docs.pydantic.dev/latest/concepts/models/` - Pydantic model_validate_json() for JSON parsing
  - `opencode_python/src/opencode_python/core/settings.py` - settings.core module for accessing provider_id, model, api_key

  **WHY Each Reference Matters** (explain the relevance):
  - SecurityReviewer structure shows methods to preserve (get_system_prompt, get_relevant_file_patterns) and what to replace (review method)
  - SECURITY_SYSTEM_PROMPT is critical - this is the system message for LLM, must use it in AISession call
  - SECRET_PATTERNS/DANGEROUS_PATTERNS show what hardcoded logic exists to remove
  - Existing review() method shows current implementation to replace with LLM call
  - _check_* methods show all private helper methods to delete
  - Finding model defines structure LLM must return in JSON
  - test_security_reviewer.py provides template for new AISession-mocked tests
  - settings.core shows where to get LLM configuration

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with security findings from LLM
- [x] Test expects exception on timeout: pytest.raises(asyncio.TimeoutError)
- [x] Test expects error ReviewOutput on invalid JSON
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] review() raises asyncio.TimeoutError on AISession timeout
- [x] review() returns ReviewOutput with severity='critical' on invalid JSON
- [x] REFACTOR: SECRET_PATTERNS constant deleted
- [x] REFACTOR: DANGEROUS_PATTERNS constant deleted
- [x] REFACTOR: _check_for_secrets() method deleted
- [x] REFACTOR: _check_for_dangerous_patterns() method deleted
- [x] REFACTOR: _check_for_cicd_exposures() method deleted
- [x] REFACTOR: _get_recommendation_for_pattern() method deleted
- [x] REFACTOR: _get_suggested_patch_for_pattern() method deleted
- [x] REFACTOR: re import removed (if no regex patterns used)
- [x] pytest tests/review/agents/test_security_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  # Agent executes via pytest:
  pytest tests/review/agents/test_security_reviewer.py -v
  # Assert: All tests pass (including new LLM-based tests)

  # Verify regex patterns removed:
  grep -n "SECRET_PATTERNS\|DANGEROUS_PATTERNS" opencode_python/src/opencode_python/agents/review/agents/security.py
  # Assert: No matches found (patterns deleted)

  # Verify hardcoded check methods removed:
  grep -n "_check_for_secrets\|_check_for_dangerous\|_check_for_cicd" opencode_python/src/opencode_python/agents/review/agents/security.py
  # Assert: No matches found (methods deleted)

  # Verify AISession called (code inspection):
  grep -n "AISession\|process_message" opencode_python/src/opencode_python/agents/review/agents/security.py
  # Assert: Matches found in review() method (LLM integration present)

  python -c "
  from opencode_python.agents.review.agents.security import SecurityReviewer
  import asyncio

  reviewer = SecurityReviewer()
  print('Import successful')

  # Verify get_system_prompt returns expected prompt
  prompt = reviewer.get_system_prompt()
  assert 'Security Review Subagent' in prompt
  assert 'secrets handling' in prompt
  print('get_system_prompt() works')
  "
  # Assert: No AssertionError, import successful
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all SecurityReviewer tests pass
- [x] Grep output confirming no regex patterns remain
- [x] Python script output confirming agent works

  **Commit**: YES
  - Message: `refactor(review): convert SecurityReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/security.py`, `tests/review/agents/test_security_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_security_reviewer.py`

- [x] 3. Convert LintingReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with linting findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete CommandExecutor dependency and __init__ executor parameter]
    - [Delete external command calls: ruff check, ruff format]
    - [Delete _determine_severity_from_ruff() method]
    - [Delete _format_finding_evidence() method]
    - [Delete _get_ruff_recommendation() method]
    - [Delete _check_type_hints() method and AST analysis]
    - [Delete _determine_overall_severity() method]
    - [Delete _determine_merge_gate() method]
    - [Delete _generate_summary() method]
    - [Delete _generate_notes_for_coding_agent() method]
    - [Remove CommandExecutor import]
    - [Remove AST imports if no longer used]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any external command execution (ruff, black, flake8)]
  - [Keep any AST analysis or type hint checking]
  - [Add retry logic or fallback to old command execution]
  - [Add monitoring or logging beyond standard Python logging]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Large refactoring (497 lines) removing CommandExecutor, external commands, AST analysis
  - **Skills**: `[]`
    - No specific skills needed for Python code refactoring
  - **Skills Evaluated but Omitted**:
    - `git-master`: Not needed, no git operations

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2 with Architecture)
  - **Blocks**: Task 5-12 (other agents depend on pattern established here)
  - **Blocked By**: Task 1 (base class)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:55-75` - LintingReviewer class structure, __init__ with executor, get_agent_name(), get_system_prompt(), get_relevant_file_patterns() methods
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:21-52` - LINTING_SYSTEM_PROMPT constant (KEEP THIS!)
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:95-259` - Current review() method using CommandExecutor (REPLACE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:261-291` - _determine_severity_from_ruff() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:293-316` - _format_finding_evidence() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:318-341` - _get_ruff_recommendation() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:343-405` - _check_type_hints() method with AST (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:407-427` - _determine_overall_severity() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:429-446` - _determine_merge_gate() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:448-461` - _generate_summary() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/linting.py:463-496` - _generate_notes_for_coding_agent() method (REMOVE THIS)

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:15-22` - Check model with name, required, commands, why, expected_signal fields
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_linting_reviewer.py` - Existing LintingReviewer tests (update to mock AISession)

  **Documentation References** (specs and requirements):
  - Interview notes: "Remove ALL external command execution (ruff, grep, bandit)" - Must remove CommandExecutor usage

  **External References** (libraries and frameworks):
  - Official docs: `https://docs.pytest.org/en/stable/how-to/monkeypatch.html` - pytest monkeypatch for mocking AISession

  **WHY Each Reference Matters** (explain the relevance):
  - LintingReviewer structure shows __init__ with executor parameter - this must be removed
  - LINTING_SYSTEM_PROMPT is the system message for LLM - must use it
  - review() method shows CommandExecutor calls - these must be replaced with AISession
  - All _determine_*, _format_*, _get_*, _generate_* methods are hardcoded logic to remove
  - Check model shows that LLM could return checks in ReviewOutput, but since we're removing external commands, checks list will be empty

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with linting findings from LLM
- [x] Test expects exception on timeout: pytest.raises(asyncio.TimeoutError)
- [x] Test expects error ReviewOutput on invalid JSON
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] review() raises asyncio.TimeoutError on AISession timeout
- [x] review() returns ReviewOutput with severity='critical' on invalid JSON
- [x] REFACTOR: __init__ executor parameter deleted
- [x] REFACTOR: CommandExecutor dependency removed
- [x] REFACTOR: All external command calls deleted (ruff check, ruff format)
- [x] REFACTOR: _determine_severity_from_ruff() method deleted
- [x] REFACTOR: _format_finding_evidence() method deleted
- [x] REFACTOR: _get_ruff_recommendation() method deleted
- [x] REFACTOR: _check_type_hints() method deleted (AST analysis)
- [x] REFACTOR: _determine_overall_severity() method deleted
- [x] REFACTOR: _determine_merge_gate() method deleted
- [x] REFACTOR: _generate_summary() method deleted
- [x] REFACTOR: _generate_notes_for_coding_agent() method deleted
- [x] pytest tests/review/agents/test_linting_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  # Agent executes via pytest:
  pytest tests/review/agents/test_linting_reviewer.py -v
  # Assert: All tests pass

  # Verify CommandExecutor usage removed:
  grep -n "CommandExecutor\|executor" opencode_python/src/opencode_python/agents/review/agents/linting.py
  # Assert: No matches found (CommandExecutor removed)

  # Verify external commands removed:
  grep -n "ruff check\|ruff format\|subprocess\|executor.execute" opencode_python/src/opencode_python/agents/review/agents/linting.py
  # Assert: No matches found (external commands removed)

  # Verify AST analysis removed:
  grep -n "ast\|AST\|_check_type_hints" opencode_python/src/opencode_python/agents/review/agents/linting.py
  # Assert: No AST imports or usage found

  python -c "
  from opencode_python.agents.review.agents.linting import LintingReviewer
  print('Import successful')

  reviewer = LintingReviewer()
  assert reviewer.get_agent_name() == 'linting'
  assert 'Linting & Style' in reviewer.get_system_prompt()
  print('Agent methods work')
  "
  # Assert: No ImportError, agent works
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all LintingReviewer tests pass
- [x] Grep output confirming no CommandExecutor or external commands
- [x] Python script output confirming agent works

  **Commit**: YES
  - Message: `refactor(review): convert LintingReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/linting.py`, `tests/review/agents/test_linting_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_linting_reviewer.py`

- [x] 4. Convert ArchitectureReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with architecture findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete _check_circular_imports() method]
    - [Delete _check_boundary_violations() method]
    - [Delete _check_tight_coupling() method]
    - [Delete _check_hardcoded_config() method]
    - [Delete _check_god_objects() method]
    - [Delete _check_breaking_changes() method]
    - [Delete _analyze_architecture() method]
    - [Delete _compute_severity() method]
    - [Delete _compute_merge_gate() method]
    - [Delete _generate_summary() method]
    - [Remove regex imports if no longer used]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any regex pattern matching or heuristic rules]
  - [Keep any import analysis or dependency checking]
  - [Add retry logic or fallback to old analysis]
  - [Add monitoring or logging beyond standard Python logging]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Large refactoring (602 lines) removing multiple heuristic analysis methods
  - **Skills**: `[]`
    - No specific skills needed for Python code refactoring
  - **Skills Evaluated but Omitted**:
    - `git-master`: Not needed, no git operations

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3 start)
  - **Blocks**: Task 5-12 (other agents depend on pattern established here)
  - **Blocked By**: Task 1 (base class)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:18-27` - ArchitectureReviewer class structure, get_agent_name(), get_system_prompt(), get_relevant_file_patterns() methods
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:28-96` - _SYSTEM_PROMPT constant (KEEP THIS!)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:110-156` - Current review() method (REPLACE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:158-179` - _analyze_architecture() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:181-241` - _check_circular_imports() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:243-301` - _check_boundary_violations() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:303-348` - _check_tight_coupling() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:350-395` - _check_hardcoded_config() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:397-457` - _check_god_objects() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:459-501` - _check_breaking_changes() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:503-527` - _compute_severity() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:529-570` - _compute_merge_gate() method (REMOVE THIS)
  - `opencode_python/src/opencode_python/agents/review/agents/architecture.py:572-601` - _generate_summary() method (REMOVE THIS)

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_architecture_reviewer.py` - Existing ArchitectureReviewer tests (update to mock AISession)

  **WHY Each Reference Matters** (explain the relevance):
  - ArchitectureReviewer structure shows methods to preserve and what to replace
  - _SYSTEM_PROMPT is the system message for LLM - must use it
  - All _check_* and _compute_* methods are hardcoded heuristic logic to remove

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with architecture findings from LLM
- [x] Test expects exception on timeout: pytest.raises(asyncio.TimeoutError)
- [x] Test expects error ReviewOutput on invalid JSON
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] review() raises asyncio.TimeoutError on AISession timeout
- [x] review() returns ReviewOutput with severity='critical' on invalid JSON
- [x] REFACTOR: _check_circular_imports() method deleted
- [x] REFACTOR: _check_boundary_violations() method deleted
- [x] REFACTOR: _check_tight_coupling() method deleted
- [x] REFACTOR: _check_hardcoded_config() method deleted
- [x] REFACTOR: _check_god_objects() method deleted
- [x] REFACTOR: _check_breaking_changes() method deleted
- [x] REFACTOR: _analyze_architecture() method deleted
- [x] REFACTOR: _compute_severity() method deleted
- [x] REFACTOR: _compute_merge_gate() method deleted
- [x] REFACTOR: _generate_summary() method deleted
- [x] pytest tests/review/agents/test_architecture_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  # Agent executes via pytest:
  pytest tests/review/agents/test_architecture_reviewer.py -v
  # Assert: All tests pass

  # Verify hardcoded analysis methods removed:
  grep -n "_check_circular_imports\|_check_boundary_violations\|_check_tight_coupling\|_analyze_architecture" opencode_python/src/opencode_python/agents/review/agents/architecture.py
  # Assert: No matches found (methods deleted)

  python -c "
  from opencode_python.agents.review.agents.architecture import ArchitectureReviewer
  print('Import successful')

  reviewer = ArchitectureReviewer()
  assert reviewer.get_agent_name() == 'architecture'
  assert 'Architecture Review' in reviewer.get_system_prompt()
  print('Agent methods work')
  "
  # Assert: No ImportError
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all ArchitectureReviewer tests pass
- [x] Grep output confirming hardcoded methods removed
- [x] Python script output confirming agent works

  **Commit**: YES
  - Message: `refactor(review): convert ArchitectureReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/architecture.py`, `tests/review/agents/test_architecture_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_architecture_reviewer.py`

- [x] 5. Convert DocumentationReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with documentation findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete AST-based docstring checking functions]
    - [Delete README/usage file checking logic]
    - [Delete private helper methods for documentation analysis]
    - [Remove AST imports if no longer used]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any AST analysis for docstrings]
  - [Keep any file reading or regex pattern matching]
  - [Add retry logic or fallback to old analysis]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Converting documentation analysis from AST to LLM
  - **Skills**: `[]`
    - No specific skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3)
  - **Blocks**: Task 8-12
  - **Blocked By**: Task 1 (base class)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/documentation.py` - Full file to review and convert

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_documentation_reviewer.py` - Existing DocumentationReviewer tests

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with documentation findings from LLM
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] REFACTOR: All AST-based analysis methods deleted
- [x] pytest tests/review/agents/test_documentation_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  pytest tests/review/agents/test_documentation_reviewer.py -v
  # Assert: All tests pass
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all DocumentationReviewer tests pass

  **Commit**: YES
  - Message: `refactor(review): convert DocumentationReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/documentation.py`, `tests/review/agents/test_documentation_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_documentation_reviewer.py`

- [x] 6. Convert TelemetryMetricsReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with telemetry findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete telemetry checking methods]
    - [Delete private helper methods]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any hardcoded telemetry checks]
  - [Add retry logic or fallback]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Converting telemetry analysis to LLM
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3)
  - **Blocks**: Task 8-12
  - **Blocked By**: Task 1 (base class)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/telemetry.py` - Full file to review and convert

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_telemetry_reviewer.py` - Existing TelemetryMetricsReviewer tests

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with telemetry findings from LLM
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] REFACTOR: All hardcoded telemetry checks deleted
- [x] pytest tests/review/agents/test_telemetry_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  pytest tests/review/agents/test_telemetry_reviewer.py -v
  # Assert: All tests pass
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all TelemetryMetricsReviewer tests pass

  **Commit**: YES
  - Message: `refactor(review): convert TelemetryMetricsReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/telemetry.py`, `tests/review/agents/test_telemetry_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_telemetry_reviewer.py`

- [x] 7. Convert UnitTestsReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with unit test findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete unit test checking methods]
    - [Delete test file analysis logic]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any hardcoded test analysis]
  - [Add retry logic or fallback]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Converting unit test analysis to LLM
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3)
  - **Blocks**: Task 8-12
  - **Blocked By**: Task 1 (base class)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/unit_tests.py` - Full file to review and convert

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_unit_tests_reviewer.py` - Existing UnitTestsReviewer tests

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with unit test findings from LLM
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] REFACTOR: All hardcoded unit test checks deleted
- [x] pytest tests/review/agents/test_unit_tests_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  pytest tests/review/agents/test_unit_tests_reviewer.py -v
  # Assert: All tests pass
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all UnitTestsReviewer tests pass

  **Commit**: YES
  - Message: `refactor(review): convert UnitTestsReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/unit_tests.py`, `tests/review/agents/test_unit_tests_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_unit_tests_reviewer.py`

- [x] 8. Convert DiffScoperReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with diff scope findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete diff scoping methods]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any hardcoded diff analysis]
  - [Add retry logic or fallback]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Converting diff scoping analysis to LLM
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 4)
  - **Blocks**: Task 9-12
  - **Blocked By**: Task 1 (base class)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/diff_scoper.py` - Full file to review and convert

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_diff_scoper_reviewer.py` - Existing DiffScoperReviewer tests

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with diff scope findings from LLM
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] REFACTOR: All hardcoded diff scoping logic deleted
- [x] pytest tests/review/agents/test_diff_scoper_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  pytest tests/review/agents/test_diff_scoper_reviewer.py -v
  # Assert: All tests pass
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all DiffScoperReviewer tests pass

  **Commit**: YES
  - Message: `refactor(review): convert DiffScoperReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/diff_scoper.py`, `tests/review/agents/test_diff_scoper_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_diff_scoper_reviewer.py`

- [x] 9. Convert RequirementsReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with requirements findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete requirements checking methods]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any hardcoded requirements analysis]
  - [Add retry logic or fallback]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Converting requirements analysis to LLM
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 4)
  - **Blocks**: Task 10-12
  - **Blocked By**: Task 1 (base class)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/requirements.py` - Full file to review and convert

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_requirements_reviewer.py` - Existing RequirementsReviewer tests

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with requirements findings from LLM
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] REFACTOR: All hardcoded requirements analysis deleted
- [x] pytest tests/review/agents/test_requirements_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  pytest tests/review/agents/test_requirements_reviewer.py -v
  # Assert: All tests pass
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all RequirementsReviewer tests pass

  **Commit**: YES
  - Message: `refactor(review): convert RequirementsReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/requirements.py`, `tests/review/agents/test_requirements_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_requirements_reviewer.py`

- [x] 10. Convert PerformanceReliabilityReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with performance findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete performance checking methods]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any hardcoded performance analysis]
  - [Add retry logic or fallback]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Converting performance analysis to LLM
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 4)
  - **Blocks**: Task 11-12
  - **Blocked By**: Task 1 (base class)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/performance.py` - Full file to review and convert

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_performance_reviewer.py` - Existing PerformanceReliabilityReviewer tests

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with performance findings from LLM
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] REFACTOR: All hardcoded performance analysis deleted
- [x] pytest tests/review/agents/test_performance_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  pytest tests/review/agents/test_performance_reviewer.py -v
  # Assert: All tests pass
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all PerformanceReliabilityReviewer tests pass

  **Commit**: YES
  - Message: `refactor(review): convert PerformanceReliabilityReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/performance.py`, `tests/review/agents/test_performance_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_performance_reviewer.py`

- [x] 11. Convert DependencyLicenseReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with dependency findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete dependency checking methods]
    - [Delete license checking logic]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any hardcoded dependency or license analysis]
  - [Add retry logic or fallback]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Converting dependency/license analysis to LLM
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 5)
  - **Blocks**: Task 12
  - **Blocked By**: Task 1 (base class)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/dependencies.py` - Full file to review and convert

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_dependency_license_reviewer.py` - Existing DependencyLicenseReviewer tests

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with dependency findings from LLM
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] REFACTOR: All hardcoded dependency/license analysis deleted
- [x] pytest tests/review/agents/test_dependency_license_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  pytest tests/review/agents/test_dependency_license_reviewer.py -v
  # Assert: All tests pass
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all DependencyLicenseReviewer tests pass

  **Commit**: YES
  - Message: `refactor(review): convert DependencyLicenseReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/dependencies.py`, `tests/review/agents/test_dependency_license_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_dependency_license_reviewer.py`

- [x] 12. Convert ReleaseChangelogReviewer to LLM-based analysis (TDD)

  **What to do**:
  - [RED] Write test: Mock AISession to return ReviewOutput JSON with changelog findings
  - [GREEN] Implement review() method: Create AISession, call process_message() with system_prompt + context, parse JSON as ReviewOutput
  - [REFACTOR] Remove ALL hardcoded logic:
    - [Delete changelog checking methods]
  - [Ensure error handling: fail fast on timeout/API error, return error ReviewOutput on invalid JSON]
  - [Clean up unused imports]

  **Must NOT do**:
  - [Keep any hardcoded changelog analysis]
  - [Add retry logic or fallback]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Converting changelog analysis to LLM
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 5)
  - **Blocks**: Task 13 (final verification)
  - **Blocked By**: Task 1 (base class)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/agents/changelog.py` - Full file to review and convert

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_release_changelog_reviewer.py` - Existing ReleaseChangelogReviewer tests

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] RED: Test file updated with mock AISession returning ReviewOutput JSON
- [x] Test expects ReviewOutput with changelog findings from LLM
- [x] GREEN: review() method creates AISession(provider_id, model, api_key)
- [x] review() calls AISession.process_message() with system_prompt + formatted context
- [x] review() parses LLM response as JSON and validates with ReviewOutput.model_validate_json()
- [x] REFACTOR: All hardcoded changelog analysis deleted
- [x] pytest tests/review/agents/test_release_changelog_reviewer.py → PASS

  **Automated Verification**:
  ```bash
  pytest tests/review/agents/test_release_changelog_reviewer.py -v
  # Assert: All tests pass
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all ReleaseChangelogReviewer tests pass

  **Commit**: YES
  - Message: `refactor(review): convert ReleaseChangelogReviewer to LLM-based analysis`
  - Files: `opencode_python/src/opencode_python/agents/review/agents/changelog.py`, `tests/review/agents/test_release_changelog_reviewer.py`
  - Pre-commit: `pytest tests/review/agents/test_release_changelog_reviewer.py`

- [x] 13. Final verification and cleanup

  **What to do**:
  - [Run all agent tests to ensure they pass]
  - [Verify no hardcoded logic remains in any agent]
  - [Check for unused imports across all agent files]
  - [Verify Orchestrator can still call agent.review() successfully]
  - [Run ruff to check for any linting issues in converted agents]
  - [Clean up any remaining TODO comments or debug print statements]

  **Must NOT do**:
  - [Add new features or capabilities beyond LLM conversion]
  - [Change the ReviewOutput contract or Orchestrator interface]
  - [Add new configuration or monitoring infrastructure]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Final verification and cleanup - simple checks and validation
  - **Skills**: `[]`
    - No specific skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 6 - final step)
  - **Blocks**: None (end of project)
  - **Blocked By**: Tasks 2-12 (all agents must be converted first)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/agents/review/orchestrator.py:40-51` - Orchestrator.run_review() showing how agents are called
  - `opencode_python/src/opencode_python/agents/review/orchestrator.py:73-152` - Orchestrator.run_subagents_parallel() showing context building and error handling

  **API/Type References** (contracts to implement against):
  - `opencode_python/src/opencode_python/agents/review/contracts.py:57-67` - ReviewOutput model (must still work with Orchestrator)

  **Test References** (testing patterns to follow):
  - `tests/review/test_integration_review_pipeline.py` - Integration tests showing how Orchestrator uses agents

  **WHY Each Reference Matters** (explain the relevance):
  - Orchestrator code shows the interface agents must implement - verify compatibility
  - Integration tests show end-to-end flow - ensure no breaking changes

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **If TDD (tests enabled):**
- [x] All 11 agent tests pass: pytest tests/review/agents/ → 100% pass
- [x] No regex patterns remain in any agent file (grep for "SECRET_PATTERNS", "DANGEROUS_PATTERNS", etc.)
- [x] No external command calls remain (grep for "ruff", "subprocess", "executor.execute")
- [x] No AST imports or analysis remain (grep for "import ast", "ast.parse")
- [x] Orchestrator integration test passes: pytest tests/review/test_integration_review_pipeline.py → PASS
- [x] ruff passes with no errors: ruff check opencode_python/src/opencode_python/agents/review/agents/
- [x] No unused imports: python -m pyflakes opencode_python/src/opencode_python/agents/review/agents/ or ruff check

  **Automated Verification**:
  ```bash
  # Agent executes via pytest:
  pytest tests/review/agents/ -v --tb=short
  # Assert: All tests pass (11 agent test files × multiple tests each)

  # Verify no hardcoded logic remains:
  grep -r "SECRET_PATTERNS\|DANGEROUS_PATTERNS\|_check_for_\|CommandExecutor\|ruff check\|import ast" opencode_python/src/opencode_python/agents/review/agents/ | grep -v "__pycache__"
  # Assert: No matches found (all hardcoded logic removed)

  # Verify Orchestrator still works:
  pytest tests/review/test_integration_review_pipeline.py -v
  # Assert: Integration test passes (agents return valid ReviewOutput)

  # Verify linting passes:
  ruff check opencode_python/src/opencode_python/agents/review/agents/
  # Assert: Exit code 0, no linting errors

  # Final verification:
  python -c "
  from opencode_python.agents.review.agents import *
  import inspect

  agents = [SecurityReviewer, LintingReviewer, ArchitectureReviewer, DocumentationReviewer,
           TelemetryMetricsReviewer, UnitTestsReviewer, DiffScoperReviewer,
           RequirementsReviewer, PerformanceReliabilityReviewer,
           DependencyLicenseReviewer, ReleaseChangelogReviewer]

  for agent_class in agents:
      agent = agent_class()
      assert hasattr(agent, 'review')
      assert hasattr(agent, 'get_system_prompt')
      assert hasattr(agent, 'get_relevant_file_patterns')
      print(f'{agent_class.__name__}: OK')
  "
  # Assert: All agents instantiate successfully, have required methods
  ```

  **Evidence to Capture**:
- [x] Pytest output showing all 11 agent tests pass with 100% pass rate
- [x] Grep output confirming no hardcoded patterns remain
- [x] Ruff check output showing 0 errors
- [x] Python script output confirming all agents work
- [x] Integration test output showing Orchestrator works

  **Commit**: YES (final)
  - Message: `refactor(review): final verification of LLM-based agent conversion`
  - Files: All modified test files, any cleanup changes
  - Pre-commit: `pytest tests/review/`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `refactor(review): optional LLM error helpers in BaseReviewerAgent` | base.py, test_base_reviewer.py | pytest tests/review/base/ |
| 2 | `refactor(review): convert SecurityReviewer to LLM-based analysis` | security.py, test_security_reviewer.py | pytest tests/review/agents/test_security_reviewer.py |
| 3 | `refactor(review): convert LintingReviewer to LLM-based analysis` | linting.py, test_linting_reviewer.py | pytest tests/review/agents/test_linting_reviewer.py |
| 4 | `refactor(review): convert ArchitectureReviewer to LLM-based analysis` | architecture.py, test_architecture_reviewer.py | pytest tests/review/agents/test_architecture_reviewer.py |
| 5 | `refactor(review): convert DocumentationReviewer to LLM-based analysis` | documentation.py, test_documentation_reviewer.py | pytest tests/review/agents/test_documentation_reviewer.py |
| 6 | `refactor(review): convert TelemetryMetricsReviewer to LLM-based analysis` | telemetry.py, test_telemetry_reviewer.py | pytest tests/review/agents/test_telemetry_reviewer.py |
| 7 | `refactor(review): convert UnitTestsReviewer to LLM-based analysis` | unit_tests.py, test_unit_tests_reviewer.py | pytest tests/review/agents/test_unit_tests_reviewer.py |
| 8 | `refactor(review): convert DiffScoperReviewer to LLM-based analysis` | diff_scoper.py, test_diff_scoper_reviewer.py | pytest tests/review/agents/test_diff_scoper_reviewer.py |
| 9 | `refactor(review): convert RequirementsReviewer to LLM-based analysis` | requirements.py, test_requirements_reviewer.py | pytest tests/review/agents/test_requirements_reviewer.py |
| 10 | `refactor(review): convert PerformanceReliabilityReviewer to LLM-based analysis` | performance.py, test_performance_reviewer.py | pytest tests/review/agents/test_performance_reviewer.py |
| 11 | `refactor(review): convert DependencyLicenseReviewer to LLM-based analysis` | dependencies.py, test_dependency_license_reviewer.py | pytest tests/review/agents/test_dependency_license_reviewer.py |
| 12 | `refactor(review): convert ReleaseChangelogReviewer to LLM-based analysis` | changelog.py, test_release_changelog_reviewer.py | pytest tests/review/agents/test_release_changelog_reviewer.py |
| 13 | `refactor(review): final verification of LLM-based agent conversion` | All test files, cleanup changes | pytest tests/review/ |

---

## Success Criteria

### Verification Commands
```bash
# Run all agent tests
pytest tests/review/agents/ -v --tb=short
# Expected: All tests pass, 100% pass rate

# Verify no hardcoded patterns remain
grep -r "SECRET_PATTERNS\|DANGEROUS_PATTERNS\|_check_for_\|CommandExecutor\|ruff check\|import ast" opencode_python/src/opencode_python/agents/review/agents/ | grep -v "__pycache__"
# Expected: No matches

# Verify integration works
pytest tests/review/test_integration_review_pipeline.py -v
# Expected: Integration test passes

# Verify linting passes
ruff check opencode_python/src/opencode_python/agents/review/agents/
# Expected: 0 errors
```

### Final Checklist
- [x] All 11 agents converted to AISession-based review() methods
- [x] All hardcoded check methods removed from all agents
- [x] All regex patterns deleted from all agents
- [x] All external command calls removed from all agents
- [x] All AST analysis code removed from all agents
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All tests pass (11 agents × multiple tests each)
- [x] Orchestrator integration test passes
- [x] No linting errors in converted agents
- [x] No unused imports in any agent
