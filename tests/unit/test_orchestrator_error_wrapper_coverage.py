"""
Comprehensive tests for orchestrator error wrapper to increase coverage.
"""
import pytest
from unittest.mock import MagicMock, patch
from orka.orchestrator_error_wrapper import (
    OrkaError,
    AgentError,
    ConfigurationError,
    ExecutionError,
    ValidationError,
    TimeoutError as OrkaTimeoutError,
    wrap_orchestrator_errors,
    handle_agent_error,
)


class TestOrkaErrors:
    """Test custom error classes."""

    def test_orka_error_basic(self):
        """Test basic OrkaError."""
        error = OrkaError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_agent_error(self):
        """Test AgentError."""
        error = AgentError("Agent failed", agent_id="test_agent")
        assert "Agent failed" in str(error)
        assert error.agent_id == "test_agent"

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Invalid config")
        assert "Invalid config" in str(error)
        assert isinstance(error, OrkaError)

    def test_execution_error(self):
        """Test ExecutionError."""
        error = ExecutionError("Execution failed")
        assert "Execution failed" in str(error)
        assert isinstance(error, OrkaError)

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Validation failed")
        assert "Validation failed" in str(error)
        assert isinstance(error, OrkaError)

    def test_timeout_error(self):
        """Test TimeoutError."""
        error = OrkaTimeoutError("Operation timed out")
        assert "timed out" in str(error)
        assert isinstance(error, OrkaError)

    def test_error_with_cause(self):
        """Test error with underlying cause."""
        cause = ValueError("underlying error")
        error = OrkaError("Wrapped error", cause=cause)
        assert hasattr(error, '__cause__')

    def test_error_with_context(self):
        """Test error with additional context."""
        error = AgentError(
            "Agent failed",
            agent_id="test",
            context={"step": 1, "input": "test"}
        )
        assert error.agent_id == "test"
        assert error.context["step"] == 1


class TestErrorWrapper:
    """Test error wrapper decorator."""

    def test_wrap_orchestrator_errors_success(self):
        """Test wrapper with successful function."""
        @wrap_orchestrator_errors
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"

    def test_wrap_orchestrator_errors_catches_exception(self):
        """Test wrapper catches and wraps exceptions."""
        @wrap_orchestrator_errors
        def failing_function():
            raise ValueError("test error")
        
        with pytest.raises(OrkaError):
            failing_function()

    def test_wrap_orchestrator_errors_preserves_orka_errors(self):
        """Test wrapper preserves OrkaError subclasses."""
        @wrap_orchestrator_errors
        def raises_orka_error():
            raise AgentError("agent failed", agent_id="test")
        
        with pytest.raises(AgentError) as exc_info:
            raises_orka_error()
        assert exc_info.value.agent_id == "test"

    @pytest.mark.asyncio
    async def test_wrap_async_function(self):
        """Test wrapper with async function."""
        @wrap_orchestrator_errors
        async def async_function():
            return "async success"
        
        result = await async_function()
        assert result == "async success"

    @pytest.mark.asyncio
    async def test_wrap_async_function_error(self):
        """Test wrapper with failing async function."""
        @wrap_orchestrator_errors
        async def failing_async_function():
            raise RuntimeError("async error")
        
        with pytest.raises(OrkaError):
            await failing_async_function()


class TestErrorHandler:
    """Test error handling utilities."""

    def test_handle_agent_error_basic(self):
        """Test basic agent error handling."""
        error = ValueError("test error")
        handled = handle_agent_error(error, agent_id="test_agent")
        assert isinstance(handled, AgentError)
        assert handled.agent_id == "test_agent"

    def test_handle_agent_error_with_orka_error(self):
        """Test handling of existing OrkaError."""
        original_error = AgentError("original", agent_id="agent1")
        handled = handle_agent_error(original_error, agent_id="agent1")
        assert handled is original_error

    def test_handle_agent_error_with_context(self):
        """Test handling with additional context."""
        error = ValueError("test")
        context = {"step": 1, "input": "test input"}
        handled = handle_agent_error(error, agent_id="test", context=context)
        assert handled.context == context

    def test_error_chain_preservation(self):
        """Test that error chains are preserved."""
        cause = ValueError("root cause")
        error = RuntimeError("wrapped error")
        error.__cause__ = cause
        
        handled = handle_agent_error(error, agent_id="test")
        assert handled.__cause__ == error
