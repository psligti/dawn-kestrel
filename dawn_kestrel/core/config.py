"""Configuration classes for SDK clients.

This module defines SDKConfig for configuring SDK client behavior
with optional overrides for storage, directories, and handler behavior.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class SDKConfig:
    """Configuration for SDK client.

    Attributes:
        storage_path: Where sessions are stored on disk.
            Default: ~/.local/share/opencode-python (from Settings.storage_dir)
            Override: Set to custom path for isolated storage.

        project_dir: Current working directory.
            Default: Path.cwd()
            Override: Set to different directory for testing or remote operations.

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

    storage_path: Optional[Path] = None
    project_dir: Optional[Path] = None
    auto_confirm: bool = False
    enable_progress: bool = True
    enable_notifications: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize configuration after initialization."""
        if self.project_dir is None:
            self.project_dir = Path.cwd()

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
