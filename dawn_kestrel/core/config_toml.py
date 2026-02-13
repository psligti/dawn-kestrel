"""TOML configuration file handling for dawn-kestrel.

This module provides utilities for reading and writing TOML configuration
files (.dawn-kestrel/config.toml) for project-local settings.

TOML files allow users to configure dawn-kestrel per-project,
similar to how VS Code uses .vscode/settings.json or git uses .git/config.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import tomli
import tomli_w

from dawn_kestrel.core.provider_settings import AccountConfig
from dawn_kestrel.providers.base import ProviderID


DEFAULT_CONFIG_PATH = Path(".dawn-kestrel") / "config.toml"


def find_config_file(project_dir: Path | None = None) -> Path | None:
    """Find the nearest .dawn-kestrel/config.toml file.

    Searches upward from current directory or specified project_dir.

    Args:
        project_dir: Starting directory for search. Uses current directory if None.

    Returns:
        Path to config file if found, None otherwise.
    """
    start_dir = Path(project_dir) if project_dir else Path.cwd()

    current_dir = start_dir
    while current_dir != current_dir.parent:
        config_path = current_dir / ".dawn-kestrel" / "config.toml"
        if config_path.exists():
            return config_path
        current_dir = current_dir.parent

    return None


def load_config(config_path: Path | None = None) -> Dict[str, Any]:
    """Load TOML configuration file.

    Args:
        config_path: Path to TOML file. If None, searches for nearest config.

    Returns:
        Dictionary with parsed configuration. Empty dict if file not found.

    Raises:
        RuntimeError: If TOML file is invalid.
    """
    if config_path is None:
        config_path = find_config_file()

    if config_path is None or not config_path.exists():
        return {}

    try:
        with open(config_path, "rb") as f:
            return tomli.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load config from {config_path}: {e}")


def save_config(config: Dict[str, Any], config_path: Path | None = None) -> Path:
    """Save configuration to TOML file.

    Creates parent directory if needed.

    Args:
        config: Configuration dictionary to save.
        config_path: Path to TOML file. If None, uses default path.

    Returns:
        Path to saved config file.

    Raises:
        RuntimeError: If file cannot be written.
    """
    if config_path is None:
        config_path = Path.cwd() / DEFAULT_CONFIG_PATH

    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, "wb") as f:
            tomli_w.dump(config, f)
        return config_path
    except Exception as e:
        raise RuntimeError(f"Failed to save config to {config_path}: {e}")


def config_to_account_config(
    account_name: str,
    provider_id_str: str,
    config_data: Dict[str, Any],
) -> AccountConfig:
    """Convert TOML config data to AccountConfig.

    Args:
        account_name: Name of the account.
        provider_id_str: Provider ID as string from TOML.
        config_data: Full configuration dictionary.

    Returns:
        AccountConfig instance.

    Raises:
        ValueError: If required fields are missing.
    """
    accounts_section = config_data.get("accounts", {})

    if account_name not in accounts_section:
        raise ValueError(f"Account '{account_name}' not found in config")

    account_data = accounts_section[account_name]

    provider_str = account_data.get("provider_id", provider_id_str)

    try:
        provider_id = ProviderID(provider_str)
    except ValueError:
        raise ValueError(f"Invalid provider_id: {provider_str}")

    api_key = account_data.get("api_key")
    if not api_key:
        raise ValueError(f"api_key not found for account '{account_name}'")

    model = account_data.get("model", "")

    return AccountConfig(
        account_name=account_name,
        provider_id=provider_id,
        api_key=api_key,
        model=model,
        base_url=account_data.get("base_url"),
        options=account_data.get("options", {}),
        is_default=account_data.get("is_default", False),
    )


def update_config_with_account(
    config: Dict[str, Any],
    account_config: AccountConfig,
    account_name: str,
) -> Dict[str, Any]:
    """Update configuration dictionary with account data.

    Args:
        config: Existing configuration dictionary.
        account_config: Account configuration to add/update.
        account_name: Name of the account.

    Returns:
        Updated configuration dictionary.
    """
    if "accounts" not in config:
        config["accounts"] = {}

    account_data = {
        "provider_id": account_config.provider_id.value,
        "api_key": account_config.api_key.get_secret_value(),
        "model": account_config.model,
        "is_default": account_config.is_default,
    }

    if account_config.base_url:
        account_data["base_url"] = account_config.base_url

    if account_config.options:
        account_data["options"] = account_config.options

    config["accounts"][account_name] = account_data

    return config


def get_project_config_path(project_dir: Path | None = None) -> Path:
    """Get the config.toml path for a project directory.

    Args:
        project_dir: Project directory. Uses current directory if None.

    Returns:
        Path to .dawn-kestrel/config.toml in project directory.
    """
    base_dir = Path(project_dir) if project_dir else Path.cwd()
    return base_dir / ".dawn-kestrel" / "config.toml"
