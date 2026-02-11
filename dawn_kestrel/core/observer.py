"""Observer pattern for change notification.

This module implements the Observer pattern to enable one-to-many notification
when objects change state. Observers subscribe to observables to receive updates
when the observable's state changes.

Key concepts:
- Observer: Protocol for objects that receive notifications
- Observable: Protocol for objects that maintain observer lists and notify them
- ObservableImpl: In-memory implementation with observer management
- StateChangeObserver: Concrete observer that tracks state changes
- MetricsObserver: Concrete observer that aggregates metrics
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable, Optional

from dawn_kestrel.core.mediator import Event, EventMediator, EventType


@runtime_checkable
class Observer(Protocol):
    """Protocol for observer.

    Observers receive notifications from observables when state changes occur.
    """

    async def on_notify(
        self,
        observable: Any,
        event: dict[str, Any],
    ) -> None:
        """Handle notification from observable.

        Args:
            observable: The object that changed.
            event: Event data containing change details.
        """
        ...


@runtime_checkable
class Observable(Protocol):
    """Protocol for observable (subject).

    Observables maintain list of observers and notify them of changes.
    """

    async def register_observer(
        self,
        observer: Observer,
    ) -> None:
        """Register observer for notifications.

        Args:
            observer: Observer to register.
        """
        ...

    async def unregister_observer(
        self,
        observer: Observer,
    ) -> None:
        """Unregister observer from notifications.

        Args:
            observer: Observer to remove.
        """
        ...

    async def notify_observers(
        self,
        event: dict[str, Any],
    ) -> None:
        """Notify all observers of change.

        Args:
            event: Event data to broadcast.
        """
        ...


class ObservableImpl:
    """Observable implementation with observer management.

    Maintains a set of observers and notifies them of state changes.
    Optionally publishes observer lifecycle events to an EventMediator.

    Thread safety: NOT thread-safe (documented limitation).
    Suitable for single-process use in async context.

    Args:
        name: Name of the observable (used in event metadata).
        mediator: Optional EventMediator for publishing lifecycle events.
    """

    def __init__(
        self,
        name: str,
        mediator: Optional[EventMediator] = None,
    ) -> None:
        """Initialize observable with empty observer set."""
        self.name = name
        self._mediator = mediator
        self._observers: set[Observer] = set()

    async def register_observer(
        self,
        observer: Observer,
    ) -> None:
        """Register observer for notifications.

        Adds observer to the observer set and publishes
        observer_registered event if mediator is configured.

        Args:
            observer: Observer to register.
        """
        self._observers.add(observer)

        if self._mediator:
            event = Event(
                event_type=EventType.DOMAIN,
                source=self.name,
                data={
                    "action": "observer_registered",
                    "observer_count": len(self._observers),
                },
            )
            await self._mediator.publish(event)

    async def unregister_observer(
        self,
        observer: Observer,
    ) -> None:
        """Unregister observer from notifications.

        Removes observer from the observer set and publishes
        observer_unregistered event if mediator is configured.
        Safe to call even if observer not registered.

        Args:
            observer: Observer to remove.
        """
        if observer in self._observers:
            self._observers.remove(observer)

        if self._mediator:
            event = Event(
                event_type=EventType.DOMAIN,
                source=self.name,
                data={
                    "action": "observer_unregistered",
                    "observer_count": len(self._observers),
                },
            )
            await self._mediator.publish(event)

    async def notify_observers(
        self,
        event: dict[str, Any],
    ) -> None:
        """Notify all observers of change.

        Calls on_notify() on all registered observers.
        Observer exceptions are caught and logged, preventing
        one faulty observer from disrupting notifications to others.

        Args:
            event: Event data to broadcast.
        """
        for observer in self._observers:
            try:
                await observer.on_notify(self, event)
            except Exception as e:
                # Log but don't fail other observers
                print(f"Observer error: {e}")

    @property
    def observer_count(self) -> int:
        """Get current observer count.

        Returns:
            Number of registered observers.
        """
        return len(self._observers)


@dataclass(unsafe_hash=True)
class StateChangeObserver(Observer):
    """Observer for state change notifications.

    Records all notifications received from observables, including
    observable name, event data, and timestamp.

    Args:
        name: Name of the observer.
    """

    name: str
    _notifications: list[dict[str, Any]] = field(default_factory=list, compare=False, hash=False)

    async def on_notify(
        self,
        observable: Any,
        event: dict[str, Any],
    ) -> None:
        """Handle notification from observable.

        Records notification with observer name, observable name,
        event data, and timestamp.

        Args:
            observable: The object that changed.
            event: Event data containing change details.
        """
        notification = {
            "observer": self.name,
            "observable": observable.name if hasattr(observable, "name") else str(type(observable)),
            "event": event,
            "timestamp": event.get("timestamp", ""),
        }
        self._notifications.append(notification)

    def get_notifications(self) -> list[dict[str, Any]]:
        """Get all recorded notifications.

        Returns:
            List of notification dictionaries.
        """
        return self._notifications.copy()

    def clear_notifications(self) -> None:
        """Clear all recorded notifications."""
        self._notifications.clear()


@dataclass(unsafe_hash=True)
class MetricsObserver(Observer):
    """Observer for metrics notifications.

    Aggregates metric counts from events.
    Events should contain 'metric_name' and 'count' fields.

    Args:
        name: Name of the observer.
    """

    name: str
    _metric_counts: dict[str, int] = field(default_factory=dict, compare=False, hash=False)

    async def on_notify(
        self,
        observable: Any,
        event: dict[str, Any],
    ) -> None:
        """Handle notification from observable.

        Extracts metric_name and count from event and aggregates.

        Args:
            observable: The object that changed.
            event: Event data containing metric_name and count.
        """
        metric_name = event.get("metric_name", "unknown")
        count = event.get("count", 0)

        if metric_name in self._metric_counts:
            self._metric_counts[metric_name] += count
        else:
            self._metric_counts[metric_name] = count

    def get_metric_counts(self) -> dict[str, int]:
        """Get aggregated metric counts.

        Returns:
            Dictionary mapping metric names to counts.
        """
        return self._metric_counts.copy()

    def clear_metrics(self) -> None:
        """Clear all metric counts."""
        self._metric_counts.clear()
