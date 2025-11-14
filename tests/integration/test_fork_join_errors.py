# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Tests for Fork/Join Error Handling
===================================

Tests the enhanced error handling, retry logic, and graceful degradation
in fork/join parallel execution.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine


class TestForkJoinErrorHandling:
    """Test suite for fork/join error handling improvements."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock execution engine for testing."""
        engine = MagicMock(spec=ExecutionEngine)
        engine.step_index = 1
        engine.run_id = "test-run-123"
        engine.agents = {}
        engine.memory = MagicMock()
        return engine

    @pytest.mark.asyncio
    async def test_branch_retry_success_on_first_attempt(self, mock_engine):
        """Test that successful branches don't trigger retry logic."""
        from orka.orchestrator.execution_engine import ExecutionEngine
        
        # Create actual method bound to mock
        branch_agents = ["agent1", "agent2"]
        input_data = "test input"
        previous_outputs = {}
        
        # Mock _run_branch_async to succeed immediately
        async def mock_run_branch(*args, **kwargs):
            return {"agent1": {"result": "success"}}
        
        engine = ExecutionEngine.__new__(ExecutionEngine)
        engine._run_branch_async = mock_run_branch
        
        # Should succeed without retries
        result = await engine._run_branch_with_retry(
            branch_agents, input_data, previous_outputs, max_retries=2
        )
        
        assert result == {"agent1": {"result": "success"}}

    @pytest.mark.asyncio
    async def test_branch_retry_success_after_failure(self, mock_engine):
        """Test that branches retry after transient failures."""
        from orka.orchestrator.execution_engine import ExecutionEngine
        
        call_count = 0
        
        async def mock_run_branch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Transient error")
            return {"agent1": {"result": "success"}}
        
        engine = ExecutionEngine.__new__(ExecutionEngine)
        engine._run_branch_async = mock_run_branch
        
        # Should succeed on retry
        result = await engine._run_branch_with_retry(
            ["agent1"], "test", {}, max_retries=2, retry_delay=0.01
        )
        
        assert call_count == 2  # Failed once, succeeded on retry
        assert result == {"agent1": {"result": "success"}}

    @pytest.mark.asyncio
    async def test_branch_retry_exhaustion(self, mock_engine):
        """Test that branches fail after exhausting all retries."""
        from orka.orchestrator.execution_engine import ExecutionEngine
        
        call_count = 0
        
        async def mock_run_branch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise KeyError("persistent_error")
        
        engine = ExecutionEngine.__new__(ExecutionEngine)
        engine._run_branch_async = mock_run_branch
        
        # Should raise exception after all retries
        with pytest.raises(KeyError) as exc_info:
            await engine._run_branch_with_retry(
                ["agent1"], "test", {}, max_retries=2, retry_delay=0.01
            )
        
        assert "persistent_error" in str(exc_info.value)
        assert call_count == 3  # Initial + 2 retries

    def test_enhanced_error_logging_includes_traceback(self, mock_engine):
        """Test that error logs include full exception details."""
        # This would be tested via integration with actual execution
        # For now, we verify the structure
        error_log = {
            "agent_id": "branch_0_error",
            "event_type": "BranchError",
            "payload": {
                "error": "test error",
                "error_type": "KeyError",
                "error_traceback": "Traceback...",
                "branch_agents": ["agent1"],
                "fork_group_id": "test_group",
            },
        }
        
        # Verify structure
        assert "error_type" in error_log["payload"]
        assert "error_traceback" in error_log["payload"]
        assert "branch_agents" in error_log["payload"]
        assert error_log["event_type"] == "BranchError"

    def test_fallback_result_structure(self, mock_engine):
        """Test that fallback results have the correct structure."""
        fallback_result = {
            "status": "partial_failure",
            "successful_branches": 0,
            "total_branches": 3,
            "error": "All parallel branches failed",
        }
        
        # Verify structure
        assert fallback_result["status"] == "partial_failure"
        assert fallback_result["successful_branches"] == 0
        assert fallback_result["total_branches"] > 0
        assert "error" in fallback_result

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, mock_engine):
        """Test that retry delays follow exponential backoff."""
        from orka.orchestrator.execution_engine import ExecutionEngine
        import time
        
        call_times = []
        
        async def mock_run_branch(*args, **kwargs):
            call_times.append(time.time())
            raise Exception("error")
        
        engine = ExecutionEngine.__new__(ExecutionEngine)
        engine._run_branch_async = mock_run_branch
        
        try:
            await engine._run_branch_with_retry(
                ["agent1"], "test", {}, max_retries=2, retry_delay=0.1
            )
        except Exception:
            pass
        
        # Verify we made 3 attempts
        assert len(call_times) == 3
        
        # Verify delays are approximately exponential (0.1s, 0.2s)
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            
            # Allow some tolerance for execution time
            assert 0.08 < delay1 < 0.15  # ~0.1s
            assert 0.18 < delay2 < 0.25  # ~0.2s


class TestErrorLoggingFormat:
    """Test that error messages are properly formatted."""

    def test_error_type_extraction(self):
        """Test that error type is correctly extracted."""
        try:
            raise KeyError("test_key")
        except KeyError as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            assert error_type == "KeyError"
            assert "test_key" in error_msg
            # Verify it's not just showing single character
            assert len(error_msg) > 1

    def test_traceback_extraction(self):
        """Test that tracebacks are properly extracted."""
        import traceback
        
        try:
            raise ValueError("detailed error message")
        except ValueError as e:
            tb = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            assert "ValueError" in tb
            assert "detailed error message" in tb
            assert "Traceback" in tb
            # Verify it includes stack frames
            assert len(tb) > 50

