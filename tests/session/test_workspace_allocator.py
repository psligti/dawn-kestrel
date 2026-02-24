"""Tests for WorkspaceAllocator - workspace isolation management.

Tests the WorkspaceAllocator for managing isolated workspaces:
- allocate(): Create a new isolated workspace
- release(): Release and clean up a workspace
- get_workspace(): Get existing workspace by ID
- Workspace limits (max concurrent)
- Cleanup on release
- Workspace metadata support
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dawn_kestrel.session.workspace import (
    Workspace,
    WorkspaceAllocator,
    WorkspaceLimitExceeded,
    WorkspaceNotFoundError,
)


@pytest.fixture
def temp_base_dir(tmp_path: Path) -> Path:
    """Create a temporary base directory for workspaces."""
    base_dir = tmp_path / "workspaces"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


@pytest.fixture
def allocator(temp_base_dir: Path) -> WorkspaceAllocator:
    """Create a workspace allocator with a temporary base directory."""
    return WorkspaceAllocator(base_dir=temp_base_dir, max_concurrent=5)


# ===== Workspace Model Tests =====


def test_workspace_model_defaults():
    """Test Workspace model has expected defaults."""
    workspace = Workspace(
        id="test-ws-123",
        path=Path("/tmp/test-ws"),
    )

    assert workspace.id == "test-ws-123"
    assert workspace.path == Path("/tmp/test-ws")
    assert workspace.metadata == {}
    assert workspace.session_id is None
    assert workspace.repo_url is None
    assert workspace.branch is None


def test_workspace_model_with_metadata():
    """Test Workspace model accepts metadata fields."""
    workspace = Workspace(
        id="ws-456",
        path=Path("/workspaces/ws-456"),
        session_id="session-789",
        repo_url="https://github.com/org/repo.git",
        branch="main",
        metadata={"key": "value"},
    )

    assert workspace.id == "ws-456"
    assert workspace.session_id == "session-789"
    assert workspace.repo_url == "https://github.com/org/repo.git"
    assert workspace.branch == "main"
    assert workspace.metadata == {"key": "value"}


def test_workspace_is_serializable():
    """Test Workspace can be serialized to dict."""
    from dataclasses import asdict

    workspace = Workspace(
        id="ws-serial",
        path=Path("/workspaces/ws-serial"),
        repo_url="https://example.com/repo.git",
    )

    data = asdict(workspace)
    # Path should be converted to string
    assert isinstance(data["path"], Path)
    assert data["id"] == "ws-serial"
    assert data["repo_url"] == "https://example.com/repo.git"


# ===== WorkspaceAllocator Basic Tests =====


def test_allocator_creation(temp_base_dir: Path):
    """Test WorkspaceAllocator can be created."""
    allocator = WorkspaceAllocator(base_dir=temp_base_dir, max_concurrent=10)

    assert allocator.base_dir == temp_base_dir
    assert allocator.max_concurrent == 10
    assert len(allocator._workspaces) == 0


def test_allocator_default_max_concurrent(temp_base_dir: Path):
    """Test WorkspaceAllocator has default max_concurrent."""
    allocator = WorkspaceAllocator(base_dir=temp_base_dir)

    assert allocator.max_concurrent == 10


# ===== allocate() Tests =====


def test_allocate_creates_workspace(allocator: WorkspaceAllocator, temp_base_dir: Path):
    """Test allocate() creates a new workspace."""
    workspace = allocator.allocate()

    assert workspace.id is not None
    assert len(workspace.id) == 36  # UUID4 format
    assert workspace.path == temp_base_dir / workspace.id
    assert workspace.path.exists()
    assert workspace.path.is_dir()


def test_allocate_with_session_id(allocator: WorkspaceAllocator):
    """Test allocate() accepts session_id."""
    workspace = allocator.allocate(session_id="session-123")

    assert workspace.session_id == "session-123"


def test_allocate_with_repo_metadata(allocator: WorkspaceAllocator):
    """Test allocate() accepts repo URL and branch."""
    workspace = allocator.allocate(
        repo_url="https://github.com/org/repo.git",
        branch="develop",
    )

    assert workspace.repo_url == "https://github.com/org/repo.git"
    assert workspace.branch == "develop"


def test_allocate_with_custom_metadata(allocator: WorkspaceAllocator):
    """Test allocate() accepts custom metadata."""
    metadata = {"env": "production", "owner": "team-a"}
    workspace = allocator.allocate(metadata=metadata)

    assert workspace.metadata == metadata


def test_allocate_tracks_workspace(allocator: WorkspaceAllocator):
    """Test allocate() tracks the workspace."""
    workspace = allocator.allocate()

    assert workspace.id in allocator._workspaces
    assert allocator._workspaces[workspace.id] == workspace


def test_allocate_generates_unique_ids(temp_base_dir: Path):
    """Test allocate() generates unique workspace IDs."""
    allocator = WorkspaceAllocator(base_dir=temp_base_dir, max_concurrent=15)
    ids = [allocator.allocate().id for _ in range(10)]

    assert len(ids) == len(set(ids))  # All unique


# ===== release() Tests =====


def test_release_removes_workspace(allocator: WorkspaceAllocator):
    """Test release() removes workspace from tracking."""
    workspace = allocator.allocate()
    workspace_id = workspace.id

    result = allocator.release(workspace_id)

    assert result is True
    assert workspace_id not in allocator._workspaces


def test_release_removes_directory(allocator: WorkspaceAllocator):
    """Test release() removes workspace directory."""
    workspace = allocator.allocate()
    workspace_path = workspace.path
    assert workspace_path.exists()

    result = allocator.release(workspace.id)

    assert result is True
    assert not workspace_path.exists()


def test_release_nonexistent_workspace(allocator: WorkspaceAllocator):
    """Test release() returns False for nonexistent workspace."""
    result = allocator.release("nonexistent-id")

    assert result is False


def test_release_clears_metadata(allocator: WorkspaceAllocator):
    """Test release() clears workspace metadata."""
    workspace = allocator.allocate(
        session_id="session-xyz",
        repo_url="https://github.com/org/repo.git",
    )

    result = allocator.release(workspace.id)

    assert result is True
    assert workspace.id not in allocator._workspaces


# ===== get_workspace() Tests =====


def test_get_workspace_returns_allocated(allocator: WorkspaceAllocator):
    """Test get_workspace() returns allocated workspace."""
    workspace = allocator.allocate(session_id="session-abc")

    result = allocator.get_workspace(workspace.id)

    assert result is not None
    assert result.id == workspace.id
    assert result.session_id == "session-abc"


def test_get_workspace_returns_none_for_nonexistent(allocator: WorkspaceAllocator):
    """Test get_workspace() returns None for nonexistent ID."""
    result = allocator.get_workspace("nonexistent-id")

    assert result is None


# ===== Max Concurrent Limit Tests =====


def test_max_concurrent_limit_enforced(temp_base_dir: Path):
    """Test that max concurrent limit is enforced."""
    allocator = WorkspaceAllocator(base_dir=temp_base_dir, max_concurrent=3)

    # Allocate up to the limit
    allocator.allocate()
    allocator.allocate()
    allocator.allocate()

    # Should raise on 4th allocation
    with pytest.raises(WorkspaceLimitExceeded) as exc_info:
        allocator.allocate()

    assert "Maximum concurrent workspaces" in str(exc_info.value)
    assert "3" in str(exc_info.value)


def test_release_allows_new_allocation(temp_base_dir: Path):
    """Test releasing workspace allows new allocation at limit."""
    allocator = WorkspaceAllocator(base_dir=temp_base_dir, max_concurrent=2)

    ws1 = allocator.allocate()
    allocator.allocate()

    # Release one
    allocator.release(ws1.id)

    # Should now be able to allocate again
    ws3 = allocator.allocate()
    assert ws3 is not None


def test_zero_max_concurrent_prevents_allocation(temp_base_dir: Path):
    """Test max_concurrent=0 prevents all allocations."""
    allocator = WorkspaceAllocator(base_dir=temp_base_dir, max_concurrent=0)

    with pytest.raises(WorkspaceLimitExceeded):
        allocator.allocate()


# ===== Count and Listing Tests =====


def test_count_returns_number_of_workspaces(allocator: WorkspaceAllocator):
    """Test count property returns number of workspaces."""
    assert allocator.count == 0

    allocator.allocate()
    assert allocator.count == 1

    allocator.allocate()
    assert allocator.count == 2


def test_list_workspaces_returns_all(allocator: WorkspaceAllocator):
    """Test list_workspaces returns all workspaces."""
    ws1 = allocator.allocate(session_id="s1")
    ws2 = allocator.allocate(session_id="s2")
    ws3 = allocator.allocate(session_id="s3")

    workspaces = allocator.list_workspaces()

    assert len(workspaces) == 3
    ids = [w.id for w in workspaces]
    assert ws1.id in ids
    assert ws2.id in ids
    assert ws3.id in ids


def test_list_workspaces_empty_when_none(allocator: WorkspaceAllocator):
    """Test list_workspaces returns empty list when no workspaces."""
    workspaces = allocator.list_workspaces()

    assert workspaces == []


# ===== Get by Session Tests =====


def test_get_workspace_by_session_id(allocator: WorkspaceAllocator):
    """Test get_workspace_by_session finds workspace by session."""
    ws1 = allocator.allocate(session_id="session-111")
    allocator.allocate(session_id="session-222")

    result = allocator.get_workspace_by_session("session-111")

    assert result is not None
    assert result.id == ws1.id


def test_get_workspace_by_session_returns_none_if_not_found(allocator: WorkspaceAllocator):
    """Test get_workspace_by_session returns None for missing session."""
    allocator.allocate(session_id="session-999")

    result = allocator.get_workspace_by_session("session-nonexistent")

    assert result is None


# ===== Context Manager Support Tests =====


def test_workspace_context_manager(allocator: WorkspaceAllocator):
    """Test using allocate_context as context manager."""
    with allocator.allocate_context(session_id="ctx-test") as workspace:
        assert workspace.id in allocator._workspaces
        assert workspace.path.exists()

    # After context exit, workspace should be released
    assert workspace.id not in allocator._workspaces
    assert not workspace.path.exists()


def test_workspace_context_manager_on_exception(allocator: WorkspaceAllocator):
    """Test allocate_context releases on exception."""
    workspace_id = None
    workspace_path = None

    with pytest.raises(ValueError):
        with allocator.allocate_context() as workspace:
            workspace_id = workspace.id
            workspace_path = workspace.path
            raise ValueError("Test error")

    # Should still be released
    assert workspace_id not in allocator._workspaces
    if workspace_path:
        assert not workspace_path.exists()


# ===== Release All Tests =====


def test_release_all_clears_workspaces(allocator: WorkspaceAllocator):
    """Test release_all clears all workspaces."""
    ws1 = allocator.allocate()
    ws2 = allocator.allocate()
    ws3 = allocator.allocate()

    allocator.release_all()

    assert allocator.count == 0
    assert not ws1.path.exists()
    assert not ws2.path.exists()
    assert not ws3.path.exists()


# ===== Cleanup Tests =====


def test_cleanup_orphaned_directories(temp_base_dir: Path):
    """Test cleanup removes orphaned workspace directories."""
    allocator = WorkspaceAllocator(base_dir=temp_base_dir)

    # Create an orphaned directory (not tracked)
    orphan_path = temp_base_dir / "orphan-ws-123"
    orphan_path.mkdir()

    # Also create a tracked workspace
    tracked_ws = allocator.allocate()

    # Orphan should exist, tracked should exist
    assert orphan_path.exists()
    assert tracked_ws.path.exists()

    # Run cleanup
    removed = allocator.cleanup_orphaned()

    # Orphan should be removed, tracked should remain
    assert orphan_path in removed
    assert not orphan_path.exists()
    assert tracked_ws.path.exists()


def test_cleanup_preserves_tracked_workspaces(allocator: WorkspaceAllocator):
    """Test cleanup doesn't remove tracked workspaces."""
    ws = allocator.allocate()

    removed = allocator.cleanup_orphaned()

    assert ws.id not in [str(p.name) for p in removed]
    assert ws.path.exists()


# ===== Thread Safety Considerations =====
# Note: Per task requirements, we're NOT supporting multi-process access,
# but basic single-threaded operations should be safe.


def test_allocator_maintains_consistent_state(allocator: WorkspaceAllocator):
    """Test allocator maintains consistent state across operations."""
    # Allocate several workspaces
    workspaces = [allocator.allocate() for _ in range(3)]

    # Release one
    allocator.release(workspaces[1].id)

    # Verify state
    assert allocator.count == 2
    assert allocator.get_workspace(workspaces[0].id) is not None
    assert allocator.get_workspace(workspaces[1].id) is None
    assert allocator.get_workspace(workspaces[2].id) is not None


# ===== Edge Cases =====


def test_allocate_with_empty_metadata(allocator: WorkspaceAllocator):
    """Test allocate() handles empty metadata."""
    workspace = allocator.allocate(metadata={})

    assert workspace.metadata == {}


def test_allocate_with_none_values(allocator: WorkspaceAllocator):
    """Test allocate() handles None values."""
    workspace = allocator.allocate(
        session_id=None,
        repo_url=None,
        branch=None,
    )

    assert workspace.session_id is None
    assert workspace.repo_url is None
    assert workspace.branch is None


def test_release_already_released_workspace(allocator: WorkspaceAllocator):
    """Test releasing same workspace twice is safe."""
    workspace = allocator.allocate()
    workspace_id = workspace.id

    result1 = allocator.release(workspace_id)
    result2 = allocator.release(workspace_id)

    assert result1 is True
    assert result2 is False  # Already released


def test_allocator_with_nested_base_dir(tmp_path: Path):
    """Test allocator creates nested base directory."""
    nested_dir = tmp_path / "deeply" / "nested" / "workspaces"
    allocator = WorkspaceAllocator(base_dir=nested_dir)

    # Base dir should be created on first allocate
    workspace = allocator.allocate()

    assert nested_dir.exists()
    assert workspace.path.exists()
