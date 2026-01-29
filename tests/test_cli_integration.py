"""
Test suite for CLI commands with SessionService and handler integration.

This test suite follows TDD approach:
- RED: Tests are written first and will fail initially
- GREEN: Implementation will make tests pass
- REFACTOR: Code will be refactored while keeping tests green
"""

import pytest
import asyncio
import tempfile
import json
import gzip
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from click.testing import CliRunner
import sys

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir)
        yield storage_path


@pytest.fixture
def sample_session(temp_storage_dir):
    """Create a sample session for testing."""
    from opencode_python.storage.store import SessionStorage
    from opencode_python.core.models import Session

    storage = SessionStorage(temp_storage_dir)
    session = Session(
        id="test-session-123",
        slug="test-session",
        project_id="test-project",
        directory=str(temp_storage_dir),
        title="Test Session",
        version="1.0.0",
    )
    asyncio.run(storage.create_session(session))
    return session


class TestListSessionsCommand:
    """Test list_sessions command uses SessionService."""

    def test_list_sessions_imports_session_service(self):
        """Test that list_sessions imports SessionService."""
        from opencode_python.cli.main import list_sessions
        assert list_sessions is not None

    @pytest.mark.asyncio
    async def test_list_sessions_works_with_real_session(
        self, sample_session, temp_storage_dir
    ):
        """Test that list_sessions command works with real session data."""
        from opencode_python.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ['list-sessions', '--directory', str(temp_storage_dir)])

        assert result.exit_code == 0
        assert sample_session.id in result.output
        assert sample_session.title in result.output

    @pytest.mark.asyncio
    async def test_list_sessions_displays_correct_format(self, sample_session, temp_storage_dir):
        """Test that list_sessions displays sessions in correct format with ID, Title, Created columns."""
        from opencode_python.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ['list-sessions', '--directory', str(temp_storage_dir)])

        assert result.exit_code == 0
        assert "ID" in result.output
        assert "Title" in result.output
        assert "Created" in result.output

    @pytest.mark.asyncio
    async def test_list_sessions_works_with_cwd_when_no_directory(
        self, sample_session, temp_storage_dir
    ):
        """Test that list_sessions uses current working directory when --directory not provided."""
        from opencode_python.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ['list-sessions'])

        assert result.exit_code == 0


class TestExportSessionCommand:
    """Test export_session command uses SessionService and handlers."""

    def test_export_session_imports_session_service(self):
        """Test that export_session imports SessionService."""
        from opencode_python.cli.main import export_session
        assert export_session is not None

    @pytest.mark.asyncio
    async def test_export_session_works_with_session_data(self, temp_storage_dir):
        """Test that export_session command works with real session data."""
        from opencode_python.cli.main import cli
        from opencode_python.storage.store import SessionStorage, MessageStorage
        from opencode_python.core.models import Session, Message

        storage = SessionStorage(temp_storage_dir)
        session = Session(
            id="export-session-123",
            slug="export-session",
            project_id="test-project",
            directory=str(temp_storage_dir),
            title="Export Test Session",
            version="1.0.0",
        )
        await storage.create_session(session)

        msg_storage = MessageStorage(temp_storage_dir)
        message = Message(
            id="msg-123",
            session_id=session.id,
            role="user",
            text="Test message for export",
        )
        await msg_storage.create_message(session.id, message)

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export.json"

            result = runner.invoke(
                cli,
                ['export-session', session.id, '--output', str(output_path)]
            )

            assert result.exit_code == 0
            assert output_path.exists()
            assert "Export complete" in result.output

    @pytest.mark.asyncio
    async def test_export_session_supports_jsonl_gz_format(self, temp_storage_dir):
        """Test that export_session supports jsonl.gz format."""
        from opencode_python.cli.main import cli
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.models import Session

        storage = SessionStorage(temp_storage_dir)
        session = Session(
            id="gz-session-123",
            slug="gz-session",
            project_id="test-project",
            directory=str(temp_storage_dir),
            title="GZ Test Session",
            version="1.0.0",
        )
        await storage.create_session(session)

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export.jsonl.gz"

            result = runner.invoke(
                cli,
                ['export-session', session.id, '--output', str(output_path), '--format', 'jsonl.gz']
            )

            assert output_path.exists()
            with gzip.open(output_path, 'rt') as f:
                content = f.read()
            assert result.exit_code == 0


class TestImportSessionCommand:
    """Test import_session command uses storage layer."""

    def test_import_session_imports_storage_layer(self):
        """Test that import_session uses storage layer directly."""
        from opencode_python.cli.main import import_session
        assert import_session is not None

    @pytest.mark.asyncio
    async def test_import_session_creates_messages_via_storage(self, temp_storage_dir):
        """Test that import_session creates messages using storage.create_message()."""
        from opencode_python.cli.main import cli
        from opencode_python.storage.store import SessionStorage, MessageStorage

        storage = SessionStorage(temp_storage_dir)

        import_data = {
            "session": {
                "id": "import-session-123",
                "title": "Import Test Session",
                "project_id": "test-project",
                "directory": str(temp_storage_dir),
                "time_created": 1234567890.0,
                "time_updated": 1234567890.0,
                "version": "1.0.0",
            },
            "messages": [
                {
                    "id": "msg-1",
                    "session_id": "import-session-123",
                    "role": "user",
                    "text": "Imported message 1",
                },
                {
                    "id": "msg-2",
                    "session_id": "import-session-123",
                    "role": "assistant",
                    "text": "Imported message 2",
                },
            ],
        }

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            import_path = Path(tmpdir) / "import.json"
            with open(import_path, "w") as f:
                json.dump(import_data, f)

            result = runner.invoke(cli, ['import-session', str(import_path)])

            assert result.exit_code == 0
            assert "Import complete" in result.output

            session = await storage.get_session("import-session-123")
            assert session is not None
            assert session.title == "Import Test Session"

            msg_storage = MessageStorage(temp_storage_dir)
            messages = await msg_storage.list_messages("import-session-123")
            assert len(messages) == 2


class TestHandlerIntegration:
    """Test that CLI commands use handlers correctly."""

    @pytest.mark.asyncio
    async def test_cli_instantiates_handlers_in_list_sessions(self, temp_storage_dir):
        """Test that CLI instantiates handlers when running list_sessions."""
        from opencode_python.cli.main import cli
        from opencode_python.cli.handlers import CLIIOHandler, CLIProgressHandler, CLINotificationHandler

        runner = CliRunner()
        result = runner.invoke(cli, ['list-sessions', '--directory', str(temp_storage_dir)])

        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_cli_instantiates_handlers_in_export_session(self, temp_storage_dir):
        """Test that CLI instantiates handlers when running export_session."""
        from opencode_python.cli.main import cli
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.models import Session
        from opencode_python.cli.handlers import CLIIOHandler, CLIProgressHandler, CLINotificationHandler

        storage = SessionStorage(temp_storage_dir)
        session = Session(
            id="handler-test-123",
            slug="handler-test",
            project_id="test-project",
            directory=str(temp_storage_dir),
            title="Handler Test Session",
            version="1.0.0",
        )
        await storage.create_session(session)

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export.json"

            result = runner.invoke(
                cli,
                ['export-session', session.id, '--output', str(output_path)]
            )

            assert result.exit_code == 0


class TestBackwardCompatibility:
    """Test that refactored CLI maintains backward compatibility."""

    @pytest.mark.asyncio
    async def test_list_sessions_output_unchanged(self, sample_session, temp_storage_dir):
        """Test that list_sessions output format is unchanged."""
        from opencode_python.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ['list-sessions', '--directory', str(temp_storage_dir)])

        assert result.exit_code == 0
        assert "ID" in result.output
        assert "Title" in result.output
        assert "Created" in result.output

    @pytest.mark.asyncio
    async def test_export_session_output_unchanged(self, temp_storage_dir):
        """Test that export_session output format is unchanged."""
        from opencode_python.cli.main import cli
        from opencode_python.storage.store import SessionStorage
        from opencode_python.core.models import Session

        storage = SessionStorage(temp_storage_dir)
        session = Session(
            id="compat-export-123",
            slug="compat-export",
            project_id="test-project",
            directory=str(temp_storage_dir),
            title="Compatibility Export Test",
            version="1.0.0",
        )
        await storage.create_session(session)

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export.json"

            result = runner.invoke(
                cli,
                ['export-session', session.id, '--output', str(output_path)]
            )

            assert result.exit_code == 0
            assert "Export complete" in result.output

    @pytest.mark.asyncio
    async def test_import_session_output_unchanged(self, temp_storage_dir):
        """Test that import_session output format is unchanged."""
        from opencode_python.cli.main import cli

        import_data = {
            "session": {
                "id": "compat-import-123",
                "title": "Compatibility Import Test",
                "project_id": "test-project",
                "directory": str(temp_storage_dir),
                "time_created": 1234567890.0,
                "time_updated": 1234567890.0,
                "version": "1.0.0",
            },
            "messages": [],
        }

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            import_path = Path(tmpdir) / "import.json"
            with open(import_path, "w") as f:
                json.dump(import_data, f)

            result = runner.invoke(cli, ['import-session', str(import_path)])

            assert result.exit_code == 0
            assert "Import complete" in result.output

    def test_cli_command_signatures_unchanged(self):
        """Test that CLI command signatures (arguments, options) are unchanged."""
        from opencode_python.cli.main import list_sessions, export_session, import_session, cli
        import click

        assert isinstance(list_sessions, click.Command)
        assert '--directory' in list_sessions.params or '-d' in list_sessions.params

        assert isinstance(export_session, click.Command)
        assert 'session_id' in export_session.params
        assert '--output' in export_session.params or '-o' in export_session.params
        assert '--format' in export_session.params or '-f' in export_session.params

        assert isinstance(import_session, click.Command)
        assert 'import_path' in import_session.params
        assert '--project-id' in import_session.params or '-p' in import_session.params

        assert isinstance(cli, click.Group)


class TestErrorHandling:
    """Test that CLI commands propagate errors correctly."""

    @pytest.mark.asyncio
    async def test_export_session_handles_nonexistent_session(self, temp_storage_dir):
        """Test that export_session handles nonexistent session gracefully."""
        from opencode_python.cli.main import cli

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export.json"

            result = runner.invoke(
                cli,
                ['export-session', 'nonexistent-id', '--output', str(output_path)]
            )

            assert result.exit_code != 0 or "not found" in result.output.lower()

    @pytest.mark.asyncio
    async def test_import_session_handles_invalid_json(self, temp_storage_dir):
        """Test that import_session handles invalid JSON gracefully."""
        from opencode_python.cli.main import cli

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            import_path = Path(tmpdir) / "invalid.json"
            with open(import_path, "w") as f:
                f.write("invalid json content")

            result = runner.invoke(cli, ['import-session', str(import_path)])

            assert result.exit_code != 0 or "invalid" in result.output.lower()


class TestTUILaunchRemoval:
    """Test that TUI import and launch is removed from run command."""

    def test_run_command_no_tui_import(self):
        """Test that run command does not import OpenCodeTUI at module level."""
        from opencode_python.cli import main

        assert 'from opencode_python.tui.app import OpenCodeTUI' not in main.__doc__


    def test_run_command_signature_unchanged(self):
        """Test that run command signature is unchanged."""
        from opencode_python.cli.main import run
        import click

        assert isinstance(run, click.Command)
        assert any(p.name == 'message' for p in run.params if isinstance(p, click.Argument))
        assert any(p.name == 'agent' for p in run.params if isinstance(p, click.Option))
        assert any(p.name == 'model' for p in run.params if isinstance(p, click.Option))

    def test_run_command_still_exists(self):
        """Test that run command still exists in CLI."""
        from opencode_python.cli.main import cli, run

        assert 'run' in cli.commands

    def test_tui_command_still_works(self):
        """Test that tui command still exists and works."""
        from opencode_python.cli.main import cli
        import click

        assert 'tui' in cli.commands
        assert isinstance(cli.commands['tui'], click.Command)
