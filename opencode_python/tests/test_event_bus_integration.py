"""Tests for event bus integration.

Tests EventBus publish/subscribe mechanism, unsubscribe functionality,
once-subscribe, exception isolation, thread safety, and Events constants.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from opencode_python.core.event_bus import (
    EventBus,
    Event,
    EventSubscription,
    Events,
)


class TestEventBusPublishSubscribe:
    """Tests for EventBus publish and subscribe mechanism."""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self) -> None:
        """Test subscribing to and publishing events."""
        bus = EventBus()
        callback = AsyncMock()

        await bus.subscribe("test.event", callback)
        await bus.publish("test.event", {"key": "value"})

        callback.assert_called_once()
        event_arg = callback.call_args[0][0]
        assert event_arg.name == "test.event"
        assert event_arg.data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_event(self) -> None:
        """Test multiple subscribers to the same event."""
        bus = EventBus()
        callback1 = AsyncMock()
        callback2 = AsyncMock()

        await bus.subscribe("test.event", callback1)
        await bus.subscribe("test.event", callback2)
        await bus.publish("test.event", {"data": "test"})

        callback1.assert_called_once()
        callback2.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_without_data(self) -> None:
        """Test publishing event without data."""
        bus = EventBus()
        callback = AsyncMock()

        await bus.subscribe("test.event", callback)
        await bus.publish("test.event")

        callback.assert_called_once()
        event_arg = callback.call_args[0][0]
        assert event_arg.data == {}

    @pytest.mark.asyncio
    async def test_subscriber_receives_event_with_correct_data(self) -> None:
        """Test that subscriber receives event with correct data."""
        bus = EventBus()
        callback = AsyncMock()

        test_data = {"user_id": 123, "action": "create"}
        await bus.subscribe("user.action", callback)
        await bus.publish("user.action", test_data)

        callback.assert_called_once()
        event_arg = callback.call_args[0][0]
        assert event_arg.name == "user.action"
        assert event_arg.data == test_data


class TestEventBusUnsubscribe:
    """Tests for EventBus unsubscribe functionality."""

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_callback(self) -> None:
        """Test that unsubscribe removes callback from subscribers."""
        bus = EventBus()
        callback = AsyncMock()

        unsubscribe = await bus.subscribe("test.event", callback)
        await bus.publish("test.event", {"data": "first"})

        await unsubscribe()
        await bus.publish("test.event", {"data": "second"})

        assert callback.call_count == 1
        event_arg = callback.call_args[0][0]
        assert event_arg.data == {"data": "first"}

    @pytest.mark.asyncio
    async def test_unsubscribe_multiple_subscribers(self) -> None:
        """Test unsubscribing one of multiple subscribers."""
        bus = EventBus()
        callback1 = AsyncMock()
        callback2 = AsyncMock()

        unsubscribe1 = await bus.subscribe("test.event", callback1)
        await bus.subscribe("test.event", callback2)

        await bus.publish("test.event", {"data": "first"})

        await unsubscribe1()
        await bus.publish("test.event", {"data": "second"})

        assert callback1.call_count == 1
        assert callback2.call_count == 2


class TestEventBusOnceSubscribe:
    """Tests for EventBus once-subscribe (auto-unsubscribe after first event)."""

    @pytest.mark.asyncio
    async def test_once_subscribe_auto_unsubscribes(self) -> None:
        """Test that once=True auto-unsubscribes after first event."""
        bus = EventBus()
        callback = AsyncMock()

        await bus.subscribe("test.event", callback, once=True)
        await bus.publish("test.event", {"data": "first"})
        await bus.publish("test.event", {"data": "second"})

        callback.assert_called_once()
        event_arg = callback.call_args[0][0]
        assert event_arg.data == {"data": "first"}

    @pytest.mark.asyncio
    async def test_normal_subscribe_without_once(self) -> None:
        """Test normal subscribe without once receives all events."""
        bus = EventBus()
        callback = AsyncMock()

        await bus.subscribe("test.event", callback, once=False)
        await bus.publish("test.event", {"data": "first"})
        await bus.publish("test.event", {"data": "second"})

        assert callback.call_count == 2


class TestEventBusExceptionIsolation:
    """Tests for EventBus exception isolation."""

    @pytest.mark.asyncio
    async def test_exception_in_callback_doesnt_break_publish(self) -> None:
        """Test that exceptions in callbacks don't break pub/sub mechanism."""
        bus = EventBus()

        async def failing_callback(event: Event) -> None:
            raise ValueError("Test error")

        working_callback = AsyncMock()

        await bus.subscribe("test.event", failing_callback)
        await bus.subscribe("test.event", working_callback)

        await bus.publish("test.event", {"data": "test"})

        working_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_callbacks_with_exceptions(self) -> None:
        """Test that multiple failing callbacks are isolated."""
        bus = EventBus()

        async def failing_callback1(event: Event) -> None:
            raise ValueError("Error 1")

        async def failing_callback2(event: Event) -> None:
            raise RuntimeError("Error 2")

        await bus.subscribe("test.event", failing_callback1)
        await bus.subscribe("test.event", failing_callback2)

        await bus.publish("test.event", {"data": "test"})


class TestEventBusThreadSafety:
    """Tests for EventBus thread safety with concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_publish_and_subscribe(self) -> None:
        """Test concurrent publish and subscribe operations."""
        bus = EventBus()
        results = []

        async def callback(event: Event) -> None:
            results.append(event.data)

        async def publisher() -> None:
            for i in range(5):
                await bus.publish("test.event", {"value": i})
                await asyncio.sleep(0.01)

        async def subscriber() -> None:
            for _ in range(3):
                callback_mock = AsyncMock(side_effect=callback)
                await bus.subscribe("test.event", callback_mock)
                await asyncio.sleep(0.01)

        await asyncio.gather(publisher(), subscriber())

    @pytest.mark.asyncio
    async def test_concurrent_publish_to_multiple_events(self) -> None:
        """Test concurrent publishes to different events."""
        bus = EventBus()
        callback = AsyncMock()

        await bus.subscribe("event.1", callback)
        await bus.subscribe("event.2", callback)

        async def publish_event1() -> None:
            for i in range(5):
                await bus.publish("event.1", {"value": i})
                await asyncio.sleep(0.01)

        async def publish_event2() -> None:
            for i in range(5):
                await bus.publish("event.2", {"value": i + 100})
                await asyncio.sleep(0.01)

        await asyncio.gather(publish_event1(), publish_event2())


class TestEventsClass:
    """Tests for predefined Events class constants."""

    def test_events_session_created_is_string(self) -> None:
        """Test SESSION_CREATED is a string."""
        assert isinstance(Events.SESSION_CREATED, str)

    def test_events_session_updated_is_string(self) -> None:
        """Test SESSION_UPDATED is a string."""
        assert isinstance(Events.SESSION_UPDATED, str)

    def test_events_message_created_is_string(self) -> None:
        """Test MESSAGE_CREATED is a string."""
        assert isinstance(Events.MESSAGE_CREATED, str)

    def test_events_permission_asked_is_string(self) -> None:
        """Test PERMISSION_ASKED is a string."""
        assert isinstance(Events.PERMISSION_ASKED, str)

    def test_events_tool_started_is_string(self) -> None:
        """Test TOOL_STARTED is a string."""
        assert isinstance(Events.TOOL_STARTED, str)

    def test_events_agent_initialized_is_string(self) -> None:
        """Test AGENT_INITIALIZED is a string."""
        assert isinstance(Events.AGENT_INITIALIZED, str)

    def test_all_event_names_are_dot_separated(self) -> None:
        """Test that all event names use dot notation."""
        events = [
            Events.SESSION_CREATED,
            Events.SESSION_UPDATED,
            Events.MESSAGE_CREATED,
            Events.PERMISSION_GRANTED,
            Events.TOOL_COMPLETED,
        ]
        for event in events:
            assert "." in event
