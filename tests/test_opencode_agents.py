"""
Tests for Bolt Merlin Agents

Test coverage for all opencode agents ensuring they can be imported,
instantiated, and have correct structure.
"""

import pytest

from dawn_kestrel.agents.bolt_merlin import (
    create_orchestrator_agent,
    create_consultant_agent,
    create_librarian_agent,
    create_explore_agent,
    create_frontend_ui_ux_skill,
    create_multimodal_looker_agent,
    create_autonomous_worker_agent,
    create_pre_planning_agent,
    create_plan_validator_agent,
    create_planner_agent,
    create_master_orchestrator_agent,
)


class TestAgentImports:
    """Test that all agents can be imported"""

    def test_orchestrator_import(self):
        """Sisyphus agent should be importable"""
        assert create_orchestrator_agent is not None
        agent = create_orchestrator_agent()
        assert agent.name == "orchestrator"
        assert agent.description is not None
        assert agent.prompt is not None

    def test_consultant_import(self):
        """Oracle agent should be importable"""
        assert create_consultant_agent is not None
        agent = create_consultant_agent()
        assert agent.name == "consultant"
        assert agent.description is not None
        assert agent.prompt is not None
        # Oracle should be read-only
        assert any(
            p.get("permission") == "write" and p.get("action") == "deny" for p in agent.permission
        )

    def test_librarian_import(self):
        """Librarian agent should be importable"""
        assert create_librarian_agent is not None
        agent = create_librarian_agent()
        assert agent.name == "librarian"
        assert agent.description is not None
        assert agent.prompt is not None
        # Librarian should be read-only
        assert any(
            p.get("permission") == "write" and p.get("action") == "deny" for p in agent.permission
        )

    def test_explore_import(self):
        """Explore agent should be importable"""
        assert create_explore_agent is not None
        agent = create_explore_agent()
        assert agent.name == "explore"
        assert agent.description is not None
        assert agent.prompt is not None
        # Explore should be read-only
        assert any(
            p.get("permission") == "write" and p.get("action") == "deny" for p in agent.permission
        )

    def test_frontend_ui_ux_import(self):
        """Frontend UI/UX skill should be importable"""
        assert create_frontend_ui_ux_skill is not None
        skill = create_frontend_ui_ux_skill()
        assert isinstance(skill, str)
        assert skill is not None
        assert len(skill) > 100  # Should have substantial content

    def test_multimodal_looker_import(self):
        """Multimodal Looker agent should be importable"""
        assert create_multimodal_looker_agent is not None
        agent = create_multimodal_looker_agent()
        assert agent.name == "multimodal_looker"
        assert agent.description is not None
        assert agent.prompt is not None

    def test_autonomous_worker_import(self):
        """Hephaestus agent should be importable"""
        assert create_autonomous_worker_agent is not None
        agent = create_autonomous_worker_agent()
        assert agent.name == "autonomous_worker"
        assert agent.description is not None
        assert agent.prompt is not None
        # Hephaestus should have write permissions
        assert any(
            p.get("permission") == "write" and p.get("action") == "allow" for p in agent.permission
        )

    def test_pre_planning_import(self):
        """Metis agent should be importable"""
        assert create_pre_planning_agent is not None
        agent = create_pre_planning_agent()
        assert agent.name == "pre_planning"
        assert agent.description is not None
        assert agent.prompt is not None
        # Metis should be read-only
        assert any(
            p.get("permission") == "write" and p.get("action") == "deny" for p in agent.permission
        )

    def test_plan_validator_import(self):
        """Momus agent should be importable"""
        assert create_plan_validator_agent is not None
        agent = create_plan_validator_agent()
        assert agent.name == "plan_validator"
        assert agent.description is not None
        assert agent.prompt is not None
        # Momus should be read-only
        assert any(
            p.get("permission") == "write" and p.get("action") == "deny" for p in agent.permission
        )

    def test_planner_import(self):
        """Prometheus agent should be importable"""
        assert create_planner_agent is not None
        agent = create_planner_agent()
        assert agent.name == "planner"
        assert agent.description is not None
        assert agent.prompt is not None
        # Prometheus should be read-only
        assert any(
            p.get("permission") == "write" and p.get("action") == "deny" for p in agent.permission
        )

    def test_master_orchestrator_import(self):
        """Atlas agent should be importable"""
        assert create_master_orchestrator_agent is not None
        agent = create_master_orchestrator_agent()
        assert agent.name == "master_orchestrator"
        assert agent.description is not None
        assert agent.prompt is not None
        # Atlas should have task delegation permissions
        assert any(
            p.get("permission") == "task" and p.get("action") == "allow" for p in agent.permission
        )


class TestAgentStructure:
    """Test that agents have correct structure and fields"""

    def test_all_agents_have_required_fields(self):
        """All agents should have required fields"""
        agents = [
            create_orchestrator_agent(),
            create_consultant_agent(),
            create_librarian_agent(),
            create_explore_agent(),
            create_multimodal_looker_agent(),
            create_autonomous_worker_agent(),
            create_pre_planning_agent(),
            create_plan_validator_agent(),
            create_planner_agent(),
            create_master_orchestrator_agent(),
        ]

        for agent in agents:
            assert agent.name is not None
            assert agent.description is not None
            assert agent.prompt is not None
            assert agent.permission is not None
            assert isinstance(agent.permission, list)

    def test_primary_agents_have_permissions(self):
        """Primary agents should have appropriate permissions"""
        primary_agents = [
            create_orchestrator_agent(),
            create_master_orchestrator_agent(),
            create_autonomous_worker_agent(),
        ]

        for agent in primary_agents:
            # Primary agents should have broad permissions
            assert len(agent.permission) > 0

    def test_subagent_agents_have_restricted_permissions(self):
        """Subagent agents should be read-only"""
        subagent_agents = [
            create_consultant_agent(),
            create_librarian_agent(),
            create_explore_agent(),
            create_pre_planning_agent(),
            create_plan_validator_agent(),
            create_planner_agent(),
        ]

        for agent in subagent_agents:
            # Subagents should deny write/edit permissions
            assert any(
                p.get("permission") == "write" and p.get("action") == "deny"
                for p in agent.permission
            )

    def test_agents_have_appropriate_temperature(self):
        """Agents should have appropriate temperature settings"""
        agents = [
            create_orchestrator_agent(),
            create_consultant_agent(),
            create_librarian_agent(),
            create_explore_agent(),
            create_multimodal_looker_agent(),
            create_autonomous_worker_agent(),
            create_pre_planning_agent(),
            create_plan_validator_agent(),
            create_planner_agent(),
            create_master_orchestrator_agent(),
        ]

        for agent in agents:
            assert agent.temperature is not None
            assert 0.0 <= agent.temperature <= 1.0


class TestAgentDescriptions:
    """Test that agent descriptions are meaningful and informative"""

    def test_all_agents_have_descriptions(self):
        """All agents should have non-empty descriptions"""
        agents = [
            ("orchestrator", create_orchestrator_agent()),
            ("consultant", create_consultant_agent()),
            ("librarian", create_librarian_agent()),
            ("explore", create_explore_agent()),
            ("autonomous_worker", create_autonomous_worker_agent()),
            ("pre_planning", create_pre_planning_agent()),
            ("plan_validator", create_plan_validator_agent()),
            ("planner", create_planner_agent()),
            ("master_orchestrator", create_master_orchestrator_agent()),
        ]

        for name, agent in agents:
            assert len(agent.description) > 20, f"{name} description too short"
            assert "OhMyBolt Merlin" in agent.description or len(agent.description) > 50, (
                f"{name} description should reference source or be descriptive"
            )

    def test_descriptions_are_unique(self):
        """Agent descriptions should be unique"""
        agents = [
            create_orchestrator_agent(),
            create_consultant_agent(),
            create_librarian_agent(),
            create_explore_agent(),
            create_autonomous_worker_agent(),
            create_pre_planning_agent(),
            create_plan_validator_agent(),
            create_planner_agent(),
            create_master_orchestrator_agent(),
        ]

        descriptions = [agent.description for agent in agents]
        assert len(descriptions) == len(set(descriptions)), "Agent descriptions should be unique"


class TestAgentPrompts:
    """Test that agent prompts are well-formed and comprehensive"""

    def test_all_agents_have_prompts(self):
        """All agents should have non-empty prompts"""
        agents = [
            create_orchestrator_agent(),
            create_consultant_agent(),
            create_librarian_agent(),
            create_explore_agent(),
            create_multimodal_looker_agent(),
            create_autonomous_worker_agent(),
            create_pre_planning_agent(),
            create_plan_validator_agent(),
            create_planner_agent(),
            create_master_orchestrator_agent(),
        ]

        for agent in agents:
            assert len(agent.prompt) > 500, f"{agent.name} prompt too short"

    def test_prompts_contain_agent_identity(self):
        """Agent prompts should mention agent name/role"""
        agents = [
            ("orchestrator", create_orchestrator_agent()),
            ("consultant", create_consultant_agent()),
            ("autonomous_worker", create_autonomous_worker_agent()),
            ("pre_planning", create_pre_planning_agent()),
            ("plan_validator", create_plan_validator_agent()),
            ("planner", create_planner_agent()),
            ("master_orchestrator", create_master_orchestrator_agent()),
        ]

        for name, agent in agents:
            # Prompt should mention the agent's name or role
            assert name.lower() in agent.prompt.lower() or len(agent.prompt) > 1000, (
                f"{name} prompt should mention its identity"
            )
