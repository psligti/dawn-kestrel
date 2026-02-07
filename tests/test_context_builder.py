"""Tests for ContextBuilder"""
from __future__ import annotations

from unittest.mock import Mock, AsyncMock
import pytest
from pathlib import Path

from dawn_kestrel.context.builder import ContextBuilder
from dawn_kestrel.core.models import Session, Message, TextPart, ToolPart
from dawn_kestrel.tools.framework import ToolRegistry, Tool, ToolContext, ToolResult
from dawn_kestrel.core.agent_types import AgentContext


class MockTool(Tool):
    """Mock tool for testing"""

    id: str
    description: str

    def __init__(self, tool_id: str, description: str, params_schema: dict):
        self.id = tool_id
        self.description = description
        self._params_schema = params_schema

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(
            title="Mock result",
            output="Mock output",
        )

    def parameters(self) -> dict:
        return self._params_schema


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
    registry = ToolRegistry()

    tool1 = MockTool(
        tool_id="bash",
        description="Execute bash commands",
        params_schema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command to execute"
                }
            },
            "required": ["command"]
        }
    )

    tool2 = MockTool(
        tool_id="read",
        description="Read file contents",
        params_schema={
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": "Path to file"
                }
            },
            "required": ["filePath"]
        }
    )

    registry.tools["bash"] = tool1
    registry.tools["read"] = tool2

    return registry


# ===== Empty History Tests =====

def test_build_llm_messages_empty_history(context_builder):
    """Test building LLM messages with empty history"""
    messages = []

    result = context_builder._build_llm_messages(messages)

    assert result == []
    assert isinstance(result, list)


# ===== Text-Only History Tests =====

def test_build_llm_messages_text_only_user(context_builder):
    """Test building LLM messages with text-only user message"""
    messages = [
        Message(
            id="msg-1",
            session_id="test-session-123",
            role="user",
            text="Hello, how are you?",
        )
    ]

    result = context_builder._build_llm_messages(messages)

    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Hello, how are you?"


def test_build_llm_messages_text_only_assistant(context_builder):
    """Test building LLM messages with text-only assistant message"""
    messages = [
        Message(
            id="msg-1",
            session_id="test-session-123",
            role="assistant",
            text="",
            parts=[
                TextPart(
                    id="part-1",
                    session_id="test-session-123",
                    message_id="msg-1",
                    part_type="text",
                    text="I'm doing great!",
                )
            ],
        )
    ]

    result = context_builder._build_llm_messages(messages)

    assert len(result) == 1
    assert result[0]["role"] == "assistant"
    assert result[0]["content"] == "I'm doing great!"


def test_build_llm_messages_conversation_history(context_builder):
    """Test building LLM messages with full conversation"""
    messages = [
        Message(
            id="msg-1",
            session_id="test-session-123",
            role="user",
            text="What is the weather?",
        ),
        Message(
            id="msg-2",
            session_id="test-session-123",
            role="assistant",
            text="",
            parts=[
                TextPart(
                    id="part-1",
                    session_id="test-session-123",
                    message_id="msg-2",
                    part_type="text",
                    text="I don't have access to weather data.",
                )
            ],
        ),
        Message(
            id="msg-3",
            session_id="test-session-123",
            role="user",
            text="Can you help me with Python?",
        ),
    ]

    result = context_builder._build_llm_messages(messages)

    assert len(result) == 3
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "What is the weather?"
    assert result[1]["role"] == "assistant"
    assert result[1]["content"] == "I don't have access to weather data."
    assert result[2]["role"] == "user"
    assert result[2]["content"] == "Can you help me with Python?"


# ===== Assistant Parts to Text Concatenation Tests =====

def test_build_llm_messages_multiple_text_parts(context_builder):
    """Test building LLM messages with multiple text parts in assistant message"""
    messages = [
        Message(
            id="msg-1",
            session_id="test-session-123",
            role="assistant",
            text="",
            parts=[
                TextPart(
                    id="part-1",
                    session_id="test-session-123",
                    message_id="msg-1",
                    part_type="text",
                    text="Hello! ",
                ),
                TextPart(
                    id="part-2",
                    session_id="test-session-123",
                    message_id="msg-1",
                    part_type="text",
                    text="How can I help?",
                ),
            ],
        )
    ]

    result = context_builder._build_llm_messages(messages)

    assert len(result) == 1
    assert result[0]["role"] == "assistant"
    assert result[0]["content"] == "Hello! How can I help?"


def test_build_llm_messages_mixed_parts(context_builder):
    """Test building LLM messages with mixed parts (text + tool)"""
    messages = [
        Message(
            id="msg-1",
            session_id="test-session-123",
            role="assistant",
            text="",
            parts=[
                TextPart(
                    id="part-1",
                    session_id="test-session-123",
                    message_id="msg-1",
                    part_type="text",
                    text="Let me check that for you. ",
                ),
                ToolPart(
                    id="part-2",
                    session_id="test-session-123",
                    message_id="msg-1",
                    part_type="tool",
                    tool="bash",
                    call_id="call-1",
                    state={
                        "status": "completed",
                        "input": {"command": "ls -la"},
                        "output": "file1.txt\nfile2.txt"
                    },
                ),
                TextPart(
                    id="part-3",
                    session_id="test-session-123",
                    message_id="msg-1",
                    part_type="text",
                    text="I found 2 files.",
                ),
            ],
        )
    ]

    result = context_builder._build_llm_messages(messages)

    assert len(result) == 1
    assert result[0]["role"] == "assistant"
    # Only TextPart instances contribute to content
    assert result[0]["content"] == "Let me check that for you. I found 2 files."


def test_build_llm_messages_empty_text_parts(context_builder):
    """Test building LLM messages with empty text content"""
    messages = [
        Message(
            id="msg-1",
            session_id="test-session-123",
            role="assistant",
            text="",
            parts=[
                TextPart(
                    id="part-1",
                    session_id="test-session-123",
                    message_id="msg-1",
                    part_type="text",
                    text="",
                )
            ],
        )
    ]

    result = context_builder._build_llm_messages(messages)

    assert len(result) == 1
    assert result[0]["role"] == "assistant"
    assert result[0]["content"] == ""


# ===== Tool Schema Formatting Tests =====

def test_build_tool_schemas_single_tool(context_builder, sample_tools):
    """Test building tool schemas with single tool"""
    registry = ToolRegistry()
    tool = MockTool(
        tool_id="grep",
        description="Search files",
        params_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Search pattern"}
            },
            "required": ["pattern"]
        }
    )
    registry.tools["grep"] = tool

    result = context_builder._build_tool_schemas(registry)

    assert len(result) == 1
    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "grep"
    assert result[0]["function"]["description"] == "Search files"
    assert result[0]["function"]["parameters"]["type"] == "object"
    assert "pattern" in result[0]["function"]["parameters"]["properties"]


def test_build_tool_schemas_multiple_tools(context_builder, sample_tools):
    """Test building tool schemas with multiple tools"""
    result = context_builder._build_tool_schemas(sample_tools)

    assert len(result) == 2

    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "bash"
    assert result[0]["function"]["description"] == "Execute bash commands"
    assert "command" in result[0]["function"]["parameters"]["properties"]

    assert result[1]["type"] == "function"
    assert result[1]["function"]["name"] == "read"
    assert result[1]["function"]["description"] == "Read file contents"
    assert "filePath" in result[1]["function"]["parameters"]["properties"]


def test_build_tool_schemas_empty_registry(context_builder):
    """Test building tool schemas with empty registry"""
    registry = ToolRegistry()

    result = context_builder._build_tool_schemas(registry)

    assert result == []
    assert isinstance(result, list)


def test_build_tool_schemas_matches_provider_format(context_builder, sample_tools):
    """Test that tool schemas match provider expectations"""
    result = context_builder._build_tool_schemas(sample_tools)

    for tool_def in result:
        # Provider expects: {type: "function", function: {name, description, parameters}}
        assert "type" in tool_def
        assert tool_def["type"] == "function"
        assert "function" in tool_def
        assert "name" in tool_def["function"]
        assert "description" in tool_def["function"]
        assert "parameters" in tool_def["function"]
        assert tool_def["function"]["parameters"]["type"] == "object"


# ===== System Prompt Tests =====

def test_build_system_prompt_no_skills(context_builder, sample_agent):
    """Test building system prompt without skills"""
    result = context_builder._build_system_prompt(
        agent=sample_agent,
        skills=[],
    )

    assert result == "You are a helpful assistant."


def test_build_system_prompt_with_custom_prompt(context_builder):
    """Test building system prompt with custom agent prompt"""
    agent = {
        "name": "custom",
        "prompt": "You are an expert Python developer.",
    }

    result = context_builder._build_system_prompt(
        agent=agent,
        skills=[],
    )

    assert result == "You are an expert Python developer."


def test_build_system_prompt_with_skills(context_builder, sample_agent):
    """Test building system prompt with injected skills"""
    mock_skill = Mock()
    mock_skill.name = "git-master"
    mock_skill.description = "Git expert"
    mock_skill.content = "You are a git operations expert."

    context_builder.skill_injector.loader.get_skill_by_name = Mock(return_value=mock_skill)

    result = context_builder._build_system_prompt(
        agent=sample_agent,
        skills=["git-master"],
    )

    assert "git-master" in result
    assert "Git expert" in result
    assert "You are a git operations expert" in result
    assert "You are a helpful assistant" in result


# ===== Provider Context Tests =====

def test_build_provider_context_anthropic(context_builder, sample_session, sample_agent, sample_tools):
    """Test building provider context for Anthropic"""
    context = AgentContext(
        system_prompt="You are helpful.",
        tools=sample_tools,
        messages=[],
        session=sample_session,
        agent=sample_agent,
    )

    result = context_builder.build_provider_context(
        context=context,
        provider_id="anthropic",
    )

    assert result["system"] == "You are helpful."
    assert result["messages"] == []
    assert len(result["tools"]) == 2


def test_build_provider_context_openai(context_builder, sample_session, sample_agent, sample_tools):
    """Test building provider context for OpenAI"""
    context = AgentContext(
        system_prompt="You are helpful.",
        tools=sample_tools,
        messages=[],
        session=sample_session,
        agent=sample_agent,
    )

    result = context_builder.build_provider_context(
        context=context,
        provider_id="openai",
    )

    assert result["system"] is None
    assert len(result["messages"]) == 1
    assert result["messages"][0]["role"] == "system"
    assert result["messages"][0]["content"] == "You are helpful."
    assert len(result["tools"]) == 2


def test_build_provider_context_with_messages(context_builder, sample_session, sample_agent, sample_tools):
    """Test building provider context with message history"""
    messages = [
        Message(
            id="msg-1",
            session_id="test-session-123",
            role="user",
            text="Hello",
        ),
        Message(
            id="msg-2",
            session_id="test-session-123",
            role="assistant",
            text="",
            parts=[
                TextPart(
                    id="part-1",
                    session_id="test-session-123",
                    message_id="msg-2",
                    part_type="text",
                    text="Hi there!",
                )
            ],
        ),
    ]

    context = AgentContext(
        system_prompt="You are helpful.",
        tools=sample_tools,
        messages=messages,
        session=sample_session,
        agent=sample_agent,
    )

    result = context_builder.build_provider_context(
        context=context,
        provider_id="anthropic",
    )

    assert len(result["messages"]) == 2
    assert result["messages"][0]["role"] == "user"
    assert result["messages"][0]["content"] == "Hello"
    assert result["messages"][1]["role"] == "assistant"
    assert result["messages"][1]["content"] == "Hi there!"


# ===== Build Agent Context Tests =====

@pytest.mark.asyncio
async def test_build_agent_context(context_builder, sample_session, sample_agent, sample_tools):
    """Test building complete agent context"""
    result = await context_builder.build_agent_context(
        session=sample_session,
        agent=sample_agent,
        tools=sample_tools,
        skills=[],
        memories=[],
    )

    assert isinstance(result, AgentContext)
    assert result.system_prompt == "You are a helpful assistant."
    assert result.tools == sample_tools
    assert result.messages == []
    assert result.memories == []
    assert result.session == sample_session
    assert result.agent == sample_agent
    assert result.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_build_agent_context_with_model_override(context_builder, sample_session, sample_tools):
    """Test building agent context with custom model"""
    agent = {
        "name": "custom",
        "model": {"model": "claude-sonnet-4-20250514"},
        "prompt": "Custom prompt",
    }

    result = await context_builder.build_agent_context(
        session=sample_session,
        agent=agent,
        tools=sample_tools,
        skills=[],
    )

    assert result.model == "claude-sonnet-4-20250514"
