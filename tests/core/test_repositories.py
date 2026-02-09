"""Tests for repository pattern implementation.

This module tests the SessionRepository, MessageRepository, and PartRepository
protocols and their implementations, ensuring they return Result types and handle
errors correctly without raising exceptions.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from dawn_kestrel.core.models import Session, Message, TextPart
from dawn_kestrel.core.repositories import (
    SessionRepositoryImpl,
    MessageRepositoryImpl,
    PartRepositoryImpl,
)
from dawn_kestrel.core.result import Ok, Err
from dawn_kestrel.storage.store import SessionStorage, MessageStorage, PartStorage


class TestSessionRepository:
    """Test SessionRepository implementation."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock SessionStorage."""
        storage = MagicMock(spec=SessionStorage)
        storage.get_session = AsyncMock()
        storage.create_session = AsyncMock()
        storage.update_session = AsyncMock()
        storage.delete_session = AsyncMock()
        storage.list_sessions = AsyncMock()
        return storage

    @pytest.fixture
    def sample_session(self):
        """Create sample session for testing."""
        return Session(
            id="test_session_1",
            slug="test",
            project_id="test_project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0.0",
        )

    async def test_get_by_id_returns_ok_when_exists(self, mock_storage, sample_session):
        """Test get_by_id returns Ok when session exists."""
        mock_storage.get_session.return_value = sample_session

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.get_by_id("test_session_1")

        assert result.is_ok()
        assert result.unwrap() == sample_session
        mock_storage.get_session.assert_called_once_with("test_session_1")

    async def test_get_by_id_returns_err_when_not_found(self, mock_storage):
        """Test get_by_id returns Err when session not found."""
        mock_storage.get_session.return_value = None

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.get_by_id("nonexistent")

        assert result.is_err()
        assert result.code == "NOT_FOUND"
        assert "not found" in result.error.lower()

    async def test_get_by_id_returns_err_on_storage_error(self, mock_storage):
        """Test get_by_id returns Err when storage raises exception."""
        mock_storage.get_session.side_effect = Exception("Storage error")

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.get_by_id("test_session_1")

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"

    async def test_create_returns_ok_with_created_session(self, mock_storage, sample_session):
        """Test create returns Ok with created session."""
        mock_storage.create_session.return_value = sample_session

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.create(sample_session)

        assert result.is_ok()
        assert result.unwrap() == sample_session
        mock_storage.create_session.assert_called_once_with(sample_session)

    async def test_create_returns_err_on_storage_error(self, mock_storage, sample_session):
        """Test create returns Err when storage raises exception."""
        mock_storage.create_session.side_effect = Exception("Create failed")

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.create(sample_session)

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"

    async def test_update_returns_ok_with_updated_session(self, mock_storage, sample_session):
        """Test update returns Ok with updated session."""
        mock_storage.update_session.return_value = sample_session

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.update(sample_session)

        assert result.is_ok()
        assert result.unwrap() == sample_session
        mock_storage.update_session.assert_called_once_with(sample_session)

    async def test_update_returns_err_on_storage_error(self, mock_storage, sample_session):
        """Test update returns Err when storage raises exception."""
        mock_storage.update_session.side_effect = Exception("Update failed")

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.update(sample_session)

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"

    async def test_delete_returns_ok_true_when_deleted(self, mock_storage, sample_session):
        """Test delete returns Ok(True) when session is deleted."""
        mock_storage.get_session.return_value = sample_session
        mock_storage.delete_session.return_value = True

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.delete("test_session_1")

        assert result.is_ok()
        assert result.unwrap() is True

    async def test_delete_returns_ok_false_when_not_found(self, mock_storage):
        """Test delete returns Ok(False) when session not found."""
        mock_storage.get_session.return_value = None

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.delete("nonexistent")

        assert result.is_ok()
        assert result.unwrap() is False

    async def test_delete_returns_err_on_storage_error(self, mock_storage, sample_session):
        """Test delete returns Err when storage raises exception."""
        mock_storage.get_session.return_value = sample_session
        mock_storage.delete_session.side_effect = Exception("Delete failed")

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.delete("test_session_1")

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"

    async def test_list_by_project_returns_ok_with_sessions(self, mock_storage, sample_session):
        """Test list_by_project returns Ok with list of sessions."""
        mock_storage.list_sessions.return_value = [sample_session]

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.list_by_project("test_project")

        assert result.is_ok()
        assert len(result.unwrap()) == 1
        assert result.unwrap()[0] == sample_session
        mock_storage.list_sessions.assert_called_once_with("test_project")

    async def test_list_by_project_returns_ok_empty_when_no_sessions(self, mock_storage):
        """Test list_by_project returns Ok with empty list when no sessions."""
        mock_storage.list_sessions.return_value = []

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.list_by_project("test_project")

        assert result.is_ok()
        assert result.unwrap() == []

    async def test_list_by_project_returns_err_on_storage_error(self, mock_storage):
        """Test list_by_project returns Err when storage raises exception."""
        mock_storage.list_sessions.side_effect = Exception("List failed")

        repo = SessionRepositoryImpl(mock_storage)
        result = await repo.list_by_project("test_project")

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"


class TestMessageRepository:
    """Test MessageRepository implementation."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock MessageStorage."""
        storage = MagicMock(spec=MessageStorage)
        storage.get_message = AsyncMock()
        storage.create_message = AsyncMock()
        storage.list_messages = AsyncMock()
        return storage

    @pytest.fixture
    def sample_message(self):
        """Create sample message for testing."""
        return Message(
            id="test_message_1",
            session_id="test_session_1",
            role="user",
            text="Hello, world!",
        )

    async def test_get_by_id_returns_ok_when_exists(self, mock_storage, sample_message):
        """Test get_by_id returns Ok when message exists."""
        mock_storage.get_message.return_value = sample_message.model_dump()

        repo = MessageRepositoryImpl(mock_storage)
        result = await repo.get_by_id("test_session_1", "test_message_1")

        assert result.is_ok()
        assert result.unwrap().id == sample_message.id
        mock_storage.get_message.assert_called_once_with("test_session_1", "test_message_1")

    async def test_get_by_id_returns_err_when_not_found(self, mock_storage):
        """Test get_by_id returns Err when message not found."""
        mock_storage.get_message.return_value = None

        repo = MessageRepositoryImpl(mock_storage)
        result = await repo.get_by_id("test_session_1", "nonexistent")

        assert result.is_err()
        assert result.code == "NOT_FOUND"

    async def test_get_by_id_returns_err_on_storage_error(self, mock_storage):
        """Test get_by_id returns Err when storage raises exception."""
        mock_storage.get_message.side_effect = Exception("Storage error")

        repo = MessageRepositoryImpl(mock_storage)
        result = await repo.get_by_id("test_session_1", "test_message_1")

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"

    async def test_create_returns_ok_with_created_message(self, mock_storage, sample_message):
        """Test create returns Ok with created message."""
        mock_storage.create_message.return_value = sample_message

        repo = MessageRepositoryImpl(mock_storage)
        result = await repo.create(sample_message)

        assert result.is_ok()
        assert result.unwrap() == sample_message
        mock_storage.create_message.assert_called_once_with(
            sample_message.session_id, sample_message
        )

    async def test_create_returns_err_on_storage_error(self, mock_storage, sample_message):
        """Test create returns Err when storage raises exception."""
        mock_storage.create_message.side_effect = Exception("Create failed")

        repo = MessageRepositoryImpl(mock_storage)
        result = await repo.create(sample_message)

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"

    async def test_list_by_session_returns_ok_with_messages(self, mock_storage, sample_message):
        """Test list_by_session returns Ok with list of messages."""
        mock_storage.list_messages.return_value = [sample_message.model_dump()]

        repo = MessageRepositoryImpl(mock_storage)
        result = await repo.list_by_session("test_session_1")

        assert result.is_ok()
        assert len(result.unwrap()) == 1
        assert result.unwrap()[0].id == sample_message.id
        mock_storage.list_messages.assert_called_once_with("test_session_1", True)

    async def test_list_by_session_returns_ok_empty_when_no_messages(self, mock_storage):
        """Test list_by_session returns Ok with empty list when no messages."""
        mock_storage.list_messages.return_value = []

        repo = MessageRepositoryImpl(mock_storage)
        result = await repo.list_by_session("test_session_1")

        assert result.is_ok()
        assert result.unwrap() == []

    async def test_list_by_session_respects_reverse_parameter(self, mock_storage, sample_message):
        """Test list_by_session passes reverse parameter to storage."""
        mock_storage.list_messages.return_value = [sample_message.model_dump()]

        repo = MessageRepositoryImpl(mock_storage)
        await repo.list_by_session("test_session_1", reverse=False)

        mock_storage.list_messages.assert_called_once_with("test_session_1", False)

    async def test_list_by_session_returns_err_on_storage_error(self, mock_storage):
        """Test list_by_session returns Err when storage raises exception."""
        mock_storage.list_messages.side_effect = Exception("List failed")

        repo = MessageRepositoryImpl(mock_storage)
        result = await repo.list_by_session("test_session_1")

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"


class TestPartRepository:
    """Test PartRepository implementation."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock PartStorage."""
        storage = MagicMock(spec=PartStorage)
        storage.get_part = AsyncMock()
        storage.create_part = AsyncMock()
        storage.update_part = AsyncMock()
        storage.list_parts = AsyncMock()
        return storage

    @pytest.fixture
    def sample_part(self):
        """Create sample part for testing."""
        return TextPart(
            id="test_part_1",
            session_id="test_session_1",
            message_id="test_message_1",
            part_type="text",
            text="Hello, world!",
        )

    async def test_get_by_id_returns_ok_when_exists(self, mock_storage, sample_part):
        """Test get_by_id returns Ok when part exists."""
        mock_storage.get_part.return_value = sample_part.model_dump()

        repo = PartRepositoryImpl(mock_storage)
        result = await repo.get_by_id("test_message_1", "test_part_1")

        assert result.is_ok()
        assert result.unwrap().id == sample_part.id
        mock_storage.get_part.assert_called_once_with("test_message_1", "test_part_1")

    async def test_get_by_id_returns_err_when_not_found(self, mock_storage):
        """Test get_by_id returns Err when part not found."""
        mock_storage.get_part.return_value = None

        repo = PartRepositoryImpl(mock_storage)
        result = await repo.get_by_id("test_message_1", "nonexistent")

        assert result.is_err()
        assert result.code == "NOT_FOUND"

    async def test_get_by_id_returns_err_on_storage_error(self, mock_storage):
        """Test get_by_id returns Err when storage raises exception."""
        mock_storage.get_part.side_effect = Exception("Storage error")

        repo = PartRepositoryImpl(mock_storage)
        result = await repo.get_by_id("test_message_1", "test_part_1")

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"

    async def test_create_returns_ok_with_created_part(self, mock_storage, sample_part):
        """Test create returns Ok with created part."""
        mock_storage.create_part.return_value = sample_part

        repo = PartRepositoryImpl(mock_storage)
        result = await repo.create("test_message_1", sample_part)

        assert result.is_ok()
        assert result.unwrap() == sample_part
        mock_storage.create_part.assert_called_once_with("test_message_1", sample_part)

    async def test_create_returns_err_on_storage_error(self, mock_storage, sample_part):
        """Test create returns Err when storage raises exception."""
        mock_storage.create_part.side_effect = Exception("Create failed")

        repo = PartRepositoryImpl(mock_storage)
        result = await repo.create("test_message_1", sample_part)

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"

    async def test_update_returns_ok_with_updated_part(self, mock_storage, sample_part):
        """Test update returns Ok with updated part."""
        mock_storage.update_part.return_value = sample_part

        repo = PartRepositoryImpl(mock_storage)
        result = await repo.update("test_message_1", sample_part)

        assert result.is_ok()
        assert result.unwrap() == sample_part
        mock_storage.update_part.assert_called_once_with("test_message_1", sample_part)

    async def test_update_returns_err_on_storage_error(self, mock_storage, sample_part):
        """Test update returns Err when storage raises exception."""
        mock_storage.update_part.side_effect = Exception("Update failed")

        repo = PartRepositoryImpl(mock_storage)
        result = await repo.update("test_message_1", sample_part)

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"

    async def test_list_by_message_returns_ok_with_parts(self, mock_storage, sample_part):
        """Test list_by_message returns Ok with list of parts."""
        mock_storage.list_parts.return_value = [sample_part.model_dump()]

        repo = PartRepositoryImpl(mock_storage)
        result = await repo.list_by_message("test_message_1")

        assert result.is_ok()
        assert len(result.unwrap()) == 1
        assert result.unwrap()[0].id == sample_part.id
        mock_storage.list_parts.assert_called_once_with("test_message_1")

    async def test_list_by_message_returns_ok_empty_when_no_parts(self, mock_storage):
        """Test list_by_message returns Ok with empty list when no parts."""
        mock_storage.list_parts.return_value = []

        repo = PartRepositoryImpl(mock_storage)
        result = await repo.list_by_message("test_message_1")

        assert result.is_ok()
        assert result.unwrap() == []

    async def test_list_by_message_returns_err_on_storage_error(self, mock_storage):
        """Test list_by_message returns Err when storage raises exception."""
        mock_storage.list_parts.side_effect = Exception("List failed")

        repo = PartRepositoryImpl(mock_storage)
        result = await repo.list_by_message("test_message_1")

        assert result.is_err()
        assert result.code == "STORAGE_ERROR"
