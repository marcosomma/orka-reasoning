import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConcurrencyManager:
    """Manages concurrency and timeouts for async operations."""

    def __init__(self, max_concurrency: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self._active_tasks: set[asyncio.Task] = set()

    async def run_with_timeout(
        self,
        coro: Callable[..., Any],
        timeout: Optional[float] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Run a coroutine with semaphore and timeout control."""
        async with self.semaphore:
            task = asyncio.create_task(coro(*args, **kwargs))
            self._active_tasks.add(task)
            try:
                if timeout is not None:
                    return await asyncio.wait_for(task, timeout=timeout)
                return await task
            except asyncio.TimeoutError:
                logger.warning(f"Operation timed out after {timeout} seconds")
                raise
            finally:
                self._active_tasks.remove(task)

    def with_concurrency(
        self, timeout: Optional[float] = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to add concurrency and timeout control to a function."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self.run_with_timeout(func, timeout, *args, **kwargs)

            return wrapper

        return decorator

    async def shutdown(self) -> None:
        """Cancel all active tasks."""
        for task in self._active_tasks:
            task.cancel()
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        self._active_tasks.clear()
