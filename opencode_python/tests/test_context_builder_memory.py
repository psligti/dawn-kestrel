"""Tests for ContextBuilder memory integration"""
from __future__ import annotations

from unittest.mock import Mock, AsyncMock
import pytest
from pathlib import Path

from opencode_python.context.builder import ContextBuilder
from opencode_python.core.models import Session
from opencode_python.tools.framework import ToolRegistry
from opencode_python.core.agent_types import AgentContext


@pytest.fixture
def context_builder():
    """Create context builder for testing"""
    return ContextBuilder(base_dir=Path("/tmp"))


@pytest.fixture
def sample_session():
    """Create sample session for testing"""
    return Session(
        id="test-session-123",
        slug="test-session",
        project_id="test-project",
        directory="/tmp/test",
        title="Test Session",
        version="1.0.0",
    )


@pytest.fixture
def sample_agent():
    """Create sample agent configuration"""
    return {
        "name": "build",
        "description": "Default agent",
        "mode": "primary",
        "permission": [
            {"permission": "*", "pattern": "*", "action": "allow"},
        ],
        "prompt": "You are a helpful assistant.",
    }


@pytest.fixture
def sample_tools():
    """Create sample tool registry"""
    return ToolRegistry()


@pytest.fixture
def sample_memories():
    """Create sample memories for testing"""
    return [
        {
            "id": "mem-1",
            "session_id": "test-session-123",
            "content": "User prefers Python over JavaScript for backend development",
            "created": 1234567890.0,
            "metadata": {"type": "preference"},
        },
        {
            "id": "mem-2",
            "session_id": "test-session-123",
            "content": "Project uses PostgreSQL as the primary database",
            "created": 1234567891.0,
            "metadata": {"type": "fact"},
        },
        {
            "id": "mem-3",
            "session_id": "test-session-123",
            "content": "Last meeting discussed migration to async/await patterns",
            "created": 1234567892.0,
            "metadata": {"type": "context"},
        },
    ]


# ===== Memory Formatting Tests =====

def test_format_memories_for_prompt_empty(context_builder):
    """Test formatting empty memories list"""
    result = context_builder._format_memories_for_prompt([])

    assert result == ""
    assert isinstance(result, str)


def test_format_memories_for_prompt_single_memory(context_builder):
    """Test formatting single memory"""
    memories = [
        {
            "id": "mem-1",
            "content": "User prefers Python",
            "created": 1234567890.0,
        }
    ]

    result = context_builder._format_memories_for_prompt(memories)

    assert "Relevant memories from previous conversations:" in result
    assert "1. User prefers Python" in result


def test_format_memories_for_prompt_multiple_memories(context_builder):
    """Test formatting multiple memories"""
    memories = [
        {
            "id": "mem-1",
            "content": "Memory one",
            "created": 1234567890.0,
        },
        {
            "id": "mem-2",
            "content": "Memory two",
            "created": 1234567891.0,
        },
        {
            "id": "mem-3",
            "content": "Memory three",
            "created": 1234567892.0,
        },
    ]

    result = context_builder._format_memories_for_prompt(memories)

    assert "Relevant memories from previous conversations:" in result
    assert "1. Memory one" in result
    assert "2. Memory two" in result
    assert "3. Memory three" in result


def test_format_memories_for_prompt_respects_limit(context_builder):
    """Test that memory formatting respects the input limit"""
    memories = [
        {"id": f"mem-{i}", "content": f"Memory {i}", "created": 1234567890.0 + i}
        for i in range(10)
    ]

    # Only pass first 3 memories (already limited by caller)
    result = context_builder._format_memories_for_prompt(memories[:3])

    assert "1. Memory 0" in result
    assert "2. Memory 1" in result
    assert "3. Memory 2" in result
    assert "Memory 3" not in result
    assert "Memory 4" not in result


def test_format_memories_for_prompt_handles_missing_fields(context_builder):
    """Test formatting memories with missing optional fields"""
    memories = [
        {"id": "mem-1", "content": "Memory without metadata"}
    ]

    result = context_builder._format_memories_for_prompt(memories)

    assert "1. Memory without metadata" in result


# ===== Memory Retrieval Tests =====

@pytest.mark.asyncio
async def test_retrieve_memories_returns_empty_list(context_builder):
    """Test that _retrieve_memories returns empty list (stub)"""
    result = await context_builder._retrieve_memories(
        session_id="test-session-123",
        limit=5,
    )

    assert result == []
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_retrieve_memories_respects_limit_param(context_builder):
    """Test that _retrieve_memories accepts limit parameter"""
    result = await context_builder._retrieve_memories(
        session_id="test-session-123",
        limit=10,
    )

    # Stub returns empty list regardless of limit
    assert result == []
    assert isinstance(result, list)


# ===== System Prompt with Memories Tests =====

def test_build_system_prompt_without_memories(context_builder, sample_agent):
    """Test building system prompt without memories"""
    result = context_builder._build_system_prompt(
        agent=sample_agent,
        skills=[],
        memories=None,
    )

    assert "You are a helpful assistant." in result
    assert "Relevant memories" not in result


def test_build_system_prompt_with_empty_memories(context_builder, sample_agent):
    """Test building system prompt with empty memories list"""
    result = context_builder._build_system_prompt(
        agent=sample_agent,
        skills=[],
        memories=[],
    )

    assert "You are a helpful assistant." in result
    assert "Relevant memories" not in result


def test_build_system_prompt_with_memories(context_builder, sample_agent, sample_memories):
    """Test building system prompt with memories"""
    result = context_builder._build_system_prompt(
        agent=sample_agent,
        skills=[],
        memories=sample_memories,
    )

    assert "Relevant memories from previous conversations:" in result
    assert "1. User prefers Python over JavaScript" in result
    assert "2. Project uses PostgreSQL" in result
    assert "3. Last meeting discussed migration" in result
    assert "You are a helpful assistant." in result


def test_build_system_prompt_memories_appear_before_base_prompt(
    context_builder, sample_agent, sample_memories
):
    """Test that memories appear before base prompt in system prompt"""
    result = context_builder._build_system_prompt(
        agent=sample_agent,
        skills=[],
        memories=sample_memories,
    )

    memories_pos = result.find("Relevant memories")
    base_prompt_pos = result.find("You are a helpful assistant")

    assert memories_pos >= 0
    assert base_prompt_pos > memories_pos


def test_build_system_prompt_memories_limit(context_builder, sample_agent):
    """Test that system prompt builder limits to 5 memories max"""
    memories = [
        {"id": f"mem-{i}", "content": f"Memory {i}", "created": 1234567890.0 + i}
        for i in range(10)
    ]

    result = context_builder._build_system_prompt(
        agent=sample_agent,
        skills=[],
        memories=memories,
    )

    # Should only include first 5 memories
    assert "1. Memory 0" in result
    assert "2. Memory 1" in result
    assert "3. Memory 2" in result
    assert "4. Memory 3" in result
    assert "5. Memory 4" in result
    assert "Memory 5" not in result


def test_build_system_prompt_memories_and_skills(
    context_builder, sample_agent, sample_memories
):
    """Test that both memories and skills are included in system prompt"""
    # Mock skill injector to return a skills section
    mock_skill = Mock()
    mock_skill.name = "git-master"
    mock_skill.description = "Git expert"
    mock_skill.content = "Git operations"

    context_builder.skill_injector.loader.get_skill_by_name = Mock(return_value=mock_skill)

    result = context_builder._build_system_prompt(
        agent=sample_agent,
        skills=["git-master"],
        memories=sample_memories,
    )

    # Check memories are present
    assert "Relevant memories from previous conversations:" in result
    assert "1. User prefers Python" in result

    # Check skills are present
    assert "You have access to the following skills:" in result
    assert "git-master" in result

    # Check base prompt is present
    assert "You are a helpful assistant." in result


# ===== Build Agent Context with Memories Tests =====

@pytest.mark.asyncio
async def test_build_agent_context_with_memories(
    context_builder, sample_session, sample_agent, sample_tools, sample_memories
):
    """Test building agent context with memories"""
    result = await context_builder.build_agent_context(
        session=sample_session,
        agent=sample_agent,
        tools=sample_tools,
        skills=[],
        memories=sample_memories,
    )

    assert isinstance(result, AgentContext)
    assert result.memories == sample_memories
    assert result.system_prompt is not None


@pytest.mark.asyncio
async def test_build_agent_context_memories_in_system_prompt(
    context_builder, sample_session, sample_agent, sample_tools, sample_memories
):
    """Test that memories are injected into system prompt"""
    result = await context_builder.build_agent_context(
        session=sample_session,
        agent=sample_agent,
        tools=sample_tools,
        skills=[],
        memories=sample_memories,
    )

    # Verify memories are in the system prompt
    assert "Relevant memories from previous conversations:" in result.system_prompt
    assert "1. User prefers Python over JavaScript" in result.system_prompt


@pytest.mark.asyncio
async def test_build_agent_context_without_memories(
    context_builder, sample_session, sample_agent, sample_tools
):
    """Test building agent context without memories (default behavior)"""
    result = await context_builder.build_agent_context(
        session=sample_session,
        agent=sample_agent,
        tools=sample_tools,
        skills=[],
    )

    assert isinstance(result, AgentContext)
    assert result.memories == []
    # System prompt should not contain memory section
    assert "Relevant memories" not in result.system_prompt
