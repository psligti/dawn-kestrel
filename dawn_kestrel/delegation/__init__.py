"""Delegation Engine Package.

Provides multi-agent delegation with configurable traversal strategies
(BFS, DFS, Adaptive), boundary enforcement, and convergence detection.

Example:
    from dawn_kestrel.delegation import (
        DelegationEngine,
        DelegationConfig,
        DelegationBudget,
        TraversalMode,
    )

    config = DelegationConfig(
        mode=TraversalMode.BFS,
        budget=DelegationBudget(
            max_depth=3,
            max_breadth=5,
            max_total_agents=20,
        ),
    )

    engine = DelegationEngine(config, runtime, registry)
    result = await engine.delegate(
        agent_name="orchestrator",
        prompt="Analyze the codebase",
        session_id="session_123",
        session_manager=session_manager,
        children=[
            {"agent": "explore", "prompt": "Find Python files"},
            {"agent": "librarian", "prompt": "Check documentation"},
        ],
    )
"""

from dawn_kestrel.delegation.types import (
    DelegationBudget,
    DelegationConfig,
    DelegationContext,
    DelegationResult,
    DelegationStopReason,
    TraversalMode,
)
from dawn_kestrel.delegation.convergence import ConvergenceTracker
from dawn_kestrel.delegation.engine import DelegationEngine
from dawn_kestrel.delegation.tool import DelegateTool, create_delegation_tool

__all__ = [
    # Core types
    "TraversalMode",
    "DelegationStopReason",
    "DelegationBudget",
    "DelegationConfig",
    "DelegationContext",
    "DelegationResult",
    # Convergence tracking
    "ConvergenceTracker",
    # Engine
    "DelegationEngine",
    # Tool integration
    "DelegateTool",
    "create_delegation_tool",
]
