"""Mediator pattern for centralized event coordination.

This module implements the Mediator pattern to centralize event handling
and eliminate component-to-component direct wiring. Components register
event handlers with the mediator, and the mediator publishes events to
all registered handlers, enabling loose coupling.

Key concepts:
- EventType: Categorization of events (domain, application, system, llm)
- Event: Base event class with source, target, and data
- EventMediator protocol: Interface for event coordination
- EventMediatorImpl: In-memory implementation
"""

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Protocol, runtime_checkable, Optional

from dawn_kestrel.core.result import Err, Ok, Result


class EventType(str, Enum):
    """Event type categories.

    Events are categorized into four types:
    - DOMAIN: Business logic events (session created, agent finished)
    - APPLICATION: UI/operational events (progress, notification)
    - SYSTEM: System events (startup, shutdown)
    - LLM: LLM-related events (response received, streaming)
    """

    DOMAIN = "domain"
    APPLICATION = "application"
    SYSTEM = "system"
    LLM = "llm"


@dataclass
class Event:
    """Base event class for all mediator events.

    Events contain:
    - event_type: Type category (domain, application, system, llm)
    - source: Component that emitted the event
    - target: Optional specific recipient (None means broadcast to all)
    - data: Event payload as dictionary
    """

    event_type: EventType
    source: str
    target: Optional[str] = None
    data: Optional[dict] = None

    def __post_init__(self) -> None:
        """Ensure data is initialized as empty dict if None."""
        if self.data is None:
            object.__setattr__(self, "data", {})


@runtime_checkable
class EventMediator(Protocol):
    """Protocol for event mediator.

    Mediator centralizes event handling, eliminating
    component-to-component direct wiring.

    Components register event handlers with subscribe().
    Components publish events with publish().
    Mediator routes events to all matching handlers.
    """

    async def publish(self, event: Event) -> Result[None]:
        """Publish an event to all registered handlers.

        Args:
            event: Event to publish.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        ...

    async def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Awaitable[None]],
        source: Optional[str] = None,
    ) -> Result[None]:
        """Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to.
            handler: Async callable that receives events.
            source: Optional source filter (only events from this source).

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        ...

    async def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Awaitable[None]],
    ) -> Result[None]:
        """Unsubscribe handler from specific event type.

        Args:
            event_type: Type of events to unsubscribe from.
            handler: Handler to remove.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        ...

    async def get_handler_count(self, event_type: EventType) -> Result[int]:
        """Get count of handlers for an event type.

        Args:
            event_type: Type of events to query.

        Returns:
            Result[int]: Count of registered handlers.
        """
        ...


class EventMediatorImpl:
    """Event mediator implementation for centralized event coordination.

    Mediator maintains in-memory mapping of event types to handlers.
    Handlers are stored with optional source filters for selective routing.
    When an event is published, all matching handlers receive the event.

    Thread safety: NOT thread-safe (documented limitation).
    Suitable for single-process use in async context.
    """

    def __init__(self) -> None:
        """Initialize mediator with empty handler registry.

        Internal structure:
        _handlers: dict[event_type, list[tuple[handler, source_filter]]]
        - event_type: EventType enum value
        - handler: Async callable that receives Event
        - source_filter: Optional source string (None means all sources)
        """
        # Map: event_type -> list[(handler, source_filter)]
        self._handlers: dict[
            EventType, list[tuple[Callable[[Event], Awaitable[None]], Optional[str]]]
        ] = defaultdict(list)

    async def publish(self, event: Event) -> Result[None]:
        """Publish an event to all registered handlers.

        Routing logic:
        - If event.target is set: only deliver to handlers with matching source_filter
        - If event.target is None: deliver to all handlers with matching source_filter or None

        Args:
            event: Event to publish.

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        try:
            handlers = self._handlers.get(event.event_type, [])

            # Filter by source if target specified
            if event.target:
                # Direct to specific handler matching source
                for handler, source_filter in handlers:
                    if source_filter == event.target:
                        await handler(event)
            else:
                # Publish to all handlers matching source filter
                for handler, source_filter in handlers:
                    if source_filter is None or source_filter == event.source:
                        await handler(event)

            return Ok(None)
        except Exception as e:
            return Err(f"Failed to publish event: {e}", code="MEDIATOR_ERROR")

    async def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Awaitable[None]],
        source: Optional[str] = None,
    ) -> Result[None]:
        """Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to.
            handler: Async callable that receives events.
            source: Optional source filter (only events from this source).

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        try:
            self._handlers[event_type].append((handler, source))
            return Ok(None)
        except Exception as e:
            return Err(f"Failed to subscribe to events: {e}", code="MEDIATOR_ERROR")

    async def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Awaitable[None]],
    ) -> Result[None]:
        """Unsubscribe handler from specific event type.

        Note: Removes first matching handler. If multiple identical handlers
        are registered, only the first one is removed.

        Args:
            event_type: Type of events to unsubscribe from.
            handler: Handler to remove.

        Returns:
            Result[None]: Ok on success, Err if handler not found.
        """
        try:
            handlers = self._handlers.get(event_type, [])

            # Remove handler if found
            for idx, (h, _src) in enumerate(handlers):
                if h == handler:
                    handlers.pop(idx)
                    return Ok(None)

            return Err("Handler not found for unsubscribe", code="HANDLER_NOT_FOUND")
        except Exception as e:
            return Err(f"Failed to unsubscribe: {e}", code="MEDIATOR_ERROR")

    async def get_handler_count(self, event_type: EventType) -> Result[int]:
        """Get count of handlers for an event type.

        Args:
            event_type: Type of events to query.

        Returns:
            Result[int]: Count of registered handlers.
        """
        try:
            count = len(self._handlers.get(event_type, []))
            return Ok(count)
        except Exception as e:
            return Err(f"Failed to get handler count: {e}", code="MEDIATOR_ERROR")
