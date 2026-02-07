"""OpenCode Python - Main package initialization"""

Session = None
Message = None
Part = None
ToolState = None
FileInfo = None
MessageSummary = None
SessionShare = None
SessionRevert = None
TokenUsage = None

try:
    from dawn_kestrel.core.models import (
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
except Exception:
    pass

# Optional imports - only available when dependencies are installed
try:
    from dawn_kestrel.core.event_bus import bus, Events

    _event_bus_available = True
except ImportError:
    _event_bus_available = False

try:
    from dawn_kestrel.core.settings import get_settings

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
        from dawn_kestrel.core.event_bus import bus

        return bus
    return None


def get_settings():
    """Get settings instance if available, None otherwise"""
    if _settings_available:
        from dawn_kestrel.core.settings import get_settings

        return get_settings()
    return None
