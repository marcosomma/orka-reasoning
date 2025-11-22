"""
Test to verify LoopNode output template access fix.

This test validates that templates can correctly access LoopNode outputs
using the safe_get_response filter after the fix documented in:
changelog/loopnode_template_fix_v0.9.7.md
"""

import pytest
from orka.orchestrator.simplified_prompt_rendering import SimplifiedPromptRenderer


def test_loopnode_template_access_via_safe_get_response():
    """Test that safe_get_response correctly extracts LoopNode output from 'response' field."""
    renderer = SimplifiedPromptRenderer()
    
    # Simulate LoopNode output structure (wraps in 'response' field)
    previous_outputs = {
        "cognitive_debate_loop": {
            "response": {
                "input": "Test question",
                "result": {
                    "synthesis_attempt": {"response": "Final synthesis"},
                },
                "loops_completed": 2,
                "final_score": 1.0,
                "threshold_met": True,
                "past_loops": [
                    {"round": "1", "agreement_score": "0.95"},
                    {"round": "2", "agreement_score": "1.0"}
                ]
            }
        }
    }
    
    # Template using get_loop_output (correct pattern)
    template = """
DEBATE SUMMARY:
{% set loop_output = get_loop_output('cognitive_debate_loop', previous_outputs) %}
{% if loop_output %}
- Rounds: {{ safe_get(loop_output, 'loops_completed', 'Unknown') }}
- Final Score: {{ safe_get(loop_output, 'final_score', 'Unknown') }}
- Status: {{ safe_get(loop_output, 'threshold_met', False) }}
{% else %}
- Loop data not available
{% endif %}
"""
    
    # Render template
    rendered = renderer.render_prompt(template, {
        "previous_outputs": previous_outputs,
        "input": "Test question"
    })
    
    # Verify values are correctly extracted (not "Unknown")
    assert "- Rounds: 2" in rendered, f"Expected 'Rounds: 2', got:\n{rendered}"
    assert "- Final Score: 1.0" in rendered, f"Expected 'Final Score: 1.0', got:\n{rendered}"
    assert "- Status: True" in rendered, f"Expected 'Status: True', got:\n{rendered}"
    assert "Unknown" not in rendered, f"Should not contain 'Unknown':\n{rendered}"


def test_loopnode_template_incorrect_access_shows_unknown():
    """Test that incorrect template access (using .result) returns default values."""
    renderer = SimplifiedPromptRenderer()
    
    # Same LoopNode output structure
    previous_outputs = {
        "cognitive_debate_loop": {
            "response": {
                "loops_completed": 2,
                "final_score": 1.0,
            }
        }
    }
    
    # INCORRECT template pattern (accessing .result directly)
    template = """
DEBATE SUMMARY:
{% if previous_outputs.cognitive_debate_loop %}
- Rounds: {{ safe_get(previous_outputs.cognitive_debate_loop.result, 'loops_completed', 'Unknown') }}
- Score: {{ safe_get(previous_outputs.cognitive_debate_loop.result, 'final_score', 'Unknown') }}
{% endif %}
"""
    
    # Render template
    rendered = renderer.render_prompt(template, {
        "previous_outputs": previous_outputs
    })
    
    # Verify that incorrect access returns default "Unknown" values
    assert "- Rounds: Unknown" in rendered, f"Should show 'Unknown' for incorrect access:\n{rendered}"
    assert "- Score: Unknown" in rendered, f"Should show 'Unknown' for incorrect access:\n{rendered}"


def test_loopnode_nested_safe_get_response():
    """Test accessing nested data from LoopNode using get_loop_output and safe_get chains."""
    renderer = SimplifiedPromptRenderer()
    
    previous_outputs = {
        "cognitive_debate_loop": {
            "response": {
                "result": {
                    "agreement_finder": {
                        "response": "Agents reached consensus on key points"
                    }
                }
            }
        }
    }
    
    # Template accessing nested result data using safe_get chains
    template = """
{% set loop_output = get_loop_output('cognitive_debate_loop', previous_outputs) %}
{% if loop_output %}
{% set result_data = safe_get(loop_output, 'result', {}) %}
{% set agreement_data = safe_get(result_data, 'agreement_finder', {}) %}
Agreement: {{ safe_get(agreement_data, 'response', 'Unknown') | truncate(50) }}
{% endif %}
"""
    
    rendered = renderer.render_prompt(template, {
        "previous_outputs": previous_outputs
    })
    
    # Should successfully extract nested agreement_finder response
    assert "Agreement: Agents reached consensus" in rendered, f"Failed to extract nested data:\n{rendered}"


def test_loopnode_past_loops_access():
    """Test accessing past_loops metadata from LoopNode output."""
    renderer = SimplifiedPromptRenderer()
    
    previous_outputs = {
        "cognitive_debate_loop": {
            "response": {
                "past_loops": [
                    {"round": "1", "agreement_score": "0.95", "status": "CONVERGED"},
                    {"round": "2", "agreement_score": "1.0", "status": "CONVERGED"}
                ]
            }
        }
    }
    
    # Template iterating over past_loops
    template = """
{% set loop_output = get_loop_output('cognitive_debate_loop', previous_outputs) %}
{% set past_loops = safe_get(loop_output, 'past_loops', []) %}
ROUNDS:
{% for loop_data in past_loops %}
Round {{ safe_get(loop_data, 'round', '?') }}: Score {{ safe_get(loop_data, 'agreement_score', '?') }}
{% endfor %}
"""
    
    rendered = renderer.render_prompt(template, {
        "previous_outputs": previous_outputs
    })
    
    # Verify loop iteration works
    assert "Round 1: Score 0.95" in rendered, f"Failed to iterate past_loops:\n{rendered}"
    assert "Round 2: Score 1.0" in rendered, f"Failed to iterate past_loops:\n{rendered}"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
