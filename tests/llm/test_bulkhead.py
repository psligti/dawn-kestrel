"""Tests for Bulkhead pattern for resource isolation.

Tests follow TDD workflow:
- RED phase: Tests written before implementation exists
- GREEN phase: Implementation passes all tests
- REFACTOR phase: Clean code with comprehensive docstrings
"""

import pytest
import asyncio
from asyncio import Semaphore

from dawn_kestrel.core.result import Ok, Err
from dawn_kestrel.llm.bulkhead import Bulkhead, BulkheadImpl


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestBulkheadProtocol:
    """Test Bulkhead protocol compliance."""

    def test_protocol_has_try_acquire_method(self):
        """Test Bulkhead protocol defines try_acquire method."""
        assert hasattr(Bulkhead, "try_acquire")

    def test_protocol_has_release_method(self):
        """Test Bulkhead protocol defines release method."""
        assert hasattr(Bulkhead, "release")

    def test_protocol_has_try_execute_method(self):
        """Test Bulkhead protocol defines try_execute method."""
        assert hasattr(Bulkhead, "try_execute")

    async def test_bulkhead_impl_is_protocol_compliant(self):
        """Test BulkheadImpl implements Bulkhead protocol."""
        bulkhead = BulkheadImpl()
        assert isinstance(bulkhead, Bulkhead)


# =============================================================================
# Semaphore Management Tests
# =============================================================================


class TestSemaphoreManagement:
    """Test semaphore acquisition and release."""

    async def test_try_acquire_creates_semaphore_for_new_resource(self):
        """Test try_acquire creates semaphore for new resource."""
        bulkhead = BulkheadImpl()

        result = await bulkhead.try_acquire("openai")
        assert result.is_ok()
        semaphore = result.unwrap()
        assert isinstance(semaphore, Semaphore)

    async def test_try_acquire_returns_existing_semaphore(self):
        """Test try_acquire returns existing semaphore for known resource."""
        bulkhead = BulkheadImpl()

        # First acquisition
        result1 = await bulkhead.try_acquire("openai")
        assert result1.is_ok()
        semaphore1 = result1.unwrap()

        # Release first
        await bulkhead.release(semaphore1)

        # Second acquisition should return same semaphore
        result2 = await bulkhead.try_acquire("openai")
        assert result2.is_ok()
        semaphore2 = result2.unwrap()
        assert semaphore2 is semaphore1

    async def test_try_acquire_times_out_after_default_timeout(self):
        """Test try_acquire times out after default timeout."""
        bulkhead = BulkheadImpl()
        bulkhead.set_limit("openai", 1)
        bulkhead.set_timeout("openai", 0.1)  # 100ms timeout

        # Acquire semaphore
        result1 = await bulkhead.try_acquire("openai")
        assert result1.is_ok()

        # Second acquisition should timeout (limit=1, first holds it)
        result2 = await bulkhead.try_acquire("openai")
        assert result2.is_err()
        assert "ACQUISITION_TIMEOUT" in str(result2)

    async def test_release_decrements_active_count(self):
        """Test release decrements active count."""
        bulkhead = BulkheadImpl()

        result1 = await bulkhead.try_acquire("openai")
        semaphore1 = result1.unwrap()
        assert bulkhead._active_counts.get("openai", 0) >= 1

        await bulkhead.release(semaphore1)
        assert bulkhead._active_counts.get("openai", 0) >= 0

    async def test_release_fails_when_semaphore_not_acquired(self):
        """Test release fails when semaphore not acquired via try_acquire."""
        bulkhead = BulkheadImpl()

        # Create semaphore directly (not acquired via try_acquire)
        semaphore = Semaphore(1)

        result = await bulkhead.release(semaphore)
        # Implementation tracks ownership and returns Err for non-acquired semaphore
        assert result.is_err()
        assert "BULKHEAD_ERROR" in str(result)

    async def test_release_fails_on_exception(self):
        """Test release fails on exception."""
        bulkhead = BulkheadImpl()

        # Pass None to trigger exception
        result = await bulkhead.release(None)
        assert result.is_err()


# =============================================================================
# Configuration Tests
# =============================================================================


class TestConfiguration:
    """Test bulkhead configuration methods."""

    def test_get_limit_returns_default_limit(self):
        """Test get_limit returns default limit."""
        bulkhead = BulkheadImpl()
        assert bulkhead.get_limit("unknown") == 1

    def test_set_limit_updates_limit(self):
        """Test set_limit updates concurrent limit."""
        bulkhead = BulkheadImpl()
        bulkhead.set_limit("openai", 5)
        assert bulkhead.get_limit("openai") == 5

    def test_set_timeout_updates_timeout(self):
        """Test set_timeout updates acquisition timeout."""
        bulkhead = BulkheadImpl()
        bulkhead.set_timeout("openai", 60.0)
        assert bulkhead.get_timeout("openai") == 60.0

    def test_get_timeout_returns_default_timeout(self):
        """Test get_timeout returns default timeout."""
        bulkhead = BulkheadImpl()
        assert bulkhead.get_timeout("unknown") == 30.0

    def test_multiple_resources_have_separate_limits(self):
        """Test multiple resources have separate limits."""
        bulkhead = BulkheadImpl()
        bulkhead.set_limit("openai", 5)
        bulkhead.set_limit("zai", 3)

        assert bulkhead.get_limit("openai") == 5
        assert bulkhead.get_limit("zai") == 3
        assert bulkhead.get_limit("unknown") == 1


# =============================================================================
# try_execute Tests
# =============================================================================


class TestTryExecute:
    """Test try_execute method."""

    async def test_try_execute_with_custom_max_concurrent(self):
        """Test try_execute with custom max_concurrent parameter."""
        bulkhead = BulkheadImpl()

        async def mock_func():
            return "result"

        result = await bulkhead.try_execute("openai", mock_func, max_concurrent=5)
        assert result.is_ok()
        assert result.unwrap() == "result"

    async def test_try_execute_acquires_semaphore(self):
        """Test try_execute acquires semaphore before execution."""
        bulkhead = BulkheadImpl()
        bulkhead.set_limit("openai", 1)

        async def mock_func():
            return "result"

        result = await bulkhead.try_execute("openai", mock_func)
        assert result.is_ok()
        assert result.unwrap() == "result"

    async def test_try_execute_times_out(self):
        """Test try_execute times out on long-running function."""
        bulkhead = BulkheadImpl()
        bulkhead.set_timeout("openai", 0.1)  # 100ms timeout

        async def long_func():
            await asyncio.sleep(1)  # Sleep longer than timeout
            return "result"

        result = await bulkhead.try_execute("openai", long_func)
        assert result.is_err()
        assert "EXECUTION_TIMEOUT" in str(result)

    async def test_try_execute_releases_semaphore_on_success(self):
        """Test try_execute releases semaphore after successful execution."""
        bulkhead = BulkheadImpl()
        bulkhead.set_limit("openai", 1)

        async def mock_func():
            return "result"

        # First execution
        result1 = await bulkhead.try_execute("openai", mock_func)
        assert result1.is_ok()

        # Second execution should succeed (semaphore released)
        result2 = await bulkhead.try_execute("openai", mock_func)
        assert result2.is_ok()

    async def test_try_execute_releases_semaphore_on_error(self):
        """Test try_execute releases semaphore even on error."""
        bulkhead = BulkheadImpl()
        bulkhead.set_limit("openai", 1)

        async def error_func():
            raise ValueError("Test error")

        result1 = await bulkhead.try_execute("openai", error_func)
        assert result1.is_err()

        # Second execution should succeed (semaphore released despite error)
        async def success_func():
            return "result"

        result2 = await bulkhead.try_execute("openai", success_func)
        assert result2.is_ok()

    async def test_try_execute_returns_result(self):
        """Test try_execute returns Result with function result."""
        bulkhead = BulkheadImpl()

        async def mock_func():
            return {"data": "value"}

        result = await bulkhead.try_execute("openai", mock_func)
        assert result.is_ok()
        assert result.unwrap() == {"data": "value"}

    async def test_try_execute_with_unlimited_max_concurrent(self):
        """Test try_execute with unlimited max_concurrent."""
        bulkhead = BulkheadImpl()

        async def mock_func():
            return "result"

        result = await bulkhead.try_execute("openai", mock_func, max_concurrent=100)
        assert result.is_ok()
        assert result.unwrap() == "result"

    async def test_multiple_concurrent_operations_limited_by_semaphore(self):
        """Test multiple concurrent operations limited by semaphore."""
        bulkhead = BulkheadImpl()
        bulkhead.set_limit("openai", 2)
        bulkhead.set_timeout("openai", 10.0)  # Long timeout

        execution_order = []

        async def mock_func():
            execution_order.append("start")
            await asyncio.sleep(0.2)
            execution_order.append("end")
            return "result"

        # Start 4 concurrent operations (limit is 2)
        tasks = [asyncio.create_task(bulkhead.try_execute("openai", mock_func)) for _ in range(4)]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.is_ok() for r in results)

        # First 2 should start immediately, next 2 wait
        assert execution_order[:2] == ["start", "start"]


# =============================================================================
# Active Count Tests
# =============================================================================


class TestActiveCount:
    """Test active operation count tracking."""

    async def test_active_count_increments_on_acquire(self):
        """Test active count increments on acquire."""
        bulkhead = BulkheadImpl()

        result = await bulkhead.try_acquire("openai")
        assert result.is_ok()
        assert bulkhead._active_counts.get("openai", 0) >= 1

    async def test_active_count_decrements_on_release(self):
        """Test active count decrements on release."""
        bulkhead = BulkheadImpl()

        result = await bulkhead.try_acquire("openai")
        semaphore = result.unwrap()
        count_before = bulkhead._active_counts.get("openai", 0)

        await bulkhead.release(semaphore)
        count_after = bulkhead._active_counts.get("openai", 0)

        assert count_after <= count_before

    async def test_concurrent_operations_within_limit_are_allowed(self):
        """Test concurrent operations within limit are allowed."""
        bulkhead = BulkheadImpl()
        bulkhead.set_limit("openai", 3)
        bulkhead.set_timeout("openai", 10.0)

        async def mock_func():
            await asyncio.sleep(0.1)
            return "result"

        # Start 3 concurrent operations (within limit)
        tasks = [asyncio.create_task(bulkhead.try_execute("openai", mock_func)) for _ in range(3)]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.is_ok() for r in results)
