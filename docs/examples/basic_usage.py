"""Basic usage example for OpenCode Python SDK (async client).

This example demonstrates:
- Creating an async client
- Creating sessions
- Adding messages
- Listing sessions
- Using callbacks for progress and notifications

Run this example:
    python docs/examples/basic_usage.py
"""
import asyncio
from pathlib import Path

from dawn_kestrel.sdk import OpenCodeAsyncClient
from dawn_kestrel.interfaces.io import Notification


async def basic_usage() -> None:
    """Demonstrate basic SDK usage with async client."""
    print("=" * 60)
    print("OpenCode Python SDK - Basic Usage Example")
    print("=" * 60)
    print()

    client = OpenCodeAsyncClient()

    def on_progress(current: int, message: str | None = None) -> None:
        print(f"  Progress: {current}", end="")
        if message:
            print(f" - {message}")
        else:
            print()

    client.on_progress(on_progress)

    def on_notification(notification: Notification) -> None:
        print(f"  Notification: [{notification.notification_type.value}] {notification.message}")

    client.on_notification(on_notification)

    print("Creating session...")
    session = await client.create_session(
        title="My Project",
        version="1.0.0"
    )
    print(f"  Created session: {session.id}")
    print(f"  Title: {session.title}")
    print(f"  Version: {session.version}")
    print(f"  Created at: {session.time_created}")
    print()

    print("Adding messages...")
    messages = [
        "Hello, OpenCode!",
        "This is a test message.",
        "The SDK is working great!",
    ]

    for i, content in enumerate(messages, 1):
        message = await client.add_message(
            session_id=session.id,
            content=content
        )
        print(f"  Message {i}: {message.id} - {message.text[:50]}...")

    print()

    print("Retrieving session...")
    retrieved_session = await client.get_session(session.id)
    print(f"  Retrieved session: {retrieved_session.id}")
    print(f"  Total messages: {len(retrieved_session.messages)}")
    print()

    print("Listing all sessions...")
    sessions = await client.list_sessions()
    print(f"  Total sessions: {len(sessions)}")
    for s in sessions:
        print(f"    - {s.id}: {s.title} ({len(s.messages)} messages)")

    print()
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


async def cleanup_example() -> None:
    """Clean up sessions created during the example."""
    print()
    print("Cleaning up...")
    client = OpenCodeAsyncClient()

    sessions = await client.list_sessions()
    for session in sessions:
        deleted = await client.delete_session(session.id)
        if deleted:
            print(f"  Deleted session: {session.id}")

    print("  Cleanup complete!")


async def main() -> None:
    """Run the example and clean up."""
    try:
        await basic_usage()
    finally:
        await cleanup_example()


if __name__ == "__main__":
    asyncio.run(main())
