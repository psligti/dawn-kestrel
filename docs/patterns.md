# Design Patterns in Dawn Kestrel

This document describes the 21 design patterns implemented across the Dawn Kestrel codebase, explaining their purpose, implementation details, and how they work together to provide excellent composition and eliminate blast exposure.

## Overview

Dawn Kestrel implements a comprehensive suite of design patterns organized into three categories:

- **Core Architecture Patterns** (8 patterns): Dependency Injection, Plugin System, Result, Repository, Unit of Work, Facade, Adapter, Mediator, Registry
- **Behavioral Patterns** (6 patterns): Command, Decorator/Proxy, Null Object, Strategy, Observer, State (FSM)
- **Reliability Patterns** (5 patterns): Circuit Breaker, Bulkhead, Retry, Rate Limiter, Configuration Object
- **Structural Patterns** (2 patterns): Composite

These patterns integrate to provide:
- Explicit error handling without exceptions
- Fault tolerance for LLM operations
- Loose coupling between components
- Transactional consistency
- Extensibility through plugins

---

## Core Architecture Patterns

### 1. Dependency Injection Container

**Purpose/Problem:**
Manages service instantiation and wiring, eliminating manual dependency management and enabling lazy initialization.

**Implementation Details:**
- Uses `dependency_injector` library for declarative dependency management
- All services registered as providers (Factory or Singleton)
- Lazy initialization - services created only when first accessed
- Configuration injection through `Configuration` provider
- Lifecycle management with `register_lifecycle()`

**Code Location:**
- `dawn_kestrel/core/di_container.py` - Container definition and wiring
- Tests: `tests/core/test_di_container.py`

**Key Components:**
```python
class Container(containers.DeclarativeContainer):
    # Configuration
    config = providers.Configuration()
    
    # Storage providers
    storage_dir = providers.Factory(lambda: container.config.storage_path() or settings.storage_dir_path())
    storage = providers.Factory(SessionStorage, base_dir=storage_dir)
    
    # Repository providers
    session_repo = providers.Factory(SessionRepositoryImpl, storage=storage)
    message_repo = providers.Factory(MessageRepositoryImpl, storage=message_storage)
    part_repo = providers.Factory(PartRepositoryImpl, storage=part_storage)
    
    # Service provider
    service = providers.Factory(
        DefaultSessionService,
        session_repo=session_repo,
        message_repo=message_repo,
        part_repo=part_repo,
    )
```

**Usage Example:**
```python
from dawn_kestrel.core.di_container import configure_container

# Configure container with runtime values
container = configure_container(
    storage_path=Path("/tmp/storage"),
    project_dir=Path("/my/project"),
)

# Access services (lazy initialization)
service = container.service()
session_repo = container.session_repo()
```

**Integration:**
- Used by Facade pattern to resolve dependencies
- Repositories injected through DI container
- Agent runtime and provider registry wired via DI

---

### 2. Plugin System

**Purpose/Problem:**
Enable runtime discovery and loading of tools, providers, and agents without modifying core code. Eliminates static registration maps and enables third-party extensions.

**Implementation Details:**
- Uses Python `importlib.metadata.entry_points` for plugin discovery
- Three plugin groups: `dawn_kestrel.tools`, `dawn_kestrel.providers`, `dawn_kestrel.agents`
- Fallback to direct imports if entry points unavailable
- Provider plugins always returned as classes (require API key)
- Tool plugins instantiated when possible

**Code Location:**
- `dawn_kestrel/core/plugin_discovery.py` - Plugin discovery system
- `pyproject.toml` - Entry point registrations

**Entry Points in pyproject.toml:**
```toml
[project.entry-points."dawn_kestrel.tools"]
bash = "dawn_kestrel.tools: BashTool"
read = "dawn_kestrel.tools: ReadTool"
# ... 17 additional tools

[project.entry-points."dawn_kestrel.providers"]
anthropic = "dawn_kestrel.providers:AnthropicProvider"
openai = "dawn_kestrel.providers:OpenAIProvider"
zai = "dawn_kestrel.providers:ZAIProvider"
zai_coding_plan = "dawn_kestrel.providers:ZAICodingPlanProvider"

[project.entry-points."dawn_kestrel.agents"]
build = "dawn_kestrel.agents.builtin:BUILD_AGENT"
plan = "dawn_kestrel.agents.builtin:PLAN_AGENT"
# ... agent factories
```

**Usage Example:**
```python
from dawn_kestrel.core.plugin_discovery import load_tools, load_providers, load_agents

# Load all tool plugins
tools = await load_tools()
bash_tool = tools.get('bash')

# Load provider plugins
providers = await load_providers()
anthropic_provider_class = providers.get('anthropic')

# Load agent plugins
agents = await load_agents()
plan_agent = agents.get('plan')
```

**Integration:**
- Tools Registry uses plugin discovery to populate registry
- Provider Registry loads providers via entry points
- Agent Registry discovers agents at runtime
- Custom extensions registered via `pyproject.toml` entry points

---

### 3. Result Pattern (Ok/Err/Pass)

**Purpose/Problem:**
Provides explicit error handling without exceptions. Enables composition, type-safe error propagation, and eliminates try/except scattering throughout codebase.

**Implementation Details:**
- Three result types: `Ok[T]`, `Err`, `Pass`
- Generic over `T` for type-safe value wrapping
- Supports composition via `bind()`, `map_result()`, `fold()`
- JSON serialization/deserialization support
- Type narrowing via `is_ok()`, `is_err()`, `is_pass()` checks
- Error codes and retryable flags on `Err`

**Code Location:**
- `dawn_kestrel/core/result.py` - Result type definitions

**Key Classes:**
```python
class Result(ABC, Generic[T]):
    @abstractmethod
    def is_ok(self) -> bool: ...
    @abstractmethod
    def is_err(self) -> bool: ...
    @abstractmethod
    def is_pass(self) -> bool: ...
    @abstractmethod
    def unwrap(self) -> T: ...

class Ok(Result[T]):
    def __init__(self, value: T): ...
    def is_ok(self) -> bool: return True

class Err(Result[T]):
    def __init__(self, error: str, code: str | None = None, retryable: bool = False): ...
    def is_err(self) -> bool: return True

class Pass(Result[T]):
    def __init__(self, message: str | None = None): ...
    def is_pass(self) -> bool: return True
```

**Usage Example:**
```python
from dawn_kestrel.core.result import Ok, Err, Result, bind

async def create_user(name: str) -> Result[User]:
    if not name:
        return Err("Name is required", code="VALIDATION_ERROR")
    
    return Ok(User(name=name))

# Composition with bind
def validate_name(user: User) -> Result[User]:
    if len(user.name) < 3:
        return Err("Name too short", code="VALIDATION_ERROR")
    return Ok(user)

result = await create_user("Alice")
final_result = bind(result, validate_name)

if final_result.is_ok():
    user = final_result.unwrap()
    print(f"Created user: {user.name}")
```

**Integration:**
- All service methods return `Result[T]` instead of raising exceptions
- Repository pattern uses Result for error handling
- Retry pattern works with Result types
- Facade methods normalize Results for user-friendly errors

---

### 4. Repository Pattern

**Purpose/Problem:**
Provides abstraction layer over storage, separating domain logic from data access. Enables testing with mocks and switching storage implementations.

**Implementation Details:**
- Three repositories: `SessionRepository`, `MessageRepository`, `PartRepository`
- Protocol-based design with `@runtime_checkable` for runtime type checking
- All methods return `Result[T]` for explicit error handling
- Storage implementations (`SessionStorage`, `MessageStorage`, `PartStorage`) wrapped by repositories
- Dict-to-model conversion for storage compatibility

**Code Location:**
- `dawn_kestrel/core/repositories.py` - Repository protocols and implementations

**Repository Protocol:**
```python
@runtime_checkable
class SessionRepository(Protocol):
    async def get_by_id(self, session_id: str) -> Result[Session]: ...
    async def create(self, session: Session) -> Result[Session]: ...
    async def update(self, session: Session) -> Result[Session]: ...
    async def delete(self, session_id: str) -> Result[bool]: ...
    async def list_by_project(self, project_id: str) -> Result[List[Session]]: ...
```

**Implementation:**
```python
class SessionRepositoryImpl:
    def __init__(self, storage: SessionStorage):
        self._storage = storage
    
    async def get_by_id(self, session_id: str) -> Result[Session]:
        try:
            session = await self._storage.get_session(session_id)
            if session is None:
                return Err(f"Session not found: {session_id}", code="NOT_FOUND")
            return Ok(session)
        except Exception as e:
            return Err(f"Failed to get session: {e}", code="STORAGE_ERROR")
```

**Usage Example:**
```python
from dawn_kestrel.core.repositories import SessionRepositoryImpl
from dawn_kestrel.storage.store import SessionStorage

storage = SessionStorage(base_dir=Path("/storage"))
repo = SessionRepositoryImpl(storage)

result = await repo.create(session)
if result.is_ok():
    created = result.unwrap()
    print(f"Created session: {created.id}")
```

**Integration:**
- Unit of Work pattern uses repositories for transactional operations
- SessionService depends on repositories via DI container
- Results from repositories composed in service layer

---

### 5. Unit of Work

**Purpose/Problem:**
Ensures transactional consistency across multiple repository operations. Groups multiple writes into atomic units - all succeed or all fail.

**Implementation Details:**
- Protocol: `UnitOfWork` with `begin()`, `commit()`, `rollback()`, `register_*()`
- Implementation: `UnitOfWorkImpl` with in-memory tracking
- Supports registering sessions, messages, and parts before commit
- Atomic commit - if any operation fails, entire transaction fails
- State validation - prevents operations without `begin()` call

**Code Location:**
- `dawn_kestrel/core/unit_of_work.py` - Unit of Work implementation

**Protocol:**
```python
@runtime_checkable
class UnitOfWork(Protocol):
    async def begin(self) -> Result[None]: ...
    async def commit(self) -> Result[None]: ...
    async def rollback(self) -> Result[None]: ...
    async def register_session(self, session: Session) -> Result[Session]: ...
    async def register_message(self, message: Message) -> Result[Message]: ...
    async def register_part(self, message_id: str, part: Part) -> Result[Part]: ...
```

**Usage Example:**
```python
async def create_session_with_message(uow: UnitOfWork):
    await uow.begin()
    
    session = Session(id="session-1", title="My Session")
    await uow.register_session(session)
    
    message = Message(session_id="session-1", role="user", text="Hello")
    await uow.register_message(message)
    
    result = await uow.commit()
    if result.is_err():
        await uow.rollback()
        return result
    
    return Ok(session)
```

**Integration:**
- Services can use Unit of Work for multi-write operations
- Works with Repository pattern for data access
- Combines with Result pattern for explicit error handling

---

### 6. Adapter Pattern

**Purpose/Problem:**
Normalizes provider interfaces, enabling custom providers without modifying core code. Converts between provider-specific APIs and normalized internal interfaces.

**Implementation Details:**
- Protocol: `ProviderAdapter` with `generate_response()` and `get_provider_name()`
- Implementations: `OpenAIAdapter`, `ZAIAdapter`
- Converts `Message` models to provider-specific list format
- Collects streaming events from providers
- Returns `Result[Message]` for explicit error handling
- Registry system for custom adapters: `register_adapter()`, `get_adapter()`

**Code Location:**
- `dawn_kestrel/providers/adapters.py` - Adapter implementations and registry

**Protocol:**
```python
@runtime_checkable
class ProviderAdapter(Protocol):
    async def generate_response(
        self, messages: list[Message], model: str, **kwargs
    ) -> Result[Message]: ...
    
    async def get_provider_name(self) -> str: ...
```

**Implementation:**
```python
class OpenAIAdapter:
    def __init__(self, provider):
        self._provider = provider
    
    async def generate_response(
        self, messages: list[Message], model: str, **kwargs
    ) -> Result[Message]:
        try:
            # Convert Message models to provider format
            provider_messages = [
                {"role": msg.role, "content": msg.text or ""} 
                for msg in messages
            ]
            
            # Collect stream events
            text_parts = []
            async for event in self._provider.stream(...):
                if event.event_type == "text-delta":
                    text_parts.append(event.data.get("delta", ""))
                elif event.event_type == "finish":
                    break
            
            response = Message(
                id=f"openai-{asyncio.get_event_loop().time()}",
                role="assistant",
                text="".join(text_parts),
            )
            return Ok(response)
        except Exception as e:
            return Err(f"OpenAI provider error: {e}", code="PROVIDER_ERROR")
```

**Usage Example:**
```python
from dawn_kestrel.providers import OpenAIProvider
from dawn_kestrel.providers.adapters import OpenAIAdapter

provider = OpenAIProvider(api_key="sk-...")
adapter = OpenAIAdapter(provider)

result = await adapter.generate_response(messages, "gpt-5")
if result.is_ok():
    response = result.unwrap()
    print(f"Response: {response.text}")
```

**Integration:**
- Used by reliability patterns (Circuit Breaker, Retry, Rate Limiter)
- Provider Registry manages adapters for provider selection
- Works with Result pattern for error handling

---

### 7. Facade Pattern

**Purpose/Problem:**
Simplifies API over complex subsystems including DI container, repositories, services, and providers. Hides complexity of manual dependency wiring and provides a simple interface for common SDK operations.

**Implementation Details:**
- Protocol: `Facade` defining simplified SDK operations
- Implementation: `FacadeImpl` using DI container for dependency resolution
- Methods: `create_session()`, `get_session()`, `list_sessions()`, `add_message()`, `execute_agent()`, `register_provider()`
- Normalizes errors from services into user-friendly format
- Uses lazy initialization through DI container

**Code Location:**
- `dawn_kestrel/core/facade.py` - Facade implementation

**Protocol:**
```python
@runtime_checkable
class Facade(Protocol):
    async def create_session(self, title: str) -> Result[Session]: ...
    async def get_session(self, session_id: str) -> Result[Session | None]: ...
    async def list_sessions(self) -> Result[list[Session]]: ...
    async def add_message(self, session_id: str, role: str, content: str) -> Result[str]: ...
    async def execute_agent(self, agent_name: str, session_id: str, user_message: str, options: Optional[Dict[str, Any]]) -> Result[AgentResult]: ...
```

**Usage Example:**
```python
from dawn_kestrel.core.facade import FacadeImpl
from dawn_kestrel.core.di_container import configure_container

# Configure DI container
container = configure_container()

# Create facade using container
facade: Facade = FacadeImpl(container)

# Use simplified API
result = await facade.create_session("My Project")
if result.is_ok():
    session = result.unwrap()
    print(f"Created session: {session.id}")

result = await facade.add_message(session.id, "user", "Hello!")
```

**Integration:**
- Simplifies DI container access for users
- Wraps service complexity behind simple methods
- Used by SDK clients for high-level operations

---

### 8. Mediator Pattern

**Purpose/Problem:**
Centralizes event handling and eliminates component-to-component direct wiring. Components register event handlers with mediator, and mediator publishes events to all registered handlers.

**Implementation Details:**
- Event types: `DOMAIN`, `APPLICATION`, `SYSTEM`, `LLM`
- `Event` dataclass with `event_type`, `source`, `target`, `data`
- Protocol: `EventMediator` with `publish()`, `subscribe()`, `unsubscribe()`, `get_handler_count()`
- Implementation: `EventMediatorImpl` with in-memory handler registry
- Source filtering for targeted event delivery
- Optional source filter in `subscribe()` for selective routing

**Code Location:**
- `dawn_kestrel/core/mediator.py` - Mediator implementation

**Protocol:**
```python
@runtime_checkable
class EventMediator(Protocol):
    async def publish(self, event: Event) -> Result[None]: ...
    async def subscribe(self, event_type: EventType, handler: Callable[[Event], Awaitable[None]], source: str | None = None) -> Result[None]: ...
    async def unsubscribe(self, event_type: EventType, handler: Callable[[Event], Awaitable[None]]) -> Result[None]: ...
    async def get_handler_count(self, event_type: EventType) -> Result[int]: ...
```

**Usage Example:**
```python
from dawn_kestrel.core.mediator import EventMediatorImpl, Event, EventType

mediator = EventMediatorImpl()

# Subscribe to events
async def on_session_created(event: Event):
    print(f"Session created: {event.data}")

await mediator.subscribe(EventType.DOMAIN, on_session_created, source="session_service")

# Publish events
event = Event(
    event_type=EventType.DOMAIN,
    source="session_service",
    data={"action": "session_created", "session_id": "session-1"},
)
await mediator.publish(event)
```

**Integration:**
- Command Queue publishes events through mediator
- Observer pattern can subscribe to mediator events
- Session Lifecycle uses mediator for lifecycle notifications

---

### 9. Registry Pattern

**Purpose/Problem:**
Provides centralized lookup and management of plugins, tools, providers, and agents. Eliminates scattered registration code and enables dynamic discovery.

**Implementation Details:**
- Multiple registries: `ToolRegistry`, `ProviderRegistry`, `AgentRegistry`
- Plugin discovery populates registries via entry points
- Get methods: `get_by_id()`, `get_all()`, `list()`
- Type-safe lookups with Result returns
- Caching for performance

**Code Location:**
- `dawn_kestrel/tools/registry.py` - Tool registry
- `dawn_kestrel/providers/registry.py` - Provider registry
- `dawn_kestrel/agents/registry.py` - Agent registry

**Tool Registry Example:**
```python
class ToolRegistry(ToolRegistry):
    def __init__(self):
        self.tools: Dict[str, "Tool"] = {}
        self._init_builtin_tools()
        self._init_additional_tools()
    
    def _init_builtin_tools(self):
        self.tools["bash"] = BashTool()
        self.tools["read"] = ReadTool()
        # ... 5 builtin tools
    
    def _init_additional_tools(self):
        self.tools["edit"] = EditTool()
        self.tools["task"] = TaskTool()
        # ... 17 additional tools
    
    async def get_all(self) -> Dict[str, "Tool"]:
        return self.tools
```

**Usage Example:**
```python
from dawn_kestrel.tools import create_builtin_registry

# Create registry with all tools
tools = await create_builtin_registry()

# Get tool by name
bash_tool = tools.get("bash")

# Execute tool
result = await bash_tool.execute({"command": "ls -la"}, ctx=...)
```

**Integration:**
- Plugin discovery loads plugins into registries
- Agent Runtime queries registries for available tools
- Facade uses registries for component lookup

---

## Behavioral Patterns

### 10. Command Pattern

**Purpose/Problem:**
Encapsulates requests as objects, enabling undo/redo, provenance tracking, and execution events. Turns actions into first-class objects.

**Implementation Details:**
- Protocol: `Command` with `execute()`, `undo()`, `can_undo()`, `get_provenance()`
- Base class: `BaseCommand` with name, description, timestamp
- Implementations: `CreateSessionCommand`, `ExecuteToolCommand`
- `CommandContext` with session_id, message_id, agent_id, user_id, metadata
- `CommandQueue` for sequential command processing with event publishing

**Code Location:**
- `dawn_kestrel/core/commands.py` - Command implementations

**Protocol:**
```python
@runtime_checkable
class Command(Protocol):
    async def execute(self, context: CommandContext) -> Result[Any]: ...
    async def undo(self) -> Result[None]: ...
    def can_undo(self) -> bool: ...
    async def get_provenance(self) -> Result[dict[str, Any]]: ...
```

**Implementation:**
```python
class CreateSessionCommand(BaseCommand):
    def __init__(self, session_id: str, title: str):
        super().__init__(
            name="create_session",
            description=f"Create session: {title}",
        )
        self.session_id = session_id
        self.title = title
    
    async def execute(self, context: CommandContext) -> Result[str]:
        session_repo = context.metadata.get("session_repo")
        session = Session(id=self.session_id, title=self.title, ...)
        result = await session_repo.create(session)
        if result.is_ok():
            return Ok(self.session_id)
        return Err(f"Failed to create session: {result.error}")
```

**Usage Example:**
```python
from dawn_kestrel.core.commands import CreateSessionCommand, CommandContext

command = CreateSessionCommand("session-1", "My Session")
context = CommandContext(
    session_id="session-1",
    metadata={"session_repo": session_repo},
)

result = await command.execute(context)
```

**Integration:**
- Command Queue manages command lifecycle with Mediator events
- Commands can be composed for complex operations
- Works with Result pattern for error handling

---

### 11. Decorator/Proxy Pattern

**Purpose/Problem:**
Provides configurable logging behavior for any function or callable. Enables cross-cutting concerns like logging without modifying original functions.

**Implementation Details:**
- `LoggingConfig` class for centralized configuration
- `log_function()` decorator with level, enabled, prefix, include_args, include_result, include_timestamp
- `FunctionProxy` class implementing proxy pattern
- Supports both sync and async functions
- Uses Python `logging` module for output
- Factory function: `create_logging_proxy()`

**Code Location:**
- `dawn_kestrel/core/decorators.py` - Logging decorator and proxy

**Decorator:**
```python
def log_function(
    level: int = logging.INFO,
    enabled: bool = True,
    prefix: str = "",
    include_args: bool = True,
    include_result: bool = True,
    include_timestamp: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    config = LoggingConfig(...)
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not config.enabled:
                return await func(*args, **kwargs)
            
            # Log entry
            logger.log(config.level, f"Calling {func.__name__}")
            
            try:
                result = await func(*args, **kwargs)
                
                # Log result
                if config.include_result:
                    logger.log(config.level, f"{func.__name__} returned")
                
                return result
            except Exception as e:
                logger.error(f"{func.__name__} raised: {e}")
                raise
        
        return wrapper
    
    return decorator
```

**Usage Example:**
```python
from dawn_kestrel.core.decorators import log_function

# Apply decorator
@log_function(level=logging.DEBUG, prefix="[API]", include_args=True)
async def my_function(x: int, y: int) -> int:
    return x + y

# Or create proxy
from dawn_kestrel.core.decorators import create_logging_proxy

def add(a: int, b: int) -> int:
    return a + b

proxy = create_logging_proxy(add, level=logging.DEBUG)
result = await proxy(5, 10)
```

**Integration:**
- Can be applied to any function in codebase
- Works with async and sync functions
- Used for observability without modifying function logic

---

### 12. Null Object Pattern

**Purpose/Problem:**
Eliminates null checks for optional dependencies. Provides safe default implementations of interfaces that do nothing.

**Implementation Details:**
- Three null implementations: `NullIOHandler`, `NullProgressHandler`, `NullNotificationHandler`
- All methods are no-ops returning default values
- Factory function: `get_null_handler()` returns existing handler or null implementation
- Used for optional handler parameters in DI container

**Code Location:**
- `dawn_kestrel/core/null_object.py` - Null object implementations

**Null Implementations:**
```python
class NullIOHandler(IOHandler):
    async def prompt(self, message: str, default: str | None = None) -> str:
        return default if default is not None else ""
    
    async def confirm(self, message: str, default: bool = False) -> bool:
        return default
    
    async def select(self, message: str, options: list[str]) -> str:
        return options[0] if options else ""

class NullProgressHandler(ProgressHandler):
    def start(self, operation: str, total: int) -> None:
        pass
    
    def update(self, current: int, message: str | None = None) -> None:
        pass
    
    def complete(self, message: str | None = None) -> None:
        pass

class NullNotificationHandler(NotificationHandler):
    def show(self, notification: Any) -> None:
        pass
```

**Usage Example:**
```python
from dawn_kestrel.core.null_object import get_null_handler

# Get null handler or existing handler
io_handler = get_null_handler("io", None)  # Returns NullIOHandler
progress_handler = get_null_handler("progress", existing_progress_handler)  # Returns existing handler

# Use without null checks
result = await io_handler.prompt("Enter value: ")
await progress_handler.start("Processing", 100)
```

**Integration:**
- DI container uses null handlers when handlers not configured
- Facade can work with or without custom handlers
- Eliminates `if handler is not None` checks throughout codebase

---

### 13. Strategy Pattern

**Purpose/Problem:**
Defines algorithm families for runtime selection without if/else chains. Enables swapping algorithms based on context or configuration.

**Implementation Details:**
- Two strategy families: `RoutingStrategy` (provider selection), `RenderingStrategy` (output formatting)
- Implementations: `RoundRobinRouting`, `CostOptimizedRouting`, `PlainTextRendering`, `MarkdownRendering`
- `StrategySelector` for context-based strategy selection
- Protocol-based design with `@runtime_checkable`

**Code Location:**
- `dawn_kestrel/core/strategies.py` - Strategy implementations

**Routing Strategy Protocol:**
```python
@runtime_checkable
class RoutingStrategy(Protocol):
    async def select_provider(self, providers: list[Any], context: dict[str, Any]) -> Result[Any]: ...
    async def get_strategy_name(self) -> str: ...
```

**Implementations:**
```python
class RoundRobinRouting:
    def __init__(self):
        self._index: int = 0
    
    async def select_provider(self, providers: list[Any], context: dict[str, Any]) -> Result[Any]:
        if not providers:
            return Err("No providers available", code="NO_PROVIDERS")
        
        provider = providers[self._index]
        self._index = (self._index + 1) % len(providers)
        return Ok(provider)
    
    async def get_strategy_name(self) -> str:
        return "round_robin"
```

**Usage Example:**
```python
from dawn_kestrel.core.strategies import RoundRobinRouting, StrategySelector

# Create strategy
selector = StrategySelector()
selector.register("routing", RoundRobinRouting())

# Select based on context
result = await selector.select("routing", {"environment": "production"})
```

**Integration:**
- Provider Registry uses routing strategies
- Facade can switch strategies based on environment
- Runtime configuration changes strategy selection

---

### 14. Observer Pattern

**Purpose/Problem:**
Enables one-to-many notification when objects change state. Observers subscribe to observables to receive updates without direct coupling.

**Implementation Details:**
- Two protocols: `Observer` and `Observable`
- Implementation: `ObservableImpl` with observer set management
- Concrete observers: `StateChangeObserver`, `MetricsObserver`
- Optional `EventMediator` integration for lifecycle events
- Safe observer registration/unregistration

**Code Location:**
- `dawn_kestrel/core/observer.py` - Observer implementation

**Protocols:**
```python
@runtime_checkable
class Observer(Protocol):
    async def on_notify(self, observable: Any, event: dict[str, Any]) -> None: ...

@runtime_checkable
class Observable(Protocol):
    async def register_observer(self, observer: Observer) -> None: ...
    async def unregister_observer(self, observer: Observer) -> None: ...
    async def notify_observers(self, event: dict[str, Any]) -> None: ...
```

**Usage Example:**
```python
from dawn_kestrel.core.observer import ObservableImpl, StateChangeObserver

# Create observable and observer
observable = ObservableImpl(name="session", mediator=mediator)
observer = StateChangeObserver(name="session_watcher")

# Subscribe to updates
await observable.register_observer(observer)

# Notify observers
await observable.notify_observers({"action": "session_updated", "session_id": "session-1"})
```

**Integration:**
- Works with Mediator pattern for event distribution
- Multiple observers can subscribe to same observable
- Used for metrics and state tracking

---

### 15. State (FSM) Pattern

**Purpose/Problem:**
Manages agent lifecycle with explicit state transitions and validation. Ensures agents only transition through valid state changes.

**Implementation Details:**
- Protocol: `AgentFSM` with state management methods
- Implementation: `AgentFSMImpl` with `VALID_STATES` and `VALID_TRANSITIONS`
- States: `idle`, `running`, `paused`, `completed`, `failed`, `cancelled`
- All transitions return `Result[T]` for explicit error handling
- State validation prevents invalid transitions

**Code Location:**
- `dawn_kestrel/core/agent_fsm.py` - FSM implementation

**Valid States and Transitions:**
```python
class AgentFSMImpl:
    VALID_STATES = {
        "idle",      # Agent waiting for task
        "running",   # Agent processing task
        "paused",    # Agent temporarily stopped
        "completed", # Agent finished successfully
        "failed",    # Agent encountered error
        "cancelled", # Agent was cancelled
    }
    
    VALID_TRANSITIONS = {
        "idle": {"running", "cancelled"},
        "running": {"paused", "completed", "failed", "cancelled"},
        "paused": {"running", "cancelled"},
        "completed": {"idle"},
        "failed": {"idle", "cancelled"},
        "cancelled": {"idle"},
    }
```

**Usage Example:**
```python
from dawn_kestrel.core.agent_fsm import create_agent_fsm

# Create FSM with initial state
fsm = create_agent_fsm("idle")

# Transition to running
result = await fsm.transition_to("running")
if result.is_ok():
    print("Agent is now running")

# Invalid transition
result = await fsm.transition_to("idle")  # running -> idle is invalid
if result.is_err():
    print(f"Cannot transition: {result.error}")
```

**Integration:**
- Agent Runtime uses FSM to track lifecycle
- Works with Result pattern for error handling
- Provides explicit lifecycle management for agents

---

## Reliability Patterns

### 16. Circuit Breaker Pattern

**Purpose/Problem:**
Provides fault tolerance by wrapping LLM provider calls with automatic state management (OPEN, CLOSED, HALF_OPEN). Tracks failures per provider and automatically opens circuits when thresholds are breached.

**Implementation Details:**
- States: `CLOSED` (normal), `OPEN` (allows traffic), `HALF_OPEN` (limited calls after timeout)
- Protocol: `CircuitBreaker` with state query methods
- Implementation: `CircuitBreakerImpl` with failure tracking per provider
- Configurable thresholds: `failure_threshold`, `half_open_threshold`, `timeout_seconds`, `reset_timeout_seconds`
- Manual state control via `open()`, `close()` methods

**Code Location:**
- `dawn_kestrel/llm/circuit_breaker.py` - Circuit breaker implementation

**Protocol:**
```python
@runtime_checkable
class CircuitBreaker(Protocol):
    async def is_open(self) -> bool: ...
    async def is_closed(self) -> bool: ...
    async def is_half_open(self) -> bool: ...
    async def get_state(self) -> str: ...
    async def open(self) -> Result[None]: ...
    async def close(self) -> Result[None]: ...
```

**Usage Example:**
```python
from dawn_kestrel.llm.circuit_breaker import CircuitBreakerImpl, CircuitState

breaker = CircuitBreakerImpl(
    provider_adapter=adapter,
    failure_threshold=5,        # Failures before opening circuit
    half_open_threshold=3,       # Failures before half-open
    timeout_seconds=60,          # Timeout for half-open state
    reset_timeout_seconds=120,     # Cooldown before reset
)

# Check circuit state
if await breaker.is_closed():
    # Circuit is closed, can call provider
    response = await provider.generate_response(messages)
else:
    # Circuit is open or half-open
    print("Circuit breaker is blocking calls")

# Manual control
await breaker.open()   # Open circuit
await breaker.close()  # Close circuit
```

**Integration:**
- Retry executor checks circuit breaker before retrying
- LLM Reliability wrapper uses circuit breaker for fault tolerance
- Works with Provider Adapter pattern

---

### 17. Bulkhead Pattern

**Purpose/Problem:**
Provides resource isolation by limiting concurrent operations per resource using semaphores. Prevents resource exhaustion from too many concurrent requests.

**Implementation Details:**
- Protocol: `Bulkhead` with semaphore management
- Implementation: `BulkheadImpl` with per-resource semaphores
- Per-resource limits and timeouts
- `try_execute()` method with automatic semaphore acquisition/release
- Active count tracking per resource
- Configurable via `set_limit()`, `set_timeout()`

**Code Location:**
- `dawn_kestrel/llm/bulkhead.py` - Bulkhead implementation

**Protocol:**
```python
@runtime_checkable
class Bulkhead(Protocol):
    async def try_acquire(self, resource: str) -> Result[asyncio.Semaphore]: ...
    async def release(self, semaphore: asyncio.Semaphore) -> Result[None]: ...
    async def try_execute(self, resource: str, func: Callable[..., Any], max_concurrent: int | None = None) -> Result[Any]: ...
```

**Usage Example:**
```python
from dawn_kestrel.llm.bulkhead import BulkheadImpl

bulkhead = BulkheadImpl()

# Set limit for OpenAI provider
bulkhead.set_limit("openai", 5)  # Max 5 concurrent calls
bulkhead.set_timeout("openai", 60)  # 60s acquisition timeout

# Execute with concurrent limiting
async def llm_call():
    return await provider.generate_response(messages)

result = await bulkhead.try_execute("openai", llm_call)
if result.is_ok():
    response = result.unwrap()
```

**Integration:**
- Used in reliability wrapper to limit concurrent LLM calls
- Works with Circuit Breaker pattern
- Prevents resource exhaustion

---

### 18. Retry + Backoff Pattern

**Purpose/Problem:**
Handles transient failures with automatic retry using configurable backoff strategies. Distinguishes between retryable and non-retryable errors.

**Implementation Details:**
- Three backoff strategies: `ExponentialBackoff`, `LinearBackoff`, `FixedBackoff`
- Protocol: `RetryExecutor` with `execute()`, `get_attempt_count()`, `get_stats()`
- Implementation: `RetryExecutorImpl` with retry loop and statistics
- Configurable: `max_attempts`, `backoff`, `transient_errors`, `circuit_breaker`
- Tracks: total calls, successful calls, failed calls, retry count, errors by type

**Code Location:**
- `dawn_kestrel/llm/retry.py` - Retry implementation

**Backoff Strategies:**
```python
class ExponentialBackoff:
    """Delay grows exponentially: delay = base_delay_ms * (exponential_base ** attempt)"""
    def __init__(self, base_delay_ms=100.0, max_delay_ms=5000.0, exponential_base=2.0, jitter=False): ...

class LinearBackoff:
    """Delay increases linearly: delay = base_delay_ms * (attempt + 1)"""
    def __init__(self, base_delay_ms=100.0, max_delay_ms=5000.0): ...

class FixedBackoff:
    """Delay remains constant: delay = delay_ms"""
    def __init__(self, delay_ms=500.0): ...
```

**Usage Example:**
```python
from dawn_kestrel.llm.retry import RetryExecutorImpl, ExponentialBackoff

executor = RetryExecutorImpl(
    max_attempts=3,
    backoff=ExponentialBackoff(base_delay_ms=100, max_delay_ms=5000),
    transient_errors={TimeoutError, ConnectionError},  # Retry only these errors
    circuit_breaker=circuit_breaker,
)

result = await executor.execute(
    lambda: provider.generate_response(messages),
    max_attempts=3,
)

if result.is_ok():
    response = result.unwrap()
    stats = await executor.get_stats()
    print(f"Success after {stats['attempts']} attempts")
```

**Integration:**
- LLM Reliability wrapper uses retry as outer layer
- Works with Circuit Breaker for fault tolerance
- Works with Result pattern for error handling

---

### 19. Rate Limiter Pattern

**Purpose/Problem:**
Prevents API overload using token bucket algorithm. Each resource has its own token bucket with configurable capacity and refill rate.

**Implementation Details:**
- Protocol: `RateLimiter` with `try_acquire()`, `release()`, `get_available()`
- Token bucket algorithm: fixed capacity, constant refill rate, tokens consumed on requests
- Implementation: `RateLimiterImpl` with per-resource token buckets
- Per-resource configuration via `set_limit()`
- Optional `reset()` method for clearing buckets
- Window-based request tracking

**Code Location:**
- `dawn_kestrel/llm/rate_limiter.py` - Rate limiter implementation

**Token Bucket:**
```python
class TokenBucket:
    def __init__(self, capacity=10, refill_rate=1, window_seconds=60):
        self._capacity = capacity
        self._refill_rate = refill_rate  # Tokens per second
        self._tokens = capacity
        self._last_refill_time = datetime.now()
    
    async def try_acquire(self, resource: str, tokens: int = 1) -> Result[bool]:
        # Refill tokens based on elapsed time
        await self._refill_tokens()
        
        if self._tokens >= tokens:
            self._tokens -= tokens
            return Ok(True)
        
        return Err(f"Not enough tokens: need {tokens}, have {self._tokens}", code="RATE_LIMIT_EXCEEDED")
```

**Usage Example:**
```python
from dawn_kestrel.llm.rate_limiter import RateLimiterImpl

limiter = RateLimiterImpl(
    default_capacity=10,        # 10 tokens max
    default_refill_rate=0.166667,  # 10 tokens per minute
    default_window_seconds=60,
)

# Set custom limit for OpenAI
limiter.set_limit('openai', capacity=100, refill_rate=1.666667, window_seconds=60)

# Try to acquire token
result = await limiter.try_acquire('openai', tokens=1)
if result.is_ok():
    # Make API call
    await provider.generate_response(messages)
else:
    # Rate limited, wait and retry
    print("Rate limited, wait and retry")
```

**Integration:**
- LLM Reliability wrapper uses rate limiter as first layer
- Applied before Circuit Breaker and Retry
- Works with Bulkhead for resource isolation

---

### 20. Configuration Object Pattern

**Purpose/Problem:**
Provides centralized, type-safe configuration with validation. Encapsulates all configuration parameters in a single object with automatic defaults and validation.

**Implementation Details:**
- Uses `pydantic` for settings with type validation
- Dataclass: `SDKConfig` with storage path, project directory, handler flags
- Environment variable support with prefixes (`DAWN_KESTREL_`, `OPENCODE_PYTHON_`)
- Multi-source configuration: environment variables, .env files, XDG directories
- Helper methods: `get_account()`, `get_default_account()`, `get_api_key_for_provider()`
- Path expansion (`~` to home directory)

**Code Location:**
- `dawn_kestrel/core/settings.py` - Settings with Pydantic (main configuration)
- `dawn_kestrel/core/config.py` - SDKConfig for client configuration

**Settings Dataclass:**
```python
@dataclass
class SDKConfig:
    storage_path: Path | None = None
    project_dir: Path | None = None
    auto_confirm: bool = False
    enable_progress: bool = True
    enable_notifications: bool = True
    
    def __post_init__(self) -> None:
        if self.project_dir is None:
            self.project_dir = Path.cwd()
    
    def as_dict(self) -> dict[str, Any]:
        return {
            "storage_path": str(self.storage_path) if self.storage_path else None,
            "project_dir": str(self.project_dir) if self.project_dir else None,
            "auto_confirm": self.auto_confirm,
            "enable_progress": self.enable_progress,
            "enable_notifications": self.enable_notifications,
        }
```

**Usage Example:**
```python
from dawn_kestrel.core.config import SDKConfig

# Create configuration with defaults
config = SDKConfig()

# Override specific settings
config = SDKConfig(
    storage_path=Path("/custom/storage"),
    auto_confirm=True,  # Skip confirm() prompts
    enable_progress=False,  # Disable progress updates
)

# Use configuration
print(f"Storage: {config.storage_path}")
print(f"Auto-confirm: {config.auto_confirm}")
```

**Integration:**
- Used by DI container for configuration injection
- Facade can customize SDK behavior via config
- Settings used throughout application for consistent configuration

---

## Structural Patterns

### 21. Composite Pattern

**Purpose/Problem:**
Treats individual objects and compositions uniformly. Enables tree structures where client code can treat leaf and composite nodes identically.

**Implementation Details:**
- Used in command validation and plan validation
- Tree structures for nested validation
- Recursive operations on composite structures
- Used in command and plan validation logic

**Code Locations:**
- `dawn_kestrel/core/commands.py` - CommandQueue manages commands as composite
- Plan validation uses composite pattern for hierarchical validation

**Usage Example:**
```python
# Command queue treats commands as composite
queue = CommandQueue(mediator)

await queue.enqueue(CreateSessionCommand("session-1", "Session 1"))
await queue.enqueue(ExecuteToolCommand("bash", {"command": "ls"}))

# Process queue (composite behavior)
await queue.process_next()  # Processes first command
await queue.process_next()  # Processes second command
```

**Integration:**
- Commands can be composed into sequences
- Plan validation uses composite for nested structures
- Works with Result pattern for validation

---

## Pattern Integration

### How Patterns Work Together

The 21 patterns in Dawn Kestrel are designed to integrate seamlessly:

**Reliability Stack:**
1. **Rate Limiter** (token bucket) - First layer, prevents API overload
2. **Circuit Breaker** - Second layer, prevents cascading failures
3. **Retry** - Third layer, handles transient errors with backoff

```python
from dawn_kestrel.llm.reliability import LLMReliabilityImpl

reliability = LLMReliabilityImpl(
    rate_limiter=rate_limiter,
    circuit_breaker=circuit_breaker,
    retry_executor=retry_executor,
)

result = await reliability.generate_with_resilience(
    provider_adapter=adapter,
    messages=messages,
    model="gpt-5",
)
# Applies rate limit → circuit breaker → retry in order
```

**Dependency Injection Flow:**
1. **DI Container** manages all services
2. **Repositories** injected via DI
3. **Facade** uses DI to resolve dependencies
4. **Null Handlers** used when handlers not configured
5. **Configuration** loaded and injected

```python
container = configure_container(
    storage_path=Path("/storage"),
    project_dir=Path("/project"),
)

# Facade resolves dependencies lazily
facade = FacadeImpl(container)
# Dependencies wired automatically when accessed
service = container.service()  # Creates service with injected repositories
```

**Event Flow:**
1. **Mediator** centralizes event handling
2. **Observer** pattern subscribes to events
3. **FSM** publishes state changes via mediator
4. **Command Queue** publishes command events

```python
# Subscribe to events
await mediator.subscribe(EventType.DOMAIN, on_session_created)

# FSM publishes events
fsm = AgentFSMImpl("idle")
await fsm.transition_to("running")
# FSM can notify mediator (via observable integration)
```

**Data Access Layer:**
1. **Repository** pattern provides data access abstraction
2. **Unit of Work** groups repository operations
3. **Result** pattern provides explicit error handling
4. **Plugin Discovery** loads tools/providers/agents

```python
# Transactional operations
async def create_session_with_message(uow: UnitOfWork):
    await uow.begin()
    await uow.register_session(session)
    await uow.register_message(message)
    result = await uow.commit()
    # All or nothing - no partial state
```

### Benefits of Pattern Integration

- **Explicit Error Handling**: Result pattern eliminates exceptions across all layers
- **Fault Tolerance**: Reliability stack prevents cascading failures
- **Loose Coupling**: Mediator and Observer decouple components
- **Testability**: DI container enables dependency injection for testing
- **Extensibility**: Plugin system enables third-party extensions
- **Transactional Consistency**: Unit of Work ensures data integrity
- **Type Safety**: Protocol-based design with `@runtime_checkable`

---

## Migration Notes

### Legacy Pattern Removal

The following legacy patterns were removed during refactoring:

- **Static Provider Factories**: Replaced by plugin discovery via entry points
- **Direct SessionStorage**: Replaced by Repository pattern
- **Exception-Based Error Handling**: Replaced by Result pattern
- **Manual Dependency Wiring**: Replaced by DI Container

### Breaking Changes

Key breaking changes from the refactor:

1. **Result Types**: All service methods now return `Result[T]` instead of raising exceptions
   ```python
   # Old (exception-based)
   session = service.get_session(session_id)
   
   # New (result-based)
   result = await service.get_session(session_id)
   if result.is_ok():
       session = result.unwrap()
   ```

2. **Repository Injection**: Services require repository injection instead of storage parameter
   ```python
   # Old (storage-based)
   service = DefaultSessionService(storage=storage)
   
   # New (repository-based)
   service = DefaultSessionService(
       session_repo=session_repo,
       message_repo=message_repo,
       part_repo=part_repo,
   )
   ```

3. **Plugin Discovery**: Tools/providers/agents loaded via entry points, not static registries
   ```python
   # Old (static registry)
   from dawn_kestrel.tools import TOOL_FACTORIES
   tool = TOOL_FACTORIES.get('bash')
   
   # New (plugin discovery)
   from dawn_kestrel.core.plugin_discovery import load_tools
   tools = await load_tools()
   tool = tools.get('bash')
   ```

4. **Configuration Access**: Use `settings.storage_dir_path()` instead of `Path(settings.storage_dir).expanduser()`
   ```python
   # Old (manual expansion)
   storage = Path(settings.storage_dir).expanduser()
   
   # New (helper method)
   storage = settings.storage_dir_path()
   ```

### Backward Compatibility

The following shims maintain backward compatibility:

- **`create_complete_registry()`** in `dawn_kestrel/tools/__init__.py`: Shim for plugin discovery
- **Deprecated `get_storage_dir()`** function in settings: Calls `storage_dir_path()`
- **Deprecated `get_config_dir()`** function in settings: Calls `config_dir_path()`

---

## Testing

### Pattern Testing

Each pattern has comprehensive test coverage:

- **DI Container**: `tests/core/test_di_container.py` - 22 tests
- **Result Pattern**: `tests/core/test_result.py` - Tests for Ok/Err/Pass
- **Repositories**: `tests/core/test_repositories.py` - Repository CRUD tests
- **Unit of Work**: `tests/core/test_unit_of_work.py` - Transactional tests
- **Commands**: `tests/core/test_commands.py` - Command execution tests
- **Mediator**: `tests/core/test_mediator.py` - Event routing tests
- **Observer**: `tests/core/test_observer.py` - Observer notification tests
- **FSM**: `tests/core/test_agent_fsm.py` - State transition tests
- **Circuit Breaker**: `tests/llm/test_circuit_breaker.py` - State management tests
- **Bulkhead**: `tests/llm/test_bulkhead.py` - Concurrency limiting tests
- **Retry**: `tests/llm/test_retry.py` - Backoff and retry logic tests
- **Rate Limiter**: `tests/llm/test_rate_limiter.py` - Token bucket tests
- **Reliability Integration**: `tests/llm/test_reliability.py` - Pattern ordering tests

### Test Patterns

Common test patterns used across all pattern tests:

- **TDD Approach**: Tests written before implementation for many patterns
- **Protocol-Based Tests**: Using `@runtime_checkable` for type checking
- **Result Testing**: Verifying `is_ok()`, `is_err()`, `unwrap()`, `unwrap_or()` behavior
- **Mock Injection**: Using DI container to inject test doubles
- **Async Testing**: All async patterns tested with `pytest` async support

---

## Conclusion

The 21 design patterns implemented in Dawn Kestrel provide:

1. **Explicit Error Handling**: Result pattern eliminates exception scattering
2. **Fault Tolerance**: Reliability stack prevents cascading failures
3. **Loose Coupling**: Mediator, DI, and Plugin patterns decouple components
4. **Transactional Consistency**: Unit of Work ensures atomic operations
5. **Extensibility**: Plugin system enables third-party extensions
6. **Type Safety**: Protocol-based design with runtime checking
7. **Composition**: Patterns integrate seamlessly for complex operations

These patterns work together to provide excellent composition and eliminate blast exposure across the codebase.

---

## References

- **Pattern Documentation**: This file (`docs/patterns.md`)
- **Getting Started**: `docs/getting-started.md` - Installation and usage guide
- **Project Structure**: `docs/STRUCTURE.md` - Code organization guide
- **Learnings**: `.sisyphus/notepads/dawn-kestrel-refactor/learnings.md` - Implementation notes
- **Source Code**: `dawn_kestrel/` directory - Pattern implementations

For questions or issues, refer to the project repository or issue tracker.
