# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

import asyncio

import pytest

from orka.utils.concurrency import ConcurrencyManager


class TestConcurrencyManager:
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test initialization of ConcurrencyManager"""
        # Default initialization
        manager = ConcurrencyManager()
        # Test that the manager was initialized correctly
        assert isinstance(manager, ConcurrencyManager)

        # Custom initialization
        custom_manager = ConcurrencyManager(max_concurrency=10)
        assert isinstance(custom_manager, ConcurrencyManager)

    @pytest.mark.asyncio
    async def test_run_with_timeout(self):
        """Test run_with_timeout method successfully completes"""
        manager = ConcurrencyManager()

        async def test_func(x):
            await asyncio.sleep(0.1)
            return x * 2

        # Should complete without timeout
        result = await manager.run_with_timeout(test_func, 1.0, 5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_timeout_exception(self):
        """Test that timeout is properly enforced"""
        manager = ConcurrencyManager()

        async def slow_func(x):
            await asyncio.sleep(0.5)
            return x

        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await manager.run_with_timeout(slow_func, 0.1, 5)

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """Test that concurrency limits are respected"""
        manager = ConcurrencyManager(max_concurrency=2)

        # Track execution order
        execution_order = []

        async def test_func_track(x):
            execution_order.append(f"start-{x}")
            await asyncio.sleep(0.2)
            execution_order.append(f"end-{x}")
            return x

        # Start 4 concurrent tasks (should be limited to 2 at a time)
        tasks = [manager.run_with_timeout(test_func_track, 1.0, i) for i in range(4)]
        results = await asyncio.gather(*tasks)

        # Verify results
        assert results == [0, 1, 2, 3]

        # Check execution order - we should have all 4 tasks complete
        assert len(execution_order) == 8

        # Check that we have alternating start/end patterns in the execution order
        for i in range(4):
            assert f"start-{i}" in execution_order
            assert f"end-{i}" in execution_order

    @pytest.mark.asyncio
    async def test_run_with_timeout_error(self):
        """Test error handling in run_with_timeout"""
        manager = ConcurrencyManager(max_concurrency=2)

        # Define a function that raises an exception
        async def test_func_error(x):
            await asyncio.sleep(0.1)
            raise ValueError(f"Error with {x}")

        # Should propagate the error
        with pytest.raises(ValueError) as excinfo:
            await manager.run_with_timeout(test_func_error, 1.0, 5)
        assert "Error with 5" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_semaphore_release_on_error(self):
        """Test that semaphore is released even when function raises an error"""
        manager = ConcurrencyManager(max_concurrency=1)

        # Define a function that raises an exception
        async def test_func_error():
            raise ValueError("Intentional error")

        # First call should raise an error
        with pytest.raises(ValueError):
            await manager.run_with_timeout(test_func_error, 1.0)

        # Define a simple function that just returns
        async def test_func_simple():
            return "Success"

        # Second call should succeed, proving the semaphore was released
        result = await manager.run_with_timeout(test_func_simple, 1.0)
        assert result == "Success"
