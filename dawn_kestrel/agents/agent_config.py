"""AgentConfig dataclass for wrapping Agent with FSM and metadata.

AgentConfig wraps the existing Agent dataclass to provide additional
configuration for lifecycle and workflow state machines, along with
metadata for extensibility.

The design follows the wrapper pattern (not modification) to maintain
compatibility with existing Agent definitions.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from dawn_kestrel.agents.builtin import Agent
from dawn_kestrel.core.fsm import FSM


@dataclass
class AgentConfig:
    """Configuration wrapper for Agent with FSM and metadata support.

    AgentConfig wraps an Agent instance to provide:
    - lifecycle_fsm: Optional FSM for agent lifecycle states
    - workflow_fsm: Optional FSM for agent workflow states
    - metadata: Dict for extensible metadata

    This is a wrapper, not a replacement - the original Agent dataclass
    remains unchanged.

    Attributes:
        agent: The Agent instance being wrapped
        lifecycle_fsm: Optional FSM for managing agent lifecycle
        workflow_fsm: Optional FSM for managing agent workflow
        metadata: Dict for extensible metadata (defaults to empty dict)
    """

    agent: Agent
    lifecycle_fsm: Optional[FSM] = None
    workflow_fsm: Optional[FSM] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_agent(cls, agent: Agent) -> "AgentConfig":
        """Create AgentConfig from an existing Agent instance.

        This factory method provides a convenient way to wrap an Agent
        with default configuration (no FSMs, empty metadata).

        Args:
            agent: The Agent instance to wrap

        Returns:
            AgentConfig instance wrapping the agent with defaults

        Example:
            >>> agent = Agent(name="test", description="test agent",
            ...              mode="subagent", permission=[])
            >>> config = AgentConfig.from_agent(agent)
            >>> config.agent is agent
            True
            >>> config.lifecycle_fsm is None
            True
            >>> config.metadata == {}
            True
        """
        return cls(agent=agent)
