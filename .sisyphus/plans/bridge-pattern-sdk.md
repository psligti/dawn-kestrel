# Bridge Pattern SDK Architecture for opencode_python

## TL;DR

> **Quick Summary**: Convert opencode_python to use Bridge design pattern with CLI, TUI, and SDK as first-class citizens. Create I/O abstraction layer (IOHandler, ProgressHandler, NotificationHandler) with Protocol-based interfaces. Core services accept handlers via constructor injection. Implement thread-safe SessionManager for shared session storage. Provide both sync and async SDK APIs. Maintain backward compatibility with deprecation warnings before breaking changes.

> **Deliverables**:
> - I/O Abstraction Protocols (`opencode_python/src/opencode_python/interfaces/io.py`)
> - Core Service Interfaces (`opencode_python/src/opencode_python/core/services/`)
> - Concrete Handlers (CLI, TUI, SDK)
> - Thread-safe SessionManager
> - Sync and Async SDK Clients
> - Updated pyproject.toml with optional dependencies
> - SDK documentation and examples

> **Estimated Effort**: Large (14-18 days)
> **Parallel Execution**: YES - 6 waves
> **Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 6

---

## Protocol Interface Specifications

### IOHandler Protocol
```python
@runtime_checkable
class IOHandler(Protocol):
    """Protocol for input/output operations"""
    
    async def prompt(
        self,
        message: str,
        default: str | None = None
    ) -> str:
        """Prompt user for input. Returns user's response.
        
        Args:
            message: The prompt message to display
            default: Default value if user doesn't provide input
        
        Returns:
            User's input as a string
        
        Raises:
            PromptError if user cancels or input fails
        """
        ...
    
    async def confirm(
        self,
        message: str,
        default: bool = False
    ) -> bool:
        """Ask user for yes/no confirmation.
        
        Args:
            message: The confirmation message to display
            default: Default answer (True for yes, False for no)
        
        Returns:
            True for yes, False for no
        
        Raises:
            PromptError if user cancels
        """
        ...
    
    async def select(
        self,
        message: str,
        options: list[str]
    ) -> str:
        """Ask user to select one option from a list.
        
        Args:
            message: The selection message to display
            options: List of string options to choose from
        
        Returns:
            The selected option as a string
        
        Raises:
            PromptError if user cancels or invalid selection
        """
        ...
    
    async def multi_select(
        self,
        message: str,
        options: list[str]
    ) -> list[str]:
        """Ask user to select multiple options from a list.
        
        Args:
            message: The selection message to display
            options: List of string options to choose from
        
        Returns:
            List of selected options
        
        Raises:
            PromptError if user cancels or invalid selections
        """
        ...
```

### ProgressHandler Protocol
```python
@runtime_checkable
class ProgressHandler(Protocol):
    """Protocol for progress updates"""
    
    def start(
        self,
        operation: str,
        total: int
    ) -> None:
        """Start a progress operation.
        
        Args:
            operation: Name of the operation (e.g., "Creating session")
            total: Total number of steps for completion
        
        Returns:
            None
        
        Note:
            Should initialize progress UI (show progress bar, status line)
        """
        ...
    
    def update(
        self,
        current: int,
        message: str = ""
    ) -> None:
        """Update progress.
        
        Args:
            current: Current step number (1 to total)
            message: Optional message to display with progress
        
        Returns:
            None
        
        Note:
            Should update progress UI (advance progress bar, update status line)
        """
        ...
    
    def complete(
        self,
        message: str = ""
    ) -> None:
        """Mark operation as complete.
        
        Args:
            message: Optional completion message
        
        Returns:
            None
        
        Note:
            Should finalize progress UI (hide progress bar, show completion message)
        """
        ...
```

### NotificationHandler Protocol
```python
@dataclass
class Notification:
    """User notification data"""
    notification_type: NotificationType  # INFO, SUCCESS, WARNING, ERROR, DEBUG
    message: str  # Notification message
    details: dict[str, Any] | None = None  # Additional context (optional)
    duration: int = 3  # Seconds for TUI (ignored for CLI/SDK)

@runtime_checkable
class NotificationHandler(Protocol):
    """Protocol for user notifications"""
    
    def show(
        self,
        notification: Notification
    ) -> None:
        """Show notification to user.
        
        Args:
            notification: Notification dataclass with type, message, details
        
        Returns:
            None
        
        Note:
            - CLI: Print to console with color coding
            - TUI: Use app.notify() with severity
            - SDK: Call callback (if registered) or ignore
        """
        ...
```

### StateHandler Protocol
```python
@runtime_checkable
class StateHandler(Protocol):
    """Protocol for UI state management"""
    
    def get_current_session_id(self) -> str | None:
        """Get currently selected session ID.
        
        Returns:
            Session ID string or None if no session selected
        """
        ...
    
    def set_current_session_id(self, session_id: str) -> None:
        """Set currently selected session ID.
        
        Args:
            session_id: Session ID string to set as current
        
        Returns:
            None
        
        Note:
            Should trigger UI update to reflect new selection
        """
        ...
    
    def get_work_directory(self) -> str:
        """Get current working directory.
        
        Returns:
            Current working directory path
        """
        ...
```

### NotificationType Enum
```python
class NotificationType(str, Enum):
    """Types of notifications"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"
```

### ProgressType Enum
```python
class ProgressType(str, Enum):
    """Types of progress operations"""
    SESSION_CREATE = "session_create"
    MESSAGE_CREATE = "message_create"
    TOOL_EXEC = "tool_execution"
    AI_RESPONSE = "ai_response"
    EXPORT = "export"
    IMPORT = "import"
```

---

## Handler Integration Pattern

### How to Inject Handlers into Core Services

Core services (SessionService, MessageService, etc.) accept handlers via constructor injection:

```python
class DefaultSessionService(SessionService):
    """Default implementation of SessionService protocol"""
    
    def __init__(
        self,
        storage: SessionStorage,
        io_handler: IOHandler | None = None,
        progress_handler: ProgressHandler | None = None,
        notification_handler: NotificationHandler | None = None,
    ):
        self.storage = storage
        self._io_handler = io_handler or NoOpIOHandler()
        self._progress_handler = progress_handler or NoOpProgressHandler()
        self._notification_handler = notification_handler or NoOpNotificationHandler()
    
    async def create_session(
        self,
        title: str,
    ) -> Session:
        """Create a new session using injected handlers"""
        # Prompt for parent session if io_handler available
        if self._io_handler:
            use_parent = await self._io_handler.confirm(
                "Create this session as a child of an existing session?",
                default=False
            )
        else:
            use_parent = False
        
        # Start progress
        if self._progress_handler:
            self._progress_handler.start("Creating session", 100)
        
        # Create session via storage
        session = await self.storage.create_session(title, parent_id=use_parent)
        
        # Update progress
        if self._progress_handler:
            self._progress_handler.update(100, "Session created")
            self._progress_handler.complete(f"Created session: {session.id}")
        
        # Show notification
        if self._notification_handler:
            self._notification_handler.show(Notification(
                notification_type=NotificationType.SUCCESS,
                message=f"Session created: {session.title}",
            ))
        
        return session
```

### No-Op Handlers for Default Behavior

When handlers are not provided, use no-op implementations:

```python
class NoOpIOHandler(IOHandler):
    """No-op implementation of IOHandler for when no UI is available"""
    
    async def prompt(self, message: str, default: str | None = None) -> str:
        return default or ""  # Return default value or empty string
    
    async def confirm(self, message: str, default: bool = False) -> bool:
        return default  # Return default value
    
    async def select(self, message: str, options: list[str]) -> str:
        return options[0] if options else ""  # Return first option or empty string
    
    async def multi_select(self, message: str, options: list[str]) -> list[str]:
        return []  # Return empty list

class NoOpProgressHandler(ProgressHandler):
    """No-op implementation of ProgressHandler"""
    
    def start(self, operation: str, total: int) -> None:
        pass  # Do nothing
    
    def update(self, current: int, message: str = "") -> None:
        pass  # Do nothing
    
    def complete(self, message: str = "") -> None:
        pass  # Do nothing

class NoOpNotificationHandler(NotificationHandler):
    """No-op implementation of NotificationHandler"""
    
    def show(self, notification: Notification) -> None:
        pass  # Do nothing
```

---

## Deprecation Warning Specification

### When Handlers Are Not Provided (Phase 1-3)

Core services should show deprecation warnings when handlers are not provided:

```python
import warnings
from typing import Protocol

class DefaultSessionService:
    def __init__(
        self,
        storage: SessionStorage,
        io_handler: IOHandler | None = None,  # Optional in Phase 1-3
        ...
    ):
        self.storage = storage
        
        # Deprecation warning for Phase 1-3
        if io_handler is None:
            warnings.warn(
                "io_handler is required in version 0.2.0. "
                "Pass QuietIOHandler() for headless mode. "
                "Direct I/O will be deprecated in Phase 4.",
                DeprecationWarning,
                stacklevel=2
            )
        
        self._io_handler = io_handler or NoOpIOHandler()
```

### Deprecation Warning Message Format

```python
warnings.warn(
    "<FEATURE> will be deprecated in version <VERSION>. "
    "<REPLACEMENT>. "
    "Please migrate to <NEW_APPROACH>.",
    DeprecationWarning,
    stacklevel=2
)
```

---

## EventBus to NotificationHandler Mapping

### Event to NotificationType Mapping

```python
EVENT_TO_NOTIFICATION_TYPE = {
    Events.SESSION_CREATED: (NotificationType.INFO, "Session {session_id} created"),
    Events.SESSION_UPDATED: (NotificationType.INFO, "Session {session_id} updated"),
    Events.MESSAGE_CREATED: (NotificationType.SUCCESS, "Message added to session"),
    Events.MESSAGE_DELETED: (NotificationType.WARNING, "Message deleted from session"),
    Events.TOOL_STARTED: (NotificationType.INFO, "Tool {tool_name} started"),
    Events.TOOL_COMPLETED: (NotificationType.INFO, "Tool {tool_name} completed"),
    Events.PERMISSION_ASKED: (NotificationType.WARNING, "Permission required for {action}"),
}
```

### EventBusNotificationSubscriber Class

```python
class EventBusNotificationSubscriber(NotificationHandler):
    """NotificationHandler that subscribes to EventBus events"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._subscriptions: list[Callable] = []
        
        # Subscribe to relevant events
        for event_type, (notification_type, message_template) in EVENT_TO_NOTIFICATION_TYPE.items():
            if event_type in Events.__dict__:
                subscription = await event_bus.subscribe(
                    event_type,
                    self._handle_event(notification_type, message_template)
                )
                self._subscriptions.append(subscription)
    
    async def _handle_event(
        self,
        notification_type: NotificationType,
        message_template: str,
    ) -> None:
        """Handle EventBus event and show notification"""
        async def event_handler(event_data):
            # Extract relevant fields from event_data
            session_id = event_data.get("session_id")
            tool_name = event_data.get("tool_name")
            
            # Format message
            message = message_template.format(**event_data)
            
            # Show notification
            if self._notification_handler:
                self._notification_handler.show(Notification(
                    notification_type=notification_type,
                    message=message,
                    details={"session_id": session_id, "tool_name": tool_name},
                ))
        
        return event_handler
```

---

## SDK Configuration Specification

### SDKConfig Field Meanings

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

@dataclass
class SDKConfig:
    """Configuration for SDK client"""
    
    storage_path: Path | None = None
    """Where sessions are stored on disk.
    
    Default: ~/.local/share/opencode-python (from get_storage_dir())
    Override: Set to custom path for isolated storage
    """
    
    project_dir: Path | None = None
    """Current working directory.
    
    Default: Path.cwd()
    Override: Set to different directory for testing or remote operations
    """
    
    auto_confirm: bool = False
    """If True, skip all confirm() calls and return True.
    
    Default: False
    Override: Set to True for non-interactive batch operations
    Effect: io_handler.confirm() returns True without prompting
    """
    
    enable_progress: bool = True
    """If True, use progress handlers for long operations.
    
    Default: True
    Override: Set to False for silent mode
    Effect: progress_handler.start/update/complete() called if True, no-op if False
    """
    
    enable_notifications: bool = True
    """If True, show notifications via notification handler.
    
    Default: True
    Override: Set to False for silent mode
    Effect: notification_handler.show() called if True, no-op if False
    """
```

### Configuration Override Pattern

```python
# Override default config
config = SDKConfig(
    storage_path=Path("/custom/storage"),
    project_dir=Path("/custom/project"),
    auto_confirm=True,  # Skip confirmations
    enable_progress=False,  # No progress updates
)

# Pass config to SDK client
sdk = OpenCodeAsyncClient(config=config)
```

---

## Optional Dependency Strategy

### Current Dependencies Classification

**Core Dependencies** (always installed):
- aiofiles>=24.0
- aiohttp>=3.10
- asyncio-extras>=0.22.0
- gitpython>=3.1
- httpx>=0.28.1
- pendulum>=3.0
- pydantic>=2.12
- pydantic-settings>=2.0
- python-frontmatter>=1.0
- tiktoken>=0.8.0

**CLI Dependencies** (install with `[cli]`):
- click>=8.0
- rich>=13.0

**TUI Dependencies** (install with `[tui]`):
- textual>=0.50.0

### Import Failure Handling

```python
# In CLI module
try:
    import click
    import rich.console
    _CLICK_AVAILABLE = True
except ImportError:
    _CLICK_AVAILABLE = False

if not _CLICK_AVAILABLE:
    raise ImportError(
        "CLI dependencies not installed. "
        "Install with: pip install opencode-python[cli]"
    )
```

### Conditional Entry Point Registration

```toml
# In pyproject.toml
[project.scripts]
# Only register CLI entry point if dependencies are available
# This is handled at build time or via entry point script

# Entry point wrapper script (bin/opencode)
#!/usr/bin/env python3
try:
    from opencode_python.cli.main import cli
    cli()
except ImportError as e:
    print(f"Error: {e}", file=sys.stderr)
    print("Install with: pip install opencode-python[cli]", file=sys.stderr)
    sys.exit(1)
```

---

## CLI/TUI Handler Implementation Details

### CLIIOHandler Implementation

```python
import click
from rich.console import Console

from opencode_python.interfaces.io import IOHandler, NotificationType, Notification

class CLIIOHandler(IOHandler):
    """CLI implementation of IOHandler using Click and Rich"""
    
    def __init__(self):
        self.console = Console()
    
    async def prompt(
        self,
        message: str,
        default: str | None = None
    ) -> str:
        """Prompt user for input"""
        return click.prompt(message, default=default, show_default=True)
    
    async def confirm(
        self,
        message: str,
        default: bool = False
    ) -> bool:
        """Ask user for yes/no confirmation"""
        return click.confirm(message, default=default)
    
    async def select(
        self,
        message: str,
        options: list[str]
    ) -> str:
        """Ask user to select from options"""
        click.echo(f"\n{message}")
        for i, option in enumerate(options, 1):
            click.echo(f"  {i}. {option}")
        
        while True:
            choice = click.prompt("Enter choice number", type=int)
            if 1 <= choice <= len(options):
                return options[choice - 1]
            click.echo("Invalid choice, please try again.")
    
    async def multi_select(
        self,
        message: str,
        options: list[str]
    ) -> list[str]:
        """Ask user to select multiple options"""
        click.echo(f"\n{message}")
        click.echo("Select multiple (comma-separated numbers, or 'all'):")
        for i, option in enumerate(options, 1):
            click.echo(f"  {i}. {option}")
        
        while True:
            choice = click.prompt("Enter choice(s)")
            if choice.lower() == 'all':
                return options
            try:
                indices = [int(x.strip()) for x in choice.split(',')]
                selected = [options[i-1] for i in indices if 1 <= i <= len(options)]
                return selected
            except (ValueError, IndexError):
                click.echo("Invalid choice, please try again.")
```

### TUINotificationHandler Implementation

```python
from textual.app import App
from textual.widgets import Notification

from opencode_python.interfaces.io import NotificationHandler, Notification, NotificationType

class TUINotificationHandler(NotificationHandler):
    """TUI implementation of NotificationHandler using Textual"""
    
    def __init__(self, app: App):
        self.app = app
    
    def show(self, notification: Notification) -> None:
        """Show notification to user"""
        severity_map = {
            NotificationType.INFO: "information",
            NotificationType.SUCCESS: "information",
            NotificationType.WARNING: "warning",
            NotificationType.ERROR: "error",
            NotificationType.DEBUG: "information",
        }
        
        severity = severity_map.get(notification.notification_type, "information")
        
        self.app.notify(
            message=notification.message,
            severity=severity,
            timeout=notification.duration,
            title=notification.details.get("title") if notification.details else None,
        )
```

### CLIProgressHandler Implementation

```python
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console

from opencode_python.interfaces.io import ProgressHandler

class CLIProgressHandler(ProgressHandler):
    """CLI implementation of ProgressHandler using Rich"""
    
    def __init__(self):
        self.console = Console()
        self._progress: Progress | None = None
        self._total: int = 0
    
    def start(self, operation: str, total: int) -> None:
        """Start a progress operation"""
        self._total = total
        self._progress = Progress(
            f"[bold]{operation}[/bold]",
            console=self.console,
            transient=True,
            bar_format="{desc}: {percentage:3.0f}% [{bar}] {elapsed}<{remaining}",
        )
        self._progress.start(total=total)
    
    def update(self, current: int, message: str = "") -> None:
        """Update progress"""
        if self._progress:
            self._progress.update(
                advance=current - self._progress.tasks[0].completed,
                description=f"{message} ({current}/{self._total})"
            )
    
    def complete(self, message: str = "") -> None:
        """Mark operation as complete"""
        if self._progress:
            self._progress.stop()
            self.console.print(f"[green]✓[/green] {message}")
```

---

## Thread Safety Implementation Details

### SessionManager Lock Scope

**Which methods need locks:**
- create() - Creates session, writes to storage
- delete_session() - Deletes session, writes to storage
- create_message() - Creates message, writes to storage
- create_messages() - Creates multiple messages, writes to storage

**Which methods DON'T need locks:**
- get_session() - Read-only, returns copy
- list_sessions() - Read-only, returns list

**Why**: Read-only operations don't corrupt shared state. Write operations must be serialized to prevent race conditions.

### Lock Implementation Pattern

```python
class SessionManager:
    def __init__(self, storage: SessionStorage, project_dir: Path):
        self.storage = storage
        self.project_dir = project_dir
        self._lock = asyncio.Lock()  # Lock for concurrent access
    
    async def create_session(self, title: str) -> Session:
        """Create session with thread safety"""
        async with self._lock:
            return await self.storage.create_session(title, project_id=self.project_dir.id)
    
    async def get_session(self, session_id: str) -> Session | None:
        """Get session (no lock needed - read-only)"""
        # No lock - returns immutable copy
        return await self.storage.get_session(session_id)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session with thread safety"""
        async with self._lock:
            return await self.storage.delete_session(session_id)
```

## SDK Configuration Specification

### SDKConfig to Handler Integration

Core services use handlers injected via constructor. SDKConfig controls when/how handlers are created and configured.

**Configuration Fields**:
```python
@dataclass
class SDKConfig:
    """Configuration for SDK client"""
    
    storage_path: Path | None = None
    """Where sessions are stored on disk.
    Default: ~/.local/share/opencode-python (from get_storage_dir())
    Override: Set to custom path for isolated storage
    """
    
    project_dir: Path | None = None
    """Current working directory.
    Default: Path.cwd()
    Override: Set to different directory for testing or remote operations
    """
    
    auto_confirm: bool = False
    """If True, skip all confirm() calls and return True.
    Default: False
    Override: Set to True for non-interactive batch operations
    Effect: io_handler.confirm() returns True without prompting
    """
    
    enable_progress: bool = True
    """If True, use progress handlers for long operations.
    Default: True
    Override: Set to False for silent mode
    Effect: progress_handler.start/update/complete() called
    """
    
    enable_notifications: bool = True
    """If True, show notifications via notification handler.
    Default: True
    Override: Set to False for silent mode
    Effect: notification_handler.show() called
    """
```

### Handler Creation from SDKConfig

**Precedence Rules**:
1. Explicit handler parameter (passed to `OpenCodeAsyncClient.__init__`) overrides SDKConfig
2. SDKConfig fields (auto_confirm, enable_progress, enable_notifications) are applied if no explicit handler provided
3. If both explicit handler AND SDKConfig field are provided, explicit handler takes precedence

**Handler Creation Logic**:
```python
class OpenCodeAsyncClient:
    def __init__(
        self,
        config: SDKConfig | None = None,
        io_handler: IOHandler | None = None,
        progress_handler: ProgressHandler | None = None,
        notification_handler: NotificationHandler | None = None,
    ):
        self.config = config or SDKConfig()
        
        # Precedence 1: Explicit handler overrides SDKConfig
        self._io_handler = io_handler or (
            NoOpIOHandler()
            if not (self.config.enable_notifications and self.config.auto_confirm)
            else AutoConfirmIOHandler()
        )
        
        # Precedence 2: SDKConfig controls behavior when no explicit handler
        if not io_handler and self.config.enable_progress:
            self._progress_handler = NoOpProgressHandler()
        else:
            self._progress_handler = progress_handler or NoOpProgressHandler()
        
        if not notification_handler and self.config.enable_notifications:
            self._notification_handler = NoOpNotificationHandler()
        else:
            self._notification_handler = notification_handler or NoOpNotificationHandler()
        
        self._service = DefaultSessionService(
            storage=...,  # from config
            io_handler=self._io_handler,
            progress_handler=self._progress_handler,
            notification_handler=self._notification_handler,
        )
```

### Auto-Confirm Handlers

**When SDKConfig.auto_confirm=True**:
```python
class AutoConfirmIOHandler(IOHandler):
    """Always returns True for confirm() without prompting"""
    
    async def confirm(
        self,
        message: str,
        default: bool = False
    ) -> bool:
        return True  # Always confirm, skip user interaction
```

**When SDKConfig.auto_confirm=False**:
- Use user's io_handler.confirm() to prompt (normal behavior)

---

## Thread Safety Implementation

### Lock Scope

**Which methods need locks:**
- **create()** - Creates session, writes to storage (MUST LOCK)
- **delete_session()** - Deletes session, writes to storage (MUST LOCK)
- **create_message()** - Creates message, writes to storage (MUST LOCK)
- **create_messages()** - Creates multiple messages, writes to storage (MUST LOCK)

**Which methods DON'T need locks:**
- **get_session()** - Read-only, returns copy (NO LOCK)
- **list_sessions()** - Read-only, returns list (NO LOCK)

**Why**: Read-only operations return immutable copies and don't corrupt shared state.

### Lock Implementation

```python
import asyncio

class SessionManager:
    def __init__(self, storage: SessionStorage, project_dir: Path):
        self.storage = storage
        self.project_dir = project_dir
        self._lock = asyncio.Lock()  # Lock for concurrent access
    
    async def create_session(self, title: str) -> Session:
        """Create session with thread safety"""
        async with self._lock:  # Lock for write operation
            return await self.storage.create_session(title)
    
    async def get_session(self, session_id: str) -> Session | None:
        """Get session (read-only, no lock needed)"""
        return await self.storage.get_session(session_id)  # Return immutable copy
```

### Lock Scope Summary

- **Locks**: create(), delete_session(), create_message(), create_messages()
- **No Locks**: get_session(), list_sessions()
- **Read-only Safety**: get_session(), list_sessions() don't modify state
- **Write Serialization**: All write operations acquire lock, preventing race conditions

---

## Context

### Interview Summary

**Key Discussions**:
- **Architecture Pattern**: Triadic Bridge with CLI, TUI, SDK as equal peers sharing same core
- **Abstraction Strategy**: Python 3.11 Protocols for I/O operations (IOHandler, ProgressHandler, NotificationHandler)
- **Dependency Injection**: Constructor-based injection for testability
- **Package Structure**: src-layout with optional extras ([core], [cli], [tui], [full])

**User Decisions**:
1. **Backward Compatibility**: Deprecation warning first (Phase 1-3), then breaking changes (Phase 4-6)
2. **State Management**: Shared sessions (CLI and TUI access same storage) → requires thread-safe SessionManager
3. **Error Handling**: Core catches handler exceptions, transforms to domain-specific exceptions
4. **Configuration**: Hybrid (core defaults + interface overrides)
5. **EventBus Integration**: Both (hybrid) - EventBus for core events, direct handler calls for UI
6. **Async/Sync APIs**: Sync + Async (Client and AsyncClient classes)

**Research Findings**:
- **Oracle Guidance**: Triadic Bridge pattern with I/O Protocols, Core Services, Persistence layers
- **Current Architecture**: Clear layering but CLI directly imports TUI (line 84-85), no formal SDK boundary
- **Protocols vs ABC**: Protocols preferred for structural typing with @runtime_checkable
- **Real-World Examples**: Boto3 (session pattern), OpenBB (multi-interface), Mininterface (single config)
- **Metis Gaps**: 6 critical questions answered, guardrails set (no plugins, no advanced logging, unit+integration tests only)

### Metis Review

**Identified Gaps** (addressed):
- **Backward compatibility strategy**: ✅ Decrecation warning → Breaking with migration guide
- **State sharing approach**: ✅ Shared sessions with thread-safe SessionManager
- **Error handling policy**: ✅ Core catches and transforms to domain exceptions
- **Configuration ownership**: ✅ Hybrid (core defaults + interface overrides)
- **EventBus integration**: ✅ Hybrid (events for core, direct calls for UI)
- **Sync/async API approach**: ✅ Both Client (sync) and AsyncClient (async)

**Guardrails Applied** (from Metis review):
- **Scope Locked Down**: NO plugins, NO advanced logging, NO performance optimization, NO new config formats
- **Testing Scope**: Unit tests for protocols, integration tests for CLI/TUI, NO E2E/property-based tests
- **Documentation Scope**: README, API reference (auto-generated), 3 examples, migration guide ONLY
- **Breaking Change Policy**: Document all changes, provide migration snippets, require team approval

---

## Work Objectives

### Core Objective
Implement Bridge design pattern for opencode_python with CLI, TUI, and SDK as first-class citizens. Create I/O abstraction layer, refactor core services to accept handlers via constructor injection, implement thread-safe session management, and expose SDK with both sync and async APIs.

### Concrete Deliverables
- I/O Abstraction Protocols (`src/opencode_python/interfaces/io.py`)
- Core Service Interfaces (`src/opencode_python/core/services/`)
- Concrete CLI Handlers (`src/opencode_python/cli/handlers.py`)
- Concrete TUI Handlers (`src/opencode_python/tui/handlers.py`)
- SDK Client Classes (`src/opencode_python/sdk/client.py`)
- Thread-safe SessionManager (`src/opencode_python/core/session.py` refactored)
- Updated pyproject.toml with optional dependencies
- SDK Documentation (`README.md`, `examples/`, migration guide)

### Definition of Done
- [ ] All I/O handler protocols defined and mypy-verifiable
- [ ] Core services accept handlers via constructor with default no-op implementations
- [ ] CLI and TUI implement all I/O handler protocols
- [ ] SDK provides both sync (Client) and async (AsyncClient) APIs
- [ ] SessionManager is thread-safe with shared session storage
- [ ] Optional dependencies work: `pip install opencode[core]`, `[cli]`, `[tui]`, `[full]`
- [ ] Backward compatibility maintained (deprecation warnings in Phase 1-3)
- [ ] Unit tests for protocols and core services with mocked handlers
- [ ] Integration tests for CLI and TUI
- [ ] SDK examples and documentation

### Must Have
- Protocol-based I/O abstractions (IOHandler, ProgressHandler, NotificationHandler, StateHandler)
- Constructor dependency injection for all core services
- Thread-safe SessionManager with locking mechanism
- Both sync and async SDK client APIs
- Backward compatibility with deprecation warnings before breaking changes
- Core error handling that catches handler exceptions and transforms to domain exceptions
- Hybrid configuration system (core defaults + interface overrides)
- Hybrid EventBus integration (events for core, direct calls for UI)

### Must NOT Have (Guardrails)
- Plugin system or extension points beyond CLI/TUI/SDK
- Advanced logging configuration in core (keep current logging as-is)
- Configuration file formats beyond what exists today
- Performance optimization (profiling, caching)
- Telemetry, analytics, or usage tracking
- E2E tests or property-based testing (beyond unit + integration)
- Tutorial documentation beyond README and examples
- Multi-threading or multiprocessing beyond SessionManager locks
- Retry logic or exponential backoff in core (leave to SDK users)

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest, pytest-asyncio)
- **User wants tests**: TDD (tests enabled)
- **Framework**: pytest, pytest-asyncio

### TDD Strategy

Each TODO follows RED-GREEN-REFACTOR:

**Task Structure**:
1. **RED**: Write failing test first
   - Test file: `test_protocols.py` (unit tests for protocols)
   - Test command: `pytest test_protocols.py -v`
   - Expected: FAIL (protocol exists, implementation doesn't)

2. **GREEN**: Implement minimum code to pass
   - Command: `pytest test_protocols.py -v`
   - Expected: PASS

3. **REFACTOR**: Clean up while keeping green
   - Command: `pytest test_protocols.py -v`
   - Expected: PASS (still)

---

## Execution Strategy

### Parallel Execution Waves

Maximize throughput by grouping independent tasks into parallel waves.

```
Wave 1 (Start Immediately):
├── Task 1: Create I/O Abstraction Protocols (no dependencies)
├── Task 2: Create Core Service Interfaces (depends on Task 1)
├── Task 3: Create Error Hierarchy (no dependencies)
└── Task 4: Create Configuration Classes (no dependencies)

Wave 2 (After Wave 1):
├── Task 5: Implement Default Core Services (depends on Task 2)
├── Task 6: Implement Thread-safe SessionManager (depends on Task 5)
├── Task 7: Implement CLI Handlers (depends on Task 1)
└── Task 8: Implement TUI Handlers (depends on Task 1)

Wave 3 (After Wave 2):
├── Task 9: Implement SDK Client (Async) (depends on Task 5)
├── Task 10: Implement SDK Client (Sync) (depends on Task 9)
└── Task 11: Create Hybrid EventBus Integration (depends on Task 5)

Wave 4 (After Wave 3):
├── Task 12: Refactor CLI Commands (depends on Task 7)
├── Task 13: Refactor TUI App (depends on Task 8)
└── Task 14: Update pyproject.toml (depends on Task 9, 10, 11)

Wave 5 (After Wave 4):
├── Task 15: Write Unit Tests (depends on all implementation tasks)
├── Task 16: Write Integration Tests (depends on Task 12, 13)
└── Task 17: Create SDK Examples (depends on Task 9, 10)

Wave 6 (After Wave 5):
└── Task 18: Write Documentation (depends on Task 17)

Critical Path: Task 1 → Task 2 → Task 5 → Task 9 → Task 10 → Task 17
Parallel Speedup: ~35% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|-------|-------------|--------|---------------------|
| 1 | None | 2, 3, 4 | None (foundation) |
| 2 | 1 | 5 | 3, 4 |
| 3 | None | None | 1, 4 |
| 4 | None | None | 1, 2, 3 |
| 5 | 2 | 6 | 7, 8 |
| 6 | 5 | 11 | 7, 8, 9 |
| 7 | 1 | 12 | 8, 9, 10 |
| 8 | 1 | 13 | 7, 9, 10, 11 |
| 9 | 5 | 10, 11 | 12, 13 |
| 10 | 9 | 14 | 11, 12, 13, 17 |
| 11 | 5, 6 | None (final core) | 12, 13, 14, 17 |
| 12 | 7 | 15 | 13, 14, 15 |
| 13 | 8 | 16 | 12, 14, 15, 16 |
| 14 | 9, 10, 11 | 15, 16 | 12, 13, 15, 16 |
| 15 | 12, 13, 14 | 17 | 16 |
| 16 | 13 | 18 | 15, 17 |
| 17 | 9, 10 | 18 | 15, 16, 18 |
| 18 | 17 | None (final) | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|-------|---------|------------------|
| 1 | 1-4 | delegate_task(category="unspecified-high", load_skills=["git-master"], run_in_background=true) |
| 2 | 5-8 | delegate_task(category="unspecified-high", load_skills=["git-master"], run_in_background=true) |
| 3 | 9-11 | delegate_task(category="unspecified-high", load_skills=["git-master"], run_in_background=true) |
| 4 | 12-14 | delegate_task(category="unspecified-high", load_skills=["git-master"], run_in_background=true) |
| 5 | 15-17 | delegate_task(category="unspecified-high", load_skills=["git-master"], run_in_background=true) |
| 6 | 18 | delegate_task(category="writing", load_skills=["git-master"], run_in_background=true) |

---

## TODOs

- [ ] 1. Create I/O Abstraction Protocols

  **What to do**:
  - Create `src/opencode_python/interfaces/io.py` with Protocol definitions
  - Define IOHandler protocol (prompt, confirm, select, multi_select)
  - Define ProgressHandler protocol (start, update, complete)
  - Define NotificationHandler protocol (show, with Notification dataclass)
  - Define StateHandler protocol (get/set current_session_id, work_directory)
  - Define ProgressType and NotificationType enums
  - Define ProgressUpdate and Notification dataclasses
  - Use @runtime_checkable decorator on all protocols
  - Add type hints for all methods

  **Must NOT do**:
  - Don't create concrete implementations yet (next task)
  - Don't add business logic to protocols (keep them pure interfaces)
  - Don't import UI-specific modules (Click, Textual)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Protocol definitions require careful design and type safety
  - **Skills**: `["git-master"]`
    - `git-master`: None (no git operations needed)

  **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4) | Sequential
  - **Blocks**: Task 2, 3, 4 | None (can start immediately)
  - **Blocked By**: None | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - None (new code, but use Oracle's protocol examples as template)

  **API/Type References** (contracts to implement against):
  - `typing.Protocol` - Python standard library protocol definition
  - `typing.Protocol.runtime_checkable` - Enable runtime protocol checking
  - `dataclasses.dataclass` - For ProgressUpdate and Notification data

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/test_protocols.py` - Create this new test file

  **Documentation References** (specs and requirements):
  - Oracle recommendations - Protocol structure from Metis consultation
  - Python typing docs: https://docs.python.org/3/library/typing.html#typing.Protocol

  **External References** (libraries and frameworks):
  - None (standard library only)

  **WHY Each Reference Matters** (explain the relevance):
  - `typing.Protocol`: Standard Python way to define structural interfaces with compile-time type checking
  - `typing.Protocol.runtime_checkable`: Allows isinstance() checks for protocol compliance at runtime

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_protocols.py
  - [ ] Test covers: IOHandler protocol definition exists
  - [ ] Test covers: ProgressHandler protocol definition exists
  - [ ] Test covers: NotificationHandler protocol definition exists
  - [ ] Test covers: StateHandler protocol definition exists
  - [ ] Test covers: All protocols use @runtime_checkable
  - [ ] pytest tests/test_protocols.py -v → PASS (5 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Library/Module changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "from opencode_python.interfaces.io import IOHandler, ProgressHandler, NotificationHandler, StateHandler; print('All protocols imported successfully')"
  # Assert: Output is "All protocols imported successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from import verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 1)
  - Message: `feat(architecture): add I/O abstraction protocols with @runtime_checkable`
  - Files: `src/opencode_python/interfaces/io.py`
  - Pre-commit: `pytest tests/test_protocols.py`

- [ ] 2. Create Core Service Interfaces

  **What to do**:
  - Create `src/opencode_python/core/services/session_service.py`
  - Define SessionService protocol (create_session, get_session, list_sessions, delete_session, add_message)
  - Create DefaultSessionService implementation using existing SessionManager logic
  - Add handler parameters (io_handler, progress_handler, notification_handler) to all methods
  - Create default no-op implementations for each handler type
  - Refactor existing SessionManager logic into DefaultSessionService
  - Maintain backward compatibility: optional handlers with deprecation warnings
  - Add error catching: catch handler exceptions, transform to SessionError

  **Must NOT do**:
  - Don't remove existing SessionManager (refactor into new structure)
  - Don't change storage layer (use as-is)
  - Don't add new business logic (extract existing logic)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core service refactoring requires careful extraction of existing logic
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of SessionManager changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8) | Sequential
  - **Blocks**: Task 6, 7, 8 | Task 1 (protocols must exist)
  - **Blocked By**: Task 1 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/core/session.py:22-150` - Current SessionManager implementation to extract
  - `src/opencode_python/core/session.py:38-42` - SessionManager.__init__ pattern
  - `src/opencode_python/core/session.py:58-95` - create_session implementation to extract
  - `src/opencode_python/interfaces/io.py` - Protocol definitions from Task 1

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/interfaces/io.py:IOHandler` - Protocol to use
  - `src/opencode_python/interfaces/io.py:ProgressHandler` - Protocol to use
  - `src/opencode_python/interfaces/io.py:NotificationHandler` - Protocol to use
  - `src/opencode_python/core/models.py:Session` - Return type for get_session
  - `src/opencode_python/core/models.py:Message` - Return type for add_message

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - Create new test file: `tests/test_session_service.py`

  **Documentation References** (specs and requirements):
  - Oracle recommendations - Service interface structure from Metis consultation
  - Existing SessionManager docstrings - Extract business intent

  **External References** (libraries and frameworks):
  - None (standard library and existing patterns)

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/core/session.py:22-150`: Extract existing session management logic into service interface
  - `src/opencode_python/interfaces/io.py:IOHandler`: Use protocol definitions for handler parameters
  - `src/opencode_python/core/models.py:Session`: Maintain return type compatibility

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_session_service.py
  - [ ] Test covers: DefaultSessionService implements SessionService protocol
  - [ ] Test covers: create_session with io_handler prompts user
  - [ ] Test covers: create_session without io_handler uses default with deprecation warning
  - [ ] Test covers: get_session returns Session or None
  - [ ] Test covers: list_sessions returns list of Session objects
  - [ ] Test covers: delete_session calls notification_handler
  - [ ] Test covers: Handler exceptions are caught and transformed to SessionError
  - [ ] pytest tests/test_session_service.py -v → PASS (8 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Library/Module changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "from opencode_python.core.services.session_service import SessionService, DefaultSessionService; print('Service interfaces imported successfully')"
  # Assert: Output is "Service interfaces imported successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from import verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 3, 4)
  - Message: `refactor(core): extract SessionManager into SessionService with handler injection`
  - Files: `src/opencode_python/core/services/session_service.py`
  - Pre-commit: `pytest tests/test_session_service.py`

- [ ] 3. Create Error Hierarchy

  **What to do**:
  - Create `src/opencode_python/core/exceptions.py`
  - Define OpenCodeError base exception class
  - Define SessionError (extends OpenCodeError)
  - Define MessageError (extends OpenCodeError)
  - Define ToolExecutionError (extends OpenCodeError)
  - Define IOHandlerError (extends OpenCodeError)
  - Define PromptError (extends IOHandlerError)
  - Define NotificationError (extends IOHandlerError)
  - Add docstrings to all exception classes
  - Ensure all exceptions have meaningful error messages

  **Must NOT do**:
  - Don't create error codes or error hierarchies beyond these 7 classes
  - Don't add recovery suggestions or retry logic
  - Don't import UI-specific modules (Click, Textual)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Exception hierarchy design requires careful consideration of error types
  - **Skills**: `["git-master"]`
    - `git-master`: For checking if existing exception patterns exist

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4) | Sequential
  - **Blocks**: None | None
  - **Blocked By**: None | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - None (new code, but follow Python exception best practices)

  **API/Type References** (contracts to implement against):
  - `builtins.Exception` - Python standard exception base class
  - Python exception docs: https://docs.python.org/3/library/exceptions.html

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - Create new test file: `tests/test_exceptions.py`

  **Documentation References** (specs and requirements):
  - Oracle recommendations - Error handling strategy from Metis consultation
  - Python exception best practices - Standard library docs

  **External References** (libraries and frameworks):
  - None (standard library only)

  **WHY Each Reference Matters** (explain the relevance):
  - `builtins.Exception`: Standard Python base class for all exceptions
  - Python exception docs: Best practices for exception hierarchy design

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_exceptions.py
  - [ ] Test covers: All exception classes are defined
  - [ ] Test covers: Exceptions inherit from correct base classes
  - [ ] Test covers: Exceptions have meaningful error messages
  - [ ] Test covers: Exception hierarchy is flat (no unnecessary nesting)
  - [ ] pytest tests/test_exceptions.py -v → PASS (7 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Library/Module changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "from opencode_python.core.exceptions import OpenCodeError, SessionError, MessageError; print('Exception hierarchy imported successfully')"
  # Assert: Output is "Exception hierarchy imported successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from import verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 1, 2)
  - Message: `feat(core): add error hierarchy for domain-specific exceptions`
  - Files: `src/opencode_python/core/exceptions.py`
  - Pre-commit: `pytest tests/test_exceptions.py`

- [ ] 4. Create Configuration Classes

  **What to do**:
  - Create `src/opencode_python/core/config.py`
  - Define SDKConfig dataclass with storage_path, project_dir, auto_confirm, enable_progress, enable_notifications
  - Refactor existing Settings from settings.py to be compatible with hybrid approach
  - Add config override mechanism (allow interfaces to pass custom config)
  - Ensure config validation via Pydantic
  - Add docstrings explaining config options
  - Maintain backward compatibility with existing Settings

  **Must NOT do**:
  - Don't add new configuration file formats (TOML/YAML)
  - Don't add advanced logging configuration
  - Don't change existing environment variable behavior

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Configuration design requires careful backward compatibility with existing Settings
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of Settings changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3) | Sequential
  - **Blocks**: None | None
  - **Blocked By**: None | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/core/settings.py:1-119` - Existing Settings class to extend
  - `src/opencode_python/core/settings.py:12-42` - Settings field definitions pattern
  - `pydantic.BaseSettings` - Pydantic base class for settings

  **API/Type References** (contracts to implement against):
  - `dataclasses.dataclass` - For SDKConfig definition
  - `pydantic.BaseSettings` - For hybrid configuration approach

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - Create new test file: `tests/test_config.py`

  **Documentation References** (specs and requirements):
  - Oracle recommendations - Hybrid configuration from Metis consultation
  - Existing Settings docstrings - Maintain environment variable behavior

  **External References** (libraries and frameworks):
  - Pydantic docs: https://docs.pydantic.dev/latest/

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/core/settings.py:1-119`: Extend existing Settings to support hybrid config (defaults + overrides)
  - `pydantic.BaseSettings`: Pydantic pattern for configuration with env var support

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_config.py
  - [ ] Test covers: SDKConfig dataclass defined with all fields
  - [ ] Test covers: Config validation works via Pydantic
  - [ ] Test covers: Config overrides work correctly
  - [ ] Test covers: Backward compatibility with existing Settings maintained
  - [ ] pytest tests/test_config.py -v → PASS (4 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Library/Module changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "from opencode_python.core.config import SDKConfig; print('Configuration classes imported successfully')"
  # Assert: Output is "Configuration classes imported successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from import verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 1, 2, 3)
  - Message: `feat(core): add hybrid configuration system with SDKConfig`
  - Files: `src/opencode_python/core/config.py`
  - Pre-commit: `pytest tests/test_config.py`

- [ ] 5. Implement Default Core Services

  **What to do**:
  - Implement DefaultSessionService in `src/opencode_python/core/services/session_service.py`
  - Add handler injection to __init__ (io_handler, progress_handler, notification_handler all optional)
  - Implement create_session with handler support:
    - If io_handler provided: use io_handler.prompt() for title
    - If io_handler not provided: use default with deprecation warning
    - Call progress_handler.start/update/complete if provided
    - Catch handler exceptions, transform to SessionError, re-raise
  - Implement get_session (read-only, no handlers needed)
  - Implement list_sessions (read-only, no handlers needed)
  - Implement delete_session:
    - Call notification_handler.show() if provided
    - Catch handler exceptions, transform to SessionError
  - Implement add_message with progress_handler support
  - Maintain backward compatibility: existing SessionManager code still works
  - Add type hints for all methods
  - Add docstrings for all methods

  **Must NOT do**:
  - Don't change SessionManager (this task implements DefaultSessionService that replaces it)
  - Don't modify storage layer (use as-is)
  - Don't add new business logic (extract existing logic)
  - Don't remove existing SessionManager until Phase 3

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core service implementation requires careful extraction of existing SessionManager logic
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of SessionManager changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8) | Sequential
  - **Blocks**: Task 6, 7, 8 | Task 2 (service interface must exist)
  - **Blocked By**: Task 2 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/core/session.py:22-95` - SessionManager methods to implement
  - `src/opencode_python/core/session.py:38-42` - SessionManager.__init__ pattern
  - `src/opencode_python/core/storage/store.py` - Storage layer to use
  - `src/opencode_python/interfaces/io.py` - Handler protocols to use

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/core/services/session_service.py:SessionService` - Protocol to implement
  - `src/opencode_python/interfaces/io.py:IOHandler` - Protocol to use
  - `src/opencode_python/interfaces/io.py:ProgressHandler` - Protocol to use
  - `src/opencode_python/interfaces/io.py:NotificationHandler` - Protocol to use
  - `src/opencode_python/core/exceptions.py:SessionError` - Exception to raise

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/test_session_service.py` - Tests created in Task 2

  **Documentation References** (specs and requirements):
  - Oracle recommendations - Core service implementation from Metis consultation
  - Existing SessionManager docstrings - Business logic intent

  **External References** (libraries and frameworks):
  - None (existing patterns and standard library)

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/core/session.py:22-95`: Extract existing session management logic into service
  - `src/opencode_python/core/storage/store.py`: Use existing storage without modification

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] pytest tests/test_session_service.py -v → PASS (8 tests, 0 failures) [from Task 2]
  - [ ] DefaultSessionService implements SessionService protocol (mypy check)
  - [ ] create_session calls io_handler.prompt() if provided
  - [ ] create_session shows deprecation warning if io_handler not provided
  - [ ] create_session calls progress_handler.start/update/complete if provided
  - [ ] Handler exceptions in create_session are caught and transformed to SessionError
  - [ ] delete_session calls notification_handler.show() if provided
  - [ ] Existing SessionManager behavior preserved (backward compatible)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Library/Module changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "from opencode_python.core.services.session_service import DefaultSessionService; s = DefaultSessionService(storage=None, project_dir='.'); print('DefaultSessionService instantiated successfully')"
  # Assert: Output is "DefaultSessionService instantiated successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from instantiation verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 6, 7)
  - Message: `feat(core): implement DefaultSessionService with handler injection and error handling`
  - Files: `src/opencode_python/core/services/session_service.py`
  - Pre-commit: `pytest tests/test_session_service.py`

- [ ] 6. Implement Thread-safe SessionManager

  **What to do**:
  - Add thread safety to SessionManager in `src/opencode_python/core/session.py`
  - Add asyncio.Lock to __init__ for concurrent access control
  - Wrap all storage read/write operations with async with self._lock
  - Wrap all session creation/deletion operations with async with self._lock
  - Ensure lock is released in finally blocks
  - Add docstrings explaining thread-safety guarantees
  - Test concurrent access scenarios
  - Maintain backward compatibility with existing SessionManager API

  **Must NOT do**:
  - Don't change SessionManager API (only add thread safety internally)
  - Don't add multi-processing (thread safety only)
  - Don't change storage layer (use as-is)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Thread-safe concurrent access requires complex synchronization logic
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of SessionManager changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 2 (with Tasks 5, 7, 8) | Sequential
  - **Blocks**: Task 11 | Task 5 (DefaultSessionService must exist)
  - **Blocked By**: Task 5 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/core/session.py:22-334` - SessionManager to add thread safety to
  - `asyncio.Lock` - Python asyncio lock for concurrent access
  - Python asyncio docs: https://docs.python.org/3/library/asyncio-sync.html

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/core/storage/store.py` - Storage layer to wrap with locks
  - `asyncio.Lock` - Python asyncio synchronization primitive

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - Create new test file: `tests/test_thread_safety.py`

  **Documentation References** (specs and requirements):
  - Oracle recommendations - Shared sessions with thread safety from Metis consultation
  - Python asyncio docs - Lock usage patterns

  **External References** (libraries and frameworks):
  - None (standard library and existing patterns)

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/core/session.py:22-334`: Add thread safety to existing SessionManager for shared session access
  - `asyncio.Lock`: Standard Python mechanism for thread-safe concurrent access

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_thread_safety.py
  - [ ] Test covers: Concurrent session creation doesn't corrupt data
  - [ ] Test covers: Concurrent session deletion doesn't corrupt data
  - [ ] Test covers: Lock is properly released in finally blocks
  - [ ] Test covers: SessionManager API unchanged (backward compatible)
  - [ ] pytest tests/test_thread_safety.py -v → PASS (4 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Concurrent/Thread-Safety changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "
  import asyncio
  from opencode_python.core.session import SessionManager

  async def test():
      sm = SessionManager(storage=None, project_dir='.')
      print('SessionManager with lock instantiated successfully')

  asyncio.run(test())
  "
  # Assert: Output is "SessionManager with lock instantiated successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from instantiation verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 5)
  - Message: `feat(core): add thread-safe locking to SessionManager for shared session access`
  - Files: `src/opencode_python/core/session.py`
  - Pre-commit: `pytest tests/test_thread_safety.py`

- [ ] 7. Implement CLI Handlers

  **What to do**:
  - Create `src/opencode_python/cli/handlers.py`
  - Implement CLIIOHandler class:
    - prompt(): Use click.prompt()
    - confirm(): Use click.confirm()
    - select(): Use click options with numbered selection
    - multi_select(): Use click options with comma-separated selection
  - Implement CLINotificationHandler class:
    - show(): Use rich.console.Console.print() with color coding
    - Map NotificationType to Rich styles (INFO=cyan, SUCCESS=green, WARNING=yellow, ERROR=red)
  - Implement CLIProgressHandler class:
    - start(): Use rich.progress.Progress()
    - update(): Update progress bar
    - complete(): Stop progress and show completion message
  - Add type hints for all methods
  - Add docstrings for all classes and methods
  - Ensure all handlers implement respective protocols from Task 1

  **Must NOT do**:
  - Don't import TUI modules
  - Don't add Click command logic (handlers are for I/O only)
  - Don't modify existing CLI commands (next task)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: CLI handler implementation requires Click and Rich integration
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of CLI changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 8) | Sequential
  - **Blocks**: Task 12 | Task 1 (protocols must exist)
  - **Blocked By**: Task 1 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/cli/main.py:23-30` - Existing click patterns to follow
  - `src/opencode_python/cli/main.py:20` - Rich console usage pattern
  - `src/opencode_python/interfaces/io.py` - Protocol definitions to implement

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/interfaces/io.py:IOHandler` - Protocol to implement
  - `src/opencode_python/interfaces/io.py:ProgressHandler` - Protocol to implement
  - `src/opencode_python/interfaces/io.py:NotificationHandler` - Protocol to implement
  - `click.prompt` - Click documentation for user input
  - `rich.console.Console.print` - Rich docs for formatted output
  - `rich.progress.Progress` - Rich docs for progress bars

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - Create new test file: `tests/test_cli_handlers.py`

  **Documentation References** (specs and requirements):
  - Oracle recommendations - CLI handler examples from Metis consultation
  - Click docs: https://click.palletsprojects.com/en/stable/api/
  - Rich docs: https://rich.readthedocs.io/en/stable/

  **External References** (libraries and frameworks):
  - None (Click and Rich patterns from docs)

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/cli/main.py:23-30`: Follow existing Click patterns for consistency
  - `src/opencode_python/interfaces/io.py`: Implement protocol contracts correctly

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_cli_handlers.py
  - [ ] Test covers: CLIIOHandler implements IOHandler protocol
  - [ ] Test covers: CLIIOHandler.prompt() uses click.prompt()
  - [ ] Test covers: CLIIOHandler.confirm() uses click.confirm()
  - [ ] Test covers: CLIIOHandler.select() shows numbered options
  - [ ] Test covers: CLINotificationHandler implements NotificationHandler protocol
  - [ ] Test covers: CLINotificationHandler.show() uses Rich color coding
  - [ ] Test covers: CLIProgressHandler implements ProgressHandler protocol
  - [ ] Test covers: CLIProgressHandler.start/update/complete uses Rich progress
  - [ ] pytest tests/test_cli_handlers.py -v → PASS (6 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For CLI/UI changes** (using Bash click):
  ```bash
  # Agent runs:
  python -c "from opencode_python.cli.handlers import CLIIOHandler, CLINotificationHandler, CLIProgressHandler; print('CLI handlers imported successfully')"
  # Assert: Output is "CLI handlers imported successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from import verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 12)
  - Message: `feat(cli): implement CLI I/O handlers with Click and Rich`
  - Files: `src/opencode_python/cli/handlers.py`
  - Pre-commit: `pytest tests/test_cli_handlers.py`

- [ ] 8. Implement TUI Handlers

  **What to do**:
  - Create `src/opencode_python/tui/handlers.py`
  - Implement TUIIOHandler class:
    - prompt(): Use Textual Input modal
    - confirm(): Use Textual confirm dialog
    - select(): Use Textual select dropdown
    - multi_select(): Use Textual multi-select
  - Implement TUINotificationHandler class:
    - show(): Use Textual app.notify() with severity mapping
    - Map NotificationType to Textual severity (INFO=information, SUCCESS=information, WARNING=warning, ERROR=error)
  - Implement TUIProgressHandler class:
    - start(): Update status bar widget
    - update(): Update progress text
    - complete(): Show completion message
  - Add type hints for all methods
  - Add docstrings for all classes and methods
  - Ensure all handlers implement respective protocols from Task 1

  **Must NOT do**:
  - Don't import CLI modules
  - Don't modify existing TUI screens (handlers are for I/O only)
  - Don't modify existing TUI app (next task)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: TUI handler implementation requires Textual framework integration
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of TUI changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7) | Sequential
  - **Blocks**: Task 13 | Task 1 (protocols must exist)
  - **Blocked By**: Task 1 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/tui/app.py:35-56` - Existing TUI binding patterns to follow
  - `src/opencode_python/tui/app.py:161-168` - Existing TUI event handling patterns
  - `src/opencode_python/interfaces/io.py` - Protocol definitions to implement

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/interfaces/io.py:IOHandler` - Protocol to implement
  - `src/opencode_python/interfaces/io.py:ProgressHandler` - Protocol to implement
  - `src/opencode_python/interfaces/io.py:NotificationHandler` - Protocol to implement
  - `textual.app.notify()` - Textual docs for notifications
  - `textual.widgets.Input` - Textual docs for input modals
  - `textual.widgets.Select` - Textual docs for selection

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - Create new test file: `tests/test_tui_handlers.py`

  **Documentation References** (specs and requirements):
  - Oracle recommendations - TUI handler examples from Metis consultation
  - Textual docs: https://textual.textualize.io/

  **External References** (libraries and frameworks):
  - None (Textual patterns from docs)

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/tui/app.py:35-56`: Follow existing Textual patterns for consistency
  - `src/opencode_python/interfaces/io.py`: Implement protocol contracts correctly

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_tui_handlers.py
  - [ ] Test covers: TUIIOHandler implements IOHandler protocol
  - [ ] Test covers: TUIIOHandler.prompt() uses Textual input modal
  - [ ] Test covers: TUIIOHandler.confirm() uses Textual confirm dialog
  - [ ] Test covers: TUIIOHandler.select() uses Textual select dropdown
  - [ ] Test covers: TUINotificationHandler implements NotificationHandler protocol
  - [ ] Test covers: TUINotificationHandler.show() uses Textual notify()
  - [ ] Test covers: TUIProgressHandler implements ProgressHandler protocol
  - [ ] Test covers: TUIProgressHandler.start/update/complete uses status bar
  - [ ] pytest tests/test_tui_handlers.py -v → PASS (6 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For TUI changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "from opencode_python.tui.handlers import TUIIOHandler, TUINotificationHandler, TUIProgressHandler; print('TUI handlers imported successfully')"
  # Assert: Output is "TUI handlers imported successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from import verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 13)
  - Message: `feat(tui): implement TUI I/O handlers with Textual`
  - Files: `src/opencode_python/tui/handlers.py`
  - Pre-commit: `pytest tests/test_tui_handlers.py`

- [x] 9. Implement SDK Client (Async)

  **What to do**:
  - Create `src/opencode_python/sdk/client.py`
  - Define SDKConfig dataclass (from Task 4)
  - Define OpenCodeAsyncClient class:
    - __init__ accepts SDKConfig, handlers (all optional)
    - create_session(): Calls SessionService.create_session with handlers
    - get_session(): Calls SessionService.get_session
    - list_sessions(): Calls SessionService.list_sessions
    - delete_session(): Calls SessionService.delete_session
    - add_message(): Calls SessionService.add_message
    - All methods are async
  - Add error handling: catch exceptions from services, re-raise for SDK users
  - Add type hints for all methods
  - Add docstrings for all classes and methods
  - Add callbacks support: on_progress(), on_notification() methods

  **Must NOT do**:
  - Don't create sync Client yet (next task)
  - Don't import CLI or TUI modules
  - Don't add UI-specific logic (SDK is headless)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: SDK client implementation requires careful async API design
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of SDK changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 3 (with Tasks 10, 11) | Sequential
  - **Blocks**: Task 10 | Task 5 (DefaultSessionService must exist)
  - **Blocked By**: Task 5 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - None (new SDK implementation)
  - `src/opencode_python/core/services/session_service.py` - Service to wrap

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/core/services/session_service.py:SessionService` - Protocol to use
  - `src/opencode_python/core/config.py:SDKConfig` - Config to use
  - `src/opencode_python/core/exceptions.py:SessionError` - Exceptions to handle

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - Create new test file: `tests/test_sdk_async_client.py`

  **Documentation References** (specs and requirements):
  - Oracle recommendations - SDK client examples from Metis consultation
  - Python asyncio docs: https://docs.python.org/3/library/asyncio.html

  **External References** (libraries and frameworks):
  - None (standard library and existing patterns)

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/core/services/session_service.py`: Wrap service methods with error handling for SDK users

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_sdk_async_client.py
  - [ ] Test covers: OpenCodeAsyncClient creates session via SessionService
  - [ ] Test covers: OpenCodeAsyncClient.get_session() returns Session or None
  - [ ] Test covers: OpenCodeAsyncClient.list_sessions() returns list of Session
  - [ ] Test covers: OpenCodeAsyncClient.delete_session() calls notification handler
  - [ ] Test covers: OpenCodeAsyncClient.add_message() calls progress handler
  - [ ] Test covers: Service exceptions are propagated to SDK user
  - [ ] Test covers: on_progress callback is called when progress updates
  - [ ] Test covers: on_notification callback is called when notifications occur
  - [ ] pytest tests/test_sdk_async_client.py -v → PASS (8 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Library/Module changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "from opencode_python.sdk.client import OpenCodeAsyncClient; print('Async SDK client imported successfully')"
  # Assert: Output is "Async SDK client imported successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from import verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 14)
  - Message: `feat(sdk): add async SDK client with handler injection`
  - Files: `src/opencode_python/sdk/client.py`
  - Pre-commit: `pytest tests/test_sdk_async_client.py`

- [x] 10. Implement SDK Client (Sync)

  **What to do**:
  - Add OpenCodeClient class to `src/opencode_python/sdk/client.py`
  - Define OpenCodeClient class (sync version):
    - __init__ accepts SDKConfig, handlers (all optional)
    - create_session(): Wraps OpenCodeAsyncClient.create_session with asyncio.run()
    - get_session(): Wraps OpenCodeAsyncClient.get_session with asyncio.run()
    - list_sessions(): Wraps OpenCodeAsyncClient.list_sessions with asyncio.run()
    - delete_session(): Wraps OpenCodeAsyncClient.delete_session with asyncio.run()
    - add_message(): Wraps OpenCodeAsyncClient.add_message with asyncio.run()
    - All methods are sync (use asyncio.run internally)
  - Add error handling: same as async client
  - Add type hints for all methods
  - Add docstrings explaining sync vs async trade-offs
  - Export both Client and AsyncClient from sdk/__init__.py

  **Must NOT do**:
  - Don't duplicate business logic (delegate to async client)
  - Don't add new SDK-specific features

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Sync client implementation requires careful asyncio wrapper design
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of SDK changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 3 (with Task 9) | Sequential
  - **Blocks**: None | Task 9 (async client must exist)
  - **Blocked By**: Task 9 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/sdk/client.py` - OpenCodeAsyncClient from Task 9
  - `asyncio.run()` - Python asyncio wrapper for sync execution

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/sdk/client.py:OpenCodeAsyncClient` - Async client to wrap

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/test_sdk_async_client.py` - Tests from Task 9

  **Documentation References** (specs and requirements):
  - Oracle recommendations - Sync + Async API from Metis consultation
  - Python asyncio docs: https://docs.python.org/3/library/asyncio.html#asyncio.run

  **External References** (libraries and frameworks):
  - None (standard library)

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/sdk/client.py`: Delegte to async client to avoid business logic duplication

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_sdk_sync_client.py
  - [ ] Test covers: OpenCodeClient wraps OpenCodeAsyncClient
  - [ ] Test covers: OpenCodeClient.create_session() uses asyncio.run()
  - [ ] Test covers: OpenCodeClient.get_session() uses asyncio.run()
  - [ ] Test covers: OpenCodeClient.list_sessions() uses asyncio.run()
  - [ ] Test covers: OpenCodeClient.delete_session() uses asyncio.run()
  - [ ] Test covers: OpenCodeClient.add_message() uses asyncio.run()
  - [ ] pytest tests/test_sdk_sync_client.py -v → PASS (5 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Library/Module changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "from opencode_python.sdk.client import OpenCodeClient; print('Sync SDK client imported successfully')"
  # Assert: Output is "Sync SDK client imported successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from import verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 9, 10)
  - Message: `feat(sdk): add sync SDK client with asyncio.run() wrappers`
  - Files: `src/opencode_python/sdk/client.py`
  - Pre-commit: `pytest tests/test_sdk_sync_client.py`

- [x] 11. Create Hybrid EventBus Integration

  **What to do**:
  - Create `src/opencode_python/core/event_bus_integration.py`
  - Implement EventBus subscriber for NotificationHandler:
    - Subscribe to session.created, message.created, session.updated events
    - Map events to NotificationHandler.show() calls
    - Handle event errors gracefully
  - Ensure NotificationHandler can subscribe/unsubscribe from events
  - Add type hints and docstrings
  - Maintain existing EventBus functionality (no breaking changes)
  - Add integration tests for event → notification flow

  **Must NOT do**:
  - Don't modify core EventBus (keep as-is)
  - Don't remove direct handler calls (hybrid approach)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: EventBus integration requires careful async event handling
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of EventBus changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 3 (with Tasks 9, 10) | Sequential
  - **Blocks**: None | Task 5, 6 (core services and handlers must exist)
  - **Blocked By**: Task 5, 6 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/core/event_bus.py:1-126` - Existing EventBus to integrate with
  - `src/opencode_python/interfaces/io.py` - NotificationHandler protocol to use

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/core/event_bus.py:Events` - Event constants to subscribe to
  - `src/opencode_python/interfaces/io.py:NotificationHandler` - Protocol to subscribe

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - Create new test file: `tests/test_event_bus_integration.py`

  **Documentation References** (specs and requirements):
  - Oracle recommendations - Hybrid EventBus integration from Metis consultation
  - Existing EventBus docstrings - Event usage patterns

  **External References** (libraries and frameworks):
  - None (standard library and existing patterns)

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/core/event_bus.py:1-126`: Integrate with existing EventBus without breaking changes
  - `src/opencode_python/interfaces/io.py`: Map EventBus events to NotificationHandler

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_event_bus_integration.py
  - [ ] Test covers: NotificationHandler subscribes to EventBus events
  - [ ] Test covers: session.created event triggers NotificationHandler.show()
  - [ ] Test covers: message.created event triggers NotificationHandler.show()
  - [ ] Test covers: NotificationHandler can unsubscribe from events
  - [ ] Test covers: Event errors are handled gracefully
  - [ ] pytest tests/test_event_bus_integration.py -v → PASS (4 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Library/Module changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "from opencode_python.core.event_bus_integration import EventBusNotificationSubscriber; print('EventBus integration imported successfully')"
  # Assert: Output is "EventBus integration imported successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from import verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 11)
  - Message: `feat(core): add hybrid EventBus integration with NotificationHandler subscription`
  - Files: `src/opencode_python/core/event_bus_integration.py`
  - Pre-commit: `pytest tests/test_event_bus_integration.py`

- [ ] 12. Refactor CLI Commands

  **What to do**:
  - Update `src/opencode_python/cli/main.py`
  - Import handlers from cli/handlers (Task 7)
  - Import SessionService from core/services/session_service
  - Create CLIIOHandler, CLIProgressHandler, CLINotificationHandler instances
  - Pass handlers to SessionService constructor
  - Update list_sessions command to use SessionService.list_sessions()
  - Update export_session command to use SessionService with handlers
  - Update import_session command to use SessionService with handlers
  - Remove line 84-85 (TUI import and launch) - replace with deprecation warning
  - Add deprecation warning for CLI → TUI launch behavior
  - Maintain backward compatibility: existing CLI commands still work
  - Add type hints and docstrings
  - Ensure all Click command signatures unchanged

  **Must NOT do**:
  - Don't change CLI command signatures (arguments, options)
  - Don't add new CLI commands
  - Don't modify CLI help text (keep as-is)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: CLI refactoring requires careful backward compatibility maintenance
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of CLI changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 4 (with Tasks 13, 14, 15) | Sequential
  - **Blocks**: Task 15 | Task 7 (handlers must exist)
  - **Blocked By**: Task 7 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/cli/main.py:23-159` - CLI commands to refactor
  - `src/opencode_python/cli/main.py:84-85` - Lines to remove (TUI import)
  - `src/opencode_python/cli/handlers.py` - Handler implementations to use
  - `src/opencode_python/core/services/session_service.py` - SessionService to use

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/cli/handlers.py` - Handlers to instantiate
  - `src/opencode_python/core/services/session_service.py` - Service to use

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - Create new test file: `tests/test_cli_integration.py`

  **Documentation References** (specs and requirements):
  - Oracle recommendations - CLI refactoring from Metis consultation
  - Existing CLI command docstrings - Maintain behavior

  **External References** (libraries and frameworks):
  - Click docs: https://click.palletsprojects.com/en/stable/api/

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/cli/main.py:84-85`: Remove CLI → TUI coupling as user decided on shared sessions
  - `src/opencode_python/cli/main.py:23-159`: Refactor to use SessionService and handlers

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_cli_integration.py
  - [ ] Test covers: list_sessions command works with SessionService
  - [ ] Test covers: export_session command works with SessionService and handlers
  - [ ] Test covers: import_session command works with SessionService and handlers
  - [ ] Test covers: CLI commands use handlers (progress, notifications)
  - [ ] Test covers: Deprecation warning shown for CLI → TUI launch
  - [ ] Test covers: Backward compatibility maintained (output unchanged)
  - [ ] pytest tests/test_cli_integration.py -v → PASS (6 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For CLI changes** (using Bash click):
  ```bash
  # Agent runs:
  opencode list-sessions --help
  # Assert: Help text unchanged
  # Assert: Command still works
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from help command (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 7, 12, 14)
  - Message: `refactor(cli): use SessionService and handlers, remove TUI import`
  - Files: `src/opencode_python/cli/main.py`
  - Pre-commit: `pytest tests/test_cli_integration.py`

- [ ] 13. Refactor TUI App

  **What to do**:
  - Update `src/opencode_python/tui/app.py`
  - Import handlers from tui/handlers (Task 8)
  - Import SessionService from core/services/session_service
  - Create TUIIOHandler, TUIProgressHandler, TUINotificationHandler instances
  - Pass handlers to SessionService constructor
  - Update session loading to use SessionService.list_sessions()
  - Update session creation to use SessionService.create_session()
  - Update message screen to use handlers for progress and notifications
  - Remove any direct I/O calls (print, input) from TUI screens
  - Maintain backward compatibility: existing TUI behavior unchanged
  - Add type hints and docstrings
  - Ensure Textual app structure unchanged

  **Must NOT do**:
  - Don't change TUI layout or styling
  - Don't modify TUI keybindings
  - Don't add new TUI screens

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: TUI refactoring requires careful Textual framework integration
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of TUI changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 4 (with Tasks 12, 14, 15) | Sequential
  - **Blocks**: Task 16 | Task 8 (handlers must exist)
  - **Blocked By**: Task 8 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/tui/app.py:1-257` - TUI app to refactor
  - `src/opencode_python/tui/screens/message_screen.py` - Message screen to update
  - `src/opencode_python/tui/handlers.py` - Handlers to use
  - `src/opencode_python/core/services/session_service.py` - SessionService to use

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/tui/handlers.py` - Handlers to instantiate
  - `src/opencode_python/core/services/session_service.py` - Service to use

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - Create new test file: `tests/test_tui_integration.py`

  **Documentation References** (specs and requirements):
  - Oracle recommendations - TUI refactoring from Metis consultation
  - Existing TUI docstrings - Maintain behavior

  **External References** (libraries and frameworks):
  - Textual docs: https://textual.textualize.io/

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/tui/app.py:1-257`: Refactor to use SessionService and handlers while maintaining Textual behavior
  - `src/opencode_python/tui/handlers.py`: Use TUI-specific I/O implementations

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_tui_integration.py
  - [ ] Test covers: TUI app launches with SessionService and handlers
  - [ ] Test covers: Session list loads correctly from SessionService
  - [ ] Test covers: Session creation uses SessionService with handlers
  - [ ] Test covers: TUI notifications use handlers
  - [ ] Test covers: TUI progress updates use handlers
  - [ ] Test covers: Backward compatibility maintained (visuals unchanged)
  - [ ] pytest tests/test_tui_integration.py -v → PASS (6 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For TUI changes** (using Bash python):
  ```bash
  # Agent runs:
  python -c "from opencode_python.tui.app import OpenCodeTUI; print('TUI app imported successfully')"
  # Assert: Output is "TUI app imported successfully"
  # Assert: No import errors
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from import verification (actual output, not expected)
  - [ ] pytest test results output

  **Commit**: YES | NO (groups with 8, 13, 14)
  - Message: `refactor(tui): use SessionService and handlers, remove direct I/O calls`
  - Files: `src/opencode_python/tui/app.py`
  - Pre-commit: `pytest tests/test_tui_integration.py`

- [ ] 14. Update pyproject.toml

  **What to do**:
  - Update `pyproject.toml`
  - Split dependencies into:
    - `dependencies` (core: always installed) - aiofiles, aiohttp, pendulum, pydantic, pydantic-settings, python-frontmatter, tiktoken
    - `dependencies.cli` (CLI only) - click, rich
    - `dependencies.tui` (TUI only) - textual
  - Create `project.optional-dependencies` section:
    - `cli = ["opencode-python[core]", "click", "rich"]`
    - `tui = ["opencode-python[core]", "textual"]`
    - `full = ["opencode-python[cli,tui]"]`
  - Update `project.scripts` to be conditional:
    - Only install `opencode` command if `[cli]` or `[full]` installed
  - Update description to mention CLI, TUI, and SDK
  - Add `sdk` to `project.optional-dependencies` if needed (currently just core)
  - Verify imports in package __init__.py work with optional deps

  **Must NOT do**:
  - Don't add new dependencies beyond Click and Rich for CLI
  - Don't change core dependencies list (keep as-is)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple pyproject.toml update, straightforward task
  - **Skills**: `["git-master"]`
    - `git-master`: For verifying dependency changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 4 (with Tasks 12, 13, 14) | Sequential
  - **Blocks**: Task 17 | Task 9, 10 (SDK clients must exist)
  - **Blocked By**: Task 9, 10 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `pyproject.toml:27-41` - Current dependencies to restructure
  - `pyproject.toml:53-54` - Entry points to update

  **API/Type References** (contracts to implement against):
  - PEP 621 pyproject.toml specification
  - PEP 508 optional dependencies specification

  **Test References** (testing patterns to follow):
  - None (verify by installation)

  **Documentation References** (specs and requirements):
  - Python packaging docs: https://packaging.python.org/en/latest/specifications/declaring-dependencies

  **External References** (libraries and frameworks):
  - uv_build docs: https://astral-sh.github.io/uv-build/

  **WHY Each Reference Matters** (explain the relevance):
  - `pyproject.toml:27-41`: Restructure dependencies to support optional extras
  - `pyproject.toml:53-54`: Update entry points to be conditional

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test covers: `pip install -e . opencode[core]` works
  - [ ] Test covers: `pip install -e . opencode[cli]` works
  - [ ] Test covers: `pip install -e . opencode[tui]` works
  - [ ] Test covers: `pip install -e . opencode[full]` works
  - [ ] Test covers: `opencode` command available when `[cli]` installed
  - [ ] Test covers: `opencode` command NOT available when `[core]` only installed
  - [ ] Test covers: TUI can launch when `[tui]` installed
  - [ ] Test covers: SDK import works with `[core]` only (no Click, no Textual)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Config/Infra changes** (using Bash pip):
  ```bash
  # Agent runs:
  pip install -e . opencode[core]
  python -c "import opencode_python; print('Core installation successful')"
  # Assert: Output is "Core installation successful"
  # Assert: No import errors

  pip install -e . opencode[cli]
  opencode --help
  # Assert: Help output shown
  # Assert: CLI works

  pip install -e . opencode[tui]
  python -c "from opencode_python.tui.app import OpenCodeTUI; print('TUI import successful')"
  # Assert: Output is "TUI import successful"
  # Assert: TUI works
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from all installation modes (actual output, not expected)
  - [ ] pip install logs

  **Commit**: YES | NO (groups with 9, 10, 11, 12, 13)
  - Message: `feat(build): split dependencies into [core], [cli], [tui], [full] extras`
  - Files: `pyproject.toml`
  - Pre-commit: (verify installations)

- [ ] 15. Write Unit Tests

  **What to do**:
  - Create unit tests for all new components:
    - `tests/test_protocols.py` (from Task 1)
    - `tests/test_session_service.py` (from Task 2)
    - `tests/test_exceptions.py` (from Task 3)
    - `tests/test_config.py` (from Task 4)
    - `tests/test_thread_safety.py` (from Task 6)
    - `tests/test_cli_handlers.py` (from Task 7)
    - `tests/test_tui_handlers.py` (from Task 8)
    - `tests/test_sdk_async_client.py` (from Task 9)
    - `tests/test_sdk_sync_client.py` (from Task 10)
    - `tests/test_event_bus_integration.py` (from Task 11)
  - Ensure each test file has comprehensive coverage of its component
  - Use pytest-asyncio for async tests
  - Use mock fixtures for handler dependencies
  - Add docstrings explaining what each test verifies
  - Follow TDD RED-GREEN-REFACTOR (tests written first, then implementation)

  **Must NOT do**:
  - Don't create E2E tests (unit only)
  - Don't create property-based tests
  - Don't add performance tests

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Unit test writing requires careful test design and mocking
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of test changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 5 (with Task 16, 17) | Sequential
  - **Blocks**: Task 16, 18 | Task 12, 13, 14 (CLI/TUI refactored, pyproject updated)
  - **Blocked By**: Task 12, 13, 14 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/tests/` - Existing test directory structure
  - `tests/` - Follow existing test patterns (pytest, pytest-asyncio)

  **API/Type References** (contracts to implement against):
  - pytest documentation: https://docs.pytest.org/
  - pytest-asyncio documentation: https://pytest-asyncio.readthedocs.io/

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Existing test directory structure

  **Documentation References** (specs and requirements):
  - Pytest docs: Write unit tests with pytest and pytest-asyncio
  - Oracle recommendations: Unit tests for protocols and core services from Metis consultation

  **External References** (libraries and frameworks):
  - unittest.mock - For mocking handlers in unit tests

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/tests/`: Follow existing test directory structure and patterns

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] All 10 test files created (listed above)
  - [ ] Test files use pytest and pytest-asyncio decorators
  - [ ] Tests mock handlers with unittest.mock
  - [ ] Test coverage for protocols: 100% of protocol methods
  - [ ] Test coverage for services: 80% of service methods
  - [ ] Test coverage for SDK clients: 90% of client methods
  - [ ] pytest tests/ -v → PASS (50+ tests, 0 failures)
  - [ ] Test execution time < 60s (performance sanity check)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Test Infrastructure** (using Bash pytest):
  ```bash
  # Agent runs:
  pytest tests/ -v
  # Assert: 50+ tests pass
  # Assert: 0 failures
  # Assert: Execution time < 60s
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from pytest run (actual output, not expected)
  - [ ] Test coverage report (if available)

  **Commit**: YES | NO (groups with all implementation tasks)
  - Message: `test: add comprehensive unit tests for protocols, services, handlers, SDK`
  - Files: `tests/test_*.py` (10 new test files)
  - Pre-commit: `pytest tests/`

- [ ] 16. Write Integration Tests

  **What to do**:
  - Create integration tests for CLI and TUI:
    - `tests/test_cli_integration.py` - CLI end-to-end workflows
    - `tests/test_tui_integration.py` - TUI end-to-end workflows
  - Test CLI commands work with real Click runner (not mocked)
  - Test TUI app launches with real Textual pilot (not mocked)
  - Test CLI uses handlers correctly (progress, notifications shown)
  - Test TUI uses handlers correctly (progress, notifications shown)
  - Test backward compatibility: CLI/TUI behavior unchanged from user perspective
  - Add docstrings explaining what each integration test verifies
  - Use Click testing patterns for CLI (CliRunner)
  - Use Textual testing patterns for TUI (app.run_test())

  **Must NOT do**:
  - Don't mock core services (use real SessionService)
  - Don't create E2E tests beyond CLI/TUI workflows

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration test writing requires careful real-world scenario testing
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of integration test changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 4 (with Task 15) | Sequential
  - **Blocks**: Task 18 | Task 12, 13 (CLI/TUI refactored)
  - **Blocked By**: Task 12, 13 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/cli/main.py` - CLI to test
  - `src/opencode_python/tui/app.py` - TUI to test
  - `src/opencode_python/tests/` - Test directory structure
  - Click testing docs: https://click.palletsprojects.com/en/stable/testing/
  - Textual testing docs: https://textual.textualize.io/guide/sub_apps_and_screens/

  **API/Type References** (contracts to implement against):
  - `click.testing.CliRunner` - Click test runner
  - `textual.app.run_test()` - Textual test pilot

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Test directory structure

  **Documentation References** (specs and requirements):
  - Oracle recommendations: Integration tests for CLI/TUI from Metis consultation
  - Click and Textual testing documentation

  **External References** (libraries and frameworks):
  - None (Click and Textual patterns from docs)

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/cli/main.py`: Test real CLI behavior
  - `src/opencode_python/tui/app.py`: Test real TUI behavior

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Test file created: tests/test_cli_integration.py
  - [ ] Test file created: tests/test_tui_integration.py
  - [ ] CLI tests use Click CliRunner (not mocked services)
  - [ ] TUI tests use Textual app.run_test() (not mocked services)
  - [ ] Test covers: CLI list_sessions command works
  - [ ] Test covers: CLI export_session command works
  - [ ] Test covers: CLI import_session command works
  - [ ] Test covers: CLI shows progress updates via handlers
  - [ ] Test covers: CLI shows notifications via handlers
  - [ ] Test covers: TUI session list loads correctly
  - [ ] Test covers: TUI session creation works
  - [ ] Test covers: TUI shows progress updates via handlers
  - [ ] Test covers: TUI shows notifications via handlers
  - [ ] Test covers: Backward compatibility maintained (output/behavior unchanged)
  - [ ] pytest tests/test_cli_integration.py -v → PASS (6 tests, 0 failures)
  - [ ] pytest tests/test_tui_integration.py -v → PASS (6 tests, 0 failures)

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Integration Tests** (using Bash pytest):
  ```bash
  # Agent runs:
  pytest tests/test_cli_integration.py tests/test_tui_integration.py -v
  # Assert: 12 tests pass (6 CLI + 6 TUI)
  # Assert: 0 failures
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from pytest run (actual output, not expected)
  - [ ] Test execution time

  **Commit**: YES | NO (groups with 15, 16)
  - Message: `test: add integration tests for CLI and TUI workflows`
  - Files: `tests/test_cli_integration.py`, `tests/test_tui_integration.py`
  - Pre-commit: `pytest tests/test_cli_integration.py tests/test_tui_integration.py`

- [ ] 17. Create SDK Examples

  **What to do**:
  - Create `examples/` directory in opencode_python package
  - Create `examples/basic_sdk_usage.py`:
    - Show how to install SDK with `pip install opencode[core]`
    - Show how to create session with SDK
    - Show how to add message with SDK
    - Show how to list sessions with SDK
    - Show error handling pattern
  - Create `examples/custom_io_handler.py`:
    - Show how to implement custom IOHandler
    - Show how to pass custom handler to SDK
    - Show use case (e.g., web application integration)
  - Create `examples/error_handling.py`:
    - Show exception hierarchy usage
    - Show try/except patterns for SDK errors
    - Show error recovery strategies (retry, fallback)
  - Create `examples/sync_vs_async.py`:
    - Show when to use Client vs AsyncClient
    - Show performance implications
    - Show asyncio.run() for sync contexts
  - Add docstrings and comments explaining each example
  - Ensure examples run without errors

  **Must NOT do**:
  - Don't create more than 4 examples (keep focused)
  - Don't add tutorials beyond basic usage

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: SDK documentation and examples require clear, explanatory writing
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of documentation changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 5 (with Task 17) | Sequential
  - **Blocks**: Task 18 | Task 9, 10 (SDK clients must exist)
  - **Blocked By**: Task 9, 10 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `src/opencode_python/sdk/client.py` - SDK client to demonstrate
  - `src/opencode_python/interfaces/io.py` - Handler protocols to implement

  **API/Type References** (contracts to implement against):
  - SDK Client API (from Task 9, 10)

  **Test References** (testing patterns to follow):
  - `src/opencode_python/tests/` - Test directory structure

  **Documentation References** (specs and requirements):
  - Oracle recommendations: SDK documentation from Metis consultation
  - Python SDK best practices - Clear, concise examples

  **External References** (libraries and frameworks):
  - None (standard library and SDK patterns)

  **WHY Each Reference Matters** (explain the relevance):
  - `src/opencode_python/sdk/client.py`: Demonstrate SDK usage patterns
  - `src/opencode_python/interfaces/io.py`: Show custom handler implementation

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] Example file created: examples/basic_sdk_usage.py
  - [ ] Example file created: examples/custom_io_handler.py
  - [ ] Example file created: examples/error_handling.py
  - [ ] Example file created: examples/sync_vs_async.py
  - [ ] All examples import SDK correctly (no CLI/TUI dependencies)
  - [ ] All examples run without errors
  - [ ] Examples demonstrate both Client (sync) and AsyncClient (async)
  - [ ] Examples show error handling patterns
  - [ ] Examples show custom IOHandler usage
  - [ ] Examples have clear docstrings and comments

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Example Code** (using Bash python):
  ```bash
  # Agent runs:
  python examples/basic_sdk_usage.py
  # Assert: No errors
  # Assert: Expected output shown

  python examples/custom_io_handler.py
  # Assert: No errors
  # Assert: Custom handler called

  python examples/error_handling.py
  # Assert: No errors
  # Assert: Error handling demonstrated

  python examples/sync_vs_async.py
  # Assert: No errors
  # Assert: Sync and async both demonstrated
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from all example runs (actual output, not expected)
  - [ ] Example execution time

  **Commit**: YES | NO (groups with 9, 10, 15, 16)
  - Message: `docs: add SDK examples for basic usage, custom handlers, error handling`
  - Files: `examples/basic_sdk_usage.py`, `examples/custom_io_handler.py`, `examples/error_handling.py`, `examples/sync_vs_async.py`
  - Pre-commit: `python examples/*.py`

- [ ] 18. Write Documentation

  **What to do**:
  - Update `README.md` with SDK section:
    - Quick start guide
    - Installation instructions (`pip install opencode[core]`, `[cli]`, `[tui]`, `[full]`)
    - Basic SDK usage example
    - Link to examples directory
    - Link to API reference
  - Create `docs/migration.md`:
    - Document breaking changes (if any)
    - Provide migration snippets from old CLI/TUI to new SDK usage
    - Document deprecation warnings timeline
    - Explain how to update code
  - Update `CONTRIBUTING.md`:
    - Add Bridge pattern architecture section
    - Document I/O handler implementation for new interfaces
    - Document service extension patterns
  - Ensure all documentation is clear and concise
  - Add code examples to documentation where helpful

  **Must NOT do**:
  - Don't create tutorials (beyond basic usage)
  - Don't add troubleshooting guides
  - Don't create recipes or advanced patterns

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation requires clear, explanatory writing
  - **Skills**: `["git-master"]`
    - `git-master`: For checking git history of documentation changes

  - **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave 6 (final task) | Sequential
  - **Blocks**: None | Task 17 (examples must exist)

  **Blocked By**: Task 17 | None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `README.md` - Existing README to update
  - `docs/` - Existing docs directory
  - `examples/` - Examples to reference

  **API/Type References** (contracts to implement against):
  - SDK Client API (from Tasks 9, 10)
  - I/O Handler Protocols (from Task 1)

  **Test References** (testing patterns to follow):
  - None (documentation doesn't require tests)

  **Documentation References** (specs and requirements):
  - Oracle recommendations: Documentation from Metis consultation
  - Python SDK best practices - Clear README with quick start

  **External References** (libraries and frameworks):
  - None (standard documentation practices)

  **WHY Each Reference Matters** (explain the relevance):
  - `README.md`: Update main documentation with SDK information
  - `examples/`: Reference examples in documentation

  **Acceptance Criteria**:

  **TDD (tests enabled)**:
  - [ ] README.md updated with SDK section
  - [ ] README.md includes installation instructions for all extras
  - [ ] README.md includes quick start example
  - [ ] README.md links to examples directory
  - [ ] docs/migration.md created with breaking changes documented
  - [ ] docs/migration.md includes migration snippets
  - [ ] CONTRIBUTING.md updated with Bridge pattern section
  - [ ] All documentation is clear and free of typos

  **Automated Verification (ALWAYS include, choose by deliverable type)**:

  **For Documentation** (using Bash):
  ```bash
  # Agent runs:
  head -50 README.md
  # Assert: SDK section present
  # Assert: Installation instructions present
  # Assert: Quick start example present

  cat docs/migration.md
  # Assert: Migration guide content exists
  # Assert: Code snippets present
  ```

  **Evidence to Capture**:
  - [ ] Terminal output from README check (first 50 lines)
  - [ ] Terminal output from migration guide check

  **Commit**: YES | NO (groups with all tasks)
  - Message: `docs: add SDK documentation with README, migration guide, CONTRIBUTING updates`
  - Files: `README.md`, `docs/migration.md`, `CONTRIBUTING.md`
  - Pre-commit: (verify documentation)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|--------|--------------|
| 1-4 | `feat(core): add I/O protocols, service interfaces, error hierarchy, config classes` | `interfaces/io.py`, `core/services/session_service.py`, `core/exceptions.py`, `core/config.py` | `pytest tests/` |
| 5-6 | `feat(core): implement DefaultSessionService with thread-safe SessionManager` | `core/session.py`, `core/session_service.py` (refactor) | `pytest tests/` |
| 7-8 | `feat(cli): implement CLI I/O handlers`<br>`feat(tui): implement TUI I/O handlers` | `cli/handlers.py`, `tui/handlers.py` | `pytest tests/` |
| 9-11 | `feat(sdk): add async SDK client, sync SDK client, hybrid EventBus integration` | `sdk/client.py`, `core/event_bus_integration.py` | `pytest tests/` |
| 12-14 | `refactor(cli): use SessionService and handlers, remove TUI import`<br>`refactor(tui): use SessionService and handlers` | `cli/main.py`, `tui/app.py` | `pytest tests/` |
| 15-16 | `test: add comprehensive unit and integration tests` | `tests/test_*.py` | `pytest tests/` |
| 17 | `docs: add SDK examples` | `examples/*.py` | `python examples/*.py` |
| 18 | `docs: add SDK documentation with README, migration guide` | `README.md`, `docs/migration.md`, `CONTRIBUTING.md` | (verify documentation) |

---

## Wave Progress Tracker

| Wave | Tasks | Status | Last Updated |
|-------|--------|--------|--------------|
| Wave 1 | 1-4 | Complete | 2026-01-29 |
| Wave 2 | 5-8 | Complete | 2026-01-29 |
| Wave 3 | 9-11 | Complete | 2026-01-29 |
| Wave 4 | 12-14 | Complete | 2026-01-29 |
| Wave 5 | 15-17 | Complete | 2026-01-29 |
| Wave 6 | 18 | Pending | 2026-01-29 |

**Overall Progress**: 17/18 tasks complete (94%)

## Wave Summaries

### Wave 3: SDK Client Implementation (Complete)

**Tasks Completed:**
- Task 9: Implement SDK Client (Async) - Built async SDK client with handler injection, SDKConfig support, error handling, and callback support
- Task 10: Implement SDK Client (Sync) - Created sync SDK client wrapping async client with asyncio.run() for sync contexts
- Task 11: Create Hybrid EventBus Integration - Integrated EventBus with NotificationHandler for event-driven notifications

**Key Achievements:**
- Both sync and async SDK clients fully functional
- Configuration system supports all SDK options (storage_path, project_dir, auto_confirm, enable_progress, enable_notifications)
- Handler injection pattern implemented throughout SDK layer
- Hybrid EventBus integration supports both event-driven and direct handler calls
- Full error handling with domain-specific exceptions (SessionError, MessageError, etc.)
- Callback support for progress and notification callbacks

**Deliverables:**
- `src/opencode_python/sdk/client.py` - SDK client module with OpenCodeAsyncClient and OpenCodeClient
- `src/opencode_python/core/event_bus_integration.py` - EventBus subscriber for NotificationHandler
- Comprehensive unit tests for SDK clients (test_sdk_async_client.py, test_sdk_sync_client.py)
- Unit tests for EventBus integration (test_event_bus_integration.py)
- SDK examples prepared for documentation

### Wave 4: CLI/TUI Refactoring (Complete)

**Tasks Completed:**
- Task 12: Refactor CLI Commands - Updated CLI commands to use SessionService and handlers, added deprecation warning for TUI launch
- Task 13: Refactor TUI App - Updated TUI screens to use SessionService and handlers, created TUI handlers
- Task 14: Update pyproject.toml - Split dependencies into [core], [cli], [tui], [full] optional extras with dependency checking in entry point

**Key Achievements:**
- CLI now uses DefaultSessionService with handler injection pattern
- CLI creates CLIIOHandler, CLIProgressHandler, CLINotificationHandler instances for all commands
- TUI now uses DefaultSessionService with handler injection pattern
- TUI handlers (TUIIOHandler, TUIProgressHandler, TUINotificationHandler) implemented with Textual integration
- Deprecation warning added for CLI → TUI launch behavior
- Dependencies split into optional extras: [core], [cli], [tui], [full], [dev]
- Entry point checks for CLI dependencies (click, rich) and shows helpful error if missing
- Backward compatibility maintained: all CLI/TUI behavior unchanged from user perspective

**Deliverables:**
- `opencode_python/src/opencode_python/core/services/session_service.py` - DefaultSessionService with handler injection
- `opencode_python/src/opencode_python/cli/main.py` - Updated with deprecation warning
- `opencode_python/src/opencode_python/cli/__init__.py` - Entry point with dependency checking
- `opencode_python/src/opencode_python/tui/handlers.py` - TUI I/O handlers
- `opencode_python/src/opencode_python/tui/app.py` - Refactored to use SessionService
- `opencode_python/src/opencode_python/tui/screens/message_screen.py` - Updated for SessionService
- `opencode_python/pyproject.toml` - Split dependencies into optional extras
- `opencode_python/tests/test_cli_integration.py` - CLI integration tests
- `opencode_python/tests/test_tui_handlers.py` - TUI handler tests
- `opencode_python/tests/test_tui_integration.py` - TUI integration tests

**Dependencies:**
- Depends on Wave 3 completion (SDK clients and services must exist)
- Unblocks Wave 5 (testing) and Wave 6 (documentation)

---

## Success Criteria

### Verification Commands
```bash
# Test core installation
pip install -e . opencode[core]
python -c "import opencode_python; print('SDK import works')"

# Test CLI installation
pip install -e . opencode[cli]
opencode --help

# Test TUI installation
pip install -e . opencode[tui]
python -c "from opencode_python.tui.app import OpenCodeTUI; print('TUI import works')"

# Test full installation
pip install -e . opencode[full]
opencode --help
python -c "from opencode_python.tui.app import OpenCodeTUI; print('Both work')"

# Run all tests
pytest tests/ -v --cov=opencode_python

# Verify examples run
python examples/basic_sdk_usage.py
```

### Final Checklist
- [ ] All I/O handler protocols defined with @runtime_checkable
- [ ] Core services accept handlers via constructor with default no-op implementations
- [ ] CLI and TUI implement all I/O handler protocols
- [ ] SDK provides both sync (Client) and async (AsyncClient) APIs
- [ ] SessionManager is thread-safe with shared session storage
- [ ] Optional dependencies work: `pip install opencode[core]`, `[cli]`, `[tui]`, `[full]`
- [ ] Backward compatibility maintained (deprecation warnings in Phase 1-3)
- [ ] Unit tests for protocols and core services with mocked handlers (50+ tests)
- [ ] Integration tests for CLI and TUI (12+ tests)
- [ ] SDK examples and documentation (4 examples + README + migration guide)
- [ ] All tests pass (0 failures)
- [ ] Test coverage > 80% (optional but recommended)
