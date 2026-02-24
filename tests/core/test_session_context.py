"""Tests for AgentContext session-related fields (workspace, credentials, config).

Tests the extension of AgentContext to include:
- workspace_id: For workspace isolation
- credential_scope: For credential scoping
- config_overrides: For session-specific configuration
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from dawn_kestrel.context.builder import ContextBuilder
from dawn_kestrel.core.agent_types import AgentContext
from dawn_kestrel.core.models import Session
from dawn_kestrel.tools.framework import ToolRegistry


@pytest.fixture
def context_builder():
    """Create context builder for testing."""
    return ContextBuilder(base_dir=Path("/tmp"))


@pytest.fixture
def sample_session():
    """Create sample session for testing."""
    return Session(
        id="test-session-123",
        slug="test-session",
        project_id="test-project",
        directory="/tmp/test",
        title="Test Session",
        version="1.0.0",
    )


@pytest.fixture
def sample_agent():
    """Create sample agent configuration."""
    return {
        "name": "build",
        "description": "Default agent",
        "mode": "primary",
        "permission": [
            {"permission": "*", "pattern": "*", "action": "allow"},
        ],
        "prompt": "You are a helpful assistant.",
    }


@pytest.fixture
def sample_tools():
    """Create sample tool registry."""
    return ToolRegistry()


# ===== AgentContext New Fields Tests =====


def test_agent_context_has_workspace_id_field():
    """Test that AgentContext includes workspace_id field."""
    context = AgentContext(
        system_prompt="Test",
        tools=ToolRegistry(),
        messages=[],
    )

    # Field should exist and be optional (default None)
    assert hasattr(context, "workspace_id")
    assert context.workspace_id is None


def test_agent_context_has_credential_scope_field():
    """Test that AgentContext includes credential_scope field."""
    context = AgentContext(
        system_prompt="Test",
        tools=ToolRegistry(),
        messages=[],
    )

    # Field should exist and be optional (default None)
    assert hasattr(context, "credential_scope")
    assert context.credential_scope is None


def test_agent_context_has_config_overrides_field():
    """Test that AgentContext includes config_overrides field."""
    context = AgentContext(
        system_prompt="Test",
        tools=ToolRegistry(),
        messages=[],
    )

    # Field should exist and be optional (default empty dict)
    assert hasattr(context, "config_overrides")
    assert context.config_overrides == {}


def test_agent_context_accepts_workspace_id():
    """Test that AgentContext can be created with workspace_id."""
    context = AgentContext(
        system_prompt="Test",
        tools=ToolRegistry(),
        messages=[],
        workspace_id="workspace-abc-123",
    )

    assert context.workspace_id == "workspace-abc-123"


def test_agent_context_accepts_credential_scope():
    """Test that AgentContext can be created with credential_scope."""
    context = AgentContext(
        system_prompt="Test",
        tools=ToolRegistry(),
        messages=[],
        credential_scope="repo:acme/webapp",
    )

    assert context.credential_scope == "repo:acme/webapp"


def test_agent_context_accepts_config_overrides():
    """Test that AgentContext can be created with config_overrides."""
    overrides = {
        "max_tokens": 4096,
        "temperature": 0.7,
        "custom_setting": "value",
    }

    context = AgentContext(
        system_prompt="Test",
        tools=ToolRegistry(),
        messages=[],
        config_overrides=overrides,
    )

    assert context.config_overrides == overrides
    assert context.config_overrides["max_tokens"] == 4096


def test_agent_context_all_new_fields_together():
    """Test that AgentContext can be created with all new fields."""
    context = AgentContext(
        system_prompt="Test prompt",
        tools=ToolRegistry(),
        messages=[],
        workspace_id="ws-production",
        credential_scope="org:acme",
        config_overrides={"timeout": 30},
    )

    assert context.workspace_id == "ws-production"
    assert context.credential_scope == "org:acme"
    assert context.config_overrides == {"timeout": 30}


# ===== ContextBuilder Population Tests =====


@pytest.mark.asyncio
async def test_build_agent_context_inherits_workspace_from_session(
    context_builder, sample_session, sample_agent, sample_tools
):
    """Test that ContextBuilder populates workspace_id from session."""
    # Session with workspace in metadata
    sample_session.metadata = {"workspace_id": "ws-789"}

    result = await context_builder.build_agent_context(
        session=sample_session,
        agent=sample_agent,
        tools=sample_tools,
        skills=[],
    )

    assert result.workspace_id == "ws-789"


@pytest.mark.asyncio
async def test_build_agent_context_inherits_credential_scope_from_session(
    context_builder, sample_session, sample_agent, sample_tools
):
    """Test that ContextBuilder populates credential_scope from session."""
    # Session with credential scope in metadata
    sample_session.metadata = {"credential_scope": "project:my-app"}

    result = await context_builder.build_agent_context(
        session=sample_session,
        agent=sample_agent,
        tools=sample_tools,
        skills=[],
    )

    assert result.credential_scope == "project:my-app"


@pytest.mark.asyncio
async def test_build_agent_context_inherits_config_overrides_from_session(
    context_builder, sample_agent, sample_tools
):
    """Test that ContextBuilder populates config_overrides from session."""
    session = Session(
        id="test-session-456",
        slug="test",
        project_id="proj",
        directory="/tmp",
        title="Test",
        version="1.0",
        metadata={"config_overrides": {"model": "claude-3-opus"}},
    )

    result = await context_builder.build_agent_context(
        session=session,
        agent=sample_agent,
        tools=sample_tools,
        skills=[],
    )

    assert result.config_overrides == {"model": "claude-3-opus"}


@pytest.mark.asyncio
async def test_build_agent_context_no_session_metadata_uses_defaults(
    context_builder, sample_session, sample_agent, sample_tools
):
    """Test that ContextBuilder uses defaults when session has no metadata."""
    # Session without metadata
    sample_session.metadata = None

    result = await context_builder.build_agent_context(
        session=sample_session,
        agent=sample_agent,
        tools=sample_tools,
        skills=[],
    )

    # Should have defaults
    assert result.workspace_id is None
    assert result.credential_scope is None
    assert result.config_overrides == {}


@pytest.mark.asyncio
async def test_build_agent_context_partial_metadata(
    context_builder, sample_session, sample_agent, sample_tools
):
    """Test ContextBuilder with partial metadata in session."""
    # Only workspace_id, no credential_scope or config_overrides
    sample_session.metadata = {"workspace_id": "ws-partial"}

    result = await context_builder.build_agent_context(
        session=sample_session,
        agent=sample_agent,
        tools=sample_tools,
        skills=[],
    )

    assert result.workspace_id == "ws-partial"
    assert result.credential_scope is None
    assert result.config_overrides == {}


# ===== Serialization Tests =====


def test_agent_context_is_serializable():
    """Test that AgentContext with new fields can be serialized."""
    context = AgentContext(
        system_prompt="Test",
        tools=ToolRegistry(),
        messages=[],
        workspace_id="ws-123",
        credential_scope="org:test",
        config_overrides={"key": "value"},
    )

    # Convert to dict (dataclass asdict)
    from dataclasses import asdict

    data = asdict(context)

    assert data["workspace_id"] == "ws-123"
    assert data["credential_scope"] == "org:test"
    assert data["config_overrides"] == {"key": "value"}


def test_agent_context_json_serializable():
    """Test that AgentContext new fields are JSON serializable."""
    import json

    context = AgentContext(
        system_prompt="Test",
        tools=ToolRegistry(),
        messages=[],
        workspace_id="ws-456",
        credential_scope="repo:owner/name",
        config_overrides={"nested": {"key": "value"}, "list": [1, 2, 3]},
    )

    from dataclasses import asdict

    data = asdict(context)

    # Remove non-serializable tools field for this test
    data.pop("tools", None)

    # Should not raise
    json_str = json.dumps(data)
    parsed = json.loads(json_str)

    assert parsed["workspace_id"] == "ws-456"
    assert parsed["credential_scope"] == "repo:owner/name"
    assert parsed["config_overrides"]["nested"]["key"] == "value"


# ===== Backward Compatibility Tests =====


def test_agent_context_backward_compatible():
    """Test that existing code without new fields still works."""
    # Old-style creation - should still work
    context = AgentContext(
        system_prompt="Test",
        tools=ToolRegistry(),
        messages=[],
        session=None,
        agent=None,
    )

    # New fields should have safe defaults
    assert context.workspace_id is None
    assert context.credential_scope is None
    assert context.config_overrides == {}


def test_agent_context_with_session_object():
    """Test AgentContext with actual Session object."""
    session = Session(
        id="session-789",
        slug="my-session",
        project_id="proj-123",
        directory="/workspace/my-project",
        title="My Session",
        version="1.0.0",
    )

    context = AgentContext(
        system_prompt="Test",
        tools=ToolRegistry(),
        messages=[],
        session=session,
    )

    assert context.session == session
    # New fields should still have defaults
    assert context.workspace_id is None
    assert context.credential_scope is None
    assert context.config_overrides == {}
