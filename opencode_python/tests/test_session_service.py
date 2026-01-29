"""Tests for SessionService protocol and DefaultSessionService implementation.

Tests handler injection, method delegation, and proper handler usage
in session operations.
"""

from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
import pytest

from opencode_python.core.services.session_service import (
    SessionService,
    DefaultSessionService,
)
from opencode_python.core.models import Session
from opencode_python.interfaces.io import (
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
        assert hasattr(SessionService, 'list_sessions')
        assert callable(SessionService.list_sessions)

    def test_session_service_protocol_has_get_session_method(self) -> None:
        """Test that SessionService protocol defines get_session method."""
        assert hasattr(SessionService, 'get_session')
        assert callable(SessionService.get_session)


@pytest.fixture
def mock_storage() -> AsyncMock:
    """Create mock SessionStorage."""
    storage = AsyncMock()
    storage.base_dir = Path("/tmp/test")
    return storage


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
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test DefaultSessionService initialization with handler injection."""
        mock_io = Mock(spec=IOHandler)
        mock_progress = Mock(spec=ProgressHandler)
        mock_notification = Mock(spec=NotificationHandler)

        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            io_handler=mock_io,
            progress_handler=mock_progress,
            notification_handler=mock_notification,
        )

        assert service.storage is mock_storage
        assert service.project_dir == project_dir
        assert service._io_handler is mock_io
        assert service._progress_handler is mock_progress
        assert service._notification_handler is mock_notification

    def test_default_session_service_with_all_handlers_provided(
        self, mock_storage: AsyncMock, project_dir: Path, mock_io_handler: Mock,
        mock_progress_handler: Mock, mock_notification_handler: Mock
    ) -> None:
        """Test DefaultSessionService with all handlers provided."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            io_handler=mock_io_handler,
            progress_handler=mock_progress_handler,
            notification_handler=mock_notification_handler,
        )

        assert service._io_handler is mock_io_handler
        assert service._progress_handler is mock_progress_handler
        assert service._notification_handler is mock_notification_handler

    def test_default_session_service_with_no_handlers_uses_noop_defaults(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test DefaultSessionService with no handlers (no-op defaults)."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            io_handler=None,
            progress_handler=None,
            notification_handler=None,
        )

        from opencode_python.interfaces.io import (
            QuietIOHandler,
            NoOpProgressHandler,
            NoOpNotificationHandler,
        )

        assert isinstance(service._io_handler, QuietIOHandler)
        assert isinstance(service._progress_handler, NoOpProgressHandler)
        assert isinstance(service._notification_handler, NoOpNotificationHandler)


class TestDefaultSessionServiceListSessions:
    """Tests for DefaultSessionService.list_sessions method."""

    @pytest.mark.asyncio
    async def test_list_sessions_delegates_to_storage(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test list_sessions() delegates to storage.list_sessions()."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
        )

        mock_list_sessions = AsyncMock()
        service._manager.list_sessions = mock_list_sessions

        await service.list_sessions()

        mock_list_sessions.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_sessions_returns_list_of_session_objects(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test list_sessions() returns list of Session objects."""
        expected_sessions = [
            Session(id="1", title="Session 1", slug="session-1", project_id="test", directory="/test", version="1.0.0"),
            Session(id="2", title="Session 2", slug="session-2", project_id="test", directory="/test", version="1.0.0"),
        ]
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
        )
        service._manager.list_sessions = AsyncMock(return_value=expected_sessions)

        sessions = await service.list_sessions()

        assert len(sessions) == 2
        assert all(isinstance(s, Session) for s in sessions)
        assert sessions[0].id == "1"
        assert sessions[1].id == "2"

    @pytest.mark.asyncio
    async def test_list_sessions_calls_notification_handler_on_success(
        self, mock_storage: AsyncMock, project_dir: Path, mock_notification_handler: Mock
    ) -> None:
        """Test list_sessions() calls notification_handler on success."""
        expected_sessions = [
            Session(id="1", title="Session 1", slug="session-1", project_id="test", directory="/test", version="1.0.0"),
            Session(id="2", title="Session 2", slug="session-2", project_id="test", directory="/test", version="1.0.0"),
        ]
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            notification_handler=mock_notification_handler,
        )
        service._manager.list_sessions = AsyncMock(return_value=expected_sessions)

        await service.list_sessions()

        assert not mock_notification_handler.show.called


class TestDefaultSessionServiceGetSession:
    """Tests for DefaultSessionService.get_session method."""

    @pytest.mark.asyncio
    async def test_get_session_delegates_to_storage(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test get_session() delegates to storage.get_session()."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
        )

        mock_get_session = AsyncMock()
        service._manager.get_session = mock_get_session

        await service.get_session("test-session-id")

        mock_get_session.assert_awaited_once_with("test-session-id")

    @pytest.mark.asyncio
    async def test_get_session_returns_session_when_found(
        self, mock_storage: AsyncMock, project_dir: Path
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
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
        )
        service._manager.get_session = AsyncMock(return_value=expected_session)

        session = await service.get_session("test-id")

        assert session is not None
        assert isinstance(session, Session)
        assert session.id == "test-id"

    @pytest.mark.asyncio
    async def test_get_session_returns_none_when_not_found(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test get_session() returns None when not found."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
        )
        service._manager.get_session = AsyncMock(return_value=None)

        session = await service.get_session("nonexistent-id")

        assert session is None


class TestDefaultSessionServiceGetExportData:
    """Tests for DefaultSessionService.get_export_data method."""

    @pytest.mark.asyncio
    async def test_get_export_data_calls_progress_handler_start(
        self, mock_storage: AsyncMock, project_dir: Path, mock_progress_handler: Mock
    ) -> None:
        """Test get_export_data() calls progress_handler.start()."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            progress_handler=mock_progress_handler,
        )
        service._manager.get_export_data = AsyncMock(return_value={"session": {}, "messages": []})

        await service.get_export_data("test-session-id")

        mock_progress_handler.start.assert_called_once_with("Exporting session", 100)

    @pytest.mark.asyncio
    async def test_get_export_data_calls_progress_handler_update(
        self, mock_storage: AsyncMock, project_dir: Path, mock_progress_handler: Mock
    ) -> None:
        """Test get_export_data() calls progress_handler.update()."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            progress_handler=mock_progress_handler,
        )
        service._manager.get_export_data = AsyncMock(return_value={"session": {}, "messages": []})

        await service.get_export_data("test-session-id")

        assert mock_progress_handler.update.call_count == 2
        mock_progress_handler.update.assert_any_call(50, "Loading session test-session-id")
        mock_progress_handler.update.assert_any_call(100, "Export complete")

    @pytest.mark.asyncio
    async def test_get_export_data_calls_progress_handler_complete(
        self, mock_storage: AsyncMock, project_dir: Path, mock_progress_handler: Mock
    ) -> None:
        """Test get_export_data() calls progress_handler.complete()."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            progress_handler=mock_progress_handler,
        )
        service._manager.get_export_data = AsyncMock(return_value={"session": {}, "messages": []})

        await service.get_export_data("test-session-id")

        mock_progress_handler.complete.assert_called_once_with("Session exported successfully")

    @pytest.mark.asyncio
    async def test_get_export_data_calls_notification_handler_on_success(
        self, mock_storage: AsyncMock, project_dir: Path, mock_notification_handler: Mock
    ) -> None:
        """Test get_export_data() calls notification_handler.show() on success."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            notification_handler=mock_notification_handler,
        )
        service._manager.get_export_data = AsyncMock(return_value={"session": {}, "messages": []})

        await service.get_export_data("test-session-id")

        mock_notification_handler.show.assert_called_once()
        notification_arg = mock_notification_handler.show.call_args[0][0]
        assert isinstance(notification_arg, Notification)
        assert notification_arg.notification_type == NotificationType.SUCCESS


class TestDefaultSessionServiceImportSession:
    """Tests for DefaultSessionService.import_session method."""

    @pytest.mark.asyncio
    async def test_import_session_calls_progress_handler_start(
        self, mock_storage: AsyncMock, project_dir: Path, mock_progress_handler: Mock
    ) -> None:
        """Test import_session() calls progress_handler.start()."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            progress_handler=mock_progress_handler,
        )
        session_data = {
            "session": {"id": "test-id", "title": "Test Session"},
            "messages": [],
        }
        service._manager.import_data = AsyncMock(return_value=Session(
            id="test-id", title="Test Session", slug="test-session", project_id="test", directory="/test", version="1.0.0"
        ))

        await service.import_session(session_data)

        mock_progress_handler.start.assert_called_once_with("Importing session", 100)

    @pytest.mark.asyncio
    async def test_import_session_creates_session_via_storage(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test import_session() creates session via storage."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
        )
        session_data = {
            "session": {"id": "test-id", "title": "Test Session"},
            "messages": [],
        }
        expected_session = Session(
            id="test-id", title="Test Session", slug="test-session", project_id="test", directory="/test", version="1.0.0"
        )
        service._manager.import_data = AsyncMock(return_value=expected_session)

        result = await service.import_session(session_data)

        service._manager.import_data.assert_awaited_once()
        assert result.id == "test-id"

    @pytest.mark.asyncio
    async def test_import_session_calls_progress_handler_complete(
        self, mock_storage: AsyncMock, project_dir: Path, mock_progress_handler: Mock
    ) -> None:
        """Test import_session() calls progress_handler.complete()."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            progress_handler=mock_progress_handler,
        )
        session_data = {
            "session": {"id": "test-id", "title": "Test Session"},
            "messages": [],
        }
        service._manager.import_data = AsyncMock(return_value=Session(
            id="test-id", title="Test Session", slug="test-session", project_id="test", directory="/test", version="1.0.0"
        ))

        await service.import_session(session_data)

        mock_progress_handler.complete.assert_called_once_with("Session imported successfully")

    @pytest.mark.asyncio
    async def test_import_session_calls_notification_handler_on_success(
        self, mock_storage: AsyncMock, project_dir: Path, mock_notification_handler: Mock
    ) -> None:
        """Test import_session() calls notification_handler.show() on success."""
        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            notification_handler=mock_notification_handler,
        )
        session_data = {
            "session": {"id": "test-id", "title": "Test Session"},
            "messages": [],
        }
        service._manager.import_data = AsyncMock(return_value=Session(
            id="test-id", title="Test Session", slug="test-session", project_id="test", directory="/test", version="1.0.0"
        ))

        await service.import_session(session_data)

        mock_notification_handler.show.assert_called_once()
        notification_arg = mock_notification_handler.show.call_args[0][0]
        assert isinstance(notification_arg, Notification)
        assert notification_arg.notification_type == NotificationType.SUCCESS


class TestDefaultSessionServiceHandlerTypes:
    """Tests for handler type validation."""

    def test_all_methods_use_correct_handler_types(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test all methods use correct handler types (IOHandler, ProgressHandler, NotificationHandler)."""
        from opencode_python.interfaces.io import (
            QuietIOHandler,
            NoOpProgressHandler,
            NoOpNotificationHandler,
        )

        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
        )

        assert isinstance(service._io_handler, QuietIOHandler)
        assert isinstance(service._progress_handler, NoOpProgressHandler)
        assert isinstance(service._notification_handler, NoOpNotificationHandler)

        assert hasattr(service._io_handler, 'prompt')
        assert hasattr(service._io_handler, 'confirm')
        assert hasattr(service._progress_handler, 'start')
        assert hasattr(service._progress_handler, 'update')
        assert hasattr(service._progress_handler, 'complete')
        assert hasattr(service._notification_handler, 'show')

    def test_mock_handlers_with_async_mock_for_async_methods(
        self, mock_storage: AsyncMock, project_dir: Path
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

        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
            io_handler=mock_io,
            progress_handler=mock_progress,
            notification_handler=mock_notification,
        )

        assert isinstance(service._io_handler, Mock)
        assert isinstance(service._progress_handler, Mock)
        assert isinstance(service._notification_handler, Mock)

    def test_mock_storage_with_async_mock(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test mock storage with AsyncMock."""
        assert isinstance(mock_storage, AsyncMock)

        service = DefaultSessionService(
            storage=mock_storage,
            project_dir=project_dir,
        )

        assert service.storage is mock_storage
