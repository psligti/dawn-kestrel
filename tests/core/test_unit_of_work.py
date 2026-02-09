"""Unit tests for Unit of Work pattern.

Tests cover transaction lifecycle, entity registration, commit/rollback behavior,
and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from dawn_kestrel.core.models import Session, Message, TextPart
from dawn_kestrel.core.result import Ok, Err
from dawn_kestrel.core.unit_of_work import UnitOfWork, UnitOfWorkImpl


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_session_repo():
    """Mock SessionRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=Ok(MagicMock()))
    return repo


@pytest.fixture
def mock_message_repo():
    """Mock MessageRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=Ok(MagicMock()))
    return repo


@pytest.fixture
def mock_part_repo():
    """Mock PartRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=Ok(MagicMock()))
    return repo


@pytest.fixture
def uow(mock_session_repo, mock_message_repo, mock_part_repo):
    """UnitOfWork instance with mocked repositories."""
    return UnitOfWorkImpl(mock_session_repo, mock_message_repo, mock_part_repo)


@pytest.fixture
def sample_session():
    """Sample session for testing."""
    return Session(
        id="test_session",
        slug="test",
        project_id="test_project",
        directory="/tmp/test",
        title="Test Session",
        version="1.0.0",
    )


@pytest.fixture
def sample_message():
    """Sample message for testing."""
    return Message(
        id="test_message",
        session_id="test_session",
        role="user",
        text="Hello, World!",
    )


@pytest.fixture
def sample_part():
    """Sample text part for testing."""
    return TextPart(
        id="test_part",
        session_id="test_session",
        message_id="test_message",
        part_type="text",
        text="Sample text content",
    )


# ============================================================================
# Transaction Lifecycle Tests
# ============================================================================


@pytest.mark.asyncio
async def test_begin_returns_ok_starts_transaction(uow):
    """begin() returns Ok and sets transaction state."""
    result = await uow.begin()
    assert result.is_ok()
    assert uow._in_transaction is True


@pytest.mark.asyncio
async def test_begin_returns_err_when_transaction_in_progress(uow):
    """begin() returns Err when transaction already in progress."""
    await uow.begin()
    result = await uow.begin()
    assert result.is_err()
    assert "already in progress" in result.error.lower()


@pytest.mark.asyncio
async def test_commit_returns_ok_when_transaction_in_progress(uow, sample_session):
    """commit() returns Ok when transaction is active."""
    await uow.begin()
    result = await uow.commit()
    assert result.is_ok()


@pytest.mark.asyncio
async def test_commit_returns_err_when_no_transaction(uow):
    """commit() returns Err when no transaction is in progress."""
    result = await uow.commit()
    assert result.is_err()
    assert "no transaction" in result.error.lower()


@pytest.mark.asyncio
async def test_rollback_returns_ok_when_transaction_in_progress(uow, sample_session):
    """rollback() returns Ok when transaction is active."""
    await uow.begin()
    result = await uow.rollback()
    assert result.is_ok()


@pytest.mark.asyncio
async def test_rollback_returns_err_when_no_transaction(uow):
    """rollback() returns Err when no transaction is in progress."""
    result = await uow.rollback()
    assert result.is_err()
    assert "no transaction" in result.error.lower()


@pytest.mark.asyncio
async def test_commit_clears_pending_state(uow, sample_session, sample_message):
    """commit() clears pending state after successful commit."""
    await uow.begin()
    await uow.register_session(sample_session)
    await uow.register_message(sample_message)
    await uow.commit()
    assert len(uow._pending_sessions) == 0
    assert len(uow._pending_messages) == 0
    assert uow._in_transaction is False


@pytest.mark.asyncio
async def test_rollback_clears_pending_state(uow, sample_session, sample_message):
    """rollback() clears pending state after rollback."""
    await uow.begin()
    await uow.register_session(sample_session)
    await uow.register_message(sample_message)
    await uow.rollback()
    assert len(uow._pending_sessions) == 0
    assert len(uow._pending_messages) == 0
    assert uow._in_transaction is False


# ============================================================================
# Entity Registration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_register_session_returns_ok_adds_to_pending(uow, sample_session):
    """register_session() returns Ok and adds to pending list."""
    await uow.begin()
    result = await uow.register_session(sample_session)
    assert result.is_ok()
    assert result.unwrap() is sample_session
    assert len(uow._pending_sessions) == 1
    assert uow._pending_sessions[0] is sample_session


@pytest.mark.asyncio
async def test_register_session_returns_err_when_no_transaction(uow, sample_session):
    """register_session() returns Err when no transaction is in progress."""
    result = await uow.register_session(sample_session)
    assert result.is_err()
    assert "no transaction" in result.error.lower()
    assert len(uow._pending_sessions) == 0


@pytest.mark.asyncio
async def test_register_message_returns_ok_adds_to_pending(uow, sample_message):
    """register_message() returns Ok and adds to pending list."""
    await uow.begin()
    result = await uow.register_message(sample_message)
    assert result.is_ok()
    assert result.unwrap() is sample_message
    assert len(uow._pending_messages) == 1
    assert uow._pending_messages[0] is sample_message


@pytest.mark.asyncio
async def test_register_message_returns_err_when_no_transaction(uow, sample_message):
    """register_message() returns Err when no transaction is in progress."""
    result = await uow.register_message(sample_message)
    assert result.is_err()
    assert "no transaction" in result.error.lower()
    assert len(uow._pending_messages) == 0


@pytest.mark.asyncio
async def test_register_part_returns_ok_adds_to_pending(uow, sample_part):
    """register_part() returns Ok and adds to pending list."""
    await uow.begin()
    result = await uow.register_part("test_message", sample_part)
    assert result.is_ok()
    assert result.unwrap() is sample_part
    assert len(uow._pending_parts) == 1
    assert uow._pending_parts[0] == ("test_message", sample_part)


@pytest.mark.asyncio
async def test_register_part_returns_err_when_no_transaction(uow, sample_part):
    """register_part() returns Err when no transaction is in progress."""
    result = await uow.register_part("test_message", sample_part)
    assert result.is_err()
    assert "no transaction" in result.error.lower()
    assert len(uow._pending_parts) == 0


# ============================================================================
# Commit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_commit_creates_all_registered_sessions(uow, mock_session_repo, sample_session):
    """commit() creates all registered sessions through repository."""
    await uow.begin()
    await uow.register_session(sample_session)
    await uow.commit()
    mock_session_repo.create.assert_called_once_with(sample_session)


@pytest.mark.asyncio
async def test_commit_creates_all_registered_messages(uow, mock_message_repo, sample_message):
    """commit() creates all registered messages through repository."""
    await uow.begin()
    await uow.register_message(sample_message)
    await uow.commit()
    mock_message_repo.create.assert_called_once_with(sample_message)


@pytest.mark.asyncio
async def test_commit_creates_all_registered_parts(uow, mock_part_repo, sample_part):
    """commit() creates all registered parts through repository."""
    await uow.begin()
    await uow.register_part("test_message", sample_part)
    await uow.commit()
    mock_part_repo.create.assert_called_once_with("test_message", sample_part)


@pytest.mark.asyncio
async def test_commit_returns_err_if_session_create_fails(uow, mock_session_repo, sample_session):
    """commit() returns Err when session repository create fails."""
    mock_session_repo.create = AsyncMock(return_value=Err("Storage error", code="STORAGE_ERROR"))
    await uow.begin()
    await uow.register_session(sample_session)
    result = await uow.commit()
    assert result.is_err()
    assert "storage error" in result.error.lower()


@pytest.mark.asyncio
async def test_commit_returns_err_if_message_create_fails(
    uow, mock_message_repo, sample_session, sample_message
):
    """commit() returns Err when message repository create fails."""
    mock_message_repo.create = AsyncMock(return_value=Err("Storage error", code="STORAGE_ERROR"))
    await uow.begin()
    await uow.register_session(sample_session)
    await uow.register_message(sample_message)
    result = await uow.commit()
    assert result.is_err()
    assert "storage error" in result.error.lower()


@pytest.mark.asyncio
async def test_commit_returns_err_if_part_create_fails(
    uow, mock_part_repo, sample_session, sample_part
):
    """commit() returns Err when part repository create fails."""
    mock_part_repo.create = AsyncMock(return_value=Err("Storage error", code="STORAGE_ERROR"))
    await uow.begin()
    await uow.register_session(sample_session)
    await uow.register_part("test_message", sample_part)
    result = await uow.commit()
    assert result.is_err()
    assert "storage error" in result.error.lower()


# ============================================================================
# Rollback Tests
# ============================================================================


@pytest.mark.asyncio
async def test_rollback_clears_pending_without_creating(
    uow,
    mock_session_repo,
    mock_message_repo,
    mock_part_repo,
    sample_session,
    sample_message,
    sample_part,
):
    """rollback() clears pending state without calling repositories."""
    await uow.begin()
    await uow.register_session(sample_session)
    await uow.register_message(sample_message)
    await uow.register_part("test_message", sample_part)
    await uow.rollback()
    assert len(uow._pending_sessions) == 0
    assert len(uow._pending_messages) == 0
    assert len(uow._pending_parts) == 0
    # Verify repositories were not called
    mock_session_repo.create.assert_not_called()
    mock_message_repo.create.assert_not_called()
    mock_part_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_rollback_does_not_modify_repositories(
    uow, mock_session_repo, mock_message_repo, mock_part_repo
):
    """rollback() does not modify any repository state."""
    await uow.begin()
    await uow.rollback()
    # Verify repositories were not called
    mock_session_repo.create.assert_not_called()
    mock_message_repo.create.assert_not_called()
    mock_part_repo.create.assert_not_called()


# ============================================================================
# Protocol Tests
# ============================================================================


def test_unitofwork_is_protocol():
    """UnitOfWork is a runtime-checkable protocol."""
    assert isinstance(UnitOfWork, type)


@pytest.mark.asyncio
async def test_unitofwork_impl_implements_protocol(uow):
    """UnitOfWorkImpl implements UnitOfWork protocol."""
    assert isinstance(uow, UnitOfWork)


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_transaction_flow_success(
    uow,
    mock_session_repo,
    mock_message_repo,
    mock_part_repo,
    sample_session,
    sample_message,
    sample_part,
):
    """Full transaction flow: begin, register, commit succeeds."""
    await uow.begin()
    await uow.register_session(sample_session)
    await uow.register_message(sample_message)
    await uow.register_part("test_message", sample_part)
    result = await uow.commit()
    assert result.is_ok()
    assert uow._in_transaction is False
    # Verify all repositories were called
    mock_session_repo.create.assert_called_once_with(sample_session)
    mock_message_repo.create.assert_called_once_with(sample_message)
    mock_part_repo.create.assert_called_once_with("test_message", sample_part)


@pytest.mark.asyncio
async def test_full_transaction_flow_with_rollback(
    uow,
    mock_session_repo,
    mock_message_repo,
    mock_part_repo,
    sample_session,
    sample_message,
    sample_part,
):
    """Full transaction flow: begin, register, rollback."""
    await uow.begin()
    await uow.register_session(sample_session)
    await uow.register_message(sample_message)
    await uow.register_part("test_message", sample_part)
    result = await uow.rollback()
    assert result.is_ok()
    assert uow._in_transaction is False
    # Verify repositories were not called
    mock_session_repo.create.assert_not_called()
    mock_message_repo.create.assert_not_called()
    mock_part_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_sessions_in_transaction(uow, mock_session_repo, sample_session):
    """Multiple sessions can be registered and committed in one transaction."""
    await uow.begin()
    session2 = Session(
        id="test_session_2",
        slug="test2",
        project_id="test_project",
        directory="/tmp/test2",
        title="Test Session 2",
        version="1.0.0",
    )
    await uow.register_session(sample_session)
    await uow.register_session(session2)
    await uow.commit()
    assert mock_session_repo.create.call_count == 2


@pytest.mark.asyncio
async def test_multiple_messages_in_transaction(uow, mock_message_repo, sample_message):
    """Multiple messages can be registered and committed in one transaction."""
    await uow.begin()
    message2 = Message(
        id="test_message_2",
        session_id="test_session",
        role="assistant",
        text="Response",
    )
    await uow.register_message(sample_message)
    await uow.register_message(message2)
    await uow.commit()
    assert mock_message_repo.create.call_count == 2
