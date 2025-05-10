# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Concurrency Module
=================

This module provides tools for managing asynchronous operations with controlled concurrency
and timeouts in the OrKa framework. It centralizes concurrency management to avoid resource
overuse and improve reliability.

Key components:
- ConcurrencyManager: Central class for controlling task concurrency and timeouts
- Semaphore-based limiting of concurrent operations
- Task tracking and graceful shutdown capabilities
- Decorator pattern for easy application to async functions

Usage example:
```python
# Create a manager with max 5 concurrent tasks
concurrency = ConcurrencyManager(max_concurrency=5)

# Option 1: Use the run_with_timeout method directly
result = await concurrency.run_with_timeout(my_async_function, timeout=10.0, arg1="value")

# Option 2: Use as a decorator
@concurrency.with_concurrency(timeout=5.0)
async def my_function(param):
    # Function will run with concurrency control and 5s timeout
    return await some_async_operation(param)

# Graceful shutdown when needed
await concurrency.shutdown()
```
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")  # Type variable for generic return types


class ConcurrencyManager:
    """
    Manages concurrency and timeouts for async operations.

    This class provides a central mechanism to limit the number of concurrent tasks,
    apply timeouts, and track active tasks for graceful shutdown. It helps prevent
    resource exhaustion and improve reliability in async applications.

    Attributes:
        semaphore (asyncio.Semaphore): Controls the maximum number of concurrent tasks
        _active_tasks (set): Tracks all active tasks for later cleanup
    """

    def __init__(self, max_concurrency: int = 10):
        """
        Initialize a new concurrency manager.

        Args:
            max_concurrency: Maximum number of tasks allowed to run concurrently.
                            Default is 10. Set based on system resources and
                            expected load patterns.
        """
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self._active_tasks: set[asyncio.Task] = set()

    async def run_with_timeout(
        self,
        coro: Callable[..., Any],
        timeout: Optional[float] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Run a coroutine with semaphore-based concurrency control and optional timeout.

        This method:
        1. Acquires a semaphore to limit concurrent executions
        2. Creates and tracks the task
        3. Applies a timeout if specified
        4. Ensures cleanup even if exceptions occur

        Args:
            coro: The coroutine function to execute
            timeout: Maximum time in seconds to wait for completion (None = no timeout)
            *args: Positional arguments to pass to the coroutine
            **kwargs: Keyword arguments to pass to the coroutine

        Returns:
            The result of the coroutine execution

        Raises:
            asyncio.TimeoutError: If the operation exceeds the specified timeout
            Exception: Any exception raised by the coroutine itself
        """
        # Use semaphore to limit concurrent tasks
        async with self.semaphore:
            # Create and register the task
            task = asyncio.create_task(coro(*args, **kwargs))
            self._active_tasks.add(task)

            try:
                # Apply timeout if specified
                if timeout is not None:
                    return await asyncio.wait_for(task, timeout=timeout)
                return await task
            except asyncio.TimeoutError:
                # Log timeout events for monitoring and debugging
                logger.warning(f"Operation timed out after {timeout} seconds")
                raise
            finally:
                # Always clean up task tracking, even on exceptions
                self._active_tasks.remove(task)

    def with_concurrency(
        self, timeout: Optional[float] = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator to add concurrency and timeout control to an async function.

        This creates a decorator that can be applied to any async function to
        automatically add concurrency control and optional timeout handling.
        The decorator preserves the function's signature and docstring.

        Args:
            timeout: Default timeout in seconds to apply to the decorated function
                    (None = no timeout)

        Returns:
            A decorator function that applies concurrency control to the decorated function

        Example:
            ```python
            @concurrency_manager.with_concurrency(timeout=5.0)
            async def fetch_data(url):
                # This function will run with concurrency control and 5s timeout
                return await some_async_operation(url)
            ```
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            # Preserve the function's metadata (docstring, name, etc.)
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Apply the concurrency control and timeout
                return await self.run_with_timeout(func, timeout, *args, **kwargs)

            return wrapper

        return decorator

    async def shutdown(self) -> None:
        """
        Cancel all active tasks and perform cleanup.

        This method should be called during application shutdown to ensure all
        tasks managed by this ConcurrencyManager are properly cancelled and
        cleaned up. It:

        1. Cancels all tracked tasks
        2. Waits for them to complete (with cancellation)
        3. Clears the task tracking set

        Tasks will receive CancelledError which they should handle gracefully.

        Returns:
            None
        """
        # Cancel all tracked tasks
        for task in self._active_tasks:
            task.cancel()

        # Wait for all tasks to complete or be cancelled
        if self._active_tasks:
            # gather with return_exceptions to ensure we don't raise during shutdown
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        # Clear the tracking set
        self._active_tasks.clear()
