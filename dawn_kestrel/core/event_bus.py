"""OpenCode Python - Event bus for async communication"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data container"""

    name: str
    data: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    parent_span_id: str | None = None
    duration_ms: float | None = None
    span_name: str | None = None


@dataclass
class EventSubscription:
    """Event subscription with callback"""

    event_name: str
    callback: Callable[[Event], Any]
    once: bool = False


class EventBus:
    """Async event bus for decoupled communication"""

    def __init__(self) -> None:
        """Initialize event bus"""
        self._subscriptions: dict[str, list[EventSubscription]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        event_name: str,
        callback: Callable[[Event], Any],
        once: bool = False,
    ) -> Callable[[], Any]:
        """Subscribe to an event

        Args:
            event_name: Name of the event to subscribe to
            callback: Async function to call when event is published
            once: If True, unsubscribe after first call

        Returns:
            Unsubscribe function
        """
        subscription = EventSubscription(event_name=event_name, callback=callback, once=once)
        self._subscriptions[event_name].append(subscription)

        async def unsubscribe() -> None:
            async with self._lock:
                if subscription in self._subscriptions.get(event_name, []):
                    self._subscriptions[event_name].remove(subscription)

        return unsubscribe

    async def publish(self, event_name: str, data: dict[str, Any] | None = None) -> None:
        """Publish an event

        Args:
            event_name: Name of event to publish
            data: Data to send with event
        """
        from dawn_kestrel.agents.review.utils.redaction import redact_dict

        redacted_data = redact_dict(data) if data else {}
        event = Event(name=event_name, data=redacted_data)

        async with self._lock:
            subscriptions = self._subscriptions[event_name].copy()
            to_remove = []

            for subscription in subscriptions:
                if subscription.once:
                    to_remove.append(subscription)
                try:
                    result = subscription.callback(event)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Error in event callback for {event_name}: {e}")

            # Remove once subscriptions
            for subscription in to_remove:
                if subscription in self._subscriptions[event_name]:
                    self._subscriptions[event_name].remove(subscription)

    async def clear_subscriptions(self, event_name: str | None = None) -> None:
        """Clear all subscriptions or subscriptions for an event"""
        async with self._lock:
            if event_name:
                self._subscriptions[event_name].clear()
            else:
                self._subscriptions.clear()


# Global event bus instance
bus = EventBus()


# Event names
class Events:
    """Predefined event names"""

    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    SESSION_DELETED = "session.deleted"
    MESSAGE_CREATED = "message.created"
    MESSAGE_DELETED = "message.deleted"
    MESSAGE_UPDATED = "message.updated"
    MESSAGE_PART_UPDATED = "message.part.updated"
    PERMISSION_ASKED = "permission.asked"
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_DENIED = "permission.denied"
    FILE_WATCHED = "file.watched"
    GIT_STATUS_CHANGED = "git.status.changed"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_ERROR = "tool.error"
    AGENT_INITIALIZED = "agent.initialized"
    AGENT_READY = "agent.ready"
    AGENT_EXECUTING = "agent.executing"
    AGENT_ERROR = "agent.error"
    AGENT_CLEANUP = "agent.cleanup"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    SUBTASK_ADDED = "subtask.added"
