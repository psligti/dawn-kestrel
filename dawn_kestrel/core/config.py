"""Configuration classes for SDK clients.

This module defines SDKConfig for configuring SDK client behavior
with optional overrides for storage, directories, and handler behavior.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


def find_project_root(start_dir: Path | None = None) -> Path:
    """Find the project root by walking up parent directories looking for .dawn-kestrel.

    Args:
        start_dir: Starting directory for search. Uses current directory if None.

    Returns:
        Path to the directory containing .dawn-kestrel, or start_dir/cwd if not found.
    """
    from dawn_kestrel.core.config_toml import find_config_file

    start = Path(start_dir) if start_dir else Path.cwd()

    config_path = find_config_file(start)
    if config_path:
        return config_path.parent.parent

    return start


@dataclass
class SDKConfig:
    """Configuration for SDK client.

    Attributes:
        storage_path: Where sessions are stored on disk.
            Default: ~/.local/share/opencode-python (from Settings.storage_dir)
            Override: Set to custom path for isolated storage.

        project_dir: Project directory for agent execution.
            Default: Found by walking up from cwd to find .dawn-kestrel directory.
            Override: Set to specific directory if you want to bypass auto-discovery.

        auto_confirm: If True, skip all confirm() calls and return True.
            Default: False
            Override: Set to True for non-interactive batch operations.
            Effect: io_handler.confirm() returns True without prompting.

        enable_progress: If True, use progress handlers for long operations.
            Default: True
            Override: Set to False for silent mode.
            Effect: progress_handler.start/update/complete() called if True, no-op if False.

        enable_notifications: If True, show notifications via notification handler.
            Default: True
            Override: Set to False for silent mode.
            Effect: notification_handler.show() called if True, no-op if False.
    """

    storage_path: Path | None = None
    project_dir: Path | None = None
    auto_confirm: bool = False
    enable_progress: bool = True
    enable_notifications: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize configuration after initialization."""
        if self.project_dir is None:
            self.project_dir = find_project_root()
        elif not self.project_dir.is_absolute():
            self.project_dir = find_project_root(self.project_dir)

    def as_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration.
        """
        return {
            "storage_path": str(self.storage_path) if self.storage_path else None,
            "project_dir": str(self.project_dir) if self.project_dir else None,
            "auto_confirm": self.auto_confirm,
            "enable_progress": self.enable_progress,
            "enable_notifications": self.enable_notifications,
        }
