"""Policy engine implementation for agent decision-making.

This module provides the core policy engine components that evaluate
and validate agent proposals before execution. The policy engine acts
as a gatekeeper, ensuring agent actions comply with constraints and
behavioral boundaries.

Key components:
- PolicyEngine: Protocol defining the policy evaluation interface
- DefaultPolicyEngine: Minimal reference implementation
- ProposalRejected: Exception for rejected proposals with feedback
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dawn_kestrel.policy.contracts import PolicyInput, StepProposal


class ProposalRejected(Exception):
    """Exception raised when a proposal is rejected by the policy engine.

    Attributes:
        reason: Human-readable explanation of why the proposal was rejected
        feedback: Structured feedback about what needs to change
        retry_allowed: Whether the agent can retry with a modified proposal

    Example:
        >>> raise ProposalRejected(
        ...     reason="Cannot edit files outside workspace",
        ...     feedback={"file_pattern": "Must match 'src/**/*.py'"},
        ...     retry_allowed=True
        ... )
    """

    def __init__(
        self,
        reason: str,
        feedback: dict[str, Any] | None = None,
        retry_allowed: bool = True,
    ) -> None:
        """Initialize the rejection exception.

        Args:
            reason: Human-readable explanation for rejection
            feedback: Optional structured feedback dictionary
            retry_allowed: Whether retry is allowed (default: True)
        """
        self.reason = reason
        self.feedback = feedback if feedback is not None else {}
        self.retry_allowed = retry_allowed
        super().__init__(reason)


@runtime_checkable
class PolicyEngine(Protocol):
    """Protocol defining the policy evaluation interface.

    Policy engines evaluate agent proposals and return approved step
    proposals or raise ProposalRejected if the proposal violates
    constraints or policies.

    Implementations can:
    - Approve proposals as-is
    - Modify proposals to comply with constraints
    - Reject proposals with structured feedback
    """

    def propose(self, input: PolicyInput) -> StepProposal:
        """Evaluate a policy input and return an approved step proposal.

        Args:
            input: Current runtime state including goals, todos, constraints

        Returns:
            StepProposal: An approved proposal for the next action

        Raises:
            ProposalRejected: If the proposal violates policies or constraints

        Example:
            >>> engine = DefaultPolicyEngine()
            >>> input_data = PolicyInput(goal="Fix the bug")
            >>> proposal = engine.propose(input_data)
            >>> proposal.intent
            'No action proposed'
        """
        ...


class DefaultPolicyEngine:
    """Minimal reference implementation of the policy engine.

    This implementation returns a minimal valid StepProposal without
    any actions. It serves as a baseline that can be extended for
    more sophisticated policy evaluation.

    This engine:
    - Never rejects proposals
    - Returns minimal valid proposals
    - Does not enforce constraints
    """

    def propose(self, input: PolicyInput) -> StepProposal:
        """Return a minimal valid step proposal.

        This implementation always approves and returns a minimal
        proposal with no actions. Override this method to implement
        custom policy logic.

        Args:
            input: Current runtime state (not used in default implementation)

        Returns:
            StepProposal: Minimal valid proposal with no actions
        """
        return StepProposal(
            intent="No action proposed",
            target_todo_ids=[],
            requested_context=[],
            actions=[],
            completion_claims=[],
        )


__all__ = [
    "PolicyEngine",
    "DefaultPolicyEngine",
    "ProposalRejected",
]
