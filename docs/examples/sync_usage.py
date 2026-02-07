"""Sync usage example for OpenCode Python SDK.

This example demonstrates sync client usage.

Run this example:
    python docs/examples/sync_usage.py
"""
from dawn_kestrel.sdk import OpenCodeClient


def sync_usage() -> None:
    """Demonstrate SDK usage with sync client."""
    print("=" * 60)
    print("OpenCode Python SDK - Sync Client Example")
    print("=" * 60)
    print()

    client = OpenCodeClient()

    print("Creating session...")
    session = client.create_session(
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
        message = client.add_message(
            session_id=session.id,
            content=content
        )
        print(f"  Message {i}: {message.id} - {message.text[:50]}...")

    print()

    print("Listing all sessions...")
    sessions = client.list_sessions()
    print(f"  Total sessions: {len(sessions)}")
    for s in sessions:
        print(f"    - {s.id}: {s.title} ({len(s.messages)} messages)")

    print()
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


def cleanup_example() -> None:
    """Clean up sessions created during the example."""
    print()
    print("Cleaning up...")
    client = OpenCodeClient()

    sessions = client.list_sessions()
    for session in sessions:
        deleted = client.delete_session(session.id)
        if deleted:
            print(f"  Deleted session: {session.id}")

    print("  Cleanup complete!")


def main() -> None:
    """Run the example and clean up."""
    try:
        sync_usage()
    finally:
        cleanup_example()


if __name__ == "__main__":
    main()
