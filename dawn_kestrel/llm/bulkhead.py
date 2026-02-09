"""Bulkhead pattern for resource isolation.

Bulkhead provides resource isolation by limiting concurrent operations
per resource using semaphores. This prevents resource exhaustion from
too many concurrent requests.

Bulkhead pattern is useful for:
- Limiting concurrent API calls to a provider
- Preventing resource exhaustion
- Isolating failures to specific resources
- Managing rate limits and quotas

This module provides:
- Bulkhead protocol for bulkhead interface
- BulkheadImpl for concurrent operation limiting
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Protocol, runtime_checkable

from dawn_kestrel.core.result import Ok, Err, Result


logger = logging.getLogger(__name__)


# =============================================================================
# Bulkhead Protocol
# =============================================================================


@runtime_checkable
class Bulkhead(Protocol):
    """Protocol for bulkhead resource isolation.

    Limits concurrent operations per resource using semaphores.
    Prevents resource exhaustion from too many concurrent requests.

    Example:
        bulkhead = BulkheadImpl()
        bulkhead.set_limit("openai", 5)  # Max 5 concurrent calls

        # Execute function with concurrent limiting
        async def llm_call():
            return await provider.generate_response(...)

        result = await bulkhead.try_execute("openai", llm_call)
        if result.is_ok():
            response = result.unwrap()
    """

    async def try_acquire(self, resource: str) -> Result[asyncio.Semaphore]:
        """Try to acquire semaphore for resource.

        Args:
            resource: Resource identifier (e.g., provider name).

        Returns:
            Result[Semaphore]: Semaphore on success, Err if acquisition times out.
        """
        ...

    async def release(self, semaphore: asyncio.Semaphore) -> Result[None]:
        """Release semaphore after operation completes.

        Args:
            semaphore: Semaphore acquired via try_acquire().

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        ...

    async def try_execute(
        self,
        resource: str,
        func: Callable[..., Any],
        max_concurrent: int | None = None,
    ) -> Result[Any]:
        """Execute function with concurrent limit.

        Acquires semaphore before execution, releases after completion.

        Args:
            resource: Resource identifier.
            func: Async function to execute.
            max_concurrent: Max concurrent operations (overrides set_limit).

        Returns:
            Result[Any]: Result of function execution.
        """
        ...


# =============================================================================
# BulkheadImpl
# =============================================================================


class BulkheadImpl:
    """Bulkhead implementation with per-resource semaphores.

    Tracks active operations per resource and limits concurrency using
    semaphores. Each resource has its own semaphore and configuration.

    Example:
        bulkhead = BulkheadImpl()
        bulkhead.set_limit("openai", 5)  # Max 5 concurrent calls
        bulkhead.set_timeout("openai", 60)  # 60s acquisition timeout

        async def llm_call():
            return await provider.generate_response(...)

        result = await bulkhead.try_execute("openai", llm_call)
        if result.is_ok():
            response = result.unwrap()

    Thread Safety:
        Not thread-safe. Suitable for single-process async use.
    """

    def __init__(self):
        """Initialize bulkhead."""
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._limits: dict[str, int] = {}
        self._active_counts: dict[str, int] = {}
        self._timeouts: dict[str, float] = {}
        self._managed_semaphores: set[asyncio.Semaphore] = set()
        self._default_limit = 1  # Default: 1 concurrent op per resource
        self._default_timeout = 30.0  # Default: 30 seconds

    def set_limit(self, resource: str, limit: int) -> None:
        """Set concurrent limit for resource.

        Args:
            resource: Resource identifier.
            limit: Max concurrent operations.
        """
        self._limits[resource] = limit

    def set_timeout(self, resource: str, timeout: float) -> None:
        """Set acquisition timeout for resource.

        Args:
            resource: Resource identifier.
            timeout: Timeout in seconds.
        """
        self._timeouts[resource] = timeout

    def get_limit(self, resource: str) -> int:
        """Get current limit for resource.

        Args:
            resource: Resource identifier.

        Returns:
            Concurrent limit (default 1).
        """
        return self._limits.get(resource, self._default_limit)

    def get_timeout(self, resource: str) -> float:
        """Get current timeout for resource.

        Args:
            resource: Resource identifier.

        Returns:
            Timeout in seconds (default 30.0).
        """
        return self._timeouts.get(resource, self._default_timeout)

    async def try_acquire(self, resource: str) -> Result[asyncio.Semaphore]:
        """Try to acquire semaphore with timeout.

        Creates semaphore if not exists, then acquires it.

        Args:
            resource: Resource identifier.

        Returns:
            Result[Semaphore]: Semaphore on success, Err if acquisition times out.
        """
        try:
            limit = self.get_limit(resource)
            timeout = self.get_timeout(resource)

            if resource not in self._semaphores:
                self._semaphores[resource] = asyncio.Semaphore(limit)

            semaphore = self._semaphores[resource]

            try:
                await asyncio.wait_for(semaphore.acquire(), timeout=timeout)

                self._managed_semaphores.add(semaphore)
                self._active_counts[resource] = self._active_counts.get(resource, 0) + 1

                return Ok(semaphore)
            except asyncio.TimeoutError:
                return Err(
                    f"Failed to acquire semaphore for {resource} after {timeout}s",
                    code="ACQUISITION_TIMEOUT",
                )
        except Exception as e:
            logger.error(f"Failed to acquire semaphore for {resource}: {e}", exc_info=True)
            return Err(f"Failed to acquire semaphore for {resource}: {e}", code="BULKHEAD_ERROR")

    async def release(self, semaphore: asyncio.Semaphore) -> Result[None]:
        """Release semaphore after operation.

        Decrements active count and releases semaphore.

        Args:
            semaphore: Semaphore acquired via try_acquire().

        Returns:
            Result[None]: Ok on success, Err on failure.
        """
        try:
            if semaphore not in self._managed_semaphores:
                return Err(
                    "Semaphore was not acquired via try_acquire",
                    code="BULKHEAD_ERROR",
                )

            semaphore.release()
            self._managed_semaphores.discard(semaphore)

            for resource, count in self._active_counts.items():
                if count > 0:
                    self._active_counts[resource] = max(0, count - 1)
                    break

            return Ok(None)
        except Exception as e:
            logger.error(f"Failed to release semaphore: {e}", exc_info=True)
            return Err(f"Failed to release semaphore: {e}", code="BULKHEAD_ERROR")

    async def try_execute(
        self,
        resource: str,
        func: Callable[..., Any],
        max_concurrent: int | None = None,
    ) -> Result[Any]:
        """Execute function with concurrent limiting.

        Acquires semaphore before execution, releases after completion.
        Handles exceptions and ensures semaphore is always released.

        Args:
            resource: Resource identifier.
            func: Async function to execute.
            max_concurrent: Max concurrent operations (overrides set_limit).

        Returns:
            Result[Any]: Result of function execution.
        """
        # Temporarily override limit if provided
        original_limit = self.get_limit(resource)
        if max_concurrent is not None:
            self.set_limit(resource, max_concurrent)

        try:
            # Acquire semaphore
            result = await self.try_acquire(resource)
            if result.is_err():
                return result

            semaphore = result.unwrap()

            # Execute function
            try:
                timeout = self.get_timeout(resource)
                result_value = await asyncio.wait_for(func(), timeout=timeout)
                return Ok(result_value)
            except asyncio.TimeoutError:
                return Err(f"Execution timeout for {resource}", code="EXECUTION_TIMEOUT")
            except Exception as e:
                logger.error(f"Function execution error: {e}", exc_info=True)
                return Err(f"Function execution error: {e}", code="EXECUTION_ERROR")
            finally:
                await self.release(semaphore)
        finally:
            if max_concurrent is not None:
                self.set_limit(resource, original_limit)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "Bulkhead",
    "BulkheadImpl",
]
