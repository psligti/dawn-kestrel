"""
OpenCode Python - Agent Registry

Provides CRUD operations for agent registration and retrieval,
with optional JSON persistence under storage/agent/.
"""
from __future__ import annotations

from typing import Optional, List, Dict
from pathlib import Path
import json
import logging
import aiofiles

from .builtin import Agent, get_all_agents


logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registry for agent definitions with CRUD operations.

    Provides in-memory storage seeded with built-in agents,
    with optional JSON persistence under storage/agent/{agent_name}.json.

    Features:
    - Case-insensitive agent name lookup
    - In-memory storage by default
    - Optional JSON persistence (disabled by default)
    - Injectable storage directory
    """

    def __init__(
        self,
        persistence_enabled: bool = False,
        storage_dir: Optional[Path] = None,
    ):
        """
        Initialize AgentRegistry.

        Args:
            persistence_enabled: If True, persist agents to JSON files
            storage_dir: Directory for storage/agent/ files. If None and
                        persistence_enabled, uses {base_dir}/storage/agent/
        """
        self.persistence_enabled = persistence_enabled
        self.storage_dir = storage_dir
        self._agents: Dict[str, Agent] = {}

        self._seed_builtin_agents()

        if persistence_enabled:
            self._initialize_persistence()

    def _seed_builtin_agents(self) -> None:
        """Seed registry with built-in agents from agents/builtin.py"""
        for agent in get_all_agents():
            self._register_internal(agent)
        logger.debug(f"Seeded registry with {len(self._agents)} built-in agents")

    def _normalize_name(self, name: str) -> str:
        """Normalize agent name for case-insensitive lookup"""
        return name.lower().strip()

    def _register_internal(self, agent: Agent) -> None:
        """
        Register agent in internal storage (case-insensitive).

        Args:
            agent: Agent to register
        """
        normalized_name = self._normalize_name(agent.name)
        self._agents[normalized_name] = agent

    def _get_agent_path(self, agent_name: str) -> Path:
        """Get file path for persisted agent"""
        if self.storage_dir is None:
            raise RuntimeError("storage_dir is required for persistence")

        agent_dir = self.storage_dir / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        return agent_dir / f"{agent_name}.json"

    def _initialize_persistence(self) -> None:
        """
        Initialize persistence layer.

        Loads any existing custom agents from storage/agent/
        """
        if not self.storage_dir:
            return

        agent_dir = self.storage_dir / "agent"
        if not agent_dir.exists():
            logger.debug(f"Agent storage directory does not exist: {agent_dir}")
            return

        # Load custom agents from JSON files
        for agent_file in agent_dir.glob("*.json"):
            try:
                with open(agent_file, "r") as f:
                    agent_data = json.load(f)

                agent = Agent(**agent_data)
                # Don't overwrite built-in agents
                if self._normalize_name(agent.name) in self._agents:
                    existing = self.get_agent(agent.name)
                    if existing and existing.native:
                        logger.debug(
                            f"Skipping built-in agent override: {agent.name}"
                        )
                        continue

                self._register_internal(agent)
                logger.debug(f"Loaded custom agent from file: {agent_file.name}")

            except Exception as e:
                logger.error(
                    f"Failed to load agent from {agent_file}: {e}"
                )

    async def register_agent(self, agent: Agent) -> Agent:
        """
        Register a new agent.

        Args:
            agent: Agent to register

        Returns:
            The registered agent

        Raises:
            ValueError: If agent with same name already exists
        """
        normalized_name = self._normalize_name(agent.name)

        if normalized_name in self._agents:
            existing = self._agents[normalized_name]
            # Allow overwriting non-native agents
            if existing.native:
                raise ValueError(
                    f"Cannot overwrite built-in agent: {agent.name}"
                )

        # Register in memory
        self._register_internal(agent)

        # Persist if enabled
        if self.persistence_enabled and not agent.native:
            try:
                await self._persist_agent(agent)
            except Exception as e:
                logger.error(f"Failed to persist agent {agent.name}: {e}")
                # Revert in-memory registration
                del self._agents[normalized_name]
                raise

        logger.info(f"Registered agent: {agent.name}")
        return agent

    async def _persist_agent(self, agent: Agent) -> None:
        """
        Persist agent to JSON file.

        Args:
            agent: Agent to persist
        """
        agent_path = self._get_agent_path(agent.name)
        agent_data = {
            "name": agent.name,
            "description": agent.description,
            "mode": agent.mode,
            "permission": agent.permission,
            "native": agent.native,
            "hidden": agent.hidden,
            "top_p": agent.top_p,
            "temperature": agent.temperature,
            "color": agent.color,
            "model": agent.model,
            "prompt": agent.prompt,
            "options": agent.options,
            "steps": agent.steps,
        }

        async with aiofiles.open(agent_path, mode="w") as f:
            await f.write(json.dumps(agent_data, indent=2, ensure_ascii=False))

    def get_agent(self, name: str) -> Optional[Agent]:
        """
        Get agent by name (case-insensitive).

        Args:
            name: Agent name

        Returns:
            Agent if found, None otherwise
        """
        normalized_name = self._normalize_name(name)
        return self._agents.get(normalized_name)

    def list_agents(self, include_hidden: bool = False) -> List[Agent]:
        """
        List all registered agents.

        Args:
            include_hidden: If True, include hidden agents

        Returns:
            List of agents
        """
        agents = list(self._agents.values())

        if not include_hidden:
            agents = [a for a in agents if not a.hidden]

        return agents

    async def remove_agent(self, name: str) -> bool:
        """
        Remove agent by name (case-insensitive).

        Cannot remove built-in (native=True) agents.

        Args:
            name: Agent name to remove

        Returns:
            True if removed, False otherwise

        Raises:
            ValueError: If attempting to remove built-in agent
        """
        normalized_name = self._normalize_name(name)

        if normalized_name not in self._agents:
            return False

        agent = self._agents[normalized_name]

        if agent.native:
            raise ValueError(
                f"Cannot remove built-in agent: {name}"
            )

        # Remove from memory
        del self._agents[normalized_name]

        # Remove persisted file if exists
        if self.persistence_enabled and self.storage_dir:
            agent_path = self._get_agent_path(agent.name)
            if agent_path.exists():
                agent_path.unlink()

        logger.info(f"Removed agent: {name}")
        return True

    def has_agent(self, name: str) -> bool:
        """
        Check if agent exists (case-insensitive).

        Args:
            name: Agent name

        Returns:
            True if agent exists, False otherwise
        """
        normalized_name = self._normalize_name(name)
        return normalized_name in self._agents


def create_agent_registry(
    persistence_enabled: bool = False,
    storage_dir: Optional[Path] = None,
) -> AgentRegistry:
    """
    Factory function to create AgentRegistry.

    Args:
        persistence_enabled: If True, persist agents to JSON files
        storage_dir: Directory for storage/agent/ files

    Returns:
        New AgentRegistry instance
    """
    return AgentRegistry(
        persistence_enabled=persistence_enabled,
        storage_dir=storage_dir,
    )
