"""Tests for AgentConfig dataclass."""

from typing import Optional

import pytest
from dawn_kestrel.agents.builtin import Agent
from dawn_kestrel.agents.agent_config import AgentConfig
from dawn_kestrel.core.fsm import FSM, FSMContext
from dawn_kestrel.core.result import Ok


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
