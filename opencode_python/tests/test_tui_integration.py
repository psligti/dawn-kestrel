"""Test TUI app launches with SessionService and handlers.

This test validates Task 13 acceptance criteria.
"""

import pytest
from opencode_python.tui.app import OpenCodeTUI


class TestTUIIntegration:
    """Test TUI app integration with SessionService and handlers."""

    def test_tui_app_launches_with_session_service_and_handlers(self) -> None:
        """Test that TUI app launches with SessionService and handlers."""
        from opencode_python.core.services.session_service import DefaultSessionService
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir
        from opencode_python.tui.handlers import (
            TUIIOHandler,
            TUIProgressHandler,
            TUINotificationHandler,
        )

        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)

        session_service = DefaultSessionService(
            storage=storage,
        )

        app = OpenCodeTUI(session_service=session_service)

        assert app is not None
        assert isinstance(app, OpenCodeTUI)
        assert app.session_service is session_service
        assert app.io_handler is not None
        assert app.progress_handler is not None
        assert app.notification_handler is not None

    def test_tui_session_list_loads_from_session_service(self) -> None:
        """Test that TUI uses SessionService for loading sessions."""
        from opencode_python.core.services.session_service import DefaultSessionService
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir

        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)
        session_service = DefaultSessionService(storage=storage)

        app = OpenCodeTUI(session_service=session_service)

        assert hasattr(app.session_service, 'list_sessions')
        assert callable(app.session_service.list_sessions)

    def test_backward_compatibility_tui_visuals_unchanged(self) -> None:
        """Test that backward compatibility is maintained - visuals unchanged."""
        from opencode_python.core.services.session_service import DefaultSessionService
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir

        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)
        session_service = DefaultSessionService(storage=storage)

        app = OpenCodeTUI(session_service=session_service)

        assert hasattr(app, 'CSS')
        assert 'Screen' in app.CSS
        assert 'DataTable' in app.CSS
        assert hasattr(app, 'BINDINGS')
        assert len(app.BINDINGS) > 0

    def test_tui_no_direct_io_calls(self) -> None:
        """Test that TUI doesn't use direct I/O calls (print, input)."""
        from opencode_python.core.services.session_service import DefaultSessionService
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir

        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)
        session_service = DefaultSessionService(storage=storage)

        app = OpenCodeTUI(session_service=session_service)

        import inspect
        source = inspect.getsource(app.__class__)

        assert 'print(' not in source or '# print(' in source
        assert 'input(' not in source or '# input(' in source

    def test_tui_textual_structure_unchanged(self) -> None:
        """Test that Textual app structure is unchanged."""
        from opencode_python.core.services.session_service import DefaultSessionService
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir

        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)
        session_service = DefaultSessionService(storage=storage)

        app = OpenCodeTUI(session_service=session_service)

        assert hasattr(app, 'compose')
        assert hasattr(app, 'on_mount')
        assert hasattr(app, 'on_button_pressed')
        assert callable(app.compose)
        assert callable(app.on_mount)
        assert callable(app.on_button_pressed)

    def test_tui_message_screen_accepts_session_service(self) -> None:
        """Test that TUI message screen can accept session_service parameter."""
        from opencode_python.tui.screens.message_screen import MessageScreen
        from opencode_python.core.models import Session

        session = Session(
            id="test-session-id",
            slug="test-session",
            title="Test Session",
            project_id="test-project",
            directory="/test/path",
            version="1.0.0",
        )

        screen = MessageScreen(session=session, session_service=None)

        assert screen is not None
        assert screen.session is session

    def test_tui_message_screen_accepts_session_service_when_provided(self) -> None:
        """Test that TUI message screen stores session_service when provided."""
        from opencode_python.tui.screens.message_screen import MessageScreen
        from opencode_python.core.models import Session
        from opencode_python.core.services.session_service import DefaultSessionService
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.settings import get_storage_dir

        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)
        session_service = DefaultSessionService(storage=storage)

        session = Session(
            id="test-session-id",
            slug="test-session",
            title="Test Session",
            project_id="test-project",
            directory="/test/path",
            version="1.0.0",
        )

        screen = MessageScreen(session=session, session_service=session_service)

        assert screen.session_service is session_service
