"""
Tests for AgentRegistry

Comprehensive test coverage for register/get/remove/list operations,
case-insensitive lookup, and optional JSON persistence.
"""
from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from dawn_kestrel.agents.registry import AgentRegistry, create_agent_registry
from dawn_kestrel.agents.builtin import Agent


class TestAgentRegistryBasic:
    """Test basic CRUD operations without persistence"""

    def test_registry_seeds_with_builtin_agents(self) -> None:
        """Registry should initialize with built-in agents"""
        registry = AgentRegistry(persistence_enabled=False)

        assert len(registry._agents) > 0

        # Verify known built-in agents exist
        assert registry.get_agent("build") is not None
        assert registry.get_agent("plan") is not None
        assert registry.get_agent("general") is not None
        assert registry.get_agent("explore") is not None

    def test_get_agent_case_insensitive(self) -> None:
        """Agent lookup should be case-insensitive"""
        registry = AgentRegistry(persistence_enabled=False)

        build_upper = registry.get_agent("BUILD")
        build_lower = registry.get_agent("build")
        build_mixed = registry.get_agent("Build")

        assert build_upper is not None
        assert build_lower is not None
        assert build_mixed is not None
        assert build_upper.name == "build"
        assert build_lower.name == "build"
        assert build_mixed.name == "build"

    def test_register_custom_agent(self) -> None:
        """Should be able to register custom agents"""
        registry = AgentRegistry(persistence_enabled=False)

        custom_agent = Agent(
            name="test_agent",
            description="Test agent",
            mode="subagent",
            permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
            native=False,
        )

        result = asyncio.run(registry.register_agent(custom_agent))

        assert result.name == "test_agent"
        assert registry.get_agent("test_agent") is not None

    def test_register_duplicate_name_non_native(self) -> None:
        """Should allow overwriting non-native agents with same name"""
        registry = AgentRegistry(persistence_enabled=False)

        agent1 = Agent(
            name="custom",
            description="First version",
            mode="subagent",
            permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
            native=False,
        )

        agent2 = Agent(
            name="custom",
            description="Second version",
            mode="subagent",
            permission=[{"permission": "*", "pattern": "*", "action": "deny"}],
            native=False,
        )

        asyncio.run(registry.register_agent(agent1))
        asyncio.run(registry.register_agent(agent2))

        retrieved = registry.get_agent("custom")
        assert retrieved is not None
        assert retrieved.description == "Second version"

    def test_register_overwrite_builtin_raises_error(self) -> None:
        """Cannot overwrite built-in agents"""
        registry = AgentRegistry(persistence_enabled=False)

        custom_agent = Agent(
            name="build",
            description="Fake build agent",
            mode="subagent",
            permission=[],
            native=False,
        )

        with pytest.raises(ValueError, match="Cannot overwrite built-in agent"):
            asyncio.run(registry.register_agent(custom_agent))

    def test_list_agents(self) -> None:
        """list_agents should return all registered agents"""
        registry = AgentRegistry(persistence_enabled=False)

        custom_agent = Agent(
            name="custom_test",
            description="Test agent",
            mode="subagent",
            permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
            native=False,
            hidden=False,
        )

        hidden_agent = Agent(
            name="hidden_test",
            description="Hidden agent",
            mode="subagent",
            permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
            native=False,
            hidden=True,
        )

        asyncio.run(registry.register_agent(custom_agent))
        asyncio.run(registry.register_agent(hidden_agent))

        # Default: exclude hidden
        visible_agents = registry.list_agents(include_hidden=False)
        agent_names = [a.name for a in visible_agents]
        assert "custom_test" in agent_names
        assert "hidden_test" not in agent_names

        # Include hidden
        all_agents = registry.list_agents(include_hidden=True)
        agent_names = [a.name for a in all_agents]
        assert "custom_test" in agent_names
        assert "hidden_test" in agent_names

    def test_remove_agent(self) -> None:
        """Should be able to remove non-native agents"""
        registry = AgentRegistry(persistence_enabled=False)

        custom_agent = Agent(
            name="to_remove",
            description="Will be removed",
            mode="subagent",
            permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
            native=False,
        )

        asyncio.run(registry.register_agent(custom_agent))
        assert registry.get_agent("to_remove") is not None

        result = asyncio.run(registry.remove_agent("to_remove"))

        assert result is True
        assert registry.get_agent("to_remove") is None

    def test_remove_builtin_agent_raises_error(self) -> None:
        """Cannot remove built-in agents"""
        registry = AgentRegistry(persistence_enabled=False)

        with pytest.raises(ValueError, match="Cannot remove built-in agent"):
            asyncio.run(registry.remove_agent("build"))

    def test_remove_nonexistent_agent(self) -> None:
        """Removing non-existent agent returns False"""
        registry = AgentRegistry(persistence_enabled=False)

        result = asyncio.run(registry.remove_agent("nonexistent"))

        assert result is False

    def test_has_agent(self) -> None:
        """has_agent should check agent existence"""
        registry = AgentRegistry(persistence_enabled=False)

        assert registry.has_agent("build") is True
        assert registry.has_agent("BUILD") is True
        assert registry.has_agent("nonexistent") is False

    def test_register_trims_whitespace(self) -> None:
        """Agent names should have whitespace trimmed"""
        registry = AgentRegistry(persistence_enabled=False)

        custom_agent = Agent(
            name="  test_agent  ",
            description="Test agent",
            mode="subagent",
            permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
            native=False,
        )

        asyncio.run(registry.register_agent(custom_agent))

        assert registry.get_agent("test_agent") is not None
        assert registry.get_agent("  test_agent  ") is not None


class TestAgentRegistryPersistence:
    """Test JSON persistence functionality"""

    def test_register_agent_persists_to_file(self) -> None:
        """Registered agents should be persisted to JSON files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = AgentRegistry(
                persistence_enabled=True,
                storage_dir=Path(tmpdir),
            )

            custom_agent = Agent(
                name="persistent_agent",
                description="Should persist",
                mode="subagent",
                permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
                native=False,
                temperature=0.7,
                top_p=0.9,
            )

            asyncio.run(registry.register_agent(custom_agent))

            # Verify file exists
            agent_file = Path(tmpdir) / "agent" / "persistent_agent.json"
            assert agent_file.exists()

            # Verify file content
            import json

            with open(agent_file, "r") as f:
                data = json.load(f)

            assert data["name"] == "persistent_agent"
            assert data["description"] == "Should persist"
            assert data["temperature"] == 0.7
            assert data["top_p"] == 0.9
            assert data["native"] is False

    def test_registry_loads_persisted_agents(self) -> None:
        """Registry should load existing agents from storage"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create persisted agent file manually
            agent_dir = Path(tmpdir) / "agent"
            agent_dir.mkdir(parents=True)

            agent_data = {
                "name": "loaded_agent",
                "description": "Loaded from storage",
                "mode": "subagent",
                "permission": [{"permission": "*", "pattern": "*", "action": "allow"}],
                "native": False,
                "hidden": False,
            }

            agent_file = agent_dir / "loaded_agent.json"
            with open(agent_file, "w") as f:
                json.dump(agent_data, f)

            # Create registry and verify it loads the agent
            registry = AgentRegistry(
                persistence_enabled=True,
                storage_dir=Path(tmpdir),
            )

            loaded = registry.get_agent("loaded_agent")
            assert loaded is not None
            assert loaded.description == "Loaded from storage"
            assert loaded.native is False

    def test_remove_agent_deletes_file(self) -> None:
        """Removing an agent should delete persisted file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = AgentRegistry(
                persistence_enabled=True,
                storage_dir=Path(tmpdir),
            )

            custom_agent = Agent(
                name="to_delete",
                description="Will be deleted",
                mode="subagent",
                permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
                native=False,
            )

            asyncio.run(registry.register_agent(custom_agent))

            agent_file = Path(tmpdir) / "agent" / "to_delete.json"
            assert agent_file.exists()

            asyncio.run(registry.remove_agent("to_delete"))

            assert not agent_file.exists()

    def test_builtin_agents_not_overwritten_by_file(self) -> None:
        """Built-in agents should not be overwritten by persisted files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file that tries to override built-in agent
            agent_dir = Path(tmpdir) / "agent"
            agent_dir.mkdir(parents=True)

            agent_data = {
                "name": "build",
                "description": "Fake build agent",
                "mode": "subagent",
                "permission": [],
                "native": False,
                "hidden": False,
            }

            agent_file = agent_dir / "build.json"
            with open(agent_file, "w") as f:
                json.dump(agent_data, f)

            # Registry should skip loading this file
            registry = AgentRegistry(
                persistence_enabled=True,
                storage_dir=Path(tmpdir),
            )

            build = registry.get_agent("build")
            assert build is not None
            assert build.description == "The default agent. Executes tools based on configured permissions."
            assert build.native is True

    def test_persistence_disabled_no_files(self) -> None:
        """With persistence disabled, no files should be created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = AgentRegistry(
                persistence_enabled=False,
                storage_dir=Path(tmpdir),
            )

            custom_agent = Agent(
                name="no_persist",
                description="Should not persist",
                mode="subagent",
                permission=[{"permission": "*", "pattern": "*", "action": "allow"}],
                native=False,
            )

            asyncio.run(registry.register_agent(custom_agent))

            agent_dir = Path(tmpdir) / "agent"
            assert not agent_dir.exists()

    def test_register_agent_with_all_fields(self) -> None:
        """All agent fields should be persisted correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = AgentRegistry(
                persistence_enabled=True,
                storage_dir=Path(tmpdir),
            )

            custom_agent = Agent(
                name="full_agent",
                description="Full featured agent",
                mode="primary",
                permission=[
                    {"permission": "bash", "pattern": "*", "action": "allow"},
                    {"permission": "write", "pattern": "*.py", "action": "deny"},
                ],
                native=False,
                hidden=False,
                temperature=0.8,
                top_p=0.95,
                color="#FF5733",
                model={"provider": "anthropic", "model": "claude-sonnet-4"},
                prompt="You are a helpful assistant.",
                options={"max_tokens": 4096},
                steps=5,
            )

            asyncio.run(registry.register_agent(custom_agent))

            agent_file = Path(tmpdir) / "agent" / "full_agent.json"
            with open(agent_file, "r") as f:
                data = json.load(f)

            assert data["name"] == "full_agent"
            assert data["temperature"] == 0.8
            assert data["top_p"] == 0.95
            assert data["color"] == "#FF5733"
            assert data["model"] == {"provider": "anthropic", "model": "claude-sonnet-4"}
            assert data["prompt"] == "You are a helpful assistant."
            assert data["options"] == {"max_tokens": 4096}
            assert data["steps"] == 5
            assert len(data["permission"]) == 2


class TestAgentRegistryFactory:
    """Test factory function"""

    def test_create_agent_registry_defaults(self) -> None:
        """Factory should create registry with default settings"""
        registry = create_agent_registry()

        assert registry.persistence_enabled is False
        assert registry.storage_dir is None
        assert len(registry._agents) > 0

    def test_create_agent_registry_with_persistence(self) -> None:
        """Factory should create registry with persistence enabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = create_agent_registry(
                persistence_enabled=True,
                storage_dir=Path(tmpdir),
            )

            assert registry.persistence_enabled is True
            assert registry.storage_dir == Path(tmpdir)
