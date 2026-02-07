# OpenCode Python

OpenCode Python SDK provides Python bindings for OpenCode with both async and sync clients, CLI, and TUI interfaces.

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

## Standalone Review Tool

The multi-agent PR review agent can be installed as a standalone `uv tool` for running reviews in any repository.

```bash
uv tool install dawn-kestrel
```

This provides two commands:
- `opencode-review` - Run multi-agent PR review
- `opencode-review-generate-docs` - Generate documentation for review agents

See [REVIEW_TOOL.md](REVIEW_TOOL.md) for detailed usage and examples.

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
