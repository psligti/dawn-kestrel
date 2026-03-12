"""Policy-driven delegation protocols and types.

This module provides the core protocols for replacing FSM-driven delegation
with configurable policy objects that decide:
- When to create subtasks
- Which agents to delegate to
- When to stop delegating
- How to aggregate results

The key innovation is replacing hardcoded FSM state transitions with
policy-driven decisions that can be configured at runtime.

Usage:
    from dawn_kestrel.policy.delegation import (
        DelegationPolicy,
        DelegationContext,
        DelegationOutput,
        DelegationDecision,
    )

    class MyDelegationPolicy(DelegationPolicy):
        def evaluate(self, context: DelegationContext) -> DelegationOutput:
            if context.task_complexity > 0.7:
                return DelegationOutput(
                    decision=DelegationDecision.DELEGATE,
                    subtasks=[
                        SubtaskProposal(agent="specialist", prompt="Analyze"),
                    ],
                )
            return DelegationOutput(decision=DelegationDecision.DONE)
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import pydantic as pd

if TYPE_CHECKING:
    from dawn_kestrel.delegation.types import DelegationBudget


class DelegationDecision(str, Enum):
    """What to do next in delegation.

    CONTINUE: Continue with current agent iteration
    DELEGATE: Create and spawn subtasks
    SYNTHESIZE: Aggregate results from subagents
    DONE: Stop delegation, return results
    """

    CONTINUE = "continue"
    DELEGATE = "delegate"
    SYNTHESIZE = "synthesize"
    DONE = "done"


class SubtaskProposal(pd.BaseModel):
    """A proposed subtask to delegate to a specialized agent.

    Attributes:
        agent: Name of the agent to delegate to
        prompt: The task prompt for the agent
        domain: Domain classification for this subtask
        priority: Priority level (1 = highest)
        metadata: Additional context for the subtask
    """

    agent: str
    prompt: str
    domain: str = "general"
    priority: int = 1
    metadata: dict[str, Any] = pd.Field(default_factory=dict)

    model_config = pd.ConfigDict(extra="forbid", frozen=True)


class DelegationContext(pd.BaseModel):
    """Context for delegation policy decisions.

    Contains all the information a policy needs to decide:
    - Whether to delegate
    - Which agents to use
    - When to stop

    Attributes:
        current_agent: Name of the currently executing agent
        current_depth: Depth in the delegation tree
        iteration_count: Number of iterations completed
        accumulated_results: Results collected so far
        accumulated_evidence: Evidence gathered so far
        findings_count: Total number of findings
        findings_per_iteration: Findings count per iteration
        tokens_used: Total tokens consumed
        cost_usd: Total cost in USD
        elapsed_seconds: Time elapsed since start
        task_complexity: Estimated task complexity (0.0-1.0)
        domains_detected: Detected task domains
        budget: Budget constraints
    """

    # Current state
    current_agent: str
    current_depth: int = 0
    iteration_count: int = 0

    # Results so far
    accumulated_results: list[Any] = pd.Field(default_factory=list)
    accumulated_evidence: list[Any] = pd.Field(default_factory=list)
    findings_count: int = 0
    findings_per_iteration: list[int] = pd.Field(default_factory=list)

    # Budget consumption
    tokens_used: int = 0
    cost_usd: float = 0.0
    elapsed_seconds: float = 0.0

    # Input analysis
    task_complexity: float = 0.5
    domains_detected: list[str] = pd.Field(default_factory=list)

    # Budget limits (passed separately to avoid circular import)
    max_depth: int = 3
    max_iterations: int = 10
    max_cost_usd: float = 1.0
    max_seconds: float = 300.0
    stagnation_threshold: int = 3

    model_config = pd.ConfigDict(extra="forbid")

    @property
    def is_budget_exhausted(self) -> bool:
        """Check if any budget limit has been reached."""
        return (
            self.cost_usd >= self.max_cost_usd
            or self.elapsed_seconds >= self.max_seconds
            or self.current_depth >= self.max_depth
            or self.iteration_count >= self.max_iterations
        )

    @property
    def is_stagnant(self) -> bool:
        """Check if progress has stagnated."""
        if len(self.findings_per_iteration) < self.stagnation_threshold:
            return False
        recent = self.findings_per_iteration[-self.stagnation_threshold :]
        return all(count == 0 for count in recent)

    @property
    def budget_remaining_percent(self) -> float:
        """Calculate remaining budget as percentage."""
        cost_pct = max(0, 1 - (self.cost_usd / self.max_cost_usd))
        time_pct = max(0, 1 - (self.elapsed_seconds / self.max_seconds))
        iter_pct = max(0, 1 - (self.iteration_count / self.max_iterations))
        return min(cost_pct, time_pct, iter_pct)


class DelegationOutput(pd.BaseModel):
    """Output from delegation policy evaluation.

    Attributes:
        decision: What to do next
        rationale: Human-readable explanation
        confidence: Confidence in this decision (0.0-1.0)
        subtasks: Subtasks to create (if DELEGATE)
        continue_with: Agent to continue with (if CONTINUE)
        budget_consumed: Budget consumed in this evaluation
    """

    decision: DelegationDecision
    rationale: str = ""
    confidence: float = 0.8

    # If DELEGATE
    subtasks: list[SubtaskProposal] = pd.Field(default_factory=list)

    # If CONTINUE
    continue_with: str | None = None

    # Budget consumed this decision
    budget_consumed: dict[str, Any] = pd.Field(default_factory=dict)

    model_config = pd.ConfigDict(extra="forbid")


@runtime_checkable
class DelegationPolicy(Protocol):
    """Protocol for policy-driven delegation decisions.

    This replaces FSM-based delegation logic with configurable
    policy objects that decide:
    - When to create subtasks
    - Which agents to delegate to
    - When to stop delegating

    Implementations should be stateless and deterministic:
    same input should produce same output.

    Example:
        class ComplexityBasedPolicy(DelegationPolicy):
            def __init__(self, threshold: float = 0.5):
                self.threshold = threshold

            def evaluate(self, context: DelegationContext) -> DelegationOutput:
                if context.task_complexity >= self.threshold:
                    return DelegationOutput(
                        decision=DelegationDecision.DELEGATE,
                        subtasks=[SubtaskProposal(agent="specialist", prompt="...")],
                    )
                return DelegationOutput(decision=DelegationDecision.DONE)
    """

    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        """Evaluate delegation context and decide next action.

        Args:
            context: Current delegation state and results

        Returns:
            DelegationOutput with decision and optional subtasks
        """
        ...


class CompositeDelegationPolicy:
    """Compose multiple policies with fallback behavior.

    Policies are evaluated in order. The first non-None decision wins.
    This allows building complex delegation behavior from simple policies.

    Example:
        policy = CompositeDelegationPolicy([
            BudgetAwarePolicy(budget),
            StagnationAwarePolicy(threshold=2),
            ComplexityBasedPolicy(threshold=0.5),
            DefaultPolicy(decision=DelegationDecision.DONE),
        ])
    """

    def __init__(self, policies: list[DelegationPolicy]):
        """Initialize with ordered list of policies.

        Args:
            policies: Policies to evaluate in order
        """
        self.policies = policies

    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        """Evaluate policies in order until one returns a decision."""
        for policy in self.policies:
            output = policy.evaluate(context)
            # Non-default decisions take precedence
            if output.decision != DelegationDecision.DONE or output.confidence >= 0.9:
                return output
        # Default: done
        return DelegationOutput(
            decision=DelegationDecision.DONE,
            rationale="All policies exhausted",
            confidence=0.5,
        )


class DefaultDelegationPolicy:
    """Default policy that always returns DONE.

    Useful as a fallback in CompositeDelegationPolicy.
    """

    def __init__(
        self,
        decision: DelegationDecision = DelegationDecision.DONE,
        rationale: str = "Default policy",
    ):
        self.decision = decision
        self.rationale = rationale

    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        return DelegationOutput(
            decision=self.decision,
            rationale=self.rationale,
            confidence=0.5,
        )


__all__ = [
    "DelegationDecision",
    "DelegationContext",
    "DelegationOutput",
    "DelegationPolicy",
    "SubtaskProposal",
    "CompositeDelegationPolicy",
    "DefaultDelegationPolicy",
]
