"""Test suite for session theme_id persistence.

Tests verify that:
- New sessions get default theme_id="aurora"
- Session with custom theme_id is persisted correctly
- Reading a session returns the correct theme_id
- Updating theme_id persists correctly
"""

import pytest
from pathlib import Path
import tempfile

from opencode_python.core.session import SessionManager
from opencode_python.storage.store import SessionStorage
from opencode_python.core.models import Session


@pytest.fixture
async def session_manager():
    """Create a SessionManager with temporary storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        storage = SessionStorage(tmp_path)
        project_dir = tmp_path / "test_project"
        project_dir.mkdir(exist_ok=True)
        manager = SessionManager(storage=storage, project_dir=project_dir)
        yield manager


class TestSessionThemeIdPersistence:
    """Tests for theme_id field in Session model and persistence."""

    @pytest.mark.asyncio
    async def test_new_session_has_default_theme_id(self, session_manager):
        """Test that new sessions get default theme_id='aurora'."""
        session = await session_manager.create(title="Test Session")

        assert session.theme_id == "aurora"

    @pytest.mark.asyncio
    async def test_new_session_with_custom_theme_id(self, session_manager):
        """Test that new sessions can be created with custom theme_id."""
        session = await session_manager.create(title="Test Session")
        updated_session = await session_manager.update_session(
            session.id,
            theme_id="ocean"
        )

        assert updated_session.theme_id == "ocean"

    @pytest.mark.asyncio
    async def test_theme_id_persisted_to_storage(self, session_manager):
        """Test that theme_id is persisted to storage and can be retrieved."""
        session = await session_manager.create(title="Test Session")

        retrieved_session = await session_manager.get_session(session.id)

        assert retrieved_session is not None
        assert retrieved_session.theme_id == "aurora"

    @pytest.mark.asyncio
    async def test_custom_theme_id_persisted_to_storage(self, session_manager):
        """Test that custom theme_id is persisted to storage and can be retrieved."""
        session = await session_manager.create(title="Test Session")
        updated_session = await session_manager.update_session(
            session.id,
            theme_id="ember"
        )

        retrieved_session = await session_manager.get_session(session.id)

        assert retrieved_session is not None
        assert retrieved_session.theme_id == "ember"

    @pytest.mark.asyncio
    async def test_theme_id_update_persists_across_reads(self, session_manager):
        """Test that theme_id updates persist across multiple reads."""
        session = await session_manager.create(title="Test Session")
        assert session.theme_id == "aurora"

        updated_ocean = await session_manager.update_session(
            session.id,
            theme_id="ocean"
        )
        assert updated_ocean.theme_id == "ocean"

        retrieved_ocean = await session_manager.get_session(session.id)
        assert retrieved_ocean.theme_id == "ocean"

        updated_ember = await session_manager.update_session(
            session.id,
            theme_id="ember"
        )
        assert updated_ember.theme_id == "ember"

        retrieved_ember = await session_manager.get_session(session.id)
        assert retrieved_ember.theme_id == "ember"

    @pytest.mark.asyncio
    async def test_all_theme_presets_are_valid(self, session_manager):
        """Test that all valid theme presets work correctly."""
        session = await session_manager.create(title="Test Session")

        theme_presets = ["aurora", "ocean", "ember"]

        for theme_id in theme_presets:
            updated = await session_manager.update_session(
                session.id,
                theme_id=theme_id
            )
            assert updated.theme_id == theme_id

            retrieved = await session_manager.get_session(session.id)
            assert retrieved.theme_id == theme_id
