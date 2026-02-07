"""
Benchmark script for agent execution performance.

Measures:
- Agent runtime invocation time
- Average, median, p95, p99 latencies
- Memory entries created
"""

import time
from pathlib import Path

from dawn_kestrel.benchmarks import BenchmarkRunner, benchmark
from dawn_kestrel.core import models


def mock_agent_execution() -> None:
    """Mock agent execution function for benchmarking."""
    # Simulate agent execution time (random variation for realism)
    time.sleep(0.001 * (1 + (time.time() % 5) / 100))


def run_agent_benchmark(iterations: int = 100) -> BenchmarkRunner:
    """Run agent execution benchmarks.

    Args:
        iterations: Number of benchmark iterations

    Returns:
        BenchmarkRunner with results
    """
    runner = BenchmarkRunner(report_name="agent_execution_benchmark")

    # Benchmark: Simple agent invocation
    result = runner.add_benchmark(
        benchmark_name="agent_execution",
        metric_name="invocation_time",
        func=mock_agent_execution,
        iterations=iterations,
        unit="s",
        memory_created=0,
    )

    print(f"\nAgent Execution Benchmark:")
    print(f"  {result}")

    # Benchmark: Session creation (simulated)
    def create_session_mock():
        """Mock session creation."""
        # Create minimal session with required fields
        session = models.Session(
            id="test-session",
            slug="test-session",
            project_id="test-project",
            directory="/tmp/test",
            title="Test Session",
            version="1.0",
        )

    result = runner.add_benchmark(
        benchmark_name="agent_execution",
        metric_name="session_creation_time",
        func=create_session_mock,
        iterations=iterations,
        unit="s",
        memory_created=0,
    )

    print(f"  {result}")

    return runner


def main() -> None:
    """Run agent execution benchmarks and save results."""
    iterations = 100

    print("Running agent execution benchmarks...")
    print(f"Iterations: {iterations}")
    print()

    runner = run_agent_benchmark(iterations)

    # Save results
    results_dir = Path(__file__).parent.parent.parent.parent / "benchmarks"
    results_file = results_dir / "agent_execution_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    runner.save_report(results_file)
    runner.print_summary()

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
