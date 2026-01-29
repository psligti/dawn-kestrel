"""Tests for SessionManager thread safety and concurrency.

Tests concurrent operations and data consistency under high concurrency scenarios.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock
import pytest

from opencode_python.core.session import SessionManager
from opencode_python.core.models import Session


@pytest.fixture
def mock_storage() -> AsyncMock:
    """Create mock SessionStorage."""
    storage = AsyncMock()
    storage.base_dir = Path("/tmp/test")
    storage.create_session = AsyncMock()
    storage.delete_session = AsyncMock(return_value=True)
    storage.get_session = AsyncMock()
    storage.list_sessions = AsyncMock(return_value=[])
    return storage


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create temporary project directory."""
    return tmp_path / "project"


@pytest.fixture
def session_manager(mock_storage: AsyncMock, project_dir: Path) -> SessionManager:
    """Create SessionManager instance."""
    return SessionManager(
        storage=mock_storage,
        project_dir=project_dir,
    )


class TestSessionManagerConcurrentCreateSession:
    """Tests for SessionManager.create_session thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_create_session_does_not_corrupt_data(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test concurrent create_session() doesn't corrupt data."""
        manager = SessionManager(
            storage=mock_storage,
            project_dir=project_dir,
        )

        created_sessions = []

        async def create_session_task(index: int) -> None:
            session = Session(
                id=f"session-{index}",
                title=f"Session {index}",
                slug=f"session-{index}",
                project_id=project_dir.name,
                directory=str(project_dir),
                version="1.0.0",
            )
            mock_storage.create_session.return_value = session
            result = await manager.create(title=f"Session {index}")
            created_sessions.append(result.id)

        tasks = [create_session_task(i) for i in range(10)]
        await asyncio.gather(*tasks)

        assert len(created_sessions) == 10
        assert len(set(created_sessions)) == 10

    @pytest.mark.asyncio
    async def test_concurrent_create_with_unique_ids(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test concurrent create operations generate unique session IDs."""
        manager = SessionManager(
            storage=mock_storage,
            project_dir=project_dir,
        )

        sessions = []

        async def create_task(title: str) -> None:
            session = Session(
                id=f"test-{title}",
                title=title,
                slug=title.lower().replace(" ", "-"),
                project_id=project_dir.name,
                directory=str(project_dir),
                version="1.0.0",
            )
            mock_storage.create_session.return_value = session
            result = await manager.create(title=title)
            sessions.append(result.id)

        tasks = [create_task(f"Session {i}") for i in range(20)]
        await asyncio.gather(*tasks)

        assert len(sessions) == 20
        assert len(set(sessions)) == 20

    @pytest.mark.asyncio
    async def test_concurrent_create_preserves_session_attributes(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test concurrent create operations preserve all session attributes."""
        manager = SessionManager(
            storage=mock_storage,
            project_dir=project_dir,
        )

        sessions = []

        async def create_task(index: int) -> None:
            session = Session(
                id=f"session-{index}",
                title=f"Session {index}",
                slug=f"session-{index}",
                project_id=project_dir.name,
                directory=str(project_dir),
                version="1.0.0",
            )
            mock_storage.create_session.return_value = session
            result = await manager.create(title=f"Session {index}")
            sessions.append({
                "id": result.id,
                "title": result.title,
                "slug": result.slug,
                "project_id": result.project_id,
            })

        tasks = [create_task(i) for i in range(10)]
        await asyncio.gather(*tasks)

        assert all(s["title"].startswith("Session ") for s in sessions)
        assert all(s["slug"].startswith("session-") for s in sessions)
        assert all(s["project_id"] == project_dir.name for s in sessions)


class TestSessionManagerConcurrentDeleteSession:
    """Tests for SessionManager.delete_session thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_delete_session_does_not_corrupt_data(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test concurrent delete_session() doesn't corrupt data."""
        manager = SessionManager(
            storage=mock_storage,
            project_dir=project_dir,
        )

        deleted_count = [0]

        async def delete_session_task(session_id: str) -> None:
            result = await manager.delete_session(session_id)
            if result:
                deleted_count[0] += 1

        tasks = [delete_session_task(f"session-{i}") for i in range(10)]
        await asyncio.gather(*tasks)

        assert deleted_count[0] == 10


class TestSessionManagerConcurrentMixedOperations:
    """Tests for SessionManager concurrent create and get operations."""

    @pytest.mark.asyncio
    async def test_concurrent_create_and_get_operations_are_safe(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test concurrent create() and get() operations are safe."""
        manager = SessionManager(
            storage=mock_storage,
            project_dir=project_dir,
        )

        session = Session(
            id="test-id",
            title="Test",
            slug="test",
            project_id=project_dir.name,
            directory=str(project_dir),
            version="1.0.0",
        )
        mock_storage.create_session.return_value = session
        mock_storage.get_session.return_value = session

        results = []

        async def create_task() -> None:
            result = await manager.create(title="Test")
            results.append(("create", result.id))

        async def get_task() -> None:
            result = await manager.get_session("test-id")
            results.append(("get", result.id if result else None))

        tasks = [create_task() for _ in range(5)] + [get_task() for _ in range(5)]
        await asyncio.gather(*tasks)

        assert len(results) == 10
        assert sum(1 for op, _ in results if op == "create") == 5
        assert sum(1 for op, _ in results if op == "get") == 5


class TestSessionManagerHighConcurrency:
    """Tests for SessionManager under high concurrency (100+ operations)."""

    @pytest.mark.asyncio
    async def test_high_concurrency_maintains_consistency(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test high concurrency (100+ operations) maintains consistency."""
        manager = SessionManager(
            storage=mock_storage,
            project_dir=project_dir,
        )

        operation_count = 100
        results = []

        async def perform_operation(index: int) -> None:
            if index % 2 == 0:
                session = Session(
                    id="test-id",
                    title="Test",
                    slug="test",
                    project_id=project_dir.name,
                    directory=str(project_dir),
                    version="1.0.0",
                )
                mock_storage.create_session.return_value = session
                result = await manager.create(title=f"Session {index}")
                results.append(("create", result.id))
            else:
                session = Session(
                    id=f"session-{index}",
                    title="Test",
                    slug="test",
                    project_id=project_dir.name,
                    directory=str(project_dir),
                    version="1.0.0",
                )
                mock_storage.get_session.return_value = session
                result = await manager.get_session(f"session-{index}")
                results.append(("get", result.id if result else None))

        tasks = [perform_operation(i) for i in range(operation_count)]
        await asyncio.gather(*tasks)

        assert len(results) == operation_count


class TestSessionManagerReadOnlyOperations:
    """Tests for SessionManager read-only operations."""

    @pytest.mark.asyncio
    async def test_read_only_operations_get_session_works(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test read-only operations (get_session) work correctly."""
        manager = SessionManager(
            storage=mock_storage,
            project_dir=project_dir,
        )

        session = Session(
            id="test-id",
            title="Test",
            slug="test",
            project_id=project_dir.name,
            directory=str(project_dir),
            version="1.0.0",
        )
        mock_storage.get_session.return_value = session

        result = await manager.get_session("test-id")

        assert result is not None
        assert result.id == "test-id"

    @pytest.mark.asyncio
    async def test_read_only_operations_list_sessions_work(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test read-only operations (list_sessions) work correctly."""
        manager = SessionManager(
            storage=mock_storage,
            project_dir=project_dir,
        )

        sessions = [
            Session(id=f"{i}", title=f"Session {i}", slug=f"session-{i}", project_id=project_dir.name, directory=str(project_dir), version="1.0.0")
            for i in range(3)
        ]
        mock_storage.list_sessions.return_value = sessions

        result = await manager.list_sessions()

        assert len(result) == 3
        assert all(isinstance(s, Session) for s in result)

    @pytest.mark.asyncio
    async def test_concurrent_get_session_does_not_corrupt(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test concurrent get_session operations don't corrupt data."""
        manager = SessionManager(
            storage=mock_storage,
            project_dir=project_dir,
        )

        session = Session(
            id="test-id",
            title="Test",
            slug="test",
            project_id=project_dir.name,
            directory=str(project_dir),
            version="1.0.0",
        )
        mock_storage.get_session.return_value = session

        results = []

        async def get_task(session_id: str) -> None:
            result = await manager.get_session(session_id)
            results.append(result.id if result else None)

        tasks = [get_task("test-id") for _ in range(10)]
        await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r == "test-id" for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_list_sessions_does_not_corrupt(
        self, mock_storage: AsyncMock, project_dir: Path
    ) -> None:
        """Test concurrent list_sessions operations don't corrupt data."""
        manager = SessionManager(
            storage=mock_storage,
            project_dir=project_dir,
        )

        sessions = [
            Session(id=f"{i}", title=f"Session {i}", slug=f"session-{i}", project_id=project_dir.name, directory=str(project_dir), version="1.0.0")
            for i in range(5)
        ]
        mock_storage.list_sessions.return_value = sessions

        results = []

        async def list_task() -> None:
            result = await manager.list_sessions()
            results.append(len(result))

        tasks = [list_task() for _ in range(10)]
        await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r == 5 for r in results)
