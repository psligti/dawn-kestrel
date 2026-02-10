# FSM-Security Production Ready

## TL;DR

> **Quick Summary**: Replace mock/simulated security review with real tool execution, multi-layered agent architecture, and dynamic review capabilities based on production-grade patterns from codebases like Remix and XState.
>
> **Deliverables**:
> - Real `ToolExecutor` component for bandit/semgrep/safety/grep/ast-grep
> - Specialized security agents (SecretsScanner, InjectionScanner, AuthReviewer, DependencyAuditor, CryptoScanner, ConfigScanner, ImpactAnalyst)
> - Dynamic todo generation with risk-based prioritization
> - Real `AgentRuntime` integration (no mocks)
> - Production-grade guard patterns and error handling from XState/Remix
> - Comprehensive test coverage for all new components
>
> **Estimated Effort**: XL (4-6 weeks)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: ToolExecutor → Specialized Agents → Dynamic Review → Integration Tests

---

## Context

### Original Request
Make fsm-security production ready with these requirements:
- No simulations (remove mock subagent execution)
- No shortcuts (real tool execution)
- Dynamic review capabilities
- Multilayer agents

### Interview Summary

**Key Discussions**:
- Architecture should preserve FSM structure while replacing mock execution
- Multi-layered defense needed: separate agents for different security domains
- Dynamic review must adapt based on changed files and risk profiles
- Production-grade patterns from Remix/XState should inform guard design and error handling

**Research Findings**:

#### Current State Analysis (from fsm_security.py and tests):
- **FSM architecture** is clean: proper state transitions (lines 46-91, 225-242)
- **Deduplication** works via `processed_finding_ids` and `processed_task_ids` sets
- **Confidence thresholding** filters low-confidence findings with safe fallback
- **Test coverage** exists for: confidence, deduplication, logging, and redaction

#### Critical Gaps Identified:
1. **Simulated Subagent Execution** (`_simulate_subagent_execution()` at lines 774-931)
   - Returns hardcoded mock findings (no real security scanning)
   - Fake 0.5s delay
   - Never calls actual security tools

2. **Mock Orchestrator** (`fsm_cli.py` lines 383-388)
   - Uses `Mock(spec=AgentRuntime)` instead of real runtime
   - Subagent calls never execute

3. **No Real Tool Execution**
   - Tools listed in prompts but never invoked
   - Missing: ToolExecutor component for bandit/semgrep/safety/grep/ast-grep

4. **Single Agent Architecture**
   - Only `SecurityReviewerAgent` exists; subagents are simulated
   - Missing: specialized agents for different security domains

5. **No Dynamic Review**
   - `_create_initial_todos()` creates fixed todos
   - Missing: adaptive generation based on file types, risk-based prioritization

#### Metis Review Findings (Gap Analysis):

**Questions I Should Have Asked**:
1. Should confidence scoring still use 0.50 fallback for malformed values?
2. Should FSM state machine remain unchanged (same transitions, same state handlers)?
3. Should iteration limit (max 5) be configurable or fixed?
4. What happens when security tools are not installed?
5. Should tool execution be synchronous (blocking) or async (parallel)?
6. What's the timeout for each tool execution?
7. Should specialized agents be separate Python classes or LLM-driven?
8. Should there be an agent per security domain or dynamic pool?
9. How adaptive should todo generation be (file-type/risk-based/resource-aware)?
10. What's the delegation pattern (AgentRuntime.execute_agent vs direct tool calls)?

**Guardrails to Set**:
- **MUST PRESERVE**: FSM state transitions, deduplication, confidence thresholding, logging format, assessment schema
- **MUST NOT DO**: Change FSM structure, break dedup, alter test contracts, over-engineer
- **SCOPE BOUNDARIES**: Replace mock execution, implement specialized agents, add dynamic review; exclude: changing state transitions, ML/analytics, persistent storage

**Identified Risks**:
- Tool execution failures (graceful degradation needed)
- Execution time explosion (parallel execution + timeouts)
- Finding schema mismatch (adapter layer needed)
- State transitions violated (error paths not in mock)
- Deduplication breaks (ID collision from real tools)

**Missing Components**:
- ToolExecutor component for running security tools
- Specialized agent implementations (7-8 agents per security domain)
- Dynamic todo generator
- Real AgentRuntime integration
- Finding normalization layer

**Scope Creep Areas to Lock Down**:
- Over-engineering dynamic review (keep rule-based, not ML)
- Adding more security tools (bandit/semgrep/safety/grep only)
- Changing confidence scoring (keep simple threshold)
- Adding persistent storage (in-memory only)
- Building web UI/dashboard (CLI output only)

**Assumptions Needing Validation**:
- Real AgentRuntime exists and is configured with LLM credentials
- Security tools can be installed via `uv tool install` or are pre-installed
- Parallel execution is safe (no tool conflicts)
- Finding IDs can be deterministically generated from tool outputs
- Rule-based dynamic review is sufficient (no ML needed)

#### Production-Grade Security Patterns (from Librarian Research):

**Remix Session Middleware** - Multi-Layered Security:
```typescript
export function session(sessionCookie: Cookie, sessionStorage: SessionStorage): Middleware {
  // Layer 1: Cryptographic validation
  if (!sessionCookie.signed) {
    throw new Error('Session cookie must be signed')
  }

  // Layer 2: Session hijacking prevention
  if (context.sessionStarted) {
    throw new Error('Existing session found, refusing to overwrite')
  }

  // Layer 3: Injection protection
  if (session !== context.session) {
    throw new Error('Cannot save session that was initialized elsewhere')
  }

  // Layer 4: Dirty tracking (reduce attack surface)
  if (setCookieValue != null) {
    response.headers.append('Set-Cookie', await sessionCookie.serialize(setCookieValue))
  }
}
```
**Pattern**: Validate at multiple layers (cryptographic, existence, injection, dirty tracking)

**XState Guard Evaluation** - Fail-Safe Error Handling:
```typescript
for (const candidate of candidates) {
  const { guard } = candidate
  let guardPassed = false

  try {
    guardPassed = !guard || evaluateGuard(guard, resolvedContext, event, snapshot)
  } catch (err: any) {
    // Security: Guard failure doesn't crash - produces descriptive error
    throw new Error(
      `Unable to evaluate guard '${guardType}' in transition for event '${eventType}' in state node '${this.id}':\n${err.message}`
    )
  }
}
```
**Pattern**: Guard failures never crash entire system; they provide context-rich error messages

**XState Error-Based State Transitions**:
```typescript
ProvisionOrder: {
  invoke: { src: 'provisionOrderFunction' },
  onDone: 'ApplyOrder',
  onError: [
    {
      guard: ({ event }) => (event.error as any).message === 'Missing order id',
      target: 'Exception.MissingId'  // Different states for different error types
    },
    {
      guard: ({ event }) => (event.error as any).message === 'Missing order item',
      target: 'Exception.MissingItem'
    }
  ]
}
```
**Pattern**: Model errors as state transitions, not exceptions; guard-based routing

---

## Work Objectives

### Core Objective
Transform fsm-security from mock/simulation-based demo to production-ready security review system with real tool execution, multi-layered agent architecture, and dynamic review capabilities.

### Concrete Deliverables
- **ToolExecutor Component** (`dawn_kestrel/agents/review/tools.py` - NEW)
  - Execute bandit/semgrep/safety/grep/ast-grep with proper error handling
  - Normalize tool outputs to `SecurityFinding` format
  - Handle tool installation failures gracefully

- **Specialized Security Agents** (`dawn_kestrel/agents/review/subagents/` - NEW directory)
  - `SecretsScannerAgent`: Real bandit/grep execution for hardcoded secrets
  - `InjectionScannerAgent`: Real semgrep for SQLi/XSS patterns
  - `AuthReviewerAgent`: LLM + patterns for auth code (JWT/OAuth validation)
  - `DependencyAuditorAgent`: Real safety/pip-audit for vulnerability checks
  - `CryptoScannerAgent`: grep/ast-grep for weak crypto (MD5, hardcoded keys)
  - `ConfigScannerAgent`: grep for security misconfigurations (DEBUG=True, etc.)
  - `ImpactAnalystAgent`: LLM for triaging findings and recommending actions

- **Dynamic Todo Generator** (method in `SecurityReviewerAgent`)
  - Adaptive todo creation based on changed file types (Python vs JS vs config)
  - Risk-based prioritization (auth files → high priority auth review)
  - Resource-aware scaling (large diff → limit parallel agents)

- **Real Runtime Integration** (update `fsm_cli.py`)
  - Pass real `AgentRuntime` from CLI to `SecurityReviewerAgent`
  - Use `runtime.execute_agent()` for subagent calls
  - Remove all `Mock` usage

### Definition of Done
- [ ] All specialized agents execute real tools (no hardcoded findings)
- [ ] ToolExecutor handles missing tools gracefully with clear logging
- [ ] Dynamic review generates adaptive todos based on context
- [ ] All existing tests pass (confidence, dedup, logging tests)
- [ ] New tests cover tool execution, normalization, and error scenarios
- [ ] FSM state machine works with real execution (same transitions preserved)
- [ ] Confidence thresholding still applies to tool-generated findings
- [ ] Deduplication prevents duplicate findings from real tools
- [ ] CLI uses real AgentRuntime (no mocks)

---

## Work Objectives

### Core Objective
Transform fsm-security from mock/simulation-based demo to production-ready security review system with real tool execution, multi-layered agent architecture, and dynamic review capabilities.

### Concrete Deliverables
- **ToolExecutor Component** (`dawn_kestrel/agents/review/tools.py` - NEW)
  - Execute bandit/semgrep/safety/grep/ast-grep with proper error handling
  - Normalize tool outputs to `SecurityFinding` format
  - Handle tool installation failures gracefully

- **Specialized Security Agents** (`dawn_kestrel/agents/review/subagents/` - NEW directory)
  - `SecretsScannerAgent`: Real bandit/grep execution for hardcoded secrets
  - `InjectionScannerAgent`: Real semgrep for SQLi/XSS patterns
  - `AuthReviewerAgent`: LLM + patterns for auth code (JWT/OAuth validation)
  - `DependencyAuditorAgent`: Real safety/pip-audit for vulnerability checks
  - `CryptoScannerAgent`: grep/ast-grep for weak crypto (MD5, hardcoded keys)
  - `ConfigScannerAgent`: grep for security misconfigurations (DEBUG=True, etc.)
  - `ImpactAnalystAgent`: LLM for triaging findings and recommending actions

- **Dynamic Todo Generator** (method in `SecurityReviewerAgent`)
  - Adaptive todo creation based on changed file types (Python vs JS vs config)
  - Risk-based prioritization (auth files → high priority auth review)
  - Resource-aware scaling (large diff → limit parallel agents)

- **Real Runtime Integration** (update `fsm_cli.py`)
  - Pass real `AgentRuntime` from CLI to `SecurityReviewerAgent`
  - Use `runtime.execute_agent()` for subagent calls
  - Remove all `Mock` usage

### Definition of Done
- [ ] All specialized agents execute real tools (no hardcoded findings)
- [ ] ToolExecutor handles missing tools gracefully with clear logging
- [ ] Dynamic review generates adaptive todos based on context
- [ ] All existing tests pass (confidence, dedup, logging tests)
- [ ] New tests cover tool execution, normalization, and error scenarios
- [ ] FSM state machine works with real execution (same transitions preserved)
- [ ] Confidence thresholding still applies to tool-generated findings
- [ ] Deduplication prevents duplicate findings from real tools
- [ ] CLI uses real AgentRuntime (no mocks)

---

## Work Objectives (continued)

### Must Have

1. **Real Tool Execution** - Replace `_simulate_subagent_execution()` with actual tool calls
   - Execute bandit, semgrep, safety, grep, ast-grep, git commands
   - Proper error handling and retry logic
   - Configurable timeouts per tool

2. **Multi-Layered Agent Architecture** - Create specialized agents for different security domains
   - Each agent has specific domain knowledge and tool access
   - Orchestrator delegates to appropriate agents based on todo type

3. **Dynamic Review Capabilities** - Adaptive todo generation based on context
   - File-type classification (Python/JS/config)
   - Risk-based prioritization
   - Resource-aware scaling

4. **Production-Grade Error Handling** - Based on XState/Remix patterns
   - Guard failures produce context-rich errors (not crashes)
   - Error state transitions for different error types
   - Graceful degradation when tools fail

5. **Comprehensive Test Coverage** - Tests for all new components
   - Tool execution tests (mock tool outputs)
   - Normalization tests (real tool output parsing)
   - Integration tests (end-to-end review flow)
   - Error scenario tests (missing tools, timeouts)

### Must NOT Have (Guardrails)

- **NO Simulated Execution** - Remove all hardcoded mock data from `_simulate_subagent_execution()`
- **NO Mock Orchestrator** - Replace `Mock(spec=AgentRuntime)` with real `AgentRuntime`
- **NO FSM Changes** - Keep state transitions, state handlers, and validation logic unchanged
- **NO Test Contract Changes** - Existing tests must pass; add new tests without breaking old ones
- **NO Over-Engineering** - Keep dynamic review rule-based (file patterns, risk scoring), not ML
- **NO Extra Security Tools** - Only implement tools referenced in current code: bandit, semgrep, safety, grep, ast-grep, git
- **NO Persistent Storage** - Findings remain in-memory only; no database/storage layer
- **NO Web UI** - CLI output only; no dashboard or UI components

---

## Verification Strategy

### Test Decision

**Infrastructure exists**: YES (pytest for existing tests)
**Automated tests**: YES (TDD - RED-GREEN-REFACTOR for all new components)
**Framework**: pytest (existing framework)
**Agent-Executed QA**: ALWAYS (mandatory for all tasks)

### TDD Workflow

**Task Structure for ALL Tasks**:

1. **RED** (Write test first):
   - Test file: `tests/review/{component}/test_{feature}.py`
   - Test command: `pytest tests/review/{component}/test_{feature}.py`
   - Expected: FAIL (test exists, implementation doesn't)

2. **GREEN** (Implement minimum code to pass):
   - Command: `pytest tests/review/{component}/test_{feature}.py`
   - Expected: PASS

3. **REFACTOR** (Clean up while keeping green):
   - Command: `pytest tests/review/{component}/test_{feature}.py`
   - Expected: PASS (still)

### Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):

#### For Tool Execution Tasks:

```
Scenario: ToolExecutor runs bandit successfully
  Tool: Bash
  Preconditions: bandit installed, target Python file exists
  Steps:
    1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
    2. python -m bandit -f json -r dawn_kestrel/agents/review/test_file.py 2>&1
    3. Assert: HTTP status 0 (success)
    4. Assert: stdout contains "results" key
    5. Assert: stderr is empty (no errors)
  Expected Result: Bandit JSON output parsed and normalized to SecurityFinding format
  Failure Indicators: Non-zero exit code, JSON parse error, stderr contains error
  Evidence: .sisyphus/evidence/task-1-bandit-success.json

Scenario: ToolExecutor handles missing bandit gracefully
  Tool: Bash
  Preconditions: bandit NOT installed
  Steps:
    1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
    2. python -m bandit -f json -r test_file.py 2>&1 || true
    3. Assert: exit code is non-zero (expected failure)
    4. Assert: stderr contains "module not found" or "command not found"
    5. Assert: log contains "[TOOL_MISSING] bandit not installed, skipping"
  Expected Result: Tool skipped, review continues without crash
  Failure Indicators: Uncaught exception, system crash
  Evidence: .sisyphus/evidence/task-1-bandit-missing.json
```

#### For Specialized Agent Tasks:

```
Scenario: SecretsScannerAgent finds AWS access key
  Tool: Bash
  Preconditions: Test file contains "AWS_ACCESS_KEY_ID='AKIAIOSFODNN7EXAMPLE'"
  Steps:
    1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
    2. dawn-kestrel fsm-security review --repo-root ./test-repo --base-ref main --head-ref feature
    3. Wait for review completion
    4. Assert: output contains finding with id containing "AWS" or "ACCESS_KEY"
    5. Assert: severity is "critical" or "high"
    6. Assert: evidence contains redacted key ("[REDACTED]")
  Expected Result: Critical finding for exposed AWS credentials
  Failure Indicators: No finding found, incorrect severity, key not redacted
  Evidence: .sisyphus/evidence/task-2-secrets-aws-key.json
```

#### For Dynamic Review Tasks:

```
Scenario: Dynamic todo generation prioritizes auth files
  Tool: Bash
  Preconditions: Diff contains Python files with auth-related paths
  Steps:
    1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
    2. Create test diff with "src/auth/login.py" and "src/api/user.py" changed
    3. dawn-kestrel fsm-security review --repo-root ./test-repo --base-ref main --head-ref feature
    4. Assert: todo list contains "Review authentication and authorization code" with HIGH priority
    5. Assert: todo description mentions auth files found
  Expected Result: High-priority auth review todo generated
  Failure Indicators: Auth review not created, wrong priority, no auth files mentioned
  Evidence: .sisyphus/evidence/task-5-dynamic-auth-priority.json
```

#### For Integration Tests:

```
Scenario: End-to-end security review completes with real tools
  Tool: Bash
  Preconditions: Test repo with Python files containing vulnerabilities
  Steps:
    1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
    2. dawn-kestrel fsm-security review --repo-root ./test-repo --base-ref main --head-ref feature
    3. Wait for completion (timeout 300s)
    4. Assert: exit code is 0
    5. Assert: output contains "Overall Severity: critical" or "high"
    6. Assert: findings list contains real file paths from test repo
    7. Assert: findings have non-simulated evidence (actual code snippets)
    8. Assert: no logs contain "Simulated" or "Mock"
  Expected Result: Complete assessment with real findings from tool execution
  Failure Indicators: Exit code non-zero, missing findings, simulated logs present
  Evidence: .sisyphus/evidence/task-10-integration-e2e.json
```

---

## Execution Strategy

### Parallel Execution Waves

**Wave 1 (Foundation - Start Immediately)**:
├── Task 1: Create ToolExecutor component
└── Task 2: Create test framework for ToolExecutor

**Wave 2 (Core Agents - After Wave 1)**:
├── Task 3: Implement SecretsScannerAgent with real bandit execution
├── Task 4: Implement InjectionScannerAgent with real semgrep execution
├── Task 5: Implement AuthReviewerAgent with LLM + patterns
└── Task 6: Create tests for specialized agents

**Wave 3 (More Agents - After Wave 2)**:
├── Task 7: Implement DependencyAuditorAgent with real safety execution
├── Task 8: Implement CryptoScannerAgent with grep/ast-grep
├── Task 9: Implement ConfigScannerAgent with grep patterns
└── Task 10: Create tests for remaining agents

**Wave 4 (Integration - After Wave 3)**:
├── Task 11: Implement Dynamic Todo Generator
├── Task 12: Update SecurityReviewerAgent to use real subagents
├── Task 13: Update fsm_cli.py to use real AgentRuntime
└── Task 14: Create integration tests for full workflow (LLM-enhanced)

**Critical Path**: Task 1 → Task 3 → Task 11 → Task 12 → Task 14
**Parallel Speedup**: ~50% faster than sequential (waves 2-4 can run partially in parallel)
├── Task 12: Create dynamic agent pool (optional enhancement)

---

## TODOs

---

### Wave 1: Foundation

- [x] 1. Create ToolExecutor Component

  **What to do**:
  - Create `dawn_kestrel/agents/review/tools.py` (NEW FILE)
  - Implement `ToolExecutor` class with:
    - `execute_tool(tool_name: str, args: list[str], timeout: int) -> ToolResult`
    - Error handling with retries (max 3 retries)
    - Logging: `[TOOL_EXEC] Starting tool {tool_name}` / `[TOOL_DONE] {tool_name} completed`
    - Timeout handling: kill process after timeout, log `[TOOL_TIMEOUT] {tool_name} timed out after {timeout}s`
  - Implement normalization functions:
    - `normalize_bandit_output(json_data) -> List[SecurityFinding]`
    - `normalize_semgrep_output(json_data) -> List[SecurityFinding]`
    - `normalize_safety_output(json_data) -> List[SecurityFinding]`
    - `normalize_grep_output(text_data) -> List[SecurityFinding]`
  - Implement tool availability check:
    - `is_tool_installed(tool_name: str) -> bool`
    - Return graceful degradation message if not installed

  **Must NOT do**:
  - Don't add support for tools not in scope (trivy, grype, sonarqube)
  - Don't implement tool auto-installation (assume pre-installed or user installs)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Reason**: New component creation following existing patterns in codebase. No specialized domain knowledge needed.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO (Blocks all other foundation work)
  - **Parallel Group**: Wave 1 (Sequential only)
  - **Blocks**: Tasks 2-14
  - **Blocked By**: None (can start immediately)

  **References**:
  - Pattern References (execution patterns):
    - `dawn_kestrel/agents/review/fsm_security.py:696-731` - Subagent task creation pattern
    - `dawn_kestrel/agents/review/fsm_cli.py:79-106` - Tool installation check pattern
  - API/Type References:
    - `dawn_kestrel/core/agent_task.py` - TaskStatus, create_agent_task patterns
  - Documentation References (external tools):
    - https://bandit.readthedocs.io/en/latest/ - Bandit CLI usage
    - https://semgrep.dev/docs/ - Semgrep command-line interface
    - https://pyup.io/docs/tools/safety/ - Safety CLI

  **WHY Each Reference Matters**:
  - `fsm_security.py:696-731`: Shows how to create SubagentTask objects with tool names and prompts - adapt this pattern for ToolExecutor
  - `fsm_cli.py:79-106`: Shows tool installation checks using subprocess.run - use similar pattern for ToolExecutor.is_tool_installed
  - `agent_task.py`: Defines TaskStatus and agent task structure - needed for ToolResult

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/tools/test_tool_executor.py`
  - [ ] Test covers: execute_tool success, tool not installed, timeout handling
  - [ ] Test covers: normalize_bandit_output, normalize_semgrep_output
  - [ ] `pytest tests/review/tools/test_tool_executor.py` → PASS (3 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: ToolExecutor executes bandit successfully
    Tool: Bash
    Preconditions: bandit installed, target Python file exists
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "from dawn_kestrel.agents.review.tools import ToolExecutor; import asyncio; executor = ToolExecutor(); result = asyncio.run(executor.execute_tool('bandit', ['-f', 'json', '-r', 'test_file.py'])); print('Tool result:', result); print('Exit code:', result.exit_code)"
      3. Assert: result.exit_code is 0
      4. Assert: result.stdout contains "results" key
      5. Assert: result.error is None
    Expected Result: ToolResult with exit_code=0, stdout contains bandit JSON
    Failure Indicators: exit_code != 0, error message present
    Evidence: .sisyphus/evidence/task-1-bandit-exec.json
  ```

  **Commit**: NO (groups with N)

---

- [ ] 2. Create Test Framework for ToolExecutor

  **What to do**:
  - Create test file: `tests/review/tools/test_tool_executor.py`
  - Create mock fixtures for tool outputs (bandit JSON, semgrep JSON, etc.)
  - Set up pytest fixtures for test files with vulnerabilities

  **Must NOT do**:
  - Don't create test infrastructure files (pytest.ini, conftest.py)
  - Don't mock ToolExecutor internals (test the interface)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Simple test file creation for new component.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO (Depends on Task 1)
  - **Parallel Group**: Wave 1 (Sequential)
  - **Blocks**: Tasks 3-14
  - **Blocked By**: Task 1

  **References**:
  - Test References (existing test patterns):
    - `tests/review/agents/test_fsm_security_confidence.py:22-90` - Test structure with pytest
    - `tests/review/agents/test_fsm_security_dedup.py:25-80` - Mock usage pattern with patch
  - Type References:
    - `dawn_kestrel/agents/review/fsm_security.py` - SecurityFinding, TaskStatus types

  **WHY Each Reference Matters**:
  - `test_fsm_security_confidence.py`: Shows pytest async test structure with caplog - follow this pattern
  - `test_fsm_security_dedup.py`: Shows how to patch create_agent_task and track delegated todos

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/tools/test_tool_executor.py`
  - [ ] Test covers: ToolExecutor init, execute_tool success/failure cases
  - [ ] `pytest tests/review/tools/test_tool_executor.py` → PASS (at least 3 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Test file validates ToolExecutor handles missing tools
    Tool: Bash
    Preconditions: pytest installed, test file exists
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -m pytest tests/review/tools/test_tool_executor.py::TestToolExecutor::test_missing_tool_graceful_degradation -v
      3. Assert: test passes (exit code 0)
      4. Assert: stdout contains "gracefully degraded" or "skipping"
    Expected Result: Test passes, confirming graceful degradation
    Failure Indicators: Test fails, exception in test
    Evidence: .sisyphus/evidence/task-2-test-missing-tool.json
  ```

  **Commit**: YES (with Task 1)
  - Message: `test(review): Add ToolExecutor tests`
  - Files: `dawn_kestrel/agents/review/tools.py`, `tests/review/tools/test_tool_executor.py`
  - Pre-commit: `pytest tests/review/tools/test_tool_executor.py`

---

### Wave 2: Core Security Agents

- [ ] 3. Implement SecretsScannerAgent

  **What to do**:
  - Create `dawn_kestrel/agents/review/subagents/secrets_scanner.py` (NEW FILE)
  - Implement `SecretsScannerAgent` class:
    - Inherits from base SecurityReviewerAgent pattern
    - Uses ToolExecutor to run bandit for hardcoded secrets
    - Implements pattern matching via grep as fallback
    - Handles bandit output normalization
  - Update SecurityReviewerAgent to use SecretsScannerAgent instead of mock

  **Must NOT do**:
  - Don't add AI-based secret detection (tool-based only)
  - Don't change FSM transitions in SecurityReviewerAgent
  - Don't add secret storage/management beyond finding

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Reason**: Agent implementing tool execution with known patterns. LLM not needed for secret scanning.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES (Independent of InjectionScannerAgent, AuthReviewerAgent)
  - **Parallel Group**: Wave 2 (can run with InjectionScannerAgent, AuthReviewerAgent)
  - **Blocks**: Tasks 11-14
  - **Blocked By**: Task 1

  **References**:
  - Pattern References (tool usage):
    - `dawn_kestrel/agents/review/tools.py` - ToolExecutor.execute_tool pattern
  - API/Type References:
    - `dawn_kestrel/agents/review/fsm_security.py` - SubagentTask, SecurityFinding
  - External References:
    - https://bandit.readthedocs.io/en/latest/config.html - Bandit configuration
    - Bandit secret detection plugin patterns

  **WHY Each Reference Matters**:
  - `tools.py`: ToolExecutor is the new interface for all specialized agents to use
  - `fsm_security.py`: SubagentTask structure shows what to return from agent execution

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/subagents/test_secrets_scanner.py`
  - [ ] Test covers: bandit execution, grep fallback, output normalization
  - [ ] Mock test fixtures for bandit output
  - [ ] `pytest tests/review/subagents/test_secrets_scanner.py` → PASS (at least 3 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: SecretsScannerAgent finds AWS access key in Python file
    Tool: Bash
    Preconditions: Test file contains "AWS_ACCESS_KEY_ID='AKIAIOSFODNN7EXAMPLE'"
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "from dawn_kestrel.agents.review.subagents.secrets_scanner import SecretsScannerAgent; import asyncio; import unittest.mock as mock; orchestrator = mock.Mock(); agent = SecretsScannerAgent(orchestrator, 'session-001'); result = asyncio.run(agent.run_tool('scan_secrets', 'test_file.py')); print('Findings:', result.findings); print('Count:', len(result.findings))"
      3. Assert: len(result.findings) > 0
      4. Assert: any(f.id.startswith('sec_') for f in result.findings)
      5. Assert: any(f.severity in ['critical', 'high'] for f in result.findings)
    Expected Result: At least one critical/high finding for exposed AWS key
    Failure Indicators: No findings found, incorrect finding ID format
    Evidence: .sisyphus/evidence/task-3-aws-key.json
  ```

  **Commit**: YES (groups with N)
  - Message: `feat(review): Implement SecretsScannerAgent with real bandit execution`
  - Files: `dawn_kestrel/agents/review/subagents/secrets_scanner.py`, `tests/review/subagents/test_secrets_scanner.py`
  - Pre-commit: `pytest tests/review/subagents/test_secrets_scanner.py`

---

- [ ] 4. Implement InjectionScannerAgent

  **What to do**:
  - Create `dawn_kestrel/agents/review/subagents/injection_scanner.py` (NEW FILE)
  - Implement `InjectionScannerAgent` class:
    - Uses ToolExecutor to run semgrep for injection patterns
    - Semgrep rules for: SQL injection, XSS, command injection, path traversal
    - Handles semgrep output normalization
  - Update SecurityReviewerAgent to use InjectionScannerAgent

  **Must NOT do**:
  - Don't add custom rules beyond standard semgrep patterns
  - Don't change finding schema for injection-specific fields

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Reason**: Agent implementing tool execution with known semgrep patterns. LLM not needed for pattern matching.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES (Independent of SecretsScannerAgent, AuthReviewerAgent)
  - **Parallel Group**: Wave 2 (can run with SecretsScannerAgent, AuthReviewerAgent)
  - **Blocks**: Tasks 11-14
  - **Blocked By**: Task 1

  **References**:
  - Pattern References (tool usage):
    - `dawn_kestrel/agents/review/tools.py` - ToolExecutor.execute_tool pattern
  - External References:
    - https://semgrep.dev/docs/writing-rules/unsafe-python - Semgrep rule patterns for injection
    - https://semgrep.dev/docs/writing-rules/unsafe-javascript - XSS patterns

  **WHY Each Reference Matters**:
  - `tools.py`: ToolExecutor is the new interface for all specialized agents to use
  - Semgrep docs: Provide production-grade rule patterns for injection vulnerabilities

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/subagents/test_injection_scanner.py`
  - [ ] Test covers: semgrep execution, output normalization, finding creation
  - [ ] Mock test fixtures for semgrep JSON output
  - [ ] `pytest tests/review/subagents/test_injection_scanner.py` → PASS (at least 3 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: InjectionScannerAgent finds SQL injection via semgrep
    Tool: Bash
    Preconditions: Test file contains "SELECT * FROM users WHERE id={user_input}"
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "from dawn_kestrel.agents.review.subagents.injection_scanner import InjectionScannerAgent; import asyncio; import unittest.mock as mock; orchestrator = mock.Mock(); agent = InjectionScannerAgent(orchestrator, 'session-001'); result = asyncio.run(agent.run_tool('scan_injection', 'test_file.py')); print('Findings:', result.findings); print('Count:', len(result.findings))"
      3. Assert: len(result.findings) > 0
      4. Assert: any('SQL' in f.title for f in result.findings)
      5. Assert: any(f.evidence contains 'SELECT' for f in result.findings)
    Expected Result: At least one high/critical finding for SQL injection
    Failure Indicators: No findings found, incorrect pattern matching
    Evidence: .sisyphus/evidence/task-4-sql-injection.json
  ```

  **Commit**: YES (groups with N)
  - Message: `feat(review): Implement InjectionScannerAgent with real semgrep execution`
  - Files: `dawn_kestrel/agents/review/subagents/injection_scanner.py`, `tests/review/subagents/test_injection_scanner.py`
  - Pre-commit: `pytest tests/review/subagents/test_injection_scanner.py`

---

- [ ] 5. Implement AuthReviewerAgent

  **What to do**:
  - Create `dawn_kestrel/agents/review/subagents/auth_reviewer.py` (NEW FILE)
  - Implement `AuthReviewerAgent` class:
    - Uses LLM for pattern-based auth code review (JWT/OAuth validation)
    - Uses grep/ast-grep for auth-specific patterns (missing exp check, hardcoded tokens)
    - Combines LLM analysis with tool-based verification

  **Must NOT do**:
  - Don't add OAuth/OAuth2 library integration (out of scope)
  - Don't add session management (focus on code patterns only)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Reason**: Auth code review requires pattern matching PLUS contextual analysis (LLM needed for reasoning about auth flows).
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES (Independent of other Wave 2 agents)
  - **Parallel Group**: Wave 2 (can run with SecretsScannerAgent, InjectionScannerAgent)
  - **Blocks**: Tasks 11-14
  - **Blocked By**: Task 1

  **References**:
  - Pattern References (LLM + tool patterns):
    - `dawn_kestrel/agents/review/fsm_security.py:721-772` - _build_subagent_prompt pattern
  - Production Patterns:
    - Remix auth middleware (multi-layer validation): https://github.com/remix-run/remix/blob/d7bbd9a34dc86fd1fffa03440e07722bd56ffd81/packages/session-middleware/src/lib/session.ts#L12-L40
  - AST patterns for auth code: JWT exp check, token validation

  **WHY Each Reference Matters**:
  - `fsm_security.py:721-772`: Shows how to build prompts with context and tool access
  - Remix session middleware: Production-grade pattern for multi-layer auth validation that should inspire auth code review

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/subagents/test_auth_reviewer.py`
  - [ ] Test covers: LLM analysis + tool pattern matching
  - [ ] Mock test fixtures for auth code scenarios
  - [ ] `pytest tests/review/subagents/test_auth_reviewer.py` → PASS (at least 4 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: AuthReviewerAgent finds missing JWT expiration check
    Tool: Bash
    Preconditions: Test file contains "if verify_token(token):  # No exp check"
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "from dawn_kestrel.agents.review.subagents.auth_reviewer import AuthReviewerAgent; import asyncio; import unittest.mock as mock; orchestrator = mock.Mock(); agent = AuthReviewerAgent(orchestrator, 'session-001'); result = asyncio.run(agent.run_review('test_file.py')); print('Findings:', result.findings); print('Count:', len(result.findings))"
      3. Assert: len(result.findings) > 0
      4. Assert: any('JWT' in f.title and 'expiration' in f.description.lower() for f in result.findings)
      5. Assert: any(f.severity in ['high', 'critical'] for f in result.findings)
    Expected Result: At least one critical/high finding for missing JWT exp check
    Failure Indicators: No findings found, incorrect auth analysis
    Evidence: .sisyphus/evidence/task-5-jwt-exp.json
  ```

  **Commit**: YES (groups with N)
  - Message: `feat(review): Implement AuthReviewerAgent with LLM + pattern analysis`
  - Files: `dawn_kestrel/agents/review/subagents/auth_reviewer.py`, `tests/review/subagents/test_auth_reviewer.py`
  - Pre-commit: `pytest tests/review/subagents/test_auth_reviewer.py`

---

- [ ] 6. Create Tests for Wave 2 Core Agents

  **What to do**:
  - Create comprehensive test suite for specialized agents
  - Test files: `tests/review/subagents/test_secrets_scanner.py`, `test_injection_scanner.py`, `test_auth_reviewer.py`
  - Mock test fixtures for tool outputs (bandit JSON, semgrep JSON, grep output)
  - Test error scenarios (tools not installed, timeouts)

  **Must NOT do**:
  - Don't modify test infrastructure files (pytest.ini, conftest.py)
  - Don't create separate test framework (use existing pytest)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Test file creation following existing patterns in codebase. No specialized domain knowledge needed.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO (Depends on Tasks 3-5)
  - **Parallel Group**: Wave 2 (Sequential)
  - **Blocks**: Tasks 7-14
  - **Blocked By**: Tasks 3-5

  **References**:
  - Test References (existing patterns):
    - `tests/review/agents/test_fsm_security_confidence.py:22-90` - Test structure with pytest async
    - `tests/review/agents/test_fsm_security_dedup.py:32-55` - Mock usage with patch for testing

  **WHY Each Reference Matters**:
  - `test_fsm_security_confidence.py`: Shows pytest async test structure and caplog usage for log verification
  - `test_fsm_security_dedup.py`: Shows how to patch internal functions for testing without breaking encapsulation

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/subagents/test_wave2_agents.py`
  - [ ] Test covers: all 3 core agents (secrets, injection, auth)
  - [ ] Mock fixtures for bandit, semgrep outputs
  - [ ] `pytest tests/review/subagents/test_wave2_agents.py` → PASS (at least 6 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: All core agents pass their tests
    Tool: Bash
    Preconditions: pytest installed, test files exist
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -m pytest tests/review/subagents/test_wave2_agents.py -v
      3. Assert: exit code is 0
      4. Assert: stdout contains "X tests passed" (X >= 6)
      5. Assert: stdout contains "0 failures"
    Expected Result: All tests pass for core agents
    Failure Indicators: Any test fails, exit code non-zero
    Evidence: .sisyphus/evidence/task-6-wave2-tests.json
  ```

  **Commit**: YES (with Tasks 3-5)
  - Message: `test(review): Add tests for core agents (secrets, injection, auth)`
  - Files: `tests/review/subagents/test_wave2_agents.py`
  - Pre-commit: `pytest tests/review/subagents/test_wave2_agents.py`

---

### Wave 3: Additional Security Agents

- [ ] 7. Implement DependencyAuditorAgent

  **What to do**:
  - Create `dawn_kestrel/agents/review/subagents/dependency_auditor.py` (NEW FILE)
  - Implement `DependencyAuditorAgent` class:
    - Uses ToolExecutor to run safety or pip-audit
    - Handles dependency vulnerability checking
    - Normalizes safety/pip-audit output to SecurityFinding format

  **Must NOT do**:
  - Don't add additional package managers (npm, cargo, go mod)
  - Don't implement dependency fix recommendations (only findings)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Reason**: Agent implementing tool execution for dependency checking. No specialized domain knowledge needed.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES (Independent of other Wave 3 agents)
  - **Parallel Group**: Wave 3 (can run with CryptoScannerAgent, ConfigScannerAgent)
  - **Blocks**: Tasks 11-14
  - **Blocked By**: Task 6

  **References**:
  - Pattern References (tool usage):
    - `dawn_kestrel/agents/review/tools.py` - ToolExecutor.execute_tool pattern
  - External References:
    - https://pyup.io/docs/tools/safety/ - Safety CLI usage
    - https://pip-audit.readthedocs.io/ - Pip-audit CLI (if needed)

  **WHY Each Reference Matters**:
  - `tools.py`: ToolExecutor is the new interface for all specialized agents to use
  - Safety docs: Provide production-grade patterns for dependency vulnerability checking

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/subagents/test_dependency_auditor.py`
  - [ ] Test covers: safety execution, output normalization
  - [ ] Mock test fixtures for safety JSON output
  - [ ] `pytest tests/review/subagents/test_dependency_auditor.py` → PASS (at least 3 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: DependencyAuditorAgent finds known vulnerability
    Tool: Bash
    Preconditions: Test requirements.txt contains "requests==2.25.0"
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "from dawn_kestrel.agents.review.subagents.dependency_auditor import DependencyAuditorAgent; import asyncio; import unittest.mock as mock; orchestrator = mock.Mock(); agent = DependencyAuditorAgent(orchestrator, 'session-001'); result = asyncio.run(agent.run_tool('audit_deps', 'requirements.txt')); print('Findings:', result.findings); print('Count:', len(result.findings))"
      3. Assert: len(result.findings) > 0
      4. Assert: any('vulnerability' in f.title.lower() or 'cve' in f.description.lower() for f in result.findings)
      5. Assert: any(f.severity in ['medium', 'high', 'critical'] for f in result.findings)
    Expected Result: At least one medium+ finding for dependency vulnerability
    Failure Indicators: No findings found, incorrect parsing
    Evidence: .sisyphus/evidence/task-7-dep-vuln.json
  ```

  **Commit**: YES (groups with N)
  - Message: `feat(review): Implement DependencyAuditorAgent with real safety execution`
  - Files: `dawn_kestrel/agents/review/subagents/dependency_auditor.py`, `tests/review/subagents/test_dependency_auditor.py`
  - Pre-commit: `pytest tests/review/subagents/test_dependency_auditor.py`

---

- [ ] 8. Implement CryptoScannerAgent

  **What to do**:
  - Create `dawn_kestrel/agents/review/subagents/crypto_scanner.py` (NEW FILE)
  - Implement `CryptoScannerAgent` class:
    - Uses ToolExecutor to run grep/ast-grep for weak crypto patterns
    - Patterns: MD5, SHA1, hardcoded keys, ECB mode, constant-time issues
    - Normalizes grep output to SecurityFinding format

  **Must NOT do**:
  - Don't add crypto library integration (focus on pattern detection only)
  - Don't implement cryptographic fixes (only findings)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Reason**: Agent implementing tool execution for crypto pattern detection. No specialized domain knowledge needed.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES (Independent of DependencyAuditorAgent, ConfigScannerAgent)
  - **Parallel Group**: Wave 3 (can run with DependencyAuditorAgent, ConfigScannerAgent)
  - **Blocks**: Tasks 11-14
  - **Blocked By**: Task 6

  **References**:
  - Pattern References (tool usage):
    - `dawn_kestrel/agents/review/tools.py` - ToolExecutor.execute_tool pattern
  - External References:
    - OWASP cryptographic cheat sheet - https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet

  **WHY Each Reference Matters**:
  - `tools.py`: ToolExecutor is the new interface for all specialized agents to use
  - OWASP cheat sheet: Provides production-grade patterns for weak cryptography detection

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/subagents/test_crypto_scanner.py`
  - [ ] Test covers: grep/ast-grep execution, pattern matching
  - [ ] Mock test fixtures for grep output
  - [ ] `pytest tests/review/subagents/test_crypto_scanner.py` → PASS (at least 3 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: CryptoScannerAgent finds MD5 hash usage
    Tool: Bash
    Preconditions: Test file contains "hashlib.md5(data).hexdigest()"
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "from dawn_kestrel.agents.review.subagents.crypto_scanner import CryptoScannerAgent; import asyncio; import unittest.mock as mock; orchestrator = mock.Mock(); agent = CryptoScannerAgent(orchestrator, 'session-001'); result = asyncio.run(agent.run_tool('scan_crypto', 'test_file.py')); print('Findings:', result.findings); print('Count:', len(result.findings))"
      3. Assert: len(result.findings) > 0
      4. Assert: any('MD5' in f.title or 'md5' in f.evidence.lower() for f in result.findings)
      5. Assert: any(f.severity in ['medium', 'high'] for f in result.findings)
    Expected Result: At least one medium+ finding for MD5 usage
    Failure Indicators: No findings found, incorrect pattern matching
    Evidence: .sisyphus/evidence/task-8-md5-weak.json
  ```

  **Commit**: YES (with Tasks 7-9)
  - Message: `feat(review): Implement CryptoScannerAgent with grep/ast-grep for weak crypto`
  - Files: `dawn_kestrel/agents/review/subagents/crypto_scanner.py`, `tests/review/subagents/test_crypto_scanner.py`
  - Pre-commit: `pytest tests/review/subagents/test_crypto_scanner.py`

---

- [ ] 9. Implement ConfigScannerAgent

  **What to do**:
  - Create `dawn_kestrel/agents/review/subagents/config_scanner.py` (NEW FILE)
  - Implement `ConfigScannerAgent` class:
    - Uses ToolExecutor to run grep for security misconfigurations
    - Patterns: DEBUG=True, test keys in production, insecure defaults, exposed env vars
    - Normalizes grep output to SecurityFinding format

  **Must NOT do**:
  - Don't add config validation beyond pattern detection
  - Don't implement config fixes (only findings)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Reason**: Agent implementing tool execution for config pattern detection. No specialized domain knowledge needed.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES (Independent of DependencyAuditorAgent, CryptoScannerAgent)
  - **Parallel Group**: Wave 3 (can run with DependencyAuditorAgent, CryptoScannerAgent)
  - **Blocks**: Tasks 11-14
  - **Blocked By**: Task 6

  **References**:
  - Pattern References (tool usage):
    - `dawn_kestrel/agents/review/tools.py` - ToolExecutor.execute_tool pattern
  - External References:
    - CIS benchmarks - Security configuration best practices

  **WHY Each Reference Matters**:
  - `tools.py`: ToolExecutor is the new interface for all specialized agents to use
  - CIS benchmarks: Provide production-grade patterns for security misconfiguration detection

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/subagents/test_config_scanner.py`
  - [ ] Test covers: grep execution, pattern matching for misconfigurations
  - [ ] Mock test fixtures for grep output
  - [ ] `pytest tests/review/subagents/test_config_scanner.py` → PASS (at least 3 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: ConfigScannerAgent finds DEBUG=True in settings
    Tool: Bash
    Preconditions: Test settings.py contains "DEBUG = True"
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -c "from dawn_kestrel.agents.review.subagents.config_scanner import ConfigScannerAgent; import asyncio; import unittest.mock as mock; orchestrator = mock.Mock(); agent = ConfigScannerAgent(orchestrator, 'session-001'); result = asyncio.run(agent.run_tool('scan_config', 'settings.py')); print('Findings:', result.findings); print('Count:', len(result.findings))"
      3. Assert: len(result.findings) > 0
      4. Assert: any('DEBUG' in f.title or 'debug' in f.evidence.lower() for f in result.findings)
      5. Assert: any(f.severity in ['medium', 'high'] for f in result.findings)
    Expected Result: At least one medium+ finding for DEBUG enabled
    Failure Indicators: No findings found, incorrect pattern matching
    Evidence: .sisyphus/evidence/task-9-debug-config.json
  ```

  **Commit**: YES (with Tasks 7-9)
  - Message: `feat(review): Implement ConfigScannerAgent with grep for security misconfigurations`
  - Files: `dawn_kestrel/agents/review/subagents/config_scanner.py`, `tests/review/subagents/test_config_scanner.py`
  - Pre-commit: `pytest tests/review/subagents/test_config_scanner.py`

---

- [ ] 10. Create Tests for Wave 3 Additional Agents

  **What to do**:
  - Create comprehensive test suite for Wave 3 agents
  - Test files: `tests/review/subagents/test_dependency_auditor.py`, `test_crypto_scanner.py`, `test_config_scanner.py`
  - Mock test fixtures for tool outputs (safety JSON, grep output)
  - Test error scenarios (tools not installed, timeouts)

  **Must NOT do**:
  - Don't modify test infrastructure files (pytest.ini, conftest.py)
  - Don't create separate test framework (use existing pytest)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Test file creation following existing patterns in codebase. No specialized domain knowledge needed.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO (Depends on Tasks 7-9)
  - **Parallel Group**: Wave 3 (Sequential)
  - **Blocks**: Tasks 11-14
  - **Blocked By**: Tasks 7-9

  **References**:
  - Test References (existing patterns):
    - `tests/review/agents/test_fsm_security_confidence.py:22-90` - Test structure with pytest async
    - `tests/review/agents/test_fsm_security_dedup.py:25-80` - Mock usage with patch for testing

  **WHY Each Reference Matters**:
  - `test_fsm_security_confidence.py`: Shows pytest async test structure and caplog usage for log verification
  - `test_fsm_security_dedup.py`: Shows how to patch internal functions for testing without breaking encapsulation

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/subagents/test_wave3_agents.py`
  - [ ] Test covers: all 3 additional agents (dep, crypto, config)
  - [ ] Mock fixtures for safety, grep outputs
  - [ ] `pytest tests/review/subagents/test_wave3_agents.py` → PASS (at least 6 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: All Wave 3 agents pass their tests
    Tool: Bash
    Preconditions: pytest installed, test files exist
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -m pytest tests/review/subagents/test_wave3_agents.py -v
      3. Assert: exit code is 0
      4. Assert: stdout contains "X tests passed" (X >= 6)
      5. Assert: stdout contains "0 failures"
    Expected Result: All tests pass for Wave 3 agents
    Failure Indicators: Any test fails, exit code non-zero
    Evidence: .sisyphus/evidence/task-10-wave3-tests.json
  ```

  **Commit**: YES (with Tasks 7-9)
  - Message: `test(review): Add tests for Wave 3 agents (dep, crypto, config)`
  - Files: `tests/review/subagents/test_wave3_agents.py`
  - Pre-commit: `pytest tests/review/subagents/test_wave3_agents.py`

---

### Wave 4: Integration

- [ ] 11. Implement Dynamic Todo Generator (LLM-powered)

  **What to do**:
  - Create `SecurityReviewerAgent._create_dynamic_todos()` method (REPLACE _create_initial_todos)
  - Logic:
    - **Rule-based layer** (preserve current approach):
      - File-type classification (Python vs JS vs config)
      - Risk-based prioritization:
        - Auth files → HIGH priority auth review
        - Dependency files → HIGH priority dependency audit
        - Config files → HIGH priority config scan
      - Resource-aware scaling:
        - Small diff (< 100 lines) → limit parallel agents to 2
        - Medium diff (100-1000 lines) → limit to 4 agents
        - Large diff (> 1000 lines) → limit to 6 agents
    - Preserve existing _create_initial_todos() as fallback for patterns not covered by rules
  - **LLM-powered discovery layer** (NEW):
      - Analyze changed files for unexpected security patterns
      - Propose context-aware todos not covered by rules
      - Prioritize findings from previous iterations
      - Create dynamic agent pool for unforeseen situations
  - Integration: Combine with existing _create_initial_todos()

  **Must NOT do**:
  - Don't add machine learning for confidence scoring (LLM provides analysis, not scores)
  - Don't change todo schema (SecurityTodo)
  - Don't add adaptive prioritization beyond rule-based + LLM analysis

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Reason**: Method implementation following existing patterns. No specialized domain knowledge needed.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO (Depends on Tasks 12-13)
  - **Parallel Group**: Wave 4 (Sequential)
  - **Blocks**: Task 14
  - **Blocked By**: Tasks 7-10

  **References**:
  - Pattern References (existing todo creation):
    - `dawn_kestrel/agents/review/fsm_security.py:450-667` - _create_initial_todos() structure
  - API/Type References:
    - `dawn_kestrel/agents/review/fsm_security.py:133-155` - SecurityTodo dataclass

  **WHY Each Reference Matters**:
  - `fsm_security.py:450-667`: Shows how to create SecurityTodo objects with specific priorities and agent assignments
  - `fsm_security.py:133-155`: Defines SecurityTodo dataclass structure to understand fields

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/fsm_security/test_dynamic_todos.py`
  - [ ] Test covers: Python file classification, auth prioritization, config prioritization, resource scaling
  - [ ] Mock git context with changed files
  - [ ] `pytest tests/review/fsm_security/test_dynamic_todos.py` → PASS (at least 4 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Dynamic todo generation prioritizes auth files
    Tool: Bash
    Preconditions: Test git diff contains Python files with "auth/" in paths
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -m pytest tests/review/fsm_security/test_dynamic_todos.py::TestDynamicTodos::test_auth_files_high_priority -v
      3. Assert: test passes (exit code 0)
      4. Assert: todo list contains "Review authentication and authorization code" with HIGH priority
    Expected Result: High-priority auth review todo generated for auth files
    Failure Indicators: No auth prioritization, wrong priority level
    Evidence: .sisyphus/evidence/task-11-dynamic-auth-priority.json
  ```

  **Commit**: YES (with Tasks 12-13)
  - Message: `feat(review): Implement dynamic todo generator with risk-based prioritization`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`
  - Pre-commit: `pytest tests/review/fsm_security/test_dynamic_todos.py`

---

- [ ] 12. Update SecurityReviewerAgent to Use Real Subagents

  **What to do**:
  - Update `SecurityReviewerAgent._delegate_investigation_tasks()`:
    - Remove `create_agent_task()` call (now use specialized agents directly)
    - Remove `_simulate_subagent_execution()` call
    - Call specialized agent's `run_tool()` or `run_review()` methods
    - Pass tool results through existing review logic

  **Must NOT do**:
  - Don't change FSM transitions or state handlers
  - Don't modify finding review/assessment logic
  - Don't remove confidence thresholding

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Reason**: Refactoring existing method to use new specialized agents. No specialized domain knowledge needed.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES (Independent of Task 11)
  - **Parallel Group**: Wave 4 (can run with Task 11)
  - **Blocks**: Tasks 13-14
  - **Blocked By**: Tasks 1-10

  **References**:
  - Pattern References (existing delegation):
    - `dawn_kestrel/agents/review/fsm_security.py:669-746` - _delegate_investigation_tasks() structure
    - `dawn_kestrel/agents/review/fsm_security.py:696-731` - create_agent_task usage
  - Agent Integration References:
    - `dawn_kestrel/agents/runtime.py` - AgentRuntime.execute_agent() method

  **WHY Each Reference Matters**:
  - `fsm_security.py:669-746`: Shows how to create SubagentTask and delegate to subagents
  - `fsm_security.py:696-731`: Shows current pattern of creating tasks via create_agent_task
  - `runtime.py`: Shows how AgentRuntime executes agents (new pattern to follow)

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file updated: `tests/review/fsm_security/test_real_delegation.py`
  - [ ] Test covers: real agent execution through SecurityReviewerAgent
  - [ ] Mock specialized agent outputs
  - [ ] Verify FSM transitions still work with real execution
  - [ ] `pytest tests/review/fsm_security/test_real_delegation.py` → PASS (at least 3 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: SecurityReviewerAgent delegates to SecretsScannerAgent
    Tool: Bash
    Preconditions: SecurityReviewerAgent configured with real AgentRuntime, test file with secrets
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -m pytest tests/review/fsm_security/test_real_delegation.py::TestRealDelegation::test_delegates_to_secrets_scanner -v
      3. Assert: test passes (exit code 0)
      4. Assert: SecretsScannerAgent.run_tool() was called
      5. Assert: findings were aggregated in SecurityReviewerAgent
    Expected Result: Real delegation to SecretsScannerAgent works
    Failure Indicators: Delegation fails, no findings returned, FSM broken
    Evidence: .sisyphus/evidence/task-12-delegation-secrets.json
  ```

  **Commit**: YES (with Tasks 12-14)
  - Message: `refactor(review): Update SecurityReviewerAgent to use real subagent delegation`
  - Files: `dawn_kestrel/agents/review/fsm_security.py`, `tests/review/fsm_security/test_real_delegation.py`
  - Pre-commit: `pytest tests/review/fsm_security/test_real_delegation.py`

---

- [ ] 13. Update fsm_cli.py to Use Real AgentRuntime

  **What to do**:
  - Update `fsm_cli.py:383-388`:
    - Remove `Mock(spec=AgentRuntime)` usage
    - Import real `AgentRuntime` from `dawn_kestrel.agents.runtime`
    - Pass real runtime to `SecurityReviewerAgent`
    - Remove all mock imports and usage

  **Must NOT do**:
  - Don't change CLI interface or commands
  - Don't add runtime configuration options
  - Don't modify orchestrator pattern

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Reason**: Simple refactoring to use real runtime instead of mock. No specialized domain knowledge needed.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES (Independent of Task 11)
  - **Parallel Group**: Wave 4 (can run with Task 11)
  - **Blocks**: Tasks 14
  - **Blocked By**: Tasks 1-10

  **References**:
  - Pattern References (CLI integration):
    - `dawn_kestrel/agents/review/fsm_cli.py:383-404` - Current mock usage
  - Runtime References:
    - `dawn_kestrel/agents/runtime.py` - AgentRuntime interface

  **WHY Each Reference Matters**:
  - `fsm_cli.py:383-404`: Shows current pattern of using Mock for AgentRuntime
  - `runtime.py`: Shows AgentRuntime interface for real execution

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file updated: `tests/cli/test_fsm_cli_real_runtime.py`
  - [ ] Test covers: real AgentRuntime passed to SecurityReviewerAgent
  - [ ] Verify no mock usage remains
  - [ ] `pytest tests/cli/test_fsm_cli_real_runtime.py` → PASS (at least 2 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: CLI uses real AgentRuntime
    Tool: Bash
    Preconditions: AgentRuntime configured, test repo available
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. dawn-kestrel fsm-security review --repo-root ./test-repo --base-ref main --head-ref feature
      3. Assert: command completes (exit code 0)
      4. Assert: output contains findings from real tools (not "Simulated" in logs)
      5. Assert: no mock references in stderr
    Expected Result: CLI uses real AgentRuntime for security review
    Failure Indicators: CLI uses mock, execution fails
    Evidence: .sisyphus/evidence/task-13-cli-real-runtime.json
  ```

  **Commit**: YES (with Tasks 12-14)
  - Message: `refactor(cli): Replace mock AgentRuntime with real AgentRuntime`
  - Files: `dawn_kestrel/agents/review/fsm_cli.py`, `tests/cli/test_fsm_cli_real_runtime.py`
  - Pre-commit: `pytest tests/cli/test_fsm_cli_real_runtime.py`

---

- [ ] 14. Create Integration Tests for Full Workflow

  **What to do**:
  - Create comprehensive integration test suite:
    - Test file: `tests/review/integration/test_full_security_review.py`
    - End-to-end test: real tools → real agents → dynamic review → final assessment
    - Test with real test repo containing vulnerabilities
    - Verify all FSM transitions work with real execution

  **Must NOT do**:
  - Don't use tool mocks (use real tool execution)
  - Don't mock agent responses (use real LLM calls if configured)
  - Don't test individual components only (test integration)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Integration tests require understanding of full workflow. Multiple components and data flow.
  - **Skills**: [`napkin`]
  - **Skills Evaluated but Omitted**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO (Depends on ALL previous tasks)
  - **Parallel Group**: Wave 4 (Sequential - final task)
  - **Blocks**: None (can start after all waves complete)

  **References**:
  - Test References (existing test patterns):
    - `tests/review/agents/test_fsm_security_confidence.py:22-90` - Test structure with pytest async
    - `tests/review/agents/test_fsm_security_dedup.py:25-80` - Mock usage for testing
  - Production Pattern References:
    - Remix auth tests (multi-step verification): https://github.com/remix-run/remix/blob/d7bbd9a34dc86fd1fffa03440e07722bd56ffd81/demos/bookstore/app/auth.test.ts#L25-L48
    - XState guard tests (error handling): https://github.com/statelyai/xstate/blob/555fcd915fd708ca82173fe065375163b04f732d/packages/core/test/guards.test.ts#L864-L895

  **WHY Each Reference Matters**:
  - `test_fsm_security_confidence.py`: Shows pytest async test structure for integration tests
  - Remix auth tests: Production-grade pattern for multi-step authentication testing that should inspire integration test design
  - XState guard tests: Production-grade pattern for guard failure testing that should inspire error scenario testing

  **Acceptance Criteria**:

  **If TDD (tests enabled)**:
  - [ ] Test file created: `tests/review/integration/test_full_security_review.py`
  - [ ] Test covers: end-to-end security review with real tools
  - [ ] Test with vulnerable test repo
  - [ ] Verify FSM transitions with real execution
  - [ ] Verify confidence thresholding applies to real findings
  - [ ] `pytest tests/review/integration/test_full_security_review.py` → PASS (at least 2 tests, 0 failures)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: End-to-end security review completes with real tools and produces assessment
    Tool: Bash
    Preconditions: Test repo with Python files containing vulnerabilities (SQLi, XSS, weak crypto, DEBUG=True)
    Steps:
      1. cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
      2. python -m pytest tests/review/integration/test_full_security_review.py::TestFullSecurityReview::test_e2e_review_with_real_tools -v
      3. Assert: test passes (exit code 0)
      4. Assert: overall severity is critical or high
      5. Assert: findings count > 0
      6. Assert: all findings have real evidence (not "Simulated")
      7. Assert: confidence threshold filtered findings
      8. Assert: no mock/simulation logs present
    Expected Result: Complete security review with real findings from multiple tools
    Failure Indicators: Review incomplete, wrong severity, simulated findings present
    Evidence: .sisyphus/evidence/task-14-e2e-real-tools.json
  ```

  **Commit**: YES (with Task 14)
  - Message: `test(review): Add end-to-end integration tests for full security review workflow`
  - Files: `tests/review/integration/test_full_security_review.py`
  - Pre-commit: `pytest tests/review/integration/test_full_security_review.py`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 2 | `feat(review): Add ToolExecutor component with normalization` | `dawn_kestrel/agents/review/tools.py` | `pytest tests/review/tools/` |
| 6 | `test(review): Add tests for core agents (secrets, injection, auth)` | `tests/review/subagents/test_wave2_agents.py` | `pytest tests/review/subagents/` |
| 10 | `feat(review): Add tests for Wave 3 agents (dep, crypto, config)` | `tests/review/subagents/test_wave3_agents.py` | `pytest tests/review/subagents/` |
| 12 | `refactor(review): Update SecurityReviewerAgent to use real subagents` | `dawn_kestrel/agents/review/fsm_security.py` | `pytest tests/review/fsm_security/test_real_delegation.py` |
| 13 | `refactor(cli): Replace mock AgentRuntime with real runtime` | `dawn_kestrel/agents/review/fsm_cli.py` | `pytest tests/cli/test_fsm_cli_real_runtime.py` |
| 14 | `feat(review): Implement dynamic todo generator with risk-based prioritization` | `dawn_kestrel/agents/review/fsm_security.py` | `pytest tests/review/fsm_security/test_dynamic_todos.py` |

---

## Success Criteria

### Verification Commands

```bash
# Verify all tools work with real test repo
cd /Users/parkersligting/develop/pt/worktrees/harness-agent-rework
python -m pytest tests/review/ -v

# Verify end-to-end integration
python -m pytest tests/review/integration/ -v

# Verify existing tests still pass
python -m pytest tests/review/agents/ -v
```

### Final Checklist

- [ ] All specialized agents execute real tools (no hardcoded findings)
- [ ] ToolExecutor handles missing tools gracefully with clear logging
- [ ] Dynamic review generates adaptive todos based on context
- [ ] All existing tests pass (confidence, dedup, logging tests)
- [ ] New tests cover tool execution, normalization, and error scenarios
- [ ] FSM state machine works with real execution (same transitions preserved)
- [ ] Confidence thresholding still applies to tool-generated findings
- [ ] Deduplication prevents duplicate findings from real tools
- [ ] CLI uses real AgentRuntime (no mocks)
- [ ] End-to-end integration tests pass (full workflow with real tools)
- [ ] Production-grade error handling based on XState/Remix patterns
- [ ] All acceptance criteria met for every task
