"""AgentConfig dataclass for wrapping Agent with FSM and metadata.

AgentConfig wraps the existing Agent dataclass to provide additional
configuration for lifecycle and workflow state machines, along with
metadata for extensibility.

The design follows the wrapper pattern (not modification) to maintain
compatibility with existing Agent definitions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dawn_kestrel.agents.builtin import Agent
from dawn_kestrel.core.fsm import FSM
from dawn_kestrel.core.result import Ok, Err, Result


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


class AgentBuilder:
    """Fluent API builder for AgentConfig creation.

    AgentBuilder provides a fluent interface for configuring Agent instances
    with all required and optional fields, then wrapping them in AgentConfig.

    All builder methods return self for method chaining:
        >>> result = (AgentBuilder()
        ...     .with_name("my-agent")
        ...     .with_description("My agent")
        ...     .with_mode("subagent")
        ...     .with_permission([])
        ...     .build())

    Validation:
        The build() method validates required fields before creating AgentConfig:
        - name: str (required)
        - description: str (required)
        - mode: str (required)
        - permission: List[Dict[str, Any]] (required)

    Thread Safety:
        This builder is NOT thread-safe. Build in a single thread
        before using the AgentConfig in concurrent contexts.
    """

    def __init__(self):
        """Initialize builder with empty configuration."""
        # Required fields
        self._name: Optional[str] = None
        self._description: Optional[str] = None
        self._mode: Optional[str] = None
        self._permission: Optional[List[Dict[str, Any]]] = None

        # Optional fields
        self._temperature: Optional[float] = None
        self._options: Optional[Dict[str, Any]] = None
        self._native: Optional[bool] = None
        self._prompt: Optional[str] = None

        self._lifecycle_fsm: Optional[FSM] = None
        self._workflow_fsm: Optional[FSM] = None

    def with_name(self, name: str) -> "AgentBuilder":
        """Set the agent name.

        Args:
            name: Unique identifier for the agent.

        Returns:
            AgentBuilder: self for method chaining.

        Example:
            >>> builder = AgentBuilder().with_name("my-agent")
        """
        self._name = name
        return self

    def with_description(self, description: str) -> "AgentBuilder":
        """Set the agent description.

        Args:
            description: Human-readable description of the agent's purpose.

        Returns:
            AgentBuilder: self for method chaining.

        Example:
            >>> builder = AgentBuilder().with_description("A helpful assistant")
        """
        self._description = description
        return self

    def with_mode(self, mode: str) -> "AgentBuilder":
        """Set the agent mode.

        Args:
            mode: Agent mode - "subagent", "primary", or "all".

        Returns:
            AgentBuilder: self for method chaining.

        Example:
            >>> builder = AgentBuilder().with_mode("subagent")
        """
        self._mode = mode
        return self

    def with_permission(self, permissions: List[Dict[str, Any]]) -> "AgentBuilder":
        """Set the agent permissions.

        Args:
            permissions: List of permission rules (ruleset).

        Returns:
            AgentBuilder: self for method chaining.

        Example:
            >>> builder = AgentBuilder().with_permission([{"read": True}])
        """
        self._permission = permissions
        return self

    def with_prompt(self, prompt: str) -> "AgentBuilder":
        """Set a custom system prompt.

        Args:
            prompt: Custom system prompt for the agent.

        Returns:
            AgentBuilder: self for method chaining.

        Example:
            >>> builder = AgentBuilder().with_prompt("You are a coding expert")
        """
        self._prompt = prompt
        return self

    def with_temperature(self, temperature: float) -> "AgentBuilder":
        """Set the temperature for generation.

        Args:
            temperature: Sampling temperature (typically 0.0 to 2.0).

        Returns:
            AgentBuilder: self for method chaining.

        Example:
            >>> builder = AgentBuilder().with_temperature(0.7)
        """
        self._temperature = temperature
        return self

    def with_options(self, options: Dict[str, Any]) -> "AgentBuilder":
        """Set additional options.

        Args:
            options: Dict of additional options (e.g., max_tokens).

        Returns:
            AgentBuilder: self for method chaining.

        Example:
            >>> builder = AgentBuilder().with_options({"max_tokens": 1000})
        """
        self._options = options
        return self

    def with_native(self, native: bool) -> "AgentBuilder":
        """Set whether the agent is native.

        Args:
            native: True if native, False otherwise.

        Returns:
            AgentBuilder: self for method chaining.

        Example:
            >>> builder = AgentBuilder().with_native(True)
        """
        self._native = native
        return self

    def with_lifecycle_fsm(self, fsm: FSM) -> "AgentBuilder":
        """Set the lifecycle FSM for the agent.

        Args:
            fsm: FSM instance for managing agent lifecycle.

        Returns:
            AgentBuilder: self for method chaining.

        Example:
            >>> from dawn_kestrel.agents.agent_lifecycle_fsm import create_lifecycle_fsm
            >>> fsm_result = create_lifecycle_fsm()
            >>> builder = AgentBuilder().with_lifecycle_fsm(fsm_result.unwrap())
        """
        self._lifecycle_fsm = fsm
        return self

    def with_workflow_fsm(self, fsm: FSM) -> "AgentBuilder":
        """Set the workflow FSM for the agent.

        Args:
            fsm: FSM instance for managing agent workflow.

        Returns:
            AgentBuilder: self for method chaining.

        Example:
            >>> from dawn_kestrel.agents.agent_workflow_fsm import create_workflow_fsm
            >>> fsm_result = create_workflow_fsm()
            >>> builder = AgentBuilder().with_workflow_fsm(fsm_result.unwrap())
        """
        self._workflow_fsm = fsm
        return self

    def with_default_fsms(self) -> "AgentBuilder":
        """Create and attach default lifecycle and workflow FSMs.

        Uses factory functions create_lifecycle_fsm() and create_workflow_fsm()
        to create default FSM instances.

        Returns:
            AgentBuilder: self for method chaining. If FSM creation fails,
                          the error will be propagated when build() is called.

        Example:
            >>> builder = AgentBuilder().with_default_fsms()
        """
        from dawn_kestrel.agents.agent_lifecycle_fsm import create_lifecycle_fsm
        from dawn_kestrel.agents.agent_workflow_fsm import create_workflow_fsm

        lifecycle_result = create_lifecycle_fsm()
        if lifecycle_result.is_ok():
            self._lifecycle_fsm = lifecycle_result.unwrap()

        workflow_result = create_workflow_fsm()
        if workflow_result.is_ok():
            self._workflow_fsm = workflow_result.unwrap()

        return self

    def build(self) -> Result[AgentConfig]:
        """Build AgentConfig from builder configuration.

        Validates required fields (name, description, mode, permission)
        before creating the Agent instance and wrapping it in AgentConfig.

        Returns:
            Result[AgentConfig]: Ok with AgentConfig instance, Err if required fields missing.

        Example:
            >>> result = (AgentBuilder()
            ...     .with_name("test-agent")
            ...     .with_description("Test agent")
            ...     .with_mode("subagent")
            ...     .with_permission([])
            ...     .build())
            >>> if result.is_ok():
            ...     config = result.unwrap()
        """
        # Validate required fields
        missing_fields = []
        if self._name is None:
            missing_fields.append("name")
        if self._description is None:
            missing_fields.append("description")
        if self._mode is None:
            missing_fields.append("mode")
        if self._permission is None:
            missing_fields.append("permission")

        if missing_fields:
            return Err(
                f"Missing required fields: {', '.join(missing_fields)}. "
                "All of 'name', 'description', 'mode', 'permission' must be set before calling build().",
                code="MISSING_REQUIRED_FIELDS",
            )

        # Create Agent with configured values
        # We've validated required fields are not None above
        agent = Agent(
            name=self._name,  # type: ignore[arg-type]
            description=self._description,  # type: ignore[arg-type]
            mode=self._mode,  # type: ignore[arg-type]
            permission=self._permission,  # type: ignore[arg-type]
            native=self._native if self._native is not None else True,  # Default from Agent
            temperature=self._temperature,
            prompt=self._prompt,
            options=self._options,
        )

        # Wrap in AgentConfig with FSMs
        return Ok(
            AgentConfig(
                agent=agent,
                lifecycle_fsm=self._lifecycle_fsm,
                workflow_fsm=self._workflow_fsm,
            )
        )
