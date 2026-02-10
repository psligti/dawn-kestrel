"""Secret redaction utility for secure logging.

This module provides functions to redact sensitive information from log messages,
following OWASP LLM02 logging hygiene guidance.

Redaction patterns cover:
- API keys (AWS, GCP, Azure, GitHub)
- API tokens
- Passwords and secrets
- Private keys (RSA, EC, etc.)
- Session IDs
- Authorization headers
"""

import re
from typing import Any, Dict, List, Optional


# Redaction patterns - ordered from most specific to least specific
REDACTION_PATTERNS: List[tuple[str, str]] = [
    # AWS keys
    (
        r'(?i)(?:aws_access_key_id|aws_secret_access_key)\s*=\s*[\'"]?([A-Z0-9]{20})[\'"]?',
        "AWS_ACCESS_KEY",
    ),
    (r"(?i)AKIA[0-9A-Z]{16}", "AWS_ACCESS_KEY"),
    (r"(?i)[A-Za-z0-9/+=]{40}", "AWS_SECRET_KEY"),
    # GitHub tokens
    (r"(?i)ghp_[a-zA-Z0-9]{36}", "GITHUB_TOKEN"),
    (r"(?i)gho_[a-zA-Z0-9]{36}", "GITHUB_OAUTH"),
    (r"(?i)ghu_[a-zA-Z0-9]{36}", "GITHUB_USER_TOKEN"),
    (r"(?i)ghs_[a-zA-Z0-9]{36}", "GITHUB_SERVER"),
    (r"(?i)ghr_[a-zA-Z0-9]{36}", "GITHUB_REFRESH"),
    # API keys (generic pattern)
    (r'(?i)api[_-]?key\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-]{20,})', "API_KEY"),
    (r'(?i)apikey\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-]{20,})', "API_KEY"),
    (r'(?i)client[_-]?secret\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-]{20,})', "CLIENT_SECRET"),
    # JWT tokens
    (r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", "JWT_TOKEN"),
    # Bearer tokens
    (r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}", "BEARER_TOKEN"),
    # Session IDs
    (r'(?i)session[_-]?id\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-]{20,})', "SESSION_ID"),
    # Private keys (PEM format)
    (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "PRIVATE_KEY"),
    (r"-----BEGIN\s+EC\s+PRIVATE\s+KEY-----", "PRIVATE_KEY"),
    # Authorization headers
    (r"(?i)authorization\s*:\s*(basic|bearer)\s+[a-zA-Z0-9_\-\.]+", "AUTHORIZATION"),
    # Passwords
    (r'(?i)password\s*[:=]\s*[\'"]?([^\s\'"]{8,})', "PASSWORD"),
    (r'(?i)passwd\s*[:=]\s*[\'"]?([^\s\'"]{8,})', "PASSWORD"),
    (r'(?i)secret\s*[:=]\s*[\'"]?([^\s\'"]{8,})', "SECRET"),
    # GCP keys
    (r"(?i)\"type\":\s*\"service_account\"", "GCP_SERVICE_ACCOUNT_KEY"),
    # Azure keys
    (
        r'(?i)azure[_-]?storage[_-]?account[_-]?key\s*[:=]\s*[\'"]?([a-zA-Z0-9+/=]{80,})',
        "AZURE_KEY",
    ),
    # Slack tokens
    (r"xoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{24}", "SLACK_TOKEN"),
    (r"xoxp-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{24}-[a-zA-Z0-9]{24}", "SLACK_TOKEN"),
    # Generic base64 strings (potential secrets)
    # Note: This is a conservative pattern - only match if it looks like a secret
    (
        r'(?i)\"?[a-zA-Z0-9_\-]{5,}(?:key|token|secret|password)\"?\s*[:=]\s*[\'"]?[A-Za-z0-9+/=]{32,}',
        "CREDENTIAL",
    ),
]

# Compiled regex patterns for performance
COMPILED_PATTERNS = [(re.compile(pattern), label) for pattern, label in REDACTION_PATTERNS]


def redact_secrets(text: str) -> str:
    """Redact secrets from text using predefined patterns.

    Args:
        text: Input text that may contain secrets

    Returns:
        Text with secrets replaced by [REDACTED]
    """
    result = text

    for pattern, _label in COMPILED_PATTERNS:
        # Replace all matches of the pattern with [REDACTED]
        result = pattern.sub("[REDACTED]", result)

    return result


def redact_dict(data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """Recursively redact sensitive values from a dictionary.

    Args:
        data: Dictionary that may contain sensitive values
        sensitive_keys: List of keys whose values should always be redacted
                      (defaults to common sensitive key patterns)

    Returns:
        Dictionary with sensitive values redacted
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "password",
            "passwd",
            "secret",
            "token",
            "key",
            "api_key",
            "apikey",
            "access_key",
            "private_key",
            "authorization",
            "session_id",
            "auth_token",
            "auth_key",
            "client_secret",
        ]

    result = {}

    for key, value in data.items():
        # Check if key is sensitive (case-insensitive)
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            if isinstance(value, str):
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = redact_dict(value, sensitive_keys)
            else:
                result[key] = "[REDACTED]"
        else:
            if isinstance(value, str):
                result[key] = redact_secrets(value)
            elif isinstance(value, dict):
                result[key] = redact_dict(value, sensitive_keys)
            else:
                result[key] = value

    return result


def redact_list(data: List[Any], sensitive_keys: Optional[List[str]] = None) -> List[Any]:
    """Recursively redact sensitive values from a list.

    Args:
        data: List that may contain sensitive values
        sensitive_keys: List of keys whose values should always be redacted

    Returns:
        List with sensitive values redacted
    """
    result = []

    for item in data:
        if isinstance(item, str):
            result.append(redact_secrets(item))
        elif isinstance(item, dict):
            result.append(redact_dict(item, sensitive_keys))
        elif isinstance(item, list):
            result.append(redact_list(item, sensitive_keys))
        else:
            result.append(item)

    return result


def format_log_with_redaction(
    message: str,
    finding_id: Optional[str] = None,
    task_id: Optional[str] = None,
    reason: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Format a structured log message with secret redaction.

    Args:
        message: Base log message
        finding_id: Optional finding ID for context
        task_id: Optional task ID for context
        reason: Optional reason for the event (skip, reject, etc.)
        **kwargs: Additional context to include in log

    Returns:
        Formatted log message with secrets redacted
    """
    # Build structured context
    context_parts = [message]

    if finding_id:
        context_parts.append(f"finding_id={finding_id}")

    if task_id:
        context_parts.append(f"task_id={task_id}")

    if reason:
        # Redact any secrets in the reason
        redacted_reason = redact_secrets(reason)
        context_parts.append(f"reason={redacted_reason}")

    # Add additional context with redaction
    for key, value in kwargs.items():
        if isinstance(value, str):
            redacted_value = redact_secrets(value)
        else:
            redacted_value = str(value)
        context_parts.append(f"{key}={redacted_value}")

    log_message = " | ".join(context_parts)

    return log_message
