"""Tests for structured logging and secret redaction in FSM-based security review.

These tests verify:
- Dedup skip logs include finding ID and reason
- Validation reject logs include finding ID and reason
- Secret redaction works correctly
- Log format standardization
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from dawn_kestrel.agents.review.utils.redaction import (
    redact_secrets,
    redact_dict,
    redact_list,
    format_log_with_redaction,
)
from dawn_kestrel.agents.review.orchestrator import PRReviewOrchestrator
from dawn_kestrel.agents.review.contracts import Finding


# =============================================================================
# Secret Redaction Tests
# =============================================================================


def test_secret_redaction_aws_keys():
    """Verify AWS access keys are redacted."""
    text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
    result = redact_secrets(text)
    assert "[REDACTED]" in result
    assert "AKIAIOSFODNN7EXAMPLE" not in result


def test_secret_redaction_github_tokens():
    """Verify GitHub tokens are redacted."""
    text = "ghp_1234567890abcdefghijklmnopqrstuvwxyz1234"
    result = redact_secrets(text)
    assert "[REDACTED]" in result
    assert "ghp_" not in result


def test_secret_redaction_jwt_tokens():
    """Verify JWT tokens are redacted."""
    text = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    result = redact_secrets(text)
    assert "[REDACTED]" in result
    assert "eyJ" not in result


def test_secret_redaction_passwords():
    """Verify passwords are redacted."""
    text = "password=mypassword123"
    result = redact_secrets(text)
    assert "[REDACTED]" in result
    assert "mypassword123" not in result


def test_secret_redaction_bearer_tokens():
    """Verify bearer tokens are redacted."""
    text = "Authorization: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    result = redact_secrets(text)
    assert "[REDACTED]" in result
    assert "bearer" not in result or "bearer" not in result.lower()


def test_secret_redaction_private_keys():
    """Verify private keys are redacted."""
    text = "-----BEGIN RSA PRIVATE KEY-----"
    result = redact_secrets(text)
    assert "[REDACTED]" in result
    assert "BEGIN RSA PRIVATE KEY" not in result


def test_secret_redaction_slack_tokens():
    """Verify Slack tokens are redacted."""
    text = "xoxb-TEST_FAKE_TOKEN_DO_NOT_USE"
    result = redact_secrets(text)
    assert "[REDACTED]" in result
    assert "xoxb-" not in result


def test_secret_redaction_preserves_safe_text():
    """Verify safe text is not redacted."""
    text = "This is safe text with no secrets."
    result = redact_secrets(text)
    assert result == text


def test_redact_dict_sensitive_keys():
    """Verify sensitive dict keys are redacted."""
    data = {
        "username": "john",
        "password": "secret123",
        "email": "john@example.com",
        "api_key": "key12345678901234567890",
    }
    result = redact_dict(data)
    assert result["username"] == "john"
    assert result["password"] == "[REDACTED]"
    assert result["email"] == "john@example.com"
    assert result["api_key"] == "[REDACTED]"


def test_redact_dict_nested():
    """Verify nested dicts are redacted."""
    data = {
        "credentials": {
            "token": "secret_token",
            "user": "john",
        },
    }
    result = redact_dict(data)
    assert result["credentials"]["token"] == "[REDACTED]"
    assert result["credentials"]["user"] == "john"


def test_redact_list():
    """Verify lists are redacted."""
    data = ["safe text", "AKIAIOSFODNN7EXAMPLE", "another safe text"]
    result = redact_list(data)
    assert result[0] == "safe text"
    assert result[1] == "[REDACTED]"
    assert result[2] == "another safe text"


# =============================================================================
# Log Format Standardization Tests
# =============================================================================


def test_log_format_with_redaction_basic():
    """Verify basic log format with redaction."""
    message = format_log_with_redaction(
        message="Test message",
    )
    assert "Test message" in message
    assert " | " not in message  # No extra fields


def test_log_format_with_finding_id():
    """Verify log format with finding ID."""
    message = format_log_with_redaction(
        message="Test message",
        finding_id="SEC-001",
    )
    assert "Test message" in message
    assert "finding_id=SEC-001" in message


def test_log_format_with_task_id():
    """Verify log format with task ID."""
    message = format_log_with_redaction(
        message="Test message",
        task_id="task_001",
    )
    assert "Test message" in message
    assert "task_id=task_001" in message


def test_log_format_with_reason():
    """Verify log format with reason."""
    message = format_log_with_redaction(
        message="Test message",
        reason="This is the reason",
    )
    assert "Test message" in message
    assert "reason=This is the reason" in message


def test_log_format_with_reason_redaction():
    """Verify reason is redacted."""
    message = format_log_with_redaction(
        message="Test message",
        reason="password=secret123",
    )
    assert "Test message" in message
    assert "reason=" in message
    assert "secret123" not in message
    assert "[REDACTED]" in message


def test_log_format_with_kwargs():
    """Verify log format with additional kwargs."""
    message = format_log_with_redaction(
        message="Test message",
        severity="high",
        count=5,
    )
    assert "Test message" in message
    assert "severity=high" in message
    assert "count=5" in message


def test_log_format_complete():
    """Verify complete log format with all fields."""
    message = format_log_with_redaction(
        message="[DEDEDUPE] Skipping duplicate finding",
        finding_id="SEC-001",
        reason="Duplicate finding",
        severity="high",
    )
    assert "[DEDEDUPE] Skipping duplicate finding" in message
    assert "finding_id=SEC-001" in message
    assert "reason=Duplicate finding" in message
    assert "severity=high" in message
    assert " | " in message  # Should have separators


# =============================================================================
# Dedup Skip Logging Tests
# =============================================================================


def test_dedup_skip_log_includes_metadata():
    """Verify dedup skip logs include finding ID and reason."""
    # Create mock findings with duplicates
    finding1 = Finding(
        id="SEC-001",
        title="SQL injection risk",
        severity="high",
        confidence=0.9,
        owner="security",
        estimate="1h",
        evidence="SELECT * FROM users WHERE id = user_id",
        risk="Injection",
        recommendation="Use parameterized queries",
        file_path="api/users.py",
    )
    finding2 = Finding(
        id="SEC-001",  # Duplicate ID
        title="SQL injection risk",  # Duplicate title
        severity="high",  # Duplicate severity
        confidence=0.8,
        owner="security",
        estimate="30m",
        evidence="SELECT * FROM users WHERE id = user_id",
        risk="Injection",
        recommendation="Use parameterized queries",
        file_path="api/users.py",
    )
    finding3 = Finding(
        id="SEC-002",
        title="XSS vulnerability",
        severity="high",
        confidence=0.85,
        owner="security",
        estimate="45m",
        evidence="return f'<div>{user_input}</div>'",
        risk="XSS",
        recommendation="Use template escaping",
        file_path="views.py",
    )

    # Capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger("dawn_kestrel.agents.review.orchestrator")
    logger.addHandler(handler)

    # Test dedup with logging
    orchestrator = PRReviewOrchestrator(subagents=[])
    unique_findings = orchestrator.dedupe_findings([finding1, finding2, finding3])

    # Verify: Should have 2 unique findings (SEC-001 and SEC-002)
    assert len(unique_findings) == 2

    # Verify log output
    log_output = log_stream.getvalue()
    assert "[DEDEDUPE]" in log_output
    assert "Skipping duplicate finding" in log_output
    assert "finding_id=SEC-001" in log_output
    assert "Duplicate finding" in log_output or "title=SQL injection risk" in log_output

    # Cleanup
    logger.removeHandler(handler)


# =============================================================================
# Validation Reject Logging Tests
# =============================================================================


def test_validation_reject_log_includes_metadata(caplog):
    """Verify validation reject logs include structured metadata."""
    import pydantic as pd

    # Create a JSON response that will fail validation
    invalid_json = """
    {
        "agent": "security",
        "summary": "Invalid response",
        "severity": "critical",
        "scope": {
            "relevant_files": ["test.py"],
            "ignored_files": [],
            "reasoning": "Test"
        },
        "findings": [
            {
                "id": "SEC-001",
                "title": "Test",
                "invalid_field": "This should cause validation error"
            }
        ]
    }
    """

    with caplog.at_level(logging.ERROR):
        try:
            # This will trigger a ValidationError
            from dawn_kestrel.agents.review.contracts import ReviewOutput

            ReviewOutput.model_validate_json(invalid_json)
        except pd.ValidationError:
            pass

    # Verify structured validation reject logging
    error_logs = [record for record in caplog.records if record.levelname == "ERROR"]
    assert len(error_logs) > 0

    # Check for structured log format
    log_message = str(error_logs[0].message)
    # Should contain structured validation reject indicators
    assert "VALIDATION_REJECT" in log_message or "validation error" in log_message.lower()


# =============================================================================
# Integration Tests
# =============================================================================


def test_log_format_standardization():
    """Verify all logs follow structured format."""
    # Test various log formats
    test_cases = [
        {
            "message": "[ITERATION_LIFECYCLE] Starting iteration 1",
            "expected_parts": ["ITERATION_LIFECYCLE", "iteration_number=1"],
        },
        {
            "message": "[TASK_SKIP] Skipping task",
            "expected_parts": ["TASK_SKIP", "task_id"],
        },
        {
            "message": "[DEDEDUPE] Skipping duplicate finding",
            "expected_parts": ["DEDEDUPE", "finding_id"],
        },
    ]

    for case in test_cases:
        message = format_log_with_redaction(
            message=case["message"],
        )
        # Verify message contains the base message
        assert case["message"] in message

        # Verify expected parts are present (if provided)
        for part in case["expected_parts"]:
            assert part in message


def test_redaction_does_not_break_log_structure():
    """Verify redaction maintains log structure."""
    message = format_log_with_redaction(
        message="[TEST] Finding AWS access key",
        finding_id="SEC-001",
        reason="Found AKIAIOSFODNN7EXAMPLE in code",
    )
    # Verify message is structured
    assert " | " in message

    # Verify secrets are redacted
    assert "[REDACTED]" in message

    # Verify finding_id is preserved (not redacted)
    assert "finding_id=SEC-001" in message or "SEC-001" in message

    # Verify reason text is redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in message
