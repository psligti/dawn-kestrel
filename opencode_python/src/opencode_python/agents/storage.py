"""OpenCode Python - Agent configuration storage"""
from __future__ import annotations
from typing import Optional, Dict, Any, Literal
import logging

from .config import AgentConfig


logger = logging.getLogger(__name__)


class AgentConfigStorage:
    """Storage for per-session agent configurations

    In-memory storage backed by optional persistent storage.
    For MVP, uses simple dict-based storage.
    """

    def __init__(self, persistent_storage=None):
        self._configs: Dict[str, AgentConfig] = {}
        self._persistent_storage = persistent_storage

    def save(self, config: AgentConfig) -> None:
        """Save agent configuration for a session

        Args:
            config: AgentConfig to save
        """
        self._configs[config.session_id] = config

        if self._persistent_storage:
            self._persist_to_disk(config)

        logger.debug(f"Saved agent config for session {config.session_id}")

    def load(self, session_id: str) -> Optional[AgentConfig]:
        """Load agent configuration for a session

        Args:
            session_id: Session ID to load config for

        Returns:
            AgentConfig if found, None otherwise
        """
        return self._configs.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete agent configuration for a session

        Args:
            session_id: Session ID to delete config for

        Returns:
            True if deleted, False if not found
        """
        if session_id in self._configs:
            del self._configs[session_id]
            logger.debug(f"Deleted agent config for session {session_id}")
            return True
        return False

    def list_all(self) -> Dict[str, AgentConfig]:
        """Get all stored configurations

        Returns:
            Dict mapping session_id -> AgentConfig
        """
        return self._configs.copy()

    def update_field(
        self,
        session_id: str,
        field: str,
        new_value: Any,
        action_source: Literal["user", "system", "profile_default"] = "user",
        reason: Optional[str] = None
    ) -> bool:
        """Update a single field in agent configuration

        Args:
            session_id: Session ID
            field: Field name to update
            new_value: New value
            action_source: Who made the change
            reason: Optional reason

        Returns:
            True if updated, False if session not found
        """
        config = self._configs.get(session_id)
        if not config:
            return False

        config.update_field(field, new_value, action_source, reason)
        self.save(config)
        return True

    def _persist_to_disk(self, config: AgentConfig) -> None:
        """Persist configuration to disk

        Args:
            config: AgentConfig to persist

        Note:
            For MVP, this is a no-op. In future, would write to storage layer.
        """
        pass


# Global storage instance
_default_storage: Optional[AgentConfigStorage] = None


def get_default_storage() -> AgentConfigStorage:
    """Get default agent config storage instance

    Returns:
        Singleton AgentConfigStorage instance
    """
    global _default_storage
    if _default_storage is None:
        _default_storage = AgentConfigStorage()
    return _default_storage
