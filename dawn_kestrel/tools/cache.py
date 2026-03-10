"""Tool result cache for avoiding redundant tool executions."""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional

# Note: event_bus imports are done lazily to avoid circular imports


@dataclass
class CacheEntry:
    """A cached tool result with metadata."""

    tool_name: str
    tool_args: dict[str, Any]
    result_output: str
    result_title: str
    result_metadata: dict[str, Any]
    result_attachments: list[dict[str, Any]] | None
    cached_at: float
    access_count: int = 0
    ttl_seconds: float = 300.0  # Default 5 minutes


class ToolResultCache:
    """LRU cache for tool execution results.

    Caches tool results keyed by (tool_name, args_fingerprint) to avoid
    redundant executions when multiple agents call the same tool with
    the same arguments.

    Features:
    - LRU eviction when max_size reached
    - TTL-based expiration
    - Access tracking for cache hit analytics
    - Configurable per-tool caching policies
    - Event bus integration for cache hit/miss events
    """

    # Default tools that should be cached (read-only operations)
    DEFAULT_CACHEABLE_TOOLS: set[str] = {
        "read",
        "glob",
        "grep",
        "rg",
        "ripgrep",
        "ast-grep",
        "git",
        "file",
        "tree",
        "ls",
    }

    # Tools that should NEVER be cached (mutations, non-deterministic)
    DEFAULT_NON_CACHEABLE_TOOLS: set[str] = {
        "write",
        "edit",
        "bash",
        "shell",
        "execute",
        "delete",
        "move",
        "rename",
        "patch",
    }

    def __init__(
        self,
        max_size: int = 500,
        default_ttl_seconds: float = 300.0,
        cacheable_tools: Optional[set[str]] = None,
        non_cacheable_tools: Optional[set[str]] = None,
    ) -> None:
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl_seconds
        self._cacheable_tools = cacheable_tools or self.DEFAULT_CACHEABLE_TOOLS
        self._non_cacheable_tools = non_cacheable_tools or self.DEFAULT_NON_CACHEABLE_TOOLS

        # Stats
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _make_key(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        """Generate a cache key from tool name and arguments.

        Uses SHA256 hash of normalized arguments for consistent keys.
        """
        normalized = self._normalize_args(tool_args)
        args_json = json.dumps(normalized, sort_keys=True, default=str)
        args_hash = hashlib.sha256(args_json.encode()).hexdigest()[:16]
        return f"{tool_name}:{args_hash}"

    def _normalize_args(self, args: dict[str, Any]) -> dict[str, Any]:
        """Normalize arguments for consistent hashing.

        - Sorts keys
        - Converts paths to strings
        - Handles nested dicts recursively
        """
        normalized = {}
        for key in sorted(args.keys()):
            value = args[key]
            if isinstance(value, dict):
                normalized[key] = self._normalize_args(value)
            elif isinstance(value, (list, tuple)):
                normalized[key] = [
                    self._normalize_args(v) if isinstance(v, dict) else str(v) for v in value
                ]
            elif hasattr(value, "__fspath__"):  # Path-like
                normalized[key] = str(value)
            else:
                normalized[key] = value
        return normalized

    def is_cacheable(self, tool_name: str) -> bool:
        """Check if a tool's results should be cached.

        Args:
            tool_name: Name of the tool

        Returns:
            True if the tool's results should be cached
        """
        if tool_name in self._non_cacheable_tools:
            return False
        return tool_name in self._cacheable_tools

    def get(self, tool_name: str, tool_args: dict[str, Any]) -> Optional[CacheEntry]:
        """Get a cached result if available and not expired.

        Args:
            tool_name: Name of the tool
            tool_args: Arguments passed to the tool

        Returns:
            CacheEntry if found and valid, None otherwise
        """
        if not self.is_cacheable(tool_name):
            return None

        key = self._make_key(tool_name, tool_args)

        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]

        # Check TTL expiration
        age = time.time() - entry.cached_at
        if age > entry.ttl_seconds:
            self._evict(key)
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        entry.access_count += 1
        self._hits += 1

        # Emit cache hit event
        asyncio.create_task(self._emit_cache_event("hit", tool_name, key))

        return entry

    def set(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        result_output: str,
        result_title: str,
        result_metadata: dict[str, Any] | None = None,
        result_attachments: list[dict[str, Any]] | None = None,
        ttl_seconds: float | None = None,
    ) -> None:
        """Cache a tool result.

        Args:
            tool_name: Name of the tool
            tool_args: Arguments passed to the tool
            result_output: The output string from the tool
            result_title: The title of the result
            result_metadata: Optional metadata dict
            result_attachments: Optional attachments list
            ttl_seconds: Optional TTL override (uses default if not provided)
        """
        if not self.is_cacheable(tool_name):
            return

        key = self._make_key(tool_name, tool_args)

        # Evict oldest if at capacity
        while len(self._cache) >= self._max_size:
            self._evict_oldest()

        entry = CacheEntry(
            tool_name=tool_name,
            tool_args=tool_args,
            result_output=result_output,
            result_title=result_title,
            result_metadata=result_metadata or {},
            result_attachments=result_attachments,
            cached_at=time.time(),
            access_count=0,
            ttl_seconds=ttl_seconds or self._default_ttl,
        )

        self._cache[key] = entry

        # Emit cache miss event
        asyncio.create_task(self._emit_cache_event("miss", tool_name, key))

    def _evict(self, key: str) -> None:
        """Remove a specific entry from the cache."""
        if key in self._cache:
            del self._cache[key]
            self._evictions += 1

    def _evict_oldest(self) -> None:
        """Evict the least recently used entry."""
        if self._cache:
            oldest_key = next(iter(self._cache))
            self._evict(oldest_key)

    async def _emit_cache_event(self, event_type: str, tool_name: str, key: str) -> None:
        """Emit cache hit/miss event to the event bus."""
        try:
            from dawn_kestrel.core.event_bus import Events, bus
            await bus.publish(
                Events.TOOL_CACHE_HIT if event_type == "hit" else Events.TOOL_CACHE_MISS,
                {
                    "tool_name": tool_name,
                    "cache_key": key,
                    "timestamp": time.time(),
                    "cache_size": len(self._cache),
                    "hits": self._hits,
                    "misses": self._misses,
                },
            )
        except ImportError:
            pass  # Event bus not available, skip event

    def invalidate(self, tool_name: Optional[str] = None) -> int:
        """Invalidate cache entries.

        Args:
            tool_name: If provided, only invalidate entries for this tool.
                      If None, invalidate all entries.

        Returns:
            Number of entries invalidated
        """
        if tool_name is None:
            count = len(self._cache)
            self._cache.clear()
            self._evictions += count
            return count

        keys_to_remove = [k for k, v in self._cache.items() if v.tool_name == tool_name]
        for key in keys_to_remove:
            self._evict(key)
        return len(keys_to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, evictions, size, hit_rate
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "size": len(self._cache),
            "max_size": self._max_size,
            "hit_rate": hit_rate,
        }

    def resize(self, new_max_size: int) -> int:
        """Resize the cache, evicting entries if necessary.

        Args:
            new_max_size: New maximum cache size

        Returns:
            Number of entries evicted during resize
        """
        self._max_size = new_max_size
        evicted = 0
        while len(self._cache) > new_max_size:
            self._evict_oldest()
            evicted += 1
        return evicted


# Import asyncio for the async event emission
import asyncio
