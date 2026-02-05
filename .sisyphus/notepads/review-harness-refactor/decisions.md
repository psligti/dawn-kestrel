# Decisions - review-harness-refactor

## Architectural Decisions

- **TDD Approach**: All tasks follow RED-GREEN-REFACTOR with pytest
- **Zero Human Intervention**: All verification must be automated
- **Backward Compatibility**: MUST preserve ReviewOutput schema and CLI entrypoints
- **No Breaking Changes**: Do NOT modify core modules (ToolRegistry, AgentRuntime, EventBus, SessionManager) unless proven necessary

## Commit Strategy

| After Task | Message |
|------------|---------|
| 1 | `test(review): add baseline parity fixtures` |
| 2 | `feat(llm): add client abstraction` |
| 3 | `feat(harness): add agent runner` |
| 4 | `refactor(review): config-only agents` |
| 5 | `feat(harness): add budgets and aggregation` |
| 6 | `refactor(review): tool-based discovery` |
| 7 | `test(review): add parity + cli checks` |

## File Structure Decisions

New modules to create:
- `core/llm/client.py` - Provider-agnostic LLM client with retry/timeout
- `core/harness/runner.py` - Template Method execution flow
- `core/harness/budgets.py` - Budget enforcement
- `core/harness/fsm.py` - Loop FSM
- `core/harness/aggregation.py` - Result aggregation, dedupe, contract validation
- `tests/fixtures/review_baseline/` - Baseline output fixtures
- `tests/review/test_parity_baseline.py` - Parity tests

## Skill Selection

Reviewing tasks and selecting appropriate skills:

**Task 1 (Baseline Tests)**:
- Category: quick
- Skills: [git-master] - for atomic commits and test verification
- Omitted skills: frontend-ui-ux (not relevant), playwright (no browser work)

**Task 2 (LLM Client)**:
- Category: unspecified-high
- Skills: [git-master] - for atomic commits
- Omitted skills: frontend-ui-ux (not relevant), playwright (no browser work)

## Parallelization Strategy

- Wave 1: Tasks 1 & 2 are independent → run in parallel
- Wave 2: Tasks 3 & 4 can run in parallel (both depend on Task 2 completion)
- Wave 3: Tasks 5 & 6 can run in parallel (depend on Wave 2 completion)
- Wave 4: Task 7 is sequential verification (depends on all previous tasks)

## Success Criteria

- All baseline parity tests pass
- Review outputs conform to ReviewOutput schema
- CLI entrypoints unchanged (`opencode-review --help` works)
- FSM/budgets enforced when enabled
- Frequent parent merges incorporated
