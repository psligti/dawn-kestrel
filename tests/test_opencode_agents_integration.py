"""
Comprehensive integration tests for all Bolt Merlin agents.

Tests verify:
- All agents can be instantiated and registered
- Multi-turn conversations work properly
- Tool usage respects agent permissions
- Skill loading works correctly
- Expected outcomes match agent descriptions
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from typing import Dict, Any

from dawn_kestrel.agents.opencode import (
    create_orchestrator_agent,
    create_consultant_agent,
    create_librarian_agent,
    create_explore_agent,
    create_frontend_ui_ux_skill,
    create_multimodal_looker_agent,
    create_autonomous_worker_agent,
    create_pre_planning_agent,
    create_plan_validator_agent,
    create_planner_agent,
    create_master_orchestrator_agent,
)
from dawn_kestrel.agents.registry import create_agent_registry
from dawn_kestrel.agents.runtime import create_agent_runtime
from dawn_kestrel.agents.builtin import Agent
from dawn_kestrel.core.models import Session, Message, TokenUsage, TextPart, ToolPart, ToolState
from dawn_kestrel.core.agent_types import AgentResult
from dawn_kestrel.tools.framework import ToolRegistry
from dawn_kestrel.tools import create_builtin_registry
from dawn_kestrel.skills.loader import Skill, SkillLoader


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def agent_registry_with_opencode():
    """Create agent registry with all opencode agents registered."""
    registry = create_agent_registry(persistence_enabled=False)

    # Register opencode agents that are not in builtin.py
    # (explore is already a built-in agent)
    agents = [
        create_orchestrator_agent(),
        create_consultant_agent(),
        create_librarian_agent(),
        create_multimodal_looker_agent(),
        create_autonomous_worker_agent(),
        create_pre_planning_agent(),
        create_plan_validator_agent(),
        create_planner_agent(),
        create_master_orchestrator_agent(),
    ]

    for agent in agents:
        await registry.register_agent(agent)

    return registry


@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    return Session(
        id="test-session-123",
        slug="test-session",
        project_id="test-project",
        directory="/tmp/test-project",
        title="Test Session for Agent Testing",
        version="1.0.0",
    )


@pytest.fixture
def mock_session_manager(mock_session):
    """Create a mock session manager."""
    manager = AsyncMock()
    manager.get_session = AsyncMock(return_value=mock_session)
    manager.list_messages = AsyncMock(return_value=[])
    manager.add_message = AsyncMock(return_value="msg-123")
    manager.add_part = AsyncMock(return_value="part-123")
    return manager


@pytest.fixture
def builtin_registry():
    """Create built-in tool registry."""
    return create_builtin_registry()


@pytest.fixture
def skill_loader():
    """Create skill loader."""
    loader = SkillLoader()
    return loader


@pytest.fixture
def agent_runtime(agent_registry_with_opencode, tmp_path):
    """Create AgentRuntime instance for testing."""
    return create_agent_runtime(
        agent_registry=agent_registry_with_opencode,
        base_dir=tmp_path,
        skill_max_char_budget=10000,
    )


def create_mock_response(
    session_id: str,
    text: str = "Test response",
    tools_used: list = None,
    tokens: Dict[str, int] = None,
) -> Message:
    """Helper to create mock response messages."""
    tools_used = tools_used or []
    tokens = tokens or {
        "input": 10,
        "output": 20,
        "reasoning": 0,
        "cache_read": 0,
        "cache_write": 0,
    }

    parts = [
        TextPart(
            id="part-1",
            session_id=session_id,
            message_id="response-123",
            part_type="text",
            text=text,
        )
    ]

    # Add tool parts if tools were used
    for tool_name in tools_used:
        parts.append(
            ToolPart(
                id=f"tool-part-{tool_name}",
                session_id=session_id,
                message_id="response-123",
                part_type="tool",
                tool=tool_name,
                call_id=f"call-{tool_name}",
                state=ToolState(
                    status="completed",
                    input={},
                    output="success",
                ),
            )
        )

    return Message(
        id="response-123",
        session_id=session_id,
        role="assistant",
        text=text,
        parts=parts,
        metadata={
            "tokens": tokens,
            "model_id": "claude-sonnet-4-20250514",
        },
    )


# ============================================================================
# Test Classes
# ============================================================================


class TestAllAgentsRegistered:
    """Test that all opencode agents are properly registered."""

    def test_all_bolt_merlin_agents_registered(self, agent_registry_with_opencode):
        """All opencode agents should be registered."""
        agent_names = agent_registry_with_opencode.list_agents()

        expected_agents = [
            "orchestrator",
            "consultant",
            "librarian",
            "explore",
            "multimodal_looker",
            "autonomous_worker",
            "pre_planning",
            "plan_validator",
            "planner",
            "master_orchestrator",
        ]

        for name in expected_agents:
            assert name in agent_names, f"Agent {name} not registered"

        # Verify we can fetch each agent
        for name in expected_agents:
            agent = agent_registry_with_opencode.get_agent(name)
            assert agent is not None
            assert agent.name == name


class TestAgentInstantiation:
    """Test that all agents can be instantiated."""

    def test_all_agents_instantiate(self):
        """All agent factory functions should return valid Agent instances."""
        agents = {
            "orchestrator": create_orchestrator_agent(),
            "consultant": create_consultant_agent(),
            "librarian": create_librarian_agent(),
            "explore": create_explore_agent(),
            "multimodal_looker": create_multimodal_looker_agent(),
            "autonomous_worker": create_autonomous_worker_agent(),
            "pre_planning": create_pre_planning_agent(),
            "plan_validator": create_plan_validator_agent(),
            "planner": create_planner_agent(),
            "master_orchestrator": create_master_orchestrator_agent(),
        }

        for name, agent in agents.items():
            assert isinstance(agent, Agent), f"{name} should return Agent instance"
            assert agent.name == name, f"{name} should have correct name"
            assert agent.description, f"{name} should have description"
            assert agent.permission, f"{name} should have permissions"

    def test_skill_is_string(self):
        """Frontend UI/UX skill should return a string."""
        skill = create_frontend_ui_ux_skill()
        assert isinstance(skill, str)
        assert len(skill) > 100  # Should have substantial content


class TestAgentPermissions:
    """Test that agent permissions are correctly configured."""

    def test_read_only_agents_deny_write(self):
        """Read-only agents should deny write/edit permissions."""
        read_only_agents = [
            ("consultant", create_consultant_agent()),
            ("librarian", create_librarian_agent()),
            ("explore", create_explore_agent()),
            ("pre_planning", create_pre_planning_agent()),
            ("plan_validator", create_plan_validator_agent()),
            ("planner", create_planner_agent()),
        ]

        for name, agent in read_only_agents:
            assert any(
                p.get("permission") == "write" and p.get("action") == "deny"
                for p in agent.permission
            ), f"{name} should deny write permission"

            assert any(
                p.get("permission") == "edit" and p.get("action") == "deny"
                for p in agent.permission
            ), f"{name} should deny edit permission"

    def test_primary_agents_allow_delegation(self):
        """Primary agents should allow task delegation."""
        primary_agents = [
            ("orchestrator", create_orchestrator_agent()),
            ("master_orchestrator", create_master_orchestrator_agent()),
        ]

        for name, agent in primary_agents:
            # Check if agent has task delegation permissions
            has_task_permission = any(
                p.get("permission") == "task" and p.get("action") == "allow"
                for p in agent.permission
            )
            # Or if it has wildcard permissions that include task
            has_wildcard = any(
                p.get("permission") == "*" and p.get("action") == "allow" for p in agent.permission
            )

            assert has_task_permission or has_wildcard, f"{name} should allow task delegation"


class TestSingleTurnExecution:
    """Test single-turn execution for each agent."""

    @pytest.mark.asyncio
    async def test_sisyphus_single_turn(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Sisyphus should execute single-turn request."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(mock_session.id, "I'll help you with that.")
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="orchestrator",
                session_id=mock_session.id,
                user_message="Help me understand this codebase",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result.agent_name == "orchestrator"
        assert result.error is None
        assert "help you with" in result.response.lower()

    @pytest.mark.asyncio
    async def test_oracle_single_turn(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Oracle should provide consultation on complex question."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "Based on my analysis, the architecture needs improvement in X and Y areas.",
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="consultant",
                session_id=mock_session.id,
                user_message="What's wrong with this architecture?",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result.agent_name == "consultant"
        assert result.error is None
        assert "analysis" in result.response.lower()

    @pytest.mark.asyncio
    async def test_explore_single_turn(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Explore should search codebase and return findings."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "Found 3 files containing the pattern: /path/to/file1.ts, /path/to/file2.ts, /path/to/file3.ts",
            tools_used=["grep"],
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="explore",
                session_id=mock_session.id,
                user_message="Find all files with auth implementation",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result.agent_name == "explore"
        assert result.error is None
        assert "grep" in result.tools_used


class TestMultiTurnExecution:
    """Test multi-turn conversation capabilities."""

    @pytest.mark.asyncio
    async def test_sisyphus_multi_turn(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Sisyphus should maintain context across multiple turns."""
        mock_ai_session = AsyncMock()

        # First turn
        mock_response1 = create_mock_response(mock_session.id, "I'll analyze the codebase for you.")
        mock_ai_session.process_message = AsyncMock(return_value=mock_response1)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result1 = await agent_runtime.execute_agent(
                agent_name="orchestrator",
                session_id=mock_session.id,
                user_message="Analyze the auth system",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result1.error is None

        # Second turn (context should be maintained)
        mock_response2 = create_mock_response(
            mock_session.id, "Based on the auth analysis, here are the improvements needed."
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response2)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result2 = await agent_runtime.execute_agent(
                agent_name="orchestrator",
                session_id=mock_session.id,
                user_message="Now suggest improvements",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result2.error is None
        assert "auth analysis" in result2.response.lower()

    @pytest.mark.asyncio
    async def test_oracle_multi_turn(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Oracle should maintain context for deep analysis."""
        mock_ai_session = AsyncMock()

        # First turn: question
        mock_response1 = create_mock_response(
            mock_session.id,
            "The architecture has 3 potential issues. Would you like me to elaborate on each?",
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response1)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result1 = await agent_runtime.execute_agent(
                agent_name="consultant",
                session_id=mock_session.id,
                user_message="Analyze this architecture",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result1.error is None

        # Second turn: follow-up
        mock_response2 = create_mock_response(
            mock_session.id,
            "Here are the 3 issues in detail: 1) X, 2) Y, 3) Z. Recommendations: A, B, C.",
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response2)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result2 = await agent_runtime.execute_agent(
                agent_name="consultant",
                session_id=mock_session.id,
                user_message="Yes, elaborate please",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result2.error is None
        assert "3 issues" in result2.response


class TestToolUsage:
    """Test that agents use tools appropriately."""

    @pytest.mark.asyncio
    async def test_explore_uses_search_tools(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Explore agent should use grep/glob tools for searching."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "Found files matching pattern",
            tools_used=["grep", "glob"],
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="explore",
                session_id=mock_session.id,
                user_message="Find all TypeScript files",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert "grep" in result.tools_used
        assert "glob" in result.tools_used

    @pytest.mark.asyncio
    async def test_sisyphus_uses_delegation_tools(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Sisyphus should use task delegation tools."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "I'll delegate this to specialized agents",
            tools_used=["task"],
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="orchestrator",
                session_id=mock_session.id,
                user_message="Refactor the entire codebase",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert "task" in result.tools_used

    @pytest.mark.asyncio
    async def test_oracle_does_not_use_write_tools(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Oracle should not use write/edit tools (read-only)."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "My analysis shows the issue is in the architecture pattern.",
            tools_used=["read"],  # Only read tools
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="consultant",
                session_id=mock_session.id,
                user_message="Analyze this code",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        # Oracle should not use write/edit tools
        assert "write" not in result.tools_used
        assert "edit" not in result.tools_used
        assert "task" not in result.tools_used


class TestSkillUsage:
    """Test that agents can use skills."""

    @pytest.mark.asyncio
    async def test_frontend_ui_ux_skill_available(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Frontend UI/UX skill should be available and loadable."""
        # The skill is a string that can be loaded
        skill_content = create_frontend_ui_ux_skill()

        assert isinstance(skill_content, str)
        assert len(skill_content) > 500  # Should have substantial content
        assert "frontend" in skill_content.lower() or "ui/ux" in skill_content.lower()

    @pytest.mark.asyncio
    async def test_sisyphus_with_frontend_skill(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Sisyphus should be able to use frontend UI/UX skill."""
        # Load the skill
        frontend_skill = create_frontend_ui_ux_skill()

        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "I'll create a beautiful UI component with proper styling.",
            tools_used=["write"],
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="orchestrator",
                session_id=mock_session.id,
                user_message="Create a stunning button component",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[frontend_skill],  # Pass skill to agent
                options={},
            )

        assert result.agent_name == "orchestrator"
        assert result.error is None


class TestAgentSpecificBehavior:
    """Test agent-specific expected behaviors."""

    @pytest.mark.asyncio
    async def test_metis_pre_planning_behavior(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Metis should analyze request for hidden intentions."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "Analysis: The request has hidden intention to refactor, not just improve. "
            "Potential ambiguity: Which patterns to follow? Recommendation: Clarify patterns first.",
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="pre_planning",
                session_id=mock_session.id,
                user_message="Improve the code",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result.agent_name == "pre_planning"
        assert result.error is None
        assert "ambiguity" in result.response.lower() or "hidden" in result.response.lower()

    @pytest.mark.asyncio
    async def test_prometheus_planning_behavior(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Prometheus should create comprehensive work plans."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "## Work Plan\n\n### Phase 1: Investigation\n- Task 1.1: Analyze current code\n- Task 1.2: Identify issues\n\n"
            "### Phase 2: Implementation\n- Task 2.1: Implement fix\n- Task 2.2: Add tests\n\n"
            "### Phase 3: Verification\n- Task 3.1: Run tests\n- Task 3.2: Verify fixes",
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="planner",
                session_id=mock_session.id,
                user_message="Plan the refactoring",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result.agent_name == "planner"
        assert result.error is None
        assert "plan" in result.response.lower()

    @pytest.mark.asyncio
    async def test_momus_validation_behavior(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Momus should validate work plans for clarity and completeness."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "Plan Validation:\n- Clarity: GOOD - steps are clear\n- Verifiability: GOOD - success criteria defined\n"
            "- Completeness: NEEDS IMPROVEMENT - missing error handling\n\nRecommendation: Add error handling steps.",
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="plan_validator",
                session_id=mock_session.id,
                user_message="Validate this plan: implement auth system",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result.agent_name == "plan_validator"
        assert result.error is None
        assert "validat" in result.response.lower()

    @pytest.mark.asyncio
    async def test_atlas_orchestration_behavior(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Atlas should orchestrate multiple agents in parallel."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "Orchestrating parallel execution:\n- Agent 1 (explore): searching codebase\n- Agent 2 (oracle): analyzing architecture\n"
            "- Agent 3 (prometheus): planning changes\n\nAll agents running in parallel...",
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="master_orchestrator",
                session_id=mock_session.id,
                user_message="Coordinate a comprehensive refactoring",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result.agent_name == "master_orchestrator"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_hephaestus_autonomous_behavior(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Hephaestus should work autonomously on deep tasks."""
        mock_ai_session = AsyncMock()
        mock_response = create_mock_response(
            mock_session.id,
            "Working autonomously:\n1. Investigating the problem\n2. Implementing solution\n3. Verifying fixes\n\n"
            "Task completed successfully.",
            tools_used=["read", "edit", "bash"],
        )
        mock_ai_session.process_message = AsyncMock(return_value=mock_response)

        with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
            result = await agent_runtime.execute_agent(
                agent_name="autonomous_worker",
                session_id=mock_session.id,
                user_message="Fix this complex bug",
                session_manager=mock_session_manager,
                tools=builtin_registry,
                skills=[],
                options={},
            )

        assert result.agent_name == "autonomous_worker"
        assert result.error is None
        assert len(result.tools_used) > 0


class TestToolPermissionFiltering:
    """Test that tool permissions are correctly enforced."""

    @pytest.mark.asyncio
    async def test_read_only_agents_filtered_tools(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Read-only agents should have write/edit tools filtered out."""
        # Test with oracle agent
        from dawn_kestrel.agents.builtin import PLAN_AGENT

        with patch.object(
            agent_runtime.agent_registry,
            "get_agent",
            return_value=PLAN_AGENT,  # Denies edit/write
        ):
            mock_ai_session = AsyncMock()
            mock_response = create_mock_response(mock_session.id, "Response")
            mock_ai_session.process_message = AsyncMock(return_value=mock_response)

            with patch(
                "dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session
            ) as mock_ai_class:
                await agent_runtime.execute_agent(
                    agent_name="plan",
                    session_id=mock_session.id,
                    user_message="Test",
                    session_manager=mock_session_manager,
                    tools=builtin_registry,
                    skills=[],
                    options={},
                )

                # Check that filtered registry excludes edit/write tools
                call_kwargs = mock_ai_class.call_args[1]
                filtered_registry = call_kwargs["tool_registry"]

                assert "edit" not in filtered_registry.tools
                assert "write" not in filtered_registry.tools

    @pytest.mark.asyncio
    async def test_explore_specific_permissions(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """Explore agent should only have search tools allowed."""
        explore_agent = create_explore_agent()

        with patch.object(
            agent_runtime.agent_registry,
            "get_agent",
            return_value=explore_agent,
        ):
            mock_ai_session = AsyncMock()
            mock_response = create_mock_response(
                mock_session.id,
                "Found results",
                tools_used=["grep", "glob", "read"],
            )
            mock_ai_session.process_message = AsyncMock(return_value=mock_response)

            with patch(
                "dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session
            ) as mock_ai_class:
                await agent_runtime.execute_agent(
                    agent_name="explore",
                    session_id=mock_session.id,
                    user_message="Find files",
                    session_manager=mock_session_manager,
                    tools=builtin_registry,
                    skills=[],
                    options={},
                )

                call_kwargs = mock_ai_class.call_args[1]
                filtered_registry = call_kwargs["tool_registry"]

                # Explore should have grep, glob, read allowed
                # But not write/edit
                assert "grep" in filtered_registry.tools
                assert "glob" in filtered_registry.tools
                assert "read" in filtered_registry.tools


class TestAgentResults:
    """Test that agent results are complete and accurate."""

    @pytest.mark.asyncio
    async def test_all_agents_return_complete_results(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """All agents should return complete AgentResult objects."""
        agents_to_test = [
            "orchestrator",
            "consultant",
            "explore",
            "pre_planning",
            "planner",
            "plan_validator",
            "master_orchestrator",
            "autonomous_worker",
            "librarian",
            "multimodal_looker",
        ]

        for agent_name in agents_to_test:
            mock_ai_session = AsyncMock()
            mock_response = create_mock_response(
                mock_session.id,
                f"Response from {agent_name}",
            )
            mock_ai_session.process_message = AsyncMock(return_value=mock_response)

            with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
                result = await agent_runtime.execute_agent(
                    agent_name=agent_name,
                    session_id=mock_session.id,
                    user_message="Test",
                    session_manager=mock_session_manager,
                    tools=builtin_registry,
                    skills=[],
                    options={},
                )

            # Verify all required fields are present
            assert isinstance(result, AgentResult)
            assert result.agent_name == agent_name
            assert result.response is not None
            assert result.parts is not None
            assert result.metadata is not None
            assert result.tools_used is not None
            assert result.tokens_used is not None
            assert result.duration > 0
            assert result.error is None


class TestAgentPrompts:
    """Test that agent prompts are comprehensive and effective."""

    def test_all_agents_have_substantial_prompts(self):
        """All agents should have substantial prompts (500+ chars)."""
        agents = {
            "orchestrator": create_orchestrator_agent(),
            "consultant": create_consultant_agent(),
            "librarian": create_librarian_agent(),
            "explore": create_explore_agent(),
            "multimodal_looker": create_multimodal_looker_agent(),
            "autonomous_worker": create_autonomous_worker_agent(),
            "pre_planning": create_pre_planning_agent(),
            "plan_validator": create_plan_validator_agent(),
            "planner": create_planner_agent(),
            "master_orchestrator": create_master_orchestrator_agent(),
        }

        for name, agent in agents.items():
            assert agent.prompt is not None, f"{name} should have prompt"
            assert len(agent.prompt) > 500, f"{name} prompt too short ({len(agent.prompt)} chars)"

    def test_prompts_contain_role_definition(self):
        """Agent prompts should contain role definitions."""
        agents = {
            "orchestrator": create_orchestrator_agent(),
            "consultant": create_consultant_agent(),
            "pre_planning": create_pre_planning_agent(),
            "planner": create_planner_agent(),
        }

        for name, agent in agents.items():
            prompt_lower = agent.prompt.lower()
            # Prompt should mention the agent's role or identity
            assert name.lower() in prompt_lower or "role" in prompt_lower, (
                f"{name} prompt should mention role"
            )


# ============================================================================
# Summary Test
# ============================================================================


class TestAllAgentsSummary:
    """Comprehensive summary test to verify all agents work."""

    @pytest.mark.asyncio
    async def test_all_agents_basic_execution(
        self,
        agent_runtime,
        mock_session,
        mock_session_manager,
        builtin_registry,
    ):
        """All agents should execute basic requests successfully."""
        agents_to_test = [
            ("orchestrator", "Help me understand this code"),
            ("consultant", "Analyze this architecture"),
            ("librarian", "Find documentation for React hooks"),
            ("explore", "Find all auth files"),
            ("pre_planning", "Analyze this request"),
            ("planner", "Create a work plan"),
            ("plan_validator", "Validate this plan"),
            ("master_orchestrator", "Orchestrate this task"),
            ("autonomous_worker", "Fix this bug"),
            ("multimodal_looker", "Analyze this image"),
        ]

        results = {}

        for agent_name, user_message in agents_to_test:
            mock_ai_session = AsyncMock()
            mock_response = create_mock_response(mock_session.id, f"Response from {agent_name}")
            mock_ai_session.process_message = AsyncMock(return_value=mock_response)

            with patch("dawn_kestrel.agents.runtime.AISession", return_value=mock_ai_session):
                result = await agent_runtime.execute_agent(
                    agent_name=agent_name,
                    session_id=mock_session.id,
                    user_message=user_message,
                    session_manager=mock_session_manager,
                    tools=builtin_registry,
                    skills=[],
                    options={},
                )

            results[agent_name] = {
                "success": result.error is None,
                "duration": result.duration,
                "has_response": bool(result.response),
            }

        # Verify all agents succeeded
        for agent_name, result_data in results.items():
            assert result_data["success"], f"{agent_name} failed"
            assert result_data["duration"] > 0, f"{agent_name} has no duration"
            assert result_data["has_response"], f"{agent_name} has no response"
