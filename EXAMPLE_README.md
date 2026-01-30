# Custom Agent Application Example

This directory contains an example demonstrating how to build a custom agent application using the OpenCode Python SDK.

## Files

- `custom_agent_app_example.py` - Complete working example
- `SDK_GAPS_AND_NEXT_STEPS.md` - Detailed analysis of missing features

## Running the Example

**Note**: This example demonstrates the desired API and patterns. Some features documented in the gaps analysis are not yet implemented.

```bash
# Ensure you're in the python-sdk worktree directory
cd /Users/parkersligting/develop/pt/agentic_coding/.worktrees/python-sdk

# Run the example
python custom_agent_app_example.py
```

## What the Example Demonstrates

### 1. Custom Tool Registration
Shows how to define and register custom tools:

```python
class CustomCalculatorTool(Tool):
    id = "calculator"
    description = "Perform mathematical calculations"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        # Tool implementation
        ...

    def parameters(self) -> Dict[str, Any]:
        # JSON schema for LLM function calling
        ...
```

### 2. Custom Agent Definitions
Shows how to define agents with specific permissions:

```python
DATA_ANALYST_AGENT = Agent(
    name="data_analyst",
    description="Specializes in data analysis",
    mode="subagent",
    permission=[
        {"permission": "calculator", "pattern": "*", "action": "allow"},
        {"permission": "bash", "pattern": "*", "action": "deny"},
    ]
)
```

### 3. SDK Configuration
Shows how to configure the SDK for your application:

```python
config = SDKConfig(
    storage_path=Path.home() / ".local" / "share" / "my-app" / "sessions",
    project_dir=Path.cwd(),
    auto_confirm=False,
    enable_progress=True,
    enable_notifications=True,
)

client = OpenCodeAsyncClient(config=config)
```

### 4. Memory Management (Planned)
Demonstrates the planned memory API (not yet implemented):

```python
await memory_manager.save_conversation_state(
    session_id=session.id,
    state_key="initial_context",
    state_data={"user_preferences": {"units": "metric"}}
)

state = await memory_manager.retrieve_conversation_state(
    session_id=session.id,
    state_key="initial_context"
)
```

### 5. Skill Loading
Shows how to load application-specific skills from `.opencode/skill/` or `.claude/skills/`:

```python
skills = await load_app_skills(Path.cwd())
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                         │
├─────────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐│
│  │ Custom Tools  │  │Custom Agents │  │   Skills  ││
│  └──────────────┘  └──────────────┘  └────────────┘│
│         │                 │                 │            │
│         └─────────────────┴─────────────────┘            │
│                           │                               │
│                           ▼                               │
│                  ┌───────────────────┐                      │
│                  │ OpenCode SDK     │                      │
│                  │  - AgentRuntime  │ ← NOT YET IMPLEMENTED │
│                  │  - MemoryManager│ ← NOT YET IMPLEMENTED │
│                  │  - ContextBuilder│ ← NOT YET IMPLEMENTED │
│                  │  - AISession    │ ← EXISTS ✓          │
│                  │  - ToolRegistry │ ← EXISTS ✓          │
│                  └───────────────────┘                      │
│                           │                               │
│                           ▼                               │
│                  ┌───────────────────┐                      │
│                  │ SessionStorage   │ ← EXISTS ✓          │
│                  └───────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## Key Takeaways

### What Works Today

1. **Tool Framework** - Define custom tools with execute() and parameters()
2. **Tool Registry** - Register and retrieve tools
3. **Agent Definitions** - Define agents with permissions
4. **SDK Configuration** - Customize storage, project dir, behavior
5. **Skill Loading** - Discover skills from markdown files
6. **AI Session** - Full streaming AI with tool execution
7. **Tool Execution** - Execute tools with permission checking
8. **Event Bus** - Subscribe to agent/tool/session events

### What's Missing (See SDK_GAPS_AND_NEXT_STEPS.md)

1. **Memory System** - No semantic search, embeddings, or retrieval
2. **Agent Runtime** - Can't execute custom agents (integration bugs)
3. **Custom Agent Registration** - No API to register custom agents
4. **Skill Injection** - Skills loaded but not injected into prompts
5. **Context Builder** - No public API for building agent context
6. **Multi-Agent Orchestration** - Can't delegate between agents

## Next Steps

1. Read `SDK_GAPS_AND_NEXT_STEPS.md` for detailed gap analysis
2. Review the implementation plan (5 phases)
3. Decide which features to prioritize for your use case
4. Consider contributing to the SDK if you implement missing features

## Contributing

The OpenCode Python SDK is open source. Contributions welcome!

- Bug reports: Check `Existing Bugs Found` section in `SDK_GAPS_AND_NEXT_STEPS.md`
- Feature requests: See `Missing Features` sections
- Pull requests: Test thoroughly with existing test suite
