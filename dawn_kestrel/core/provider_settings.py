"""
Multi-account provider settings model.

Defines the structure for account-based provider configurations,
supporting multiple accounts per provider with validation.
"""
from __future__ import annotations

import warnings
from typing import Any, Dict, Optional

from pydantic import BaseModel, SecretStr, ValidationError, field_validator

from dawn_kestrel.providers.base import ProviderID


class AccountConfig(BaseModel):
    """
    Configuration for a provider account.

    Supports multiple accounts per provider with validation and secure credential storage.

    Attributes:
        account_name: Unique name for this account (e.g., "openai-prod", "anthropic-dev")
        provider_id: Provider identifier from ProviderID enum
        api_key: API key for the provider (stored securely as SecretStr)
        model: Model ID to use (e.g., "gpt-4", "claude-sonnet-4-20250514")
        base_url: Custom base URL for the provider API (optional)
        options: Additional provider-specific options (optional)
        is_default: Whether this is the default account for the provider
    """

    account_name: str
    """Unique name for this account (required)"""

    provider_id: ProviderID
    """Provider identifier from ProviderID enum (required)"""

    api_key: SecretStr
    """API key for the provider (required, stored securely)"""

    model: str = ""
    """Model ID to use (required)"""

    base_url: Optional[str] = None
    """Custom base URL for the provider API (optional)"""

    options: Dict[str, Any] = {}
    """Additional provider-specific options (optional)"""

    is_default: bool = False
    """Whether this is the default account for the provider"""

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, v: str) -> str:
        """
        Validate account name.

        Strips whitespace and rejects empty strings.

        Args:
            v: Account name value

        Returns:
            Validated and stripped account name

        Raises:
            ValidationError: If account_name is empty after stripping
        """
        stripped = v.strip()
        if not stripped:
            raise ValueError("account_name cannot be empty")
        return stripped

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: SecretStr) -> SecretStr:
        """
        Validate API key with warning for short keys.

        Warns if API key is shorter than 32 characters but accepts it.

        Args:
            v: API key as SecretStr

        Returns:
            The validated SecretStr
        """
        api_key_value = v.get_secret_value()
        if len(api_key_value) < 32:
            warnings.warn(
                f"API key is shorter than 32 characters ({len(api_key_value)} chars). "
                "This may be insecure or invalid.",
                UserWarning,
                stacklevel=2,
            )
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """
        Validate model ID.

        Rejects empty model strings.

        Args:
            v: Model ID value

        Returns:
            Validated model ID

        Raises:
            ValidationError: If model is empty
        """
        if not v:
            raise ValueError("model cannot be empty")
        return v

    def get_api_key(self) -> str:
        """
        Get the API key value securely.

        Returns:
            The raw API key string
        """
        return self.api_key.get_secret_value()

    def model_dump_safe(self) -> Dict[str, Any]:
        """
        Convert model to dictionary without exposing secrets.

        Returns:
            Dictionary with masked API key
        """
        data = self.model_dump()
        data["api_key"] = "********"
        return data
