"""Tests for ConvergenceTracker module.

Tests verify that ConvergenceTracker provides:
- SHA-256 hash signatures for novelty detection
- Novelty checking with stagnation tracking
- Convergence detection based on stagnation threshold
- Handling of AgentResult objects (extracts from .metadata first, then .response)
- Graceful handling of empty results list
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest


# Mock AgentResult for testing - mirrors the real AgentResult structure
@dataclass
class MockAgentResult:
    """Mock AgentResult for testing convergence tracker."""

    agent_name: str
    response: str
    parts: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tools_used: List[str] = field(default_factory=list)
    error: Optional[str] = None


class TestConvergenceTrackerInit:
    """Test ConvergenceTracker initialization."""

    def test_init_with_evidence_keys(self):
        """ConvergenceTracker can be initialized with evidence keys."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer", "confidence"])
        assert tracker.evidence_keys == ["answer", "confidence"]
        assert tracker.signatures == []
        assert tracker.stagnation_count == 0

    def test_init_with_empty_evidence_keys(self):
        """ConvergenceTracker can be initialized with empty evidence keys."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=[])
        assert tracker.evidence_keys == []


class TestComputeSignature:
    """Test compute_signature method."""

    def test_compute_signature_returns_sha256_hexdigest(self):
        """compute_signature returns SHA-256 hex digest."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results = [{"answer": "test value"}]

        signature = tracker.compute_signature(results)
        # SHA-256 produces 64 character hex string
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)

    def test_compute_signature_consistent_for_same_input(self):
        """compute_signature returns same hash for same input."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results = [{"answer": "test value", "other": "ignored"}]

        sig1 = tracker.compute_signature(results)
        sig2 = tracker.compute_signature(results)
        assert sig1 == sig2

    def test_compute_signature_different_for_different_input(self):
        """compute_signature returns different hash for different input."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results1 = [{"answer": "value1"}]
        results2 = [{"answer": "value2"}]

        sig1 = tracker.compute_signature(results1)
        sig2 = tracker.compute_signature(results2)
        assert sig1 != sig2

    def test_compute_signature_with_multiple_evidence_keys(self):
        """compute_signature extracts multiple evidence keys."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer", "confidence"])
        results = [{"answer": "yes", "confidence": 0.9}]

        signature = tracker.compute_signature(results)
        assert len(signature) == 64

    def test_compute_signature_ignores_non_evidence_keys(self):
        """compute_signature ignores keys not in evidence_keys."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results1 = [{"answer": "yes", "extra": "data1"}]
        results2 = [{"answer": "yes", "extra": "data2"}]

        sig1 = tracker.compute_signature(results1)
        sig2 = tracker.compute_signature(results2)
        # Same answer, different extra - should have same signature
        assert sig1 == sig2

    def test_compute_signature_with_dict_result(self):
        """compute_signature handles dict results correctly."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["key"])
        results = [{"key": "value"}]

        signature = tracker.compute_signature(results)
        assert len(signature) == 64

    def test_compute_signature_with_list_values(self):
        """compute_signature handles list values by sorting them."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["items"])
        # Same items in different order should produce same signature
        results1 = [{"items": ["a", "b", "c"]}]
        results2 = [{"items": ["c", "a", "b"]}]

        sig1 = tracker.compute_signature(results1)
        sig2 = tracker.compute_signature(results2)
        assert sig1 == sig2

    def test_compute_signature_with_empty_results(self):
        """compute_signature handles empty results list."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["key"])
        signature = tracker.compute_signature([])

        # Empty list should still produce a valid signature
        assert len(signature) == 64


class TestComputeSignatureWithAgentResult:
    """Test compute_signature with AgentResult objects."""

    def test_compute_signature_extracts_from_metadata(self):
        """compute_signature extracts evidence from AgentResult.metadata."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer", "confidence"])
        results = [
            MockAgentResult(
                agent_name="test_agent",
                response="The answer is yes",
                metadata={"answer": "yes", "confidence": 0.95},
            )
        ]

        signature = tracker.compute_signature(results)
        assert len(signature) == 64

    def test_compute_signature_falls_back_to_response(self):
        """compute_signature falls back to AgentResult.response when metadata lacks keys."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results = [
            MockAgentResult(
                agent_name="test_agent",
                response="The answer is no",
                metadata={"other_key": "value"},  # No "answer" key
            )
        ]

        signature = tracker.compute_signature(results)
        # Should use response string as fallback
        assert len(signature) == 64

    def test_compute_signature_metadata_takes_precedence(self):
        """compute_signature prefers metadata over response."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        result_with_metadata = [
            MockAgentResult(
                agent_name="test_agent",
                response="response text",
                metadata={"answer": "metadata_answer"},
            )
        ]
        result_without_metadata = [
            MockAgentResult(
                agent_name="test_agent",
                response="metadata_answer",  # Same value as metadata above
                metadata={},
            )
        ]

        sig1 = tracker.compute_signature(result_with_metadata)
        sig2 = tracker.compute_signature(result_without_metadata)
        # Should produce different signatures since one extracts from metadata
        assert sig1 == sig2  # Both should extract "metadata_answer"

    def test_compute_signature_with_mixed_result_types(self):
        """compute_signature handles mix of AgentResult and dict."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results = [
            MockAgentResult(
                agent_name="agent1", response="response1", metadata={"answer": "same_answer"}
            ),
            {"answer": "same_answer"},
        ]

        signature = tracker.compute_signature(results)
        assert len(signature) == 64


class TestCheckNovelty:
    """Test check_novelty method."""

    def test_check_novelty_returns_true_for_first_call(self):
        """check_novelty returns True for first call with results."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results = [{"answer": "first result"}]

        is_novel = tracker.check_novelty(results)
        assert is_novel is True
        assert len(tracker.signatures) == 1
        assert tracker.stagnation_count == 0

    def test_check_novelty_returns_true_for_different_results(self):
        """check_novelty returns True when results differ."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])

        tracker.check_novelty([{"answer": "result1"}])
        is_novel = tracker.check_novelty([{"answer": "result2"}])

        assert is_novel is True
        assert tracker.stagnation_count == 0

    def test_check_novelty_returns_false_for_identical_consecutive(self):
        """check_novelty returns False for identical consecutive results."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results = [{"answer": "same result"}]

        tracker.check_novelty(results)
        is_novel = tracker.check_novelty(results)

        assert is_novel is False
        assert tracker.stagnation_count == 1

    def test_check_novelty_increments_stagnation_count(self):
        """check_novelty increments stagnation_count on identical results."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results = [{"answer": "same"}]

        tracker.check_novelty(results)
        assert tracker.stagnation_count == 0

        tracker.check_novelty(results)
        assert tracker.stagnation_count == 1

        tracker.check_novelty(results)
        assert tracker.stagnation_count == 2

    def test_check_novelty_resets_stagnation_on_novelty(self):
        """check_novelty resets stagnation_count when novel results appear."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])

        tracker.check_novelty([{"answer": "result1"}])
        tracker.check_novelty([{"answer": "result1"}])
        assert tracker.stagnation_count == 1

        tracker.check_novelty([{"answer": "result2"}])
        assert tracker.stagnation_count == 0

    def test_check_novelty_returns_false_for_empty_results(self):
        """check_novelty returns False for empty results list."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])

        is_novel = tracker.check_novelty([])
        assert is_novel is False
        assert tracker.stagnation_count == 0

    def test_check_novelty_appends_signature_on_novelty(self):
        """check_novelty appends signature to signatures list on novelty."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])

        tracker.check_novelty([{"answer": "r1"}])
        assert len(tracker.signatures) == 1

        tracker.check_novelty([{"answer": "r2"}])
        assert len(tracker.signatures) == 2

    def test_check_novelty_does_not_append_on_stagnation(self):
        """check_novelty does not append signature on stagnant results."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results = [{"answer": "same"}]

        tracker.check_novelty(results)
        tracker.check_novelty(results)
        tracker.check_novelty(results)

        # Only one signature should exist (the first one)
        assert len(tracker.signatures) == 1


class TestIsConverged:
    """Test is_converged method."""

    def test_is_converged_false_below_threshold(self):
        """is_converged returns False when stagnation_count < threshold."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        tracker.stagnation_count = 2

        assert tracker.is_converged(threshold=3) is False

    def test_is_converged_true_at_threshold(self):
        """is_converged returns True when stagnation_count >= threshold."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        tracker.stagnation_count = 3

        assert tracker.is_converged(threshold=3) is True

    def test_is_converged_true_above_threshold(self):
        """is_converged returns True when stagnation_count > threshold."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        tracker.stagnation_count = 5

        assert tracker.is_converged(threshold=3) is True

    def test_is_converged_false_at_zero_stagnation(self):
        """is_converged returns False when stagnation_count is 0."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])

        assert tracker.is_converged(threshold=1) is False

    def test_is_converged_with_threshold_one(self):
        """is_converged with threshold=1 converges after first stagnation."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer"])
        results = [{"answer": "same"}]

        tracker.check_novelty(results)
        assert tracker.is_converged(threshold=1) is False

        tracker.check_novelty(results)
        assert tracker.is_converged(threshold=1) is True


class TestIntegration:
    """Integration tests for ConvergenceTracker."""

    def test_full_convergence_workflow(self):
        """Test complete workflow from start to convergence."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["result"])

        # First iteration - novel
        assert tracker.check_novelty([{"result": "A"}]) is True
        assert tracker.is_converged(threshold=3) is False

        # Second iteration - same, stagnant
        assert tracker.check_novelty([{"result": "A"}]) is False
        assert tracker.is_converged(threshold=3) is False

        # Third iteration - same, stagnant
        assert tracker.check_novelty([{"result": "A"}]) is False
        assert tracker.is_converged(threshold=3) is False

        # Fourth iteration - same, converged!
        assert tracker.check_novelty([{"result": "A"}]) is False
        assert tracker.is_converged(threshold=3) is True

    def test_convergence_resets_on_new_information(self):
        """Test convergence resets when new information appears."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["result"])

        # Build up stagnation (need 4 calls: 1st=novel, 2nd/3rd/4th=stagnant)
        tracker.check_novelty([{"result": "A"}])  # novel, stagnation=0
        tracker.check_novelty([{"result": "A"}])  # stagnant, stagnation=1
        tracker.check_novelty([{"result": "A"}])  # stagnant, stagnation=2
        tracker.check_novelty([{"result": "A"}])  # stagnant, stagnation=3
        assert tracker.is_converged(threshold=3) is True

        # New information resets stagnation
        tracker.check_novelty([{"result": "B"}])
        assert tracker.is_converged(threshold=3) is False

    def test_with_agent_results(self):
        """Test convergence workflow with AgentResult objects."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["answer", "confidence"])

        results = [
            MockAgentResult(
                agent_name="explorer",
                response="Exploration complete",
                metadata={"answer": "found", "confidence": 0.9},
            )
        ]

        # First call - novel
        assert tracker.check_novelty(results) is True

        # Same results - stagnant
        assert tracker.check_novelty(results) is False
        assert tracker.stagnation_count == 1

    def test_signature_determinism(self):
        """Test that signature computation is deterministic."""
        from dawn_kestrel.delegation.convergence import ConvergenceTracker

        tracker = ConvergenceTracker(evidence_keys=["a", "b", "c"])

        results = [
            {"a": "1", "b": "2", "c": "3"},
            {"a": "4", "b": "5"},
        ]

        # Call multiple times - should always produce same signature
        signatures = [tracker.compute_signature(results) for _ in range(10)]
        assert len(set(signatures)) == 1  # All signatures identical
