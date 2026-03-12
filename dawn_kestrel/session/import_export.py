"""
Session export and import functionality for OpenCode.

Provides JSON export/import for sessions with all messages and parts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dawn_kestrel.core.models import (
    AgentPart,
    CompactionPart,
    FilePart,
    Part,
    PatchPart,
    ReasoningPart,
    RetryPart,
    SnapshotPart,
    SubtaskPart,
    TextPart,
    ToolPart,
)
from dawn_kestrel.core.session import Session

logger = logging.getLogger(__name__)


# Map part_type to the corresponding Part class
PART_TYPE_MAP: dict[str, type[Part]] = {
    "text": TextPart,
    "file": FilePart,
    "tool": ToolPart,
    "reasoning": ReasoningPart,
    "snapshot": SnapshotPart,
    "patch": PatchPart,
    "agent": AgentPart,
    "subtask": SubtaskPart,
    "retry": RetryPart,
    "compaction": CompactionPart,
}


def _deserialize_part(part_dict: dict[str, Any]) -> Part:
    """Deserialize a part dict to the appropriate Part subclass."""
    part_type = part_dict.get("part_type", "text")
    part_class = PART_TYPE_MAP.get(part_type, TextPart)
    return part_class(**part_dict)


class SessionImportExport:
    """Handle session export and import operations"""

    def __init__(self, session: Session):
        self.session = session

    async def export_session(self, session_id: str | None = None) -> dict[str, Any]:
        """
        Export session to JSON format with all messages and parts.
        
        Args:
            session_id: Session ID to export (default: current session)
        
        Returns:
            Dictionary with session info, messages, parts
        """
        if session_id is None:
            session_data = self.session.to_dict()
        else:
            session_data = await self.session.manager.get_export_data(session_id)

        messages_data = []
        parts_data = []

        for message_info in session_data.get("messages", []):
            message_id = message_info["id"]
            message_data = await self.session.manager.get_messages(session_id)
            for msg in message_data:
                if msg["id"] == message_id:
                    message_dict = msg.to_dict()
                    messages_data.append(message_dict)

                    for part in msg.get("parts", []):
                        part_dict = part.to_dict()
                        parts_data.append(part_dict)

        export_data = {
            "session": session_data,
            "messages": messages_data,
            "parts": parts_data,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "version": "0.1.0"
        }

        logger.info(f"Exported session with {len(messages_data)} messages, {len(parts_data)} parts")

        return export_data

    async def import_session(self, file_path: str) -> Session:
        """
        Import session from JSON file.
        
        Args:
            file_path: Path to JSON file
        
        Returns:
            Imported Session object
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Session file not found: {file_path}")

        with open(path) as f:
            import_data = json.load(f)

        if "session" not in import_data:
            raise ValueError("Invalid session export format")

        session_data = import_data["session"]
        messages_data = import_data.get("messages", [])
        parts_data = import_data.get("parts", [])

        session_obj = self.session.manager.from_dict(session_data)

        for message_dict in messages_data:
            message_obj = self.session.manager.from_dict({
                "session": session_obj,
                **message_dict
            })
            await self.session.manager.add_message(message_obj)

            for part_dict in message_dict.get("parts", []):
                part_obj = _deserialize_part(part_dict)
                part_obj.message_id = message_obj.id
                await self.session.manager.add_part(part_obj)

        for part_dict in parts_data:
            part_obj = _deserialize_part(part_dict)
            if "message_id" in part_dict:
                part_obj.message_id = part_dict["message_id"]
            await self.session.manager.add_part(part_obj)

        logger.info(f"Imported session {session_obj.id} with {len(messages_data)} messages, {len(parts_data)} parts")

        return session_obj


def create_import_export_manager(session: Session) -> SessionImportExport:
    """Factory function to create import/export manager"""
    return SessionImportExport(session)
