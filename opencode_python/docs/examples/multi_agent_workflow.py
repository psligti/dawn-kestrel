"""Multi-agent workflow example for OpenCode Python SDK.

This example demonstrates:
- Agent A delegates tasks to Agent B using the task tool
- Parallel execution of multiple agents via AgentOrchestrator
- Task status tracking and result aggregation
- Coordinated workflows with dependencies

Run this example:
    python docs/examples/multi_agent_workflow.py
"""
import asyncio
from typing import Any, Dict, List
from pathlib import Path

from opencode_python.sdk import OpenCodeAsyncClient
from opencode_python.interfaces.io import Notification
from opencode_python.agents.memory_manager import MemoryManager
from opencode_python.agents.orchestrator import AgentOrchestrator, create_agent_orchestrator
from opencode_python.agents.runtime import AgentRuntime
from opencode_python.agents.registry import create_agent_registry
from opencode_python.tools import create_builtin_registry
from opencode_python.storage.memory_storage import MemoryStorage
from opencode_python.core.models import Session


async def setup_session(client: OpenCodeAsyncClient) -> tuple[str, MemoryManager, AgentOrchestrator]:
    """Create session, memory manager, and orchestrator for workflow."""
    # Create session
    session = await client.create_session(
        title="Multi-Agent Workflow Demo",
        version="1.0.0"
    )
    print(f"Created session: {session.id}")

    # Initialize memory manager
    storage_dir = Path(session.storage_path) if hasattr(session, 'storage_path') else Path.cwd()
    memory_manager = MemoryManager(storage_dir / "memory")

    # Initialize orchestrator
    orchestrator = create_agent_orchestrator(client._runtime)

    return session.id, memory_manager, orchestrator


async def agent_a_task(session_id: str, memory_manager: MemoryManager) -> Dict[str, Any]:
    """Agent A: Analyzes code and identifies issues.

    This agent performs initial analysis and delegates specialized tasks.
    """
    print(f"\n[Agent A] Starting task analysis...")
    print(f"[Agent A] Session: {session_id}")

    # Store analysis context in memory
    analysis_memory = await memory_manager.store(
        session_id=session_id,
        content="Agent A: Initial code analysis completed. Identified need for specialized review.",
        metadata={"agent": "agent_a", "task": "initial_analysis"}
    )
    print(f"[Agent A] Analysis stored in memory: {analysis_memory.id}")

    # Perform analysis
    analysis = {
        "agent": "agent_a",
        "message": "Code analysis complete. I've identified several areas that need review:\n\n"
                  "1. Type hints missing for function parameters\n"
                  "2. Inconsistent error handling patterns\n"
                  "3. Potential performance optimization opportunities\n\n"
                  "Let me delegate specialized review tasks to focus on these areas."
    }

    return analysis


async def agent_b_task(session_id: str, memory_manager: MemoryManager) -> Dict[str, Any]:
    """Agent B: Performs code style review.

    A specialized agent that focuses on code style and consistency.
    """
    print(f"\n[Agent B] Starting style review...")
    print(f"[Agent B] Session: {session_id}")

    # Store style review in memory
    style_memory = await memory_manager.store(
        session_id=session_id,
        content="Agent B: Style review completed. Found issues with formatting and naming conventions.",
        metadata={"agent": "agent_b", "task": "style_review"}
    )
    print(f"[Agent B] Style review stored in memory: {style_memory.id}")

    review = {
        "agent": "agent_b",
        "message": "Style review complete. Found:\n\n"
                  "- Inconsistent indentation in several functions\n"
                  "- Mixed use of snake_case and CamelCase for variables\n"
                  "- Missing docstrings for complex functions\n\n"
                  "Recommend: Standardize on PEP 8 conventions."
    }

    return review


async def agent_c_task(session_id: str, memory_manager: MemoryManager) -> Dict[str, Any]:
    """Agent C: Performs performance review.

    A specialized agent that focuses on performance optimization.
    """
    print(f"\n[Agent C] Starting performance review...")
    print(f"[Agent C] Session: {session_id}")

    # Store performance review in memory
    performance_memory = await memory_manager.store(
        session_id=session_id,
        content="Agent C: Performance review completed. Identified optimization opportunities.",
        metadata={"agent": "agent_c", "task": "performance_review"}
    )
    print(f"[Agent C] Performance review stored in memory: {performance_memory.id}")

    review = {
        "agent": "agent_c",
        "message": "Performance review complete. Found:\n\n"
                  "- Potential for using list comprehensions\n"
                  "- Database query could be optimized with indexing\n"
                  "- Consider caching frequently accessed data\n\n"
                  "Recommend: Profile before optimizing, focus on hot paths."
    }

    return review


async def multi_agent_workflow_example() -> None:
    """Demonstrate multi-agent workflow with delegation and parallel execution."""
    print("=" * 60)
    print("OpenCode Python SDK - Multi-Agent Workflow Example")
    print("=" * 60)
    print()

    # Create client
    client = OpenCodeAsyncClient()

    # Setup callbacks
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

    # Setup session, memory, and orchestrator
    session_id, memory_manager, orchestrator = await setup_session(client)

    try:
        print()
        print("Step 1: Agent A performs initial analysis and delegates tasks")
        print("-" * 60)

        # Agent A performs analysis and stores result in memory
        agent_a_result = await agent_a_task(session_id, memory_manager)
        print()
        print("[Agent A] Response:")
        print(agent_a_result["message"])

        # Agent A delegates to specialized agents
        print()
        print("[Agent A] Delegating specialized tasks to agents B and C...")
        print()

        # Define tasks for delegation
        agent_b_task = {
            "task_id": "task_style_review",
            "agent_name": "build",  # Using built-in 'build' agent for demonstration
            "description": "Perform code style review",
            "skill_names": ["python-programmer"],
            "options": {}
        }

        agent_c_task = {
            "task_id": "task_performance_review",
            "agent_name": "build",  # Using built-in 'build' agent for demonstration
            "description": "Perform performance review",
            "skill_names": ["python-programmer"],
            "options": {}
        }

        # Execute delegated tasks (could be parallel in real implementation)
        print("[Agent A] Executing Agent B (style review)...")
        agent_b_result = await orchestrator.delegate_task(
            task=agent_b_task,
            session_id=session_id,
            user_message="Review the code for style and consistency issues",
            session_manager=client._service,
            tools=create_builtin_registry(),
            session=None
        )
        print(f"[Agent B] Delegation complete: {agent_b_result}")

        print("[Agent A] Executing Agent C (performance review)...")
        agent_c_result = await orchestrator.delegate_task(
            task=agent_c_task,
            session_id=session_id,
            user_message="Review the code for performance optimization opportunities",
            session_manager=client._service,
            tools=create_builtin_registry(),
            session=None
        )
        print(f"[Agent C] Delegation complete: {agent_c_result}")

        print()
        print("-" * 60)

        # Retrieve and display memories
        print()
        print("Step 2: Retrieving memories from all agents")
        print("-" * 60)

        memories = await memory_manager.search(session_id)
        print(f"Found {len(memories)} memories in session {session_id}:")

        for i, memory in enumerate(memories, 1):
            print(f"\n  Memory {i}:")
            print(f"    ID: {memory.id}")
            print(f"    Agent: {memory.metadata.get('agent', 'unknown')}")
            print(f"    Content: {memory.content[:100]}...")

        # Generate session summary
        print()
        print("-" * 60)
        print("Step 3: Generating session summary")
        print("-" * 60)

        summary = await memory_manager.summarize(session_id)
        print(f"\nSession Summary:")
        print(f"  Total memories: {summary['count']}")
        print(f"  Total characters: {summary['total_characters']}")
        print(f"  Oldest memory: {summary['oldest_timestamp']}")
        print(f"  Newest memory: {summary['newest_timestamp']}")

        # Display complete workflow summary
        print()
        print("=" * 60)
        print("Multi-Agent Workflow Summary")
        print("=" * 60)
        print()
        print("Agent A (Coordinator):")
        print("  - Performed initial analysis")
        print("  - Identified need for specialized review")
        print("  - Delegated tasks to Agent B and C")
        print()
        print("Agent B (Style Review):")
        print("  - Analyzed code style")
        print("  - Found formatting and naming issues")
        print("  - Recommended PEP 8 conventions")
        print()
        print("Agent C (Performance Review):")
        print("  - Analyzed performance")
        print("  - Found optimization opportunities")
        print("  - Recommended profiling and caching")
        print()
        print("Workflow completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Cleanup
        print()
        print("Cleaning up...")
        deleted = await client.delete_session(session_id)
        if deleted:
            print(f"  Deleted session: {session_id}")
        print("  Cleanup complete!")


async def main() -> None:
    """Run the multi-agent workflow example."""
    try:
        await multi_agent_workflow_example()
    except Exception as e:
        print(f"Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
