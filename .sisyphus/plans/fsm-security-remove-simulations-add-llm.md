# FSM Security Reviewer - Remove Simulations & Add LLM Prompts

## TL;DR

> **Quick Summary**: Transform FSM security reviewer from tool-based only to true agentic system with LLM prompts driving all states
>
> **Deliverables**:
> - Remove simulation code with mock findings
> - Enable LLM client integration throughout FSM workflow
> - Add LLM prompts for todo creation, result analysis, final assessment
> - Pass LLM client to subagents
>
> **Estimated Effort**: Medium
> **Parallel Execution**: NO - sequential changes required
> **Critical Path**: Remove simulation → Enable LLM → Add prompts → Test

---

## Context

### Original Request
The user wants to make the FSM security reviewer production-ready by:
1. Removing all simulations and canned responses
2. Making it truly agentic with LLM prompts throughout the workflow
3. Ensuring prompts guide the process through each state

### Current State Analysis

**What Works (Production-Ready):**
- Subagents (SecretsScannerAgent, InjectionScannerAgent, etc.) use real tools (bandit, semgrep, grep)
- ToolExecutor runs actual bandit, semgrep, grep commands
- FSM state transitions are properly defined
- AuthReviewerAgent has LLM integration built-in (but LLM client not passed)

**What Blocks Production:**
1. `_simulate_subagent_execution()` (lines 1233-1390 in fsm_security.py) - Contains hardcoded mock findings
2. LLM discovery disabled (`llm_client=None` on line 462) - LLM discovery never runs
3. No LLM client parameter in SecurityReviewerAgent `__init__`
4. FSM state handlers use rule-based logic only, no LLM prompts
5. Subagents don't receive LLM client (auth_reviewer needs it)

---

## Work Objectives

### Core Objective
Transform the FSM security reviewer from a tool-based orchestration system to a true agentic system where LLM prompts drive decision-making at each FSM state, with real tool execution for investigations.

### Concrete Deliverables
- Modified `dawn_kestrel/agents/review/fsm_security.py` with:
  - LLM client parameter in `__init__`
  - LLM prompts for todo creation, result analysis, final assessment
  - No simulation code
- Updated subagent calls to pass LLM client where needed
- FSM CLI updated to create and pass LLM client

### Definition of Done
- [x] All mock/simulation code removed from fsm_security.py
- [x] LLM client passed to SecurityReviewerAgent constructor
- [x] LLM client passed to auth_reviewer subagent
- [x] `_llm_discover_todos()` enabled by default (not None)
- [x] `_review_investigation_results()` uses LLM to analyze findings
- [x] `_generate_final_assessment()` uses LLM to create assessment
- [x] FSM CLI creates LLM client and passes to reviewer
- [x] No hardcoded findings in any method

### Must Have
- Real tool execution only (no mock data)
- LLM prompts for all strategic decision points
- Subagents receive LLM client when appropriate
- Backward compatible with existing subagents

### Must NOT Have (Guardrails)
- No mock/simulation methods in production code
- No hardcoded findings
- No `llm_client=None` as default in critical paths
- No simulation method references

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: Tests-after
- **Framework**: pytest

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

```
Scenario: Run FSM security review with LLM on real repository
  Tool: Bash (CLI command)
  Preconditions: dawn-kestrel installed, LLM_API_KEY set, git repo exists
  Steps:
    1. cd /path/to/test-repo
    2. export LLM_API_KEY="test-key"
    3. dawn-kestrel fsm-security review --base-ref main --head-ref HEAD --verbose
  Expected Result: Review completes without simulation warnings, real findings from tools
  Failure Indicators: "Simulating" in logs, mock findings with "AKIAIOSFODNN7EXAMPLE"
  Evidence: Terminal output showing tool execution (bandit, semgrep)

Scenario: LLM-powered todo creation generates context-aware todos
  Tool: Bash (grep on logs)
  Preconditions: Review ran with verbose logging
  Steps:
    1. dawn-kestrel fsm-security review --base-ref main --head-ref HEAD --verbose 2>&1 | grep "LLM_DISCOVERY"
    2. dawn-kestrel fsm-security review --base-ref main --head-ref HEAD --verbose 2>&1 | grep "Starting LLM-powered discovery layer"
  Expected Result: LLM discovery ran and created additional todos
  Failure Indicators: "No LLM client provided, skipping discovery layer"
  Evidence: Log entries showing LLM-discovered todos

Scenario: auth_reviewer receives LLM client and uses it
  Tool: Bash (grep on logs)
  Preconditions: Review ran with auth files present
  Steps:
    1. dawn-kestrel fsm-security review --verbose 2>&1 | grep "AUTH_REVIEWER.*LLM client provided"
    2. dawn-kestrel fsm-security review --verbose 2>&1 | grep "Analyzing with LLM for JWT/OAuth validation"
  Expected Result: Auth reviewer uses LLM analysis
  Failure Indicators: "No LLM client provided, skipping LLM-based analysis"
  Evidence: Log entries showing LLM-based auth findings

Scenario: Final assessment uses LLM for summary generation
  Tool: Bash (grep on logs)
  Preconditions: Review completed
  Steps:
    1. dawn-kestrel fsm-security review --verbose 2>&1 | grep "FINAL_ASSESSMENT.*Generating with LLM"
    2. dawn-kestrel fsm-security review --verbose 2>&1 | grep "LLM-based final assessment generated"
  Expected Result: Final assessment generated via LLM
  Failure Indicators: Rule-based assessment without LLM
  Evidence: Log entries showing LLM assessment generation

Scenario: No simulation code executed
  Tool: Bash (grep on source code)
  Preconditions: Code changes deployed
  Steps:
    1. grep -n "_simulate_subagent_execution" dawn_kestrel/agents/review/fsm_security.py
    2. grep -n "AWS_ACCESS_KEY_ID='AKIA" dawn_kestrel/agents/review/fsm_security.py
  Expected Result: No simulation method or mock findings in source
  Failure Indicators: Method definition found, mock evidence strings found
  Evidence: grep returns no matches
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Remove simulation code from fsm_security.py
├── Task 2: Add LLM client to SecurityReviewerAgent

Wave 2 (After Wave 1):
├── Task 3: Enable LLM discovery for todo creation
├── Task 4: Pass LLM client to subagents
└── Task 5: Add LLM prompts to result analysis

Wave 3 (After Wave 2):
├── Task 6: Add LLM prompts to final assessment
└── Task 7: Update FSM CLI to create LLM client

Critical Path: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7
Parallel Speedup: ~30% (tasks 3-5 can run together)
```

---

## TODOs

- [x] 1. Remove simulation code from fsm_security.py

  **What to do**:
  - Delete `_simulate_subagent_execution()` method (lines 1233-1390)
  - Remove any calls to `_simulate_subagent_execution()` if they exist
  - Remove mock/canned finding data from the file

  **Must NOT do**:
  - Remove `_delegate_investigation_tasks()` which calls real subagents
  - Remove `_wait_for_investigation_tasks()` which manages async task completion

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Simple code deletion task, no complex logic
  - **Skills**: [`napkin`]
    - `napkin`: Record this change in napkin - removed simulation code

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 1)
  - **Blocks**: Task 2 (can't add LLM client until simulation removed)
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/agents/review/fsm_security.py:1233-1390` - `_simulate_subagent_execution()` method to delete
  - `dawn_kestrel/agents/review/fsm_security.py:1057-1179` - Real subagent delegation pattern to preserve

  **API/Type References** (contracts to implement against):
  - None - simple code deletion

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_fsm_security_dedup.py` - FSM security tests to ensure still pass

  **Documentation References** (specs and requirements):
  - `dawn_kestrel/agents/review/fsm_security.py:1-30` - Module docstring mentions FSM-based approach

  **External References** (libraries and frameworks):
  - None

  **WHY Each Reference Matters** (explain the relevance):
  - fsm_security.py:1233-1390 - Contains the exact simulation code to remove, including all mock findings
  - fsm_security.py:1057-1179 - Shows the REAL subagent delegation pattern that must be preserved

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.
  > REPLACE all placeholders with actual values from task context.

  - [ ] Method `_simulate_subagent_execution()` deleted from fsm_security.py
  - [ ] No references to `_simulate_subagent_execution()` remain in the file
  - [ ] No mock finding strings (e.g., "AKIAIOSFODNN7EXAMPLE") in the file
  - [ ] grep -n "_simulate_subagent_execution" dawn_kestrel/agents/review/fsm_security.py → 0 matches
  - [ ] grep -n "AKIAIOSFODNN7EXAMPLE" dawn_kestrel/agents/review/fsm_security.py → 0 matches

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: Simulation code fully removed
    Tool: Bash (grep)
    Preconditions: Code changes applied
    Steps:
      1. grep -c "_simulate_subagent_execution" dawn_kestrel/agents/review/fsm_security.py
      2. grep -c "AKIAIOSFODNN7EXAMPLE" dawn_kestrel/agents/review/fsm_security.py
    Expected Result: Both grep commands return 0 matches
    Failure Indicators: grep returns > 0 matches
    Evidence: grep output showing 0 matches
  ```

  **Evidence to Capture**:
  - [ ] grep output showing 0 matches for simulation method
  - [ ] git diff showing deleted lines

  **Commit**: YES (groups with Tasks 2-3)
  - Message: `refactor(fsm-security): Remove simulation code and add LLM integration`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`
  - Pre-commit: `pytest tests/review/agents/ -v`

---

- [x] 2. Add LLM client to SecurityReviewerAgent constructor

  **What to do**:
  - Add `llm_client: Optional[LLMClient]` parameter to `__init__`
  - Store `self.llm_client` as instance variable
  - Update docstring to document LLM client parameter
  - Add typing import for Optional and LLMClient

  **Must NOT do**:
  - Create LLM client inside SecurityReviewerAgent (should be injected)
  - Make llm_client required (allow None for backward compatibility with tests)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Simple parameter addition, straightforward task
  - **Skills**: [`napkin`]
    - `napkin`: Record LLM client injection pattern

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 1, after Task 1)
  - **Blocks**: Task 3 (needs llm_client to enable discovery)
  - **Blocked By**: Task 1 (should be done first for clean diff)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/agents/review/subagents/auth_reviewer.py:69-84` - AuthReviewerAgent LLM client injection pattern
  - `dawn_kestrel/agents/review/fsm_security.py:259-271` - SecurityReviewerAgent.__init__ to modify

  **API/Type References** (contracts to implement against):
  - `dawn_kestrel/llm:LLMClient` - LLM client type for type hints

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_fsm_security_dedup.py` - See how FSM agent is instantiated in tests

  **Documentation References** (specs and requirements):
  - `dawn_kestrel/agents/review/fsm_security.py:224-237` - Class docstring mentions FSM-based approach

  **External References** (libraries and frameworks):
  - None

  **WHY Each Reference Matters** (explain the relevance):
  - auth_reviewer.py:69-84 - Shows the exact pattern for injecting LLM client (parameter, storage, optional)
  - fsm_security.py:259-271 - The __init__ method that needs LLM client parameter
  - tests/.../test_fsm_security_dedup.py - Shows test patterns that may need updating for new parameter

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.
  > REPLACE all placeholders with actual values from task context.

  **If TDD (tests enabled):**
  - [ ] Test verifies LLM client is stored correctly
  - [ ] Test handles None case (backward compatibility)

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: LLM client parameter added and stored
    Tool: Bash (python -c import)
    Preconditions: Code changes applied
    Steps:
      1. python -c "from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent; from unittest.mock import MagicMock; a = SecurityReviewerAgent(MagicMock(), 'test', llm_client=None); print('llm_client' in dir(a))"
    Expected Result: Prints True (llm_client attribute exists)
    Failure Indicators: Prints False or AttributeError
    Evidence: Python output showing attribute exists
  ```

  **Evidence to Capture**:
  - [ ] Python verification output
  - [ ] git diff showing added parameter

  **Commit**: YES (groups with Tasks 1,3)
  - Message: `refactor(fsm-security): Remove simulation code and add LLM integration`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`
  - Pre-commit: `pytest tests/review/agents/ -v`

---

- [x] 3. Enable LLM discovery for dynamic todo creation

  **What to do**:
  - In `_initial_exploration()`, pass `self.llm_client` instead of `None` to `_create_dynamic_todos()`
  - Remove or update comment "Pass None for rule-only mode, can be enhanced later"
  - Ensure `_llm_discover_todos()` is called when LLM client is available
  - Update `_create_dynamic_todos()` to use passed llm_client

  **Must NOT do**:
  - Break rule-based todo creation (LLM should be additive)
  - Remove existing rule-based patterns that work well

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Simple parameter change, enabling existing code
  - **Skills**: [`napkin`]
    - `napkin`: Record LLM discovery enablement

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2, after Task 2)
  - **Blocks**: None
  - **Blocked By**: Task 2 (needs llm_client instance variable)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/agents/review/fsm_security.py:461-463` - Line passing llm_client=None to change
  - `dawn_kestrel/agents/review/fsm_security.py:884-892` - LLM discovery conditional to enable

  **API/Type References** (contracts to implement against):
  - None - using existing LLM client instance

  **Test References** (testing patterns to follow):
  - `tests/review/integration/test_full_security_review.py` - Integration tests that may need LLM client

  **Documentation References** (specs and requirements):
  - `dawn_kestrel/agents/review/fsm_security.py:883-893` - _create_dynamic_todos docstring mentions LLM discovery

  **External References** (libraries and frameworks):
  - None

  **WHY Each Reference Matters** (explain the relevance):
  - fsm_security.py:461-463 - Exact line where llm_client=None is passed, needs to pass self.llm_client
  - fsm_security.py:884-892 - Shows the conditional that checks for llm_client before calling _llm_discover_todos

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.
  > REPLACE all placeholders with actual values from task context.

  - [ ] Line 462 passes `self.llm_client` instead of `None`
  - [ ] Comment about rule-only mode updated or removed
  - [ ] grep "llm_client=None" dawn_kestrel/agents/review/fsm_security.py → 0 matches in _initial_exploration

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: LLM discovery runs when llm_client is provided
    Tool: Bash (grep on logs)
    Preconditions: Review ran with LLM client, verbose logging
    Steps:
      1. dawn-kestrel fsm-security review --verbose 2>&1 | grep "Starting LLM-powered discovery layer"
    Expected Result: Log shows LLM discovery started
    Failure Indicators: "No LLM client provided, skipping discovery layer"
    Evidence: Log output showing LLM discovery
  ```

  **Evidence to Capture**:
  - [ ] Log output showing LLM discovery executed
  - [ ] git diff showing parameter change

  **Commit**: YES (groups with Tasks 1-2)
  - Message: `refactor(fsm-security): Remove simulation code and add LLM integration`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`
  - Pre-commit: `pytest tests/review/agents/ -v`

---

- [x] 4. Pass LLM client to subagents that need it

- [x] 5. Add LLM prompt to _review_investigation_results for analysis

  **What to do**:
  - Create new method `_analyze_findings_with_llm()` that uses LLM to:
    - Analyze all findings from current iteration
    - Determine if additional review tasks are needed
    - Identify patterns across findings
    - Prioritize high-severity issues
  - In `_review_investigation_results()`, call LLM analysis if llm_client is available
  - Update return logic to use LLM's decision about whether more tasks are needed
  - Maintain backward compatibility: if no LLM client, use existing rule-based logic

  **Must NOT do**:
  - Remove existing rule-based analysis entirely (LLM should enhance, not replace)
  - Make LLM mandatory (fallback to rules if unavailable)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: New method creation with LLM integration, moderate complexity
  - **Skills**: [`napkin`]
    - `napkin`: Record LLM-based finding analysis pattern

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 4)
  - **Blocks**: Task 6 (needs good analysis to create better assessments)
  - **Blocked By**: Task 2 (needs self.llm_client)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/agents/review/fsm_security.py:1406-1466` - `_review_investigation_results()` method to enhance
  - `dawn_kestrel/agents/review/subagents/auth_reviewer.py:214-339` - LLM prompt pattern for reference

  **API/Type References** (contracts to implement against):
  - `dawn_kestrel/llm:LLMClient`, `dawn_kestrel/llm:LLMRequestOptions` - LLM client types

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_fsm_security_confidence.py` - Tests for finding analysis

  **Documentation References** (specs and requirements):
  - `dawn_kestrel/agents/review/fsm_security.py:1406-1420` - Method docstring

  **External References** (libraries and frameworks):
  - None

  **WHY Each Reference Matters** (explain the relevance):
  - fsm_security.py:1406-1466 - The _review_investigation_results method that needs LLM analysis added
  - auth_reviewer.py:214-339 - Shows the exact pattern for building LLM prompts and parsing JSON responses

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.
  > REPLACE all placeholders with actual values from task context.

  - [ ] New method `_analyze_findings_with_llm()` created
  - [ ] `_review_investigation_results()` calls LLM analysis when available
  - [ ] LLM prompt asks about: patterns, priorities, need for more tasks
  - [ ] Fallback to rule-based logic when no LLM client

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: Finding analysis uses LLM to determine next actions
    Tool: Bash (grep on logs)
    Preconditions: Review ran with LLM client, findings generated
    Steps:
      1. dawn-kestrel fsm-security review --verbose 2>&1 | grep "REVIEWING_RESULTS.*LLM-based finding analysis"
      2. dawn-kestrel fsm-security review --verbose 2>&1 | grep "LLM determined.*tasks needed"
    Expected Result: Log shows LLM analysis influenced decision
    Failure Indicators: Only rule-based analysis logs
    Evidence: Log output showing LLM-based decisions
  ```

  **Evidence to Capture**:
  - [ ] Log output showing LLM finding analysis
  - [ ] git diff showing new method

  **Commit**: YES (groups with Task 4)
  - Message: `refactor(fsm-security): Pass LLM client to subagents and add result analysis prompts`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `dawn_kestrel/agents/review/subagents/*.py`
  - Pre-commit: `pytest tests/review/agents/ -v`

---

- [x] 6. Add LLM prompt to _generate_final_assessment

  **What to do**:
  - Create new method `_generate_assessment_with_llm()` that uses LLM to:
    - Analyze all findings for overall severity determination
    - Generate comprehensive summary
    - Determine merge recommendation (approve/needs_changes/block)
    - Create notes highlighting key issues
  - In `_generate_final_assessment()`, call LLM generation if llm_client is available
  - Update return logic to use LLM's assessment
  - Maintain backward compatibility: if no LLM client, use existing rule-based logic

  **Must NOT do**:
  - Remove existing rule-based assessment entirely (LLM should enhance)
  - Make LLM mandatory (fallback to rules if unavailable)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: New method with LLM integration, similar to Task 5
  - **Skills**: [`napkin`]
    - `napkin`: Record LLM-based final assessment pattern

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3, after Tasks 3-5)
  - **Blocks**: Task 7 (CLI needs working assessment)
  - **Blocked By**: Tasks 3-5 (better to have them working first)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/agents/review/fsm_security.py:1540-1617` - `_generate_final_assessment()` method to enhance
  - `dawn_kestrel/agents/review/fsm_security.py:1406-1466` - _review_investigation_results for LLM pattern reference

  **API/Type References** (contracts to implement against):
  - `dawn_kestrel/llm:LLMClient`, `dawn_kestrel/llm:LLMRequestOptions` - LLM client types

  **Test References** (testing patterns to follow):
  - `tests/review/agents/test_fsm_security_confidence.py` - Tests for assessment generation

  **Documentation References** (specs and requirements):
  - `dawn_kestrel/agents/review/fsm_security.py:203-217` - SecurityAssessment dataclass definition

  **External References** (libraries and frameworks):
  - None

  **WHY Each Reference Matters** (explain the relevance):
  - fsm_security.py:1540-1617 - The _generate_final_assessment method that needs LLM generation added
  - fsm_security.py:203-217 - SecurityAssessment structure that LLM must generate (overall_severity, merge_recommendation, etc.)

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.
  > REPLACE all placeholders with actual values from task context.

  - [ ] New method `_generate_assessment_with_llm()` created
  - [ ] `_generate_final_assessment()` calls LLM generation when available
  - [ ] LLM prompt asks for: severity, merge_recommendation, summary, notes
  - [ ] LLM returns SecurityAssessment-compatible JSON structure
  - [ ] Fallback to rule-based logic when no LLM client

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: Final assessment uses LLM for summary generation
    Tool: Bash (grep on logs)
    Preconditions: Review completed, verbose logging
    Steps:
      1. dawn-kestrel fsm-security review --verbose 2>&1 | grep "FINAL_ASSESSMENT.*Generating with LLM"
      2. dawn-kestrel fsm-security review --verbose 2>&1 | grep "LLM-based final assessment generated"
    Expected Result: Log shows LLM assessment generation
    Failure Indicators: Rule-based assessment only
    Evidence: Log output showing LLM assessment
  ```

  **Evidence to Capture**:
  - [ ] Log output showing LLM assessment generation
  - [ ] git diff showing new method

  **Commit**: YES
  - Message: `refactor(fsm-security): Add LLM-based final assessment generation`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`
  - Pre-commit: `pytest tests/review/agents/ -v`

---

- [x] 7. Update FSM CLI to create and pass LLM client

  **What to do**:
  - In `fsm_cli.py`, create LLMClient instance in `review()` function
  - Use environment variables or settings for LLM configuration
  - Pass llm_client to SecurityReviewerAgent constructor
  - Handle LLM client creation errors gracefully with clear error messages
  - Update CLI help text to mention LLM usage

  **Must NOT do**:
  - Hardcode API keys or credentials
  - Break existing CLI options

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Straightforward CLI modification, existing LLM creation patterns
  - **Skills**: [`napkin`]
    - `napkin`: Record LLM client creation in CLI

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3, after Task 6)
  - **Blocks**: None
  - **Blocked By**: Task 6 (need working assessment generation first)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/agents/review/fsm_cli.py:334-467` - `review()` function to modify
  - `dawn_kestrel/llm/__init__.py` - LLMClient creation pattern (look for `create_client()` or similar)

  **API/Type References** (contracts to implement against):
  - `dawn_kestrel/llm:LLMClient` - LLM client type

  **Test References** (testing patterns to follow):
  - `tests/review/integration/test_full_security_review.py` - CLI integration tests

  **Documentation References** (specs and requirements):
  - `dawn_kestrel/agents/review/fsm_cli.py:1-10` - Module docstring

  **External References** (libraries and frameworks):
  - `dawn_kestrel/core/settings.py` - Check for existing LLM configuration patterns

  **WHY Each Reference Matters** (explain the relevance):
  - fsm_cli.py:334-467 - The review function where LLMClient needs to be created and passed
  - dawn_kestrel/llm/__init__.py - Shows the correct way to instantiate LLMClient for production use

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.
  > REPLACE all placeholders with actual values from task context.

  - [ ] LLMClient created in `review()` function
  - [ ] llm_client passed to SecurityReviewerAgent constructor
  - [ ] Error handling for LLM client creation failures
  - [ ] grep "llm_client=" dawn_kestrel/agents/review/fsm_cli.py → shows pass to SecurityReviewerAgent

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```
  Scenario: CLI creates LLM client and passes to reviewer
    Tool: Bash (CLI command)
    Preconditions: dawn-kestrel installed, LLM_API_KEY set
    Steps:
      1. export LLM_API_KEY="test-key"
      2. dawn-kestrel fsm-security review --base-ref main --head-ref HEAD --verbose 2>&1 | grep "SecurityReviewerAgent"
    Expected Result: SecurityReviewerAgent instantiated with llm_client
    Failure Indicators: TypeError or missing parameter
    Evidence: CLI output showing successful review start
  ```

  **Evidence to Capture**:
  - [ ] CLI output showing LLM client created
  - [ ] git diff showing CLI changes

  **Commit**: YES
  - Message: `refactor(fsm-security): Update CLI to create and pass LLM client`
  - Files: `dawn_kestrel/agents/review/fsm_cli.py`
  - Pre-commit: `pytest tests/review/integration/ -v`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1-3 | `refactor(fsm-security): Remove simulation code and add LLM integration` | fsm_security.py | pytest tests/review/agents/ |
| 4-5 | `refactor(fsm-security): Pass LLM client to subagents and add result analysis prompts` | fsm_security.py, subagents/*.py | pytest tests/review/subagents/ |
| 6 | `refactor(fsm-security): Add LLM-based final assessment generation` | fsm_security.py | pytest tests/review/agents/ |
| 7 | `refactor(fsm-security): Update CLI to create and pass LLM client` | fsm_cli.py | pytest tests/review/integration/ |

---

## Success Criteria

### Verification Commands
```bash
# Verify simulation code removed
grep -n "_simulate_subagent_execution" dawn_kestrel/agents/review/fsm_security.py
# Expected: 0 matches

# Verify LLM client exists in agent
python -c "from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent; from unittest.mock import MagicMock; import inspect; sig = inspect.signature(SecurityReviewerAgent.__init__); print('llm_client' in sig.parameters)"
# Expected: True

# Run review with LLM
export LLM_API_KEY="test-key"
dawn-kestrel fsm-security review --base-ref main --head-ref HEAD --verbose 2>&1 | grep -E "(LLM_DISCOVERY|LLM-based finding analysis|LLM-based final assessment)"
# Expected: All three patterns found in logs

# Run integration tests
pytest tests/review/integration/test_full_security_review.py -v
# Expected: All tests pass
```

### Final Checklist
- [x] All mock/simulation code removed
- [x] LLM client integrated throughout FSM workflow
- [x] LLM prompts for todo creation, analysis, assessment
- [x] Subagents receive LLM client
- [x] CLI creates and passes LLM client
- [x] All tests pass
