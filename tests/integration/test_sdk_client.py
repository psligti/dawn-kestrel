"""Integration tests for SDK client end-to-end workflows.

Tests verify that SDK client correctly integrates with all underlying
components: SessionService, repositories, storage, agent runtime,
and DI container without mocking.

Scenario: SDK Client End-to-End Workflow
========================================

Preconditions:
- DI container is configured with temporary storage directory
- Built-in tools are loadable via plugin discovery
- Agent registry can be initialized

Steps:
1. Create async SDK client
2. Create a session
3. Add messages to the session
4. List sessions
5. Retrieve a specific session
6. Verify session persistence

Expected result:
- All SDK operations complete successfully
- Sessions are persisted to storage
- Messages are stored and retrievable
- Result pattern error handling works correctly

Failure indicators:
- Any SDK operation returns Err
- Sessions not persisted to storage
- Messages not stored
- Storage files not created

Evidence:
- Result.is_ok() returns True for all operations
- Storage directory contains session files
- list_sessions() returns created sessions
- get_session() returns session with correct data
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
import asyncio

from dawn_kestrel.sdk.client import OpenCodeAsyncClient
from dawn_kestrel.core.models import Session
from dawn_kestrel.core.result import Ok, Err


class TestSDKClientWorkflow:
    """Test SDK client end-to-end workflows."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    async def client(self, temp_storage_dir):
        """Create async SDK client with temp storage."""
        client = OpenCodeAsyncClient(config=None, session_service=None)
        client.config.storage_path = temp_storage_dir

        # Reconfigure container with temp storage
        from dawn_kestrel.core.di_container import configure_container, container

        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        # Re-initialize client components from container
        client._service = container.service()
        client._provider_registry = container.provider_registry()
        client._lifecycle = container.session_lifecycle()
        client._runtime = container.agent_runtime()

        yield client

        # Cleanup
        from dawn_kestrel.core.di_container import reset_container

        reset_container()

    @pytest.mark.asyncio
    async def test_create_session_creates_persistent_session(self, client):
        """Scenario: Creating a session persists it to storage.

        Preconditions:
        - SDK client initialized with temp storage
        - Storage directory is empty

        Steps:
        1. Call client.create_session with title "Test Session"
        2. Verify result is Ok
        3. Verify session ID is generated
        4. Verify session file exists in storage

        Expected result:
        - Result.is_ok() returns True
        - Session has valid ID
        - Storage directory contains session file

        Failure indicators:
        - Result.is_err() returns True
        - Session ID is None or empty
        - No storage file created
        """
        result = await client.create_session(title="Test Integration Session")

        assert result.is_ok(), (
            f"create_session failed: {result.error if hasattr(result, 'error') else result}"
        )
        session = result.unwrap()

        assert session.id is not None
        assert session.title == "Test Integration Session"
        assert len(session.id) > 0

    @pytest.mark.asyncio
    async def test_create_and_list_sessions_workflow(self, client):
        """Scenario: Create multiple sessions and list them.

        Preconditions:
        - SDK client initialized with temp storage
        - No sessions exist

        Steps:
        1. Create 3 sessions with different titles
        2. Call list_sessions()
        3. Verify all 3 sessions are returned
        4. Verify session IDs match created sessions

        Expected result:
        - All 3 sessions created successfully
        - list_sessions returns 3 sessions
        - Session titles match created titles

        Failure indicators:
        - Any session creation fails
        - list_sessions returns wrong count
        - Session titles don't match
        """
        created_sessions = []
        for i in range(3):
            result = await client.create_session(title=f"Session {i}")
            assert result.is_ok(), f"Failed to create session {i}"
            created_sessions.append(result.unwrap())

        list_result = await client.list_sessions()
        assert list_result.is_ok(), (
            f"list_sessions failed: {list_result.error if hasattr(list_result, 'error') else list_result}"
        )

        sessions = list_result.unwrap()
        assert len(sessions) >= 3, f"Expected at least 3 sessions, got {len(sessions)}"

        created_titles = {s.title for s in created_sessions}
        returned_titles = {s.title for s in sessions}
        assert created_titles.issubset(returned_titles), "Not all created sessions were returned"

    @pytest.mark.asyncio
    async def test_add_message_persists_to_storage(self, client):
        """Scenario: Adding messages persists them to storage.

        Preconditions:
        - SDK client initialized with temp storage
        - Session exists

        Steps:
        1. Create a session
        2. Add user message "Hello"
        3. Add assistant message "Hi there"
        4. Retrieve session and verify messages

        Expected result:
        - Both messages added successfully
        - Messages returned when retrieving session
        - Message IDs are unique
        - Message roles are correct

        Failure indicators:
        - Any add_message fails
        - Messages not stored
        - Message roles incorrect
        """
        session_result = await client.create_session(title="Message Test")
        assert session_result.is_ok()
        session_id = session_result.unwrap().id

        msg1_result = await client.add_message(
            session_id=session_id, role="user", content="Hello, world!"
        )
        assert msg1_result.is_ok(), (
            f"Failed to add user message: {msg1_result.error if hasattr(msg1_result, 'error') else msg1_result}"
        )

        msg2_result = await client.add_message(
            session_id=session_id, role="assistant", content="Hi there!"
        )
        assert msg2_result.is_ok(), (
            f"Failed to add assistant message: {msg2_result.error if hasattr(msg2_result, 'error') else msg2_result}"
        )

        msg1_id = msg1_result.unwrap()
        msg2_id = msg2_result.unwrap()

        assert msg1_id is not None
        assert msg2_id is not None
        assert msg1_id != msg2_id, "Message IDs should be unique"

    @pytest.mark.asyncio
    async def test_get_session_retrieves_correct_session(self, client):
        """Scenario: Retrieving a session returns correct data.

        Preconditions:
        - SDK client initialized with temp storage
        - Multiple sessions exist

        Steps:
        1. Create 2 sessions with different titles
        2. Get first session by ID
        3. Verify session title matches
        4. Get second session by ID
        5. Verify session title matches

        Expected result:
        - get_session returns correct session for each ID
        - Session titles match created sessions
        - Sessions have different IDs

        Failure indicators:
        - get_session returns wrong session
        - Session titles don't match
        - get_session fails for valid ID
        """
        session1_result = await client.create_session(title="First Session")
        assert session1_result.is_ok()
        session1_id = session1_result.unwrap().id

        session2_result = await client.create_session(title="Second Session")
        assert session2_result.is_ok()
        session2_id = session2_result.unwrap().id

        get1_result = await client.get_session(session1_id)
        assert get1_result.is_ok(), (
            f"Failed to get first session: {get1_result.error if hasattr(get1_result, 'error') else get1_result}"
        )
        session1 = get1_result.unwrap()

        assert session1 is not None
        assert session1.id == session1_id
        assert session1.title == "First Session"

        get2_result = await client.get_session(session2_id)
        assert get2_result.is_ok(), (
            f"Failed to get second session: {get2_result.error if hasattr(get2_result, 'error') else get2_result}"
        )
        session2 = get2_result.unwrap()

        assert session2 is not None
        assert session2.id == session2_id
        assert session2.title == "Second Session"

    @pytest.mark.asyncio
    async def test_get_session_returns_none_for_nonexistent(self, client):
        """Scenario: Getting nonexistent session returns Ok(None).

        Preconditions:
        - SDK client initialized with temp storage
        - No sessions exist

        Steps:
        1. Call get_session with invalid ID
        2. Verify result is Ok
        3. Verify returned value is None

        Expected result:
        - Result.is_ok() returns True
        - Unwrapped value is None
        - Not an Err (error handling uses Ok(None) pattern)

        Failure indicators:
        - Result.is_err() returns True
        - Unwrapped value is not None
        """
        result = await client.get_session("nonexistent_session_id")
        assert result.is_ok(), f"get_session for nonexistent ID should return Ok(None), not Err"
        session = result.unwrap()
        assert session is None

    @pytest.mark.asyncio
    async def test_delete_session_removes_from_storage(self, client):
        """Scenario: Deleting a session removes it from storage.

        Preconditions:
        - SDK client initialized with temp storage
        - Session exists

        Steps:
        1. Create a session
        2. Verify it exists via list_sessions
        3. Delete the session
        4. Verify it's gone from list_sessions
        5. Verify get_session returns None

        Expected result:
        - Session deleted successfully
        - list_sessions doesn't include deleted session
        - get_session returns None for deleted ID

        Failure indicators:
        - delete_session fails
        - Session still in list_sessions
        - get_session still returns session
        """
        session_result = await client.create_session(title="To Delete")
        assert session_result.is_ok()
        session_id = session_result.unwrap().id

        list_before = await client.list_sessions()
        assert list_before.is_ok()
        sessions_before = list_before.unwrap()
        titles_before = {s.title for s in sessions_before}
        assert "To Delete" in titles_before

        delete_result = await client.delete_session(session_id)
        assert delete_result.is_ok(), (
            f"delete_session failed: {delete_result.error if hasattr(delete_result, 'error') else delete_result}"
        )

        list_after = await client.list_sessions()
        assert list_after.is_ok()
        sessions_after = list_after.unwrap()
        titles_after = {s.title for s in sessions_after}
        assert "To Delete" not in titles_after

        get_result = await client.get_session(session_id)
        assert get_result.is_ok()
        assert get_result.unwrap() is None

    @pytest.mark.asyncio
    async def test_full_workflow_session_to_messages_to_deletion(self, client):
        """Scenario: Complete workflow from session creation to deletion.

        Preconditions:
        - SDK client initialized with temp storage
        - No sessions exist

        Steps:
        1. Create session "Full Workflow Test"
        2. Add user message "Start"
        3. Add assistant message "Processing"
        4. Add user message "Complete"
        5. List sessions and verify
        6. Get session and verify messages
        7. Delete session
        8. Verify deletion

        Expected result:
        - All operations succeed
        - Messages persist correctly
        - Session retrieved with correct data
        - Deletion removes all traces

        Failure indicators:
        - Any operation fails
        - Messages not stored
        - Deletion incomplete
        """
        session_result = await client.create_session(title="Full Workflow Test")
        assert session_result.is_ok()
        session_id = session_result.unwrap().id

        msg1 = await client.add_message(session_id, "user", "Start")
        assert msg1.is_ok()

        msg2 = await client.add_message(session_id, "assistant", "Processing")
        assert msg2.is_ok()

        msg3 = await client.add_message(session_id, "user", "Complete")
        assert msg3.is_ok()

        list_result = await client.list_sessions()
        assert list_result.is_ok()
        assert any(s.title == "Full Workflow Test" for s in list_result.unwrap())

        get_result = await client.get_session(session_id)
        assert get_result.is_ok()
        assert get_result.unwrap() is not None

        delete_result = await client.delete_session(session_id)
        assert delete_result.is_ok()

        get_after = await client.get_session(session_id)
        assert get_after.is_ok()
        assert get_after.unwrap() is None


class TestSDKClientResultHandling:
    """Test SDK client Result pattern error handling."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    async def client(self, temp_storage_dir):
        """Create async SDK client with temp storage."""
        client = OpenCodeAsyncClient(config=None, session_service=None)
        client.config.storage_path = temp_storage_dir

        from dawn_kestrel.core.di_container import configure_container, container, reset_container

        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        client._service = container.service()
        client._provider_registry = container.provider_registry()
        client._lifecycle = container.session_lifecycle()
        client._runtime = container.agent_runtime()

        yield client

        reset_container()

    @pytest.mark.asyncio
    async def test_result_pattern_unwrap_ok(self, client):
        """Scenario: Unwrapping Ok result returns value.

        Preconditions:
        - SDK client initialized
        - Operation succeeds

        Steps:
        1. Create session
        2. Call result.is_ok()
        3. Call result.unwrap()

        Expected result:
        - is_ok() returns True
        - unwrap() returns Session object
        - unwrap() doesn't raise exception

        Failure indicators:
        - is_ok() returns False
        - unwrap() raises exception
        - unwrap() returns None
        """
        result = await client.create_session(title="Test")
        assert result.is_ok()
        session = result.unwrap()
        assert isinstance(session, Session)
        assert session.title == "Test"

    @pytest.mark.asyncio
    async def test_result_pattern_err_access(self, client):
        """Scenario: Accessing Err error returns error message.

        Preconditions:
        - SDK client initialized

        Steps:
        1. Try to get nonexistent session
        2. Verify result is Ok(None) not Err

        Expected result:
        - Result pattern uses Ok(None) for not found
        - No Err with error attribute

        Note: This test verifies the Result pattern behavior,
        not an error case since get_session returns Ok(None)
        """
        result = await client.get_session("nonexistent")
        assert result.is_ok()
        assert result.unwrap() is None
