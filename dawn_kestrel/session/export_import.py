"""OpenCode Python - Export/Import Session Management"""
from __future__ import annotations
from typing import Optional, Dict, Any
from pathlib import Path
import json
import logging
import gzip

from dawn_kestrel.core.session import SessionManager
from dawn_kestrel.snapshot.index import GitSnapshot


logger = logging.getLogger(__name__)


class ExportImportManager:
    """Export session to file and import from file"""

    def __init__(self, session_manager: SessionManager, git_snapshot: GitSnapshot):
        self.session_manager = session_manager
        self.git_snapshot = git_snapshot

    async def export_session(
        self,
        session_id: str,
        output_path: Optional[Path] = None,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Export a session to file
        
        Args:
            session_id: Session ID to export
            output_path: Path to export to (default: {session_id}.json)
            format: Export format (json, jsonl, jsonl.gz)
            
        Returns:
            Export info (path, format, message_count, size)
        """
        if not output_path:
            output_path = Path.cwd() / f"{session_id}.{format}"
        
        # Get session data
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Get all messages and parts
        messages = await self.session_manager.list_messages(session_id)
        
        export_data = {
            "session": {
                "id": session.id,
                "title": session.title,
                "project_id": session.project_id,
                "directory": session.directory,
                "time_created": session.time_created,
                "time_updated": session.time_updated,
                "version": session.version,
            },
            "messages": messages,
        }
        
        # Write to file
        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                file_size = f.tell()
        elif format == "jsonl":
            with open(output_path, "w", encoding="utf-8") as f:
                # Write each message as JSONL line
                for msg in messages:
                    msg_line = json.dumps({"role": msg.role, "content": msg.text})
                    f.write(msg_line + "\n")
                file_size = f.tell()
        elif format == "jsonl.gz":
            with gzip.open(output_path, "wt", encoding="utf-8") as f:
                for msg in messages:
                    msg_line = json.dumps({"role": msg.role, "content": msg.text})
                    f.write(msg_line + "\n")
                file_size = f.tell()
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported session to {output_path} ({file_size} bytes)")
        
        return {
            "path": str(output_path),
            "format": format,
            "message_count": len(messages),
            "size": file_size,
        }

    async def import_session(
        self,
        import_path: Path,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import session from file
        
        Args:
            import_path: Path to import from
            project_id: Project ID (for multi-project repos)
            
        Returns:
            Import info (session_id, message_count, imported)
        """
        if not import_path.exists():
            raise FileNotFoundError(f"Import file not found: {import_path}")
        
        # Determine format from extension
        format = "json"
        if import_path.suffix == ".jsonl.gz":
            format = "jsonl.gz"
        elif import_path.suffix == ".jsonl":
            format = "jsonl"
        elif import_path.suffix == ".json":
            format = "json"

        # Read and parse
        export_data = {}

        if format == "json" or format == "jsonl":
            with open(import_path, "r", encoding="utf-8") as f:
                export_data = json.load(f)
        elif format == "jsonl.gz":
            with gzip.open(import_path, "rt", encoding="utf-8") as f:
                export_data = json.loads(f.read())

        session_data = export_data.get("session", {})

        # Convert messages to Message objects
        from dawn_kestrel.core.models import Message

        messages_data = export_data.get("messages", [])

        messages = []
        for msg_data in messages_data:
            if isinstance(msg_data, dict):
                messages.append(Message(**msg_data))
            elif isinstance(msg_data, Message):
                messages.append(msg_data)

        # Get session_id from export data
        session_id = session_data.get("id")

        # Create or update session
        work_dir = Path.cwd()

        # Check if session exists
        existing = await self.session_manager.storage.get_session(session_id)

        if existing:
            # Update existing session
            session = await self.session_manager.update_session(
                session_id,
                title=session_data.get("title"),
                summary=session_data.get("summary"),
            )
            message_count = len(messages)
        else:
            # Create new session
            session = await self.session_manager.create(
                title=session_data.get("title", "Imported Session"),
                parent_id=None,
                version=session_data.get("version", "1.0.0"),
                summary=session_data.get("summary"),
            )
            message_count = len(messages)

        # Import messages
        await self.session_manager.create_messages(session.id, messages)

        logger.info(f"Imported session: {session.id} ({message_count} messages)")

        return {
            "session_id": session.id,
            "message_count": message_count,
        }
