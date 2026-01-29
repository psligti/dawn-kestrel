"""
Test suite for session export/import functionality.
"""

import json
import pytest
from pathlib import Path
from io import StringIO
import sys

sys.path.insert(0, str(Path(__file__).parent))

from opencode_python.session.import_export import SessionImportExport, create_import_export_manager
from opencode_python.core.models import Session


@pytest.fixture
def temp_session():
    """Create a temporary session for testing"""
    import tempfile
    from opencode_python.core.session import SessionManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        session_mgr = SessionManager(storage_dir=Path(tmpdir))
        session_obj = session_mgr.create(
            directory=Path(tmpdir),
            title="Test Session"
        )
        
        msg = session_mgr.create_message(
            session_id=session_obj.id,
            role="user",
            parts=[]
        )
        
        part = session_mgr.create_part(
            session_id=session_obj.id,
            message_id=msg.id,
            part_type="text",
            text="Test message content"
        )
        
        await session_mgr.add_part(part)
        await session_mgr.add_message(msg)
        
        yield session_mgr, session_obj


@pytest.mark.asyncio
async def test_session_export(temp_session):
    """Test session export to JSON"""
    session_mgr, session_obj = await temp_session()
    
    exporter = create_import_export_manager(session_obj)
    export_data = await exporter.export_session()
    
    assert export_data["session"]["id"] == session_obj.id
    assert "messages" in export_data
    assert "parts" in export_data
    assert export_data["exported_at"]
    
    message_count = len(export_data["messages"])
    part_count = len(export_data["parts"])
    
    assert message_count == 1
    assert part_count == 2
    
    print(f"Test session export: {message_count} messages, {part_count} parts")


@pytest.mark.asyncio
async def test_session_export_to_file(temp_session, tmp_path):
    """Test exporting session to file"""
    session_mgr, session_obj = await temp_session()
    
    exporter = create_import_export_manager(session_obj)
    export_data = await exporter.export_session()
    
    export_path = tmp_path / "test_export.json"
    exporter.export_to_file(str(export_path), export_data)
    
    assert export_path.exists()
    
    with open(export_path, "r") as f:
        loaded = json.load(f)
    
    assert loaded["session"]["id"] == session_obj.id
    assert "messages" in loaded
    assert "parts" in loaded
