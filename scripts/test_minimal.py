"""
Minimal CLI for AI interactions without complex dependencies.

For testing - will be replaced with full version.
"""

import sys
import os


def run_command():
    """Run a message (minimal version for testing)"""
    message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello"
    
    print(f"Processing: {message}")
    print(f"API Key: {os.getenv('OPENCODE_PYTHON_ANTHROPIC_API_KEY', 'not set')}")
    print(f"Provider: {os.getenv('OPENCODE_PYTHON_PROVIDER', 'anthropic')}")
    
    return 0


if __name__ == "__main__":
    sys.exit(run_command())
