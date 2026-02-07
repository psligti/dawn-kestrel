"""CLI integration example for OpenCode Python SDK.

Uses QuietIOHandler for headless mode. For interactive CLI integration,
use CLIIOHandler with Click prompts.

Run this example:
    python docs/examples/cli_integration.py
"""
import asyncio
from dawn_kestrel.sdk import OpenCodeAsyncClient
from dawn_kestrel.interfaces.io import QuietIOHandler


async def cli_integration() -> None:
    """Demonstrate SDK usage with CLI integration."""
    print("=" * 60)
    print("OpenCode Python SDK - CLI Integration Example")
    print("=" * 60)
    print()

    io_handler = QuietIOHandler()
    client = OpenCodeAsyncClient(io_handler=io_handler)

    session = await client.create_session(
        title="My Project",
        version="1.0.0"
    )
    print(f"Created session: {session.id}")
    print(f"  Title: {session.title}")
    print(f"  Version: {session.version}")
    print()

    message = await client.add_message(
        session_id=session.id,
        content="Hello from CLI!"
    )
    print(f"Added message: {message.id}")
    print(f"  Content: {message.text}")
    print()

    sessions = await client.list_sessions()
    print(f"Total sessions: {len(sessions)}")
    for s in sessions:
        print(f"  - {s.id}: {s.title} ({len(s.messages)} messages)")

    print()
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


async def cleanup_example() -> None:
    """Clean up sessions created during the example."""
    print()
    print("Cleaning up...")

    io_handler = QuietIOHandler()
    client = OpenCodeAsyncClient(io_handler=io_handler)

    sessions = await client.list_sessions()
    for session in sessions:
        deleted = await client.delete_session(session.id)
        if deleted:
            print(f"Deleted session: {session.id}")

    print("Cleanup complete!")


async def main() -> None:
    """Run the example and clean up."""
    try:
        await cli_integration()
    finally:
        await cleanup_example()


if __name__ == "__main__":
    asyncio.run(main())
