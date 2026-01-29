# Draft: Pythonic Refactoring Analysis

## User's Goal
Ensure the Python OpenCode implementation is **Pythonic** - using Python idioms, conventions, and design patterns the way Python developers would naturally write them, not just TypeScript translated literally.

## Current Issues Identified

### Non-Pythonic Patterns in Python Code

1. **JavaScript-style loops** instead of comprehensions
   - Current: `for item in items: result.append(transform(item))`
   - Pythonic: `[transform(item) for item in items]`

2. **Missing context managers**
   - Current: Manual resource cleanup
   - Pythonic: `with` statements

3. **Class-heavy** where simple data structures suffice
   - Current: Custom classes for simple data
   - Pythonic: `@dataclass` or `NamedTuple`

4. **Type hints missing or incomplete**
   - Current: Some functions lack type hints
   - Pythonic: Full type hints with TypeVar for generics

5. **LBYL instead of EAFP**
   - Current: Check if file exists before reading
   - Pythonic: Try to read, catch FileNotFoundError

6. **String concatenation** instead of f-strings
   - Current: `"text" + variable`
   - Pythonic: `f"text {variable}"`

7. **Direct dict access** without `.get()`
   - Current: `dict["key"]` causing KeyError
   - Pythonic: `dict.get("key", default)`

8. **List comprehensions** could be generators
   - Current: Building full lists in memory
   - Pythonic: Generator expressions `(x for x in items)`

9. **Custom decorators** when standard library exists
   - Current: Custom validation decorators
   - Pythonic: `functools` decorators

10. **Exception handling** too broad
    - Current: `except Exception:` catching everything
    - Pythonic: Specific exception types

## Areas to Analyze

1. **Type System**
   - Protocol vs ABC usage
   - TypeVar for generics
   - Proper type hints

2. **Data Structures**
   - Dataclasses vs regular classes
   - NamedTuple for immutable records
   - frozenset for immutable collections

3. **Control Flow**
   - Context managers for resources
   - EAFP pattern
   - List/dict/set comprehensions

4. **Async Patterns**
   - Proper async/await usage
   - Async generators
   - Async context managers

5. **Error Handling**
   - Exception hierarchy
   - Custom exception classes
   - Proper exception chaining

6. **Modules & Imports**
   - Proper import organization
   - `__all__` exports
   - Relative imports

7. **Decorators**
   - Property decorators
   - Class/method decorators
   - Parameter validation

8. **Generators & Iteration**
   - Yield expressions
   - Generator expressions
   - itertools usage

9. **File I/O**
   - Pathlib usage
   - Context managers for files
   - Proper encoding handling

10. **API Design**
    - Function signatures
    - Default arguments
    - *args and **kwargs
    - Keyword-only arguments

## Research Needed

- Python PEP 8 (style guide)
- Python PEP 20 (Zen of Python)
- Pythonic design patterns
- Pydantic best practices
- FastAPI best practices
- Asyncio best practices
- Type hints best practices

## Success Criteria

Code should feel natural to Python developers:
- Readable like prose
- Uses built-in features when possible
- Follows Python conventions (PEP 8)
- Leverages type hints properly
- Uses context managers
- Has proper exception handling
- Uses Pythonic data structures
