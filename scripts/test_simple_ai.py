"""
AI Session runner - simplified for testing.

Minimal version without complex imports for basic testing.
"""

import os


class SimpleAISession:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "test-key")
        self.model = "claude-sonnet-4"
    
    def test_basic_stream(self):
        print(f"[green]Testing {self.model} stream[/green]")
        print(f"[dim]API Key: {self.api_key[:8]}***[/dim]")
        print()
        yield "START"
        yield "Thinking..."
        yield "Hello, this is a basic test stream."
        yield "STOP"
        print(f"[green]Stream complete[/green]")


def run_test():
    session = SimpleAISession()
    for event in session.test_basic_stream():
        print(f"  [cyan]→ {event}[/cyan]")


if __name__ == "__main__":
    run_test()
