"""OpenCode Python - Storage layer with JSON persistence"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
import json
import aiofiles
from pydantic import ValidationError
from datetime import datetime

from dawn_kestrel.core.models import Session, Message, Part
from dawn_kestrel.core.security import safe_path, SecurityError


class Storage:
    """JSON storage layer with file locking"""

    def __init__(self, base_dir: Path):
        """Initialize storage with base directory"""
        self.base_dir = Path(base_dir)
        self.storage_dir = self.base_dir / "storage"

    async def _get_path(self, *keys: str) -> Path:
        """Get full path for a key with path traversal protection"""
        for key in keys:
            if not key or ".." in key or "/" in key or "\\" in key or "\x00" in key:
                raise SecurityError(f"Invalid storage key: {key}")

        path = self.storage_dir / "/".join(keys)
        try:
            resolved = path.resolve()
            if not str(resolved).startswith(str(self.storage_dir.resolve())):
                raise SecurityError(f"Path traversal attempt detected: {path}")
            return path
        except (OSError, RuntimeError) as e:
            raise SecurityError(f"Invalid path: {path}") from e

    async def _ensure_dir(self, path: Path) -> None:
        """Ensure directory exists"""
        path.parent.mkdir(parents=True, exist_ok=True)

    async def read(self, key: List[str]) -> Optional[Dict[str, Any]]:
        """Read JSON data by key"""
        try:
            key_with_ext = list(key)
            if not key_with_ext[-1].endswith(".json"):
                key_with_ext[-1] = key_with_ext[-1] + ".json"
            path = await self._get_path(*key_with_ext)
            async with aiofiles.open(path, mode="r") as f:
                content = await f.read()
                data: Dict[str, Any] = json.loads(content)
                return data
        except (FileNotFoundError, json.JSONDecodeError, ValidationError):
            return None

    async def write(self, key: List[str], data: Dict[str, Any]) -> None:
        """Write JSON data by key"""
        key_with_ext = list(key)
        if not key_with_ext[-1].endswith(".json"):
            key_with_ext[-1] = key_with_ext[-1] + ".json"
        path = await self._get_path(*key_with_ext)
        await self._ensure_dir(path)
        async with aiofiles.open(path, mode="w") as f:
            content = json.dumps(data, indent=2, ensure_ascii=False)
            await f.write(content)

    async def update(self, key: List[str], fn: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
        """Update JSON data by key with update function"""
        data = await self.read(key) or {}
        fn(data)
        await self.write(key, data)
        return data

    async def remove(self, key: List[str]) -> bool:
        """Remove data by key"""
        try:
            key_with_ext = list(key)
            if not key_with_ext[-1].endswith(".json"):
                key_with_ext[-1] = key_with_ext[-1] + ".json"
            path = await self._get_path(*key_with_ext)
            path.unlink()
            return True
        except FileNotFoundError:
            return False

    async def list(self, prefix: List[str]) -> List[List[str]]:
        """List all keys with given prefix"""
        prefix_path = await self._get_path(*prefix)
        if not prefix_path.exists():
            return []
        keys = []
        for path in prefix_path.rglob("*.json"):
            relative = path.relative_to(self.storage_dir)
            parts = list(relative.parts)
            keys.append(parts)
        keys.sort()
        return keys


class SessionStorage(Storage):
    """Session-specific storage operations"""

    async def get_session(self, session_id: str, project_id: str) -> Optional[Session]:
        """Get session by ID"""
        keys = await self.list(["session", project_id])
        for key in keys:
            data = await self.read(key)
            if data and data.get("id") == session_id:
                return Session(**data)
        return None

    async def list_sessions(self, project_id: str) -> List[Session]:
        """List all sessions for a project"""
        keys = await self.list(["session", project_id])
        sessions = []
        for key in keys:
            data = await self.read(key)
            if data:
                sessions.append(Session(**data))
        # Sort by updated timestamp descending
        sessions.sort(key=lambda s: s.time_updated, reverse=True)
        return sessions

    async def create_session(self, session: Session) -> Session:
        """Create a new session"""
        await self.write(
            ["session", session.project_id, session.id], session.model_dump(mode="json")
        )
        return session

    async def update_session(self, session: Session) -> Session:
        """Update session data"""
        session.time_updated = datetime.now().timestamp()
        await self.write(
            ["session", session.project_id, session.id], session.model_dump(mode="json")
        )
        return session

    async def delete_session(self, session_id: str, project_id: str) -> bool:
        """Delete session"""
        key = session_id + ".json"
        return await self.remove(["session", project_id, key])


class MessageStorage(Storage):
    """Message-specific storage operations"""

    async def get_message(self, session_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message by ID"""
        data = await self.read(["message", session_id, message_id])
        if data:
            return data
        return None

    async def create_message(self, session_id: str, message: Message) -> Message:
        """Create a new message"""
        await self.write(["message", session_id, message.id], message.model_dump(mode="json"))
        return message

    async def list_messages(self, session_id: str, reverse: bool = True) -> List[Dict[str, Any]]:
        """List all messages for a session"""
        keys = await self.list(["message", session_id])
        messages = []
        for key in keys:
            data = await self.read(key)
            if data:
                messages.append(data)
        messages.sort(key=lambda m: m.get("time", {}).get("created", 0), reverse=reverse)
        return messages


class PartStorage(Storage):
    """Part-specific storage operations"""

    async def get_part(self, message_id: str, part_id: str) -> Optional[Dict[str, Any]]:
        """Get part by ID"""
        data = await self.read(["part", message_id, part_id])
        if data:
            return data
        return None

    async def create_part(self, message_id: str, part: Part) -> Part:
        """Create a new part"""
        await self.write(["part", message_id, part.id], part.model_dump(mode="json"))
        return part

    async def update_part(self, message_id: str, part: Part) -> Part:
        """Update part data"""
        await self.write(["part", message_id, part.id], part.model_dump(mode="json"))
        return part

    async def list_parts(self, message_id: str) -> List[Dict[str, Any]]:
        """List all parts for a message"""
        keys = await self.list(["part", message_id])
        parts = []
        for key in keys:
            data = await self.read(key)
            if data:
                parts.append(data)
        return parts
