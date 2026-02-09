"""SDK clients for OpenCode Python

This module provides async and sync client implementations
that wrap SessionService with handler injection and callbacks.
"""

from __future__ import annotations

from typing import Optional, Callable, Any, Dict, cast
from pathlib import Path
import asyncio

from dawn_kestrel.core.config import SDKConfig
from dawn_kestrel.core.services.session_service import DefaultSessionService
from dawn_kestrel.storage.store import SessionStorage
from dawn_kestrel.core.models import Session
from dawn_kestrel.interfaces.io import Notification
from dawn_kestrel.core.exceptions import OpenCodeError, SessionError
from dawn_kestrel.core.settings import settings
from dawn_kestrel.agents.runtime import create_agent_runtime
from dawn_kestrel.core.agent_types import AgentResult, SessionManagerLike
from dawn_kestrel.agents.registry import create_agent_registry
from dawn_kestrel.tools import create_builtin_registry
from dawn_kestrel.providers.registry import create_provider_registry
from dawn_kestrel.core.provider_config import ProviderConfig
from dawn_kestrel.core.session_lifecycle import SessionLifecycle


class OpenCodeAsyncClient:
    """Async client for OpenCode SDK with handler injection.

    This client provides async methods for session and message operations,
    using injected handlers for I/O, progress, and notifications.

    Attributes:
        config: SDKConfig instance for client configuration.
        _service: SessionService instance for core operations.
        _runtime: AgentRuntime instance for agent execution.
        _provider_registry: ProviderRegistry instance for provider management.
        _lifecycle: SessionLifecycle instance for lifecycle events.
        _on_progress: Optional callback for progress updates.
        _on_notification: Optional callback for notifications.
    """

    def __init__(
        self,
        config: Optional[SDKConfig] = None,
        io_handler: Optional[Any] = None,
        progress_handler: Optional[Any] = None,
        notification_handler: Optional[Any] = None,
    ):
        """Initialize async SDK client.

        Args:
            config: Optional SDKConfig for configuration.
            io_handler: Optional I/O handler for user interaction.
            progress_handler: Optional progress handler for operations.
            notification_handler: Optional notification handler for feedback.
        """
        self.config = config or SDKConfig()
        self._on_progress: Optional[Callable[[int, Optional[str]], None]] = None
        self._on_notification: Optional[Callable[[Notification], None]] = None

        storage_dir = self.config.storage_path or settings.storage_dir_path()
        storage = SessionStorage(storage_dir)
        project_dir = self.config.project_dir or Path.cwd()

        self._service = DefaultSessionService(
            storage=storage,
            project_dir=project_dir,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        self._provider_registry = create_provider_registry(storage_dir)
        self._lifecycle = SessionLifecycle()

        agent_registry = create_agent_registry(
            persistence_enabled=False,
            storage_dir=storage_dir,
        )
        self._runtime = create_agent_runtime(
            agent_registry=agent_registry,
            base_dir=project_dir,
            session_lifecycle=self._lifecycle,
        )

        self._provider_registry.register_lifecycle(self._lifecycle)

    def on_progress(self, callback: Optional[Callable[[int, Optional[str]], None]]) -> None:
        """Register progress callback.

        Args:
            callback: Callback function called with (current, message) during operations.
        """
        self._on_progress = callback

    def on_notification(self, callback: Optional[Callable[[Notification], None]]) -> None:
        """Register notification callback.

        Args:
            callback: Callback function called with Notification when events occur.
        """
        self._on_notification = callback

    async def create_session(
        self,
        title: str,
        version: str = "1.0.0",
    ) -> Session:
        """Create a new session.

        Args:
            title: Session title.
            version: Session version.

        Returns:
            Created Session object.

        Raises:
            SessionError: If session creation fails.
        """
        try:
            session = await self._service.create_session(title)
            return session
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to create session: {e}") from e

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.

        Args:
            session_id: Session ID to retrieve.

        Returns:
            Session object or None if not found.

        Raises:
            SessionError: If retrieval fails.
        """
        try:
            session = await self._service.get_session(session_id)
            return session
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to get session: {e}") from e

    async def list_sessions(self) -> list[Session]:
        """List all sessions.

        Returns:
            List of Session objects.

        Raises:
            SessionError: If listing fails.
        """
        try:
            sessions = await self._service.list_sessions()
            return sessions
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to list sessions: {e}") from e

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: Session ID to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            SessionError: If deletion fails.
        """
        try:
            deleted = await self._service.delete_session(session_id)
            return deleted
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to delete session: {e}") from e

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> str:
        """Add a message to a session.

        Args:
            session_id: Session ID.
            role: Message role (user, assistant, system).
            content: Message content.

        Returns:
            Created message ID.

        Raises:
            SessionError: If adding message fails.
        """
        try:
            message_id = await self._service.add_message(session_id, role, content)
            return message_id
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to add message: {e}") from e

    async def register_agent(self, agent: Any) -> Any:
        """Register a custom agent.

        Args:
            agent: Agent to register (Agent dataclass or dict with name, description, etc.)

        Returns:
            Registered agent

        Raises:
            ValueError: If agent with same name already exists
            SessionError: If registration fails

        Example:
            >>> custom_agent = Agent(
            ...     name="reviewer",
            ...     description="Code review agent",
            ...     mode="subagent",
            ...     permission=[{"permission": "*", "pattern": "*", "action": "allow"}]
            ... )
            >>> await client.register_agent(custom_agent)
        """
        try:
            return await self._runtime.agent_registry.register_agent(agent)
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise SessionError(f"Failed to register agent: {e}") from e

    async def get_agent(self, name: str) -> Optional[Any]:
        """Get an agent by name.

        Args:
            name: Agent name (case-insensitive)

        Returns:
            Agent if found, None otherwise

        Example:
            >>> agent = await client.get_agent("build")
            >>> if agent:
            ...     print(f"Found: {agent.description}")
        """
        try:
            return self._runtime.agent_registry.get_agent(name)
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise SessionError(f"Failed to get agent: {e}") from e

    async def execute_agent(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
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
            AgentResult with response text, parts, metadata, tools used, duration, error

        Raises:
            ValueError: If agent not found, session not found, or missing required data
            SessionError: If execution fails

        Example:
            >>> result = await client.execute_agent(
            ...     agent_name="build",
            ...     session_id="ses_123",
            ...     user_message="Create a new user model"
            ... )
            >>> print(f"Response: {result.response}")
            >>> print(f"Tools used: {result.tools_used}")
        """
        options = options or {}

        skills = options.get("skills", [])
        tools = create_builtin_registry()

        try:
            return await self._runtime.execute_agent(
                agent_name=agent_name,
                session_id=session_id,
                user_message=user_message,
                session_manager=cast(SessionManagerLike, self._service),
                tools=tools,
                skills=skills,
                options=options,
            )
        except ValueError:
            raise
        except Exception as e:
            raise SessionError(f"Failed to execute agent: {e}") from e

    async def register_provider(
        self,
        name: str,
        provider_id: str,
        model: str,
        api_key: Optional[str] = None,
        is_default: bool = False,
    ) -> ProviderConfig:
        """Register a provider configuration.

        Args:
            name: Name for this provider configuration
            provider_id: Provider ID (e.g., "anthropic", "openai")
            model: Model ID to use
            api_key: API key for the provider (optional)
            is_default: Whether to set as default provider

        Returns:
            Registered ProviderConfig

        Raises:
            ValueError: If provider with same name already exists
            SessionError: If registration fails

        Example:
            >>> await client.register_provider(
            ...     name="my-anthropic",
            ...     provider_id="anthropic",
            ...     model="claude-sonnet-4-20250514"
            ... )
        """
        try:
            config = ProviderConfig(
                provider_id=provider_id,
                model=model,
                api_key=api_key,
                is_default=is_default,
            )
            return await self._provider_registry.register_provider(name, config, is_default)
        except ValueError:
            raise
        except Exception as e:
            raise SessionError(f"Failed to register provider: {e}") from e

    async def get_provider(self, name: str) -> Optional[ProviderConfig]:
        """Get a provider configuration by name.

        Args:
            name: Provider name

        Returns:
            ProviderConfig or None if not found

        Example:
            >>> provider = await client.get_provider("my-anthropic")
            >>> if provider:
            ...     print(f"Model: {provider.model}")
        """
        return await self._provider_registry.get_provider(name)

    async def list_providers(self) -> list[Dict[str, Any]]:
        """List all provider configurations.

        Returns:
            List of provider configuration dictionaries

        Example:
            >>> providers = await client.list_providers()
            >>> for p in providers:
            ...     print(f"{p['name']}: {p['config']['model']}")
        """
        return await self._provider_registry.list_providers()

    async def remove_provider(self, name: str) -> bool:
        """Remove a provider configuration.

        Args:
            name: Provider name

        Returns:
            True if removed, False if not found

        Raises:
            SessionError: If removal fails

        Example:
            >>> removed = await client.remove_provider("my-anthropic")
            >>> print(f"Removed: {removed}")
        """
        try:
            return await self._provider_registry.remove_provider(name)
        except Exception as e:
            raise SessionError(f"Failed to remove provider: {e}") from e

    async def update_provider(
        self,
        name: str,
        provider_id: str,
        model: str,
        api_key: Optional[str] = None,
    ) -> ProviderConfig:
        """Update an existing provider configuration.

        Args:
            name: Provider name
            provider_id: New provider ID
            model: New model ID
            api_key: New API key (optional)

        Returns:
            Updated ProviderConfig

        Raises:
            ValueError: If provider not found
            SessionError: If update fails

        Example:
            >>> await client.update_provider(
            ...     name="my-anthropic",
            ...     model="claude-sonnet-4-20250514"
            ... )
        """
        try:
            config = ProviderConfig(
                provider_id=provider_id,
                model=model,
                api_key=api_key,
            )
            return await self._provider_registry.update_provider(name, config)
        except ValueError:
            raise
        except Exception as e:
            raise SessionError(f"Failed to update provider: {e}") from e

    def on_session_created(self, callback: Any) -> None:
        """Register callback for session creation events.

        Args:
            callback: Function called with session data when session is created

        Example:
            >>> def on_created(data):
            ...     print(f"Session created: {data['id']}")
            >>> client.on_session_created(on_created)
        """
        self._lifecycle.on_session_created(callback)

    def on_session_updated(self, callback: Any) -> None:
        """Register callback for session update events.

        Args:
            callback: Function called with session data when session is updated

        Example:
            >>> def on_updated(data):
            ...     print(f"Session updated: {data['id']}")
            >>> client.on_session_updated(on_updated)
        """
        self._lifecycle.on_session_updated(callback)

    def on_message_added(self, callback: Any) -> None:
        """Register callback for message addition events.

        Args:
            callback: Function called with message data when message is added

        Example:
            >>> def on_message(data):
            ...     print(f"Message added: {data['role']}")
            >>> client.on_message_added(on_message)
        """
        self._lifecycle.on_message_added(callback)

    def on_session_archived(self, callback: Any) -> None:
        """Register callback for session archive events.

        Args:
            callback: Function called with session data when session is archived

        Example:
            >>> def on_archived(data):
            ...     print(f"Session archived: {data['id']}")
            >>> client.on_session_archived(on_archived)
        """
        self._lifecycle.on_session_archived(callback)


class OpenCodeSyncClient:
    """Sync client for OpenCode SDK.

    This client provides sync methods that wrap async client operations.
    Trade-off: Simpler API for synchronous code, but blocks event loop.

    Attributes:
        _async_client: OpenCodeAsyncClient instance for actual operations.
    """

    def __init__(
        self,
        config: Optional[SDKConfig] = None,
        io_handler: Optional[Any] = None,
        progress_handler: Optional[Any] = None,
        notification_handler: Optional[Any] = None,
    ):
        """Initialize sync SDK client.

        Args:
            config: Optional SDKConfig for configuration.
            io_handler: Optional I/O handler for user interaction.
            progress_handler: Optional progress handler for operations.
            notification_handler: Optional notification handler for feedback.

        Note:
            This client runs async operations synchronously using asyncio.run().
            Consider using OpenCodeAsyncClient for async codebases.
        """
        self._async_client = OpenCodeAsyncClient(
            config=config,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

    def on_progress(self, callback: Optional[Callable[[int, Optional[str]], None]]) -> None:
        """Register progress callback.

        Args:
            callback: Callback function called with (current, message) during operations.
        """
        self._async_client.on_progress(callback)

    def on_notification(self, callback: Optional[Callable[[Notification], None]]) -> None:
        """Register notification callback.

        Args:
            callback: Callback function called with Notification when events occur.
        """
        self._async_client.on_notification(callback)

    def create_session(self, title: str, version: str = "1.0.0") -> Session:
        """Create a new session (sync).

        Args:
            title: Session title.
            version: Session version.

        Returns:
            Created Session object.

        Raises:
            SessionError: If session creation fails.

        Note:
            Blocks event loop. Consider async client for non-blocking operations.
        """
        return asyncio.run(self._async_client.create_session(title, version))

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID (sync).

        Args:
            session_id: Session ID to retrieve.

        Returns:
            Session object or None if not found.

        Raises:
            SessionError: If retrieval fails.

        Note:
            Blocks event loop. Consider async client for non-blocking operations.
        """
        return asyncio.run(self._async_client.get_session(session_id))

    def list_sessions(self) -> list[Session]:
        """List all sessions (sync).

        Returns:
            List of Session objects.

        Raises:
            SessionError: If listing fails.

        Note:
            Blocks event loop. Consider async client for non-blocking operations.
        """
        return asyncio.run(self._async_client.list_sessions())

    def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID (sync).

        Args:
            session_id: Session ID to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            SessionError: If deletion fails.

        Note:
            Blocks event loop. Consider async client for non-blocking operations.
        """
        return asyncio.run(self._async_client.delete_session(session_id))

    def add_message(self, session_id: str, role: str, content: str) -> str:
        """Add a message to a session (sync).

        Args:
            session_id: Session ID.
            role: Message role (user, assistant, system).
            content: Message content.

        Returns:
            Created message ID.

        Raises:
            SessionError: If adding message fails.

        Note:
            Blocks event loop. Consider async client for non-blocking operations.
        """
        return asyncio.run(self._async_client.add_message(session_id, role, content))

    def register_agent(self, agent: Any) -> Any:
        """Register a custom agent (sync)."""
        return asyncio.run(self._async_client.register_agent(agent))

    def get_agent(self, name: str) -> Optional[Any]:
        """Get an agent by name (sync)."""
        return asyncio.run(self._async_client.get_agent(name))

    def execute_agent(
        self,
        agent_name: str,
        session_id: str,
        user_message: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Execute an agent for a user message (sync)."""
        return asyncio.run(
            self._async_client.execute_agent(agent_name, session_id, user_message, options)
        )

    def register_provider(
        self,
        name: str,
        provider_id: str,
        model: str,
        api_key: Optional[str] = None,
        is_default: bool = False,
    ) -> ProviderConfig:
        """Register a provider configuration (sync)."""
        return asyncio.run(
            self._async_client.register_provider(name, provider_id, model, api_key, is_default)
        )

    def get_provider(self, name: str) -> Optional[ProviderConfig]:
        """Get a provider configuration by name (sync)."""
        return asyncio.run(self._async_client.get_provider(name))

    def list_providers(self) -> list[Dict[str, Any]]:
        """List all provider configurations (sync)."""
        return asyncio.run(self._async_client.list_providers())

    def remove_provider(self, name: str) -> bool:
        """Remove a provider configuration (sync)."""
        return asyncio.run(self._async_client.remove_provider(name))

    def update_provider(
        self,
        name: str,
        provider_id: str,
        model: str,
        api_key: Optional[str] = None,
    ) -> ProviderConfig:
        """Update an existing provider configuration (sync)."""
        return asyncio.run(self._async_client.update_provider(name, provider_id, model, api_key))

    def on_session_created(self, callback: Any) -> None:
        """Register callback for session creation events (sync)."""
        self._async_client.on_session_created(callback)

    def on_session_updated(self, callback: Any) -> None:
        """Register callback for session update events (sync)."""
        self._async_client.on_session_updated(callback)

    def on_message_added(self, callback: Any) -> None:
        """Register callback for message addition events (sync)."""
        self._async_client.on_message_added(callback)

    def on_session_archived(self, callback: Any) -> None:
        """Register callback for session archive events (sync)."""
        self._async_client.on_session_archived(callback)
