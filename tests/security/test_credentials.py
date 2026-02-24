"""Tests for CredentialStore.

Tests per-repo credential management, environment variable fallback,
and credential isolation.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from dawn_kestrel.security.credentials import (
    CredentialRef,
    CredentialStore,
    CredentialSource,
)


class TestCredentialRef:
    """Tests for CredentialRef model."""

    def test_credential_ref_instantiates_with_required_fields(self) -> None:
        """Test CredentialRef instantiates with provider_id."""
        ref = CredentialRef(provider_id="openai")
        assert ref.provider_id == "openai"
        assert ref.credential_key is None

    def test_credential_ref_with_custom_key(self) -> None:
        """Test CredentialRef with custom credential key."""
        ref = CredentialRef(provider_id="anthropic", credential_key="work-account")
        assert ref.provider_id == "anthropic"
        assert ref.credential_key == "work-account"


class TestCredentialStore:
    """Tests for CredentialStore."""

    def test_get_credential_from_env_fallback(self) -> None:
        """Test getting credential from environment variable."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345678901234567890"}):
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential is not None
            assert credential.get_secret_value() == "sk-test-key-12345678901234567890"

    def test_get_credential_from_env_with_prefix(self) -> None:
        """Test getting credential from prefixed env var."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="anthropic")

        with patch.dict(
            os.environ,
            {"DAWN_KESTREL_ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234"},
            clear=False,
        ):
            # Clear the non-prefixed version if it exists
            os.environ.pop("ANTHROPIC_API_KEY", None)
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential is not None
            assert credential.get_secret_value() == "sk-ant-test-key-12345678901234"

    def test_get_credential_repo_override(self) -> None:
        """Test repo-specific credential override."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        # Set repo-specific credential
        store.set_credential(
            repo_id="special-repo",
            ref=ref,
            credential=SecretStr("sk-repo-specific-key-123456789012"),
        )

        # Repo-specific should take precedence over env
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key-12345678901234567890"}):
            credential = store.get_credential(repo_id="special-repo", ref=ref)
            assert credential is not None
            assert credential.get_secret_value() == "sk-repo-specific-key-123456789012"

    def test_get_credential_different_repos_isolated(self) -> None:
        """Test credentials are isolated between repos."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        # Set different credentials for different repos
        store.set_credential(
            repo_id="repo-a",
            ref=ref,
            credential=SecretStr("sk-repo-a-key-123456789012345678"),
        )
        store.set_credential(
            repo_id="repo-b",
            ref=ref,
            credential=SecretStr("sk-repo-b-key-123456789012345678"),
        )

        # Each repo should get its own credential
        cred_a = store.get_credential(repo_id="repo-a", ref=ref)
        cred_b = store.get_credential(repo_id="repo-b", ref=ref)

        assert cred_a is not None
        assert cred_b is not None
        assert cred_a.get_secret_value() == "sk-repo-a-key-123456789012345678"
        assert cred_b.get_secret_value() == "sk-repo-b-key-123456789012345678"

    def test_get_credential_returns_none_when_not_found(self) -> None:
        """Test None is returned when credential doesn't exist."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="unknown-provider")

        # Remove any env vars that might exist
        with patch.dict(os.environ, {}, clear=True):
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential is None

    def test_get_credential_with_custom_key(self) -> None:
        """Test getting credential with custom credential key."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai", credential_key="work-account")

        store.set_credential(
            repo_id="repo-1",
            ref=ref,
            credential=SecretStr("sk-work-key-12345678901234567890"),
        )

        credential = store.get_credential(repo_id="repo-1", ref=ref)
        assert credential is not None
        assert credential.get_secret_value() == "sk-work-key-12345678901234567890"

    def test_get_credential_custom_key_does_not_fall_back_to_default(self) -> None:
        """Test custom key doesn't fall back to default env var."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai", credential_key="work-account")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key-12345678901234567890"}):
            # Custom key should NOT fall back to OPENAI_API_KEY
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential is None

    def test_set_credential_overwrites_existing(self) -> None:
        """Test setting credential overwrites existing value."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        store.set_credential(
            repo_id="repo-1",
            ref=ref,
            credential=SecretStr("sk-first-key-12345678901234567890"),
        )

        store.set_credential(
            repo_id="repo-1",
            ref=ref,
            credential=SecretStr("sk-second-key-12345678901234567890"),
        )

        credential = store.get_credential(repo_id="repo-1", ref=ref)
        assert credential is not None
        assert credential.get_secret_value() == "sk-second-key-12345678901234567890"

    def test_clear_credential(self) -> None:
        """Test clearing a credential."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        store.set_credential(
            repo_id="repo-1",
            ref=ref,
            credential=SecretStr("sk-test-key-12345678901234567890"),
        )

        # Clear the credential
        result = store.clear_credential(repo_id="repo-1", ref=ref)
        assert result is True

        # Should now return None
        with patch.dict(os.environ, {}, clear=True):
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential is None

    def test_clear_credential_returns_false_if_not_found(self) -> None:
        """Test clear returns False if credential doesn't exist."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        result = store.clear_credential(repo_id="repo-1", ref=ref)
        assert result is False

    def test_clear_all_credentials_for_repo(self) -> None:
        """Test clearing all credentials for a repo."""
        store = CredentialStore()

        store.set_credential(
            repo_id="repo-1",
            ref=CredentialRef(provider_id="openai"),
            credential=SecretStr("sk-openai-12345678901234567890"),
        )
        store.set_credential(
            repo_id="repo-1",
            ref=CredentialRef(provider_id="anthropic"),
            credential=SecretStr("sk-ant-12345678901234567890"),
        )

        # Clear all for repo-1
        store.clear_all_for_repo(repo_id="repo-1")

        with patch.dict(os.environ, {}, clear=True):
            assert (
                store.get_credential(repo_id="repo-1", ref=CredentialRef(provider_id="openai"))
                is None
            )
            assert (
                store.get_credential(repo_id="repo-1", ref=CredentialRef(provider_id="anthropic"))
                is None
            )

    def test_has_credential(self) -> None:
        """Test checking if credential exists."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        # No credential set
        with patch.dict(os.environ, {}, clear=True):
            assert store.has_credential(repo_id="repo-1", ref=ref) is False

        # Set credential
        store.set_credential(
            repo_id="repo-1",
            ref=ref,
            credential=SecretStr("sk-test-key-12345678901234567890"),
        )

        assert store.has_credential(repo_id="repo-1", ref=ref) is True

        # Has env fallback
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-12345678901234567890"}):
            anthropic_ref = CredentialRef(provider_id="anthropic")
            assert store.has_credential(repo_id="repo-1", ref=anthropic_ref) is True

    def test_get_credential_source(self) -> None:
        """Test getting the source of a credential."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        # No credential
        with patch.dict(os.environ, {}, clear=True):
            assert store.get_credential_source(repo_id="repo-1", ref=ref) is None

        # From env
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-12345678901234567890"}):
            assert (
                store.get_credential_source(repo_id="repo-1", ref=ref)
                == CredentialSource.ENVIRONMENT
            )

        # From store
        store.set_credential(
            repo_id="repo-1",
            ref=ref,
            credential=SecretStr("sk-stored-12345678901234567890"),
        )
        assert store.get_credential_source(repo_id="repo-1", ref=ref) == CredentialSource.REPO_STORE

    def test_list_providers_with_credentials(self) -> None:
        """Test listing providers that have credentials."""
        store = CredentialStore()

        store.set_credential(
            repo_id="repo-1",
            ref=CredentialRef(provider_id="openai"),
            credential=SecretStr("sk-openai-12345678901234567890"),
        )
        store.set_credential(
            repo_id="repo-1",
            ref=CredentialRef(provider_id="anthropic"),
            credential=SecretStr("sk-ant-12345678901234567890"),
        )

        providers = store.list_providers_with_credentials(repo_id="repo-1")
        assert "openai" in providers
        assert "anthropic" in providers
        assert len(providers) == 2

    def test_provider_id_normalization(self) -> None:
        """Test provider ID normalization for env var lookup."""
        store = CredentialStore()

        # Provider with dots should have them stripped for env lookup
        ref = CredentialRef(provider_id="z.ai")
        with patch.dict(os.environ, {"ZAI_API_KEY": "sk-zai-12345678901234567890"}):
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential is not None
            assert credential.get_secret_value() == "sk-zai-12345678901234567890"

        # Provider with dashes
        ref = CredentialRef(provider_id="google-vertex")
        with patch.dict(os.environ, {"GOOGLE_VERTEX_API_KEY": "sk-gv-12345678901234567890"}):
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential is not None
            assert credential.get_secret_value() == "sk-gv-12345678901234567890"


class TestCredentialStoreSecurity:
    """Security-focused tests for CredentialStore."""

    def test_repr_does_not_leak_credentials(self) -> None:
        """Test __repr__ doesn't expose credentials."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        store.set_credential(
            repo_id="repo-1",
            ref=ref,
            credential=SecretStr("sk-secret-key-12345678901234567890"),
        )

        repr_str = repr(store)
        assert "sk-secret-key" not in repr_str
        assert "secret" not in repr_str.lower() or "********" in repr_str

    def test_str_does_not_leak_credentials(self) -> None:
        """Test __str__ doesn't expose credentials."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        store.set_credential(
            repo_id="repo-1",
            ref=ref,
            credential=SecretStr("sk-secret-key-12345678901234567890"),
        )

        str_repr = str(store)
        assert "sk-secret-key" not in str_repr

    def test_credential_ref_repr_safe(self) -> None:
        """Test CredentialRef repr is safe."""
        ref = CredentialRef(provider_id="openai", credential_key="work")
        repr_str = repr(ref)
        # Should contain provider and key info but nothing sensitive
        assert "openai" in repr_str
        assert "work" in repr_str


class TestCredentialStoreEnvVarPrefixes:
    """Tests for environment variable prefix handling."""

    def test_opencode_python_prefix(self) -> None:
        """Test OPENCODE_PYTHON_ prefix is checked."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        with patch.dict(
            os.environ, {"OPENCODE_PYTHON_OPENAI_API_KEY": "sk-oc-12345678901234567890"}, clear=True
        ):
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("DAWN_KESTREL_OPENAI_API_KEY", None)
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential is not None
            assert credential.get_secret_value() == "sk-oc-12345678901234567890"

    def test_dawn_kestrel_prefix_priority(self) -> None:
        """Test DAWN_KESTREL_ prefix has priority over unprefixed."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="openai")

        env_vars = {
            "OPENAI_API_KEY": "sk-unprefixed-12345678901234567890",
            "DAWN_KESTREL_OPENAI_API_KEY": "sk-prefixed-12345678901234567890",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential is not None
            # Should prefer DAWN_KESTREL_ prefixed version
            assert credential.get_secret_value() == "sk-prefixed-12345678901234567890"

    def test_prefix_priority_order(self) -> None:
        """Test prefix priority order: DAWN_KESTREL_ > OPENCODE_PYTHON_ > none."""
        store = CredentialStore()
        ref = CredentialRef(provider_id="anthropic")

        # All three set - DAWN_KESTREL_ should win
        env_vars = {
            "ANTHROPIC_API_KEY": "sk-none-12345678901234567890",
            "OPENCODE_PYTHON_ANTHROPIC_API_KEY": "sk-oc-12345678901234567890",
            "DAWN_KESTREL_ANTHROPIC_API_KEY": "sk-dk-12345678901234567890",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential.get_secret_value() == "sk-dk-12345678901234567890"

        # Only OPENCODE_PYTHON_ and none - OPENCODE_PYTHON_ should win
        env_vars = {
            "ANTHROPIC_API_KEY": "sk-none-12345678901234567890",
            "OPENCODE_PYTHON_ANTHROPIC_API_KEY": "sk-oc-12345678901234567890",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            os.environ.pop("DAWN_KESTREL_ANTHROPIC_API_KEY", None)
            credential = store.get_credential(repo_id="repo-1", ref=ref)
            assert credential.get_secret_value() == "sk-oc-12345678901234567890"
