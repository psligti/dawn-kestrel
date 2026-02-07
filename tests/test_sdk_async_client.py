"""Tests for async SDK client."""
from __future__ import annotations

from unittest.mock import Mock, AsyncMock, patch
import pytest
from dawn_kestrel.sdk.client import OpenCodeAsyncClient
from dawn_kestrel.core.models import Session
from dawn_kestrel.core.exceptions import SessionError
from dawn_kestrel.core.agent_types import AgentResult
from dawn_kestrel.agents.builtin import Agent


class TestOpenCodeAsyncClientInitialization:
    """Tests for OpenCodeAsyncClient initialization."""

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    def test_async_client_initialization_default(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient initialization with default config."""
        from dawn_kestrel.core.config import SDKConfig

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        client = OpenCodeAsyncClient()
        
        assert client is not None
        assert client._service is not None
        assert client._on_progress is None
        assert client._on_notification is None

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    def test_async_client_initialization_with_sdk_config(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient initialization with SDKConfig."""
        from dawn_kestrel.core.config import SDKConfig

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        config = SDKConfig(auto_confirm=True)
        client = OpenCodeAsyncClient(config=config)
        
        assert client is not None
        assert client._service is not None
        assert client._on_progress is None
        assert client._on_notification is None

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    def test_async_client_initialization_with_handlers(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient initialization with custom handlers."""
        from dawn_kestrel.interfaces.io import QuietIOHandler, NoOpProgressHandler, NoOpNotificationHandler

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        io_handler = QuietIOHandler()
        progress_handler = NoOpProgressHandler()
        notification_handler = NoOpNotificationHandler()

        client = OpenCodeAsyncClient(
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )
        
        assert client is not None
        assert client._service is not None
        assert client._on_progress is None
        assert client._on_notification is None


class TestOpenCodeAsyncClientCallbacks:
    """Tests for OpenCodeAsyncClient callback registration."""

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    def test_on_progress_callback_registration(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test progress callback registration."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        client = OpenCodeAsyncClient()
        
        progress_callback = Mock()
        client.on_progress(progress_callback)
        
        assert client._on_progress == progress_callback

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    def test_on_notification_callback_registration(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test notification callback registration."""
        from dawn_kestrel.interfaces.io import Notification, NotificationType

        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        client = OpenCodeAsyncClient()
        
        notification_callback = Mock()
        client.on_notification(notification_callback)
        
        assert client._on_notification == notification_callback


class TestOpenCodeAsyncClientSessionMethods:
    """Tests for OpenCodeAsyncClient session management methods."""

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    @pytest.mark.asyncio
    async def test_async_client_create_session(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient.create_session() method."""
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

        client = OpenCodeAsyncClient()
        result = await client.create_session(title="Test Session")

        assert result == session
        mock_service.create_session.assert_called_once_with("Test Session")

    @patch("dawn_kestrel.core.services.session_service.DefaultSessionService")
    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @pytest.mark.asyncio
    async def test_async_client_get_session(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient.get_session() method."""
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
        mock_storage.get_session = AsyncMock(return_value=session)

        client = OpenCodeAsyncClient()
        result = await client.get_session(session_id="ses_001")

        assert result == session
        mock_storage.get_session.assert_called_once_with("ses_001")

    @patch("dawn_kestrel.core.services.session_service.DefaultSessionService")
    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @pytest.mark.asyncio
    async def test_async_client_get_session_not_found(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient.get_session() when session not found."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_storage.get_session = AsyncMock(return_value=None)

        client = OpenCodeAsyncClient()
        result = await client.get_session(session_id="nonexistent")

        assert result is None
        mock_storage.get_session.assert_called_once_with("nonexistent")

    @patch("dawn_kestrel.core.services.session_service.DefaultSessionService")
    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @pytest.mark.asyncio
    async def test_async_client_list_sessions(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient.list_sessions() method."""
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
        mock_storage.list_sessions = AsyncMock(return_value=[session1, session2])

        client = OpenCodeAsyncClient()
        result = await client.list_sessions()
        
        assert result == [session1, session2]
        mock_storage.list_sessions.assert_called_once()

    @patch("dawn_kestrel.core.services.session_service.DefaultSessionService")
    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @pytest.mark.asyncio
    async def test_async_client_delete_session(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient.delete_session() method."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_service.delete_session = AsyncMock(return_value=True)

        client = OpenCodeAsyncClient()
        result = await client.delete_session(session_id="ses_001")
        
        assert result is True
        mock_service.delete_session.assert_called_once_with("ses_001")

    @patch("dawn_kestrel.core.services.session_service.DefaultSessionService")
    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @pytest.mark.asyncio
    async def test_async_client_delete_session_not_found(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient.delete_session() when session not found."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_service.delete_session = AsyncMock(return_value=False)

        client = OpenCodeAsyncClient()
        result = await client.delete_session(session_id="nonexistent")
        
        assert result is False
        mock_service.delete_session.assert_called_once_with("nonexistent")

    @patch("dawn_kestrel.core.services.session_service.DefaultSessionService")
    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @pytest.mark.asyncio
    async def test_async_client_add_message(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient.add_message() method."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_service.add_message = AsyncMock(return_value="msg_001")

        client = OpenCodeAsyncClient()
        result = await client.add_message(
            session_id="ses_001",
            role="user",
            content="Test message",
        )
        
        assert result == "msg_001"
        mock_service.add_message.assert_called_once_with("ses_001", "user", "Test message")

    @patch("dawn_kestrel.core.services.session_service.DefaultSessionService")
    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @pytest.mark.asyncio
    async def test_async_client_exception_handling(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test that service exceptions are propagated to SDK user."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_service.create_session = AsyncMock(
            side_effect=ValueError("Storage error")
        )

        client = OpenCodeAsyncClient()
        
        with pytest.raises(SessionError, match="Failed to create session"):
            await client.create_session(title="Test")


class TestOpenCodeAsyncClientAgentMethods:
    """Tests for OpenCodeAsyncClient agent management methods."""

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    @pytest.mark.asyncio
    async def test_async_client_register_agent(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient.register_agent() method."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        client = OpenCodeAsyncClient()

        custom_agent = Agent(
            name="test-agent",
            description="Test agent",
            mode="subagent",
            permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
            native=False,
        )

        result = await client.register_agent(custom_agent)

        assert result == custom_agent
        assert await client._runtime.get_agent("test-agent") == custom_agent

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    @pytest.mark.asyncio
    async def test_async_client_get_agent(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient.get_agent() method."""
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        client = OpenCodeAsyncClient()

        agent = await client.get_agent("build")
        assert agent is not None
        assert agent.name == "build"

        agent = await client.get_agent("nonexistent")
        assert agent is None

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    @patch("dawn_kestrel.sdk.client.AgentRuntime.execute")
    @pytest.mark.asyncio
    async def test_async_client_execute_agent(
        self, mock_storage_cls, mock_service_cls, mock_runtime_execute
    ) -> None:
        """Test OpenCodeAsyncClient.execute_agent() method."""
        from unittest.mock import Mock, AsyncMock
        from dawn_kestrel.core.agent_types import AgentResult

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

        client = OpenCodeAsyncClient()

        mock_result = AgentResult(
            agent_name="build",
            response="Test response",
            parts=[],
            duration=0.5,
        )

        mock_runtime_execute.return_value = mock_result

        result = await client.execute_agent(
            agent_name="build",
            session_id="ses_001",
            user_message="Hello",
        )

        assert result == mock_result
        assert mock_runtime_execute.called
        assert mock_runtime_execute.call_args[0] == ("build", "ses_001", "Hello", None)

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    @patch("dawn_kestrel.sdk.client.AgentRuntime.execute")
    @pytest.mark.asyncio
    async def test_async_client_execute_agent_with_options(
        self, mock_storage_cls, mock_service_cls, mock_runtime_execute
    ) -> None:
        """Test OpenCodeAsyncClient.execute_agent() with options."""
        from unittest.mock import Mock, AsyncMock
        from dawn_kestrel.core.agent_types import AgentResult

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

        client = OpenCodeAsyncClient()

        mock_result = AgentResult(
            agent_name="build",
            response="Test response",
            parts=[],
            duration=0.5,
        )

        mock_runtime_execute.return_value = mock_result

        result = await client.execute_agent(
            agent_name="build",
            session_id="ses_001",
            user_message="Hello",
            options={"skills": ["test"], "model": "gpt-4"},
        )

        assert result == mock_result
        assert mock_runtime_execute.call_args[0] == ("build", "ses_001", "Hello", {"skills": ["test"], "model": "gpt-4"})
        assert isinstance(result.duration, float)

    @patch("dawn_kestrel.sdk.client.SessionStorage")
    @patch("dawn_kestrel.sdk.client.DefaultSessionService")
    @pytest.mark.asyncio
    async def test_async_client_execute_agent_with_options(
        self, mock_storage_cls, mock_service_cls
    ) -> None:
        """Test OpenCodeAsyncClient.execute_agent() with options."""
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

        client = OpenCodeAsyncClient()

        result = await client.execute_agent(
            agent_name="build",
            session_id="ses_001",
            user_message="Hello",
            options={"skills": ["test"], "model": "gpt-4"},
        )

        assert isinstance(result, AgentResult)
        assert result.agent_name == "build"

