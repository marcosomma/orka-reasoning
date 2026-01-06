# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Tests for InvariantValidatorAgent.
"""

import pytest
from orka.agents.invariant_validator_agent import InvariantValidatorAgent


class TestInvariantValidatorAgent:
    """Test suite for InvariantValidatorAgent."""

    def test_init_default_config(self):
        """Test agent initialization with default config."""
        agent = InvariantValidatorAgent(
            agent_id="validator1",
            agent_type="invariant_validator",
            prompt="",  # Not used but required
            queue=[]
        )
        
        assert agent.agent_id == "validator1"
        assert agent.validator_config["max_depth"] is None
        assert agent.validator_config["allow_reentrant_nodes"] == []
        assert not agent.validator_config["strict_tool_errors"]
    
    def test_init_custom_config(self):
        """Test agent initialization with custom config."""
        params = {
            "max_depth": 5,
            "allow_reentrant_nodes": ["loop_node"],
            "strict_tool_errors": True
        }
        
        agent = InvariantValidatorAgent(
            agent_id="validator2",
            agent_type="invariant_validator",
            prompt="",
            queue=[],
            params=params
        )
        
        assert agent.validator_config["max_depth"] == 5
        assert agent.validator_config["allow_reentrant_nodes"] == ["loop_node"]
        assert agent.validator_config["strict_tool_errors"]
    
    def test_process_all_pass(self):
        """Test process with all invariants passing."""
        execution_data = {
            "nodes_executed": ["a", "b", "c"],
            "fork_groups": {
                "fork1": {
                    "has_join": True,
                    "branches": ["x", "y"],
                    "completed_branches": ["x", "y"]
                }
            },
            "router_decisions": {
                "router1": {"chosen_target": "target_a"}
            },
            "graph_structure": {
                "nodes": {"router1": {}, "target_a": {}},
                "edges": [{"src": "router1", "dst": "target_a"}]
            },
            "tool_calls": [],
            "structured_outputs": {}
        }
        
        agent = InvariantValidatorAgent(
            agent_id="validator",
            agent_type="invariant_validator",
            prompt="",
            queue=[],
            params={"execution_data": execution_data}
        )
        
        result = agent.process("")
        
        assert result["fork_join_integrity"]["status"] == "PASS"
        assert result["routing_integrity"]["status"] == "PASS"
        assert result["cycle_detection"]["status"] == "PASS"
        assert result["tool_integrity"]["status"] == "PASS"
        assert result["schema_compliance"]["status"] == "PASS"
        assert result["depth_compliance"]["status"] == "PASS"
        assert not result["critical_failures_detected"]
        assert result["validation_summary"]["total_violations"] == 0
    
    def test_process_with_violations(self):
        """Test process with multiple invariant violations."""
        execution_data = {
            "nodes_executed": ["a", "b", "a", "c"],  # Cycle: 'a' repeats
            "fork_groups": {
                "fork1": {
                    "has_join": False,  # Missing join
                    "branches": ["x", "y"],
                    "completed_branches": []
                }
            },
            "router_decisions": {
                "router1": {"chosen_target": "nonexistent"}  # Invalid target
            },
            "graph_structure": {
                "nodes": {"router1": {}},
                "edges": []
            },
            "tool_calls": [
                {
                    "status": "error",
                    "node_id": "tool1",
                    "error_handled": False,
                    "execution_continued_after_error": True  # Swallowed error
                }
            ],
            "structured_outputs": {
                "node1": {"schema_valid": False}  # Schema violation
            }
        }
        
        agent = InvariantValidatorAgent(
            agent_id="validator",
            agent_type="invariant_validator",
            prompt="",
            queue=[],
            params={
                "execution_data": execution_data,
                "max_depth": 3  # Depth violation (4 nodes > 3)
            }
        )
        
        result = agent.process("")
        
        assert result["fork_join_integrity"]["status"] == "FAIL"
        assert result["routing_integrity"]["status"] == "FAIL"
        assert result["cycle_detection"]["status"] == "FAIL"
        assert result["tool_integrity"]["status"] == "FAIL"
        assert result["schema_compliance"]["status"] == "FAIL"
        assert result["depth_compliance"]["status"] == "FAIL"
        assert result["critical_failures_detected"]
        
        summary = result["validation_summary"]
        assert summary["total_violations"] > 0
        assert summary["critical_count"] > 0
        assert len(summary["categories_failed"]) > 0
    
    def test_process_no_execution_data(self):
        """Test process when no execution data provided."""
        agent = InvariantValidatorAgent(
            agent_id="validator",
            agent_type="invariant_validator",
            prompt="",
            queue=[],
            params={}
        )
        
        result = agent.process("")
        
        # Should still return valid structure, just with empty checks
        assert "fork_join_integrity" in result
        assert "validation_summary" in result
    
    def test_process_with_exception(self):
        """Test process handles exceptions gracefully."""
        # Invalid execution data that will cause validator to error
        invalid_data = {
            "nodes_executed": None,  # Invalid type
        }
        
        agent = InvariantValidatorAgent(
            agent_id="validator",
            agent_type="invariant_validator",
            prompt="",
            queue=[],
            params={"execution_data": invalid_data}
        )
        
        result = agent.process("")
        
        # Should return error state
        assert result["critical_failures_detected"]
        assert result["fork_join_integrity"]["status"] == "ERROR"
        assert "error" in result["validation_summary"]
    
    def test_process_reentrant_nodes_config(self):
        """Test that reentrant nodes config is respected."""
        execution_data = {
            "nodes_executed": ["a", "loop_node", "b", "loop_node", "c"],
            "fork_groups": {},
            "router_decisions": {},
            "graph_structure": {"nodes": {}, "edges": []},
            "tool_calls": [],
            "structured_outputs": {}
        }
        
        agent = InvariantValidatorAgent(
            agent_id="validator",
            agent_type="invariant_validator",
            prompt="",
            queue=[],
            params={
                "execution_data": execution_data,
                "allow_reentrant_nodes": ["loop_node"]
            }
        )
        
        result = agent.process("")
        
        # loop_node is allowed to repeat, so no cycle violation
        assert result["cycle_detection"]["status"] == "PASS"
        assert not result["critical_failures_detected"]
