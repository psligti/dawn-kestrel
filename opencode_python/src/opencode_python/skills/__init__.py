"""OpenCode Python - Skills package

Skills provide specialized capabilities to the agent, such as planning, refactoring,
test generation, and documentation. Each skill has a contract (prompt template
and output schema) and can be enabled/disabled per session.
"""

from opencode_python.skills.models import Skill, SkillState
from opencode_python.skills.registry import SkillRegistry
from opencode_python.skills.contracts import (
    SkillContract,
    PlanningOutput,
    RefactorOutput,
    TestGenerationOutput,
    DocsOutput,
)
from opencode_python.skills.blocking import SkillBlockingInterceptor

__all__ = [
    # Models
    "Skill",
    "SkillState",
    # Registry
    "SkillRegistry",
    # Contracts
    "SkillContract",
    "PlanningOutput",
    "RefactorOutput",
    "TestsOutput",
    "DocsOutput",
    # Blocking
    "SkillBlockingInterceptor",
]
