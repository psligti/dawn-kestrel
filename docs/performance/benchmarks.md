# Performance Benchmarking Guide

## Overview

This document describes the performance benchmarking framework for the OpenCode Python SDK. Benchmarks measure key performance characteristics of the SDK's core operations.

## What Gets Benchmarked

### 1. Agent Execution Speed
Measures the time to invoke and execute agents, including:
- Agent runtime initialization
- Message processing
- Tool execution overhead

### 2. Memory Search Latency
Measures query performance on memory entries:
- Search query processing time
- Results retrieval speed
- Impact of query complexity

### 3. Context Building Overhead
Measures context construction performance:
- Session aggregation time
- Tool inclusion processing
- Message filtering and ranking

## Running Benchmarks

### Quick Start

Run all benchmarks:

```bash
cd .

# Run agent execution benchmark
python -m dawn_kestrel.benchmarks.agent_execution

# Run memory search benchmark
python -m dawn_kestrel.benchmarks.memory_search

# Run context building benchmark
python -m dawn_kestrel.benchmarks.context_build
```

### Advanced Usage

Run a specific benchmark with custom iterations:

```bash
ITERATIONS=500 python -m dawn_kestrel.benchmarks.agent_execution
```

Run a single benchmark from Python:

```python
from dawn_kestrel.benchmarks import BenchmarkRunner

runner = BenchmarkRunner(report_name="my_benchmark")
result = runner.add_benchmark(
    benchmark_name="my_benchmark",
    metric_name="execution_time",
    func=my_function,
    iterations=100,
    unit="s",
    memory_created=0,
)

runner.print_summary()
runner.save_report(Path("results.json"))
```

## Benchmark Results Format

All benchmark results are saved as JSON files:

```json
{
  "report_name": "agent_execution_benchmark",
  "timestamp": "2026-01-30 14:30:00",
  "results": [
    {
      "benchmark_name": "agent_execution",
      "metric_name": "invocation_time",
      "metric_value": 0.0234,
      "unit": "s",
      "count": 100,
      "mean": 0.0234,
      "median": 0.0231,
      "std_dev": 0.0012,
      "p95": 0.0250,
      "p99": 0.0268,
      "min_value": 0.0200,
      "max_value": 0.0280,
      "memory_created": 0
    }
  ]
}
```

### Metric Definitions

- **mean**: Average execution time across all iterations
- **median**: Middle value when sorted (less affected by outliers)
- **std_dev**: Standard deviation (variability)
- **p95**: 95th percentile (95% of requests complete faster than this)
- **p99**: 99th percentile (99% of requests complete faster than this)
- **min_value**: Fastest execution
- **max_value**: Slowest execution
- **memory_created**: Number of entries created during benchmark

## Adding New Benchmarks

### Step 1: Create Benchmark Script

Create a new file in `dawn_kestrel/benchmarks/`:

```python
"""
Benchmark script for [feature_name] performance.

Measures:
- [metric 1]
- [metric 2]
"""

import time
from pathlib import Path

from dawn_kestrel.benchmarks import BenchmarkRunner, benchmark


def mock_function_for_benchmarking() -> dict:
    """Mock function to benchmark.

    Returns:
        Dict with benchmark-relevant data
    """
    # Simulate operation
    time.sleep(0.001)

    return {"result": "benchmark_data"}


def run_benchmark(iterations: int = 100) -> BenchmarkRunner:
    """Run benchmarks for the feature.

    Args:
        iterations: Number of iterations

    Returns:
        BenchmarkRunner with results
    """
    runner = BenchmarkRunner(report_name="[feature]_benchmark")

    result = runner.add_benchmark(
        benchmark_name="[feature]",
        metric_name="[metric_name]",
        func=mock_function_for_benchmarking,
        iterations=iterations,
        unit="s",
        memory_created=0,
    )

    print(f"Benchmark result: {result}")

    return runner


def main() -> None:
    """Run benchmarks and save results."""
    runner = run_benchmark(iterations=100)

    # Save results
    results_dir = Path(__file__).parent.parent.parent.parent / "benchmarks"
    results_file = results_dir / "[feature]_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    runner.save_report(results_file)
    runner.print_summary()


if __name__ == "__main__":
    main()
```

### Step 2: Update __init__.py

Add the benchmark script to the `__init__.py` exports (optional):

```python
from .agent_execution import main as run_agent_benchmark
from .memory_search import main as run_memory_benchmark
from .context_build import main as run_context_benchmark

__all__ = [
    "run_agent_benchmark",
    "run_memory_benchmark",
    "run_context_benchmark",
]
```

### Step 3: Run Tests

Ensure the benchmark framework tests pass:

```bash
pytest tests/test_benchmarks.py -v
```

### Step 4: Document Performance

Add your benchmark to this document with:
- Description of what's being measured
- Expected performance characteristics
- How to interpret results

## Interpreting Results

### Performance Goals

Use benchmarks to establish performance baselines and detect regressions.

#### Example Goals

| Metric | Goal | Rationale |
|--------|------|-----------|
| Agent execution mean | < 50ms | Should be responsive for real-time interaction |
| Memory search p95 | < 10ms | Users expect quick search responses |
| Context build p95 | < 100ms | Context construction happens frequently |

### Monitoring Changes

Compare benchmark results over time to detect performance regression:

```bash
# Run benchmark
python -m dawn_kestrel.benchmarks.agent_execution

# Check results
cat benchmarks/agent_execution_results.json

# Look for:
# - Mean time increased by > 20%
# - p95/p99 significantly slower
# - Increased memory usage
```

### Performance Regression Checklist

If benchmarks show performance degradation:

1. **Identify the regression**:
   - Compare current results to baseline
   - Check if recent changes affected the metric

2. **Investigate the cause**:
   - Review recent commits
   - Check if tests pass
   - Profile the slow operation

3. **Fix and validate**:
   - Apply performance fixes
   - Re-run benchmarks
   - Verify improvement

## Best Practices

### Measurement Practices

- **Keep iterations consistent**: Use the same iteration count for fair comparisons
- **Warm up**: Allow system to stabilize before benchmarking
- **Isolate metrics**: Each benchmark should measure one specific aspect
- **Use realistic mock data**: Mimic real-world data patterns

### Reporting Practices

- **Document baselines**: Record initial benchmark results
- **Track over time**: Save results with timestamps
- **Share findings**: Include benchmarks in pull requests for performance reviews

### Code Practices

- **Avoid optimization bias**: Don't tune code to pass benchmarks
- **Benchmark for visibility**: Simple, clear metrics are better than complex ones
- **Benchmark for regression detection**: Focus on stability, not maximum performance

## Limitations

### What Benchmarks Don't Measure

- Memory leaks (use tools like `memory_profiler`)
- Network latency (use integration tests)
- Disk I/O performance (use separate benchmarks)
- Long-term performance degradation (run regularly)

### When to Use Additional Tools

For deep performance analysis:

- **cProfile**: Profile Python functions
- **memory_profiler**: Memory usage profiling
- **Py-spy**: Runtime profiling without modifying code
- **tracemalloc**: Track memory allocations

## Troubleshooting

### Benchmarks Run Too Fast

If benchmarks show times < 1ms, they may not be measuring meaningful differences:

```python
# Add artificial delay for testing
time.sleep(0.001)
```

### Results Vary Wildly

Variability can come from:
- System load
- Other processes
- Caching effects

Solution: Run multiple times and use median/p95 metrics.

### Test Failures

If benchmark tests fail:

1. Check imports work correctly
2. Verify mock data is valid
3. Check iteration counts are reasonable
4. Review test setup

## Related Documentation

- [OpenCode SDK Documentation](../../README.md)
- [Performance Considerations](./performance_considerations.md)
- [API Documentation](../api.md)
