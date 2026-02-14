"""DelegateTool for agent-based delegation.

Provides a Tool interface for the DelegationEngine, allowing agents to
spawn and coordinate subagents with convergence guarantees.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from dawn_kestrel.tools.framework import Tool, ToolContext, ToolResult

from .engine import DelegationEngine
from .types import DelegationBudget, DelegationConfig, TraversalMode

if TYPE_CHECKING:
    from dawn_kestrel.agents.registry import AgentRegistry
    from dawn_kestrel.agents.runtime import AgentRuntime
    from dawn_kestrel.core.agent_types import SessionManagerLike


class DelegateTool(Tool):
    """Tool for spawning and coordinating subagents with convergence guarantees.

    This tool wraps the DelegationEngine and exposes it as a Tool that agents
    can use to delegate work to subagents with configurable traversal modes
    (BFS, DFS, Adaptive) and boundary enforcement.

    Attributes:
        _runtime: AgentRuntime for executing agents.
        _registry: AgentRegistry for fetching agent definitions.
        _session_manager: SessionManager for session operations.
    """

    id = "delegate"
    description = "Spawn and coordinate subagents with convergence guarantees"
    category = "delegation"
    tags = ["agent", "subagent", "parallel", "coordination"]

    def __init__(
        self,
        runtime: Optional["AgentRuntime"] = None,
        registry: Optional["AgentRegistry"] = None,
        session_manager: Optional["SessionManagerLike"] = None,
    ):
        """Initialize the DelegateTool.

        Args:
            runtime: AgentRuntime for executing agents.
            registry: AgentRegistry for fetching agent definitions.
            session_manager: SessionManager for session operations.
        """
        self._runtime = runtime
        self._registry = registry
        self._session_manager = session_manager

    def parameters(self) -> Dict[str, Any]:
        """Get JSON schema for tool parameters.

        Returns:
            JSON schema for LLM function calling.
        """
        return {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "Name of agent to delegate to",
                },
                "prompt": {
                    "type": "string",
                    "description": "Prompt for the agent",
                },
                "mode": {
                    "type": "string",
                    "enum": ["breadth_first", "depth_first", "adaptive"],
                    "default": "breadth_first",
                    "description": "Traversal mode for delegation",
                },
                "children": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Child delegations to spawn",
                },
                "budget": {
                    "type": "object",
                    "description": "Budget limits (max_depth, max_breadth, etc.)",
                },
            },
            "required": ["agent", "prompt"],
        }

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Execute the delegation.

        Args:
            args: Tool arguments including agent, prompt, mode, children, budget.
            ctx: Tool execution context.

        Returns:
            ToolResult with delegation summary.
        """
        # Parse mode
        mode_str = args.get("mode", "breadth_first")
        mode_map = {
            "breadth_first": TraversalMode.BFS,
            "depth_first": TraversalMode.DFS,
            "adaptive": TraversalMode.ADAPTIVE,
        }
        mode = mode_map.get(mode_str, TraversalMode.BFS)

        # Parse budget
        budget_dict = args.get("budget", {})
        if budget_dict:
            budget = DelegationBudget(**budget_dict)
        else:
            budget = DelegationBudget()

        # Create config and engine
        config = DelegationConfig(mode=mode, budget=budget)
        engine = DelegationEngine(config, self._runtime, self._registry)

        # Execute delegation
        result = await engine.delegate(
            agent_name=args.get("agent", "general"),
            prompt=args.get("prompt", ""),
            session_id=ctx.session_id,
            session_manager=self._session_manager,
            tools=None,
            children=args.get("children"),
        )

        # Build result
        if result.is_ok():
            delegation_result = result.unwrap()
            return ToolResult(
                title="Delegation complete",
                output=f"Spawned {delegation_result.total_agents} agents, "
                f"converged: {delegation_result.converged}",
                metadata={
                    "success": delegation_result.success,
                    "total_agents": delegation_result.total_agents,
                    "converged": delegation_result.converged,
                    "stop_reason": delegation_result.stop_reason.value,
                    "max_depth_reached": delegation_result.max_depth_reached,
                    "elapsed_seconds": delegation_result.elapsed_seconds,
                },
            )
        else:
            # Handle error case - unwrap_or returns None, but we need error info
            error_msg = getattr(result, "error", "Unknown error")
            error_code = getattr(result, "code", None)
            return ToolResult(
                title="Delegation failed",
                output=f"Error: {error_msg}",
                metadata={"error": error_msg, "code": error_code},
            )


def create_delegation_tool(
    runtime: "AgentRuntime",
    registry: "AgentRegistry",
    session_manager: Optional["SessionManagerLike"] = None,
) -> DelegateTool:
    """Factory function to create a DelegateTool with injected dependencies.

    Args:
        runtime: AgentRuntime for executing agents.
        registry: AgentRegistry for fetching agent definitions.
        session_manager: Optional SessionManager for session operations.

    Returns:
        Configured DelegateTool instance.
    """
    return DelegateTool(
        runtime=runtime,
        registry=registry,
        session_manager=session_manager,
    )
