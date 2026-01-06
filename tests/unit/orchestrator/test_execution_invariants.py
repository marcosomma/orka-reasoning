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
Unit tests for execution invariants validator.
"""

import pytest
from orka.orchestrator.execution_invariants import (
    ExecutionInvariantsValidator,
    ExecutionInvariants,
    InvariantViolation,
)


class TestInvariantViolation:
    """Test InvariantViolation dataclass."""

    def test_create_violation(self):
        """Test creating a basic violation."""
        violation = InvariantViolation(
            category="fork_join",
            severity="error",
            message="Test violation",
            node_id="test_node"
        )
        
        assert violation.category == "fork_join"
        assert violation.severity == "error"
        assert violation.message == "Test violation"
        assert violation.node_id == "test_node"
        assert violation.details == {}


class TestExecutionInvariants:
    """Test ExecutionInvariants dataclass."""

    def test_has_critical_failures_all_pass(self):
        """Test has_critical_failures when all checks pass."""
        invariants = ExecutionInvariants()
        assert not invariants.has_critical_failures
    
    def test_has_critical_failures_fork_join_violation(self):
        """Test has_critical_failures with fork/join violation."""
        invariants = ExecutionInvariants()
        invariants.all_forks_have_joins = False
        assert invariants.has_critical_failures
    
    def test_has_critical_failures_routing_violation(self):
        """Test has_critical_failures with routing violation."""
        invariants = ExecutionInvariants()
        invariants.all_router_targets_exist = False
        assert invariants.has_critical_failures
    
    def test_has_critical_failures_cycle_detected(self):
        """Test has_critical_failures with unexpected cycle."""
        invariants = ExecutionInvariants()
        invariants.has_unexpected_cycles = True
        assert invariants.has_critical_failures
    
    def test_all_violations_aggregation(self):
        """Test that all_violations aggregates from all categories."""
        invariants = ExecutionInvariants()
        invariants.fork_join_violations = [
            InvariantViolation("fork_join", "error", "msg1")
        ]
        invariants.routing_violations = [
            InvariantViolation("routing", "error", "msg2")
        ]
        
        all_viols = invariants.all_violations
        assert len(all_viols) == 2
        assert all_viols[0].message == "msg1"
        assert all_viols[1].message == "msg2"
    
    def test_to_compact_facts_all_pass(self):
        """Test compact facts representation when all checks pass."""
        invariants = ExecutionInvariants()
        facts = invariants.to_compact_facts()
        
        assert facts["fork_join_integrity"]["status"] == "PASS"
        assert facts["routing_integrity"]["status"] == "PASS"
        assert facts["cycle_detection"]["status"] == "PASS"
        assert facts["tool_integrity"]["status"] == "PASS"
        assert facts["schema_compliance"]["status"] == "PASS"
        assert facts["depth_compliance"]["status"] == "PASS"
        assert not facts["critical_failures_detected"]
    
    def test_to_compact_facts_with_failures(self):
        """Test compact facts representation with failures."""
        invariants = ExecutionInvariants()
        invariants.all_forks_have_joins = False
        invariants.fork_join_violations = [
            InvariantViolation("fork_join", "error", "Missing join for fork_1")
        ]
        invariants.has_unexpected_cycles = True
        invariants.cycle_paths = [["a", "b", "a"]]
        
        facts = invariants.to_compact_facts()
        
        assert facts["fork_join_integrity"]["status"] == "FAIL"
        assert len(facts["fork_join_integrity"]["violations"]) == 1
        assert facts["cycle_detection"]["status"] == "FAIL"
        assert len(facts["cycle_detection"]["cycles_found"]) == 1
        assert facts["critical_failures_detected"]


class TestExecutionInvariantsValidator:
    """Test ExecutionInvariantsValidator class."""

    def test_init_default_config(self):
        """Test validator initialization with default config."""
        validator = ExecutionInvariantsValidator()
        assert validator.config == {}
        assert validator.allow_reentrant_nodes == set()
        assert validator.max_depth is None
        assert not validator.strict_tool_errors
    
    def test_init_custom_config(self):
        """Test validator initialization with custom config."""
        config = {
            "allow_reentrant_nodes": ["loop_node"],
            "max_depth": 5,
            "strict_tool_errors": True
        }
        validator = ExecutionInvariantsValidator(config)
        
        assert validator.allow_reentrant_nodes == {"loop_node"}
        assert validator.max_depth == 5
        assert validator.strict_tool_errors
    
    def test_check_fork_join_integrity_all_complete(self):
        """Test fork/join check when all branches complete."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "fork_groups": {
                "fork_1": {
                    "has_join": True,
                    "branches": ["branch_a", "branch_b"],
                    "completed_branches": ["branch_a", "branch_b"]
                }
            }
        }
        
        invariants = validator.validate(execution_data)
        
        assert invariants.all_forks_have_joins
        assert invariants.all_joins_have_complete_branches
        assert len(invariants.fork_join_violations) == 0
    
    def test_check_fork_join_integrity_missing_join(self):
        """Test fork/join check when join is missing."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "fork_groups": {
                "fork_1": {
                    "has_join": False,
                    "branches": ["branch_a", "branch_b"],
                    "completed_branches": []
                }
            }
        }
        
        invariants = validator.validate(execution_data)
        
        assert not invariants.all_forks_have_joins
        assert len(invariants.fork_join_violations) >= 1
        assert "no matching join" in invariants.fork_join_violations[0].message.lower()
    
    def test_check_fork_join_integrity_incomplete_branches(self):
        """Test fork/join check when branches incomplete."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "fork_groups": {
                "fork_1": {
                    "has_join": True,
                    "branches": ["branch_a", "branch_b", "branch_c"],
                    "completed_branches": ["branch_a"]
                }
            }
        }
        
        invariants = validator.validate(execution_data)
        
        assert not invariants.all_joins_have_complete_branches
        assert len(invariants.fork_join_violations) >= 1
        violation = invariants.fork_join_violations[0]
        assert "missing results" in violation.message.lower()
        assert "branch_b" in str(violation.details.get("missing", []))
    
    def test_check_fork_join_integrity_nested_branches(self):
        """Test fork/join check with nested branch lists (sequential execution within branches)."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "fork_groups": {
                "fork_parallel": {
                    "has_join": True,
                    "branches": [
                        ["agent_a1", "agent_a2"],  # Sequential agents in branch A
                        ["agent_b1", "agent_b2"],  # Sequential agents in branch B
                        ["agent_c1"]                # Single agent in branch C
                    ],
                    "completed_branches": [
                        ["agent_a1", "agent_a2"],
                        ["agent_b1", "agent_b2"],
                        ["agent_c1"]
                    ]
                }
            }
        }
        
        invariants = validator.validate(execution_data)
        
        # Should pass - all nested branches completed
        assert invariants.all_forks_have_joins
        assert invariants.all_joins_have_complete_branches
        assert len(invariants.fork_join_violations) == 0
    
    def test_check_routing_validity_target_exists(self):
        """Test routing check when target exists."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "router_decisions": {
                "router_1": {"chosen_target": "target_a"}
            },
            "graph_structure": {
                "nodes": {"router_1": {}, "target_a": {}},
                "edges": [{"src": "router_1", "dst": "target_a"}]
            }
        }
        
        invariants = validator.validate(execution_data)
        
        assert invariants.all_router_targets_exist
        assert invariants.all_router_targets_reachable
        assert len(invariants.routing_violations) == 0
    
    def test_check_routing_validity_target_missing(self):
        """Test routing check when target doesn't exist."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "router_decisions": {
                "router_1": {"chosen_target": "nonexistent"}
            },
            "graph_structure": {
                "nodes": {"router_1": {}},
                "edges": []
            }
        }
        
        invariants = validator.validate(execution_data)
        
        assert not invariants.all_router_targets_exist
        assert len(invariants.routing_violations) >= 1
        assert "non-existent" in invariants.routing_violations[0].message.lower()
    
    def test_check_routing_validity_no_target_selected(self):
        """Test routing check when no target selected."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "router_decisions": {
                "router_1": {"chosen_target": None}
            },
            "graph_structure": {
                "nodes": {"router_1": {}},
                "edges": []
            }
        }
        
        invariants = validator.validate(execution_data)
        
        assert not invariants.all_router_targets_exist
        assert len(invariants.routing_violations) >= 1
        assert "no target selection" in invariants.routing_violations[0].message.lower()
    
    def test_check_cycle_violations_no_cycles(self):
        """Test cycle detection when no cycles exist."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "nodes_executed": ["a", "b", "c", "d"]
        }
        
        invariants = validator.validate(execution_data)
        
        assert not invariants.has_unexpected_cycles
        assert len(invariants.cycle_violations) == 0
        assert len(invariants.cycle_paths) == 0
    
    def test_check_cycle_violations_unexpected_cycle(self):
        """Test cycle detection with unexpected cycle."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "nodes_executed": ["a", "b", "c", "b", "d"]
        }
        
        invariants = validator.validate(execution_data)
        
        assert invariants.has_unexpected_cycles
        assert len(invariants.cycle_violations) >= 1
        assert "appears 2 times" in invariants.cycle_violations[0].message
        assert invariants.cycle_violations[0].node_id == "b"
    
    def test_check_cycle_violations_allowed_reentrant(self):
        """Test cycle detection with allowed reentrant node."""
        validator = ExecutionInvariantsValidator({"allow_reentrant_nodes": ["loop_node"]})
        execution_data = {
            "nodes_executed": ["a", "loop_node", "b", "loop_node", "c"]
        }
        
        invariants = validator.validate(execution_data)
        
        # Reentrant node should not trigger cycle violation
        assert not invariants.has_unexpected_cycles
        assert len(invariants.cycle_violations) == 0
    
    def test_check_tool_call_integrity_no_errors(self):
        """Test tool integrity check when no errors."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "tool_calls": [
                {"status": "success", "node_id": "tool_1"}
            ]
        }
        
        invariants = validator.validate(execution_data)
        
        assert not invariants.has_swallowed_tool_errors
        assert len(invariants.tool_violations) == 0
    
    def test_check_tool_call_integrity_swallowed_error(self):
        """Test tool integrity check when error is swallowed."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "tool_calls": [
                {
                    "status": "error",
                    "node_id": "tool_1",
                    "error_handled": False,
                    "execution_continued_after_error": True
                }
            ]
        }
        
        invariants = validator.validate(execution_data)
        
        assert invariants.has_swallowed_tool_errors
        assert len(invariants.tool_violations) >= 1
        assert "swallowed" in invariants.tool_violations[0].message.lower()
    
    def test_check_tool_call_integrity_handled_error(self):
        """Test tool integrity check when error is properly handled."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "tool_calls": [
                {
                    "status": "error",
                    "node_id": "tool_1",
                    "error_handled": True,
                    "execution_continued_after_error": True
                }
            ]
        }
        
        invariants = validator.validate(execution_data)
        
        # Handled error should not trigger violation
        assert not invariants.has_swallowed_tool_errors
        assert len(invariants.tool_violations) == 0
    
    def test_check_schema_compliance_all_valid(self):
        """Test schema compliance when all outputs valid."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "structured_outputs": {
                "node_1": {"schema_valid": True},
                "node_2": {"schema_valid": True}
            }
        }
        
        invariants = validator.validate(execution_data)
        
        assert invariants.all_structured_outputs_valid
        assert len(invariants.schema_violations) == 0
    
    def test_check_schema_compliance_invalid_output(self):
        """Test schema compliance when output is invalid."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "structured_outputs": {
                "node_1": {
                    "schema_valid": False,
                    "error": "Missing required field 'response'"
                }
            }
        }
        
        invariants = validator.validate(execution_data)
        
        assert not invariants.all_structured_outputs_valid
        assert len(invariants.schema_violations) >= 1
        assert "violating declared schema" in invariants.schema_violations[0].message
    
    def test_check_depth_constraints_no_limit(self):
        """Test depth check when no limit configured."""
        validator = ExecutionInvariantsValidator()
        execution_data = {
            "nodes_executed": ["a", "b", "c", "d", "e", "f"]  # depth 6
        }
        
        invariants = validator.validate(execution_data)
        
        # No limit = no violations
        assert invariants.respects_max_depth
        assert len(invariants.depth_violations) == 0
    
    def test_check_depth_constraints_within_limit(self):
        """Test depth check when within limit."""
        validator = ExecutionInvariantsValidator({"max_depth": 5})
        execution_data = {
            "nodes_executed": ["a", "b", "c"]  # depth 3
        }
        
        invariants = validator.validate(execution_data)
        
        assert invariants.respects_max_depth
        assert len(invariants.depth_violations) == 0
    
    def test_check_depth_constraints_exceeds_limit(self):
        """Test depth check when exceeding limit."""
        validator = ExecutionInvariantsValidator({"max_depth": 3})
        execution_data = {
            "nodes_executed": ["a", "b", "c", "d", "e"]  # depth 5 > 3
        }
        
        invariants = validator.validate(execution_data)
        
        assert not invariants.respects_max_depth
        assert len(invariants.depth_violations) >= 1
        assert "exceeds max_depth" in invariants.depth_violations[0].message
    
    def test_check_depth_constraints_graphscout_candidate(self):
        """Test depth check for GraphScout candidates."""
        validator = ExecutionInvariantsValidator({"max_depth": 3})
        execution_data = {
            "nodes_executed": ["a", "b"],
            "graphscout_candidates": [
                {"path": ["x", "y", "z", "w"]}  # depth 4 > 3
            ]
        }
        
        invariants = validator.validate(execution_data)
        
        assert not invariants.respects_max_depth
        assert len(invariants.depth_violations) >= 1
        assert "GraphScout candidate" in invariants.depth_violations[0].message
    
    def test_validate_integration(self):
        """Test full validation with multiple violation types."""
        validator = ExecutionInvariantsValidator({"max_depth": 3})
        execution_data = {
            "nodes_executed": ["a", "b", "a", "c", "d"],  # cycle: a appears twice, depth 5 > 3
            "fork_groups": {
                "fork_1": {
                    "has_join": False,  # missing join
                    "branches": ["x", "y"],
                    "completed_branches": []
                }
            },
            "router_decisions": {
                "router_1": {"chosen_target": "nonexistent"}  # invalid target
            },
            "graph_structure": {
                "nodes": {"router_1": {}},
                "edges": []
            },
            "tool_calls": [
                {
                    "status": "error",
                    "node_id": "tool_1",
                    "error_handled": False,
                    "execution_continued_after_error": True  # swallowed error
                }
            ],
            "structured_outputs": {
                "node_x": {"schema_valid": False}  # schema violation
            }
        }
        
        invariants = validator.validate(execution_data)
        
        # Should detect all violation types
        assert invariants.has_critical_failures
        assert len(invariants.fork_join_violations) >= 1
        assert len(invariants.routing_violations) >= 1
        assert len(invariants.cycle_violations) >= 1
        assert len(invariants.tool_violations) >= 1
        assert len(invariants.schema_violations) >= 1
        assert len(invariants.depth_violations) >= 1
        
        # Check compact facts structure
        facts = invariants.to_compact_facts()
        assert facts["critical_failures_detected"]
        assert facts["fork_join_integrity"]["status"] == "FAIL"
        assert facts["routing_integrity"]["status"] == "FAIL"
        assert facts["cycle_detection"]["status"] == "FAIL"
        assert facts["tool_integrity"]["status"] == "FAIL"
        assert facts["schema_compliance"]["status"] == "FAIL"
        assert facts["depth_compliance"]["status"] == "FAIL"
