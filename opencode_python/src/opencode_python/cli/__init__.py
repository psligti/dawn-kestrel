"""OpenCode Python CLI Interface"""

try:
    from opencode_python.cli.main import cli
except ImportError as e:
    import sys
    print(
        "Error: CLI dependencies (click, rich) are not installed.\n"
        "Install with: pip install opencode-python[cli]",
        file=sys.stderr,
    )
    sys.exit(1)

__all__ = ["cli"]
