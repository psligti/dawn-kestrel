# Baseline Coverage Gaps

## Baseline Summary

- **Date**: 2026-02-09
- **Test Results**: 988 passed, 147 failed, 2 skipped, 42 errors (in 114s)
- **Overall Coverage**: 54% (5015/10900 lines)

## Pre-existing Test Failures

### Review Agent Tests (42 errors, 30+ failures)
**Issue**: Can't instantiate abstract class MockReviewerAgent/TestReviewer with abstract method `get_allowed_tools`
**Affected Files**:
- `tests/review/agents/test_security_reviewer.py`
- `tests/review/agents/test_unit_tests_reviewer.py` (missing AISession import)
- `tests/review/base/test_base_reviewer.py`
- `tests/review/test_base.py`
- `tests/review/test_orchestrator_entry_points.py`
- `tests/review/test_parity_baseline.py`
- `tests/review/test_self_verification.py`

**Root Cause**: Tests need to be updated to implement the new abstract method `get_allowed_tools` in mock agents

### Tool Tracking Tests (20+ failures)
**Issue**: Various errors with tool execution tracking and event bus integration
**Affected File**: `tests/test_tool_tracking.py`
- `test_get_execution_history_with_limit`: TypeError comparing None values
- `test_update_execution_not_found`: FileNotFoundError
- `test_listener_protocol_message_added`: Assertion failed (callback not called)
- `test_event_bus_integration_*`: TypeError - coroutine object not callable

**Root Cause**: Incomplete tool tracking implementation or test setup issues

### Other Issues
- **Deprecation Warnings**: Invalid escape sequences in agent prompts (librarian.py:13, security_reviewer.py:13)
- **RuntimeWarning**: AsyncMock coroutine never awaited in regex pattern matching
- **TestCollectionWarning**: TestApp in test_keybindings.py has __init__ constructor

## Low Coverage Modules

### 0% Coverage (Needs Attention)
- `dawn_kestrel/utils/__init__.py` (0 lines)

### Low Coverage (< 50%)
- `dawn_kestrel/tui/widgets/header.py` (46%)

### Medium Coverage (50-75%)
- Multiple modules have 50-70% coverage (see full report)

## Notes

1. **These failures are pre-existing** - NOT caused by refactor work
2. **Review agent failures** appear to be from recent agent refactoring (Bolt Merlin agents)
3. **Tool tracking failures** suggest incomplete implementation
4. **Coverage baseline** will be used to compare against post-refactor coverage

## Action Items for Refactor

1. Do NOT fix pre-existing test failures during refactor (unless blocking)
2. Focus on maintaining 54%+ coverage throughout refactor
3. Update failing tests if they block refactoring tasks
4. Document any new test failures introduced by refactor
