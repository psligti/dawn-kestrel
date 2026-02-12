"""Tests for AgentConfig dataclass."""

from typing import Any, Optional, cast

import pytest
from dawn_kestrel.agents.builtin import Agent
from dawn_kestrel.agents.agent_config import AgentConfig, AgentBuilder
from dawn_kestrel.core.fsm import FSM, FSMContext
from dawn_kestrel.core.result import Ok, Err


class TestAgentConfig:
    """Test AgentConfig dataclass functionality."""

    def test_agent_config_creates_from_agent(self) -> None:
        """Verify AgentConfig can be created from existing Agent."""
        # Create a test Agent
        agent = Agent(
            name="test-agent",
            description="Test agent description",
            mode="subagent",
            permission=[{"read": True}],
            native=True,
            hidden=False,
            top_p=0.9,
            temperature=0.7,
            color="#FF0000",
            model={"provider": "openai", "model": "gpt-4"},
            prompt="You are a helpful assistant",
            options={"max_tokens": 1000},
        )

        # Create AgentConfig from Agent
        config = AgentConfig.from_agent(agent)

        # Verify Agent is wrapped
        assert config.agent is agent
        assert config.agent.name == "test-agent"
        assert config.agent.description == "Test agent description"

        # Verify FSMs are None by default
        assert config.lifecycle_fsm is None
        assert config.workflow_fsm is None

        # Verify metadata defaults to empty dict
        assert config.metadata == {}

    def test_agent_config_with_fsms_and_metadata(self) -> None:
        """Verify AgentConfig with FSMs and metadata."""
        # Create test Agent
        agent = Agent(
            name="agent-with-fsms",
            description="Agent with FSMs",
            mode="primary",
            permission=[{"write": True}],
        )

        # Create mock FSM
        class MockFSM(FSM):
            def __init__(self, state: str = "initial") -> None:
                self._state = state

            async def get_state(self) -> str:
                return self._state

            async def transition_to(
                self, new_state: str, context: Optional[FSMContext] = None
            ) -> Ok[None]:
                self._state = new_state
                return Ok(None)

            async def is_transition_valid(self, from_state: str, to_state: str) -> bool:
                return True

        lifecycle_fsm = MockFSM("idle")
        workflow_fsm = MockFSM("pending")
        metadata = {"version": "1.0", "author": "test"}

        # Create AgentConfig with all parameters
        config = AgentConfig(
            agent=agent,
            lifecycle_fsm=lifecycle_fsm,
            workflow_fsm=workflow_fsm,
            metadata=metadata,
        )

        # Verify all fields are set correctly
        assert config.agent is agent
        assert config.agent.name == "agent-with-fsms"
        assert config.lifecycle_fsm is lifecycle_fsm
        assert config.workflow_fsm is workflow_fsm
        assert config.metadata == metadata
        assert config.metadata["version"] == "1.0"
        assert config.metadata["author"] == "test"

    def test_agent_config_metadata_defaults_to_empty_dict(self) -> None:
        """Verify metadata defaults to empty dict when not provided."""
        agent = Agent(
            name="simple-agent",
            description="Simple agent",
            mode="subagent",
            permission=[],
        )

        # Create AgentConfig without specifying metadata
        config = AgentConfig(agent=agent)

        # Verify metadata is empty dict
        assert config.metadata == {}
        assert isinstance(config.metadata, dict)
        assert len(config.metadata) == 0

    def test_agent_config_fsms_are_optional(self) -> None:
        """Verify FSMs are optional and default to None."""
        agent = Agent(
            name="no-fsm-agent",
            description="Agent without FSMs",
            mode="subagent",
            permission=[],
        )

        # Create AgentConfig without FSMs
        config = AgentConfig(agent=agent)

        # Verify FSMs are None
        assert config.lifecycle_fsm is None
        assert config.workflow_fsm is None


class TestAgentBuilder:
    """Test AgentBuilder fluent API."""

    def test_agent_builder_method_chaining(self) -> None:
        """Verify AgentBuilder supports method chaining."""
        # This test should pass once AgentBuilder is implemented
        builder = AgentBuilder()

        # All fluent methods should return self
        assert builder.with_name("test") is builder
        assert builder.with_description("Test agent") is builder
        assert builder.with_mode("subagent") is builder
        assert builder.with_permission([]) is builder
        assert builder.with_temperature(0.7) is builder
        assert builder.with_options({"key": "value"}) is builder
        assert builder.with_native(True) is builder
        assert builder.with_prompt("Custom prompt") is builder

    def test_agent_builder_creates_valid_agent_config(self) -> None:
        """Verify AgentBuilder creates valid AgentConfig with all fields."""
        result = (
            AgentBuilder()
            .with_name("test-agent")
            .with_description("Test description")
            .with_mode("subagent")
            .with_permission([{"read": True}])
            .with_temperature(0.8)
            .with_options({"max_tokens": 1000})
            .with_native(True)
            .with_prompt("Custom system prompt")
            .build()
        )

        assert result.is_ok()
        config = result.unwrap()

        # Verify AgentConfig wraps Agent correctly
        assert isinstance(config, AgentConfig)
        assert config.agent.name == "test-agent"
        assert config.agent.description == "Test description"
        assert config.agent.mode == "subagent"
        assert config.agent.permission == [{"read": True}]
        assert config.agent.temperature == 0.8
        assert config.agent.options == {"max_tokens": 1000}
        assert config.agent.native is True
        assert config.agent.prompt == "Custom system prompt"

        # Verify FSMs and metadata defaults
        assert config.lifecycle_fsm is None
        assert config.workflow_fsm is None
        assert config.metadata == {}

    def test_agent_builder_requires_mandatory_fields(self) -> None:
        """Verify build() fails without required fields (name, description, mode, permission)."""
        # Missing all required fields
        result = AgentBuilder().build()
        assert result.is_err()
        assert (
            "required" in cast(Any, result).error.lower()
            or "missing" in cast(Any, result).error.lower()
        )

        # Missing name
        result = (
            AgentBuilder()
            .with_description("Test")
            .with_mode("subagent")
            .with_permission([])
            .build()
        )
        assert result.is_err()

        # Missing description
        result = AgentBuilder().with_name("test").with_mode("subagent").with_permission([]).build()
        assert result.is_err()

        # Missing mode
        result = (
            AgentBuilder().with_name("test").with_description("Test").with_permission([]).build()
        )
        assert result.is_err()

        # Missing permission
        result = (
            AgentBuilder().with_name("test").with_description("Test").with_mode("subagent").build()
        )
        assert result.is_err()

    def test_agent_builder_optional_fields_default_correctly(self) -> None:
        """Verify optional fields have correct defaults when not set."""
        result = (
            AgentBuilder()
            .with_name("minimal-agent")
            .with_description("Minimal agent")
            .with_mode("subagent")
            .with_permission([])
            .build()
        )

        assert result.is_ok()
        agent = result.unwrap().agent

        # Verify defaults from Agent dataclass
        assert agent.native is True  # Default from Agent
        assert agent.hidden is False  # Default from Agent
        assert agent.top_p is None
        assert agent.temperature is None
        assert agent.color is None
        assert agent.model is None
        assert agent.prompt is None
        assert agent.options is None
        assert agent.steps is None

    def test_agent_builder_permission_with_multiple_rules(self) -> None:
        """Verify AgentBuilder handles multiple permission rules."""
        permissions = [
            {"read": True},
            {"write": False},
            {"execute": True, "admin": False},
        ]

        result = (
            AgentBuilder()
            .with_name("multi-perm-agent")
            .with_description("Agent with multiple permissions")
            .with_mode("primary")
            .with_permission(permissions)
            .build()
        )

        assert result.is_ok()
        assert result.unwrap().agent.permission == permissions

    def test_agent_builder_override_default_fields(self) -> None:
        """Verify AgentBuilder can override default field values."""
        result = (
            AgentBuilder()
            .with_name("override-agent")
            .with_description("Agent overriding defaults")
            .with_mode("subagent")
            .with_permission([])
            .with_native(False)  # Override default True
            .build()
        )

        assert result.is_ok()
        agent = result.unwrap().agent
        assert agent.native is False


class TestAgentBuilderFSM:
    """Test AgentBuilder FSM integration methods."""

    def test_with_lifecycle_fsm_attaches_fsm(self) -> None:
        """Verify with_lifecycle_fsm() attaches FSM to builder."""
        from dawn_kestrel.agents.agent_lifecycle_fsm import create_lifecycle_fsm

        # Create lifecycle FSM
        fsm_result = create_lifecycle_fsm()
        assert fsm_result.is_ok()
        lifecycle_fsm = fsm_result.unwrap()

        # Build with lifecycle FSM
        result = (
            AgentBuilder()
            .with_name("test-agent")
            .with_description("Test agent")
            .with_mode("subagent")
            .with_permission([])
            .with_lifecycle_fsm(lifecycle_fsm)
            .build()
        )

        assert result.is_ok()
        config = result.unwrap()
        assert config.lifecycle_fsm is lifecycle_fsm
        assert config.workflow_fsm is None  # Not set

    def test_with_workflow_fsm_attaches_fsm(self) -> None:
        """Verify with_workflow_fsm() attaches FSM to builder."""
        from dawn_kestrel.agents.agent_workflow_fsm import create_workflow_fsm

        # Create workflow FSM
        fsm_result = create_workflow_fsm()
        assert fsm_result.is_ok()
        workflow_fsm = fsm_result.unwrap()

        # Build with workflow FSM
        result = (
            AgentBuilder()
            .with_name("test-agent")
            .with_description("Test agent")
            .with_mode("subagent")
            .with_permission([])
            .with_workflow_fsm(workflow_fsm)
            .build()
        )

        assert result.is_ok()
        config = result.unwrap()
        assert config.workflow_fsm is workflow_fsm
        assert config.lifecycle_fsm is None  # Not set

    def test_with_default_fsms_creates_and_attaches_both_fsms(self) -> None:
        """Verify with_default_fsms() creates and attaches both lifecycle and workflow FSMs."""
        # Build with default FSMs
        result = (
            AgentBuilder()
            .with_name("test-agent")
            .with_description("Test agent")
            .with_mode("subagent")
            .with_permission([])
            .with_default_fsms()
            .build()
        )

        assert result.is_ok()
        config = result.unwrap()
        assert config.lifecycle_fsm is not None
        assert config.workflow_fsm is not None

        # Verify FSMs are valid (can get initial state)
        import asyncio

        async def verify_fsms() -> None:
            lifecycle_state = await config.lifecycle_fsm.get_state()
            workflow_state = await config.workflow_fsm.get_state()
            assert lifecycle_state == "idle"
            assert workflow_state == "intake"

        asyncio.run(verify_fsms())

    def test_fsm_methods_support_chaining(self) -> None:
        """Verify FSM methods return self for method chaining."""
        from dawn_kestrel.agents.agent_lifecycle_fsm import create_lifecycle_fsm
        from dawn_kestrel.agents.agent_workflow_fsm import create_workflow_fsm

        fsm_result1 = create_lifecycle_fsm()
        fsm_result2 = create_workflow_fsm()
        assert fsm_result1.is_ok()
        assert fsm_result2.is_ok()

        lifecycle_fsm = fsm_result1.unwrap()
        workflow_fsm = fsm_result2.unwrap()

        builder = (
            AgentBuilder()
            .with_name("test-agent")
            .with_description("Test agent")
            .with_mode("subagent")
            .with_permission([])
            .with_lifecycle_fsm(lifecycle_fsm)
            .with_workflow_fsm(workflow_fsm)
        )

        # Verify chaining works - each method returns the same builder
        assert isinstance(builder, AgentBuilder)

    def test_build_returns_agent_config_with_fsms_attached(self) -> None:
        """Verify build() returns AgentConfig with FSMs attached."""
        from dawn_kestrel.agents.agent_lifecycle_fsm import create_lifecycle_fsm
        from dawn_kestrel.agents.agent_workflow_fsm import create_workflow_fsm

        fsm_result1 = create_lifecycle_fsm()
        fsm_result2 = create_workflow_fsm()
        assert fsm_result1.is_ok()
        assert fsm_result2.is_ok()

        lifecycle_fsm = fsm_result1.unwrap()
        workflow_fsm = fsm_result2.unwrap()

        result = (
            AgentBuilder()
            .with_name("test-agent")
            .with_description("Test agent")
            .with_mode("subagent")
            .with_permission([])
            .with_lifecycle_fsm(lifecycle_fsm)
            .with_workflow_fsm(workflow_fsm)
            .build()
        )

        assert result.is_ok()
        config = result.unwrap()
        assert isinstance(config, AgentConfig)
        assert config.lifecycle_fsm is lifecycle_fsm
        assert config.workflow_fsm is workflow_fsm
