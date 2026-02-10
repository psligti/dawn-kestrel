"""Integration tests for DI container service wiring.

Tests verify that DI container correctly wires all services
and dependencies together without mocking.

Scenario: DI Container End-to-End Wiring
======================================

Preconditions:
- DI container can be configured
- All providers exist
- All services can be instantiated

Steps:
1. Configure container with storage path
2. Get all providers
3. Verify each provider returns correct type
4. Get service
5. Verify service has all dependencies wired
6. Get agent runtime
7. Verify runtime has all dependencies

Expected result:
- All providers return correct types
- Service has session_repo, message_repo, part_repo
- Runtime has agent_registry, session_lifecycle
- No dependencies missing

Failure indicators:
- Provider returns None or wrong type
- Service missing dependencies
- Runtime missing dependencies
- Dependency chain broken

Evidence:
- container.storage() returns SessionStorage
- container.service() has _session_repo
- container.agent_runtime() has agent_registry
"""

import tempfile
from pathlib import Path
import pytest


class TestDIContainerProviders:
    """Test DI container providers return correct types."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def configured_container(self, temp_storage_dir):
        """Configure container with temp storage."""
        from dawn_kestrel.core.di_container import configure_container, reset_container

        reset_container()
        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        from dawn_kestrel.core.di_container import container

        yield container

        reset_container()

    def test_storage_provider_returns_storage(self, configured_container):
        """Scenario: Storage provider returns SessionStorage instance.

        Preconditions:
        - Container configured with storage path

        Steps:
        1. Get container.storage()
        2. Verify type is SessionStorage
        3. Verify base_dir matches configured path

        Expected result:
        - Returns SessionStorage instance
        - base_dir is configured path

        Failure indicators:
        - Returns None
        - Returns wrong type
        - base_dir doesn't match
        """
        from dawn_kestrel.storage.store import SessionStorage

        storage = configured_container.storage()
        assert isinstance(storage, SessionStorage), "Expected SessionStorage instance"
        assert storage.base_dir == configured_container.storage_dir()

    def test_message_storage_provider_returns_storage(self, configured_container):
        """Scenario: Message storage provider returns MessageStorage.

        Preconditions:
        - Container configured

        Steps:
        1. Get container.message_storage()
        2. Verify type is MessageStorage

        Expected result:
        - Returns MessageStorage instance

        Failure indicators:
        - Returns None
        - Returns wrong type
        """
        from dawn_kestrel.storage.store import MessageStorage

        storage = configured_container.message_storage()
        assert isinstance(storage, MessageStorage), "Expected MessageStorage instance"

    def test_part_storage_provider_returns_storage(self, configured_container):
        """Scenario: Part storage provider returns PartStorage.

        Preconditions:
        - Container configured

        Steps:
        1. Get container.part_storage()
        2. Verify type is PartStorage

        Expected result:
        - Returns PartStorage instance

        Failure indicators:
        - Returns None
        - Returns wrong type
        """
        from dawn_kestrel.storage.store import PartStorage

        storage = configured_container.part_storage()
        assert isinstance(storage, PartStorage), "Expected PartStorage instance"

    def test_session_repo_provider_returns_repository(self, configured_container):
        """Scenario: Session repo provider returns SessionRepositoryImpl.

        Preconditions:
        - Container configured

        Steps:
        1. Get container.session_repo()
        2. Verify type is SessionRepositoryImpl

        Expected result:
        - Returns SessionRepositoryImpl instance

        Failure indicators:
        - Returns None
        - Returns wrong type
        """
        from dawn_kestrel.core.repositories import SessionRepositoryImpl

        repo = configured_container.session_repo()
        assert isinstance(repo, SessionRepositoryImpl), "Expected SessionRepositoryImpl instance"

    def test_message_repo_provider_returns_repository(self, configured_container):
        """Scenario: Message repo provider returns MessageRepositoryImpl.

        Preconditions:
        - Container configured

        Steps:
        1. Get container.message_repo()
        2. Verify type is MessageRepositoryImpl

        Expected result:
        - Returns MessageRepositoryImpl instance

        Failure indicators:
        - Returns None
        - Returns wrong type
        """
        from dawn_kestrel.core.repositories import MessageRepositoryImpl

        repo = configured_container.message_repo()
        assert isinstance(repo, MessageRepositoryImpl), "Expected MessageRepositoryImpl instance"

    def test_part_repo_provider_returns_repository(self, configured_container):
        """Scenario: Part repo provider returns PartRepositoryImpl.

        Preconditions:
        - Container configured

        Steps:
        1. Get container.part_repo()
        2. Verify type is PartRepositoryImpl

        Expected result:
        - Returns PartRepositoryImpl instance

        Failure indicators:
        - Returns None
        - Returns wrong type
        """
        from dawn_kestrel.core.repositories import PartRepositoryImpl

        repo = configured_container.part_repo()
        assert isinstance(repo, PartRepositoryImpl), "Expected PartRepositoryImpl instance"


class TestDIContainerServiceWiring:
    """Test DI container service dependency wiring."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def configured_container(self, temp_storage_dir):
        """Configure container with temp storage."""
        from dawn_kestrel.core.di_container import configure_container, reset_container

        reset_container()
        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        from dawn_kestrel.core.di_container import container

        yield container

        reset_container()

    def test_service_has_all_repositories(self, configured_container):
        """Scenario: SessionService has all repositories wired.

        Preconditions:
        - Container configured

        Steps:
        1. Get container.service()
        2. Verify service has _session_repo
        3. Verify service has _message_repo
        4. Verify service has _part_repo

        Expected result:
        - Service has all 3 repositories
        - All repositories are instances

        Failure indicators:
        - Repository is None
        - Repository wrong type
        """
        from dawn_kestrel.core.repositories import (
            SessionRepositoryImpl,
            MessageRepositoryImpl,
            PartRepositoryImpl,
        )

        service = configured_container.service()
        assert hasattr(service, "_session_repo"), "Service missing _session_repo"
        assert hasattr(service, "_message_repo"), "Service missing _message_repo"
        assert hasattr(service, "_part_repo"), "Service missing _part_repo"

        assert isinstance(service._session_repo, SessionRepositoryImpl), "Session repo wrong type"
        assert isinstance(service._message_repo, MessageRepositoryImpl), "Message repo wrong type"
        assert isinstance(service._part_repo, PartRepositoryImpl), "Part repo wrong type"

    def test_agent_runtime_has_dependencies(self, configured_container):
        """Scenario: AgentRuntime has all dependencies wired.

        Preconditions:
        - Container configured

        Steps:
        1. Get container.agent_runtime()
        2. Verify runtime has agent_registry
        3. Verify runtime has session_lifecycle

        Expected result:
        - Runtime has agent_registry
        - Runtime has session_lifecycle

        Failure indicators:
        - Dependency is None
        - Dependency wrong type
        """
        runtime = configured_container.agent_runtime()
        assert hasattr(runtime, "agent_registry"), "Runtime missing agent_registry"
        assert hasattr(runtime, "_session_lifecycle"), "Runtime missing _session_lifecycle"
        assert runtime.agent_registry is not None, "agent_registry is None"
        assert runtime._session_lifecycle is not None, "session_lifecycle is None"

    def test_provider_registry_has_dependencies(self, configured_container):
        """Scenario: ProviderRegistry has storage wired.

        Preconditions:
        - Container configured

        Steps:
        1. Get container.provider_registry()
        2. Verify registry has storage_dir

        Expected result:
        - Registry has storage_dir attribute
        - storage_dir is Path

        Failure indicators:
        - storage_dir is None
        - storage_dir wrong type
        """
        registry = configured_container.provider_registry()
        assert hasattr(registry, "_storage_dir"), "Registry missing _storage_dir"
        assert registry._storage_dir is not None, "storage_dir is None"
        assert isinstance(registry._storage_dir, Path), "storage_dir not a Path"


class TestDIContainerFullWiring:
    """Test full DI container wiring integration."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def configured_container(self, temp_storage_dir):
        """Configure container with temp storage."""
        from dawn_kestrel.core.di_container import configure_container, reset_container

        reset_container()
        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        from dawn_kestrel.core.di_container import container

        yield container

        reset_container()

    def test_all_providers_accessible(self, configured_container):
        """Scenario: All providers are accessible and return correct types.

        Preconditions:
        - Container configured

        Steps:
        1. Call all provider methods
        2. Verify each returns non-None value
        3. Verify each returns correct type

        Expected result:
        - All providers accessible
        - All providers return correct types
        - No missing providers

        Failure indicators:
        - Provider method raises exception
        - Provider returns None
        - Provider returns wrong type
        """
        from dawn_kestrel.storage.store import (
            SessionStorage,
            MessageStorage,
            PartStorage,
        )
        from dawn_kestrel.core.repositories import (
            SessionRepositoryImpl,
            MessageRepositoryImpl,
            PartRepositoryImpl,
        )

        assert configured_container.storage() is not None
        assert isinstance(configured_container.storage(), SessionStorage)

        assert configured_container.message_storage() is not None
        assert isinstance(configured_container.message_storage(), MessageStorage)

        assert configured_container.part_storage() is not None
        assert isinstance(configured_container.part_storage(), PartStorage)

        assert configured_container.session_repo() is not None
        assert isinstance(configured_container.session_repo(), SessionRepositoryImpl)

        assert configured_container.message_repo() is not None
        assert isinstance(configured_container.message_repo(), MessageRepositoryImpl)

        assert configured_container.part_repo() is not None
        assert isinstance(configured_container.part_repo(), PartRepositoryImpl)

    def test_full_dependency_chain_intact(self, configured_container):
        """Scenario: Full dependency chain from storage to runtime is intact.

        Preconditions:
        - Container configured

        Steps:
        1. Get storage
        2. Get repositories (depend on storage)
        3. Get service (depends on repositories)
        4. Get runtime (depends on registry, lifecycle)

        Expected result:
        - All providers instantiate successfully
        - No circular dependencies
        - No missing dependencies

        Failure indicators:
        - Provider instantiation fails
        - Circular dependency detected
        - Missing dependency error
        """
        storage = configured_container.storage()
        assert storage is not None, "Storage is None"

        session_repo = configured_container.session_repo()
        assert session_repo is not None, "Session repo is None"

        service = configured_container.service()
        assert service is not None, "Service is None"

        runtime = configured_container.agent_runtime()
        assert runtime is not None, "Runtime is None"

        assert service._session_repo is not None, "Service missing session repo"
        assert service._message_repo is not None, "Service missing message repo"
        assert service._part_repo is not None, "Service missing part repo"

        assert runtime.agent_registry is not None, "Runtime missing agent registry"
        assert runtime._session_lifecycle is not None, "Runtime missing session lifecycle"
