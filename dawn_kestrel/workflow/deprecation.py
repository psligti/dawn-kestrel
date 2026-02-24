"""Deprecation utilities for workflow state transitions.

This module provides soft deprecation warnings for legacy state names
to guide users toward newer, more semantic state naming conventions.

Primary Use Case:
    The 'plan' state is being deprecated in favor of the 'reason' state
    to better align with the REACT pattern (Reason-Act-Observe).

Usage:
    from dawn_kestrel.workflow.deprecation import deprecate_plan_state

    # In code that encounters 'plan' state usage:
    if state == "plan":
        deprecate_plan_state()
        # Continue with backward-compatible behavior
"""

from __future__ import annotations

import warnings

PLAN_STATE_DEPRECATED_MSG = (
    "Use 'reason' state instead of 'plan'. "
    "The 'plan' state is deprecated and will be removed in a future version. "
    "The 'reason' state aligns with the REACT pattern (Reason-Act-Observe)."
)
"""Migration guidance message for the deprecated 'plan' state."""


def deprecate_plan_state() -> None:
    """Emit a deprecation warning for the 'plan' state.

    This function emits a DeprecationWarning when code uses the legacy
    'plan' state instead of the new 'reason' state. The warning provides
    migration guidance to help users update their code.

    The function does NOT raise an exception - it only emits a warning
    to allow backward-compatible operation while alerting users to the
    upcoming change.

    Example:
        >>> deprecate_plan_state()  # Emits DeprecationWarning
        >>> # Code continues normally

    Note:
        Uses stacklevel=2 to ensure the warning points to the caller
        of this function, not to this internal implementation.
    """
    warnings.warn(
        PLAN_STATE_DEPRECATED_MSG,
        category=DeprecationWarning,
        stacklevel=2,
    )
