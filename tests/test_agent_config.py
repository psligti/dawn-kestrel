"""Tests for agent configuration and audit trail"""
import pytest

from opencode_python.agents import (
    AgentConfig,
    AuditEntry,
    AgentConfigStorage,
)


class TestAgentConfig:
    """Test AgentConfig model"""

    def test_create_config(self):
        config = AgentConfig(
            session_id="test-session",
            agent_profile_id="coder",
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
            budget=100000,
        )
        assert config.session_id == "test-session"
        assert config.agent_profile_id == "coder"
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.temperature == 0.7
        assert config.budget == 100000

    def test_update_field(self):
        config = AgentConfig(
            session_id="test-session",
            agent_profile_id="coder",
            model="claude-3-5-sonnet-20241022",
        )
        config.update_field("model", "gpt-4", "user", "Testing new model")
        assert config.model == "gpt-4"
        assert len(config.audit_trail) == 1
        assert config.audit_trail[0].field == "model"
        assert config.audit_trail[0].old_value == "claude-3-5-sonnet-20241022"
        assert config.audit_trail[0].new_value == "gpt-4"
        assert config.audit_trail[0].action_source == "user"

    def test_update_field_no_change(self):
        config = AgentConfig(
            session_id="test-session",
            agent_profile_id="coder",
            model="claude-3-5-sonnet-20241022",
        )
        initial_trail_count = len(config.audit_trail)
        config.update_field("model", "claude-3-5-sonnet-20241022", "user")
        assert len(config.audit_trail) == initial_trail_count

    def test_get_model_fallback(self):
        config = AgentConfig(
            session_id="test-session",
            agent_profile_id="coder",
            model=None,
        )
        assert config.get_model("gpt-4") == "gpt-4"
        assert config.get_model(None) == "claude-3-5-sonnet-20241022"

    def test_get_temperature_fallback(self):
        config = AgentConfig(
            session_id="test-session",
            agent_profile_id="coder",
            temperature=None,
        )
        assert config.get_temperature(0.5) == 0.5
        assert config.get_temperature(None) == 0.7

    def test_get_budget_fallback(self):
        config = AgentConfig(
            session_id="test-session",
            agent_profile_id="coder",
            budget=None,
        )
        assert config.get_budget(50000) == 50000
        assert config.get_budget(None) is None

    def test_get_audit_summary(self):
        config = AgentConfig(
            session_id="test-session",
            agent_profile_id="coder",
        )
        config.update_field("model", "gpt-4", "user", "Testing")
        config.update_field("temperature", 0.5, "user", "Testing")

        summary = config.get_audit_summary()
        assert len(summary) == 2
        assert summary[0]["field"] == "model"
        assert summary[1]["field"] == "temperature"

    def test_from_profile(self):
        config = AgentConfig.from_profile(
            session_id="test-session",
            agent_profile_id="coder",
            profile_model="claude-3-5-sonnet-20241022",
            profile_temperature=0.8,
            profile_budget=50000,
        )
        assert config.session_id == "test-session"
        assert config.agent_profile_id == "coder"
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.temperature == 0.8
        assert config.budget == 50000
        assert len(config.audit_trail) == 3


class TestAgentConfigStorage:
    """Test AgentConfigStorage"""

    def test_save_and_load(self):
        storage = AgentConfigStorage()
        config = AgentConfig(
            session_id="test-session",
            agent_profile_id="coder",
        )

        storage.save(config)
        loaded = storage.load("test-session")

        assert loaded is not None
        assert loaded.session_id == "test-session"
        assert loaded.agent_profile_id == "coder"

    def test_load_not_found(self):
        storage = AgentConfigStorage()
        loaded = storage.load("nonexistent")
        assert loaded is None

    def test_delete(self):
        storage = AgentConfigStorage()
        config = AgentConfig(
            session_id="test-session",
            agent_profile_id="coder",
        )
        storage.save(config)

        assert storage.delete("test-session") is True
        assert storage.load("test-session") is None
        assert storage.delete("test-session") is False

    def test_update_field(self):
        storage = AgentConfigStorage()
        config = AgentConfig(
            session_id="test-session",
            agent_profile_id="coder",
            model="claude-3-5-sonnet-20241022",
        )
        storage.save(config)

        result = storage.update_field(
            "test-session",
            "model",
            "gpt-4",
            "user",
            "Testing update"
        )

        assert result is True
        loaded = storage.load("test-session")
        assert loaded.model == "gpt-4"
        assert len(loaded.audit_trail) == 1

    def test_update_field_not_found(self):
        storage = AgentConfigStorage()
        result = storage.update_field(
            "nonexistent",
            "model",
            "gpt-4",
            "user",
        )
        assert result is False

    def test_list_all(self):
        storage = AgentConfigStorage()
        config1 = AgentConfig(session_id="session-1", agent_profile_id="coder")
        config2 = AgentConfig(session_id="session-2", agent_profile_id="reviewer")

        storage.save(config1)
        storage.save(config2)

        all_configs = storage.list_all()
        assert len(all_configs) == 2
        assert "session-1" in all_configs
        assert "session-2" in all_configs
