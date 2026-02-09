"""Tests for agent plugin discovery using entry_points

Tests verify that:
1. All built-in agents are discoverable via entry_points
2. Plugin discovery loads agents correctly
3. Backward compatibility is maintained
4. Agent registry uses plugin discovery

TDD: RED-GREEN-REFACTOR workflow
- Write tests first (RED - they fail)
- Implement to pass (GREEN)
- Refactor if needed (still GREEN)
"""

import pytest
from dawn_kestrel.core.plugin_discovery import load_agents
from dawn_kestrel.agents.registry import AgentRegistry, create_agent_registry
from dawn_kestrel.agents.builtin import Agent


class TestAgentPluginDiscovery:
    """Test agent discovery via entry_points"""

    def test_load_agents_returns_dict(self):
        """Test that load_agents returns a dictionary"""
        agents = load_agents()
        assert isinstance(agents, dict), "load_agents should return a dict"
        assert len(agents) > 0, "Should load at least one agent"

    def test_all_builtin_agents_discovered(self):
        """Test that all 4 builtin agents are discovered"""
        agents = load_agents()

        # Builtin agents from dawn_kestrel/agents/builtin.py
        assert "build" in agents, "build agent should be discoverable"
        assert "plan" in agents, "plan agent should be discoverable"
        assert "general" in agents, "general agent should be discoverable"
        assert "explore" in agents, "explore agent should be discoverable"

    def test_bolt_merlin_agents_discovered(self):
        """Test that all 10 Bolt Merlin agents are discovered (excluding skill)"""
        agents = load_agents()

        # Bolt Merlin agents (frontend_ui_ux is a skill, not an agent)
        expected_agents = [
            "orchestrator",
            "master_orchestrator",
            "consultant",
            "librarian",
            "multimodal_looker",
            "autonomous_worker",
            "pre_planning",
            "plan_validator",
            "planner",
        ]

        for agent_name in expected_agents:
            assert agent_name in agents, f"{agent_name} agent should be discoverable"

    def test_agent_entry_points_are_valid(self):
        """Test that all loaded agents are valid Agent instances or factories"""
        agents = load_agents()

        for name, agent in agents.items():
            # Entry points can return Agent instances or factory functions
            # Both are valid
            if callable(agent):
                # Factory function - should return Agent when called
                agent_instance = agent()
                assert isinstance(agent_instance, Agent), (
                    f"{name} factory should return Agent instance"
                )
            else:
                # Direct Agent instance
                assert isinstance(agent, Agent), f"{name} should be an Agent instance"

    def test_at_least_13_agents_total(self):
        """Test that we have at least 13 agents (4 builtin + 10 bolt_merlin, with duplicate 'explore' overlapping)"""
        agents = load_agents()
        assert len(agents) >= 13, f"Expected at least 13 agents, got {len(agents)}"


class TestAgentRegistryPluginDiscovery:
    """Test AgentRegistry uses plugin discovery"""

    def test_registry_loads_from_plugins(self):
        """Test that AgentRegistry seeds agents from plugins"""
        registry = create_agent_registry()

        # Registry should have built-in agents from plugin discovery
        assert registry.has_agent("build"), "Registry should have build agent"
        assert registry.has_agent("plan"), "Registry should have plan agent"
        assert registry.has_agent("general"), "Registry should have general agent"
        assert registry.has_agent("explore"), "Registry should have explore agent"

    def test_registry_has_bolt_merlin_agents(self):
        """Test that AgentRegistry has Bolt Merlin agents"""
        registry = create_agent_registry()

        bolt_merlin_agents = [
            "orchestrator",
            "master_orchestrator",
            "consultant",
            "librarian",
            "planner",
        ]

        for agent_name in bolt_merlin_agents:
            assert registry.has_agent(agent_name), f"Registry should have {agent_name} agent"

    def test_registry_list_agents(self):
        """Test that list_agents returns all registered agents"""
        registry = create_agent_registry()
        agents = registry.list_agents(include_hidden=False)

        assert len(agents) >= 4, "Should have at least 4 builtin agents"
        assert all(isinstance(a, Agent) for a in agents), "All items should be Agent instances"

    def test_registry_get_agent(self):
        """Test that get_agent returns correct agent"""
        registry = create_agent_registry()

        build_agent = registry.get_agent("build")
        assert build_agent is not None, "build agent should be found"
        assert isinstance(build_agent, Agent), "build agent should be Agent instance"
        assert build_agent.name == "build", "Agent name should match"

    def test_registry_case_insensitive(self):
        """Test that agent lookup is case-insensitive"""
        registry = create_agent_registry()

        agent1 = registry.get_agent("BUILD")
        agent2 = registry.get_agent("Build")
        agent3 = registry.get_agent("build")

        assert agent1 is not None
        assert agent2 is not None
        assert agent3 is not None
        assert agent1.name == agent2.name == agent3.name == "build"


class TestBackwardCompatibility:
    """Test backward compatibility with direct agent imports"""

    def test_direct_builtin_imports_still_work(self):
        """Test that direct imports from builtin still work"""
        from dawn_kestrel.agents.builtin import (
            BUILD_AGENT,
            PLAN_AGENT,
            GENERAL_AGENT,
            EXPLORE_AGENT,
            get_all_agents,
            get_agent_by_name,
        )

        assert BUILD_AGENT is not None
        assert PLAN_AGENT is not None
        assert GENERAL_AGENT is not None
        assert EXPLORE_AGENT is not None

        agents = get_all_agents()
        assert len(agents) == 4, "get_all_agents should still return 4 builtin agents"

        plan = get_agent_by_name("plan")
        assert plan is not None
        assert plan.name == "plan"

    def test_direct_bolt_merlin_imports_still_work(self):
        """Test that direct imports from bolt_merlin still work"""
        from dawn_kestrel.agents.bolt_merlin import (
            create_orchestrator_agent,
            create_explore_agent,
        )

        orchestrator = create_orchestrator_agent()
        explore = create_explore_agent()

        assert isinstance(orchestrator, Agent)
        assert isinstance(explore, Agent)
        assert orchestrator.name == "orchestrator"
        assert explore.name == "explore"

    def test_registry_dynamic_registration_still_works(self):
        """Test that dynamic agent registration still works"""
        registry = create_agent_registry()

        custom_agent = Agent(
            name="custom_test",
            description="Test agent",
            mode="subagent",
            native=False,
            permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
        )

        # This should work
        import asyncio

        async def test():
            await registry.register_agent(custom_agent)
            assert registry.has_agent("custom_test"), "Custom agent should be registered"

        asyncio.run(test())


class TestAgentCapabilities:
    """Test that loaded agents have expected capabilities"""

    def test_build_agent_has_all_permissions(self):
        """Test that build agent has full permissions"""
        registry = create_agent_registry()
        build = registry.get_agent("build")

        assert build is not None
        assert build.permission is not None
        # Build agent should have allow all permission
        has_allow_all = any(
            p.get("permission") == "*" and p.get("action") == "allow" for p in build.permission
        )
        assert has_allow_all, "build agent should have allow-all permission"

    def test_explore_agent_read_only(self):
        """Test that explore agent is read-only"""
        registry = create_agent_registry()
        explore = registry.get_agent("explore")

        assert explore is not None
        assert explore.mode == "subagent"
        # Explore should deny write/edit
        has_deny_write = any(
            p.get("permission") == "write" and p.get("action") == "deny" for p in explore.permission
        )
        has_deny_edit = any(
            p.get("permission") == "edit" and p.get("action") == "deny" for p in explore.permission
        )
        assert has_deny_write, "explore agent should deny write"
        assert has_deny_edit, "explore agent should deny edit"

    def test_orchestrator_agent_permissions(self):
        """Test that orchestrator agent has orchestration permissions"""
        registry = create_agent_registry()
        orchestrator = registry.get_agent("orchestrator")

        assert orchestrator is not None
        assert orchestrator.name == "orchestrator"
        assert orchestrator.mode == "primary"

        # Should allow orchestration tools
        has_allow_all = any(
            p.get("permission") == "*" and p.get("action") == "allow"
            for p in orchestrator.permission
        )
        assert has_allow_all, "orchestrator agent should have allow-all permission"
