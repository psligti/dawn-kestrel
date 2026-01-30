"""Tests for Provider and Account models"""
import pytest
from datetime import datetime
import time

from opencode_python.providers_mgmt import Provider, Account, ProviderConnectionTest
from opencode_python.providers_mgmt import hash_api_key


def test_provider_creation():
    """Test that Provider can be created with valid data"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=["model-1", "model-2"],
        description="Test provider description"
    )

    assert provider.id == "test-provider"
    assert provider.name == "Test Provider"
    assert provider.base_url == "https://api.example.com/v1"
    assert provider.models == ["model-1", "model-2"]
    assert provider.description == "Test provider description"
    assert isinstance(provider.created_at, float)
    assert isinstance(provider.updated_at, float)


def test_provider_validation_empty_id():
    """Test that Provider validation rejects empty ID"""
    with pytest.raises(ValueError, match="Provider ID cannot be empty"):
        Provider(
            id="",
            name="Test Provider",
            base_url="https://api.example.com/v1",
            models=["model-1"]
        )


def test_provider_validation_empty_name():
    """Test that Provider validation rejects empty name"""
    with pytest.raises(ValueError, match="Provider name cannot be empty"):
        Provider(
            id="test-provider",
            name="",
            base_url="https://api.example.com/v1",
            models=["model-1"]
        )


def test_provider_validation_empty_base_url():
    """Test that Provider validation rejects empty base URL"""
    with pytest.raises(ValueError, match="Base URL cannot be empty"):
        Provider(
            id="test-provider",
            name="Test Provider",
            base_url="",
            models=["model-1"]
        )


def test_provider_validation_invalid_base_url():
    """Test that Provider validation rejects invalid base URL"""
    with pytest.raises(ValueError, match="Base URL must start with http:// or https://"):
        Provider(
            id="test-provider",
            name="Test Provider",
            base_url="ftp://api.example.com",
            models=["model-1"]
        )


def test_account_creation():
    """Test that Account can be created with valid data"""
    account = Account(
        id="test-account",
        provider_id="test-provider",
        name="Test Account",
        api_key_hash="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x",
        is_active=True,
        description="Test account description"
    )

    assert account.id == "test-account"
    assert account.provider_id == "test-provider"
    assert account.name == "Test Account"
    assert account.api_key_hash == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x"
    assert account.is_active is True
    assert account.description == "Test account description"
    assert isinstance(account.created_at, float)
    assert isinstance(account.updated_at, float)


def test_account_validation_empty_id():
    """Test that Account validation rejects empty ID"""
    with pytest.raises(ValueError, match="Account ID cannot be empty"):
        Account(
            id="",
            provider_id="test-provider",
            name="Test Account",
            api_key_hash="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x"
        )


def test_account_validation_empty_provider_id():
    """Test that Account validation rejects empty provider ID"""
    with pytest.raises(ValueError, match="Provider ID cannot be empty"):
        Account(
            id="test-account",
            provider_id="",
            name="Test Account",
            api_key_hash="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x"
        )


def test_account_validation_empty_name():
    """Test that Account validation rejects empty name"""
    with pytest.raises(ValueError, match="Account name cannot be empty"):
        Account(
            id="test-account",
            provider_id="test-provider",
            name="",
            api_key_hash="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x"
        )


def test_account_validation_empty_api_key_hash():
    """Test that Account validation rejects empty API key hash"""
    with pytest.raises(ValueError, match="API key hash cannot be empty"):
        Account(
            id="test-account",
            provider_id="test-provider",
            name="Test Account",
            api_key_hash=""
        )


def test_hash_api_key():
    """Test that API key hashing works correctly"""
    api_key = "my-secret-api-key-123"
    hash1 = hash_api_key(api_key)
    hash2 = hash_api_key(api_key)

    assert len(hash1) == 64
    assert hash1 == hash2
    assert hash1 != api_key
    assert "my-secret-api-key-123" not in hash1


def test_hash_api_key_different_inputs():
    """Test that different API keys produce different hashes"""
    api_key1 = "api-key-1"
    api_key2 = "api-key-2"

    hash1 = hash_api_key(api_key1)
    hash2 = hash_api_key(api_key2)

    assert hash1 != hash2


def test_provider_connection_test():
    """Test that ProviderConnectionTest can be created"""
    result = ProviderConnectionTest(
        provider_id="test-provider",
        success=True,
        message="Connection successful",
        details={"latency": 123, "models_count": 5}
    )

    assert result.provider_id == "test-provider"
    assert result.success is True
    assert result.message == "Connection successful"
    assert result.details["latency"] == 123
    assert result.details["models_count"] == 5
    assert isinstance(result.timestamp, float)


def test_provider_default_values():
    """Test that Provider has sensible default values"""
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        base_url="https://api.example.com/v1",
        models=[]
    )

    assert provider.models == []
    assert provider.description is None
    assert provider.metadata == {}
    assert isinstance(provider.created_at, float)
    assert isinstance(provider.updated_at, float)


def test_account_default_values():
    """Test that Account has sensible default values"""
    account = Account(
        id="test-account",
        provider_id="test-provider",
        name="Test Account",
        api_key_hash="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x"
    )

    assert account.is_active is False
    assert account.description is None
    assert account.metadata == {}
    assert isinstance(account.created_at, float)
    assert isinstance(account.updated_at, float)
