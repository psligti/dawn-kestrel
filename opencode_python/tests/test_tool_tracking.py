"""
Tests for tool execution tracking and session lifecycle.
"""
import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from opencode_python.agents.tool_execution_tracker import ToolExecutionTracker, create_tool_tracker
from opencode_python.core.session_lifecycle import (
    SessionLifecycle,
    create_session_lifecycle,
    SessionLifecycleListener,
)
from opencode_python.core.models import ToolState, Session, Message
from opencode_python.core.event_bus import bus, Events


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_session():
    """Create a sample session for testing"""
    return Session(
        id="test-session-id",
        slug="test-session",
        project_id="test-project",
        directory="/tmp/test",
        title="Test Session",
        version="1.0.0",
    )


@pytest.fixture
def sample_message():
    """Create a sample message for testing"""
    return Message(
        id="test-message-id",
        session_id="test-session-id",
        role="user",
        text="Test message",
        time={"created": 0.0},
    )


@pytest.fixture
def sample_tool_state():
    """Create a sample tool state for testing"""
    return ToolState(
        status="pending",
        input={"param": "value"},
        output=None,
    )


class TestToolExecutionTracker:
    """Tests for ToolExecutionTracker"""

    def test_create_tracker(self, temp_dir):
        """Test creating a tool tracker"""
        tracker = ToolExecutionTracker(temp_dir)

        assert tracker.base_dir == temp_dir
        assert tracker.storage_dir == temp_dir / "storage" / "tool_execution"

    def test_log_execution(self, temp_dir, sample_tool_state):
        """Test logging a tool execution"""
        tracker = create_tool_tracker(temp_dir)

        session_id = "session-123"
        message_id = "message-456"
        tool_id = "test-tool"
        execution_id = "execution-789"

        asyncio.run(tracker.log_execution(
            execution_id=execution_id,
            session_id=session_id,
            message_id=message_id,
            tool_id=tool_id,
            state=sample_tool_state,
            start_time=1000.0,
            end_time=2000.0,
        ))

        execution_file = (
            temp_dir / "storage" / "tool_execution" / session_id / f"{execution_id}.json"
        )
        assert execution_file.exists()

        with open(execution_file, "r") as f:
            record = json.load(f)

        assert record["id"] == execution_id
        assert record["session_id"] == session_id
        assert record["message_id"] == message_id
        assert record["tool_id"] == tool_id
        assert record["start_time"] == 1000.0
        assert record["end_time"] == 2000.0
        assert record["state"]["status"] == "pending"

    def test_get_execution_history(self, temp_dir, sample_tool_state):
        """Test retrieving execution history"""
        tracker = create_tool_tracker(temp_dir)
        session_id = "session-123"

        execution_id_1 = "exec-1"
        execution_id_2 = "exec-2"

        asyncio.run(tracker.log_execution(
            execution_id=execution_id_1,
            session_id=session_id,
            message_id="msg-1",
            tool_id="tool-1",
            state=sample_tool_state,
        ))

        asyncio.run(tracker.log_execution(
            execution_id=execution_id_2,
            session_id=session_id,
            message_id="msg-2",
            tool_id="tool-2",
            state=ToolState(
                status="completed",
                input={"param": "value"},
                output="result",
            ),
        ))

        history = asyncio.run(tracker.get_execution_history(session_id))

        assert len(history) == 2
        assert history[0]["id"] == execution_id_2
        assert history[1]["id"] == execution_id_1

    def test_get_execution_history_with_filter(self, temp_dir, sample_tool_state):
        """Test retrieving execution history with tool filter"""
        tracker = create_tool_tracker(temp_dir)
        session_id = "session-123"

        asyncio.run(tracker.log_execution(
            execution_id="exec-1",
            session_id=session_id,
            message_id="msg-1",
            tool_id="tool-1",
            state=sample_tool_state,
        ))

        asyncio.run(tracker.log_execution(
            execution_id="exec-2",
            session_id=session_id,
            message_id="msg-2",
            tool_id="tool-2",
            state=sample_tool_state,
        ))

        history = asyncio.run(tracker.get_execution_history(session_id, tool_id="tool-1"))

        assert len(history) == 1
        assert history[0]["tool_id"] == "tool-1"

    def test_get_execution_history_with_limit(self, temp_dir, sample_tool_state):
        """Test retrieving execution history with limit"""
        tracker = create_tool_tracker(temp_dir)
        session_id = "session-123"

        for i in range(5):
            asyncio.run(tracker.log_execution(
                execution_id=f"exec-{i}",
                session_id=session_id,
                message_id=f"msg-{i}",
                tool_id=f"tool-{i}",
                state=sample_tool_state,
            ))

        history = asyncio.run(tracker.get_execution_history(session_id, limit=3))

        assert len(history) == 3

    def test_get_execution(self, temp_dir, sample_tool_state):
        """Test getting a specific execution"""
        tracker = create_tool_tracker(temp_dir)

        execution_id = "exec-123"
        session_id = "session-456"

        asyncio.run(tracker.log_execution(
            execution_id=execution_id,
            session_id=session_id,
            message_id="msg-789",
            tool_id="test-tool",
            state=sample_tool_state,
        ))

        execution = asyncio.run(tracker.get_execution(execution_id))

        assert execution is not None
        assert execution["id"] == execution_id
        assert execution["session_id"] == session_id

    def test_update_execution(self, temp_dir, sample_tool_state):
        """Test updating an execution record"""
        tracker = create_tool_tracker(temp_dir)

        execution_id = "exec-123"
        session_id = "session-456"

        initial_state = ToolState(status="pending", input={"param": "value"})
        asyncio.run(tracker.log_execution(
            execution_id=execution_id,
            session_id=session_id,
            message_id="msg-789",
            tool_id="test-tool",
            state=initial_state,
        ))

        updated_state = ToolState(
            status="completed",
            input={"param": "value"},
            output="result",
        )
        asyncio.run(tracker.update_execution(
            execution_id=execution_id,
            state=updated_state,
            end_time=2000.0,
        ))

        execution = asyncio.run(tracker.get_execution(execution_id))
        assert execution["state"]["status"] == "completed"
        assert execution["state"]["output"] == "result"
        assert execution["end_time"] == 2000.0

    def test_update_execution_not_found(self, temp_dir):
        """Test updating non-existent execution returns None"""
        tracker = create_tool_tracker(temp_dir)

        updated_state = ToolState(status="completed", input={}, output="result")
        result = asyncio.run(tracker.update_execution(
            execution_id="non-existent",
            state=updated_state,
        ))

        assert result is None


class TestSessionLifecycle:
    """Tests for SessionLifecycle"""

    def test_create_lifecycle(self):
        """Test creating a session lifecycle"""
        lifecycle = create_session_lifecycle()

        assert lifecycle is not None
        assert len(lifecycle._on_session_created) == 0
        assert len(lifecycle._listeners) == 0

    def test_register_callback(self):
        """Test registering lifecycle callbacks"""
        lifecycle = SessionLifecycle()

        callback = Mock()

        lifecycle.on_session_created(callback)

        assert len(lifecycle._on_session_created) == 1
        assert callback in lifecycle._on_session_created

    def test_unregister_callback(self):
        """Test unregistering lifecycle callbacks"""
        lifecycle = SessionLifecycle()

        callback = Mock()
        lifecycle.on_session_created(callback)
        lifecycle.unregister_session_created(callback)

        assert len(lifecycle._on_session_created) == 0
        assert callback not in lifecycle._on_session_created

    def test_register_listener(self):
        """Test registering protocol-based listeners"""
        lifecycle = SessionLifecycle()

        listener = Mock(spec=SessionLifecycleListener)

        asyncio.run(lifecycle.register_listener(listener))

        assert len(lifecycle._listeners) == 1
        assert listener in lifecycle._listeners

    def test_unregister_listener(self):
        """Test unregistering protocol-based listeners"""
        lifecycle = SessionLifecycle()

        listener = Mock(spec=SessionLifecycleListener)
        asyncio.run(lifecycle.register_listener(listener))
        asyncio.run(lifecycle.unregister_listener(listener))

        assert len(lifecycle._listeners) == 0
        assert listener not in lifecycle._listeners

    @pytest.mark.asyncio
    async def test_emit_session_created(self, sample_session):
        """Test emitting session created event"""
        lifecycle = SessionLifecycle()

        callback = Mock()
        lifecycle.on_session_created(callback)

        event_data = sample_session.model_dump()
        await lifecycle.emit_session_created(event_data)

        callback.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_emit_session_updated(self, sample_session):
        """Test emitting session updated event"""
        lifecycle = SessionLifecycle()

        callback = Mock()
        lifecycle.on_session_updated(callback)

        event_data = sample_session.model_dump()
        await lifecycle.emit_session_updated(event_data)

        callback.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_emit_message_added(self, sample_session, sample_message):
        """Test emitting message added event"""
        lifecycle = SessionLifecycle()

        callback = Mock()
        lifecycle.on_message_added(callback)

        event_data = sample_message.model_dump()
        await lifecycle.emit_message_added(event_data)

        callback.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_emit_message_updated(self, sample_session, sample_message):
        """Test emitting message updated event"""
        lifecycle = SessionLifecycle()

        callback = Mock()
        lifecycle.on_message_updated(callback)

        event_data = sample_message.model_dump()
        await lifecycle.emit_message_updated(event_data)

        callback.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_emit_session_archived(self, sample_session):
        """Test emitting session archived event"""
        lifecycle = SessionLifecycle()

        callback = Mock()
        lifecycle.on_session_archived(callback)

        event_data = sample_session.model_dump()
        await lifecycle.emit_session_archived(event_data)

        callback.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_emit_session_compacted(self, sample_session):
        """Test emitting session compacted event"""
        lifecycle = SessionLifecycle()

        callback = Mock()
        lifecycle.on_session_compacted(callback)

        event_data = sample_session.model_dump()
        await lifecycle.emit_session_compacted(event_data)

        callback.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_emit_session_deleted(self):
        """Test emitting session deleted event"""
        lifecycle = SessionLifecycle()

        callback = Mock()
        lifecycle.on_session_deleted(callback)

        session_id = "deleted-session-id"
        await lifecycle.emit_session_deleted(session_id)

        callback.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_listener_protocol_session_created(self, sample_session):
        """Test listener receives session created event"""
        lifecycle = SessionLifecycle()

        listener = Mock(spec=SessionLifecycleListener)
        listener.on_session_created = AsyncMock()

        await lifecycle.register_listener(listener)
        await lifecycle.emit_session_created(sample_session.model_dump())

        listener.on_session_created.assert_called_once_with(sample_session)

    @pytest.mark.asyncio
    async def test_listener_protocol_message_added(self, sample_session, sample_message):
        """Test listener receives message added event"""
        lifecycle = SessionLifecycle()

        listener = Mock(spec=SessionLifecycleListener)
        listener.on_message_added = AsyncMock()

        message_data = sample_message.model_dump()
        await lifecycle.register_listener(listener)
        await lifecycle.emit_message_added(message_data)

        listener.on_message_added.assert_called_once()
        args = listener.on_message_added.call_args[0]
        assert args[0].id == sample_session.id

    @pytest.mark.asyncio
    async def test_listener_error_handling(self):
        """Test errors in listeners don't break emission"""
        lifecycle = SessionLifecycle()

        listener = Mock(spec=SessionLifecycleListener)
        listener.on_session_created = AsyncMock(side_effect=Exception("Test error"))

        await lifecycle.register_listener(listener)
        await lifecycle.emit_session_created({})

        listener.on_session_created.assert_called_once()
        assert listener.on_session_created.call_count == 1

    @pytest.mark.asyncio
    async def test_clear_callbacks(self):
        """Test clearing all callbacks"""
        lifecycle = SessionLifecycle()

        lifecycle.on_session_created(Mock())
        lifecycle.on_session_updated(Mock())
        lifecycle.on_message_added(Mock())

        assert len(lifecycle._on_session_created) == 1
        assert len(lifecycle._on_session_updated) == 1
        assert len(lifecycle._on_message_added) == 1

        lifecycle.clear()

        assert len(lifecycle._on_session_created) == 0
        assert len(lifecycle._on_session_updated) == 0
        assert len(lifecycle._on_message_added) == 0

    @pytest.mark.asyncio
    async def test_event_bus_integration_session_created(self, sample_session):
        """Test session lifecycle events are published to event bus"""
        lifecycle = SessionLifecycle()

        with patch.object(bus, "publish", new_callable=AsyncMock()) as mock_publish:
            await lifecycle.emit_session_created(sample_session.model_dump())

            mock_publish.assert_called_once_with(
                Events.SESSION_CREATED,
                {"session": sample_session.model_dump()}
            )

    @pytest.mark.asyncio
    async def test_event_bus_integration_message_added(self, sample_message):
        """Test message lifecycle events are published to event bus"""
        lifecycle = SessionLifecycle()

        with patch.object(bus, "publish", new_callable=AsyncMock()) as mock_publish:
            await lifecycle.emit_message_added(sample_message.model_dump())

            mock_publish.assert_called_once_with(
                Events.MESSAGE_CREATED,
                {"message": sample_message.model_dump()}
            )

    @pytest.mark.asyncio
    async def test_event_bus_integration_session_deleted(self):
        """Test session deleted event is published to event bus"""
        lifecycle = SessionLifecycle()

        session_id = "test-session-id"
        with patch.object(bus, "publish", new_callable=AsyncMock()) as mock_publish:
            await lifecycle.emit_session_deleted(session_id)

            mock_publish.assert_called_once_with(
                Events.SESSION_DELETED,
                {"session_id": session_id}
            )


class TestSessionLifecycleListener:
    """Tests for SessionLifecycleListener protocol"""

    @pytest.mark.asyncio
    async def test_listener_all_methods(self):
        """Test listener implements all required methods"""
        listener = SessionLifecycleListener()

        await listener.on_session_created(Mock())
        await listener.on_session_updated(Mock())
        await listener.on_message_added(Mock(), Mock())
        await listener.on_message_updated(Mock(), Mock())
        await listener.on_session_archived(Mock())
        await listener.on_session_compacted(Mock())
        await listener.on_session_deleted("session-id")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
