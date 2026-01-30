"""Tests for destructive action confirmation dialogs"""
import pytest
from opencode_python.observability.models import (
    DestructiveAction,
)
from opencode_python.observability.safety import DestructiveActionGuard


@pytest.fixture
def safety_guard():
    """Create a destructive action guard for testing"""
    return DestructiveActionGuard()


@pytest.mark.asyncio
async def test_is_destructive_default_actions(safety_guard):
    """Test default destructive actions are recognized"""
    assert safety_guard.is_destructive(DestructiveAction.FORCE_PUSH) is True
    assert safety_guard.is_destructive(DestructiveAction.DELETE_BRANCH) is True
    assert safety_guard.is_destructive(DestructiveAction.DELETE_FILES) is True
    assert safety_guard.is_destructive(DestructiveAction.MASS_REFACTOR) is True
    assert safety_guard.is_destructive(DestructiveAction.RESET_HARD) is True
    assert safety_guard.is_destructive(DestructiveAction.REVERT_COMMIT) is True


@pytest.mark.asyncio
async def test_is_destructive_custom_actions(safety_guard):
    """Test custom destructive actions list"""
    safety_guard.remove_destructive_action(DestructiveAction.FORCE_PUSH)

    assert safety_guard.is_destructive(DestructiveAction.FORCE_PUSH) is False
    assert safety_guard.is_destructive(DestructiveAction.DELETE_BRANCH) is True


@pytest.mark.asyncio
async def test_get_description(safety_guard):
    """Test getting action descriptions"""
    desc = safety_guard.get_description(DestructiveAction.FORCE_PUSH)
    assert "overwrite remote history" in desc.lower()

    desc = safety_guard.get_description(DestructiveAction.DELETE_FILES)
    assert "cannot be easily undone" in desc.lower()


@pytest.mark.asyncio
async def test_request_confirmation(safety_guard):
    """Test requesting confirmation for destructive action"""
    callback_called = []
    async def mock_callback(approved):
        callback_called.append(approved)

    request = await safety_guard.request_confirmation(
        session_id="session-1",
        action=DestructiveAction.FORCE_PUSH,
        callback=mock_callback,
    )

    assert request.session_id == "session-1"
    assert request.action == DestructiveAction.FORCE_PUSH
    assert "overwrite remote history" in request.impact.lower()
    assert len(callback_called) == 0


@pytest.mark.asyncio
async def test_approve_request(safety_guard):
    """Test approving a destructive action request"""
    callback_called = []
    async def mock_callback(approved):
        callback_called.append(approved)

    request = await safety_guard.request_confirmation(
        session_id="session-1",
        action=DestructiveAction.DELETE_BRANCH,
        callback=mock_callback,
    )

    approved = await safety_guard.approve_request(request.id)

    assert approved is True
    assert len(callback_called) == 1
    assert callback_called[0] is True

    assert safety_guard.get_pending_request("session-1") is None


@pytest.mark.asyncio
async def test_deny_request(safety_guard):
    """Test denying a destructive action request"""
    callback_called = []
    async def mock_callback(approved):
        callback_called.append(approved)

    request = await safety_guard.request_confirmation(
        session_id="session-1",
        action=DestructiveAction.RESET_HARD,
        callback=mock_callback,
    )

    approved = await safety_guard.deny_request(request.id)

    assert approved is True
    assert len(callback_called) == 1
    assert callback_called[0] is False

    assert safety_guard.get_pending_request("session-1") is None


@pytest.mark.asyncio
async def test_get_pending_request(safety_guard):
    """Test getting pending request for a session"""
    request = await safety_guard.request_confirmation(
        session_id="session-1",
        action=DestructiveAction.MASS_REFACTOR,
    )

    pending = safety_guard.get_pending_request("session-1")

    assert pending is not None
    assert pending.id == request.id
    assert pending.action == DestructiveAction.MASS_REFACTOR


@pytest.mark.asyncio
async def test_get_pending_request_none(safety_guard):
    """Test getting pending request when none exists"""
    pending = safety_guard.get_pending_request("nonexistent")
    assert pending is None


@pytest.mark.asyncio
async def test_add_destructive_action(safety_guard):
    """Test adding a custom destructive action"""
    assert safety_guard.is_destructive(DestructiveAction.REVERT_COMMIT) is True

    safety_guard.remove_destructive_action(DestructiveAction.REVERT_COMMIT)
    assert safety_guard.is_destructive(DestructiveAction.REVERT_COMMIT) is False

    safety_guard.add_destructive_action(DestructiveAction.REVERT_COMMIT)
    assert safety_guard.is_destructive(DestructiveAction.REVERT_COMMIT) is True


@pytest.mark.asyncio
async def test_remove_destructive_action(safety_guard):
    """Test removing a destructive action"""
    assert safety_guard.is_destructive(DestructiveAction.FORCE_PUSH) is True

    safety_guard.remove_destructive_action(DestructiveAction.FORCE_PUSH)
    assert safety_guard.is_destructive(DestructiveAction.FORCE_PUSH) is False


@pytest.mark.asyncio
async def test_approve_nonexistent_request(safety_guard):
    """Test approving a nonexistent request returns False"""
    approved = await safety_guard.approve_request("nonexistent-id")
    assert approved is False


@pytest.mark.asyncio
async def test_deny_nonexistent_request(safety_guard):
    """Test denying a nonexistent request returns False"""
    approved = await safety_guard.deny_request("nonexistent-id")
    assert approved is False


def test_default_destructive_actions():
    """Test default destructive actions list"""
    guard = DestructiveActionGuard()

    expected_actions = [
        DestructiveAction.FORCE_PUSH,
        DestructiveAction.DELETE_BRANCH,
        DestructiveAction.DELETE_FILES,
        DestructiveAction.MASS_REFACTOR,
        DestructiveAction.RESET_HARD,
        DestructiveAction.REVERT_COMMIT,
    ]

    for action in expected_actions:
        assert guard.is_destructive(action) is True
