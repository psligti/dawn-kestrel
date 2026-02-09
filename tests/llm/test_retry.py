"""Tests for Retry + Backoff pattern.

TDD tests for retry executor with backoff strategies.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dawn_kestrel.core.result import Ok, Err, Result
from dawn_kestrel.llm.retry import (
    BackoffStrategy,
    ExponentialBackoff,
    LinearBackoff,
    FixedBackoff,
    RetryExecutor,
    RetryExecutorImpl,
)


# =============================================================================
# BackoffStrategy Tests
# =============================================================================


class TestExponentialBackoff:
    """Tests for ExponentialBackoff implementation."""

    def test_exponential_backoff_calculates_delay_correctly(self):
        """Test that exponential backoff doubles delay each attempt."""
        backoff = ExponentialBackoff(
            base_delay_ms=100,
            max_delay_ms=5000,
            exponential_base=2.0,
            jitter=False,
        )

        async def test_delays():
            delay_0 = await backoff.calculate_delay(0, 100, 5000)
            delay_1 = await backoff.calculate_delay(1, 100, 5000)
            delay_2 = await backoff.calculate_delay(2, 100, 5000)

            # Exponential: 100, 200, 400
            assert delay_0 == 100.0
            assert delay_1 == 200.0
            assert delay_2 == 400.0

        asyncio.run(test_delays())

    def test_exponential_backoff_applies_jitter(self):
        """Test that exponential backoff adds random jitter."""
        backoff = ExponentialBackoff(
            base_delay_ms=100,
            max_delay_ms=5000,
            exponential_base=2.0,
            jitter=True,
        )

        async def test_jitter():
            # Run multiple times to check randomness
            delays = []
            for _ in range(10):
                delay = await backoff.calculate_delay(1, 100, 5000)
                delays.append(delay)

            # With 10% jitter, delays should vary around 200ms
            # Range: 180ms - 220ms
            for delay in delays:
                assert 180 <= delay <= 220, f"Delay {delay} outside jitter range"

            # Verify some variation exists
            assert min(delays) < max(delays), "No variation in jitter"

        asyncio.run(test_jitter())

    def test_exponential_backoff_caps_at_max_delay(self):
        """Test that exponential backoff caps at max_delay_ms."""
        backoff = ExponentialBackoff(
            base_delay_ms=100,
            max_delay_ms=500,
            exponential_base=2.0,
            jitter=False,
        )

        async def test_capping():
            # 5 attempts: 100, 200, 400, 800, 1600
            # Should cap at 500
            delay_0 = await backoff.calculate_delay(0, 100, 500)
            delay_1 = await backoff.calculate_delay(1, 100, 500)
            delay_2 = await backoff.calculate_delay(2, 100, 500)
            delay_3 = await backoff.calculate_delay(3, 100, 500)
            delay_4 = await backoff.calculate_delay(4, 100, 500)

            assert delay_0 == 100.0
            assert delay_1 == 200.0
            assert delay_2 == 400.0
            assert delay_3 == 500.0  # Capped
            assert delay_4 == 500.0  # Capped

        asyncio.run(test_capping())


class TestLinearBackoff:
    """Tests for LinearBackoff implementation."""

    def test_linear_backoff_calculates_delay_correctly(self):
        """Test that linear backoff increases linearly."""
        backoff = LinearBackoff(
            base_delay_ms=100,
            max_delay_ms=5000,
        )

        async def test_linear():
            delay_0 = await backoff.calculate_delay(0, 100, 5000)
            delay_1 = await backoff.calculate_delay(1, 100, 5000)
            delay_2 = await backoff.calculate_delay(2, 100, 5000)

            # Linear: 100, 200, 300
            assert delay_0 == 100.0
            assert delay_1 == 200.0
            assert delay_2 == 300.0

        asyncio.run(test_linear())

    def test_linear_backoff_caps_at_max_delay(self):
        """Test that linear backoff caps at max_delay_ms."""
        backoff = LinearBackoff(
            base_delay_ms=100,
            max_delay_ms=500,
        )

        async def test_capping():
            delay_0 = await backoff.calculate_delay(0, 100, 500)
            delay_1 = await backoff.calculate_delay(1, 100, 500)
            delay_2 = await backoff.calculate_delay(2, 100, 500)
            delay_3 = await backoff.calculate_delay(3, 100, 500)
            delay_4 = await backoff.calculate_delay(4, 100, 500)

            # Linear: 100, 200, 300, 400, 500
            assert delay_0 == 100.0
            assert delay_1 == 200.0
            assert delay_2 == 300.0
            assert delay_3 == 400.0
            assert delay_4 == 500.0

            # Next would cap
            delay_5 = await backoff.calculate_delay(5, 100, 500)
            assert delay_5 == 500.0  # Capped

        asyncio.run(test_capping())


class TestFixedBackoff:
    """Tests for FixedBackoff implementation."""

    def test_fixed_backoff_returns_constant_delay(self):
        """Test that fixed backoff always returns the same delay."""
        backoff = FixedBackoff(
            delay_ms=500,
        )

        async def test_fixed():
            delay_0 = await backoff.calculate_delay(0, 100, 5000)
            delay_1 = await backoff.calculate_delay(1, 100, 5000)
            delay_2 = await backoff.calculate_delay(2, 100, 5000)

            # Always 500ms
            assert delay_0 == 500.0
            assert delay_1 == 500.0
            assert delay_2 == 500.0

        asyncio.run(test_fixed())


# =============================================================================
# RetryExecutor Tests
# =============================================================================


class TestRetryExecutor:
    """Tests for RetryExecutor protocol and RetryExecutorImpl."""

    def test_execute_returns_success_on_first_attempt(self):
        """Test that execute returns success on first attempt."""
        backoff = ExponentialBackoff(base_delay_ms=10, max_delay_ms=100)
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
        )

        async def test_success():
            async def success_func():
                return Ok("success")

            result = await retry.execute(success_func)

            assert result.is_ok()
            assert result.unwrap() == "success"

            # Check stats
            stats = await retry.get_stats()
            assert stats["successful_calls"] == 1
            assert stats["failed_calls"] == 0
            assert stats["retry_count"] == 0

        asyncio.run(test_success())

    def test_execute_retries_on_transient_failure(self):
        """Test that execute retries on transient failures."""
        backoff = ExponentialBackoff(base_delay_ms=10, max_delay_ms=100)
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
            transient_errors={TimeoutError, Exception},
        )

        async def test_retry():
            attempt_count = 0

            async def failing_then_success():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:
                    raise TimeoutError("Transient error")
                return Ok("success after retry")

            result = await retry.execute(failing_then_success)

            assert result.is_ok()
            assert result.unwrap() == "success after retry"
            assert attempt_count == 3

            # Check stats
            stats = await retry.get_stats()
            assert stats["successful_calls"] == 1
            assert stats["failed_calls"] == 0
            assert stats["retry_count"] == 2

        asyncio.run(test_retry())

    def test_execute_returns_permanent_error_immediately(self):
        """Test that execute returns permanent error without retry."""
        backoff = ExponentialBackoff(base_delay_ms=10, max_delay_ms=100)
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
            transient_errors={TimeoutError},  # ValueError is not transient
        )

        async def test_permanent():
            attempt_count = 0

            async def permanent_error_func():
                nonlocal attempt_count
                attempt_count += 1
                raise ValueError("Permanent error")

            result = await retry.execute(permanent_error_func)

            assert result.is_err()
            assert "Permanent error" in result.error
            assert attempt_count == 1  # No retries

            # Check stats
            stats = await retry.get_stats()
            assert stats["successful_calls"] == 0
            assert stats["failed_calls"] == 1
            assert stats["retry_count"] == 0

        asyncio.run(test_permanent())

    def test_execute_respects_max_attempts(self):
        """Test that execute respects max_attempts limit."""
        backoff = ExponentialBackoff(base_delay_ms=10, max_delay_ms=100)
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
            transient_errors={TimeoutError},
        )

        async def test_max_attempts():
            attempt_count = 0

            async def always_failing():
                nonlocal attempt_count
                attempt_count += 1
                raise TimeoutError("Always fails")

            result = await retry.execute(always_failing)

            assert result.is_err()
            assert "MAX_RETRIES_EXCEEDED" in result.error
            assert attempt_count == 3  # Attempted max 3 times

            # Check stats
            stats = await retry.get_stats()
            assert stats["successful_calls"] == 0
            assert stats["failed_calls"] == 1
            assert stats["retry_count"] == 3

        asyncio.run(test_max_attempts())

    def test_execute_uses_backoff_between_retries(self):
        """Test that execute uses backoff delay between retries."""
        backoff = ExponentialBackoff(
            base_delay_ms=50,
            max_delay_ms=500,
            jitter=False,
        )
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
            transient_errors={TimeoutError},
        )

        async def test_backoff():
            attempt_count = 0
            attempt_times = []

            async def failing_func():
                nonlocal attempt_count
                attempt_count += 1
                attempt_times.append(datetime.now())
                raise TimeoutError("Transient error")

            result = await retry.execute(failing_func)

            assert result.is_err()
            assert attempt_count == 3

            # Check delays between attempts
            if len(attempt_times) >= 2:
                delay_0_1 = (attempt_times[1] - attempt_times[0]).total_seconds()
                # Should be at least 50ms
                assert delay_0_1 >= 0.04, f"Delay too short: {delay_0_1}s"

            if len(attempt_times) >= 3:
                delay_1_2 = (attempt_times[2] - attempt_times[1]).total_seconds()
                # Should be at least 100ms (exponential: 50 * 2)
                assert delay_1_2 >= 0.09, f"Delay too short: {delay_1_2}s"

        asyncio.run(test_backoff())

    def test_execute_checks_circuit_breaker(self):
        """Test that execute checks circuit breaker before retry."""
        backoff = ExponentialBackoff(base_delay_ms=10, max_delay_ms=100)

        # Mock circuit breaker that returns is_closed=True (blocks calls)
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_closed = AsyncMock(return_value=True)

        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
            circuit_breaker=mock_circuit_breaker,
        )

        async def test_circuit():
            attempt_count = 0

            async def success_func():
                nonlocal attempt_count
                attempt_count += 1
                return Ok("success")

            result = await retry.execute(success_func)

            assert result.is_err()
            assert "CIRCUIT_OPEN" in result.error
            assert attempt_count == 0  # Function never called

            # Circuit breaker was checked
            mock_circuit_breaker.is_closed.assert_called_once()

        asyncio.run(test_circuit())

    def test_get_stats_returns_statistics(self):
        """Test that get_stats returns retry statistics."""
        backoff = ExponentialBackoff(base_delay_ms=10, max_delay_ms=100)
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
        )

        async def test_stats():
            stats = await retry.get_stats()

            assert "total_calls" in stats
            assert "successful_calls" in stats
            assert "failed_calls" in stats
            assert "retry_count" in stats

            # Initial values
            assert stats["total_calls"] == 0
            assert stats["successful_calls"] == 0
            assert stats["failed_calls"] == 0
            assert stats["retry_count"] == 0

        asyncio.run(test_stats())

    def test_stats_increment_on_success(self):
        """Test that stats increment on successful calls."""
        backoff = ExponentialBackoff(base_delay_ms=10, max_delay_ms=100)
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
        )

        async def test_increment():
            async def success_func():
                return Ok("success")

            await retry.execute(success_func)

            stats = await retry.get_stats()
            assert stats["total_calls"] == 1
            assert stats["successful_calls"] == 1
            assert stats["failed_calls"] == 0
            assert stats["retry_count"] == 0

        asyncio.run(test_increment())

    def test_stats_increment_on_failure(self):
        """Test that stats increment on failed calls."""
        backoff = ExponentialBackoff(base_delay_ms=10, max_delay_ms=100)
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
            transient_errors={TimeoutError},
        )

        async def test_failure_stats():
            async def failing_func():
                raise TimeoutError("Always fails")

            await retry.execute(failing_func)

            stats = await retry.get_stats()
            assert stats["total_calls"] == 1
            assert stats["successful_calls"] == 0
            assert stats["failed_calls"] == 1
            assert stats["retry_count"] == 3

        asyncio.run(test_failure_stats())

    def test_stats_track_retry_count(self):
        """Test that stats track retry count accurately."""
        backoff = ExponentialBackoff(base_delay_ms=10, max_delay_ms=100)
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
            transient_errors={TimeoutError},
        )

        async def test_retry_stats():
            attempt_count = 0

            async def twice_failing():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:
                    raise TimeoutError("Transient error")
                return Ok("success")

            await retry.execute(twice_failing)

            stats = await retry.get_stats()
            assert stats["total_calls"] == 1
            assert stats["successful_calls"] == 1
            assert stats["failed_calls"] == 0
            assert stats["retry_count"] == 2

        asyncio.run(test_retry_stats())


# =============================================================================
# Integration Tests
# =============================================================================


class TestRetryIntegration:
    """Integration tests for retry with backoff."""

    def test_retry_with_backoff_integration(self):
        """Test retry executor with exponential backoff integration."""
        backoff = ExponentialBackoff(
            base_delay_ms=10,
            max_delay_ms=100,
            jitter=False,
        )
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
            transient_errors={TimeoutError},
        )

        async def test_integration():
            attempt_count = 0

            async def twice_failing():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:
                    raise TimeoutError("Transient error")
                return Ok("success after retry")

            result = await retry.execute(twice_failing)

            assert result.is_ok()
            assert result.unwrap() == "success after retry"
            assert attempt_count == 3

            # Verify stats
            stats = await retry.get_stats()
            assert stats["successful_calls"] == 1
            assert stats["retry_count"] == 2

        asyncio.run(test_integration())

    def test_retry_with_circuit_breaker_integration(self):
        """Test retry executor with circuit breaker integration."""
        from dawn_kestrel.llm.circuit_breaker import CircuitBreakerImpl

        # Create mock provider adapter
        mock_adapter = Mock()
        mock_adapter.get_provider_name = AsyncMock(return_value="test")

        # Create circuit breaker
        circuit_breaker = CircuitBreakerImpl(
            provider_adapter=mock_adapter,
            failure_threshold=10,
            half_open_threshold=5,
            timeout_seconds=60,
        )

        backoff = ExponentialBackoff(base_delay_ms=10, max_delay_ms=100)
        retry = RetryExecutorImpl(
            max_attempts=3,
            backoff=backoff,
            circuit_breaker=circuit_breaker,
            transient_errors={TimeoutError},
        )

        async def test_integration():
            # Circuit should be closed (blocks calls) by default
            is_closed = await circuit_breaker.is_closed()
            assert is_closed is True

            # Open circuit to allow calls
            await circuit_breaker.open()

            # Should succeed with retry
            attempt_count = 0

            async def twice_failing():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:
                    raise TimeoutError("Transient error")
                return Ok("success")

            result = await retry.execute(twice_failing)

            assert result.is_ok()
            assert result.unwrap() == "success"
            assert attempt_count == 3

        asyncio.run(test_integration())
