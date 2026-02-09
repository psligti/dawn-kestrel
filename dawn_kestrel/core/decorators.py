"""Logging decorators and proxies for configurable, centralized logging.

This module implements the Decorator/Proxy pattern for logging, providing
configurable logging that can be applied to any function or callable.

Features:
- LoggingConfig: Centralized configuration for logging behavior
- log_function: Decorator to add logging to any async function
- FunctionProxy: Proxy to wrap callables with logging
- Support for different log levels (DEBUG, INFO, WARNING, ERROR)
- Configurable output (console, file, silent via Python logging)
- Optional arguments, results, and timestamps in logs
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Protocol, runtime_checkable
from datetime import datetime
import logging


# ============ Configuration ============


class LoggingConfig:
    """Configuration for logging behavior.

    This class encapsulates all configuration options for logging decorators
    and proxies, enabling fine-grained control over what gets logged and how.

    Attributes:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
        enabled: Enable/disable logging (useful for toggling at runtime).
        prefix: Prefix for all log messages.
        include_args: Include function arguments in entry logs.
        include_result: Include function return value in exit logs.
        include_timestamp: Include timestamp in log messages.
    """

    def __init__(
        self,
        level: int = logging.INFO,
        enabled: bool = True,
        prefix: str = "",
        include_args: bool = True,
        include_result: bool = True,
        include_timestamp: bool = False,
    ):
        self.level = level
        self.enabled = enabled
        self.prefix = prefix
        self.include_args = include_args
        self.include_result = include_result
        self.include_timestamp = include_timestamp


# ============ Decorator ============


def log_function(
    level: int = logging.INFO,
    enabled: bool = True,
    prefix: str = "",
    include_args: bool = True,
    include_result: bool = True,
    include_timestamp: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to add logging to async function calls.

    This decorator wraps any async function with configurable logging behavior,
    logging function entry, exit (result), and exceptions.

    Args:
        level: Logging level (default: logging.INFO).
        enabled: Enable/disable logging (default: True).
        prefix: Prefix for log messages.
        include_args: Include function arguments in logs.
        include_result: Include function return value in logs.
        include_timestamp: Include timestamp in logs.

    Returns:
        Decorator function that wraps async callables.

    Example:
        @log_function(level=logging.DEBUG, prefix="[API]")
        async def my_function(x: int, y: int) -> int:
            return x + y
    """
    config = LoggingConfig(
        level=level,
        enabled=enabled,
        prefix=prefix,
        include_args=include_args,
        include_result=include_result,
        include_timestamp=include_timestamp,
    )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not config.enabled:
                return await func(*args, **kwargs)

            logger = logging.getLogger(func.__module__)

            # Log entry
            message = ""
            if config.prefix:
                message = f"{config.prefix} "

            func_name = getattr(func, "__qualname__", getattr(func, "__name__", str(func)))
            message += f"Calling {func_name}"

            if config.include_args and args:
                # Truncate long args for readability
                args_str = str(args)[:100]
                message += f" args={args_str}"

            if config.include_args and kwargs:
                kwargs_str = str(kwargs)[:100]
                message += f" kwargs={kwargs_str}"

            if config.include_timestamp:
                message += f" at {datetime.now().isoformat()}"

            logger.log(config.level, message)

            try:
                # Call function
                result = await func(*args, **kwargs)

                # Log result
                if config.include_result:
                    result_message = f"{func_name} returned"
                    if config.prefix:
                        result_message = f"{config.prefix} {result_message}"
                    result_str = str(result)[:100]
                    result_message += f" {result_str}"
                    logger.log(config.level, result_message)

                return result
            except Exception as e:
                # Log exception
                error_message = f"{func_name} raised: {e}"
                if config.prefix:
                    error_message = f"{config.prefix} {error_message}"
                logger.error(error_message)
                raise

        return wrapper

    return decorator


# ============ Proxy ============


@runtime_checkable
class LoggingProxy(Protocol):
    """Protocol for logging proxy.

    This protocol defines the interface for proxies that wrap callables
    with logging behavior.
    """

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Proxy method call with logging."""
        ...


class FunctionProxy:
    """Proxy that wraps any callable with logging.

    This class implements the Proxy pattern, providing a surrogate for
    any callable that adds logging behavior without modifying the original.

    Attributes:
        _func: The wrapped function/callable.
        _level: Logging level for this proxy.
        _enabled: Enable/disable logging.
        _prefix: Prefix for log messages.
        _logger: Logger instance for this proxy.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        level: int = logging.INFO,
        enabled: bool = True,
        prefix: str = "",
    ):
        self._func = func
        self._level = level
        self._enabled = enabled
        self._prefix = prefix
        self._logger = logging.getLogger(func.__module__)

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the wrapped function with logging.

        Logs function entry, result, and exceptions if logging is enabled.

        Args:
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The result of calling the wrapped function.

        Raises:
            Any exception raised by the wrapped function.
        """
        if not self._enabled:
            # If function is not async, call it directly
            if not asyncio.iscoroutinefunction(self._func):
                return self._func(*args, **kwargs)
            return await self._func(*args, **kwargs)

        # Log call
        message = ""
        if self._prefix:
            message = f"{self._prefix} "
        func_name = getattr(self._func, "__name__", str(self._func))
        message += f"Calling {func_name}"

        self._logger.log(self._level, message)

        # Call function
        try:
            # Handle both sync and async functions
            if asyncio.iscoroutinefunction(self._func):
                result = await self._func(*args, **kwargs)
            else:
                result = self._func(*args, **kwargs)

            # Log result
            result_str = str(result)[:100]
            result_message = f"{func_name} returned: {result_str}"
            self._logger.log(self._level, result_message)

            return result
        except Exception as e:
            # Log exception
            self._logger.error(f"{func_name} raised: {e}")
            raise


def create_logging_proxy(
    func: Callable[..., Any],
    level: int = logging.INFO,
    enabled: bool = True,
    prefix: str = "",
) -> FunctionProxy:
    """Create a logging proxy for a function.

    This factory function creates a FunctionProxy instance with the specified
    configuration, wrapping the provided callable with logging behavior.

    Args:
        func: Function to wrap.
        level: Logging level.
        enabled: Enable/disable logging.
        prefix: Prefix for log messages.

    Returns:
        FunctionProxy instance that wraps the function.

    Example:
        def add(x: int, y: int) -> int:
            return x + y

        proxy = create_logging_proxy(add, level=logging.DEBUG)
        result = await proxy(5, 10)
    """
    return FunctionProxy(func, level=level, enabled=enabled, prefix=prefix)


# Import asyncio for iscoroutinefunction check
import asyncio
