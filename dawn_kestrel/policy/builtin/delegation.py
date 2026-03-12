"""Built-in delegation policy implementations.

This module provides ready-to-use delegation policies:

1. ComplexityBasedDelegationPolicy - Delegate based on task complexity
2. BudgetAwareDelegationPolicy - Enforce budget constraints
3. StagnationAwarePolicy - Stop when progress stalls
4. DomainBasedDelegationPolicy - Route to agents by domain

These policies can be composed using CompositeDelegationPolicy:

    from dawn_kestrel.policy.delegation import CompositeDelegationPolicy
    from dawn_kestrel.policy.builtin import (
        ComplexityBasedDelegationPolicy,
        BudgetAwareDelegationPolicy,
        StagnationAwarePolicy,
    )

    policy = CompositeDelegationPolicy([
        BudgetAwareDelegationPolicy(budget),
        StagnationAwarePolicy(threshold=2),
        ComplexityBasedDelegationPolicy(threshold=0.5),
    ])

    output = policy.evaluate(context)
"""

from __future__ import annotations

from typing import Any

from dawn_kestrel.policy.delegation import (
    DelegationContext,
    DelegationDecision,
    DelegationOutput,
    DelegationPolicy,
    SubtaskProposal,
)


class ComplexityBasedDelegationPolicy:
    """Delegate based on task complexity analysis.

    This policy analyzes task complexity and creates subtasks when
    complexity exceeds a threshold. Complexity is estimated from:
    - Number of domains detected
    - Scope of accumulated evidence
    - Iteration patterns

    Attributes:
        complexity_threshold: Minimum complexity to trigger delegation (0.0-1.0)
        max_subtasks: Maximum number of subtasks to create
        domain_agents: Mapping from domain to agent name
    """

    def __init__(
        self,
        complexity_threshold: float = 0.5,
        max_subtasks: int = 5,
        domain_agents: dict[str, str] | None = None,
    ):
        """Initialize complexity-based policy.

        Args:
            complexity_threshold: Threshold for delegation (default 0.5)
            max_subtasks: Max subtasks to create per delegation (default 5)
            domain_agents: Map domain names to agent names
        """
        self.complexity_threshold = complexity_threshold
        self.max_subtasks = max_subtasks
        self.domain_agents = domain_agents or {}

    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        """Evaluate whether to delegate based on complexity."""
        # Check stop conditions first
        if context.is_budget_exhausted:
            return DelegationOutput(
                decision=DelegationDecision.DONE,
                rationale="Budget exhausted",
                confidence=1.0,
            )

        # Don't delegate if already at max depth
        if context.current_depth >= context.max_depth - 1:
            return DelegationOutput(
                decision=DelegationDecision.SYNTHESIZE,
                rationale="Approaching max depth, synthesizing",
                confidence=0.9,
            )

        # Check if complexity warrants delegation
        if context.task_complexity >= self.complexity_threshold:
            subtasks = self._create_subtasks(context)
            if subtasks:
                return DelegationOutput(
                    decision=DelegationDecision.DELEGATE,
                    rationale=f"Task complexity {context.task_complexity:.2f} exceeds threshold {self.complexity_threshold:.2f}",
                    confidence=0.8,
                    subtasks=subtasks[: self.max_subtasks],
                )

        # Continue with current agent
        return DelegationOutput(
            decision=DelegationDecision.CONTINUE,
            rationale=f"Task complexity {context.task_complexity:.2f} below threshold",
            confidence=0.7,
            continue_with=context.current_agent,
        )

    def _create_subtasks(self, context: DelegationContext) -> list[SubtaskProposal]:
        """Create subtasks based on detected domains."""
        subtasks = []

        # Create subtasks for each detected domain
        for domain in context.domains_detected[: self.max_subtasks]:
            agent = self.domain_agents.get(domain, f"{domain}_agent")
            subtasks.append(
                SubtaskProposal(
                    agent=agent,
                    prompt=f"Analyze {domain} aspects of the task",
                    domain=domain,
                    priority=1,
                )
            )

        # If no domains detected, create a general subtask
        if not subtasks and context.task_complexity > 0.7:
            subtasks.append(
                SubtaskProposal(
                    agent="specialist",
                    prompt="Perform deep analysis of this complex task",
                    domain="general",
                    priority=1,
                )
            )

        return subtasks


class BudgetAwareDelegationPolicy:
    """Delegate with budget awareness.

    This policy wraps another policy and enforces budget constraints.
    It will stop delegation when budget limits are reached.

    Attributes:
        inner_policy: The policy to wrap
        budget: Budget constraints
    """

    def __init__(self, inner_policy: DelegationPolicy):
        """Initialize budget-aware policy.

        Args:
            inner_policy: Policy to wrap with budget enforcement
        """
        self.inner_policy = inner_policy

    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        """Evaluate with budget constraints."""
        # Hard budget checks
        if context.cost_usd >= context.max_cost_usd:
            return DelegationOutput(
                decision=DelegationDecision.DONE,
                rationale=f"Budget exhausted: cost ${context.cost_usd:.2f} >= ${context.max_cost_usd:.2f}",
                confidence=1.0,
            )

        if context.elapsed_seconds >= context.max_seconds:
            return DelegationOutput(
                decision=DelegationDecision.DONE,
                rationale=f"Budget exhausted: time {context.elapsed_seconds:.1f}s >= {context.max_seconds:.1f}s",
                confidence=1.0,
            )

        if context.current_depth >= context.max_depth:
            return DelegationOutput(
                decision=DelegationDecision.SYNTHESIZE,
                rationale=f"Max depth reached ({context.current_depth}), synthesizing",
                confidence=0.9,
            )

        if context.iteration_count >= context.max_iterations:
            return DelegationOutput(
                decision=DelegationDecision.DONE,
                rationale=f"Max iterations reached ({context.iteration_count})",
                confidence=0.9,
            )

        # Warn on low budget
        budget_pct = context.budget_remaining_percent
        if budget_pct <= 0.2:
            # Pass to inner policy but note low budget
            output = self.inner_policy.evaluate(context)
            if output.decision == DelegationDecision.DELEGATE:
                # Limit subtasks when budget is low
                limited_subtasks = output.subtasks[:1]  # Only one subtask
                return DelegationOutput(
                    decision=DelegationDecision.DELEGATE,
                    rationale=f"Low budget ({budget_pct:.0%} remaining): {output.rationale}",
                    confidence=output.confidence,
                    subtasks=limited_subtasks,
                )
            return output

        # Delegate to inner policy
        return self.inner_policy.evaluate(context)


class StagnationAwarePolicy:
    """Stop when progress stagnates.

    This policy detects when results stop improving and triggers
    early termination to avoid wasted effort.

    Stagnation is detected when:
    - No findings for N consecutive iterations
    - Evidence accumulation plateaus

    Attributes:
        inner_policy: The policy to wrap
        stagnation_threshold: Number of iterations with no findings before stopping
    """

    def __init__(
        self,
        inner_policy: DelegationPolicy,
        stagnation_threshold: int = 2,
    ):
        """Initialize stagnation-aware policy.

        Args:
            inner_policy: Policy to wrap
            stagnation_threshold: Iterations with no findings before stop
        """
        self.inner_policy = inner_policy
        self.stagnation_threshold = stagnation_threshold

    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        """Evaluate with stagnation detection."""
        # Check for stagnation
        if len(context.findings_per_iteration) >= self.stagnation_threshold:
            recent = context.findings_per_iteration[-self.stagnation_threshold :]

            # Stagnation type 1: Zero findings for multiple iterations
            if all(count == 0 for count in recent):
                return DelegationOutput(
                    decision=DelegationDecision.DONE,
                    rationale=f"Stagnation: no findings for {self.stagnation_threshold} iterations",
                    confidence=0.85,
                )

            # Stagnation type 2: After 3+ iterations with findings, diminishing returns
            if len(context.findings_per_iteration) >= 3 and sum(recent) > 0:
                return DelegationOutput(
                    decision=DelegationDecision.DONE,
                    rationale="Stagnation: 3+ iterations with findings, forcing completion",
                    confidence=0.8,
                )

        # No stagnation detected, delegate to inner policy
        return self.inner_policy.evaluate(context)


class DomainBasedDelegationPolicy:
    """Route subtasks to agents based on domain.

    This policy analyzes the task and routes delegation to specialized
    agents based on detected domains.

    Attributes:
        domain_agents: Mapping from domain name to agent name
        default_agent: Agent to use when no domain matches
        priority_order: Order in which to prioritize domains
    """

    def __init__(
        self,
        domain_agents: dict[str, str],
        default_agent: str = "generalist",
        priority_order: list[str] | None = None,
    ):
        """Initialize domain-based policy.

        Args:
            domain_agents: Map domain names to agent names
            default_agent: Fallback agent when no domain matches
            priority_order: Order to prioritize domains (None = any order)
        """
        self.domain_agents = domain_agents
        self.default_agent = default_agent
        self.priority_order = priority_order or list(domain_agents.keys())

    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        """Evaluate and route based on domains."""
        # Check stop conditions
        if context.is_budget_exhausted:
            return DelegationOutput(
                decision=DelegationDecision.DONE,
                rationale="Budget exhausted",
                confidence=1.0,
            )

        # Don't delegate if no domains detected
        if not context.domains_detected:
            if context.iteration_count >= 2:
                return DelegationOutput(
                    decision=DelegationDecision.DONE,
                    rationale="No domains detected after multiple iterations",
                    confidence=0.7,
                )
            return DelegationOutput(
                decision=DelegationDecision.CONTINUE,
                rationale="No domains detected, continuing analysis",
                confidence=0.6,
            )

        # Create subtasks for detected domains
        subtasks = []
        for domain in self._prioritized_domains(context.domains_detected):
            if domain in self.domain_agents:
                subtasks.append(
                    SubtaskProposal(
                        agent=self.domain_agents[domain],
                        prompt=f"Analyze {domain} aspects",
                        domain=domain,
                        priority=self.priority_order.index(domain) + 1
                        if domain in self.priority_order
                        else 99,
                    )
                )

        if subtasks:
            return DelegationOutput(
                decision=DelegationDecision.DELEGATE,
                rationale=f"Delegating to specialized agents for domains: {context.domains_detected}",
                confidence=0.8,
                subtasks=subtasks,
            )

        # No matching agents, use default
        return DelegationOutput(
            decision=DelegationDecision.DELEGATE,
            rationale=f"Using default agent for domains: {context.domains_detected}",
            confidence=0.6,
            subtasks=[
                SubtaskProposal(
                    agent=self.default_agent,
                    prompt="Analyze task",
                    domain="general",
                    priority=99,
                )
            ],
        )

    def _prioritized_domains(self, domains: list[str]) -> list[str]:
        """Sort domains by priority order."""
        # Sort by priority order, unknown domains last
        return sorted(
            domains,
            key=lambda d: self.priority_order.index(d) if d in self.priority_order else 999,
        )


class IterationLimitPolicy:
    """Stop after a fixed number of iterations.

    Simple policy that enforces a maximum iteration count.
    Useful as a safety net in composite policies.
    """

    def __init__(self, max_iterations: int, inner_policy: DelegationPolicy | None = None):
        self.max_iterations = max_iterations
        self.inner_policy = inner_policy

    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        if context.iteration_count >= self.max_iterations:
            return DelegationOutput(
                decision=DelegationDecision.DONE,
                rationale=f"Max iterations ({self.max_iterations}) reached",
                confidence=1.0,
            )

        if self.inner_policy:
            return self.inner_policy.evaluate(context)

        return DelegationOutput(
            decision=DelegationDecision.CONTINUE,
            rationale=f"Iteration {context.iteration_count}/{self.max_iterations}",
            confidence=0.5,
        )


class EvidenceThresholdPolicy:
    """Continue until enough evidence is collected.

    This policy delegates and continues until a minimum amount
    of evidence has been accumulated.
    """

    def __init__(
        self,
        min_evidence_count: int,
        inner_policy: DelegationPolicy,
    ):
        self.min_evidence_count = min_evidence_count
        self.inner_policy = inner_policy

    def evaluate(self, context: DelegationContext) -> DelegationOutput:
        evidence_count = len(context.accumulated_evidence)

        if evidence_count >= self.min_evidence_count:
            return DelegationOutput(
                decision=DelegationDecision.DONE,
                rationale=f"Evidence threshold met: {evidence_count} >= {self.min_evidence_count}",
                confidence=0.9,
            )

        # Not enough evidence yet
        output = self.inner_policy.evaluate(context)
        if output.decision == DelegationDecision.DONE:
            # Override DONE if we don't have enough evidence
            return DelegationOutput(
                decision=DelegationDecision.CONTINUE,
                rationale=f"Evidence threshold not met: {evidence_count}/{self.min_evidence_count}",
                confidence=0.7,
            )

        return output


__all__ = [
    "ComplexityBasedDelegationPolicy",
    "BudgetAwareDelegationPolicy",
    "StagnationAwarePolicy",
    "DomainBasedDelegationPolicy",
    "IterationLimitPolicy",
    "EvidenceThresholdPolicy",
]
