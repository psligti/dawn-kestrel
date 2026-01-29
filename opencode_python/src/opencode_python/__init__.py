"""OpenCode Python - Main package initialization"""
from opencode_python.core.models import (
    Session,
    Message,
    Part,
    ToolState,
    FileInfo,
    MessageSummary,
    SessionShare,
    SessionRevert,
    TokenUsage,
)

# Optional imports - only available when dependencies are installed
try:
    from opencode_python.core.event_bus import bus, Events
    _event_bus_available = True
except ImportError:
    _event_bus_available = False

try:
    from opencode_python.core.settings import get_settings
    _settings_available = True
except ImportError:
    _settings_available = False


__version__ = "0.1.0"
__all__ = [
    "Session",
    "Message",
    "Part",
    "ToolState",
    "FileInfo",
    "MessageSummary",
    "SessionShare",
    "SessionRevert",
    "TokenUsage",
]


def get_event_bus():
    """Get event bus instance if available, None otherwise"""
    if _event_bus_available:
        from opencode_python.core.event_bus import bus
        return bus
    return None


def get_settings():
    """Get settings instance if available, None otherwise"""
    if _settings_available:
        from opencode_python.core.settings import get_settings
        return get_settings()
    return None

