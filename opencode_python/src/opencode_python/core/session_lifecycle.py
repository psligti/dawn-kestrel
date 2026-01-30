"""
Session lifecycle hooks for SDK client integration.

Provides callbacks for session events (created, updated, message added, archived)
that can be registered by SDK clients or external systems.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from abc import ABC, abstractmethod
import asyncio
import logging

from opencode_python.core.event_bus import bus, Events
from opencode_python.core.models import Session, Message


logger = logging.getLogger(__name__)


class SessionLifecycleListener(ABC):
    """Protocol for session lifecycle event listeners

    Subclasses should implement lifecycle event hooks to react to
    session state changes.
    """

    async def on_session_created(self, session: Session) -> None:
        """Called when a new session is created

        Args:
            session: Newly created session
        """
        pass

    async def on_session_updated(self, session: Session) -> None:
        """Called when a session is updated

        Args:
            session: Updated session
        """
        pass

    async def on_message_added(self, session: Session, message: Message) -> None:
        """Called when a message is added to a session

        Args:
            session: Session receiving message
            message: Newly added message
        """
        pass

    async def on_message_updated(self, session: Session, message: Message) -> None:
        """Called when a message is updated in a session

        Args:
            session: Session containing message
            message: Updated message
        """
        pass

    async def on_session_archived(self, session: Session) -> None:
        """Called when a session is archived

        Args:
            session: Archived session
        """
        pass

    async def on_session_compacted(self, session: Session) -> None:
        """Called when a session is compacted

        Args:
            session: Compacted session
        """
        pass

    async def on_session_deleted(self, session_id: str) -> None:
        """Called when a session is deleted

        Args:
            session_id: ID of deleted session
        """
        pass


class SessionLifecycle:
    """
    Session lifecycle hooks for SDK client integration.

    Manages callback registration and emission for session events.
    Supports multiple callbacks per event type for cross-cutting concerns.

    Attributes:
        _on_session_created: Callbacks for session creation events
        _on_session_updated: Callbacks for session update events
        _on_message_added: Callbacks for message addition events
        _on_message_updated: Callbacks for message update events
        _on_session_archived: Callbacks for session archive events
        _on_session_compacted: Callbacks for session compaction events
        _on_session_deleted: Callbacks for session deletion events
        _listeners: Protocol-based lifecycle listeners
    """

    def __init__(self) -> None:
        """Initialize SessionLifecycle with empty callback lists."""
        self._on_session_created: List[Callable[[Dict[str, Any]], None]] = []
        self._on_session_updated: List[Callable[[Dict[str, Any]], None]] = []
        self._on_message_added: List[Callable[[Dict[str, Any]], None]] = []
        self._on_message_updated: List[Callable[[Dict[str, Any]], None]] = []
        self._on_session_archived: List[Callable[[Dict[str, Any]], None]] = []
        self._on_session_compacted: List[Callable[[Dict[str, Any]], None]] = []
        self._on_session_deleted: List[Callable[[str], None]] = []
        self._listeners: List[SessionLifecycleListener] = []

    def on_session_created(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Register a callback for session creation events.

        Args:
            callback: Function called with session data when a session is created.
                Signature: (session_data: Dict[str, Any]) -> None
        """
        self._on_session_created.append(callback)
        logger.debug(f"Registered session_created callback: {getattr(callback, '__name__', str(callback))}")

    def on_session_updated(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Register a callback for session update events.

        Args:
            callback: Function called with session data when a session is updated.
                Signature: (session_data: Dict[str, Any]) -> None
        """
        self._on_session_updated.append(callback)
        logger.debug(f"Registered session_updated callback: {getattr(callback, '__name__', str(callback))}")

    def on_message_added(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Register a callback for message addition events.

        Args:
            callback: Function called with message data when a message is added.
                Signature: (message_data: Dict[str, Any]) -> None
        """
        self._on_message_added.append(callback)
        logger.debug(f"Registered message_added callback: {getattr(callback, '__name__', str(callback))}")

    def on_session_archived(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Register a callback for session archive events.

        Args:
            callback: Function called with session data when a session is archived.
                Signature: (session_data: Dict[str, Any]) -> None
        """
        self._on_session_archived.append(callback)
        logger.debug(f"Registered session_archived callback: {getattr(callback, '__name__', str(callback))}")

    def on_message_updated(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Register a callback for message update events.

        Args:
            callback: Function called with message data when a message is updated.
                Signature: (message_data: Dict[str, Any]) -> None
        """
        self._on_message_updated.append(callback)
        logger.debug(f"Registered message_updated callback: {getattr(callback, '__name__', str(callback))}")

    def on_session_compacted(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Register a callback for session compaction events.

        Args:
            callback: Function called with session data when a session is compacted.
                Signature: (session_data: Dict[str, Any]) -> None
        """
        self._on_session_compacted.append(callback)
        logger.debug(f"Registered session_compacted callback: {getattr(callback, '__name__', str(callback))}")

    def on_session_deleted(
        self,
        callback: Callable[[str], None],
    ) -> None:
        """
        Register a callback for session deletion events.

        Args:
            callback: Function called with session ID when a session is deleted.
                Signature: (session_id: str) -> None
        """
        self._on_session_deleted.append(callback)
        logger.debug(f"Registered session_deleted callback: {getattr(callback, '__name__', str(callback))}")

    def unregister_session_created(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> bool:
        """
        Unregister a session creation callback.

        Args:
            callback: Callback function to remove.

        Returns:
            True if callback was found and removed, False otherwise.
        """
        if callback in self._on_session_created:
            self._on_session_created.remove(callback)
            logger.debug(f"Unregistered session_created callback: {getattr(callback, '__name__', str(callback))}")
            return True
        return False

    def unregister_session_updated(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> bool:
        """
        Unregister a session update callback.

        Args:
            callback: Callback function to remove.

        Returns:
            True if callback was found and removed, False otherwise.
        """
        if callback in self._on_session_updated:
            self._on_session_updated.remove(callback)
            logger.debug(f"Unregistered session_updated callback: {getattr(callback, '__name__', str(callback))}")
            return True
        return False

    def unregister_message_added(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> bool:
        """
        Unregister a message addition callback.

        Args:
            callback: Callback function to remove.

        Returns:
            True if callback was found and removed, False otherwise.
        """
        if callback in self._on_message_added:
            self._on_message_added.remove(callback)
            logger.debug(f"Unregistered message_added callback: {getattr(callback, '__name__', str(callback))}")
            return True
        return False

    def unregister_session_archived(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> bool:
        """
        Unregister a session archive callback.

        Args:
            callback: Callback function to remove.

        Returns:
            True if callback was found and removed, False otherwise.
        """
        if callback in self._on_session_archived:
            self._on_session_archived.remove(callback)
            logger.debug(f"Unregistered session_archived callback: {getattr(callback, '__name__', str(callback))}")
            return True
        return False

    def unregister_message_updated(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> bool:
        """
        Unregister a message update callback.

        Args:
            callback: Callback function to remove.

        Returns:
            True if callback was found and removed, False otherwise.
        """
        if callback in self._on_message_updated:
            self._on_message_updated.remove(callback)
            logger.debug(f"Unregistered message_updated callback: {getattr(callback, '__name__', str(callback))}")
            return True
        return False

    def unregister_session_compacted(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> bool:
        """
        Unregister a session compaction callback.

        Args:
            callback: Callback function to remove.

        Returns:
            True if callback was found and removed, False otherwise.
        """
        if callback in self._on_session_compacted:
            self._on_session_compacted.remove(callback)
            logger.debug(f"Unregistered session_compacted callback: {getattr(callback, '__name__', str(callback))}")
            return True
        return False

    def unregister_session_deleted(
        self,
        callback: Callable[[str], None],
    ) -> bool:
        """
        Unregister a session deletion callback.

        Args:
            callback: Callback function to remove.

        Returns:
            True if callback was found and removed, False otherwise.
        """
        if callback in self._on_session_deleted:
            self._on_session_deleted.remove(callback)
            logger.debug(f"Unregistered session_deleted callback: {getattr(callback, '__name__', str(callback))}")
            return True
        return False

    async def register_listener(self, listener: SessionLifecycleListener) -> None:
        """Register a protocol-based lifecycle listener

        Args:
            listener: Listener implementing SessionLifecycleListener protocol
        """
        if listener not in self._listeners:
            self._listeners.append(listener)
            logger.debug(f"Registered lifecycle listener: {listener.__class__.__name__}")

    async def unregister_listener(self, listener: SessionLifecycleListener) -> None:
        """Unregister a protocol-based lifecycle listener

        Args:
            listener: Listener to remove
        """
        if listener in self._listeners:
            self._listeners.remove(listener)
            logger.debug(f"Unregistered lifecycle listener: {listener.__class__.__name__}")

    async def emit_session_created(self, session_data: Dict[str, Any]) -> None:
        """
        Emit session creation event to all registered callbacks.

        Args:
            session_data: Session data dictionary.
        """
        for callback in self._on_session_created:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(session_data)
                else:
                    callback(session_data)
            except Exception as e:
                logger.error(f"Error in session_created callback: {e}")

        for listener in self._listeners:
            try:
                from opencode_python.core.models import Session
                session = Session(**session_data)
                await listener.on_session_created(session)
            except Exception as e:
                logger.error(f"Error in lifecycle listener on_session_created: {e}")

        await bus.publish(Events.SESSION_CREATED, {"session": session_data})

    async def emit_session_updated(self, session_data: Dict[str, Any]) -> None:
        """
        Emit session update event to all registered callbacks.

        Args:
            session_data: Session data dictionary.
        """
        for callback in self._on_session_updated:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(session_data)
                else:
                    callback(session_data)
            except Exception as e:
                logger.error(f"Error in session_updated callback: {e}")

        for listener in self._listeners:
            try:
                from opencode_python.core.models import Session
                session = Session(**session_data)
                await listener.on_session_updated(session)
            except Exception as e:
                logger.error(f"Error in lifecycle listener on_session_updated: {e}")

        await bus.publish(Events.SESSION_UPDATED, {"session": session_data})

    async def emit_message_added(self, message_data: Dict[str, Any]) -> None:
        """
        Emit message addition event to all registered callbacks.

        Args:
            message_data: Message data dictionary.
        """
        for callback in self._on_message_added:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message_data)
                else:
                    callback(message_data)
            except Exception as e:
                logger.error(f"Error in message_added callback: {e}")

        for listener in self._listeners:
            try:
                from opencode_python.core.models import Session, Message
                session = Session(**message_data.get("session", {}))
                message = Message(**message_data)
                await listener.on_message_added(session, message)
            except Exception as e:
                logger.error(f"Error in lifecycle listener on_message_added: {e}")

        await bus.publish(Events.MESSAGE_CREATED, {"message": message_data})

    async def emit_message_updated(self, message_data: Dict[str, Any]) -> None:
        """
        Emit message update event to all registered callbacks.

        Args:
            message_data: Message data dictionary.
        """
        for callback in self._on_message_updated:
            try:
                callback(message_data)
            except Exception as e:
                logger.error(f"Error in message_updated callback: {e}")

        for listener in self._listeners:
            try:
                from opencode_python.core.models import Session, Message
                session = Session(**message_data.get("session", {}))
                message = Message(**message_data)
                await listener.on_message_updated(session, message)
            except Exception as e:
                logger.error(f"Error in lifecycle listener on_message_updated: {e}")

        await bus.publish(Events.MESSAGE_UPDATED, {"message": message_data})

    async def emit_session_archived(self, session_data: Dict[str, Any]) -> None:
        """
        Emit session archive event to all registered callbacks.

        Args:
            session_data: Session data dictionary.
        """
        for callback in self._on_session_archived:
            try:
                callback(session_data)
            except Exception as e:
                logger.error(f"Error in session_archived callback: {e}")

        for listener in self._listeners:
            try:
                from opencode_python.core.models import Session
                session = Session(**session_data)
                await listener.on_session_archived(session)
            except Exception as e:
                logger.error(f"Error in lifecycle listener on_session_archived: {e}")

    async def emit_session_compacted(self, session_data: Dict[str, Any]) -> None:
        """
        Emit session compaction event to all registered callbacks.

        Args:
            session_data: Session data dictionary.
        """
        for callback in self._on_session_compacted:
            try:
                callback(session_data)
            except Exception as e:
                logger.error(f"Error in session_compacted callback: {e}")

        for listener in self._listeners:
            try:
                from opencode_python.core.models import Session
                session = Session(**session_data)
                await listener.on_session_compacted(session)
            except Exception as e:
                logger.error(f"Error in lifecycle listener on_session_compacted: {e}")

    async def emit_session_deleted(self, session_id: str) -> None:
        """
        Emit session deletion event to all registered callbacks.

        Args:
            session_id: Session ID.
        """
        for callback in self._on_session_deleted:
            try:
                callback(session_id)
            except Exception as e:
                logger.error(f"Error in session_deleted callback: {e}")

        for listener in self._listeners:
            try:
                await listener.on_session_deleted(session_id)
            except Exception as e:
                logger.error(f"Error in lifecycle listener on_session_deleted: {e}")

        await bus.publish(Events.SESSION_DELETED, {"session_id": session_id})

    def clear(self) -> None:
        """Clear all registered callbacks."""
        self._on_session_created.clear()
        self._on_session_updated.clear()
        self._on_message_added.clear()
        self._on_message_updated.clear()
        self._on_session_archived.clear()
        self._on_session_compacted.clear()
        self._on_session_deleted.clear()
        self._listeners.clear()
        logger.debug("Cleared all lifecycle callbacks")


def create_session_lifecycle() -> SessionLifecycle:
    """
    Factory function to create a SessionLifecycle instance.

    Returns:
        SessionLifecycle instance.
    """
    return SessionLifecycle()
