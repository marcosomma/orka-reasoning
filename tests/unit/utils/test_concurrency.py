"""Unit tests for orka.utils.concurrency."""

import asyncio
from unittest.mock import Mock, AsyncMock, patch

import pytest

from orka.utils.concurrency import ConcurrencyManager

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestConcurrencyManager:
    """Test suite for ConcurrencyManager class."""

    def test_init(self):
        """Test ConcurrencyManager initialization."""
        manager = ConcurrencyManager(max_concurrency=5)
        
        assert manager.semaphore._value == 5
        assert manager._active_tasks == set()

    def test_init_default(self):
        """Test ConcurrencyManager initialization with default max_concurrency."""
        manager = ConcurrencyManager()
        
        assert manager.semaphore._value == 10  # Default value

    @pytest.mark.asyncio
    async def test_run_with_timeout_success(self):
        """Test run_with_timeout with successful execution."""
        manager = ConcurrencyManager(max_concurrency=2)
        
        async def test_coro(value):
            await asyncio.sleep(0.01)
            return f"result_{value}"
        
        result = await manager.run_with_timeout(test_coro, timeout=1.0, value="test")
        
        assert result == "result_test"

    @pytest.mark.asyncio
    async def test_run_with_timeout_timeout_error(self):
        """Test run_with_timeout raises TimeoutError on timeout."""
        manager = ConcurrencyManager(max_concurrency=2)
        
        async def slow_coro():
            await asyncio.sleep(1.0)
            return "result"
        
        with pytest.raises(asyncio.TimeoutError):
            await manager.run_with_timeout(slow_coro, timeout=0.01)

    @pytest.mark.asyncio
    async def test_run_with_timeout_no_timeout(self):
        """Test run_with_timeout without timeout."""
        manager = ConcurrencyManager(max_concurrency=2)
        
        async def test_coro():
            await asyncio.sleep(0.01)
            return "result"
        
        result = await manager.run_with_timeout(test_coro, timeout=None)
        
        assert result == "result"

    @pytest.mark.asyncio
    async def test_run_with_timeout_exception(self):
        """Test run_with_timeout handles exceptions."""
        manager = ConcurrencyManager(max_concurrency=2)
        
        async def failing_coro():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            await manager.run_with_timeout(failing_coro)

    @pytest.mark.asyncio
    async def test_with_concurrency_decorator(self):
        """Test with_concurrency decorator."""
        manager = ConcurrencyManager(max_concurrency=2)
        
        @manager.with_concurrency(timeout=1.0)
        async def test_function(value):
            await asyncio.sleep(0.01)
            return f"result_{value}"
        
        result = await test_function("test")
        
        assert result == "result_test"

    @pytest.mark.asyncio
    async def test_with_concurrency_decorator_timeout(self):
        """Test with_concurrency decorator with timeout."""
        manager = ConcurrencyManager(max_concurrency=2)
        
        @manager.with_concurrency(timeout=0.01)
        async def slow_function():
            await asyncio.sleep(1.0)
            return "result"
        
        with pytest.raises(asyncio.TimeoutError):
            await slow_function()

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test shutdown method cancels active tasks."""
        manager = ConcurrencyManager(max_concurrency=2)
        
        async def long_task():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                pass
        
        # Start a task
        task = asyncio.create_task(manager.run_with_timeout(long_task, timeout=None))
        
        # Wait a bit for task to start
        await asyncio.sleep(0.01)
        
        # Shutdown should cancel tasks
        await manager.shutdown()
        
        # Task should be cancelled
        assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """Test that concurrency limit is enforced."""
        manager = ConcurrencyManager(max_concurrency=2)
        
        active_count = 0
        max_active = 0
        
        async def counting_task():
            nonlocal active_count, max_active
            active_count += 1
            max_active = max(max_active, active_count)
            await asyncio.sleep(0.1)
            active_count -= 1
        
        # Start 5 tasks
        tasks = [manager.run_with_timeout(counting_task) for _ in range(5)]
        await asyncio.gather(*tasks)
        
        # Max active should not exceed concurrency limit
        assert max_active <= 2

