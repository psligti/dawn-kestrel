"""Tests for policy-driven delegation system.

This module tests:
- DelegationPolicy protocol
- DelegationContext model
- DelegationOutput model
- Built-in delegation policies
- CompositeDelegationPolicy
"""

from __future__ import annotations

import pytest

from dawn_kestrel.policy.delegation import (
    CompositeDelegationPolicy,
    DefaultDelegationPolicy,
    DelegationContext,
    DelegationDecision,
    DelegationOutput,
    DelegationPolicy,
    SubtaskProposal,
)


class TestDelegationContext:
    """Test DelegationContext model."""

    def test_context_defaults(self):
        """Context has sensible defaults."""
        context = DelegationContext(current_agent="test")

        assert context.current_agent == "test"
        assert context.current_depth == 0
        assert context.iteration_count == 0
        assert context.accumulated_results == []
        assert context.tokens_used == 0
        assert context.cost_usd == 0.0
        assert context.task_complexity == 0.5

    def test_budget_exhausted_by_cost(self):
        """Budget is exhausted when cost exceeds limit."""
        context = DelegationContext(
            current_agent="test",
            cost_usd=2.0,
            max_cost_usd=1.0,
        )

        assert context.is_budget_exhausted is True

    def test_budget_exhausted_by_time(self):
        """Budget is exhausted when time exceeds limit."""
        context = DelegationContext(
            current_agent="test",
            elapsed_seconds=400.0,
            max_seconds=300.0,
        )

        assert context.is_budget_exhausted is True

    def test_budget_exhausted_by_depth(self):
        """Budget is exhausted when depth exceeds limit."""
        context = DelegationContext(
            current_agent="test",
            current_depth=5,
            max_depth=3,
        )

        assert context.is_budget_exhausted is True

    def test_budget_not_exhausted(self):
        """Budget is not exhausted when within limits."""
        context = DelegationContext(
            current_agent="test",
            cost_usd=0.5,
            max_cost_usd=1.0,
            elapsed_seconds=100.0,
            max_seconds=300.0,
            current_depth=1,
            max_depth=3,
            iteration_count=5,
            max_iterations=10,
        )

        assert context.is_budget_exhausted is False

    def test_stagnant_when_no_findings(self):
        """Progress is stagnant when no findings in recent iterations."""
        context = DelegationContext(
            current_agent="test",
            findings_per_iteration=[0, 0, 0, 0, 0],
            stagnation_threshold=3,
        )

        assert context.is_stagnant is True

    def test_not_stagnant_with_findings(self):
        """Progress is not stagnant when findings exist."""
        context = DelegationContext(
            current_agent="test",
            findings_per_iteration=[1, 0, 2, 0, 1],
            stagnation_threshold=3,
        )

        assert context.is_stagnant is False

    def test_not_stagnant_too_few_iterations(self):
        """Cannot detect stagnation with too few iterations."""
        context = DelegationContext(
            current_agent="test",
            findings_per_iteration=[0, 0],
            stagnation_threshold=3,
        )

        assert context.is_stagnant is False

    def test_budget_remaining_percent(self):
        """Budget remaining is minimum of all constraints."""
        context = DelegationContext(
            current_agent="test",
            cost_usd=0.5,
            max_cost_usd=1.0,
            elapsed_seconds=150.0,
            max_seconds=300.0,
            iteration_count=5,
            max_iterations=10,
        )

        assert context.budget_remaining_percent == 0.5


class TestDelegationOutput:
    """Test DelegationOutput model."""

    def test_output_defaults(self):
        """Output has sensible defaults."""
        output = DelegationOutput(decision=DelegationDecision.DONE)

        assert output.decision == DelegationDecision.DONE
        assert output.rationale == ""
        assert output.confidence == 0.8
        assert output.subtasks == []
        assert output.continue_with is None

    def test_output_with_subtasks(self):
        """Output can include subtasks."""
        output = DelegationOutput(
            decision=DelegationDecision.DELEGATE,
            subtasks=[
                SubtaskProposal(agent="specialist", prompt="Analyze this"),
            ],
        )

        assert output.decision == DelegationDecision.DELEGATE
        assert len(output.subtasks) == 1
        assert output.subtasks[0].agent == "specialist"

    def test_subtask_proposal_defaults(self):
        """SubtaskProposal has sensible defaults."""
        proposal = SubtaskProposal(agent="test", prompt="Do something")

        assert proposal.agent == "test"
        assert proposal.prompt == "Do something"
        assert proposal.domain == "general"
        assert proposal.priority == 1
        assert proposal.metadata == {}


class TestDelegationDecision:
    """Test DelegationDecision enum."""

    def test_all_decisions_exist(self):
        """All expected decisions exist."""
        assert DelegationDecision.CONTINUE.value == "continue"
        assert DelegationDecision.DELEGATE.value == "delegate"
        assert DelegationDecision.SYNTHESIZE.value == "synthesize"
        assert DelegationDecision.DONE.value == "done"


class TestDelegationPolicyProtocol:
    """Test DelegationPolicy protocol."""

    def test_policy_is_protocol(self):
        """DelegationPolicy is a Protocol."""
        from typing import Protocol

        assert issubclass(DelegationPolicy, Protocol)

    def test_custom_implementation(self):
        """Custom implementation satisfies the protocol."""

        class CustomPolicy:
            def evaluate(self, context: DelegationContext) -> DelegationOutput:
                return DelegationOutput(decision=DelegationDecision.DONE)

        policy = CustomPolicy()
        assert isinstance(policy, DelegationPolicy)


class TestDefaultDelegationPolicy:
    """Test DefaultDelegationPolicy."""

    def test_default_returns_done(self):
        """Default policy returns DONE."""
        policy = DefaultDelegationPolicy()
        context = DelegationContext(current_agent="test")

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DONE
        assert output.confidence == 0.5

    def test_custom_decision(self):
        """Default policy can return custom decision."""
        policy = DefaultDelegationPolicy(
            decision=DelegationDecision.DELEGATE,
            rationale="Testing",
        )
        context = DelegationContext(current_agent="test")

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DELEGATE
        assert output.rationale == "Testing"


class TestCompositeDelegationPolicy:
    """Test CompositeDelegationPolicy."""

    def test_first_policy_wins_with_high_confidence(self):
        """First policy with high confidence wins."""

        class HighConfidencePolicy:
            def evaluate(self, context: DelegationContext) -> DelegationOutput:
                return DelegationOutput(
                    decision=DelegationDecision.DELEGATE,
                    confidence=0.95,
                )

        class NeverCalledPolicy:
            def evaluate(self, context: DelegationContext) -> DelegationOutput:
                raise AssertionError("Should not be called")

        policy = CompositeDelegationPolicy(
            [
                HighConfidencePolicy(),
                NeverCalledPolicy(),
            ]
        )
        context = DelegationContext(current_agent="test")

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DELEGATE
        assert output.confidence == 0.95

    def test_policies_evaluated_in_order(self):
        """Policies are evaluated in order."""

        call_order = []

        class TrackingPolicy:
            def __init__(self, name: str):
                self.name = name

            def evaluate(self, context: DelegationContext) -> DelegationOutput:
                call_order.append(self.name)
                return DelegationOutput(decision=DelegationDecision.DONE)

        policy = CompositeDelegationPolicy(
            [
                TrackingPolicy("first"),
                TrackingPolicy("second"),
                TrackingPolicy("third"),
            ]
        )
        context = DelegationContext(current_agent="test")

        policy.evaluate(context)

        assert call_order == ["first", "second", "third"]

    def test_fallback_to_done(self):
        """Composite falls back to DONE if no policy decides."""
        policy = CompositeDelegationPolicy([])
        context = DelegationContext(current_agent="test")

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DONE
        assert "exhausted" in output.rationale.lower()


class TestBuiltInPolicies:
    """Test built-in delegation policies."""

    def test_complexity_based_delegates_when_high(self):
        """ComplexityBasedDelegationPolicy delegates when complexity is high."""
        from dawn_kestrel.policy.builtin.delegation import ComplexityBasedDelegationPolicy

        policy = ComplexityBasedDelegationPolicy(complexity_threshold=0.5)
        context = DelegationContext(
            current_agent="test",
            task_complexity=0.8,
            domains_detected=["security"],
        )

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DELEGATE

    def test_complexity_based_continue_when_low(self):
        """ComplexityBasedDelegationPolicy continues when complexity is low."""
        from dawn_kestrel.policy.builtin.delegation import ComplexityBasedDelegationPolicy

        policy = ComplexityBasedDelegationPolicy(complexity_threshold=0.5)
        context = DelegationContext(
            current_agent="test",
            task_complexity=0.3,
        )

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.CONTINUE

    def test_budget_aware_stops_when_exhausted(self):
        """BudgetAwareDelegationPolicy stops when budget is exhausted."""
        from dawn_kestrel.policy.builtin.delegation import BudgetAwareDelegationPolicy

        inner = DefaultDelegationPolicy(decision=DelegationDecision.DELEGATE)
        policy = BudgetAwareDelegationPolicy(inner_policy=inner)
        context = DelegationContext(
            current_agent="test",
            cost_usd=2.0,
            max_cost_usd=1.0,
        )

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DONE
        assert "budget" in output.rationale.lower()

    def test_budget_aware_passes_to_inner(self):
        """BudgetAwareDelegationPolicy passes to inner when budget OK."""
        from dawn_kestrel.policy.builtin.delegation import BudgetAwareDelegationPolicy

        inner = DefaultDelegationPolicy(decision=DelegationDecision.DELEGATE)
        policy = BudgetAwareDelegationPolicy(inner_policy=inner)
        context = DelegationContext(
            current_agent="test",
            cost_usd=0.5,
            max_cost_usd=1.0,
        )

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DELEGATE

    def test_stagnation_aware_stops_when_stagnant(self):
        """StagnationAwarePolicy stops when progress is stagnant."""
        from dawn_kestrel.policy.builtin.delegation import StagnationAwarePolicy

        inner = DefaultDelegationPolicy(decision=DelegationDecision.DELEGATE)
        policy = StagnationAwarePolicy(inner_policy=inner, stagnation_threshold=3)
        context = DelegationContext(
            current_agent="test",
            findings_per_iteration=[0, 0, 0, 0],
        )

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DONE

    def test_stagnation_aware_passes_to_inner(self):
        """StagnationAwarePolicy passes to inner when not stagnant."""
        from dawn_kestrel.policy.builtin.delegation import StagnationAwarePolicy

        inner = DefaultDelegationPolicy(decision=DelegationDecision.DELEGATE)
        policy = StagnationAwarePolicy(inner_policy=inner, stagnation_threshold=3)
        context = DelegationContext(
            current_agent="test",
            findings_per_iteration=[1, 2],
        )

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DELEGATE

    def test_iteration_limit_enforces_max(self):
        """IterationLimitPolicy enforces maximum iterations."""
        from dawn_kestrel.policy.builtin.delegation import IterationLimitPolicy

        policy = IterationLimitPolicy(max_iterations=5)
        context = DelegationContext(
            current_agent="test",
            iteration_count=6,
            max_iterations=5,
        )

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DONE

    def test_domain_based_creates_subtasks(self):
        """DomainBasedDelegationPolicy creates subtasks for domains."""
        from dawn_kestrel.policy.builtin.delegation import DomainBasedDelegationPolicy

        policy = DomainBasedDelegationPolicy(
            {
                "security": "security_reviewer",
                "docs": "doc_writer",
            }
        )
        context = DelegationContext(
            current_agent="test",
            domains_detected=["security", "docs"],
        )

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DELEGATE
        assert len(output.subtasks) == 2


class TestDelegationPolicyIntegration:
    """Integration tests for delegation policies."""

    def test_composite_with_real_policies(self):
        """Composite works with real built-in policies."""
        from dawn_kestrel.policy.builtin.delegation import (
            BudgetAwareDelegationPolicy,
            ComplexityBasedDelegationPolicy,
            StagnationAwarePolicy,
        )

        inner = ComplexityBasedDelegationPolicy(complexity_threshold=0.5)
        policy = CompositeDelegationPolicy([
            BudgetAwareDelegationPolicy(inner_policy=inner),
            StagnationAwarePolicy(inner_policy=inner, stagnation_threshold=3),
            inner,
            DefaultDelegationPolicy(decision=DelegationDecision.DONE),
        ])

        context = DelegationContext(
            current_agent="test",
            task_complexity=0.8,
            cost_usd=0.3,
            max_cost_usd=1.0,
            findings_per_iteration=[1, 2, 1],
            domains_detected=["security"],
        )

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DELEGATE

    def test_policy_chain_stops_at_budget(self):
        """Policy chain stops when budget is exhausted."""
        from dawn_kestrel.policy.builtin.delegation import (
            BudgetAwareDelegationPolicy,
            ComplexityBasedDelegationPolicy,
        )

        inner = ComplexityBasedDelegationPolicy(complexity_threshold=0.5)
        policy = CompositeDelegationPolicy([
            BudgetAwareDelegationPolicy(inner_policy=inner),
            inner,
        ])

        context = DelegationContext(
            current_agent="test",
            task_complexity=0.9,
            cost_usd=2.0,
            max_cost_usd=1.0,
        )

        output = policy.evaluate(context)

        assert output.decision == DelegationDecision.DONE
        assert "budget" in output.rationale.lower()

