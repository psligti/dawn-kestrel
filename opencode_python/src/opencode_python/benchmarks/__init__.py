"""
Performance benchmarking framework for OpenCode Python SDK.

Provides core benchmarking utilities for measuring:
- Agent execution speed
- Memory search latency
- Context building overhead

All benchmarks use pure Python standard library measurements (time.time(), memory profiling)
to keep dependencies minimal.
"""

import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from opencode_python.core import models


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    benchmark_name: str
    metric_name: str
    metric_value: float
    unit: str
    count: int
    mean: float
    median: float
    std_dev: Optional[float] = None
    p95: Optional[float] = None
    p99: Optional[float] = None
    min_value: float = 0.0
    max_value: float = 0.0
    memory_created: int = 0  # Number of entries created during benchmark
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert benchmark result to dictionary."""
        return {
            "benchmark_name": self.benchmark_name,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "unit": self.unit,
            "count": self.count,
            "mean": self.mean,
            "median": self.median,
            "std_dev": self.std_dev,
            "p95": self.p95,
            "p99": self.p99,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "memory_created": self.memory_created,
            "timestamp": self.timestamp,
        }

    def __str__(self) -> str:
        """String representation of benchmark result."""
        return (
            f"{self.benchmark_name}: {self.metric_name}={self.mean:.3f}{self.unit} "
            f"(count={self.count}, p95={self.p95:.3f}{self.unit} if self.p95 else 'N/A') "
            f"(memory_created={self.memory_created})"
        )


@dataclass
class BenchmarkReport:
    """Complete report containing multiple benchmark results."""
    name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result to the report."""
        self.results.append(result)

    def save_to_file(self, filepath: Path) -> None:
        """Save benchmark report to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump({
                "report_name": self.name,
                "timestamp": self.timestamp,
                "results": [r.to_dict() for r in self.results],
            }, f, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "report_name": self.name,
            "timestamp": self.timestamp,
            "results": [r.to_dict() for r in self.results],
        }


def calculate_percentiles(values: List[float], percentiles: List[float]) -> Dict[float, float]:
    """Calculate percentile values for a list of numbers."""
    sorted_values = sorted(values)
    return {
        percentile: sorted_values[int((len(sorted_values) - 1) * percentile / 100)]
        for percentile in percentiles
    }


def record_result(
    benchmark_name: str,
    metric_name: str,
    values: List[float],
    count: int,
    unit: str,
    memory_created: int = 0,
) -> BenchmarkResult:
    """Record benchmark results for a metric."""
    if not values:
        raise ValueError("Values list cannot be empty")

    mean = statistics.mean(values)
    median = statistics.median(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
    p95_values = calculate_percentiles(values, [95])
    p99_values = calculate_percentiles(values, [99])
    min_value = min(values)
    max_value = max(values)

    return BenchmarkResult(
        benchmark_name=benchmark_name,
        metric_name=metric_name,
        metric_value=mean,
        unit=unit,
        count=count,
        mean=mean,
        median=median,
        std_dev=std_dev,
        p95=p95_values.get(95, None),
        p99=p99_values.get(99, None),
        min_value=min_value,
        max_value=max_value,
        memory_created=memory_created,
    )


def benchmark(
    benchmark_name: str,
    metric_name: str,
    func: Callable,
    iterations: int = 100,
    unit: str = "s",
    memory_created: int = 0,
) -> BenchmarkResult:
    """
    Run a benchmark on a function.

    Args:
        benchmark_name: Name of the benchmark (e.g., "agent_execution")
        metric_name: Name of the metric being measured (e.g., "execution_time")
        func: Function to benchmark
        iterations: Number of iterations to run
        unit: Unit of measurement (e.g., "s", "ms", "us")
        memory_created: Number of entries created during benchmark

    Returns:
        BenchmarkResult object with statistics
    """
    times = []

    for _ in range(iterations):
        start_time = time.perf_counter()
        func()
        end_time = time.perf_counter()
        times.append(end_time - start_time)

    return record_result(
        benchmark_name=benchmark_name,
        metric_name=metric_name,
        values=times,
        count=iterations,
        unit=unit,
        memory_created=memory_created,
    )


class BenchmarkRunner:
    """Runner for multiple benchmarks with reporting."""

    def __init__(self, report_name: str = "benchmark_report"):
        """Initialize benchmark runner."""
        self.report_name = report_name
        self.report = BenchmarkReport(name=report_name)

    def add_benchmark(
        self,
        benchmark_name: str,
        metric_name: str,
        func: Callable,
        iterations: int = 100,
        unit: str = "s",
        memory_created: int = 0,
    ) -> BenchmarkResult:
        """
        Add and run a benchmark.

        Args:
            benchmark_name: Name of the benchmark
            metric_name: Name of the metric
            func: Function to benchmark
            iterations: Number of iterations
            unit: Unit of measurement
            memory_created: Number of entries created

        Returns:
            BenchmarkResult
        """
        result = benchmark(
            benchmark_name=benchmark_name,
            metric_name=metric_name,
            func=func,
            iterations=iterations,
            unit=unit,
            memory_created=memory_created,
        )
        self.report.add_result(result)
        return result

    def save_report(self, filepath: Path) -> None:
        """Save benchmark report to file."""
        self.report.save_to_file(filepath)

    def print_summary(self) -> None:
        """Print summary of all benchmark results."""
        print(f"\n{'='*80}")
        print(f"BENCHMARK REPORT: {self.report.name}")
        print(f"{'='*80}\n")

        for result in self.report.results:
            print(result)

        print(f"\n{'='*80}\n")
