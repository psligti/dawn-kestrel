"""Tests for memory system (MemoryStorage and MemoryManager)"""
from __future__ import annotations
import pytest
from pathlib import Path
import tempfile
import shutil
from typing import Generator

from opencode_python.storage.memory_storage import MemoryStorage
from opencode_python.agents.memory_manager import MemoryManager
from opencode_python.core.models import Memory


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test storage"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def memory_storage(temp_dir: Path) -> MemoryStorage:
    """Create a MemoryStorage instance for testing"""
    return MemoryStorage(temp_dir)


@pytest.fixture
def memory_manager(temp_dir: Path) -> MemoryManager:
    """Create a MemoryManager instance for testing"""
    return MemoryManager(temp_dir)


class TestMemoryModel:
    """Test the Memory data model"""

    def test_memory_creation(self) -> None:
        """Test creating a Memory model"""
        memory = Memory(
            id="mem_123",
            session_id="session_456",
            content="Test memory content",
            embedding=[0.1, 0.2, 0.3],
            metadata={"key": "value"},
            created=1234567890.0,
        )
        assert memory.id == "mem_123"
        assert memory.session_id == "session_456"
        assert memory.content == "Test memory content"
        assert memory.embedding == [0.1, 0.2, 0.3]
        assert memory.metadata == {"key": "value"}
        assert memory.created == 1234567890.0

    def test_memory_defaults(self) -> None:
        """Test Memory model with default values"""
        memory = Memory(
            id="mem_123",
            session_id="session_456",
            content="Test",
        )
        assert memory.embedding is None
        assert memory.metadata == {}
        assert isinstance(memory.created, float)


class TestMemoryStorage:
    """Test MemoryStorage operations"""

    @pytest.mark.asyncio
    async def test_store_memory(self, memory_storage: MemoryStorage) -> None:
        """Test storing a memory"""
        memory = Memory(
            id="mem_1",
            session_id="session_1",
            content="First memory",
        )
        result = await memory_storage.store_memory(memory)
        assert result.id == "mem_1"
        assert result.session_id == "session_1"

    @pytest.mark.asyncio
    async def test_get_memory(self, memory_storage: MemoryStorage) -> None:
        """Test retrieving a memory"""
        memory = Memory(
            id="mem_2",
            session_id="session_1",
            content="Second memory",
        )
        await memory_storage.store_memory(memory)

        retrieved = await memory_storage.get_memory("session_1", "mem_2")
        assert retrieved is not None
        assert retrieved.id == "mem_2"
        assert retrieved.content == "Second memory"

    @pytest.mark.asyncio
    async def test_get_nonexistent_memory(self, memory_storage: MemoryStorage) -> None:
        """Test retrieving a non-existent memory"""
        result = await memory_storage.get_memory("session_1", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_memories_empty(self, memory_storage: MemoryStorage) -> None:
        """Test listing memories when none exist"""
        memories = await memory_storage.list_memories("session_1")
        assert memories == []

    @pytest.mark.asyncio
    async def test_list_memories(self, memory_storage: MemoryStorage) -> None:
        """Test listing multiple memories"""
        await memory_storage.store_memory(
            Memory(id="mem_1", session_id="session_1", content="First")
        )
        await memory_storage.store_memory(
            Memory(id="mem_2", session_id="session_1", content="Second")
        )
        await memory_storage.store_memory(
            Memory(id="mem_3", session_id="session_1", content="Third")
        )

        memories = await memory_storage.list_memories("session_1")
        assert len(memories) == 3
        assert all(isinstance(m, Memory) for m in memories)

    @pytest.mark.asyncio
    async def test_list_memories_sorted(self, memory_storage: MemoryStorage) -> None:
        """Test that memories are sorted by created timestamp"""
        await memory_storage.store_memory(
            Memory(
                id="mem_1",
                session_id="session_1",
                content="First",
                created=1000.0,
            )
        )
        await memory_storage.store_memory(
            Memory(
                id="mem_2",
                session_id="session_1",
                content="Second",
                created=3000.0,
            )
        )
        await memory_storage.store_memory(
            Memory(
                id="mem_3",
                session_id="session_1",
                content="Third",
                created=2000.0,
            )
        )

        memories = await memory_storage.list_memories("session_1")
        assert memories[0].id == "mem_2"
        assert memories[1].id == "mem_3"
        assert memories[2].id == "mem_1"

    @pytest.mark.asyncio
    async def test_list_memories_by_session(self, memory_storage: MemoryStorage) -> None:
        """Test that listing memories respects session isolation"""
        await memory_storage.store_memory(
            Memory(id="mem_1", session_id="session_1", content="First")
        )
        await memory_storage.store_memory(
            Memory(id="mem_2", session_id="session_2", content="Second")
        )

        session1_memories = await memory_storage.list_memories("session_1")
        session2_memories = await memory_storage.list_memories("session_2")

        assert len(session1_memories) == 1
        assert session1_memories[0].id == "mem_1"
        assert len(session2_memories) == 1
        assert session2_memories[0].id == "mem_2"

    @pytest.mark.asyncio
    async def test_delete_memory(self, memory_storage: MemoryStorage) -> None:
        """Test deleting a memory"""
        memory = Memory(id="mem_1", session_id="session_1", content="Delete me")
        await memory_storage.store_memory(memory)

        deleted = await memory_storage.delete_memory("session_1", "mem_1")
        assert deleted is True

        retrieved = await memory_storage.get_memory("session_1", "mem_1")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_memory(self, memory_storage: MemoryStorage) -> None:
        """Test deleting a non-existent memory"""
        deleted = await memory_storage.delete_memory("session_1", "nonexistent")
        assert deleted is False


class TestMemoryManager:
    """Test MemoryManager operations"""

    @pytest.mark.asyncio
    async def test_store_memory(self, memory_manager: MemoryManager) -> None:
        """Test storing a memory through MemoryManager"""
        memory = await memory_manager.store(
            session_id="session_1",
            content="Test memory",
        )
        assert memory.id is not None
        assert memory.session_id == "session_1"
        assert memory.content == "Test memory"
        assert memory.embedding is None
        assert memory.metadata == {}

    @pytest.mark.asyncio
    async def test_store_memory_with_embedding(self, memory_manager: MemoryManager) -> None:
        """Test storing a memory with embedding"""
        memory = await memory_manager.store(
            session_id="session_1",
            content="Test with embedding",
            embedding=[0.1, 0.2, 0.3],
        )
        assert memory.embedding == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_store_memory_with_metadata(self, memory_manager: MemoryManager) -> None:
        """Test storing a memory with metadata"""
        memory = await memory_manager.store(
            session_id="session_1",
            content="Test with metadata",
            metadata={"source": "user", "priority": 1},
        )
        assert memory.metadata == {"source": "user", "priority": 1}

    @pytest.mark.asyncio
    async def test_retrieve_memory(self, memory_manager: MemoryManager) -> None:
        """Test retrieving a memory through MemoryManager"""
        stored = await memory_manager.store(
            session_id="session_1",
            content="Retrieve this",
        )

        retrieved = await memory_manager.retrieve("session_1", stored.id)
        assert retrieved is not None
        assert retrieved.id == stored.id
        assert retrieved.content == "Retrieve this"

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_memory(self, memory_manager: MemoryManager) -> None:
        """Test retrieving a non-existent memory"""
        result = await memory_manager.retrieve("session_1", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_all_memories(self, memory_manager) -> None:
        """Test searching returns all memories without filters"""
        await memory_manager.store(session_id="session_1", content="First")
        await memory_manager.store(session_id="session_1", content="Second")
        await memory_manager.store(session_id="session_1", content="Third")

        memories = await memory_manager.search("session_1")
        assert len(memories) == 3

    @pytest.mark.asyncio
    async def test_search_with_query(self, memory_manager) -> None:
        """Test searching with content query filter"""
        await memory_manager.store(session_id="session_1", content="Python code")
        await memory_manager.store(session_id="session_1", content="JavaScript code")
        await memory_manager.store(session_id="session_1", content="Python tutorial")

        memories = await memory_manager.search("session_1", query="python")
        assert len(memories) == 2
        assert all("python" in m.content.lower() for m in memories)

    @pytest.mark.asyncio
    async def test_search_with_limit(self, memory_manager) -> None:
        """Test searching with limit"""
        await memory_manager.store(session_id="session_1", content="First")
        await memory_manager.store(session_id="session_1", content="Second")
        await memory_manager.store(session_id="session_1", content="Third")

        memories = await memory_manager.search("session_1", limit=2)
        assert len(memories) == 2

    @pytest.mark.asyncio
    async def test_search_with_offset(self, memory_manager) -> None:
        """Test searching with offset"""
        await memory_manager.store(session_id="session_1", content="First")
        await memory_manager.store(session_id="session_1", content="Second")
        await memory_manager.store(session_id="session_1", content="Third")

        memories = await memory_manager.search("session_1", offset=1)
        assert len(memories) == 2

    @pytest.mark.asyncio
    async def test_search_combined_filters(self, memory_manager) -> None:
        """Test searching with query, limit, and offset combined"""
        await memory_manager.store(session_id="session_1", content="Python code")
        await memory_manager.store(session_id="session_1", content="JavaScript code")
        await memory_manager.store(session_id="session_1", content="Python tutorial")

        memories = await memory_manager.search(
            session_id="session_1", query="python", limit=1, offset=0
        )
        assert len(memories) == 1
        assert "python" in memories[0].content.lower()

    @pytest.mark.asyncio
    async def test_delete_memory(self, memory_manager) -> None:
        """Test deleting a memory through MemoryManager"""
        memory = await memory_manager.store(
            session_id="session_1", content="Delete this"
        )

        deleted = await memory_manager.delete("session_1", memory.id)
        assert deleted is True

        retrieved = await memory_manager.retrieve("session_1", memory.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_memory(self, memory_manager) -> None:
        """Test deleting a non-existent memory"""
        deleted = await memory_manager.delete("session_1", "nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_summarize_empty(self, memory_manager) -> None:
        """Test summarizing when no memories exist"""
        summary = await memory_manager.summarize("session_1")
        assert summary["count"] == 0
        assert summary["total_characters"] == 0
        assert summary["memories"] == []

    @pytest.mark.asyncio
    async def test_summarize_with_memories(self, memory_manager) -> None:
        """Test summarizing with memories"""
        await memory_manager.store(session_id="session_1", content="First memory")
        await memory_manager.store(session_id="session_1", content="Second memory")
        await memory_manager.store(session_id="session_1", content="Third memory")

        summary = await memory_manager.summarize("session_1")
        assert summary["count"] == 3
        assert summary["total_characters"] == 37
        assert summary["oldest_timestamp"] is not None
        assert summary["newest_timestamp"] is not None
        assert len(summary["memories"]) == 3

    @pytest.mark.asyncio
    async def test_summarize_with_since(self, memory_manager) -> None:
        """Test summarizing with time filter"""
        # Store first memory
        await memory_manager.store(session_id="session_1", content="Old")

        # Get timestamp of first (oldest) memory
        first_summary = await memory_manager.summarize("session_1")
        # Memories are sorted descending, so last is oldest
        oldest_timestamp = first_summary["memories"][-1]["created"]

        # Store second memory (will have later timestamp)
        await memory_manager.store(session_id="session_1", content="New")

        # Filter by time between oldest and now
        summary = await memory_manager.summarize("session_1", since=oldest_timestamp)
        assert summary["count"] == 2
        assert "New" in [m["content"] for m in summary["memories"]]
        assert "Old" in [m["content"] for m in summary["memories"]]
