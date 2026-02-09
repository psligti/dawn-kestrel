"""Tests for SessionService protocol and DefaultSessionService implementation.

Tests handler injection, method delegation, and proper handler usage
in session operations.
"""

from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
import pytest

from dawn_kestrel.core.services.session_service import (
    SessionService,
    DefaultSessionService,
)
from dawn_kestrel.core.models import Session
from dawn_kestrel.core.result import Ok, Err
from dawn_kestrel.interfaces.io import (
    IOHandler,
    ProgressHandler,
    NotificationHandler,
    Notification,
    NotificationType,
)


class TestSessionServiceProtocol:
    """Tests for SessionService protocol definition."""

    def test_session_service_protocol_has_list_sessions_method(self) -> None:
        """Test that SessionService protocol defines list_sessions method."""
        assert hasattr(SessionService, "list_sessions")
        assert callable(SessionService.list_sessions)

    def test_session_service_protocol_has_get_session_method(self) -> None:
        """Test that SessionService protocol defines get_session method."""
        assert hasattr(SessionService, "get_session")
        assert callable(SessionService.get_session)


@pytest.fixture
def mock_storage() -> AsyncMock:
    """Create mock SessionStorage (for backward compatibility tests)."""
    storage = AsyncMock()
    storage.base_dir = Path("/tmp/test")
    return storage


@pytest.fixture
def mock_session_repo() -> AsyncMock:
    """Create mock SessionRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_message_repo() -> AsyncMock:
    """Create mock MessageRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_part_repo() -> AsyncMock:
    """Create mock PartRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_io_handler() -> Mock:
    """Create mock IOHandler."""
    handler = Mock(spec=IOHandler)
    handler.prompt = AsyncMock(return_value="test_input")
    handler.confirm = AsyncMock(return_value=True)
    handler.select = AsyncMock(return_value="option1")
    handler.multi_select = AsyncMock(return_value=["option1", "option2"])
    return handler


@pytest.fixture
def mock_progress_handler() -> Mock:
    """Create mock ProgressHandler."""
    handler = Mock(spec=ProgressHandler)
    handler.start = Mock()
    handler.update = Mock()
    handler.complete = Mock()
    return handler


@pytest.fixture
def mock_notification_handler() -> Mock:
    """Create mock NotificationHandler."""
    handler = Mock(spec=NotificationHandler)
    handler.show = Mock()
    return handler


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create temporary project directory."""
    return tmp_path / "project"


class TestDefaultSessionServiceInitialization:
    """Tests for DefaultSessionService initialization with handler injection."""

    def test_default_session_service_with_handler_injection(
        self, mock_session_repo: AsyncMock, mock_message_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test DefaultSessionService initialization with handler injection."""
        mock_io = Mock(spec=IOHandler)
        mock_progress = Mock(spec=ProgressHandler)
        mock_notification = Mock(spec=NotificationHandler)

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            io_handler=mock_io,
            progress_handler=mock_progress,
            notification_handler=mock_notification,
        )

        assert service.project_dir == project_dir
        assert service._io_handler is mock_io
        assert service._progress_handler is mock_progress
        assert service._notification_handler is mock_notification

    def test_default_session_service_with_all_handlers_provided(
        self,
        mock_session_repo: AsyncMock,
        mock_message_repo: AsyncMock,
        project_dir: Path,
        mock_io_handler: Mock,
        mock_progress_handler: Mock,
        mock_notification_handler: Mock,
    ) -> None:
        """Test DefaultSessionService with all handlers provided."""
        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            io_handler=mock_io_handler,
            progress_handler=mock_progress_handler,
            notification_handler=mock_notification_handler,
        )

        assert service._io_handler is mock_io_handler
        assert service._progress_handler is mock_progress_handler
        assert service._notification_handler is mock_notification_handler

    def test_default_session_service_with_no_handlers_uses_noop_defaults(
        self, mock_session_repo: AsyncMock, mock_message_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test DefaultSessionService with no handlers (no-op defaults)."""
        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            io_handler=None,
            progress_handler=None,
            notification_handler=None,
        )

        from dawn_kestrel.interfaces.io import (
            QuietIOHandler,
            NoOpProgressHandler,
            NoOpNotificationHandler,
        )

        assert isinstance(service._io_handler, QuietIOHandler)
        assert isinstance(service._progress_handler, NoOpProgressHandler)
        assert isinstance(service._notification_handler, NoOpNotificationHandler)

    def test_default_session_service_backward_compatibility_with_storage(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test DefaultSessionService with storage parameter (backward compatibility)."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
        )

        assert service.storage is mock_storage
        assert service.project_dir == project_dir
        assert service._manager is not None


class TestDefaultSessionServiceListSessions:
    """Tests for DefaultSessionService.list_sessions method."""

    @pytest.mark.asyncio
    async def test_list_sessions_delegates_to_repository(
        self, mock_session_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test list_sessions() delegates to repository.list_by_project()."""
        expected_sessions = [
            Session(
                id="1",
                title="Session 1",
                slug="session-1",
                project_id="test",
                directory="/test",
                version="1.0.0",
            ),
            Session(
                id="2",
                title="Session 2",
                slug="session-2",
                project_id="test",
                directory="/test",
                version="1.0.0",
            ),
        ]
        mock_session_repo.list_by_project = AsyncMock(return_value=Ok(expected_sessions))

        mock_message_repo = AsyncMock()
        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
        )

        sessions = await service.list_sessions()

        mock_session_repo.list_by_project.assert_awaited_once()
        assert len(sessions) == 2
        assert all(isinstance(s, Session) for s in sessions)

    @pytest.mark.asyncio
    async def test_list_sessions_returns_list_of_session_objects(
        self, mock_session_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test list_sessions() returns list of Session objects."""
        expected_sessions = [
            Session(
                id="1",
                title="Session 1",
                slug="session-1",
                project_id="test",
                directory="/test",
                version="1.0.0",
            ),
            Session(
                id="2",
                title="Session 2",
                slug="session-2",
                project_id="test",
                directory="/test",
                version="1.0.0",
            ),
        ]
        mock_session_repo.list_by_project = AsyncMock(return_value=Ok(expected_sessions))

        mock_message_repo = AsyncMock()
        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
        )

        sessions = await service.list_sessions()

        assert len(sessions) == 2
        assert all(isinstance(s, Session) for s in sessions)
        assert sessions[0].id == "1"
        assert sessions[1].id == "2"

    @pytest.mark.asyncio
    async def test_list_sessions_calls_notification_handler_on_success(
        self, mock_session_repo: AsyncMock, project_dir: Path, mock_notification_handler: Mock
    ) -> None:
        """Test list_sessions() calls notification_handler on success."""
        expected_sessions = [
            Session(
                id="1",
                title="Session 1",
                slug="session-1",
                project_id="test",
                directory="/test",
                version="1.0.0",
            ),
            Session(
                id="2",
                title="Session 2",
                slug="session-2",
                project_id="test",
                directory="/test",
                version="1.0.0",
            ),
        ]
        mock_session_repo.list_by_project = AsyncMock(return_value=Ok(expected_sessions))

        mock_message_repo = AsyncMock()
        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            notification_handler=mock_notification_handler,
        )

        await service.list_sessions()

        assert not mock_notification_handler.show.called


class TestDefaultSessionServiceGetSession:
    """Tests for DefaultSessionService.get_session method."""

    @pytest.mark.asyncio
    async def test_get_session_delegates_to_repository(
        self, mock_session_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test get_session() delegates to repository.get_by_id()."""
        expected_session = Session(
            id="test-id",
            title="Test Session",
            slug="test-session",
            project_id="test",
            directory="/test",
            version="1.0.0",
        )
        mock_session_repo.get_by_id = AsyncMock(return_value=Ok(expected_session))

        mock_message_repo = AsyncMock()
        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
        )

        session = await service.get_session("test-id")

        mock_session_repo.get_by_id.assert_awaited_once_with("test-id")
        assert session is not None
        assert session.id == "test-id"

    @pytest.mark.asyncio
    async def test_get_session_returns_session_when_found(
        self, mock_session_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test get_session() returns Session object when found."""
        expected_session = Session(
            id="test-id",
            title="Test Session",
            slug="test-session",
            project_id="test",
            directory="/test",
            version="1.0.0",
        )
        mock_session_repo.get_by_id = AsyncMock(return_value=Ok(expected_session))

        mock_message_repo = AsyncMock()
        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
        )

        session = await service.get_session("test-id")

        assert session is not None
        assert isinstance(session, Session)
        assert session.id == "test-id"

    @pytest.mark.asyncio
    async def test_get_session_returns_none_when_not_found(
        self, mock_session_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test get_session() returns None when not found."""
        mock_session_repo.get_by_id = AsyncMock(return_value=Err("Not found", code="NOT_FOUND"))

        mock_message_repo = AsyncMock()
        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
        )

        session = await service.get_session("nonexistent-id")

        assert session is None


class TestDefaultSessionServiceGetExportData:
    """Tests for DefaultSessionService.get_export_data method."""

    @pytest.mark.asyncio
    async def test_get_export_data_calls_progress_handler_start(
        self,
        mock_session_repo: AsyncMock,
        mock_message_repo: AsyncMock,
        project_dir: Path,
        mock_progress_handler: Mock,
    ) -> None:
        """Test get_export_data() calls progress_handler.start()."""
        session = Session(
            id="test-id",
            title="Test",
            slug="test",
            project_id="test",
            directory="/test",
            version="1.0.0",
        )
        mock_session_repo.get_by_id = AsyncMock(return_value=Ok(session))
        mock_message_repo.list_by_session = AsyncMock(return_value=Ok([]))

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            progress_handler=mock_progress_handler,
        )

        await service.get_export_data("test-session-id")

        mock_progress_handler.start.assert_called_once_with("Exporting session", 100)

    @pytest.mark.asyncio
    async def test_get_export_data_calls_progress_handler_update(
        self,
        mock_session_repo: AsyncMock,
        mock_message_repo: AsyncMock,
        project_dir: Path,
        mock_progress_handler: Mock,
    ) -> None:
        """Test get_export_data() calls progress_handler.update()."""
        session = Session(
            id="test-id",
            title="Test",
            slug="test",
            project_id="test",
            directory="/test",
            version="1.0.0",
        )
        mock_session_repo.get_by_id = AsyncMock(return_value=Ok(session))
        mock_message_repo.list_by_session = AsyncMock(return_value=Ok([]))

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            progress_handler=mock_progress_handler,
        )

        await service.get_export_data("test-session-id")

        assert mock_progress_handler.update.call_count == 2
        mock_progress_handler.update.assert_any_call(50, "Loading session test-session-id")
        mock_progress_handler.update.assert_any_call(100, "Export complete")

    @pytest.mark.asyncio
    async def test_get_export_data_calls_progress_handler_complete(
        self,
        mock_session_repo: AsyncMock,
        mock_message_repo: AsyncMock,
        project_dir: Path,
        mock_progress_handler: Mock,
    ) -> None:
        """Test get_export_data() calls progress_handler.complete()."""
        session = Session(
            id="test-id",
            title="Test",
            slug="test",
            project_id="test",
            directory="/test",
            version="1.0.0",
        )
        mock_session_repo.get_by_id = AsyncMock(return_value=Ok(session))
        mock_message_repo.list_by_session = AsyncMock(return_value=Ok([]))

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            progress_handler=mock_progress_handler,
        )

        await service.get_export_data("test-session-id")

        mock_progress_handler.complete.assert_called_once_with("Session exported successfully")

    @pytest.mark.asyncio
    async def test_get_export_data_calls_notification_handler_on_success(
        self,
        mock_session_repo: AsyncMock,
        mock_message_repo: AsyncMock,
        project_dir: Path,
        mock_notification_handler: Mock,
    ) -> None:
        """Test get_export_data() calls notification_handler.show() on success."""
        session = Session(
            id="test-id",
            title="Test",
            slug="test",
            project_id="test",
            directory="/test",
            version="1.0.0",
        )
        mock_session_repo.get_by_id = AsyncMock(return_value=Ok(session))
        mock_message_repo.list_by_session = AsyncMock(return_value=Ok([]))

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            notification_handler=mock_notification_handler,
        )

        await service.get_export_data("test-session-id")

        mock_notification_handler.show.assert_called_once()
        notification_arg = mock_notification_handler.show.call_args[0][0]
        assert isinstance(notification_arg, Notification)
        assert notification_arg.notification_type == NotificationType.SUCCESS


class TestDefaultSessionServiceImportSession:
    """Tests for DefaultSessionService.import_session method."""

    @pytest.mark.asyncio
    async def test_import_session_calls_progress_handler_start(
        self,
        mock_session_repo: AsyncMock,
        mock_message_repo: AsyncMock,
        project_dir: Path,
        mock_progress_handler: Mock,
    ) -> None:
        """Test import_session() calls progress_handler.start()."""
        mock_session_repo.get_by_id = AsyncMock(return_value=Err("Not found", code="NOT_FOUND"))
        mock_session_repo.create = AsyncMock(
            return_value=Ok(
                Session(
                    id="test-id",
                    title="Test Session",
                    slug="test-session",
                    project_id="test",
                    directory="/test",
                    version="1.0.0",
                )
            )
        )

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            progress_handler=mock_progress_handler,
        )
        session_data = {
            "session": {"id": "test-id", "title": "Test Session"},
            "messages": [],
        }

        await service.import_session(session_data)

        mock_progress_handler.start.assert_called_once_with("Importing session", 100)

    @pytest.mark.asyncio
    async def test_import_session_creates_session_via_repository(
        self, mock_session_repo: AsyncMock, mock_message_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test import_session() creates session via repository."""
        mock_session_repo.get_by_id = AsyncMock(return_value=Err("Not found", code="NOT_FOUND"))
        expected_session = Session(
            id="test-id",
            title="Test Session",
            slug="test-session",
            project_id="test",
            directory="/test",
            version="1.0.0",
        )
        mock_session_repo.create = AsyncMock(return_value=Ok(expected_session))

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
        )
        session_data = {
            "session": {"id": "test-id", "title": "Test Session"},
            "messages": [],
        }

        result = await service.import_session(session_data)

        mock_session_repo.create.assert_awaited_once()
        assert result.id == "test-id"

    @pytest.mark.asyncio
    async def test_import_session_calls_progress_handler_complete(
        self,
        mock_session_repo: AsyncMock,
        mock_message_repo: AsyncMock,
        project_dir: Path,
        mock_progress_handler: Mock,
    ) -> None:
        """Test import_session() calls progress_handler.complete()."""
        mock_session_repo.get_by_id = AsyncMock(return_value=Err("Not found", code="NOT_FOUND"))
        mock_session_repo.create = AsyncMock(
            return_value=Ok(
                Session(
                    id="test-id",
                    title="Test Session",
                    slug="test-session",
                    project_id="test",
                    directory="/test",
                    version="1.0.0",
                )
            )
        )

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            progress_handler=mock_progress_handler,
        )
        session_data = {
            "session": {"id": "test-id", "title": "Test Session"},
            "messages": [],
        }

        await service.import_session(session_data)

        mock_progress_handler.complete.assert_called_once_with("Session imported successfully")

    @pytest.mark.asyncio
    async def test_import_session_calls_notification_handler_on_success(
        self,
        mock_session_repo: AsyncMock,
        mock_message_repo: AsyncMock,
        project_dir: Path,
        mock_notification_handler: Mock,
    ) -> None:
        """Test import_session() calls notification_handler.show() on success."""
        mock_session_repo.get_by_id = AsyncMock(return_value=Err("Not found", code="NOT_FOUND"))
        mock_session_repo.create = AsyncMock(
            return_value=Ok(
                Session(
                    id="test-id",
                    title="Test Session",
                    slug="test-session",
                    project_id="test",
                    directory="/test",
                    version="1.0.0",
                )
            )
        )

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            notification_handler=mock_notification_handler,
        )
        session_data = {
            "session": {"id": "test-id", "title": "Test Session"},
            "messages": [],
        }

        await service.import_session(session_data)

        mock_notification_handler.show.assert_called_once()
        notification_arg = mock_notification_handler.show.call_args[0][0]
        assert isinstance(notification_arg, Notification)
        assert notification_arg.notification_type == NotificationType.SUCCESS


class TestDefaultSessionServiceHandlerTypes:
    """Tests for handler type validation."""

    def test_all_methods_use_correct_handler_types(
        self, mock_session_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test all methods use correct handler types (IOHandler, ProgressHandler, NotificationHandler)."""
        from dawn_kestrel.interfaces.io import (
            QuietIOHandler,
            NoOpProgressHandler,
            NoOpNotificationHandler,
        )

        mock_message_repo = AsyncMock()
        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
        )

        assert isinstance(service._io_handler, QuietIOHandler)
        assert isinstance(service._progress_handler, NoOpProgressHandler)
        assert isinstance(service._notification_handler, NoOpNotificationHandler)

        assert hasattr(service._io_handler, "prompt")
        assert hasattr(service._io_handler, "confirm")
        assert hasattr(service._progress_handler, "start")
        assert hasattr(service._progress_handler, "update")
        assert hasattr(service._progress_handler, "complete")
        assert hasattr(service._notification_handler, "show")

    def test_mock_handlers_with_async_mock_for_async_methods(
        self, mock_session_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test mock handlers with AsyncMock for async methods, Mock for sync methods."""
        mock_io = Mock(spec=IOHandler)
        mock_io.prompt = AsyncMock(return_value="test")
        mock_io.confirm = AsyncMock(return_value=True)

        mock_progress = Mock(spec=ProgressHandler)
        mock_progress.start = Mock()
        mock_progress.update = Mock()
        mock_progress.complete = Mock()

        mock_notification = Mock(spec=NotificationHandler)
        mock_notification.show = Mock()

        mock_message_repo = AsyncMock()
        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            io_handler=mock_io,
            progress_handler=mock_progress,
            notification_handler=mock_notification,
        )

        assert isinstance(service._io_handler, Mock)
        assert isinstance(service._progress_handler, Mock)
        assert isinstance(service._notification_handler, Mock)


class TestSessionServiceRepositoryIntegration:
    """Tests for repository integration in SessionService."""

    @pytest.mark.asyncio
    async def test_create_session_uses_session_repository(
        self, mock_session_repo: AsyncMock, mock_message_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test create_session() uses session repository."""
        expected_session = Session(
            id="test-id",
            title="Test Session",
            slug="test-session",
            project_id="test",
            directory="/test",
            version="1.0.0",
        )
        mock_session_repo.create = AsyncMock(return_value=Ok(expected_session))

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            io_handler=Mock(spec=IOHandler),
        )

        session = await service.create_session("Test Session")

        mock_session_repo.create.assert_awaited_once()
        assert session.id == "test-id"
        assert session.title == "Test Session"

    @pytest.mark.asyncio
    async def test_repository_error_propagates_to_session_service(
        self, mock_session_repo: AsyncMock, mock_message_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test repository errors propagate to SessionService Result-returning methods."""
        mock_session_repo.create = AsyncMock(
            return_value=Err("Database error", code="STORAGE_ERROR")
        )

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            io_handler=Mock(spec=IOHandler),
        )

        result = await service.create_session_result("Test Session")

        assert result.is_err()
        assert "Database error" in result.error

    @pytest.mark.asyncio
    async def test_repository_ok_returns_session(
        self, mock_session_repo: AsyncMock, mock_message_repo: AsyncMock, project_dir: Path
    ) -> None:
        """Test repository Ok returns session in SessionService."""
        expected_session = Session(
            id="test-id",
            title="Test Session",
            slug="test-session",
            project_id="test",
            directory="/test",
            version="1.0.0",
        )
        mock_session_repo.create = AsyncMock(return_value=Ok(expected_session))

        service = DefaultSessionService(
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            project_dir=project_dir,
            io_handler=Mock(spec=IOHandler),
        )

        result = await service.create_session_result("Test Session")

        assert result.is_ok()
        session = result.unwrap()
        assert session.id == "test-id"
        assert session.title == "Test Session"
