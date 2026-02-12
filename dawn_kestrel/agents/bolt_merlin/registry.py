"""
Bolt Merlin Agent Registry for Dawn Kestrel.

This module provides a centralized registry for all Bolt Merlin agents,
making it easy to load and register them with the Dawn Kestrel plugin system.

Bolt Merlin agents include specialized roles for orchestration, exploration,
consultation, planning, and various subagent tasks.

All agents are available as instantiated AgentConfig objects ready for use.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import all Bolt Merlin agent factories
from .orchestrator import create_orchestrator_agent
from .master_orchestrator import create_master_orchestrator_agent
from .planner import create_planner_agent
from .autonomous_worker import create_autonomous_worker_agent
from .consultant import create_consultant_agent
from .pre_planning import create_pre_planning_agent
from .plan_validator import create_plan_validator_agent
from .librarian import create_librarian_agent
from .explore import create_explore_agent
from .frontend_ui_engineer import create_frontend_ui_ux_skill
from .multimodal_looker import create_multimodal_looker_agent


# Agent factory registry - maps agent names to their creation functions
_AGENT_FACTORIES: Dict[str, Any] = {
    "orchestrator": create_orchestrator_agent,
    "master_orchestrator": create_master_orchestrator_agent,
    "planner": create_planner_agent,
    "autonomous_worker": create_autonomous_worker_agent,
    "consultant": create_consultant_agent,
    "pre_planning": create_pre_planning_agent,
    "plan_validator": create_plan_validator_agent,
    "librarian": create_librarian_agent,
    "explore": create_explore_agent,
    "frontend_ui_engineer": create_frontend_ui_ux_skill,
    "multimodal_looker": create_multimodal_looker_agent,
}


# Cache for instantiated agents
_agent_cache: Optional[Dict[str, Any]] = None


def get_bolt_merlin_agents() -> Dict[str, Any]:
    """
    Get all Bolt Merlin agents as instantiated AgentConfig objects.

    This function creates instances of all registered Bolt Merlin agents
    and returns them in a dictionary keyed by agent name.

    Results are cached for efficiency - subsequent calls return the same
    instances without re-instantiating.

    Returns:
        Dictionary mapping agent names to AgentConfig instances

    Example:
        >>> agents = get_bolt_merlin_agents()
        >>> orchestrator = agents.get("orchestrator")
        >>> explore = agents.get("explore")
    """
    global _agent_cache

    if _agent_cache is not None:
        return _agent_cache

    logger.info("Instantiating Bolt Merlin agents...")

    agents: Dict[str, Any] = {}
    failed_agents: list[str] = []

    for agent_name, factory_func in _AGENT_FACTORIES.items():
        try:
            agent = factory_func()
            if agent is None:
                logger.warning(f"Agent factory '{agent_name}' returned None, skipping")
                failed_agents.append(agent_name)
                continue

            agents[agent_name] = agent
            logger.debug(f"Instantiated Bolt Merlin agent: {agent_name}")

        except Exception as e:
            logger.error(f"Failed to instantiate Bolt Merlin agent '{agent_name}': {e}")
            failed_agents.append(agent_name)

    if failed_agents:
        logger.warning(f"Failed to load {len(failed_agents)} Bolt Merlin agents: {failed_agents}")

    logger.info(f"Loaded {len(agents)} Bolt Merlin agents")
    _agent_cache = agents
    return agents


def get_bolt_merlin_agent_names() -> list[str]:
    """
    Get list of all Bolt Merlin agent names.

    Returns:
        List of agent names that can be instantiated

    Example:
        >>> names = get_bolt_merlin_agent_names()
        >>> print(names)
        ['orchestrator', 'explore', 'librarian', ...]
    """
    return list(_AGENT_FACTORIES.keys())


def get_bolt_merlin_agent(agent_name: str) -> Any:
    """
    Get a specific Bolt Merlin agent by name.

    Args:
        agent_name: Name of the agent to retrieve

    Returns:
        AgentConfig instance if found, None otherwise

    Example:
        >>> orchestrator = get_bolt_merlin_agent("orchestrator")
        >>> if orchestrator:
        ...     print(orchestrator.name)
    """
    factory = _AGENT_FACTORIES.get(agent_name)
    if factory is None:
        logger.warning(f"Bolt Merlin agent '{agent_name}' not found")
        return None

    try:
        agent = factory()
        logger.debug(f"Retrieved Bolt Merlin agent: {agent_name}")
        return agent
    except Exception as e:
        logger.error(f"Failed to instantiate Bolt Merlin agent '{agent_name}': {e}")
        return None


def clear_agent_cache():
    """
    Clear the agent cache, forcing re-instantiation on next call.

    This is useful for testing or when agents need to be reloaded
    with updated configuration.

    Example:
        >>> clear_agent_cache()
        >>> agents = get_bolt_merlin_agents()  # Will re-instantiate
    """
    global _agent_cache
    _agent_cache = None
    logger.debug("Cleared Bolt Merlin agent cache")


def register_bolt_merlin_agent(name: str, factory: Any):
    """
    Register a custom Bolt Merlin agent factory.

    This allows extending the Bolt Merlin registry with custom agents
    that follow the same pattern.

    Args:
        name: Name for the agent
        factory: Function that returns an AgentConfig instance

    Example:
        >>> def create_my_agent():
        ...     return AgentBuilder().with_name("my_agent").build()
        >>>
        >>> register_bolt_merlin_agent("my_agent", create_my_agent)
    """
    _AGENT_FACTORIES[name] = factory
    # Clear cache to include new agent
    clear_agent_cache()
    logger.info(f"Registered custom Bolt Merlin agent: {name}")


def get_bolt_merlin_agent_descriptions() -> Dict[str, str]:
    """
    Get descriptions of all Bolt Merlin agents.

    Returns:
        Dictionary mapping agent names to their descriptions

    Example:
        >>> descriptions = get_bolt_merlin_agent_descriptions()
        >>> print(descriptions.get("explore"))
        Contextual grep for codebases...
    """
    agents = get_bolt_merlin_agents()
    return {
        name: agent.description if hasattr(agent, "description") else "No description"
        for name, agent in agents.items()
    }


__all__ = [
    "get_bolt_merlin_agents",
    "get_bolt_merlin_agent_names",
    "get_bolt_merlin_agent",
    "clear_agent_cache",
    "register_bolt_merlin_agent",
    "get_bolt_merlin_agent_descriptions",
]
