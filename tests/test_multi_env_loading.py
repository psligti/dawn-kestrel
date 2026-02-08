"""
Integration tests for multi-.env file loading in Settings.

Tests loading configuration from both repository and home directory .env files,
with proper precedence (home overrides repo).
"""

from pathlib import Path

import pytest
from pydantic_settings.main import SettingsConfigDict
from pydantic import ValidationError

from dawn_kestrel.core.settings import Settings
from dawn_kestrel.core.provider_settings import AccountConfig
from dawn_kestrel.providers.base import ProviderID


class TestMultiEnvLoading:
    """Integration tests for multi-.env file loading."""

    def test_loads_from_repo_env_only(self, tmp_path: Path) -> None:
        """Test that Settings loads from only the repo .env when it exists."""
        repo_env = tmp_path / ".env"
        repo_env.write_text(
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__ACCOUNT_NAME="openai_prod"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__API_KEY="sk-repo-key-12345"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__PROVIDER_ID="openai"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__MODEL="gpt-4"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__IS_DEFAULT="true"\n'
        )

        home_dir = tmp_path / "home"
        home_config_dir = home_dir / ".config" / "opencode-python"
        home_config_dir.mkdir(parents=True)

        class TestSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=(repo_env, home_config_dir / ".env"),
                env_file_encoding="utf-8",
                env_prefix="OPENCODE_PYTHON_",
                env_nested_delimiter="__",
                case_sensitive=False,
                extra="ignore",
            )

        settings = TestSettings()

        assert "openai_prod" in settings.accounts
        account = settings.accounts["openai_prod"]
        assert account.account_name == "openai_prod"
        assert account.provider_id == ProviderID.OPENAI
        assert account.api_key.get_secret_value() == "sk-repo-key-12345"
        assert account.model == "gpt-4"
        assert account.is_default is True

    def test_loads_from_home_env_only(self, tmp_path: Path) -> None:
        """Test that Settings loads from only the home .env when it exists."""
        repo_env = tmp_path / "repo" / ".env"

        home_dir = tmp_path / "home"
        home_config_dir = home_dir / ".config" / "opencode-python"
        home_config_dir.mkdir(parents=True)
        home_env = home_config_dir / ".env"
        home_env.write_text(
            'OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_DEV__ACCOUNT_NAME="anthropic_dev"\n'
            'OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_DEV__API_KEY="sk-ant-home-key-67890"\n'
            'OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_DEV__PROVIDER_ID="anthropic"\n'
            'OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_DEV__MODEL="claude-3-5-sonnet-20241022"\n'
            'OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_DEV__IS_DEFAULT="true"\n'
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

        assert "anthropic_dev" in settings.accounts
        account = settings.accounts["anthropic_dev"]
        assert account.account_name == "anthropic_dev"
        assert account.provider_id == ProviderID.ANTHROPIC
        assert account.api_key.get_secret_value() == "sk-ant-home-key-67890"
        assert account.model == "claude-3-5-sonnet-20241022"
        assert account.is_default is True

    def test_loads_from_both_envs(self, tmp_path: Path) -> None:
        """Test that Settings loads from both repo and home .env files."""
        repo_env = tmp_path / "repo" / ".env"
        repo_env.parent.mkdir(parents=True)
        repo_env.write_text(
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__ACCOUNT_NAME="openai_prod"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__API_KEY="sk-repo-key-12345"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__PROVIDER_ID="openai"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__MODEL="gpt-4"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__IS_DEFAULT="true"\n'
        )

        home_dir = tmp_path / "home"
        home_config_dir = home_dir / ".config" / "opencode-python"
        home_config_dir.mkdir(parents=True)
        home_env = home_config_dir / ".env"
        home_env.write_text(
            'OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_DEV__ACCOUNT_NAME="anthropic_dev"\n'
            'OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_DEV__API_KEY="sk-ant-home-key-67890"\n'
            'OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_DEV__PROVIDER_ID="anthropic"\n'
            'OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_DEV__MODEL="claude-3-5-sonnet-20241022"\n'
            'OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_DEV__IS_DEFAULT="true"\n'
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

        assert "openai_prod" in settings.accounts
        assert "anthropic_dev" in settings.accounts

        openai_account = settings.accounts["openai_prod"]
        assert openai_account.account_name == "openai_prod"
        assert openai_account.provider_id == ProviderID.OPENAI
        assert openai_account.api_key.get_secret_value() == "sk-repo-key-12345"
        assert openai_account.model == "gpt-4"

        anthropic_account = settings.accounts["anthropic_dev"]
        assert anthropic_account.account_name == "anthropic_dev"
        assert anthropic_account.provider_id == ProviderID.ANTHROPIC
        assert anthropic_account.api_key.get_secret_value() == "sk-ant-home-key-67890"
        assert anthropic_account.model == "claude-3-5-sonnet-20241022"

    def test_home_env_overrides_repo_env_for_same_account(self, tmp_path: Path) -> None:
        """Test that home .env overrides repo .env for the same account."""
        repo_env = tmp_path / "repo" / ".env"
        repo_env.parent.mkdir(parents=True)
        repo_env.write_text(
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__ACCOUNT_NAME="openai_prod"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__API_KEY="sk-repo-key-12345"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__PROVIDER_ID="openai"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__MODEL="gpt-4"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__IS_DEFAULT="false"\n'
        )

        home_dir = tmp_path / "home"
        home_config_dir = home_dir / ".config" / "opencode-python"
        home_config_dir.mkdir(parents=True)
        home_env = home_config_dir / ".env"
        home_env.write_text(
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__ACCOUNT_NAME="openai_prod"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__API_KEY="sk-home-key-override"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__PROVIDER_ID="openai"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__MODEL="gpt-4-turbo"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__IS_DEFAULT="true"\n'
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

        assert "openai_prod" in settings.accounts
        account = settings.accounts["openai_prod"]
        assert account.account_name == "openai_prod"

        assert account.api_key.get_secret_value() == "sk-home-key-override"
        assert account.model == "gpt-4-turbo"
        assert account.is_default is True

    def test_loads_with_no_env_files(self, tmp_path: Path) -> None:
        """Test that Settings loads with empty accounts when no .env files exist."""
        repo_env = tmp_path / "nonexistent" / ".env"
        home_env = tmp_path / "nonexistent2" / ".env"

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

        assert settings.accounts == {}

    def test_nested_env_vars_parse_correctly(self, tmp_path: Path) -> None:
        """Test that nested env vars with '__' delimiter parse correctly."""
        repo_env = tmp_path / "repo" / ".env"
        repo_env.parent.mkdir(parents=True)
        repo_env.write_text(
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__ACCOUNT_NAME="openai_prod"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__API_KEY="sk-nested-key-12345"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__PROVIDER_ID="openai"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__MODEL="gpt-4"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__BASE_URL="https://custom.openai.com/v1"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__IS_DEFAULT="true"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__OPTIONS__TEMPERATURE="0.7"\n'
            'OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__OPTIONS__MAX_TOKENS="4096"\n'
        )

        home_env = tmp_path / "nonexistent" / ".env"

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

        assert "openai_prod" in settings.accounts
        account = settings.accounts["openai_prod"]
        assert account.account_name == "openai_prod"

        assert account.api_key.get_secret_value() == "sk-nested-key-12345"
        assert account.provider_id == ProviderID.OPENAI
        assert account.model == "gpt-4"
        assert account.base_url == "https://custom.openai.com/v1"
        assert account.is_default is True

        assert account.options == {"temperature": 0.7, "max_tokens": 4096}

    def test_invalid_provider_id_raises_validation_error(self, tmp_path: Path) -> None:
        """Test that an invalid ProviderID in .env raises a ValidationError."""
        repo_env = tmp_path / "repo" / ".env"
        repo_env.parent.mkdir(parents=True)
        repo_env.write_text(
            'OPENCODE_PYTHON_ACCOUNTS__INVALID_ACCOUNT__ACCOUNT_NAME="invalid_account"\n'
            'OPENCODE_PYTHON_ACCOUNTS__INVALID_ACCOUNT__API_KEY="sk-key-12345"\n'
            'OPENCODE_PYTHON_ACCOUNTS__INVALID_ACCOUNT__PROVIDER_ID="invalid-provider"\n'
            'OPENCODE_PYTHON_ACCOUNTS__INVALID_ACCOUNT__MODEL="model-1"\n'
        )

        home_env = tmp_path / "nonexistent" / ".env"

        class TestSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=(repo_env, home_env),
                env_file_encoding="utf-8",
                env_prefix="OPENCODE_PYTHON_",
                env_nested_delimiter="__",
                case_sensitive=False,
                extra="ignore",
            )

        with pytest.raises(ValidationError) as exc_info:
            TestSettings()

        error_str = str(exc_info.value)
        assert "invalid-provider" in error_str.lower() or "ProviderID" in error_str

    def test_env_vars_case_insensitive_for_prefix(self, tmp_path: Path) -> None:
        """Test that env vars are case-insensitive for DAWN_KESTREL_ prefix."""
        repo_env = tmp_path / "repo" / ".env"
        repo_env.parent.mkdir(parents=True)
        repo_env.write_text(
            'dawn_kestrel_ACCOUNTS__OPENAI_PROD__ACCOUNT_NAME="openai_prod"\n'
            'dawn_kestrel_ACCOUNTS__OPENAI_PROD__API_KEY="sk-mixed-case-key"\n'
            'dawn_kestrel_ACCOUNTS__OPENAI_PROD__PROVIDER_ID="openai"\n'
            'dawn_kestrel_ACCOUNTS__OPENAI_PROD__MODEL="gpt-4"\n'
        )

        home_env = tmp_path / "nonexistent" / ".env"

        class TestSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=(repo_env, home_env),
                env_file_encoding="utf-8",
                env_prefix="DAWN_KESTREL_",
                env_nested_delimiter="__",
                case_sensitive=False,
                extra="ignore",
            )

        settings = TestSettings()

        assert "openai_prod" in settings.accounts
        account = settings.accounts["openai_prod"]
        assert account.account_name == "openai_prod"
        assert account.api_key.get_secret_value() == "sk-mixed-case-key"
        assert account.provider_id == ProviderID.OPENAI
        assert account.model == "gpt-4"

    def test_dawn_kestrel_prefix_in_dotenv(self, tmp_path: Path) -> None:
        """Test DAWN_KESTREL_* values are loaded from .env file."""
        repo_env = tmp_path / ".env"
        repo_env.write_text(
            'DAWN_KESTREL_PROVIDER_DEFAULT="openai"\nDAWN_KESTREL_MODEL_DEFAULT="gpt-4.1"\n'
        )

        class TestSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=(repo_env,),
                env_file_encoding="utf-8",
                env_nested_delimiter="__",
                case_sensitive=False,
                extra="ignore",
            )

        settings = TestSettings()

        assert settings.provider_default == "openai"
        assert settings.model_default == "gpt-4.1"
