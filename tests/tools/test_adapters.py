"""Tests for ToolAdapter pattern.

Tests cover protocol compliance, adapter implementations, and registration system.
Follows TDD workflow: RED-GREEN-REFACTOR.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dawn_kestrel.tools.framework import ToolContext, ToolResult
from dawn_kestrel.core.result import Ok, Err

# Note: These tests will fail initially (RED phase)
# Import will fail until adapters module is created
try:
    from dawn_kestrel.tools.adapters import (
        ToolAdapter,
        BashToolAdapter,
        ReadToolAdapter,
        WriteToolAdapter,
        GenericToolAdapter,
        register_adapter,
        get_adapter,
        list_adapters,
    )

    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    pytest.skip("adapters module not yet implemented", allow_module_level=True)

# =============================================================================
# Protocol Tests
# =============================================================================


def test_adapter_has_execute_method():
    """Test ToolAdapter protocol has execute method."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock a tool
    mock_tool = AsyncMock()
    adapter = BashToolAdapter(mock_tool)

    # Verify method exists (callable)
    assert callable(adapter.execute)


def test_adapter_has_get_tool_name_method():
    """Test ToolAdapter protocol has get_tool_name method."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock a tool
    mock_tool = AsyncMock()
    adapter = BashToolAdapter(mock_tool)

    # Verify method exists (callable)
    assert callable(adapter.get_tool_name)


# =============================================================================
# BashToolAdapter Tests
# =============================================================================


@pytest.mark.asyncio
async def test_bash_adapter_wraps_tool():
    """Test BashToolAdapter wraps tool correctly."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool
    mock_tool = MagicMock()
    adapter = BashToolAdapter(mock_tool)

    # Verify adapter wraps tool
    assert adapter._tool is mock_tool


@pytest.mark.asyncio
async def test_bash_adapter_returns_ok_on_success():
    """Test BashToolAdapter returns Ok on successful execution."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool
    mock_tool = AsyncMock()
    mock_tool.execute = AsyncMock(
        return_value=ToolResult(
            title="Success",
            output="Command executed",
            metadata={"exit_code": 0},
        )
    )

    # Create adapter
    adapter = BashToolAdapter(mock_tool)

    # Create context
    context = ToolContext(
        session_id="test_session",
        message_id="test_message",
        agent="test_agent",
        abort=MagicMock(),
        messages=[],
    )

    # Execute via adapter
    result = await adapter.execute(context, command="echo hello")

    # Verify Ok result
    assert result.is_ok()
    output = result.unwrap()
    assert isinstance(output, dict)


@pytest.mark.asyncio
async def test_bash_adapter_returns_err_on_failure():
    """Test BashToolAdapter returns Err on tool error."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool that raises exception
    mock_tool = AsyncMock()
    mock_tool.execute = AsyncMock(side_effect=Exception("Bash error"))

    # Create adapter
    adapter = BashToolAdapter(mock_tool)

    # Create context
    context = ToolContext(
        session_id="test_session",
        message_id="test_message",
        agent="test_agent",
        abort=MagicMock(),
        messages=[],
    )

    # Execute via adapter
    result = await adapter.execute(context, command="invalid")

    # Verify Err result
    assert result.is_err()
    assert "TOOL_ERROR" in str(result)


@pytest.mark.asyncio
async def test_bash_adapter_gets_tool_name():
    """Test BashToolAdapter returns correct tool name."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool
    mock_tool = MagicMock()
    adapter = BashToolAdapter(mock_tool)

    # Test tool name
    name = await adapter.get_tool_name()
    assert name == "bash"


# =============================================================================
# ReadToolAdapter Tests
# =============================================================================


@pytest.mark.asyncio
async def test_read_adapter_wraps_tool():
    """Test ReadToolAdapter wraps tool correctly."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool
    mock_tool = MagicMock()
    adapter = ReadToolAdapter(mock_tool)

    # Verify adapter wraps tool
    assert adapter._tool is mock_tool


@pytest.mark.asyncio
async def test_read_adapter_returns_ok_on_success():
    """Test ReadToolAdapter returns Ok on successful read."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool
    mock_tool = AsyncMock()
    mock_tool.execute = AsyncMock(
        return_value=ToolResult(
            title="Read file",
            output="File content",
            metadata={"path": "test.txt"},
        )
    )

    # Create adapter
    adapter = ReadToolAdapter(mock_tool)

    # Create context
    context = ToolContext(
        session_id="test_session",
        message_id="test_message",
        agent="test_agent",
        abort=MagicMock(),
        messages=[],
    )

    # Execute via adapter
    result = await adapter.execute(context, filePath="test.txt")

    # Verify Ok result
    assert result.is_ok()
    output = result.unwrap()
    assert isinstance(output, dict)


@pytest.mark.asyncio
async def test_read_adapter_returns_err_on_failure():
    """Test ReadToolAdapter returns Err on tool error."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool that raises exception
    mock_tool = AsyncMock()
    mock_tool.execute = AsyncMock(side_effect=Exception("Read error"))

    # Create adapter
    adapter = ReadToolAdapter(mock_tool)

    # Create context
    context = ToolContext(
        session_id="test_session",
        message_id="test_message",
        agent="test_agent",
        abort=MagicMock(),
        messages=[],
    )

    # Execute via adapter
    result = await adapter.execute(context, filePath="nonexistent.txt")

    # Verify Err result
    assert result.is_err()
    assert "TOOL_ERROR" in str(result)


@pytest.mark.asyncio
async def test_read_adapter_gets_tool_name():
    """Test ReadToolAdapter returns correct tool name."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool
    mock_tool = MagicMock()
    adapter = ReadToolAdapter(mock_tool)

    # Test tool name
    name = await adapter.get_tool_name()
    assert name == "read"


# =============================================================================
# WriteToolAdapter Tests
# =============================================================================


@pytest.mark.asyncio
async def test_write_adapter_wraps_tool():
    """Test WriteToolAdapter wraps tool correctly."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool
    mock_tool = MagicMock()
    adapter = WriteToolAdapter(mock_tool)

    # Verify adapter wraps tool
    assert adapter._tool is mock_tool


@pytest.mark.asyncio
async def test_write_adapter_returns_ok_on_success():
    """Test WriteToolAdapter returns Ok on successful write."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool
    mock_tool = AsyncMock()
    mock_tool.execute = AsyncMock(
        return_value=ToolResult(
            title="Wrote file",
            output="Written 10 bytes",
            metadata={"path": "test.txt", "bytes": 10},
        )
    )

    # Create adapter
    adapter = WriteToolAdapter(mock_tool)

    # Create context
    context = ToolContext(
        session_id="test_session",
        message_id="test_message",
        agent="test_agent",
        abort=MagicMock(),
        messages=[],
    )

    # Execute via adapter
    result = await adapter.execute(context, filePath="test.txt", content="Hello")

    # Verify Ok result
    assert result.is_ok()
    output = result.unwrap()
    assert isinstance(output, dict)


@pytest.mark.asyncio
async def test_write_adapter_returns_err_on_failure():
    """Test WriteToolAdapter returns Err on tool error."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool that raises exception
    mock_tool = AsyncMock()
    mock_tool.execute = AsyncMock(side_effect=Exception("Write error"))

    # Create adapter
    adapter = WriteToolAdapter(mock_tool)

    # Create context
    context = ToolContext(
        session_id="test_session",
        message_id="test_message",
        agent="test_agent",
        abort=MagicMock(),
        messages=[],
    )

    # Execute via adapter
    result = await adapter.execute(context, filePath="/readonly/file.txt", content="test")

    # Verify Err result
    assert result.is_err()
    assert "TOOL_ERROR" in str(result)


@pytest.mark.asyncio
async def test_write_adapter_gets_tool_name():
    """Test WriteToolAdapter returns correct tool name."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool
    mock_tool = MagicMock()
    adapter = WriteToolAdapter(mock_tool)

    # Test tool name
    name = await adapter.get_tool_name()
    assert name == "write"


# =============================================================================
# GenericToolAdapter Tests
# =============================================================================


@pytest.mark.asyncio
async def test_generic_adapter_wraps_tool():
    """Test GenericToolAdapter wraps tool correctly."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool with name attribute
    mock_tool = MagicMock()
    mock_tool.name = "custom_tool"
    adapter = GenericToolAdapter(mock_tool)

    # Verify adapter wraps tool
    assert adapter._tool is mock_tool


@pytest.mark.asyncio
async def test_generic_adapter_returns_ok_on_success():
    """Test GenericToolAdapter returns Ok on successful execution."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool
    mock_tool = MagicMock()
    mock_tool.name = "custom_tool"
    mock_tool.execute = AsyncMock(
        return_value=ToolResult(
            title="Success",
            output="Tool executed",
            metadata={},
        )
    )

    # Create adapter
    adapter = GenericToolAdapter(mock_tool)

    # Create context
    context = ToolContext(
        session_id="test_session",
        message_id="test_message",
        agent="test_agent",
        abort=MagicMock(),
        messages=[],
    )

    # Execute via adapter
    result = await adapter.execute(context, param="value")

    # Verify Ok result
    assert result.is_ok()
    output = result.unwrap()
    assert isinstance(output, dict)


@pytest.mark.asyncio
async def test_generic_adapter_returns_err_on_failure():
    """Test GenericToolAdapter returns Err on tool error."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock tool that raises exception
    mock_tool = MagicMock()
    mock_tool.name = "failing_tool"
    mock_tool.execute = AsyncMock(side_effect=Exception("Tool failed"))

    # Create adapter
    adapter = GenericToolAdapter(mock_tool)

    # Create context
    context = ToolContext(
        session_id="test_session",
        message_id="test_message",
        agent="test_agent",
        abort=MagicMock(),
        messages=[],
    )

    # Execute via adapter
    result = await adapter.execute(context, param="value")

    # Verify Err result
    assert result.is_err()
    assert "TOOL_ERROR" in str(result)


# =============================================================================
# Adapter Registration Tests
# =============================================================================


def test_register_adapter_adds_to_registry():
    """Test register_adapter adds adapter to registry."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Clear registry
    _clear_adapters_for_test()

    # Mock tool and adapter
    mock_tool = MagicMock()
    adapter = GenericToolAdapter(mock_tool)

    # Register adapter
    register_adapter("custom-tool", adapter)

    # Verify registered
    registered = get_adapter("custom-tool")
    assert registered is adapter


def test_get_adapter_returns_registered_adapter():
    """Test get_adapter returns registered adapter."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Clear registry
    _clear_adapters_for_test()

    # Mock tool and adapter
    mock_tool = MagicMock()
    adapter = GenericToolAdapter(mock_tool)

    # Register adapter
    register_adapter("my-tool", adapter)

    # Get adapter
    retrieved = get_adapter("my-tool")
    assert retrieved is adapter


def test_get_adapter_returns_none_for_unknown():
    """Test get_adapter returns None for unknown adapter."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Try to get non-existent adapter
    retrieved = get_adapter("unknown-tool")
    assert retrieved is None


def test_list_adapters_returns_all_names():
    """Test list_adapters returns all registered adapter names."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Clear registry
    _clear_adapters_for_test()

    # Mock tools and adapters
    mock_tool1 = MagicMock()
    mock_tool2 = MagicMock()
    adapter1 = GenericToolAdapter(mock_tool1)
    adapter2 = GenericToolAdapter(mock_tool2)

    # Register adapters
    register_adapter("tool-1", adapter1)
    register_adapter("tool-2", adapter2)

    # List adapters
    names = list_adapters()
    assert set(names) == {"tool-1", "tool-2"}


def _clear_adapters_for_test():
    """Helper to clear adapter registry for testing."""
    if not IMPORTS_AVAILABLE:
        return

    from dawn_kestrel.tools.adapters import _adapters

    _adapters.clear()
