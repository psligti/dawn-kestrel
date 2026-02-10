"""Tests for FSM security reviewer confidence scoring and threshold filtering.

Tests TD-018:
- Confidence threshold filters low-confidence findings
- Malformed confidence values use safe fallback (0.50)
- Confidence metadata appears in logs
- Threshold is configurable
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from io import StringIO
import logging

from dawn_kestrel.agents.review.fsm_security import (
    SecurityReviewerAgent,
    SecurityFinding,
    ReviewState,
)


class TestConfidenceThresholdFilters:
    """Test that low-confidence findings are filtered from final assessment."""

    @pytest.mark.asyncio
    async def test_low_confidence_findings_filtered(self):
        """Verify findings below confidence threshold are excluded from final assessment.

        Tests that findings with confidence_score < threshold are filtered out,
        while findings >= threshold are included.
        """
        orchestrator = Mock(spec=object)
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator, session_id="test-session", confidence_threshold=0.60
        )

        # Create mock findings with varying confidence scores
        reviewer.findings = [
            SecurityFinding(
                id="sec_001",
                severity="critical",
                title="Critical issue",
                description="Critical security issue",
                evidence="Evidence for critical issue",
                confidence_score=0.90,  # Above threshold - should be included
            ),
            SecurityFinding(
                id="sec_002",
                severity="high",
                title="High issue",
                description="High security issue",
                evidence="Evidence for high issue",
                confidence_score=0.65,  # Above threshold - should be included
            ),
            SecurityFinding(
                id="sec_003",
                severity="medium",
                title="Medium issue",
                description="Medium security issue",
                evidence="Evidence for medium issue",
                confidence_score=0.40,  # Below threshold - should be filtered out
            ),
            SecurityFinding(
                id="sec_004",
                severity="low",
                title="Low issue",
                description="Low security issue",
                evidence="Evidence for low issue",
                confidence_score=0.25,  # Below threshold - should be filtered out
            ),
        ]

        # Generate final assessment
        assessment = await reviewer._generate_final_assessment()

        # Verify only findings above threshold are included
        assert assessment.total_findings == 2
        assert len(assessment.findings) == 2
        assert assessment.findings[0].id == "sec_001"
        assert assessment.findings[1].id == "sec_002"

        # Verify counts reflect filtered findings
        assert assessment.critical_count == 1
        assert assessment.high_count == 1
        assert assessment.medium_count == 0
        assert assessment.low_count == 0

        # Verify notes mention filtering
        assert "Filtered out 2 findings below confidence threshold" in " ".join(assessment.notes)

    @pytest.mark.asyncio
    async def test_default_threshold_0_50(self):
        """Verify default threshold of 0.50 is used when not specified."""
        orchestrator = Mock(spec=object)
        reviewer = SecurityReviewerAgent(orchestrator=orchestrator, session_id="test-session")

        assert reviewer.confidence_threshold == 0.50

        # Create findings at threshold boundary
        reviewer.findings = [
            SecurityFinding(
                id="sec_001",
                severity="critical",
                title="At threshold",
                description="At threshold issue",
                evidence="Evidence",
                confidence_score=0.50,  # Exactly at threshold - should be included
            ),
            SecurityFinding(
                id="sec_002",
                severity="high",
                title="Below threshold",
                description="Below threshold issue",
                evidence="Evidence",
                confidence_score=0.49,  # Just below threshold - should be filtered
            ),
        ]

        assessment = await reviewer._generate_final_assessment()

        # Only sec_001 should be included (0.50 >= 0.50)
        assert assessment.total_findings == 1
        assert assessment.findings[0].id == "sec_001"


class TestMalformedConfidenceFallback:
    """Test that malformed confidence values use safe fallback of 0.50."""

    @pytest.mark.asyncio
    async def test_string_confidence_uses_fallback(self):
        """Verify string confidence values use 0.50 fallback and are included."""
        orchestrator = Mock(spec=object)
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator, session_id="test-session", confidence_threshold=0.60
        )

        # Create finding with malformed string confidence
        reviewer.findings = [
            SecurityFinding(
                id="sec_001",
                severity="critical",
                title="Malformed confidence",
                description="Issue with malformed confidence",
                evidence="Evidence",
                confidence_score="high",  # String instead of number - uses fallback
            )
        ]

        assessment = await reviewer._generate_final_assessment()

        # Fallback 0.50 is below 0.60 threshold, so finding should be filtered
        assert assessment.total_findings == 0

    @pytest.mark.asyncio
    async def test_negative_confidence_uses_fallback(self):
        """Verify negative confidence values use 0.50 fallback."""
        orchestrator = Mock(spec=object)
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator, session_id="test-session", confidence_threshold=0.60
        )

        # Create finding with negative confidence (invalid)
        reviewer.findings = [
            SecurityFinding(
                id="sec_001",
                severity="critical",
                title="Negative confidence",
                description="Issue with negative confidence",
                evidence="Evidence",
                confidence_score=-1.0,  # Negative - uses fallback
            )
        ]

        assessment = await reviewer._generate_final_assessment()

        # Should use fallback 0.50, which is below 0.60 threshold
        assert assessment.total_findings == 0

    @pytest.mark.asyncio
    async def test_confidence_greater_than_1_0(self):
        """Verify confidence > 1.0 is still valid (no upper bound enforced)."""
        orchestrator = Mock(spec=object)
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator, session_id="test-session", confidence_threshold=0.80
        )

        # Create finding with confidence > 1.0
        reviewer.findings = [
            SecurityFinding(
                id="sec_001",
                severity="critical",
                title="High confidence",
                description="Issue with high confidence",
                evidence="Evidence",
                confidence_score=1.5,  # > 1.0 but valid number - should be included
            )
        ]

        assessment = await reviewer._generate_final_assessment()

        # 1.5 >= 0.80, so finding should be included
        assert assessment.total_findings == 1
        assert assessment.findings[0].id == "sec_001"


class TestConfidenceLoggedWithFindings:
    """Test that confidence metadata appears in logs."""

    @pytest.mark.asyncio
    async def test_confidence_logged_for_each_finding(self, caplog):
        """Verify each finding's confidence is logged with threshold pass/fail status."""
        orchestrator = Mock(spec=object)
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator, session_id="test-session", confidence_threshold=0.60
        )

        # Create findings with varying confidence
        reviewer.findings = [
            SecurityFinding(
                id="sec_001",
                severity="critical",
                title="Critical issue",
                description="Critical",
                evidence="Evidence",
                confidence_score=0.90,  # Above threshold
            ),
            SecurityFinding(
                id="sec_002",
                severity="high",
                title="High issue",
                description="High",
                evidence="Evidence",
                confidence_score=0.40,  # Below threshold
            ),
        ]

        # Capture logs
        with caplog.at_level(logging.INFO):
            assessment = await reviewer._generate_final_assessment()

        # Verify confidence filter logs exist
        confidence_logs = [
            record for record in caplog.records if "[CONFIDENCE_FILTER]" in record.message
        ]

        assert len(confidence_logs) == 2

        # Verify log entries contain expected metadata
        log_messages = [log.message for log in confidence_logs]
        assert any("sec_001" in msg for msg in log_messages)
        assert any("sec_002" in msg for msg in log_messages)
        assert any("0.9" in msg for msg in log_messages)
        assert any("0.4" in msg for msg in log_messages)
        assert any("passed=yes" in msg for msg in log_messages)
        assert any("passed=no" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_filter_summary_logged(self, caplog):
        """Verify summary of filtered findings is logged."""
        orchestrator = Mock(spec=object)
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator, session_id="test-session", confidence_threshold=0.60
        )

        # Create 3 findings, 2 below threshold
        reviewer.findings = [
            SecurityFinding(
                id="sec_001",
                severity="critical",
                title="Critical",
                description="Critical",
                evidence="Evidence",
                confidence_score=0.90,
            ),
            SecurityFinding(
                id="sec_002",
                severity="high",
                title="High",
                description="High",
                evidence="Evidence",
                confidence_score=0.40,
            ),
            SecurityFinding(
                id="sec_003",
                severity="medium",
                title="Medium",
                description="Medium",
                evidence="Evidence",
                confidence_score=0.30,
            ),
        ]

        with caplog.at_level(logging.INFO):
            await reviewer._generate_final_assessment()

        # Verify filter summary log
        filter_logs = [
            record
            for record in caplog.records
            if "Filtered out" in record.message and "below confidence threshold" in record.message
        ]

        assert len(filter_logs) >= 1
        assert "Filtered out 2 findings below confidence threshold" in filter_logs[0].message


class TestThresholdConfigurable:
    """Test that threshold can be configured."""

    @pytest.mark.asyncio
    async def test_custom_threshold_used(self):
        """Verify custom threshold is used instead of default."""
        orchestrator = Mock(spec=object)
        custom_threshold = 0.85
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator,
            session_id="test-session",
            confidence_threshold=custom_threshold,
        )

        assert reviewer.confidence_threshold == custom_threshold

        # Create findings - only 0.90 should pass
        reviewer.findings = [
            SecurityFinding(
                id="sec_001",
                severity="critical",
                title="High confidence",
                description="High",
                evidence="Evidence",
                confidence_score=0.90,  # Passes 0.85
            ),
            SecurityFinding(
                id="sec_002",
                severity="high",
                title="Medium confidence",
                description="Medium",
                evidence="Evidence",
                confidence_score=0.80,  # Fails 0.85
            ),
        ]

        assessment = await reviewer._generate_final_assessment()

        # Only sec_001 should pass threshold
        assert assessment.total_findings == 1
        assert assessment.findings[0].id == "sec_001"

    @pytest.mark.asyncio
    async def test_zero_threshold_includes_all(self):
        """Verify threshold of 0.0 includes all findings."""
        orchestrator = Mock(spec=object)
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator,
            session_id="test-session",
            confidence_threshold=0.0,
        )

        # Create findings with various confidences
        reviewer.findings = [
            SecurityFinding(
                id="sec_001",
                severity="critical",
                title="Lowest",
                description="Low",
                evidence="Evidence",
                confidence_score=0.01,
            ),
            SecurityFinding(
                id="sec_002",
                severity="high",
                title="Medium",
                description="Medium",
                evidence="Evidence",
                confidence_score=0.50,
            ),
            SecurityFinding(
                id="sec_003",
                severity="medium",
                title="Highest",
                description="High",
                evidence="Evidence",
                confidence_score=0.99,
            ),
        ]

        assessment = await reviewer._generate_final_assessment()

        # All findings should be included
        assert assessment.total_findings == 3

    @pytest.mark.asyncio
    async def test_threshold_1_0_filters_most(self):
        """Verify threshold of 1.0 filters out all findings below 1.0."""
        orchestrator = Mock(spec=object)
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator,
            session_id="test-session",
            confidence_threshold=1.0,
        )

        # Create findings - none reach 1.0
        reviewer.findings = [
            SecurityFinding(
                id="sec_001",
                severity="critical",
                title="High",
                description="High",
                evidence="Evidence",
                confidence_score=0.99,
            ),
            SecurityFinding(
                id="sec_002",
                severity="high",
                title="Medium",
                description="Medium",
                evidence="Evidence",
                confidence_score=0.50,
            ),
        ]

        assessment = await reviewer._generate_final_assessment()

        # No findings should pass threshold
        assert assessment.total_findings == 0
