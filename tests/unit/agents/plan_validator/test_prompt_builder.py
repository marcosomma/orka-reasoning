import pytest
import json
from orka.agents.plan_validator.prompt_builder import build_validation_prompt, _format_critique_history, _build_criteria_instructions

def test_build_validation_prompt_basic():
    """Test basic prompt generation without critiques."""
    query = "test query"
    proposed_path = {"path": ["a", "b"]}
    loop_number = 1
    prompt = build_validation_prompt(
        query=query,
        proposed_path=proposed_path,
        previous_critiques=[],
        loop_number=loop_number,
        preset_name="moderate"
    )
    
    assert f"**VALIDATION ROUND:** {loop_number}" in prompt
    assert f"**ORIGINAL QUERY:**\n{query}" in prompt
    assert f"**PROPOSED PATH (from GraphScout):**\n{json.dumps(proposed_path, indent=2)}" in prompt
    assert "PREVIOUS CRITIQUES" not in prompt
    assert "COMPLETENESS" in prompt

def test_build_validation_prompt_with_critiques():
    """Test prompt generation with previous critiques."""
    critiques = [{"validation_score": 0.5, "assessment": "NEEDS_IMPROVEMENT", "failed_criteria": ["completeness.handles_edge_cases"]}]
    query = "test query"
    proposed_path = {"path": ["a", "b", "c"]}
    loop_number = 2
    prompt = build_validation_prompt(
        query=query,
        proposed_path=proposed_path,
        previous_critiques=critiques,
        loop_number=loop_number,
        preset_name="moderate"
    )
    
    assert f"**VALIDATION ROUND:** {loop_number}" in prompt
    assert "**PREVIOUS CRITIQUES:**" in prompt
    assert "Round 1: Score=0.5, Assessment=NEEDS_IMPROVEMENT" in prompt
    assert "Failed: completeness.handles_edge_cases" in prompt

def test_format_critique_history():
    """Test the formatting of critique history."""
    critiques = [
        {"score": 0.6, "assessment": "NEEDS_IMPROVEMENT", "failed_criteria": ["safety.validates_inputs"]},
        {"validation_score": 0.9, "overall_assessment": "APPROVED", "failed_criteria": []}
    ]
    history = _format_critique_history(critiques)
    
    assert "Round 1: Score=0.6, Assessment=NEEDS_IMPROVEMENT" in history
    assert "Failed: safety.validates_inputs" in history
    assert "Round 2: Score=0.9, Assessment=APPROVED" in history

def test_build_criteria_instructions():
    """Test the generation of criteria instructions."""
    instructions = _build_criteria_instructions("moderate")
    
    assert "COMPLETENESS" in instructions
    assert "has_all_required_steps" in instructions
    # Check for a description
    assert "All necessary steps are included" in instructions
