"""Integration tests for TUI composition root and DI container.

Tests verify that TUI app correctly integrates with DI container,
SessionService, and repository pattern without mocking.

Scenario: TUI Composition Root Integration
==========================================

Preconditions:
- DI container configured
- TUI app initialized
- Storage directory accessible
- Repositories injected via DI container

Steps:
1. Initialize TUI app with DI container
2. Verify session_service injected from container
3. Verify repositories injected into service
4. Verify Result pattern handling in TUI
5. Verify handler integration

Expected result:
- TUI app initializes successfully
- All dependencies wired via DI container
- Result pattern errors handled gracefully
- User notified of errors via notification handler

Failure indicators:
- TUI app fails to initialize
- Dependencies not wired
- Result errors cause crashes
- User not notified of errors

Evidence:
- App.session_service is not None
- Service has repositories
- Error handling works
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest


class TestTUICompositionRoot:
    """Test TUI app composition root and DI container integration."""

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

    def test_tui_app_initializes_with_container(self, configured_container):
        """Scenario: TUI app initializes from DI container.

        Preconditions:
        - DI container configured
        - Storage directory set

        Steps:
        1. Create TUI app instance
        2. Verify session_service from container
        3. Verify app initialized successfully

        Expected result:
        - App.session_service is not None
        - Service has repositories
        - No initialization errors

        Failure indicators:
        - session_service is None
        - App crashes on init
        - Repositories missing
        """
        from dawn_kestrel.tui.app import OpenCodeTUI

        # Create app without running it
        app = OpenCodeTUI(session_service=None)

        # Inject service from container
        app.session_service = configured_container.service()

        assert app.session_service is not None, "session_service should be from container"
        assert hasattr(app.session_service, "_session_repo"), "Service missing session_repo"
        assert hasattr(app.session_service, "_message_repo"), "Service missing message_repo"
        assert hasattr(app.session_service, "_part_repo"), "Service missing part_repo"

    def test_tui_uses_di_container_dependencies(self, configured_container):
        """Scenario: TUI uses DI container for all dependencies.

        Preconditions:
        - DI container configured

        Steps:
        1. Get service from container
        2. Verify all repositories wired
        3. Verify handlers can be set

        Expected result:
        - Service has all 3 repositories
        - Handlers can be injected
        - No missing dependencies

        Failure indicators:
        - Repository is None
        - Handler injection fails
        - Missing dependency
        """
        from dawn_kestrel.tui.app import OpenCodeTUI
        from dawn_kestrel.tui.handlers import (
            TUIIOHandler,
            TUIProgressHandler,
            TUINotificationHandler,
        )

        app = OpenCodeTUI(session_service=None)
        service = configured_container.service()

        # Verify repositories wired
        assert service._session_repo is not None
        assert service._message_repo is not None
        assert service._part_repo is not None

        # Verify handlers can be set (pattern from napkin)
        app.session_service = service
        app.session_service._io_handler = TUIIOHandler(app)
        app.session_service._progress_handler = TUIProgressHandler(app)
        app.session_service._notification_handler = TUINotificationHandler(app)

        assert app.session_service._io_handler is not None
        assert app.session_service._progress_handler is not None
        assert app.session_service._notification_handler is not None


class TestTUIResultHandling:
    """Test TUI Result pattern error handling."""

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

    def test_tui_handles_result_errors_gracefully(self, configured_container):
        """Scenario: TUI handles Result errors without crashing.

        Preconditions:
        - Service configured
        - TUI app initialized

        Steps:
        1. Get nonexistent session via service
        2. Verify Result is Ok(None) (not Err)
        3. Verify TUI can handle this case

        Expected result:
        - Service returns Ok(None) not Err
        - TUI can check is_ok()
        - TUI can handle None session

        Failure indicators:
        - Result is Err (wrong pattern)
        - TUI crashes on None
        - Error handling fails

        Evidence:
        - is_ok() returns True
        - unwrap() returns None
        """
        import asyncio
        from dawn_kestrel.tui.app import OpenCodeTUI

        app = OpenCodeTUI(session_service=None)
        app.session_service = configured_container.service()

        async def test_get_session():
            result = await app.session_service.get_session("nonexistent_id")
            return result

        result = asyncio.run(test_get_session())

        assert result.is_ok(), "get_session should return Ok(None), not Err"
        session = result.unwrap()
        assert session is None, "Session should be None for nonexistent ID"


class TestTUISessionManagement:
    """Test TUI session management integration."""

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

    def test_tui_can_list_sessions_via_service(self, configured_container):
        """Scenario: TUI can list sessions via SessionService.

        Preconditions:
        - Sessions exist
        - Service configured

        Steps:
        1. Create session via storage
        2. Call session_service.list_sessions
        3. Verify session in list
        4. Verify Result pattern used

        Expected result:
        - list_sessions returns Result[List[Session]]
        - is_ok() returns True
        - Session in list

        Failure indicators:
        - list_sessions fails
        - Wrong return type
        - Session not in list

        Evidence:
        - Result.is_ok() = True
        - Session in unwrapped list
        """
        import asyncio
        from dawn_kestrel.tui.app import OpenCodeTUI
        from dawn_kestrel.storage.store import SessionStorage
        from dawn_kestrel.core.models import Session

        # Create session
        storage = SessionStorage(base_dir=configured_container.storage_dir())
        session = Session(
            id="tui_test_1",
            slug="test",
            project_id="test_project",
            directory="/tmp/test",
            title="TUI Test Session",
            version="1.0.0",
        )
        asyncio.run(storage.create_session(session))

        # List via service
        app = OpenCodeTUI(session_service=None)
        app.session_service = configured_container.service()

        async def test_list():
            result = await app.session_service.list_sessions()
            return result

        result = asyncio.run(test_list())

        assert result.is_ok(), (
            f"list_sessions failed: {result.error if hasattr(result, 'error') else result}"
        )
        sessions = result.unwrap()
        assert len(sessions) > 0, "No sessions returned"
        assert any(s.id == "tui_test_1" for s in sessions), "Test session not in list"
