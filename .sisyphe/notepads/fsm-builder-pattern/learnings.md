# FSM Builder Pattern - Learnings

## Deprecation Implementation (2026-02-10)

Successfully deprecated AgentFSMImpl and ReviewFSMImpl classes:

### Implementation Approach
- Added `warnings` import to both files
- Added deprecation warning in `__init__` methods of both classes using `warnings.warn()`
- Used `DeprecationWarning` category with `stacklevel=2` (standard pattern from SessionService)
- Updated module-level docstrings with DEPRECATED notice
- Updated class-level docstrings to mention Facade.create_fsm() alternative

### Message Pattern
```python
warnings.warn(
    "ClassName is deprecated. Use Facade.create_fsm() instead. "
    "See dawn_kestrel.core.facade.Facade for creating FSM instances.",
    DeprecationWarning,
    stacklevel=2,
)
```

### Test Coverage
- Created `TestAgentFSMDeprecation` test class with 4 tests
- All tests use `pytest.warns()` to verify deprecation warnings
- Tests verify both warning emission and message content
- Tests for both AgentFSMImpl and ReviewFSMImpl

### Test Results
- All 27 AgentFSM tests passed
- 4 new deprecation tests passed
- Deprecation warnings visible in pytest output
- Existing functionality still works (backward compatibility maintained)

### Key Lessons
1. **warnings.warn() pattern**: Use same pattern as existing deprecations (SessionService, CLI)
2. **stacklevel=2**: Important for correct warning source attribution
3. **pytest.warns()**: Use to verify warnings in tests, with regex matching
4. **Module docstring**: Add DEPRECATED section at module level for visibility
5. **Class docstring**: Update to mention alternative (Facade.create_fsm)
6. **No breaking changes**: Deprecation must not break existing functionality

### Migration Path
Users should migrate from:
- `AgentFSMImpl("idle")` → `facade.create_fsm("idle")`
- `ReviewFSMImpl("idle")` → `facade.create_fsm("idle")`

Both patterns remain functional with deprecation warnings guiding migration.
