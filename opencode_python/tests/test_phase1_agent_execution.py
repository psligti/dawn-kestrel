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
from unittest.mock import Mock, AsyncMock

from opencode_python.agents import AgentExecutor, create_agent_manager
from opencode_python.core.session import SessionManager
from opencode_python.storage.store import SessionStorage
from opencode_python.core.models import Session
from opencode_python.ai_session import AISession


class TestAgentExecutorSession:
    """Test AgentExecutor uses real Session objects instead of fakes."""

    @pytest.mark.asyncio
    async def test_execute_agent_requires_session_manager(self) -> None:
        """AgentExecutor should raise error without session_manager."""
        storage = SessionStorage(Path.cwd())
        agent_manager = create_agent_manager(storage)

        from opencode_python.ai.tool_execution import ToolExecutionManager
        tool_manager = Mock(spec=ToolExecutionManager)

        executor = AgentExecutor(
            agent_manager=agent_manager,
            tool_manager=tool_manager,
            session_manager=None
        )

        with pytest.raises(ValueError, match="requires session_manager"):
            await executor.execute_agent(
                agent_name="build",
                user_message="test",
                session_id="test-session-id"
            )

    @pytest.mark.asyncio
    async def test_execute_agent_requires_real_session(self) -> None:
        """AgentExecutor should raise error for non-existent session."""
        storage = SessionStorage(Path.cwd())
        agent_manager = create_agent_manager(storage)
        session_manager = SessionManager(storage=storage, project_dir=Path.cwd())

        from opencode_python.ai.tool_execution import ToolExecutionManager
        tool_manager = Mock(spec=ToolExecutionManager)
        tool_manager.tool_registry = Mock()
        tool_manager.tool_registry.tools = {}

        executor = AgentExecutor(
            agent_manager=agent_manager,
            tool_manager=tool_manager,
            session_manager=session_manager
        )

        with pytest.raises(ValueError, match="Session not found"):
            await executor.execute_agent(
                agent_name="build",
                user_message="test",
                session_id="non-existent-session-id"
            )

    @pytest.mark.asyncio
    async def test_execute_agent_requires_non_empty_session_metadata(self) -> None:
        """AgentExecutor should raise error for sessions with empty metadata."""
        storage = SessionStorage(Path.cwd())
        agent_manager = create_agent_manager(storage)
        session_manager = SessionManager(storage=storage, project_dir=Path.cwd())

        session = Session(
            id="test-session-empty-metadata",
            slug="test-session",
            project_id="",
            directory="",
            title="",
            version="1.0"
        )

        await storage.create_session(session)

        from opencode_python.ai.tool_execution import ToolExecutionManager
        tool_manager = Mock(spec=ToolExecutionManager)
        tool_manager.tool_registry = Mock()
        tool_manager.tool_registry.tools = {}

        executor = AgentExecutor(
            agent_manager=agent_manager,
            tool_manager=tool_manager,
            session_manager=session_manager
        )

        with pytest.raises(ValueError, match="has empty project_id"):
            await executor.execute_agent(
                agent_name="build",
                user_message="test",
                session_id="test-session-empty-metadata"
            )

    @pytest.mark.asyncio
    async def test_execute_agent_uses_real_session_with_metadata(self) -> None:
        """AgentExecutor should successfully use real session with valid metadata."""
        storage = SessionStorage(Path.cwd())
        agent_manager = create_agent_manager(storage)
        session_manager = SessionManager(storage=storage, project_dir=Path.cwd())

        session = await session_manager.create(
            title="Test Session",
            version="1.0"
        )

        assert session.project_id != "", "Session should have non-empty project_id"
        assert session.directory != "", "Session should have non-empty directory"
        assert session.title != "", "Session should have non-empty title"

        from opencode_python.ai.tool_execution import ToolExecutionManager
        tool_manager = Mock(spec=ToolExecutionManager)
        tool_manager.tool_registry = Mock()
        tool_manager.tool_registry.tools = {}

        executor = AgentExecutor(
            agent_manager=agent_manager,
            tool_manager=tool_manager,
            session_manager=session_manager
        )

        agent = await agent_manager.get_agent_by_name("build")
        if agent:
            await agent_manager.initialize_agent(agent, session)
            state = agent_manager.get_agent_state(session.id)
            assert state is not None
            assert state.agent_name == "build"


class TestToolRegistryWiring:

    def test_ai_session_has_builtin_tools(self) -> None:
        session = Session(
            id="test_session",
            slug="test",
            project_id="test-project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0"
        )

        ai_session = AISession(
            session=session,
            provider_id="anthropic",
            model="claude-3-5-sonnet-20241022",
        )

        assert ai_session.tool_manager is not None
        assert ai_session.tool_manager.tool_registry is not None
        assert len(ai_session.tool_manager.tool_registry.tools) > 0

        expected_tools = {"bash", "read", "write", "grep", "glob"}
        actual_tools = set(ai_session.tool_manager.tool_registry.tools.keys())

        assert expected_tools.issubset(actual_tools), f"Missing tools: {expected_tools - actual_tools}"

    def test_ai_session_custom_tool_registry(self) -> None:
        from opencode_python.tools.framework import ToolRegistry

        session = Session(
            id="test_session",
            slug="test",
            project_id="test-project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0"
        )

        custom_registry = ToolRegistry()
        ai_session = AISession(
            session=session,
            provider_id="anthropic",
            model="claude-3-5-sonnet-20241022",
            tool_registry=custom_registry,
        )

        assert ai_session.tool_manager.tool_registry is custom_registry

    def test_get_tool_definitions_returns_non_empty(self) -> None:
        session = Session(
            id="test_session",
            slug="test",
            project_id="test-project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0"
        )

        ai_session = AISession(
            session=session,
            provider_id="anthropic",
            model="claude-3-5-sonnet-20241022",
        )

        tool_definitions = ai_session._get_tool_definitions()

        assert len(tool_definitions) > 0
        assert "bash" in tool_definitions or "read" in tool_definitions

        if "bash" in tool_definitions:
            bash_def = tool_definitions["bash"]
            assert "type" in bash_def
            assert bash_def["type"] == "function"
            assert "function" in bash_def
            assert "name" in bash_def["function"]
            assert "description" in bash_def["function"]
            assert "parameters" in bash_def["function"]


class TestPhase1Placeholder:
    """Placeholder tests for Phase 1 agent execution."""

    def test_phase1_placeholder(self) -> None:
        """Placeholder test - Phase 1 features to be implemented."""
        assert True


class TestAgentTypes:
    """Test Phase 1 agent types and protocols."""

    def test_agent_result_basic(self) -> None:
        """AgentResult should create with minimal fields."""
        from opencode_python.core.agent_types import AgentResult

        result = AgentResult(
            agent_name="test-agent",
            response="Hello, world!",
        )

        assert result.agent_name == "test-agent"
        assert result.response == "Hello, world!"
        assert result.parts == []
        assert result.tools_used == []
        assert result.tokens_used is None
        assert result.duration == 0.0
        assert result.error is None

    def test_agent_result_with_metadata(self) -> None:
        """AgentResult should support all fields."""
        from opencode_python.core.agent_types import AgentResult
        from opencode_python.core.models import TokenUsage, ToolPart, ToolState, TextPart

        result = AgentResult(
            agent_name="build-agent",
            response="Build completed successfully",
            parts=[
                TextPart(
                    id="part1",
                    session_id="session1",
                    message_id="msg1",
                    part_type="text",
                    text="Step 1",
                )
            ],
            metadata={"key": "value"},
            tools_used=["bash", "read"],
            tokens_used=TokenUsage(input=100, output=50, reasoning=10),
            duration=3.5,
            error=None,
        )

        assert result.agent_name == "build-agent"
        assert len(result.parts) == 1
        assert result.metadata["key"] == "value"
        assert "bash" in result.tools_used
        assert result.tokens_used.input == 100
        assert result.duration == 3.5

    def test_agent_context_basic(self) -> None:
        """AgentContext should create with minimal fields."""
        from opencode_python.core.agent_types import AgentContext
        from opencode_python.tools.framework import ToolRegistry

        context = AgentContext(
            system_prompt="You are a helpful assistant",
            tools=ToolRegistry(),
            messages=[],
        )

        assert context.system_prompt == "You are a helpful assistant"
        assert context.messages == []
        assert context.memories == []
        assert context.session is None
        assert context.agent is None
        assert context.model == "gpt-4o-mini"
        assert context.metadata == {}

    def test_agent_context_full(self) -> None:
        """AgentContext should support all fields."""
        from opencode_python.core.agent_types import AgentContext
        from opencode_python.tools.framework import ToolRegistry
        from opencode_python.core.models import Session, Message

        session = Session(
            id="session1",
            slug="test",
            project_id="test-project",
            directory="/tmp",
            title="Test",
            version="1.0.0",
        )

        context = AgentContext(
            system_prompt="System prompt",
            tools=ToolRegistry(),
            messages=[
                Message(
                    id="msg1",
                    session_id="session1",
                    role="user",
                    text="Hello",
                )
            ],
            memories=[{"type": "note", "content": "Important info"}],
            session=session,
            agent={"name": "test-agent", "permissions": []},
            model="claude-3-5-sonnet-20241022",
            metadata={"custom_key": "value"},
        )

        assert context.system_prompt == "System prompt"
        assert len(context.messages) == 1
        assert len(context.memories) == 1
        assert context.session is not None
        assert context.session.id == "session1"
        assert context.agent is not None
        assert context.agent["name"] == "test-agent"
        assert context.model == "claude-3-5-sonnet-20241022"
        assert context.metadata["custom_key"] == "value"

    def test_session_manager_like_protocol(self) -> None:
        """SessionManagerLike should work as a protocol."""
        from opencode_python.core.agent_types import SessionManagerLike
        from opencode_python.core.session import SessionManager
        from opencode_python.storage.store import SessionStorage
        from pathlib import Path

        # SessionManager should satisfy SessionManagerLike protocol
        storage = SessionStorage(Path.cwd())
        manager = SessionManager(storage, Path.cwd())

        # Runtime check should pass
        assert isinstance(manager, SessionManagerLike)

    def test_provider_like_protocol(self) -> None:
        """ProviderLike should work as a protocol."""
        from opencode_python.core.agent_types import ProviderLike
        from unittest.mock import AsyncMock

        # Create a mock that satisfies the protocol
        mock_provider = AsyncMock()
        mock_provider.stream = AsyncMock()
        mock_provider.generate = AsyncMock()

        # Runtime check should pass
        assert isinstance(mock_provider, ProviderLike)


class TestToolPermissionFilter:
    """Test ToolPermissionFilter for filtering tools based on agent permissions."""

    def test_plan_agent_denies_edit_and_write(self) -> None:
        """PLAN agent permission rules should deny edit and write tools."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter
        from opencode_python.tools.framework import ToolRegistry

        # PLAN agent permissions (from agents/builtin.py)
        plan_permissions = [
            {"permission": "*", "pattern": "*", "action": "allow"},
            {"permission": "question", "pattern": "*", "action": "allow"},
            {"permission": "plan_exit", "pattern": "*", "action": "deny"},
            {"permission": "edit", "pattern": "*", "action": "deny"},
            {"permission": "write", "pattern": "*", "action": "deny"},
            {"permission": "plan_exit", "pattern": ".opencode/plans/*.md", "action": "allow"},
        ]

        # Create a mock tool registry with common tools
        registry = ToolRegistry()
        tool_ids = {"bash", "read", "write", "edit", "grep", "glob", "question"}

        filter_obj = ToolPermissionFilter(
            permissions=plan_permissions,
            tool_registry=registry,
        )

        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        # edit and write should be denied
        assert "edit" not in allowed_ids, "edit should be denied for PLAN agent"
        assert "write" not in allowed_ids, "write should be denied for PLAN agent"

        # Other tools should be allowed
        assert "bash" in allowed_ids, "bash should be allowed for PLAN agent"
        assert "read" in allowed_ids, "read should be allowed for PLAN agent"
        assert "grep" in allowed_ids, "grep should be allowed for PLAN agent"
        assert "glob" in allowed_ids, "glob should be allowed for PLAN agent"
        assert "question" in allowed_ids, "question should be allowed for PLAN agent"

    def test_build_agent_allows_all(self) -> None:
        """BUILD agent permission rules should allow all tools."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter
        from opencode_python.tools.framework import ToolRegistry

        # BUILD agent permissions (from agents/builtin.py)
        build_permissions = [
            {"permission": "*", "pattern": "*", "action": "allow"},
            {"permission": "question", "pattern": "*", "action": "allow"},
            {"permission": "plan_enter", "pattern": "*", "action": "allow"},
        ]

        registry = ToolRegistry()
        tool_ids = {"bash", "read", "write", "edit", "grep", "glob", "question"}

        filter_obj = ToolPermissionFilter(
            permissions=build_permissions,
            tool_registry=registry,
        )

        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        # All tools should be allowed
        assert allowed_ids == tool_ids, f"Expected all tools, got {allowed_ids}"

    def test_wildcard_permission_allows_all_tools(self) -> None:
        """Wildcard permission should match all tool IDs."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        permissions = [
            {"permission": "*", "pattern": "*", "action": "allow"},
        ]

        tool_ids = {"bash", "read", "write", "edit", "grep", "glob"}
        filter_obj = ToolPermissionFilter(permissions=permissions)

        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        assert allowed_ids == tool_ids, "Wildcard should allow all tools"

    def test_specific_tool_permission(self) -> None:
        """Specific tool permission should only match that tool."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        permissions = [
            {"permission": "bash", "pattern": "*", "action": "allow"},
            {"permission": "read", "pattern": "*", "action": "allow"},
        ]

        tool_ids = {"bash", "read", "write", "edit"}
        filter_obj = ToolPermissionFilter(permissions=permissions)

        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        assert "bash" in allowed_ids, "bash should be allowed"
        assert "read" in allowed_ids, "read should be allowed"
        assert "write" not in allowed_ids, "write should be denied (no rule)"
        assert "edit" not in allowed_ids, "edit should be denied (no rule)"

    def test_last_matching_rule_wins(self) -> None:
        """Rules are evaluated in order, last matching rule wins."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        permissions = [
            {"permission": "*", "pattern": "*", "action": "allow"},  # First: allow all
            {"permission": "edit", "pattern": "*", "action": "deny"},  # Last: deny edit
        ]

        tool_ids = {"bash", "read", "write", "edit"}
        filter_obj = ToolPermissionFilter(permissions=permissions)

        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        # edit should be denied (last matching rule wins)
        assert "edit" not in allowed_ids, "edit should be denied by last rule"
        # Other tools should be allowed by first rule
        assert "bash" in allowed_ids, "bash should be allowed"
        assert "read" in allowed_ids, "read should be allowed"
        assert "write" in allowed_ids, "write should be allowed"

    def test_deny_then_allow_ordering(self) -> None:
        """Deny then allow rules: last matching rule wins."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        permissions = [
            {"permission": "bash", "pattern": "*", "action": "deny"},
            {"permission": "bash", "pattern": "*", "action": "allow"},
        ]

        tool_ids = {"bash"}
        filter_obj = ToolPermissionFilter(permissions=permissions)

        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        # Last rule (allow) should win
        assert "bash" in allowed_ids, "Last rule (allow) should win"

    def test_allow_then_deny_ordering(self) -> None:
        """Allow then deny rules: last matching rule wins."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        permissions = [
            {"permission": "bash", "pattern": "*", "action": "allow"},
            {"permission": "bash", "pattern": "*", "action": "deny"},
        ]

        tool_ids = {"bash"}
        filter_obj = ToolPermissionFilter(permissions=permissions)

        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        # Last rule (deny) should win
        assert "bash" not in allowed_ids, "Last rule (deny) should win"

    def test_empty_permissions_default_to_deny(self) -> None:
        """Empty permissions should default to deny all tools."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        filter_obj = ToolPermissionFilter(permissions=[])

        tool_ids = {"bash", "read", "write"}
        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        assert len(allowed_ids) == 0, "Empty permissions should deny all"

    def test_none_permissions_handled(self) -> None:
        """None permissions should be handled gracefully."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        filter_obj = ToolPermissionFilter(permissions=None)

        tool_ids = {"bash", "read"}
        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        assert len(allowed_ids) == 0, "None permissions should deny all"

    def test_is_tool_allowed(self) -> None:
        """is_tool_allowed should correctly check individual tools."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        permissions = [
            {"permission": "*", "pattern": "*", "action": "allow"},
            {"permission": "edit", "pattern": "*", "action": "deny"},
        ]

        filter_obj = ToolPermissionFilter(permissions=permissions)

        assert filter_obj.is_tool_allowed("bash") is True
        assert filter_obj.is_tool_allowed("read") is True
        assert filter_obj.is_tool_allowed("edit") is False
        assert filter_obj.is_tool_allowed("unknown") is True  # wildcard matches

    def test_get_filtered_tool_ids_uses_registry_if_none_provided(self) -> None:
        """get_filtered_tool_ids should use registry tools if tool_ids is None."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter
        from opencode_python.tools.framework import ToolRegistry
        from unittest.mock import Mock

        registry = ToolRegistry()
        registry.tools = {
            "bash": Mock(),
            "read": Mock(),
            "write": Mock(),
        }

        permissions = [
            {"permission": "*", "pattern": "*", "action": "allow"},
            {"permission": "write", "pattern": "*", "action": "deny"},
        ]

        filter_obj = ToolPermissionFilter(
            permissions=permissions,
            tool_registry=registry,
        )

        # Don't provide tool_ids, should use registry
        allowed_ids = filter_obj.get_filtered_tool_ids()

        assert "bash" in allowed_ids
        assert "read" in allowed_ids
        assert "write" not in allowed_ids

    def test_get_filtered_registry_returns_new_registry(self) -> None:
        """get_filtered_registry should return new registry with only allowed tools."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter
        from opencode_python.tools.framework import ToolRegistry
        from unittest.mock import Mock

        registry = ToolRegistry()
        registry.tools = {
            "bash": Mock(),
            "read": Mock(),
            "write": Mock(),
        }
        registry.tool_metadata = {
            "bash": {"category": "system"},
            "read": {"category": "io"},
        }

        permissions = [
            {"permission": "*", "pattern": "*", "action": "allow"},
            {"permission": "write", "pattern": "*", "action": "deny"},
        ]

        filter_obj = ToolPermissionFilter(
            permissions=permissions,
            tool_registry=registry,
        )

        filtered_registry = filter_obj.get_filtered_registry()

        assert filtered_registry is not None
        assert "bash" in filtered_registry.tools
        assert "read" in filtered_registry.tools
        assert "write" not in filtered_registry.tools

        # Metadata should be preserved
        assert filtered_registry.get_metadata("bash") == {"category": "system"}
        assert filtered_registry.get_metadata("read") == {"category": "io"}

    def test_get_filtered_registry_with_none_registry(self) -> None:
        """get_filtered_registry should return None if no registry available."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        filter_obj = ToolPermissionFilter(permissions=[], tool_registry=None)

        assert filter_obj.get_filtered_registry() is None

    def test_general_agent_denies_todos(self) -> None:
        """GENERAL agent permission rules should deny todoread and todowrite."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        # GENERAL agent permissions (from agents/builtin.py)
        general_permissions = [
            {"permission": "*", "pattern": "*", "action": "allow"},
            {"permission": "todoread", "pattern": "*", "action": "deny"},
            {"permission": "todowrite", "pattern": "*", "action": "deny"},
        ]

        tool_ids = {"bash", "read", "write", "todoread", "todowrite"}
        filter_obj = ToolPermissionFilter(permissions=general_permissions)

        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        assert "todoread" not in allowed_ids, "todoread should be denied for GENERAL agent"
        assert "todowrite" not in allowed_ids, "todowrite should be denied for GENERAL agent"
        assert "bash" in allowed_ids, "bash should be allowed"
        assert "read" in allowed_ids, "read should be allowed"
        assert "write" in allowed_ids, "write should be allowed"

    def test_explore_agent_specific_permissions(self) -> None:
        """EXPLORE agent should only allow specific tools."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        # EXPLORE agent permissions (from agents/builtin.py)
        explore_permissions = [
            {"permission": "*", "pattern": "*", "action": "deny"},
            {"permission": "grep", "pattern": "*", "action": "allow"},
            {"permission": "glob", "pattern": "*", "action": "allow"},
            {"permission": "list", "pattern": "*", "action": "allow"},
            {"permission": "bash", "pattern": "*", "action": "allow"},
            {"permission": "webfetch", "pattern": "*", "action": "allow"},
            {"permission": "websearch", "pattern": "*", "action": "allow"},
            {"permission": "codesearch", "pattern": "*", "action": "allow"},
            {"permission": "read", "pattern": "*", "action": "allow"},
        ]

        tool_ids = {"grep", "glob", "list", "bash", "webfetch", "websearch", "codesearch", "read", "write", "edit"}
        filter_obj = ToolPermissionFilter(permissions=explore_permissions)

        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        # Only allowed tools should be present
        expected_allowed = {"grep", "glob", "list", "bash", "webfetch", "websearch", "codesearch", "read"}
        assert allowed_ids == expected_allowed, f"Expected {expected_allowed}, got {allowed_ids}"

        # Write and edit should be denied
        assert "write" not in allowed_ids
        assert "edit" not in allowed_ids

    def test_invalid_permission_rules_ignored(self) -> None:
        """Invalid permission rules should be ignored."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        permissions = [
            {"permission": "*", "pattern": "*", "action": "allow"},
            {},  # Empty rule
            {"action": "allow"},  # Missing permission
            {"permission": "bash"},  # Missing action
            None,  # None rule
            {"permission": "read", "pattern": "*", "action": "deny"},
        ]

        tool_ids = {"bash", "read", "write"}
        filter_obj = ToolPermissionFilter(permissions=permissions)

        allowed_ids = filter_obj.get_filtered_tool_ids(tool_ids)

        # Valid rules should still work
        assert "bash" in allowed_ids
        assert "read" not in allowed_ids
        assert "write" in allowed_ids

    def test_pattern_field_reserved_for_future(self) -> None:
        """Pattern field should be parsed but not used in current implementation."""
        from opencode_python.tools.permission_filter import ToolPermissionFilter

        # Pattern field is reserved for future use (e.g., file paths)
        # Currently, both rules match because they have the same permission field
        permissions = [
            {"permission": "read", "pattern": "*.py", "action": "allow"},
            {"permission": "read", "pattern": "*.md", "action": "deny"},
        ]

        filter_obj = ToolPermissionFilter(permissions=permissions)

        # Both rules match based on permission field, last one wins (deny)
        is_allowed = filter_obj.is_tool_allowed("read")
        assert is_allowed is False, "Last matching rule (deny) should determine permission"
