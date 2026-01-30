"""Skill registry - manages skill registration and session-scoped state"""
from __future__ import annotations

from typing import Dict, List, Optional
import logging

from opencode_python.skills.models import Skill, SkillState
from opencode_python.core.event_bus import bus


logger = logging.getLogger(__name__)


class SkillRegistry:
    """Registry for managing skills and their session state"""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._session_states: Dict[str, Dict[str, SkillState]] = {}

    def register_skill(self, skill: Skill) -> None:
        """Register a new skill

        Args:
            skill: Skill to register
        """
        self._skills[skill.id] = skill
        logger.debug(f"Registered skill: {skill.id}")

    def unregister_skill(self, skill_id: str) -> None:
        """Unregister a skill

        Args:
            skill_id: ID of skill to unregister
        """
        if skill_id in self._skills:
            del self._skills[skill_id]
            logger.debug(f"Unregistered skill: {skill_id}")

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID

        Args:
            skill_id: ID of skill to retrieve

        Returns:
            Skill if found, None otherwise
        """
        return self._skills.get(skill_id)

    def list_skills(self) -> List[Skill]:
        """List all registered skills

        Returns:
            List of all registered skills
        """
        return list(self._skills.values())

    def get_enabled_skills(self, session_id: str) -> List[Skill]:
        """Get all enabled skills for a session

        Args:
            session_id: ID of the session

        Returns:
            List of enabled skills
        """
        enabled = []
        for skill_id, state in self._session_states.get(session_id, {}).items():
            if state.is_enabled and not state.is_blocked:
                skill = self._skills.get(skill_id)
                if skill:
                    enabled.append(skill)
        return enabled

    def is_skill_enabled(self, session_id: str, skill_id: str) -> bool:
        """Check if a skill is enabled for a session

        Args:
            session_id: ID of the session
            skill_id: ID of the skill

        Returns:
            True if skill is enabled, False otherwise
        """
        state = self._session_states.get(session_id, {}).get(skill_id)
        return state is not None and state.is_enabled and not state.is_blocked

    def is_skill_blocked(self, session_id: str, skill_id: str) -> bool:
        """Check if a skill is blocked for a session

        Args:
            session_id: ID of the session
            skill_id: ID of the skill

        Returns:
            True if skill is blocked, False otherwise
        """
        state = self._session_states.get(session_id, {}).get(skill_id)
        return state is not None and state.is_blocked

    def enable_skill(self, session_id: str, skill_id: str) -> bool:
        """Enable a skill for a session

        Args:
            session_id: ID of the session
            skill_id: ID of the skill to enable

        Returns:
            True if successful, False if skill not found
        """
        if skill_id not in self._skills:
            logger.warning(f"Cannot enable unknown skill: {skill_id}")
            return False

        if session_id not in self._session_states:
            self._session_states[session_id] = {}

        state = self._session_states[session_id].get(skill_id)
        if state:
            state.is_enabled = True
            state.is_blocked = False
            state.block_reason = None
        else:
            state = SkillState(
                session_id=session_id,
                skill_id=skill_id,
                is_enabled=True,
                is_blocked=False,
            )
            self._session_states[session_id][skill_id] = state

        logger.info(f"Enabled skill {skill_id} for session {session_id}")
        self._emit_event("skill:enable", session_id, skill_id)
        return True

    def disable_skill(self, session_id: str, skill_id: str) -> bool:
        """Disable a skill for a session

        Args:
            session_id: ID of the session
            skill_id: ID of the skill to disable

        Returns:
            True if successful, False if skill not found
        """
        if skill_id not in self._skills:
            logger.warning(f"Cannot disable unknown skill: {skill_id}")
            return False

        if session_id not in self._session_states:
            self._session_states[session_id] = {}

        state = self._session_states[session_id].get(skill_id)
        if state:
            state.is_enabled = False
        else:
            state = SkillState(
                session_id=session_id,
                skill_id=skill_id,
                is_enabled=False,
                is_blocked=False,
            )
            self._session_states[session_id][skill_id] = state

        logger.info(f"Disabled skill {skill_id} for session {session_id}")
        self._emit_event("skill:disable", session_id, skill_id)
        return True

    def block_skill(self, session_id: str, skill_id: str, reason: str) -> bool:
        """Block a skill for a session with a reason

        Args:
            session_id: ID of the session
            skill_id: ID of the skill to block
            reason: Reason for blocking

        Returns:
            True if successful, False if skill not found
        """
        if skill_id not in self._skills:
            logger.warning(f"Cannot block unknown skill: {skill_id}")
            return False

        if session_id not in self._session_states:
            self._session_states[session_id] = {}

        state = self._session_states[session_id].get(skill_id)
        if state:
            state.is_blocked = True
            state.block_reason = reason
        else:
            state = SkillState(
                session_id=session_id,
                skill_id=skill_id,
                is_enabled=False,
                is_blocked=True,
                block_reason=reason,
            )
            self._session_states[session_id][skill_id] = state

        logger.warning(f"Blocked skill {skill_id} for session {session_id}: {reason}")
        self._emit_event("skill:block", session_id, skill_id, reason=reason)
        return True

    def unblock_skill(self, session_id: str, skill_id: str) -> bool:
        """Unblock a skill for a session

        Args:
            session_id: ID of the session
            skill_id: ID of the skill to unblock

        Returns:
            True if successful, False if skill not found
        """
        if skill_id not in self._skills:
            logger.warning(f"Cannot unblock unknown skill: {skill_id}")
            return False

        state = self._session_states.get(session_id, {}).get(skill_id)
        if state:
            state.is_blocked = False
            state.block_reason = None
            logger.info(f"Unblocked skill {skill_id} for session {session_id}")
            return True

        return False

    def mark_skill_used(self, session_id: str, skill_id: str) -> None:
        """Mark a skill as used in a session

        Args:
            session_id: ID of the session
            skill_id: ID of the skill
        """
        state = self._session_states.get(session_id, {}).get(skill_id)
        if state:
            state.mark_used()

    def get_skill_state(self, session_id: str, skill_id: str) -> Optional[SkillState]:
        """Get the state of a skill for a session

        Args:
            session_id: ID of the session
            skill_id: ID of the skill

        Returns:
            SkillState if found, None otherwise
        """
        return self._session_states.get(session_id, {}).get(skill_id)

    def initialize_session(self, session_id: str) -> None:
        """Initialize a new session with default skill states

        Args:
            session_id: ID of the session to initialize
        """
        self._session_states[session_id] = {}

        for skill_id, skill in self._skills.items():
            if skill.is_enabled_by_default:
                state = SkillState(
                    session_id=session_id,
                    skill_id=skill_id,
                    is_enabled=True,
                    is_blocked=False,
                )
                self._session_states[session_id][skill_id] = state

        logger.debug(f"Initialized session {session_id} with {len(self._session_states[session_id])} skills")

    def cleanup_session(self, session_id: str) -> None:
        """Clean up session state

        Args:
            session_id: ID of the session to clean up
        """
        if session_id in self._session_states:
            del self._session_states[session_id]
            logger.debug(f"Cleaned up session {session_id}")

    def _emit_event(self, event_name: str, session_id: str, skill_id: str, **kwargs: object) -> None:
        """Emit a skill event

        Args:
            event_name: Name of the event
            session_id: ID of the session
            skill_id: ID of the skill
            **kwargs: Additional event data
        """
        import asyncio

        data = {"session_id": session_id, "skill_id": skill_id, **kwargs}

        try:
            asyncio.get_running_loop()
            asyncio.create_task(bus.publish(event_name, data))
        except RuntimeError:
            pass


# Global skill registry instance
registry = SkillRegistry()


def register_default_skills() -> None:
    """Register default skills (planning, refactor, tests, docs)"""
    from opencode_python.skills.contracts import (
        PLANNING_CONTRACT,
        REFACTOR_CONTRACT,
        TESTS_CONTRACT,
        DOCS_CONTRACT,
    )

    planning = Skill(
        id="planning",
        name="Planning",
        description="Create detailed task plans with dependencies and priorities",
        prompt_template=PLANNING_CONTRACT.prompt_template,
        output_schema=PLANNING_CONTRACT.output_schema,
        is_enabled_by_default=True,
        category="code",
    )

    refactor = Skill(
        id="refactor",
        name="Refactor",
        description="Identify and implement code quality improvements",
        prompt_template=REFACTOR_CONTRACT.prompt_template,
        output_schema=REFACTOR_CONTRACT.output_schema,
        is_enabled_by_default=True,
        category="code",
    )

    tests = Skill(
        id="tests",
        name="Test Generation",
        description="Generate comprehensive tests with coverage analysis",
        prompt_template=TESTS_CONTRACT.prompt_template,
        output_schema=TESTS_CONTRACT.output_schema,
        is_enabled_by_default=True,
        category="testing",
    )

    docs = Skill(
        id="docs",
        name="Documentation",
        description="Create and update code documentation",
        prompt_template=DOCS_CONTRACT.prompt_template,
        output_schema=DOCS_CONTRACT.output_schema,
        is_enabled_by_default=True,
        category="docs",
    )

    registry.register_skill(planning)
    registry.register_skill(refactor)
    registry.register_skill(tests)
    registry.register_skill(docs)
