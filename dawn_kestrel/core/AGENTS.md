# DAWN KESTREL CORE MODULE

**Generated:** 2026-02-25

## OVERVIEW

Foundational abstractions: FSM workflows, EventBus, DI container, Result types, 12 design patterns.

## WHERE TO LOOK

| Task | File | Key Export |
|------|------|------------|
| State machine | `fsm.py` | `FSMBuilder`, `FSMImpl`, `FSMContext` |
| Error handling | `result.py` | `Ok`, `Err`, `Pass`, `Result` |
| Event pub/sub | `event_bus.py` | `EventBus`, `bus` (singleton) |
| DI container | `di_container.py` | `Container`, `container`, `configure_container` |
| Observer | `observer.py` | `Observer`, `Observable` |
| Mediator | `mediator.py` | `EventMediator`, `Event` |
| Repositories | `repositories.py` | `SessionRepository`, `MessageRepository` |
| Models | `models.py` | `Session`, `Message`, `TextPart`, `ToolPart` |
| Commands | `commands.py` | `Command`, `TransitionCommand` |
| Strategies | `strategies.py` | `RoutingStrategy`, `RenderingStrategy` |
| Unit of Work | `unit_of_work.py` | `UnitOfWork` |
| Facade | `facade.py` | `Facade`, `FacadeImpl` |
| Null Object | `null_object.py` | `NullIOHandler` |

## KEY PATTERNS

```python
# FSM Builder
from dawn_kestrel.core.fsm import FSMBuilder

fsm = (FSMBuilder()
    .with_initial_state("idle")
    .with_transition("idle", "running")
    .with_entry_hook("running", on_enter)
    .with_persistence(repo)
    .build()
    .unwrap())

# Result Types (never raise)
from dawn_kestrel.core.result import Ok, Err, Result

async def operation() -> Result[Data]:
    return Ok(data) if success else Err("failed", code="CODE")

result = operation().bind(process)  # compose with bind/map

# DI Container
from dawn_kestrel.core.di_container import container, configure_container

container = configure_container(storage_path=path)
storage = container.storage()  # lazily initialized

# EventBus (global singleton)
from dawn_kestrel.core.event_bus import bus

unsubscribe = await bus.subscribe("session.created", on_created)
await bus.publish("session.created", {"id": id})

# Protocol-first design
from typing import Protocol, runtime_checkable

@runtime_checkable
class Repository(Protocol[T]):
    async def get_by_id(self, id: str) -> Result[T]: ...
```

## FILE STRUCTURE

```
core/
├── fsm.py              # FSMBuilder, FSMImpl, WorkflowFSMBuilder
├── result.py           # Ok, Err, Pass with bind/map/fold
├── event_bus.py        # Async EventBus + Events constants
├── di_container.py     # dependency-injector Container
├── mediator.py         # EventMediator for domain events
├── observer.py         # Observer/Observable protocol
├── repositories.py     # Session/Message/Part repositories
├── models.py           # Pydantic models
├── commands.py         # Command pattern + CommandQueue
├── strategies.py       # RoutingStrategy, RenderingStrategy
├── unit_of_work.py     # Transactional consistency
├── facade.py           # Simplified SDK API
├── null_object.py      # Null handlers (no-op defaults)
└── decorators.py       # Logging decorators
```

## CONVENTIONS

- **Protocol-first**: `@runtime_checkable Protocol` before implementations
- **Result everywhere**: All fallible ops return `Result[T]`, never raise
- **Async by default**: All I/O and repository methods are async
- **Builder returns Result**: `build()` returns `Result[FSM]`, `.unwrap()` after validation
- **Singletons**: `bus` and `container` are global

## ANTI-PATTERNS

- **NEVER** return `None` for error - use `Err`
- **NEVER** use `except: pass` or bare except
- **NEVER** call `.unwrap()` on unchecked Result
- **NEVER** create new EventBus/Container - use globals
- **NEVER** bypass repository for storage access

## WORKFLOW FSM

Predefined states: `intake`, `plan`, `reason`, `act`, `synthesize`, `check`, `done`

```python
from dawn_kestrel.core.fsm import WorkflowFSMBuilder, FSMBudget

fsm = (WorkflowFSMBuilder()
    .with_budget(FSMBudget(max_iterations=50))
    .build()
    .unwrap())
```
