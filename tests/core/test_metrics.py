"""Tests for metrics decorators and proxies."""

import asyncio
import pytest
from dawn_kestrel.core.metrics import (
    MetricsCollector,
    InMemoryMetricsStore,
    metrics_decorator,
    MethodMetricsProxy,
    create_metrics_proxy,
)


# ============ MetricsCollector Protocol Tests ============


def test_collector_has_record_timing_method():
    """Test that MetricsCollector protocol defines record_timing."""
    assert hasattr(MetricsCollector, "record_timing")


def test_collector_has_increment_counter_method():
    """Test that MetricsCollector protocol defines increment_counter."""
    assert hasattr(MetricsCollector, "increment_counter")


def test_collector_has_get_metric_method():
    """Test that MetricsCollector protocol defines get_metric."""
    assert hasattr(MetricsCollector, "get_metric")


# ============ InMemoryMetricsStore Tests ============


@pytest.mark.asyncio
async def test_record_timing_stores_metric():
    """Test that record_timing stores timing metric."""
    store = InMemoryMetricsStore()
    await store.record_timing("test_function", 100.5)
    stats = await store.get_metric("test_function")

    assert stats["count"] == 1.0
    assert stats["sum"] == 100.5
    assert stats["min"] == 100.5
    assert stats["max"] == 100.5
    assert stats["avg"] == 100.5


@pytest.mark.asyncio
async def test_record_timing_with_tags_stores_with_tags():
    """Test that record_timing stores metrics with tags."""
    store = InMemoryMetricsStore()
    tags = {"operation": "test", "user": "admin"}
    await store.record_timing("test_function", 100.5, tags)

    stats = await store.get_metric("test_function", tags)
    assert stats["count"] == 1.0
    assert stats["sum"] == 100.5


@pytest.mark.asyncio
async def test_increment_counter_increments_value():
    """Test that increment_counter increments counter value."""
    store = InMemoryMetricsStore()
    await store.increment_counter("api_calls")
    await store.increment_counter("api_calls", 5)

    stats = await store.get_metric("api_calls")
    assert stats["count"] == 6.0


@pytest.mark.asyncio
async def test_increment_counter_with_tags_separates_counters():
    """Test that increment_counter with tags separates counters."""
    store = InMemoryMetricsStore()
    await store.increment_counter("api_calls", tags={"method": "GET"})
    await store.increment_counter("api_calls", tags={"method": "POST"})

    stats_get = await store.get_metric("api_calls", tags={"method": "GET"})
    stats_post = await store.get_metric("api_calls", tags={"method": "POST"})

    assert stats_get["count"] == 1.0
    assert stats_post["count"] == 1.0


@pytest.mark.asyncio
async def test_get_metric_returns_aggregated_stats():
    """Test that get_metric returns aggregated statistics."""
    store = InMemoryMetricsStore()
    await store.record_timing("test_function", 100.0)
    await store.record_timing("test_function", 200.0)
    await store.record_timing("test_function", 300.0)

    stats = await store.get_metric("test_function")
    assert stats["count"] == 3.0
    assert stats["sum"] == 600.0
    assert stats["min"] == 100.0
    assert stats["max"] == 300.0
    assert stats["avg"] == 200.0


@pytest.mark.asyncio
async def test_get_metric_filters_by_tags():
    """Test that get_metric filters metrics by tags."""
    store = InMemoryMetricsStore()
    await store.record_timing("test_function", 100.0, {"operation": "read"})
    await store.record_timing("test_function", 200.0, {"operation": "write"})

    stats_read = await store.get_metric("test_function", {"operation": "read"})
    stats_write = await store.get_metric("test_function", {"operation": "write"})

    assert stats_read["count"] == 1.0
    assert stats_read["min"] == 100.0
    assert stats_write["count"] == 1.0
    assert stats_write["min"] == 200.0


@pytest.mark.asyncio
async def test_get_metric_returns_zeros_for_no_data():
    """Test that get_metric returns zeros when no data exists."""
    store = InMemoryMetricsStore()
    stats = await store.get_metric("nonexistent_metric")

    assert stats["count"] == 0.0
    assert stats["sum"] == 0.0
    assert stats["min"] == 0.0
    assert stats["max"] == 0.0
    assert stats["avg"] == 0.0


# ============ metrics_decorator Tests ============


@pytest.mark.asyncio
async def test_metrics_decorator_measures_execution_time():
    """Test that metrics_decorator measures execution time."""
    store = InMemoryMetricsStore()

    @metrics_decorator(collector=store)
    async def test_function():
        await asyncio.sleep(0.1)
        return 42

    result = await test_function()
    assert result == 42

    stats = await store.get_metric("test_function")
    assert stats["count"] == 1.0
    assert stats["min"] > 90.0  # At least 90ms
    assert stats["max"] > 90.0


@pytest.mark.asyncio
async def test_metrics_decorator_with_custom_metric_name():
    """Test that metrics_decorator uses custom metric name."""
    store = InMemoryMetricsStore()

    @metrics_decorator(collector=store, metric_name="custom_metric")
    async def test_function():
        return 42

    await test_function()

    stats = await store.get_metric("custom_metric")
    assert stats["count"] == 1.0


@pytest.mark.asyncio
async def test_metrics_decorator_with_tags():
    """Test that metrics_decorator records tags."""
    store = InMemoryMetricsStore()
    tags = {"operation": "test", "module": "api"}

    @metrics_decorator(collector=store, tags=tags)
    async def test_function():
        return 42

    await test_function()

    stats = await store.get_metric("test_function", tags)
    assert stats["count"] == 1.0


@pytest.mark.asyncio
async def test_metrics_decorator_records_timing_on_exception():
    """Test that metrics_decorator records timing even on exception."""
    store = InMemoryMetricsStore()

    @metrics_decorator(collector=store)
    async def test_function():
        await asyncio.sleep(0.01)
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        await test_function()

    stats = await store.get_metric("test_function")
    assert stats["count"] == 1.0
    assert stats["min"] > 5.0


@pytest.mark.asyncio
async def test_metrics_decorator_preserves_function_metadata():
    """Test that metrics_decorator preserves function metadata."""
    store = InMemoryMetricsStore()

    @metrics_decorator(collector=store)
    async def test_function(x: int, y: int) -> int:
        """Test function docstring."""
        return x + y

    assert test_function.__name__ == "test_function"
    assert "Test function docstring" in test_function.__doc__


# ============ MetricsProxy Tests ============


@pytest.mark.asyncio
async def test_method_metrics_proxy_wraps_function():
    """Test that MethodMetricsProxy wraps function."""
    store = InMemoryMetricsStore()

    async def test_function(x: int) -> int:
        return x * 2

    proxy = MethodMetricsProxy(test_function, store)
    result = await proxy(5)

    assert result == 10


@pytest.mark.asyncio
async def test_method_metrics_proxy_records_call_count():
    """Test that MethodMetricsProxy records call count."""
    store = InMemoryMetricsStore()

    async def test_function(x: int) -> int:
        return x * 2

    proxy = MethodMetricsProxy(test_function, store, metric_name="multiply")
    await proxy(5)
    await proxy(10)

    stats = await store.get_metric("multiply_calls", tags={"method": "test_function"})
    assert stats["count"] == 2.0


@pytest.mark.asyncio
async def test_method_metrics_proxy_with_custom_metric_name():
    """Test that MethodMetricsProxy uses custom metric name."""
    store = InMemoryMetricsStore()

    async def test_function(x: int) -> int:
        return x * 2

    proxy = MethodMetricsProxy(test_function, store, metric_name="custom_metric")
    await proxy(5)

    stats = await store.get_metric("custom_metric_calls", tags={"method": "test_function"})
    assert stats["count"] == 1.0


@pytest.mark.asyncio
async def test_method_metrics_proxy_passes_through_return_value():
    """Test that MethodMetricsProxy passes through return value."""
    store = InMemoryMetricsStore()

    async def test_function(x: int) -> int:
        return x * 2

    proxy = MethodMetricsProxy(test_function, store)
    result = await proxy(21)

    assert result == 42


@pytest.mark.asyncio
async def test_create_metrics_proxy_returns_proxy():
    """Test that create_metrics_proxy returns MethodMetricsProxy."""
    store = InMemoryMetricsStore()

    async def test_function(x: int) -> int:
        return x * 2

    proxy = create_metrics_proxy(test_function, store)

    assert isinstance(proxy, MethodMetricsProxy)
    result = await proxy(5)
    assert result == 10


# ============ Integration Tests ============


@pytest.mark.asyncio
async def test_collector_and_store_integration():
    """Test integration between collector and store."""
    store = InMemoryMetricsStore()

    @metrics_decorator(collector=store, tags={"module": "api"})
    async def get_user(user_id: int) -> dict:
        await asyncio.sleep(0.01)
        return {"id": user_id, "name": "Test User"}

    # Call function multiple times
    await get_user(1)
    await get_user(2)
    await get_user(3)

    stats = await store.get_metric("get_user", tags={"module": "api"})
    assert stats["count"] == 3.0
    assert stats["min"] > 5.0


@pytest.mark.asyncio
async def test_decorator_and_collector_integration():
    """Test integration between decorator and collector."""
    store = InMemoryMetricsStore()

    @metrics_decorator(collector=store, metric_name="api_call")
    async def api_endpoint():
        await asyncio.sleep(0.05)
        return {"status": "ok"}

    # Use proxy for another function
    async def helper_function():
        return "helper"

    proxy = create_metrics_proxy(helper_function, store, metric_name="helper_call")
    await proxy()

    # Call the decorated function to record timing
    await api_endpoint()

    # Check both metrics recorded
    api_stats = await store.get_metric("api_call")
    helper_stats = await store.get_metric("helper_call_calls", tags={"method": "helper_function"})

    assert api_stats["count"] == 1.0
    assert helper_stats["count"] == 1.0
