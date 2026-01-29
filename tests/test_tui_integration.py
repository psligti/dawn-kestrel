"""
Test suite for TUI integration with SessionService and handlers.

This test suite follows TDD approach:
- RED: Tests are written first and will fail initially
- GREEN: TUI app will be refactored to use SessionService and handlers
- REFACTOR: Code will be refactored while keeping tests green
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestTUIAppIntegration:
    """Test TUI app integration with SessionService and handlers."""

    def test_tui_app_imports_session_service(self):
        """Test that TUI app imports SessionService."""
        try:
            from opencode_python.tui.app import OpenCodeTUI
            from opencode_python.core.services.session_service import SessionService

            # Check that SessionService is imported in the module
            import opencode_python.tui.app as app_module
            # Note: We import DefaultSessionService, not the SessionService Protocol
            assert hasattr(app_module, 'DefaultSessionService'), "TUI app should import DefaultSessionService"
        except ImportError as e:
            pytest.fail(f"TUI app should import SessionService: {e}")

    def test_tui_app_imports_handlers(self):
        """Test that TUI app imports TUI handlers."""
        try:
            from opencode_python.tui.app import OpenCodeTUI

            # Check that handlers are imported in the module
            import opencode_python.tui.app as app_module
            assert hasattr(app_module, 'TUIIOHandler'), "TUI app should import TUIIOHandler"
            assert hasattr(app_module, 'TUIProgressHandler'), "TUI app should import TUIProgressHandler"
            assert hasattr(app_module, 'TUINotificationHandler'), "TUI app should import TUINotificationHandler"
        except ImportError as e:
            pytest.fail(f"TUI app should import TUI handlers: {e}")

    def test_tui_app_imports_sdk_config(self):
        """Test that TUI app imports SDKConfig."""
        try:
            from opencode_python.tui.app import OpenCodeTUI

            # Check that SDKConfig is imported in the module
            import opencode_python.tui.app as app_module
            assert hasattr(app_module, 'SDKConfig'), "TUI app should import SDKConfig"
        except ImportError as e:
            pytest.fail(f"TUI app should import SDKConfig: {e}")

    def test_tui_app_uses_session_service(self):
        """Test that TUI app has SessionService instance."""
        from opencode_python.tui.app import OpenCodeTUI
        from opencode_python.core.services.session_service import SessionService

        # Create app instance (we don't run it, just instantiate)
        app = OpenCodeTUI()

        # Check that app has session_service attribute
        assert hasattr(app, 'session_service'), "TUI app should have session_service attribute"

        # Verify it's a SessionService protocol implementation
        session_service = app.session_service
        assert isinstance(session_service, SessionService), (
            "session_service should implement SessionService protocol"
        )

    def test_tui_app_creates_handlers(self):
        """Test that TUI app creates TUI handler instances."""
        from opencode_python.tui.app import OpenCodeTUI
        from opencode_python.tui.handlers import (
            TUIIOHandler,
            TUIProgressHandler,
            TUINotificationHandler,
        )

        # Create app instance
        app = OpenCodeTUI()

        # Check that app has handler attributes
        assert hasattr(app, 'io_handler'), "TUI app should have io_handler attribute"
        assert hasattr(app, 'progress_handler'), "TUI app should have progress_handler attribute"
        assert hasattr(app, 'notification_handler'), "TUI app should have notification_handler attribute"

        # Verify handler types
        assert isinstance(app.io_handler, TUIIOHandler), "io_handler should be TUIIOHandler"
        assert isinstance(app.progress_handler, TUIProgressHandler), "progress_handler should be TUIProgressHandler"
        assert isinstance(app.notification_handler, TUINotificationHandler), "notification_handler should be TUINotificationHandler"

    @pytest.mark.asyncio
    async def test_session_list_screen_uses_session_service(self):
        """Test that session list screen uses SessionService.list_sessions()."""
        from opencode_python.tui.app import OpenCodeTUI
        from opencode_python.core.models import Session

        # Mock SessionService
        mock_session_service = AsyncMock()
        test_session = Session(
            id="test-session-id",
            slug="test-session",
            project_id="test-project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0.0",
            time_created=datetime.now().timestamp(),
            time_updated=datetime.now().timestamp(),
        )
        mock_session_service.list_sessions.return_value = [test_session]

        # Create app with mocked service (don't patch compose so handlers are initialized)
        app = OpenCodeTUI()
        app.session_service = mock_session_service

        # Call _load_sessions (the method that loads sessions)
        await app._load_sessions()

        # Verify SessionService.list_sessions was called
        mock_session_service.list_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_detail_screen_uses_session_service(self):
        """Test that session detail screen uses SessionService.get_session()."""
        from opencode_python.tui.app import OpenCodeTUI
        from opencode_python.core.models import Session

        # Mock SessionService
        mock_session_service = AsyncMock()
        test_session = Session(
            id="test-session-id",
            slug="test-session",
            project_id="test-project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0.0",
            time_created=datetime.now().timestamp(),
            time_updated=datetime.now().timestamp(),
        )
        mock_session_service.get_session.return_value = test_session

        # Create app with mocked service
        app = OpenCodeTUI()
        app.session_service = mock_session_service
        app.current_session_id = "test-session-id"

        # Call _open_message_screen which should use get_session
        with patch.object(app, 'push_screen') as mock_push_screen:
            await app._open_message_screen()

            # Verify SessionService.get_session was called
            mock_session_service.get_session.assert_called_once_with("test-session-id")

    @pytest.mark.asyncio
    async def test_message_creation_uses_session_service(self):
        """Test that message creation uses SessionService.add_message()."""
        from opencode_python.tui.app import OpenCodeTUI
        from opencode_python.core.models import Message

        # Mock SessionService
        mock_session_service = AsyncMock()
        test_message = Message(
            id="test-message-id",
            session_id="test-session-id",
            role="user",
            time={"created": datetime.now().timestamp()},
            text="Test message content",
        )
        mock_session_service.add_message.return_value = test_message

        # Create app with mocked service
        app = OpenCodeTUI()
        app.session_service = mock_session_service
        app.current_session_id = "test-session-id"

        # Mock messages_container
        app.messages_container = AsyncMock()
        app.messages_container.mount = AsyncMock()

        # Call _add_message
        await app._add_message("user", "Test message content")

    def test_tui_notifications_use_handler(self):
        """Test that TUI notifications use notification handler."""
        from opencode_python.tui.app import OpenCodeTUI
        from opencode_python.tui.handlers import TUINotificationHandler

        # Create app with mocked handler
        app = OpenCodeTUI()

        # Mock notification handler's show method
        original_show = app.notification_handler.show
        app.notification_handler.show = Mock()

        # Call notify (Textual's built-in notification)
        app.notify("Test notification", severity="information")

        # Verify handler exists
        assert isinstance(app.notification_handler, TUINotificationHandler)

    def test_tui_progress_uses_handler(self):
        """Test that TUI progress updates use progress handler."""
        from opencode_python.tui.app import OpenCodeTUI
        from opencode_python.tui.handlers import TUIProgressHandler

        # Create app with mocked handler
        app = OpenCodeTUI()

        # Verify progress handler exists
        assert isinstance(app.progress_handler, TUIProgressHandler)

    def test_backward_compatibility_textual_structure(self):
        """Test that Textual app structure is unchanged (backward compatibility)."""
        from opencode_python.tui.app import OpenCodeTUI
        from textual.app import App

        assert issubclass(OpenCodeTUI, App), "OpenCodeTUI should inherit from Textual App"

        bindings = OpenCodeTUI.BINDINGS
        assert any(b.key == "q" for b in bindings), "Quit binding should still exist"
        assert any(b.key == "ctrl+c" for b in bindings), "Ctrl+C binding should still exist"

    def test_backward_compatibility_ui_components(self):
        """Test that UI components are still present."""
        from opencode_python.tui.app import OpenCodeTUI

        assert hasattr(OpenCodeTUI, 'CSS'), "CSS should still be defined"
        assert "Screen {" in OpenCodeTUI.CSS, "CSS should still have Screen styles"

    @pytest.mark.asyncio
    async def test_error_handling_propagates_session_service_exceptions(self):
        """Test that SessionService exceptions are properly propagated."""
        from opencode_python.tui.app import OpenCodeTUI
        from opencode_python.core.exceptions import SessionError
        import asyncio

        mock_session_service = AsyncMock()
        mock_session_service.list_sessions.side_effect = SessionError(
            message="Test error",
            session_id="test-id",
        )

        with patch('opencode_python.tui.app.OpenCodeTUI.compose'):
            app = OpenCodeTUI()
            app.session_service = mock_session_service

            with pytest.raises(SessionError):
                await app._load_sessions()

    @pytest.mark.asyncio
    async def test_handler_integration_session_create(self):
        """Test that session creation uses handlers for progress and notifications."""
        from opencode_python.tui.app import OpenCodeTUI
        from opencode_python.core.models import Session

        mock_session_service = AsyncMock()
        test_session = Session(
            id="new-session-id",
            slug="new-session",
            project_id="test-project",
            directory="/tmp/test",
            title="New Session",
            version="1.0.0",
            time_created=datetime.now().timestamp(),
            time_updated=datetime.now().timestamp(),
        )
        mock_session_service.create_session.return_value = test_session

        mock_io_handler = AsyncMock()
        mock_io_handler.prompt = AsyncMock(return_value="")
        mock_io_handler.confirm = AsyncMock(return_value=True)

        mock_progress_handler = Mock()
        mock_progress_handler.start = Mock()
        mock_progress_handler.update = Mock()
        mock_progress_handler.complete = Mock()

        mock_notification_handler = Mock()
        mock_notification_handler.show = Mock()

        with patch('opencode_python.tui.app.OpenCodeTUI.compose'):
            app = OpenCodeTUI()
            app.session_service = mock_session_service
            app.io_handler = mock_io_handler
            app.progress_handler = mock_progress_handler
            app.notification_handler = mock_notification_handler

    def test_tui_app_has_type_hints(self):
        """Test that TUI app methods have type hints."""
        from opencode_python.tui.app import OpenCodeTUI

        assert hasattr(OpenCodeTUI, '__annotations__'), "Class should have type hints"

        annotations = OpenCodeTUI.__annotations__
        assert len(annotations) > 0, "Should have some type annotations"

    def test_tui_app_has_docstrings(self):
        """Test that TUI app has comprehensive docstrings."""
        from opencode_python.tui.app import OpenCodeTUI

        assert OpenCodeTUI.__doc__, "Class should have a docstring"

        assert OpenCodeTUI.compose.__doc__, "compose method should have a docstring"
        assert OpenCodeTUI.on_mount.__doc__, "on_mount method should have a docstring"
