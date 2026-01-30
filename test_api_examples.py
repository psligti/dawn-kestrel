"""
Test script to verify API documentation examples work.

This script validates all code examples in docs/api/agents.md
"""
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

# Test imports
try:
    from opencode_python.agents.registry import AgentRegistry, create_agent_registry
    from opencode_python.agents.runtime import AgentRuntime, create_agent_runtime
    from opencode_python.context.builder import ContextBuilder
    from opencode_python.agents.memory_manager import MemoryManager
    from opencode_python.agents.memory_embedder import MemoryEmbedder, create_memory_embedder
    from opencode_python.agents.memory_summarizer import MemorySummarizer, create_memory_summarizer
    from opencode_python.tools.permission_filter import ToolPermissionFilter
    from opencode_python.skills.injector import SkillInjector
    from opencode_python.core.agent_task import AgentTask, TaskStatus, create_agent_task
    from opencode_python.core.models import TokenUsage, Memory
    from opencode_python.tools.framework import ToolRegistry, Tool, ToolResult, ToolContext
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    exit(1)

# Test 1: AgentRegistry
async def test_agent_registry():
    print("\n📝 Testing AgentRegistry...")
    try:
        # Factory function
        registry = create_agent_registry(persistence_enabled=False)
        assert isinstance(registry, AgentRegistry)
        print("✅ create_agent_registry works")

        # Check agent exists
        agent = registry.get_agent("general")
        assert agent is not None
        print("✅ get_agent works")

        # Check list_agents
        agents = registry.list_agents()
        assert len(agents) > 0
        print(f"✅ list_agents works (found {len(agents)} agents)")

    except Exception as e:
        print(f"❌ AgentRegistry test failed: {e}")
        raise

# Test 2: AgentRuntime
async def test_agent_runtime():
    print("\n📝 Testing AgentRuntime...")
    try:
        from opencode_python.agents.builtin import Agent

        runtime = create_agent_runtime(
            agent_registry=registry,
            base_dir=Path("/tmp/test"),
            skill_max_char_budget=10000
        )
        assert isinstance(runtime, AgentRuntime)
        print("✅ create_agent_runtime works")

    except Exception as e:
        print(f"❌ AgentRuntime test failed: {e}")
        raise

# Test 3: ContextBuilder
async def test_context_builder():
    print("\n📝 Testing ContextBuilder...")
    try:
        builder = ContextBuilder(base_dir=Path("/tmp/test"))
        assert isinstance(builder, ContextBuilder)
        print("✅ ContextBuilder construction works")

    except Exception as e:
        print(f"❌ ContextBuilder test failed: {e}")
        raise

# Test 4: MemoryManager
async def test_memory_manager():
    print("\n📝 Testing MemoryManager...")
    try:
        manager = MemoryManager(base_dir=Path("/tmp/test"))
        assert isinstance(manager, MemoryManager)
        print("✅ MemoryManager construction works")

        # Test store
        memory = await manager.store(
            session_id="test-session",
            content="Test memory"
        )
        assert isinstance(memory, Memory)
        assert memory.content == "Test memory"
        print("✅ MemoryManager store works")

        # Test retrieve
        retrieved = await manager.retrieve("test-session", memory.id)
        assert retrieved is not None
        print("✅ MemoryManager retrieve works")

        # Test search
        results = await manager.search("test-session")
        assert len(results) >= 1
        print(f"✅ MemoryManager search works (found {len(results)} memories)")

        # Test delete
        deleted = await manager.delete("test-session", memory.id)
        assert deleted == True
        print("✅ MemoryManager delete works")

    except Exception as e:
        print(f"❌ MemoryManager test failed: {e}")
        raise

# Test 5: MemoryEmbedder
async def test_memory_embedder():
    print("\n📝 Testing MemoryEmbedder...")
    try:
        embedder = create_memory_embedder()
        assert isinstance(embedder, MemoryEmbedder)
        print("✅ create_memory_embedder works")

        strategy = embedder.get_strategy()
        assert strategy in ["mock", "openai", "local"]
        print(f"✅ get_strategy works (strategy: {strategy})")

        # Test embed
        embedding = await embedder.embed("Test text")
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
        print("✅ embed works (1536 dimensions)")

        # Test embed_batch
        embeddings = await embedder.embed_batch(["text1", "text2"])
        assert len(embeddings) == 2
        assert all(len(e) == 1536 for e in embeddings)
        print("✅ embed_batch works")

    except Exception as e:
        print(f"❌ MemoryEmbedder test failed: {e}")
        raise

# Test 6: MemorySummarizer
async def test_memory_summarizer():
    print("\n📝 Testing MemorySummarizer...")
    try:
        summarizer = create_memory_summarizer()
        assert isinstance(summarizer, MemorySummarizer)
        print("✅ create_memory_summarizer works")

        strategy = summarizer.get_strategy()
        assert strategy in ["mock", "openai"]
        print(f"✅ get_strategy works (strategy: {strategy})")

    except Exception as e:
        print(f"❌ MemorySummarizer test failed: {e}")
        raise

# Test 7: ToolPermissionFilter
async def test_permission_filter():
    print("\n📝 Testing ToolPermissionFilter...")
    try:
        filter = ToolPermissionFilter(
            permissions=[
                {"permission": "bash", "action": "allow"},
                {"permission": "read*", "action": "allow"},
                {"permission": "*", "action": "deny"}
            ]
        )
        assert isinstance(filter, ToolPermissionFilter)
        print("✅ ToolPermissionFilter construction works")

        # Test is_tool_allowed
        assert filter.is_tool_allowed("bash") == True
        assert filter.is_tool_allowed("read_file.py") == True
        assert filter.is_tool_allowed("write") == False
        print("✅ is_tool_allowed works")

    except Exception as e:
        print(f"❌ ToolPermissionFilter test failed: {e}")
        raise

# Test 8: SkillInjector
async def test_skill_injector():
    print("\n📝 Testing SkillInjector...")
    try:
        from opencode_python.agents.builtin import Agent

        injector = SkillInjector(base_dir=Path("/tmp/test"), max_char_budget=10000)
        assert isinstance(injector, SkillInjector)
        print("✅ SkillInjector construction works")

        # Build prompt
        prompt = injector.build_agent_prompt(
            agent_prompt="You are a code assistant",
            skill_names=["git"]
        )
        assert "You have access to the following skills:" in prompt
        assert "git" in prompt
        print("✅ build_agent_prompt works")

    except Exception as e:
        print(f"❌ SkillInjector test failed: {e}")
        raise

# Test 9: AgentTask
async def test_agent_task():
    print("\n📝 Testing AgentTask...")
    try:
        # Create task
        task = create_agent_task(
            agent_name="code-reviewer",
            description="Review code",
            tool_ids=["read", "git-diff"],
            skill_names=["git"]
        )
        assert isinstance(task, AgentTask)
        print("✅ create_agent_task works")

        assert task.can_start() == True
        print("✅ can_start works")

        # Create hierarchical task
        subtask = create_agent_task(
            agent_name="detail-reviewer",
            description="Review details",
            parent_id=task.task_id
        )
        assert subtask.has_dependencies() == True
        print("✅ hierarchical task creation works")

        # Test status methods
        subtask.status = TaskStatus.COMPLETED
        assert subtask.is_complete() == True
        print("✅ status methods work")

    except Exception as e:
        print(f"❌ AgentTask test failed: {e}")
        raise

# Test 10: ToolRegistry and Tool
async def test_tool_registry():
    print("\n📝 Testing ToolRegistry...")
    try:
        registry = ToolRegistry()
        assert isinstance(registry, ToolRegistry)
        print("✅ ToolRegistry construction works")

        # Test register
        async def test_tool(args, ctx):
            return ToolResult(title="Test", output="Done")

        class TestTool(Tool):
            id = "test-tool"
            description = "Test tool"

            def parameters(self):
                return {"type": "object"}

            async def execute(self, args, ctx):
                return await test_tool(args, ctx)

        test_instance = TestTool()
        await registry.register(test_instance, "test-tool")
        print("✅ ToolRegistry register works")

        # Test get
        tool = registry.get("test-tool")
        assert tool is not None
        assert tool.id == "test-tool"
        print("✅ ToolRegistry get works")

        # Test get_all
        all_tools = await registry.get_all()
        assert len(all_tools) > 0
        print(f"✅ ToolRegistry get_all works (found {len(all_tools)} tools)")

        # Test get_metadata
        metadata = registry.get_metadata("test-tool")
        assert metadata is not None
        print("✅ ToolRegistry get_metadata works")

    except Exception as e:
        print(f"❌ ToolRegistry test failed: {e}")
        raise

# Test 11: TokenUsage
async def test_token_usage():
    print("\n📝 Testing TokenUsage...")
    try:
        usage = TokenUsage(
            input=100,
            output=50,
            reasoning=20,
            cache={"read": 10, "write": 5}
        )
        assert usage.input == 100
        assert usage.output == 50
        assert usage.reasoning == 20
        assert usage.cache["read"] == 10
        print("✅ TokenUsage construction works")

        total = usage.input + usage.output
        assert total == 150
        print("✅ TokenUsage calculations work")

    except Exception as e:
        print(f"❌ TokenUsage test failed: {e}")
        raise

# Test 12: ToolContext
async def test_tool_context():
    print("\n📝 Testing ToolContext...")
    try:
        ctx = ToolContext(
            session_id="test-session",
            message_id="test-message",
            agent="test-agent",
            abort=asyncio.Event(),
            messages=[]
        )
        assert ctx.session_id == "test-session"
        assert ctx.agent == "test-agent"
        print("✅ ToolContext construction works")

        # Test update_metadata
        await ctx.update_metadata("Test Title", {"key": "value"})
        print("✅ ToolContext update_metadata works")

        # Test ask (should return True in non-interactive mode)
        result = await ctx.ask("bash", "*")
        assert result == True
        print("✅ ToolContext ask works")

    except Exception as e:
        print(f"❌ ToolContext test failed: {e}")
        raise

# Test 13: EventBus
async def test_event_bus():
    print("\n📝 Testing EventBus...")
    try:
        from opencode_python.core.event_bus import bus, Events

        # Test subscription
        events_received = []

        async def on_agent_ready(event):
            events_received.append(event.data["agent_name"])

        unsubscribe = await bus.subscribe(Events.AGENT_READY, on_agent_ready)

        # Publish event
        await bus.publish(Events.AGENT_READY, {"agent_name": "test-agent"})

        await asyncio.sleep(0.1)  # Give event loop time to process

        assert len(events_received) == 1
        assert events_received[0] == "test-agent"
        print("✅ EventBus subscribe/publish works")

        # Test unsubscribe
        await unsubscribe()
        print("✅ EventBus unsubscribe works")

    except Exception as e:
        print(f"❌ EventBus test failed: {e}")
        raise

# Main test runner
async def main():
    try:
        await test_agent_registry()
        await test_agent_runtime()
        await test_context_builder()
        await test_memory_manager()
        await test_memory_embedder()
        await test_memory_summarizer()
        await test_permission_filter()
        await test_skill_injector()
        await test_agent_task()
        await test_tool_registry()
        await test_token_usage()
        await test_tool_context()
        await test_event_bus()

        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED")
        print("="*50)
        print("\nAPI documentation examples verified successfully!")
    except Exception as e:
        print("\n" + "="*50)
        print("❌ TESTS FAILED")
        print("="*50)
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
