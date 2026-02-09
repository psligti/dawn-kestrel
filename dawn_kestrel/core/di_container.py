"""
Dependency Injection Container for Dawn Kestrel.

This module provides a centralized DI container using the dependency-injector library
to manage service instantiation and wiring. All services are lazily initialized and
configured through factory functions.

Services:
    - storage: SessionStorage for session persistence
    - service: DefaultSessionService for session management
    - provider_registry: ProviderRegistry for AI provider configuration
    - agent_runtime: AgentRuntime for agent execution
    - session_lifecycle: SessionLifecycle for event management

Example:
    >>> from dawn_kestrel.core.di_container import container
    >>> storage = container.storage()
    >>> service = container.service()
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Any

from dependency_injector import containers, providers

from dawn_kestrel.storage.store import SessionStorage
from dawn_kestrel.core.services.session_service import DefaultSessionService
from dawn_kestrel.providers.registry import ProviderRegistry, create_provider_registry
from dawn_kestrel.agents.runtime import AgentRuntime, create_agent_runtime
from dawn_kestrel.agents.registry import AgentRegistry, create_agent_registry
from dawn_kestrel.core.session_lifecycle import SessionLifecycle, create_session_lifecycle
from dawn_kestrel.core.settings import settings


class Container(containers.DeclarativeContainer):
    """
    Dependency Injection Container for Dawn Kestrel services.

    This container manages the lifecycle and wiring of all core services.
    All services use lazy initialization for optimal performance.
    """

    # Configuration
    config = providers.Configuration()

    # Storage directory
    storage_dir = providers.Factory(
        lambda: container.config.storage_path() or settings.storage_dir_path(),
    )

    # Project directory
    project_dir = providers.Factory(
        lambda: container.config.project_dir() or Path.cwd(),
    )

    # SessionStorage - lazily initialized
    storage = providers.Factory(
        SessionStorage,
        base_dir=storage_dir,
    )

    # SessionLifecycle - singleton, no dependencies
    session_lifecycle = providers.Singleton(
        SessionLifecycle,
    )

    # DefaultSessionService - depends on storage and project_dir
    service = providers.Factory(
        DefaultSessionService,
        storage=storage,
        project_dir=project_dir,
        io_handler=providers.Factory(lambda: container.config.io_handler()),
        progress_handler=providers.Factory(lambda: container.config.progress_handler()),
        notification_handler=providers.Factory(lambda: container.config.notification_handler()),
    )

    # AgentRegistry - lazily initialized
    agent_registry = providers.Factory(
        create_agent_registry,
        persistence_enabled=providers.Factory(
            lambda: container.config.agent_registry_persistence_enabled()
        ),
        storage_dir=storage_dir,
    )

    # ProviderRegistry - lazily initialized
    provider_registry = providers.Factory(
        create_provider_registry,
        storage_dir=storage_dir,
    )

    # AgentRuntime - depends on agent_registry, project_dir, session_lifecycle
    agent_runtime = providers.Factory(
        create_agent_runtime,
        agent_registry=agent_registry,
        base_dir=project_dir,
        skill_max_char_budget=providers.Factory(lambda: container.config.skill_max_char_budget()),
        session_lifecycle=session_lifecycle,
    )

    # Lifecycle registration - ensure provider_registry knows about session_lifecycle
    @staticmethod
    def register_lifecycle(container: Container) -> None:
        """
        Register session_lifecycle with provider_registry.

        This must be called after the container is initialized to ensure
        the provider_registry can emit lifecycle events.

        Args:
            container: The Container instance
        """
        lifecycle = container.session_lifecycle()
        registry = container.provider_registry()
        registry.register_lifecycle(lifecycle)


# Global container instance
# Note: Using __new__ to get a fresh container instance
def _create_container() -> Container:
    return Container()


container = _create_container()


def configure_container(
    storage_path: Optional[Path] = None,
    project_dir: Optional[Path] = None,
    io_handler: Optional[Any] = None,
    progress_handler: Optional[Any] = None,
    notification_handler: Optional[Any] = None,
    agent_registry_persistence_enabled: bool = False,
    skill_max_char_budget: Optional[int] = None,
) -> Container:
    """
    Configure the global DI container with runtime values.

    This function sets up the container configuration and registers
    the lifecycle hooks. Call this before accessing services from the container.

    Args:
        storage_path: Optional custom storage directory path
        project_dir: Optional custom project directory path
        io_handler: Optional I/O handler for user interaction
        progress_handler: Optional progress handler for operations
        notification_handler: Optional notification handler for feedback
        agent_registry_persistence_enabled: Enable agent registry persistence
        skill_max_char_budget: Optional max character budget for skills

    Returns:
        Configured Container instance

    Example:
        >>> from dawn_kestrel.core.di_container import configure_container
        >>> container = configure_container(
        ...     storage_path=Path("/tmp/storage"),
        ...     project_dir=Path("/my/project"),
        ... )
    """
    container.config.set("storage_path", storage_path)
    container.config.set("project_dir", project_dir)
    container.config.set("io_handler", io_handler)
    container.config.set("progress_handler", progress_handler)
    container.config.set("notification_handler", notification_handler)
    container.config.set("agent_registry_persistence_enabled", agent_registry_persistence_enabled)
    container.config.set("skill_max_char_budget", skill_max_char_budget)

    # Register lifecycle hooks
    Container.register_lifecycle(container)

    return container


def reset_container() -> None:
    """
    Reset the global container to its initial state.

    This is primarily useful for testing to ensure clean state between tests.
    After calling this, you must reconfigure the container before using it.

    Warning:
        Do not call this in production code as it will invalidate all
        existing service instances.
    """
    container.config.set("storage_path", None)
    container.config.set("project_dir", None)
    container.config.set("io_handler", None)
    container.config.set("progress_handler", None)
    container.config.set("notification_handler", None)
    container.config.set("agent_registry_persistence_enabled", False)
    container.config.set("skill_max_char_budget", None)
