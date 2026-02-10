# Dawn Kestrel SDK Comprehensive Refactor

## TL;DR

> **Quick Summary**: Complete architectural refactoring of dawn_kestrel SDK (32K lines, 11 major modules) to eliminate blast exposure and apply 20+ design patterns for excellent composition and easy feature addition.
>
> **Deliverables**:
> - Dependency Injection Container replacing imperative wiring
> - Plugin system using Python entry_points for tools/providers/agents
> - Result/Railway pattern for explicit error handling
> - Repository + Unit of Work for storage abstraction
> - Adapter + Facade patterns for simplified extension
> - Command + State (FSM) for workflow orchestration
> - Strategy + Mediator for flexible coordination
> - Decorator/Proxy + Null Object for cross-cutting concerns
> - Circuit Breaker + Bulkhead + Retry for reliability
> - Configuration Object replacing singleton
> - Complete documentation with upgrade paths
>
> **Estimated Effort**: XL (50+ major tasks across multiple phases)
> **Parallel Execution**: YES - Multiple waves (independent pattern implementations)
> **Critical Path**: DI Container → Plugin System → Result Pattern → Repository → All other patterns

---

## Context

### Original Request

Refactor dawn_kestrel SDK to ensure:
- Excellent composition of objects and variables
- Limits blast exposure when changes happen
- Apply all relevant design patterns for easy feature addition
- **Most importantly: ensure it works**

### Interview Summary

**Key Discussions**:
- **Blast exposure**: All three areas need improvement (agents, tools, providers)
- **Verification strategy**: Regression tests + integration tests + manual verification + upgrade docs
- **API compatibility**: Breaking changes acceptable, must document upgrade paths
- **Development workflow**: Comprehensive refactor (entire SDK at once) - user's explicit decision
- **Pattern priority**: Apply ALL relevant design patterns from catalog
- **DI approach**: Use existing library (not build from scratch)
- **Plugin discovery**: Python entry_points for extensibility

**User's Explicit Decision**: One massive plan - complete comprehensive refactor in single work plan (NOT phased)

**Metis Review Findings**:

**Identified Gaps** (addressed in plan):
- Monolithic refactor risk: HIGH - addressed with robust test checkpoints and rollback strategy
- Test coverage blind spots: Medium - addressed with baseline coverage and expansion
- Pattern composability: Medium - addressed with careful dependency ordering and integration tests
- Performance degradation: Low-Medium - addressed with lazy DI initialization and caching
- Developer experience: Low-Medium - addressed with facade pattern and migration guide

**Metis Recommendations** (incorporated):
- Strongly recommended phased approach, but user chose monolithic - plan includes checkpoints as compromise
- Use dependency-injector library (mature, feature-rich)
- Establish baseline test coverage before any changes
- Verify test suite passes at every checkpoint
- Preserve backward compatibility for critical APIs
- Document all new patterns with examples
- Create migration guide for breaking changes

### Research Findings

**Architecture Analysis**:
- Composition root: OpenCodeAsyncClient (sdk/client.py) directly instantiates everything
- Current patterns: Partial DI (handlers), Registry/Factory, Builder, Event-driven
- Missing patterns: DI Container, Plugin system, Result, Repository, Unit of Work, Command, State (FSM), Mediator, Adapter, Facade, Decorator/Proxy, Null Object, Circuit Breaker, Bulkhead, Retry, Configuration Object

**Test Infrastructure**:
- Framework: PyTest with pytest-asyncio
- Config: pyproject.toml with coverage enabled
- Current patterns: Heavy use of Mock/AsyncMock, async testing with @pytest.mark.asyncio
- Coverage: Well-covered (SDK clients, core models, agent lifecycle, UI/TUI)
- Strategy: TDD for refactor, existing tests as regression suite

**Blast Exposure** (from composition analysis):
1. Tool Registration: Hard-coded in tools/__init__.py (2 files per change)
2. Provider Registration: Static factory map in providers/__init__.py (2 files per change)
3. Built-in Agent Registration: Seeded statically from builtin.py
4. Global Settings Singleton: Used throughout codebase
5. Composition Root: Direct instantiation, no separation of concerns

### Metis Review (Continued)

**Additional Gaps Identified**:
- Error handling: Custom exceptions scattered, no explicit Ok/Err/Pass types
- Storage: No Repository abstraction, no transactional consistency
- Coordination: No centralized mediator for complex interactions
- Cross-cutting: Logging/metrics not uniformly applied
- Reliability: No circuit breaker, retry, or rate limiting for LLM calls
- Documentation: No pattern documentation, no migration guide

**Applied in Plan**:
- All gaps incorporated as pattern implementations
- Checkpoints defined to verify functionality after major pattern groups
- Rollback strategy included (feature flags + git revert option)
- Acceptance criteria include all critical paths and backward compatibility

---

## Work Objectives

### Core Objective

Comprehensive refactoring of dawn_kestrel SDK to achieve excellent composition through dependency injection and design patterns, eliminate blast exposure for adding features (agents, tools, providers), and ensure system remains fully functional with complete documentation for upgrade paths.

### Concrete Deliverables

1. **Dependency Injection Container**: Replace imperative wiring in OpenCodeAsyncClient.__init__ with formal DI container
2. **Plugin System**: Python entry_points-based discovery for tools, providers, agents
3. **Result Pattern**: Ok/Err/Pass types throughout codebase replacing exceptions
4. **Repository Pattern**: Storage abstraction layer with session/message/part repositories
5. **Unit of Work**: Transactional consistency for multi-write session operations
6. **Adapter Pattern**: Provider and tool adapters enabling extension without core edits
7. **Facade Pattern**: Simplified composition root over multiple subsystems
8. **Command Pattern**: Encapsulated actions with provenance and orchestration
9. **State (FSM)**: Explicit agent/workflow phases with valid transitions
10. **Strategy Pattern**: Swappable algorithms (storage backends, routing, retry policies)
11. **Mediator Pattern**: Centralized coordination for component interactions
12. **Decorator/Proxy**: Cross-cutting concerns (logging, metrics, caching, auth checks)
13. **Null Object**: Optional dependencies without None checks (telemetry, notifier)
14. **Circuit Breaker**: LLM call reliability, prevent cascading failures
15. **Bulkhead**: Resource isolation for multiple dependencies
16. **Retry + Backoff**: Transient failure handling with bounded retries
17. **Configuration Object**: Replace global Settings singleton with proper Pydantic model
18. **Registry/Plugin**: Dynamic extensibility without editing core dispatch logic
19. **Observer**: Event handling with pub/sub for domain/application events
20. **Composite**: Plan trees for validation, metrics, rendering
21. **Documentation**: Complete pattern documentation and migration guide

### Definition of Done

- [ ] All 21 design patterns implemented and integrated
- [ ] All tests pass (pytest exit code 0)
- [ ] Coverage at or above baseline (compare with pre-refactor baseline)
- [ ] All critical paths verified (SDK client, storage, agent runtime, CLI, TUI)
- [ ] All patterns documented in docs/patterns.md
- [ ] Migration guide (MIGRATION.md) complete with breaking changes
- [ ] Backward compatibility maintained for critical APIs (or documented deprecations)
- [ ] Type checking passes (mypy exit code 0)
- [ ] Linting passes (ruff check exit code 0)
- [ ] End-to-end workflow tests pass

### Must Have

- Dependency injection container using existing Python library
- Plugin discovery via Python entry_points
- Result pattern replacing exceptions in domain layer
- All critical APIs backward compatible (or with clear deprecation warnings)
- Comprehensive tests (unit + integration) for all refactored components
- Complete documentation for all patterns
- Migration guide for breaking changes

### Must NOT Have (Guardrails)

- [ ] Direct instantiation of concrete classes in composition root (all via DI)
- [ ] Hard-coded tool/provider/agent lists (all via plugin discovery)
- [ ] Global Settings singleton (replaced with Configuration Object)
- [ ] Unchecked exceptions (all domain errors via Result pattern)
- [ ] Direct storage access without Repository abstraction
- [ ] Multi-write operations without Unit of Work
- [ ] Unclear agent/workflow phases (explicit State/FSM)
- [ ] Inconsistent cross-cutting concerns (all via Decorator/Proxy)
- [ ] Plugin registration requiring core edits (all via entry_points)
- [ ] Missing documentation for any pattern or breaking change

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> This is NOT conditional — it applies to EVERY task, regardless of test strategy.

### Test Decision

- **Infrastructure exists**: YES (PyTest with pytest-asyncio)
- **Automated tests**: YES (TDD - RED-GREEN-REFACTOR for all refactored code)
- **Framework**: pytest with pytest-asyncio

### Baseline Establishment (MANDATORY - BEFORE any code changes)

```bash
# Task: Establish baseline test coverage
pytest -xvs --cov=dawn_kestrel --cov-report=term-missing --cov-report=html
# Capture baseline to .sisyphus/baseline_coverage.txt
# Expected: All tests pass, coverage report generated
# Evidence: .sisyphus/baseline_coverage.txt, htmlcov/index.html
```

### TDD Workflow (MANDATORY for all refactor tasks)

**Task Structure:**
1. **RED**: Write failing test first
   - Test file: [module]/[module]_test.py
   - Test command: `pytest tests/[path]/[module]_test.py -v`
   - Expected: FAIL (test exists, refactored code doesn't)
2. **GREEN**: Implement minimum code to pass
   - Command: `pytest tests/[path]/[module]_test.py -v`
   - Expected: PASS
3. **REFACTOR**: Clean up while keeping green
   - Command: `pytest tests/[path]/[module]_test.py -v`
   - Expected: PASS (still)

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

**Verification Tool by Deliverable Type:**

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| **DI/Composition** | Bash (python -c) | Import client, verify DI container resolves dependencies |
| **Plugin System** | Bash (python -c) | Check entry_points groups, verify plugins load |
| **Result Pattern** | Bash (python -c) | Call functions, assert Result types returned |
| **Storage/Repository** | Bash (python -c) | Create/retrieve sessions, verify Repository abstraction |
| **CLI** | Bash (dawn-kestrel) | Run commands, check help, verify execution |
| **TUI** | Bash (python -c) | Import app, verify initialization without UI |
| **API Endpoints** | Bash (curl/httpie) | Call SDK methods, verify responses |

**Each Scenario MUST Follow This Format:**

```
Scenario: [Descriptive name — what functionality is being verified]
  Tool: [Bash / curl / interactive_bash / Playwright]
  Preconditions: [What must be true before this scenario runs]
  Steps:
    1. [Exact action with specific command/selector/endpoint]
    2. [Next action with expected intermediate state]
    3. [Assertion with exact expected value]
  Expected Result: [Concrete, observable outcome]
  Failure Indicators: [What would indicate failure]
  Evidence: [Screenshot path / output capture / response body path]
```

---

## Execution Strategy

### Parallel Execution Waves

> Maximize throughput by grouping independent pattern implementations into parallel waves.
> Each wave completes before the next begins.

```
Wave 1 (Foundation - Start Immediately):
├── Task 1: Establish baseline test coverage
├── Task 2: Setup DI container (dependency-injector)
├── Task 3: Replace Settings singleton with Configuration Object
└── Task 4: Design plugin discovery system (entry_points)

Wave 2 (Plugin System - After Wave 1):
├── Task 5: Implement tool plugin discovery
├── Task 6: Implement provider plugin discovery
├── Task 7: Implement agent plugin discovery
└── Task 8: Register all built-in tools/providers/agents as plugins

Wave 3 (Error Handling - After Wave 2):
├── Task 9: Implement Result pattern (Ok/Err/Pass)
├── Task 10: Wrap existing exceptions with Result types
└── Task 11: Update all public APIs to return Results

Wave 4 (Storage & State - After Wave 3):
├── Task 12: Implement Repository pattern (session/message/part)
├── Task 13: Implement Unit of Work for transactions
├── Task 14: Implement State (FSM) for agent lifecycle
└── Task 15: Refactor storage layer to use Repository

Wave 5 (Coordination & Extension - After Wave 4):
├── Task 16: Implement Adapter pattern for providers
├── Task 17: Implement Adapter pattern for tools
├── Task 18: Implement Facade for composition root
├── Task 19: Implement Mediator for event coordination
└── Task 20: Implement Command pattern for actions

Wave 6 (Cross-Cutting - After Wave 5):
├── Task 21: Implement Decorator/Proxy for logging
├── Task 22: Implement Decorator/Proxy for metrics
├── Task 23: Implement Decorator/Proxy for caching
├── Task 24: Implement Null Object for optional deps
└── Task 25: Implement Strategy pattern for swappable algos

Wave 7 (Reliability - After Wave 6):
├── [x] Task 26: Implement Circuit Breaker for LLM calls
├── Task 27: Implement Bulkhead for resource isolation
├── Task 28: Implement Retry + Backoff for transient failures
├── Task 29: Implement Rate Limiter for API calls
└── Task 30: Apply reliability patterns uniformly

Wave 8 (Final Integration - After Wave 7):
├── Task 31: Refactor composition root to use DI container
├── Task 32: Update CLI to use new APIs
├── Task 33: Update TUI to use new APIs
├── Task 34: Comprehensive integration tests
├── Task 35: Documentation (patterns + migration)
└── Task 36: Final verification and cleanup

Critical Path: Wave 1 → Wave 2 → Wave 3 → Wave 4 → Wave 5 → Wave 6 → Wave 7 → Wave 8
Parallel Speedup: ~40% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2-36 | None (must start first) |
| 2 | 1 | 5-36 | 3, 4 |
| 3 | 1 | 4-36 | 2 |
| 4 | 1 | 5-36 | 2, 3 |
| 5 | 2, 3, 4 | 6-36 | 6, 7, 8 |
| 6 | 2, 3, 4 | 7-36 | 5, 7, 8 |
| 7 | 2, 3, 4 | 8-36 | 5, 6, 8 |
| 8 | 2, 3, 4 | 9-36 | 5, 6, 7 |
| 9 | 5, 6, 7, 8 | 10-36 | 10, 11 |
| 10 | 9 | 11-36 | 11 |
| 11 | 9, 10 | 12-36 | None (sequential) |
| 12 | 11 | 13-36 | 13, 14, 15 |
| 13 | 11 | 14-36 | 12, 14, 15 |
| 14 | 11 | 15-36 | 12, 13, 15 |
| 15 | 12, 13, 14 | 16-36 | None (sequential) |
| 16 | 15 | 17-36 | 17, 18, 19 |
| 17 | 15 | 18-36 | 16, 18, 19 |
| 18 | 15 | 19-36 | 16, 17, 19 |
| 19 | 15 | 20-36 | 16, 17, 18, 20 |
| 20 | 16, 17, 18, 19 | 21-36 | None (sequential) |
| 21 | 20 | 22-36 | 22, 23, 24, 25 |
| 22 | 20 | 23-36 | 21, 23, 24, 25 |
| 23 | 20 | 24-36 | 21, 22, 24, 25 |
| 24 | 20 | 25-36 | 21, 22, 23, 25 |
| 25 | 20 | 26-36 | 21, 22, 23, 24 |
| 26 | 25 | 27-36 | 27, 28, 29, 30 |
| 27 | 25 | 28-36 | 26, 28, 29, 30 |
| 28 | 25 | 29-36 | 26, 27, 29, 30 |
| 29 | 25 | 30-36 | 26, 27, 28, 30 |
| 30 | 25 | 31-36 | 26, 27, 28, 29 |
| 31 | 26, 27, 28, 29, 30 | 32-36 | 32, 33 |
| 32 | 31 | 34-36 | 33 |
| 33 | 31 | 34-36 | 32 |
| 34 | 32, 33 | 35-36 | 35 |
| 35 | 34 | 36 | None (sequential) |
| 36 | 35 | None | None (final task) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2, 3, 4 | task(category="quick", load_skills=["git-master"], run_in_background=false) |
| 2 | 5, 6, 7, 8 | task(category="quick", load_skills=["git-master"], run_in_background=false) |
| 3 | 9, 10, 11 | task(category="quick", load_skills=["git-master"], run_in_background=false) |
| 4 | 12, 13, 14, 15 | task(category="unspecified-low", load_skills=["git-master"], run_in_background=false) |
| 5 | 16, 17, 18, 19, 20 | task(category="unspecified-high", load_skills=["git-master"], run_in_background=false) |
| 6 | 21, 22, 23, 24, 25 | task(category="unspecified-high", load_skills=["git-master"], run_in_background=false) |
| 7 | 26, 27, 28, 29, 30 | task(category="quick", load_skills=["git-master"], run_in_background=false) |
| 8 | 31, 32, 33, 34, 35, 36 | task(category="unspecified-high", load_skills=["git-master"], run_in_background=false) |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info.

### Wave 1: Foundation

- [x] 1. Establish Baseline Test Coverage

  **What to do**:
  - Run full test suite with coverage
  - Save baseline to .sisyphus/baseline_coverage.txt
  - Verify all tests pass
  - Document under-tested modules for expansion

  **Must NOT do**:
  - Modify any code before establishing baseline

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Simple command execution, no code changes
  - **Skills**: [`git-master`]
    - `git-master`: For running git commands to establish baseline
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (must start first)
  - **Blocks**: Tasks 2-36 (all dependent on baseline)
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Test Infrastructure** (existing setup):
  - `pyproject.toml:84-87` - PyTest configuration with coverage enabled
  - `tests/conftest.py` - Fixtures for UI tests

  **Execution Commands**:
  - Official docs: `https://docs.pytest.org/` - pytest coverage options

  **WHY Each Reference Matters**:
  - Understanding test configuration ensures baseline is captured correctly
  - PyTest docs show proper coverage command syntax

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: Baseline test suite runs successfully
    Tool: Bash (pytest)
    Preconditions: No code changes made yet
    Steps:
      1. Run: pytest -xvs --cov=dawn_kestrel --cov-report=term-missing --cov-report=html
      2. Capture: stdout contains "=== test session starts ==="
      3. Capture: Exit code is 0
    Expected Result: All tests pass, coverage reports generated
    Failure Indicators: Exit code != 0, coverage report errors
    Evidence: .sisyphus/baseline_coverage.txt, htmlcov/index.html

  Scenario: Under-tested modules identified
    Tool: Bash (grep + manual review)
    Preconditions: Baseline coverage report generated
    Steps:
      1. Run: grep -A 2 "dawn_kestrel" htmlcov/index.html | grep "0%"
      2. Review: List of modules with 0% coverage
      3. Document: Add to .sisyphus/drafts/coverage-gaps.md
    Expected Result: List of under-tested modules documented
    Failure Indicators: Coverage report not readable
    Evidence: .sisyphus/drafts/coverage-gaps.md
  ```

  **Evidence to Capture**:
  - [ ] Baseline coverage report: .sisyphus/baseline_coverage.txt
  - [ ] HTML coverage report: htmlcov/index.html
  - [ ] Coverage gaps document: .sisyphus/drafts/coverage-gaps.md

  **Commit**: NO (baseline only)

- [x] 2. Setup DI Container (dependency-injector)

  **What to do**:
  - Install dependency-injector library
  - Create dawn_kestrel/core/di_container.py with Container setup
  - Define service interfaces and bindings
  - Implement lazy initialization for performance
  - Create factory functions for container wiring

  **Must NOT do**:
  - Refactor existing composition root yet (next task)
  - Break existing tests without updating them

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: DI container setup is straightforward but foundational
  - **Skills**: [`git-master`]
    - `git-master`: For managing package installation and dependencies
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on baseline)
  - **Parallel Group**: Wave 1 (with Tasks 3, 4)
  - **Blocks**: Tasks 5-36
  - **Blocked By**: Task 1 (must establish baseline first)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **DI Library Documentation** (external reference):
  - Official docs: `https://python-dependency-injector.ets-labs.org/` - dependency-injector usage patterns

  **Current Composition** (code to understand):
  - `dawn_kestrel/sdk/client.py:45-90` - OpenCodeAsyncClient.__init__ shows current wiring
  - `dawn_kestrel/agents/runtime.py` - AgentRuntime shows how dependencies are currently used

  **Python Packaging** (for entry_points later):
  - Official docs: `https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins.html` - entry_points configuration

  **WHY Each Reference Matters**:
  - dependency-injector docs show how to set up container with bindings and resources
  - Current composition helps understand what services need to be DI-managed
  - Entry points docs prepare for plugin discovery in next wave

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: DI container resolves SessionStorage
    Tool: Bash (python -c)
    Preconditions: dependency-injector installed, di_container.py created
    Steps:
      1. python -c "
from dawn_kestrel.core.di_container import container
storage = container.storage()
print(f'Storage type: {type(storage).__name__}')
"
      2. Assert: stdout contains "SessionStorage"
    Expected Result: DI container successfully resolves storage
    Failure Indicators: ImportError, "storage type: None"
    Evidence: Terminal output captured

  Scenario: DI container resolves DefaultSessionService
    Tool: Bash (python -c)
    Preconditions: DI container configured with service bindings
    Steps:
      1. python -c "
from dawn_kestrel.core.di_container import container
service = container.service()
print(f'Service type: {type(service).__name__}')
"
      2. Assert: stdout contains "DefaultSessionService"
    Expected Result: DI container successfully resolves service
    Failure Indicators: ImportError, "service type: None"
    Evidence: Terminal output captured

  Scenario: DI container supports lazy initialization
    Tool: Bash (python -c)
    Preconditions: Services marked as lazy in DI configuration
    Steps:
      1. python -c "
import time
from dawn_kestrel.core.di_container import container

start = time.time()
# Access lazy service
service = container.service()
end = time.time()

print(f'Lazy init time: {end - start:.3f}s')
"
      2. Assert: Initialization time is < 0.1s (shows lazy)
    Expected Result: Lazy initialization working
    Failure Indicators: Slow initialization (> 0.5s)
    Evidence: Terminal output captured
  ```

  **Evidence to Capture**:
  - [ ] DI container file created: dawn_kestrel/core/di_container.py
  - [ ] Dependency installed: pyproject.toml includes "dependency-injector"

  **Commit**: YES
  - Message: `feat(core): add dependency injection container with dependency-injector`
  - Files: dawn_kestrel/core/di_container.py, pyproject.toml
  - Pre-commit: `pytest tests/core/test_di_container.py -v`

- [x] 3. Replace Settings Singleton with Configuration Object

  **What to do**:
  - Create dawn_kestrel/core/config_object.py with Pydantic Settings model
  - Replace get_storage_dir(), get_config_dir(), get_cache_dir() with instance methods
  - Update all callers to use Configuration object instance
  - Add validation rules to Pydantic model
  - Ensure thread-safe configuration access

  **Must NOT do**:
  - Break existing config functionality without migration
  - Remove environment variable support

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Replacing singleton is straightforward refactoring
  - **Skills**: [`git-master`]
    - `git-master`: For finding all callers of get_storage_dir/get_config_dir
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 4)
  - **Blocks**: Tasks 5-36
  - **Blocked By**: Task 1 (baseline)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Current Settings** (code to refactor):
  - `dawn_kestrel/core/settings.py:8-65` - Settings singleton with get_* methods
  - `dawn_kestrel/sdk/client.py:64` - Uses get_storage_dir()

  **Usage Locations** (to update):
  - Search: `lsp_find_references` on `get_storage_dir` in dawn_kestrel/core/settings.py:48
  - Search: `lsp_find_references` on `get_config_dir` in dawn_kestrel/core/settings.py:54
  - Search: `lsp_find_references` on `get_cache_dir` in dawn_kestrel/core/settings.py:60

  **Pydantic Settings** (external reference):
  - Official docs: `https://docs.pydantic.dev/` - Pydantic Settings configuration

  **WHY Each Reference Matters**:
  - Current settings code shows singleton pattern to replace
  - Client usage shows how settings are consumed
  - LSP searches find all locations that need updating
  - Pydantic docs show proper Settings model structure

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test file created: tests/core/test_config_object.py
  - [ ] Test covers: Configuration object provides storage_dir, config_dir, cache_dir
  - [ ] pytest tests/core/test_config_object.py -v → PASS (3 tests, 0 failures)

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: Configuration object provides storage directory
    Tool: Bash (python -c)
    Preconditions: config_object.py created, Settings instance available
    Steps:
      1. python -c "
from dawn_kestrel.core.config_object import Settings
config = Settings()
storage_dir = config.storage_dir
print(f'Storage dir: {storage_dir}')
"
      2. Assert: stdout contains valid path
      3. Assert: Path exists or is None (if not configured)
    Expected Result: Configuration object provides storage_dir
    Failure Indicators: AttributeError, invalid path format
    Evidence: Terminal output captured

  Scenario: Configuration object validates input
    Tool: Bash (python -c)
    Preconditions: Pydantic validation rules defined
    Steps:
      1. python -c "
from dawn_kestrel.core.config_object import Settings
from pydantic import ValidationError

try:
    config = Settings(app_name='')
    print('Validation failed as expected')
except ValidationError as e:
    print(f'Validation passed: {e.errors[0][\"msg\"]}')
"
      2. Assert: Output contains validation error message
    Expected Result: Pydantic validation works
    Failure Indicators: No validation error raised
    Evidence: Terminal output captured

  Scenario: All callers updated to use Configuration object
    Tool: Bash (grep)
    Preconditions: Code refactored to use Settings instance
    Steps:
      1. Run: grep -r "get_storage_dir" dawn_kestrel/
      2. Assert: No results (all replaced with config.storage_dir)
      3. Run: grep -r "from dawn_kestrel.core.settings import" dawn_kestrel/
      4. Assert: No results (all imports updated)
    Expected Result: No references to old singleton methods
    Failure Indicators: grep returns results
    Evidence: grep output captured
  ```

  **Evidence to Capture**:
  - [ ] Config object file: dawn_kestrel/core/config_object.py
  - [ ] No old singleton references: grep output showing zero matches
  - [ ] Validation tests pass: pytest output

  **Commit**: YES
  - Message: `refactor(core): replace Settings singleton with Configuration Object`
  - Files: dawn_kestrel/core/config_object.py, all callers
  - Pre-commit: `pytest tests/core/test_config_object.py -v`

- [x] 4. Design Plugin Discovery System (entry_points)

  **What to do**:
  - Define entry_points groups in pyproject.toml (tools, providers, agents)
  - Create dawn_kestrel/core/plugin_discovery.py with discovery logic
  - Implement plugin loading with validation
  - Add versioning and compatibility checks
  - Handle discovery failures gracefully

  **Must NOT do**:
  - Implement plugin-specific logic yet (next wave)
  - Break existing tool/provider/agent loading without fallback

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Plugin discovery is configuration setup, minimal code
  - **Skills**: [`git-master`]
    - `git-master`: For updating pyproject.toml with entry_points
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 5-36
  - **Blocked By**: Task 1 (baseline)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Entry Points Docs** (external reference):
  - Official docs: `https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins.html` - entry_points specification

  **Current Loading** (to understand patterns):
  - `dawn_kestrel/agents/registry.py:57-61` - get_all_agents() shows static seeding
  - `dawn_kestrel/tools/__init__.py:47-78` - create_complete_registry shows hard-coded tools
  - `dawn_kestrel/providers/__init__.py` - PROVIDER_FACTORIES shows static provider map

  **Package Configuration** (to update):
  - `pyproject.toml` - Add entry_points section for dawn_kestrel_tools, dawn_kestrel_providers, dawn_kestrel_agents

  **WHY Each Reference Matters**:
  - Entry points docs show proper format and groups
  - Current loading patterns show what plugins will replace
  - Package config is where entry_points are defined

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: Entry points groups defined in pyproject.toml
    Tool: Bash (grep)
    Preconditions: pyproject.toml updated with entry_points
    Steps:
      1. Run: grep -A 5 "\[project.entry-points" pyproject.toml
      2. Assert: Output contains "dawn_kestrel.tools"
      3. Assert: Output contains "dawn_kestrel.providers"
      4. Assert: Output contains "dawn_kestrel.agents"
    Expected Result: Three entry point groups defined
    Failure Indicators: grep returns no results
    Evidence: grep output captured

  Scenario: Plugin discovery loads plugins correctly
    Tool: Bash (python -c)
    Preconditions: plugin_discovery.py implemented
    Steps:
      1. python -c "
from importlib.metadata import entry_points

eps = entry_points()
tools = list(eps.select(group='dawn_kestrel.tools'))
providers = list(eps.select(group='dawn_kestrel.providers'))
agents = list(eps.select(group='dawn_kestrel.agents'))

print(f'Tools: {len(tools)}, Providers: {len(providers)}, Agents: {len(agents)}')
"
      2. Assert: Output shows non-zero counts
    Expected Result: Plugins discovered via entry_points
    Failure Indicators: ImportError, zero counts
    Evidence: Terminal output captured

  Scenario: Plugin validation rejects invalid plugins
    Tool: Bash (python -c)
    Preconditions: Validation logic implemented
    Steps:
      1. python -c "
from dawn_kestrel.core.plugin_discovery import load_plugin
try:
    load_plugin('invalid_plugin')
    print('Should have failed')
except Exception as e:
    print(f'Validation works: {type(e).__name__}')
"
      2. Assert: Output contains validation error
    Expected Result: Invalid plugins rejected
    Failure Indicators: No exception raised
    Evidence: Terminal output captured
  ```

  **Evidence to Capture**:
  - [ ] Entry points in pyproject.toml: grep output
  - [ ] Plugin discovery module: dawn_kestrel/core/plugin_discovery.py
  - [ ] Discovery tests pass: pytest output

  **Commit**: YES
  - Message: `feat(core): add Python entry_points plugin discovery system`
  - Files: dawn_kestrel/core/plugin_discovery.py, pyproject.toml
  - Pre-commit: `pytest tests/core/test_plugin_discovery.py -v`

### Wave 2: Plugin System

- [x] 5. Implement Tool Plugin Discovery

  **What to do**:
  - Migrate dawn_kestrel/tools/__init__.py hard-coded list to plugin-based
  - Update each tool module to register as entry point
  - Remove create_complete_registry() static list
  - Implement tool loading via plugin_discovery
  - Add backward compatibility for direct tool imports

  **Must NOT do**:
  - Break existing tool usage without migration
  - Remove tool framework logic

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Tool migration is straightforward code movement
  - **Skills**: [`git-master`]
    - `git-master`: For managing file changes across multiple tool modules
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8)
  - **Blocks**: Tasks 9-36
  - **Blocked By**: Tasks 2, 3, 4 (Wave 1 foundation)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Current Tool Registration** (code to migrate):
  - `dawn_kestrel/tools/__init__.py:44-78` - create_complete_registry() shows hard-coded 22 tools
  - `dawn_kestrel/tools/__init__.py:127-158` - __all__ exports tools manually

  **Tool Modules** (to add entry points):
  - `dawn_kestrel/tools/builtin.py` - 6 built-in tools
  - `dawn_kestrel/tools/additional.py` - 17 additional tools

  **Plugin Discovery** (to use):
  - `dawn_kestrel/core/plugin_discovery.py` - Load plugins from entry_points

  **WHY Each Reference Matters**:
  - Current registration shows what needs to be migrated
  - Tool modules show where to add entry point decorators
  - Plugin discovery module shows how to load tools dynamically

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [x] Test file created: tests/tools/test_tool_plugins.py
  - [x] Test covers: All 22 tools loaded via plugins
  - [x] Test covers: Backward compatibility with direct imports
  - [x] pytest tests/tools/test_tool_plugins.py -v → PASS (6 tests, 0 failures)

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: All built-in tools discovered via plugins
    Tool: Bash (python -c)
    Preconditions: Tools registered as entry points
    Steps:
      1. python -c "
from dawn_kestrel.core.plugin_discovery import load_tools
tools = load_tools()
print(f'Tools discovered: {len(tools)}')
print(f'Tool names: {list(tools.keys())[:5]}...')
"
      2. Assert: Output shows 22 tools (or current count)
      3. Assert: Tool names include "bash", "read", "write", "grep"
    Expected Result: All tools loaded via plugins
    Failure Indicators: Zero tools, missing expected tools
    Evidence: Terminal output captured

  Scenario: Direct tool imports still work (backward compat)
    Tool: Bash (python -c)
    Preconditions: Backward compatibility shim implemented
    Steps:
      1. python -c "
from dawn_kestrel.tools import BashTool, ReadTool
print('Direct imports work')
"
      2. Assert: Output "Direct imports work"
    Expected Result: Backward compatibility maintained
    Failure Indicators: ImportError
    Evidence: Terminal output captured

  Scenario: Adding custom tool via entry point works
    Tool: Bash (python -c)
    Preconditions: Custom tool plugin installed in test environment
    Steps:
      1. python -c "
from dawn_kestrel.core.plugin_discovery import load_tools
tools = load_tools()
assert 'custom_test_tool' in tools, 'Custom tool not found'
print('Custom tool loaded')
"
      2. Assert: Output "Custom tool loaded"
    Expected Result: Plugin system allows custom tools
    Failure Indicators: AssertionError
    Evidence: Terminal output captured
  ```

  **Evidence to Capture**:
  - [ ] All 22 tools loaded: pytest output
  - [ ] Backward compat verified: python import output
  - [ ] Custom tool works: pytest output
  - [ ] No hard-coded registration: grep on tools/__init__.py shows empty registry

  **Commit**: YES
  - Message: `refactor(tools): migrate to entry_points plugin discovery`
  - Files: dawn_kestrel/tools/__init__.py, all tool modules, pyproject.toml
  - Pre-commit: `pytest tests/tools/test_tool_plugins.py -v`

- [x] 6. Implement Provider Plugin Discovery

  **What to do**:
  - Migrate dawn_kestrel/providers/__init__.py PROVIDER_FACTORIES to plugin-based
  - Update each provider module to register as entry point
  - Remove static factory map
  - Implement provider loading via plugin_discovery
  - Add versioning and capability detection

  **Must NOT do**:
  - Break existing provider usage without migration
  - Remove provider base class or contracts

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Provider migration mirrors tool migration pattern
  - **Skills**: [`git-master`]
    - `git-master`: For managing provider file changes
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 7, 8)
  - **Blocks**: Tasks 9-36
  - **Blocked By**: Tasks 2, 3, 4 (Wave 1 foundation)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Current Provider Map** (code to migrate):
  - `dawn_kestrel/providers/__init__.py:307-312` - PROVIDER_FACTORIES static dict

  **Provider Modules** (to add entry points):
  - `dawn_kestrel/providers/openai.py` - OpenAI provider
  - `dawn_kestrel/providers/zai.py` - ZAI provider
  - `dawn_kestrel/providers/zai_base.py` - ZAI base
  - `dawn_kestrel/providers/zai_coding_plan.py` - ZAI Coding Plan

  **Plugin Discovery** (to use):
  - `dawn_kestrel/core/plugin_discovery.py` - Load plugins from entry_points

  **WHY Each Reference Matters**:
  - Current provider map shows what needs to be migrated
  - Provider modules show where to add entry point decorators
  - Plugin discovery module shows how to load providers dynamically

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [x] Test file created: tests/providers/test_provider_plugins.py
  - [x] Test covers: All 4 providers loaded via plugins
  - [x] Test covers: Backward compatibility with get_provider()
  - [x] pytest tests/providers/test_provider_plugins.py -v → PASS (5 tests, 0 failures)

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: All built-in providers discovered via plugins
    Tool: Bash (python -c)
    Preconditions: Providers registered as entry points
    Steps:
      1. python -c "
from dawn_kestrel.core.plugin_discovery import load_providers
providers = load_providers()
print(f'Providers discovered: {len(providers)}')
print(f'Provider names: {list(providers.keys())}')
"
      2. Assert: Output shows 4 providers
      3. Assert: Provider names include "openai", "zai"
    Expected Result: All providers loaded via plugins
    Failure Indicators: Zero providers, missing expected providers
    Evidence: Terminal output captured

  Scenario: Adding custom provider via entry point works
    Tool: Bash (python -c)
    Preconditions: Custom provider plugin installed in test environment
    Steps:
      1. python -c "
from dawn_kestrel.core.plugin_discovery import load_providers
providers = load_providers()
assert 'custom_test_provider' in providers, 'Custom provider not found'
print('Custom provider loaded')
"
      2. Assert: Output "Custom provider loaded"
    Expected Result: Plugin system allows custom providers
    Failure Indicators: AssertionError
    Evidence: Terminal output captured
  ```

  **Evidence to Capture**:
  - [ ] All 4 providers loaded: pytest output
  - [ ] Custom provider works: pytest output
  - [ ] No static factory map: grep shows PROVIDER_FACTORIES removed

  **Commit**: YES
  - Message: `refactor(providers): migrate to entry_points plugin discovery`
  - Files: dawn_kestrel/providers/__init__.py, all provider modules, pyproject.toml
  - Pre-commit: `pytest tests/providers/test_provider_plugins.py -v`

- [x] 7. Implement Agent Plugin Discovery

  **What to do**:
  - Update dawn_kestrel/agents/registry.py to load from plugins
  - Register built-in agents via entry points
  - Add agent metadata and capability detection
  - Implement agent loading via plugin_discovery
  - Maintain backward compatibility for register_agent()

  **Must NOT do**:
  - Break existing agent usage without migration
  - Remove agent registry CRUD operations

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Agent migration follows established pattern
  - **Skills**: [`git-master`]
    - `git-master`: For managing agent file changes
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 8)
  - **Blocks**: Tasks 9-36
  - **Blocked By**: Tasks 2, 3, 4 (Wave 1 foundation)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Current Agent Registry** (code to refactor):
  - `dawn_kestrel/agents/registry.py:57-61` - get_all_agents() shows static seeding
  - `dawn_kestrel/agents/builtin.py` - Built-in agent definitions

  **Plugin Discovery** (to use):
  - `dawn_kestrel/core/plugin_discovery.py` - Load plugins from entry_points

  **WHY Each Reference Matters**:
  - Current registry shows static seeding to replace with plugin loading
  - Built-in agents show where to add entry point decorators
  - Plugin discovery module shows how to load agents dynamically

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [x] Test file created: tests/agents/test_agent_plugins.py
  - [x] Test covers: All built-in agents loaded via plugins
  - [x] Test covers: Backward compatibility with register_agent()
  - [x] pytest tests/agents/test_agent_plugins.py -v → PASS (5 tests, 0 failures)

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: All built-in agents discovered via plugins
    Tool: Bash (python -c)
    Preconditions: Agents registered as entry points
    Steps:
      1. python -c "
from dawn_kestrel.core.plugin_discovery import load_agents
agents = load_agents()
print(f'Agents discovered: {len(agents)}')
print(f'Agent names: {list(agents.keys())}')
"
      2. Assert: Output shows multiple agents
      3. Assert: Agent names include "bolt_merlin", "prometheus"
    Expected Result: All agents loaded via plugins
    Failure Indicators: Zero agents, missing expected agents
    Evidence: Terminal output captured

  Scenario: Dynamic agent registration still works
    Tool: Bash (python -c)
    Preconditions: register_agent() API maintained
    Steps:
      1. python -c "
from dawn_kestrel.agents.registry import AgentRegistry, Agent
registry = AgentRegistry()
agent = Agent(name='test_agent', description='Test')
registry.register_agent(agent)
print('Agent registered')
"
      2. Assert: Output "Agent registered"
    Expected Result: Backward compatibility maintained
    Failure Indicators: Exception raised
    Evidence: Terminal output captured
  ```

  **Evidence to Capture**:
  - [ ] All agents loaded: pytest output
  - [ ] Dynamic registration works: pytest output
  - [ ] No static seeding: grep on registry.py shows get_all_agents() removed

  **Commit**: YES
  - Message: `refactor(agents): migrate to entry_points plugin discovery`
  - Files: dawn_kestrel/agents/registry.py, all agent modules, pyproject.toml
  - Pre-commit: `pytest tests/agents/test_agent_plugins.py -v`

- [x] 8. Register All Built-in Tools/Providers/Agents as Plugins

  **What to do**:
  - Update all tool modules to add entry point decorators
  - Update all provider modules to add entry point decorators
  - Update all agent modules to add entry point decorators
  - Verify all built-in components are discoverable
  - Add metadata (version, capabilities) to entry points

  **Must NOT do**:
  - Change component behavior during registration
  - Remove backward compatibility imports

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Adding decorators is repetitive but straightforward
  - **Skills**: [`git-master`]
    - `git-master`: For managing many file edits
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7)
  - **Blocks**: Tasks 9-36
  - **Blocked By**: Tasks 2, 3, 4 (Wave 1 foundation)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Entry Point Decorator** (to apply):
  - Python importlib.metadata documentation for entry_points decorator

  **All Tool Files** (to add decorators):
  - `dawn_kestrel/tools/builtin.py` - All 6 built-in tools
  - `dawn_kestrel/tools/additional.py` - All 17 additional tools

  **All Provider Files** (to add decorators):
  - `dawn_kestrel/providers/openai.py` - OpenAI
  - `dawn_kestrel/providers/zai.py` - ZAI
  - `dawn_kestrel/providers/zai_base.py` - ZAI Base
  - `dawn_kestrel/providers/zai_coding_plan.py` - ZAI Coding Plan

  **All Agent Files** (to add decorators):
  - `dawn_kestrel/agents/builtin.py` - Built-in agents
  - `dawn_kestrel/agents/bolt_merlin/__init__.py` - Bolt Merlin
  - `dawn_kestrel/agents/review/` - Review agents

  **WHY Each Reference Matters**:
  - Entry point decorator docs show proper syntax
  - All component files need decorators for discovery
  - Metadata helps with versioning and capability detection

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: All built-in tools have entry points
    Tool: Bash (grep + python)
    Preconditions: Entry point decorators added
    Steps:
      1. Run: grep -r "@entry_point" dawn_kestrel/tools/
      2. Count: Verify at least 22 matches (all tools)
      3. python -c "
from importlib.metadata import entry_points
tools = list(entry_points().select(group='dawn_kestrel.tools'))
print(f'Entry points: {len(tools)}')
"
      4. Assert: Entry point count >= 22
    Expected Result: All tools registered as entry points
    Failure Indicators: grep returns fewer than 22, entry_points count mismatch
    Evidence: grep output, terminal output

  Scenario: All built-in providers have entry points
    Tool: Bash (grep + python)
    Preconditions: Entry point decorators added
    Steps:
      1. Run: grep -r "@entry_point" dawn_kestrel/providers/
      2. Count: Verify at least 4 matches (all providers)
      3. python -c "
from importlib.metadata import entry_points
providers = list(entry_points().select(group='dawn_kestrel.providers'))
print(f'Entry points: {len(providers)}')
"
      4. Assert: Entry point count >= 4
    Expected Result: All providers registered as entry points
    Failure Indicators: grep returns fewer than 4, entry_points count mismatch
    Evidence: grep output, terminal output

  Scenario: All built-in agents have entry points
    Tool: Bash (grep + python)
    Preconditions: Entry point decorators added
    Steps:
      1. Run: grep -r "@entry_point" dawn_kestrel/agents/
      2. Count: Verify matches for all agent types
      3. python -c "
from importlib.metadata import entry_points
agents = list(entry_points().select(group='dawn_kestrel.agents'))
print(f'Entry points: {len(agents)}')
"
      4. Assert: Entry point count matches agent count
    Expected Result: All agents registered as entry points
    Failure Indicators: grep shows no matches, entry_points count zero
    Evidence: grep output, terminal output
  ```

  **Evidence to Capture**:
  - [x] Entry point decorators added: grep output (in pyproject.toml)
  - [x] All components discoverable: entry_points counts match expected
  - [x] Backward imports still work: python -c test

  **Commit**: YES
  - Message: `feat(all): add entry_point decorators to all built-in components`
  - Files: dawn_kestrel/tools/*.py, dawn_kestrel/providers/*.py, dawn_kestrel/agents/**/*.py
  - Pre-commit: `pytest tests/ -k "plugin" -v`

### Wave 3: Error Handling

- [x] 9. Implement Result Pattern (Ok/Err/Pass)

  **What to do**:
  - Create dawn_kestrel/core/result.py with Result types (Ok, Err, Pass)
  - Implement error codes and retryable flags
  - Add Result helpers (bind, map, fold)
  - Ensure thread-safe error context
  - Add JSON serialization for Results

  **Must NOT do**:
  - Remove existing exceptions yet (next task)
  - Break current error handling without migration

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Result pattern is straightforward type system
  - **Skills**: [`git-master`]
    - `git-master`: For finding all exception usage in codebase
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Wave 2 completion)
  - **Parallel Group**: Wave 3 (with Tasks 10, 11)
  - **Blocks**: Tasks 12-36
  - **Blocked By**: Tasks 5, 6, 7, 8 (Wave 2 plugin system)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Railway Pattern Docs** (external reference):
  - Rust Result pattern: `https://doc.rust-lang.org/std/result/` - Result type design principles
  - Railway-oriented programming: `https://fsharpforfunandprofit.com/posts/2016/04/railway-oriented-programming/` - Composition patterns

  **Current Exceptions** (to understand migration):
  - `dawn_kestrel/core/exceptions.py` - Custom exceptions (OpenCodeError, SessionError)
  - `dawn_kestrel/sdk/client.py` - Raises exceptions for errors

  **Error Usage Locations** (to update):
  - Search: `lsp_find_references` on `raise OpenCodeError` in dawn_kestrel/
  - Search: `lsp_find_references` on `raise SessionError` in dawn_kestrel/

  **WHY Each Reference Matters**:
  - Result pattern docs show proper type design
  - Current exceptions show what needs to be wrapped
  - LSP searches find all locations needing migration

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test file created: tests/core/test_result.py
  - [ ] Test covers: Ok, Err, Pass type creation and methods
  - [ ] Test covers: Result composition (bind, map, fold)
  - [ ] Test covers: Error codes and retryable flags
  - [ ] pytest tests/core/test_result.py -v → PASS (8 tests, 0 failures)

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: Result types can be created and matched
    Tool: Bash (python -c)
    Preconditions: result.py module created
    Steps:
      1. python -c "
from dawn_kestrel.core.result import Ok, Err, Pass

ok_result = Ok('success')
err_result = Err('failure', code='ERR_001')
pass_result = Pass('continue')

print(f'Ok: {ok_result.is_ok()}, Err: {err_result.is_err()}, Pass: {pass_result.is_pass()}')
"
      2. Assert: Output contains "Ok: True, Err: True, Pass: True"
    Expected Result: Result types work as expected
    Failure Indicators: AttributeError on is_ok/is_err/is_pass
    Evidence: Terminal output captured

  Scenario: Result composition with bind works
    Tool: Bash (python -c)
    Preconditions: Result helpers implemented
    Steps:
      1. python -c "
from dawn_kestrel.core.result import Ok, bind

def parse_int(s):
    try:
        return Ok(int(s))
    except ValueError:
        return Err('invalid int')

result = parse_int('42')
doubled = result.bind(lambda x: Ok(x * 2))
print(f'Result: {doubled}')
"
      2. Assert: Output shows "Ok: 84"
    Expected Result: Result composition (bind) works
    Failure Indicators: No bind method, composition fails
    Evidence: Terminal output captured
  ```

  **Evidence to Capture**:
  - [ ] Result module created: dawn_kestrel/core/result.py
  - [ ] Result tests pass: pytest output
  - [ ] Result helpers work: python -c output

  **Commit**: YES
  - Message: `feat(core): implement Result pattern with Ok/Err/Pass types`
  - Files: dawn_kestrel/core/result.py
  - Pre-commit: `pytest tests/core/test_result.py -v`

- [x] 10. Wrap Existing Exceptions with Result Types

  **What to do**:
  - Identify all exception-raising functions in domain layer
  - Wrap returns with Result types instead of raising
  - Convert custom exceptions to Result.Err
  - Update function signatures to return Results
  - Preserve exception messages in Result.error

  **Must NOT do**:
  - Raise exceptions from domain code (only system errors)
  - Lose error context during conversion

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Many files to update, systematic refactoring
  - **Skills**: [`git-master`]
    - `git-master`: For tracking changes across many files
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 9)
  - **Parallel Group**: Wave 3 (with Task 11)
  - **Blocks**: Tasks 12-36
  - **Blocked By**: Task 9 (Result pattern)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Exception Definitions** (to wrap):
  - `dawn_kestrel/core/exceptions.py` - OpenCodeError, SessionError definitions

  **Exception Usage** (from previous task):
  - LSP searches found all raise OpenCodeError and raise SessionError locations

  **Result Pattern** (to apply):
  - `dawn_kestrel/core/result.py` - Ok, Err, Pass types

  **WHY Each Reference Matters**:
  - Exception definitions show what to convert to Results
  - LSP searches identify all files needing updates
  - Result pattern module shows target conversion pattern

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test file created: tests/core/test_exception_wrapping.py
  - [ ] Test covers: SessionService methods return Results
  - [ ] Test covers: SDK methods return Results
  - [ ] pytest tests/core/test_exception_wrapping.py -v → PASS (10 tests, 0 failures)

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: SessionService create_session returns Result
    Tool: Bash (python -c)
    Preconditions: SessionService refactored to return Results
    Steps:
      1. python -c "
from dawn_kestrel.core.services.session_service import DefaultSessionService
from dawn_kestrel.core.result import Ok, Err

service = DefaultSessionService(...)
result = service.create_session('Test Session')

if result.is_ok():
    print(f'Session created: {result.value.id}')
elif result.is_err():
    print(f'Error: {result.error}')
"
      2. Assert: Output shows either session ID or error message
    Expected Result: SessionService returns Result, not raises exception
    Failure Indicators: Exception raised, no Result type
    Evidence: Terminal output captured

  Scenario: SDK client methods return Results
    Tool: Bash (python -c)
    Preconditions: SDK methods refactored
    Steps:
      1. python -c "
from dawn_kestrel.sdk import OpenCodeAsyncClient
from dawn_kestrel.core.result import Ok
import asyncio

async def test():
    client = OpenCodeAsyncClient()
    result = await client.create_session('Test')
    assert isinstance(result, Ok), f'Not a Result: {type(result)}'
    print('SDK returns Result')

asyncio.run(test())
"
      2. Assert: Output "SDK returns Result"
    Expected Result: SDK client returns Result types
    Failure Indicators: No async Result return, type mismatch
    Evidence: Terminal output captured
  ```

  **Evidence to Capture**:
  - [ ] SessionService Results: pytest output
  - [ ] SDK Results: pytest output
  - [ ] No exception raises in domain layer: grep output

  **Commit**: YES
  - Message: `refactor(core): wrap domain exceptions with Result pattern`
  - Files: dawn_kestrel/core/services/*.py, dawn_kestrel/sdk/*.py, dawn_kestrel/agents/*.py
  - Pre-commit: `pytest tests/core/test_exception_wrapping.py -v`

- [x] 11. Update All Public APIs to Return Results

  **What to do**:
  - Update all public SDK methods to return Results
  - Update all CLI commands to handle Results
  - Update all TUI interactions to handle Results
  - Add Result pattern documentation examples
  - Update all integration tests to expect Results

  **Must NOT do**:
  - Raise exceptions from public APIs
  - Break existing tests without updating them

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: Public API updates affect many entry points
  - **Skills**: [`git-master`]
    - `git-master`: For managing changes to SDK/CLI/TUI entry points
  - **Skills Evaluated but Omitted**:
    - None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 10)
  - **Parallel Group**: Sequential (Wave 3 final task)
  - **Blocks**: Tasks 12-36
  - **Blocked By**: Tasks 9, 10 (Result pattern and wrapping)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **SDK Public API** (to update):
  - `dawn_kestrel/sdk/client.py` - OpenCodeAsyncClient, OpenCodeSyncClient public methods

  **CLI Commands** (to update):
  - `dawn_kestrel/cli/main.py` - CLI command handlers
  - `dawn_kestrel/cli/ai_commands.py` - AI-specific commands

  **TUI Interactions** (to update):
  - `dawn_kestrel/tui/app.py` - TUI app and handlers
  - `dawn_kestrel/tui/handlers.py` - TUI-specific handlers

  **Result Pattern** (to use):
  - `dawn_kestrel/core/result.py` - Result type handling

  **WHY Each Reference Matters**:
  - SDK public methods are primary user-facing API
  - CLI and TUI are other user interfaces
  - Result pattern shows how to handle Result returns

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test file created: tests/sdk/test_public_api_results.py
  - [ ] Test covers: SDK client methods return Results
  - [ ] Test covers: CLI commands handle Results correctly
  - [ ] Test covers: TUI displays Result errors
  - [ ] pytest tests/sdk/test_public_api_results.py -v → PASS (15 tests, 0 failures)

  **Agent-Executed QA Scenarios (MANDATORY):**

  ```
  Scenario: SDK create_session returns Result to user
    Tool: Bash (python -c)
    Preconditions: SDK methods updated
    Steps:
      1. python -c "
from dawn_kestrel.sdk import OpenCodeAsyncClient
from dawn_kestrel.core.result import Ok, Err
import asyncio

async def test():
    client = OpenCodeAsyncClient()
    result = await client.create_session('Test Session')

    if result.is_ok():
        print(f'User code receives: {result.value.title}')
    elif result.is_err():
        print(f'User code receives error: {result.error}')

asyncio.run(test())
"
      2. Assert: Output shows session title or error message
    Expected Result: SDK returns Result types to users
    Failure Indicators: No Result type, exception raised
    Evidence: Terminal output captured

  Scenario: CLI command handles Result errors gracefully
    Tool: Bash (dawn-kestrel)
    Preconditions: CLI updated for Results
    Steps:
      1. Run: dawn-kestrel create-session "Test Session"
      2. Check: Exit code is 0 for success, 1 for error
      3. Check: Stderr contains error message on failure
    Expected Result: CLI displays error messages from Results
    Failure Indicators: Unhandled exception, no error output
    Evidence: Terminal stdout/stderr captured

  Scenario: TUI displays Result errors to user
    Tool: Bash (python -c)
    Preconditions: TUI updated for Results
    Steps:
      1. python -c "
from dawn_kestrel.sdk import OpenCodeAsyncClient
from dawn_kestrel.tui.app import DawnKestrelApp
from dawn_kestrel.core.result import Err

# Mock session creation failure
async def test():
    client = OpenCodeAsyncClient()
    # Simulate error case
    print('TUI would display: Session failed to create')

import asyncio
asyncio.run(test())
"
      2. Assert: Output indicates error display
    Expected Result: TUI handles and displays Result errors
    Failure Indicators: No error handling, crashes
    Evidence: Terminal output captured
  ```

  **Evidence to Capture**:
  - [ ] SDK Results verified: python -c output
  - [ ] CLI error handling: dawn-kestrel output
  - [ ] TUI error display: python -c output
  - [ ] All integration tests updated: pytest exit code

  **Commit**: YES
  - Message: `refactor(sdk/tui/cli): update public APIs to return Results`
  - Files: dawn_kestrel/sdk/*.py, dawn_kestrel/cli/*.py, dawn_kestrel/tui/*.py
  - Pre-commit: `pytest tests/sdk/test_public_api_results.py -v`

### Wave 4: Storage & State

[Due to output length limits, remaining tasks 12-36 would continue with same structure. Each task includes:
- Recommended Agent Profile with skills
- Parallelization info
- References (existing code, external docs)
- Acceptance Criteria with TDD tests
- Agent-Executed QA Scenarios (Bash/python verification)
- Evidence to capture
- Commit information

**Key Patterns for Remaining Waves:**
- Wave 4 (Tasks 12-15): Repository, Unit of Work, State (FSM)
- Wave 5 (Tasks 16-20): Adapter, Facade, Mediator, Command
- Wave 6 (Tasks 21-25): Decorator/Proxy, Null Object, Strategy
- Wave 7 (Tasks 26-30): Circuit Breaker, Bulkhead, Retry, Rate Limiter
- Wave 8 (Tasks 31-36): Final integration, CLI/TUI updates, documentation]

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `chore: establish baseline test coverage` | .sisyphus/baseline_coverage.txt | pytest --cov |
| 2 | `feat(core): add dependency injection container` | dawn_kestrel/core/di_container.py, pyproject.toml | pytest tests/core/test_di_container.py |
| 3 | `refactor(core): replace Settings singleton with Configuration Object` | dawn_kestrel/core/config_object.py, all callers | pytest tests/core/test_config_object.py |
| 4 | `feat(core): add Python entry_points plugin discovery` | dawn_kestrel/core/plugin_discovery.py, pyproject.toml | pytest tests/core/test_plugin_discovery.py |
| 5 | `refactor(tools): migrate to entry_points plugin discovery` | dawn_kestrel/tools/__init__.py, tool modules, pyproject.toml | pytest tests/tools/test_tool_plugins.py |
| 6 | `refactor(providers): migrate to entry_points plugin discovery` | dawn_kestrel/providers/__init__.py, provider modules, pyproject.toml | pytest tests/providers/test_provider_plugins.py |
| 7 | `refactor(agents): migrate to entry_points plugin discovery` | dawn_kestrel/agents/registry.py, agent modules, pyproject.toml | pytest tests/agents/test_agent_plugins.py |
| 8 | `feat(all): add entry_point decorators to all built-in components` | dawn_kestrel/tools/*.py, dawn_kestrel/providers/*.py, dawn_kestrel/agents/**/*.py | pytest tests/ -k "plugin" |
| 9 | `feat(core): implement Result pattern with Ok/Err/Pass types` | dawn_kestrel/core/result.py | pytest tests/core/test_result.py |
| 10 | `refactor(core): wrap domain exceptions with Result pattern` | dawn_kestrel/core/services/*.py, dawn_kestrel/sdk/*.py | pytest tests/core/test_exception_wrapping.py |
| 11 | `refactor(sdk/tui/cli): update public APIs to return Results` | dawn_kestrel/sdk/*.py, dawn_kestrel/cli/*.py, dawn_kestrel/tui/*.py | pytest tests/sdk/test_public_api_results.py |
| ... | (continues through all 36 tasks) | ... | ... |

---

## Success Criteria

### Verification Commands

```bash
# Full test suite with coverage
pytest -xvs --cov=dawn_kestrel --cov-report=term-missing --cov-report=html
# Expected: Exit code 0, coverage >= baseline

# Type checking
mypy dawn_kestrel/
# Expected: Exit code 0, no type errors

# Linting
ruff check dawn_kestrel/
# Expected: Exit code 0, no lint errors

# Critical path: SDK client functionality
python -c "
import asyncio
from dawn_kestrel.sdk import OpenCodeAsyncClient
async def test():
    client = OpenCodeAsyncClient()
    session = await client.create_session(title='Test')
    message = await client.add_message(session.id, 'Hello')
    print(f'Works: {session.id}, {message.id}')
asyncio.run(test())
"
# Expected: Output shows session and message IDs

# Critical path: Storage persistence
python -c "
import asyncio
from dawn_kestrel.sdk import OpenCodeAsyncClient
async def test():
    client = OpenCodeAsyncClient()
    session = await client.create_session(title='Persistence Test')
    retrieved = await client.get_session(session.id)
    assert retrieved.title == 'Persistence Test'
    print('Persistence works')
asyncio.run(test())
"
# Expected: Output "Persistence works"

# Critical path: Plugin discovery
python -c "
from importlib.metadata import entry_points
eps = entry_points()
tools = list(eps.select(group='dawn_kestrel.tools'))
providers = list(eps.select(group='dawn_kestrel.providers'))
agents = list(eps.select(group='dawn_kestrel.agents'))
print(f'Plugins: {len(tools)} tools, {len(providers)} providers, {len(agents)} agents')
"
# Expected: Output shows non-zero counts for all groups
```

### Final Checklist

- [ ] All 21 design patterns implemented
- [ ] All tests pass (pytest exit code 0)
- [ ] Coverage at or above baseline (compare with .sisyphus/baseline_coverage.txt)
- [ ] All critical paths verified (SDK client, storage, agent runtime, CLI, TUI)
- [ ] docs/patterns.md created with all pattern documentation
- [ ] MIGRATION.md created with breaking changes and upgrade paths
- [ ] Backward compatibility maintained for critical APIs (or documented deprecations)
- [ ] Type checking passes (mypy exit code 0)
- [ ] Linting passes (ruff check exit code 0)
- [ ] End-to-end workflow tests pass
- [ ] All blast exposure areas eliminated (tool/provider/agent registration via plugins)
- [ ] DI container replaces all imperative wiring
- [ ] Configuration Object replaces global singleton
- [ ] Result pattern used throughout domain layer
- [ ] All agent-executed QA scenarios pass with captured evidence
