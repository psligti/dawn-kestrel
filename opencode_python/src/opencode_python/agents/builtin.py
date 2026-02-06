"""OpenCode Python - Agent definitions"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Agent:
    """Agent definition"""

    name: str
    description: str
    mode: str  # "subagent", "primary", "all"
    permission: List[Dict[str, Any]]  # Ruleset
    native: bool = True
    hidden: bool = False
    top_p: Optional[float] = None
    temperature: Optional[float] = None
    color: Optional[str] = None
    model: Optional[Dict[str, str]] = None  # providerID/modelID
    prompt: Optional[str] = None  # Custom system prompt
    options: Optional[Dict[str, Any]] = None
    steps: Optional[int] = None


# Built-in agents matching TypeScript OpenCode
PLAN_ORCHESTRATION_CONTROLS = """Planning orchestration controls (canonical spec: opencode_python/docs/planning-agent-orchestration.md):
- Budget defaults: max_iterations=5, max_subagent_calls=8, max_wall_time=5 minutes.
- Evidence rule: each iteration must add new evidence, reduce uncertainty, increase confidence, or falsify a hypothesis.
- Stagnation triggers: repeated failure signature, no new files for 2 iterations, confidence plateau, redundant queries.
- Strategy switch: on stagnation, declare current strategy failed and switch approach with reduced budget (max_iterations=2, max_subagent_calls=3).
- Deterministic stop reasons: recommendation_ready, blocking_question, budget_exhausted, stagnation, human_required.
"""


BUILD_AGENT = Agent(
    name="build",
    description="The default agent. Executes tools based on configured permissions.",
    mode="primary",
    native=True,
    permission=[
        {"permission": "*", "pattern": "*", "action": "allow"},
        {"permission": "question", "pattern": "*", "action": "allow"},
        {"permission": "plan_enter", "pattern": "*", "action": "allow"},
    ],
)

PLAN_AGENT = Agent(
    name="plan",
    description="Plan mode. Disallows all edit tools.",
    mode="primary",
    native=True,
    prompt="You are the planning agent. Produce an actionable recommendation or one precise blocking question. Follow the canonical policy in opencode_python/docs/planning-agent-orchestration.md.",
    permission=[
        {"permission": "*", "pattern": "*", "action": "allow"},
        {"permission": "question", "pattern": "*", "action": "allow"},
        {"permission": "plan_exit", "pattern": "*", "action": "deny"},
        {"permission": "edit", "pattern": "*", "action": "deny"},
        {"permission": "write", "pattern": "*", "action": "deny"},
        {"permission": "plan_exit", "pattern": ".opencode/plans/*.md", "action": "allow"},
    ],
    options={"planning_orchestration_controls": PLAN_ORCHESTRATION_CONTROLS},
)

GENERAL_AGENT = Agent(
    name="general",
    description="General-purpose agent for researching complex questions and executing multi-step tasks. Use this agent to execute multiple units of work in parallel.",
    mode="subagent",
    native=True,
    permission=[
        {"permission": "*", "pattern": "*", "action": "allow"},
        {"permission": "todoread", "pattern": "*", "action": "deny"},
        {"permission": "todowrite", "pattern": "*", "action": "deny"},
    ],
)

EXPLORE_AGENT = Agent(
    name="explore",
    description='Fast agent specialized for exploring codebases. Use this when you need to quickly find files by patterns (eg. "src/components/**/*.tsx"), search code for keywords (eg. "API endpoints"), or answer questions about codebase (eg. "how do API endpoints work?"). When calling this agent, specify desired thoroughness level: "quick" for basic searches, "medium" for moderate exploration, or "very thorough" for comprehensive analysis across multiple locations and naming conventions.',
    mode="subagent",
    native=True,
    permission=[
        {"permission": "*", "pattern": "*", "action": "deny"},
        {"permission": "grep", "pattern": "*", "action": "allow"},
        {"permission": "glob", "pattern": "*", "action": "allow"},
        {"permission": "list", "pattern": "*", "action": "allow"},
        {"permission": "bash", "pattern": "*", "action": "allow"},
        {"permission": "webfetch", "pattern": "*", "action": "allow"},
        {"permission": "websearch", "pattern": "*", "action": "allow"},
        {"permission": "codesearch", "pattern": "*", "action": "allow"},
        {"permission": "read", "pattern": "*", "action": "allow"},
        {"permission": "external_directory", "pattern": "/path/to/truncate/dir", "action": "allow"},
        {"permission": "external_directory", "pattern": "/path/to/glob", "action": "allow"},
    ],
)


# Default agent for plan mode
PLAN_DEFAULTS = [
    {
        "permission": "question",
        "pattern": "deny",
    },
]


def get_all_agents() -> List[Agent]:
    """Get all available agents"""
    return [BUILD_AGENT, PLAN_AGENT, GENERAL_AGENT, EXPLORE_AGENT]


def get_agent_by_name(name: str) -> Optional[Agent]:
    """Get an agent by name (case-insensitive)"""
    name_lower = name.lower()
    agents = get_all_agents()
    for agent in agents:
        if agent.name.lower() == name_lower:
            return agent
    return None
