"""Unit tests for workflow deprecation module."""

import warnings

import pytest

from dawn_kestrel.workflow.deprecation import (
    PLAN_STATE_DEPRECATED_MSG,
    deprecate_plan_state,
)


class TestDeprecationWarning:
    """Tests for plan state deprecation warning."""

    def test_plan_deprecation_warning_emitted(self):
        """Test that deprecate_plan_state() emits DeprecationWarning."""
        with pytest.warns(DeprecationWarning) as record:
            deprecate_plan_state()

        assert len(record) == 1
        assert "plan" in str(record[0].message).lower()
        assert "reason" in str(record[0].message).lower()

    def test_plan_deprecation_message_contains_migration_guidance(self):
        """Test that deprecation message includes migration guidance."""
        with pytest.warns(DeprecationWarning) as record:
            deprecate_plan_state()

        message = str(record[0].message)
        assert "'reason'" in message
        assert "'plan'" in message
        assert "deprecated" in message.lower()

    def test_plan_deprecation_message_constant_exists(self):
        """Test that PLAN_STATE_DEPRECATED_MSG constant has correct content."""
        assert "reason" in PLAN_STATE_DEPRECATED_MSG.lower()
        assert "plan" in PLAN_STATE_DEPRECATED_MSG.lower()
        assert "deprecated" in PLAN_STATE_DEPRECATED_MSG.lower()
        assert "removed" in PLAN_STATE_DEPRECATED_MSG.lower()

    def test_deprecate_plan_state_does_not_raise(self):
        """Test that deprecate_plan_state() does not raise an exception."""
        # This should emit a warning, not raise
        try:
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                deprecate_plan_state()
        except Exception as e:
            pytest.fail(f"deprecate_plan_state() raised an exception: {e}")

    def test_deprecate_plan_state_stacklevel_correct(self):
        """Test that stacklevel=2 points to caller, not internal function."""
        with pytest.warns(DeprecationWarning) as record:
            deprecate_plan_state()

        # With stacklevel=2, the warning should point to this test function
        # rather than the deprecate_plan_state function itself
        assert record[0].filename.endswith("test_deprecation.py")
