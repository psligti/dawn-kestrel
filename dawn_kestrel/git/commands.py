"""OpenCode Python - Git Commands"""

from __future__ import annotations
from typing import Dict
from pathlib import Path
import subprocess
import logging

from dawn_kestrel.core.security import validate_git_hash, SecurityError


logger = logging.getLogger(__name__)


class GitCommands:
    """Git command execution for snapshots"""

    def __init__(self, snapshot_dir: Path):
        """Initialize with snapshot directory"""
        self.snapshot_dir = snapshot_dir
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def _run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Helper to run git command"""
        full_cmd = ["git"] + list(args)

        result = subprocess.run(
            full_cmd, check=True, cwd=self.snapshot_dir, capture_output=True, text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {' '.join(args)}: {result.stderr}")

        return result

    def get_root_commit(self) -> str:
        """Get current root commit hash"""
        result = self._run_git("rev-parse", "HEAD")
        return result.stdout.strip()

    def write_tree(self) -> str:
        """Write tree object and return hash"""
        result = self._run_git("add", ".")

        if result.returncode != 0:
            raise RuntimeError(f"git add failed: {result.stderr}")

        result = self._run_git("write-tree", "--porcelain")

        if result.returncode != 0:
            raise RuntimeError(f"git write-tree failed: {result.stderr}")

        return result.stdout.strip()

    def get_changed_files(self, hash_value: str) -> list[str]:
        """Get list of changed files for a snapshot"""
        try:
            validated_hash = validate_git_hash(hash_value)
        except SecurityError as e:
            raise ValueError(f"Invalid git hash: {e}")

        result = self._run_git("diff", "--name-only", validated_hash)

        if result.returncode != 0:
            raise RuntimeError(f"git diff failed: {result.stderr}")

        files = result.stdout.strip().split("\n")
        return [f for f in files if f]

    def get_diff(self, from_hash: str, to_hash: str) -> str:
        """Get full diff between two snapshots"""
        try:
            from_validated = validate_git_hash(from_hash)
            to_validated = validate_git_hash(to_hash)
        except SecurityError as e:
            raise ValueError(f"Invalid git hash: {e}")

        result = self._run_git("diff", from_validated, to_validated)

        if result.returncode != 0:
            raise RuntimeError(f"git diff failed: {result.stderr}")

        return result.stdout

    def checkout_files(self, hash_value: str) -> None:
        """Checkout files from a snapshot"""
        try:
            validated_hash = validate_git_hash(hash_value)
        except SecurityError as e:
            raise ValueError(f"Invalid git hash: {e}")

        result = self._run_git("read-tree", validated_hash, "--checkout-index", "-a", "-f")

        if result.returncode != 0:
            raise RuntimeError(f"git read-tree failed: {result.stderr}")

        self._run_git("checkout-index", "-f")

        logger.info(f"Checked out files from snapshot: {hash_value}")

    def get_diff_stats(self, from_hash: str, to_hash: str) -> Dict[str, Dict[str, int]]:
        """Get diff statistics"""
        try:
            from_validated = validate_git_hash(from_hash)
            to_validated = validate_git_hash(to_hash)
        except SecurityError as e:
            raise ValueError(f"Invalid git hash: {e}")

        result = self._run_git("diff", "--numstat", from_validated, to_validated)

        if result.returncode != 0:
            raise RuntimeError(f"git diff --numstat failed: {result.stderr}")

        # Parse stats
        stats: Dict[str, Dict[str, int]] = {}
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 5:
                filename = parts[4]
                additions = int(parts[0])
                deletions = int(parts[1])
                stats[filename] = {
                    "additions": additions,
                    "deletions": deletions,
                }

        return stats

    def cleanup(self, days: int = 7) -> None:
        """Clean up old snapshots"""
        result = self._run_git("gc", "--prune", f"--expire={days}d")

        if result.returncode != 0:
            raise RuntimeError(f"git gc failed: {result.stderr}")

        logger.info(f"Cleaned up snapshots older than {days} days")
