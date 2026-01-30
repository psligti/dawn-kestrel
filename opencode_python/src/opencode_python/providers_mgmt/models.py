"""OpenCode Python - Provider and Account Management Models"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import Field, field_validator
from pydantic import BaseModel


class Provider(BaseModel):
    """Provider configuration model

    Represents an AI provider (OpenAI, Anthropic, local, etc.)
    with its base URL, available models, and connection details.
    """
    id: str = Field(description="Unique provider identifier")
    name: str = Field(description="Human-readable provider name")
    base_url: str = Field(description="Base URL for provider API")
    models: List[str] = Field(
        default_factory=list,
        description="List of model IDs available from this provider"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the provider"
    )
    created_at: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="Creation timestamp"
    )
    updated_at: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="Last update timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider metadata"
    )

    model_config = {"extra": "forbid"}

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate provider ID is not empty"""
        if not v or not v.strip():
            raise ValueError("Provider ID cannot be empty")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate provider name is not empty"""
        if not v or not v.strip():
            raise ValueError("Provider name cannot be empty")
        return v.strip()

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL is a valid HTTP URL"""
        v = v.strip()
        if not v:
            raise ValueError("Base URL cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v


class Account(BaseModel):
    """Account model for provider credentials

    Represents an account with credentials (API key, etc.)
    for a specific provider. API keys are stored securely as hashes.
    """
    id: str = Field(description="Unique account identifier")
    provider_id: str = Field(description="Provider ID this account belongs to")
    name: str = Field(description="Human-readable account name")
    api_key_hash: str = Field(
        description="Secure hash of the API key (never store plain text)"
    )
    is_active: bool = Field(
        default=False,
        description="Whether this is the active account for its provider"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the account"
    )
    created_at: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="Creation timestamp"
    )
    updated_at: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="Last update timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional account metadata"
    )

    model_config = {"extra": "forbid"}

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate account ID is not empty"""
        if not v or not v.strip():
            raise ValueError("Account ID cannot be empty")
        return v.strip()

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, v: str) -> str:
        """Validate provider ID is not empty"""
        if not v or not v.strip():
            raise ValueError("Provider ID cannot be empty")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate account name is not empty"""
        if not v or not v.strip():
            raise ValueError("Account name cannot be empty")
        return v.strip()

    @field_validator("api_key_hash")
    @classmethod
    def validate_api_key_hash(cls, v: str) -> str:
        """Validate API key hash is not empty"""
        if not v or not v.strip():
            raise ValueError("API key hash cannot be empty")
        return v.strip()


class ProviderConnectionTest(BaseModel):
    """Result of provider connectivity test"""
    provider_id: str = Field(description="Provider ID that was tested")
    success: bool = Field(description="Whether connection was successful")
    message: str = Field(description="Human-readable test result message")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional test details (error codes, latency, etc.)"
    )
    timestamp: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="Test timestamp"
    )

    model_config = {"extra": "forbid"}


__all__ = [
    "Provider",
    "Account",
    "ProviderConnectionTest",
]
