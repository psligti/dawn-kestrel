import importlib

import pytest

from dawn_kestrel.agents.builtin import Agent
from dawn_kestrel.agents.registry import create_agent_registry
from dawn_kestrel.core.plugin_discovery import load_agents


@pytest.mark.asyncio
async def test_load_agents_discovers_builtin_agents() -> None:
    agents = await load_agents()

    assert isinstance(agents, dict)
    assert "build" in agents
    assert "plan" in agents
    assert "general" in agents


@pytest.mark.asyncio
async def test_bolt_merlin_agent_package_removed() -> None:
    with pytest.raises(ImportError):
        importlib.import_module("dawn_kestrel.agents.bolt_merlin")


@pytest.mark.asyncio
async def test_registry_serves_builtin_agents() -> None:
    registry = create_agent_registry()

    build = await registry.get_agent("build")
    plan = await registry.get_agent("plan")
    listed = await registry.list_agents(include_hidden=False)

    assert isinstance(build, Agent)
    assert isinstance(plan, Agent)
    assert any(agent.name == "build" for agent in listed)
    assert any(agent.name == "plan" for agent in listed)
