"""OpenCode Python - Git Snapshot System"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
from pathlib import Path
import subprocess
import json
import logging


logger = logging.getLogger(__name__)


class GitSnapshot:
    """Git snapshot manager for tracking changes"""

    def __init__(self, snapshot_dir: Path, project_id: str):
        self.snapshot_dir = snapshot_dir / project_id
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    async def track(self) -> str:
        """
        Take a snapshot of current changes
        
        Returns:
            Snapshot hash
        """
        try:
            # Stage all changes
            subprocess.run(
                ["git", "add", "."],
                check=True,
                cwd=self.snapshot_dir,
                capture_output=True
            )
            
            # Write tree to get hash
            result = subprocess.run(
                ["git", "write-tree", "--porcelain"],
                check=True,
                cwd=self.snapshot_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"git write-tree failed: {result.stderr}")
            
            hash_value = result.stdout.strip()
            
            # Store hash
            await self._store_hash(hash_value)
            
            logger.info(f"Snapshot tracked: {hash_value}")
            return hash_value
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to track snapshot: {e}")

    async def patch(self, hash_value: str) -> List[str]:
        """
        Get list of changed files for a snapshot
        
        Returns:
            List of changed files
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", hash_value],
                check=True,
                cwd=self.snapshot_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"git diff failed: {result.stderr}")
            
            files = result.stdout.strip().split("\n")
            files = [f for f in files if f]
            
            return files
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get patch: {e}")

    async def diff(
        self,
        from_hash: str,
        to_hash: str
    ) -> str:
        """
        Get full diff between two snapshots
        
        Returns:
            Diff output
        """
        try:
            result = subprocess.run(
                ["git", "diff", from_hash, to_hash],
                check=True,
                cwd=self.snapshot_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"git diff failed: {result.stderr}")
            
            return result.stdout
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get diff: {e}")

    async def diff_full(
        self,
        from_hash: str,
        to_hash: str
    ) -> str:
        """
        Get full diff with before/after content
        
        Returns:
            Full diff output
        """
        try:
            result = subprocess.run(
                ["git", "diff", from_hash, to_hash],
                check=True,
                cwd=self.snapshot_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"git diff failed: {result.stderr}")
            
            return result.stdout
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get full diff: {e}")

    async def restore(self, hash_value: str) -> None:
        """
        Restore to a specific snapshot
        
        Args:
            hash_value: Snapshot hash to restore
        """
        try:
            # Checkout files from snapshot
            result = subprocess.run(
                ["git", "read-tree", hash_value, "--checkout-index", "-a", "-f"],
                check=True,
                cwd=self.snapshot_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"git read-tree failed: {result.stderr}")
            
            # Update index
            subprocess.run(
                ["git", "checkout-index", "-f"],
                check=True,
                cwd=self.snapshot_dir,
                capture_output=True
            )
            
            logger.info(f"Restored to snapshot: {hash_value}")
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to restore snapshot: {e}")

    async def cleanup(self, days: int = 7) -> None:
        """
        Clean up old snapshots
        
        Args:
            days: Number of days to keep
        """
        try:
            result = subprocess.run(
                ["git", "gc", "--prune", f"--expire={days}d"],
                check=True,
                cwd=self.snapshot_dir,
                capture_output=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"git gc failed: {result.stderr}")
            
            logger.info(f"Cleaned up snapshots older than {days} days")
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to cleanup: {e}")

    async def _store_hash(self, hash_value: str) -> None:
        """Store snapshot hash mapping"""
        hash_file = self.snapshot_dir / "hashes.json"
        
        hashes = {}
        if hash_file.exists():
            hashes = json.loads(hash_file.read_text())
        
        hashes[hash_value] = {
            "timestamp": self._now(),
            "hash": hash_value,
        }
        
        hash_file.write_text(json.dumps(hashes, indent=2))

    async def _get_hash(self, hash_value: str) -> Optional[Dict[str, Any]]:
        """Get stored hash information"""
        hash_file = self.snapshot_dir / "hashes.json"
        
        if not hash_file.exists():
            return None
        
        hashes = json.loads(hash_file.read_text())
        return hashes.get(hash_value)

    def _now(self) -> int:
        """Get current timestamp in milliseconds"""
        import time
        return int(time.time() * 1000)
