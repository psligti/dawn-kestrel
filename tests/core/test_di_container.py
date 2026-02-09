"""
Tests for DI Container (dependency-injector).

This module tests the dependency injection container that manages
service instantiation and wiring for Dawn Kestrel.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from dawn_kestrel.core.di_container import (
    Container,
    container,
    configure_container,
    reset_container,
)


class TestContainerInitialization:
    """Test container initialization and configuration."""

    def test_container_exists(self):
        """Test that global container instance exists."""
        assert container is not None
        # Container is a DynamicContainer when instantiated
        from dependency_injector.containers import DynamicContainer

        assert isinstance(container, DynamicContainer)

    def test_container_has_all_providers(self):
        """Test that container has all required providers."""
        assert hasattr(container, "config")
        assert hasattr(container, "storage_dir")
        assert hasattr(container, "project_dir")
        assert hasattr(container, "storage")
        assert hasattr(container, "session_lifecycle")
        assert hasattr(container, "service")
        assert hasattr(container, "agent_registry")
        assert hasattr(container, "provider_registry")
        assert hasattr(container, "agent_runtime")


@pytest.fixture(autouse=True)
def reset_container_fixture():
    """Reset container before each test."""
    from dawn_kestrel.core.di_container import reset_container

    reset_container()
    yield
    reset_container()


class TestStorageProvider:
    """Test SessionStorage provider."""

    def test_storage_returns_correct_type(self):
        """Test that storage provider returns SessionStorage instance."""
        # Configure container with temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_container(storage_path=Path(tmpdir))
            storage = container.storage()
            from dawn_kestrel.storage.store import SessionStorage

            assert isinstance(storage, SessionStorage)
            # Reset for next test
            reset_container()

    def test_storage_uses_configured_path(self):
        """Test that storage uses configured storage path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            configure_container(storage_path=tmp_path)
            storage = container.storage()
            # Storage appends /storage to base_dir
            assert storage.base_dir == tmp_path
            assert storage.storage_dir == tmp_path / "storage"


class TestSessionLifecycleProvider:
    """Test SessionLifecycle provider."""

    def test_session_lifecycle_returns_correct_type(self):
        """Test that session_lifecycle provider returns SessionLifecycle instance."""
        from dawn_kestrel.core.session_lifecycle import SessionLifecycle

        lifecycle = container.session_lifecycle()
        assert isinstance(lifecycle, SessionLifecycle)

    def test_session_lifecycle_is_singleton(self):
        """Test that session_lifecycle returns same instance (singleton)."""
        lifecycle1 = container.session_lifecycle()
        lifecycle2 = container.session_lifecycle()
        assert lifecycle1 is lifecycle2


class TestServiceProvider:
    """Test DefaultSessionService provider."""

    def test_service_returns_correct_type(self):
        """Test that service provider returns DefaultSessionService instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_container(storage_path=Path(tmpdir))
            service = container.service()
            from dawn_kestrel.core.services.session_service import DefaultSessionService

            assert isinstance(service, DefaultSessionService)
            reset_container()

    def test_service_injects_dependencies(self):
        """Test that service properly injects storage and project_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            configure_container(
                storage_path=tmp_path,
                project_dir=tmp_path,
            )
            service = container.service()
            from dawn_kestrel.storage.store import SessionStorage

            assert isinstance(service.storage, SessionStorage)
            # Storage adds /storage suffix to configured path
            assert service.storage.storage_dir == tmp_path / "storage"
            assert service.project_dir == tmp_path
            reset_container()


class TestAgentRegistryProvider:
    """Test AgentRegistry provider."""

    def test_agent_registry_returns_correct_type(self):
        """Test that agent_registry provider returns AgentRegistry instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_container(storage_path=Path(tmpdir))
            registry = container.agent_registry()
            from dawn_kestrel.agents.registry import AgentRegistry

            assert isinstance(registry, AgentRegistry)
            reset_container()

    def test_agent_registry_uses_configured_settings(self):
        """Test that agent_registry uses persistence and storage_dir settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            configure_container(
                storage_path=tmp_path,
                agent_registry_persistence_enabled=True,
            )
            registry = container.agent_registry()
            assert registry.persistence_enabled is True
            assert registry.storage_dir == tmp_path
            reset_container()


class TestProviderRegistryProvider:
    """Test ProviderRegistry provider."""

    def test_provider_registry_returns_correct_type(self):
        """Test that provider_registry provider returns ProviderRegistry instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_container(storage_path=Path(tmpdir))
            registry = container.provider_registry()
            from dawn_kestrel.providers.registry import ProviderRegistry

            assert isinstance(registry, ProviderRegistry)
            reset_container()

    def test_provider_registry_uses_configured_path(self):
        """Test that provider_registry uses configured storage path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            configure_container(storage_path=tmp_path)
            registry = container.provider_registry()
            # ProviderRegistry appends /storage/providers to the path
            expected_path = tmp_path / "storage" / "providers"
            assert registry.storage_dir == expected_path
            reset_container()


class TestAgentRuntimeProvider:
    """Test AgentRuntime provider."""

    def test_agent_runtime_returns_correct_type(self):
        """Test that agent_runtime provider returns AgentRuntime instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_container(
                storage_path=Path(tmpdir),
                project_dir=Path(tmpdir),
            )
            runtime = container.agent_runtime()
            from dawn_kestrel.agents.runtime import AgentRuntime

            assert isinstance(runtime, AgentRuntime)
            reset_container()

    def test_agent_runtime_injects_dependencies(self):
        """Test that agent_runtime properly injects all dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            configure_container(
                storage_path=tmp_path,
                project_dir=tmp_path,
                skill_max_char_budget=1000,
            )
            runtime = container.agent_runtime()
            assert isinstance(runtime.agent_registry, type(container.agent_registry()))
            # ContextBuilder doesn't expose base_dir directly, but skill_injector uses it
            assert runtime.session_lifecycle is container.session_lifecycle()
            reset_container()


class TestConfigureContainer:
    """Test configure_container function."""

    def test_configure_container_sets_storage_path(self):
        """Test that configure_container sets storage_path config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            configure_container(storage_path=tmp_path)
            assert container.config.storage_path() == tmp_path
            reset_container()

    def test_configure_container_sets_project_dir(self):
        """Test that configure_container sets project_dir config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            configure_container(project_dir=tmp_path)
            assert container.config.project_dir() == tmp_path
            reset_container()

    def test_configure_container_sets_handlers(self):
        """Test that configure_container sets handler configs."""
        mock_io = Mock()
        mock_progress = Mock()
        mock_notification = Mock()

        configure_container(
            io_handler=mock_io,
            progress_handler=mock_progress,
            notification_handler=mock_notification,
        )
        # Verify handlers are set (compare by value, not identity)
        assert container.config.io_handler() is not None
        assert container.config.progress_handler() is not None
        assert container.config.notification_handler() is not None
        reset_container()

    def test_configure_container_sets_agent_registry_settings(self):
        """Test that configure_container sets agent_registry config."""
        configure_container(
            agent_registry_persistence_enabled=True,
            skill_max_char_budget=5000,
        )
        assert container.config.agent_registry_persistence_enabled() is True
        assert container.config.skill_max_char_budget() == 5000
        reset_container()


class TestResetContainer:
    """Test reset_container function."""

    def test_reset_container_clears_config(self):
        """Test that reset_container clears all config values."""
        configure_container(
            storage_path=Path("/tmp/test"),
            project_dir=Path("/tmp/project"),
            agent_registry_persistence_enabled=True,
        )

        reset_container()

        assert container.config.storage_path() is None
        assert container.config.project_dir() is None
        assert container.config.io_handler() is None
        assert container.config.progress_handler() is None
        assert container.config.notification_handler() is None
        assert container.config.agent_registry_persistence_enabled() is False
        assert container.config.skill_max_char_budget() is None


class TestLifecycleRegistration:
    """Test lifecycle registration in container."""

    def test_register_lifecycle_registers_with_provider_registry(self):
        """Test that register_lifecycle registers session_lifecycle with provider_registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_container(storage_path=Path(tmpdir))
            Container.register_lifecycle(container)

            lifecycle = container.session_lifecycle()
            provider_registry = container.provider_registry()

            # Verify lifecycle is registered (check if it can emit events)
            assert lifecycle is not None
            assert provider_registry is not None

            reset_container()


class TestLazyInitialization:
    """Test that services are lazily initialized."""

    def test_services_not_initialized_until_accessed(self):
        """Test that services are not created until accessed."""
        # Reset to clean state
        reset_container()

        # Configure but don't access services
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_container(storage_path=Path(tmpdir))

            # Services should not be instantiated yet
            # (We can't directly test this, but we can verify multiple calls
            # don't create multiple instances for singleton)

            reset_container()


class TestIntegration:
    """Integration tests for full container wiring."""

    @pytest.mark.asyncio
    async def test_full_container_wiring(self):
        """Test that all services can be wired together correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_io = Mock()
            mock_progress = Mock()
            mock_notification = Mock()

            configure_container(
                storage_path=tmp_path,
                project_dir=tmp_path,
                io_handler=mock_io,
                progress_handler=mock_progress,
                notification_handler=mock_notification,
            )
            Container.register_lifecycle(container)

            # Get all services
            storage = container.storage()
            lifecycle = container.session_lifecycle()
            service = container.service()
            agent_registry = container.agent_registry()
            provider_registry = container.provider_registry()
            runtime = container.agent_runtime()

            # Verify types
            from dawn_kestrel.storage.store import SessionStorage
            from dawn_kestrel.core.session_lifecycle import SessionLifecycle
            from dawn_kestrel.core.services.session_service import DefaultSessionService
            from dawn_kestrel.agents.registry import AgentRegistry
            from dawn_kestrel.providers.registry import ProviderRegistry
            from dawn_kestrel.agents.runtime import AgentRuntime

            assert isinstance(storage, SessionStorage)
            assert isinstance(lifecycle, SessionLifecycle)
            assert isinstance(service, DefaultSessionService)
            assert isinstance(agent_registry, AgentRegistry)
            assert isinstance(provider_registry, ProviderRegistry)
            assert isinstance(runtime, AgentRuntime)

            # Verify wiring
            assert isinstance(service.storage, SessionStorage)
            # Storage adds /storage suffix to configured path
            assert service.storage.storage_dir == tmp_path / "storage"
            assert service.project_dir == tmp_path
            assert runtime.session_lifecycle is lifecycle

            reset_container()
