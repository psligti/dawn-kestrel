# Getting Started with OpenCode Python SDK

Welcome to OpenCode Python SDK! This guide will help you get started with using SDK for managing sessions and messages in your applications.

## Installation

Install SDK using pip:

```bash
pip install dawn-kestrel
```

For development with additional dependencies:

```bash
pip install dawn-kestrel[dev]
```

## Quick Start

The OpenCode Python SDK provides both async and sync clients for managing sessions. Choose async client for better performance and concurrency, or sync client for simpler integration with synchronous code.

## Async Client Usage

The `OpenCodeAsyncClient` is the recommended client for most use cases. It provides full async support and allows concurrent operations.

```python
import asyncio
from dawn_kestrel.sdk import OpenCodeAsyncClient

async def main() -> None:
    # Create async client with default configuration
    client = OpenCodeAsyncClient()

    # Create a new session
    session = await client.create_session(
        title="My Project",
        version="1.0.0"
    )
    print(f"Created session: {session.id}")

    # Add a message to session
    message = await client.add_message(
        session_id=session.id,
        content="Hello, OpenCode!"
    )
    print(f"Added message: {message.id}")

    # List all sessions
    sessions = await client.list_sessions()
    print(f"Total sessions: {len(sessions)}")

asyncio.run(main())
```

### Using Callbacks

The async client supports callbacks for progress and notifications:

```python
import asyncio
from dawn_kestrel.sdk import OpenCodeAsyncClient

async def main() -> None:
    client = OpenCodeAsyncClient()

    # Register progress callback
    def on_progress(current: int, message: str | None) -> None:
        print(f"Progress: {current} - {message}")

    client.on_progress(on_progress)

    # Register notification callback
    from dawn_kestrel.interfaces.io import Notification

    def on_notification(notification: Notification) -> None:
        print(f"Notification: {notification.notification_type} - {notification.message}")

    client.on_notification(on_notification)

    # Operations will trigger callbacks
    session = await client.create_session("My Project")

asyncio.run(main())
```

## Sync Client Usage

The `OpenCodeClient` provides a synchronous API that wraps the async client. Use this when you need to integrate with synchronous code or prefer simpler syntax without async/await.

```python
from dawn_kestrel.sdk import OpenCodeClient

def main() -> None:
    # Create sync client
    client = OpenCodeClient()

    # Create a new session (synchronous)
    session = client.create_session(
        title="My Project",
        version="1.0.0"
    )
    print(f"Created session: {session.id}")

    # Add a message (synchronous)
    message = client.add_message(
        session_id=session.id,
        content="Hello, OpenCode!"
    )
    print(f"Added message: {message.id}")

    # List all sessions (synchronous)
    sessions = client.list_sessions()
    print(f"Total sessions: {len(sessions)}")

if __name__ == "__main__":
    main()
```

**Note:** The sync client uses `asyncio.run()` internally for each operation, which blocks the calling thread. For better performance and concurrency, use the async client.

## Handler Configuration

The SDK uses a bridge pattern with pluggable handlers for I/O, progress tracking, and notifications. You can customize these handlers to integrate with your application's UI or logging systems.

### Default Handlers

By default, the client uses silent handlers:

```python
from dawn_kestrel.sdk import OpenCodeAsyncClient

# Uses QuietIOHandler, NoOpProgressHandler, NoOpNotificationHandler
client = OpenCodeAsyncClient()
```

### Custom I/O Handler

Implement your own I/O handler for user interaction:

```python
from dawn_kestrel.interfaces.io import IOHandler
from dawn_kestrel.sdk import OpenCodeAsyncClient

class MyIOHandler(IOHandler):
    """Custom I/O handler for your application."""

    async def prompt(self, message: str, default: str | None = None) -> str:
        print(f"PROMPT: {message}")
        if default:
            print(f"  (default: {default})")
        result = input("> ")
        return result if result else (default or "")

    async def confirm(self, message: str, default: bool = False) -> bool:
        print(f"CONFIRM: {message} (y/n) {'[y]' if default else '[n]'}")
        result = input("> ").lower()
        if not result:
            return default
        return result in ('y', 'yes')

    async def select(self, message: str, options: list[str]) -> str:
        print(f"SELECT: {message}")
        for i, option in enumerate(options):
            print(f"  {i + 1}. {option}")
        choice = input("> ")
        try:
            index = int(choice) - 1
            return options[index]
        except (ValueError, IndexError):
            return options[0]

    async def multi_select(self, message: str, options: list[str]) -> list[str]:
        print(f"MULTI-SELECT: {message}")
        for i, option in enumerate(options):
            print(f"  [{i + 1}] {option}")
        print("Enter numbers separated by commas:")
        choice = input("> ")
        if not choice:
            return []
        indices = [int(x.strip()) - 1 for x in choice.split(',')]
        return [options[i] for i in indices if 0 <= i < len(options)]

# Use custom handler
client = OpenCodeAsyncClient(io_handler=MyIOHandler())
```

### Custom Progress Handler

Implement a custom progress handler for tracking operations:

```python
from dawn_kestrel.interfaces.io import ProgressHandler
from dawn_kestrel.sdk import OpenCodeAsyncClient

class MyProgressHandler(ProgressHandler):
    """Custom progress handler for your application."""

    def start(self, operation: str, total: int) -> None:
        print(f"Starting: {operation} (total: {total})")

    def update(self, current: int, message: str | None = None) -> None:
        msg = f"Progress: {current}"
        if message:
            msg += f" - {message}"
        print(msg)

    def complete(self, message: str | None = None) -> None:
        msg = "Complete!"
        if message:
            msg += f" - {message}"
        print(msg)

# Use custom handler
client = OpenCodeAsyncClient(progress_handler=MyProgressHandler())
```

### Custom Notification Handler

Implement a custom notification handler for user feedback:

```python
from dawn_kestrel.interfaces.io import Notification, NotificationType
from dawn_kestrel.sdk import OpenCodeAsyncClient

class MyNotificationHandler(NotificationHandler):
    """Custom notification handler for your application."""

    def show(self, notification: Notification) -> None:
        type_str = notification.notification_type.value
        print(f"[{type_str.upper()}] {notification.message}")
        if notification.details:
            for key, value in notification.details.items():
                print(f"  {key}: {value}")

# Use custom handler
client = OpenCodeAsyncClient(notification_handler=MyNotificationHandler())
```

## Error Handling

The SDK provides a structured exception hierarchy. All SDK exceptions extend from `OpenCodeError`.

### Exception Hierarchy

```python
from dawn_kestrel.core.exceptions import (
    OpenCodeError,      # Base exception for all SDK errors
    SessionError,       # Session-related errors
    MessageError,       # Message-related errors
    ToolExecutionError, # Tool execution errors
    IOHandlerError,     # I/O handler errors
)
```

### Error Handling Patterns

Catch specific exceptions for appropriate handling:

```python
import asyncio
from dawn_kestrel.sdk import OpenCodeAsyncClient
from dawn_kestrel.core.exceptions import (
    OpenCodeError,
    SessionError,
    MessageError,
)
```

### Error Recovery Strategies

Implement retry logic for transient errors:

```python
import asyncio
from dawn_kestrel.sdk import OpenCodeAsyncClient
from dawn_kestrel.core.exceptions import OpenCodeError
```

## Migration Guide

### From Legacy SessionManager

If you're migrating from legacy `SessionManager` API, here's how to update your code:

**Old (Legacy):**
```python
from dawn_kestrel.session.manager import SessionManager

manager = SessionManager()
session = manager.create_session(title="My Project")
message = manager.add_message(session.id, content="Hello")
```

**New (SDK):**
```python
from dawn_kestrel.sdk import OpenCodeAsyncClient

import asyncio

async def main() -> None:
    client = OpenCodeAsyncClient()
    session = await client.create_session(title="My Project")
    message = await client.add_message(session_id=session.id, content="Hello")

asyncio.run(main())
```

### Key Differences

1. **Async-first API:** The SDK is designed with async/await in mind
2. **Pluggable handlers:** Customize I/O, progress, and notifications
3. **Structured errors:** Use exception hierarchy for error handling
4. **Type hints:** Full type annotations for better IDE support

### Migration Checklist

- [ ] Update imports from `SessionManager` to `OpenCodeAsyncClient` or `OpenCodeClient`
- [ ] Add `async`/`await` if using async client
- [ ] Update error handling to use `OpenCodeError` hierarchy
- [ ] Consider implementing custom handlers if needed
- [ ] Run your tests to verify functionality

## Next Steps

- Explore [docs/examples/](docs/examples/) for more detailed examples
- Read [README.md](../README.md) for project information
- Check source code for detailed API documentation

## Support

For issues, questions, or contributions, please refer to project repository.
