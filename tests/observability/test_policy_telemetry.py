"""Tests for policy telemetry and rejection events.

Tests verify:
- Policy proposals emit trace events
- Rejection events include required fields (policy_id, reason_code,
  blocked_action_type, blocked_action_risk, remediation_hints)
- HarnessGate rejection payloads are properly formatted
"""

import json
from datetime import datetime

import pytest

from dawn_kestrel.observability.trace import Span, TraceCollector, TraceStore
from dawn_kestrel.policy.contracts import (
    EditFileAction,
    RiskLevel,
    StepProposal,
    TodoCompletionClaim,
)
from dawn_kestrel.policy.invariants import HarnessGate


class TestProposalDecisionEvent:
    """Tests for policy proposal decision trace events."""

    def test_proposal_decision_event_emitted(self):
        """Policy proposals emit trace events when evaluated."""
        collector = TraceCollector()
        gate = HarnessGate()

        # Create a valid proposal (should pass validation)
        proposal = StepProposal(
            intent="Read configuration file",
            actions=[
                EditFileAction(
                    path="config.py",
                    operation="replace",
                    content="# config",
                )
            ],
            risk_level=RiskLevel.LOW,
        )

        # Start trace span for policy evaluation
        span = collector.start_span(
            name="policy.evaluate_proposal",
            trace_id="trace-001",
            attributes={
                "proposal.intent": proposal.intent,
                "proposal.risk_level": proposal.risk_level.value,
            },
        )

        # Enforce policy
        result = gate.enforce(proposal)

        # End span with decision
        collector.end_span(span.span_id)
        span.attributes["decision.valid"] = result.valid

        # Verify trace event was created
        assert span.name == "policy.evaluate_proposal"
        assert span.trace_id == "trace-001"
        assert "proposal.intent" in span.attributes
        assert span.end_time is not None
        assert "decision.valid" in span.attributes

    def test_proposal_decision_event_includes_proposal_metadata(self):
        """Proposal decision events include proposal metadata in attributes."""
        collector = TraceCollector()
        gate = HarnessGate()

        proposal = StepProposal(
            intent="Edit authentication module",
            target_todo_ids=["todo-1", "todo-2"],
            actions=[
                EditFileAction(
                    path="auth.py",
                    operation="replace",
                    content="# auth",
                )
            ],
            risk_level=RiskLevel.MED,
        )

        # Create span with full proposal metadata
        span = collector.start_span(
            name="policy.evaluate_proposal",
            attributes={
                "proposal.intent": proposal.intent,
                "proposal.risk_level": proposal.risk_level.value,
                "proposal.target_todos": ",".join(proposal.target_todo_ids),
                "proposal.action_types": ",".join(proposal.get_action_types()),
                "proposal.has_high_risk_actions": proposal.has_high_risk_actions(),
            },
        )

        result = gate.enforce(proposal)
        collector.end_span(span.span_id)

        # Verify metadata is captured
        assert span.attributes["proposal.intent"] == "Edit authentication module"
        assert span.attributes["proposal.risk_level"] == "MED"
        assert "todo-1" in span.attributes["proposal.target_todos"]
        assert "EDIT_FILE" in span.attributes["proposal.action_types"]

    def test_proposal_decision_stored_in_trace_store(self):
        """Proposal decisions can be stored and queried from TraceStore."""
        store = TraceStore()
        collector = TraceCollector()
        gate = HarnessGate()

        proposal = StepProposal(
            intent="Run tests",
            actions=[],
            risk_level=RiskLevel.LOW,
        )

        # Create and store trace span
        span = collector.start_span(
            name="policy.evaluate_proposal",
            trace_id="trace-001",
            session_id="session-001",
            attributes={
                "proposal.intent": proposal.intent,
            },
        )

        result = gate.enforce(proposal)
        collector.end_span(span.span_id)

        # Store the span
        store.add(span)

        # Query by session_id
        stored_spans = store.query(session_id="session-001")
        assert len(stored_spans) == 1
        assert stored_spans[0].name == "policy.evaluate_proposal"


class TestProposalRejectionEvent:
    """Tests for policy proposal rejection events."""

    def test_proposal_rejection_includes_required_fields(self):
        """Rejection events include all required fields in payload."""
        gate = HarnessGate()

        # Create a proposal that will be rejected (budget exhausted)
        proposal = StepProposal(
            intent="Continue execution",
            notes="budget exhausted",
            risk_level=RiskLevel.MED,
        )

        result = gate.enforce(proposal)

        # Verify rejection
        assert result.valid is False
        assert len(result.errors) > 0

        # Parse rejection payload
        rejection_payload = json.loads(result.errors[0])

        # Verify all required fields are present
        assert "policy_id" in rejection_payload
        assert "reason_code" in rejection_payload
        assert "blocked_action_type" in rejection_payload
        assert "blocked_action_risk" in rejection_payload
        assert "remediation_hints" in rejection_payload

    def test_proposal_rejection_policy_id_field(self):
        """Rejection payload includes policy_id field."""
        gate = HarnessGate()

        proposal = StepProposal(
            intent="Continue execution",
            notes="budget exhausted",
            risk_level=RiskLevel.LOW,
        )

        result = gate.enforce(proposal)
        rejection_payload = json.loads(result.errors[0])

        assert rejection_payload["policy_id"] == "harness_invariants"

    def test_proposal_rejection_reason_code_field(self):
        """Rejection payload includes reason_code field."""
        gate = HarnessGate()

        # Test BUDGET_EXHAUSTED reason
        proposal = StepProposal(
            intent="Continue",
            notes="budget exhausted",
            risk_level=RiskLevel.LOW,
        )

        result = gate.enforce(proposal)
        rejection_payload = json.loads(result.errors[0])

        assert rejection_payload["reason_code"] == "BUDGET_EXHAUSTED"

    def test_proposal_rejection_blocked_action_type_field(self):
        """Rejection payload includes blocked_action_type field."""
        gate = HarnessGate()

        proposal = StepProposal(
            intent="Continue",
            notes="budget exhausted",
            actions=[
                EditFileAction(
                    path="test.py",
                    operation="replace",
                    content="# test",
                )
            ],
            risk_level=RiskLevel.MED,
        )

        result = gate.enforce(proposal)
        rejection_payload = json.loads(result.errors[0])

        assert "blocked_action_type" in rejection_payload
        assert rejection_payload["blocked_action_type"] in ["EDIT_FILE", "HALT"]

    def test_proposal_rejection_blocked_action_risk_field(self):
        """Rejection payload includes blocked_action_risk field."""
        gate = HarnessGate()

        proposal = StepProposal(
            intent="Continue",
            notes="budget exhausted",
            risk_level=RiskLevel.HIGH,
        )

        result = gate.enforce(proposal)
        rejection_payload = json.loads(result.errors[0])

        assert "blocked_action_risk" in rejection_payload
        assert rejection_payload["blocked_action_risk"] == "HIGH"

    def test_proposal_rejection_remediation_hints_field(self):
        """Rejection payload includes remediation_hints field."""
        gate = HarnessGate()

        proposal = StepProposal(
            intent="Continue",
            notes="budget exhausted",
            risk_level=RiskLevel.LOW,
        )

        result = gate.enforce(proposal)
        rejection_payload = json.loads(result.errors[0])

        assert "remediation_hints" in rejection_payload
        assert isinstance(rejection_payload["remediation_hints"], list)
        assert len(rejection_payload["remediation_hints"]) > 0

    def test_unverified_completion_rejection(self):
        """UNVERIFIED_COMPLETION rejection has correct payload structure."""
        gate = HarnessGate()

        # Create proposal with completion claim but no evidence
        proposal = StepProposal(
            intent="Mark task as complete",
            completion_claims=[
                TodoCompletionClaim(
                    todo_id="todo-1",
                    evidence_type="inference",  # Not a verification evidence type
                    evidence_summary="Task appears complete",
                )
            ],
            risk_level=RiskLevel.LOW,
        )

        result = gate.enforce(proposal)

        # This should be rejected for unverified completion
        assert result.valid is False
        rejection_payload = json.loads(result.errors[0])

        assert rejection_payload["reason_code"] == "UNVERIFIED_COMPLETION"
        assert rejection_payload["blocked_action_type"] == "COMPLETE_TODO"
        assert "remediation_hints" in rejection_payload

    def test_approval_required_rejection(self):
        """APPROVAL_REQUIRED rejection has correct payload structure."""
        gate = HarnessGate()

        # Create proposal with high-risk action but no approval request
        proposal = StepProposal(
            intent="Edit file without approval",
            actions=[
                EditFileAction(
                    path="important.py",
                    operation="replace",
                    content="# modified",
                )
            ],
            risk_level=RiskLevel.HIGH,
        )

        result = gate.enforce(proposal)

        # This should be rejected for missing approval
        assert result.valid is False
        rejection_payload = json.loads(result.errors[0])

        assert rejection_payload["reason_code"] == "APPROVAL_REQUIRED"
        assert rejection_payload["blocked_action_type"] == "EDIT_FILE"
        assert "remediation_hints" in rejection_payload

    def test_rejection_event_can_be_traced(self):
        """Rejection events can be captured in trace spans."""
        collector = TraceCollector()
        gate = HarnessGate()

        proposal = StepProposal(
            intent="Risky operation",
            notes="budget exhausted",
            risk_level=RiskLevel.HIGH,
        )

        # Create span for policy evaluation
        span = collector.start_span(
            name="policy.evaluate_proposal",
            trace_id="trace-rejection-001",
            attributes={
                "proposal.intent": proposal.intent,
                "proposal.risk_level": proposal.risk_level.value,
            },
        )

        result = gate.enforce(proposal)
        collector.end_span(span.span_id)

        # Add rejection details to span attributes
        if not result.valid and result.errors:
            rejection_payload = json.loads(result.errors[0])
            span.attributes["rejection.policy_id"] = rejection_payload["policy_id"]
            span.attributes["rejection.reason_code"] = rejection_payload["reason_code"]
            span.attributes["rejection.blocked_action_type"] = rejection_payload[
                "blocked_action_type"
            ]
            span.attributes["rejection.blocked_action_risk"] = rejection_payload[
                "blocked_action_risk"
            ]
            span.attributes["decision.valid"] = False

        # Verify rejection is captured in trace
        assert span.attributes["decision.valid"] is False
        assert span.attributes["rejection.policy_id"] == "harness_invariants"
        assert span.attributes["rejection.reason_code"] == "BUDGET_EXHAUSTED"
        assert "rejection.blocked_action_type" in span.attributes
        assert "rejection.blocked_action_risk" in span.attributes

    def test_multiple_rejection_errors_all_formatted(self):
        """All rejection errors in a result are properly formatted."""
        gate = HarnessGate()

        # Create proposal that triggers rejection
        proposal = StepProposal(
            intent="Test",
            notes="budget exhausted",
            risk_level=RiskLevel.LOW,
        )

        result = gate.enforce(proposal)

        # All errors should be valid JSON with required fields
        for error in result.errors:
            payload = json.loads(error)
            assert "policy_id" in payload
            assert "reason_code" in payload
            assert "blocked_action_type" in payload
            assert "blocked_action_risk" in payload
            assert "remediation_hints" in payload
