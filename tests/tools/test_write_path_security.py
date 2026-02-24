"""Tests for WriteTool path traversal protection.

TDD tests for applying safe_path() validation to WriteTool.
These tests verify that path traversal attacks are blocked.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from dawn_kestrel.core.security import SecurityError
from dawn_kestrel.tools.builtin import WriteTool
from dawn_kestrel.tools.framework import ToolContext


@pytest.fixture
def tool_context():
    """Create a minimal ToolContext for testing."""
    return ToolContext(
        session_id="test-session",
        message_id="test-message",
        agent="test-agent",
        abort=asyncio.Event(),
        messages=[],
    )


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


class TestWriteToolPathSecurity:
    """Test suite for WriteTool path traversal protection."""

    @pytest.mark.asyncio
    async def test_blocks_path_traversal_with_dotdot(
        self, tool_context, temp_workspace, monkeypatch
    ):
        """WriteTool should block attempts to write outside workspace using .."""
        # Change to temp workspace
        monkeypatch.chdir(temp_workspace)

        tool = WriteTool()
        args = {
            "filePath": "../malicious.txt",
            "content": "malicious content",
        }

        result = await tool.execute(args, tool_context)

        assert result.metadata.get("security_error") is True
        assert "traversal" in result.output.lower() or "security" in result.output.lower()

    @pytest.mark.asyncio
    async def test_blocks_path_traversal_with_dotdot(
        self, tool_context, temp_workspace, monkeypatch
    ):
        """WriteTool should block attempts to write outside workspace using .."""
        monkeypatch.chdir(temp_workspace)

        tool = WriteTool()
        args = {
            "filePath": "subdir/../../../tmp/malicious.txt",
            "content": "malicious content",
        }

        result = await tool.execute(args, tool_context)

        assert result.metadata.get("security_error") is True

    @pytest.mark.asyncio
    async def test_blocks_directory_creation_outside_workspace(
        self, tool_context, temp_workspace, monkeypatch
    ):
        """WriteTool should block create_dirs that would create directories outside workspace."""
        monkeypatch.chdir(temp_workspace)

        tool = WriteTool()
        args = {
            "filePath": "../outside_dir/file.txt",
            "content": "content",
            "create": True,
        }

        result = await tool.execute(args, tool_context)

        assert result.metadata.get("security_error") is True

    @pytest.mark.asyncio
    async def test_blocks_absolute_path(self, tool_context, temp_workspace, monkeypatch):
        """WriteTool should block absolute paths by default."""
        monkeypatch.chdir(temp_workspace)

        tool = WriteTool()
        args = {
            "filePath": "/tmp/malicious.txt",
            "content": "malicious content",
        }

        result = await tool.execute(args, tool_context)

        assert result.metadata.get("security_error") is True
        assert "absolute" in result.output.lower()

    @pytest.mark.asyncio
    async def test_allows_valid_relative_path(self, tool_context, temp_workspace, monkeypatch):
        """WriteTool should allow valid relative paths within workspace."""
        monkeypatch.chdir(temp_workspace)

        tool = WriteTool()
        args = {
            "filePath": "valid_file.txt",
            "content": "valid content",
        }

        result = await tool.execute(args, tool_context)

        assert result.metadata.get("security_error") is not True
        assert result.metadata.get("error") is None
        assert (temp_workspace / "valid_file.txt").exists()
        assert (temp_workspace / "valid_file.txt").read_text() == "valid content"

    @pytest.mark.asyncio
    async def test_allows_nested_directory_within_workspace(
        self, tool_context, temp_workspace, monkeypatch
    ):
        """WriteTool should allow creating nested directories within workspace."""
        monkeypatch.chdir(temp_workspace)

        tool = WriteTool()
        args = {
            "filePath": "subdir/nested/file.txt",
            "content": "nested content",
            "create": True,
        }

        result = await tool.execute(args, tool_context)

        assert result.metadata.get("security_error") is not True
        assert result.metadata.get("error") is None
        assert (temp_workspace / "subdir" / "nested" / "file.txt").exists()

    @pytest.mark.asyncio
    async def test_blocks_null_byte_in_path(self, tool_context, temp_workspace, monkeypatch):
        """WriteTool should block paths containing null bytes."""
        monkeypatch.chdir(temp_workspace)

        tool = WriteTool()
        args = {
            "filePath": "file.txt\x00malicious",
            "content": "content",
        }

        result = await tool.execute(args, tool_context)

        assert result.metadata.get("security_error") is True

    @pytest.mark.asyncio
    async def test_security_error_returns_proper_metadata(
        self, tool_context, temp_workspace, monkeypatch
    ):
        """Security errors should return proper metadata with security_error=True."""
        monkeypatch.chdir(temp_workspace)

        tool = WriteTool()
        args = {
            "filePath": "../escape.txt",
            "content": "content",
        }

        result = await tool.execute(args, tool_context)

        assert "security_error" in result.metadata
        assert result.metadata["security_error"] is True
        assert "error" in result.metadata
        assert isinstance(result.metadata["error"], str)
