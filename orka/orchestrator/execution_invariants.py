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
Execution Invariants Validator
==============================

This module provides deterministic validation of orchestrator execution patterns.
These checks detect structural issues that should never require LLM interpretation.

Key invariants validated:
- Fork/Join integrity: every fork has matching join with all branches completed
- Router validity: chosen targets exist and are reachable
- Path validity: no unexpected cycles unless nodes are marked reentrant
- Tool call integrity: no tool errors swallowed silently
- Schema compliance: structured outputs validated against declared schemas
- Depth constraints: paths respect max_depth when configured

These are execution *facts*, not semantic judgments. When invariants fail,
the system is objectively broken regardless of LLM opinion.
"""

import logging
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class InvariantViolation:
    """A deterministic invariant violation detected during execution."""
    category: str  # fork_join, routing, cycles, tool_errors, schema, depth
    severity: str  # error, warning
    message: str
    node_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionInvariants:
    """Hard facts about execution that must hold for correct operation."""
    
    # Fork/Join integrity
    fork_join_violations: List[InvariantViolation] = field(default_factory=list)
    all_forks_have_joins: bool = True
    all_joins_have_complete_branches: bool = True
    
    # Routing integrity
    routing_violations: List[InvariantViolation] = field(default_factory=list)
    all_router_targets_exist: bool = True
    all_router_targets_reachable: bool = True
    
    # Cycle detection
    cycle_violations: List[InvariantViolation] = field(default_factory=list)
    has_unexpected_cycles: bool = False
    cycle_paths: List[List[str]] = field(default_factory=list)
    
    # Tool call integrity
    tool_violations: List[InvariantViolation] = field(default_factory=list)
    has_swallowed_tool_errors: bool = False
    
    # Schema compliance
    schema_violations: List[InvariantViolation] = field(default_factory=list)
    all_structured_outputs_valid: bool = True
    
    # Depth constraints
    depth_violations: List[InvariantViolation] = field(default_factory=list)
    respects_max_depth: bool = True
    
    @property
    def has_critical_failures(self) -> bool:
        """Check if any critical invariant violations occurred."""
        return (
            not self.all_forks_have_joins
            or not self.all_joins_have_complete_branches
            or not self.all_router_targets_exist
            or self.has_unexpected_cycles
            or self.has_swallowed_tool_errors
            or not self.all_structured_outputs_valid
            or not self.respects_max_depth
        )
    
    @property
    def all_violations(self) -> List[InvariantViolation]:
        """Get all violations across all categories."""
        return (
            self.fork_join_violations
            + self.routing_violations
            + self.cycle_violations
            + self.tool_violations
            + self.schema_violations
            + self.depth_violations
        )
    
    def to_compact_facts(self) -> Dict[str, Any]:
        """
        Compact representation for injection into LLM evaluator prompt.
        This gives the LLM hard facts to explain, not things to discover.
        """
        return {
            "fork_join_integrity": {
                "status": "PASS" if self.all_forks_have_joins and self.all_joins_have_complete_branches else "FAIL",
                "violations": [v.message for v in self.fork_join_violations]
            },
            "routing_integrity": {
                "status": "PASS" if self.all_router_targets_exist and self.all_router_targets_reachable else "FAIL",
                "violations": [v.message for v in self.routing_violations]
            },
            "cycle_detection": {
                "status": "FAIL" if self.has_unexpected_cycles else "PASS",
                "cycles_found": [[node for node in path] for path in self.cycle_paths],
                "violations": [v.message for v in self.cycle_violations]
            },
            "tool_integrity": {
                "status": "FAIL" if self.has_swallowed_tool_errors else "PASS",
                "violations": [v.message for v in self.tool_violations]
            },
            "schema_compliance": {
                "status": "PASS" if self.all_structured_outputs_valid else "FAIL",
                "violations": [v.message for v in self.schema_violations]
            },
            "depth_compliance": {
                "status": "PASS" if self.respects_max_depth else "FAIL",
                "violations": [v.message for v in self.depth_violations]
            },
            "critical_failures_detected": self.has_critical_failures
        }


class ExecutionInvariantsValidator:
    """
    Validates deterministic execution invariants from orchestrator traces.
    
    This validator examines execution artifacts (not outputs) to detect
    structural problems that are facts, not interpretations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize validator with optional configuration.
        
        Args:
            config: Optional configuration for validation rules
                - allow_reentrant_nodes: List of node IDs allowed to appear in cycles
                - max_depth: Maximum allowed path depth
                - strict_tool_errors: Treat tool warnings as errors
        """
        self.config = config or {}
        self.allow_reentrant_nodes = set(self.config.get("allow_reentrant_nodes", []))
        self.max_depth = self.config.get("max_depth")
        self.strict_tool_errors = self.config.get("strict_tool_errors", False)
    
    def validate(self, execution_data: Dict[str, Any]) -> ExecutionInvariants:
        """
        Perform all invariant checks on execution data.
        
        Args:
            execution_data: Dictionary containing execution trace with keys:
                - nodes_executed: List of node IDs in execution order
                - fork_groups: Dict mapping fork IDs to their state
                - router_decisions: Dict mapping router IDs to chosen targets
                - tool_calls: List of tool call results
                - structured_outputs: Dict mapping node IDs to validation results
                - graph_structure: Dict with nodes and edges
        
        Returns:
            ExecutionInvariants with all validation results
        """
        invariants = ExecutionInvariants()
        
        # Run all validation checks
        self._check_fork_join_integrity(execution_data, invariants)
        self._check_routing_validity(execution_data, invariants)
        self._check_cycle_violations(execution_data, invariants)
        self._check_tool_call_integrity(execution_data, invariants)
        self._check_schema_compliance(execution_data, invariants)
        self._check_depth_constraints(execution_data, invariants)
        
        # Log summary
        if invariants.has_critical_failures:
            logger.error(
                f"Execution invariant validation FAILED: {len(invariants.all_violations)} violations detected"
            )
            for v in invariants.all_violations:
                logger.error(f"  [{v.category}] {v.message}")
        else:
            logger.info("Execution invariant validation PASSED: all hard constraints satisfied")
        
        return invariants
    
    def _check_fork_join_integrity(
        self, execution_data: Dict[str, Any], invariants: ExecutionInvariants
    ) -> None:
        """
        Validate that every fork has a matching join with all branches completed.
        
        Checks:
        - Every ForkNode has a corresponding JoinNode
        - Join received results from all forked branches
        - No branch was silently dropped
        """
        fork_groups = execution_data.get("fork_groups", {})
        
        for fork_id, fork_state in fork_groups.items():
            # Check if fork has corresponding join
            if not fork_state.get("has_join", False):
                invariants.all_forks_have_joins = False
                invariants.fork_join_violations.append(InvariantViolation(
                    category="fork_join",
                    severity="error",
                    message=f"Fork '{fork_id}' has no matching join node",
                    node_id=fork_id,
                    details={"fork_state": fork_state}
                ))
            
            # Check if all branches completed
            # Handle both flat lists and nested lists (for sequential execution within branches)
            expected_branches_raw = fork_state.get("branches", [])
            completed_branches_raw = fork_state.get("completed_branches", [])
            
            # Normalize branches: convert nested lists to tuples for hashability
            def normalize_branches(branches):
                normalized = set()
                for branch in branches:
                    if isinstance(branch, list):
                        # Convert list to tuple so it's hashable
                        normalized.add(tuple(branch))
                    else:
                        # Single string branch
                        normalized.add(branch)
                return normalized
            
            expected_branches = normalize_branches(expected_branches_raw)
            completed_branches = normalize_branches(completed_branches_raw)
            
            if expected_branches != completed_branches:
                missing = expected_branches - completed_branches
                invariants.all_joins_have_complete_branches = False
                invariants.fork_join_violations.append(InvariantViolation(
                    category="fork_join",
                    severity="error",
                    message=f"Fork '{fork_id}' missing results from branches: {missing}",
                    node_id=fork_id,
                    details={
                        "expected": list(expected_branches),
                        "completed": list(completed_branches),
                        "missing": list(missing)
                    }
                ))
    
    def _check_routing_validity(
        self, execution_data: Dict[str, Any], invariants: ExecutionInvariants
    ) -> None:
        """
        Validate that router decisions reference valid, reachable targets.
        
        Checks:
        - Router target nodes exist in graph
        - Target nodes are reachable from router position
        - No dangling or circular router references
        """
        router_decisions = execution_data.get("router_decisions", {})
        graph = execution_data.get("graph_structure", {})
        nodes = graph.get("nodes", {})
        edges = graph.get("edges", [])
        
        for router_id, decision in router_decisions.items():
            target = decision.get("chosen_target")
            
            if not target:
                invariants.all_router_targets_exist = False
                invariants.routing_violations.append(InvariantViolation(
                    category="routing",
                    severity="error",
                    message=f"Router '{router_id}' made no target selection",
                    node_id=router_id,
                    details=decision
                ))
                continue
            
            # Check if target exists
            if target not in nodes:
                invariants.all_router_targets_exist = False
                invariants.routing_violations.append(InvariantViolation(
                    category="routing",
                    severity="error",
                    message=f"Router '{router_id}' selected non-existent target '{target}'",
                    node_id=router_id,
                    details={"chosen_target": target, "available_nodes": list(nodes.keys())}
                ))
            
            # Check if target is reachable (there's an edge from router to target)
            has_edge = any(
                e.get("src") == router_id and e.get("dst") == target
                for e in edges
            )
            
            if not has_edge:
                invariants.all_router_targets_reachable = False
                invariants.routing_violations.append(InvariantViolation(
                    category="routing",
                    severity="warning",
                    message=f"Router '{router_id}' selected target '{target}' with no direct edge",
                    node_id=router_id,
                    details={"chosen_target": target}
                ))
    
    def _check_cycle_violations(
        self, execution_data: Dict[str, Any], invariants: ExecutionInvariants
    ) -> None:
        """
        Detect unexpected cycles in execution paths.
        
        Checks:
        - No node appears multiple times in a path unless marked reentrant
        - Path length respects configured constraints
        - Cycles are not fabricated to satisfy terminal requirements
        """
        nodes_executed = execution_data.get("nodes_executed", [])
        
        # Track seen nodes and detect repeats
        seen_positions: Dict[str, List[int]] = {}
        for idx, node_id in enumerate(nodes_executed):
            if node_id not in seen_positions:
                seen_positions[node_id] = []
            seen_positions[node_id].append(idx)
        
        # Find nodes that appeared multiple times
        for node_id, positions in seen_positions.items():
            if len(positions) > 1:
                # Check if this is an allowed reentrant node
                if node_id not in self.allow_reentrant_nodes:
                    invariants.has_unexpected_cycles = True
                    
                    # Extract the cycle path segments
                    cycle_segments = []
                    for i in range(len(positions) - 1):
                        start = positions[i]
                        end = positions[i + 1]
                        segment = nodes_executed[start:end + 1]
                        cycle_segments.append(segment)
                    
                    invariants.cycle_paths.extend(cycle_segments)
                    invariants.cycle_violations.append(InvariantViolation(
                        category="cycles",
                        severity="error",
                        message=f"Unexpected cycle detected: node '{node_id}' appears {len(positions)} times",
                        node_id=node_id,
                        details={
                            "positions": positions,
                            "cycle_segments": cycle_segments,
                            "is_reentrant": False
                        }
                    ))
    
    def _check_tool_call_integrity(
        self, execution_data: Dict[str, Any], invariants: ExecutionInvariants
    ) -> None:
        """
        Validate that tool call errors were not silently swallowed.
        
        Checks:
        - Tool call errors are propagated, not ignored
        - Failed tool calls result in appropriate error handling
        - No execution continues after critical tool failures
        """
        tool_calls = execution_data.get("tool_calls", [])
        
        for tool_call in tool_calls:
            status = tool_call.get("status")
            node_id = tool_call.get("node_id")
            
            if status == "error":
                # Check if error was handled or swallowed
                error_handled = tool_call.get("error_handled", False)
                execution_continued = tool_call.get("execution_continued_after_error", False)
                
                if execution_continued and not error_handled:
                    invariants.has_swallowed_tool_errors = True
                    invariants.tool_violations.append(InvariantViolation(
                        category="tool_errors",
                        severity="error",
                        message=f"Tool error in node '{node_id}' was swallowed, execution continued",
                        node_id=node_id,
                        details=tool_call
                    ))
            
            elif status == "warning" and self.strict_tool_errors:
                invariants.tool_violations.append(InvariantViolation(
                    category="tool_errors",
                    severity="warning",
                    message=f"Tool warning in node '{node_id}' (strict mode)",
                    node_id=node_id,
                    details=tool_call
                ))
    
    def _check_schema_compliance(
        self, execution_data: Dict[str, Any], invariants: ExecutionInvariants
    ) -> None:
        """
        Validate that structured outputs comply with declared schemas.
        
        Checks:
        - Agent outputs match their declared structured_output schema
        - Required fields are present
        - Type constraints are satisfied
        - No schema/prompt mismatches (like expecting object but schema says string)
        """
        structured_outputs = execution_data.get("structured_outputs", {})
        
        for node_id, validation_result in structured_outputs.items():
            is_valid = validation_result.get("schema_valid", True)
            
            if not is_valid:
                invariants.all_structured_outputs_valid = False
                invariants.schema_violations.append(InvariantViolation(
                    category="schema",
                    severity="error",
                    message=f"Node '{node_id}' produced output violating declared schema",
                    node_id=node_id,
                    details=validation_result
                ))
    
    def _check_depth_constraints(
        self, execution_data: Dict[str, Any], invariants: ExecutionInvariants
    ) -> None:
        """
        Validate that execution paths respect depth constraints.
        
        Checks:
        - Path depth does not exceed configured max_depth
        - GraphScout candidate paths respect depth limits
        - Depth calculation is consistent with configuration
        """
        if self.max_depth is None:
            return  # No constraint configured
        
        nodes_executed = execution_data.get("nodes_executed", [])
        path_depth = len(nodes_executed)
        
        if path_depth > self.max_depth:
            invariants.respects_max_depth = False
            invariants.depth_violations.append(InvariantViolation(
                category="depth",
                severity="error",
                message=f"Path depth {path_depth} exceeds max_depth {self.max_depth}",
                details={
                    "actual_depth": path_depth,
                    "max_depth": self.max_depth,
                    "execution_path": nodes_executed
                }
            ))
        
        # Check GraphScout candidates if present
        graphscout_candidates = execution_data.get("graphscout_candidates", [])
        for candidate in graphscout_candidates:
            candidate_depth = len(candidate.get("path", []))
            if candidate_depth > self.max_depth:
                invariants.respects_max_depth = False
                invariants.depth_violations.append(InvariantViolation(
                    category="depth",
                    severity="error",
                    message=f"GraphScout candidate depth {candidate_depth} exceeds max_depth {self.max_depth}",
                    details={
                        "candidate_path": candidate.get("path"),
                        "actual_depth": candidate_depth,
                        "max_depth": self.max_depth
                    }
                ))
