"""OpenCode Python - Session Meta Storage (separate namespace for session context)"""
from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field

from opencode_python.storage.store import Storage


class SessionMeta(BaseModel):
    """Session metadata (repo context, objective, constraints) stored separately"""
    repo_path: Optional[str] = Field(default=None, description="Git repository path")
    objective: Optional[str] = Field(default=None, description="Session objective/goal")
    constraints: Optional[str] = Field(default=None, description="Constraints for the session")
    time_updated: float = Field(default_factory=lambda: 0, description="Last update timestamp")


class SessionMetaStorage(Storage):
    """Storage for session metadata in separate namespace"""

    async def get_meta(self, session_id: str) -> Optional[SessionMeta]:
        """Get session metadata by ID"""
        data = await self.read(["session_meta", session_id, "meta"])
        if data:
            return SessionMeta(**data)
        return None

    async def save_meta(self, session_id: str, meta: SessionMeta) -> SessionMeta:
        """Save session metadata"""
        import time
        meta.time_updated = time.time()
        await self.write(["session_meta", session_id, "meta"], meta.model_dump(mode="json"))
        return meta

    async def update_meta(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> SessionMeta:
        """Update session metadata"""
        meta = await self.get_meta(session_id) or SessionMeta()
        for key, value in kwargs.items():
            if hasattr(meta, key):
                setattr(meta, key, value)
        return await self.save_meta(session_id, meta)

    async def delete_meta(self, session_id: str) -> bool:
        """Delete session metadata"""
        return await self.remove(["session_meta", session_id, "meta"])
