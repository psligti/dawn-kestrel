"""Workspace isolation management for multi-session and multi-repo support."""

from __future__ import annotations

import shutil
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


class WorkspaceLimitExceeded(Exception):
    """Raised when attempting to allocate more than max_concurrent workspaces."""

    pass


class WorkspaceNotFoundError(Exception):
    """Raised when a workspace cannot be found."""

    pass


@dataclass
class Workspace:
    """Represents an isolated workspace directory."""

    id: str
    path: Path
    session_id: str | None = None
    repo_url: str | None = None
    branch: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict[str, Any])

    def __enter__(self) -> "Workspace":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        del exc_type, exc_val, exc_tb


class WorkspaceAllocator:
    """Manages isolated workspace directories for sessions and repositories.

    Provides workspace isolation, allocation limits, and cleanup.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        max_concurrent: int = 10,
    ):
        if base_dir is None:
            from dawn_kestrel.core.settings import get_cache_dir

            base_dir = get_cache_dir() / "workspaces"

        self.base_dir = Path(base_dir)
        self.max_concurrent = max_concurrent
        self._workspaces: dict[str, Workspace] = {}

    def allocate(
        self,
        session_id: str | None = None,
        repo_url: str | None = None,
        branch: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Workspace:
        """Allocate a new isolated workspace.

        Args:
            session_id: Optional session identifier for tracking.
            repo_url: Optional repository URL this workspace is for.
            branch: Optional git branch name.
            metadata: Optional additional metadata.

        Returns:
            The allocated Workspace instance.

        Raises:
            WorkspaceLimitExceeded: If max_concurrent workspaces already allocated.
        """
        if len(self._workspaces) >= self.max_concurrent:
            raise WorkspaceLimitExceeded(
                f"Maximum concurrent workspaces ({self.max_concurrent}) reached. "
                "Release a workspace before allocating a new one."
            )

        workspace_id = str(uuid.uuid4())
        workspace_path = self.base_dir / workspace_id

        workspace_path.mkdir(parents=True, exist_ok=True)

        workspace = Workspace(
            id=workspace_id,
            path=workspace_path,
            session_id=session_id,
            repo_url=repo_url,
            branch=branch,
            metadata=metadata or {},
        )

        self._workspaces[workspace_id] = workspace
        return workspace

    def release(self, workspace_id: str) -> bool:
        """Release a workspace and clean up its directory.

        Args:
            workspace_id: The ID of the workspace to release.

        Returns:
            True if workspace was released, False if not found.
        """
        workspace = self._workspaces.pop(workspace_id, None)
        if workspace is None:
            return False

        if workspace.path.exists():
            shutil.rmtree(workspace.path, ignore_errors=True)

        return True

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        """Get a workspace by its ID.

        Args:
            workspace_id: The workspace ID to look up.

        Returns:
            The Workspace if found, None otherwise.
        """
        return self._workspaces.get(workspace_id)

    def get_workspace_by_session(self, session_id: str) -> Workspace | None:
        """Find a workspace by its associated session ID.

        Args:
            session_id: The session ID to search for.

        Returns:
            The Workspace if found, None otherwise.
        """
        for workspace in self._workspaces.values():
            if workspace.session_id == session_id:
                return workspace
        return None

    def list_workspaces(self) -> list[Workspace]:
        """List all currently allocated workspaces.

        Returns:
            List of all allocated Workspace instances.
        """
        return list(self._workspaces.values())

    @property
    def count(self) -> int:
        """Return the number of currently allocated workspaces."""
        return len(self._workspaces)

    def release_all(self) -> None:
        """Release all workspaces and clean up their directories."""
        workspace_ids = list(self._workspaces.keys())
        for workspace_id in workspace_ids:
            self.release(workspace_id)

    def cleanup_orphaned(self) -> list[Path]:
        """Remove workspace directories that exist on disk but aren't tracked.

        This can happen if the allocator crashed or was recreated.

        Returns:
            List of paths that were removed.
        """
        removed: list[Path] = []

        if not self.base_dir.exists():
            return removed

        tracked_ids = set(self._workspaces.keys())

        for path in self.base_dir.iterdir():
            if path.is_dir() and path.name not in tracked_ids:
                shutil.rmtree(path, ignore_errors=True)
                removed.append(path)

        return removed

    @contextmanager
    def allocate_context(
        self,
        session_id: str | None = None,
        repo_url: str | None = None,
        branch: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[Workspace]:
        """Context manager for allocating and automatically releasing a workspace.

        Args:
            session_id: Optional session identifier.
            repo_url: Optional repository URL.
            branch: Optional git branch.
            metadata: Optional metadata.

        Yields:
            The allocated Workspace.
        """
        workspace = self.allocate(
            session_id=session_id,
            repo_url=repo_url,
            branch=branch,
            metadata=metadata,
        )
        try:
            yield workspace
        finally:
            self.release(workspace.id)
