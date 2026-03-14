"""Dawn Kestrel hooks for external system integration.

Hooks provide extension points for external systems to participate
in the agent execution lifecycle without coupling to internals.
"""

from __future__ import annotations

from dawn_kestrel.hooks.post_run_review_hook import PostRunReviewHook

__all__ = [
    "PostRunReviewHook",
]
