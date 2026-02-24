"""OpenCode Python - Session Management"""

from dawn_kestrel.session.compaction import is_overflow, process, prune
from dawn_kestrel.session.processor import SessionProcessor
from dawn_kestrel.session.revert import SessionRevert
from dawn_kestrel.session.workspace import (
    Workspace,
    WorkspaceAllocator,
    WorkspaceLimitExceeded,
    WorkspaceNotFoundError,
)
from dawn_kestrel.snapshot import GitSnapshot

__all__ = [
    "SessionProcessor",
    "Workspace",
    "WorkspaceAllocator",
    "WorkspaceLimitExceeded",
    "WorkspaceNotFoundError",
    "is_overflow",
    "prune",
    "process",
    "SessionRevert",
    "GitSnapshot",
]
