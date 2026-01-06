"""Test InvariantValidatorAgent JSON parsing from params."""
import json
import pytest
from orka.agents.invariant_validator_agent import InvariantValidatorAgent


def test_json_string_parsing():
    """Test that agent properly parses JSON string from params."""
    # Sample execution data that would come from get_execution_artifacts()
    execution_data = {
        "nodes_executed": ["agent1", "agent2", "agent3"],
        "fork_groups": {
            "parallel_group": {
                "fork_node": "fork1",
                "branches": [["path_a"], ["path_b"]],
                "join_node": "join1",
                "has_join": True
            }
        },
        "router_decisions": {},
        "graph_structure": {
            "nodes": ["agent1", "agent2", "agent3"],
            "edges": [["agent1", "agent2"], ["agent2", "agent3"]]
        }
    }
    
    # Convert to JSON string (as tojson filter would do in YAML)
    execution_data_json = json.dumps(execution_data)
    
    # Create agent with JSON string in params (BaseAgent stores kwargs in self.params)
    agent = InvariantValidatorAgent(
        agent_id="test_validator",
        execution_data=execution_data_json,
        max_depth=50
    )
    
    # Process should parse JSON and validate
    result = agent.process("test input")
    
    # Should return facts dict with validation categories
    assert "fork_join_integrity" in result
    assert "validation_summary" in result
    assert isinstance(result["validation_summary"], dict)
    
    # Check that violations were detected (branches don't exist in nodes_executed)
    assert result["validation_summary"]["critical_count"] > 0


def test_dict_direct_passing():
    """Test that agent handles dict passed directly (backward compatibility)."""
    execution_data = {
        "nodes_executed": ["agent1", "agent2"],
        "fork_groups": {},
        "router_decisions": {},
        "graph_structure": {"nodes": ["agent1", "agent2"], "edges": [["agent1", "agent2"]]}
    }
    
    # Pass dict directly (no JSON string) - BaseAgent stores kwargs in self.params
    agent = InvariantValidatorAgent(
        agent_id="test_validator",
        execution_data=execution_data,
        max_depth=50
    )
    
    result = agent.process("test input")
    
    assert "fork_join_integrity" in result
    assert "validation_summary" in result


def test_invalid_json_handling():
    """Test that agent handles invalid JSON gracefully."""
    agent = InvariantValidatorAgent(
        agent_id="test_validator",
        execution_data="{invalid json}",
        max_depth=50
    )
    
    result = agent.process("test input")
    
    # Should return error status, not crash
    assert result["status"] == "error"
    assert "error" in result
    assert "JSON" in result["error"]


def test_empty_execution_data():
    """Test that agent handles empty/missing execution_data."""
    agent = InvariantValidatorAgent(
        agent_id="test_validator",
        max_depth=50  # No execution_data
    )
    
    result = agent.process("test input")
    
    # Should still work, just with limited validation
    assert "fork_join_integrity" in result
    assert "validation_summary" in result
