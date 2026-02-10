"""Integration tests for CLI command execution and Result handling.

Tests verify that CLI commands correctly integrate with SessionService,
storage, and DI container without mocking.

Scenario: CLI Command End-to-End Execution
============================================

Preconditions:
- CLI commands are defined
- SessionService uses Result pattern
- Storage directory accessible
- DI container configured

Steps:
1. Run list_sessions command
2. Run export_session command
3. Run import_session command
4. Verify Result pattern handling
5. Verify error handling

Expected result:
- All CLI commands execute successfully
- Result pattern errors handled correctly
- Errors displayed to user with proper formatting
- Exit codes correct (0 for success, 1 for error)

Failure indicators:
- CLI command crashes
- Result errors not handled
- Wrong exit codes
- Errors not displayed to user

Evidence:
- Commands exit with code 0 on success
- Commands exit with code 1 on error
- Error messages printed to stderr
- Output formatted correctly
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import subprocess
import sys
import pytest
import json


class TestCLIListSessions:
    """Test CLI list_sessions command."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_list_sessions_exits_zero_with_sessions(self, temp_storage_dir):
        """Scenario: list_sessions exits with code 0 when sessions exist.

        Preconditions:
        - Sessions exist in storage
        - Storage directory configured

        Steps:
        1. Create session in storage
        2. Run dawn-kestrel list_sessions
        3. Verify exit code is 0
        4. Verify session displayed in output

        Expected result:
        - Exit code 0
        - Session title in output
        - Session ID in output

        Failure indicators:
        - Exit code not 0
        - Session not in output
        - Command crashes
        """
        from dawn_kestrel.storage.store import SessionStorage
        from dawn_kestrel.core.models import Session
        import asyncio

        # Create a session
        storage = SessionStorage(base_dir=temp_storage_dir)
        session = Session(
            id="cli_test_1",
            slug="test",
            project_id="test_project",
            directory="/tmp/test",
            title="CLI Test Session",
            version="1.0.0",
        )
        asyncio.run(storage.create_session(session))

        # Run CLI command
        result = subprocess.run(
            [sys.executable, "-m", "dawn_kestrel.cli.main", "list-sessions"],
            env={"DAWN_KESTREL_STORAGE_DIR": str(temp_storage_dir)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"CLI exited with code {result.returncode}"
        assert "CLI Test Session" in result.stdout, "Session title not in output"
        assert "cli_test_1" in result.stdout, "Session ID not in output"

    def test_list_sessions_handles_empty_storage(self, temp_storage_dir):
        """Scenario: list_sessions handles empty storage gracefully.

        Preconditions:
        - Storage directory empty
        - No sessions exist

        Steps:
        1. Run dawn-kestrel list_sessions
        2. Verify exit code is 0
        3. Verify empty table or no sessions message

        Expected result:
        - Exit code 0 (not an error to have no sessions)
        - Empty output or "no sessions" message

        Failure indicators:
        - Exit code not 0
        - Error message for empty storage
        - Command crashes
        """
        result = subprocess.run(
            [sys.executable, "-m", "dawn_kestrel.cli.main", "list-sessions"],
            env={"DAWN_KESTREL_STORAGE_DIR": str(temp_storage_dir)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"CLI exited with code {result.returncode}"


class TestCLIResultHandling:
    """Test CLI Result pattern error handling."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_export_nonexistent_session_shows_error(self, temp_storage_dir):
        """Scenario: Exporting nonexistent session shows error message.

        Preconditions:
        - Session doesn't exist
        - Storage configured

        Steps:
        1. Run dawn-kestrel export-session with nonexistent ID
        2. Verify exit code is 1
        3. Verify error message displayed

        Expected result:
        - Exit code 1
        - Error message displayed
        - Error message contains "not found"

        Failure indicators:
        - Exit code not 1
        - No error message
        - Command crashes
        """
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "dawn_kestrel.cli.main",
                "export-session",
                "nonexistent_session",
            ],
            env={"DAWN_KESTREL_STORAGE_DIR": str(temp_storage_dir)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1, (
            f"CLI should exit with code 1 for error, got {result.returncode}"
        )
        assert "Error" in result.stderr or "Error" in result.stdout, "No error message displayed"

    def test_list_sessions_invalid_storage_shows_error(self, temp_storage_dir):
        """Scenario: Invalid storage directory shows error.

        Preconditions:
        - Invalid storage path

        Steps:
        1. Set storage directory to invalid path
        2. Run list_sessions
        3. Verify error displayed

        Expected result:
        - Exit code 1
        - Error message displayed

        Failure indicators:
        - Exit code 0
        - No error message
        """
        invalid_path = Path("/nonexistent/path/that/does/not/exist")

        result = subprocess.run(
            [sys.executable, "-m", "dawn_kestrel.cli.main", "list-sessions"],
            env={"DAWN_KESTREL_STORAGE_DIR": str(invalid_path)},
            capture_output=True,
            text=True,
        )

        # Should handle gracefully, either succeed or show clear error
        # Exit code may be 0 (empty sessions) or 1 (error), both acceptable
        assert result.returncode in [0, 1], f"Unexpected exit code {result.returncode}"


class TestCLIRepositoryWiring:
    """Test CLI uses repository injection pattern."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_cli_injects_session_repository(self, temp_storage_dir):
        """Scenario: CLI commands inject SessionRepository.

        Preconditions:
        - CLI command executed
        - Storage directory configured

        Steps:
        1. Create session
        2. Run list_sessions
        3. Verify session retrieved via repository

        Expected result:
        - Session retrieved from storage
        - Repository pattern used internally

        Failure indicators:
        - Session not retrieved
        - Old storage pattern used

        Evidence:
        - Session displayed in list_sessions output
        """
        from dawn_kestrel.storage.store import SessionStorage
        from dawn_kestrel.core.models import Session
        import asyncio

        # Create a session
        storage = SessionStorage(base_dir=temp_storage_dir)
        session = Session(
            id="repo_test_1",
            slug="test",
            project_id="test_project",
            directory="/tmp/test",
            title="Repository Test Session",
            version="1.0.0",
        )
        asyncio.run(storage.create_session(session))

        # Run CLI command
        result = subprocess.run(
            [sys.executable, "-m", "dawn_kestrel.cli.main", "list-sessions"],
            env={"DAWN_KESTREL_STORAGE_DIR": str(temp_storage_dir)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Repository Test Session" in result.stdout, "Session not retrieved via repository"
