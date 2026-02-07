"""
SkillInjector - Inject skills into agent prompts

Merges agent base prompt with selected skills into a single system instruction
string with stable formatting and optional character budget for truncation.
"""
from __future__ import annotations

from typing import List, Optional
from pathlib import Path

from dawn_kestrel.skills.loader import Skill, SkillLoader


class SkillInjector:
    """Inject skills into agent prompts with stable formatting."""

    def __init__(
        self,
        base_dir: Path,
        max_char_budget: Optional[int] = None,
    ):
        """
        Initialize skill injector.

        Args:
            base_dir: Base directory for skill discovery
            max_char_budget: Optional maximum total characters for injected content.
                           If specified, skills will be truncated to fit this budget.
        """
        self.loader = SkillLoader(base_dir)
        self.max_char_budget = max_char_budget

    def build_agent_prompt(
        self,
        agent_prompt: str,
        skill_names: List[str],
        default_prompt: str = "You are a helpful assistant.",
    ) -> str:
        """
        Build agent prompt with injected skills.

        Args:
            agent_prompt: Base prompt for the agent
            skill_names: List of skill names to inject
            default_prompt: Default prompt if agent_prompt is empty

        Returns:
            System instruction string with skills injected before base prompt
        """
        skills = []
        for name in skill_names:
            skill = self.loader.get_skill_by_name(name)
            if skill:
                skills.append(skill)

        if not skills:
            return agent_prompt or default_prompt

        skills_section = self._build_skills_section(skills)

        combined = f"{skills_section}\n\n{agent_prompt or default_prompt}"

        if self.max_char_budget and len(combined) > self.max_char_budget:
            combined = self._truncate_content(combined, self.max_char_budget)

        return combined

    def _build_skills_section(self, skills: List[Skill]) -> str:
        """
        Build formatted skills section.

        Format:
        You have access to the following skills:
        - skill-name: description
          content: [skill content]

        Args:
            skills: List of skills to format

        Returns:
            Formatted skills section string
        """
        lines = ["You have access to the following skills:"]
        lines.append("")

        for skill in skills:
            lines.append(f"- {skill.name}: {skill.description}")
            lines.append(f"  content: {skill.content}")

        return "\n".join(lines)

    def _truncate_content(
        self,
        content: str,
        max_chars: int,
        suffix: str = "...",
    ) -> str:
        """
        Truncate content to max characters with suffix.

        Args:
            content: Content to truncate
            max_chars: Maximum number of characters
            suffix: Truncation suffix

        Returns:
            Truncated content
        """
        if len(content) <= max_chars:
            return content

        # Truncate to max_chars - suffix length
        max_without_suffix = max_chars - len(suffix)
        if max_without_suffix <= 0:
            return suffix

        return content[:max_without_suffix] + suffix
