# Migration Guide

This guide helps you migrate your Dawn Kestrel code to the refactored architecture. The refactor improves extensibility, testability, and error handling through several key changes.

## Table of Contents

- [Overview](#overview)
- [Breaking Changes](#breaking-changes)
- [Step-by-Step Upgrade Checklist](#step-by-step-upgrade-checklist)
- [API Migration Examples](#api-migration-examples)
- [Handler Injection Deprecations](#handler-injection-deprecations)
- [Plugin Discovery Migration](#plugin-discovery-migration)
- [Result Pattern Migration](#result-pattern-migration)
- [Storage/Repository Wiring Migration](#storagerepository-wiring-migration)
- [Troubleshooting](#troubleshooting)

## Overview

The Dawn Kestrel refactor introduces these major changes:

### Completed Changes (Waves 1-4)

- ✅ **Repository Pattern**: Storage layer abstracted behind repository interfaces
- ✅ **Result Pattern**: All SDK methods return `Result[T]` instead of raising exceptions
- ✅ **Configuration Object**: Settings singleton replaced with instance methods
- ✅ **Plugin Discovery**: Tools, providers, and agents discovered via `entry_points`
- ✅ **Repository Injection**: Services require explicit repository dependencies

### In Progress

- ⏳ **Reliability Patterns**: Circuit breaker, bulkhead, retry, rate limiter
- ⏳ **Cross-Cutting Concerns**: Decorators for logging, metrics, caching

## Breaking Changes

### 1. Result Type Returns (Exception Handling)

**Impact**: High

All public SDK methods now return `Result[T]` instead of raising exceptions. You must handle Results explicitly.

### 2. Storage Path Accessor

**Impact**: Low

Changed from `Path(settings.storage_dir).expanduser()` to `settings.storage_dir_path()`.

### 3. Repository Injection

**Impact**: Medium

`DefaultSessionService` now requires repository parameters instead of a single `storage=` parameter.

### 4. Plugin Registration

**Impact**: Medium

Custom tools/providers/agents must use `entry_points` instead of runtime registration.

### 5. Dependency Injection Container

**Impact**: Low

Manual dependency wiring replaced with DI container for centralized service management.

### 6. Facade API

**Impact**: Low (Optional)

New Facade pattern provides simplified API over complex subsystems (optional enhancement).

### 7. Handler Injection (Null Object Pattern)

**Impact**: Low

Handler parameters no longer require null checks - Null handlers provide safe defaults.

### 8. AgentResult Constructor

**Impact**: Low

AgentResult now requires `agent_name` as first positional parameter.

### 9. Static Registries Removed

**Impact**: Medium

`TOOL_FACTORIES`, `PROVIDER_FACTORIES` static dicts removed - use plugin discovery.

## Step-by-Step Upgrade Checklist

- [ ] **Phase 1**: Update Result handling in SDK calls
- [ ] **Phase 2**: Update storage path accessors
- [ ] **Phase 3**: Update service wiring to use repositories
- [ ] **Phase 4**: Migrate custom components to entry points
- [ ] **Phase 5**: Update handler injection (if using custom handlers)
- [ ] **Phase 6**: Run tests and verify

## Dependency Injection Container Changes

### What Changed

**Old Pattern**: Manual dependency wiring
```python
# Old - manual wiring
from dawn_kestrel.storage.store import SessionStorage
from dawn_kestrel.core.repositories import SessionRepositoryImpl, MessageRepositoryImpl
from dawn_kestrel.core.services import DefaultSessionService

storage = SessionStorage(base_dir=Path("/storage"))
session_repo = SessionRepositoryImpl(storage)
message_repo = MessageRepositoryImpl(storage)
service = DefaultSessionService(
    session_repo=session_repo,
    message_repo=message_repo,
    part_repo=part_repo,
)
```

**New Pattern**: DI container with lazy initialization
```python
# New - DI container
from dawn_kestrel.core.di_container import configure_container

container = configure_container(
    storage_path=Path("/storage"),
    project_dir=Path("/project"),
)

# Services created lazily on first access
service = container.service()
```

### Why It Changed

- Eliminates manual dependency management
- Enables lazy initialization
- Centralized dependency wiring
- Easier testing with mock injection

### Migration Path

1. **Identify manual dependency creation** in your code
2. **Create DI container** with `configure_container()`
3. **Replace manual wiring** with container access
4. **Verify lazy initialization** - services created only when accessed

### Before/After Example

```python
# Before - manual wiring
from dawn_kestrel.storage.store import SessionStorage
from dawn_kestrel.core.repositories import SessionRepositoryImpl, MessageRepositoryImpl
from dawn_kestrel.core.services import DefaultSessionService

storage = SessionStorage(base_dir=Path.cwd())
session_repo = SessionRepositoryImpl(storage)
message_repo = MessageRepositoryImpl(storage)
service = DefaultSessionService(
    session_repo=session_repo,
    message_repo=message_repo,
    part_repo=part_repo,
)

# After - DI container
from dawn_kestrel.core.di_container import configure_container

container = configure_container(
    storage_path=Path.cwd(),
    project_dir=Path.cwd(),
)
service = container.service()
```

### Key Providers Available

```python
from dawn_kestrel.core.di_container import configure_container

container = configure_container(
    storage_path=Path("/storage"),
    project_dir=Path("/project"),
)

# Access services (lazy initialization)
service = container.service()          # DefaultSessionService
session_repo = container.session_repo()  # SessionRepositoryImpl
message_repo = container.message_repo()  # MessageRepositoryImpl
part_repo = container.part_repo()       # PartRepositoryImpl

# Configuration
config = container.config.storage_path()
storage_dir = container.storage_dir()
```

## Facade API Changes

### What Changed

**New Pattern**: Facade provides simplified API over complex subsystems

```python
# New - Facade pattern (optional enhancement)
from dawn_kestrel.core.facade import FacadeImpl
from dawn_kestrel.core.di_container import configure_container

container = configure_container()
facade = FacadeImpl(container)

# Simple API without manual dependency wiring
result = await facade.create_session("My Project")
if result.is_ok():
    session = result.unwrap()
    print(f"Created session: {session.id}")
```

### Why It Changed

- Hides complexity of DI container and repositories
- Provides simple interface for common SDK operations
- Normalizes errors from services into user-friendly format
- Lazy initialization through DI container

### Facade API Available

```python
# Session management
async def create_session(title: str) -> Result[Session]
async def get_session(session_id: str) -> Result[Session | None]
async def list_sessions() -> Result[list[Session]]
async def delete_session(session_id: str) -> Result[bool]

# Message management
async def add_message(session_id: str, role: str, content: str) -> Result[str]

# Agent execution
async def execute_agent(
    agent_name: str,
    session_id: str,
    user_message: str,
    options: Optional[Dict[str, Any]] = None,
) -> Result[AgentResult]

# Provider management
async def register_provider(
    provider_id: str,
    config: Dict[str, Any],
) -> Result[ProviderConfig]
async def get_provider(provider_id: str) -> Result[Optional[ProviderConfig]]
async def list_providers() -> Result[list[Dict[str, Any]]]
```

### Migration Path

**This is an optional enhancement** - existing code continues to work.

1. **Create DI container** with `configure_container()`
2. **Initialize Facade** with container
3. **Replace complex service calls** with facade methods
4. **Handle Result returns** from facade methods

### Before/After Example

```python
# Before - manual service access
from dawn_kestrel.core.di_container import configure_container

container = configure_container(
    storage_path=Path("/storage"),
    project_dir=Path("/project"),
)

service = container.service()
result = await service.create_session("My Project")

# After - Facade (simpler API)
from dawn_kestrel.core.facade import FacadeImpl
from dawn_kestrel.core.di_container import configure_container

container = configure_container(
    storage_path=Path("/storage"),
    project_dir=Path("/project"),
)

facade = FacadeImpl(container)
result = await facade.create_session("My Project")
```

### Benefits

- **Simpler API**: No manual DI container access
- **Less boilerplate**: Direct method calls instead of service wiring
- **Error normalization**: Facade converts service errors to user-friendly messages
- **Lazy initialization**: Services created only when needed

## API Migration Examples

### SDK `create_session` Result Handling

#### Before (Exception-based)

```python
from dawn_kestrel.sdk import OpenCodeAsyncClient

client = OpenCodeAsyncClient()

try:
    session = await client.create_session("My Session")
    print(f"Created: {session.id}")

    try:
        message_id = await client.add_message(session.id, "Hello!")
        print(f"Message: {message_id}")
    except Exception as e:
        print(f"Failed to add message: {e}")

except Exception as e:
    print(f"Failed to create session: {e}")
```

#### After (Result-based)

```python
from dawn_kestrel.sdk import OpenCodeAsyncClient

client = OpenCodeAsyncClient()

# Create session - returns Result[Session]
session_result = await client.create_session("My Session")

if session_result.is_ok():
    session = session_result.value
    print(f"Created: {session.id}")

    # Add message - returns Result[str]
    message_result = await client.add_message(session.id, "Hello!")

    if message_result.is_ok():
        message_id = message_result.value
        print(f"Message: {message_id}")
    else:
        print(f"Failed to add message: {message_result.error}")
else:
    print(f"Failed to create session: {session_result.error}")
```

### CLI Service Wiring: storage= to repository injection

#### Before (storage parameter)

```python
from dawn_kestrel.core.services.session_service import DefaultSessionService
from dawn_kestrel.storage.store import SessionStorage
from dawn_kestrel.core.settings import settings

storage_dir = Path(settings.storage_dir).expanduser()
storage = SessionStorage(storage_dir)

service = DefaultSessionService(
    storage=storage,
    io_handler=io_handler,
    progress_handler=progress_handler,
    notification_handler=notification_handler,
)

sessions = await service.list_sessions()
```

#### After (repository injection)

```python
from dawn_kestrel.core.services.session_service import DefaultSessionService
from dawn_kestrel.storage.store import SessionStorage, MessageStorage, PartStorage
from dawn_kestrel.core.repositories import (
    SessionRepositoryImpl,
    MessageRepositoryImpl,
    PartRepositoryImpl,
)
from dawn_kestrel.core.settings import settings

storage_dir = settings.storage_dir_path()

# Create storages
session_storage = SessionStorage(storage_dir)
message_storage = MessageStorage(storage_dir)
part_storage = PartStorage(storage_dir)

# Build repositories
session_repo = SessionRepositoryImpl(session_storage)
message_repo = MessageRepositoryImpl(message_storage)
part_repo = PartRepositoryImpl(part_storage)

# Inject repositories
service = DefaultSessionService(
    session_repo=session_repo,
    message_repo=message_repo,
    part_repo=part_repo,
    io_handler=io_handler,
    progress_handler=progress_handler,
    notification_handler=notification_handler,
)

# List sessions - now returns Result[list[Session]]
result = await service.list_sessions()
if result.is_ok():
    sessions = result.unwrap()
else:
    print(f"Error: {result.error}")
```

### Storage Path Accessor Update

#### Before

```python
from pathlib import Path
from dawn_kestrel.core.settings import settings

storage_dir = Path(settings.storage_dir).expanduser()
```

#### After

```python
from dawn_kestrel.core.settings import settings

# settings.storage_dir_path() returns Path with expanduser() called
storage_dir = settings.storage_dir_path()
```

## Configuration Object Changes

### What Changed

**Old Pattern**: Settings singleton with manual path expansion
```python
# Old - settings singleton
from dawn_kestrel.core.settings import settings

storage_dir = Path(settings.storage_dir).expanduser()
config_dir = Path(settings.config_dir).expanduser()
```

**New Pattern**: Helper methods with built-in expansion
```python
# New - helper methods
from dawn_kestrel.core.settings import settings

storage_dir = settings.storage_dir_path()
config_dir = settings.config_dir_path()
```

### Why It Changed

- Encapsulates path expansion logic
- Consistent accessor pattern
- Type-safe with Pydantic validation
- Removes redundant `.expanduser()` calls

### Migration Path

1. **Find all uses** of `Path(settings.storage_dir).expanduser()`
2. **Replace with** `settings.storage_dir_path()`
3. **Find all uses** of `Path(settings.config_dir).expanduser()`
4. **Replace with** `settings.config_dir_path()`

### Before/After Example

```python
# Before - manual expansion
from pathlib import Path
from dawn_kestrel.core.settings import settings

storage = SessionStorage(
    base_dir=Path(settings.storage_dir).expanduser()
)

config_path = Path(settings.config_dir).expanduser() / "config.json"

# After - helper methods
from dawn_kestrel.core.settings import settings

storage = SessionStorage(
    base_dir=settings.storage_dir_path()
)

config_path = settings.config_dir_path() / "config.json"
```

### Backward Compatibility

Deprecated functions still work (but may emit warnings):

```python
# Deprecated - still works but warns
storage_dir = settings.get_storage_dir()
config_dir = settings.get_config_dir()

# Preferred - use new methods
storage_dir = settings.storage_dir_path()
config_dir = settings.config_dir_path()
```

## Handler Injection Changes (Null Object Pattern)

### What Changed

**Old Pattern**: Handler constructors with explicit parameters and null checks
```python
# Old - explicit handler injection with null checks
async def execute_command(handler: IOHandler | None = None):
    if handler is None:
        handler = IOHandler()  # Default

    # Use handler with null checks
    if handler is not None:
        result = await handler.prompt("Continue?")
        if result == "yes":
            # ...
            pass
```

**New Pattern**: Null handlers as defaults - no null checks needed
```python
# New - null object pattern
from dawn_kestrel.core.null_object import get_null_handler

async def execute_command(handler: IOHandler | None = None):
    handler = get_null_handler("io", handler)  # Returns NullIOHandler if None

    # Use handler directly - no null checks needed
    result = await handler.prompt("Continue?")
    if result == "yes":
        # ...
        pass
```

### Why It Changed

- Eliminates null checks for optional dependencies
- Provides safe default implementations that do nothing
- Simplifies handler injection
- Consistent with Null Object pattern

### Migration Path

1. **Find handler parameters** that may be `None`
2. **Wrap with `get_null_handler()`** for null safety
3. **Remove `if handler is not None` checks** throughout code
4. **Use null handlers directly** - they're safe no-ops

### Null Handler Behavior

**NullIOHandler**:
- `prompt(message, default)` → Returns default (or empty string)
- `confirm(message, default)` → Returns default
- `select(message, options)` → Returns first option (or empty string)

**NullProgressHandler**:
- `start(operation, total)` → No-op
- `update(current, message)` → No-op
- `complete(message)` → No-op

**NullNotificationHandler**:
- `show(notification)` → No-op

### Before/After Example

```python
# Before - null checks everywhere
io_handler = IOHandler(...)
progress_handler = ProgressHandler(...)
notification_handler = NotificationHandler(...)

client = OpenCodeAsyncClient(
    io_handler=io_handler,
    progress_handler=progress_handler,
    notification_handler=notification_handler,
)

async def some_function(handler: IOHandler | None = None):
    if handler is None:
        handler = IOHandler()
    # Use with null checks
    if handler is not None:
        result = await handler.prompt("Continue?")
        # ...

# After - null object pattern
from dawn_kestrel.core.null_object import get_null_handler

io_handler = get_null_handler("io", io_handler or None)  # NullIOHandler if None
progress_handler = get_null_handler("progress", progress_handler or None)
notification_handler = get_null_handler("notification", notification_handler or None)

client = OpenCodeAsyncClient(
    io_handler=io_handler,
    progress_handler=progress_handler,
    notification_handler=notification_handler,
)

async def some_function(handler: IOHandler | None = None):
    handler = get_null_handler("io", handler)  # Safe null handling

    # Use directly - no null checks
    result = await handler.prompt("Continue?")
    # ...
```

## Handler Injection Deprecations

### Handler Parameters

The `io_handler`, `progress_handler`, and `notification_handler` parameters are still supported in `DefaultSessionService`, but they now work with Null Object pattern.

**What breaks if you don't migrate**:
- Potential crashes when handlers are `None`
- Need for manual null checks throughout code

**Migration path**:
```python
# Recommended - use null object pattern
from dawn_kestrel.core.null_object import get_null_handler

io_handler = get_null_handler("io", None)
progress_handler = get_null_handler("progress", None)
notification_handler = get_null_handler("notification", None)

service = DefaultSessionService(
    session_repo=session_repo,
    message_repo=message_repo,
    part_repo=part_repo,
    io_handler=io_handler,
    progress_handler=progress_handler,
    notification_handler=notification_handler,
)

# Or use DI container for automatic null handling
from dawn_kestrel.core.di_container import configure_container

container = configure_container()
service = container.service()  # Handlers auto-created as null objects
```

## Plugin Discovery Migration

### Custom Tool Registration

#### Before (Runtime registration)

```python
from dawn_kestrel.tools import register_tool

# This no longer works
@register_tool("my_tool")
class MyTool:
    # ...
```

#### After (Entry points)

Add to your `pyproject.toml`:

```toml
[project.entry-points."dawn_kestrel.tools"]
"my_tool" = "my_package.tools:MyTool"
```

### Custom Provider Registration

#### Before (Runtime registration)

```python
from dawn_kestrel.providers import register_provider_factory

# This no longer works
@register_provider_factory("my_provider")
def my_provider_factory(config):
    # ...
```

#### After (Entry points)

Add to your `pyproject.toml`:

```toml
[project.entry-points."dawn_kestrel.providers"]
"my_provider" = "my_package.providers:MyProvider"
```

### Custom Agent Registration

#### Before (Runtime registration)

```python
from dawn_kestrel.agents import register_agent

# This no longer works
@register_agent("my_agent")
class MyAgent:
    # ...
```

#### After (Entry points)

Add to your `pyproject.toml`:

```toml
[project.entry-points."dawn_kestrel.agents"]
"my_agent" = "my_package.agents:MyAgent"
```

**What breaks if you don't migrate**:
- `register_tool`, `register_provider_factory`, and `register_agent` functions removed
- Runtime registration no longer works
- Custom components must use entry points

## Result Pattern Migration

### Understanding Result Types

The Result type is a union of `Ok[T]`, `Err[E]`, and `Pass[T]`:

```python
from dawn_kestrel.core.result import Ok, Err

# Success
result = Ok(session_id)
assert result.is_ok()
assert result.value == session_id

# Error
result = Err("Session not found", code="NOT_FOUND")
assert result.is_err()
assert result.error == "Session not found"
```

### Working with Results

#### Basic Pattern

```python
result = await client.create_session("My Session")

if result.is_ok():
    session = result.value
    print(f"Created: {session.id}")
else:
    print(f"Error: {result.error}")
```

#### Chaining with `bind` and `map`

```python
from dawn_kestrel.core.result import bind, map

def validate_title(title: str):
    if not title or len(title) < 3:
        return Err("Title too short", code="INVALID_TITLE")
    return Ok(title)

# Chain operations
result = (Ok("My Session")
    .bind(validate_title)
    .bind(lambda t: client.create_session(t)))

if result.is_ok():
    session = result.value
else:
    print(f"Error: {result.error}")
```

### Error Codes

Results include error codes for programmatic handling:

```python
result = await client.create_session("")

if result.is_err():
    match result.code:
        case "INVALID_TITLE":
            print("Title is invalid")
        case "STORAGE_ERROR":
            print("Storage failure")
        case _:
            print(f"Unknown error: {result.error}")
```

## Storage/Repository Wiring Migration

### Direct Service Instantiation

#### Before

```python
from dawn_kestrel.core.services.session_service import DefaultSessionService
from dawn_kestrel.storage.store import SessionStorage

storage_dir = Path(settings.storage_dir).expanduser()
service = DefaultSessionService(
    storage=storage_dir,
)
```

#### After

```python
from dawn_kestrel.core.services.session_service import DefaultSessionService
from dawn_kestrel.storage.store import SessionStorage, MessageStorage, PartStorage
from dawn_kestrel.core.repositories import (
    SessionRepositoryImpl,
    MessageRepositoryImpl,
    PartRepositoryImpl,
)
from dawn_kestrel.core.settings import settings

storage_dir = settings.storage_dir_path()

session_repo = SessionRepositoryImpl(SessionStorage(storage_dir))
message_repo = MessageRepositoryImpl(MessageStorage(storage_dir))
part_repo = PartRepositoryImpl(PartStorage(storage_dir))

service = DefaultSessionService(
    session_repo=session_repo,
    message_repo=message_repo,
    part_repo=part_repo,
)
```

### Using DI Container

#### Before

```python
from dawn_kestrel.core.services.session_service import DefaultSessionService
from dawn_kestrel.storage.store import SessionStorage

service = DefaultSessionService(
    storage=SessionStorage(storage_dir),
)
```

#### After

```python
from dawn_kestrel.core.di_container import container

# Container handles all wiring
service = container.service()
```

**Benefits of DI container**:
- No manual wiring required
- Lazy initialization
- Easy to mock for testing
- Centralized configuration

### Repository Methods Return Results

All repository methods now return `Result[T]`:

```python
# SessionRepository
await session_repo.add(session)         # -> Result[None]
await session_repo.get(session_id)     # -> Result[Session | None]
await session_repo.list()              # -> Result[list[Session]]
await session_repo.delete(session_id)   # -> Result[bool]

# MessageRepository
await message_repo.add(message)         # -> Result[str]
await message_repo.get(message_id)     # -> Result[Message]
await message_repo.list(session_id)    # -> Result[list[Message]]

# PartRepository
await part_repo.add(part)              # -> Result[str]
await part_repo.get(part_id)           # -> Result[Part]
await part_repo.list(message_id)       # -> Result[list[Part]]
```

## Other Minor Breaking Changes

### AgentResult Constructor Changes

**Old Pattern**:
```python
from dawn_kestrel.agents.base import AgentResult

agent_result = AgentResult(
    response=response,
    parts=parts,
    metadata=metadata,
    tools_used=tools_used,
    duration=5.2,  # Duration in seconds
)
```

**New Pattern**:
```python
from dawn_kestrel.agents.base import AgentResult

agent_result = AgentResult(
    agent_name="build",  # NEW: required positional parameter
    response=response,
    parts=parts,
    metadata=metadata,
    tools_used=tools_used,
    duration=5.2,  # Still float in seconds
    error=None,
)
```

**Breaking Changes**:
- **Added**: `agent_name` positional parameter (required)
- **Unchanged**: `duration` is float in seconds

### create_complete_registry() Removed

**Old Pattern**:
```python
from dawn_kestrel.tools import create_complete_registry

registry = await create_complete_registry()
tool = registry.get('bash')
```

**New Pattern**:
```python
from dawn_kestrel.core.plugin_discovery import load_tools

tools = await load_tools()
tool = tools.get('bash')

# Or if you need ToolRegistry:
from dawn_kestrel.core.plugin_discovery import get_all_tools
from dawn_kestrel.tools.registry import ToolRegistry

tool_dict = await get_all_tools()
registry = ToolRegistry()
registry.tools = tool_dict
```

### Static Registries Removed

**Old Pattern**:
```python
from dawn_kestrel.tools import TOOL_FACTORIES
from dawn_kestrel.providers import PROVIDER_FACTORIES

# Static registration
if 'bash' in TOOL_FACTORIES:
    tool = TOOL_FACTORIES['bash']()
```

**New Pattern**:
```python
from dawn_kestrel.core.plugin_discovery import load_tools, load_providers

# Plugin discovery
tools = await load_tools()
tool = tools.get('bash')  # Tools already instantiated

providers = await load_providers()
provider_class = providers.get('anthropic')  # Returns class, not instance
```

**Breaking Changes**:
- **Removed**: `TOOL_FACTORIES` static dict
- **Removed**: `PROVIDER_FACTORIES` static dict
- **Removed**: `register_tool_factory()` function
- **Removed**: `register_provider_factory()` function
- **Changed**: `load_tools()` returns `Dict[str, Tool]` (instantiated) instead of factories

### Backward Compatibility Shim

A shim exists for tests that still use the old `create_complete_registry()` API:

```python
from dawn_kestrel.tools import create_complete_registry

# This shim delegates to plugin discovery (for backward compatibility)
registry = await create_complete_registry()
```

### SDK Client Result Normalization

SDK client methods now normalize service returns to always return `Result[T]`:

```python
# Old - service might return raw value
session = await client.get_session(session_id)
if session is None:
    raise SessionError("Session not found")

# New - always returns Result[...]
result = await client.get_session(session_id)
if result.is_err():
    print(f"Error: {result.error}")
    return None

session = result.unwrap()
```

**Normalization Rule**: Client methods wrap non-Result returns in `Ok()`:

```python
# Client normalization (internal implementation)
result = await self._service.get_session(session_id)
if hasattr(result, 'is_ok'):
    return result  # Already a Result
return Ok(result)  # Raw value, wrap in Ok()
```

This ensures backward compatibility with services that might return raw values (e.g., in tests with mocks).

### SessionManager Replaced with Repositories

**Old Pattern**:
```python
from dawn_kestrel.storage.store import SessionStorage
from dawn_kestrel.storage.session_manager import SessionManager

storage = SessionStorage(base_dir=storage_dir)
session_mgr = SessionManager(storage)

session = await session_mgr.add_session(session)
```

**New Pattern**:
```python
from dawn_kestrel.storage.store import SessionStorage
from dawn_kestrel.core.repositories import SessionRepositoryImpl

storage = SessionStorage(base_dir=storage_dir)
session_repo = SessionRepositoryImpl(storage)

result = await session_repo.create(session)
if result.is_ok():
    created_session = result.unwrap()
```

### Result.error Access vs Result.error()

**Important**: Result uses `error` attribute, not `error()` method:

```python
# Wrong - will fail
if result.is_err():
    error_msg = result.error()  # AttributeError: 'Err' object has no attribute 'error()'

# Correct - access as attribute
if result.is_err():
    error_msg = result.error  # Returns string
```

### LSP Type Narrowing Warnings (Expected False Positive)

When accessing `result.error` after `is_err()` check, LSP may show a warning:

```python
result = await service.get_session(session_id)
if result.is_err():
    # LSP warning: "error" not defined on Result type
    print(f"Error: {result.error}")
```

**This is expected** - LSP doesn't understand type narrowing after `is_err()` check.

**Workaround**:
```python
from typing import Any, cast

result = await service.get_session(session_id)
if result.is_err():
    err_result = cast(Any, result)  # Cast to satisfy LSP
    print(f"Error: {err_result.error}")
```

## Troubleshooting

### "Result object has no attribute 'error'"

**Cause**: Trying to access `.error` on an `Ok` result.

**Fix**: Check `is_err()` before accessing error:

```python
# Wrong
result = await client.create_session("...")
print(result.error)  # Error!

# Correct
result = await client.create_session("...")
if result.is_err():
    print(result.error)  # OK
```

### "storage= parameter not accepted"

**Cause**: Passing deprecated `storage=` parameter to `DefaultSessionService`.

**Fix**: Use repository injection:

```python
# Wrong
service = DefaultSessionService(storage=storage_dir)

# Correct
service = DefaultSessionService(
    session_repo=session_repo,
    message_repo=message_repo,
    part_repo=part_repo,
)
```

### "'Path' object has no attribute 'expanduser'"

**Cause**: Already called `expanduser()` but still calling it again.

**Fix**: Use `settings.storage_dir_path()` directly:

```python
# Wrong
storage_dir = settings.storage_dir_path().expanduser()

# Correct - storage_dir_path() already calls expanduser()
storage_dir = settings.storage_dir_path()
```

### "Tool not found in registry"

**Cause**: Custom tools not registered via entry points.

**Fix**: Add entry point to `pyproject.toml`:

```toml
[project.entry-points."dawn_kestrel.tools"]
"my_tool" = "my_package.tools:MyTool"
```

### LSP Type Warnings on `result.error`

**Cause**: LSP doesn't understand type narrowing after `is_err()` check.

**Fix**: Use `cast(Any, result)` to suppress warnings:

```python
from typing import cast, Any

result = await client.create_session("...")
if result.is_err():
    err_result = cast(Any, result)
    print(err_result.error)  # No LSP warning
```

This is a known limitation of type checkers with Result types.

### TypeError: "storage" parameter not accepted

**Cause**: Services now require repository injection instead of `storage=` parameter.

**Fix**:
```python
# Old - storage parameter (no longer works)
service = DefaultSessionService(storage=storage)

# New - repository injection
service = DefaultSessionService(
    session_repo=session_repo,
    message_repo=message_repo,
    part_repo=part_repo,
)
```

### ImportError: "create_complete_registry" not found

**Cause**: Plugin discovery migration removed static registries.

**Fix**: Use plugin discovery:
```python
# Old
from dawn_kestrel.tools import create_complete_registry

# New
from dawn_kestrel.core.plugin_discovery import load_tools

tools = await load_tools()
tool = tools.get('bash')
```

### TypeError on Path operations (unsupported operand types)

**Cause**: Mixing Path and string types incorrectly.

**Fix**:
```python
# Wrong - string + Path
storage_dir = str(settings.storage_dir_path()) + "/sessions"

# Correct - Path / operator
storage_dir = settings.storage_dir_path() / "sessions"
```

### AttributeError: "Result object has no attribute 'error()'" 

**Cause**: Trying to call `error()` as method instead of accessing as attribute.

**Fix**:
```python
# Wrong
error_msg = result.error()  # No such method

# Correct
error_msg = result.error  # Attribute access
```

### ImportError: No module named 'entry_points'

**Cause**: Using Python 3.9 with old importlib.metadata API.

**Fix**: The refactor handles this internally. If you see this error, ensure you're using the latest Dawn Kestrel version with compatibility layer.

### TypeError: "agent_name" missing positional argument

**Cause**: AgentResult constructor now requires `agent_name` as first parameter.

**Fix**:
```python
# Old - missing agent_name
agent_result = AgentResult(response=response, ...)

# New - include agent_name
agent_result = AgentResult(
    agent_name="build",  # Required positional argument
    response=response,
    ...
)
```

### AttributeError: "NoneType has no attribute 'prompt'" (Handler crashes)

**Cause**: Handler parameter is `None` and trying to call methods without null checks.

**Fix**:
```python
# Old - crashes if handler is None
async def execute(handler: IOHandler | None = None):
    result = await handler.prompt("Continue?")  # Crashes if None

# New - use null object pattern
from dawn_kestrel.core.null_object import get_null_handler

async def execute(handler: IOHandler | None = None):
    handler = get_null_handler("io", handler)
    result = await handler.prompt("Continue?")  # Safe even if None
```

### ImportError: No module named 'entry_points'

**Cause**: Using Python 3.9 with old importlib.metadata API.

**Fix**: The refactor handles this internally. If you see this error, ensure you're using the latest Dawn Kestrel version with compatibility layer.

## Additional Resources

- [Architecture Documentation](docs/refactor/architecture.md) - System architecture details
- [Design Patterns](docs/refactor/patterns.md) - 21+ design patterns explained
- [Execution Waves](docs/refactor/execution-waves.md) - Detailed wave execution plans
- [Component Map](docs/refactor/component-map.md) - Component relationships

## What Breaks If You Don't Migrate

If you continue using old patterns, you'll encounter:

### Immediate Failures

| Change | Error | Root Cause |
|---------|--------|-------------|
| Plugin discovery | `ImportError: name 'TOOL_FACTORIES' not defined` | Static registries removed |
| Repository injection | `TypeError: got an unexpected keyword argument 'storage'` | `storage=` parameter removed from service constructors |
| Result attribute access | `AttributeError: 'Err' object has no attribute 'error()'` | `error` is attribute, not method |
| AgentResult constructor | `TypeError: missing required positional argument 'agent_name'` | New required parameter added |
| Path operations | `TypeError: unsupported operand type(s) for /: 'str' and 'str'` | Mixed string/Path types |

### Runtime Errors

| Change | Error | Description |
|---------|--------|-------------|
| Result pattern | `SessionError` not raised | Services no longer raise exceptions - they return `Result[Err]` |
| Handler injection | `AttributeError: 'NoneType' object has no attribute 'prompt'` | Handler is None without null checks |
| Missing repositories | Services fail | Services require `session_repo`, `message_repo`, `part_repo` to initialize |

### LSP Warnings

| Change | Warning | Description |
|---------|----------|-------------|
| Result type narrowing | `'error' not defined on Result type` | LSP doesn't understand type narrowing after `is_err()` check |
| Handler None type | `Possible 'None' value` | Handler may be None (use null object pattern) |

### Maintenance Burden

| Impact | Description |
|---------|-------------|
| Outdated patterns | Code won't benefit from new reliability patterns (circuit breaker, retry, rate limiter) |
| No extensibility | Can't use plugin system for custom tools/providers/agents |
| Harder testing | Without DI container, testing requires manual mocking of all dependencies |
| Increased complexity | Manual dependency wiring makes code harder to maintain and understand |

### Impact Summary Table

| Change | Impact | Migration Effort | What Breaks If Not Migrated |
|--------|--------|------------------|------------------------------|
| Result Pattern | HIGH | Moderate | Exceptions not raised, SDK returns `Result[T]` |
| Repository Injection | MEDIUM | Low | `storage=` parameter not accepted |
| Plugin Discovery | MEDIUM | Low | `TOOL_FACTORIES`, `PROVIDER_FACTORIES` don't exist |
| Configuration Access | LOW | Trivial | Redundant `.expanduser()` calls |
| Handler Injection | LOW | Trivial | Handler crashes when None without null checks |
| Facade API | LOW | Optional | No direct impact - existing code continues to work |
| DI Container | LOW | Low | Manual dependency wiring required |
| AgentResult Constructor | LOW | Trivial | Missing `agent_name` parameter |

## Rollback Strategy

If you encounter issues:

1. **Check git history**: The refactor is committed in waves
2. **Use feature flags**: Some changes can be toggled via environment variables
3. **Report issues**: Include error messages and code snippets

For detailed rollback instructions, see [docs/refactor/migration.md](docs/refactor/migration.md).

## Quick Reference

### Common Migrations

| Old Pattern | New Pattern |
|-------------|-------------|
| `Path(settings.storage_dir).expanduser()` | `settings.storage_dir_path()` |
| `service = DefaultSessionService(storage=storage)` | `service = DefaultSessionService(session_repo=..., message_repo=..., part_repo=...)` |
| `tool = TOOL_FACTORIES['bash']()` | `tools = await load_tools(); tool = tools.get('bash')` |
| `try: session = await service.get_session(id) except SessionError as e: ...` | `result = await service.get_session(id); if result.is_err(): ...` |
| `result.error()` | `result.error` (attribute) |
| `AgentResult(response=...)` | `AgentResult(agent_name="build", response=...)` |
| `handler = None` | `handler = get_null_handler("io", None)` |
| `await create_complete_registry()` | `tools = await load_tools()` |

### Import Changes

| Old Import | New Import |
|------------|------------|
| `from dawn_kestrel.tools import TOOL_FACTORIES` | `from dawn_kestrel.core.plugin_discovery import load_tools` |
| `from dawn_kestrel.providers import PROVIDER_FACTORIES` | `from dawn_kestrel.core.plugin_discovery import load_providers` |
| `from dawn_kestrel.tools import create_complete_registry` | `from dawn_kestrel.core.plugin_discovery import load_tools` |
| `from dawn_kestrel.core.exceptions import SessionError` | No longer needed - use Result pattern |
| `from dawn_kestrel.tools import register_tool_factory` | No longer exists - use entry points |
| `from dawn_kestrel.providers import register_provider_factory` | No longer exists - use entry points |

### Result Pattern Cheatsheet

```python
from dawn_kestrel.core.result import Ok, Err, Pass

# Create results
Ok(value)                               # Success with value
Err("error message", code="CODE")         # Error with message and code
Pass("optional message")                  # Skip operation

# Check result type
result.is_ok()                           # bool - is this Ok?
result.is_err()                          # bool - is this Err?
result.is_pass()                         # bool - is this Pass?

# Extract values
result.unwrap()                          # T - get value (raises if not Ok)
result.unwrap_or(default)                 # T - get value or default
result.error                             # str - error message (only if is_err())
result.code                              # str | None - error code (only if is_err())
result.retryable                         # bool - can retry? (only if is_err())
```

### Composition with Result

```python
from dawn_kestrel.core.result import bind, map_result

# Chain operations
def validate(user: User) -> Result[User]:
    if not user.name:
        return Err("Name required")
    return Ok(user)

result = await create_user("Alice")
validated = bind(result, validate)  # Chains operations

# Transform values
uppercased = map_result(validated, lambda user: user.name.upper())
```

### DI Container Cheatsheet

```python
from dawn_kestrel.core.di_container import configure_container

# Configure container
container = configure_container(
    storage_path=Path("/storage"),
    project_dir=Path("/project"),
)

# Access providers
service = container.service()              # DefaultSessionService
session_repo = container.session_repo()    # SessionRepositoryImpl
message_repo = container.message_repo()    # MessageRepositoryImpl
part_repo = container.part_repo()         # PartRepositoryImpl
```

### Plugin Discovery Cheatsheet

```python
from dawn_kestrel.core.plugin_discovery import load_tools, load_providers, load_agents

# Load plugins
tools = await load_tools()
providers = await load_providers()
agents = await load_agents()

# Use plugins
tool = tools.get('bash')
provider_class = providers.get('anthropic')
agent = agents.get('build')
```

### Entry Points Configuration

```toml
# pyproject.toml
[project.entry-points."dawn_kestrel.tools"]
my_tool = "my_package.tools:MyTool"

[project.entry-points."dawn_kestrel.providers"]
my_provider = "my_package.providers:MyProvider"

[project.entry-points."dawn_kestrel.agents"]
my_agent = "my_package.agents:MyAgent"
```

### Null Object Pattern Cheatsheet

```python
from dawn_kestrel.core.null_object import get_null_handler

# Get null handler
io_handler = get_null_handler("io", None)           # NullIOHandler
progress_handler = get_null_handler("progress", None)  # NullProgressHandler
notification_handler = get_null_handler("notification", None)  # NullNotificationHandler

# Use directly - no null checks needed
result = await io_handler.prompt("Continue?")
```

---

**Last Updated**: February 9, 2026
**Refactor Status**: Waves 1-4 Complete
