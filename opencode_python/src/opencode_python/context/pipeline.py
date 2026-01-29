"""OpenCode Python - Context pipeline (file scanning, ignore rules, git integration)"""
from __future__ import annotations
from typing import List, Optional, Tuple
from pathlib import Path
import subprocess
import re
import logging

from opencode_python.core.models import FileInfo
from opencode_python.core.settings import get_settings


logger = logging.getLogger(__name__)


class IgnoreRules:
    """Predefined ignore patterns matching TypeScript OpenCode"""

    FOLDERS = {
        "node_modules",
        "bower_components",
        ".pnpm-store",
        "vendor",
        ".npm",
        "dist",
        "build",
        "out",
        ".next",
        "target",
        "bin",
        "obj",
        ".git",
        ".svn",
        ".hg",
        ".vscode",
        ".idea",
        ".turbo",
        ".output",
        ".sst",
        ".cache",
        ".webkit-cache",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".gradle",
    }

    FILES = [
        "**/*.swp",
        "**/*.swo",
        "**/*.pyc",
        # OS
        "**/.DS_Store",
        "**/Thumbs.db",
        # Logs & temp
        "**/logs/**",
        "**/tmp/**",
        "**/temp/**",
        "**/*.log",
        # Coverage/test outputs
        "**/coverage/**",
        "**/.nyc_output/**",
    ]

    @classmethod
    def match_folder(cls, path: str) -> bool:
        """Check if path matches a folder to ignore"""
        parts = Path(path).parts
        for part in parts:
            if part in cls.FOLDERS:
                return True
        return False

    @classmethod
    def match_file(cls, path: str) -> bool:
        """Check if path matches a file pattern to ignore"""
        parts = Path(path).parts
        filename = parts[-1]

        # Check extension patterns
        for pattern in cls.FILES:
            if re.match(pattern.replace("*", ".*"), filename):
                return True

        # Check if in ignored folder
        for part in parts[:-1]:
            if part in cls.FOLDERS:
                return True

        return False


class FileScanner:
    """Repository scanner using Ripgrep"""

    def __init__(self, directory: Path):
        """Initialize scanner

        Args:
            directory: Directory to scan
        """
        self.directory = Path(directory).absolute()
        self._cache: Optional[List[str]] = None
        self._cache_time: Optional[float] = None

    def _get_timestamp(self) -> float:
        import time
        return time.time()

    async def scan_files(self, force_refresh: bool = False) -> List[str]:
        """Scan all files in directory using Ripgrep

        Args:
            force_refresh: Force re-scan even if cached

        Returns:
            List of file paths relative to directory
        """
        # Check cache
        if not force_refresh and self._cache is not None:
            return self._cache

        logger.debug(f"Scanning directory: {self.directory}")

        try:
            # Run ripgrep with --files flag
            result = subprocess.run(
                ["ripgrep", "--files", "--glob", "!.git/*"],
                cwd=self.directory,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Ripgrep failed: {result.stderr}")

            # Parse output
            files = result.stdout.strip().split("\n")
            self._cache = files
            self._cache_time = self._get_timestamp()
            return files

        except FileNotFoundError:
            logger.warning(f"Ripgrep not found - directory not a git repo")
            return []

    async def list_files(
        self,
        pattern: str = "",
        limit: int = 100,
        dirs: bool = True,
    ) -> List[str]:
        """List files with optional filtering

        Args:
            pattern: Fuzzy search pattern
            limit: Maximum results to return
            dirs: Include directories in results

        Returns:
            List of matching files/directories
        """
        files = await self.scan_files()

        # Filter by pattern if provided
        if pattern:
            import fnmatch
            files = [f for f in files if fnmatch.fnmatch(f, pattern)]

        # Limit results
        if len(files) > limit:
            files = files[:limit]

        return files


class GitManager:
    """Git integration for status, diffs, and snapshots"""

    def __init__(self, directory: Path):
        """Initialize git manager

        Args:
            directory: Path to git repository
        """
        self.directory = Path(directory).absolute()

    def _run_git(self, *args: str) -> str:
        """Run a git command and return output"""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.directory,
            capture_output=True,
            text=True,
            check=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {result.stderr}")

        return result.stdout.strip()

    async def get_status(self) -> List[FileInfo]:
        """Get git status (modified, added, deleted, untracked files)"""
        if not self.directory.joinpath(".git").exists():
            logger.warning("Not a git repository")
            return []

        files = []

        # Get modified files
        diff_output = self._run_git("diff", "--numstat", "HEAD")
        if diff_output:
            for line in diff_output.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) >= 3:
                    added, removed, filepath = parts
                    files.append({
                        "path": filepath,
                        "added": 0 if added == "-" else int(added),
                        "removed": 0 if removed == "-" else int(removed),
                        "status": "modified",
                    })

        # Get untracked files
        untracked_output = self._run_git("ls-files", "--others", "--exclude-standard")
        if untracked_output:
            for filepath in untracked_output.strip().split("\n"):
                files.append({
                    "path": filepath,
                    "added": len(filepath) + 1,  # Estimate lines
                    "removed": 0,
                    "status": "added",
                })

        # Get deleted files
        deleted_output = self._run_git("diff", "--name-only", "--diff-filter=D", "HEAD")
        if deleted_output:
            for filepath in deleted_output.strip().split("\n"):
                files.append({
                    "path": filepath,
                    "added": 0,
                    "removed": 0,
                    "status": "deleted",
                })

        return files

    async def get_diff(self, file_path: str) -> Optional[str]:
        """Get git diff for a file

        Args:
            file_path: Path to file (relative to directory)

        Returns:
            Unified diff string, or None if file doesn't exist
        """
        try:
            diff = self._run_git("diff", str(file_path))
            return diff if diff else None
        except subprocess.CalledProcessError:
            return None

    async def read_file_with_diff(self, file_path: str) -> Tuple[str, Optional[str]]:
        """Read file content and include git diff if available

        Args:
            file_path: Path to file (relative to directory)

        Returns:
            Tuple of (content, diff) where diff is git diff string
        """
        full_path = self.directory / file_path
        if not full_path.exists():
            return "", None

        content = full_path.read_text()
        diff = await self.get_diff(file_path)
        return content, diff
