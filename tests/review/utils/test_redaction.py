"""Tests for secret redaction utilities."""

from __future__ import annotations

import pytest

from dawn_kestrel.agents.review.utils.redaction import (
    REDACTED,
    format_log_with_redaction,
    redact_dict,
    redact_list,
    redact_secrets,
)


class TestRedactSecrets:
    """Tests for redact_secrets function."""

    def test_redact_aws_access_key(self):
        """AWS access keys are redacted."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        result = redact_secrets(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert REDACTED in result

    def test_redact_aws_access_key_in_context(self):
        """AWS keys are redacted in context."""
        text = "Set AWS_ACCESS_KEY_ID to AKIAIOSFODNN7EXAMPLE for production"
        result = redact_secrets(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert REDACTED in result

    def test_redact_github_personal_token(self):
        """GitHub personal access tokens are redacted."""
        text = "ghp_1234567890abcdefghijklmnopqrstuvwxyz1234"
        result = redact_secrets(text)
        assert "ghp_" not in result
        assert REDACTED in result

    def test_redact_github_oauth_token(self):
        """GitHub OAuth tokens are redacted."""
        text = "gho_1234567890abcdefghijklmnopqrstuvwxyz1234"
        result = redact_secrets(text)
        assert "gho_" not in result
        assert REDACTED in result

    def test_redact_github_app_token(self):
        """GitHub app tokens are redacted."""
        text = "ghu_1234567890abcdefghijklmnopqrstuvwxyz1234"
        result = redact_secrets(text)
        assert "ghu_" not in result
        assert REDACTED in result

    def test_redact_github_refresh_token(self):
        """GitHub refresh tokens are redacted."""
        text = "ghr_1234567890abcdefghijklmnopqrstuvwxyz1234"
        result = redact_secrets(text)
        assert "ghr_" not in result
        assert REDACTED in result

    def test_redact_openai_api_key(self):
        """OpenAI API keys are redacted."""
        text = "api_key = 'sk-1234567890abcdefghijklmnop'"
        result = redact_secrets(text)
        assert "sk-1234567890abcdefghijklmnop" not in result
        assert REDACTED in result

    def test_redact_jwt_token(self):
        """JWT tokens are redacted."""
        text = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = redact_secrets(text)
        assert "eyJ" not in result
        assert REDACTED in result

    def test_redact_password_pattern(self):
        """Password patterns are redacted."""
        text = "password=mypassword123"
        result = redact_secrets(text)
        assert "mypassword123" not in result
        assert REDACTED in result

    def test_redact_password_with_spaces(self):
        """Password with spaces around equals is redacted."""
        text = "password = 'mysecretvalue'"
        result = redact_secrets(text)
        assert "mysecretvalue" not in result
        assert REDACTED in result

    def test_redact_bearer_token(self):
        """Bearer tokens are redacted."""
        text = "Authorization: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = redact_secrets(text)
        assert REDACTED in result

    def test_redact_private_key_marker(self):
        """Private key markers are redacted."""
        text = "-----BEGIN RSA PRIVATE KEY-----"
        result = redact_secrets(text)
        assert "BEGIN RSA PRIVATE KEY" not in result
        assert REDACTED in result

    def test_redact_slack_token(self):
        """Slack tokens are redacted."""
        text = "xoxb-FAKEEXAMPLE-FAKEEXAMPLE-FAKEEXAMPLEFAKEEXAMPLEFA"
        result = redact_secrets(text)
        assert "xoxb-" not in result
        assert REDACTED in result

    def test_redact_slack_webhook(self):
        """Slack webhooks are redacted."""
        text = "https://hooks.example-fake.org/FAKE/FAKE/FAKEEXAMPLEFAKEEXAMPLEFAKEEX"
        result = redact_secrets(text)
        assert "hooks.example-fake.org" not in result or REDACTED in result

    def test_redact_payment_provider_key(self):
        """Payment provider keys are redacted."""
        # Use generic pattern that won't trigger secret scanners
        text = "payment_key_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        result = redact_secrets(text)
        assert REDACTED in result

    def test_redact_test_api_key(self):
        """Test API keys are redacted."""
        # Use generic pattern
        text = "test_api_key_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        result = redact_secrets(text)
        assert REDACTED in result

    def test_preserves_safe_text(self):
        """Safe text without secrets is unchanged."""
        text = "This is safe text with no secrets."
        result = redact_secrets(text)
        assert result == text

    def test_preserves_normal_code(self):
        """Normal code is unchanged."""
        text = "def hello():\n    return 'world'"
        result = redact_secrets(text)
        assert result == text

    def test_empty_string(self):
        """Empty string returns empty."""
        result = redact_secrets("")
        assert result == ""

    def test_multiple_secrets_in_one_line(self):
        """Multiple secrets in same line are redacted."""
        text = "api_key='sk-1234567890abcdef' password='secretvalue123'"
        result = redact_secrets(text)
        assert "sk-1234567890abcdef" not in result
        assert "secretvalue123" not in result

    def test_redaction_is_stable(self):
        """Redacting twice gives same result."""
        text = "api_key = 'sk-1234567890abcdef1234'"
        result1 = redact_secrets(text)
        result2 = redact_secrets(result1)
        assert result1 == result2

    def test_case_insensitive_password(self):
        """Password pattern is case insensitive."""
        text = "PASSWORD=secret123"
        result = redact_secrets(text)
        assert "secret123" not in result

    def test_case_insensitive_api_key(self):
        """API key pattern is case insensitive."""
        text = "API_KEY=myapikeyvalue12345678"
        result = redact_secrets(text)
        assert REDACTED in result


class TestRedactDict:
    """Tests for redact_dict function."""

    def test_redacts_password_key(self):
        """Password values are redacted."""
        data = {"username": "john", "password": "secret123"}
        result = redact_dict(data)
        assert result["username"] == "john"
        assert result["password"] == REDACTED

    def test_redacts_api_key_key(self):
        """API key values are redacted."""
        data = {"api_key": "key12345678901234567890", "name": "test"}
        result = redact_dict(data)
        assert result["api_key"] == REDACTED
        assert result["name"] == "test"

    def test_redacts_token_key(self):
        """Token values are redacted."""
        data = {"token": "secret_token_value", "id": 123}
        result = redact_dict(data)
        assert result["token"] == REDACTED
        assert result["id"] == 123

    def test_redacts_nested_dict(self):
        """Nested dicts are processed recursively."""
        data = {"credentials": {"token": "secret", "user": "john"}}
        result = redact_dict(data)
        assert result["credentials"]["token"] == REDACTED
        assert result["credentials"]["user"] == "john"

    def test_redacts_deeply_nested(self):
        """Deeply nested dicts are processed."""
        data = {"level1": {"level2": {"level3": {"secret": "hidden"}}}}
        result = redact_dict(data)
        assert result["level1"]["level2"]["level3"]["secret"] == REDACTED

    def test_preserves_non_sensitive_values(self):
        """Non-sensitive values are preserved."""
        data = {"name": "John", "email": "john@example.com", "count": 42}
        result = redact_dict(data)
        assert result["name"] == "John"
        assert result["email"] == "john@example.com"
        assert result["count"] == 42

    def test_handles_list_values(self):
        """Lists within dicts are processed."""
        data = {"items": ["safe", "AKIAIOSFODNN7EXAMPLE", "also_safe"]}
        result = redact_dict(data)
        assert result["items"][0] == "safe"
        assert result["items"][1] == REDACTED
        assert result["items"][2] == "also_safe"

    def test_handles_none_values(self):
        """None values are preserved."""
        data = {"value": None, "password": None}
        result = redact_dict(data)
        assert result["value"] is None
        assert result["password"] == REDACTED

    def test_handles_boolean_values(self):
        """Boolean values are preserved."""
        data = {"enabled": True, "disabled": False}
        result = redact_dict(data)
        assert result["enabled"] is True
        assert result["disabled"] is False

    def test_handles_numeric_values(self):
        """Numeric values are preserved."""
        data = {"count": 42, "price": 19.99, "password": "secret"}
        result = redact_dict(data)
        assert result["count"] == 42
        assert result["price"] == 19.99
        assert result["password"] == REDACTED

    def test_empty_dict(self):
        """Empty dict returns empty dict."""
        result = redact_dict({})
        assert result == {}

    def test_returns_copy(self):
        """Returns a new dict, not modifying original."""
        data = {"password": "secret"}
        result = redact_dict(data)
        assert data["password"] == "secret"
        assert result["password"] == REDACTED

    def test_case_insensitive_keys(self):
        """Key matching is case insensitive."""
        data = {"PASSWORD": "secret", "API_KEY": "key", "Token": "value"}
        result = redact_dict(data)
        assert result["PASSWORD"] == REDACTED
        assert result["API_KEY"] == REDACTED
        assert result["Token"] == REDACTED


class TestRedactList:
    """Tests for redact_list function."""

    def test_redacts_secrets_in_strings(self):
        """Secrets in string items are redacted."""
        data = ["safe text", "AKIAIOSFODNN7EXAMPLE", "another safe text"]
        result = redact_list(data)
        assert result[0] == "safe text"
        assert result[1] == REDACTED
        assert result[2] == "another safe text"

    def test_handles_nested_dicts(self):
        """Nested dicts in lists are redacted."""
        data = [{"password": "secret", "name": "john"}]
        result = redact_list(data)
        assert result[0]["password"] == REDACTED
        assert result[0]["name"] == "john"

    def test_handles_nested_lists(self):
        """Nested lists are processed recursively."""
        data = [["safe", "AKIAIOSFODNN7EXAMPLE"], ["another"]]
        result = redact_list(data)
        assert result[0][0] == "safe"
        assert result[0][1] == REDACTED

    def test_preserves_non_string_items(self):
        """Non-string items are preserved."""
        data = [1, 2.5, True, None, "AKIAIOSFODNN7EXAMPLE"]
        result = redact_list(data)
        assert result[0] == 1
        assert result[1] == 2.5
        assert result[2] is True
        assert result[3] is None
        assert result[4] == REDACTED

    def test_empty_list(self):
        """Empty list returns empty list."""
        result = redact_list([])
        assert result == []

    def test_returns_copy(self):
        """Returns a new list, not modifying original."""
        data = ["AKIAIOSFODNN7EXAMPLE"]
        result = redact_list(data)
        assert data[0] == "AKIAIOSFODNN7EXAMPLE"
        assert result[0] == REDACTED


class TestFormatLogWithRedaction:
    """Tests for format_log_with_redaction function."""

    def test_basic_message(self):
        """Basic message without kwargs is returned as-is."""
        message = format_log_with_redaction("Test message")
        assert "Test message" in message
        assert " | " not in message

    def test_with_level(self):
        """Level is prepended to message."""
        message = format_log_with_redaction("Test message", level="INFO")
        assert "[INFO]" in message
        assert "Test message" in message

    def test_with_finding_id(self):
        """Finding ID is appended as key=value."""
        message = format_log_with_redaction("Test message", finding_id="SEC-001")
        assert "Test message" in message
        assert "finding_id=SEC-001" in message

    def test_with_task_id(self):
        """Task ID is appended as key=value."""
        message = format_log_with_redaction("Test message", task_id="task_001")
        assert "Test message" in message
        assert "task_id=task_001" in message

    def test_with_reason(self):
        """Reason is appended as key=value."""
        message = format_log_with_redaction("Test message", reason="This is the reason")
        assert "Test message" in message
        assert "reason=This is the reason" in message

    def test_reason_is_redacted(self):
        """Reason containing secrets is redacted."""
        message = format_log_with_redaction("Test message", reason="password=secret123")
        assert "Test message" in message
        assert "reason=" in message
        assert "secret123" not in message
        assert REDACTED in message

    def test_with_multiple_kwargs(self):
        """Multiple kwargs are formatted correctly."""
        message = format_log_with_redaction("Test message", severity="high", count=5, enabled=True)
        assert "Test message" in message
        assert "severity=high" in message
        assert "count=5" in message
        assert "enabled=True" in message

    def test_complete_format(self):
        """Complete format with all fields."""
        message = format_log_with_redaction(
            "[DEDUP] Skipping duplicate finding",
            level="INFO",
            finding_id="SEC-001",
            reason="Duplicate finding",
            severity="high",
        )
        assert "[DEDUP] Skipping duplicate finding" in message
        assert "finding_id=SEC-001" in message
        assert "reason=Duplicate finding" in message
        assert "severity=high" in message
        assert " | " in message

    def test_dict_values_are_redacted(self):
        """Dict values in kwargs are redacted."""
        message = format_log_with_redaction("Test", config={"password": "secret", "name": "test"})
        assert REDACTED in message
        assert "secret" not in message

    def test_list_values_are_redacted(self):
        """List values in kwargs are redacted."""
        message = format_log_with_redaction("Test", items=["safe", "AKIAIOSFODNN7EXAMPLE"])
        assert REDACTED in message
        assert "AKIAIOSFODNN7EXAMPLE" not in message

    def test_empty_kwargs(self):
        """Empty kwargs still works."""
        message = format_log_with_redaction("Just a message")
        assert message == "Just a message"


class TestEdgeCases:
    """Edge case tests for redaction utilities."""

    def test_very_long_string(self):
        """Very long strings are handled efficiently."""
        text = "safe " * 10000 + "AKIAIOSFODNN7EXAMPLE" + " safe" * 10000
        result = redact_secrets(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert REDACTED in result

    def test_unicode_text(self):
        """Unicode text is handled correctly."""
        text = "密码=password123 你好 AWS=AKIAIOSFODNN7EXAMPLE"
        result = redact_secrets(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert REDACTED in result

    def test_special_regex_chars_in_text(self):
        """Special regex characters don't break matching."""
        text = "password=[special*chars?here]"
        result = redact_secrets(text)
        assert REDACTED in result

    def test_nested_list_with_dicts(self):
        """Deeply nested structures are handled."""
        data = {"level1": [{"level2": [{"password": "deep_secret", "value": "safe"}]}]}
        result = redact_dict(data)
        assert result["level1"][0]["level2"][0]["password"] == REDACTED
        assert result["level1"][0]["level2"][0]["value"] == "safe"

    def test_multiple_patterns_in_same_value(self):
        """Multiple secret patterns in same value are all redacted."""
        text = "AWS=AKIAIOSFODNN7EXAMPLE and GitHub=ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        result = redact_secrets(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "ghp_" not in result

    def test_secret_at_string_boundaries(self):
        """Secrets at string boundaries are redacted."""
        text1 = "AKIAIOSFODNN7EXAMPLE at start"
        text2 = "at end AKIAIOSFODNN7EXAMPLE"
        assert "AKIAIOSFODNN7EXAMPLE" not in redact_secrets(text1)
        assert "AKIAIOSFODNN7EXAMPLE" not in redact_secrets(text2)

    def test_partial_secret_matches_not_redacted(self):
        """Short strings that don't meet minimum length are not redacted."""
        text = "AKIA"  # Too short to be AWS key
        result = redact_secrets(text)
        assert result == text


class TestEventBusRedactionIntegration:
    """Tests for EventBus redaction of sensitive data."""

    @pytest.mark.asyncio
    async def test_event_bus_redacts_password(self):
        from dawn_kestrel.core.event_bus import EventBus, Event

        bus = EventBus()
        received_data = {}

        async def capture_callback(event: Event):
            received_data.update(event.data)

        await bus.subscribe("test.event", capture_callback)
        await bus.publish("test.event", {"username": "john", "password": "secret123"})

        assert received_data["username"] == "john"
        assert received_data["password"] == REDACTED

    @pytest.mark.asyncio
    async def test_event_bus_redacts_api_key(self):
        from dawn_kestrel.core.event_bus import EventBus, Event

        bus = EventBus()
        received_data = {}

        async def capture_callback(event: Event):
            received_data.update(event.data)

        await bus.subscribe("test.event", capture_callback)
        await bus.publish("test.event", {"api_key": "sk-1234567890abcdefghijklmnop"})

        assert received_data["api_key"] == REDACTED

    @pytest.mark.asyncio
    async def test_event_bus_redacts_nested_secrets(self):
        from dawn_kestrel.core.event_bus import EventBus, Event

        bus = EventBus()
        received_data = {}

        async def capture_callback(event: Event):
            received_data.update(event.data)

        await bus.subscribe("test.event", capture_callback)
        await bus.publish("test.event", {"config": {"token": "secret_token", "user": "john"}})

        assert received_data["config"]["token"] == REDACTED
        assert received_data["config"]["user"] == "john"

    @pytest.mark.asyncio
    async def test_event_bus_does_not_modify_original_data(self):
        from dawn_kestrel.core.event_bus import EventBus

        bus = EventBus()
        original_data = {"password": "secret123", "username": "john"}

        await bus.publish("test.event", original_data)

        assert original_data["password"] == "secret123"
        assert original_data["username"] == "john"
