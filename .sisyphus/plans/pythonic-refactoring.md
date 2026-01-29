# Plan: Pythonic Refactoring

## TL;DR

> **Quick Summary**: Refactor Python OpenCode codebase to use Pythonic idioms, patterns, and conventions throughout. Fix type errors, replace LBYL with EAFP, improve error handling, and ensure code feels natural to Python developers.
>
> **Deliverables**:
> - Fixed type errors in tool system
> - Replaced LBYL patterns with EAFP (9 instances)
> - Improved exception handling
> - Better import organization
> - Added missing type annotations
> - Documentation of Pythonic patterns
>
> **Estimated Effort**: Medium
> **Parallel Execution**: NO - sequential type fixes needed
> **Critical Path**: Fix type errors → Replace patterns → Add type hints

---

## Context

### Original Request
User wants to ensure the Python OpenCode implementation is **Pythonic** - using Python idioms, conventions, and design patterns the way Python developers would naturally write them, not just TypeScript patterns translated literally.

### Current State Analysis

**Already Pythonic (Good!):**
- ✅ Using `Path` from pathlib
- ✅ Using `async with` for resource management
- ✅ Using `BaseModel` with Pydantic
- ✅ Using `.get()` for safe dict access (21 instances)
- ✅ Using f-strings
- ✅ Type hints present (mostly)
- ✅ List/dict comprehensions
- ✅ `pydantic-settings` for config

**Issues Found:**
- ❌ Type errors from TypeScript translation (30+ mypy errors)
- ❌ LBYL pattern instead of EAFP (9 instances)
- ❌ Broad exception handling (1 `except Exception`)
- ❌ Imports inside functions
- ❌ Missing return type annotations
- ❌ Async/callable type mismatches

---

## Work Objectives

### Core Objective
Refactor the Python OpenCode codebase to be truly Pythonic by:
1. Fixing all type errors
2. Replacing LBYL with EAFP patterns
3. Improving exception handling
4. Organizing imports properly
5. Adding comprehensive type hints

### Concrete Deliverables
- All mypy errors resolved
- 9 LBYL patterns replaced with EAFP
- Proper exception hierarchy implemented
- All imports at top level
- Full type hint coverage
- Pythonic patterns documented

### Definition of Done
- [ ] `mypy` passes with no errors
- [ ] All imports at top of files
- [ ] No `except Exception:` without specific type
- [ ] No `.exists()` checks (EAFP instead)
- [ ] All functions have return type hints
- [ ] Code follows PEP 8 style guide

### Must Have
- Maintain Pydantic validation
- Preserve async/await patterns
- Keep FastAPI routes functional
- Maintain tool registry pattern
- Preserve all features

### Must NOT Have (Guardrails)
- Do NOT break existing API compatibility
- Do NOT remove Pydantic validation
- Do NOT change public interface of models
- Do NOT remove async patterns
- Do NOT introduce breaking changes

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest configured)
- **User wants tests**: NO
- **Framework**: pytest, pytest-asyncio

### Manual QA Required

Since no automated tests for refactoring, manual verification includes:

**Type Checking:**
```bash
# Run mypy on all files
mypy src/opencode --strict

# Expected: Zero errors
```

**Code Quality:**
```bash
# Run ruff for style checking
ruff check src/opencode

# Expected: No style errors
```

**Functionality Testing:**
```bash
# Test tool registration
python -c "from opencode.tool import ToolRegistry; t = ToolRegistry(); print('OK')"

# Test agent registry
python -c "from opencode.agent import create_global_registry; print('OK')"

# Test config loading
python -c "from opencode.config import get_settings; print('OK')"
```

**Evidence Required:**
- [ ] mypy output showing 0 errors
- [ ] ruff output showing 0 errors
- [ ] Python import tests passing
- [ ] Screenshot/console output of test runs

---

## Execution Strategy

### Parallel Execution Waves

**Wave 1 (Foundation - Sequential):**
1. Fix type errors in core models
2. Fix type errors in tool system
3. Fix type errors in server

**Wave 2 (Refactoring - Can Parallel):**
4. Replace LBYL with EAFP (file operations)
5. Replace LBYL with EAFP (config loading)
6. Improve exception handling

**Wave 3 (Polishing - Can Parallel):**
7. Add missing type hints (multiple files)
8. Reorganize imports (multiple files)
9. Add `__all__` exports

**Wave 4 (Verification):**
10. Run mypy and ruff checks
11. Manual functionality testing
12. Documentation updates

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3 | None |
| 2 | 1 | 4, 5, 6 | None |
| 3 | 1 | 4, 5, 6 | None |
| 4 | 2 | 7, 8 | 5, 6 |
| 5 | 2 | 7, 8 | 4, 6 |
| 6 | 2 | 7, 8 | 4, 5 |
| 7 | 4, 5, 6 | 10, 11 | 8, 9 |
| 8 | 4, 5, 6 | 10, 11 | 7, 9 |
| 9 | 4, 5, 6 | 10, 11 | 7, 8 |
| 10 | 7, 8, 9 | 11 | None |
| 11 | 10 | 12 | None |
| 12 | 11 | None | None |

---

## TODOs

### Wave 1: Type Fixes (Foundation)

- [ ] 1. Fix type errors in `tool/__init__.py`

  **What to do**:
  - Fix `execute_wrapper` return type issue
  - Add missing return type to `default_init`
  - Fix ToolInfo constructor call arguments
  - Make execute callback type compatible

  **Must NOT do**:
  - Change ToolInfo interface (breaking change)
  - Remove async from wrappers

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple type fixes, file-local changes
  - **Skills**: [`git-master`]
    - `git-master`: For git commit of type fixes
  - **Skills Evaluated but Omitted**:
    - None needed for this task

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Tasks 2-12
  - **Blocked By**: None (start immediately)

  **References**:

  **Pattern References** (existing code to follow):
  - `python_opencode/src/opencode/models/tool.py:ToolInfo` - ToolInfo model definition
  - `python_opencode/src/opencode/models/tool.py:ToolContext` - Context type
  - `python_opencode/src/opencode/models/tool.py:ToolExecutionResult` - Execution result type

  **API/Type References** (contracts to implement against):
  - `python_opencode/src/opencode/tool/__init__.py:define_tool()` - Function signature
  - `python_opencode/src/opencode/models/tool.py:ToolInfo` - Required fields and types

  **Python Type System** (built-ins to leverage):
  - `typing.Callable` - Function type with parameter types
  - `typing.Coroutine` - Async function type
  - `typing.Union` - Union of types
  - `typing.Awaitable` - Objects that can be awaited

  **External References** (libraries and frameworks):
  - PEP 484 - Type hints
  - PEP 492 - Type hinting generics
  - Mypy docs - Type checking behavior

  **WHY Each Reference Matters**:
  - ToolInfo model: Need to match constructor signature exactly
  - Type hints: Python's typing module defines all type constructs

  **Acceptance Criteria**:

  **Manual Execution Verification**:
  - [ ] `mypy src/opencode/tool/__init__.py` returns 0 errors
  - [ ] No LSP type errors in VS Code/IDE
  - [ ] ToolInfo can be instantiated with `define_tool()`
  - [ ] Tools can be registered and executed

  **Evidence Required**:
  - [ ] Terminal output of mypy run
  - [ ] Python import test passes

  **Commit**: NO (group with next type fixes)
  - Message: `fix(tool): resolve type errors in tool system`

- [ ] 2. Fix type errors in `models/agent.py`

  **What to do**:
  - Fix Field alias arguments errors
  - Ensure ModelConfig types are correct

  **Must NOT do**:
  - Change field names (breaking change)
  - Remove validation (Pydantic required)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple model field type fixes
  - **Skills**: [`git-master`]
    - `git-master`: For git commit

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Tasks 4-12
  - **Blocked By**: None (start immediately)

  **References**:
  - `python_opencode/src/opencode/models/agent.py:AgentMode` - Enum definition
  - `python_opencode/src/opencode/models/agent.py:AgentInfo` - Agent model
  - `python_opencode/src/opencode/models/agent.py:ModelConfig` - Model config

  **Acceptance Criteria**:
  - [ ] `mypy src/opencode/models/agent.py` returns 0 errors
  - [ ] No LSP type errors
  - [ ] Agent models can be instantiated

  **Commit**: NO (group with next type fixes)
  - Message: `fix(models): resolve type errors in agent models`

- [ ] 3. Fix type errors in `server/app.py`

  **What to do**:
  - Fix import issues
  - Fix UUID usage
  - Fix async config loading

  **Must NOT do**:
  - Change API routes (breaking change)
  - Remove FastAPI features

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Server type fixes
  - **Skills**: [`git-master`]
    - `git-master`: For git commit

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Tasks 4-12
  - **Blocked By**: None (start immediately)

  **References**:
  - `python_opencode/src/opencode/server/app.py:app` - FastAPI app
  - `python_opencode/src/opencode/config/settings.py:Settings` - Config model
  - `python_opencode/src/opencode/storage/session.py:SessionInfo` - Session model

  **Acceptance Criteria**:
  - [ ] `mypy src/opencode/server/app.py` returns 0 errors
  - [ ] Server can be imported
  - [ ] FastAPI app starts successfully

  **Commit**: YES
  - Message: `fix(server): resolve type errors in FastAPI application`
  - Files: `src/opencode/server/app.py`
  - Pre-commit: `mypy src/opencode/server/app.py`

### Wave 2: EAFP Pattern Replacement

- [ ] 4. Replace LBYL with EAFP in file operations

  **What to do**:
  - Remove `.exists()` checks in file tools
  - Add try/except FileNotFoundError
  - Add try/except IsADirectoryError

  **Must NOT do**:
  - Remove error handling (EAFP still needs exceptions)
  - Change API behavior

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Simple pattern replacements
  - **Skills**: [`git-master`]
    - `git-master`: For git commits

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (Tasks 5-6)
  - **Blocks**: Tasks 7-12
  - **Blocked By**: Tasks 1-3 (type fixes)

  **References**:

  **Pattern References** (Pythonic patterns):
  - `python_opencode/src/opencode/file/read.py:53-58` - Example of EAFP with FileNotFoundError
  - `python_opencode/src/opencode/file/read.py:56-58` - Example of EAFP with IsADirectoryError

  **Files to modify**:
  - `src/opencode/skills/loader.py:105, 125`
  - `src/opencode/file/ls.py:25`
  - `src/opencode/file/grep.py:36`
  - `src/opencode/file/write.py:36`
  - `src/opencode/storage/session.py:45`

  **External References** (Python best practices):
  - PEP 8 - Style guide
  - PEP 20 - Zen of Python ("Easier to Ask for Forgiveness than Permission")

  **WHY Each Reference Matters**:
  - EAFP pattern: More Pythonic than checking before acting
  - file/read.py examples: Shows correct Pythonic pattern to follow

  **Acceptance Criteria**:
  - [ ] No `.exists()` checks in file operations
  - [ ] All file ops wrapped in try/except
  - [ ] Tests still pass (if any exist)

  **Evidence Required**:
  - [ ] Code diff showing EAFP pattern
  - [ ] File operations still work

  **Commit**: YES
  - Message: `refactor: replace LBYL with EAFP in file operations`
  - Files: multiple
  - Pre-commit: `python -m compileall src/opencode`

- [ ] 5. Replace LBYL with EAFP in config loading

  **What to do**:
  - Remove `.exists()` checks in config loading
  - Add try/except for missing config files
  - Use defaults when config missing

  **Must NOT do**:
  - Remove error handling
  - Change default behavior

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Config pattern replacement
  - **Skills**: [`git-master`]
    - `git-master`: For git commits

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (Tasks 4-6)
  - **Blocks**: Tasks 7-12
  - **Blocked By**: Tasks 1-3 (type fixes)

  **References**:
  - `src/opencode/config/loader.py` - Config loading logic
  - `src/opencode/config/settings.py:Settings` - Config defaults

  **Acceptance Criteria**:
  - [ ] No `.exists()` checks in config loading
  - [ ] Missing configs handled gracefully
  - [ ] Default values used correctly

  **Commit**: YES
  - Message: `refactor: replace LBYL with EAFP in config loading`
  - Files: `src/opencode/config/loader.py`
  - Pre-commit: `python -c "from opencode.config import get_settings; get_settings()"`

### Wave 3: Polish

- [ ] 6. Improve exception handling

  **What to do**:
  - Replace broad `except Exception:` with specific types
  - Add custom exception classes for domain errors
  - Create exception hierarchy

  **Must NOT do**:
  - Remove error handling
  - Swallow exceptions silently

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Exception handling improvement
  - **Skills**: [`git-master`]
    - `git-master`: For git commits

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (Tasks 6-8)
  - **Blocks**: Tasks 10-12
  - **Blocked By**: Tasks 4-5 (EAFP replacements)

  **References**:

  **Code to modify**:
  - `src/opencode/runtime/clock.py:43` - Broad exception catch

  **Pattern to follow**:
  ```python
  # Non-Pythonic
  try:
      risky_operation()
  except Exception:  # Too broad
      handle_error()

  # Pythonic
  try:
      risky_operation()
  except (SpecificError1, SpecificError2) as e:  # Specific exceptions
      handle_error(e)
  ```

  **Acceptance Criteria**:
  - [ ] No `except Exception:` without specific type
  - [ ] Custom exceptions defined
  - [ ] All exceptions handled appropriately

  **Commit**: YES
  - Message: `refactor: improve exception handling with specific types`
  - Files: `src/opencode/runtime/clock.py`

- [ ] 7. Add missing type hints

  **What to do**:
  - Add return type annotations to functions
  - Add parameter type hints where missing
  - Ensure all public APIs are typed

  **Must NOT do**:
  - Change function signatures (breaking change)
  - Remove existing valid hints

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Type hint additions
  - **Skills**: [`git-master`]
    - `git-master`: For git commits

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (Tasks 7-9)
  - **Blocks**: Tasks 10-12
  - **Blocked By**: Tasks 4-6 (pattern replacements)

  **Files to review** (all python_opencode/src/opencode/):
  - Multiple files with missing return annotations

  **Acceptance Criteria**:
  - [ ] All functions have return type hints
  - [ ] mypy passes for modified files
  - [ ] LSP shows no type errors

  **Commit**: YES
  - Message: `refactor: add missing type hints across codebase`
  - Files: multiple
  - Pre-commit: `mypy src/opencode`

- [ ] 8. Reorganize imports

  **What to do**:
  - Move all imports to top of files
  - Remove mid-function imports
  - Organize by type (stdlib, third-party, local)

  **Must NOT do**:
  - Change what's imported (break imports)
  - Remove necessary imports

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Import reorganization
  - **Skills**: [`git-master`]
    - `git-master`: For git commits

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (Tasks 7-9)
  - **Blocks**: Tasks 10-12
  - **Blocked By**: Tasks 4-6 (pattern replacements)

  **Files to modify**:
  - `src/opencode/file/read.py` - Mid-function import
  - `src/opencode/file/write.py` - Likely mid-function imports

  **Import organization standard**:
  ```python
  # PEP 8 order
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
  ```

  **Acceptance Criteria**:
  - [ ] No mid-function imports
  - [ ] All imports at top level
  - [ ] Imports organized by PEP 8
  - [ ] Code runs without import errors

  **Commit**: YES
  - Message: `refactor: reorganize imports following PEP 8`
  - Files: multiple
  - Pre-commit: `python -c "from opencode.file import read, write; print('OK')"`

- [ ] 9. Add `__all__` exports

  **What to do**:
  - Add `__all__` to modules
  - Control public API
  - Document public vs private

  **Must NOT do**:
  - Export internal implementation details
  - Break existing imports

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Export control
  - **Skills**: [`git-master`]
    - `git-master`: For git commits

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (Tasks 7-9)
  - **Blocks**: Tasks 10-12
  - **Blocked By**: Tasks 4-6 (pattern replacements)

  **Modules to add `__all__`**:
  - `src/opencode/tool/__init__.py`
  - `src/opencode/agent/__init__.py`
  - `src/opencode/models/__init__.py`
  - Other public modules

  **Pattern**:
  ```python
  __all__ = ["PublicClass1", "PublicClass2", "public_function"]
  ```

  **Acceptance Criteria**:
  - [ ] All public modules have `__all__`
  - [ ] Only documented exports included
  - [ ] `from module import *` works correctly

  **Commit**: YES
  - Message: `refactor: add __all__ to control public API exports`
  - Files: multiple
  - Pre-commit: `python -c "from opencode import *; print('Should fail')"`

### Wave 4: Verification & Documentation

- [ ] 10. Run mypy type checking

  **What to do**:
  - Run `mypy src/opencode --strict`
  - Fix any remaining errors
  - Ensure zero mypy errors

  **Must NOT do**:
  - Skip mypy checks
  - Ignore type errors

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Type checking
  - **Skills**: [`git-master`]
    - `git-master`: For git commit

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (Tasks 10-11)
  - **Blocks**: Task 12
  - **Blocked By**: Tasks 7-9 (polishing)

  **Acceptance Criteria**:
  - [ ] `mypy src/opencode` returns 0 errors
  - [ ] All modules pass type checking
  - [ ] No type warnings

  **Evidence Required**:
  - [ ] Terminal output showing 0 mypy errors
  - [ ] Screenshot of mypy output

  **Commit**: YES
  - Message: `test: mypy type checking - all modules pass`
  - Files: None (type check only)
  - Pre-commit: `mypy src/opencode --strict`

- [ ] 11. Run ruff style checking

  **What to do**:
  - Run `ruff check src/opencode`
  - Fix any style violations
  - Ensure PEP 8 compliance

  **Must NOT do**:
  - Skip style checks
  - Ignore PEP 8 violations

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Style checking
  - **Skills**: [`git-master`]
    - `git-master`: For git commit

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (Tasks 10-11)
  - **Blocks**: Task 12
  - **Blocked By**: Tasks 7-9 (polishing)

  **Acceptance Criteria**:
  - [ ] `ruff check` returns 0 errors
  - [ ] No PEP 8 violations
  - [ ] Code style consistent

  **Evidence Required**:
  - [ ] Terminal output of ruff check
  - [ ] Screenshot of output

  **Commit**: YES
  - Message: `style: ruff linting - codebase PEP 8 compliant`
  - Files: any files modified
  - Pre-commit: `ruff check src/opencode`

- [ ] 12. Create Pythonic patterns documentation

  **What to do**:
  - Document Pythonic patterns used
  - Explain EAFP vs LBYL
  - Create examples of Pythonic vs non-Pythonic
  - Add to `.sisyphus/docs/` directory

  **Must NOT do**:
  - Document non-Pythonic patterns
  - Add irrelevant examples

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation creation
  - **Skills**: None needed

  - **Skills Evaluated but Omitted**:
    - None - documentation task

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (final task)
  - **Blocks**: None
  - **Blocked By**: Tasks 10-11 (verification)

  **Documentation to create**:
  1. `.sisyphus/docs/pythonic-patterns.md` - Patterns guide
  2. Include before/after examples
  3. Reference to PEPs
  4. Style guide snippets

  **Content sections**:
  - EAFP pattern explanation
  - Type hints best practices
  - Exception handling patterns
  - Import organization
  - Context managers
  - Generators and iteration

  **Acceptance Criteria**:
  - [ ] Documentation file created
  - [ ] All major patterns explained
  - [ ] Code examples provided

  **Commit**: YES
  - Message: `docs: add Pythonic patterns and best practices guide`
  - Files: `.sisyphus/docs/pythonic-patterns.md`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1, 2, 3 | `fix(types): resolve type errors in core modules` | `tool/__init__.py`, `models/agent.py`, `server/app.py` | `mypy <files>` |
| 4, 5 | `refactor: replace LBYL with EAFP pattern` | All modified files | `python -m compileall src/opencode` |
| 6 | `refactor: improve exception handling` | `runtime/clock.py` | `python -c "from opencode.runtime.clock import Clock; Clock()" |
| 7 | `refactor: add missing type hints` | Multiple files | `mypy src/opencode` |
| 8 | `refactor: reorganize imports following PEP 8` | Multiple files | `python -c "test imports"` |
| 9 | `refactor: add __all__ to control exports` | Multiple files | `python -c "from module import *"` |
| 10 | `test: mypy type checking - all modules pass` | None | `mypy src/opencode --strict` |
| 11 | `style: ruff linting - codebase PEP 8 compliant` | Any style fixes | `ruff check src/opencode` |
| 12 | `docs: add Pythonic patterns and best practices guide` | `.sisyphus/docs/pythonic-patterns.md` | Read docs file |

---

## Success Criteria

### Verification Commands
```bash
# Type checking
mypy src/opencode --strict
# Expected: Success (0 errors)

# Style checking
ruff check src/opencode
# Expected: Success (0 errors)

# Import tests
python -c "from opencode.tool import ToolRegistry; from opencode.agent import create_global_registry; from opencode.config import get_settings; print('All imports successful')"
# Expected: "All imports successful"
```

### Final Checklist
- [ ] All mypy errors resolved
- [ ] Zero ruff style errors
- [ ] No LBYL patterns remain
- [ ] All imports at top level
- [ ] All functions have type hints
- [ ] Custom exceptions defined
- [ ] `__all__` exports added
- [ ] Documentation created
- [ ] Code is Pythonic and readable

---

## Appendix: Pythonic Patterns Reference

### EAFP (Easier to Ask for Forgiveness than Permission)

**Non-Pythonic (LBYL):**
```python
if file_path.exists():
    with open(file_path) as f:
        return f.read()
else:
    raise FileNotFoundError
```

**Pythonic (EAFP):**
```python
try:
    with open(file_path) as f:
        return f.read()
except FileNotFoundError:
    # Handle missing file
```

### Context Managers

**Non-Pythonic:**
```python
file = open(path)
try:
    data = file.read()
finally:
    file.close()
```

**Pythonic:**
```python
with open(path) as f:
    data = f.read()
# File automatically closed
```

### Type Hints

**Non-Pythonic:**
```python
def process(data):
    return data.upper()
```

**Pythonic:**
```python
def process(data: str) -> str:
    return data.upper()
```

### Comprehensions

**Non-Pythonic:**
```python
result = []
for item in items:
    result.append(transform(item))
```

**Pythonic:**
```python
result = [transform(item) for item in items]
```

### Generators

**Non-Pythonic:**
```python
def get_items():
    items = []
    for item in source:
        items.append(transform(item))
    return items
```

**Pythonic:**
```python
def get_items():
    for item in source:
        yield transform(item)
```

### Exception Hierarchy

**Non-Pythonic:**
```python
try:
    risky_operation()
except Exception:  # Too broad
    handle_error()
```

**Pythonic:**
```python
class FileOperationError(Exception):
    pass

class FileNotFoundError(FileOperationError):
    pass

try:
    risky_operation()
except (FileNotFoundError, PermissionError) as e:  # Specific
    handle_error(e)
```

### Dataclasses vs Classes

**Non-Pythonic:**
```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __repr__(self):
        return f"Point({self.x}, {self.y})"
```

**Pythonic:**
```python
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float
    # __repr__ generated automatically
```

### F-strings vs Concatenation

**Non-Pythonic:**
```python
message = "Hello " + name + ", welcome!"
```

**Pythonic:**
```python
message = f"Hello {name}, welcome!"
```
