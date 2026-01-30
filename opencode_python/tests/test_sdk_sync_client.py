"""Tests for sync SDK client."""
from __future__ import annotations

from unittest.mock import Mock, AsyncMock, patch
import pytest
from opencode_python.sdk.client import OpenCodeSyncClient
from opencode_python.core.models import Session
from opencode_python.core.exceptions import SessionError


class TestOpenCodeClientInitialization:
    """Tests for OpenCodeSyncClient initialization."""

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_initialization_default(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient initialization with default config."""
        from opencode_python.core.config import SDKConfig

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        client = OpenCodeSyncClient()

        assert client is not None
        assert client._async_client == mock_service
        assert client._on_progress is None
        assert client._on_notification is None

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_initialization_with_sdk_config(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient initialization with SDKConfig."""
        from opencode_python.core.config import SDKConfig

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        config = SDKConfig(auto_confirm=True)
        client = OpenCodeSyncClient(config=config)

        assert client is not None
        assert client._async_client == mock_service
        assert client._on_progress is None
        assert client._on_notification is None

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_initialization_with_handlers(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient initialization with custom handlers."""
        from opencode_python.interfaces.io import QuietIOHandler, NoOpProgressHandler, NoOpNotificationHandler

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        io_handler = QuietIOHandler()
        progress_handler = NoOpProgressHandler()
        notification_handler = NoOpNotificationHandler()

        client = OpenCodeSyncClient(
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        assert client is not None
        assert client._async_client == mock_service
        assert client._on_progress is None
        assert client._on_notification is None


class TestOpenCodeClientCallbacks:
    """Tests for OpenCodeSyncClient callback registration."""

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_on_progress_callback_registration(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test progress callback registration."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        client = OpenCodeSyncClient()

        progress_callback = Mock()
        client.on_progress(progress_callback)

        assert client._on_progress == progress_callback

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_on_notification_callback_registration(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test notification callback registration."""
        from opencode_python.interfaces.io import Notification

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        client = OpenCodeSyncClient()

        notification_callback = Mock()
        client.on_notification(notification_callback)

        assert client._on_notification == notification_callback


class TestOpenCodeClientSessionMethods:
    """Tests for OpenCodeSyncClient session management methods."""

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_create_session(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient.create_session() method."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        session = Session(
            id="ses_001",
            title="Test Session",
            slug="test-session",
            project_id="test-project",
            directory="/test",
            time_created=1234567890,
            version="1.0.0",
        )
        mock_service.create_session = AsyncMock(return_value=session)

        client = OpenCodeSyncClient()
        result = client.create_session(title="Test Session")

        assert result == session
        mock_service.create_session.assert_called_once_with("Test Session")

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_get_session(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient.get_session() method."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        session = Session(
            id="ses_001",
            title="Test Session",
            slug="test-session",
            project_id="test-project",
            directory="/test",
            time_created=1234567890,
            version="1.0.0",
        )
        mock_service.get_session = AsyncMock(return_value=session)

        client = OpenCodeSyncClient()
        result = client.get_session(session_id="ses_001")

        assert result == session
        mock_service.get_session.assert_called_once_with("ses_001")

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_get_session_not_found(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient.get_session() when session not found."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_service.get_session = AsyncMock(return_value=None)

        client = OpenCodeSyncClient()
        result = client.get_session(session_id="nonexistent")

        assert result is None
        mock_service.get_session.assert_called_once_with("nonexistent")

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_list_sessions(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient.list_sessions() method."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        session1 = Session(
            id="ses_001",
            title="Test Session 1",
            slug="test-session-1",
            project_id="test-project",
            directory="/test",
            time_created=1234567890,
            version="1.0.0",
        )
        session2 = Session(
            id="ses_002",
            title="Test Session 2",
            slug="test-session-2",
            project_id="test-project",
            directory="/test",
            time_created=1234567900,
            version="1.0.0",
        )
        mock_service.list_sessions = AsyncMock(return_value=[session1, session2])

        client = OpenCodeSyncClient()
        result = client.list_sessions()

        assert result == [session1, session2]
        mock_service.list_sessions.assert_called_once()

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_delete_session(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient.delete_session() method."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_service.delete_session = AsyncMock(return_value=True)

        client = OpenCodeSyncClient()
        result = client.delete_session(session_id="ses_001")

        assert result is True
        mock_service.delete_session.assert_called_once_with("ses_001")

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_delete_session_not_found(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient.delete_session() when session not found."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_service.delete_session = AsyncMock(return_value=False)

        client = OpenCodeSyncClient()
        result = client.delete_session(session_id="nonexistent")

        assert result is False
        mock_service.delete_session.assert_called_once_with("nonexistent")

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_add_message(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient.add_message() method."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_service.add_message = AsyncMock(return_value="msg_001")

        client = OpenCodeSyncClient()
        result = client.add_message(
            session_id="ses_001",
            role="user",
            content="Test message",
        )

        assert result == "msg_001"
        mock_service.add_message.assert_called_once_with("ses_001", "user", "Test message")

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_wraps_async_client(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient wraps async client methods."""
        from opencode_python.sdk.client import OpenCodeAsyncClient
        import asyncio

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        async_mock = Mock()
        mock_storage_cls.return_value = async_mock

        client = OpenCodeSyncClient()
        assert hasattr(client._async_client, 'create_session')
        assert hasattr(client._async_client, 'get_session')
        assert hasattr(client._async_client, 'list_sessions')
        assert hasattr(client._async_client, 'delete_session')
        assert hasattr(client._async_client, 'add_message')

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_uses_asyncio_run(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test that sync client uses asyncio.run internally."""
        from opencode_python.sdk.client import OpenCodeAsyncClient
        import asyncio

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        async_client_mock = Mock(spec=OpenCodeAsyncClient)
        with patch('asyncio.run', return_value=async_client_mock.return_value):
            with patch('opencode_python.sdk.client.OpenCodeAsyncClient', return_value=async_client_mock):
                client = OpenCodeSyncClient()
                client.create_session(title="Test")

        asyncio.run.assert_called_once()
        async_client_mock.create_session.assert_called_once_with("Test")


class TestOpenCodeClientExceptionHandling:
    """Tests for OpenCodeSyncClient exception handling."""

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_exception_handling(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test that service exceptions are propagated to SDK user."""
        from opencode_python.core.config import SDKConfig

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_service.create_session = AsyncMock(
            side_effect=ValueError("Storage error")
        )

        client = OpenCodeSyncClient()

        with pytest.raises(SessionError, match="Failed to create session"):
            client.create_session(title="Test")


class TestOpenCodeClientAsyncIntegration:
    """Tests for OpenCodeSyncClient async integration."""

    @patch("opencode_python.sdk.client.SessionStorage")
    @patch("opencode_python.sdk.client.DefaultSessionService")
    def test_sync_client_handler_integration(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeSyncClient handler integration."""
        from opencode_python.interfaces.io import QuietIOHandler, NoOpProgressHandler, NoOpNotificationHandler

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        io_handler = QuietIOHandler()
        progress_handler = NoOpProgressHandler()
        notification_handler = NoOpNotificationHandler()

        client = OpenCodeSyncClient(
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        assert client is not None
        assert client._async_client == mock_service
        assert client._async_client._io_handler == io_handler
        assert client._async_client._progress_handler == progress_handler
        assert client._async_client._notification_handler == notification_handler
