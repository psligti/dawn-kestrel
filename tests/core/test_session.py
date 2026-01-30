"""Tests for Session functionality - creation, persistence, resume, export"""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import json

from opencode_python.storage.session_meta import SessionMeta, SessionMetaStorage
from opencode_python.core.session import SessionManager
from opencode_python.storage.store import SessionStorage
from opencode_python.export.session_exporter import MarkdownExporter, JSONExporter, export_session
from opencode_python.core.models import Session, Message, TextPart


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def storage(temp_dir):
    return SessionStorage(temp_dir)


@pytest.fixture
def meta_storage(temp_dir):
    return SessionMetaStorage(temp_dir)


@pytest.fixture
def session_manager(temp_dir):
    return SessionManager(SessionStorage(temp_dir), temp_dir)


@pytest.fixture
def sample_session_data():
    return {
        "title": "Test Session",
        "repo_path": "/fake/repo",
        "objective": "Test objective",
        "constraints": "Test constraints",
    }


class TestSessionMetaStorage:
    async def test_save_and_get_meta(self, meta_storage):
        meta = SessionMeta(
            repo_path="/test/repo",
            objective="Test objective",
            constraints="Test constraints",
        )

        saved = await meta_storage.save_meta("session-1", meta)
        assert saved.repo_path == "/test/repo"
        assert saved.objective == "Test objective"
        assert saved.time_updated > 0

        retrieved = await meta_storage.get_meta("session-1")
        assert retrieved is not None
        assert retrieved.repo_path == "/test/repo"
        assert retrieved.objective == "Test objective"

    async def test_get_nonexistent_meta(self, meta_storage):
        result = await meta_storage.get_meta("nonexistent")
        assert result is None

    async def test_update_meta(self, meta_storage):
        meta = SessionMeta(repo_path="/original")
        await meta_storage.save_meta("session-1", meta)

        updated = await meta_storage.update_meta("session-1", repo_path="/updated")
        assert updated.repo_path == "/updated"

    async def test_delete_meta(self, meta_storage):
        meta = SessionMeta(repo_path="/test")
        await meta_storage.save_meta("session-1", meta)

        deleted = await meta_storage.delete_meta("session-1")
        assert deleted is True

        retrieved = await meta_storage.get_meta("session-1")
        assert retrieved is None


class TestSessionManagerEnhancements:
    async def test_validate_repo_path_exists(self, session_manager, temp_dir):
        result = await session_manager.validate_repo_path(str(temp_dir))
        assert result is True

    async def test_validate_repo_path_not_exists(self, session_manager):
        result = await session_manager.validate_repo_path("/nonexistent/path")
        assert result is False

    async def test_validate_repo_path_not_directory(self, session_manager, temp_dir):
        file_path = temp_dir / "test.txt"
        file_path.touch()

        result = await session_manager.validate_repo_path(str(file_path))
        assert result is False

    async def test_create_with_context(self, session_manager, temp_dir, sample_session_data):
        repo_path = temp_dir / "test_repo"
        repo_path.mkdir()

        session = await session_manager.create_with_context(
            title=sample_session_data["title"],
            repo_path=str(repo_path),
            objective=sample_session_data["objective"],
            constraints=sample_session_data["constraints"],
        )

        assert session is not None
        assert session.title == sample_session_data["title"]

        meta = await session_manager.get_session_meta(session.id)
        assert meta is not None
        assert meta.repo_path == str(repo_path)
        assert meta.objective == sample_session_data["objective"]

    async def test_create_with_invalid_repo_path(self, session_manager):
        with pytest.raises(ValueError, match="Invalid repository path"):
            await session_manager.create_with_context(
                title="Test",
                repo_path="/nonexistent/path",
            )

    async def test_get_session_meta(self, session_manager, temp_dir):
        session = await session_manager.create(title="Test Session")
        meta = SessionMeta(repo_path=str(temp_dir))
        await session_manager._get_meta_storage().save_meta(session.id, meta)

        retrieved = await session_manager.get_session_meta(session.id)
        assert retrieved is not None
        assert retrieved.repo_path == str(temp_dir)

    async def test_resume_session(self, session_manager, temp_dir):
        session = await session_manager.create(title="Test Session")
        meta = SessionMeta(repo_path=str(temp_dir), objective="Test objective")
        await session_manager._get_meta_storage().save_meta(session.id, meta)

        retrieved_session, retrieved_meta = await session_manager.resume_session(session.id)

        assert retrieved_session.id == session.id
        assert retrieved_meta is not None
        assert retrieved_meta.objective == "Test objective"

    async def test_resume_nonexistent_session(self, session_manager):
        with pytest.raises(ValueError, match="Session not found"):
            await session_manager.resume_session("nonexistent-id")


class TestSessionExport:
    async def test_export_markdown(self, session_manager, temp_dir):
        session = await session_manager.create(title="Test Session")
        meta = SessionMeta(
            repo_path=str(temp_dir),
            objective="Test objective",
            constraints="Test constraints",
        )
        await session_manager._get_meta_storage().save_meta(session.id, meta)

        message = Message(
            id="msg-1",
            session_id=session.id,
            role="user",
            time={"created": 0},
            text="Test message with api_key=secret123",
        )
        await session_manager.create_message(session.id, "user", "Test message with api_key=secret123")

        messages = await session_manager.list_messages(session.id)
        result = await session_manager._export_markdown(session.id, redact_secrets=True)

        assert "# Session: Test Session" in result
        assert "Test objective" in result
        assert "api_key=***REDACTED***" in result
        assert "secret123" not in result

    async def test_export_json(self, session_manager, temp_dir):
        session = await session_manager.create(title="Test Session")
        meta = SessionMeta(repo_path=str(temp_dir))
        await session_manager._get_meta_storage().save_meta(session.id, meta)

        await session_manager.create_message(session.id, "user", "Test message")

        messages = await session_manager.list_messages(session.id)
        result = await session_manager._export_json(session.id)

        data = json.loads(result)
        assert data["session"]["id"] == session.id
        assert data["session"]["title"] == "Test Session"
        assert data["meta"]["repo_path"] == str(temp_dir)
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) >= 1


class TestExporters:
    async def test_markdown_exporter(self, temp_dir):
        session = Session(
            id="test-id",
            slug="test",
            project_id="test",
            directory=str(temp_dir),
            title="Test Session",
            version="1.0.0",
        )
        meta = SessionMeta(
            repo_path=str(temp_dir),
            objective="Test objective",
        )
        message = Message(
            id="msg-1",
            session_id="test-id",
            role="user",
            time={"created": 0},
            text="Test message",
        )

        exporter = MarkdownExporter(redact_secrets=True)
        result = await exporter.export(session, meta, [message])

        assert "# Session: Test Session" in result
        assert "Test objective" in result
        assert "Test message" in result

    async def test_json_exporter(self, temp_dir):
        session = Session(
            id="test-id",
            slug="test",
            project_id="test",
            directory=str(temp_dir),
            title="Test Session",
            version="1.0.0",
        )
        meta = SessionMeta(repo_path=str(temp_dir))
        message = Message(
            id="msg-1",
            session_id="test-id",
            role="user",
            time={"created": 0},
            text="Test message",
        )

        exporter = JSONExporter(redact_secrets=False)
        result = await exporter.export(session, meta, [message])

        data = json.loads(result)
        assert data["session"]["id"] == "test-id"
        assert data["meta"]["repo_path"] == str(temp_dir)
        assert len(data["messages"]) == 1

    async def test_secret_redaction(self, temp_dir):
        session = Session(
            id="test-id",
            slug="test",
            project_id="test",
            directory=str(temp_dir),
            title="Test",
            version="1.0.0",
        )
        message = Message(
            id="msg-1",
            session_id="test-id",
            role="user",
            time={"created": 0},
            text="API key: api_key=secret, token: abc123, password: pass456",
        )

        exporter = MarkdownExporter(redact_secrets=True)
        result = await exporter.export(session, None, [message])

        assert "api_key=***REDACTED***" in result
        assert "token=***REDACTED***" in result
        assert "password=***REDACTED***" in result
        assert "secret" not in result
        assert "abc123" not in result
        assert "pass456" not in result

    async def test_export_session_function(self, temp_dir):
        session = Session(
            id="test-id",
            slug="test",
            project_id="test",
            directory=str(temp_dir),
            title="Test",
            version="1.0.0",
        )
        message = Message(
            id="msg-1",
            session_id="test-id",
            role="user",
            time={"created": 0},
            text="Test",
        )

        result = await export_session(session, None, [message], format="markdown")
        assert "# Session: Test" in result

        result = await export_session(session, None, [message], format="json")
        data = json.loads(result)
        assert data["session"]["id"] == "test-id"
