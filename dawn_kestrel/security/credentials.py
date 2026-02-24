"""Per-repository credential management with environment variable fallback.

Provides secure credential storage with per-repo isolation and
fallback to standard environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Final

from pydantic import BaseModel, SecretStr


class CredentialSource(str, Enum):
    """Source of a retrieved credential."""

    REPO_STORE = "repo_store"
    ENVIRONMENT = "environment"


@dataclass(frozen=True)
class CredentialRef:
    """Reference to a credential by provider and optional key.

    Attributes:
        provider_id: Provider identifier (e.g., "openai", "anthropic")
        credential_key: Optional key for multi-account support (e.g., "work", "personal")
    """

    provider_id: str
    credential_key: str | None = None

    def __repr__(self) -> str:
        key_part = f":{self.credential_key}" if self.credential_key else ""
        return f"CredentialRef({self.provider_id}{key_part})"


class CredentialRefModel(BaseModel):
    """Pydantic model for CredentialRef serialization."""

    provider_id: str
    credential_key: str | None = None

    def to_ref(self) -> CredentialRef:
        return CredentialRef(
            provider_id=self.provider_id,
            credential_key=self.credential_key,
        )


ENV_PREFIXES: Final = ("DAWN_KESTREL_", "OPENCODE_PYTHON_", "")


def _normalize_provider_for_env(provider_id: str) -> str:
    """Normalize provider ID for environment variable lookup.

    Strips dots and dashes, converts to uppercase.

    Examples:
        "z.ai" -> "ZAI"
        "google-vertex" -> "GOOGLE_VERTEX"
        "anthropic" -> "ANTHROPIC"
    """
    return provider_id.replace(".", "").replace("-", "_").upper()


def _get_env_var_name(provider_id: str, prefix: str) -> str:
    """Build environment variable name for provider.

    Args:
        provider_id: Provider identifier
        prefix: Environment variable prefix (e.g., "DAWN_KESTREL_")

    Returns:
        Full environment variable name (e.g., "DAWN_KESTREL_OPENAI_API_KEY")
    """
    normalized = _normalize_provider_for_env(provider_id)
    return f"{prefix}{normalized}_API_KEY"


def _lookup_env_credential(provider_id: str) -> SecretStr | None:
    """Look up credential from environment variables.

    Checks prefixes in priority order: DAWN_KESTREL_, OPENCODE_PYTHON_, none.

    Args:
        provider_id: Provider identifier

    Returns:
        SecretStr if found in environment, None otherwise
    """
    for prefix in ENV_PREFIXES:
        env_var = _get_env_var_name(provider_id, prefix)
        value = os.getenv(env_var)
        if value:
            return SecretStr(value)
    return None


@dataclass
class CredentialStore:
    """Per-repository credential store with environment variable fallback.

    Stores credentials in memory, keyed by (repo_id, provider_id, credential_key).
    Falls back to environment variables when no repo-specific credential exists.

    Security:
        - Credentials are never logged or exposed in repr/str
        - Per-repo isolation prevents credential leakage between repos
        - Uses SecretStr for secure credential handling
    """

    _credentials: dict[tuple[str, str, str | None], SecretStr] = field(default_factory=dict)

    def _make_key(self, repo_id: str, ref: CredentialRef) -> tuple[str, str, str | None]:
        return (repo_id, ref.provider_id, ref.credential_key)

    def get_credential(self, repo_id: str, ref: CredentialRef) -> SecretStr | None:
        """Get credential for a repo and provider reference.

        Checks repo-specific store first, then falls back to environment.

        Args:
            repo_id: Repository identifier
            ref: Credential reference (provider + optional key)

        Returns:
            SecretStr if credential found, None otherwise
        """
        key = self._make_key(repo_id, ref)

        if key in self._credentials:
            return self._credentials[key]

        if ref.credential_key is None:
            return _lookup_env_credential(ref.provider_id)

        return None

    def set_credential(
        self,
        repo_id: str,
        ref: CredentialRef,
        credential: SecretStr,
    ) -> None:
        """Store a credential for a specific repo and provider.

        Args:
            repo_id: Repository identifier
            ref: Credential reference (provider + optional key)
            credential: The credential to store
        """
        key = self._make_key(repo_id, ref)
        self._credentials[key] = credential

    def clear_credential(self, repo_id: str, ref: CredentialRef) -> bool:
        """Clear a stored credential.

        Args:
            repo_id: Repository identifier
            ref: Credential reference

        Returns:
            True if credential was removed, False if it didn't exist
        """
        key = self._make_key(repo_id, ref)
        if key in self._credentials:
            del self._credentials[key]
            return True
        return False

    def clear_all_for_repo(self, repo_id: str) -> None:
        """Clear all credentials for a specific repo.

        Args:
            repo_id: Repository identifier
        """
        keys_to_remove = [k for k in self._credentials if k[0] == repo_id]
        for key in keys_to_remove:
            del self._credentials[key]

    def has_credential(self, repo_id: str, ref: CredentialRef) -> bool:
        """Check if a credential exists for the given repo and ref.

        Checks both stored credentials and environment fallback.

        Args:
            repo_id: Repository identifier
            ref: Credential reference

        Returns:
            True if credential exists, False otherwise
        """
        return self.get_credential(repo_id, ref) is not None

    def get_credential_source(
        self,
        repo_id: str,
        ref: CredentialRef,
    ) -> CredentialSource | None:
        """Get the source of a credential.

        Args:
            repo_id: Repository identifier
            ref: Credential reference

        Returns:
            CredentialSource if credential exists, None otherwise
        """
        key = self._make_key(repo_id, ref)

        if key in self._credentials:
            return CredentialSource.REPO_STORE

        if ref.credential_key is None and _lookup_env_credential(ref.provider_id):
            return CredentialSource.ENVIRONMENT

        return None

    def list_providers_with_credentials(self, repo_id: str) -> list[str]:
        """List all providers that have stored credentials for a repo.

        Note: This only lists stored credentials, not environment fallbacks.

        Args:
            repo_id: Repository identifier

        Returns:
            List of provider IDs with stored credentials
        """
        providers: set[str] = set()
        for key in self._credentials:
            if key[0] == repo_id:
                providers.add(key[1])
        return sorted(providers)

    def __repr__(self) -> str:
        return f"CredentialStore(repos={len(self._get_repos())}, credentials=***)"

    def __str__(self) -> str:
        repo_count = len(self._get_repos())
        cred_count = len(self._credentials)
        return f"CredentialStore({repo_count} repos, {cred_count} credentials)"

    def _get_repos(self) -> set[str]:
        return {k[0] for k in self._credentials}
