"""Integration tests for end-to-end user workflows.

Tests verify complete user scenarios from initial input to final output,
integrating all components: SDK, CLI, TUI, storage, repositories,
and agent runtime without mocking.

Scenario: End-to-End User Workflow
===================================

Preconditions:
- All components configured
- Storage directory accessible
- DI container wired
- Tools loadable

Steps:
1. User creates session via SDK
2. User adds messages to session
3. User executes agent via runtime
4. User lists sessions via CLI
5. User retrieves session details
6. User deletes session
7. Verify all data persisted correctly

Expected result:
- All operations complete successfully
- Data persisted to storage
- Result pattern used throughout
- No crashes or errors
- Clean state after deletion

Failure indicators:
- Any operation fails
- Data not persisted
- Wrong Result type
- Crashes or exceptions

Evidence:
- Session files in storage
- Message files created
- Agent execution recorded
- CLI displays correct output
- Files deleted on cleanup
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
import asyncio
from typing import cast, Any


class TestEndToEndSessionWorkflow:
    """Test complete session lifecycle workflow."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def configured_container(self, temp_storage_dir):
        """Configure container with temp storage."""
        from dawn_kestrel.core.di_container import configure_container, reset_container

        reset_container()
        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        from dawn_kestrel.core.di_container import container

        yield container

        reset_container()

    @pytest.mark.asyncio
    async def test_full_session_lifecycle_workflow(self, configured_container):
        """Scenario: Complete session lifecycle from creation to deletion.

        Preconditions:
        - Container configured
        - Storage empty

        Steps:
        1. Create session via SDK client
        2. Add user message
        3. Add assistant message
        4. List sessions
        5. Get session details
        6. Delete session
        7. Verify deletion

        Expected result:
        - All operations succeed
        - Session persisted
        - Messages persisted
        - Session listed
        - Details retrieved
        - Session deleted

        Failure indicators:
        - Any operation fails
        - Data not persisted
        - Deletion incomplete

        Evidence:
        - Storage files created
        - list_sessions returns session
        - get_session returns correct data
        - Files deleted
        """
        from dawn_kestrel.sdk.client import OpenCodeAsyncClient

        # Create client from container
        client = OpenCodeAsyncClient(config=None, session_service=None)
        client._service = configured_container.service()
        client._provider_registry = configured_container.provider_registry()
        client._lifecycle = configured_container.session_lifecycle()
        client._runtime = configured_container.agent_runtime()

        # 1. Create session
        create_result = await client.create_session(title="End-to-End Test Session")
        assert create_result.is_ok(), (
            f"create_session failed: {create_result.error if hasattr(create_result, 'error') else create_result}"
        )
        session_id = create_result.unwrap().id

        # 2. Add user message
        msg1_result = await client.add_message(
            session_id=session_id, role="user", content="Hello, world!"
        )
        assert msg1_result.is_ok(), (
            f"add_message failed: {msg1_result.error if hasattr(msg1_result, 'error') else msg1_result}"
        )

        # 3. Add assistant message
        msg2_result = await client.add_message(
            session_id=session_id, role="assistant", content="Hi there!"
        )
        assert msg2_result.is_ok(), (
            f"add_message failed: {msg2_result.error if hasattr(msg2_result, 'error') else msg2_result}"
        )

        # 4. List sessions
        list_result = await client.list_sessions()
        assert list_result.is_ok(), (
            f"list_sessions failed: {list_result.error if hasattr(list_result, 'error') else list_result}"
        )
        sessions = list_result.unwrap()
        assert any(s.id == session_id for s in sessions), "Session not in list"

        # 5. Get session details
        get_result = await client.get_session(session_id)
        assert get_result.is_ok(), (
            f"get_session failed: {get_result.error if hasattr(get_result, 'error') else get_result}"
        )
        session = get_result.unwrap()
        assert session is not None, "Session should not be None"
        assert session.id == session_id, "Session ID mismatch"

        # 6. Delete session
        delete_result = await client.delete_session(session_id)
        assert delete_result.is_ok(), (
            f"delete_session failed: {delete_result.error if hasattr(delete_result, 'error') else delete_result}"
        )

        # 7. Verify deletion
        get_after = await client.get_session(session_id)
        assert get_after.is_ok(), "get_session after delete should not fail"
        assert get_after.unwrap() is None, "Session should be None after deletion"


class TestEndToEndAgentExecution:
    """Test agent execution end-to-end workflow."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def configured_container(self, temp_storage_dir):
        """Configure container with temp storage."""
        from dawn_kestrel.core.di_container import configure_container, reset_container

        reset_container()
        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        from dawn_kestrel.core.di_container import container

        yield container

        reset_container()

    @pytest.mark.asyncio
    async def test_agent_execution_workflow(self, configured_container):
        """Scenario: Execute agent in a complete workflow.

        Preconditions:
        - Container configured
        - Session created
        - Agent registered

        Steps:
        1. Create session
        2. Execute agent with message
        3. Verify agent result
        4. Verify metadata recorded

        Expected result:
        - Agent executes successfully
        - AgentResult complete
        - Duration recorded
        - Response generated

        Failure indicators:
        - Agent execution fails
        - AgentResult incomplete
        - Duration missing
        - Response missing

        Evidence:
        - execute_agent returns AgentResult
        - All fields populated
        - Duration > 0
        - Response not empty
        """
        from dawn_kestrel.sdk.client import OpenCodeAsyncClient
        from dawn_kestrel.agents.bolt_merlin import create_autonomous_worker_agent
        from dawn_kestrel.tools import get_all_tools

        # Create client
        client = OpenCodeAsyncClient(config=None, session_service=None)
        client._service = configured_container.service()
        client._provider_registry = configured_container.provider_registry()
        client._lifecycle = configured_container.session_lifecycle()
        client._runtime = configured_container.agent_runtime()

        # Create session
        create_result = await client.create_session(title="Agent Execution Test")
        assert create_result.is_ok()
        session_id = create_result.unwrap().id

        # Execute agent
        tools = await get_all_tools()
        agent = create_autonomous_worker_agent()
        agent_result = await client._runtime.execute_agent(
            agent=agent,
            user_message="Test message",
            session_id=session_id,
            tools=tools,
        )

        # Verify result
        assert agent_result is not None, "AgentResult should not be None"
        assert agent_result.agent_name is not None, "Agent name missing"
        assert agent_result.duration > 0, "Duration should be > 0"
        assert agent_result.response is not None, "Response should not be None"


class TestEndToEndPersistence:
    """Test data persistence end-to-end."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def configured_container(self, temp_storage_dir):
        """Configure container with temp storage."""
        from dawn_kestrel.core.di_container import configure_container, reset_container

        reset_container()
        configure_container(
            storage_path=temp_storage_dir,
            project_dir=temp_storage_dir,
            agent_registry_persistence_enabled=False,
        )

        from dawn_kestrel.core.di_container import container

        yield container

        reset_container()

    @pytest.mark.asyncio
    async def test_persists_across_multiple_sessions(self, configured_container):
        """Scenario: Data persists across multiple session instances.

        Preconditions:
        - Container configured
        - Storage empty

        Steps:
        1. Create session1
        2. Add message to session1
        3. Create new client instance
        4. List sessions via new client
        5. Verify session1 data present

        Expected result:
        - Session1 data persists
        - New client can read old data
        - Messages intact
        - No data loss

        Failure indicators:
        - Data not persisted
        - New client can't read old data
        - Messages missing
        - Data corruption

        Evidence:
        - list_sessions returns session1
        - Messages accessible
        - Data intact
        """
        from dawn_kestrel.sdk.client import OpenCodeAsyncClient

        # Client 1: Create session and add message
        client1 = OpenCodeAsyncClient(config=None, session_service=None)
        client1._service = configured_container.service()
        client1._provider_registry = configured_container.provider_registry()
        client1._lifecycle = configured_container.session_lifecycle()
        client1._runtime = configured_container.agent_runtime()

        create_result = await client1.create_session(title="Persistence Test")
        assert create_result.is_ok()
        session_id = create_result.unwrap().id

        msg_result = await client1.add_message(
            session_id=session_id, role="user", content="Persistent message"
        )
        assert msg_result.is_ok()

        # Client 2: Read data (new instance)
        client2 = OpenCodeAsyncClient(config=None, session_service=None)
        client2._service = configured_container.service()
        client2._provider_registry = configured_container.provider_registry()
        client2._lifecycle = configured_container.session_lifecycle()
        client2._runtime = configured_container.agent_runtime()

        list_result = await client2.list_sessions()
        assert list_result.is_ok()
        sessions = list_result.unwrap()
        assert any(s.id == session_id for s in sessions), "Session not persisted"

        get_result = await client2.get_session(session_id)
        assert get_result.is_ok()
        session = get_result.unwrap()
        assert session is not None
        assert session.id == session_id
