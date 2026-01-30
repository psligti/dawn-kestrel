"""Tests for Provider and Account storage operations"""
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from opencode_python.providers_mgmt import Provider, Account, ProvidersStorage, hash_api_key
from opencode_python.core.event_bus import bus


@pytest.fixture
async def storage():
    """Create temporary storage for testing"""
    temp_dir = tempfile.mkdtemp()
    storage = ProvidersStorage(Path(temp_dir))
    yield storage
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_storage_create_provider(storage):
    """Test creating a provider"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1", "model-2"]
    )

    created = await storage.create_provider(provider)

    assert created.id == provider.id
    assert created.name == provider.name

    retrieved = await storage.get_provider(provider.id)
    assert retrieved is not None
    assert retrieved.id == provider.id


@pytest.mark.asyncio
async def test_storage_list_providers(storage):
    """Test listing all providers"""
    provider1 = Provider(
        id="provider-1",
        name="Provider 1",
        base_url="https://api1.example.com/v1",
        models=["model-1"]
    )

    provider2 = Provider(
        id="provider-2",
        name="Provider 2",
        base_url="https://api2.example.com/v1",
        models=["model-2"]
    )

    await storage.create_provider(provider1)
    await storage.create_provider(provider2)

    providers = await storage.list_providers()

    assert len(providers) == 2
    assert any(p.id == "provider-1" for p in providers)
    assert any(p.id == "provider-2" for p in providers)


@pytest.mark.asyncio
async def test_storage_update_provider(storage):
    """Test updating a provider"""
    provider = Provider(
        id="test-provider",
        name="Original Name",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    updated_provider = Provider(
        id=provider.id,
        name="Updated Name",
        base_url="https://api-updated.example.com/v1",
        models=["model-1", "model-2"]
    )

    result = await storage.update_provider(updated_provider)

    assert result.id == provider.id
    assert result.name == "Updated Name"

    retrieved = await storage.get_provider(provider.id)
    assert retrieved.name == "Updated Name"


@pytest.mark.asyncio
async def test_storage_delete_provider(storage):
    """Test deleting a provider"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    deleted = await storage.delete_provider(provider.id)

    assert deleted is True

    retrieved = await storage.get_provider(provider.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_storage_delete_provider_deletes_accounts(storage):
    """Test that deleting a provider also deletes its accounts"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    account = Account(
        id="test-account",
        provider_id=provider.id,
        name="Test Account",
        api_key_hash=hash_api_key("test-api-key")
    )

    await storage.create_account(account)

    await storage.delete_provider(provider.id)

    accounts = await storage.list_accounts(provider.id)
    assert len(accounts) == 0


@pytest.mark.asyncio
async def test_storage_create_account(storage):
    """Test creating an account"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    account = Account(
        id="test-account",
        provider_id=provider.id,
        name="Test Account",
        api_key_hash=hash_api_key("my-secret-key")
    )

    created = await storage.create_account(account)

    assert created.id == account.id
    assert created.name == account.name

    retrieved = await storage.get_account(account.id, provider.id)
    assert retrieved is not None
    assert retrieved.id == account.id


@pytest.mark.asyncio
async def test_storage_list_accounts(storage):
    """Test listing accounts for a provider"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    account1 = Account(
        id="account-1",
        provider_id=provider.id,
        name="Account 1",
        api_key_hash=hash_api_key("key-1")
    )

    account2 = Account(
        id="account-2",
        provider_id=provider.id,
        name="Account 2",
        api_key_hash=hash_api_key("key-2")
    )

    await storage.create_account(account1)
    await storage.create_account(account2)

    accounts = await storage.list_accounts(provider.id)

    assert len(accounts) == 2
    assert any(a.id == "account-1" for a in accounts)
    assert any(a.id == "account-2" for a in accounts)


@pytest.mark.asyncio
async def test_storage_set_active_account(storage):
    """Test setting an account as active"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    account1 = Account(
        id="account-1",
        provider_id=provider.id,
        name="Account 1",
        api_key_hash=hash_api_key("key-1"),
        is_active=False
    )

    account2 = Account(
        id="account-2",
        provider_id=provider.id,
        name="Account 2",
        api_key_hash=hash_api_key("key-2"),
        is_active=False
    )

    await storage.create_account(account1)
    await storage.create_account(account2)

    await storage.set_active_account("account-1", provider.id)

    accounts = await storage.list_accounts(provider.id)
    account1_updated = next((a for a in accounts if a.id == "account-1"), None)
    account2_updated = next((a for a in accounts if a.id == "account-2"), None)

    assert account1_updated.is_active is True
    assert account2_updated.is_active is False


@pytest.mark.asyncio
async def test_storage_get_active_account(storage):
    """Test getting active account for a provider"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    account1 = Account(
        id="account-1",
        provider_id=provider.id,
        name="Account 1",
        api_key_hash=hash_api_key("key-1"),
        is_active=True
    )

    account2 = Account(
        id="account-2",
        provider_id=provider.id,
        name="Account 2",
        api_key_hash=hash_api_key("key-2"),
        is_active=False
    )

    await storage.create_account(account1)
    await storage.create_account(account2)

    active_account = await storage.get_active_account(provider.id)

    assert active_account is not None
    assert active_account.id == "account-1"


@pytest.mark.asyncio
async def test_storage_update_account(storage):
    """Test updating an account"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    account = Account(
        id="test-account",
        provider_id=provider.id,
        name="Original Name",
        api_key_hash=hash_api_key("key-1"),
        is_active=False
    )

    await storage.create_account(account)

    updated_account = Account(
        id=account.id,
        provider_id=provider.id,
        name="Updated Name",
        api_key_hash=hash_api_key("key-2"),
        is_active=True
    )

    result = await storage.update_account(updated_account)

    assert result.id == account.id
    assert result.name == "Updated Name"

    retrieved = await storage.get_account(account.id, provider.id)
    assert retrieved.name == "Updated Name"


@pytest.mark.asyncio
async def test_storage_delete_account(storage):
    """Test deleting an account"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    account = Account(
        id="test-account",
        provider_id=provider.id,
        name="Test Account",
        api_key_hash=hash_api_key("test-api-key")
    )

    await storage.create_account(account)

    deleted = await storage.delete_account(account.id, provider.id)

    assert deleted is True

    retrieved = await storage.get_account(account.id, provider.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_storage_test_provider_connection(storage):
    """Test provider connection testing"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    result = await storage.test_provider_connection(provider.id)

    assert result.provider_id == provider.id
    assert result.success is True
    assert "Connection test successful" in result.message


@pytest.mark.asyncio
async def test_storage_test_provider_connection_not_found(storage):
    """Test connection test with non-existent provider"""
    result = await storage.test_provider_connection("non-existent-provider")

    assert result.provider_id == "non-existent-provider"
    assert result.success is False
    assert "not found" in result.message.lower()


@pytest.mark.asyncio
async def test_storage_test_provider_connection_invalid_url(storage):
    """Test connection test with invalid URL"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="ftp://api.example.com",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    result = await storage.test_provider_connection(provider.id)

    assert result.success is False
    assert "Invalid base URL format" in result.message


@pytest.mark.asyncio
async def test_create_account_deactivates_others(storage):
    """Test that creating an active account deactivates other accounts"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1"]
    )

    await storage.create_provider(provider)

    account1 = Account(
        id="account-1",
        provider_id=provider.id,
        name="Account 1",
        api_key_hash=hash_api_key("key-1"),
        is_active=True
    )

    account2 = Account(
        id="account-2",
        provider_id=provider.id,
        name="Account 2",
        api_key_hash=hash_api_key("key-2"),
        is_active=True
    )

    await storage.create_account(account1)
    await storage.create_account(account2)

    accounts = await storage.list_accounts(provider.id)

    account1_updated = next((a for a in accounts if a.id == "account-1"), None)
    account2_updated = next((a for a in accounts if a.id == "account-2"), None)

    assert account2_updated.is_active is True
    assert account1_updated.is_active is False
