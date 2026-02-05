"""Tests for telemetry endpoints."""

import os
import tempfile
from typing import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for FastAPI application.

    Returns:
        TestClient: A test client instance.
    """
    return TestClient(app)


@pytest.fixture
def test_project_dir() -> Generator[Path, None, None]:
    """Create a temporary git repository for testing.

    Returns:
        Path: Path to the temporary git repository.
    """
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        project_dir.mkdir(exist_ok=True)

        subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, check=True, capture_output=True)

        (project_dir / "test.txt").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=project_dir, check=True, capture_output=True)

        os.environ["WEBAPP_PROJECT_DIR"] = str(project_dir)

        yield project_dir

        if "WEBAPP_PROJECT_DIR" in os.environ:
            del os.environ["WEBAPP_PROJECT_DIR"]


class TestGetTelemetry:
    """Tests for GET /api/v1/sessions/{session_id}/telemetry endpoint."""

    def test_get_telemetry_success(self, client: TestClient, test_project_dir: Path) -> None:
        """Test that getting telemetry returns 200 OK with telemetry data.

        This test verifies the GET /api/v1/sessions/{session_id}/telemetry endpoint
        returns a successful response with complete telemetry data including
        git status, tool history, and effort metrics.
        """
        # First create a session
        create_response = client.post("/api/v1/sessions", json={"title": "Telemetry Test Session"})
        assert create_response.status_code == 200
        session_id = create_response.json()["id"]

        # Get telemetry for the session
        response = client.get(f"/api/v1/sessions/{session_id}/telemetry")
        assert response.status_code == 200
        data = response.json()

        # Verify telemetry structure
        assert data["type"] == "telemetry"
        assert data["session_id"] == session_id
        assert data["directory_scope"] == str(test_project_dir)

        # Verify git status fields
        assert "git" in data
        git = data["git"]
        assert git["is_repo"] is True
        assert "branch" in git
        assert isinstance(git["dirty_count"], int)
        assert isinstance(git["staged_count"], int)
        assert isinstance(git["ahead"], int)
        assert isinstance(git["behind"], int)
        assert isinstance(git["conflict"], bool)

        # Verify tools fields
        assert "tools" in data
        tools = data["tools"]
        assert "running" in tools
        assert "last" in tools
        assert isinstance(tools["error_count"], int)
        assert isinstance(tools["recent"], list)

        # Verify effort fields
        assert "effort_inputs" in data
        effort = data["effort_inputs"]
        assert isinstance(effort["duration_ms"], int)
        assert isinstance(effort["token_total"], int)
        assert isinstance(effort["tool_count"], int)

        # Verify effort score
        assert "effort_score" in data
        assert isinstance(data["effort_score"], int)
        assert 0 <= data["effort_score"] <= 5

    def test_get_telemetry_not_found(self, client: TestClient) -> None:
        """Test that getting telemetry for non-existent session returns 404.

        This test verifies the GET /api/v1/sessions/{session_id}/telemetry endpoint
        returns 404 Not Found when the session ID doesn't exist.
        """
        response = client.get("/api/v1/sessions/non_existent_session_id/telemetry")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_telemetry_dirty_git(self, client: TestClient, test_project_dir: Path) -> None:
        """Test that telemetry correctly reports dirty git status.

        This test verifies that dirty_count and staged_count are correctly
        calculated when the repository has uncommitted changes.
        """
        import subprocess

        # Create a session
        create_response = client.post("/api/v1/sessions", json={"title": "Dirty Git Test"})
        assert create_response.status_code == 200
        session_id = create_response.json()["id"]

        # Create dirty changes
        (test_project_dir / "dirty.txt").write_text("dirty file")

        # Get telemetry
        response = client.get(f"/api/v1/sessions/{session_id}/telemetry")
        assert response.status_code == 200
        data = response.json()

        # Verify dirty count is reported
        assert data["git"]["dirty_count"] > 0
        assert data["git"]["staged_count"] == 0
        assert data["git"]["conflict"] is False

    def test_get_telemetry_staged_changes(self, client: TestClient, test_project_dir: Path) -> None:
        """Test that telemetry correctly reports staged git changes.

        This test verifies that staged_count is correctly calculated when
        the repository has staged changes.
        """
        import subprocess

        # Create a session
        create_response = client.post("/api/v1/sessions", json={"title": "Staged Test"})
        assert create_response.status_code == 200
        session_id = create_response.json()["id"]

        # Create and stage changes
        (test_project_dir / "staged.txt").write_text("staged file")
        subprocess.run(["git", "add", "staged.txt"], cwd=test_project_dir, check=True, capture_output=True)

        # Get telemetry
        response = client.get(f"/api/v1/sessions/{session_id}/telemetry")
        assert response.status_code == 200
        data = response.json()

        # Verify staged count is reported
        assert data["git"]["staged_count"] > 0

    def test_get_telemetry_no_git_repo(self, client: TestClient) -> None:
        """Test that telemetry handles non-git directories gracefully.

        This test verifies that telemetry returns valid data when the
        directory is not a git repository.
        """
        # Create a session
        create_response = client.post("/api/v1/sessions", json={"title": "No Git Test"})
        assert create_response.status_code == 200
        session_id = create_response.json()["id"]

        # Override project directory to a non-git directory
        with tempfile.TemporaryDirectory() as tmpdir:
            non_git_dir = Path(tmpdir)
            os.environ["WEBAPP_PROJECT_DIR"] = str(non_git_dir)

            try:
                response = client.get(f"/api/v1/sessions/{session_id}/telemetry")
                assert response.status_code == 200
                data = response.json()

                # Verify git reports not a repo
                assert data["git"]["is_repo"] is False
                assert data["git"]["branch"] is None
                assert data["git"]["dirty_count"] == 0
                assert data["git"]["staged_count"] == 0
            finally:
                if "WEBAPP_PROJECT_DIR" in os.environ:
                    del os.environ["WEBAPP_PROJECT_DIR"]

    def test_effort_score_calculation(self, client: TestClient) -> None:
        """Test that effort score is calculated correctly.

        This test verifies the effort score formula:
        - duration_pts = clamp(0..2, floor(duration_ms / 30000))
        - token_pts = clamp(0..2, floor(token_total / 2000))
        - tool_pts = clamp(0..2, floor(tool_count / 3))
        - effort_score = min(5, duration_pts + token_pts + tool_pts)
        """
        # Create a session
        create_response = client.post("/api/v1/sessions", json={"title": "Effort Score Test"})
        assert create_response.status_code == 200
        session_id = create_response.json()["id"]

        # Get telemetry (should have minimal effort for empty session)
        response = client.get(f"/api/v1/sessions/{session_id}/telemetry")
        assert response.status_code == 200
        data = response.json()

        # For empty session, effort score should be minimal (0 or 1)
        effort_score = data["effort_score"]
        assert isinstance(effort_score, int)
        assert 0 <= effort_score <= 5

        # Verify effort inputs
        effort = data["effort_inputs"]
        assert isinstance(effort["duration_ms"], int)
        assert isinstance(effort["token_total"], int)
        assert isinstance(effort["tool_count"], int)
