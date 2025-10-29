# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Graph Introspection Module
=========================

Discovers and analyzes available paths in the workflow graph.
This module implements intelligent path discovery with cycle detection,
constraint checking, and bounded exploration.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from .graph_api import EdgeDescriptor, GraphState, NodeDescriptor

logger = logging.getLogger(__name__)


class GraphIntrospector:
    """
    Intelligent graph exploration and path discovery.

    Discovers available paths from the current position with:
    - Bounded depth exploration
    - Cycle detection and prevention
    - Constraint-based filtering
    - Join feasibility analysis
    """

    def __init__(self, config: Any):
        """Initialize graph introspector with configuration."""
        self.config = config
        self.max_depth = getattr(config, "max_depth", 4)  # Default to 4 if not specified
        self.k_beam = config.k_beam

        logger.debug(f"GraphIntrospector initialized with max_depth={self.max_depth}")

    def _filter_memory_agents_from_candidates(
        self, neighbors: List[str], graph_state: GraphState
    ) -> List[str]:
        """
        Filter out memory agents from regular candidate discovery.
        Memory agents will be handled specially in the execution engine.

        Args:
            neighbors: List of neighbor node IDs
            graph_state: Current graph state with orchestrator info

        Returns:
            Filtered list of neighbors excluding memory agents
        """
        try:
            filtered_neighbors = []
            for neighbor_id in neighbors:
                if not self._is_memory_agent(neighbor_id, graph_state):
                    filtered_neighbors.append(neighbor_id)
                else:
                    logger.debug(f"Filtering memory agent {neighbor_id} from regular candidates")

            memory_count = len(neighbors) - len(filtered_neighbors)
            logger.info(f"Filtered {memory_count} memory agents from {len(neighbors)} neighbors")

            # Debug: Log node types for all neighbors
            for neighbor_id in neighbors:
                node_desc = graph_state.nodes.get(neighbor_id)
                if node_desc:
                    logger.debug(
                        f"Neighbor {neighbor_id}: type='{node_desc.type}', is_memory={node_desc.type in ['MemoryReaderNode', 'MemoryWriterNode']}"
                    )
                else:
                    logger.debug(f"Neighbor {neighbor_id}: no node descriptor found")
            return filtered_neighbors

        except Exception as e:
            logger.error(f"Failed to filter memory agents: {e}")
            return neighbors  # Fallback to original list

    def _filter_control_flow_agents_from_candidates(
        self, neighbors: List[str], graph_state: GraphState
    ) -> List[str]:
        """
        Filter out control flow agents (validators, classifiers) from GraphScout routing.
        These agents are part of the loop's control flow, not routing targets.

        Args:
            neighbors: List of neighbor node IDs
            graph_state: Current graph state with orchestrator info

        Returns:
            Filtered list of neighbors excluding control flow agents
        """
        try:
            # Control flow agent types that should not be routing candidates
            control_flow_types = {
                "PlanValidatorAgent",
                "ValidationAndStructuringAgent",
                "ClassificationAgent",
                "BinaryAgent",
            }

            # Also filter by ID patterns commonly used for control flow
            control_flow_id_patterns = {
                "validator",
                "classifier",
                "input_classifier",
                "path_validator",
                "plan_validator",
            }

            filtered_neighbors = []
            for neighbor_id in neighbors:
                node_desc = graph_state.nodes.get(neighbor_id)

                # Skip if it's a known control flow type
                if node_desc and node_desc.type in control_flow_types:
                    logger.debug(
                        f"Filtering control flow agent {neighbor_id} (type: {node_desc.type})"
                    )
                    continue

                # Skip if ID matches control flow patterns
                neighbor_lower = neighbor_id.lower()
                if any(pattern in neighbor_lower for pattern in control_flow_id_patterns):
                    logger.debug(f"Filtering control flow agent {neighbor_id} (pattern match)")
                    continue

                filtered_neighbors.append(neighbor_id)

            control_count = len(neighbors) - len(filtered_neighbors)
            if control_count > 0:
                logger.info(
                    f"Filtered {control_count} control flow agents from {len(neighbors)} neighbors"
                )

            return filtered_neighbors

        except Exception as e:
            logger.error(f"Failed to filter control flow agents: {e}")
            return neighbors  # Fallback to original list

    def _add_memory_agents_for_shortlist(
        self, neighbors: List[str], graph_state: GraphState
    ) -> List[Dict[str, Any]]:
        """
        Add memory agents back as candidates for shortlist decisions.
        They will be specially positioned by the execution engine.

        Args:
            neighbors: List of neighbor node IDs
            graph_state: Current graph state with orchestrator info

        Returns:
            List of memory agent candidates
        """
        try:
            memory_candidates = []
            for neighbor_id in neighbors:
                if self._is_memory_agent(neighbor_id, graph_state):
                    operation = self._get_memory_operation(neighbor_id, graph_state)
                    candidate = {
                        "node_id": neighbor_id,
                        "path": [neighbor_id],
                        "depth": 1,
                        "feasible": True,
                        "constraints_met": True,
                        "memory_operation": operation,  # Add operation metadata
                        "special_routing": True,  # Mark for special handling
                    }
                    memory_candidates.append(candidate)
                    logger.debug(
                        f"Added memory agent {neighbor_id} ({operation}) for special routing"
                    )

            if memory_candidates:
                logger.info(f"Added {len(memory_candidates)} memory agents for intelligent routing")

            return memory_candidates

        except Exception as e:
            logger.error(f"Failed to add memory agents for shortlist: {e}")
            return []

    def _is_memory_agent(self, agent_id: str, graph_state: GraphState) -> bool:
        """Check if an agent is a memory agent (reader or writer)."""
        try:
            # Get the node descriptor from graph state
            node_desc = graph_state.nodes.get(agent_id)
            if node_desc:
                # Check the node type for memory agents
                node_type = node_desc.type
                return node_type in ["MemoryReaderNode", "MemoryWriterNode"]
            return False
        except Exception as e:
            logger.error(f"Failed to check if {agent_id} is memory agent: {e}")
            return False

    def _get_memory_operation(self, agent_id: str, graph_state: GraphState) -> str:
        """Get the operation type (read/write) for a memory agent."""
        try:
            # Get the node descriptor from graph state
            node_desc = graph_state.nodes.get(agent_id)
            if node_desc:
                node_type = node_desc.type
                if node_type == "MemoryReaderNode":
                    return "read"
                elif node_type == "MemoryWriterNode":
                    return "write"
            return "unknown"
        except Exception as e:
            logger.error(f"Failed to get memory operation for {agent_id}: {e}")
            return "unknown"

    async def discover_paths(
        self,
        graph_state: GraphState,
        question: str,
        context: Dict[str, Any],
        executing_node: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discover candidate paths from current position.

        Args:
            graph_state: Complete graph state
            question: The question/query to route
            context: Execution context

        Returns:
            List of candidate path dictionaries
        """
        try:
            # Use executing_node if provided, otherwise fall back to graph_state.current_node
            current_node = executing_node if executing_node else graph_state.current_node
            visited = graph_state.visited_nodes.copy()

            logger.info(f"Discovering paths from node: {current_node}")

            # Get immediate neighbors
            neighbors = self._get_eligible_neighbors(graph_state, current_node, visited)

            if not neighbors:
                logger.warning(f"No eligible neighbors found for node: {current_node}")
                return []

            # Explore paths with bounded search
            candidates = []

            # Depth 1: Direct neighbors (single-hop paths)
            # Filter out memory agents from regular candidate discovery
            filtered_neighbors = self._filter_memory_agents_from_candidates(neighbors, graph_state)

            # Filter out control flow agents (validators, classifiers) from routing
            filtered_neighbors = self._filter_control_flow_agents_from_candidates(
                filtered_neighbors, graph_state
            )

            for neighbor_id in filtered_neighbors:
                candidate = {
                    "node_id": neighbor_id,
                    "path": [neighbor_id],  # GraphScout direct routing - single node path
                    "depth": 1,
                    "feasible": True,
                    "constraints_met": True,
                }
                candidates.append(candidate)

            # Add memory agents back with special handling for shortlist decision
            memory_candidates = self._add_memory_agents_for_shortlist(neighbors, graph_state)
            candidates.extend(memory_candidates)

            # Depth 2+: Extended paths if configured (multi-hop paths)
            if self.max_depth > 1:
                extended_candidates = await self._explore_extended_paths(
                    graph_state, neighbors, visited, question, context
                )
                # Filter out any single-hop duplicates from extended exploration
                unique_extended = []
                for ext_candidate in extended_candidates:
                    if ext_candidate.get("depth", 1) > 1:  # Only keep multi-hop paths
                        unique_extended.append(ext_candidate)

                candidates.extend(unique_extended)
                logger.info(
                    f"Extended path exploration: found {len(unique_extended)} additional multi-hop candidates"
                )

            # Filter and rank candidates
            filtered_candidates = self._filter_candidates(candidates, graph_state, context)

            # Don't limit to beam width here - let scoring system handle prioritization
            # This allows all candidates (single-hop + multi-hop) to compete fairly
            logger.info(f"Discovered {len(filtered_candidates)} candidate paths")

            return filtered_candidates

        except Exception as e:
            logger.error(f"Path discovery failed: {e}")
            return []

    def _get_eligible_neighbors(
        self, graph_state: GraphState, current_node: str, visited: Set[str]
    ) -> List[str]:
        """Get eligible neighbor nodes from current position."""
        neighbors = []

        try:
            logger.debug(
                f"Looking for neighbors of '{current_node}' in {len(graph_state.edges)} edges"
            )
            logger.debug(f"Available nodes: {list(graph_state.nodes.keys())}")
            logger.debug(f"Edges: {[(e.src, e.dst) for e in graph_state.edges]}")

            # SPECIAL CASE: If current node is GraphScout, it can route to ANY available agent
            # This provides universal compatibility across ALL orchestrator types (sequential, dynamic, fork/join, etc.)
            if current_node in graph_state.nodes:
                current_node_obj = graph_state.nodes[current_node]
                current_is_graphscout = (
                    hasattr(current_node_obj, "type")
                    and "graphscout" in current_node_obj.type.lower()
                )
            else:
                current_is_graphscout = False

            if current_is_graphscout:
                logger.info(
                    f"GraphScout detected - enabling universal agent visibility across all orchestrator types"
                )

                # GraphScout can route to ANY agent in the workflow (except itself)
                # This works for ALL orchestrator strategies: sequential, dynamic, fork/join, parallel, etc.
                available_agents = []

                for node_id, node_obj in graph_state.nodes.items():
                    # Skip self-routing to prevent infinite loops
                    if node_id == current_node:
                        logger.debug(f"Skipping self-routing to {node_id}")
                        continue

                    # Skip already visited nodes to prevent cycles
                    if node_id in visited:
                        logger.debug(f"Skipping visited node: {node_id}")
                        continue

                    # Skip other GraphScout agents to prevent routing loops
                    target_is_graphscout = (
                        hasattr(node_obj, "type") and "graphscout" in node_obj.type.lower()
                    )
                    if target_is_graphscout:
                        logger.debug(f"Skipping other GraphScout agent: {node_id}")
                        continue

                    available_agents.append(node_id)
                    logger.debug(
                        f"GraphScout can route to: {node_id} (type: {getattr(node_obj, 'type', 'unknown')})"
                    )

                logger.info(
                    f"GraphScout universal routing: found {len(available_agents)} available agents (before filtering): {available_agents}"
                )

                # Filter out memory agents from regular candidate discovery
                filtered_agents = self._filter_memory_agents_from_candidates(
                    available_agents, graph_state
                )

                # Filter out control flow agents (validators, classifiers) from GraphScout routing
                filtered_agents = self._filter_control_flow_agents_from_candidates(
                    filtered_agents, graph_state
                )

                logger.info(
                    f"GraphScout routing after filtering: {len(filtered_agents)} agents: {filtered_agents}"
                )
                logger.info(
                    f"GraphScout supports ALL orchestrator types: sequential, dynamic, fork/join, parallel"
                )
                return filtered_agents

            # NORMAL CASE: Follow sequential edges for non-GraphScout agents
            # Find outgoing edges from current node
            for edge in graph_state.edges:
                logger.debug(f"Checking edge: {edge.src} -> {edge.dst}")
                if edge.src == current_node:
                    target_node = edge.dst
                    logger.debug(f"Found outgoing edge to: {target_node}")

                    # Skip already visited nodes (cycle prevention)
                    if target_node in visited:
                        logger.debug(f"Skipping visited node: {target_node}")
                        continue

                    # Check if target node exists
                    if target_node not in graph_state.nodes:
                        logger.warning(f"Target node {target_node} not found in graph")
                        continue

                    # Skip GraphScout agents only if we're currently IN a GraphScout agent
                    # to prevent infinite loops (GraphScout routing to itself)
                    if target_node in graph_state.nodes and current_node in graph_state.nodes:
                        current_node_obj = graph_state.nodes[current_node]
                        target_node_obj = graph_state.nodes[target_node]

                        # Only skip if current node is GraphScout and target is also GraphScout
                        current_is_graphscout = (
                            hasattr(current_node_obj, "type")
                            and "graphscout" in current_node_obj.type.lower()
                        )
                        target_is_graphscout = (
                            hasattr(target_node_obj, "type")
                            and "graphscout" in target_node_obj.type.lower()
                        )
                        logger.info(f"curr{current_is_graphscout}, tar:{target_is_graphscout}")

                        if current_is_graphscout and target_is_graphscout:
                            logger.debug(
                                f"Skipping GraphScout->GraphScout routing: {current_node} -> {target_node}"
                            )
                            continue

                    # Check edge conditions
                    if self._check_edge_condition(edge, graph_state):
                        neighbors.append(target_node)
                        logger.debug(f"Added eligible neighbor: {target_node}")

            logger.debug(f"Found {len(neighbors)} eligible neighbors: {neighbors}")
            return neighbors

        except Exception as e:
            logger.error(f"Failed to get eligible neighbors: {e}")
            return []

    def _check_edge_condition(self, edge: EdgeDescriptor, graph_state: GraphState) -> bool:
        """Check if edge condition is satisfied."""
        try:
            # If no condition, edge is always traversable
            if not edge.condition:
                return True

            # TODO: Implement condition evaluation
            # This would evaluate conditions like:
            # - Previous agent outputs
            # - Runtime state
            # - Budget constraints

            return True

        except Exception as e:
            logger.error(f"Failed to check edge condition: {e}")
            return False

    async def _explore_extended_paths(
        self,
        graph_state: GraphState,
        start_nodes: List[str],
        visited: Set[str],
        question: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Explore multi-step paths from starting nodes."""
        extended_candidates = []

        try:
            # Check if this is GraphScout-initiated path discovery
            initiating_node = context.get("executing_node", graph_state.current_node)
            is_graphscout_discovery = self._is_graphscout_node(graph_state, initiating_node)

            for start_node in start_nodes:
                # Explore paths starting from this node
                paths = await self._explore_from_node(
                    graph_state,
                    start_node,
                    visited | {start_node},
                    [start_node],
                    1,
                    is_graphscout_discovery,
                )

                for path in paths:
                    logger.debug(f"Processing path from _explore_from_node: {' → '.join(path)}")

                    # Ensure all paths end with a response builder
                    terminal_path = await self._ensure_terminal_path(graph_state, path, visited)

                    logger.debug(f"After _ensure_terminal_path: {' → '.join(terminal_path)}")

                    candidate = {
                        "node_id": terminal_path[
                            0
                        ],  # First node in path (starting point for routing)
                        "path": terminal_path,
                        "depth": len(terminal_path),
                        "feasible": True,
                        "constraints_met": True,
                    }
                    extended_candidates.append(candidate)

                    if len(terminal_path) > 1:
                        logger.info(
                            f"Multi-hop candidate added: {' → '.join(terminal_path)} (depth: {len(terminal_path)})"
                        )

                    if len(terminal_path) > len(path):
                        logger.info(
                            f"GraphScout: Enhanced path to ensure terminal: {' → '.join(path)} → {' → '.join(terminal_path)}"
                        )

            return extended_candidates

        except Exception as e:
            logger.error(f"Extended path exploration failed: {e}")
            return []

    async def _explore_from_node(
        self,
        graph_state: GraphState,
        current_node: str,
        visited: Set[str],
        current_path: List[str],
        depth: int,
        is_graphscout_discovery: bool = False,
    ) -> List[List[str]]:
        """Recursively explore paths from a node."""
        paths = []

        try:
            # Stop if max depth reached
            if depth >= self.max_depth:
                return [current_path]

            # Get neighbors of current node
            # For GraphScout, use universal routing even for extended paths
            if self._is_graphscout_node(graph_state, current_node):
                neighbors = self._get_eligible_neighbors(graph_state, current_node, visited)
            else:
                neighbors = self._get_graph_neighbors(graph_state, current_node, visited)

            if not neighbors:
                # Dead end - return current path
                return [current_path]

            # Explore each neighbor
            for neighbor in neighbors:
                new_path = current_path + [neighbor]
                new_visited = visited | {neighbor}

                # Always add the current path as a valid multi-hop path
                if len(new_path) > 1:  # Only multi-hop paths
                    paths.append(new_path)
                    logger.info(
                        f"GraphScout: Created {len(new_path)}-hop path: {' → '.join(new_path)}"
                    )

                # For GraphScout-initiated discovery, stop at response builders to avoid infinite exploration
                if is_graphscout_discovery and self._is_response_builder_node(
                    graph_state, neighbor
                ):
                    logger.debug(f"Stopping exploration at response builder: {neighbor}")
                    continue  # Don't explore further from response builders

                # Recursively explore from neighbor if we haven't reached max depth
                if depth < self.max_depth:
                    sub_paths = await self._explore_from_node(
                        graph_state,
                        neighbor,
                        new_visited,
                        new_path,
                        depth + 1,
                        is_graphscout_discovery,
                    )
                    paths.extend(sub_paths)

            return paths

        except Exception as e:
            logger.error(f"Node exploration failed: {e}")
            return [current_path]

    def _get_graph_neighbors(
        self, graph_state: GraphState, current_node: str, visited: Set[str]
    ) -> List[str]:
        """Get neighbors following actual graph edges (not GraphScout universal routing)."""
        neighbors = []

        try:
            # Find outgoing edges from current node
            for edge in graph_state.edges:
                if edge.src == current_node:
                    target_node = edge.dst

                    # Skip already visited nodes (cycle prevention)
                    if target_node in visited:
                        continue

                    # Check if target node exists
                    if target_node not in graph_state.nodes:
                        continue

                    # Skip GraphScout agents to prevent routing loops
                    if target_node in graph_state.nodes:
                        target_node_obj = graph_state.nodes[target_node]
                        target_is_graphscout = (
                            hasattr(target_node_obj, "type")
                            and "graphscout" in target_node_obj.type.lower()
                        )
                        if target_is_graphscout:
                            continue

                    # Check edge conditions
                    if self._check_edge_condition(edge, graph_state):
                        neighbors.append(target_node)

            return neighbors

        except Exception as e:
            logger.error(f"Failed to get graph neighbors: {e}")
            return []

    def _is_graphscout_node(self, graph_state: GraphState, node_id: str) -> bool:
        """Check if a node is a GraphScout agent."""
        try:
            if node_id in graph_state.nodes:
                node_obj = graph_state.nodes[node_id]
                return hasattr(node_obj, "type") and "graphscout" in node_obj.type.lower()
        except Exception:
            pass
        return False

    def _is_response_builder_node(self, graph_state: GraphState, node_id: str) -> bool:
        """Check if a node is a response builder using capabilities and type."""
        try:
            if node_id in graph_state.nodes:
                node_obj = graph_state.nodes[node_id]

                # Check capabilities first (most reliable)
                if hasattr(node_obj, "capabilities"):
                    capabilities = getattr(node_obj, "capabilities", [])
                    if "answer_emit" in capabilities or "response_generation" in capabilities:
                        return True

                # Fallback to type-based detection
                if hasattr(node_obj, "type"):
                    agent_type = node_obj.type.lower()
                    if (
                        any(
                            term in agent_type
                            for term in [
                                "localllm",
                                "local_llm",
                                "answer",
                                "response",
                                "builder",
                            ]
                        )
                        and "classification" not in agent_type
                    ):
                        return True

                # Name-based fallback
                return (
                    "response_builder" in node_id.lower()
                    or "answer" in node_id.lower()
                    or "final" in node_id.lower()
                )
        except Exception:
            pass
        return False

    async def _ensure_terminal_path(
        self, graph_state: GraphState, path: List[str], visited: Set[str]
    ) -> List[str]:
        """
        Ensure a path ends with a response builder.
        If it doesn't, append the best available response builder.

        Args:
            graph_state: Current graph state
            path: Original path
            visited: Set of visited nodes

        Returns:
            Path guaranteed to end with a response builder
        """
        try:
            # Check if path already ends with a response builder
            if path and self._is_response_builder_node(graph_state, path[-1]):
                return path

            # Find the best response builder to append
            response_builders = []
            path_set = set(path)  # Convert to set for faster lookup
            for node_id in graph_state.nodes:
                if (
                    self._is_response_builder_node(graph_state, node_id)
                    and node_id not in path_set  # Avoid cycles
                    and node_id not in visited  # Respect visited constraints
                ):
                    response_builders.append(node_id)

            if not response_builders:
                # No available response builders, return original path
                logger.warning(
                    f"No available response builders to append to path: {' → '.join(path)}"
                )
                return path

            # Choose the best response builder (prefer "response_builder" in name)
            best_builder = None
            for builder in response_builders:
                if "response_builder" in builder.lower():
                    best_builder = builder
                    break

            if not best_builder:
                best_builder = response_builders[0]  # Take first available

            # Append the response builder to create terminal path
            terminal_path = path + [best_builder]
            logger.debug(f"Enhanced path with terminal agent: {' → '.join(path)} + {best_builder}")

            return terminal_path

        except Exception as e:
            logger.error(f"Failed to ensure terminal path: {e}")
            return path  # Return original path on error

    def _filter_candidates(
        self, candidates: List[Dict[str, Any]], graph_state: GraphState, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter candidates based on constraints and feasibility."""
        filtered = []

        try:
            for candidate in candidates:
                # Check basic feasibility
                if not self._check_path_feasibility(candidate, graph_state):
                    continue

                # Check join requirements
                if not self._check_join_feasibility(candidate, graph_state):
                    continue

                # Check resource constraints
                if not self._check_resource_constraints(candidate, graph_state):
                    continue

                filtered.append(candidate)

            # Don't sort by path length here - let the scoring system handle prioritization
            # This allows multi-hop paths to compete fairly with single-hop paths
            logger.debug(f"Filtered candidates: {len(filtered)} total")
            return filtered

        except Exception as e:
            logger.error(f"Candidate filtering failed: {e}")
            return candidates

    def _check_path_feasibility(self, candidate: Dict[str, Any], graph_state: GraphState) -> bool:
        """Check if path is feasible to execute."""
        try:
            path = candidate["path"]

            # Check all nodes in path exist
            for node_id in path:
                if node_id not in graph_state.nodes:
                    logger.debug(f"Path infeasible: node {node_id} not found")
                    return False

            # SPECIAL CASE: For GraphScout direct routing (depth=1), skip edge connectivity checks
            # GraphScout can route directly to any available agent regardless of edges
            if candidate.get("depth", 1) == 1 and len(path) == 1:
                logger.debug(f"GraphScout direct routing to {path[0]} - skipping edge checks")
                return True

            # Check path connectivity for multi-step paths
            for i in range(len(path) - 1):
                src = path[i]
                dst = path[i + 1]

                # Find edge between nodes
                edge_found = False
                for edge in graph_state.edges:
                    if edge.src == src and edge.dst == dst:
                        edge_found = True
                        break

                if not edge_found:
                    logger.debug(f"Path infeasible: no edge from {src} to {dst}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Path feasibility check failed: {e}")
            return False

    def _check_join_feasibility(self, candidate: Dict[str, Any], graph_state: GraphState) -> bool:
        """Check if path leads to satisfiable joins."""
        try:
            # TODO: Implement join feasibility analysis
            # This would check if downstream joins can be satisfied
            # given the current branch and available parallel paths

            return True

        except Exception as e:
            logger.error(f"Join feasibility check failed: {e}")
            return False

    def _check_resource_constraints(
        self, candidate: Dict[str, Any], graph_state: GraphState
    ) -> bool:
        """Check if path meets resource constraints."""
        try:
            path = candidate["path"]
            budgets = graph_state.budgets

            # Estimate path cost
            estimated_cost = 0.0
            estimated_latency = 0.0

            for node_id in path:
                if node_id in graph_state.nodes:
                    node = graph_state.nodes[node_id]
                    cost_model = node.cost_model

                    estimated_cost += cost_model.get("base_cost", 0.001)
                    estimated_latency += cost_model.get("latency_estimate_ms", 1000)

            # Check against budgets
            max_cost = budgets.get("max_cost_usd", 1.0)
            max_latency = budgets.get("max_latency_ms", 30000)

            if estimated_cost > max_cost:
                logger.debug(f"Path exceeds cost budget: {estimated_cost} > {max_cost}")
                return False

            if estimated_latency > max_latency:
                logger.debug(f"Path exceeds latency budget: {estimated_latency} > {max_latency}")
                return False

            # Store estimates in candidate
            candidate["estimated_cost"] = estimated_cost
            candidate["estimated_latency"] = estimated_latency

            return True

        except Exception as e:
            logger.error(f"Resource constraint check failed: {e}")
            return True  # Default to allowing if check fails
