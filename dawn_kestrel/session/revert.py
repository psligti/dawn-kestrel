"""OpenCode Python - Session Revert System"""
from __future__ import annotations
from typing import Dict, Any
from pathlib import Path
import subprocess
import logging


logger = logging.getLogger(__name__)


class SessionRevert:
    """Session revert manager for undoing changes"""

    def __init__(self, snapshot_dir: Path, session_id: str):
        self.session_id = session_id
        self.snapshot_dir = snapshot_dir / session_id
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    async def revert(
        self,
        message_id: str,
        part_id: str
    ) -> Dict[str, Any]:
        """
        Revert to state before a specific message/part
        
        Args:
            message_id: Message ID containing the revert trigger
            part_id: Part ID to revert to
            
        Returns:
            Revert information (snapshot, diff, reverted_message, reverted_part)
        """
        try:
            # Take snapshot of current state
            from dawn_kestrel.snapshot import GitSnapshot
            git = GitSnapshot(self.snapshot_dir, self.session_id)
            current_snapshot = await git.track()

            # Collect all patches from revert point
            patches = []
            # TODO: Load from session.revert storage
            # patches = await SessionStorage.list_reverts(self.session_id, message_id, part_id)

            # Revert each patch
            from dawn_kestrel.snapshot import GitSnapshot
            git2 = GitSnapshot(self.snapshot_dir, self.session_id)
            
            for patch_hash in patches:
                await git2.restore(patch_hash)
            
            # Compute diff from original snapshot
            diff_output = await git2.diff(current_snapshot, "HEAD")
            
            # Store in session
            revert_info = {
                "message_id": message_id,
                "part_id": part_id,
                "snapshot": current_snapshot,
                "diff": diff_output,
            }
            
            # TODO: await SessionStorage.create_revert(revert_info)
            
            logger.info(f"Reverted to snapshot: {current_snapshot}")
            
            return {
                "snapshot": current_snapshot,
                "diff": diff_output,
                "reverted_message": message_id,
                "reverted_part": part_id,
            }
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to revert: {e}")

    async def cleanup(self, message_id: str) -> None:
        """
        Clean up revert state
        
        Args:
            message_id: Message ID to clean up
        """
        # TODO: Remove from session.revert storage
        logger.info(f"Cleaned up revert state for message {message_id}")

    async def unrevert(self, message_id: str) -> None:
        """
        Restore original state (undo revert)
        
        Args:
            message_id: Message ID to unrevert
        """
        # TODO: Load revert info and restore to before state
        logger.info(f"Unreverted message {message_id}")
