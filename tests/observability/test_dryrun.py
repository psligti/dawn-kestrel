"""Tests for dry-run mode and diff/patch preview"""
import pytest
from opencode_python.observability.dryrun import DryRunManager


@pytest.fixture
def dryrun_manager():
    """Create a dry-run manager for testing"""
    return DryRunManager(enabled=True)


@pytest.fixture
def dryrun_disabled_manager():
    """Create a dry-run manager with dry-run disabled"""
    return DryRunManager(enabled=False)


@pytest.mark.asyncio
async def test_enabled_property(dryrun_manager):
    """Test checking if dry-run is enabled"""
    assert dryrun_manager.enabled is True


@pytest.mark.asyncio
async def test_disabled_property(dryrun_disabled_manager):
    """Test checking if dry-run is disabled"""
    assert dryrun_disabled_manager.enabled is False


@pytest.mark.asyncio
async def test_toggle_enabled_to_disabled(dryrun_manager):
    """Test toggling dry-run from enabled to disabled"""
    assert dryrun_manager.enabled is True

    new_state = await dryrun_manager.toggle()

    assert new_state is False
    assert dryrun_manager.enabled is False


@pytest.mark.asyncio
async def test_toggle_disabled_to_enabled(dryrun_disabled_manager):
    """Test toggling dry-run from disabled to enabled"""
    assert dryrun_disabled_manager.enabled is False

    new_state = await dryrun_disabled_manager.toggle()

    assert new_state is True
    assert dryrun_disabled_manager.enabled is True


@pytest.mark.asyncio
async def test_set_enabled(dryrun_disabled_manager):
    """Test setting dry-run to enabled"""
    new_state = await dryrun_disabled_manager.toggle(enabled=True)

    assert new_state is True
    assert dryrun_disabled_manager.enabled is True


@pytest.mark.asyncio
async def test_preview_write_enabled(dryrun_manager):
    """Test previewing a file write when dry-run is enabled"""
    new_content = "def new_function():\n    pass\n"
    original_content = "def old_function():\n    pass\n"

    preview = await dryrun_manager.preview_write(
        file_path="test.py",
        new_content=new_content,
        original_content=original_content,
    )

    assert preview["dry_run"] is True
    assert preview["would_write"] is True
    assert preview["file_path"] == "test.py"
    assert "diff" in preview
    assert "old_function" in preview["diff"]
    assert "new_function" in preview["diff"]


@pytest.mark.asyncio
async def test_preview_write_disabled(dryrun_disabled_manager):
    """Test previewing a file write when dry-run is disabled"""
    preview = await dryrun_disabled_manager.preview_write(
        file_path="test.py",
        new_content="new content",
    )

    assert preview["dry_run"] is False
    assert preview["would_write"] is False


@pytest.mark.asyncio
async def test_preview_write_no_changes(dryrun_manager):
    """Test previewing a write with no changes"""
    content = "same content"

    preview = await dryrun_manager.preview_write(
        file_path="test.py",
        new_content=content,
        original_content=content,
    )

    assert preview["dry_run"] is True
    assert preview["diff"] == "(no changes)"


@pytest.mark.asyncio
async def test_preview_delete_enabled(dryrun_manager, tmp_path):
    """Test previewing a file delete when dry-run is enabled"""
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test content")

    preview = await dryrun_manager.preview_delete(str(test_file))

    assert preview["dry_run"] is True
    assert preview["would_delete"] is True
    assert preview["file_path"] == str(test_file)
    assert preview["file_exists"] is True


@pytest.mark.asyncio
async def test_preview_delete_disabled(dryrun_disabled_manager):
    """Test previewing a file delete when dry-run is disabled"""
    preview = await dryrun_disabled_manager.preview_delete("test.py")

    assert preview["dry_run"] is False
    assert preview["would_delete"] is False


@pytest.mark.asyncio
async def test_preview_bulk_changes(dryrun_manager):
    """Test previewing bulk file changes"""
    changes = [
        {"action": "write", "file_path": "file1.py", "content": "content 1"},
        {"action": "write", "file_path": "file2.py", "content": "content 2"},
        {"action": "delete", "file_path": "old_file.py"},
    ]

    preview = await dryrun_manager.preview_bulk_changes(changes)

    assert preview["dry_run"] is True
    assert preview["changes_count"] == 3
    assert len(preview["previews"]) == 3
    assert "total_diff" in preview
    assert preview["previews"][0]["would_write"] is True
    assert preview["previews"][2]["would_delete"] is True


@pytest.mark.asyncio
async def test_preview_bulk_changes_disabled(dryrun_disabled_manager):
    """Test previewing bulk changes when dry-run is disabled"""
    changes = [{"action": "write", "file_path": "file.py", "content": "content"}]

    preview = await dryrun_disabled_manager.preview_bulk_changes(changes)

    assert preview["dry_run"] is False
    assert preview["changes_count"] == 0


@pytest.mark.asyncio
async def test_record_dry_run(dryrun_manager):
    """Test recording a dry-run preview for a session"""
    preview = {"dry_run": True, "file_path": "test.py"}

    await dryrun_manager.record_dry_run("session-1", preview)

    dry_runs = dryrun_manager.get_dry_runs("session-1")

    assert len(dry_runs) == 1
    assert dry_runs[0] == preview


@pytest.mark.asyncio
async def test_get_dry_runs_multiple(dryrun_manager):
    """Test getting multiple dry-runs for a session"""
    preview1 = {"dry_run": True, "file_path": "file1.py"}
    preview2 = {"dry_run": True, "file_path": "file2.py"}

    await dryrun_manager.record_dry_run("session-1", preview1)
    await dryrun_manager.record_dry_run("session-1", preview2)

    dry_runs = dryrun_manager.get_dry_runs("session-1")

    assert len(dry_runs) == 2
    assert dry_runs[0] == preview1
    assert dry_runs[1] == preview2


@pytest.mark.asyncio
async def test_get_dry_runs_nonexistent_session(dryrun_manager):
    """Test getting dry-runs for nonexistent session"""
    dry_runs = dryrun_manager.get_dry_runs("nonexistent")
    assert dry_runs == []


def test_generate_diff():
    """Test generating unified diff between two strings"""
    manager = DryRunManager()

    original = "line 1\nline 2\nline 3\n"
    modified = "line 1\nline 2 modified\nline 3\n"

    diff = manager._generate_diff(original, modified, "test.txt")

    assert "line 2 modified" in diff
    assert "-line 2" in diff
    assert "+line 2 modified" in diff


def test_generate_diff_no_changes():
    """Test generating diff when content is identical"""
    manager = DryRunManager()

    content = "same content"
    diff = manager._generate_diff(content, content, "test.txt")

    assert diff == "(no changes)"


def test_generate_diff_empty_strings():
    """Test generating diff between empty strings"""
    manager = DryRunManager()

    diff = manager._generate_diff("", "", "test.txt")

    assert diff == "(no changes)"
