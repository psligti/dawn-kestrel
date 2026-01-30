"""Skill blocking interceptor - intercepts and blocks skill execution"""
from __future__ import annotations

from typing import Callable, Optional, Dict, Any
import logging

from opencode_python.skills.registry import registry
from opencode_python.core.event_bus import bus, Events


logger = logging.getLogger(__name__)


class SkillExecutionDenied(Exception):
    """Raised when skill execution is denied"""

    def __init__(self, skill_id: str, reason: str):
        self.skill_id = skill_id
        self.reason = reason
        super().__init__(f"Skill '{skill_id}' execution denied: {reason}")


class SkillBlockingInterceptor:
    """Intercepts skill execution attempts and enforces blocking rules"""

    def __init__(self):
        self._interceptors: Dict[str, Callable[[str, str, Dict[str, Any]], bool]] = {}
        self._registry = registry

    def register_interceptor(
        self,
        skill_id: str,
        interceptor: Callable[[str, str, Dict[str, Any]], bool],
    ) -> None:
        """Register a custom interceptor for a skill

        Args:
            skill_id: ID of the skill to intercept
            interceptor: Function that takes (session_id, skill_id, context) and returns True to allow, False to deny
        """
        self._interceptors[skill_id] = interceptor
        logger.debug(f"Registered interceptor for skill: {skill_id}")

    def unregister_interceptor(self, skill_id: str) -> None:
        """Unregister a custom interceptor

        Args:
            skill_id: ID of the skill
        """
        if skill_id in self._interceptors:
            del self._interceptors[skill_id]
            logger.debug(f"Unregistered interceptor for skill: {skill_id}")

    async def check_execution_allowed(
        self,
        session_id: str,
        skill_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if skill execution is allowed

        Args:
            session_id: ID of the session
            skill_id: ID of the skill
            context: Optional execution context

        Returns:
            True if allowed, False otherwise

        Raises:
            SkillExecutionDenied: If execution is blocked
        """
        context = context or {}

        # Check if skill exists
        skill = registry.get_skill(skill_id)
        if not skill:
            error_msg = f"Skill '{skill_id}' not found in registry"
            logger.warning(error_msg)
            await self._emit_block_event(session_id, skill_id, error_msg)
            raise SkillExecutionDenied(skill_id, error_msg)

        # Check if skill is blocked
        if registry.is_skill_blocked(session_id, skill_id):
            state = registry.get_skill_state(session_id, skill_id)
            block_reason = state.block_reason if state else "Skill is blocked"
            error_msg = f"Skill '{skill_id}' is blocked: {block_reason}"
            logger.warning(error_msg)
            await self._emit_block_event(session_id, skill_id, error_msg)
            raise SkillExecutionDenied(skill_id, error_msg)

        # Check if skill is enabled
        if not registry.is_skill_enabled(session_id, skill_id):
            state = registry.get_skill_state(session_id, skill_id)
            error_msg = f"Skill '{skill_id}' is disabled"
            if state and state.block_reason:
                error_msg += f": {state.block_reason}"
            logger.warning(error_msg)
            await self._emit_block_event(session_id, skill_id, error_msg)
            raise SkillExecutionDenied(skill_id, error_msg)

        # Run custom interceptors
        interceptor = self._interceptors.get(skill_id)
        if interceptor:
            try:
                allowed = interceptor(session_id, skill_id, context)
                if not allowed:
                    error_msg = f"Custom interceptor denied execution of skill '{skill_id}'"
                    logger.warning(error_msg)
                    await self._emit_block_event(session_id, skill_id, error_msg)
                    raise SkillExecutionDenied(skill_id, error_msg)
            except Exception as e:
                logger.error(f"Error in custom interceptor for skill '{skill_id}': {e}")
                raise SkillExecutionDenied(skill_id, f"Interceptor error: {e}")

        # Mark skill as used
        registry.mark_skill_used(session_id, skill_id)

        # Allow execution
        await self._emit_execute_event(session_id, skill_id)
        return True

    async def _emit_block_event(
        self,
        session_id: str,
        skill_id: str,
        reason: str,
    ) -> None:
        """Emit a skill block event

        Args:
            session_id: ID of the session
            skill_id: ID of the skill
            reason: Reason for blocking
        """
        data = {
            "session_id": session_id,
            "skill_id": skill_id,
            "reason": reason,
        }
        await bus.publish("skill:block", data)

    async def _emit_execute_event(
        self,
        session_id: str,
        skill_id: str,
    ) -> None:
        """Emit a skill execution event

        Args:
            session_id: ID of the session
            skill_id: ID of the skill
        """
        data = {
            "session_id": session_id,
            "skill_id": skill_id,
        }
        await bus.publish("skill:execute", data)


# Global skill blocking interceptor instance
interceptor = SkillBlockingInterceptor()


def setup_event_listeners() -> None:
    """Setup event listeners for skill-related events"""

    async def on_session_created(event) -> None:
        """Handle session.created event - initialize skills"""
        session_id = event.data.get("session_id")
        if session_id:
            registry.initialize_session(session_id)

    async def on_agent_execute(event) -> None:
        """Handle agent.execute event - check skill execution"""
        session_id = event.data.get("session_id")
        skill_id = event.data.get("skill_id")
        context = event.data.get("context")

        if session_id and skill_id:
            try:
                await interceptor.check_execution_allowed(session_id, skill_id, context)
            except SkillExecutionDenied as e:
                logger.warning(f"Agent skill execution denied: {e}")
                raise

    # Subscribe to events
    import asyncio

    asyncio.create_task(bus.subscribe(Events.SESSION_CREATED, on_session_created))
    asyncio.create_task(bus.subscribe("agent:execute", on_agent_execute))

    logger.debug("Skill event listeners setup complete")
