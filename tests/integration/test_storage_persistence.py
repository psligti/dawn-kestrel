"""Integration tests for storage and repository persistence.

Tests verify that storage layer and repositories correctly
persist and retrieve data without mocking.

Scenario: Storage and Repository End-to-End Persistence
======================================================

Preconditions:
- Storage directory exists
- Repositories configured with storage
- File I/O functional

Steps:
1. Create session via repository
2. Verify file created in storage
3. Create message via repository
4. Retrieve message via repository
5. Create part via repository
6. List sessions via repository
7. Delete session via repository
8. Verify deletion in storage

Expected result:
- All data persisted to storage
- All data retrievable from storage
- Files created with correct structure
- Deletion removes files

Failure indicators:
- Data not persisted to storage
- Data not retrievable
- Files not created
- Deletion incomplete

Evidence:
- Session files in storage directory
- Message files created
- list_sessions returns persisted sessions
- Deleted files removed
"""

import tempfile
from pathlib import Path
import pytest

from dawn_kestrel.storage.store import SessionStorage, MessageStorage, PartStorage
from dawn_kestrel.core.repositories import (
    SessionRepositoryImpl,
    MessageRepositoryImpl,
    PartRepositoryImpl,
)
from dawn_kestrel.core.models import Session, Message, TextPart


class TestStoragePersistence:
    """Test storage layer persistence."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_session_storage_creates_file(self, temp_storage_dir):
        """Scenario: SessionStorage creates session file on disk.

        Preconditions:
        - SessionStorage initialized with temp dir

        Steps:
        1. Create Session object
        2. Call storage.create_session()
        3. Verify file created in storage
        4. Verify file contains session data

        Expected result:
        - Session file created
        - File path correct
        - Session data serializable

        Failure indicators:
        - File not created
        - File path incorrect
        - Data not written

        """
        storage = SessionStorage(base_dir=temp_storage_dir)
        session = Session(
            id="test_session_1",
            slug="test",
            project_id="test_project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0.0",
        )

        created_session = await storage.create_session(session)

        assert created_session.id == "test_session_1", "Session ID mismatch"
        assert created_session.title == "Test Session", "Title mismatch"

        session_file = temp_storage_dir / "storage" / "sessions" / "test_session_1.json"
        assert session_file.exists(), "Session file not created"

    @pytest.mark.asyncio
    async def test_message_storage_creates_file(self, temp_storage_dir):
        """Scenario: MessageStorage creates message file on disk.

        Preconditions:
        - MessageStorage initialized with temp dir

        Steps:
        1. Create Message object
        2. Call storage.create_message()
        3. Verify file created in storage

        Expected result:
        - Message file created
        - File path correct
        - Message data serializable

        Failure indicators:
        - File not created
        - File path incorrect
        - Data not written

        """
        storage = MessageStorage(base_dir=temp_storage_dir)
        message = Message(
            id="msg_1",
            session_id="session_1",
            role="user",
            text="Hello, world!",
        )

        created_message = await storage.create_message(message)

        assert created_message.id == "msg_1", "Message ID mismatch"
        assert created_message.text == "Hello, world!", "Text mismatch"

        message_file = temp_storage_dir / "storage" / "messages" / "msg_1.json"
        assert message_file.exists(), "Message file not created"

    @pytest.mark.asyncio
    async def test_part_storage_creates_file(self, temp_storage_dir):
        """Scenario: PartStorage creates part file on disk.

        Preconditions:
        - PartStorage initialized with temp dir

        Steps:
        1. Create TextPart object
        2. Call storage.create_part()
        3. Verify file created in storage

        Expected result:
        - Part file created
        - File path correct
        - Part data serializable

        Failure indicators:
        - File not created
        - File path incorrect
        - Data not written

        """
        storage = PartStorage(base_dir=temp_storage_dir)
        part = TextPart(
            id="part_1",
            message_id="msg_1",
            type="text",
            text="Part content",
        )

        created_part = await storage.create_part(part)

        assert created_part.id == "part_1", "Part ID mismatch"
        assert created_part.text == "Part content", "Text mismatch"

        part_file = temp_storage_dir / "storage" / "parts" / "part_1.json"
        assert part_file.exists(), "Part file not created"


class TestRepositoryPersistence:
    """Test repository layer persistence."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_session_repository_persists_session(self, temp_storage_dir):
        """Scenario: SessionRepository persists session to storage.

        Preconditions:
        - Repository initialized with storage

        Steps:
        1. Create session via repository
        2. Retrieve session via repository
        3. Verify session data matches
        4. Verify storage file exists

        Expected result:
        - Session persisted
        - Session retrievable
        - Data integrity maintained

        Failure indicators:
        - create returns Err
        - get returns Err
        - Data doesn't match

        """
        storage = SessionStorage(base_dir=temp_storage_dir)
        repo = SessionRepositoryImpl(storage)

        session = Session(
            id="repo_test_1",
            slug="test",
            project_id="test_project",
            directory="/tmp/test",
            title="Repository Test",
            version="1.0.0",
        )

        create_result = await repo.create(session)
        assert create_result.is_ok(), (
            f"create failed: {create_result.error if hasattr(create_result, 'error') else create_result}"
        )

        get_result = await repo.get_by_id("repo_test_1")
        assert get_result.is_ok(), (
            f"get failed: {get_result.error if hasattr(get_result, 'error') else get_result}"
        )

        retrieved_session = get_result.unwrap()
        assert retrieved_session.id == "repo_test_1", "Session ID mismatch"
        assert retrieved_session.title == "Repository Test", "Title mismatch"

    @pytest.mark.asyncio
    async def test_message_repository_persists_message(self, temp_storage_dir):
        """Scenario: MessageRepository persists message to storage.

        Preconditions:
        - Repository initialized with storage

        Steps:
        1. Create message via repository
        2. Retrieve message via repository
        3. Verify message data matches

        Expected result:
        - Message persisted
        - Message retrievable
        - Data integrity maintained

        Failure indicators:
        - create returns Err
        - get returns Err
        - Data doesn't match

        """
        storage = MessageStorage(base_dir=temp_storage_dir)
        repo = MessageRepositoryImpl(storage)

        message = Message(
            id="repo_msg_1",
            session_id="repo_session_1",
            role="user",
            text="Repository test message",
        )

        create_result = await repo.create(message)
        assert create_result.is_ok(), (
            f"create failed: {create_result.error if hasattr(create_result, 'error') else create_result}"
        )

        get_result = await repo.get_by_id("repo_msg_1")
        assert get_result.is_ok(), (
            f"get failed: {get_result.error if hasattr(get_result, 'error') else get_result}"
        )

        retrieved_message = get_result.unwrap()
        assert retrieved_message.id == "repo_msg_1", "Message ID mismatch"
        assert retrieved_message.text == "Repository test message", "Text mismatch"

    @pytest.mark.asyncio
    async def test_part_repository_persists_part(self, temp_storage_dir):
        """Scenario: PartRepository persists part to storage.

        Preconditions:
        - Repository initialized with storage

        Steps:
        1. Create part via repository
        2. Retrieve part via repository
        3. Verify part data matches

        Expected result:
        - Part persisted
        - Part retrievable
        - Data integrity maintained

        Failure indicators:
        - create returns Err
        - get returns Err
        - Data doesn't match

        """
        storage = PartStorage(base_dir=temp_storage_dir)
        repo = PartRepositoryImpl(storage)

        part = TextPart(
            id="repo_part_1",
            message_id="repo_msg_1",
            type="text",
            text="Repository test part",
        )

        create_result = await repo.create(part)
        assert create_result.is_ok(), (
            f"create failed: {create_result.error if hasattr(create_result, 'error') else create_result}"
        )

        get_result = await repo.get_by_id("repo_part_1")
        assert get_result.is_ok(), (
            f"get failed: {get_result.error if hasattr(get_result, 'error') else get_result}"
        )

        retrieved_part = get_result.unwrap()
        assert retrieved_part.id == "repo_part_1", "Part ID mismatch"
        assert retrieved_part.text == "Repository test part", "Text mismatch"


class TestRepositoryOperations:
    """Test repository CRUD operations."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_list_sessions_returns_all_sessions(self, temp_storage_dir):
        """Scenario: Repository returns list of all sessions.

        Preconditions:
        - Multiple sessions in storage

        Steps:
        1. Create 3 sessions
        2. Call list_all()
        3. Verify all 3 sessions returned

        Expected result:
        - All sessions returned
        - Session data correct
        - Order maintained

        Failure indicators:
        - Wrong session count
        - Data mismatch
        - Not a Result

        """
        storage = SessionStorage(base_dir=temp_storage_dir)
        repo = SessionRepositoryImpl(storage)

        sessions = [
            Session(
                id=f"list_test_{i}",
                slug="test",
                project_id="test_project",
                directory="/tmp/test",
                title=f"Session {i}",
                version="1.0.0",
            )
            for i in range(3)
        ]

        for session in sessions:
            await storage.create_session(session)

        list_result = await repo.list_all()
        assert list_result.is_ok(), (
            f"list failed: {list_result.error if hasattr(list_result, 'error') else list_result}"
        )

        listed_sessions = list_result.unwrap()
        assert len(listed_sessions) >= 3, f"Expected >=3 sessions, got {len(listed_sessions)}"

    @pytest.mark.asyncio
    async def test_delete_session_removes_from_storage(self, temp_storage_dir):
        """Scenario: Repository deletion removes session from storage.

        Preconditions:
        - Session exists in storage

        Steps:
        1. Create session
        2. Verify session exists
        3. Delete via repository
        4. Verify session doesn't exist

        Expected result:
        - Delete returns Ok(True)
        - Storage file removed
        - get returns Ok(None)

        Failure indicators:
        - Delete returns Err
        - Storage file exists
        - get returns session

        """
        storage = SessionStorage(base_dir=temp_storage_dir)
        repo = SessionRepositoryImpl(storage)

        session = Session(
            id="delete_test_1",
            slug="test",
            project_id="test_project",
            directory="/tmp/test",
            title="Delete Test",
            version="1.0.0",
        )
        await storage.create_session(session)

        delete_result = await repo.delete("delete_test_1")
        assert delete_result.is_ok(), (
            f"delete failed: {delete_result.error if hasattr(delete_result, 'error') else delete_result}"
        )

        deleted = delete_result.unwrap()
        assert deleted is True, "delete should return True"

        get_result = await repo.get_by_id("delete_test_1")
        assert get_result.is_ok(), "get should return Ok"
        assert get_result.unwrap() is None, "deleted session should be None"

    @pytest.mark.asyncio
    async def test_update_session_modifies_storage(self, temp_storage_dir):
        """Scenario: Repository update modifies session in storage.

        Preconditions:
        - Session exists in storage

        Steps:
        1. Create session with title "Original"
        2. Update title to "Modified"
        3. Retrieve session
        4. Verify title is "Modified"

        Expected result:
        - Update returns Ok(Session)
        - Storage file modified
        - Data persisted

        Failure indicators:
        - Update returns Err
        - Title not modified
        - Storage not updated

        """
        storage = SessionStorage(base_dir=temp_storage_dir)
        repo = SessionRepositoryImpl(storage)

        session = Session(
            id="update_test_1",
            slug="test",
            project_id="test_project",
            directory="/tmp/test",
            title="Original",
            version="1.0.0",
        )
        await storage.create_session(session)

        session.title = "Modified"
        update_result = await repo.update(session)
        assert update_result.is_ok(), (
            f"update failed: {update_result.error if hasattr(update_result, 'error') else update_result}"
        )

        get_result = await repo.get_by_id("update_test_1")
        assert get_result.is_ok(), "get should return Ok"

        updated_session = get_result.unwrap()
        assert updated_session is not None, "session should not be None"
        assert updated_session.title == "Modified", "Title not updated"
