"""Bolt Merlin Agents for Dawn Kestrel

This package provides specialized agents from the Bolt Merlin project,
adapted for use with the Dawn Kestrel SDK.

Agents include:
- Orchestrator: Main orchestrator with full delegation capabilities
- Master Orchestrator: Master orchestrator for coordination
- Planner: Strategic planning agent
- Autonomous Worker: Autonomous deep worker
- Consultant: Read-only consultation agent
- Pre-Planning: Pre-planning analysis agent
- Plan Validator: Plan validation agent
- Librarian: Docs and codebase search specialist
- Explore: Fast codebase exploration
- Frontend UI/UX Engineer: Frontend development
- Multimodal Looker: PDF/image analysis

Each agent is registered in the AgentRegistry and can be invoked
via AgentRuntime and AgentOrchestrator.
"""

from __future__ import annotations

# Import agent factories from each subdirectory
from .orchestrator import create_orchestrator_agent
from .master_orchestrator import create_master_orchestrator_agent
from .planner import create_planner_agent
from .autonomous_worker import create_autonomous_worker_agent
from .consultant import create_consultant_agent
from .pre_planning import create_pre_planning_agent
from .plan_validator import create_plan_validator_agent
from .librarian import create_librarian_agent
from .explore import create_explore_agent
from .frontend_ui_engineer import create_frontend_ui_ux_skill
from .multimodal_looker import create_multimodal_looker_agent

# Import registry functions
from .registry import (
    get_bolt_merlin_agents,
    get_bolt_merlin_agent_names,
    get_bolt_merlin_agent,
    clear_agent_cache,
    register_bolt_merlin_agent,
    get_bolt_merlin_agent_descriptions,
)

# Re-export all agent factory functions and registry functions
__all__ = [
    "create_orchestrator_agent",
    "create_master_orchestrator_agent",
    "create_planner_agent",
    "create_autonomous_worker_agent",
    "create_consultant_agent",
    "create_pre_planning_agent",
    "create_plan_validator_agent",
    "create_librarian_agent",
    "create_explore_agent",
    "create_frontend_ui_ux_skill",
    "create_multimodal_looker_agent",
    "get_bolt_merlin_agents",
    "get_bolt_merlin_agent_names",
    "get_bolt_merlin_agent",
    "clear_agent_cache",
    "register_bolt_merlin_agent",
    "get_bolt_merlin_agent_descriptions",
]
