"""
Integration tests for SDK provider and tool tracking.

Tests the full integration of ProviderRegistry, SessionLifecycle,
AISession, AgentRuntime, and SDK client.
"""
import pytest
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_python.sdk import OpenCodeAsyncClient
from opencode_python.core.provider_config import ProviderConfig
from opencode_python.core.session_lifecycle import SessionLifecycle
from opencode_python.providers.registry import ProviderRegistry


@pytest.mark.asyncio
async def test_provider_registry_crud():
    """Test provider registration, retrieval, listing, and removal."""
    with TemporaryDirectory() as tmpdir:
        registry = ProviderRegistry(Path(tmpdir))

        config = ProviderConfig(
            provider_id="anthropic",
            model="claude-sonnet-4-20250514",
            api_key="test-key",
            is_default=True,
        )

        await registry.register_provider("test-anthropic", config, is_default=True)

        retrieved = await registry.get_provider("test-anthropic")
        assert retrieved is not None
        assert retrieved.provider_id == "anthropic"
        assert retrieved.model == "claude-sonnet-4-20250514"

        providers = await registry.list_providers()
        assert len(providers) == 1
        assert providers[0]["name"] == "test-anthropic"
        assert providers[0]["is_default"] is True

        removed = await registry.remove_provider("test-anthropic")
        assert removed is True

        after_removal = await registry.get_provider("test-anthropic")
        assert after_removal is None


@pytest.mark.asyncio
async def test_provider_registry_default():
    """Test default provider selection."""
    with TemporaryDirectory() as tmpdir:
        registry = ProviderRegistry(Path(tmpdir))

        config1 = ProviderConfig(
            provider_id="anthropic",
            model="claude-sonnet-4-20250514",
        )
        config2 = ProviderConfig(
            provider_id="openai",
            model="gpt-4",
        )

        await registry.register_provider("anthropic-config", config1, is_default=True)
        await registry.register_provider("openai-config", config2, is_default=False)

        default = await registry.get_default_provider()
        assert default is not None
        assert default.provider_id == "anthropic"

        await registry.set_default_provider("openai-config")

        new_default = await registry.get_default_provider()
        assert new_default is not None
        assert new_default.provider_id == "openai"


@pytest.mark.asyncio
async def test_provider_registry_lifecycle_events():
    """Test provider registry emits lifecycle events."""
    events = []
    lifecycle = SessionLifecycle()

    async def on_session_updated(data):
        events.append(("updated", data))

    lifecycle.on_session_updated(on_session_updated)

    with TemporaryDirectory() as tmpdir:
        registry = ProviderRegistry(Path(tmpdir))
        registry.register_lifecycle(lifecycle)

        config = ProviderConfig(
            provider_id="anthropic",
            model="claude-sonnet-4-20250514",
        )

        await registry.register_provider("test", config)

        await asyncio.sleep(0.01)

        assert len(events) > 0


@pytest.mark.asyncio
async def test_session_lifecycle_callbacks():
    """Test session lifecycle callback registration and emission."""
    lifecycle = SessionLifecycle()

    created_events = []
    updated_events = []
    message_events = []

    async def on_created(data):
        created_events.append(data)

    async def on_updated(data):
        updated_events.append(data)

    async def on_message(data):
        message_events.append(data)

    lifecycle.on_session_created(on_created)
    lifecycle.on_session_updated(on_updated)
    lifecycle.on_message_added(on_message)

    await lifecycle.emit_session_created({"id": "test-1"})
    await lifecycle.emit_session_updated({"id": "test-2"})
    await lifecycle.emit_message_added({"role": "user"})

    assert len(created_events) == 1
    assert created_events[0]["id"] == "test-1"
    assert len(updated_events) == 1
    assert updated_events[0]["id"] == "test-2"
    assert len(message_events) == 1
    assert message_events[0]["role"] == "user"

    lifecycle.unregister_session_created(on_created)
    await lifecycle.emit_session_created({"id": "test-3"})

    assert len(created_events) == 1


@pytest.mark.asyncio
async def test_sdk_client_provider_methods():
    """Test SDK client provider registry methods."""
    with TemporaryDirectory() as tmpdir:
        from opencode_python.core.config import SDKConfig

        config = SDKConfig(storage_path=Path(tmpdir))
        client = OpenCodeAsyncClient(config=config)

        await client.register_provider(
            name="test-provider",
            provider_id="anthropic",
            model="claude-sonnet-4-20250514",
        )

        retrieved = await client.get_provider("test-provider")
        assert retrieved is not None
        assert retrieved.provider_id == "anthropic"

        providers = await client.list_providers()
        assert len(providers) >= 1

        await client.update_provider(
            name="test-provider",
            provider_id="openai",
            model="gpt-4",
        )

        updated = await client.get_provider("test-provider")
        assert updated.provider_id == "openai"

        removed = await client.remove_provider("test-provider")
        assert removed is True


@pytest.mark.asyncio
async def test_sdk_client_lifecycle_methods():
    """Test SDK client lifecycle callback methods."""
    with TemporaryDirectory() as tmpdir:
        from opencode_python.core.config import SDKConfig

        config = SDKConfig(storage_path=Path(tmpdir))
        client = OpenCodeAsyncClient(config=config)

        session_events = []
        message_events = []

        async def on_session(data):
            session_events.append(data)

        async def on_message(data):
            message_events.append(data)

        client.on_session_created(on_session)
        client.on_message_added(on_message)

        assert client._lifecycle is not None

        await client._lifecycle.emit_session_created({"id": "test-1"})
        await client._lifecycle.emit_message_added({"role": "user"})

        assert len(session_events) == 1
        assert len(message_events) == 1
        assert session_events[0]["id"] == "test-1"
        assert message_events[0]["role"] == "user"


@pytest.mark.asyncio
async def test_provider_config_with_model():
    """Test ProviderConfig.with_model method."""
    config = ProviderConfig(
        provider_id="anthropic",
        model="claude-sonnet-4-20250514",
    )

    new_config = config.with_model("claude-opus-4-20250514")

    assert new_config.provider_id == "anthropic"
    assert new_config.model == "claude-opus-4-20250514"
    assert new_config.api_key == config.api_key


@pytest.mark.asyncio
async def test_provider_config_to_dict():
    """Test ProviderConfig serialization."""
    config = ProviderConfig(
        provider_id="anthropic",
        model="claude-sonnet-4-20250514",
        api_key="test-key",
        is_default=True,
        name="Test Provider",
    )

    data = config.as_dict()

    assert data["provider_id"] == "anthropic"
    assert data["model"] == "claude-sonnet-4-20250514"
    assert data["api_key"] == "test-key"
    assert data["is_default"] is True
    assert data["name"] == "Test Provider"


@pytest.mark.asyncio
async def test_provider_config_from_dict():
    """Test ProviderConfig deserialization."""
    data = {
        "provider_id": "openai",
        "model": "gpt-4",
        "api_key": "test-key",
        "is_default": False,
    }

    config = ProviderConfig.from_dict(data)

    assert config.provider_id == "openai"
    assert config.model == "gpt-4"
    assert config.api_key == "test-key"
    assert config.is_default is False
