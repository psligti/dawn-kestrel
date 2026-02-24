"""Security tests for ReadTool path traversal protection.

Tests that ReadTool validates all paths using safe_path() to prevent:
- Path traversal attacks (../etc/passwd)
- Absolute path access (/etc/passwd)
- Null byte injection
- Symlink escapes (if applicable)
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from dawn_kestrel.tools.builtin import ReadTool
from dawn_kestrel.tools.framework import ToolContext


def make_context() -> ToolContext:
    """Create a minimal ToolContext for testing."""
    return ToolContext(
        session_id="test-session",
        message_id="test-message",
        agent="test-agent",
        abort=asyncio.Event(),
        messages=[],
    )


class TestReadToolPathSecurity:
    """Test ReadTool path security validation."""

    @pytest.mark.asyncio
    async def test_path_traversal_attack_blocked(self):
        """Verify path traversal with ../ is blocked."""
        tool = ReadTool()
        ctx = make_context()

        result = await tool.execute({"filePath": "../etc/passwd"}, ctx)

        assert result.metadata.get("security_error") is True
        assert "traversal" in result.output.lower() or "security" in result.output.lower()

    @pytest.mark.asyncio
    async def test_absolute_path_blocked(self):
        """Verify absolute paths are blocked by default."""
        tool = ReadTool()
        ctx = make_context()

        result = await tool.execute({"filePath": "/etc/passwd"}, ctx)

        assert result.metadata.get("security_error") is True
        assert "absolute" in result.output.lower() or "security" in result.output.lower()

    @pytest.mark.asyncio
    async def test_null_byte_injection_blocked(self):
        """Verify null bytes in path are blocked."""
        tool = ReadTool()
        ctx = make_context()

        result = await tool.execute({"filePath": "safe.txt\x00../../../etc/passwd"}, ctx)

        assert result.metadata.get("security_error") is True
        assert "null" in result.output.lower() or "security" in result.output.lower()

    @pytest.mark.asyncio
    async def test_complex_path_traversal_blocked(self):
        """Verify complex path traversal attempts are blocked."""
        tool = ReadTool()
        ctx = make_context()

        # Try multiple levels of traversal
        result = await tool.execute({"filePath": "subdir/../../../etc/passwd"}, ctx)

        assert result.metadata.get("security_error") is True

    @pytest.mark.asyncio
    async def test_backslash_traversal_blocked(self):
        """Verify backslash traversal attempts are blocked."""
        tool = ReadTool()
        ctx = make_context()

        result = await tool.execute({"filePath": "..\\..\\etc\\passwd"}, ctx)

        assert result.metadata.get("security_error") is True

    @pytest.mark.asyncio
    async def test_valid_relative_path_allowed(self):
        """Verify valid relative paths within workspace are allowed."""
        tool = ReadTool()
        ctx = make_context()

        # Create a temp file to read
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name).name  # Just the filename, relative

        # Change to temp dir to test relative path
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(Path(tempfile.gettempdir()))
            result = await tool.execute({"filePath": temp_path}, ctx)

            # Should NOT have security error for valid relative path
            assert result.metadata.get("security_error") is not True
            assert "test content" in result.output
        finally:
            os.chdir(old_cwd)
            (Path(tempfile.gettempdir()) / temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error_not_security_error(self):
        """Verify file not found is distinct from security error."""
        tool = ReadTool()
        ctx = make_context()

        result = await tool.execute({"filePath": "nonexistent_safe_file.txt"}, ctx)

        # Should be file not found, NOT security error
        assert result.metadata.get("security_error") is not True
        assert "not found" in result.title.lower() or "error" in result.title.lower()

    @pytest.mark.asyncio
    async def test_empty_path_returns_error(self):
        """Verify empty path is handled gracefully."""
        tool = ReadTool()
        ctx = make_context()

        result = await tool.execute({"filePath": ""}, ctx)

        # Should return error (could be security error for empty path)
        assert (
            result.metadata.get("error") is not None
            or result.metadata.get("security_error") is True
        )
