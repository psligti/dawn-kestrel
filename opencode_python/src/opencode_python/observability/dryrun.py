"""OpenCode Python - Dry-run mode for safe preview

Provides diff/patch preview without modifying files when dry-run is enabled.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Any
import logging
import asyncio
from difflib import unified_diff
from pathlib import Path

from opencode_python.core.event_bus import bus

logger = logging.getLogger(__name__)


class DryRunManager:
    """Manager for dry-run mode with diff/patch preview"""

    def __init__(self, enabled: bool = False):
        """Initialize dry-run manager

        Args:
            enabled: Whether dry-run mode is enabled
        """
        self._enabled = enabled
        self._dry_runs: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        """Check if dry-run mode is enabled

        Returns:
            True if dry-run is active
        """
        return self._enabled

    async def toggle(self, enabled: Optional[bool] = None) -> bool:
        """Toggle dry-run mode

        Args:
            enabled: New state (None toggles current state)

        Returns:
            New enabled state
        """
        async with self._lock:
            if enabled is None:
                self._enabled = not self._enabled
            else:
                self._enabled = enabled

            await bus.publish(
                "dryrun:toggle",
                {"enabled": self._enabled},
            )

            logger.info(f"Dry-run mode: {self._enabled}")
            return self._enabled

    async def preview_write(
        self,
        file_path: str,
        new_content: str,
        original_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Preview a file write operation

        In dry-run mode, generates diff instead of writing file.

        Args:
            file_path: Path to file
            new_content: New file content
            original_content: Original content (if None, reads from file)

        Returns:
            Preview dict with diff and status
        """
        if not self._enabled:
            return {"dry_run": False, "would_write": False}

        path = Path(file_path)

        if original_content is None and path.exists():
            original_content = path.read_text()
        elif original_content is None:
            original_content = ""

        diff = self._generate_diff(original_content or "", new_content, str(path))

        preview = {
            "dry_run": True,
            "would_write": True,
            "file_path": file_path,
            "diff": diff,
            "lines_added": len(new_content.splitlines()) - len((original_content or "").splitlines()),
        }

        logger.debug(f"Dry-run preview for write: {file_path}")

        return preview

    async def preview_delete(self, file_path: str) -> Dict[str, Any]:
        """Preview a file delete operation

        In dry-run mode, returns preview without deleting.

        Args:
            file_path: Path to file

        Returns:
            Preview dict with file info
        """
        if not self._enabled:
            return {"dry_run": False, "would_delete": False}

        path = Path(file_path)
        exists = path.exists()

        preview = {
            "dry_run": True,
            "would_delete": True,
            "file_path": file_path,
            "file_exists": exists,
            "file_size": path.stat().st_size if exists else 0,
        }

        logger.debug(f"Dry-run preview for delete: {file_path}")

        return preview

    async def preview_bulk_changes(
        self,
        changes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Preview bulk file changes

        In dry-run mode, generates combined diff for all changes.

        Args:
            changes: List of change dicts with 'action', 'file_path', 'content'

        Returns:
            Combined preview with all diffs
        """
        if not self._enabled:
            return {"dry_run": False, "changes_count": 0}

        previews = []
        total_diff = ""

        for change in changes:
            action = change.get("action")
            file_path = change.get("file_path")

            if action == "write":
                content = change.get("content", "")
                if not isinstance(content, str):
                    content = ""
                preview = await self.preview_write(
                    file_path or "",
                    content,
                    change.get("original_content"),
                )
            elif action == "delete":
                if not file_path:
                    preview = {"dry_run": False, "action": action}
                else:
                    preview = await self.preview_delete(file_path)
            else:
                preview = {"dry_run": False, "action": action}

            previews.append(preview)
            diff_str = preview.get("diff")
            if isinstance(diff_str, str):
                total_diff += diff_str + "\n"

        combined = {
            "dry_run": True,
            "changes_count": len(changes),
            "previews": previews,
            "total_diff": total_diff,
        }

        logger.debug(f"Dry-run preview for {len(changes)} changes")

        return combined

    def _generate_diff(
        self,
        original: str,
        modified: str,
        filename: str = "file",
    ) -> str:
        """Generate unified diff between two strings

        Args:
            original: Original content
            modified: Modified content
            filename: File name for diff header

        Returns:
            Unified diff string
        """
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = "".join(
            unified_diff(
                original_lines,
                modified_lines,
                fromfile=f"a/{filename}",
                tofile=f"b/{filename}",
                lineterm="",
            )
        )

        return diff if diff else "(no changes)"

    def get_dry_runs(self, session_id: str) -> List[Dict[str, Any]]:
        """Get dry-run previews for a session

        Args:
            session_id: Session identifier

        Returns:
            List of dry-run previews
        """
        return self._dry_runs.get(session_id, [])

    async def record_dry_run(self, session_id: str, preview: Dict[str, Any]) -> None:
        """Record a dry-run preview for a session

        Args:
            session_id: Session identifier
            preview: Preview dict from preview_write/delete
        """
        async with self._lock:
            if session_id not in self._dry_runs:
                self._dry_runs[session_id] = []
            self._dry_runs[session_id].append(preview)


# Global dry-run manager instance
dryrun_manager = DryRunManager()
