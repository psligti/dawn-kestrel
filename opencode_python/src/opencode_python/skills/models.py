"""Skill models - Pydantic models for skills and their session state"""
from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime
import pydantic as pd


class Skill(pd.BaseModel):
    """Skill definition with contract details"""

    id: str
    """Unique skill identifier (e.g., 'planning', 'refactor')"""

    name: str
    """Human-readable skill name"""

    description: str
    """Brief description of what the skill does"""

    prompt_template: str
    """Prompt template with variable placeholders"""

    output_schema: Dict[str, Any]
    """Pydantic model schema for structured output"""

    is_enabled_by_default: bool = True
    """Whether the skill is enabled by default for new sessions"""

    category: Optional[str] = None
    """Skill category (e.g., 'code', 'testing', 'docs')"""

    model_config = pd.ConfigDict(extra="forbid")


class SkillState(pd.BaseModel):
    """Session-scoped skill state"""

    session_id: str
    """ID of the session this state belongs to"""

    skill_id: str
    """ID of the skill this state is for"""

    is_enabled: bool
    """Whether the skill is currently enabled"""

    is_blocked: bool = False
    """Whether the skill is blocked (e.g., due to safety)"""

    block_reason: Optional[str] = None
    """Reason why the skill is blocked, if applicable"""

    last_used: Optional[float] = None
    """Timestamp when skill was last used"""

    use_count: int = 0
    """Number of times this skill has been used in the session"""

    model_config = pd.ConfigDict(extra="forbid")

    def mark_used(self) -> None:
        """Mark skill as used"""
        self.last_used = datetime.now().timestamp()
        self.use_count += 1
