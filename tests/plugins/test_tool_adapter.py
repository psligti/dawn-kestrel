"""Tests for ToolAdapter protocol in plugins module."""

from unittest.mock import AsyncMock, MagicMock

import pytest


def _get_framework_classes():
    """Lazy import to avoid circular import at module level."""
    from dawn_kestrel.tools.framework import Tool, ToolContext, ToolResult

    return Tool, ToolContext, ToolResult


def _get_tool_adapter_classes():
    """Lazy import tool_adapter module."""
    from dawn_kestrel.plugins.tool_adapter import (
        ToolAdapter,
        ExternalToolAdapter,
        discover_adapters,
        register_external_adapter,
        get_external_adapter,
        list_external_adapters,
    )

    return (
        ToolAdapter,
        ExternalToolAdapter,
        discover_adapters,
        register_external_adapter,
        get_external_adapter,
        list_external_adapters,
    )


# =============================================================================
# Protocol Tests
# =============================================================================


def test_adapter_has_wrap_method():
    """Test ToolAdapter protocol has wrap method."""
    ToolAdapter, _, _, _, _, _ = _get_tool_adapter_classes()
    Tool, _, _ = _get_framework_classes()

    class MockAdapter:
        async def wrap(self, external_tool):
            return MagicMock(spec=Tool)

    adapter = MockAdapter()
    assert callable(adapter.wrap)


def test_adapter_protocol_is_runtime_checkable():
    """Test ToolAdapter is runtime checkable."""
    ToolAdapter, _, _, _, _, _ = _get_tool_adapter_classes()
    Tool, _, _ = _get_framework_classes()

    class CompliantAdapter:
        async def wrap(self, external_tool):
            return MagicMock(spec=Tool)

    adapter = CompliantAdapter()
    assert isinstance(adapter, ToolAdapter)


# =============================================================================
# ExternalToolAdapter Tests
# =============================================================================


@pytest.mark.asyncio
async def test_external_adapter_wraps_tool():
    """Test ExternalToolAdapter wraps external tool correctly."""
    _, ExternalToolAdapter, _, _, _, _ = _get_tool_adapter_classes()
    Tool, _, _ = _get_framework_classes()

    mock_external = MagicMock()
    mock_external.name = "external_tool"
    mock_external.execute = AsyncMock(return_value={"result": "success"})

    adapter = ExternalToolAdapter()
    wrapped = await adapter.wrap(mock_external)

    assert isinstance(wrapped, Tool)


@pytest.mark.asyncio
async def test_wrapped_tool_has_correct_id():
    """Test wrapped tool has correct id from external tool."""
    _, ExternalToolAdapter, _, _, _, _ = _get_tool_adapter_classes()

    mock_external = MagicMock()
    mock_external.id = "my_external_tool"

    adapter = ExternalToolAdapter()
    wrapped = await adapter.wrap(mock_external)

    assert wrapped.id == "my_external_tool"


@pytest.mark.asyncio
async def test_wrapped_tool_has_correct_description():
    """Test wrapped tool has correct description from external tool."""
    _, ExternalToolAdapter, _, _, _, _ = _get_tool_adapter_classes()

    mock_external = MagicMock()
    mock_external.id = "test_tool"
    mock_external.description = "An external tool description"

    adapter = ExternalToolAdapter()
    wrapped = await adapter.wrap(mock_external)

    assert wrapped.description == "An external tool description"


@pytest.mark.asyncio
async def test_wrapped_tool_execute_delegates():
    """Test wrapped tool execute delegates to external tool."""
    _, ExternalToolAdapter, _, _, _, _ = _get_tool_adapter_classes()
    _, ToolContext, ToolResult = _get_framework_classes()

    mock_external = MagicMock()
    mock_external.id = "test_tool"
    mock_external.description = "Test tool"
    mock_external.execute = AsyncMock(
        return_value=ToolResult(
            title="Success",
            output="Tool executed successfully",
            metadata={"status": "ok"},
        )
    )

    adapter = ExternalToolAdapter()
    wrapped = await adapter.wrap(mock_external)

    context = ToolContext(
        session_id="test_session",
        message_id="test_message",
        agent="test_agent",
        abort=MagicMock(),
        messages=[],
    )

    result = await wrapped.execute({"param": "value"}, context)

    assert result.title == "Success"
    assert "executed successfully" in result.output


@pytest.mark.asyncio
async def test_wrapped_tool_parameters():
    """Test wrapped tool returns parameters from external tool."""
    _, ExternalToolAdapter, _, _, _, _ = _get_tool_adapter_classes()

    mock_external = MagicMock()
    mock_external.id = "test_tool"
    mock_external.description = "Test tool"
    mock_external.parameters = MagicMock(
        return_value={
            "type": "object",
            "properties": {"input": {"type": "string"}},
        }
    )

    adapter = ExternalToolAdapter()
    wrapped = await adapter.wrap(mock_external)

    params = wrapped.parameters()

    assert params["type"] == "object"
    assert "input" in params["properties"]


# =============================================================================
# Adapter Registration Tests
# =============================================================================


def test_register_external_adapter():
    """Test register_external_adapter adds adapter to registry."""
    (
        _,
        ExternalToolAdapter,
        _,
        register_external_adapter,
        get_external_adapter,
        _,
    ) = _get_tool_adapter_classes()

    _clear_registry_for_test()

    adapter = ExternalToolAdapter()
    register_external_adapter("my_external", adapter)

    registered = get_external_adapter("my_external")
    assert registered is adapter


def test_get_external_adapter_returns_none_for_unknown():
    """Test get_external_adapter returns None for unknown adapter."""
    _, _, _, _, get_external_adapter, _ = _get_tool_adapter_classes()

    retrieved = get_external_adapter("unknown_tool")
    assert retrieved is None


def test_list_external_adapters():
    """Test list_external_adapters returns all registered adapter names."""
    (
        _,
        ExternalToolAdapter,
        _,
        register_external_adapter,
        _,
        list_external_adapters,
    ) = _get_tool_adapter_classes()

    _clear_registry_for_test()

    adapter1 = ExternalToolAdapter()
    adapter2 = ExternalToolAdapter()

    register_external_adapter("tool_1", adapter1)
    register_external_adapter("tool_2", adapter2)

    names = list_external_adapters()
    assert set(names) == {"tool_1", "tool_2"}


# =============================================================================
# Discovery Tests
# =============================================================================


@pytest.mark.asyncio
async def test_discover_adapters_from_entry_points():
    """Test discover_adapters loads adapters from entry points."""
    _, _, discover_adapters, _, _, _ = _get_tool_adapter_classes()

    _clear_registry_for_test()

    adapters = await discover_adapters()

    assert isinstance(adapters, dict)


@pytest.mark.asyncio
async def test_discover_adapters_returns_tool_names():
    """Test discover_adapters returns tool names as keys."""
    _, _, discover_adapters, _, _, _ = _get_tool_adapter_classes()

    adapters = await discover_adapters()

    for name in adapters.keys():
        assert isinstance(name, str)


def _clear_registry_for_test():
    """Helper to clear adapter registry for testing."""
    from dawn_kestrel.plugins.tool_adapter import _external_adapters

    _external_adapters.clear()
