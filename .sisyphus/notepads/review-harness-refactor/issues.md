# Issues - review-harness-refactor

## Known Issues from Codebase Analysis

- **BaseReviewerAgent god class**: Contains too many responsibilities (review logic, prompt formatting, verification, grep operations, pattern learning)
- **Duplicate LLM handling**: AISession provider logic repeated in review agents (security.py has own flow)
- **Orchestrator duplication**: Contains aggregation and looping logic that should be in harness
- **No centralized budgets**: No budget enforcement (max iterations, max tool calls, max wall time)
- **No FSM loop**: Current flow is linear, no iteration with budget awareness
- **Discovery subprocess**: Uses subprocess calls instead of ToolRegistry

## Potential Issues to Watch

- **Breaking changes to ReviewOutput schema**: MUST NOT happen
- **CLI entrypoint changes**: MUST preserve behavior
- **Core module modifications**: Only modify if necessary and proven
- **Parent merge conflicts**: Need to handle during wave transitions

## Edge Cases to Address

- Budget exhaustion handling
- Missing tools handling
- Tool failure handling
- Provider API errors
- Timeout handling
- Schema validation failures

## Dependencies and Constraints

- Python >= 3.11 required
- pytest-asyncio for async tests
- Pydantic >= 2.12 for schema validation
- Existing core modules must remain compatible
