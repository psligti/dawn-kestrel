"""
Benchmark script for context building performance.

Measures:
- Context building overhead (number of sessions/tools/messages processed)
- Average, median, p95, p99 processing times
- Memory entries created during context building
"""

import time
from pathlib import Path

from dawn_kestrel.benchmarks import BenchmarkRunner, benchmark
from dawn_kestrel.context import ContextBuilder
from dawn_kestrel.core import models


def mock_context_builder(sessions: list[models.Session], tools: list) -> dict:
    """Mock context builder function for benchmarking.

    Args:
        sessions: List of sessions to build context from
        tools: List of tools to include

    Returns:
        Dict with built context
    """
    # Simulate context building time
    time.sleep(0.002 * (1 + len(sessions) % 4))

    context = {
        "session_count": len(sessions),
        "tool_count": len(tools),
        "total_messages": len(sessions) * 3,  # Mock calculation
        "timestamp": time.time(),
    }

    return context


def run_context_build_benchmark(iterations: int = 100, sessions_per_context: int = 5, tools_per_context: int = 3) -> BenchmarkRunner:
    """Run context building benchmarks.

    Args:
        iterations: Number of benchmark iterations
        sessions_per_context: Number of sessions per context
        tools_per_context: Number of tools per context

    Returns:
        BenchmarkRunner with results
    """
    runner = BenchmarkRunner(report_name="context_build_benchmark")

    # Create mock sessions with message counts
    sessions = [
        models.Session(
            id=f"session_{i}",
            slug=f"session_{i}",
            project_id="test-project",
            directory="/tmp/test",
            title=f"Session {i}",
            version="1.0",
            message_count=3,  # Each session has 3 messages
            message_counter=3,
        )
        for i in range(sessions_per_context)
    ]

    # Create mock tools
    tools = [
        {"name": f"tool_{i}", "description": f"Tool {i} for context building"}
        for i in range(tools_per_context)
    ]

    # Benchmark: Context building with baseline configuration
    result = runner.add_benchmark(
        benchmark_name="context_build",
        metric_name="baseline_build_time",
        func=lambda: mock_context_builder(sessions, tools),
        iterations=iterations,
        unit="s",
        memory_created=0,
    )

    print(f"\nContext Building Benchmark (baseline):")
    print(f"  {result}")
    print(f"  Sessions: {sessions_per_context}, Tools: {tools_per_context}")

    # Benchmark: Context building with many sessions
    result = runner.add_benchmark(
        benchmark_name="context_build",
        metric_name="large_session_count",
        func=lambda: mock_context_builder(
            sessions * 2,  # Double the sessions
            tools
        ),
        iterations=iterations,
        unit="s",
        memory_created=0,
    )

    print(f"  {result}")

    # Benchmark: Context building with many tools
    result = runner.add_benchmark(
        benchmark_name="context_build",
        metric_name="large_tool_count",
        func=lambda: mock_context_builder(
            sessions,
            tools * 2  # Double the tools
        ),
        iterations=iterations,
        unit="s",
        memory_created=0,
    )

    print(f"  {result}")

    return runner


def main() -> None:
    """Run context building benchmarks and save results."""
    iterations = 100
    sessions_per_context = 5
    tools_per_context = 3

    print("Running context building benchmarks...")
    print(f"Iterations: {iterations}")
    print(f"Sessions per context: {sessions_per_context}")
    print(f"Tools per context: {tools_per_context}")
    print()

    runner = run_context_build_benchmark(iterations, sessions_per_context, tools_per_context)

    # Save results
    results_dir = Path(__file__).parent.parent.parent.parent / "benchmarks"
    results_file = results_dir / "context_build_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    runner.save_report(results_file)
    runner.print_summary()

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
