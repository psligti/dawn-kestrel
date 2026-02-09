"""Metrics decorators and proxies for performance monitoring.

This module implements the Decorator/Proxy pattern for metrics collection,
providing in-memory timing and counting metrics for observability.

Features:
- MetricsCollector Protocol: Interface for metrics collection
- InMemoryMetricsStore: In-memory storage for timing and counter metrics
- metrics_decorator: Decorator to measure function execution time
- MethodMetricsProxy: Proxy to count method calls
- Support for tags for grouping and filtering metrics
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Protocol, runtime_checkable


# ============ Protocol ============


@runtime_checkable
class MetricsCollector(Protocol):
    """Protocol for metrics collection.

    Collector records timing and counting metrics for monitoring
    and observability.

    Methods:
        record_timing: Record execution duration for a named operation.
        increment_counter: Increment a counter metric.
        get_metric: Get aggregated statistics for a metric.
    """

    async def record_timing(
        self,
        name: str,
        duration_ms: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record timing metric.

        Args:
            name: Metric name (e.g., function_name, operation).
            duration_ms: Duration in milliseconds.
            tags: Optional dict of tags for grouping/filtering.
        """
        ...

    async def increment_counter(
        self,
        name: str,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Increment counter metric.

        Args:
            name: Metric name (e.g., errors, calls).
            value: Value to add (default: 1).
            tags: Optional dict of tags for grouping/filtering.
        """
        ...

    async def get_metric(
        self,
        name: str,
        tags: dict[str, str] | None = None,
    ) -> dict[str, float]:
        """Get aggregated metric data.

        Args:
            name: Metric name.
            tags: Optional tags to filter by.

        Returns:
            Dict with aggregated stats (count, sum, min, max, avg).
        """
        ...


# ============ In-Memory Storage ============


class InMemoryMetricsStore:
    """In-memory metrics storage.

    Stores timing metrics and counters in memory. Suitable for
    single-process use and testing. Not thread-safe.

    Attributes:
        _timings: List of (name, duration_ms, tags, timestamp) tuples.
        _counters: Dict mapping (name, tags_key) to count values.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        # Timing metrics: list of (name, duration_ms, tags, timestamp)
        self._timings: list[tuple[str, float, dict[str, str], datetime]] = []
        # Counting metrics: dict[(name, tags_key)] -> count
        self._counters: defaultdict[tuple[str, str], int] = defaultdict(int)

    def _tags_key(self, tags: dict[str, str] | None) -> str:
        """Convert tags dict to key for counter storage.

        Args:
            tags: Tags dict or None.

        Returns:
            String representation of sorted tags tuple, or "()" for None.
        """
        if not tags:
            return "()"
        items = tuple(sorted(tags.items()))
        return str(items)

    async def record_timing(
        self,
        name: str,
        duration_ms: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record timing metric.

        Args:
            name: Metric name.
            duration_ms: Duration in milliseconds.
            tags: Optional tags.
        """
        self._timings.append((name, duration_ms, tags or {}, datetime.now()))

    async def increment_counter(
        self,
        name: str,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Increment counter metric.

        Args:
            name: Metric name.
            value: Value to add (default: 1).
            tags: Optional tags.
        """
        key = (name, self._tags_key(tags))
        self._counters[key] += value

    async def get_metric(
        self,
        name: str,
        tags: dict[str, str] | None = None,
    ) -> dict[str, float]:
        """Get aggregated metric data.

        Args:
            name: Metric name.
            tags: Optional tags to filter by.

        Returns:
            Dict with count, sum, min, max, avg statistics.
            If timings exist: count = number of timings, sum/min/max/avg from timings.
            If only counters exist: count = counter value, other stats = 0.
        """
        key = (name, self._tags_key(tags))
        counter_count = self._counters[key]

        timings = [
            (n, d, t) for n, d, t, _ in self._timings if n == name and (tags is None or t == tags)
        ]

        if not timings:
            return {
                "count": float(counter_count),
                "sum": 0.0,
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
            }

        durations = [d for _, d, _ in timings]
        return {
            "count": float(len(timings)),
            "sum": sum(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
        }

        durations = [d for _, d, _ in timings]
        return {
            "count": float(counter_count),
            "sum": sum(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
        }

        durations = [d for _, d, _ in timings]
        return {
            "count": float(counter_count),
            "sum": sum(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
        }

        durations = [d for _, d, _ in timings]
        return {
            "count": float(len(timings)),
            "sum": sum(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
        }


# ============ Decorator ============


def metrics_decorator(
    collector: MetricsCollector,
    metric_name: str | None = None,
    tags: dict[str, str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to record function execution timing.

    Measures execution duration of async functions and records
    timing metrics to the provided collector.

    Args:
        collector: MetricsCollector instance for recording metrics.
        metric_name: Metric name (defaults to function name).
        tags: Optional tags for grouping.

    Returns:
        Decorator function that wraps async callables.

    Example:
        >>> store = InMemoryMetricsStore()
        >>> @metrics_decorator(collector=store, tags={"module": "api"})
        ... async def get_user(user_id: int) -> dict:
        ...     return {"id": user_id}
        >>> await get_user(1)
        >>> stats = await store.get_metric("get_user")
        >>> print(stats["count"])
        1.0
    """
    config_tags = tags

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        name = metric_name or func.__name__

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                await collector.record_timing(name, duration_ms, config_tags)

        return wrapper

    return decorator


# ============ Proxy ============


class MethodMetricsProxy:
    """Proxy that records method call counts.

    Wraps any callable and records a counter metric each time
    the callable is invoked.

    Attributes:
        _func: The wrapped function/callable.
        _collector: MetricsCollector for recording metrics.
        _metric_name: Name for the metric.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        collector: MetricsCollector,
        metric_name: str | None = None,
    ) -> None:
        """Initialize metrics proxy.

        Args:
            func: Function to wrap.
            collector: MetricsCollector instance.
            metric_name: Metric name (defaults to function name).
        """
        self._func = func
        self._collector = collector
        self._metric_name = metric_name or func.__name__

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call wrapped function with metrics.

        Records a counter metric and calls the wrapped function.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Result of calling wrapped function.
        """
        # Record call count
        await self._collector.increment_counter(
            f"{self._metric_name}_calls",
            tags={"method": self._func.__name__},
        )

        # Call function
        return await self._func(*args, **kwargs)


def create_metrics_proxy(
    func: Callable[..., Any],
    collector: MetricsCollector,
    metric_name: str | None = None,
) -> MethodMetricsProxy:
    """Create a metrics proxy for a function.

    Factory function that creates a MethodMetricsProxy instance
    with specified configuration.

    Args:
        func: Function to wrap.
        collector: MetricsCollector instance.
        metric_name: Metric name (defaults to function name).

    Returns:
        MethodMetricsProxy instance that wraps function.

    Example:
        >>> store = InMemoryMetricsStore()
        >>> async def helper(x: int) -> int:
        ...     return x * 2
        >>> proxy = create_metrics_proxy(helper, store, metric_name="multiply")
        >>> result = await proxy(5)
        >>> stats = await store.get_metric("multiply_calls")
        >>> print(stats["count"])
        1.0
    """
    return MethodMetricsProxy(func, collector, metric_name)
