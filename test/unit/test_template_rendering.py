"""
Tests for template rendering functionality, particularly around agent response handling.
"""

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine
from orka.orchestrator.prompt_rendering import PromptRenderer


def test_local_llm_response_access():
    """Test that local LLM agent responses can be accessed via templates."""
    engine = ExecutionEngine({})  # Empty config for testing

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
    renderer = PromptRenderer()
    template = "Progressive view: {{ previous_outputs.radical_progressive.response }}"
    rendered = renderer.render_prompt(template, {"previous_outputs": enhanced})

    assert "Progressive view: This is a progressive response" in rendered


def test_nested_response_access():
    """Test that nested response structures can be accessed via templates."""
    engine = ExecutionEngine({})

    # Simulate nested response structure
    previous_outputs = {
        "memory_reader": {
            "result": {
                "memories": ["memory1", "memory2"],
                "response": "Memory response",
                "confidence": "0.8",
            }
        }
    }

    # Process through context enhancement
    enhanced = engine._ensure_complete_context(previous_outputs)

    # Verify structure
    assert "memory_reader" in enhanced
    assert "memories" in enhanced["memory_reader"]
    assert "response" in enhanced["memory_reader"]
    assert enhanced["memory_reader"]["memories"] == ["memory1", "memory2"]
    assert enhanced["memory_reader"]["response"] == "Memory response"

    # Test template rendering
    renderer = PromptRenderer()
    template = """
    Memories: {{ previous_outputs.memory_reader.memories }}
    Response: {{ previous_outputs.memory_reader.response }}
    """
    rendered = renderer.render_prompt(template, {"previous_outputs": enhanced})

    assert "memory1" in rendered
    assert "memory2" in rendered
    assert "Memory response" in rendered


def test_mixed_agent_responses():
    """Test that different types of agent responses can be accessed together."""
    engine = ExecutionEngine({})

    # Simulate mixed agent responses
    previous_outputs = {
        "llm_agent": {"response": "LLM response", "confidence": "0.9"},
        "memory_agent": {"result": {"memories": ["mem1"], "response": "Memory response"}},
        "simple_agent": "Simple response",
    }

    # Process through context enhancement
    enhanced = engine._ensure_complete_context(previous_outputs)

    # Test template rendering
    renderer = PromptRenderer()
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
    engine = ExecutionEngine({})

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
