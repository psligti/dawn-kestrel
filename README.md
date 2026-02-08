# Dawn Kestrel

Dawn Kestrel SDK provides async/sync AI client with optional CLI and TUI interfaces.

## Features

- **Async & Sync Clients**: Choose async client for performance or sync client for simplicity
- **Pluggable Handlers**: Customize I/O, progress, and notifications for your needs
- **CLI & TUI Support**: Built-in Click-based CLI and Textual-based TUI
- **Type Hints**: Full type annotations for better IDE support
- **Bridge Pattern**: Clean separation between SDK and UI components

## Installation

```bash
pip install dawn-kestrel
```

For development with additional dependencies:

```bash
pip install dawn-kestrel[dev]
```

## CLI Commands

After installation, you can use the CLI with:

```bash
dawn-kestrel review --help      # Run multi-agent PR review
dawn-kestrel docs --help         # Generate documentation for review agents
```

For detailed usage and examples, see the getting started guide and documentation.

## Getting Started

For quick start guide and usage examples, see:

- **[Getting Started Guide](docs/getting-started.md)** - Installation, quick start, async/sync clients, handlers, error handling
- **[Examples](docs/examples/)** - Working code examples:
  - `basic_usage.py` - Async client usage with callbacks
  - `sync_usage.py` - Sync client for synchronous code
  - `cli_integration.py` - Integrating with CLI applications
  - `tui_integration.py` - Integrating with TUI applications

## Quick Example

```python
import asyncio
from dawn_kestrel.sdk import OpenCodeAsyncClient

async def main() -> None:
    client = OpenCodeAsyncClient()

    session = await client.create_session(title="My Project")
    message = await client.add_message(session.id, "Hello!")

    print(f"Created session: {session.id}")

asyncio.run(main())
```

See [Getting Started](docs/getting-started.md) for more details.

## Documentation

- **[Getting Started](docs/getting-started.md)** - Installation and usage guide
- **[Examples](docs/examples/)** - Code examples for common use cases
- **API Reference** - See docstrings in source code for detailed API documentation

## License

MIT License - see [LICENSE](LICENSE) file for details.
