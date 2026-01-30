"""OpenCode Python - Timeline event labeling and management

Provides timeline event tracking with automatic labeling
and session status management.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime
import logging
import asyncio

from opencode_python.observability.models import (
    TimelineEvent,
    EventType,
    SessionStatus,
    Blocker,
)
from opencode_python.core.event_bus import bus

logger = logging.getLogger(__name__)


class TimelineManager:
    """Manages timeline events and session status tracking"""

    def __init__(self):
        """Initialize timeline manager"""
        self._events: Dict[str, List[TimelineEvent]] = {}
        self._session_status: Dict[str, SessionStatus] = {}
        self._blockers: Dict[str, Blocker] = {}
        self._lock = asyncio.Lock()

    async def add_event(
        self,
        session_id: str,
        event_type: EventType,
        details: Optional[dict] = None,
        error_details: Optional[str] = None,
    ) -> TimelineEvent:
        """Add a timeline event

        Args:
            session_id: Session identifier
            event_type: Type of event (plan, tool, code, review, failure, info)
            details: Additional event metadata
            error_details: Error message if event is a failure

        Returns:
            Created timeline event
        """
        async with self._lock:
            event = TimelineEvent(
                id=self._generate_event_id(),
                session_id=session_id,
                event_type=event_type,
                details=details or {},
                is_expandable=event_type in [EventType.FAILURE, EventType.TOOL, EventType.REVIEW, EventType.PLAN],
                error_details=error_details,
            )

            if session_id not in self._events:
                self._events[session_id] = []

            self._events[session_id].append(event)

            await bus.publish(
                "timeline:label",
                {
                    "event_id": event.id,
                    "session_id": session_id,
                    "event_type": event_type.value,
                    "timestamp": event.timestamp,
                },
            )

            logger.debug(f"Added timeline event {event.id} for session {session_id}")

            if event_type == EventType.FAILURE:
                await self._handle_failure(session_id, error_details or "Unknown error")

            return event

    async def set_session_status(
        self,
        session_id: str,
        status: SessionStatus,
        reason: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
    ) -> None:
        """Set session status

        Args:
            session_id: Session identifier
            status: New status (draft, active, blocked, completed)
            reason: Reason for status change (especially for blocked status)
            next_steps: Steps to resolve blocked status
        """
        async with self._lock:
            old_status = self._session_status.get(session_id)
            self._session_status[session_id] = status

            if status == SessionStatus.BLOCKED:
                blocker = Blocker(
                    session_id=session_id,
                    reason=reason or "Session blocked",
                    next_steps=next_steps or [],
                )
                self._blockers[session_id] = blocker

                await bus.publish(
                    "session:blocked",
                    {
                        "session_id": session_id,
                        "reason": blocker.reason,
                        "next_steps": blocker.next_steps,
                    },
                )
            elif session_id in self._blockers:
                del self._blockers[session_id]

            logger.debug(
                f"Session {session_id} status: {old_status} -> {status}"
                + (f" (reason: {reason})" if reason else "")
            )

    async def resolve_blocker(self, session_id: str) -> None:
        """Mark a blocked session as resolved

        Args:
            session_id: Session identifier
        """
        async with self._lock:
            if session_id in self._blockers:
                self._blockers[session_id].is_resolved = True
                await self.set_session_status(session_id, SessionStatus.ACTIVE)

    def get_events(self, session_id: str) -> List[TimelineEvent]:
        """Get all timeline events for a session

        Args:
            session_id: Session identifier

        Returns:
            List of timeline events
        """
        return self._events.get(session_id, [])

    def get_session_status(self, session_id: str) -> SessionStatus:
        """Get session status

        Args:
            session_id: Session identifier

        Returns:
            Session status (defaults to DRAFT)
        """
        return self._session_status.get(session_id, SessionStatus.DRAFT)

    def get_blocker(self, session_id: str) -> Optional[Blocker]:
        """Get blocker information for a blocked session

        Args:
            session_id: Session identifier

        Returns:
            Blocker info if session is blocked, None otherwise
        """
        return self._blockers.get(session_id)

    def _generate_event_id(self) -> str:
        """Generate unique event ID

        Returns:
            Unique event identifier
        """
        return f"evt_{int(datetime.now().timestamp() * 1000)}"

    async def _handle_failure(self, session_id: str, error_message: str) -> None:
        """Handle a failure event

        Automatically sets session to blocked if appropriate.

        Args:
            session_id: Session identifier
            error_message: Error message from failure
        """
        await self.set_session_status(
            session_id,
            SessionStatus.BLOCKED,
            reason=error_message,
            next_steps=["Review the error details", "Fix the underlying issue", "Retry the operation"],
        )


# Global timeline manager instance
timeline_manager = TimelineManager()
