"""OpenCode Python - Event bus for async communication"""
from __future__ import annotations
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
import asyncio
from collections import defaultdict
import logging


logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data container"""
    name: str
    data: Dict[str, Any] = field(default_factory=dict)


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
        self._subscriptions: Dict[str, List[EventSubscription]] = defaultdict(list)
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

    async def publish(self, event_name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Publish an event

        Args:
            event_name: Name of event to publish
            data: Data to send with event
        """
        event = Event(name=event_name, data=data or {})

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

    async def clear_subscriptions(self, event_name: Optional[str] = None) -> None:
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
    SESSION_RESUMED = "session.resumed"
    SESSION_AUTOSAVE = "session.autosave"
    SESSION_EXPORT = "session.export"
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
    TOOL_DISCOVER = "tool.discover"
    TOOL_ALLOW = "tool.allow"
    TOOL_DENY = "tool.deny"
    TOOL_EXECUTE = "tool.execute"
    TOOL_LOG = "tool.log"
    AGENT_INITIALIZED = "agent.initialized"
    AGENT_READY = "agent.ready"
    AGENT_EXECUTING = "agent.executing"
    AGENT_ERROR = "agent.error"
    AGENT_CLEANUP = "agent.cleanup"
    AGENT_EXECUTE = "agent.execute"
    SKILL_ENABLED = "skill.enable"
    SKILL_DISABLED = "skill.disable"
    SKILL_BLOCKED = "skill.block"
    SKILL_EXECUTE = "skill.execute"
