"""Integration tests for plugin discovery system.

Tests verify that plugin discovery correctly loads all built-in
plugins (tools, providers, agents) via Python entry_points
without mocking.

Scenario: Plugin Discovery End-to-End
=====================================

Preconditions:
- dawn-kestrel package is installed with entry_points configured
- All built-in tools/providers/agents have entry point definitions

Steps:
1. Load tools via load_tools()
2. Verify all expected tools are loaded
3. Load providers via load_providers()
4. Verify all expected providers are loaded
5. Load agents via get_all_agents()
6. Verify built-in agents are available

Expected result:
- All 20+ tools loaded
- All 4 providers loaded
- All 11 Bolt Merlin agents loaded
- Each plugin has correct structure

Failure indicators:
- Plugin count doesn't match expected
- Plugin doesn't have required attributes
- Plugin not instantiable

Evidence:
- load_tools() returns dict with 20+ entries
- load_providers() returns dict with 4 entries
- get_all_agents() returns list with 11 agents
- Each tool has execute() method
- Each provider has required methods
"""

import pytest
import asyncio


class TestPluginDiscoveryTools:
    """Test tool plugin discovery integration."""

    @pytest.mark.asyncio
    async def test_load_tools_loads_all_builtin_tools(self):
        """Scenario: Loading tools loads all built-in tools via entry_points.

        Preconditions:
        - dawn-kestrel package installed
        - Tools have entry point definitions

        Steps:
        1. Call load_tools()
        2. Verify result is dict
        3. Verify count >= 20
        4. Verify expected tools present

        Expected result:
        - At least 20 tools loaded
        - Common tools present: bash, grep, glob, read, write
        - Each tool has correct structure

        Failure indicators:
        - Less than 20 tools loaded
        - Expected tools missing
        - Tools don't have required methods
        """
        from dawn_kestrel.core.plugin_discovery import load_tools

        tools = await load_tools()

        assert isinstance(tools, dict), f"Expected dict, got {type(tools)}"
        assert len(tools) >= 20, f"Expected at least 20 tools, got {len(tools)}"

        expected_tools = ["bash", "grep", "glob", "read", "write"]
        for tool_name in expected_tools:
            assert tool_name in tools, f"Expected tool '{tool_name}' not found"

    @pytest.mark.asyncio
    async def test_tool_has_required_attributes(self):
        """Scenario: Each loaded tool has required attributes.

        Preconditions:
        - Tools loaded via load_tools()

        Steps:
        1. Load tools
        2. Check each tool has name
        3. Check each tool has description
        4. Check each tool has execute method

        Expected result:
        - All tools have name attribute
        - All tools have description attribute
        - All tools have execute method

        Failure indicators:
        - Tool missing name
        - Tool missing description
        - Tool missing execute method
        """
        from dawn_kestrel.core.plugin_discovery import load_tools

        tools = await load_tools()

        for tool_name, tool in tools.items():
            assert hasattr(tool, "name"), f"Tool {tool_name} missing name attribute"
            assert hasattr(tool, "description"), f"Tool {tool_name} missing description attribute"
            assert hasattr(tool, "execute"), f"Tool {tool_name} missing execute method"

    @pytest.mark.asyncio
    async def test_tool_execute_is_callable(self):
        """Scenario: Tool execute method is callable.

        Preconditions:
        - Tools loaded via load_tools()

        Steps:
        1. Load tools
        2. Verify each tool.execute is callable

        Expected result:
        - All tool execute methods are callable
        - Execute accepts required parameters

        Failure indicators:
        - execute method not callable
        - execute method signature incorrect
        """
        from dawn_kestrel.core.plugin_discovery import load_tools

        tools = await load_tools()

        for tool_name, tool in tools.items():
            assert callable(tool.execute), f"Tool {tool_name}.execute is not callable"


class TestPluginDiscoveryProviders:
    """Test provider plugin discovery integration."""

    @pytest.mark.asyncio
    async def test_load_providers_loads_all_builtin_providers(self):
        """Scenario: Loading providers loads all built-in providers via entry_points.

        Preconditions:
        - dawn-kestrel package installed
        - Providers have entry point definitions

        Steps:
        1. Call load_providers()
        2. Verify result is dict
        3. Verify count == 4
        4. Verify expected providers present

        Expected result:
        - Exactly 4 providers loaded
        - Providers: anthropic, openai, zai, zai_coding_plan
        - Each provider has correct structure

        Failure indicators:
        - Wrong provider count
        - Expected providers missing
        - Providers don't have required methods
        """
        from dawn_kestrel.core.plugin_discovery import load_providers

        providers = await load_providers()

        assert isinstance(providers, dict), f"Expected dict, got {type(providers)}"
        assert len(providers) == 4, f"Expected 4 providers, got {len(providers)}"

        expected_providers = ["anthropic", "openai", "zai", "zai_coding_plan"]
        for provider_name in expected_providers:
            assert provider_name in providers, f"Expected provider '{provider_name}' not found"

    @pytest.mark.asyncio
    async def test_provider_has_required_methods(self):
        """Scenario: Each loaded provider has required methods.

        Preconditions:
        - Providers loaded via load_providers()

        Steps:
        1. Load providers
        2. Check each provider has __init__
        3. Check each provider has generate_response

        Expected result:
        - All providers are callable (class)
        - All providers have generate_response method

        Failure indicators:
        - Provider not callable
        - Provider missing generate_response
        """
        from dawn_kestrel.core.plugin_discovery import load_providers

        providers = await load_providers()

        for provider_name, provider_class in providers.items():
            assert callable(provider_class), (
                f"Provider {provider_name} is not callable (not a class)"
            )
            assert hasattr(provider_class, "generate_response"), (
                f"Provider {provider_name} missing generate_response method"
            )


class TestPluginDiscoveryAgents:
    """Test agent plugin discovery integration."""

    @pytest.mark.asyncio
    async def test_get_all_agents_loads_builtin_agents(self):
        """Scenario: Loading agents loads all built-in Bolt Merlin agents.

        Preconditions:
        - dawn-kestrel package installed
        - Agents have entry point definitions

        Steps:
        1. Create agent registry
        2. Call get_all_agents()
        3. Verify count >= 11
        4. Verify expected agents present

        Expected result:
        - At least 11 agents loaded
        - Agents: Orchestrator, Consultant, Librarian, Explore, Multimodal Looker,
          Frontend UI/UX, Autonomous Worker, Pre-Planning, Plan Validator,
          Planner, Master Orchestrator
        - Each agent has correct structure

        Failure indicators:
        - Wrong agent count
        - Expected agents missing
        - Agents don't have required attributes
        """
        from dawn_kestrel.agents.registry import create_agent_registry

        agent_registry = create_agent_registry(persistence_enabled=False)

        agents = agent_registry.get_all_agents()

        assert isinstance(agents, list), f"Expected list, got {type(agents)}"
        assert len(agents) >= 11, f"Expected at least 11 agents, got {len(agents)}"

        agent_names = [agent.name for agent in agents]
        expected_agents = [
            "Orchestrator",
            "Consultant",
            "Librarian",
            "Explore",
            "Multimodal Looker",
            "Frontend UI/UX",
            "Autonomous Worker",
            "Pre-Planning",
            "Plan Validator",
            "Planner",
            "Master Orchestrator",
        ]

        for expected_agent in expected_agents:
            assert expected_agent in agent_names, f"Expected agent '{expected_agent}' not found"

    @pytest.mark.asyncio
    async def test_agent_has_required_attributes(self):
        """Scenario: Each loaded agent has required attributes.

        Preconditions:
        - Agents loaded via agent registry

        Steps:
        1. Create agent registry
        2. Get all agents
        3. Check each agent has name
        4. Check each agent has description
        5. Check each agent has mode

        Expected result:
        - All agents have name attribute
        - All agents have description attribute
        - All agents have mode attribute

        Failure indicators:
        - Agent missing name
        - Agent missing description
        - Agent missing mode
        """
        from dawn_kestrel.agents.registry import create_agent_registry

        agent_registry = create_agent_registry(persistence_enabled=False)
        agents = agent_registry.get_all_agents()

        for agent in agents:
            assert hasattr(agent, "name"), f"Agent missing name attribute"
            assert hasattr(agent, "description"), f"Agent missing description attribute"
            assert hasattr(agent, "mode"), f"Agent missing mode attribute"


class TestPluginDiscoveryIntegration:
    """Test full plugin discovery workflow integration."""

    @pytest.mark.asyncio
    async def test_complete_plugin_loading_workflow(self):
        """Scenario: Load all plugins and verify integration.

        Preconditions:
        - dawn-kestrel package installed

        Steps:
        1. Load all tools
        2. Load all providers
        3. Load all agents
        4. Verify all plugins loaded successfully
        5. Verify no plugin loading errors

        Expected result:
        - All plugins load without errors
        - Tools, providers, agents all accessible
        - Plugin structure validated

        Failure indicators:
        - Any plugin loading fails
        - Plugin count incorrect
        - Plugin structure invalid
        """
        from dawn_kestrel.core.plugin_discovery import load_tools, load_providers
        from dawn_kestrel.agents.registry import create_agent_registry

        tools = await load_tools()
        providers = await load_providers()
        agent_registry = create_agent_registry(persistence_enabled=False)
        agents = agent_registry.get_all_agents()

        assert len(tools) >= 20, "Insufficient tools loaded"
        assert len(providers) == 4, "Incorrect provider count"
        assert len(agents) >= 11, "Insufficient agents loaded"

        assert all(hasattr(t, "name") for t in tools.values()), "Tools missing name attribute"
        assert all(callable(p) for p in providers.values()), "Providers not callable"
        assert all(hasattr(a, "name") for a in agents), "Agents missing name attribute"
