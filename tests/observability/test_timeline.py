"""Tests for timeline event labeling and session status tracking"""
import pytest
from opencode_python.observability.models import (
    EventType,
    EventLabel,
    SessionStatus,
)
from opencode_python.observability.timeline import TimelineManager


@pytest.fixture
def timeline_manager():
    """Create a timeline manager for testing"""
    return TimelineManager()


@pytest.mark.asyncio
async def test_add_plan_event(timeline_manager):
    """Test adding a plan event to timeline"""
    event = await timeline_manager.add_event(
        session_id="session-1",
        event_type=EventType.PLAN,
        details={"action": "create implementation plan"},
    )

    assert event.session_id == "session-1"
    assert event.event_type == EventType.PLAN
    assert event.label.label == "Plan"
    assert event.label.color == "blue"
    assert event.is_expandable is True
    assert "action" in event.details


@pytest.mark.asyncio
async def test_add_tool_event(timeline_manager):
    """Test adding a tool event to timeline"""
    event = await timeline_manager.add_event(
        session_id="session-1",
        event_type=EventType.TOOL,
        details={"tool": "bash", "command": "ls"},
    )

    assert event.event_type == EventType.TOOL
    assert event.label.label == "Tool"
    assert event.label.color == "yellow"
    assert event.is_expandable is True


@pytest.mark.asyncio
async def test_add_failure_event(timeline_manager):
    """Test adding a failure event and automatic session blocking"""
    event = await timeline_manager.add_event(
        session_id="session-1",
        event_type=EventType.FAILURE,
        error_details="API key not found",
    )

    assert event.event_type == EventType.FAILURE
    assert event.label.label == "Failure"
    assert event.label.color == "red"
    assert event.error_details == "API key not found"

    status = timeline_manager.get_session_status("session-1")
    assert status == SessionStatus.BLOCKED

    blocker = timeline_manager.get_blocker("session-1")
    assert blocker is not None
    assert "API key not found" in blocker.reason


@pytest.mark.asyncio
async def test_set_session_status(timeline_manager):
    """Test setting session status"""
    await timeline_manager.set_session_status(
        session_id="session-1",
        status=SessionStatus.ACTIVE,
    )

    status = timeline_manager.get_session_status("session-1")
    assert status == SessionStatus.ACTIVE


@pytest.mark.asyncio
async def test_set_blocked_status_with_reason(timeline_manager):
    """Test setting session to blocked with reason and next steps"""
    await timeline_manager.set_session_status(
        session_id="session-1",
        status=SessionStatus.BLOCKED,
        reason="Missing credentials",
        next_steps=["Add API key", "Retry operation"],
    )

    status = timeline_manager.get_session_status("session-1")
    assert status == SessionStatus.BLOCKED

    blocker = timeline_manager.get_blocker("session-1")
    assert blocker.reason == "Missing credentials"
    assert len(blocker.next_steps) == 2


@pytest.mark.asyncio
async def test_resolve_blocker(timeline_manager):
    """Test resolving a blocked session"""
    await timeline_manager.set_session_status(
        session_id="session-1",
        status=SessionStatus.BLOCKED,
        reason="Error",
    )

    await timeline_manager.resolve_blocker("session-1")

    status = timeline_manager.get_session_status("session-1")
    assert status == SessionStatus.ACTIVE

    blocker = timeline_manager.get_blocker("session-1")
    assert blocker.is_resolved is True


@pytest.mark.asyncio
async def test_get_events(timeline_manager):
    """Test retrieving timeline events for a session"""
    await timeline_manager.add_event("session-1", EventType.PLAN)
    await timeline_manager.add_event("session-1", EventType.CODE)
    await timeline_manager.add_event("session-2", EventType.TOOL)

    events_1 = timeline_manager.get_events("session-1")
    events_2 = timeline_manager.get_events("session-2")

    assert len(events_1) == 2
    assert len(events_2) == 1
    assert events_1[0].event_type == EventType.PLAN
    assert events_1[1].event_type == EventType.CODE


@pytest.mark.asyncio
async def test_default_session_status(timeline_manager):
    """Test default session status is DRAFT"""
    status = timeline_manager.get_session_status("nonexistent")
    assert status == SessionStatus.DRAFT


@pytest.mark.asyncio
async def test_get_blocker_for_non_blocked_session(timeline_manager):
    """Test getting blocker for non-blocked session returns None"""
    await timeline_manager.set_session_status("session-1", SessionStatus.ACTIVE)

    blocker = timeline_manager.get_blocker("session-1")
    assert blocker is None


def test_event_label_for_type():
    """Test EventLabel.for_type returns correct labels"""
    plan_label = EventLabel.for_type(EventType.PLAN)
    assert plan_label.label == "Plan"
    assert plan_label.color == "blue"
    assert plan_label.icon == "📋"

    failure_label = EventLabel.for_type(EventType.FAILURE)
    assert failure_label.label == "Failure"
    assert failure_label.color == "red"
    assert failure_label.icon == "❌"

    code_label = EventLabel.for_type(EventType.CODE)
    assert code_label.label == "Code"
    assert code_label.color == "green"
    assert code_label.icon == "💻"
