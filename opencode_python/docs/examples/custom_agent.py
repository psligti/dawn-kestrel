"""Custom agent registration and usage example for OpenCode Python SDK.

This example demonstrates:
- Creating a custom agent with specific permissions
- Registering the custom agent with the SDK client
- Executing the agent with custom tools and skills
- Error handling and monitoring during agent execution

Run this example:
    python docs/examples/custom_agent.py
"""
import asyncio
from typing import Any, Dict, List
from pathlib import Path

from opencode_python.sdk import OpenCodeAsyncClient
from opencode_python.interfaces.io import Notification
from opencode_python.core.exceptions import OpenCodeError


async def create_custom_agent() -> dict:
    """Create a custom code review agent.

    Returns:
        Agent configuration dictionary
    """
    agent = {
        "name": "code_reviewer",
        "description": "Specialized agent for code review and quality analysis",
        "mode": "subagent",
        "permission": [
            {
                "permission": "read",
                "pattern": "**/*.py",
                "action": "allow"
            },
            {
                "permission": "write",
                "pattern": "**/*.py",
                "action": "allow"
            },
            {
                "permission": "tool",
                "pattern": "build, test, lint",
                "action": "allow"
            }
        ],
        "skills": ["git-master", "python-programmer"],
        "options": {
            "model": "claude-3-5-sonnet-20241022",
            "temperature": 0.3
        }
    }
    return agent


async def custom_agent_example() -> None:
    """Demonstrate custom agent registration and execution."""
    print("=" * 60)
    print("OpenCode Python SDK - Custom Agent Example")
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

    print("Step 1: Creating custom agent...")
    agent_config = await create_custom_agent()
    print(f"  Agent name: {agent_config['name']}")
    print(f"  Agent description: {agent_config['description']}")
    print(f"  Agent skills: {', '.join(agent_config['skills'])}")
    print()

    print("Step 2: Registering custom agent...")
    try:
        registered_agent = await client.register_agent(agent_config)
        print(f"  ✓ Agent registered successfully!")
        print(f"  Registered agent: {registered_agent.name}")
    except ValueError as e:
        print(f"  ⚠ Agent already registered or registration failed: {e}")
        # Try to get existing agent instead
        registered_agent = await client.get_agent("code_reviewer")
        print(f"  ✓ Using existing registered agent: {registered_agent.name}")
    print()

    print("Step 3: Executing custom agent...")
    try:
        # Create a session for the agent execution
        session = await client.create_session(
            title="Code Review Session",
            version="1.0.0"
        )
        print(f"  Created session: {session.id}")

        # Execute the custom agent with a code review task
        result = await client.execute_agent(
            agent_name="code_reviewer",
            session_id=session.id,
            user_message="Review the following code snippet and identify potential improvements:\n\n"
                       "def calculate_discount(price, rate):\n"
                       "    if price < 0 or rate < 0 or rate > 1:\n"
                       "        return 0\n"
                       "    return price * (1 - rate)\n\n"
                       "Consider edge cases, performance, and Python best practices.",
            options={
                "skills": ["git-master"],  # Add git-master skill for better code review
                "provider": "anthropic",
            }
        )

        print(f"  ✓ Agent execution completed!")
        print(f"  Response preview: {result.response[:200]}...")
        print(f"  Tools used: {', '.join(result.tools_used) if result.tools_used else 'None'}")
        print(f"  Duration: {result.duration:.2f} seconds")

        # Display full response
        print()
        print("=" * 60)
        print("Agent Response:")
        print("=" * 60)
        print(result.response)
        print("=" * 60)

    except OpenCodeError as e:
        print(f"  ✗ Agent execution failed: {e}")
        if e.original_exception:
            print(f"    Caused by: {e.original_exception}")
        raise
    finally:
        # Cleanup: delete the session
        print()
        print("Cleaning up...")
        deleted = await client.delete_session(session.id)
        if deleted:
            print(f"  Deleted session: {session.id}")
        print("  Cleanup complete!")

    print()
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


async def error_handling_example() -> None:
    """Demonstrate error handling when registering invalid agents."""
    print()
    print("=" * 60)
    print("Error Handling Example")
    print("=" * 60)
    print()

    client = OpenCodeAsyncClient()

    print("Attempting to register invalid agent...")
    invalid_agent = {
        "name": "reviewer",  # Missing required fields
        "description": "Code review agent",
    }

    try:
        await client.register_agent(invalid_agent)
    except ValueError as e:
        print(f"  Expected error caught: {e}")
    except Exception as e:
        print(f"  Unexpected error: {e}")

    print()
    print("Attempting to execute non-existent agent...")
    try:
        result = await client.execute_agent(
            agent_name="nonexistent_agent",
            session_id="test_session",
            user_message="Hello"
        )
    except ValueError as e:
        print(f"  Expected error caught: {e}")
    except Exception as e:
        print(f"  Unexpected error: {e}")

    print()
    print("Error handling example completed!")


async def main() -> None:
    """Run the custom agent example and error handling demo."""
    try:
        await custom_agent_example()
    except Exception as e:
        print(f"Example failed: {e}")
        import traceback
        traceback.print_exc()

    # Run error handling example
    try:
        await error_handling_example()
    except Exception as e:
        print(f"Error handling demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
