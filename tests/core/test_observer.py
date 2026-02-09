"""Tests for Observer pattern implementation.

Tests the Observer pattern including:
- Observer and Observable protocols
- ObservableImpl with observer management
- StateChangeObserver and MetricsObserver
- Multiple observers per observable
- Integration with EventMediator
"""

import pytest

from dawn_kestrel.core.mediator import Event, EventMediator, EventType
from dawn_kestrel.core.observer import (
    MetricsObserver,
    Observable,
    ObservableImpl,
    StateChangeObserver,
)


class MockObserver:
    """Mock observer for testing."""

    def __init__(self, name: str):
        self.name = name
        self.notifications: list[tuple] = []

    async def on_notify(self, observable: object, event: dict) -> None:
        """Record notification."""
        self.notifications.append((observable, event))


# Observer Protocol Tests


def test_observer_has_on_notify_method() -> None:
    """Test Observer protocol defines on_notify method."""
    observer = MockObserver("test")
    assert hasattr(observer, "on_notify")
    assert callable(observer.on_notify)


def test_observable_has_register_observer_method() -> None:
    """Test Observable protocol defines register_observer method."""
    observable = ObservableImpl("test")
    assert hasattr(observable, "register_observer")
    assert callable(observable.register_observer)


def test_observable_has_unregister_observer_method() -> None:
    """Test Observable protocol defines unregister_observer method."""
    observable = ObservableImpl("test")
    assert hasattr(observable, "unregister_observer")
    assert callable(observable.unregister_observer)


def test_observable_has_notify_observers_method() -> None:
    """Test Observable protocol defines notify_observers method."""
    observable = ObservableImpl("test")
    assert hasattr(observable, "notify_observers")
    assert callable(observable.notify_observers)


# ObservableImpl Tests


@pytest.mark.asyncio
async def test_observable_initializes_with_no_observers() -> None:
    """Test observable initializes with empty observer set."""
    observable = ObservableImpl("test_observable")
    assert observable.observer_count == 0


@pytest.mark.asyncio
async def test_observable_register_observer_adds_observer() -> None:
    """Test register_observer adds observer to set."""
    observable = ObservableImpl("test_observable")
    observer = MockObserver("test_observer")

    await observable.register_observer(observer)

    assert observable.observer_count == 1


@pytest.mark.asyncio
async def test_observable_register_observer_publishes_event() -> None:
    """Test register_observer publishes event to mediator."""
    mediator = EventMediatorImpl()
    events_published: list[Event] = []

    async def handler(event: Event) -> None:
        events_published.append(event)

    await mediator.subscribe(EventType.DOMAIN, handler)
    observable = ObservableImpl("test_observable", mediator)
    observer = MockObserver("test_observer")

    await observable.register_observer(observer)

    assert len(events_published) == 1
    assert events_published[0].source == "test_observable"
    assert events_published[0].data["action"] == "observer_registered"
    assert events_published[0].data["observer_count"] == 1


@pytest.mark.asyncio
async def test_observable_unregister_observer_removes_observer() -> None:
    """Test unregister_observer removes observer from set."""
    observable = ObservableImpl("test_observable")
    observer = MockObserver("test_observer")

    await observable.register_observer(observer)
    assert observable.observer_count == 1

    await observable.unregister_observer(observer)
    assert observable.observer_count == 0


@pytest.mark.asyncio
async def test_observable_unregister_observer_publishes_event() -> None:
    """Test unregister_observer publishes event to mediator."""
    mediator = EventMediatorImpl()
    events_published: list[Event] = []

    async def handler(event: Event) -> None:
        events_published.append(event)

    await mediator.subscribe(EventType.DOMAIN, handler)
    observable = ObservableImpl("test_observable", mediator)
    observer = MockObserver("test_observer")

    await observable.register_observer(observer)
    await observable.unregister_observer(observer)

    # Should have 2 events: registered and unregistered
    assert len(events_published) == 2
    assert events_published[1].source == "test_observable"
    assert events_published[1].data["action"] == "observer_unregistered"
    assert events_published[1].data["observer_count"] == 0


@pytest.mark.asyncio
async def test_observable_notify_observers_calls_all_observers() -> None:
    """Test notify_observers calls on_notify on all observers."""
    observable = ObservableImpl("test_observable")
    observer1 = MockObserver("observer1")
    observer2 = MockObserver("observer2")
    observer3 = MockObserver("observer3")

    await observable.register_observer(observer1)
    await observable.register_observer(observer2)
    await observable.register_observer(observer3)

    event = {"state": "active", "timestamp": "2026-01-01T00:00:00Z"}
    await observable.notify_observers(event)

    assert len(observer1.notifications) == 1
    assert len(observer2.notifications) == 1
    assert len(observer3.notifications) == 1
    assert observer1.notifications[0][1] == event
    assert observer2.notifications[0][1] == event
    assert observer3.notifications[0][1] == event


@pytest.mark.asyncio
async def test_observable_notify_observers_skips_failed_observer() -> None:
    """Test notify_observers continues even if observer raises exception."""

    class FailingObserver:
        """Observer that always fails."""

        async def on_notify(self, observable: object, event: dict) -> None:
            raise Exception("Observer failed")

    observable = ObservableImpl("test_observable")
    failing_observer = FailingObserver()
    good_observer = MockObserver("good_observer")

    await observable.register_observer(failing_observer)
    await observable.register_observer(good_observer)

    # Should not raise exception
    event = {"state": "active"}
    await observable.notify_observers(event)

    # Good observer should still be called
    assert len(good_observer.notifications) == 1


# StateChangeObserver Tests


@pytest.mark.asyncio
async def test_state_change_observer_records_notifications() -> None:
    """Test StateChangeObserver records all notifications."""
    observable = ObservableImpl("test_observable")
    observer = StateChangeObserver("test_observer")

    await observable.register_observer(observer)

    await observable.notify_observers({"state": "active", "timestamp": "2026-01-01T00:00:00Z"})
    await observable.notify_observers({"state": "paused", "timestamp": "2026-01-01T01:00:00Z"})

    notifications = observer.get_notifications()
    assert len(notifications) == 2
    assert notifications[0]["observer"] == "test_observer"
    assert notifications[0]["observable"] == "test_observable"
    assert notifications[0]["event"]["state"] == "active"
    assert notifications[1]["event"]["state"] == "paused"


@pytest.mark.asyncio
async def test_state_change_observer_on_notify_callable() -> None:
    """Test StateChangeObserver.on_notify is callable."""
    observer = StateChangeObserver("test_observer")
    assert callable(observer.on_notify)

    observable = ObservableImpl("test")
    await observer.on_notify(observable, {"test": "data"})

    assert len(observer.get_notifications()) == 1


# MetricsObserver Tests


@pytest.mark.asyncio
async def test_metrics_observer_counts_metrics() -> None:
    """Test MetricsObserver aggregates metric counts."""
    observable = ObservableImpl("test_observable")
    observer = MetricsObserver("test_observer")

    await observable.register_observer(observer)

    await observable.notify_observers({"metric_name": "requests", "count": 10})
    await observable.notify_observers({"metric_name": "requests", "count": 5})
    await observable.notify_observers({"metric_name": "errors", "count": 2})

    counts = observer.get_metric_counts()
    assert counts["requests"] == 15
    assert counts["errors"] == 2


@pytest.mark.asyncio
async def test_metrics_observer_on_notify_callable() -> None:
    """Test MetricsObserver.on_notify is callable."""
    observer = MetricsObserver("test_observer")
    assert callable(observer.on_notify)

    observable = ObservableImpl("test")
    await observer.on_notify(observable, {"metric_name": "test", "count": 5})

    assert observer.get_metric_counts()["test"] == 5


@pytest.mark.asyncio
async def test_metrics_observer_get_metric_counts() -> None:
    """Test MetricsObserver.get_metric_counts returns copy."""
    observable = ObservableImpl("test_observable")
    observer = MetricsObserver("test_observer")

    await observable.register_observer(observer)
    await observable.notify_observers({"metric_name": "test", "count": 5})

    counts1 = observer.get_metric_counts()
    counts2 = observer.get_metric_counts()

    # Should be equal but different objects
    assert counts1 == counts2
    assert counts1 is not counts2

    # Modifying returned copy should not affect internal state
    counts1["new_metric"] = 999
    assert "new_metric" not in observer.get_metric_counts()


# Integration Tests


@pytest.mark.asyncio
async def test_multiple_observers_per_observable() -> None:
    """Test multiple observers can subscribe to one observable."""
    observable = ObservableImpl("test_observable")
    observer1 = StateChangeObserver("observer1")
    observer2 = StateChangeObserver("observer2")
    observer3 = StateChangeObserver("observer3")

    await observable.register_observer(observer1)
    await observable.register_observer(observer2)
    await observable.register_observer(observer3)

    event = {"state": "active", "timestamp": "2026-01-01T00:00:00Z"}
    await observable.notify_observers(event)

    # All observers should receive notification
    assert len(observer1.get_notifications()) == 1
    assert len(observer2.get_notifications()) == 1
    assert len(observer3.get_notifications()) == 1


@pytest.mark.asyncio
async def test_observable_with_mediator_publishes_events() -> None:
    """Test observable publishes lifecycle events to mediator."""
    mediator = EventMediatorImpl()
    events_published: list[Event] = []

    async def handler(event: Event) -> None:
        events_published.append(event)

    await mediator.subscribe(EventType.DOMAIN, handler)
    observable = ObservableImpl("test_observable", mediator)
    observer = StateChangeObserver("test_observer")

    # Register observer
    await observable.register_observer(observer)
    # Unregister observer
    await observable.unregister_observer(observer)

    # Should have published 2 events
    assert len(events_published) == 2
    assert events_published[0].data["action"] == "observer_registered"
    assert events_published[1].data["action"] == "observer_unregistered"


# Helper class for tests


class EventMediatorImpl:
    """Simple EventMediator implementation for testing."""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list] = {}

    async def publish(self, event: Event) -> None:
        """Publish event to handlers."""
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            await handler(event)

    async def subscribe(
        self, event_type: EventType, handler: object, source: str | None = None
    ) -> None:
        """Subscribe handler to event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def unsubscribe(self, event_type: EventType, handler: object) -> None:
        """Unsubscribe handler from event type."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def get_handler_count(self, event_type: EventType) -> int:
        """Get handler count for event type."""
        return len(self._handlers.get(event_type, []))
