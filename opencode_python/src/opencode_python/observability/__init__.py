"""OpenCode Python - Observability & Safety Package

This package provides:
- Timeline event labeling for session tracking
- Session status tracking (Active, Blocked, Completed)
- Destructive action safeguards with confirmation dialogs
- Dry-run mode for safe preview of changes
"""
from __future__ import annotations

from opencode_python.observability.models import (
    TimelineEvent,
    EventType,
    EventLabel,
    SessionStatus,
    Blocker,
    DestructiveAction,
    DestructiveActionRequest,
)
from opencode_python.observability.timeline import TimelineManager, timeline_manager
from opencode_python.observability.safety import DestructiveActionGuard, destructive_guard
from opencode_python.observability.dryrun import DryRunManager, dryrun_manager

__all__ = [
    "TimelineEvent",
    "EventType",
    "EventLabel",
    "SessionStatus",
    "Blocker",
    "DestructiveAction",
    "DestructiveActionRequest",
    "TimelineManager",
    "timeline_manager",
    "DestructiveActionGuard",
    "destructive_guard",
    "DryRunManager",
    "dryrun_manager",
]
