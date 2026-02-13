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

        if hasattr(eps, "select"):
            plugin_entries = list(eps.select(group=group))
        else:
            plugin_entries = list(eps.get(group, []))

        for ep in plugin_entries:
            try:
                plugin = ep.load()

                if plugin is None:
                    logger.warning(
                        f"{plugin_type.capitalize()} plugin '{ep.name}' returned None, skipping"
                    )
                    continue

                # For provider plugins, always return class (factory) not instance
                # Provider classes require api_key argument for instantiation
                # For other plugins (tools), try to instantiate if possible
                if group == "dawn_kestrel.providers":
                    # Always use class for providers (they require api_key)
                    instance = plugin
                elif isinstance(plugin, type):
                    try:
                        instance = plugin()
                    except (TypeError, ValueError):
                        # Can't instantiate without arguments, use the class itself
                        instance = plugin
                        logger.debug(
                            f"Using {plugin_type} class '{ep.name}' as factory (requires constructor arguments)"
                        )
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


async def load_tools() -> Dict[str, Any]:
    """
    Load tool plugins from dawn_kestrel.tools entry points.

    Falls back to direct imports if entry points are not available.

    Returns:
        Dictionary mapping tool names to tool instances

    Example:
        >>> tools = await load_tools()
        >>> bash_tool = tools.get('bash')
    """
    tools = _load_plugins("dawn_kestrel.tools", "tool")

    if not tools:
        logger.info("No tools found via entry points, using fallback direct imports")
        tools = _load_tools_fallback()

    return tools


def _load_tools_fallback() -> Dict[str, Any]:
    from dawn_kestrel.tools.builtin import (
        BashTool,
        ReadTool,
        WriteTool,
        GrepTool,
        GlobTool,
        ASTGrepTool,
    )
    from dawn_kestrel.tools.additional import (
        EditTool,
        ListTool,
        TaskTool,
        QuestionTool,
        TodoTool,
        TodowriteTool,
        WebFetchTool,
        WebSearchTool,
        MultiEditTool,
        CodeSearchTool,
        LspTool,
        SkillTool,
        ExternalDirectoryTool,
        CompactionTool,
    )

    tools = {
        "bash": BashTool(),
        "read": ReadTool(),
        "write": WriteTool(),
        "grep": GrepTool(),
        "glob": GlobTool(),
        "ast_grep_search": ASTGrepTool(),
        "edit": EditTool(),
        "list": ListTool(),
        "task": TaskTool(),
        "question": QuestionTool(),
        "todoread": TodoTool(),
        "todowrite": TodowriteTool(),
        "webfetch": WebFetchTool(),
        "websearch": WebSearchTool(),
        "multiedit": MultiEditTool(),
        "codesearch": CodeSearchTool(),
        "lsp": LspTool(),
        "skill": SkillTool(),
        "externaldirectory": ExternalDirectoryTool(),
        "compact": CompactionTool(),
    }

    logger.info(f"Loaded {len(tools)} tools via fallback")
    return tools


def load_providers() -> Dict[str, Any]:
    """
    Load provider plugins from dawn_kestrel.providers entry points.

    Falls back to direct imports if entry points are not available.

    Returns:
        Dictionary mapping provider names to provider factories/classes

    Example:
        >>> providers = load_providers()
        >>> anthropic_provider = providers.get('anthropic')
    """
    providers = _load_plugins("dawn_kestrel.providers", "provider")

    if not providers:
        logger.info("No providers found via entry points, using fallback direct imports")
        providers = _load_providers_fallback()

    return providers


def _load_providers_fallback() -> Dict[str, Any]:
    # Import inside function to avoid circular dependency at module load time
    # Only import providers from separate modules; inline providers in __init__.py
    # are automatically available when providers module is imported
    from dawn_kestrel.providers.zai import ZAIProvider
    from dawn_kestrel.providers.zai_coding_plan import ZAICodingPlanProvider

    # For inline providers (Anthropic, OpenAI), import __init__ module directly
    # but only within this function to avoid circular dependency
    import dawn_kestrel.providers as providers_module

    return {
        "anthropic": providers_module.AnthropicProvider,
        "openai": providers_module.OpenAIProvider,
        "zai": ZAIProvider,
        "zai_coding_plan": ZAICodingPlanProvider,
    }


async def load_agents() -> Dict[str, Any]:
    """
    Load agent plugins from dawn_kestrel.agents entry points.

    Returns:
        Dictionary mapping agent names to agent instances or factories
    """
    agents = _load_plugins("dawn_kestrel.agents", "agent")
    if not agents:
        logger.info("No agents found via entry points, using fallback imports")
        agents = _load_agents_fallback()

    logger.info(f"Loaded {len(agents)} agents via plugin discovery")
    return agents


def _load_agents_fallback() -> Dict[str, Any]:
    """Fallback to load agents if entry points are not available."""
    from dawn_kestrel.agents.builtin import (
        BUILD_AGENT,
        PLAN_AGENT,
        GENERAL_AGENT,
    )

    builtin_agents = {
        agent.name: agent
        for agent in [
            BUILD_AGENT,
            PLAN_AGENT,
            GENERAL_AGENT,
        ]
    }

    # Try to load bolt_merlin agents for enhanced functionality
    try:
        from dawn_kestrel.agents.bolt_merlin.registry import get_bolt_merlin_agents

        bolt_merlin_agents = get_bolt_merlin_agents()
        logger.info(f"Loaded {len(bolt_merlin_agents)} Bolt Merlin agents")
        return {**builtin_agents, **bolt_merlin_agents}

    except ImportError as e:
        logger.warning(f"Bolt Merlin package not available, skipping bolt_merlin agents: {e}")
        return builtin_agents


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
    "_load_tools_fallback",
    "_load_providers_fallback",
    "_load_agents_fallback",
]
