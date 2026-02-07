"""Tests for AccountConfig model.

Tests AccountConfig Pydantic model validation, field validators,
and secure API key handling.
"""

import warnings

import pytest
from pydantic import ValidationError, SecretStr

from dawn_kestrel.core.provider_settings import AccountConfig
from dawn_kestrel.providers.base import ProviderID


class TestAccountConfig:
    """Tests for AccountConfig model."""

    def test_valid_account_config_instantiates(self) -> None:
        """Test AccountConfig instantiates with all fields and valid data."""
        config = AccountConfig(
            account_name="openai-prod",
            provider_id=ProviderID.OPENAI,
            api_key=SecretStr("sk-proj-" + "a" * 32),
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            options={"max_tokens": 4096},
            is_default=True,
        )
        assert config.account_name == "openai-prod"
        assert config.provider_id == ProviderID.OPENAI
        assert config.get_api_key() == "sk-proj-" + "a" * 32
        assert config.model == "gpt-4"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.options == {"max_tokens": 4096}
        assert config.is_default is True

    def test_account_name_validation_rejects_empty(self) -> None:
        """Test empty account_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AccountConfig(
                account_name="",
                provider_id=ProviderID.OPENAI,
                api_key=SecretStr("sk-proj-" + "a" * 32),
                model="gpt-4",
            )
        assert "account_name" in str(exc_info.value)
        assert "cannot be empty" in str(exc_info.value)

    def test_account_name_validation_strips_whitespace(self) -> None:
        """Test leading/trailing spaces are stripped from account_name."""
        config = AccountConfig(
            account_name="  my-account  ",
            provider_id=ProviderID.ANTHROPIC,
            api_key=SecretStr("sk-ant-" + "a" * 32),
            model="claude-3-5-sonnet-20241022",
        )
        assert config.account_name == "my-account"

    def test_model_validation_rejects_empty(self) -> None:
        """Test empty model raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AccountConfig(
                account_name="test-account",
                provider_id=ProviderID.OPENAI,
                api_key=SecretStr("sk-proj-" + "a" * 32),
                model="",
            )
        assert "model" in str(exc_info.value)
        assert "cannot be empty" in str(exc_info.value)

    def test_api_key_validation_warns_short_keys(self) -> None:
        """Test short API keys (< 32 chars) warn but don't reject."""
        short_key = "sk-proj-short"
        with pytest.warns(UserWarning, match=r"API key is shorter than 32 characters"):
            config = AccountConfig(
                account_name="test-account",
                provider_id=ProviderID.OPENAI,
                api_key=SecretStr(short_key),
                model="gpt-4",
            )
        assert config.get_api_key() == short_key

    def test_api_key_validation_accepts_valid_keys(self) -> None:
        """Test valid API keys (>= 32 chars) are accepted without warnings."""
        valid_key = "sk-proj-" + "a" * 32
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors
            config = AccountConfig(
                account_name="test-account",
                provider_id=ProviderID.OPENAI,
                api_key=SecretStr(valid_key),
                model="gpt-4",
            )
        assert config.get_api_key() == valid_key

    def test_provider_id_validation_rejects_invalid(self) -> None:
        """Test invalid ProviderID raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AccountConfig(
                account_name="test-account",
                provider_id="invalid-provider",  # type: ignore[arg-type]
                api_key=SecretStr("sk-proj-" + "a" * 32),
                model="gpt-4",
            )
        assert "provider_id" in str(exc_info.value)

    def test_provider_id_validation_accepts_valid(self) -> None:
        """Test valid ProviderID values are accepted."""
        valid_providers = [
            ProviderID.ANTHROPIC,
            ProviderID.OPENAI,
            ProviderID.GOOGLE,
            ProviderID.AMAZON_BEDROCK,
            ProviderID.AZURE,
        ]
        for provider in valid_providers:
            config = AccountConfig(
                account_name=f"test-{provider.value}",
                provider_id=provider,
                api_key=SecretStr("test-key-" + "a" * 32),
                model="test-model",
            )
            assert config.provider_id == provider

    def test_base_url_optional_field(self) -> None:
        """Test base_url can be None or string."""
        # Test with None (default)
        config_no_url = AccountConfig(
            account_name="test-account",
            provider_id=ProviderID.OPENAI,
            api_key=SecretStr("sk-proj-" + "a" * 32),
            model="gpt-4",
        )
        assert config_no_url.base_url is None

        # Test with string value
        config_with_url = AccountConfig(
            account_name="test-account",
            provider_id=ProviderID.OPENAI,
            api_key=SecretStr("sk-proj-" + "a" * 32),
            model="gpt-4",
            base_url="https://custom.api.com/v1",
        )
        assert config_with_url.base_url == "https://custom.api.com/v1"

    def test_options_field_dict(self) -> None:
        """Test options is a dictionary."""
        # Test with default empty dict
        config_default = AccountConfig(
            account_name="test-account",
            provider_id=ProviderID.OPENAI,
            api_key=SecretStr("sk-proj-" + "a" * 32),
            model="gpt-4",
        )
        assert config_default.options == {}

        # Test with custom dict
        custom_options = {"max_tokens": 4096, "temperature": 0.7}
        config_custom = AccountConfig(
            account_name="test-account",
            provider_id=ProviderID.OPENAI,
            api_key=SecretStr("sk-proj-" + "a" * 32),
            model="gpt-4",
            options=custom_options,
        )
        assert config_custom.options == custom_options

    def test_is_default_field(self) -> None:
        """Test is_default is a bool field."""
        # Test with default False
        config_not_default = AccountConfig(
            account_name="test-account",
            provider_id=ProviderID.OPENAI,
            api_key=SecretStr("sk-proj-" + "a" * 32),
            model="gpt-4",
        )
        assert config_not_default.is_default is False

        # Test with True
        config_default = AccountConfig(
            account_name="test-account",
            provider_id=ProviderID.OPENAI,
            api_key=SecretStr("sk-proj-" + "a" * 32),
            model="gpt-4",
            is_default=True,
        )
        assert config_default.is_default is True
