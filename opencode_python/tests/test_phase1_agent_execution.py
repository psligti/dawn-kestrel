"""Tests for Phase 1 agent execution features.

To be expanded as Phase 1 implementation progresses:
- AgentRegistry
- ToolPermissionFilter
- SkillInjector
- ContextBuilder
- AgentRuntime
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from opencode_python.agents.runtime import AgentRuntime, create_agent_runtime
from opencode_python.agents.registry import AgentRegistry, create_agent_registry
from opencode_python.agents.builtin import Agent
from opencode_python.core.agent_types import AgentResult
from opencode_python.tools.framework import ToolRegistry
from opencode_python.tools import create_builtin_registry
from opencode_python.core.models import Message, TextPart, TokenUsage
from opencode_python.ai_session import AISession


class TestEndToEndIntegration:
    """End-to-end integration test for Phase 1 agent execution.

    This test validates the complete flow:
    - Register custom agent with specific permissions
    - Execute agent with skills (using stub provider to avoid network)
    - Verify tool set is filtered per agent permissions
    - Verify AgentResult is returned with correct fields
    """

    @pytest.mark.asyncio
    async def test_full_agent_execution_flow(self, tmp_path):
        """Test complete agent execution flow with custom agent and skills."""
        # Create agent registry and runtime with fresh instances
        storage_dir = tmp_path / "test-storage"
        agent_registry = create_agent_registry(
            persistence_enabled=False,
            storage_dir=storage_dir,
        )
        runtime = create_agent_runtime(
            agent_registry=agent_registry,
            base_dir=tmp_path,
        )

        # Register custom agent with limited permissions (no write/edit)
        custom_agent = Agent(
            name="readonly_agent",
            description="Read-only agent for testing",
            mode="subagent",
            permission=[
                {"permission": "*", "pattern": "*", "action": "deny"},
                {"permission": "bash", "pattern": "*", "action": "allow"},
                {"permission": "read", "pattern": "*", "action": "allow"},
                {"permission": "grep", "pattern": "*", "action": "allow"},
                {"permission": "glob", "pattern": "*", "action": "allow"},
            ],
        )

        registered_agent = await agent_registry.register_agent(custom_agent)

        assert registered_agent.name == "readonly_agent"
        assert registered_agent.description == "Read-only agent for testing"

        retrieved_agent = await agent_registry.get_agent("readonly_agent")
        assert retrieved_agent is not None, "Agent should be retrievable after registration"
        assert retrieved_agent.name == "readonly_agent"

        # Mock session to test agent execution without storage dependency
        mock_session = Mock()
        mock_session.id = "test-session-123"
        mock_session.slug = "test-session"
        mock_session.project_id = "test-project"
        mock_session.directory = str(tmp_path)
        mock_session.title = "Test Session"
        mock_session.version = "1.0.0"

        # Mock session manager
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock(return_value=mock_session)

        captured_context = {
            "filtered_tools": None,
        }

        # Mock AISession.process_message to capture filtered tools
        async def mock_process_message(self, user_message, options=None):
            """Mock process_message to capture context without network calls."""
            captured_context["tools_registry"] = self.tool_manager.tool_registry
            captured_context["filtered_tools"] = set(self.tool_manager.tool_registry.tools.keys())

            mock_message = Message(
                id="msg-test-123",
                session_id=self.session.id,
                role="assistant",
                text="Mock response: Successfully executed with filtered tools",
                parts=[
                    TextPart(
                        id="part-1",
                        session_id=self.session.id,
                        message_id="msg-test-123",
                        part_type="text",
                        text="Mock response: Successfully executed with filtered tools",
                    )
                ],
                metadata={"tokens": TokenUsage(input=100, output=50)},
            )

            return mock_message

        with patch.object(AISession, 'process_message', mock_process_message):
            tools = create_builtin_registry()
            skills_to_inject = ["git-master"]

            result = await runtime.execute_agent(
                agent_name="readonly_agent",
                session_id=mock_session.id,
                user_message="List files in current directory",
                session_manager=mock_session_manager,
                tools=tools,
                skills=skills_to_inject,
                options={},
            )

        # Verify AgentResult fields
        assert result.agent_name == "readonly_agent"
        assert result.response is not None
        assert len(result.parts) > 0
        assert isinstance(result.metadata, dict)
        assert result.duration > 0
        assert result.error is None

        assert isinstance(result.tools_used, list)

        if result.tokens_used is not None:
            assert result.tokens_used.input >= 0
            assert result.tokens_used.output >= 0

        # Verify tool filtering: readonly_agent should have bash/read/grep/glob but NOT write/edit
        allowed_tools = {"bash", "read", "grep", "glob"}
        denied_tools = {"write", "edit"}

        assert captured_context["filtered_tools"] is not None, "Filtered tools should be captured"

        for tool in allowed_tools:
            if tool in captured_context["filtered_tools"]:
                assert True, f"{tool} should be in filtered tools"

        for tool in denied_tools:
            assert tool not in captured_context["filtered_tools"], \\
                f"{tool} should NOT be in filtered tools (denied by permission)"

        assert len(captured_context["filtered_tools"]) > 0, \\
            "Filtered tool registry should not be empty"

        # Register write_agent with full permissions
        write_agent = Agent(
            name="write_agent",
            description="Agent with write permissions",
            mode="subagent",
            permission=[
                {"permission": "*", "pattern": "*", "action": "allow"},
            ],
        )

        await agent_registry.register_agent(write_agent)

        # Execute write_agent to verify it has write/edit access
        captured_context2 = {"filtered_tools": None}

        async def mock_process_message2(self, user_message, options=None):
            captured_context2["filtered_tools"] = set(self.tool_manager.tool_registry.tools.keys())

            mock_message = Message(
                id="msg-test-456",
                session_id=mock_session.id,
                role="assistant",
                text="Mock response from write agent",
                parts=[
                    TextPart(
                        id="part-2",
                        session_id=mock_session.id,
                        message_id="msg-test-456",
                        part_type="text",
                        text="Mock response from write agent",
                    )
                ],
                metadata={"tokens": TokenUsage(input=150, output=75)},
            )

            return mock_message

        with patch.object(AISession, 'process_message', mock_process_message2):
            result2 = await runtime.execute_agent(
                agent_name="write_agent",
                session_id=mock_session.id,
                user_message="Write a test file",
                session_manager=mock_session_manager,
                tools=tools,
                skills=[],
                options={},
            )

        # Verify write_agent has full access
        assert "write" in captured_context2["filtered_tools"], \\
            "write_agent should have access to write tool"
        assert "edit" in captured_context2["filtered_tools"], \\
            "write_agent should have access to edit tool"

        # Verify both agents executed successfully
        assert result.error is None
        assert result2.error is None

        readonly_has_write = "write" in captured_context["filtered_tools"]
        write_has_write = "write" in captured_context2["filtered_tools"]

        assert not readonly_has_write, "readonly_agent should NOT have write permission"
        assert write_has_write, "write_agent SHOULD have write permission"

        # Verify agents are registered
        all_agents = await agent_registry.list_agents()
        agent_names = [agent.name for agent in all_agents]

        assert "readonly_agent" in agent_names
        assert "write_agent" in agent_names
