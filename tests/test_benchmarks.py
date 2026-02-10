"""
Tests for performance benchmarking framework.

Tests:
- Benchmark framework functionality
- Result recording and persistence
- Performance assertions
- Mock data handling
"""

import json
import time
import tempfile
from pathlib import Path

import pytest

from dawn_kestrel.benchmarks import (
    BenchmarkRunner,
    benchmark,
    calculate_percentiles,
    record_result,
)


class TestBenchmarkResult:
    """Test BenchmarkResult dataclass."""

    def test_result_creation(self):
        """Test creating a benchmark result."""
        values = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = record_result(
            benchmark_name="test_benchmark",
            metric_name="execution_time",
            values=values,
            count=len(values),
            unit="s",
        )

        assert result.benchmark_name == "test_benchmark"
        assert result.metric_name == "execution_time"
        assert result.mean == 0.3
        assert result.median == 0.3
        assert result.std_dev == 0.15811388300841897
        assert result.min_value == 0.1
        assert result.max_value == 0.5

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = record_result(
            benchmark_name="test",
            metric_name="time",
            values=[0.1, 0.2],
            count=2,
            unit="s",
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["benchmark_name"] == "test"
        assert result_dict["metric_name"] == "time"
        assert result_dict["mean"] == pytest.approx(0.15)

    def test_result_with_zero_iterations(self):
        """Test that zero iterations raises error."""
        with pytest.raises(ValueError):
            record_result(
                benchmark_name="test",
                metric_name="time",
                values=[],
                count=0,
                unit="s",
            )


class TestCalculatePercentiles:
    """Test percentile calculation utility."""

    def test_calculate_p50(self):
        """Test 50th percentile calculation."""
        values = [1, 2, 3, 4, 5]
        percentiles = calculate_percentiles(values, [50])
        assert percentiles[50] == 3

    def test_calculate_p95_and_p99(self):
        """Test 95th and 99th percentile calculations."""
        values = [i for i in range(100)]
        percentiles = calculate_percentiles(values, [95, 99])

        assert percentiles[95] == 94  # 95th percentile
        assert percentiles[99] == 98  # 99th percentile

    def test_calculate_percentiles_single_value(self):
        """Test percentile calculation with single value."""
        values = [5]
        percentiles = calculate_percentiles(values, [50, 95, 99])
        assert percentiles[50] == 5
        assert percentiles[95] == 5
        assert percentiles[99] == 5


class TestBenchmarkFunction:
    """Test benchmark utility function."""

    def test_benchmark_simple_function(self):
        """Test benchmarking a simple function."""

        def slow_function():
            """Simulate slow function."""
            time.sleep(0.01)

        result = benchmark(
            benchmark_name="test",
            metric_name="execution",
            func=slow_function,
            iterations=10,
            unit="s",
        )

        assert result.benchmark_name == "test"
        assert result.metric_name == "execution"
        assert result.count == 10
        assert result.unit == "s"
        assert result.mean > 0  # Should be positive
        assert result.min_value > 0
        assert result.max_value > 0

    def test_benchmark_zero_iterations(self):
        """Test that zero iterations raises error."""

        def empty_function():
            pass

        with pytest.raises(ValueError):
            benchmark(
                benchmark_name="test",
                metric_name="execution",
                func=empty_function,
                iterations=0,
                unit="s",
            )


class TestBenchmarkRunner:
    """Test BenchmarkRunner class."""

    def test_runner_initialization(self):
        """Test creating a benchmark runner."""
        runner = BenchmarkRunner(report_name="test_report")
        assert runner.report_name == "test_report"
        assert len(runner.report.results) == 0

    def test_add_benchmark(self):
        """Test adding a benchmark to runner."""
        runner = BenchmarkRunner(report_name="test")

        def mock_func():
            pass

        result = runner.add_benchmark(
            benchmark_name="test_benchmark",
            metric_name="test_metric",
            func=mock_func,
            iterations=10,
            unit="s",
        )

        assert len(runner.report.results) == 1
        assert result in runner.report.results

    def test_add_multiple_benchmarks(self):
        """Test adding multiple benchmarks."""
        runner = BenchmarkRunner(report_name="test")

        for i in range(3):
            result = runner.add_benchmark(
                benchmark_name="test_benchmark",
                metric_name=f"metric_{i}",
                func=lambda: None,
                iterations=5,
                unit="s",
            )
            assert result.benchmark_name == "test_benchmark"
            assert result.metric_name == f"metric_{i}"

        assert len(runner.report.results) == 3

    def test_save_report(self, tmp_path):
        """Test saving report to file."""
        runner = BenchmarkRunner(report_name="test_report")

        result = runner.add_benchmark(
            benchmark_name="test",
            metric_name="time",
            func=lambda: None,
            iterations=10,
            unit="s",
        )

        filepath = tmp_path / "test_results.json"
        runner.save_report(filepath)

        assert filepath.exists()

        # Verify content
        with open(filepath, "r") as f:
            data = json.load(f)

        assert data["report_name"] == "test_report"
        assert len(data["results"]) == 1
        assert data["results"][0]["benchmark_name"] == "test"

    def test_print_summary(self, capsys):
        """Test printing benchmark summary."""
        runner = BenchmarkRunner(report_name="test_report")

        runner.add_benchmark(
            benchmark_name="test_benchmark",
            metric_name="test_metric",
            func=lambda: None,
            iterations=10,
            unit="s",
        )

        runner.print_summary()

        captured = capsys.readouterr()
        assert "test_report" in captured.out
        assert "test_benchmark" in captured.out


class TestBenchmarkIntegration:
    """Integration tests for benchmark framework."""

    def test_complete_benchmark_workflow(self, tmp_path):
        """Test complete benchmark workflow: add benchmarks, save, load."""
        runner = BenchmarkRunner(report_name="integration_test")

        # Add multiple benchmarks
        for i in range(5):
            runner.add_benchmark(
                benchmark_name="test_benchmark",
                metric_name=f"metric_{i}",
                func=lambda: None,
                iterations=10,
                unit="s",
                memory_created=i,
            )

        # Save report
        filepath = tmp_path / "integration_test.json"
        runner.save_report(filepath)

        assert filepath.exists()

        # Verify report
        report_data = json.loads(filepath.read_text())
        assert len(report_data["results"]) == 5
        assert report_data["results"][0]["memory_created"] == 0
        assert report_data["results"][4]["memory_created"] == 4

    def test_performance_assertions(self):
        """Test that performance metrics are reasonable."""
        runner = BenchmarkRunner(report_name="performance_test")

        def fast_function():
            """Simulate very fast function."""
            time.sleep(0.0001)

        result = runner.add_benchmark(
            benchmark_name="fast_test",
            metric_name="execution",
            func=fast_function,
            iterations=1000,
            unit="s",
        )

        # Verify metrics are reasonable
        assert result.mean > 0
        assert result.mean < 1  # Should be very fast
        assert result.p95 > result.mean  # p95 should be >= mean
        assert result.p99 > result.mean  # p99 should be >= mean


class TestBenchmarkMockFunctions:
    """Test benchmark framework with mock functions."""

    def test_benchmark_with_sleep_function(self):
        """Test benchmarking function with predictable sleep."""
        import time

        runner = BenchmarkRunner(report_name="sleep_test")

        def sleeping_function():
            """Function that sleeps for 0.1s."""
            time.sleep(0.1)

        result = runner.add_benchmark(
            benchmark_name="sleep_test",
            metric_name="sleep_time",
            func=sleeping_function,
            iterations=5,
            unit="s",
        )

        # Mean should be around 0.1s
        assert 0.09 <= result.mean <= 0.11

    def test_benchmark_with_variable_time(self):
        """Test benchmarking function with variable execution time."""
        import time

        runner = BenchmarkRunner(report_name="variable_test")

        def variable_function():
            """Function with variable execution time."""
            time.sleep(0.001 * (1 + (time.time() % 3)))

        result = runner.add_benchmark(
            benchmark_name="variable_test",
            metric_name="variable_time",
            func=variable_function,
            iterations=20,
            unit="s",
        )

        # Should have some variance
        assert result.std_dev > 0
        assert result.mean > 0
        assert result.min_value > 0
        assert result.max_value > result.mean


def test_benchmark_module_import():
    """Test that benchmark module can be imported."""
    from dawn_kestrel.benchmarks import (
        BenchmarkRunner,
        BenchmarkResult,
        benchmark,
        calculate_percentiles,
        record_result,
    )

    assert BenchmarkRunner is not None
    assert benchmark is not None
    assert record_result is not None


def test_benchmark_scripts_exist():
    """Test that benchmark scripts exist."""
    from pathlib import Path

    opencode_root = Path(__file__).parent.parent
    benchmarks_dir = opencode_root / "dawn_kestrel" / "benchmarks"

    assert benchmarks_dir.exists()

    # Check for benchmark scripts
    agent_benchmark = benchmarks_dir / "agent_execution.py"
    memory_benchmark = benchmarks_dir / "memory_search.py"
    context_benchmark = benchmarks_dir / "context_build.py"

    assert agent_benchmark.exists(), "agent_execution.py should exist"
    assert memory_benchmark.exists(), "memory_search.py should exist"
    assert context_benchmark.exists(), "context_build.py should exist"
