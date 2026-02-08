"""Bolt Merlin Agents for Dawn Kestrel

This package provides specialized agents from the Bolt Merlin project,
adapted for use with the Dawn Kestrel SDK.

Agents include:
- Sisyphus: Main orchestrator with full delegation capabilities
- Atlas: Master orchestrator for coordination
- Prometheus: Strategic planning agent
- Hephaestus: Autonomous deep worker
- Oracle: Read-only consultation agent
- Metis: Pre-planning analysis agent
- Momus: Plan validation agent
- Librarian: Docs and codebase search specialist
- Explore: Fast codebase exploration
- Frontend UI/UX Engineer: Frontend development
- Multimodal Looker: PDF/image analysis

Each agent is registered in the AgentRegistry and can be invoked
via the AgentRuntime and AgentOrchestrator.
"""

from __future__ import annotations

# Import agent factories from each subdirectory
from .sisyphus import create_sisyphus_agent
from .oracle import create_oracle_agent
from .librarian import create_librarian_agent
from .explore import create_explore_agent
from .frontend_ui_engineer import create_frontend_ui_ux_skill
from .multimodal_looker import create_multimodal_looker_agent
from .hephaestus import create_hephaestus_agent
from .metis import create_metis_agent
from .momus import create_momus_agent
from .prometheus import create_prometheus_agent
from .atlas import create_atlas_agent

# Re-export all agent factory functions
__all__ = [
    "create_sisyphus_agent",
    "create_oracle_agent",
    "create_librarian_agent",
    "create_explore_agent",
    "create_frontend_ui_ux_skill",
    "create_multimodal_looker_agent",
    "create_hephaestus_agent",
    "create_metis_agent",
    "create_momus_agent",
    "create_prometheus_agent",
    "create_atlas_agent",
]
