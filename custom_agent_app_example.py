"""
Example: Custom Agent Application

This example demonstrates how to build a small Python application that
brings in its own agents, tools, configs, memory, and skills using the
OpenCode Python SDK.

The application showcases:
1. Custom agent definitions with specific permissions
2. Custom tool registration
3. SDK configuration
4. Memory management through session storage
5. Skill loading and integration
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from opencode_python.sdk import OpenCodeAsyncClient, SDKConfig
from opencode_python.agents import Agent
from opencode_python.tools.framework import Tool, ToolRegistry, ToolContext, ToolResult
from opencode_python.storage.store import SessionStorage
from opencode_python.skills.loader import SkillLoader
from opencode_python.core.models import Session, Message


# ============================================================================
# 1. Custom Tool Definition
# ============================================================================

class CustomCalculatorTool(Tool):
    """A custom tool that performs calculations"""

    id = "calculator"
    description = "Perform mathematical calculations (add, subtract, multiply, divide)"

    async def execute(
        self,
        args: Dict[str, Any],
        ctx: ToolContext,
    ) -> ToolResult:
        """Execute calculator tool"""
        operation = args.get("operation", "")
        a = args.get("a", 0)
        b = args.get("b", 0)

        try:
            if operation == "add":
                result = a + b
                output = f"{a} + {b} = {result}"
            elif operation == "subtract":
                result = a - b
                output = f"{a} - {b} = {result}"
            elif operation == "multiply":
                result = a * b
                output = f"{a} * {b} = {result}"
            elif operation == "divide":
                if b == 0:
                    output = "Error: Division by zero"
                else:
                    result = a / b
                    output = f"{a} / {b} = {result}"
            else:
                output = f"Unknown operation: {operation}"

            return ToolResult(
                title=f"Calculator: {operation}",
                output=output,
                metadata={"operation": operation, "a": a, "b": b}
            )
        except Exception as e:
            return ToolResult(
                title=f"Calculator: {operation}",
                output=f"Error: {str(e)}",
                metadata={"error": str(e)}
            )

    def parameters(self) -> Dict[str, Any]:
        """Return JSON schema for tool parameters"""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The operation to perform"
                },
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["operation", "a", "b"]
        }


class CustomWeatherTool(Tool):
    """A mock weather tool for demonstration"""

    id = "weather"
    description = "Get weather information for a location (mock)"

    async def execute(
        self,
        args: Dict[str, Any],
        ctx: ToolContext,
    ) -> ToolResult:
        """Execute weather tool"""
        location = args.get("location", "unknown")

        # Mock weather data
        weather_data = {
            "San Francisco": {"temp": 65, "condition": "Foggy"},
            "New York": {"temp": 45, "condition": "Rainy"},
            "Denver": {"temp": 30, "condition": "Snowy"},
        }

        result = weather_data.get(location, {"temp": 72, "condition": "Sunny"})

        output = (
            f"Weather in {location}:\n"
            f"  Temperature: {result['temp']}°F\n"
            f"  Condition: {result['condition']}"
        )

        return ToolResult(
            title=f"Weather for {location}",
            output=output,
            metadata={"location": location, **result}
        )

    def parameters(self) -> Dict[str, Any]:
        """Return JSON schema for tool parameters"""
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or location"
                }
            },
            "required": ["location"]
        }


# ============================================================================
# 2. Custom Agent Definitions
# ============================================================================

# Create custom agents with specific permissions
DATA_ANALYST_AGENT = Agent(
    name="data_analyst",
    description="Specializes in data analysis and calculations",
    mode="subagent",
    permission=[
        {"permission": "calculator", "pattern": "*", "action": "allow"},
        {"permission": "read", "pattern": "*.csv", "action": "allow"},
        {"permission": "read", "pattern": "*.json", "action": "allow"},
        {"permission": "bash", "pattern": "*", "action": "deny"},  # No bash access
    ],
    temperature=0.3,  # More deterministic
)

WEATHER_BOT_AGENT = Agent(
    name="weather_bot",
    description="Provides weather information",
    mode="subagent",
    permission=[
        {"permission": "weather", "pattern": "*", "action": "allow"},
        {"permission": "websearch", "pattern": "*", "action": "deny"},  # No web search
    ],
    temperature=0.7,  # More conversational
)

CUSTOM_SUPERVISOR_AGENT = Agent(
    name="supervisor",
    description="Coordinates between specialist agents",
    mode="primary",
    permission=[
        {"permission": "*", "pattern": "*", "action": "allow"},  # Full access
        {"permission": "task", "pattern": "*", "action": "allow"},  # Can delegate
    ],
    temperature=0.5,
)


# ============================================================================
# 3. SDK Configuration
# ============================================================================

def create_app_config() -> SDKConfig:
    """Create application-specific SDK configuration"""
    return SDKConfig(
        storage_path=Path.home() / ".local" / "share" / "my-app" / "sessions",
        project_dir=Path.cwd(),
        auto_confirm=False,  # Require user confirmation
        enable_progress=True,
        enable_notifications=True,
    )


# ============================================================================
# 4. Memory Management
# ============================================================================

class AppMemoryManager:
    """Manages application memory using session storage"""

    def __init__(self, storage: SessionStorage):
        self.storage = storage

    async def save_conversation_state(
        self,
        session_id: str,
        state_key: str,
        state_data: Dict[str, Any]
    ) -> None:
        """Save conversation state to memory

        NOTE: This is a simplified example. Real implementation would need:
        - Dedicated memory storage layer
        - Vector embeddings for semantic search
        - Memory summarization and compression
        - Retrieval mechanisms (semantic, keyword, temporal)
        - Memory access permissions per agent
        """
        # For now, we'd store this in a custom storage structure
        # This is a placeholder for the required implementation
        print(f"  [Memory] Saving state '{state_key}' for session {session_id}")
        # Implementation needed: storage.write(["memory", session_id, state_key], state_data)

    async def retrieve_conversation_state(
        self,
        session_id: str,
        state_key: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve conversation state from memory

        NOTE: This is a placeholder. Real implementation needs:
        - Semantic search across memories
        - Relevance scoring
        - Temporal filtering
        """
        print(f"  [Memory] Retrieving state '{state_key}' for session {session_id}")
        # Implementation needed: return await storage.read(["memory", session_id, state_key])
        return None


# ============================================================================
# 5. Skill Loading
# ============================================================================

async def load_app_skills(base_dir: Path) -> List[str]:
    """Load application-specific skills

    Skills should be in .opencode/skill/ or .claude/skills/ directories.

    NOTE: This is a simplified example. Real implementation would need:
    - Skill validation and versioning
    - Skill dependency management
    - Hot-reloading of skills
    - Skill permission mapping
    """
    skill_loader = SkillLoader(base_dir)

    skills = skill_loader.discover_skills()
    skill_names = [skill.name for skill in skills]

    print(f"  [Skills] Loaded {len(skill_names)} skills:")
    for name in skill_names:
        print(f"    - {name}")

    return skill_names


# ============================================================================
# 6. Main Application
# ============================================================================

async def main():
    """Run the custom agent application"""
    print("=" * 80)
    print("Custom Agent Application Example")
    print("=" * 80)
    print()

    # 1. Create SDK client with custom config
    print("1. Initializing SDK with custom configuration...")
    config = create_app_config()
    client = OpenCodeAsyncClient(config=config)

    # Register progress and notification callbacks
    def on_progress(current: int, message: str | None = None) -> None:
        print(f"  [Progress] {current}", end="")
        if message:
            print(f" - {message}")
        else:
            print()

    def on_notification(notification) -> None:
        print(f"  [Notification] {notification.message}")

    client.on_progress(on_progress)
    client.on_notification(on_notification)
    print(f"  Config: {config.as_dict()}")
    print()

    # 2. Create tool registry with custom tools
    print("2. Registering custom tools...")
    tool_registry = ToolRegistry()

    custom_tools = [
        (CustomCalculatorTool(), "calculator"),
        (CustomWeatherTool(), "weather"),
    ]

    for tool, tool_id in custom_tools:
        await tool_registry.register(tool, tool_id)
        print(f"  Registered tool: {tool_id}")
    print()

    # 3. Load custom skills
    print("3. Loading application skills...")
    skills = await load_app_skills(Path.cwd())
    print(f"  Skills available: {skills}")
    print()

    # 4. Define custom agents
    print("4. Defining custom agents...")
    custom_agents = [
        DATA_ANALYST_AGENT,
        WEATHER_BOT_AGENT,
        CUSTOM_SUPERVISOR_AGENT,
    ]
    for agent in custom_agents:
        print(f"  Agent: {agent.name}")
        print(f"    Description: {agent.description}")
        print(f"    Mode: {agent.mode}")
        print(f"    Permissions: {len(agent.permission)} rules")
    print()

    # 5. Initialize memory manager
    print("5. Initializing memory manager...")
    storage_base_dir = config.storage_path or Path.home() / ".local" / "share" / "opencode-python"
    storage = SessionStorage(base_dir=storage_base_dir)
    memory_manager = AppMemoryManager(storage)
    print("  Memory manager ready")
    print()

    # 6. Create a session
    print("6. Creating session...")
    session = await client.create_session(
        title="Custom Agent Demo",
        version="1.0.0"
    )
    print(f"  Session ID: {session.id}")
    print(f"  Title: {session.title}")
    print()

    # 7. Save conversation state to memory
    print("7. Saving conversation state to memory...")
    await memory_manager.save_conversation_state(
        session_id=session.id,
        state_key="initial_context",
        state_data={
            "user_preferences": {"units": "metric"},
            "app_version": "1.0.0",
            "custom_agents": [a.name for a in custom_agents]
        }
    )
    print()

    # 8. Add messages to the session
    print("8. Adding messages...")
    messages = [
        ("user", "I need to calculate 15 * 23"),
        ("assistant", "Let me use the calculator tool for that."),
    ]

    for role, content in messages:
        message_id = await client.add_message(
            session_id=session.id,
            role=role,
            content=content
        )
        print(f"  [{role.upper()}] {content[:50]}...")
    print()

    # 9. Show custom tool execution example
    print("9. Custom tool execution example...")
    calculator = CustomCalculatorTool()

    # Create a mock tool context
    class MockToolContext:
        def __init__(self, session_id: str, message_id: str):
            self.session_id = session_id
            self.message_id = message_id
            self.agent = "data_analyst"
            self.abort = asyncio.Event()

    mock_ctx = MockToolContext(session.id, "msg_001")

    result = await calculator.execute(
        args={"operation": "multiply", "a": 15, "b": 23},
        ctx=mock_ctx
    )
    print(f"  Tool: {result.title}")
    print(f"  Output: {result.output}")
    print()

    # 10. Retrieve memory
    print("10. Retrieving conversation state from memory...")
    state = await memory_manager.retrieve_conversation_state(
        session_id=session.id,
        state_key="initial_context"
    )
    if state:
        print(f"  Retrieved state: {state}")
    else:
        print("  No state found (expected - placeholder implementation)")
    print()

    # 11. Summary
    print("=" * 80)
    print("Summary: Custom Agent Application")
    print("=" * 80)
    print(f"  Session: {session.id}")
    print(f"  Custom Tools: {len(custom_tools)}")
    print(f"  Custom Agents: {len(custom_agents)}")
    print(f"  Skills Loaded: {len(skills)}")
    print(f"  Memory Manager: Active")
    print()
    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
