"""Facade pattern for composition root simplification.

This module provides a simplified API over complex subsystems including
DI container, repositories, services, and providers. The Facade hides
the complexity of manual dependency wiring and provides a simple interface
for common SDK operations.

Example:
    >>> from dawn_kestrel.core.facade import Facade, FacadeImpl
    >>> from dawn_kestrel.core.di_container import configure_container
    >>>
    >>> # Configure DI container
    >>> container = configure_container()
    >>>
    >>> # Create facade using container
    >>> facade: Facade = FacadeImpl(container)
    >>>
    >>> # Use simplified API
    >>> result = await facade.create_session("My Project")
    >>> if result.is_ok():
    ...     session = result.unwrap()
    ...     print(f"Created session: {session.id}")
"""

from __future__ import annotations

from typing import Protocol, Optional, Dict, Any, cast, runtime_checkable
from abc import abstractmethod

from dawn_kestrel.core.models import Session
from dawn_kestrel.core.agent_types import AgentResult
from dawn_kestrel.core.provider_config import ProviderConfig
from dawn_kestrel.core.result import Result, Ok, Err
from dawn_kestrel.core.di_container import Container
from dawn_kestrel.core.fsm import FSM


@runtime_checkable
class Facade(Protocol):
    """Protocol defining simplified SDK operations facade.

    This protocol defines a simple API over complex subsystems including
    DI container, repositories, services, and providers. Implementations
    should use dependency injection to wire components and provide a
    simplified interface for common operations.
    """

    @abstractmethod
    async def create_session(
        self,
        title: str,
    ) -> Result[Session]:
        """Create a new session.

        Args:
            title: Session title.

        Returns:
            Result with created Session object on success, or Err on failure.
        """

    @abstractmethod
    async def get_session(
        self,
        session_id: str,
    ) -> Result[Session | None]:
        """Get a session by ID.

        Args:
            session_id: Session ID to retrieve.

        Returns:
            Result with Session object or None if not found on success,
            or Err on failure.
        """

    @abstractmethod
    async def list_sessions(self) -> Result[list[Session]]:
        """List all sessions.

        Returns:
            Result with list of Session objects on success, or Err on failure.
        """

    @abstractmethod
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> Result[str]:
        """Add a message to a session.

        Args:
            session_id: Session ID.
            role: Message role (user, assistant, system).
            content: Message content.

        Returns:
            Result with message ID on success, or Err on failure.
        """

    @abstractmethod
    async def execute_agent(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Result[AgentResult]:
        """Execute an agent for a user message.

        Args:
            agent_name: Name of agent to execute (e.g., "build", "plan", "explore")
            session_id: Session ID to execute in
            user_message: User's message or request
            options: Optional execution parameters:
                - skills: List[str] - Skill names to inject into system prompt
                - provider: str - Provider ID ("anthropic", "openai")
                - model: str - Model ID (overrides agent default)

        Returns:
            Result with AgentResult on success, or Err on failure.
        """

    @abstractmethod
    async def register_provider(
        self,
        name: str,
        provider_id: str,
        model: str,
        api_key: Optional[str] = None,
        is_default: bool = False,
    ) -> Result[ProviderConfig]:
        """Register a provider configuration.

        Args:
            name: Name for this provider configuration
            provider_id: Provider ID (e.g., "anthropic", "openai")
            model: Model ID to use
            api_key: API key for provider (optional)
            is_default: Whether to set as default provider

        Returns:
            Result with registered ProviderConfig on success, or Err on failure.
        """

    @abstractmethod
    async def get_fsm_state(self, fsm_id: str) -> Result[str]:
        """Get the current state of an FSM instance.

        Args:
            fsm_id: Unique identifier for the FSM instance.

        Returns:
            Result with current state string on success, or Err on failure.
        """

    @abstractmethod
    async def create_fsm(self, initial_state: str) -> Result[FSM]:
        """Create a new FSM instance with default configuration.

        Args:
            initial_state: Initial state for the FSM.

        Returns:
            Result with FSM instance on success, or Err on failure.
        """


class FacadeImpl:
    """Implementation of Facade using DI container for dependencies.

    This class provides a simplified API over complex subsystems by using
    the DI container to resolve dependencies on-demand. It hides the complexity
    of manual component wiring and provides clean, simple methods for common
    SDK operations.

    The facade uses lazy initialization - services are only created when
    first accessed through the DI container.

    Attributes:
        _container: DI container for dependency resolution.
    """

    def __init__(self, container: Container) -> None:
        """Initialize facade with DI container.

        Args:
            container: DI container instance for dependency resolution.
        """
        self._container = container

    async def create_session(
        self,
        title: str,
    ) -> Result[Session]:
        """Create a new session.

        Args:
            title: Session title.

        Returns:
            Result with created Session object on success, or Err on failure.
        """
        try:
            service = self._container.service()
            result = await service.create_session(title)

            if result.is_err():
                err_result = cast(Any, result)
                return Err(f"Failed to create session: {err_result.error}", code="SessionError")

            return result

        except Exception as e:
            return Err(f"Failed to create session: {e}", code="SessionError")

    async def get_session(
        self,
        session_id: str,
    ) -> Result[Session | None]:
        """Get a session by ID.

        Args:
            session_id: Session ID to retrieve.

        Returns:
            Result with Session object or None if not found on success,
            or Err on failure.
        """
        try:
            service = self._container.service()
            result = await service.get_session(session_id)

            if result.is_err():
                err_result = cast(Any, result)
                # If session not found, return Ok(None) instead of Err
                if err_result.code == "NOT_FOUND":
                    return Ok(None)
                return Err(f"Failed to get session: {err_result.error}", code="SessionError")

            return result

        except Exception as e:
            return Err(f"Failed to get session: {e}", code="SessionError")

    async def list_sessions(self) -> Result[list[Session]]:
        """List all sessions.

        Returns:
            Result with list of Session objects on success, or Err on failure.
        """
        try:
            service = self._container.service()
            result = await service.list_sessions()

            if result.is_err():
                err_result = cast(Any, result)
                return Err(f"Failed to list sessions: {err_result.error}", code="SessionError")

            return result

        except Exception as e:
            return Err(f"Failed to list sessions: {e}", code="SessionError")

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> Result[str]:
        """Add a message to a session.

        Args:
            session_id: Session ID.
            role: Message role (user, assistant, system).
            content: Message content.

        Returns:
            Result with message ID on success, or Err on failure.
        """
        try:
            service = self._container.service()
            result = await service.add_message(session_id, role, content)

            if result.is_err():
                err_result = cast(Any, result)
                return Err(f"Failed to add message: {err_result.error}", code="SessionError")

            return result

        except Exception as e:
            return Err(f"Failed to add message: {e}", code="SessionError")

    async def execute_agent(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Result[AgentResult]:
        """Execute an agent for a user message.

        Args:
            agent_name: Name of agent to execute (e.g., "build", "plan", "explore")
            session_id: Session ID to execute in
            user_message: User's message or request
            options: Optional execution parameters:
                - skills: List[str] - Skill names to inject into system prompt
                - provider: str - Provider ID ("anthropic", "openai")
                - model: str - Model ID (overrides agent default)

        Returns:
            Result with AgentResult on success, or Err on failure.
        """
        try:
            runtime = self._container.agent_runtime()
            service = self._container.service()

            from dawn_kestrel.tools import create_builtin_registry
            from dawn_kestrel.core.agent_types import SessionManagerLike
            from typing import cast

            options = options or {}
            skills = options.get("skills", [])
            tools = create_builtin_registry()

            agent_result = await runtime.execute_agent(
                agent_name=agent_name,
                session_id=session_id,
                user_message=user_message,
                session_manager=cast(SessionManagerLike, service),
                tools=tools,
                skills=skills,
                options=options,
            )

            return Ok(agent_result)

        except ValueError as e:
            return Err(f"Failed to execute agent: {e}", code="ValueError")
        except Exception as e:
            return Err(f"Failed to execute agent: {e}", code="SessionError")

    async def register_provider(
        self,
        name: str,
        provider_id: str,
        model: str,
        api_key: Optional[str] = None,
        is_default: bool = False,
    ) -> Result[ProviderConfig]:
        """Register a provider configuration.

        Args:
            name: Name for this provider configuration
            provider_id: Provider ID (e.g., "anthropic", "openai")
            model: Model ID to use
            api_key: API key for provider (optional)
            is_default: Whether to set as default provider

        Returns:
            Result with registered ProviderConfig on success, or Err on failure.
        """
        try:
            config = ProviderConfig(
                provider_id=provider_id,
                model=model,
                api_key=api_key,
                is_default=is_default,
            )

            registry = self._container.provider_registry()
            provider = await registry.register_provider(name, config, is_default)

            return Ok(provider)

        except ValueError as e:
            return Err(f"Failed to register provider: {e}", code="ValueError")
        except Exception as e:
            return Err(f"Failed to register provider: {e}", code="SessionError")

    async def get_fsm_state(self, fsm_id: str) -> Result[str]:
        """Get the current state of an FSM instance.

        Args:
            fsm_id: Unique identifier for the FSM instance.

        Returns:
            Result with current state string on success, or Err on failure.
        """
        try:
            fsm_repository = self._container.fsm_repository()
            result = await fsm_repository.get_state(fsm_id)

            if result.is_err():
                err_result = cast(Any, result)
                return Err(f"Failed to get FSM state: {err_result.error}", code="FSMError")

            return result

        except Exception as e:
            return Err(f"Failed to get FSM state: {e}", code="FSMError")

    async def create_fsm(self, initial_state: str) -> Result[FSM]:
        """Create a new FSM instance with default configuration.

        Args:
            initial_state: Initial state for the FSM.

        Returns:
            Result with FSM instance on success, or Err on failure.
        """
        try:
            fsm_builder = self._container.fsm_builder()

            # Build FSM with initial state and default empty configuration
            fsm_result = fsm_builder.with_state(initial_state).build(initial_state=initial_state)

            if fsm_result.is_err():
                err_result = cast(Any, fsm_result)
                return Err(f"Failed to create FSM: {err_result.error}", code="FSMError")

            return fsm_result

        except Exception as e:
            return Err(f"Failed to create FSM: {e}", code="FSMError")
