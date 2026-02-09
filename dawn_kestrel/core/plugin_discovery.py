"""
Plugin discovery system using Python entry_points.

This module provides dynamic discovery and loading of plugins for tools, providers, and agents
using Python's importlib.metadata entry_points mechanism.

Plugin Groups:
- dawn_kestrel.tools: Tool plugins
- dawn_kestrel.providers: Provider plugins
- dawn_kestrel.agents: Agent plugins

Each plugin is registered via entry_points in pyproject.toml and loaded dynamically.
"""

import logging
from typing import Dict, Any, Optional
from importlib.metadata import entry_points, EntryPoint


logger = logging.getLogger(__name__)


def _load_plugins(group: str, plugin_type: str) -> Dict[str, Any]:
    """
    Generic plugin loader for entry point groups.

    Args:
        group: Entry point group name (e.g., "dawn_kestrel.tools")
        plugin_type: Type name for logging (e.g., "tool", "provider", "agent")

    Returns:
        Dictionary mapping plugin names to plugin instances

    Raises:
        No exceptions raised - errors are logged and skipped
    """
    plugins: Dict[str, Any] = {}

    try:
        eps = entry_points()
        plugin_entries = list(eps.select(group=group))

        for ep in plugin_entries:
            try:
                plugin = ep.load()

                if plugin is None:
                    logger.warning(
                        f"{plugin_type.capitalize()} plugin '{ep.name}' returned None, skipping"
                    )
                    continue

                # Instantiate if it's a class (type), otherwise use as-is
                if isinstance(plugin, type):
                    instance = plugin()
                else:
                    instance = plugin

                plugins[ep.name] = instance
                logger.debug(f"Loaded {plugin_type} plugin: {ep.name}")

            except ImportError as e:
                logger.warning(f"Failed to import {plugin_type} plugin '{ep.name}': {e}")
            except Exception as e:
                logger.warning(f"Failed to load {plugin_type} plugin '{ep.name}': {e}")

    except Exception as e:
        logger.error(f"Failed to discover {plugin_type} plugins: {e}")

    logger.info(f"Loaded {len(plugins)} {plugin_type} plugins")
    return plugins


def load_tools() -> Dict[str, Any]:
    """
    Load tool plugins from dawn_kestrel.tools entry points.

    Returns:
        Dictionary mapping tool names to tool instances

    Example:
        >>> tools = load_tools()
        >>> bash_tool = tools.get('bash')
    """
    return _load_plugins("dawn_kestrel.tools", "tool")


def load_providers() -> Dict[str, Any]:
    """
    Load provider plugins from dawn_kestrel.providers entry points.

    Returns:
        Dictionary mapping provider names to provider factories/classes

    Example:
        >>> providers = load_providers()
        >>> anthropic_provider = providers.get('anthropic')
    """
    return _load_plugins("dawn_kestrel.providers", "provider")


def load_agents() -> Dict[str, Any]:
    """
    Load agent plugins from dawn_kestrel.agents entry points.

    Returns:
        Dictionary mapping agent names to agent instances or factories

    Example:
        >>> agents = load_agents()
        >>> orchestrator = agents.get('orchestrator')
    """
    return _load_plugins("dawn_kestrel.agents", "agent")


def get_plugin_version(entry_point: EntryPoint) -> Optional[str]:
    """
    Get version information from a plugin entry point.

    Args:
        entry_point: The entry point to query

    Returns:
        Version string if available, None otherwise

    Example:
        >>> from importlib.metadata import entry_points
        >>> eps = entry_points()
        >>> tool_ep = list(eps.select(group='dawn_kestrel.tools'))[0]
        >>> version = get_plugin_version(tool_ep)
    """
    try:
        if hasattr(entry_point, "dist") and entry_point.dist:
            return str(entry_point.dist.version)
    except Exception as e:
        logger.debug(f"Could not get version for entry point '{entry_point.name}': {e}")

    return None


def validate_plugin(plugin: Any, plugin_name: str) -> bool:
    """
    Validate that a plugin meets minimum requirements.

    Args:
        plugin: The loaded plugin object
        plugin_name: Name of the plugin (for logging)

    Returns:
        True if valid, False otherwise
    """
    # Basic validation: plugin should not be None
    if plugin is None:
        logger.warning(f"Plugin '{plugin_name}' is None, validation failed")
        return False

    # Plugin should have a class name (at minimum)
    if not hasattr(plugin, "__class__"):
        logger.warning(f"Plugin '{plugin_name}' has no __class__ attribute, validation failed")
        return False

    return True


__all__ = [
    "load_tools",
    "load_providers",
    "load_agents",
    "get_plugin_version",
    "validate_plugin",
]
