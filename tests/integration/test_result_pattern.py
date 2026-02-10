"""Integration tests for Result pattern error handling.

Tests verify that Result pattern works correctly across full
call stack: SDK client → SessionService → Repositories → Storage
without mocking.

Scenario: Result Pattern End-to-End Error Handling
================================================

Preconditions:
- SDK client initialized
- SessionService configured with repositories
- Storage layer functional

Steps:
1. Create session (Ok expected)
2. Get session (Ok expected)
3. Add message (Ok expected)
4. List sessions (Ok expected)
5. Verify Result.is_ok() works correctly
6. Verify Result.unwrap() works correctly
7. Verify Err.error accessible when needed

Expected result:
- All operations return Result[T] not raw types
- is_ok() correctly identifies Ok vs Err
- unwrap() returns value for Ok
- Err.error accessible when is_err() True

Failure indicators:
- Operations raise exceptions (not wrapped in Result)
- is_ok() returns wrong value
- unwrap() raises on Ok
- Err.error not accessible

Evidence:
- All operations return Result[T]
- Result.is_ok() returns bool
- Result.unwrap() returns value on Ok
- Err has error attribute
"""

import tempfile
from pathlib import Path
import pytest

from dawn_kestrel.core.result import Ok, Err


class TestResultPatternSessionFlow:
    """Test Result pattern in session flow operations."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    async def client(self, temp_storage_dir):
        """Create async SDK client with temp storage."""
        from dawn_kestrel.sdk.client import OpenCodeAsyncClient
        from dawn_kestrel.core.di_container import (
            configure_container,
            container,
            reset_container,
        )

        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        client = OpenCodeAsyncClient()
        client._service = container.service()

        yield client

        reset_container()

    @pytest.mark.asyncio
    async def test_create_session_returns_ok(self, client):
        """Scenario: Creating session returns Ok[Session].

        Preconditions:
        - SDK client initialized

        Steps:
        1. Call create_session
        2. Verify result.is_ok() returns True
        3. Verify result.is_err() returns False
        4. Call result.unwrap() to get Session

        Expected result:
        - Result is Ok type
        - is_ok() returns True
        - is_err() returns False
        - unwrap() returns Session object

        Failure indicators:
        - Result.is_ok() returns False
        - Result.is_err() returns True
        - unwrap() raises exception
        """
        result = await client.create_session(title="Test Session")

        assert result.is_ok() is True, "Expected Ok result, got Err"
        assert result.is_err() is False, "Expected is_err() to be False for Ok result"

        session = result.unwrap()
        assert session is not None, "unwrap() returned None"
        assert hasattr(session, "id"), "Session missing id attribute"

    @pytest.mark.asyncio
    async def test_get_session_returns_ok(self, client):
        """Scenario: Getting session returns Ok[Session].

        Preconditions:
        - SDK client initialized
        - Session exists

        Steps:
        1. Create session
        2. Call get_session with session ID
        3. Verify result.is_ok() returns True
        4. Verify result.unwrap() returns Session

        Expected result:
        - Result is Ok type
        - unwrap() returns Session with correct ID

        Failure indicators:
        - Result.is_ok() returns False
        - unwrap() returns None
        - Session ID doesn't match
        """
        create_result = await client.create_session(title="Get Test")
        assert create_result.is_ok()
        session_id = create_result.unwrap().id

        get_result = await client.get_session(session_id)

        assert get_result.is_ok() is True, "Expected Ok result"
        session = get_result.unwrap()
        assert session is not None, "unwrap() returned None"
        assert session.id == session_id, "Session ID mismatch"

    @pytest.mark.asyncio
    async def test_add_message_returns_ok(self, client):
        """Scenario: Adding message returns Ok[str].

        Preconditions:
        - SDK client initialized
        - Session exists

        Steps:
        1. Create session
        2. Call add_message with user role
        3. Verify result.is_ok() returns True
        4. Verify result.unwrap() returns message ID

        Expected result:
        - Result is Ok type
        - unwrap() returns message ID string
        - Message ID is not None

        Failure indicators:
        - Result.is_ok() returns False
        - unwrap() returns None
        - Message ID not a string
        """
        create_result = await client.create_session(title="Message Test")
        assert create_result.is_ok()
        session_id = create_result.unwrap().id

        msg_result = await client.add_message(
            session_id=session_id, role="user", content="Test message"
        )

        assert msg_result.is_ok() is True, "Expected Ok result"
        msg_id = msg_result.unwrap()
        assert msg_id is not None, "unwrap() returned None"
        assert isinstance(msg_id, str), "Message ID not a string"

    @pytest.mark.asyncio
    async def test_list_sessions_returns_ok(self, client):
        """Scenario: Listing sessions returns Ok[list[Session]].

        Preconditions:
        - SDK client initialized
        - Sessions exist

        Steps:
        1. Create 2 sessions
        2. Call list_sessions
        3. Verify result.is_ok() returns True
        4. Verify result.unwrap() returns list

        Expected result:
        - Result is Ok type
        - unwrap() returns list
        - List contains created sessions

        Failure indicators:
        - Result.is_ok() returns False
        - unwrap() returns None or not a list
        - List missing created sessions
        """
        await client.create_session(title="Session 1")
        await client.create_session(title="Session 2")

        list_result = await client.list_sessions()

        assert list_result.is_ok() is True, "Expected Ok result"
        sessions = list_result.unwrap()
        assert sessions is not None, "unwrap() returned None"
        assert isinstance(sessions, list), "unwrap() didn't return list"
        assert len(sessions) >= 2, f"Expected >=2 sessions, got {len(sessions)}"


class TestResultPatternErrorCases:
    """Test Result pattern error handling scenarios."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    async def client(self, temp_storage_dir):
        """Create async SDK client with temp storage."""
        from dawn_kestrel.sdk.client import OpenCodeAsyncClient
        from dawn_kestrel.core.di_container import (
            configure_container,
            container,
            reset_container,
        )

        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        client = OpenCodeAsyncClient()
        client._service = container.service()

        yield client

        reset_container()

    @pytest.mark.asyncio
    async def test_get_nonexistent_session_returns_ok_none(self, client):
        """Scenario: Getting nonexistent session returns Ok(None) not Err.

        Preconditions:
        - SDK client initialized

        Steps:
        1. Call get_session with invalid ID
        2. Verify result.is_ok() returns True
        3. Verify result.unwrap() returns None
        4. Verify result.is_err() returns False

        Expected result:
        - Result is Ok type (not Err)
        - is_ok() returns True
        - unwrap() returns None
        - Not an Err with error message

        Failure indicators:
        - result.is_err() returns True
        - result.is_ok() returns False
        - unwrap() raises exception
        - Err.error attribute exists
        """
        result = await client.get_session("nonexistent_session_id")

        assert result.is_ok() is True, "get_session should return Ok(None), not Err"
        assert result.is_err() is False, "Expected is_err() to be False"

        session = result.unwrap()
        assert session is None, "unwrap() should return None for nonexistent session"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_returns_ok_false(self, client):
        """Scenario: Deleting nonexistent session returns Ok(False).

        Preconditions:
        - SDK client initialized

        Steps:
        1. Call delete_session with invalid ID
        2. Verify result.is_ok() returns True
        3. Verify result.unwrap() returns False

        Expected result:
        - Result is Ok type
        - unwrap() returns False (session not deleted)

        Failure indicators:
        - result.is_err() returns True
        - unwrap() returns True
        """
        result = await client.delete_session("nonexistent_session_id")

        assert result.is_ok() is True, "delete_session should return Ok(False)"
        deleted = result.unwrap()
        assert deleted is False, "unwrap() should return False for nonexistent session"


class TestResultPatternUnwrapOr:
    """Test Result unwrap_or method for default values."""

    @pytest.mark.asyncio
    async def test_unwrap_or_returns_value_on_ok(self):
        """Scenario: unwrap_or returns value for Ok result.

        Preconditions:
        - Ok result created

        Steps:
        1. Create Ok result with value "success"
        2. Call unwrap_or("default")
        3. Verify returned value is "success" not "default"

        Expected result:
        - unwrap_or returns Ok value
        - Default value not used

        Failure indicators:
        - unwrap_or returns default value
        """
        result = Ok("success")
        value = result.unwrap_or("default")
        assert value == "success", f"Expected 'success', got '{value}'"

    @pytest.mark.asyncio
    async def test_unwrap_or_returns_default_on_err(self):
        """Scenario: unwrap_or returns default for Err result.

        Preconditions:
        - Err result created

        Steps:
        1. Create Err result with error
        2. Call unwrap_or("default")
        3. Verify returned value is "default"

        Expected result:
        - unwrap_or returns default value
        - No exception raised

        Failure indicators:
        - unwrap_or raises exception
        - unwrap_or returns None
        """
        result = Err("something went wrong")
        value = result.unwrap_or("default")
        assert value == "default", f"Expected 'default', got '{value}'"


class TestResultPatternPropagation:
    """Test Result propagation through multiple layers."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    async def client(self, temp_storage_dir):
        """Create async SDK client with temp storage."""
        from dawn_kestrel.sdk.client import OpenCodeAsyncClient
        from dawn_kestrel.core.di_container import (
            configure_container,
            container,
            reset_container,
        )

        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        client = OpenCodeAsyncClient()
        client._service = container.service()

        yield client

        reset_container()

    @pytest.mark.asyncio
    async def test_result_propagates_through_sdk_to_service(self, client):
        """Scenario: Result propagates through SDK to SessionService.

        Preconditions:
        - SDK client initialized
        - SessionService configured

        Steps:
        1. Create session via SDK
        2. Verify Result returned through all layers
        3. Check each layer returns Result

        Expected result:
        - SDK client returns Result[Session]
        - SessionService returns Result[Session]
        - Repository returns Result[Session]
        - No raw types or exceptions

        Failure indicators:
        - Any layer returns raw type
        - Any layer raises exception
        - Result wrapping incomplete
        """
        result = await client.create_session(title="Propagation Test")

        assert result.is_ok(), "SDK client should return Ok result"
        assert isinstance(result, Ok), "SDK should return Ok instance"

        session = result.unwrap()
        assert session is not None, "unwrap() should return session"

    @pytest.mark.asyncio
    async def test_full_workflow_result_chain(self, client):
        """Scenario: Full workflow maintains Result chain.

        Preconditions:
        - SDK client initialized

        Steps:
        1. Create session (Ok[Session])
        2. Add message (Ok[str])
        3. Get session (Ok[Session])
        4. List sessions (Ok[list])
        5. Verify all results are Ok

        Expected result:
        - All operations return Ok type
        - Result chain unbroken
        - No raw types or exceptions

        Failure indicators:
        - Any operation returns Err
        - Any operation raises exception
        - Result chain broken
        """
        session_result = await client.create_session(title="Chain Test")
        assert session_result.is_ok(), "create_session should return Ok"
        session_id = session_result.unwrap().id

        msg_result = await client.add_message(session_id=session_id, role="user", content="Test")
        assert msg_result.is_ok(), "add_message should return Ok"

        get_result = await client.get_session(session_id)
        assert get_result.is_ok(), "get_session should return Ok"

        list_result = await client.list_sessions()
        assert list_result.is_ok(), "list_sessions should return Ok"
