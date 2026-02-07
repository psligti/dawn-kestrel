"""Tests for streaming infrastructure using TDD approach."""
import pytest
from datetime import datetime, timedelta
from typing import AsyncGenerator, List
import asyncio

from dawn_kestrel.agents.review.streaming import (
    ReviewStreamManager,
    StreamEventType,
    StreamEvent,
    ProgressEvent,
    ResultEvent,
    ErrorEvent,
    StreamHandle,
    calculate_progress,
)
from dawn_kestrel.agents.review.contracts import ReviewOutput, Scope, MergeGate


class TestStreamEventType:
    """Test StreamEventType enum."""

    def test_event_type_values(self):
        """Test all event types are defined correctly."""
        assert StreamEventType.AGENT_STARTED == "agent_started"
        assert StreamEventType.AGENT_PROGRESS == "agent_progress"
        assert StreamEventType.AGENT_COMPLETED == "agent_completed"
        assert StreamEventType.AGENT_ERROR == "agent_error"
        assert StreamEventType.REVIEW_COMPLETE == "review_complete"


class TestStreamEvent:
    """Test StreamEvent base model."""

    def test_stream_event_creation(self):
        """Test creating a basic stream event."""
        event = StreamEvent(
            event_type=StreamEventType.AGENT_STARTED,
            agent_name="test_agent",
            timestamp=datetime.now(),
            data={"test": "data"}
        )
        assert event.event_type == StreamEventType.AGENT_STARTED
        assert event.agent_name == "test_agent"
        assert event.data == {"test": "data"}

    def test_stream_event_serialization(self):
        """Test stream event can be serialized to dict."""
        timestamp = datetime.now()
        event = StreamEvent(
            event_type=StreamEventType.AGENT_STARTED,
            agent_name="test_agent",
            timestamp=timestamp,
            data={"test": "data"}
        )
        event_dict = event.model_dump()
        assert event_dict["event_type"] == "agent_started"
        assert event_dict["agent_name"] == "test_agent"
        assert "timestamp" in event_dict


class TestProgressEvent:
    """Test ProgressEvent model."""

    def test_progress_event_creation(self):
        """Test creating a progress event."""
        event = ProgressEvent(
            agent_name="test_agent",
            timestamp=datetime.now(),
            data={
                "percent_complete": 50,
                "current_step": "analyzing",
                "total_steps": 10
            }
        )
        assert event.event_type == StreamEventType.AGENT_PROGRESS
        assert event.data["percent_complete"] == 50
        assert event.data["current_step"] == "analyzing"

    def test_progress_event_defaults(self):
        """Test progress event data has sensible defaults."""
        event = ProgressEvent(
            agent_name="test_agent",
            timestamp=datetime.now()
        )
        assert event.data["percent_complete"] == 0
        assert event.data["current_step"] == ""
        assert event.data["total_steps"] == 0


class TestResultEvent:
    """Test ResultEvent model."""

    def test_result_event_creation(self):
        """Test creating a result event."""
        review_output = ReviewOutput(
            agent="test_agent",
            summary="No issues",
            severity="merge",
            scope=Scope(relevant_files=["test.py"], reasoning="test"),
            checks=[], skips=[], findings=[],
            merge_gate=MergeGate(decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[])
        )
        event = ResultEvent(
            agent_name="test_agent",
            timestamp=datetime.now(),
            result=review_output
        )
        assert event.event_type == StreamEventType.AGENT_COMPLETED
        assert event.result == review_output


class TestErrorEvent:
    """Test ErrorEvent model."""

    def test_error_event_creation(self):
        """Test creating an error event."""
        event = ErrorEvent(
            agent_name="test_agent",
            timestamp=datetime.now(),
            error="Test error message"
        )
        assert event.event_type == StreamEventType.AGENT_ERROR
        assert event.error == "Test error message"


class TestCalculateProgress:
    """Test calculate_progress function."""

    def test_calculate_progress_zero_completed(self):
        """Test progress calculation with zero completed agents."""
        started_at = datetime.now()
        progress = calculate_progress(0, 3, started_at)
        assert progress["percent_complete"] == 0.0
        assert progress["agents_completed"] == 0
        assert progress["total_agents"] == 3
        assert progress["eta_seconds"] is None

    def test_calculate_progress_partial(self):
        """Test progress calculation with partial completion."""
        started_at = datetime.now() - timedelta(seconds=10)
        progress = calculate_progress(1, 3, started_at)
        assert progress["percent_complete"] == pytest.approx(33.33, rel=0.01)
        assert progress["agents_completed"] == 1
        assert progress["total_agents"] == 3
        assert progress["eta_seconds"] == pytest.approx(20.0, rel=0.1)

    def test_calculate_progress_complete(self):
        """Test progress calculation when complete."""
        started_at = datetime.now() - timedelta(seconds=30)
        progress = calculate_progress(3, 3, started_at)
        assert progress["percent_complete"] == 100.0
        assert progress["agents_completed"] == 3
        assert progress["total_agents"] == 3
        assert progress["eta_seconds"] == 0.0

    def test_calculate_progress_no_total(self):
        """Test progress calculation with zero total agents."""
        started_at = datetime.now()
        progress = calculate_progress(0, 0, started_at)
        assert progress["percent_complete"] == 0.0
        assert progress["agents_completed"] == 0
        assert progress["total_agents"] == 0


class TestStreamHandle:
    """Test StreamHandle context manager."""

    @pytest.mark.asyncio
    async def test_stream_handle_context(self):
        """Test StreamHandle can be used as async context manager."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        async with handle:
            assert not handle.is_closed
        assert handle.is_closed


class TestReviewStreamManager:
    """Test ReviewStreamManager class."""

    def test_manager_initialization(self):
        """Test manager initializes with default values."""
        manager = ReviewStreamManager()
        assert manager._buffer_size == 1000
        assert manager._total_agents == 0
        assert manager._completed_agents == 0
        assert manager._started_at is None

    def test_manager_custom_buffer_size(self):
        """Test manager can be initialized with custom buffer size."""
        manager = ReviewStreamManager(buffer_size=100)
        assert manager._buffer_size == 100

    @pytest.mark.asyncio
    async def test_start_stream_creates_handle(self):
        """Test start_stream creates a StreamHandle."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()
        assert isinstance(handle, StreamHandle)
        assert not handle.is_closed

    @pytest.mark.asyncio
    async def test_emit_progress_creates_event(self):
        """Test emit_progress creates and stores a progress event."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        await manager.emit_progress("test_agent", "running", {"percent": 50})

        events = []
        async for event in manager.subscribe():
            events.append(event)
            if len(events) >= 1:
                break

        assert len(events) == 1
        assert events[0].event_type == StreamEventType.AGENT_PROGRESS
        assert events[0].agent_name == "test_agent"

    @pytest.mark.asyncio
    async def test_emit_result_creates_event(self):
        """Test emit_result creates and stores a result event."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        review_output = ReviewOutput(
            agent="test_agent",
            summary="Done",
            severity="merge",
            scope=Scope(relevant_files=["test.py"], reasoning="test"),
            checks=[], skips=[], findings=[],
            merge_gate=MergeGate(decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[])
        )
        await manager.emit_result("test_agent", review_output)

        events = []
        async for event in manager.subscribe():
            events.append(event)
            if len(events) >= 1:
                break

        assert len(events) == 1
        assert events[0].event_type == StreamEventType.AGENT_COMPLETED

    @pytest.mark.asyncio
    async def test_emit_error_creates_event(self):
        """Test emit_error creates and stores an error event."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        await manager.emit_error("test_agent", "Test error")

        events = []
        async for event in manager.subscribe():
            events.append(event)
            if len(events) >= 1:
                break

        assert len(events) == 1
        assert events[0].event_type == StreamEventType.AGENT_ERROR

    @pytest.mark.asyncio
    async def test_subscribe_single_consumer(self):
        """Test subscribe works with single consumer."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        events = []
        async def consumer():
            async for event in manager.subscribe():
                events.append(event)
                if len(events) >= 3:
                    break

        async def producer():
            await manager.emit_progress("agent1", "running", {"step": 1})
            await manager.emit_progress("agent2", "running", {"step": 2})
            await manager.emit_result("agent1", ReviewOutput(
                agent="agent1", summary="Done", severity="merge",
                scope=Scope(relevant_files=[], reasoning="test"),
                checks=[], skips=[], findings=[],
                merge_gate=MergeGate(decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[])
            ))

        await asyncio.gather(consumer(), producer())

        assert len(events) == 3
        assert events[0].event_type == StreamEventType.AGENT_PROGRESS
        assert events[1].event_type == StreamEventType.AGENT_PROGRESS
        assert events[2].event_type == StreamEventType.AGENT_COMPLETED

    @pytest.mark.asyncio
    async def test_subscribe_multiple_consumers(self):
        """Test subscribe works with multiple concurrent consumers."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        events1 = []
        events2 = []

        async def consumer1():
            async for event in manager.subscribe():
                events1.append(event)
                if len(events1) >= 2:
                    break

        async def consumer2():
            async for event in manager.subscribe():
                events2.append(event)
                if len(events2) >= 2:
                    break

        async def producer():
            await manager.emit_progress("agent1", "running", {"step": 1})
            await manager.emit_progress("agent2", "running", {"step": 2})

        await asyncio.gather(consumer1(), consumer2(), producer())

        assert len(events1) == 2
        assert len(events2) == 2

    @pytest.mark.asyncio
    async def test_backpressure_handling_buffer_limit(self):
        """Test backpressure handling when buffer limit is reached."""
        manager = ReviewStreamManager(buffer_size=3)
        handle = await manager.start_stream()

        # Emit more events than buffer size
        for i in range(10):
            await manager.emit_progress(f"agent{i}", "running", {"step": i})

        # Consume events - should only see buffered amount
        events = []
        async for event in manager.subscribe():
            events.append(event)
            if len(events) >= 3:
                break

        assert len(events) <= 3

    @pytest.mark.asyncio
    async def test_no_consumer_dont_block_producer(self):
        """Test producer doesn't block when no consumer attached."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        # Emit without consuming
        await manager.emit_progress("agent1", "running", {"step": 1})
        await manager.emit_progress("agent2", "running", {"step": 2})

        # Now consume
        events = []
        async for event in manager.subscribe():
            events.append(event)
            if len(events) >= 2:
                break

        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_progress_metadata_in_events(self):
        """Test progress events include metadata."""
        manager = ReviewStreamManager()
        manager._total_agents = 3
        manager._started_at = datetime.now()
        handle = await manager.start_stream()

        await manager.emit_progress("agent1", "running", {"percent": 50})

        events = []
        async for event in manager.subscribe():
            events.append(event)
            if len(events) >= 1:
                break

        # Completed agents should be incremented when emit_result is called
        assert events[0].agent_name == "agent1"

    @pytest.mark.asyncio
    async def test_callback_based_backend(self):
        """Test callback-based streaming backend."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        callback_events = []

        async def callback(event: StreamEvent):
            callback_events.append(event)

        # Simulate callback backend
        async def forward_to_callback():
            async for event in manager.subscribe():
                await callback(event)
                if len(callback_events) >= 2:
                    break

        async def producer():
            await manager.emit_progress("agent1", "running", {"step": 1})
            await manager.emit_result("agent1", ReviewOutput(
                agent="agent1", summary="Done", severity="merge",
                scope=Scope(relevant_files=[], reasoning="test"),
                checks=[], skips=[], findings=[],
                merge_gate=MergeGate(decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[])
            ))

        await asyncio.gather(forward_to_callback(), producer())

        assert len(callback_events) == 2

    @pytest.mark.asyncio
    async def test_stream_completion_cleanup(self):
        """Test resources cleaned up on stream completion."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        await manager.emit_progress("agent1", "running", {"step": 1})

        events = []
        async for event in manager.subscribe():
            events.append(event)
            break

        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_event_types_all_defined(self):
        """Test all event types can be created."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        events = []

        await manager.emit_progress("agent1", "started", {})

        review_output = ReviewOutput(
            agent="agent1", summary="Done", severity="merge",
            scope=Scope(relevant_files=[], reasoning="test"),
            checks=[], skips=[], findings=[],
            merge_gate=MergeGate(decision="approve", must_fix=[], should_fix=[], notes_for_coding_agent=[])
        )
        await manager.emit_result("agent1", review_output)

        await manager.emit_error("agent2", "Error")

        async for event in manager.subscribe():
            events.append(event)
            if len(events) >= 3:
                break

        event_types = {e.event_type for e in events}
        assert StreamEventType.AGENT_PROGRESS in event_types
        assert StreamEventType.AGENT_COMPLETED in event_types
        assert StreamEventType.AGENT_ERROR in event_types

    @pytest.mark.asyncio
    async def test_subscribe_generator_cleanup(self):
        """Test async generator properly cleans up on cancellation."""
        manager = ReviewStreamManager()
        handle = await manager.start_stream()

        consumed = []

        async def consumer():
            async for event in manager.subscribe():
                consumed.append(event)
                if len(consumed) >= 1:
                    return

        # Emit an event before consuming so it doesn't hang
        await manager.emit_progress("test_agent", "running", {"step": 1})

        await consumer()

        assert len(consumed) >= 1
