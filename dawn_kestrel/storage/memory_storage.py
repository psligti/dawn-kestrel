"""OpenCode Python - Memory storage with JSON persistence"""
from __future__ import annotations
from typing import Optional, List

from dawn_kestrel.storage.store import Storage
from dawn_kestrel.core.models import Memory


class MemoryStorage(Storage):
    """Memory-specific storage operations"""

    async def store_memory(self, memory: Memory) -> Memory:
        """Store a memory entry"""
        await self.write(
            ["memory", memory.session_id, f"{memory.id}.json"],
            memory.model_dump(mode="json")
        )
        return memory

    async def get_memory(self, session_id: str, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID"""
        data = await self.read(["memory", session_id, f"{memory_id}.json"])
        if data:
            return Memory(**data)
        return None

    async def list_memories(self, session_id: str) -> List[Memory]:
        """List all memories for a session"""
        keys = await self.list(["memory", session_id])
        memories = []
        for key in keys:
            memory_id = key[-1]
            # List returns stem (without .json), need to add it back for reading
            data = await self.read(["memory", session_id, f"{memory_id}.json"])
            if data:
                memories.append(Memory(**data))
        # Sort by created timestamp descending
        memories.sort(key=lambda m: m.created, reverse=True)
        return memories

    async def delete_memory(self, session_id: str, memory_id: str) -> bool:
        """Delete a memory by ID"""
        return await self.remove(["memory", session_id, f"{memory_id}.json"])
