"""Tests for Settings class accounts functionality.

Tests Settings class multi-account provider settings including:
- accounts field presence and defaults
- get_account() method
- get_accounts_by_provider() method
- get_default_account() method
- multi-.env file loading
- SecretStr redaction in str/repr
"""

from pathlib import Path
from typing import Dict

import pytest
from pydantic import SecretStr
from pydantic_settings.main import SettingsConfigDict

from dawn_kestrel.core.settings import Settings
from dawn_kestrel.core.provider_settings import AccountConfig
from dawn_kestrel.providers.base import ProviderID


class TestSettingsAccounts:
    """Tests for Settings accounts field and methods."""

    def test_accounts_field_exists(self) -> None:
        """Test that accounts field is present in Settings."""
        settings = Settings()
        assert hasattr(settings, "accounts")
        assert isinstance(settings.accounts, dict)

    def test_accounts_field_default_empty_dict(self) -> None:
        """Test that accounts field defaults to empty dict."""
        settings = Settings()
        assert settings.accounts == {}

    def test_get_account_returns_account_for_valid_name(self) -> None:
        """Test get_account returns AccountConfig for valid account name."""
        account = AccountConfig(
            account_name="test-account",
            provider_id=ProviderID.OPENAI,
            api_key=SecretStr("sk-test-key-12345678901234567890"),
            model="gpt-4",
        )
        settings = Settings(accounts={"test-account": account})
        result = settings.get_account("test-account")
        assert result is not None
        assert result.account_name == "test-account"
        assert result.provider_id == ProviderID.OPENAI

    def test_get_account_returns_none_for_nonexistent(self) -> None:
        """Test get_account returns None for nonexistent account."""
        settings = Settings()
        result = settings.get_account("nonexistent")
        assert result is None

    def test_get_accounts_by_provider_filters_correctly(self) -> None:
        """Test get_accounts_by_provider returns filtered dict for provider."""
        accounts: Dict[str, AccountConfig] = {
            "openai-1": AccountConfig(
                account_name="openai-1",
                provider_id=ProviderID.OPENAI,
                api_key=SecretStr("sk-key1-12345678901234567890"),
                model="gpt-4",
            ),
            "openai-2": AccountConfig(
                account_name="openai-2",
                provider_id=ProviderID.OPENAI,
                api_key=SecretStr("sk-key2-12345678901234567890"),
                model="gpt-3.5",
            ),
            "anthropic-1": AccountConfig(
                account_name="anthropic-1",
                provider_id=ProviderID.ANTHROPIC,
                api_key=SecretStr("sk-ant-key-12345678901234567890"),
                model="claude-3",
            ),
        }
        settings = Settings(accounts=accounts)
        result = settings.get_accounts_by_provider(ProviderID.OPENAI)
        assert len(result) == 2
        assert "openai-1" in result
        assert "openai-2" in result
        assert "anthropic-1" not in result
        assert result["openai-1"].provider_id == ProviderID.OPENAI

    def test_get_accounts_by_provider_returns_empty_for_no_matches(self) -> None:
        """Test get_accounts_by_provider returns empty dict if no matches."""
        accounts: Dict[str, AccountConfig] = {
            "anthropic-1": AccountConfig(
                account_name="anthropic-1",
                provider_id=ProviderID.ANTHROPIC,
                api_key=SecretStr("sk-ant-key-12345678901234567890"),
                model="claude-3",
            ),
        }
        settings = Settings(accounts=accounts)
        result = settings.get_accounts_by_provider(ProviderID.OPENAI)
        assert result == {}

    def test_get_default_account_returns_default(self) -> None:
        """Test get_default_account returns account with is_default=True."""
        accounts: Dict[str, AccountConfig] = {
            "openai-1": AccountConfig(
                account_name="openai-1",
                provider_id=ProviderID.OPENAI,
                api_key=SecretStr("sk-key1-12345678901234567890"),
                model="gpt-4",
                is_default=False,
            ),
            "openai-default": AccountConfig(
                account_name="openai-default",
                provider_id=ProviderID.OPENAI,
                api_key=SecretStr("sk-key2-12345678901234567890"),
                model="gpt-4",
                is_default=True,
            ),
        }
        settings = Settings(accounts=accounts)
        result = settings.get_default_account()
        assert result is not None
        assert result.account_name == "openai-default"
        assert result.is_default is True

    def test_get_default_account_falls_back_to_provider_default(self) -> None:
        """Test get_default_account falls back to provider_default account."""
        accounts: Dict[str, AccountConfig] = {
            "openai-1": AccountConfig(
                account_name="openai-1",
                provider_id=ProviderID.OPENAI,
                api_key=SecretStr("sk-key1-12345678901234567890"),
                model="gpt-4",
                is_default=False,
            ),
            "anthropic-1": AccountConfig(
                account_name="anthropic-1",
                provider_id=ProviderID.ANTHROPIC,
                api_key=SecretStr("sk-ant-key-12345678901234567890"),
                model="claude-3",
                is_default=False,
            ),
        }
        settings = Settings(accounts=accounts)
        settings.provider_default = ProviderID.ANTHROPIC.value
        result = settings.get_default_account()
        assert result is not None
        assert result.account_name == "anthropic-1"

    def test_get_default_account_synthesizes_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_default_account creates default account from env vars."""
        monkeypatch.setenv("OPENCODE_PYTHON_PROVIDER_DEFAULT", "openai")
        monkeypatch.setenv("OPENCODE_PYTHON_MODEL_DEFAULT", "gpt-4.1")
        monkeypatch.setenv("OPENCODE_PYTHON_OPENAI_API_KEY", "sk-fallback-key-12345678901234567890")

        settings = Settings()
        result = settings.get_default_account()
        assert result is not None
        assert result.account_name == "default"
        assert result.provider_id == ProviderID.OPENAI
        assert result.model == "gpt-4.1"
        assert result.is_default is True

    def test_get_default_account_prefers_dawn_prefix_env_over_legacy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test DAWN_KESTREL_* API key takes precedence over OPENCODE_PYTHON_* key."""
        monkeypatch.setenv("DAWN_KESTREL_PROVIDER_DEFAULT", "openai")
        monkeypatch.setenv("DAWN_KESTREL_MODEL_DEFAULT", "gpt-4.1-mini")
        monkeypatch.setenv("DAWN_KESTREL_OPENAI_API_KEY", "sk-dawn-priority-key-1234567890")
        monkeypatch.setenv("OPENCODE_PYTHON_PROVIDER_DEFAULT", "anthropic")
        monkeypatch.setenv("OPENCODE_PYTHON_MODEL_DEFAULT", "claude-legacy")
        monkeypatch.setenv("OPENCODE_PYTHON_OPENAI_API_KEY", "sk-legacy-key-1234567890")

        settings = Settings()
        result = settings.get_default_account()

        assert result is not None
        assert result.provider_id == ProviderID.OPENAI
        assert result.model == "gpt-4.1-mini"
        assert result.api_key.get_secret_value() == "sk-dawn-priority-key-1234567890"

    def test_multi_env_file_loading(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that both repo and home .env files are loaded."""
        # Create repo .env
        repo_env = tmp_path / ".env"
        repo_env.write_text(
            "OPENCODE_PYTHON_ACCOUNTS__REPO_ACCOUNT__ACCOUNT_NAME=repo_account\n"
            "OPENCODE_PYTHON_ACCOUNTS__REPO_ACCOUNT__PROVIDER_ID=openai\n"
            "OPENCODE_PYTHON_ACCOUNTS__REPO_ACCOUNT__API_KEY=sk-repo-key-12345678901234567890\n"
            "OPENCODE_PYTHON_ACCOUNTS__REPO_ACCOUNT__MODEL=gpt-4\n"
        )

        # Create home .env
        home_dir = tmp_path / "home" / ".config" / "opencode-python"
        home_dir.mkdir(parents=True)
        home_env = home_dir / ".env"
        home_env.write_text(
            "OPENCODE_PYTHON_ACCOUNTS__HOME_ACCOUNT__ACCOUNT_NAME=home_account\n"
            "OPENCODE_PYTHON_ACCOUNTS__HOME_ACCOUNT__PROVIDER_ID=anthropic\n"
            "OPENCODE_PYTHON_ACCOUNTS__HOME_ACCOUNT__API_KEY=sk-ant-home-12345678901234567890\n"
            "OPENCODE_PYTHON_ACCOUNTS__HOME_ACCOUNT__MODEL=claude-3\n"
        )

        class TestSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=(repo_env, home_env),
                env_file_encoding="utf-8",
                env_prefix="OPENCODE_PYTHON_",
                env_nested_delimiter="__",
                case_sensitive=False,
                extra="ignore",
            )

        settings = TestSettings()

        # Both accounts should be loaded
        assert len(settings.accounts) == 2
        assert "repo_account" in settings.accounts
        assert "home_account" in settings.accounts

    def test_home_env_overrides_repo_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that home .env overrides repo .env for same account."""
        # Create repo .env
        repo_env = tmp_path / ".env"
        repo_env.write_text(
            "OPENCODE_PYTHON_ACCOUNTS__TEST_ACCOUNT__ACCOUNT_NAME=test_account\n"
            "OPENCODE_PYTHON_ACCOUNTS__TEST_ACCOUNT__PROVIDER_ID=openai\n"
            "OPENCODE_PYTHON_ACCOUNTS__TEST_ACCOUNT__API_KEY=sk-repo-key-12345678901234567890\n"
            "OPENCODE_PYTHON_ACCOUNTS__TEST_ACCOUNT__MODEL=gpt-4\n"
        )

        # Create home .env with override
        home_dir = tmp_path / "home" / ".config" / "opencode-python"
        home_dir.mkdir(parents=True)
        home_env = home_dir / ".env"
        home_env.write_text(
            "OPENCODE_PYTHON_ACCOUNTS__TEST_ACCOUNT__ACCOUNT_NAME=test_account\n"
            "OPENCODE_PYTHON_ACCOUNTS__TEST_ACCOUNT__PROVIDER_ID=anthropic\n"
            "OPENCODE_PYTHON_ACCOUNTS__TEST_ACCOUNT__API_KEY=sk-ant-home-12345678901234567890\n"
            "OPENCODE_PYTHON_ACCOUNTS__TEST_ACCOUNT__MODEL=claude-3\n"
        )

        class TestSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=(repo_env, home_env),
                env_file_encoding="utf-8",
                env_prefix="OPENCODE_PYTHON_",
                env_nested_delimiter="__",
                case_sensitive=False,
                extra="ignore",
            )

        settings = TestSettings()

        # Home values should override repo values
        account = settings.get_account("test_account")
        assert account is not None
        assert account.provider_id == ProviderID.ANTHROPIC
        assert account.model == "claude-3"

    def test_secret_str_redacts_in_str(self) -> None:
        """Test that secrets are not leaked in str()."""
        account = AccountConfig(
            account_name="test-account",
            provider_id=ProviderID.OPENAI,
            api_key=SecretStr("sk-secret-key-12345678901234567890"),
            model="gpt-4",
        )
        settings = Settings(accounts={"test-account": account})
        str_repr = str(settings)
        assert "sk-secret-key-12345678901234567890" not in str_repr

    def test_secret_str_redacts_in_repr(self) -> None:
        """Test that secrets are not leaked in repr()."""
        account = AccountConfig(
            account_name="test-account",
            provider_id=ProviderID.OPENAI,
            api_key=SecretStr("sk-secret-key-12345678901234567890"),
            model="gpt-4",
        )
        settings = Settings(accounts={"test-account": account})
        repr_str = repr(settings)
        assert "sk-secret-key-12345678901234567890" not in repr_str
