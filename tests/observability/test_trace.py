"""Tests for trace collection system.

Tests verify:
- Span model with proper fields
- TraceCollector for managing spans (start/end/get)
- TraceStore for in-memory storage with size limit
- Trace context propagation
- Query by session_id and time range
"""

import time
from datetime import datetime, timedelta

import pytest


class TestSpanModel:
    """Tests for Span data model."""

    def test_span_has_required_fields(self):
        """Span has all required fields."""
        from dawn_kestrel.observability.trace import Span

        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_operation",
            start_time=datetime.now(),
        )

        assert span.span_id == "span-001"
        assert span.trace_id == "trace-001"
        assert span.name == "test_operation"
        assert span.start_time is not None

    def test_span_has_optional_parent_span_id(self):
        """Span can have optional parent_span_id."""
        from dawn_kestrel.observability.trace import Span

        span = Span(
            span_id="span-002",
            trace_id="trace-001",
            name="child_operation",
            start_time=datetime.now(),
            parent_span_id="span-001",
        )

        assert span.parent_span_id == "span-001"

    def test_span_parent_span_id_defaults_to_none(self):
        """Span parent_span_id defaults to None for root spans."""
        from dawn_kestrel.observability.trace import Span

        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="root_operation",
            start_time=datetime.now(),
        )

        assert span.parent_span_id is None

    def test_span_has_optional_end_time(self):
        """Span can have optional end_time."""
        from dawn_kestrel.observability.trace import Span

        now = datetime.now()
        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_operation",
            start_time=now,
            end_time=now + timedelta(milliseconds=100),
        )

        assert span.end_time is not None

    def test_span_end_time_defaults_to_none(self):
        """Span end_time defaults to None for in-progress spans."""
        from dawn_kestrel.observability.trace import Span

        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_operation",
            start_time=datetime.now(),
        )

        assert span.end_time is None

    def test_span_has_optional_attributes(self):
        """Span can have optional attributes dict."""
        from dawn_kestrel.observability.trace import Span

        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_operation",
            start_time=datetime.now(),
            attributes={"user_id": "123", "operation": "query"},
        )

        assert span.attributes == {"user_id": "123", "operation": "query"}

    def test_span_attributes_defaults_to_empty_dict(self):
        """Span attributes defaults to empty dict."""
        from dawn_kestrel.observability.trace import Span

        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_operation",
            start_time=datetime.now(),
        )

        assert span.attributes == {}

    def test_span_duration_ms_calculated(self):
        """Span duration_ms is calculated when end_time is set."""
        from dawn_kestrel.observability.trace import Span

        now = datetime.now()
        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_operation",
            start_time=now,
            end_time=now + timedelta(milliseconds=150),
        )

        assert span.duration_ms == 150.0

    def test_span_duration_ms_none_when_no_end_time(self):
        """Span duration_ms is None when end_time is not set."""
        from dawn_kestrel.observability.trace import Span

        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_operation",
            start_time=datetime.now(),
        )

        assert span.duration_ms is None

    def test_span_is_root_property(self):
        """Span is_root property returns True for spans without parent."""
        from dawn_kestrel.observability.trace import Span

        root_span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="root_operation",
            start_time=datetime.now(),
        )
        child_span = Span(
            span_id="span-002",
            trace_id="trace-001",
            name="child_operation",
            start_time=datetime.now(),
            parent_span_id="span-001",
        )

        assert root_span.is_root is True
        assert child_span.is_root is False


class TestTraceCollector:
    """Tests for TraceCollector."""

    def test_trace_collector_start_span(self):
        """TraceCollector can start a span."""
        from dawn_kestrel.observability.trace import TraceCollector

        collector = TraceCollector()
        span = collector.start_span(name="test_operation", trace_id="trace-001")

        assert span is not None
        assert span.name == "test_operation"
        assert span.trace_id == "trace-001"
        assert span.end_time is None  # Span is in-progress

    def test_trace_collector_start_span_generates_ids(self):
        """TraceCollector generates span_id and trace_id if not provided."""
        from dawn_kestrel.observability.trace import TraceCollector

        collector = TraceCollector()
        span = collector.start_span(name="test_operation")

        assert span.span_id is not None
        assert len(span.span_id) > 0
        assert span.trace_id is not None
        assert len(span.trace_id) > 0

    def test_trace_collector_end_span(self):
        """TraceCollector can end a span."""
        from dawn_kestrel.observability.trace import TraceCollector

        collector = TraceCollector()
        span = collector.start_span(name="test_operation", trace_id="trace-001")

        ended_span = collector.end_span(span.span_id)

        assert ended_span is not None
        assert ended_span.end_time is not None
        assert ended_span.duration_ms is not None

    def test_trace_collector_end_span_returns_none_for_unknown(self):
        """TraceCollector end_span returns None for unknown span."""
        from dawn_kestrel.observability.trace import TraceCollector

        collector = TraceCollector()
        result = collector.end_span("unknown-span-id")

        assert result is None

    def test_trace_collector_get_trace(self):
        """TraceCollector can get all spans for a trace."""
        from dawn_kestrel.observability.trace import TraceCollector

        collector = TraceCollector()
        collector.start_span(name="op1", trace_id="trace-001")
        collector.start_span(name="op2", trace_id="trace-001")
        collector.start_span(name="op3", trace_id="trace-002")

        trace1 = collector.get_trace("trace-001")
        trace2 = collector.get_trace("trace-002")

        assert len(trace1) == 2
        assert len(trace2) == 1
        assert all(s.trace_id == "trace-001" for s in trace1)

    def test_trace_collector_get_trace_returns_empty_for_unknown(self):
        """TraceCollector get_trace returns empty list for unknown trace."""
        from dawn_kestrel.observability.trace import TraceCollector

        collector = TraceCollector()
        result = collector.get_trace("unknown-trace-id")

        assert result == []

    def test_trace_collector_child_span_has_parent(self):
        """TraceCollector can create child spans with parent."""
        from dawn_kestrel.observability.trace import TraceCollector

        collector = TraceCollector()
        parent = collector.start_span(name="parent", trace_id="trace-001")
        child = collector.start_span(
            name="child",
            trace_id="trace-001",
            parent_span_id=parent.span_id,
        )

        assert child.parent_span_id == parent.span_id
        assert child.trace_id == parent.trace_id

    def test_trace_collector_context_propagation(self):
        """TraceCollector supports trace context propagation."""
        from dawn_kestrel.observability.trace import TraceCollector

        collector = TraceCollector()

        # Start parent span and set as current
        parent = collector.start_span(name="parent", trace_id="trace-001")
        collector.set_current_span(parent)

        # Start child span - should inherit trace context
        child = collector.start_span(name="child")

        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id

    def test_trace_collector_get_current_span(self):
        """TraceCollector can get current span from context."""
        from dawn_kestrel.observability.trace import TraceCollector

        collector = TraceCollector()

        # No current span initially
        assert collector.get_current_span() is None

        # Set current span
        span = collector.start_span(name="test", trace_id="trace-001")
        collector.set_current_span(span)

        assert collector.get_current_span() == span

    def test_trace_collector_clear_current_span(self):
        """TraceCollector can clear current span."""
        from dawn_kestrel.observability.trace import TraceCollector

        collector = TraceCollector()
        span = collector.start_span(name="test", trace_id="trace-001")
        collector.set_current_span(span)

        collector.clear_current_span()

        assert collector.get_current_span() is None


class TestTraceStore:
    """Tests for TraceStore."""

    def test_trace_store_add_span(self):
        """TraceStore can add a span."""
        from dawn_kestrel.observability.trace import Span, TraceStore

        store = TraceStore()
        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_operation",
            start_time=datetime.now(),
            session_id="session-001",
        )

        store.add(span)

        assert len(store.get_all()) == 1

    def test_trace_store_query_by_session_id(self):
        """TraceStore can query spans by session_id."""
        from dawn_kestrel.observability.trace import Span, TraceStore

        store = TraceStore()
        now = datetime.now()

        for i in range(3):
            store.add(
                Span(
                    span_id=f"span-{i}",
                    trace_id="trace-001",
                    name=f"op-{i}",
                    start_time=now,
                    session_id="session-001",
                )
            )
        for i in range(3, 5):
            store.add(
                Span(
                    span_id=f"span-{i}",
                    trace_id="trace-002",
                    name=f"op-{i}",
                    start_time=now,
                    session_id="session-002",
                )
            )

        session1_spans = store.query(session_id="session-001")
        session2_spans = store.query(session_id="session-002")

        assert len(session1_spans) == 3
        assert len(session2_spans) == 2

    def test_trace_store_query_by_time_range(self):
        """TraceStore can query spans by time range."""
        from dawn_kestrel.observability.trace import Span, TraceStore

        store = TraceStore()
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        # Add spans at different times
        store.add(
            Span(
                span_id="span-1",
                trace_id="trace-001",
                name="op1",
                start_time=base_time,
            )
        )
        store.add(
            Span(
                span_id="span-2",
                trace_id="trace-001",
                name="op2",
                start_time=base_time + timedelta(hours=1),
            )
        )
        store.add(
            Span(
                span_id="span-3",
                trace_id="trace-001",
                name="op3",
                start_time=base_time + timedelta(hours=2),
            )
        )

        # Query for spans in first hour
        results = store.query(
            start_time=base_time,
            end_time=base_time + timedelta(minutes=30),
        )

        assert len(results) == 1
        assert results[0].span_id == "span-1"

    def test_trace_store_query_by_trace_id(self):
        """TraceStore can query spans by trace_id."""
        from dawn_kestrel.observability.trace import Span, TraceStore

        store = TraceStore()
        now = datetime.now()

        for i in range(3):
            store.add(
                Span(
                    span_id=f"span-{i}",
                    trace_id="trace-001",
                    name=f"op-{i}",
                    start_time=now,
                )
            )
        for i in range(3, 5):
            store.add(
                Span(
                    span_id=f"span-{i}",
                    trace_id="trace-002",
                    name=f"op-{i}",
                    start_time=now,
                )
            )

        trace1_spans = store.query(trace_id="trace-001")

        assert len(trace1_spans) == 3
        assert all(s.trace_id == "trace-001" for s in trace1_spans)

    def test_trace_store_size_limit(self):
        """TraceStore enforces size limit."""
        from dawn_kestrel.observability.trace import Span, TraceStore

        store = TraceStore(max_size=5)
        now = datetime.now()

        # Add more spans than the limit
        for i in range(10):
            store.add(
                Span(
                    span_id=f"span-{i}",
                    trace_id=f"trace-{i}",
                    name=f"op-{i}",
                    start_time=now + timedelta(seconds=i),
                )
            )

        # Should only have the most recent 5
        all_spans = store.get_all()
        assert len(all_spans) == 5
        # Should have spans 5-9 (most recent)
        span_ids = {s.span_id for s in all_spans}
        assert "span-5" in span_ids
        assert "span-9" in span_ids
        assert "span-0" not in span_ids

    def test_trace_store_default_no_limit(self):
        """TraceStore with max_size=0 has no limit."""
        from dawn_kestrel.observability.trace import Span, TraceStore

        store = TraceStore(max_size=0)
        now = datetime.now()

        # Add many spans
        for i in range(100):
            store.add(
                Span(
                    span_id=f"span-{i}",
                    trace_id=f"trace-{i}",
                    name=f"op-{i}",
                    start_time=now,
                )
            )

        assert len(store.get_all()) == 100

    def test_trace_store_clear(self):
        """TraceStore can be cleared."""
        from dawn_kestrel.observability.trace import Span, TraceStore

        store = TraceStore()
        now = datetime.now()

        store.add(
            Span(
                span_id="span-1",
                trace_id="trace-001",
                name="op1",
                start_time=now,
            )
        )

        store.clear()

        assert len(store.get_all()) == 0

    def test_trace_store_get_span_count(self):
        """TraceStore can report span count."""
        from dawn_kestrel.observability.trace import Span, TraceStore

        store = TraceStore()
        now = datetime.now()

        assert store.count == 0

        for i in range(5):
            store.add(
                Span(
                    span_id=f"span-{i}",
                    trace_id="trace-001",
                    name=f"op-{i}",
                    start_time=now,
                )
            )

        assert store.count == 5


class TestEventTraceFields:
    """Tests for Event extension with trace fields."""

    def test_event_has_trace_id_field(self):
        """Event can have trace_id field."""
        from dawn_kestrel.core.event_bus import Event

        event = Event(name="test.event", data={}, trace_id="trace-001")

        assert event.trace_id == "trace-001"

    def test_event_trace_id_defaults_to_none(self):
        """Event trace_id defaults to None."""
        from dawn_kestrel.core.event_bus import Event

        event = Event(name="test.event", data={})

        assert event.trace_id is None

    def test_event_has_parent_span_id_field(self):
        """Event can have parent_span_id field."""
        from dawn_kestrel.core.event_bus import Event

        event = Event(name="test.event", data={}, parent_span_id="span-001")

        assert event.parent_span_id == "span-001"

    def test_event_parent_span_id_defaults_to_none(self):
        """Event parent_span_id defaults to None."""
        from dawn_kestrel.core.event_bus import Event

        event = Event(name="test.event", data={})

        assert event.parent_span_id is None

    def test_event_has_duration_ms_field(self):
        """Event can have duration_ms field."""
        from dawn_kestrel.core.event_bus import Event

        event = Event(name="test.event", data={}, duration_ms=150.0)

        assert event.duration_ms == 150.0

    def test_event_duration_ms_defaults_to_none(self):
        """Event duration_ms defaults to None."""
        from dawn_kestrel.core.event_bus import Event

        event = Event(name="test.event", data={})

        assert event.duration_ms is None

    def test_event_has_span_name_field(self):
        """Event can have span_name field."""
        from dawn_kestrel.core.event_bus import Event

        event = Event(name="test.event", data={}, span_name="operation_name")

        assert event.span_name == "operation_name"

    def test_event_span_name_defaults_to_none(self):
        """Event span_name defaults to None."""
        from dawn_kestrel.core.event_bus import Event

        event = Event(name="test.event", data={})

        assert event.span_name is None

    def test_event_backwards_compatible(self):
        """Event with only existing fields still works."""
        from dawn_kestrel.core.event_bus import Event

        # Old-style usage should still work
        event = Event(name="test.event", data={"key": "value"})

        assert event.name == "test.event"
        assert event.data == {"key": "value"}
        assert event.trace_id is None
        assert event.parent_span_id is None
        assert event.duration_ms is None
        assert event.span_name is None


class TestSpanToDict:
    """Tests for Span serialization."""

    def test_span_to_dict(self):
        """Span can be serialized to dict."""
        from dawn_kestrel.observability.trace import Span

        now = datetime.now()
        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_operation",
            start_time=now,
            end_time=now + timedelta(milliseconds=100),
            parent_span_id="span-000",
            attributes={"key": "value"},
            session_id="session-001",
        )

        data = span.to_dict()

        assert data["span_id"] == "span-001"
        assert data["trace_id"] == "trace-001"
        assert data["name"] == "test_operation"
        assert data["parent_span_id"] == "span-000"
        assert data["duration_ms"] == 100.0
        assert data["attributes"] == {"key": "value"}
        assert data["session_id"] == "session-001"
        assert "start_time" in data
        assert "end_time" in data

    def test_span_to_dict_with_none_values(self):
        """Span to_dict handles None values correctly."""
        from dawn_kestrel.observability.trace import Span

        span = Span(
            span_id="span-001",
            trace_id="trace-001",
            name="test_operation",
            start_time=datetime.now(),
        )

        data = span.to_dict()

        assert data["parent_span_id"] is None
        assert data["end_time"] is None
        assert data["duration_ms"] is None
