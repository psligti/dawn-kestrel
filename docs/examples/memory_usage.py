"""Memory system usage example for OpenCode Python SDK.

This example demonstrates:
- Storing conversation memories with context and metadata
- Searching and retrieving memories using filters
- Memory summarization for long sessions
- Memory-based context injection for agent prompts
- Memory lifecycle management

Run this example:
    python docs/examples/memory_usage.py
"""
import asyncio
from typing import Any, Dict, List
from pathlib import Path

from dawn_kestrel.sdk import OpenCodeAsyncClient
from dawn_kestrel.interfaces.io import Notification
from dawn_kestrel.agents.memory_manager import MemoryManager
from dawn_kestrel.core.models import Session


async def setup_memory_system() -> tuple[Session, MemoryManager]:
    """Create session and initialize memory system."""
    client = OpenCodeAsyncClient()

    # Create a session for memory operations
    session = await client.create_session(
        title="Memory System Demo",
        version="1.0.0"
    )
    print(f"Created session: {session.id}")
    print()

    # Initialize memory manager
    # Use the session directory for memory storage
    storage_dir = Path(session.storage_path) if hasattr(session, 'storage_path') else Path.cwd()
    memory_manager = MemoryManager(storage_dir / "memory")

    return session, memory_manager


async def memory_storage_example(session: Session, memory_manager: MemoryManager) -> None:
    """Demonstrate storing memories with various content types."""
    print("=" * 60)
    print("Memory Storage Example")
    print("=" * 60)
    print()

    print("Storing different types of memories...")

    # Store user message
    user_memory = await memory_manager.store(
        session_id=session.id,
        content="I need to build a web application with authentication, database, and API endpoints.",
        metadata={
            "type": "user_message",
            "priority": "high",
            "user_role": "developer"
        }
    )
    print(f"  ✓ Stored user message: {user_memory.id}")

    # Store system analysis
    system_memory = await memory_manager.store(
        session_id=session.id,
        content="System analysis complete. Recommended tech stack: React for frontend, PostgreSQL for database, FastAPI for API.",
        metadata={
            "type": "system_analysis",
            "priority": "medium",
            "architecture_decision": "tech_stack"
        }
    )
    print(f"  ✓ Stored system analysis: {system_memory.id}")

    # Store action items
    action_memory = await memory_manager.store(
        session_id=session.id,
        content="Action items: 1. Set up React project, 2. Configure PostgreSQL, 3. Build FastAPI endpoints.",
        metadata={
            "type": "action_items",
            "priority": "high",
            "checked_off": False
        }
    )
    print(f"  ✓ Stored action items: {action_memory.id}")

    # Store preferences
    preference_memory = await memory_manager.store(
        session_id=session.id,
        content="User prefers TypeScript over JavaScript, and wants Docker for containerization.",
        metadata={
            "type": "preference",
            "priority": "low",
            "area": "development_preferences"
        }
    )
    print(f"  ✓ Stored preferences: {preference_memory.id}")

    print()
    print(f"Total memories stored: {len(await memory_manager.list_memories(session.id))}")
    print()


async def memory_search_example(session: Session, memory_manager: MemoryManager) -> None:
    """Demonstrate searching and filtering memories."""
    print("=" * 60)
    print("Memory Search Example")
    print("=" * 60)
    print()

    print("Searching memories with different filters...")

    # Search by content query
    print("\n1. Search by content keyword 'authentication':")
    results = await memory_manager.search(
        session_id=session.id,
        query="authentication",
        limit=5
    )
    print(f"   Found {len(results)} matching memories:")
    for memory in results:
        print(f"     - {memory.content[:80]}... (ID: {memory.id})")

    # Search without query (all memories)
    print("\n2. Search all memories:")
    all_memories = await memory_manager.search(session_id=session.id)
    print(f"   Total memories: {len(all_memories)}")

    # Search with limit
    print("\n3. Search with limit of 2:")
    limited_results = await memory_manager.search(
        session_id=session.id,
        limit=2
    )
    print(f"   Found {len(limited_results)} memories (limited)")

    # Search with offset
    print("\n4. Search with offset of 2:")
    offset_results = await memory_manager.search(
        session_id=session.id,
        offset=2
    )
    print(f"   Found {len(offset_results)} memories (offset=2)")

    print()


async def memory_retrieval_example(session: Session, memory_manager: MemoryManager) -> None:
    """Demonstrate retrieving specific memories by ID."""
    print("=" * 60)
    print("Memory Retrieval Example")
    print("=" * 60)
    print()

    # Get all memories to find IDs
    all_memories = await memory_manager.search(session_id=session.id)

    if all_memories:
        memory_id = all_memories[0].id
        print(f"Retrieving specific memory by ID: {memory_id}")

        retrieved = await memory_manager.retrieve(
            session_id=session.id,
            memory_id=memory_id
        )

        if retrieved:
            print(f"\n  Memory details:")
            print(f"    ID: {retrieved.id}")
            print(f"    Content: {retrieved.content}")
            print(f"    Session: {retrieved.session_id}")
            print(f"    Created: {retrieved.created}")
            print(f"    Metadata: {retrieved.metadata}")
        else:
            print(f"  Memory not found!")

    print()


async def memory_summarization_example(session: Session, memory_manager: MemoryManager) -> None:
    """Demonstrate summarizing long sessions of memories."""
    print("=" * 60)
    print("Memory Summarization Example")
    print("=" * 60)
    print()

    print("Generating session summary...")

    # Generate summary of all memories
    summary = await memory_manager.summarize(session_id=session.id)

    print(f"\nSession Summary:")
    print(f"  Total memories: {summary['count']}")
    print(f"  Total characters: {summary['total_characters']}")
    print(f"  Oldest timestamp: {summary['oldest_timestamp']}")
    print(f"  Newest timestamp: {summary['newest_timestamp']}")

    if summary['memories']:
        print(f"\n  Detailed memory list ({len(summary['memories'])} memories):")
        for i, memory in enumerate(summary['memories'][:5], 1):  # Show first 5
            print(f"\n    Memory {i}:")
            print(f"      ID: {memory['id']}")
            print(f"      Content: {memory['content'][:80]}...")
            print(f"      Created: {memory['created']}")

        if len(summary['memories']) > 5:
            print(f"\n    ... and {len(summary['memories']) - 5} more memories")

    # Generate summary filtered by time
    print("\n\nFiltered summary (last 3 days):")
    summary_3days = await memory_manager.summarize(
        session_id=session.id,
        since=3 * 24 * 60 * 60  # 3 days ago
    )

    print(f"  Total memories in last 3 days: {summary_3days['count']}")
    print(f"  Total characters: {summary_3days['total_characters']}")

    print()


async def memory_lifecycle_example(session: Session, memory_manager: MemoryManager) -> None:
    """Demonstrate memory deletion and lifecycle management."""
    print("=" * 60)
    print("Memory Lifecycle Example")
    print("=" * 60)
    print()

    # Delete a memory
    all_memories = await memory_manager.search(session_id=session.id)
    if all_memories:
        memory_to_delete = all_memories[0]
        print(f"Deleting memory: {memory_to_delete.id}")

        deleted = await memory_manager.delete(
            session_id=session.id,
            memory_id=memory_to_delete.id
        )

        if deleted:
            print(f"  ✓ Memory deleted successfully")
        else:
            print(f"  ✗ Deletion failed")

        # Verify deletion
        remaining = await memory_manager.search(session_id=session.id)
        print(f"  Remaining memories: {len(remaining)}")

    print()


async def memory_with_embedding_example(session: Session, memory_manager: MemoryManager) -> None:
    """Demonstrate storing memories with embeddings (future semantic search)."""
    print("=" * 60)
    print("Memory with Embedding Example")
    print("=" * 60)
    print()

    print("Storing memory with embeddings...")

    # Mock embedding (in real implementation, this would come from MemoryEmbedder)
    mock_embedding = [0.1, -0.2, 0.3, -0.4, 0.5]

    memory = await memory_manager.store(
        session_id=session.id,
        content="This is a semantic search demonstration memory with embedding vector.",
        embedding=mock_embedding,
        metadata={
            "type": "semantic_demo",
            "has_embedding": True
        }
    )

    print(f"  ✓ Stored memory with embedding: {memory.id}")
    print(f"    Embedding length: {len(memory.embedding) if memory.embedding else 0}")
    print(f"    Metadata: {memory.metadata}")

    print()
    print("Note: Future implementations will support semantic search using embeddings.")
    print("For now, search functionality uses content-based filtering.")
    print()


async def memory_usage_example() -> None:
    """Demonstrate complete memory system workflow."""
    print("=" * 60)
    print("OpenCode Python SDK - Memory System Example")
    print("=" * 60)
    print()

    # Create client and setup
    client = OpenCodeAsyncClient()

    def on_progress(current: int, message: str | None = None) -> None:
        print(f"  Progress: {current}", end="")
        if message:
            print(f" - {message}")
        else:
            print()

    client.on_progress(on_progress)

    def on_notification(notification) -> None:
        print(f"  Notification: [{notification.notification_type.value}] {notification.message}")

    client.on_notification(on_notification)

    # Setup memory system
    session, memory_manager = await setup_memory_system()

    try:
        # Execute all examples
        await memory_storage_example(session, memory_manager)
        await memory_search_example(session, memory_manager)
        await memory_retrieval_example(session, memory_manager)
        await memory_summarization_example(session, memory_manager)
        await memory_lifecycle_example(session, memory_manager)
        await memory_with_embedding_example(session, memory_manager)

        # Display final summary
        print("=" * 60)
        print("Memory System Summary")
        print("=" * 60)
        final_count = len(await memory_manager.list_memories(session.id))
        print(f"\nFinal memory count: {final_count}")
        print("\nWorkflow completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Example failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Cleanup
        print("\n" + "=" * 60)
        print("Cleaning up...")
        deleted = await client.delete_session(session.id)
        if deleted:
            print(f"  Deleted session: {session.id}")
        print("  Cleanup complete!")
        print("=" * 60)


async def main() -> None:
    """Run the memory usage example."""
    try:
        await memory_usage_example()
    except Exception as e:
        print(f"Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
