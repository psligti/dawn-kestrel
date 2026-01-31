"""Recents Manager for command palette
Tracks recent selections per scope with LRU eviction.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

class RecentsManager:
    """Manages recent selections per scope with LRU tracking"""

    def __init__(self, storage_path: Path) -> None:
        """Initialize RecentsManager

        Args:
            storage_path: Path to JSON storage file
        """
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._recents: Dict[str, List[str]] = {}
        self._load()

    def _load(self) -> None:
        """Load recents from JSON file"""
        if self.storage_path.exists():
            with open(self.storage_path, 'r') as f:
                self._recents = json.load(f)
        else:
            self._recents = {}

    def add_recent(self, scope: str, item: str) -> None:
        """Add item to scope's recent list (last 10)

        Args:
            scope: Scope name (providers, accounts, models, agents, sessions)
            item: Item identifier (e.g., 'openai', 'gpt-4', 'build')
        """
        if scope not in self._recents:
            self._recents[scope] = []

        # Remove if already exists, add to front (LRU)
        if item in self._recents[scope]:
            self._recents[scope].remove(item)

        self._recents[scope].insert(0, item)

        # Keep only last 10
        self._recents[scope] = self._recents[scope][:10]

    def get_recents(self, scope: str) -> List[str]:
        """Get recents for a scope in LRU order

        Args:
            scope: Scope name

        Returns:
            List of recent items in LRU order
        """
        return self._recents.get(scope, [])

    def save(self) -> None:
        """Persist recents to JSON file"""
        with open(self.storage_path, 'w') as f:
            json.dump(self._recents, f, indent=2)
