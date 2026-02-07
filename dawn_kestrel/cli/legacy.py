"""Legacy CLI entrypoint wrappers with deprecation notices."""

from __future__ import annotations

import sys
from typing import Any, cast

import click  # type: ignore[import-not-found]


def _warn(legacy_name: str, replacement: str) -> None:
    if replacement:
        target = f"dawn-kestrel {replacement}"
    else:
        target = "dawn-kestrel"

    click.echo(
        f"Deprecation warning: '{legacy_name}' is deprecated and will be removed in a future release. "
        f"Use '{target}' instead.",
        err=True,
    )


def parkcode() -> None:
    """Backward-compatible wrapper for the main CLI entrypoint."""
    from dawn_kestrel.cli.main import cli

    _warn("parkcode", "")
    cast(Any, cli).main(args=sys.argv[1:], prog_name="dawn-kestrel", standalone_mode=True)


def opencode_review() -> None:
    """Backward-compatible wrapper for the review command."""
    from dawn_kestrel.cli.main import cli

    _warn("opencode-review", "review")
    cast(Any, cli).main(
        args=["review", *sys.argv[1:]],
        prog_name="dawn-kestrel",
        standalone_mode=True,
    )


def opencode_review_generate_docs() -> None:
    """Backward-compatible wrapper for review docs generation."""
    from dawn_kestrel.cli.main import cli

    _warn("opencode-review-generate-docs", "docs")
    cast(Any, cli).main(
        args=["docs", *sys.argv[1:]], prog_name="dawn-kestrel", standalone_mode=True
    )
