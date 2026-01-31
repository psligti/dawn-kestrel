"""OpenCode Python - Error collection and management

Collects and displays errors from all system components with level categorization.
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from threading import Lock
import logging

from opencode_python.core.event_bus import bus
import pydantic as pd

logger = logging.getLogger(__name__)


class ErrorLevel(Enum):
    """Error severity levels for categorization"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"


class ErrorRecord(pd.BaseModel):
    """Error record with metadata for collection and display"""
    record_id: str
    session_id: str
    level: ErrorLevel
    message: str
    context: Dict[str, Any] = pd.Field(default_factory=dict)
    timestamp: float = pd.Field(default_factory=lambda: datetime.now().timestamp())
    source: Optional[str] = None
    is_resolved: bool = False
    error_details: Optional[str] = None

    @property
    def formatted_timestamp(self) -> str:
        """Get human-readable timestamp"""
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def icon(self) -> str:
        """Get icon based on error level"""
        icons = {
            ErrorLevel.CRITICAL: "🔴",
            ErrorLevel.ERROR: "❌",
            ErrorLevel.WARNING: "⚠️",
        }
        return icons.get(self.level, "❓")


class ErrorCollector:
    """Collects and manages errors across the system"""

    _instance: Optional["ErrorCollector"] = None
    _lock: Lock

    def __new__(cls) -> "ErrorCollector":
        """Singleton pattern to ensure single error collector instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = Lock()
        return cls._instance

    def __init__(self) -> None:
        """Initialize error collector"""
        if hasattr(self, "_initialized"):
            return
        self._errors: Dict[str, ErrorRecord] = {}
        self._by_session: Dict[str, List[str]] = {}
        self._by_level: Dict[ErrorLevel, List[str]] = {}
        self._initialized = True

    def collect_error(
        self,
        level: ErrorLevel,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> str:
        record_id = f"error_{datetime.now().timestamp()}_{len(self._errors)}"
        error_record = ErrorRecord(
            record_id=record_id,
            session_id=session_id,
            level=level,
            message=message,
            context=context or {},
            source=source,
            error_details=error_details,
        )

        try:
            with self._lock:
                self._errors[record_id] = error_record
                if session_id not in self._by_session:
                    self._by_session[session_id] = []
                self._by_session[session_id].append(record_id)

                if level not in self._by_level:
                    self._by_level[level] = []
                self._by_level[level].append(record_id)

                # Emit event for error display
                asyncio.create_task(
                    bus.publish(
                        "DRAWER_ERROR_DISPLAYED",
                        {
                            "record_id": record_id,
                            "level": level.value,
                            "message": message,
                            "session_id": session_id,
                            "source": source,
                            "timestamp": error_record.timestamp,
                        },
                    )
                )
        except RuntimeError:
            pass

        logger.warning(
            f"Collected {level.value} error: {message} (record_id={record_id})"
        )

        return record_id

    def get_errors(
        self,
        session_id: Optional[str] = None,
        level: Optional[ErrorLevel] = None,
        resolved: Optional[bool] = None,
    ) -> List[ErrorRecord]:
        """Get errors with optional filtering

        Args:
            session_id: Filter by session ID
            level: Filter by error level
            resolved: Filter by resolved status

        Returns:
            List of ErrorRecord objects sorted by timestamp (newest first)
        """
        errors = list(self._errors.values())

        if session_id:
            record_ids = self._by_session.get(session_id, [])
            errors = [e for e in errors if e.record_id in record_ids]

        if level:
            record_ids = self._by_level.get(level, [])
            errors = [e for e in errors if e.record_id in record_ids]

        if resolved is not None:
            errors = [e for e in errors if e.is_resolved == resolved]

        errors.sort(key=lambda e: e.timestamp, reverse=True)

        return errors

    def get_errors_count(
        self,
        session_id: Optional[str] = None,
        level: Optional[ErrorLevel] = None,
        resolved: Optional[bool] = None,
    ) -> int:
        """Get count of errors matching filters

        Args:
            session_id: Filter by session ID
            level: Filter by error level
            resolved: Filter by resolved status

        Returns:
            Count of matching errors
        """
        return len(self.get_errors(session_id, level, resolved))

    def resolve_error(self, record_id: str) -> bool:
        with self._lock:
            error = self._errors.get(record_id)
            if not error:
                return False

            error.is_resolved = True
            return True

    def clear_session_errors(self, session_id: str) -> int:
        with self._lock:
            record_ids = self._by_session.get(session_id, [])
            cleared = 0
            for record_id in record_ids:
                if record_id in self._errors:
                    del self._errors[record_id]
                    cleared += 1
            if session_id in self._by_session:
                del self._by_session[session_id]
            return cleared

    def clear_all_errors(self) -> int:
        with self._lock:
            count = len(self._errors)
            self._errors.clear()
            self._by_session.clear()
            self._by_level.clear()
            return count

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_errors": len(self._errors),
                "by_level": {
                    level.value: len(ids) for level, ids in self._by_level.items()
                },
                "by_session": {
                    session_id: len(ids)
                    for session_id, ids in self._by_session.items()
                },
                "unresolved": len(
                    [e for e in self._errors.values() if not e.is_resolved]
                ),
            }


# Global error collector instance
error_collector = ErrorCollector()
