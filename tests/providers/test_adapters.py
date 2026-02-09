"""Tests for ProviderAdapter pattern.

Tests cover protocol compliance, adapter implementations, and registration system.
Follows TDD workflow: RED-GREEN-REFACTOR.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dawn_kestrel.core.models import Message
from dawn_kestrel.core.result import Ok, Err


# Note: These tests will fail initially (RED phase)
# Import will fail until adapters module is created
try:
    from dawn_kestrel.providers.adapters import (
        ProviderAdapter,
        OpenAIAdapter,
        ZAIAdapter,
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


def test_adapter_has_generate_response_method():
    """Test ProviderAdapter protocol has generate_response method."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock a provider
    mock_provider = MagicMock()
    adapter = OpenAIAdapter(mock_provider)

    # Verify method exists (callable)
    assert callable(adapter.generate_response)


def test_adapter_has_get_provider_name_method():
    """Test ProviderAdapter protocol has get_provider_name method."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock a provider
    mock_provider = MagicMock()
    adapter = OpenAIAdapter(mock_provider)

    # Verify method exists (callable)
    assert callable(adapter.get_provider_name)


# =============================================================================
# OpenAIAdapter Tests
# =============================================================================


@pytest.mark.asyncio
async def test_openai_adapter_wraps_provider():
    """Test OpenAIAdapter wraps provider correctly."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock provider
    mock_provider = MagicMock()
    adapter = OpenAIAdapter(mock_provider)

    # Verify adapter wraps provider
    assert adapter._provider is mock_provider


@pytest.mark.asyncio
async def test_openai_adapter_returns_ok_on_success():
    """Test OpenAIAdapter returns Ok on successful generation."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock provider
    mock_provider = AsyncMock()
    response = Message(
        id="msg-1",
        session_id="sess-1",
        role="assistant",
        text="Hello!",
    )

    # Mock get_models to return model info
    from dawn_kestrel.providers.base import (
        ModelInfo,
        ModelCapabilities,
        ModelCost,
        ModelLimits,
        ProviderID,
        StreamEvent,
    )

    model_info = ModelInfo(
        id="gpt-5",
        provider_id=ProviderID.OPENAI,
        api_id="gpt-5",
        api_url="https://api.openai.com/v1",
        name="GPT-5",
        family="gpt",
        capabilities=ModelCapabilities(
            temperature=True, reasoning=True, toolcall=True, input={"text": True}
        ),
        cost=ModelCost(input=0.10, output=0.40, cache=None),
        limit=ModelLimits(context=1000000, input=1000000, output=100000),
        status="active",
        options={},
        headers={},
    )
    mock_provider.get_models = AsyncMock(return_value=[model_info])

    # Create adapter
    adapter = OpenAIAdapter(mock_provider)

    # Mock stream to collect events
    events = [
        StreamEvent(event_type="text-delta", data={"delta": "Hello!"}, timestamp=0),
        StreamEvent(event_type="finish", data={"finish_reason": "stop"}, timestamp=1),
    ]

    # Mock provider stream to yield events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    mock_provider.stream = mock_stream

    # Test adapter
    messages = [Message(id="msg-1", session_id="sess-1", role="user", text="Hi")]
    result = await adapter.generate_response(messages, "gpt-5")

    # Verify Ok result
    assert result.is_ok()
    message = result.unwrap()
    assert isinstance(message, Message)
    assert message.text == "Hello!"


@pytest.mark.asyncio
async def test_openai_adapter_returns_err_on_failure():
    """Test OpenAIAdapter returns Err on provider error."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock provider that raises exception
    mock_provider = AsyncMock()
    mock_provider.get_models = AsyncMock(side_effect=Exception("API error"))

    # Create adapter
    adapter = OpenAIAdapter(mock_provider)

    # Test adapter
    messages = [Message(id="msg-1", session_id="sess-1", role="user", text="Hi")]
    result = await adapter.generate_response(messages, "gpt-5")

    # Verify Err result
    assert result.is_err()
    assert "PROVIDER_ERROR" in str(result)  # Check full result string for error code


@pytest.mark.asyncio
async def test_openai_adapter_gets_provider_name():
    """Test OpenAIAdapter returns correct provider name."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock provider
    mock_provider = MagicMock()
    adapter = OpenAIAdapter(mock_provider)

    # Test provider name
    name = await adapter.get_provider_name()
    assert name == "openai"


# =============================================================================
# ZAIAdapter Tests
# =============================================================================


@pytest.mark.asyncio
async def test_zai_adapter_wraps_provider():
    """Test ZAIAdapter wraps provider correctly."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock provider
    mock_provider = MagicMock()
    adapter = ZAIAdapter(mock_provider)

    # Verify adapter wraps provider
    assert adapter._provider is mock_provider


@pytest.mark.asyncio
async def test_zai_adapter_returns_ok_on_success():
    """Test ZAIAdapter returns Ok on successful generation."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock provider
    mock_provider = AsyncMock()

    # Mock get_models to return model info
    from dawn_kestrel.providers.base import (
        ModelInfo,
        ModelCapabilities,
        ModelCost,
        ModelLimits,
        ProviderID,
        StreamEvent,
    )

    model_info = ModelInfo(
        id="glm-4.7",
        provider_id=ProviderID.Z_AI,
        api_id="glm-4.7",
        api_url="https://api.z.ai/api/paas/v4",
        name="GLM-4.7",
        family="glm",
        capabilities=ModelCapabilities(
            temperature=True, reasoning=True, toolcall=True, input={"text": True}
        ),
        cost=ModelCost(input=0.01, output=0.03, cache=None),
        limit=ModelLimits(context=128000, input=128000, output=8192),
        status="active",
        options={},
        headers={},
    )
    mock_provider.get_models = AsyncMock(return_value=[model_info])

    # Create adapter
    adapter = ZAIAdapter(mock_provider)

    # Mock stream to collect events
    events = [
        StreamEvent(event_type="text-delta", data={"delta": "Hi there!"}, timestamp=0),
        StreamEvent(event_type="finish", data={"finish_reason": "stop"}, timestamp=1),
    ]

    # Mock provider stream to yield events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    mock_provider.stream = mock_stream

    # Test adapter
    messages = [Message(id="msg-1", session_id="sess-1", role="user", text="Hi")]
    result = await adapter.generate_response(messages, "glm-4.7")

    # Verify Ok result
    assert result.is_ok()
    message = result.unwrap()
    assert isinstance(message, Message)
    assert message.text == "Hi there!"


@pytest.mark.asyncio
async def test_zai_adapter_returns_err_on_failure():
    """Test ZAIAdapter returns Err on provider error."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock provider that raises exception
    mock_provider = AsyncMock()
    mock_provider.get_models = AsyncMock(side_effect=Exception("Z.AI API error"))

    # Create adapter
    adapter = ZAIAdapter(mock_provider)

    # Test adapter
    messages = [Message(id="msg-1", session_id="sess-1", role="user", text="Hi")]
    result = await adapter.generate_response(messages, "glm-4.7")

    # Verify Err result
    assert result.is_err()
    assert "PROVIDER_ERROR" in str(result)  # Check full result string for error code


@pytest.mark.asyncio
async def test_zai_adapter_gets_provider_name():
    """Test ZAIAdapter returns correct provider name."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Mock provider
    mock_provider = MagicMock()
    adapter = ZAIAdapter(mock_provider)

    # Test provider name
    name = await adapter.get_provider_name()
    assert name == "zai"


# =============================================================================
# Adapter Registration Tests
# =============================================================================


def test_register_adapter_adds_to_registry():
    """Test register_adapter adds adapter to registry."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Clear registry
    _clear_adapters_for_test()

    # Mock provider and adapter
    mock_provider = MagicMock()
    adapter = OpenAIAdapter(mock_provider)

    # Register adapter
    register_adapter("custom-openai", adapter)

    # Verify registered
    registered = get_adapter("custom-openai")
    assert registered is adapter


def test_get_adapter_returns_registered_adapter():
    """Test get_adapter returns registered adapter."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Clear registry
    _clear_adapters_for_test()

    # Mock provider and adapter
    mock_provider = MagicMock()
    adapter = ZAIAdapter(mock_provider)

    # Register adapter
    register_adapter("custom-zai", adapter)

    # Get adapter
    retrieved = get_adapter("custom-zai")
    assert retrieved is adapter


def test_get_adapter_returns_none_for_unknown():
    """Test get_adapter returns None for unknown adapter."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Try to get non-existent adapter
    retrieved = get_adapter("unknown-adapter")
    assert retrieved is None


def test_list_adapters_returns_all_names():
    """Test list_adapters returns all registered adapter names."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Module not imported")

    # Clear registry
    _clear_adapters_for_test()

    # Mock providers and adapters
    mock_provider1 = MagicMock()
    mock_provider2 = MagicMock()
    adapter1 = OpenAIAdapter(mock_provider1)
    adapter2 = ZAIAdapter(mock_provider2)

    # Register adapters
    register_adapter("adapter-1", adapter1)
    register_adapter("adapter-2", adapter2)

    # List adapters
    names = list_adapters()
    assert set(names) == {"adapter-1", "adapter-2"}


def _clear_adapters_for_test():
    """Helper to clear adapter registry for testing."""
    if not IMPORTS_AVAILABLE:
        return

    from dawn_kestrel.providers.adapters import _adapters

    _adapters.clear()
