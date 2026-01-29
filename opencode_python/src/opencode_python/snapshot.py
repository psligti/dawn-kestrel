"""
Git integration snapshot system.

Provides snapshot creation, file revert, and diff management
for OpenCode sessions.
"""

import logging
import asyncio
from typing import Optional, List
from pathlib import Path
from datetime import datetime

try:
    from git import Repo, InvalidGitRepositoryError
except ImportError:
    logging.error("gitpython not installed")
    Repo = None

from .core.models import SnapshotPart, PatchPart


logger = logging.getLogger(__name__)


class GitSnapshot:
    """Git snapshot manager for session files"""
    
    def __init__(self, session_id: str, project_root: Path):
        self.session_id = session_id
        self.project_root = project_root
        self.repo = None
        
        if Repo is not None:
            try:
                self.repo = Repo(project_root)
                logger.info(f"Initialized git repo for session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize git repo: {e}")
    
    async def create_snapshot(self) -> Optional[str]:
        """Create a git snapshot of current state"""
        if self.repo is None:
            logger.error("Git repo not initialized")
            return None
        
        try:
            tree = self.repo.head.commit.tree
            snapshot_hash = tree.hexsha
            
            logger.info(f"Created snapshot: {snapshot_hash}")
            return snapshot_hash
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            return None
    
    async def save_diff(self, before_hash: str, after_hash: str, changes: List[str]) -> str:
        """Calculate and save diff between snapshots"""
        if self.repo is None:
            logger.error("Git repo not initialized")
            return ""
        
        try:
            if before_hash == after_hash:
                logger.info("No changes between snapshots")
                return ""
            
            diff_output = []
            
            for i in range(0, len(changes), 2):
                file_path = changes[i]
                before_content = self.repo.head.commit.tree[str(before_hash)][file_path] if str(before_hash) in self.repo.head.commit.tree else None
                after_content = self.repo.head.commit.tree[str(after_hash)][file_path] if str(after_hash) in self.repo.head.commit.tree else None
                
                if before_content is None:
                    if after_content is not None:
                        added_lines = after_content.data_stream.decode().splitlines()
                        diff_output.append(f"+ {file_path}")
                        diff_output.extend(f"  {line}" for line in added_lines[:100])
                        if len(added_lines) > 100:
                            diff_output.append(f"  +... ({len(added_lines) - 100} more lines)")
                else:
                    if after_content is None:
                        if before_content is not None:
                            diff_output.append(f"- {file_path}")
                            removed_lines = before_content.data_stream.decode().splitlines()
                            diff_output.extend(f"  {line}" for line in removed_lines[:100])
                            if len(removed_lines) > 100:
                                diff_output.append(f"  +... ({len(removed_lines) - 100} more lines)")
                    else:
                        diff = self.repo.diff(before_hash, after_hash, create_patch=True, context_lines=None)
                        diff_output.append(str(diff))
            
            logger.info(f"Calculated diff with {len(diff_output)} lines")
            return "\n".join(diff_output)
        except Exception as e:
            logger.error(f"Failed to calculate diff: {e}")
            return ""
    
    async def revert_file(self, file_path: str, snapshot_hash: str) -> bool:
        """Revert single file to snapshot state"""
        if self.repo is None:
            logger.error("Git repo not initialized")
            return False
        
        try:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                logger.error(f"File not found: {full_path}")
                return False
            
            tree = self.repo.head.commit.tree[str(snapshot_hash)]
            if str(snapshot_hash) not in tree or tree[str(snapshot_hash)].type != "tree":
                logger.error(f"Snapshot not found: {snapshot_hash}")
                return False
            
            blob = tree[str(snapshot_hash)][file_path]
            
            if blob.type != "blob":
                logger.error(f"Target is not a file: {file_path}")
                return False
            
            with open(full_path, "wb") as f:
                f.write(blob.data_stream.read())
            
            self.repo.index.add([full_path])
            logger.info(f"Reverted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to revert file: {e}")
            return False
    
    async def create_snapshot_part(self, snapshot_hash: str) -> SnapshotPart:
        """Create snapshot part for session"""
        return SnapshotPart(
            id=f"{self.session_id}_snapshot_{int(datetime.now().timestamp())}",
            session_id=self.session_id,
            message_id=self.session_id,
            part_type="snapshot",
            snapshot=snapshot_hash
        )
    
    async def create_patch_part(self, snapshot_hash: str, files: List[str]) -> PatchPart:
        """Create patch part for session"""
        return PatchPart(
            id=f"{self.session_id}_patch_{int(datetime.now().timestamp())}",
            session_id=self.session_id,
            message_id=self.session_id,
            part_type="patch",
            hash=snapshot_hash,
            files=files
        )


def create_git_manager(session_id: str, project_root: Path) -> GitSnapshot:
    """Factory function to create git manager"""
    return GitSnapshot(session_id, project_root)


async def test_basic_snapshot():
    """Test basic snapshot functionality"""
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        (tmppath / "test.txt").write_text("Initial content")
        (tmppath / "test.txt").write_text("Modified content")
        
        manager = GitSnapshot("test-session", tmppath)
        
        try:
            import subprocess
            subprocess.run(["git", "init"], cwd=tmppath, check=True)
            subprocess.run(["git", "add", "test.txt"], cwd=tmppath, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmppath, check=True)
            
            snapshot1 = asyncio.run(manager.create_snapshot())
            print(f"Created snapshot: {snapshot1}")
            
            (tmppath / "test.txt").write_text("Modified content again")
            subprocess.run(["git", "add", "test.txt"], cwd=tmppath, check=True)
            subprocess.run(["git", "commit", "-m", "Second commit"], cwd=tmppath, check=True)
            
            snapshot2 = asyncio.run(manager.create_snapshot())
            print(f"Created snapshot: {snapshot2}")
            
            diff = asyncio.run(manager.save_diff(snapshot1, snapshot2, ["test.txt"]))
            print(f"Diff:\n{diff}")
            
            result = asyncio.run(manager.revert_file("test.txt", snapshot1))
            print(f"Revert result: {result}")
            
            content = (tmppath / "test.txt").read_text()
            print(f"Current content: {content}")
            
        except Exception as e:
            print(f"Error: {e}")
