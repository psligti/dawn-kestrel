"""OpenCode Python - Memory Manager"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid
import logging

from dawn_kestrel.storage.memory_storage import MemoryStorage
from dawn_kestrel.core.models import Memory


logger = logging.getLogger(__name__)


class MemoryManager:
    """Manager for memory operations with storage integration"""

    def __init__(self, base_dir: Path):
        """Initialize memory manager with base directory"""
        self.storage = MemoryStorage(base_dir)

    async def store(
        self,
        session_id: str,
        content: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """Store a new memory entry"""
        memory_id = str(uuid.uuid4())
        memory = Memory(
            id=memory_id,
            session_id=session_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            created=datetime.now().timestamp(),
        )
        await self.storage.store_memory(memory)
        logger.debug(f"Stored memory {memory_id} for session {session_id}")
        return memory

    async def retrieve(
        self,
        session_id: str,
        memory_id: str,
    ) -> Optional[Memory]:
        """Retrieve a specific memory by ID"""
        return await self.storage.get_memory(session_id, memory_id)

    async def search(
        self,
        session_id: str,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Memory]:
        """Search memories in a session

        For now, returns all memories with optional filtering by content.
        Future implementations will add semantic search with embeddings.
        """
        memories = await self.storage.list_memories(session_id)

        # Apply content filter if query provided
        if query:
            memories = [m for m in memories if query.lower() in m.content.lower()]

        # Apply offset
        if offset > 0:
            memories = memories[offset:]

        # Apply limit
        if limit is not None and limit > 0:
            memories = memories[:limit]

        logger.debug(f"Found {len(memories)} memories for session {session_id}")
        return memories

    async def delete(
        self,
        session_id: str,
        memory_id: str,
    ) -> bool:
        """Delete a memory by ID"""
        deleted = await self.storage.delete_memory(session_id, memory_id)
        if deleted:
            logger.debug(f"Deleted memory {memory_id} from session {session_id}")
        else:
            logger.warning(f"Memory {memory_id} not found in session {session_id}")
        return deleted

    async def summarize(
        self,
        session_id: str,
        since: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Summarize memories in a session

        Returns statistics and aggregated information about memories.
        Future implementations will use LLM to generate actual summaries.
        """
        memories = await self.storage.list_memories(session_id)

        # Filter by time if since is provided
        if since is not None:
            memories = [m for m in memories if m.created >= since]

        # Calculate statistics
        total_count = len(memories)
        total_content_length = sum(len(m.content) for m in memories)
        oldest = None
        newest = None

        if memories:
            oldest = min(m.created for m in memories)
            newest = max(m.created for m in memories)

        summary = {
            "session_id": session_id,
            "count": total_count,
            "total_characters": total_content_length,
            "oldest_timestamp": oldest,
            "newest_timestamp": newest,
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "created": m.created,
                }
                for m in memories
            ],
        }

        logger.debug(f"Generated summary for {total_count} memories in session {session_id}")
        return summary
