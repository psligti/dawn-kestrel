"""Secret redaction utilities for secure logging and data handling.

This module provides functions to redact sensitive information from text,
dictionaries, and lists to prevent secrets from leaking into logs.
"""

from __future__ import annotations

import re
from typing import Any

# Redaction marker
REDACTED = "[REDACTED]"


def _is_sensitive_key(key: str) -> bool:
    """Check if a key name indicates a sensitive field.

    Uses word-boundary matching to avoid false positives like
    'credentials' matching 'credential'.
    """
    key_lower = key.lower()
    sensitive_words = [
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "apikey",
        "accesskey",
        "secretkey",
        "bearer",
        "privatekey",
    ]
    if key_lower in sensitive_words:
        return True
    key_with_underscores = "_" + key_lower + "_"
    return any(
        "_" + word + "_" in key_with_underscores
        for word in ["api_key", "secret_key", "access_key", "private_key", "auth", "credential"]
    )


# Compiled regex patterns for common secrets
# Each pattern is designed to be efficient and avoid ReDoS
SECRET_PATTERNS = [
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"gh[posur]_[A-Za-z0-9]{36,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"sk_(live|test)_[A-Za-z0-9]{24,}"),
    re.compile(r"xox[baprs]-[0-9]{10,}-[0-9]{10,}-[A-Za-z0-9]{24}"),
    re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]{8,}/B[A-Z0-9]{8,}/[A-Za-z0-9]{24}"),
    re.compile(r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|access[_-]?key)\s*[=:]\s*['\"]?[A-Za-z0-9_-]{16,}['\"]?"),
    re.compile(r"(?i)password\s*[=:]\s*['\"]?[^\s'\"]{8,}['\"]?"),
    re.compile(r"(?i)(mysql|postgres|postgresql|mongodb|redis)://[^:]+:[^@]+@[^\s]+"),
    re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
    re.compile(r"-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
    re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{32,}(?![0-9a-fA-F])"),
    re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])"),
]


def redact_secrets(text: str) -> str:
    """Redact sensitive information from a text string.

    This function scans text for common secret patterns and replaces them
    with [REDACTED]. It handles:
    - AWS access keys and secret keys
    - GitHub tokens (personal, OAuth, app, refresh)
    - OpenAI API keys
    - Stripe API keys
    - Slack tokens and webhooks
    - JWT tokens
    - Bearer tokens
    - Password patterns
    - Connection strings with credentials
    - Private key markers
    - Generic hex and base64 tokens

    Args:
        text: The text to scan for secrets.

    Returns:
        The text with secrets replaced by [REDACTED].

    Examples:
        >>> redact_secrets("api_key = 'sk-1234567890abcdef1234'")
        "api_key = '[REDACTED]'"

        >>> redact_secrets("password=secret123")
        "[REDACTED]"

        >>> redact_secrets("This is safe text")
        "This is safe text"
    """
    if not text:
        return text

    result = text

    for pattern in SECRET_PATTERNS:
        result = pattern.sub(REDACTED, result)

    return result


def redact_dict(data: dict) -> dict:
    """Redact sensitive values from a dictionary.

    Creates a deep copy of the dictionary and redacts:
    1. Values for keys that match sensitive key patterns (password, token, etc.)
    2. String values that contain secret patterns

    Nested dictionaries and lists are processed recursively.

    Args:
        data: The dictionary to redact.

    Returns:
        A new dictionary with sensitive values redacted.

    Examples:
        >>> redact_dict({"password": "secret123", "name": "John"})
        {"password": "[REDACTED]", "name": "John"}

        >>> redact_dict({"config": {"api_key": "sk-abc123"}})
        {"config": {"api_key": "[REDACTED]"}}
    """
    if not isinstance(data, dict):
        return data

    result = {}

    for key, value in data.items():
        if isinstance(key, str) and _is_sensitive_key(key):
            result[key] = REDACTED
        elif isinstance(value, dict):
            # Recursively process nested dicts
            result[key] = redact_dict(value)
        elif isinstance(value, list):
            # Recursively process lists
            result[key] = redact_list(value)
        elif isinstance(value, str):
            # Redact secrets in string values
            result[key] = redact_secrets(value)
        else:
            # Keep other types as-is (numbers, booleans, None)
            result[key] = value

    return result


def redact_list(data: list) -> list:
    """Redact sensitive information from a list.

    Creates a copy of the list and redacts:
    1. String items that contain secret patterns
    2. Nested dictionaries and lists recursively

    Args:
        data: The list to redact.

    Returns:
        A new list with sensitive information redacted.

    Examples:
        >>> redact_list(["safe", "AKIAIOSFODNN7EXAMPLE", "also safe"])
        ["safe", "[REDACTED]", "also safe"]

        >>> redact_list([{"password": "secret"}])
        [{"password": "[REDACTED]"}]
    """
    if not isinstance(data, list):
        return data

    result = []

    for item in data:
        if isinstance(item, dict):
            result.append(redact_dict(item))
        elif isinstance(item, list):
            result.append(redact_list(item))
        elif isinstance(item, str):
            result.append(redact_secrets(item))
        else:
            result.append(item)

    return result


def format_log_with_redaction(
    message: str,
    *,
    level: str | None = None,
    **kwargs: Any,
) -> str:
    """Format a log message with redaction of sensitive data.

    Creates a structured log message with:
    - The main message (always first)
    - Optional level prefix
    - Additional key=value pairs from kwargs
    - All values are redacted for secrets

    Args:
        message: The main log message.
        level: Optional log level (e.g., "INFO", "ERROR").
        **kwargs: Additional key-value pairs to include in the log.

    Returns:
        A formatted log string with secrets redacted.

    Examples:
        >>> format_log_with_redaction("Test message")
        "Test message"

        >>> format_log_with_redaction("Test", finding_id="SEC-001")
        "Test | finding_id=SEC-001"

        >>> format_log_with_redaction("Test", reason="password=secret123")
        "Test | reason=password=[REDACTED]"
    """
    # Redact the main message
    redacted_message = redact_secrets(message)

    parts = [redacted_message]

    # Add level if provided
    if level:
        parts.insert(0, f"[{level}]")

    # Add kwargs as key=value pairs
    for key, value in kwargs.items():
        # Convert value to string and redact
        if isinstance(value, str):
            redacted_value = redact_secrets(value)
        elif isinstance(value, dict):
            redacted_value = str(redact_dict(value))
        elif isinstance(value, list):
            redacted_value = str(redact_list(value))
        else:
            redacted_value = str(value)

        parts.append(f"{key}={redacted_value}")

    return " | ".join(parts)


__all__ = [
    "REDACTED",
    "redact_secrets",
    "redact_dict",
    "redact_list",
    "format_log_with_redaction",
]
