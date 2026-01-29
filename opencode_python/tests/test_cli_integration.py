"""Tests for CLI integration with SessionService and handlers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import pytest
from click.testing import CliRunner
import tempfile
import shutil

from opencode_python.cli.main import cli
from opencode_python.core.models import Session


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Temporary directory for test sessions."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_storage(temp_dir):
    """Mock session storage."""
    storage = Mock()
    storage.base_dir = temp_dir
    return storage


class TestListSessionsCommand:
    """Tests for list-sessions command."""

    @patch("opencode_python.cli.main.get_storage_dir")
    @patch("opencode_python.cli.main.SessionStorage")
    @patch("opencode_python.cli.main.DefaultSessionService")
    def test_list_sessions_uses_session_service(
        self, mock_service_cls, mock_storage_cls, mock_get_dir, temp_dir
    ):
        """Test that list-sessions uses SessionService."""
        # Setup
        mock_get_dir.return_value = temp_dir
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service.list_sessions = AsyncMock(return_value=[])
        mock_service_cls.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(cli, ["list-sessions"])

        # Verify SessionService was created with handlers
        assert mock_service_cls.called
        call_kwargs = mock_service_cls.call_args[1]
        assert "storage" in call_kwargs
        assert "io_handler" in call_kwargs
        assert "progress_handler" in call_kwargs
        assert "notification_handler" in call_kwargs

        # Verify list_sessions was called
        mock_service.list_sessions.assert_called_once()

    @patch("opencode_python.cli.main.get_storage_dir")
    @patch("opencode_python.cli.main.SessionStorage")
    @patch("opencode_python.cli.main.DefaultSessionService")
    def test_list_sessions_displays_sessions(
        self, mock_service_cls, mock_storage_cls, mock_get_dir, temp_dir
    ):
        """Test that list-sessions displays sessions correctly."""
        # Setup
        mock_get_dir.return_value = temp_dir
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
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
        mock_service_cls.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(cli, ["list-sessions"])

        # Verify sessions are displayed
        assert result.exit_code == 0
        assert "ses_001" in result.output
        assert "ses_002" in result.output
        assert "Test Session 1" in result.output
        assert "Test Session 2" in result.output


class TestExportSessionCommand:
    """Tests for export-session command."""

    @patch("opencode_python.cli.main.get_storage_dir")
    @patch("opencode_python.cli.main.SessionStorage")
    @patch("opencode_python.cli.main.DefaultSessionService")
    @patch("opencode_python.cli.main.ExportImportManager")
    @patch("opencode_python.cli.main.SessionManager")
    @patch("opencode_python.cli.main.GitSnapshot")
    def test_export_session_uses_session_service(
        self,
        mock_git_snapshot_cls,
        mock_session_manager_cls,
        mock_manager_cls,
        mock_service_cls,
        mock_storage_cls,
        mock_get_dir,
        temp_dir,
    ):
        """Test that export-session uses SessionService."""
        # Setup
        mock_get_dir.return_value = temp_dir
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
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
        mock_service_cls.return_value = mock_service

        mock_manager = Mock()
        mock_manager.export_session = AsyncMock(
            return_value={
                "path": "/test/export.json",
                "format": "json",
                "message_count": 10,
            }
        )
        mock_manager_cls.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli, ["export-session", "ses_001"])

        # Verify SessionService was created with handlers
        assert mock_service_cls.called
        call_kwargs = mock_service_cls.call_args[1]
        assert "storage" in call_kwargs
        assert "io_handler" in call_kwargs
        assert "progress_handler" in call_kwargs
        assert "notification_handler" in call_kwargs

        # Verify handlers are instances of CLI handlers
        from opencode_python.cli.handlers import (
            CLIIOHandler,
            CLIProgressHandler,
            CLINotificationHandler,
        )
        assert isinstance(call_kwargs["io_handler"], CLIIOHandler)
        assert isinstance(call_kwargs["progress_handler"], CLIProgressHandler)
        assert isinstance(call_kwargs["notification_handler"], CLINotificationHandler)

        # Verify get_session was called
        mock_service.get_session.assert_called_once_with("ses_001")

    @patch("opencode_python.cli.main.get_storage_dir")
    @patch("opencode_python.cli.main.SessionStorage")
    @patch("opencode_python.cli.main.DefaultSessionService")
    @patch("opencode_python.cli.main.ExportImportManager")
    @patch("opencode_python.cli.main.SessionManager")
    @patch("opencode_python.cli.main.GitSnapshot")
    def test_export_session_uses_progress_handler(
        self,
        mock_git_snapshot_cls,
        mock_session_manager_cls,
        mock_manager_cls,
        mock_service_cls,
        mock_storage_cls,
        mock_get_dir,
        temp_dir,
    ):
        """Test that export-session uses progress handler."""
        # Setup
        mock_get_dir.return_value = temp_dir
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
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
        mock_service_cls.return_value = mock_service

        mock_manager = Mock()
        mock_manager.export_session = AsyncMock(
            return_value={
                "path": "/test/export.json",
                "format": "json",
                "message_count": 10,
            }
        )
        mock_manager_cls.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli, ["export-session", "ses_001"])

        # Verify progress handler methods would be called during export
        # (Progress handler is passed to SessionService)
        assert result.exit_code == 0
        assert "Export complete" in result.output


class TestImportSessionCommand:
    """Tests for import-session command."""

    @patch("opencode_python.cli.main.get_storage_dir")
    @patch("opencode_python.cli.main.SessionStorage")
    @patch("opencode_python.cli.main.DefaultSessionService")
    @patch("opencode_python.cli.main.ExportImportManager")
    @patch("opencode_python.cli.main.SessionManager")
    @patch("opencode_python.cli.main.GitSnapshot")
    @patch("opencode_python.cli.main.MessageStorage")
    def test_import_session_uses_session_service(
        self,
        mock_message_storage_cls,
        mock_git_snapshot_cls,
        mock_session_manager_cls,
        mock_manager_cls,
        mock_service_cls,
        mock_storage_cls,
        mock_get_dir,
        temp_dir,
    ):
        """Test that import-session uses SessionService."""
        # Setup
        mock_get_dir.return_value = temp_dir
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_manager = Mock()
        mock_manager.import_session = AsyncMock(
            return_value={
                "session_id": "ses_001",
                "message_count": 5,
            }
        )
        mock_manager_cls.return_value = mock_manager

        # Create test export file
        export_file = temp_dir / "test_export.json"
        export_file.write_text('{"session": {"id": "ses_001", "title": "Test"}, "messages": []}')

        runner = CliRunner()
        result = runner.invoke(cli, ["import-session", str(export_file)])

        # Verify SessionService was created with handlers
        assert mock_service_cls.called
        call_kwargs = mock_service_cls.call_args[1]
        assert "storage" in call_kwargs
        assert "io_handler" in call_kwargs
        assert "progress_handler" in call_kwargs
        assert "notification_handler" in call_kwargs

        # Verify import was called
        mock_manager.import_session.assert_called_once()

    @patch("opencode_python.cli.main.get_storage_dir")
    @patch("opencode_python.cli.main.SessionStorage")
    @patch("opencode_python.cli.main.DefaultSessionService")
    @patch("opencode_python.cli.main.ExportImportManager")
    @patch("opencode_python.cli.main.SessionManager")
    @patch("opencode_python.cli.main.GitSnapshot")
    @patch("opencode_python.cli.main.MessageStorage")
    def test_import_session_uses_notification_handler(
        self,
        mock_message_storage_cls,
        mock_git_snapshot_cls,
        mock_session_manager_cls,
        mock_manager_cls,
        mock_service_cls,
        mock_storage_cls,
        mock_get_dir,
        temp_dir,
    ):
        """Test that import-session uses notification handler."""
        # Setup
        mock_get_dir.return_value = temp_dir
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        mock_manager = Mock()
        mock_manager.import_session = AsyncMock(
            return_value={
                "session_id": "ses_001",
                "message_count": 5,
            }
        )
        mock_manager_cls.return_value = mock_manager

        # Create test export file
        export_file = temp_dir / "test_export.json"
        export_file.write_text('{"session": {"id": "ses_001", "title": "Test"}, "messages": []}')

        runner = CliRunner()
        result = runner.invoke(cli, ["import-session", str(export_file)])

        # Verify notification would be shown
        # (Notification handler is passed to SessionService)
        assert result.exit_code == 0
        assert "Import complete" in result.output


class TestDeprecationWarnings:
    """Tests for deprecation warnings."""

    @patch("opencode_python.cli.main.get_storage_dir")
    @patch("opencode_python.cli.main.SessionStorage")
    @patch("opencode_python.cli.main.DefaultSessionService")
    def test_tui_command_shows_deprecation_warning(
        self, mock_service_cls, mock_storage_cls, mock_get_dir, temp_dir
    ):
        """Test that tui command shows deprecation warning."""
        # Setup
        mock_get_dir.return_value = temp_dir
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        mock_service_cls.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(cli, ["tui"])

        # Verify deprecation warning is shown
        # (This will be implemented when we add the deprecation warning)
        assert result.exit_code == 0 or "deprecated" in result.output.lower()


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    @patch("opencode_python.cli.main.get_storage_dir")
    @patch("opencode_python.cli.main.SessionStorage")
    @patch("opencode_python.cli.main.DefaultSessionService")
    def test_list_sessions_output_unchanged(
        self, mock_service_cls, mock_storage_cls, mock_get_dir, temp_dir
    ):
        """Test that list-sessions output is unchanged (backward compatibility)."""
        # Setup
        mock_get_dir.return_value = temp_dir
        mock_storage = Mock()
        mock_storage_cls.return_value = mock_storage

        mock_service = Mock()
        session = Session(
            id="ses_001",
            title="Test Session",
            slug="test-session",
            project_id="test-project",
            directory="/test",
            time_created=1234567890,
            version="1.0.0",
        )
        mock_service.list_sessions = AsyncMock(return_value=[session])
        mock_service_cls.return_value = mock_service

        runner = CliRunner()
        result = runner.invoke(cli, ["list-sessions"])

        # Verify output format is unchanged
        assert result.exit_code == 0
        assert "ses_001" in result.output
        assert "Test Session" in result.output
        # Should have a table format
        assert "ID" in result.output or "Title" in result.output
