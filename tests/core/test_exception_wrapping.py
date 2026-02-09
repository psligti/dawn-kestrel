"""Tests for exception wrapping in Result types.

This module tests that domain exceptions are wrapped in Result types
instead of being raised, both in services and SDK clients.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from pathlib import Path

from dawn_kestrel.core.services.session_service import DefaultSessionService
from dawn_kestrel.sdk.client import OpenCodeAsyncClient, OpenCodeSyncClient
from dawn_kestrel.core.result import Result, Ok, Err
from dawn_kestrel.core.repositories import SessionRepository, MessageRepository
from dawn_kestrel.core.models import Session
from dawn_kestrel.core.exceptions import OpenCodeError


class MockSessionRepository:
    """Mock session repository for testing."""

    async def create(self, session: Session) -> Result[Session]:
        return Ok(session)

    async def delete(self, session_id: str) -> Result[bool]:
        return Ok(True)

    async def get_by_id(self, session_id: str) -> Result[Session]:
        return Ok(session)

    async def list_by_project(self, project_id: str) -> Result[list[Session]]:
        return Ok([])


class MockMessageRepository:
    """Mock message repository for testing."""

    async def create(self, message) -> Result:
        return Ok(message)

    async def list_by_session(self, session_id: str, reverse: bool = False) -> Result:
        return Ok([])


class TestSessionServiceExceptionWrapping:
    """Test that SessionService wraps exceptions in Result types."""

    @pytest.mark.asyncio
    async def test_create_session_returns_ok_on_success(self):
        """Test create_session returns Ok on success."""
        session_repo = MockSessionRepository()
        message_repo = MockMessageRepository()
        service = DefaultSessionService(
            session_repo=session_repo,
            message_repo=message_repo,
            project_dir=Path("/tmp/test"),
        )

        result = await service.create_session("Test Session")

        assert isinstance(result, Ok)
        assert result.is_ok()
        assert result.unwrap().title == "Test Session"

    @pytest.mark.asyncio
    async def test_create_session_returns_err_on_failure(self):
        """Test create_session returns Err on repository failure."""

        class FailingRepository:
            async def create(self, session: Session) -> Result[Session]:
                return Err("Database connection failed", code="DatabaseError")

        session_repo = FailingRepository()
        message_repo = MockMessageRepository()
        service = DefaultSessionService(
            session_repo=session_repo,
            message_repo=message_repo,
            project_dir=Path("/tmp/test"),
        )

        result = await service.create_session("Test Session")

        assert isinstance(result, Err)
        assert result.is_err()
        assert result.code == "SessionError"
        assert "Failed to create session" in result.error

    @pytest.mark.asyncio
    async def test_delete_session_returns_ok_on_success(self):
        """Test delete_session returns Ok on success."""
        session_repo = MockSessionRepository()
        message_repo = MockMessageRepository()
        service = DefaultSessionService(
            session_repo=session_repo,
            message_repo=message_repo,
            project_dir=Path("/tmp/test"),
        )

        result = await service.delete_session("test-id")

        assert isinstance(result, Ok)
        assert result.is_ok()
        assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_delete_session_returns_err_on_failure(self):
        """Test delete_session returns Err on repository failure."""

        class FailingRepository:
            async def delete(self, session_id: str) -> Result[bool]:
                return Err("Session not found", code="NotFound")

        session_repo = FailingRepository()
        message_repo = MockMessageRepository()
        service = DefaultSessionService(
            session_repo=session_repo,
            message_repo=message_repo,
            project_dir=Path("/tmp/test"),
        )

        result = await service.delete_session("test-id")

        assert isinstance(result, Err)
        assert result.is_err()
        assert result.code == "SessionError"
        assert "Failed to delete session" in result.error

    @pytest.mark.asyncio
    async def test_add_message_returns_ok_on_success(self):
        """Test add_message returns Ok on success."""
        session_repo = MockSessionRepository()
        message_repo = MockMessageRepository()
        service = DefaultSessionService(
            session_repo=session_repo,
            message_repo=message_repo,
            project_dir=Path("/tmp/test"),
        )

        result = await service.add_message("test-id", "user", "Hello")

        assert isinstance(result, Ok)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_add_message_returns_err_on_failure(self):
        """Test add_message returns Err on repository failure."""

        class FailingRepository:
            async def create(self, message) -> Result:
                return Err("Invalid session ID", code="NotFound")

        session_repo = MockSessionRepository()
        message_repo = FailingRepository()
        service = DefaultSessionService(
            session_repo=session_repo,
            message_repo=message_repo,
            project_dir=Path("/tmp/test"),
        )

        result = await service.add_message("test-id", "user", "Hello")

        assert isinstance(result, Err)
        assert result.is_err()
        assert result.code == "SessionError"
        assert "Failed to add message" in result.error


class TestAsyncClientExceptionWrapping:
    """Test that async SDK client wraps exceptions in Result types."""

    @pytest.fixture
    def client(self):
        """Create async client for testing."""
        with patch("dawn_kestrel.sdk.client.SessionStorage"):
            client = OpenCodeAsyncClient()
        return client

    @pytest.mark.asyncio
    async def test_create_session_wraps_service_result(self, client):
        """Test create_session wraps service Result."""
        # Mock service to return a Result
        with patch.object(client._service, "create_session", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = Ok(
                Session(
                    id="test-id",
                    slug="test-slug",
                    project_id="test",
                    directory="/tmp/test",
                    parent_id=None,
                    title="Test Session",
                    version="1.0.0",
                    time_created=0,
                    time_updated=0,
                )
            )

            result = await client.create_session("Test Session")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().title == "Test Session"

    @pytest.mark.asyncio
    async def test_create_session_catches_exceptions(self, client):
        """Test create_session catches and wraps exceptions."""
        # Mock service to raise an exception
        with patch.object(client._service, "create_session", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Service unavailable")

            result = await client.create_session("Test Session")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to create session" in result.error

    @pytest.mark.asyncio
    async def test_get_session_returns_ok(self, client):
        """Test get_session returns Ok on success."""
        with patch.object(client._service, "get_session", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Session(
                id="test-id",
                slug="test-slug",
                project_id="test",
                directory="/tmp/test",
                parent_id=None,
                title="Test Session",
                version="1.0.0",
                time_created=0,
                time_updated=0,
            )

            result = await client.get_session("test-id")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().id == "test-id"

    @pytest.mark.asyncio
    async def test_get_session_catches_exceptions(self, client):
        """Test get_session catches and wraps exceptions."""
        with patch.object(client._service, "get_session", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Database error")

            result = await client.get_session("test-id")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to get session" in result.error

    @pytest.mark.asyncio
    async def test_list_sessions_returns_ok(self, client):
        """Test list_sessions returns Ok on success."""
        with patch.object(client._service, "list_sessions", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            result = await client.list_sessions()

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap() == []

    @pytest.mark.asyncio
    async def test_list_sessions_catches_exceptions(self, client):
        """Test list_sessions catches and wraps exceptions."""
        with patch.object(client._service, "list_sessions", new_callable=AsyncMock) as mock_list:
            mock_list.side_effect = Exception("Storage error")

            result = await client.list_sessions()

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to list sessions" in result.error

    @pytest.mark.asyncio
    async def test_delete_session_returns_ok(self, client):
        """Test delete_session returns Ok on success."""
        with patch.object(client._service, "delete_session", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = Ok(True)

            result = await client.delete_session("test-id")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_delete_session_catches_exceptions(self, client):
        """Test delete_session catches and wraps exceptions."""
        with patch.object(client._service, "delete_session", new_callable=AsyncMock) as mock_delete:
            mock_delete.side_effect = Exception("Delete failed")

            result = await client.delete_session("test-id")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to delete session" in result.error

    @pytest.mark.asyncio
    async def test_add_message_returns_ok(self, client):
        """Test add_message returns Ok on success."""
        with patch.object(client._service, "add_message", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = Ok("message-id")

            result = await client.add_message("test-id", "user", "Hello")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap() == "message-id"

    @pytest.mark.asyncio
    async def test_add_message_catches_exceptions(self, client):
        """Test add_message catches and wraps exceptions."""
        with patch.object(client._service, "add_message", new_callable=AsyncMock) as mock_add:
            mock_add.side_effect = Exception("Add failed")

            result = await client.add_message("test-id", "user", "Hello")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to add message" in result.error

    @pytest.mark.asyncio
    async def test_register_agent_returns_ok(self, client):
        """Test register_agent returns Ok on success."""
        with patch.object(
            client._runtime.agent_registry, "register_agent", new_callable=AsyncMock
        ) as mock_reg:
            mock_reg.return_value = {"name": "test-agent"}

            result = await client.register_agent({"name": "test-agent"})

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap()["name"] == "test-agent"

    @pytest.mark.asyncio
    async def test_register_agent_catches_exceptions(self, client):
        """Test register_agent catches and wraps exceptions."""
        with patch.object(
            client._runtime.agent_registry, "register_agent", new_callable=AsyncMock
        ) as mock_reg:
            mock_reg.side_effect = Exception("Registration failed")

            result = await client.register_agent({"name": "test-agent"})

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to register agent" in result.error

    @pytest.mark.asyncio
    async def test_get_agent_returns_ok(self, client):
        """Test get_agent returns Ok on success."""
        with patch.object(
            client._runtime.agent_registry, "get_agent", return_value={"name": "test-agent"}
        ):
            result = await client.get_agent("test-agent")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap()["name"] == "test-agent"

    @pytest.mark.asyncio
    async def test_get_agent_catches_exceptions(self, client):
        """Test get_agent catches and wraps exceptions."""
        with patch.object(
            client._runtime.agent_registry, "get_agent", side_effect=Exception("Get failed")
        ):
            result = await client.get_agent("test-agent")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to get agent" in result.error

    @pytest.mark.asyncio
    async def test_execute_agent_returns_ok(self, client):
        """Test execute_agent returns Ok on success."""
        from dawn_kestrel.core.agent_types import AgentResult

        mock_result = AgentResult(
            agent_name="test-agent",
            response="Test response",
            parts=[],
            metadata={},
            tools_used=[],
            duration=100,
            error=None,
        )

        with patch.object(client._runtime, "execute_agent", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_result

            result = await client.execute_agent("test-agent", "test-id", "Hello")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().response == "Test response"

    @pytest.mark.asyncio
    async def test_execute_agent_catches_exceptions(self, client):
        """Test execute_agent catches and wraps exceptions."""
        with patch.object(client._runtime, "execute_agent", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = Exception("Execution failed")

            result = await client.execute_agent("test-agent", "test-id", "Hello")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to execute agent" in result.error

    @pytest.mark.asyncio
    async def test_register_provider_returns_ok(self, client):
        """Test register_provider returns Ok on success."""
        from dawn_kestrel.core.provider_config import ProviderConfig

        mock_config = ProviderConfig(
            provider_id="test",
            model="test-model",
            api_key=None,
            is_default=False,
        )

        with patch.object(
            client._provider_registry, "register_provider", new_callable=AsyncMock
        ) as mock_reg:
            mock_reg.return_value = mock_config

            result = await client.register_provider("test-provider", "test", "test-model")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().model == "test-model"

    @pytest.mark.asyncio
    async def test_register_provider_catches_exceptions(self, client):
        """Test register_provider catches and wraps exceptions."""
        with patch.object(
            client._provider_registry, "register_provider", new_callable=AsyncMock
        ) as mock_reg:
            mock_reg.side_effect = Exception("Registration failed")

            result = await client.register_provider("test-provider", "test", "test-model")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to register provider" in result.error

    @pytest.mark.asyncio
    async def test_get_provider_returns_ok(self, client):
        """Test get_provider returns Ok on success."""
        from dawn_kestrel.core.provider_config import ProviderConfig

        mock_config = ProviderConfig(
            provider_id="test",
            model="test-model",
            api_key=None,
            is_default=False,
        )

        with patch.object(
            client._provider_registry, "get_provider", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_config

            result = await client.get_provider("test-provider")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().model == "test-model"

    @pytest.mark.asyncio
    async def test_get_provider_catches_exceptions(self, client):
        """Test get_provider catches and wraps exceptions."""
        with patch.object(
            client._provider_registry, "get_provider", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = Exception("Get failed")

            result = await client.get_provider("test-provider")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to get provider" in result.error

    @pytest.mark.asyncio
    async def test_list_providers_returns_ok(self, client):
        """Test list_providers returns Ok on success."""
        with patch.object(
            client._provider_registry, "list_providers", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []

            result = await client.list_providers()

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap() == []

    @pytest.mark.asyncio
    async def test_list_providers_catches_exceptions(self, client):
        """Test list_providers catches and wraps exceptions."""
        with patch.object(
            client._provider_registry, "list_providers", new_callable=AsyncMock
        ) as mock_list:
            mock_list.side_effect = Exception("List failed")

            result = await client.list_providers()

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to list providers" in result.error

    @pytest.mark.asyncio
    async def test_remove_provider_returns_ok(self, client):
        """Test remove_provider returns Ok on success."""
        with patch.object(
            client._provider_registry, "remove_provider", new_callable=AsyncMock
        ) as mock_remove:
            mock_remove.return_value = True

            result = await client.remove_provider("test-provider")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_remove_provider_catches_exceptions(self, client):
        """Test remove_provider catches and wraps exceptions."""
        with patch.object(
            client._provider_registry, "remove_provider", new_callable=AsyncMock
        ) as mock_remove:
            mock_remove.side_effect = Exception("Remove failed")

            result = await client.remove_provider("test-provider")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to remove provider" in result.error

    @pytest.mark.asyncio
    async def test_update_provider_returns_ok(self, client):
        """Test update_provider returns Ok on success."""
        from dawn_kestrel.core.provider_config import ProviderConfig

        mock_config = ProviderConfig(
            provider_id="test",
            model="test-model",
            api_key=None,
            is_default=False,
        )

        with patch.object(
            client._provider_registry, "update_provider", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = mock_config

            result = await client.update_provider("test-provider", "test", "test-model")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().model == "test-model"

    @pytest.mark.asyncio
    async def test_update_provider_catches_exceptions(self, client):
        """Test update_provider catches and wraps exceptions."""
        with patch.object(
            client._provider_registry, "update_provider", new_callable=AsyncMock
        ) as mock_update:
            mock_update.side_effect = Exception("Update failed")

            result = await client.update_provider("test-provider", "test", "test-model")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "SessionError"
            assert "Failed to update provider" in result.error


class TestSyncClientExceptionWrapping:
    """Test that sync SDK client wraps exceptions in Result types."""

    @pytest.fixture
    def client(self):
        """Create sync client for testing."""
        with patch("dawn_kestrel.sdk.client.SessionStorage"):
            client = OpenCodeSyncClient()
        return client

    def test_create_session_returns_ok(self, client):
        """Test create_session returns Ok on success."""
        with patch.object(
            client._async_client, "create_session", new_callable=AsyncMock
        ) as mock_create:
            from dawn_kestrel.core.models import Session

            mock_session = Session(
                id="test-id",
                slug="test-slug",
                project_id="test",
                directory="/tmp/test",
                parent_id=None,
                title="Test Session",
                version="1.0.0",
                time_created=0,
                time_updated=0,
            )
            mock_create.return_value = Ok(mock_session)

            result = client.create_session("Test Session")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().title == "Test Session"

    def test_create_session_wraps_async_result(self, client):
        """Test create_session passes through async Result."""
        with patch.object(
            client._async_client, "create_session", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = Err("Async error", code="AsyncError")

            result = client.create_session("Test Session")

            assert isinstance(result, Err)
            assert result.is_err()
            assert result.code == "AsyncError"

    def test_get_session_returns_ok(self, client):
        """Test get_session returns Ok on success."""
        with patch.object(client._async_client, "get_session", new_callable=AsyncMock) as mock_get:
            from dawn_kestrel.core.models import Session

            mock_session = Session(
                id="test-id",
                slug="test-slug",
                project_id="test",
                directory="/tmp/test",
                parent_id=None,
                title="Test Session",
                version="1.0.0",
                time_created=0,
                time_updated=0,
            )
            mock_get.return_value = Ok(mock_session)

            result = client.get_session("test-id")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().id == "test-id"

    def test_list_sessions_returns_ok(self, client):
        """Test list_sessions returns Ok on success."""
        with patch.object(
            client._async_client, "list_sessions", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = Ok([])

            result = client.list_sessions()

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap() == []

    def test_delete_session_returns_ok(self, client):
        """Test delete_session returns Ok on success."""
        with patch.object(
            client._async_client, "delete_session", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = Ok(True)

            result = client.delete_session("test-id")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap() is True

    def test_add_message_returns_ok(self, client):
        """Test add_message returns Ok on success."""
        with patch.object(client._async_client, "add_message", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = Ok("message-id")

            result = client.add_message("test-id", "user", "Hello")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap() == "message-id"

    def test_register_agent_returns_ok(self, client):
        """Test register_agent returns Ok on success."""
        with patch.object(
            client._async_client, "register_agent", new_callable=AsyncMock
        ) as mock_reg:
            mock_reg.return_value = Ok({"name": "test-agent"})

            result = client.register_agent({"name": "test-agent"})

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap()["name"] == "test-agent"

    def test_get_agent_returns_ok(self, client):
        """Test get_agent returns Ok on success."""
        with patch.object(client._async_client, "get_agent", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Ok({"name": "test-agent"})

            result = client.get_agent("test-agent")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap()["name"] == "test-agent"

    def test_execute_agent_returns_ok(self, client):
        """Test execute_agent returns Ok on success."""
        from dawn_kestrel.core.agent_types import AgentResult

        mock_result = AgentResult(
            agent_name="test-agent",
            response="Test response",
            parts=[],
            metadata={},
            tools_used=[],
            duration=100,
            error=None,
        )

        with patch.object(
            client._async_client, "execute_agent", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = Ok(mock_result)

            result = client.execute_agent("test-agent", "test-id", "Hello")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().response == "Test response"

    def test_register_provider_returns_ok(self, client):
        """Test register_provider returns Ok on success."""
        from dawn_kestrel.core.provider_config import ProviderConfig

        mock_config = ProviderConfig(
            provider_id="test",
            model="test-model",
            api_key=None,
            is_default=False,
        )

        with patch.object(
            client._async_client, "register_provider", new_callable=AsyncMock
        ) as mock_reg:
            mock_reg.return_value = Ok(mock_config)

            result = client.register_provider("test-provider", "test", "test-model")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().model == "test-model"

    def test_get_provider_returns_ok(self, client):
        """Test get_provider returns Ok on success."""
        from dawn_kestrel.core.provider_config import ProviderConfig

        mock_config = ProviderConfig(
            provider_id="test",
            model="test-model",
            api_key=None,
            is_default=False,
        )

        with patch.object(client._async_client, "get_provider", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Ok(mock_config)

            result = client.get_provider("test-provider")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().model == "test-model"

    def test_list_providers_returns_ok(self, client):
        """Test list_providers returns Ok on success."""
        with patch.object(
            client._async_client, "list_providers", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = Ok([])

            result = client.list_providers()

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap() == []

    def test_remove_provider_returns_ok(self, client):
        """Test remove_provider returns Ok on success."""
        with patch.object(
            client._async_client, "remove_provider", new_callable=AsyncMock
        ) as mock_remove:
            mock_remove.return_value = Ok(True)

            result = client.remove_provider("test-provider")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap() is True

    def test_update_provider_returns_ok(self, client):
        """Test update_provider returns Ok on success."""
        from dawn_kestrel.core.provider_config import ProviderConfig

        mock_config = ProviderConfig(
            provider_id="test",
            model="test-model",
            api_key=None,
            is_default=False,
        )

        with patch.object(
            client._async_client, "update_provider", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = Ok(mock_config)

            result = client.update_provider("test-provider", "test", "test-model")

            assert isinstance(result, Ok)
            assert result.is_ok()
            assert result.unwrap().model == "test-model"
