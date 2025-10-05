"""
Tests for template rendering functionality, particularly around agent response handling.
"""

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine
from orka.orchestrator.simplified_prompt_rendering import SimplifiedPromptRenderer


def test_local_llm_response_access():
    """Test that local LLM agent responses can be accessed via templates."""
    engine = ExecutionEngine("tests/dummy.yml")  # Use dummy config for testing

    # Simulate local LLM agent response
    previous_outputs = {
        "radical_progressive": {
            "response": "This is a progressive response",
            "confidence": "0.9",
            "internal_reasoning": "Some reasoning",
            "_metrics": {"tokens": 100},
        }
    }

    # Process through context enhancement
    enhanced = engine._ensure_complete_context(previous_outputs)

    # Verify structure
    assert "radical_progressive" in enhanced
    assert "response" in enhanced["radical_progressive"]
    assert enhanced["radical_progressive"]["response"] == "This is a progressive response"

    # Test template rendering
    renderer = SimplifiedPromptRenderer()
    template = "Progressive view: {{ previous_outputs.radical_progressive.response }}"
    rendered = renderer.render_prompt(template, {"previous_outputs": enhanced})

    assert "Progressive view: This is a progressive response" in rendered


def test_nested_response_access():
    """Test that nested response structures can be accessed via templates."""
    engine = ExecutionEngine("tests/dummy.yml")

    # Simulate nested response structure (memories only, no response to test memories path)
    previous_outputs = {
        "memory_reader": {
            "result": {
                "memories": ["memory1", "memory2"],
                "query": "test query",
                "backend": "redis",
            }
        }
    }

    # Process through context enhancement
    enhanced = engine._ensure_complete_context(previous_outputs)

    # Verify structure - the _ensure_complete_context method flattens the result into the agent response
    assert "memory_reader" in enhanced
    # The memories from the nested "result" are now at the top level of the agent response
    assert "memories" in enhanced["memory_reader"]
    assert "query" in enhanced["memory_reader"]
    assert "backend" in enhanced["memory_reader"]
    assert enhanced["memory_reader"]["memories"] == ["memory1", "memory2"]
    assert enhanced["memory_reader"]["query"] == "test query"
    assert enhanced["memory_reader"]["backend"] == "redis"

    # Test template rendering
    renderer = SimplifiedPromptRenderer()
    template = """
    Memories: {{ previous_outputs.memory_reader.memories }}
    Query: {{ previous_outputs.memory_reader.query }}
    Backend: {{ previous_outputs.memory_reader.backend }}
    """
    rendered = renderer.render_prompt(template, {"previous_outputs": enhanced})

    assert "memory1" in rendered
    assert "memory2" in rendered
    assert "test query" in rendered
    assert "redis" in rendered


def test_mixed_agent_responses():
    """Test that different types of agent responses can be accessed together."""
    engine = ExecutionEngine("tests/dummy.yml")

    # Simulate mixed agent responses
    previous_outputs = {
        "llm_agent": {"response": "LLM response", "confidence": "0.9"},
        "memory_agent": {"result": {"memories": ["mem1"], "response": "Memory response"}},
        "simple_agent": "Simple response",
    }

    # Process through context enhancement
    enhanced = engine._ensure_complete_context(previous_outputs)

    # Test template rendering
    renderer = SimplifiedPromptRenderer()
    template = """
    LLM: {{ previous_outputs.llm_agent.response }}
    Memory: {{ previous_outputs.memory_agent.response }}
    Simple: {{ previous_outputs.simple_agent }}
    """
    rendered = renderer.render_prompt(template, {"previous_outputs": enhanced})

    assert "LLM: LLM response" in rendered
    assert "Memory: Memory response" in rendered
    assert "Simple: Simple response" in rendered


def test_response_structure_preservation():
    """Test that original response structure is preserved while enabling template access."""
    engine = ExecutionEngine("tests/dummy.yml")

    # Original response with metrics
    original_response = {
        "response": "Test response",
        "confidence": "0.9",
        "internal_reasoning": "Some reasoning",
        "_metrics": {"tokens": 100, "latency_ms": 150},
    }

    previous_outputs = {"test_agent": original_response}

    # Process through context enhancement
    enhanced = engine._ensure_complete_context(previous_outputs)

    # Verify all original fields are preserved
    enhanced_response = enhanced["test_agent"]
    assert enhanced_response["response"] == original_response["response"]
    assert enhanced_response["confidence"] == original_response["confidence"]
    assert enhanced_response["internal_reasoning"] == original_response["internal_reasoning"]
    assert enhanced_response["_metrics"] == original_response["_metrics"]
