"""
Tests for prompt rendering functionality, particularly around agent response handling.
"""

import pytest

from orka.orchestrator.prompt_rendering import PromptRenderer


def test_render_prompt_with_nested_llm_response():
    """Test that LLM agent responses with nested structures can be accessed via templates."""
    renderer = PromptRenderer()

    # Test payload with nested LLM response
    payload = {
        "input": {"loop_number": 1},
        "previous_outputs": {
            "agent1": {
                "result": {
                    "response": "Test response",
                    "confidence": "0.9",
                    "internal_reasoning": "Test reasoning",
                    "_metrics": {"tokens": 100},
                    "formatted_prompt": "Original prompt",
                }
            }
        },
    }

    template = "Response: {{ previous_outputs.agent1.response }}"
    result = renderer.render_prompt(template, payload)
    assert result == "Response: Test response"


def test_render_prompt_with_direct_llm_response():
    """Test that LLM agent responses without nesting can be accessed via templates."""
    renderer = PromptRenderer()

    # Test payload with direct LLM response
    payload = {
        "input": {"loop_number": 1},
        "previous_outputs": {
            "agent1": {
                "response": "Test response",
                "confidence": "0.9",
                "internal_reasoning": "Test reasoning",
                "_metrics": {"tokens": 100},
                "formatted_prompt": "Original prompt",
            }
        },
    }

    template = "Response: {{ previous_outputs.agent1.response }}"
    result = renderer.render_prompt(template, payload)
    assert result == "Response: Test response"


def test_render_prompt_with_memory_response():
    """Test that memory agent responses can be accessed via templates."""
    renderer = PromptRenderer()

    # Test payload with memory response
    payload = {
        "input": {"loop_number": 1},
        "previous_outputs": {
            "memory_reader": {
                "result": {
                    "memories": ["Memory 1", "Memory 2"],
                    "query": "test query",
                    "backend": "redis",
                    "search_type": "vector",
                    "num_results": 2,
                }
            }
        },
    }

    template = "Memories: {{ previous_outputs.memory_reader.memories|join(', ') }}"
    result = renderer.render_prompt(template, payload)
    assert result == "Memories: Memory 1, Memory 2"


def test_render_prompt_with_mixed_responses():
    """Test that mixed agent responses can be accessed via templates."""
    renderer = PromptRenderer()

    # Test payload with mixed response types
    payload = {
        "input": {"loop_number": 1},
        "previous_outputs": {
            "llm_agent": {"result": {"response": "LLM response", "confidence": "0.9"}},
            "memory_agent": {"result": {"memories": ["Memory"], "query": "test"}},
            "simple_agent": "Simple response",
        },
    }

    template = """
    LLM: {{ previous_outputs.llm_agent.response }}
    Memory: {{ previous_outputs.memory_agent.memories[0] }}
    Simple: {{ previous_outputs.simple_agent }}
    """
    result = renderer.render_prompt(template, payload)
    assert "LLM: LLM response" in result
    assert "Memory: Memory" in result
    assert "Simple: Simple response" in result


def test_render_prompt_with_loop_number():
    """Test that loop_number is properly exposed at root level."""
    renderer = PromptRenderer()

    payload = {"input": {"loop_number": 5}, "previous_outputs": {}}

    template = "Loop: {{ loop_number }}"
    result = renderer.render_prompt(template, payload)
    assert result == "Loop: 5"


def test_render_prompt_with_past_loops_metadata():
    """Test that past_loops_metadata is properly exposed at root level."""
    renderer = PromptRenderer()

    payload = {
        "input": {
            "loop_number": 1,
            "past_loops_metadata": {"insights": "Test insight", "improvements": "Test improvement"},
        },
        "previous_outputs": {},
    }

    template = "Insights: {{ past_loops_metadata.insights }}"
    result = renderer.render_prompt(template, payload)
    assert result == "Insights: Test insight"
