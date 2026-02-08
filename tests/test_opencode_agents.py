"""
Tests for Bolt Merlin Agents

Test coverage for all opencode agents ensuring they can be imported,
instantiated, and have correct structure.
"""

import pytest

from dawn_kestrel.agents.opencode import (
    create_sisyphus_agent,
    create_oracle_agent,
    create_librarian_agent,
    create_explore_agent,
    create_frontend_ui_ux_skill,
    create_multimodal_looker_agent,
    create_hephaestus_agent,
    create_metis_agent,
    create_momus_agent,
    create_prometheus_agent,
    create_atlas_agent,
)


class TestAgentImports:
    """Test that all agents can be imported"""

    def test_sisyphus_import(self):
        """Sisyphus agent should be importable"""
        assert create_sisyphus_agent is not None
        agent = create_sisyphus_agent()
        assert agent.name == "sisyphus"
        assert agent.description is not None
        assert agent.prompt is not None

    def test_oracle_import(self):
        """Oracle agent should be importable"""
        assert create_oracle_agent is not None
        agent = create_oracle_agent()
        assert agent.name == "oracle"
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

    def test_hephaestus_import(self):
        """Hephaestus agent should be importable"""
        assert create_hephaestus_agent is not None
        agent = create_hephaestus_agent()
        assert agent.name == "hephaestus"
        assert agent.description is not None
        assert agent.prompt is not None
        # Hephaestus should have write permissions
        assert any(
            p.get("permission") == "write" and p.get("action") == "allow" for p in agent.permission
        )

    def test_metis_import(self):
        """Metis agent should be importable"""
        assert create_metis_agent is not None
        agent = create_metis_agent()
        assert agent.name == "metis"
        assert agent.description is not None
        assert agent.prompt is not None
        # Metis should be read-only
        assert any(
            p.get("permission") == "write" and p.get("action") == "deny" for p in agent.permission
        )

    def test_momus_import(self):
        """Momus agent should be importable"""
        assert create_momus_agent is not None
        agent = create_momus_agent()
        assert agent.name == "momus"
        assert agent.description is not None
        assert agent.prompt is not None
        # Momus should be read-only
        assert any(
            p.get("permission") == "write" and p.get("action") == "deny" for p in agent.permission
        )

    def test_prometheus_import(self):
        """Prometheus agent should be importable"""
        assert create_prometheus_agent is not None
        agent = create_prometheus_agent()
        assert agent.name == "prometheus"
        assert agent.description is not None
        assert agent.prompt is not None
        # Prometheus should be read-only
        assert any(
            p.get("permission") == "write" and p.get("action") == "deny" for p in agent.permission
        )

    def test_atlas_import(self):
        """Atlas agent should be importable"""
        assert create_atlas_agent is not None
        agent = create_atlas_agent()
        assert agent.name == "atlas"
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
            create_sisyphus_agent(),
            create_oracle_agent(),
            create_librarian_agent(),
            create_explore_agent(),
            create_multimodal_looker_agent(),
            create_hephaestus_agent(),
            create_metis_agent(),
            create_momus_agent(),
            create_prometheus_agent(),
            create_atlas_agent(),
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
            create_sisyphus_agent(),
            create_atlas_agent(),
            create_hephaestus_agent(),
        ]

        for agent in primary_agents:
            # Primary agents should have broad permissions
            assert len(agent.permission) > 0

    def test_subagent_agents_have_restricted_permissions(self):
        """Subagent agents should be read-only"""
        subagent_agents = [
            create_oracle_agent(),
            create_librarian_agent(),
            create_explore_agent(),
            create_metis_agent(),
            create_momus_agent(),
            create_prometheus_agent(),
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
            create_sisyphus_agent(),
            create_oracle_agent(),
            create_librarian_agent(),
            create_explore_agent(),
            create_multimodal_looker_agent(),
            create_hephaestus_agent(),
            create_metis_agent(),
            create_momus_agent(),
            create_prometheus_agent(),
            create_atlas_agent(),
        ]

        for agent in agents:
            assert agent.temperature is not None
            assert 0.0 <= agent.temperature <= 1.0


class TestAgentDescriptions:
    """Test that agent descriptions are meaningful and informative"""

    def test_all_agents_have_descriptions(self):
        """All agents should have non-empty descriptions"""
        agents = [
            ("sisyphus", create_sisyphus_agent()),
            ("oracle", create_oracle_agent()),
            ("librarian", create_librarian_agent()),
            ("explore", create_explore_agent()),
            ("hephaestus", create_hephaestus_agent()),
            ("metis", create_metis_agent()),
            ("momus", create_momus_agent()),
            ("prometheus", create_prometheus_agent()),
            ("atlas", create_atlas_agent()),
        ]

        for name, agent in agents:
            assert len(agent.description) > 20, f"{name} description too short"
            assert "OhMyBolt Merlin" in agent.description or len(agent.description) > 50, (
                f"{name} description should reference source or be descriptive"
            )

    def test_descriptions_are_unique(self):
        """Agent descriptions should be unique"""
        agents = [
            create_sisyphus_agent(),
            create_oracle_agent(),
            create_librarian_agent(),
            create_explore_agent(),
            create_hephaestus_agent(),
            create_metis_agent(),
            create_momus_agent(),
            create_prometheus_agent(),
            create_atlas_agent(),
        ]

        descriptions = [agent.description for agent in agents]
        assert len(descriptions) == len(set(descriptions)), "Agent descriptions should be unique"


class TestAgentPrompts:
    """Test that agent prompts are well-formed and comprehensive"""

    def test_all_agents_have_prompts(self):
        """All agents should have non-empty prompts"""
        agents = [
            create_sisyphus_agent(),
            create_oracle_agent(),
            create_librarian_agent(),
            create_explore_agent(),
            create_multimodal_looker_agent(),
            create_hephaestus_agent(),
            create_metis_agent(),
            create_momus_agent(),
            create_prometheus_agent(),
            create_atlas_agent(),
        ]

        for agent in agents:
            assert len(agent.prompt) > 500, f"{agent.name} prompt too short"

    def test_prompts_contain_agent_identity(self):
        """Agent prompts should mention agent name/role"""
        agents = [
            ("sisyphus", create_sisyphus_agent()),
            ("oracle", create_oracle_agent()),
            ("hephaestus", create_hephaestus_agent()),
            ("metis", create_metis_agent()),
            ("momus", create_momus_agent()),
            ("prometheus", create_prometheus_agent()),
            ("atlas", create_atlas_agent()),
        ]

        for name, agent in agents:
            # Prompt should mention the agent's name or role
            assert name.lower() in agent.prompt.lower() or len(agent.prompt) > 1000, (
                f"{name} prompt should mention its identity"
            )
