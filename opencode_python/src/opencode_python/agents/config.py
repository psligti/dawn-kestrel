"""OpenCode Python - Agent configuration per session"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import pydantic as pd


__all__ = [
    "AuditEntry",
    "AgentConfig",
]


class AuditEntry(pd.BaseModel):
    """Single audit trail entry for configuration changes"""

    timestamp: float
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    action_source: Literal["user", "system", "profile_default"]
    reason: Optional[str] = None


class AgentConfig(pd.BaseModel):
    """Per-session agent configuration

    Overrides agent profile defaults for a specific session.
    Configuration changes are tracked in the audit trail.
    """

    # Session identification
    session_id: str
    agent_profile_id: str

    # Agent settings (can override profile defaults)
    model: Optional[str] = None
    temperature: Optional[float] = None
    budget: Optional[int] = None

    # Audit trail
    audit_trail: List[AuditEntry] = pd.Field(default_factory=list)

    class Config:
        extra = "forbid"

    def update_field(
        self,
        field: str,
        new_value: Any,
        action_source: Literal["user", "system", "profile_default"] = "user",
        reason: Optional[str] = None
    ) -> None:
        """Update a configuration field and record in audit trail

        Args:
            field: Field name to update (model, temperature, budget)
            new_value: New value for the field
            action_source: Who made the change (user, system, profile_default)
            reason: Optional reason for the change
        """
        old_value = getattr(self, field, None)

        if old_value != new_value:
            setattr(self, field, new_value)

            self.audit_trail.append(AuditEntry(
                timestamp=datetime.now().timestamp(),
                field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
                action_source=action_source,
                reason=reason
            ))

    def get_model(self, profile_default: Optional[str] = None) -> str:
        """Get model to use, falling back to profile default

        Args:
            profile_default: Default model from agent profile

        Returns:
            Model string to use
        """
        return self.model or profile_default or "claude-3-5-sonnet-20241022"

    def get_temperature(self, profile_default: Optional[float] = None) -> float:
        """Get temperature to use, falling back to profile default

        Args:
            profile_default: Default temperature from agent profile

        Returns:
            Temperature value to use
        """
        return self.temperature if self.temperature is not None else profile_default or 0.7

    def get_budget(self, profile_default: Optional[int] = None) -> Optional[int]:
        """Get budget to use, falling back to profile default

        Args:
            profile_default: Default budget from agent profile

        Returns:
            Budget value to use, or None if not set
        """
        return self.budget if self.budget is not None else profile_default

    def get_audit_summary(self) -> List[Dict[str, Any]]:
        """Get a human-readable summary of audit trail

        Returns:
            List of dict entries with readable timestamp and change info
        """
        summary = []
        for entry in self.audit_trail:
            summary.append({
                "timestamp": datetime.fromtimestamp(entry.timestamp).isoformat(),
                "field": entry.field,
                "old_value": entry.old_value,
                "new_value": entry.new_value,
                "action_source": entry.action_source,
                "reason": entry.reason,
            })
        return summary

    @classmethod
    def from_profile(
        cls,
        session_id: str,
        agent_profile_id: str,
        profile_model: Optional[str] = None,
        profile_temperature: Optional[float] = None,
        profile_budget: Optional[int] = None
    ) -> "AgentConfig":
        """Create AgentConfig from profile defaults

        Args:
            session_id: Session ID
            agent_profile_id: Agent profile ID
            profile_model: Default model from profile
            profile_temperature: Default temperature from profile
            profile_budget: Default budget from profile

        Returns:
            New AgentConfig with profile defaults
        """
        config = cls(
            session_id=session_id,
            agent_profile_id=agent_profile_id,
            model=profile_model,
            temperature=profile_temperature,
            budget=profile_budget,
        )

        # Record initial values as from profile
        if profile_model:
            config.audit_trail.append(AuditEntry(
                timestamp=datetime.now().timestamp(),
                field="model",
                old_value=None,
                new_value=profile_model,
                action_source="profile_default",
                reason="Initial value from profile"
            ))

        if profile_temperature:
            config.audit_trail.append(AuditEntry(
                timestamp=datetime.now().timestamp(),
                field="temperature",
                old_value=None,
                new_value=str(profile_temperature),
                action_source="profile_default",
                reason="Initial value from profile"
            ))

        if profile_budget:
            config.audit_trail.append(AuditEntry(
                timestamp=datetime.now().timestamp(),
                field="budget",
                old_value=None,
                new_value=str(profile_budget),
                action_source="profile_default",
                reason="Initial value from profile"
            ))

        return config
