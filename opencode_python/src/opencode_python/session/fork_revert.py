"""
Session fork and revert functionality.

Enables creating child sessions from specific messages and
reverting sessions to previous snapshot states.
"""

import logging
from typing import Optional, List
from pathlib import Path

from .core.session import Session
from .core.models import Message as MessageModel, Part as PartModel
from .snapshot import GitSnapshot, create_git_manager


logger = logging.getLogger(__name__)


async def fork_session(session: Session, message_id: str, title: Optional[str] = None) -> str:
    """Fork session by creating child from specific message"""
    if not session.project_id:
        logger.error("Cannot fork session without project ID")
        return None
    
    from .storage.store import SessionStorage
    
    storage = SessionStorage()
    
    child_title = title or f"{session.title} (fork from {message_id[:8]}...)"
    
    child_session = await storage.create(
        project_id=session.project_id,
        parent_id=session.id,
        directory=session.directory,
        title=child_title,
        metadata={"forked_from": message_id}
    )
    
    logger.info(f"Created child session: {child_session.id} (fork from {message_id[:8]}...)")
    
    from .core.event_bus import bus, Events
    
    await bus.publish(Events.SESSION_CREATED, {
        "info": {
            "id": child_session.id,
            "session_id": child_session.id,
            "parent_id": session.id,
            "title": child_session.title,
            "directory": str(child_session.directory)
        }
    })
    
    return child_session.id


async def list_child_sessions(session: Session) -> List[Session]:
    """List all child sessions for current session"""
    from .storage.store import SessionStorage
    
    storage = SessionStorage()
    sessions = await storage.list_by_project(session.project_id)
    
    child_sessions = [s for s in sessions if s.parent_id == session.id]
    
    logger.info(f"Found {len(child_sessions)} child sessions for session {session.id}")
    
    return child_sessions


async def revert_session(session: Session, snapshot_id: str, files: Optional[List[str]] = None) -> bool:
    """Revert files to previous snapshot state"""
    from .storage.store import SessionStorage
    
    storage = SessionStorage()
    
    if not snapshot_id:
        logger.error("Cannot revert without snapshot ID")
        return False
    
    if not files:
        files = []
        logger.info("No files specified for revert, asking which files to revert")
    
    git_manager = create_git_manager(session.id, session.directory)
    
    target_snapshot_id = None
    for part in await storage.get_parts(session.id):
        if part.part_type == "snapshot" and part.snapshot == snapshot_id:
            target_snapshot_id = part.id
            break
    
    if not target_snapshot_id:
        logger.error(f"Snapshot {snapshot_id} not found in session {session.id}")
        return False
    
    logger.info(f"Reverting {len(files)} files to snapshot {target_snapshot_id}")
    
    reverted_files = []
    for file_path in files:
        try:
            success = await git_manager.revert_file(file_path, target_snapshot_id)
            
            if success:
                reverted_files.append(file_path)
                logger.info(f"Reverted {file_path} to snapshot {target_snapshot_id}")
            else:
                logger.warning(f"Failed to revert {file_path}")
        except Exception as e:
            logger.error(f"Error reverting {file_path}: {e}")
    
    if not reverted_files:
        return False
    
    create_snapshot_part = PartModel(
        id=f"{session.id}_revert_{int(time.time())}",
        session_id=session.id,
        message_id=session.id,
        part_type="snapshot",
        snapshot=target_snapshot_id
    )
    
    await storage.create_part(create_snapshot_part)
    
    revert_part = PartModel(
        id=f"{session.id}_revert_summary",
        session_id=session.id,
        message_id=session.id,
        part_type="text",
        text=f"Reverted {len(reverted_files)} files to snapshot {target_snapshot_id}"
    )
    
    await storage.create_part(revert_part)
    
    from .core.event_bus import bus, Events
    
    await bus.publish(Events.SESSION_UPDATED, {
        "info": {
            "id": session.id,
            "session_id": session.id,
            "reverted_files": len(reverted_files),
            "target_snapshot": target_snapshot_id
        }
    })
    
    logger.info(f"Reverted session {session.id} to snapshot {target_snapshot_id}")
    
    return True


async def get_session_tree(session: Session) -> dict:
    """Build session tree hierarchy"""
    from .storage.store import SessionStorage
    
    storage = SessionStorage()
    
    async def build_tree(session_id: str, max_depth: int = 10) -> dict:
        session_data = await storage.get(session_id)
        if not session_data:
            return {}
        
        tree = {
            "id": session_id,
            "title": session_data.get("title", ""),
            "children": []
        }
        
        children = await storage.list_by_parent(session_id)
        
        for child_session in children:
            child_tree = await build_tree(child_session["id"], max_depth - 1)
            if child_tree:
                tree["children"].append(child_tree)
        
        return tree


async def export_session_tree(session: Session) -> str:
    """Export session tree to text format"""
    tree = await get_session_tree(session.id)
    
    output = f"Session Tree:\n{tree['title']}\n"
    output += _format_tree(tree["children"], indent="  ")
    
    return output


def _format_tree(sessions: List[dict], indent: str = "") -> str:
    if not sessions:
        return ""
    
    lines = []
    for session in sessions:
        title = session.get("title", "")
        lines.append(f"{indent}• {title}")
        lines.extend(_format_tree(session.get("children", []), indent + "  "))
    
    return "\n".join(lines)
