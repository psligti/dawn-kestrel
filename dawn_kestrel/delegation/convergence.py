"""Convergence tracking module for delegation engine.

Provides the ConvergenceTracker class for detecting when agent results
have stopped producing new information (converged), enabling termination
of iterative delegation workflows.
"""

import hashlib
from typing import Any, List


class ConvergenceTracker:
    """Tracks evidence for convergence detection.

    Uses SHA-256 hash signatures to detect novelty in agent results.
    When results stop changing (stagnation), the tracker can signal
    convergence based on a configurable threshold.

    Attributes:
        evidence_keys: List of keys to extract from results for hashing.
        signatures: History of computed signatures.
        stagnation_count: Number of consecutive identical results.
    """

    def __init__(self, evidence_keys: List[str]):
        """Initialize the convergence tracker.

        Args:
            evidence_keys: List of keys to extract from results for signature computation.
        """
        self.evidence_keys = evidence_keys
        self.signatures: List[str] = []
        self.stagnation_count = 0

    def compute_signature(self, results: List[Any]) -> str:
        """Compute a hash signature from results for novelty detection.

        Extracts evidence from results based on evidence_keys and computes
        a SHA-256 hash. Handles both dict results and AgentResult objects.

        For AgentResult objects:
        1. First tries to extract from result.metadata using evidence_keys
        2. Falls back to parsing result.response if metadata lacks keys
        3. Falls back to str(result) if neither is available

        Args:
            results: List of results (dicts, AgentResult objects, or other).

        Returns:
            SHA-256 hex digest string of the sorted evidence.
        """
        evidence_parts = []

        for result in results:
            # Check if result has metadata attribute (AgentResult-like object)
            if hasattr(result, "metadata") and isinstance(result.metadata, dict):
                # Try to extract from metadata first
                extracted = False
                for key in self.evidence_keys:
                    if key in result.metadata:
                        value = result.metadata[key]
                        evidence_parts.append(self._value_to_str(value))
                        extracted = True

                # If nothing extracted from metadata, try response attribute
                if not extracted and hasattr(result, "response"):
                    evidence_parts.append(str(result.response))
                elif not extracted:
                    evidence_parts.append(str(result))
            elif isinstance(result, dict):
                # Handle dict results
                for key in self.evidence_keys:
                    if key in result:
                        value = result[key]
                        evidence_parts.append(self._value_to_str(value))
            else:
                # Fallback: convert to string
                evidence_parts.append(str(result))

        # Sort for consistent hashing
        evidence_str = "|".join(sorted(evidence_parts))
        return hashlib.sha256(evidence_str.encode()).hexdigest()

    def _value_to_str(self, value: Any) -> str:
        """Convert a value to string for hashing.

        Handles lists by sorting them for consistent comparison.
        Handles dicts by converting to string representation.

        Args:
            value: Any value to convert.

        Returns:
            String representation of the value.
        """
        if isinstance(value, list):
            return str(sorted(value))
        elif isinstance(value, dict):
            return str(value)
        else:
            return str(value)

    def check_novelty(self, results: List[Any]) -> bool:
        """Check if results contain new information.

        Compares the signature of the new results against the last recorded
        signature. Updates stagnation_count and signatures list accordingly.

        Args:
            results: List of results to check for novelty.

        Returns:
            True if results are novel (new information detected).
            False if results are stagnant (same as last) or empty.
        """
        # Handle empty results gracefully
        if not results:
            return False

        new_signature = self.compute_signature(results)

        # Check if same as last signature (stagnation)
        if self.signatures and new_signature == self.signatures[-1]:
            self.stagnation_count += 1
            return False

        # Novel information detected
        self.signatures.append(new_signature)
        self.stagnation_count = 0
        return True

    def is_converged(self, threshold: int) -> bool:
        """Check if convergence has been achieved.

        Convergence is achieved when stagnation_count reaches or exceeds
        the threshold, indicating that results have stopped changing.

        Args:
            threshold: Number of consecutive stagnant results required for convergence.

        Returns:
            True if stagnation_count >= threshold, False otherwise.
        """
        return self.stagnation_count >= threshold
