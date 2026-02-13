# Python 3.9.6 Compatibility Fix - Learnings

## Corrections
| Date | Source | What Went Wrong | What To Do Instead |
|------|--------|----------------|-------------------|

## User Preferences

## Patterns That Work

## Patterns That Don't Work

## Domain Notes

## Task 1: Fix dawn_kestrel/core/fsm.py Type Annotations (2026-02-11)
- **Problem**: fsm.py had 19 `|` union operators not supported in Python 3.9.6
- **Solution**: Replaced all `T | None` patterns with `Optional[T]` syntax
- **Changes Made**:
  - Added `Union` to imports (line 21) - though not used, kept for consistency with plan
  - Lines 65, 273: `FSMContext | None` → `Optional[FSMContext]`
  - Lines 110-112: `Callable[...] | None` → `Optional[Callable[...]]`
  - Lines 153-155: `Callable[... | None` → `Optional[Callable[...]]`
  - Lines 175-178: Type fields in FSMReliabilityConfig (circuit_breaker, retry_executor, rate_limiter, bulkhead)
  - Lines 208-214: FSMImpl.__init__ parameters (fsm_id, observers, entry_hooks, exit_hooks, reliability_config)
  - Line 248: Instance variable self._reliability_config
  - Line 500: FSMBuilder instance variable self._reliability_config
- **Verification**:
  - Grep confirms no `|` operators remain in fsm.py
  - .venv/bin/python (Python 3.10+) imports FSMBuilder successfully
  - All 76 FSM tests pass
  - LSP diagnostics on fsm.py are clean (no errors related to type annotations)
- **Note**: System Python 3.9.6 import fails due to mediator.py still having `|` operators (Task 2)

## Task 1 Complete - FSM, Mediator, Observer Type Annotations Fixed (2026-02-11)
- **Problem**: Python 3.9.6 does not support `|` union operator in type annotations
- **Root cause**: fsm.py, mediator.py, and observer.py had `|` operators blocking imports
- **Files Fixed**:
  1. `dawn_kestrel/core/fsm.py` - Already had all 19 `|` operators fixed in previous session
  2. `dawn_kestrel/core/mediator.py` - Fixed 5 `|` operators
  3. `dawn_kestrel/core/observer.py` - Fixed 1 `|` operator (found during import verification)

- **mediator.py Changes**:
  - Added `Optional` to imports (line 18)
  - Line 52: `target: str | None` → `target: Optional[str]`
  - Line 53: `data: dict | None` → `data: Optional[dict]`
  - Line 88 (Protocol): `source: str | None` → `source: Optional[str]`
  - Line 152 (Impl): `...str | None]` → `...Optional[str]]`
  - Line 191 (Impl): `source: str | None` → `source: Optional[str]`

- **observer.py Changes**:
  - Added `Optional` to imports (line 16)
  - Line 100: `mediator: EventMediator | None` → `mediator: Optional[EventMediator]`

- **Verification**:
  - Grep confirms no `|` operators in fsm.py, mediator.py, observer.py
  - Python 3.9.6 successfully imports FSMBuilder and EventMediator
  - All 76 FSM tests pass (100%)
  - LSP diagnostics clean (no `|` operator errors)

- **Learning**: observer.py was not in the plan but had to be fixed because it imports from mediator.py and uses `EventMediator | None`, which blocked FSM imports through the dependency chain.

