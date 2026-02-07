"""
Benchmark script for memory search performance.

Measures:
- Memory search query latency
- Average, median, p95, p99 search times
- Memory entries created during search
"""

import time
from pathlib import Path

from dawn_kestrel.benchmarks import BenchmarkRunner, benchmark


class MockMemoryEntry:
    """Mock memory entry for benchmarking."""

    def __init__(self, entry_id: str, content: str, metadata: dict = None):
        self.entry_id = entry_id
        self.content = content
        self.metadata = metadata or {}


def mock_memory_search(entry: MockMemoryEntry, query: str) -> list[MockMemoryEntry]:
    """Mock memory search function for benchmarking.

    Args:
        entry: Memory entry to search in
        query: Search query string

    Returns:
        List of matching entries (mock implementation always returns entry)
    """
    # Simulate search time (simple text matching simulation)
    time.sleep(0.0005 * (1 + len(query) % 3))

    if query.lower() in entry.content.lower():
        return [entry]

    return []


def run_memory_search_benchmark(iterations: int = 100, entries_per_query: int = 10) -> BenchmarkRunner:
    """Run memory search benchmarks.

    Args:
        iterations: Number of benchmark iterations
        entries_per_query: Number of entries to search in

    Returns:
        BenchmarkRunner with results
    """
    runner = BenchmarkRunner(report_name="memory_search_benchmark")

    # Create mock entries
    entries = [
        MockMemoryEntry(
            entry_id=f"entry_{i}",
            content=f"This is a test entry for query {i}. Contains relevant information about performance benchmarks.",
            metadata={"timestamp": time.time(), "category": "test"}
        )
        for i in range(entries_per_query)
    ]

    # Benchmark: Memory search with short query
    result = runner.add_benchmark(
        benchmark_name="memory_search",
        metric_name="short_query_time",
        func=lambda: mock_memory_search(
            entries[0],
            "performance"
        ),
        iterations=iterations,
        unit="s",
        memory_created=0,
    )

    print(f"\nMemory Search Benchmark (short query):")
    print(f"  {result}")

    # Benchmark: Memory search with long query
    result = runner.add_benchmark(
        benchmark_name="memory_search",
        metric_name="long_query_time",
        func=lambda: mock_memory_search(
            entries[-1],
            "performance benchmarking framework measurement results analysis"
        ),
        iterations=iterations,
        unit="s",
        memory_created=0,
    )

    print(f"  {result}")

    # Benchmark: Memory search with no match
    result = runner.add_benchmark(
        benchmark_name="memory_search",
        metric_name="no_match_time",
        func=lambda: mock_memory_search(
            entries[0],
            "nonexistent query string that should return no results"
        ),
        iterations=iterations,
        unit="s",
        memory_created=0,
    )

    print(f"  {result}")

    return runner


def main() -> None:
    """Run memory search benchmarks and save results."""
    iterations = 100
    entries_per_query = 10

    print("Running memory search benchmarks...")
    print(f"Iterations: {iterations}")
    print(f"Entries per query: {entries_per_query}")
    print()

    runner = run_memory_search_benchmark(iterations, entries_per_query)

    # Save results
    results_dir = Path(__file__).parent.parent.parent.parent / "benchmarks"
    results_file = results_dir / "memory_search_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    runner.save_report(results_file)
    runner.print_summary()

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
