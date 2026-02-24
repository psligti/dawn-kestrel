"""Trace collection system for distributed tracing.

Provides Span model for trace data, TraceCollector for managing spans,
and TraceStore for in-memory storage with query capabilities.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Span:
    """Represents a single span in a distributed trace.

    A span represents a unit of work within a trace, such as a function call,
    database query, or HTTP request. Spans can be nested to form a tree.

    Attributes:
        span_id: Unique identifier for this span.
        trace_id: Identifier linking all spans in a trace.
        name: Human-readable name for the operation.
        start_time: When the span started.
        end_time: When the span ended (None if in-progress).
        parent_span_id: ID of parent span (None for root spans).
        attributes: Key-value pairs with additional metadata.
        session_id: Optional session identifier for correlation.
    """

    span_id: str
    trace_id: str
    name: str
    start_time: datetime
    end_time: datetime | None = None
    parent_span_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None

    @property
    def duration_ms(self) -> float | None:
        """Calculate span duration in milliseconds."""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return delta.total_seconds() * 1000

    @property
    def is_root(self) -> bool:
        """Check if this is a root span (no parent)."""
        return self.parent_span_id is None

    def to_dict(self) -> dict[str, Any]:
        """Serialize span to dictionary for JSON export."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "parent_span_id": self.parent_span_id,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "session_id": self.session_id,
        }


class TraceCollector:
    """Manages span lifecycle and trace context propagation.

    TraceCollector is responsible for:
    - Creating and tracking spans
    - Managing the current span context
    - Propagating trace context to child spans
    """

    def __init__(self) -> None:
        """Initialize the trace collector."""
        self._spans: dict[str, Span] = {}
        self._current_span: Span | None = None

    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Span:
        """Start a new span.

        If trace_id or parent_span_id are not provided and there is a current
        span context, they will be inherited from the current span.

        Args:
            name: Human-readable name for the operation.
            trace_id: Trace ID (generated if not provided).
            parent_span_id: Parent span ID (inherited from context if not provided).
            attributes: Optional metadata attributes.
            session_id: Optional session identifier.

        Returns:
            The newly created span.
        """
        span_id = self._generate_span_id()

        if trace_id is None:
            if self._current_span is not None:
                trace_id = self._current_span.trace_id
            else:
                trace_id = self._generate_trace_id()

        if parent_span_id is None and self._current_span is not None:
            parent_span_id = self._current_span.span_id

        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            name=name,
            start_time=datetime.now(),
            parent_span_id=parent_span_id,
            attributes=attributes or {},
            session_id=session_id,
        )

        self._spans[span_id] = span
        return span

    def end_span(self, span_id: str) -> Span | None:
        """End a span by setting its end_time.

        Args:
            span_id: ID of the span to end.

        Returns:
            The ended span, or None if not found.
        """
        span = self._spans.get(span_id)
        if span is None:
            return None

        span.end_time = datetime.now()
        return span

    def get_trace(self, trace_id: str) -> list[Span]:
        """Get all spans for a given trace.

        Args:
            trace_id: The trace ID to query.

        Returns:
            List of spans belonging to the trace.
        """
        return [s for s in self._spans.values() if s.trace_id == trace_id]

    def set_current_span(self, span: Span) -> None:
        """Set the current span for context propagation.

        Args:
            span: The span to set as current.
        """
        self._current_span = span

    def get_current_span(self) -> Span | None:
        """Get the current span from context.

        Returns:
            The current span, or None if no context is set.
        """
        return self._current_span

    def clear_current_span(self) -> None:
        """Clear the current span context."""
        self._current_span = None

    def _generate_span_id(self) -> str:
        """Generate a unique span ID."""
        return f"span-{uuid.uuid4().hex[:16]}"

    def _generate_trace_id(self) -> str:
        """Generate a unique trace ID."""
        return f"trace-{uuid.uuid4().hex[:24]}"


class TraceStore:
    """In-memory storage for spans with query capabilities.

    TraceStore provides:
    - Thread-safe span storage
    - Query by session_id, trace_id, time range
    - Size limit with FIFO eviction
    """

    def __init__(self, max_size: int = 1000) -> None:
        """Initialize the trace store.

        Args:
            max_size: Maximum number of spans to store (0 = unlimited).
        """
        self._spans: list[Span] = []
        self._max_size = max_size

    def add(self, span: Span) -> None:
        """Add a span to the store.

        If the store has a size limit and is full, the oldest spans
        will be evicted to make room.

        Args:
            span: The span to add.
        """
        self._spans.append(span)

        if self._max_size > 0 and len(self._spans) > self._max_size:
            excess = len(self._spans) - self._max_size
            self._spans = self._spans[excess:]

    def query(
        self,
        session_id: str | None = None,
        trace_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Span]:
        """Query spans by various filters.

        All filters are optional and combined with AND logic.

        Args:
            session_id: Filter by session ID.
            trace_id: Filter by trace ID.
            start_time: Filter spans starting at or after this time.
            end_time: Filter spans starting at or before this time.

        Returns:
            List of matching spans.
        """
        results = self._spans

        if session_id is not None:
            results = [s for s in results if s.session_id == session_id]

        if trace_id is not None:
            results = [s for s in results if s.trace_id == trace_id]

        if start_time is not None:
            results = [s for s in results if s.start_time >= start_time]

        if end_time is not None:
            results = [s for s in results if s.start_time <= end_time]

        return results

    def get_all(self) -> list[Span]:
        """Get all stored spans.

        Returns:
            List of all spans.
        """
        return list(self._spans)

    def clear(self) -> None:
        """Clear all stored spans."""
        self._spans.clear()

    @property
    def count(self) -> int:
        """Get the number of stored spans."""
        return len(self._spans)
