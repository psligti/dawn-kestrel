"""Integration tests for todos and delegation tools/skills."""

from pathlib import Path

from dawn_kestrel.agents.builtin import EXPLORE_AGENT, GENERAL_AGENT
from dawn_kestrel.skills.loader import SkillLoader
from dawn_kestrel.tools.registry import ToolRegistry


class TestDelegateToolRegistration:
    """Test that DelegateTool is properly registered."""

    def test_delegate_tool_registered(self):
        """Verify delegate tool is in registry."""
        registry = ToolRegistry()
        assert "delegate" in registry.tools, "delegate tool should be registered"

    def test_delegate_tool_has_correct_id(self):
        """Verify delegate tool has correct id."""
        registry = ToolRegistry()
        tool = registry.tools.get("delegate")
        assert tool is not None
        assert tool.id == "delegate"


class TestTodoToolsRegistration:
    """Test that todo tools are properly registered."""

    def test_todo_tools_registered(self):
        """Verify both todo tools are in registry."""
        registry = ToolRegistry()
        assert "todoread" in registry.tools, "todoread tool should be registered"
        assert "todowrite" in registry.tools, "todowrite tool should be registered"


class TestAgentPermissions:
    """Test that agents have correct permissions for todos/delegation."""

    def test_general_agent_can_use_todos(self):
        """Verify GENERAL_AGENT allows todoread and todowrite."""
        # GENERAL_AGENT should not have deny rules for todo tools
        deny_rules = [
            p
            for p in GENERAL_AGENT.permission
            if p.get("action") == "deny" and p.get("permission") in ["todoread", "todowrite"]
        ]
        assert len(deny_rules) == 0, "GENERAL_AGENT should not deny todo tools"

    def test_general_agent_can_delegate(self):
        """Verify GENERAL_AGENT allows delegate."""
        # GENERAL_AGENT has allow all with "*"
        allow_all = [
            p
            for p in GENERAL_AGENT.permission
            if p.get("permission") == "*" and p.get("action") == "allow"
        ]
        assert len(allow_all) > 0, "GENERAL_AGENT should have allow all rule"

    def test_explore_agent_can_use_todos(self):
        """Verify EXPLORE_AGENT allows todo tools."""
        allow_rules = [
            p
            for p in EXPLORE_AGENT.permission
            if p.get("action") == "allow" and p.get("permission") in ["todoread", "todowrite"]
        ]
        assert len(allow_rules) >= 2, "EXPLORE_AGENT should allow todo tools"

    def test_explore_agent_can_delegate(self):
        """Verify EXPLORE_AGENT allows delegate."""
        allow_rules = [
            p
            for p in EXPLORE_AGENT.permission
            if p.get("action") == "allow" and p.get("permission") == "delegate"
        ]
        assert len(allow_rules) >= 1, "EXPLORE_AGENT should allow delegate"


class TestSkillDiscovery:
    """Test that skills are discoverable by SkillLoader."""

    def test_todos_skill_discoverable(self):
        """Verify todos skill is found by SkillLoader."""
        loader = SkillLoader(Path("."))
        skills = loader.discover_skills()
        skill_names = [s.name for s in skills]
        assert "todos" in skill_names, "todos skill should be discoverable"

    def test_delegation_skill_discoverable(self):
        """Verify delegation skill is found by SkillLoader."""
        loader = SkillLoader(Path("."))
        skills = loader.discover_skills()
        skill_names = [s.name for s in skills]
        assert "delegation" in skill_names, "delegation skill should be discoverable"
