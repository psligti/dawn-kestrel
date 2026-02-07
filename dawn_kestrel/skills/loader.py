"""OpenCode Python - Skills system"""
from __future__ import annotations
from typing import Optional, List, Iterable, Tuple, Any
from pathlib import Path
import logging
import importlib

frontmatter: Any = None
try:
    frontmatter = importlib.import_module("frontmatter")
except ImportError:
    logging.warning("python-frontmatter package not installed. Frontmatter support disabled.")


logger = logging.getLogger(__name__)


class Skill:
    """Skill definition from SKILL.md files"""

    name: str
    description: str
    location: Path
    content: str

    def __init__(self, name: str, description: str, location: Path, content: str):
        self.name = name
        self.description = description
        self.location = location
        self.content = content


class SkillLoader:
    """Loader for skills from .opencode/skill/ and .claude/skills/ directories"""

    SKILL_SOURCES: Tuple[Tuple[str, str], ...] = (
        (".opencode", "skill"),
        (".claude", "skills"),
    )

    def __init__(self, base_dir: Path):
        """Initialize skill loader

        Args:
            base_dir: Base directory for skill discovery
        """
        self.base_dir = Path(base_dir)
        self._skills_cache: Optional[List[Skill]] = None

    def clear_cache(self) -> None:
        """Clear cached skills and force reload on next access."""
        self._skills_cache = None

    def _iter_skill_files(self) -> Iterable[Path]:
        """Yield all discovered SKILL.md files from configured sources."""
        for parent, child in self.SKILL_SOURCES:
            skill_dir = self.base_dir / parent / child
            if not skill_dir.exists():
                continue
            yield from skill_dir.rglob("*/SKILL.md")

    def discover_skills(self) -> List[Skill]:
        """Discover all available skills

        Returns:
            List of skills found in standard locations
        """
        if self._skills_cache is not None:
            return list(self._skills_cache)

        skills: List[Skill] = []
        for skill_file in self._iter_skill_files():
            try:
                skill = self._load_skill_file(skill_file)
                if skill:
                    skills.append(skill)
            except Exception as e:
                logger.error(f"Failed to load skill {skill_file}: {e}")

        self._skills_cache = skills
        return list(skills)

    def _load_skill_file(self, file_path: Path) -> Optional[Skill]:
        """Load a single SKILL.md file

        Args:
            file_path: Path to SKILL.md file

        Returns:
            Skill object if successful, None otherwise
        """
        try:
            content = file_path.read_text()
            # Parse frontmatter
            if frontmatter is not None:
                meta, content_body = frontmatter.parse(content)
                meta_dict = dict(meta)
            else:
                meta_dict = {}
                content_body = content

            # Extract name from frontmatter or directory
            name = meta_dict.get("name", file_path.parent.name)
            if not name:
                logger.warning(f"No name in frontmatter for {file_path}")
                name = file_path.parent.name

            description = meta_dict.get("description", "")

            return Skill(
                name=name,
                description=description,
                location=file_path.parent,
                content=content_body.strip(),
            )
        except Exception as e:
            logger.error(f"Error loading skill {file_path}: {e}")
            return None

    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """Get a skill by name

        Args:
            name: Name of the skill to find

        Returns:
            Skill object if found, None otherwise
        """
        skills = self.discover_skills()
        for skill in skills:
            if skill.name.lower() == name.lower():
                return skill
        return None

    def list_skills(self) -> List[str]:
        """List all available skill names"""
        skills = self.discover_skills()
        return [skill.name for skill in skills]


# Global skill loader instance
loader = SkillLoader(Path.cwd())
