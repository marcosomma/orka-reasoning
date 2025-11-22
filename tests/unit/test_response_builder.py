"""Unit tests for orka.response_builder."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from orka.response_builder import ResponseBuilder

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestResponseBuilder:
    """Test suite for ResponseBuilder class."""

    def test_create_success_response(self):
        """Test create_success_response method."""
        result = ResponseBuilder.create_success_response(
            result="test result",
            component_id="test_component",
            component_type="agent",
        )
        
        assert result["result"] == "test result"
        assert result["status"] == "success"
        assert result["component_id"] == "test_component"
        assert result["component_type"] == "agent"
        assert "timestamp" in result

    def test_create_success_response_with_execution_time(self):
        """Test create_success_response with execution time."""
        start_time = 1000.0
        with patch('time.time', return_value=1000.5):
            result = ResponseBuilder.create_success_response(
                result="test",
                component_id="test",
                component_type="agent",
                execution_start_time=start_time,
            )
            
            assert "execution_time_ms" in result
            assert result["execution_time_ms"] == 500.0

    def test_create_success_response_with_optional_fields(self):
        """Test create_success_response with optional fields."""
        result = ResponseBuilder.create_success_response(
            result="test",
            component_id="test",
            component_type="agent",
            confidence="0.9",
            token_usage=100,
            cost_usd=0.001,
        )
        
        assert result["confidence"] == "0.9"
        assert result["token_usage"] == 100
        assert result["cost_usd"] == 0.001

    def test_create_error_response(self):
        """Test create_error_response method."""
        result = ResponseBuilder.create_error_response(
            error="Test error",
            component_id="test_component",
            component_type="agent",
        )
        
        assert result["status"] == "error"
        assert result["error"] == "Test error"
        assert result["component_id"] == "test_component"

    def test_create_error_response_with_execution_time(self):
        """Test create_error_response with execution time."""
        start_time = 1000.0
        with patch('time.time', return_value=1000.1):
            result = ResponseBuilder.create_error_response(
                error="Test error",
                component_id="test",
                component_type="agent",
                execution_start_time=start_time,
            )
            
            assert "execution_time_ms" in result

    def test_from_llm_agent_response(self):
        """Test from_llm_agent_response method."""
        legacy_response = {
            "response": "LLM output",
            "confidence": "0.9",
            "internal_reasoning": "Reasoning",
        }
        
        result = ResponseBuilder.from_llm_agent_response(legacy_response, "agent1")
        
        assert result["result"] == "LLM output"
        assert result["component_id"] == "agent1"
        assert result["component_type"] == "agent"

    def test_from_memory_agent_response(self):
        """Test from_memory_agent_response method."""
        legacy_response = {
            "memories": [{"key": "test", "value": "data"}],
            "num_results": 1,
        }
        
        result = ResponseBuilder.from_memory_agent_response(legacy_response, "memory1")
        
        assert result["memory_entries"] == [{"key": "test", "value": "data"}]
        assert result["component_id"] == "memory1"

    def test_from_node_response(self):
        """Test from_node_response method."""
        legacy_response = {
            "result": "node output",
        }
        
        result = ResponseBuilder.from_node_response(legacy_response, "node1")
        
        assert result["result"] == "node output"
        assert result["component_id"] == "node1"
        assert result["component_type"] == "node"

    def test_from_tool_response(self):
        """Test from_tool_response method."""
        legacy_response = "tool output"  # Can be any type
        
        result = ResponseBuilder.from_tool_response(legacy_response, "tool1")
        
        assert result["result"] == "tool output"  # Entire response becomes result
        assert result["component_id"] == "tool1"
        assert result["component_type"] == "tool"

    def test_validate_response_valid(self):
        """Test validate_response with valid response."""
        response = {
            "result": "test",
            "status": "success",
            "component_id": "test",
            "component_type": "agent",
            "timestamp": datetime.now(),
        }
        
        assert ResponseBuilder.validate_response(response) is True

    def test_validate_response_invalid(self):
        """Test validate_response with invalid response."""
        response = {
            "result": "test",
            # Missing required fields
        }
        
        assert ResponseBuilder.validate_response(response) is False

    def test_extract_legacy_fields(self):
        """Test extract_legacy_fields method."""
        response = {
            "result": "test",
            "status": "success",
            "response": "legacy response",
            "memories": ["memory1"],
        }
        
        legacy = ResponseBuilder.extract_legacy_fields(response)
        
        # Should map legacy fields to standard names
        assert "result" in legacy  # "response" mapped to "result"
        assert "memory_entries" in legacy  # "memories" mapped to "memory_entries"

    def test_create_success_response_with_trace_id(self):
        """Test create_success_response with trace_id."""
        result = ResponseBuilder.create_success_response(
            result="test",
            component_id="test",
            component_type="agent",
            trace_id="trace-123",
        )
        
        assert result["trace_id"] == "trace-123"

    def test_create_success_response_with_metadata_and_metrics(self):
        """Test create_success_response with metadata and metrics."""
        result = ResponseBuilder.create_success_response(
            result="test",
            component_id="test",
            component_type="agent",
            metadata={"key1": "value1"},
            metrics={"duration": 100},
        )
        
        assert result["metadata"]["key1"] == "value1"
        assert result["metrics"]["duration"] == 100

    def test_create_error_response_with_trace_id(self):
        """Test create_error_response with trace_id."""
        result = ResponseBuilder.create_error_response(
            error="Test error",
            component_id="test",
            component_type="agent",
            trace_id="trace-456",
        )
        
        assert result["trace_id"] == "trace-456"

    def test_create_error_response_with_partial_result(self):
        """Test create_error_response with partial result."""
        result = ResponseBuilder.create_error_response(
            error="Test error",
            component_id="test",
            component_type="agent",
            result="partial output",
        )
        
        assert result["result"] == "partial output"
        assert result["status"] == "error"

    def test_from_node_response_with_output_field(self):
        """Test from_node_response when using 'output' field."""
        legacy_response = {
            "output": "node output via output field",
        }
        
        result = ResponseBuilder.from_node_response(legacy_response, "node1")
        
        assert result["result"] == "node output via output field"

    def test_from_node_response_direct_value(self):
        """Test from_node_response when response is direct value."""
        legacy_response = {"some": "data", "without": "result"}
        
        result = ResponseBuilder.from_node_response(legacy_response, "node1")
        
        # Should use entire response as result when no result/output field
        assert result["result"] == legacy_response

    def test_extract_legacy_fields_with_answer(self):
        """Test extract_legacy_fields with 'answer' field."""
        response = {
            "answer": "test answer",
            "content": "test content",
            "text": "test text",
            "_metrics": {"token_count": 50},
        }
        
        legacy = ResponseBuilder.extract_legacy_fields(response)
        
        # First matching field should be used
        assert legacy["result"] in ["test answer", "test content", "test text"]
        assert legacy["metrics"]["token_count"] == 50

    def test_from_llm_agent_response_with_all_fields(self):
        """Test from_llm_agent_response with all optional fields."""
        legacy_response = {
            "response": "LLM output",
            "confidence": "0.95",
            "internal_reasoning": "Reasoning process",
            "formatted_prompt": "Formatted prompt text",
            "token_usage": 150,
            "cost_usd": 0.002,
            "metadata": {"model": "gpt-4"},
            "_metrics": {"latency_ms": 500},
        }
        
        result = ResponseBuilder.from_llm_agent_response(legacy_response, "agent1")
        
        assert result["result"] == "LLM output"
        assert result["formatted_prompt"] == "Formatted prompt text"
        assert result["internal_reasoning"] == "Reasoning process"
        assert result["token_usage"] == 150
        assert result["cost_usd"] == 0.002
        assert result["metadata"]["model"] == "gpt-4"
        assert result["metrics"]["latency_ms"] == 500

    def test_from_memory_agent_response_with_all_fields(self):
        """Test from_memory_agent_response with all fields."""
        legacy_response = {
            "memories": [{"key": "test1"}, {"key": "test2"}],
            "num_results": 2,
            "metadata": {"source": "redis"},
            "_metrics": {"search_time_ms": 50},
        }
        
        result = ResponseBuilder.from_memory_agent_response(legacy_response, "memory1")
        
        assert len(result["memory_entries"]) == 2
        assert result["metadata"]["source"] == "redis"
        assert result["metrics"]["search_time_ms"] == 50

    def test_create_error_response_with_metadata_and_metrics(self):
        """Test create_error_response with metadata and metrics."""
        result = ResponseBuilder.create_error_response(
            error="Test error",
            component_id="test",
            component_type="agent",
            metadata={"error_code": "E001"},
            metrics={"retry_count": 3},
        )
        
        assert result["metadata"]["error_code"] == "E001"
        assert result["metrics"]["retry_count"] == 3

    def test_validate_response_not_dict(self):
        """Test validate_response with non-dict input."""
        assert ResponseBuilder.validate_response("not a dict") is False
        assert ResponseBuilder.validate_response(None) is False
        assert ResponseBuilder.validate_response([]) is False

