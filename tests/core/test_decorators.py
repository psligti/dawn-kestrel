"""Tests for logging decorators and proxies.

This module tests the Decorator/Proxy pattern for logging, which provides
configurable, centralized logging for functions and methods.
"""

import asyncio
import logging
from io import StringIO
from dataclasses import dataclass

import pytest

from dawn_kestrel.core.decorators import (
    LoggingConfig,
    log_function,
    FunctionProxy,
    create_logging_proxy,
)


# ============ LoggingConfig Tests ============


def test_logging_config_initializes_with_defaults():
    """Test that LoggingConfig initializes with default values."""
    config = LoggingConfig()

    assert config.level == logging.INFO
    assert config.enabled is True
    assert config.prefix == ""
    assert config.include_args is True
    assert config.include_result is True
    assert config.include_timestamp is False


def test_logging_config_allows_custom_level():
    """Test that LoggingConfig accepts custom log level."""
    config = LoggingConfig(level=logging.DEBUG)

    assert config.level == logging.DEBUG


def test_logging_config_allows_disabling():
    """Test that LoggingConfig can be disabled."""
    config = LoggingConfig(enabled=False)

    assert config.enabled is False


# ============ log_function Decorator Tests ============


@pytest.mark.asyncio
async def test_log_function_wraps_function():
    """Test that log_function decorator wraps async functions correctly."""

    @log_function()
    async def sample_function(x: int, y: int) -> int:
        return x + y

    result = await sample_function(5, 10)
    assert result == 15


@pytest.mark.asyncio
async def test_log_function_logs_entry_with_enabled_logging(caplog):
    """Test that log_function logs function entry when enabled."""
    caplog.set_level(logging.DEBUG)

    @log_function(level=logging.DEBUG, enabled=True, include_args=True)
    async def sample_function(x: int, y: int) -> int:
        return x + y

    await sample_function(5, 10)

    # Check for "Calling" and function name (not full qualified name)
    assert any(
        "Calling" in record.message and "sample_function" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_log_function_logs_result(caplog):
    """Test that log_function logs function result."""
    caplog.set_level(logging.DEBUG)

    @log_function(level=logging.DEBUG, enabled=True, include_result=True)
    async def sample_function(x: int, y: int) -> int:
        return x + y

    await sample_function(5, 10)

    assert any("returned" in record.message.lower() for record in caplog.records)


@pytest.mark.asyncio
async def test_log_function_logs_exception(caplog):
    """Test that log_function logs exceptions."""
    caplog.set_level(logging.DEBUG)

    @log_function(level=logging.DEBUG, enabled=True)
    async def failing_function():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        await failing_function()

    assert any("raised:" in record.message.lower() for record in caplog.records)
    assert any("Test error" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_log_function_respects_log_level(caplog):
    """Test that log_function respects log level configuration."""
    caplog.set_level(logging.INFO)

    @log_function(level=logging.DEBUG, enabled=True)
    async def sample_function(x: int, y: int) -> int:
        return x + y

    await sample_function(5, 10)

    # DEBUG level logs should not appear when logger is at INFO level
    assert not any("sample_function" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_log_function_with_prefix(caplog):
    """Test that log_function adds prefix to log messages."""
    caplog.set_level(logging.DEBUG)

    @log_function(level=logging.DEBUG, prefix="[TEST]")
    async def sample_function(x: int, y: int) -> int:
        return x + y

    await sample_function(5, 10)

    assert any("[TEST]" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_log_function_disabled_skips_logging(caplog):
    """Test that log_function skips logging when disabled."""
    caplog.set_level(logging.DEBUG)

    @log_function(level=logging.DEBUG, enabled=False)
    async def sample_function(x: int, y: int) -> int:
        return x + y

    await sample_function(5, 10)

    # No logs should appear when disabled
    assert not any("sample_function" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_log_function_async_function_works():
    """Test that log_function works with async functions."""

    @log_function()
    async def async_add(x: int, y: int) -> int:
        await asyncio.sleep(0.01)  # Simulate async work
        return x + y

    result = await async_add(5, 10)
    assert result == 15


# ============ LoggingProxy Tests ============


@pytest.mark.asyncio
async def test_function_proxy_wraps_function():
    """Test that FunctionProxy wraps async functions correctly."""

    async def sample_function(x: int, y: int) -> int:
        return x + y

    proxy = FunctionProxy(sample_function, enabled=False)
    result = await proxy(5, 10)

    assert result == 15


@pytest.mark.asyncio
async def test_function_proxy_logs_call(caplog):
    """Test that FunctionProxy logs function calls."""
    caplog.set_level(logging.INFO)

    async def sample_function(x: int, y: int) -> int:
        return x + y

    proxy = FunctionProxy(sample_function, level=logging.INFO, enabled=True)
    await proxy(5, 10)

    assert any("Calling sample_function" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_function_proxy_logs_result(caplog):
    """Test that FunctionProxy logs function results."""
    caplog.set_level(logging.INFO)

    async def sample_function(x: int, y: int) -> int:
        return x + y

    proxy = FunctionProxy(sample_function, level=logging.INFO, enabled=True)
    await proxy(5, 10)

    assert any("returned:" in record.message.lower() for record in caplog.records)


@pytest.mark.asyncio
async def test_function_proxy_logs_exception(caplog):
    """Test that FunctionProxy logs exceptions."""
    caplog.set_level(logging.ERROR)

    async def failing_function():
        raise ValueError("Test error")

    proxy = FunctionProxy(failing_function, enabled=True)
    with pytest.raises(ValueError):
        await proxy()

    assert any("raised:" in record.message.lower() for record in caplog.records)
    assert any("Test error" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_function_proxy_respects_level(caplog):
    """Test that FunctionProxy respects log level configuration."""
    caplog.set_level(logging.INFO)

    async def sample_function(x: int, y: int) -> int:
        return x + y

    proxy = FunctionProxy(sample_function, level=logging.DEBUG, enabled=True)
    await proxy(5, 10)

    # DEBUG level logs should not appear when logger is at INFO level
    assert not any("sample_function" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_function_proxy_with_prefix(caplog):
    """Test that FunctionProxy adds prefix to log messages."""
    caplog.set_level(logging.INFO)

    async def sample_function(x: int, y: int) -> int:
        return x + y

    proxy = FunctionProxy(sample_function, prefix="[TEST]", enabled=True)
    await proxy(5, 10)

    assert any("[TEST]" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_function_proxy_disabled_skips_logging(caplog):
    """Test that FunctionProxy skips logging when disabled."""
    caplog.set_level(logging.INFO)

    async def sample_function(x: int, y: int) -> int:
        return x + y

    proxy = FunctionProxy(sample_function, enabled=False)
    await proxy(5, 10)

    # No logs should appear when disabled
    assert not any("sample_function" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_create_logging_proxy_returns_proxy():
    """Test that create_logging_proxy returns a FunctionProxy."""

    async def sample_function(x: int, y: int) -> int:
        return x + y

    proxy = create_logging_proxy(sample_function)
    assert isinstance(proxy, FunctionProxy)


# ============ Configuration Tests ============


@pytest.mark.asyncio
async def test_log_level_debug_logs_everything(caplog):
    """Test that DEBUG level logs all messages."""
    caplog.set_level(logging.DEBUG)

    @log_function(level=logging.DEBUG, enabled=True, include_args=True, include_result=True)
    async def sample_function(x: int, y: int) -> int:
        return x + y

    await sample_function(5, 10)

    # Should log both call and result at DEBUG level
    call_logs = [r for r in caplog.records if "Calling" in r.message]
    result_logs = [r for r in caplog.records if "returned" in r.message.lower()]

    assert len(call_logs) > 0
    assert len(result_logs) > 0


@pytest.mark.asyncio
async def test_log_level_warning_filters_info(caplog):
    """Test that WARNING level filters INFO messages."""
    caplog.set_level(logging.DEBUG)

    @log_function(level=logging.WARNING, enabled=True)
    async def sample_function(x: int, y: int) -> int:
        return x + y

    await sample_function(5, 10)

    # Only WARNING or higher level logs should appear
    # The decorator logs at WARNING level, so we should see logs
    # But not at INFO level
    warning_logs = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_logs) > 0


@pytest.mark.asyncio
async def test_log_level_error_logs_only_errors(caplog):
    """Test that ERROR level only logs errors."""
    caplog.set_level(logging.DEBUG)

    @log_function(level=logging.ERROR, enabled=True)
    async def failing_function():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        await failing_function()

    # Should see ERROR log
    error_logs = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_logs) > 0


@pytest.mark.asyncio
async def test_logging_configurable_per_instance(caplog):
    """Test that logging can be configured per instance."""
    caplog.set_level(logging.DEBUG)

    @log_function(level=logging.DEBUG, enabled=True, prefix="[A]")
    async def function_a(x: int) -> int:
        return x * 2

    @log_function(level=logging.DEBUG, enabled=True, prefix="[B]")
    async def function_b(x: int) -> int:
        return x * 3

    await function_a(5)
    await function_b(5)

    # Both prefixes should appear in logs
    assert any("[A]" in record.message for record in caplog.records)
    assert any("[B]" in record.message for record in caplog.records)
