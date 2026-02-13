"""Example workflow demonstrating REACT + Thinking framework.

This example shows a complete workflow execution with:
- REACT pattern integration (Reason → Act → Observe cycles)
- Dynamic thinking that reflects actual work
- Evidence references to concrete artifacts
- Console and JSON logging

Run this example:
    python -m dawn_kestrel.workflow.example
    # or
    python dawn_kestrel/workflow/example.py
"""

from dawn_kestrel.workflow.fsm import run_workflow_fsm
from dawn_kestrel.workflow.loggers import ConsoleLogger, JsonLogger
from typing import Optional, Any


def run_example(changed_files: Optional[list[str]] = None) -> Any:
    """Run the example workflow.

    Args:
        changed_files: List of changed files (default: sample files)

    Returns:
        StructuredContext with complete workflow trace
    """
    if changed_files is None:
        changed_files = [
            "src/main.py",
            "src/auth.py",
            "src/database.py",
            "tests/test_main.py",
            "README.md",
        ]

    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 12 + "REACT + Thinking Framework Example" + " " * 12 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    print(f"Processing {len(changed_files)} changed files:")
    for i, file in enumerate(changed_files, 1):
        print(f"  {i}. {file}")
    print()

    # Run workflow FSM with REACT tracing
    ctx = run_workflow_fsm(changed_files)

    # Display console output
    ConsoleLogger.log_log(ctx.log)

    # Export JSON
    json_output = JsonLogger.log(ctx.log, indent=2)

    # Show JSON preview
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "JSON Export Preview" + " " * 17 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    lines = json_output.split("\n")
    for line in lines[:30]:
        print(line)
    if len(lines) > 30:
        print(f"... ({len(lines) - 30} more lines)")

    return ctx


def demonstrate_git_commit_thinking() -> None:
    """Demonstrate how thinking traces can be used for git commits.

    Shows how the structured thinking from the workflow can be
    converted into a meaningful commit message.
    """
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 13 + "Git Commit Integration" + " " * 19 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    print("The thinking traces captured by this framework can be used for:")
    print()
    print("  1. Git Commit Messages:")
    print("     • Extract decision summaries from each frame")
    print("     • Use evidence references to cite changed files")
    print("     • Include confidence levels for transparency")
    print()
    print("  2. Agent Memory:")
    print("     • Store full JSON traces for future reference")
    print("     • Enable reproducible decision auditing")
    print("     • Support retrospective analysis")
    print()
    print("  3. CI/CD Integration:")
    print("     • Upload JSON traces as build artifacts")
    print("     • Enable post-mortem debugging")
    print("     • Support automated review workflows")
    print()


def main() -> None:
    """Main entry point for the example."""
    print()
    print("=" * 60)
    print("REACT-Enhanced Workflow Framework")
    print("=" * 60)
    print()
    print("This example demonstrates:")
    print("  • REACT pattern: Reason → Act → Observe")
    print("  • Dynamic thinking (not static strings)")
    print("  • Evidence references (file paths, tool outputs)")
    print("  • Console and JSON logging")
    print()
    print("=" * 60)
    print()

    # Run example with default files
    ctx = run_example()

    # Show integration examples
    demonstrate_git_commit_thinking()

    # Final statistics
    print()
    print("=" * 60)
    print("Final Statistics")
    print("=" * 60)
    print()
    print(f"Total states processed: {ctx.log.frame_count}")
    print(f"Todos created: {ctx.todo_count}")
    print(f"Subagent results: {len(ctx.subagent_results)}")
    print(f"Evaluation verdict: {ctx.evaluation.get('verdict')}")
    print(f"Confidence: {ctx.evaluation.get('confidence'):.2f}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
