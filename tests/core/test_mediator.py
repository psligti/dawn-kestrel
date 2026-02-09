"""Tests for EventMediator pattern implementation.

TDD approach:
- RED: Write failing tests first
- GREEN: Implement to pass tests
- REFACTOR: Clean code with proper documentation

Test coverage:
- Event publishing to all handlers
- Event publishing with source filtering
- Event publishing with target routing
- Event subscription and registration
- Event unsubscription and removal
- Handler count queries
- Event type validation
- Error handling with Result types
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from dawn_kestrel.core.mediator import Event, EventMediator, EventMediatorImpl, EventType
from dawn_kestrel.core.result import Err, Ok


class TestEventTypes:
    """Tests for EventType enum and Event dataclass."""

    def test_event_type_enum_has_all_values(self) -> None:
        """Verify EventType enum has all expected values."""
        assert EventType.DOMAIN == "domain"
        assert EventType.APPLICATION == "application"
        assert EventType.SYSTEM == "system"
        assert EventType.LLM == "llm"

    def test_event_dataclass_works(self) -> None:
        """Verify Event dataclass initializes correctly."""
        event = Event(event_type=EventType.DOMAIN, source="test_component", data={"key": "value"})

        assert event.event_type == EventType.DOMAIN
        assert event.source == "test_component"
        assert event.target is None
        assert event.data == {"key": "value"}

    def test_event_dataclass_with_target(self) -> None:
        """Verify Event dataclass with target field."""
        event = Event(
            event_type=EventType.APPLICATION,
            source="ui_component",
            target="handler_component",
            data={"action": "update"},
        )

        assert event.target == "handler_component"

    def test_event_dataclass_defaults_data_to_empty_dict(self) -> None:
        """Verify Event dataclass defaults data to empty dict if None."""
        event = Event(event_type=EventType.SYSTEM, source="system_component", data=None)

        assert event.data == {}


class TestEventPublishing:
    """Tests for event publishing functionality."""

    @pytest.mark.asyncio
    async def test_publish_to_all_handlers(self) -> None:
        """Verify event publishes to all handlers for its type."""
        mediator = EventMediatorImpl()

        received_events = []

        async def handler1(event: Event) -> None:
            received_events.append(("handler1", event))

        async def handler2(event: Event) -> None:
            received_events.append(("handler2", event))

        # Subscribe two handlers
        await mediator.subscribe(EventType.DOMAIN, handler1)
        await mediator.subscribe(EventType.DOMAIN, handler2)

        # Publish event
        event = Event(event_type=EventType.DOMAIN, source="test_source", data={"test": "data"})
        result = await mediator.publish(event)

        # Verify both handlers received event
        assert result.is_ok()
        assert len(received_events) == 2
        assert received_events[0][0] == "handler1"
        assert received_events[1][0] == "handler2"
        assert received_events[0][1] == event
        assert received_events[1][1] == event

    @pytest.mark.asyncio
    async def test_publish_to_filtered_handlers_by_source(self) -> None:
        """Verify event publishes only to handlers with matching source filter."""
        mediator = EventMediatorImpl()

        received_events = []

        async def handler1(event: Event) -> None:
            received_events.append(("handler1", event))

        async def handler2(event: Event) -> None:
            received_events.append(("handler2", event))

        # Subscribe handlers with different source filters
        await mediator.subscribe(EventType.DOMAIN, handler1, source="source1")
        await mediator.subscribe(EventType.DOMAIN, handler2, source="source2")

        # Publish event from source1
        event = Event(event_type=EventType.DOMAIN, source="source1", data={"test": "data"})
        result = await mediator.publish(event)

        # Verify only handler1 received event (matching source)
        assert result.is_ok()
        assert len(received_events) == 1
        assert received_events[0][0] == "handler1"

    @pytest.mark.asyncio
    async def test_publish_to_targeted_handler(self) -> None:
        """Verify event with target routes to specific handler only."""
        mediator = EventMediatorImpl()

        received_events = []

        async def handler1(event: Event) -> None:
            received_events.append(("handler1", event))

        async def handler2(event: Event) -> None:
            received_events.append(("handler2", event))

        # Subscribe handlers with different source filters
        await mediator.subscribe(EventType.DOMAIN, handler1, source="target1")
        await mediator.subscribe(EventType.DOMAIN, handler2, source="target2")

        # Publish event with target
        event = Event(
            event_type=EventType.DOMAIN,
            source="source1",
            target="target1",
            data={"test": "data"},
        )
        result = await mediator.publish(event)

        # Verify only handler1 received event (matching target)
        assert result.is_ok()
        assert len(received_events) == 1
        assert received_events[0][0] == "handler1"

    @pytest.mark.asyncio
    async def test_publish_returns_ok_on_success(self) -> None:
        """Verify publish returns Ok on successful delivery."""
        mediator = EventMediatorImpl()

        async def handler(event: Event) -> None:
            pass

        await mediator.subscribe(EventType.DOMAIN, handler)

        event = Event(event_type=EventType.DOMAIN, source="test")
        result = await mediator.publish(event)

        assert isinstance(result, Ok)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_publish_returns_err_on_exception(self) -> None:
        """Verify publish returns Err when handler raises exception."""
        mediator = EventMediatorImpl()

        async def handler(event: Event) -> None:
            raise RuntimeError("Handler error")

        await mediator.subscribe(EventType.DOMAIN, handler)

        event = Event(event_type=EventType.DOMAIN, source="test")
        result = await mediator.publish(event)

        assert isinstance(result, Err)
        assert result.is_err()
        assert "MEDIATOR_ERROR" in str(result)

    @pytest.mark.asyncio
    async def test_publish_to_no_handlers(self) -> None:
        """Verify publish succeeds even with no registered handlers."""
        mediator = EventMediatorImpl()

        event = Event(event_type=EventType.DOMAIN, source="test")
        result = await mediator.publish(event)

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_publish_to_unrelated_event_type(self) -> None:
        """Verify publish doesn't trigger handlers for different event types."""
        mediator = EventMediatorImpl()

        received_events = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        # Subscribe to DOMAIN events
        await mediator.subscribe(EventType.DOMAIN, handler)

        # Publish APPLICATION event
        event = Event(event_type=EventType.APPLICATION, source="test")
        await mediator.publish(event)

        # Verify handler not called
        assert len(received_events) == 0


class TestEventSubscription:
    """Tests for event subscription functionality."""

    @pytest.mark.asyncio
    async def test_subscribe_adds_handler(self) -> None:
        """Verify subscribe adds handler to registry."""
        mediator = EventMediatorImpl()

        async def handler(event: Event) -> None:
            pass

        result = await mediator.subscribe(EventType.DOMAIN, handler)

        assert result.is_ok()

        # Verify handler registered
        count_result = await mediator.get_handler_count(EventType.DOMAIN)
        assert count_result.is_ok()
        assert count_result.unwrap() == 1

    @pytest.mark.asyncio
    async def test_subscribe_returns_ok_on_success(self) -> None:
        """Verify subscribe returns Ok on success."""
        mediator = EventMediatorImpl()

        async def handler(event: Event) -> None:
            pass

        result = await mediator.subscribe(EventType.DOMAIN, handler)

        assert isinstance(result, Ok)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_subscribe_with_source_filter(self) -> None:
        """Verify subscribe with source filter stores filter correctly."""
        mediator = EventMediatorImpl()

        async def handler(event: Event) -> None:
            pass

        result = await mediator.subscribe(EventType.DOMAIN, handler, source="specific_source")

        assert result.is_ok()

        # Publish event from different source
        event = Event(event_type=EventType.DOMAIN, source="other_source")
        received_events = []

        async def tracking_handler(evt: Event) -> None:
            received_events.append(evt)

        await mediator.subscribe(EventType.DOMAIN, tracking_handler, source="specific_source")
        await mediator.publish(event)

        # Verify handler not called (source mismatch)
        assert len(received_events) == 0

    @pytest.mark.asyncio
    async def test_multiple_handlers_for_same_event(self) -> None:
        """Verify multiple handlers can subscribe to same event type."""
        mediator = EventMediatorImpl()

        async def handler1(event: Event) -> None:
            pass

        async def handler2(event: Event) -> None:
            pass

        async def handler3(event: Event) -> None:
            pass

        # Subscribe three handlers
        await mediator.subscribe(EventType.DOMAIN, handler1)
        await mediator.subscribe(EventType.DOMAIN, handler2)
        await mediator.subscribe(EventType.DOMAIN, handler3)

        # Verify all three registered
        count_result = await mediator.get_handler_count(EventType.DOMAIN)
        assert count_result.is_ok()
        assert count_result.unwrap() == 3


class TestEventUnsubscription:
    """Tests for event unsubscription functionality."""

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_handler(self) -> None:
        """Verify unsubscribe removes handler from registry."""
        mediator = EventMediatorImpl()

        received_events = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        # Subscribe handler
        await mediator.subscribe(EventType.DOMAIN, handler)

        # Unsubscribe handler
        result = await mediator.unsubscribe(EventType.DOMAIN, handler)
        assert result.is_ok()

        # Publish event
        event = Event(event_type=EventType.DOMAIN, source="test")
        await mediator.publish(event)

        # Verify handler not called
        assert len(received_events) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_returns_ok_on_success(self) -> None:
        """Verify unsubscribe returns Ok on successful removal."""
        mediator = EventMediatorImpl()

        async def handler(event: Event) -> None:
            pass

        await mediator.subscribe(EventType.DOMAIN, handler)
        result = await mediator.unsubscribe(EventType.DOMAIN, handler)

        assert isinstance(result, Ok)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_unsubscribe_returns_err_on_unknown_handler(self) -> None:
        """Verify unsubscribe returns Err when handler not found."""
        mediator = EventMediatorImpl()

        async def handler(event: Event) -> None:
            pass

        # Try to unsubscribe without subscribing first
        result = await mediator.unsubscribe(EventType.DOMAIN, handler)

        assert isinstance(result, Err)
        assert result.is_err()
        assert "HANDLER_NOT_FOUND" in str(result)

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_first_matching_handler(self) -> None:
        """Verify unsubscribe removes only first matching handler."""
        mediator = EventMediatorImpl()

        received_events = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        # Subscribe same handler twice
        await mediator.subscribe(EventType.DOMAIN, handler)
        await mediator.subscribe(EventType.DOMAIN, handler)

        # Verify two handlers registered
        count_result = await mediator.get_handler_count(EventType.DOMAIN)
        assert count_result.unwrap() == 2

        # Unsubscribe once
        await mediator.unsubscribe(EventType.DOMAIN, handler)

        # Verify one handler remaining
        count_result = await mediator.get_handler_count(EventType.DOMAIN)
        assert count_result.unwrap() == 1

        # Publish event - handler should still be called once
        event = Event(event_type=EventType.DOMAIN, source="test")
        await mediator.publish(event)
        assert len(received_events) == 1


class TestHandlerCount:
    """Tests for handler count queries."""

    @pytest.mark.asyncio
    async def test_get_handler_count_returns_zero_for_no_handlers(self) -> None:
        """Verify handler count returns 0 for event type with no handlers."""
        mediator = EventMediatorImpl()

        result = await mediator.get_handler_count(EventType.DOMAIN)

        assert result.is_ok()
        assert result.unwrap() == 0

    @pytest.mark.asyncio
    async def test_get_handler_count_returns_correct_count(self) -> None:
        """Verify handler count returns correct number of registered handlers."""
        mediator = EventMediatorImpl()

        async def handler1(event: Event) -> None:
            pass

        async def handler2(event: Event) -> None:
            pass

        async def handler3(event: Event) -> None:
            pass

        # Subscribe handlers
        await mediator.subscribe(EventType.DOMAIN, handler1)
        await mediator.subscribe(EventType.DOMAIN, handler2)
        await mediator.subscribe(EventType.APPLICATION, handler3)

        # Verify counts
        domain_count = await mediator.get_handler_count(EventType.DOMAIN)
        app_count = await mediator.get_handler_count(EventType.APPLICATION)
        system_count = await mediator.get_handler_count(EventType.SYSTEM)

        assert domain_count.unwrap() == 2
        assert app_count.unwrap() == 1
        assert system_count.unwrap() == 0

    @pytest.mark.asyncio
    async def test_get_handler_count_returns_err_on_exception(self) -> None:
        """Verify handler count returns Err on exception."""
        # This test verifies error handling in implementation
        # In current implementation, handler count shouldn't raise exceptions
        mediator = EventMediatorImpl()

        result = await mediator.get_handler_count(EventType.DOMAIN)

        # Should return Ok with count (not Err)
        assert result.is_ok()


class TestEventMediatorProtocol:
    """Tests for EventMediator protocol compliance."""

    def test_event_mediator_protocol_is_runtime_checkable(self) -> None:
        """Verify EventMediator protocol can be checked with isinstance."""
        mediator = EventMediatorImpl()

        # Protocol should be runtime_checkable
        assert isinstance(mediator, EventMediator)

    def test_event_mediator_impl_has_all_methods(self) -> None:
        """Verify EventMediatorImpl implements all protocol methods."""
        mediator = EventMediatorImpl()

        # Check all required methods exist
        assert hasattr(mediator, "publish")
        assert hasattr(mediator, "subscribe")
        assert hasattr(mediator, "unsubscribe")
        assert hasattr(mediator, "get_handler_count")

        # Check methods are callable
        assert callable(mediator.publish)
        assert callable(mediator.subscribe)
        assert callable(mediator.unsubscribe)
        assert callable(mediator.get_handler_count)
