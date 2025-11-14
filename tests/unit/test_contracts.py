"""Unit tests for orka.contracts."""

import pytest
from datetime import datetime
from typing import Dict, Any
from orka.contracts import (
    Context, Output, ResourceConfig, Registry, Trace, MemoryEntry, OrkaResponse
)


# Skip auto-mocking for this test since we're testing data structures
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestContracts:
    """Test suite for contract data structures."""

    def test_context_creation(self):
        """Test Context TypedDict creation and structure."""
        # Test minimal context
        context: Context = {
            "input": "test query"
        }
        assert context["input"] == "test query"
        
        # Test full context
        full_context: Context = {
            "input": "test query",
            "previous_outputs": {"agent1": {"result": "test"}},
            "metadata": {"run_id": "123"},
            "trace_id": "trace_123",
            "timestamp": datetime.now()
        }
        
        assert full_context["input"] == "test query"
        assert "agent1" in full_context["previous_outputs"]
        assert full_context["metadata"]["run_id"] == "123"
        assert full_context["trace_id"] == "trace_123"
        assert isinstance(full_context["timestamp"], datetime)

    def test_context_optional_fields(self):
        """Test that Context fields are properly optional."""
        # Should work with just input
        minimal_context: Context = {"input": "test"}
        assert minimal_context["input"] == "test"
        
        # Should work with additional optional fields
        context_with_outputs: Context = {
            "input": "test",
            "previous_outputs": {"agent1": {"data": "value"}}
        }
        assert len(context_with_outputs["previous_outputs"]) == 1

    def test_output_creation(self):
        """Test Output TypedDict creation and structure."""
        output: Output = {
            "result": "test result",
            "metadata": {"tokens": 100}
        }
        
        assert output["result"] == "test result"
        assert output["metadata"]["tokens"] == 100

    def test_output_with_various_result_types(self):
        """Test Output with different result types."""
        # String result
        string_output: Output = {
            "result": "string result",
            "metadata": {}
        }
        assert isinstance(string_output["result"], str)
        
        # Dict result
        dict_output: Output = {
            "result": {"key": "value", "number": 42},
            "metadata": {}
        }
        assert isinstance(dict_output["result"], dict)
        assert dict_output["result"]["number"] == 42
        
        # List result
        list_output: Output = {
            "result": ["item1", "item2", "item3"],
            "metadata": {}
        }
        assert isinstance(list_output["result"], list)
        assert len(list_output["result"]) == 3

    def test_resource_config_creation(self):
        """Test ResourceConfig TypedDict creation."""
        resource_config: ResourceConfig = {
            "type": "redis",
            "config": {
                "host": "localhost",
                "port": 6379,
                "db": 0
            }
        }
        
        assert resource_config["type"] == "redis"
        assert resource_config["config"]["host"] == "localhost"
        assert resource_config["config"]["port"] == 6379

    def test_resource_config_different_types(self):
        """Test ResourceConfig with different resource types."""
        # Redis config
        redis_config: ResourceConfig = {
            "type": "redis",
            "config": {"url": "redis://localhost:6379"}
        }
        assert redis_config["type"] == "redis"
        
        # OpenAI config
        openai_config: ResourceConfig = {
            "type": "openai",
            "config": {"api_key": "test_key", "model": "gpt-4"}
        }
        assert openai_config["type"] == "openai"
        assert openai_config["config"]["model"] == "gpt-4"
        
        # SentenceTransformer config
        embedder_config: ResourceConfig = {
            "type": "sentence_transformer",
            "config": {"model_name": "all-MiniLM-L6-v2"}
        }
        assert embedder_config["type"] == "sentence_transformer"

    def test_registry_creation(self):
        """Test Registry TypedDict creation."""
        registry: Registry = {
            "resources": {
                "redis": {
                    "type": "redis",
                    "config": {"host": "localhost"}
                },
                "embedder": {
                    "type": "sentence_transformer",
                    "config": {"model_name": "test-model"}
                }
            }
        }
        
        assert "redis" in registry["resources"]
        assert "embedder" in registry["resources"]
        assert registry["resources"]["redis"]["type"] == "redis"
        assert registry["resources"]["embedder"]["config"]["model_name"] == "test-model"

    def test_trace_creation(self):
        """Test Trace TypedDict creation."""
        trace: Trace = {
            "trace_id": "trace_123",
            "start_time": datetime.now(),
            "steps": [
                {
                    "agent_id": "agent1",
                    "input": "test input",
                    "output": "test output",
                    "timestamp": datetime.now()
                }
            ]
        }
        
        assert trace["trace_id"] == "trace_123"
        assert isinstance(trace["start_time"], datetime)
        assert len(trace["steps"]) == 1
        assert trace["steps"][0]["agent_id"] == "agent1"

    def test_trace_with_multiple_steps(self):
        """Test Trace with multiple execution steps."""
        now = datetime.now()
        trace: Trace = {
            "trace_id": "multi_step_trace",
            "start_time": now,
            "steps": [
                {
                    "agent_id": "parser",
                    "input": "raw query",
                    "output": "parsed query",
                    "timestamp": now
                },
                {
                    "agent_id": "processor",
                    "input": "parsed query",
                    "output": "processed result",
                    "timestamp": now
                }
            ]
        }
        
        assert len(trace["steps"]) == 2
        assert trace["steps"][0]["agent_id"] == "parser"
        assert trace["steps"][1]["agent_id"] == "processor"

    def test_memory_entry_creation(self):
        """Test MemoryEntry TypedDict creation."""
        memory_entry: MemoryEntry = {
            "id": "memory_123",
            "content": "This is stored content",
            "timestamp": datetime.now(),
            "metadata": {
                "source": "user_input",
                "importance": 0.8
            }
        }
        
        assert memory_entry["id"] == "memory_123"
        assert memory_entry["content"] == "This is stored content"
        assert isinstance(memory_entry["timestamp"], datetime)
        assert memory_entry["metadata"]["source"] == "user_input"
        assert memory_entry["metadata"]["importance"] == 0.8

    def test_memory_entry_with_vector(self):
        """Test MemoryEntry with optional vector field."""
        memory_entry: MemoryEntry = {
            "id": "vectorized_memory",
            "content": "Content with embedding",
            "timestamp": datetime.now(),
            "metadata": {"type": "semantic"},
            "vector": [0.1, 0.2, 0.3, 0.4, 0.5]
        }
        
        assert memory_entry["id"] == "vectorized_memory"
        assert "vector" in memory_entry
        assert len(memory_entry["vector"]) == 5
        assert memory_entry["vector"][0] == 0.1

    def test_orka_response_creation(self):
        """Test OrkaResponse TypedDict creation."""
        # Minimal response
        minimal_response: OrkaResponse = {
            "response": "This is the response"
        }
        assert minimal_response["response"] == "This is the response"
        
        # Full response
        full_response: OrkaResponse = {
            "response": "Detailed response",
            "metadata": {
                "tokens_used": 150,
                "cost": 0.002,
                "latency_ms": 1200
            },
            "trace": {
                "trace_id": "response_trace",
                "start_time": datetime.now(),
                "steps": []
            },
            "context": {
                "input": "original query",
                "previous_outputs": {}
            }
        }
        
        assert full_response["response"] == "Detailed response"
        assert full_response["metadata"]["tokens_used"] == 150
        assert full_response["trace"]["trace_id"] == "response_trace"
        assert full_response["context"]["input"] == "original query"

    def test_orka_response_optional_fields(self):
        """Test OrkaResponse with various optional field combinations."""
        # Response with metadata only
        response_with_metadata: OrkaResponse = {
            "response": "Response text",
            "metadata": {"source": "agent_x"}
        }
        assert "metadata" in response_with_metadata
        assert "trace" not in response_with_metadata
        
        # Response with trace only
        response_with_trace: OrkaResponse = {
            "response": "Response text",
            "trace": {
                "trace_id": "trace_only",
                "start_time": datetime.now(),
                "steps": []
            }
        }
        assert "trace" in response_with_trace
        assert "metadata" not in response_with_trace

    def test_nested_data_structures(self):
        """Test complex nested data structures using contracts."""
        # Complex context with nested outputs
        complex_context: Context = {
            "input": "complex query",
            "previous_outputs": {
                "agent1": {
                    "result": {
                        "analysis": "detailed analysis",
                        "confidence": 0.95,
                        "sub_results": [
                            {"item": "result1", "score": 0.8},
                            {"item": "result2", "score": 0.9}
                        ]
                    },
                    "metadata": {"processing_time": 2.5}
                },
                "agent2": {
                    "result": ["item1", "item2", "item3"],
                    "metadata": {"count": 3}
                }
            },
            "metadata": {
                "workflow_id": "complex_workflow",
                "step": 3,
                "total_steps": 5
            }
        }
        
        # Verify nested structure access
        assert complex_context["previous_outputs"]["agent1"]["result"]["confidence"] == 0.95
        assert len(complex_context["previous_outputs"]["agent1"]["result"]["sub_results"]) == 2
        assert complex_context["previous_outputs"]["agent2"]["result"][1] == "item2"
        assert complex_context["metadata"]["step"] == 3

    def test_type_flexibility(self):
        """Test that contracts allow flexible typing as expected."""
        # Context with various input types
        contexts = [
            {"input": "string input"},
            {"input": {"structured": "input", "type": "dict"}},
            {"input": ["list", "input", "items"]},
            {"input": 42},  # numeric input
            {"input": True}  # boolean input
        ]
        
        for ctx in contexts:
            # Should all be valid Context instances
            context: Context = ctx
            assert "input" in context

    def test_metadata_flexibility(self):
        """Test that metadata fields accept various data types."""
        flexible_metadata = {
            "string_field": "value",
            "numeric_field": 123,
            "float_field": 45.67,
            "boolean_field": True,
            "list_field": [1, 2, 3],
            "dict_field": {"nested": "value"},
            "none_field": None
        }
        
        # Should work in various contract contexts
        output: Output = {
            "result": "test",
            "metadata": flexible_metadata
        }
        
        memory_entry: MemoryEntry = {
            "id": "flexible_memory",
            "content": "content",
            "timestamp": datetime.now(),
            "metadata": flexible_metadata
        }
        
        assert output["metadata"]["numeric_field"] == 123
        assert memory_entry["metadata"]["boolean_field"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
