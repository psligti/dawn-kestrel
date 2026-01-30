"""OpenCode Python - Agent profiles for TUI selection"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass, field
import pydantic as pd


__all__ = [
    "AgentProfile",
    "Prerequisite",
    "get_default_profiles",
    "get_profile_by_id",
    "check_prerequisites",
]


class Prerequisite(pd.BaseModel):
    """Prerequisite for an agent profile"""

    type: Literal["skill", "tool", "provider"]
    id: str
    name: str
    description: str = ""


class AgentProfile(pd.BaseModel):
    """Agent profile for TUI selection

    Defines agent capabilities, requirements, and default configuration.
    This is different from the Agent execution model - this is for user-facing
    agent selection in the TUI.
    """

    # Identification
    id: str
    name: str
    description: str

    # Default configuration
    default_model: Optional[str] = None
    default_temperature: float = 0.7
    default_budget: Optional[int] = None  # Token budget

    # Requirements
    required_skills: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    required_providers: List[str] = field(default_factory=list)
    prerequisites: List[Prerequisite] = field(default_factory=list)

    # Capabilities (what the agent can do)
    capabilities: List[str] = field(default_factory=list)

    # Additional metadata
    color: Optional[str] = None
    category: str = "general"
    tags: List[str] = field(default_factory=list)

    class Config:
        extra = "forbid"

    def get_missing_prerequisites(
        self,
        available_skills: List[str],
        available_tools: List[str],
        available_providers: List[str]
    ) -> List[Prerequisite]:
        """Check what prerequisites are missing

        Args:
            available_skills: List of enabled skill IDs
            available_tools: List of available tool IDs
            available_providers: List of configured provider IDs

        Returns:
            List of missing prerequisites
        """
        missing = []

        # Check skills
        for skill_id in self.required_skills:
            if skill_id not in available_skills:
                missing.append(Prerequisite(
                    type="skill",
                    id=skill_id,
                    name=skill_id,
                    description=f"Skill '{skill_id}' is required for this agent"
                ))

        # Check tools
        for tool_id in self.required_tools:
            if tool_id not in available_tools:
                missing.append(Prerequisite(
                    type="tool",
                    id=tool_id,
                    name=tool_id,
                    description=f"Tool '{tool_id}' is required for this agent"
                ))

        # Check providers
        for provider_id in self.required_providers:
            if provider_id not in available_providers:
                missing.append(Prerequisite(
                    type="provider",
                    id=provider_id,
                    name=provider_id,
                    description=f"Provider '{provider_id}' is required for this agent"
                ))

        return missing

    def has_prerequisites(
        self,
        available_skills: List[str],
        available_tools: List[str],
        available_providers: List[str]
    ) -> bool:
        """Check if all prerequisites are met

        Args:
            available_skills: List of enabled skill IDs
            available_tools: List of available tool IDs
            available_providers: List of configured provider IDs

        Returns:
            True if all prerequisites are met
        """
        return len(self.get_missing_prerequisites(
            available_skills,
            available_tools,
            available_providers
        )) == 0


# Default agent profiles for MVP
CODER_PROFILE = AgentProfile(
    id="coder",
    name="Coder",
    description="Full-stack development agent for writing, testing, and debugging code. Best for feature implementation, bug fixes, and refactoring tasks.",
    default_temperature=0.7,
    default_budget=None,
    required_skills=[
        "code_generation",
        "test_generation",
        "code_review",
    ],
    required_tools=[
        "read",
        "write",
        "bash",
        "grep",
    ],
    required_providers=[],
    capabilities=[
        "Write new code from scratch",
        "Modify existing code",
        "Generate unit tests",
        "Debug and fix issues",
        "Refactor code structure",
        "Apply code reviews",
        "Execute shell commands",
    ],
    color="blue",
    category="development",
    tags=["code", "development", "testing"],
)

REVIEWER_PROFILE = AgentProfile(
    id="reviewer",
    name="Reviewer",
    description="Code review specialist for analyzing code quality, security, and best practices. Best for PR reviews, security audits, and quality checks.",
    default_temperature=0.3,
    default_budget=None,
    required_skills=[
        "code_review",
        "security_analysis",
        "linting",
    ],
    required_tools=[
        "read",
        "grep",
    ],
    required_providers=[],
    capabilities=[
        "Analyze code quality",
        "Identify security issues",
        "Check for best practices",
        "Suggest improvements",
        "Review pull requests",
        "Generate review reports",
    ],
    color="green",
    category="quality",
    tags=["review", "security", "quality"],
)

PLANNER_PROFILE = AgentProfile(
    id="planner",
    name="Planner",
    description="Strategic planning agent for breaking down complex tasks into steps. Best for architecture design, migration planning, and task decomposition.",
    default_temperature=0.5,
    default_budget=None,
    required_skills=[
        "planning",
        "task_breakdown",
    ],
    required_tools=[
        "read",
        "grep",
        "glob",
    ],
    required_providers=[],
    capabilities=[
        "Break down complex tasks",
        "Create implementation plans",
        "Design system architecture",
        "Plan migrations",
        "Define task dependencies",
        "Generate project roadmaps",
    ],
    color="purple",
    category="planning",
    tags=["planning", "architecture", "strategy"],
)

# All default profiles
DEFAULT_PROFILES = [
    CODER_PROFILE,
    REVIEWER_PROFILE,
    PLANNER_PROFILE,
]


def get_default_profiles() -> List[AgentProfile]:
    """Get all default agent profiles"""
    return DEFAULT_PROFILES.copy()


def get_profile_by_id(profile_id: str) -> Optional[AgentProfile]:
    """Get an agent profile by ID

    Args:
        profile_id: Profile ID to look up

    Returns:
        AgentProfile if found, None otherwise
    """
    for profile in DEFAULT_PROFILES:
        if profile.id == profile_id:
            return profile
    return None


def check_prerequisites(
    profile: AgentProfile,
    available_skills: List[str],
    available_tools: List[str],
    available_providers: List[str]
) -> Dict[str, Any]:
    """Check prerequisites for an agent profile

    Args:
        profile: Agent profile to check
        available_skills: List of enabled skill IDs
        available_tools: List of available tool IDs
        available_providers: List of configured provider IDs

    Returns:
        Dict with:
        - satisfied: bool
        - missing: List[Prerequisite]
        - warnings: List[str]
    """
    missing = profile.get_missing_prerequisites(
        available_skills,
        available_tools,
        available_providers
    )

    warnings = []

    # Warn about optional skills/tools not available
    if not required_tools_available(profile.required_tools, available_tools):
        warnings.append("Some required tools may not be available")

    if not required_skills_available(profile.required_skills, available_skills):
        warnings.append("Some required skills may not be enabled")

    return {
        "satisfied": len(missing) == 0,
        "missing": missing,
        "warnings": warnings,
    }


def required_tools_available(required: List[str], available: List[str]) -> bool:
    """Check if required tools are available"""
    return all(tool_id in available for tool_id in required)


def required_skills_available(required: List[str], available: List[str]) -> bool:
    """Check if required skills are available"""
    return all(skill_id in available for skill_id in required)
