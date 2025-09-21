# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Graph API Interface
==================

Provides runtime access to the orchestrator's graph structure and state.
This module enables GraphScout to inspect the workflow graph and understand
available paths and constraints.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class NodeDescriptor:
    """Describes a node in the workflow graph."""

    id: str
    type: str
    prompt_summary: str
    capabilities: List[str]
    contract: Dict[str, Any]
    cost_model: Dict[str, Any]
    safety_tags: List[str]
    metadata: Dict[str, Any]


@dataclass
class EdgeDescriptor:
    """Describes an edge between nodes."""

    src: str
    dst: str
    condition: Optional[Dict[str, Any]] = None
    weight: float = 1.0
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class GraphState:
    """Complete graph state for path discovery."""

    nodes: Dict[str, NodeDescriptor]
    edges: List[EdgeDescriptor]
    current_node: str
    visited_nodes: Set[str]
    runtime_state: Dict[str, Any]
    budgets: Dict[str, Any]
    constraints: Dict[str, Any]


class GraphAPI:
    """
    Runtime interface to orchestrator graph structure.

    Provides methods to inspect the workflow graph, understand node
    relationships, and access runtime state for intelligent path selection.
    """

    def __init__(self):
        """Initialize Graph API interface."""
        self.cache: Dict[str, Any] = {}
        logger.debug("GraphAPI initialized")

    async def get_graph_state(self, orchestrator: Any, run_id: str) -> GraphState:
        """
        Get complete graph state for path discovery.

        Args:
            orchestrator: The orchestrator instance
            run_id: Current run identifier

        Returns:
            Complete graph state with nodes, edges, and runtime information
        """
        try:
            # Extract nodes from orchestrator
            nodes = await self._extract_nodes(orchestrator)

            # Build edges from orchestrator configuration
            edges = await self._build_edges(orchestrator)

            # Determine current position
            current_node = await self._get_current_node(orchestrator, run_id)

            # Get visited nodes
            visited_nodes = await self._get_visited_nodes(orchestrator, run_id)

            # Extract runtime state
            runtime_state = await self._get_runtime_state(orchestrator, run_id)

            # Get budget information
            budgets = await self._get_budgets(orchestrator)

            # Get constraints
            constraints = await self._get_constraints(orchestrator)

            graph_state = GraphState(
                nodes=nodes,
                edges=edges,
                current_node=current_node,
                visited_nodes=visited_nodes,
                runtime_state=runtime_state,
                budgets=budgets,
                constraints=constraints,
            )

            logger.debug(
                f"Graph state extracted: {len(nodes)} nodes, {len(edges)} edges, "
                f"current: {current_node}"
            )

            return graph_state

        except Exception as e:
            logger.error(f"Failed to extract graph state: {e}")
            raise

    async def _extract_nodes(self, orchestrator: Any) -> Dict[str, NodeDescriptor]:
        """Extract node descriptors from orchestrator."""
        nodes = {}

        try:
            # Access orchestrator's agents
            if hasattr(orchestrator, "agents"):
                for node_id, agent in orchestrator.agents.items():
                    nodes[node_id] = NodeDescriptor(
                        id=node_id,
                        type=getattr(agent, "type", agent.__class__.__name__),
                        prompt_summary=self._extract_prompt_summary(agent),
                        capabilities=self._extract_capabilities(agent),
                        contract=self._extract_contract(agent),
                        cost_model=self._extract_cost_model(agent),
                        safety_tags=self._extract_safety_tags(agent),
                        metadata=self._extract_metadata(agent),
                    )

            logger.debug(f"Extracted {len(nodes)} node descriptors")
            return nodes

        except Exception as e:
            logger.error(f"Failed to extract nodes: {e}")
            return {}

    async def _build_edges(self, orchestrator: Any) -> List[EdgeDescriptor]:
        """Build edge descriptors from orchestrator configuration."""
        edges = []

        try:
            # Get orchestrator configuration
            if hasattr(orchestrator, "orchestrator_cfg"):
                config = orchestrator.orchestrator_cfg
                strategy = config.get("strategy", "sequential").lower()

                logger.debug(f"Building edges for orchestrator strategy: {strategy}")

                if strategy == "sequential":
                    # Sequential orchestrator: A -> B -> C -> D
                    agent_sequence = config.get("agents", [])
                    for i in range(len(agent_sequence) - 1):
                        src = agent_sequence[i]
                        dst = agent_sequence[i + 1]
                        edges.append(
                            EdgeDescriptor(
                                src=src, dst=dst, weight=1.0, metadata={"type": "sequential"}
                            )
                        )

                elif strategy == "dynamic":
                    # Dynamic orchestrator: All agents can potentially connect to each other
                    # GraphScout will handle the actual routing decisions
                    agent_list = config.get("agents", [])
                    for src in agent_list:
                        for dst in agent_list:
                            if src != dst:  # No self-loops
                                edges.append(
                                    EdgeDescriptor(
                                        src=src, dst=dst, weight=1.0, metadata={"type": "dynamic"}
                                    )
                                )

                elif strategy in ["fork_join", "parallel"]:
                    # Fork/Join orchestrator: Handle fork and join nodes
                    agent_sequence = config.get("agents", [])
                    # Build basic sequential edges, fork/join logic handled by specific nodes
                    for i in range(len(agent_sequence) - 1):
                        src = agent_sequence[i]
                        dst = agent_sequence[i + 1]
                        edges.append(
                            EdgeDescriptor(
                                src=src, dst=dst, weight=1.0, metadata={"type": "fork_join"}
                            )
                        )

                else:
                    # Unknown strategy - create minimal connectivity
                    logger.warning(
                        f"Unknown orchestrator strategy '{strategy}', using minimal connectivity"
                    )
                    agent_list = config.get("agents", [])
                    if len(agent_list) > 1:
                        # Connect first to last as fallback
                        edges.append(
                            EdgeDescriptor(
                                src=agent_list[0],
                                dst=agent_list[-1],
                                weight=1.0,
                                metadata={"type": "fallback"},
                            )
                        )

            logger.debug(
                f"Built {len(edges)} edge descriptors for strategy: {config.get('strategy', 'sequential')}"
            )
            return edges

        except Exception as e:
            logger.error(f"Failed to build edges: {e}")
            return []

    async def _get_current_node(self, orchestrator: Any, run_id: str) -> str:
        """Determine current node position in the workflow."""
        try:
            # For now, use a simple heuristic based on queue position
            if (
                hasattr(orchestrator, "queue")
                and orchestrator.queue
                and isinstance(orchestrator.queue[0], str)
            ):
                return orchestrator.queue[0]

            # Fallback to first agent in configuration
            if hasattr(orchestrator, "orchestrator_cfg"):
                agents = orchestrator.orchestrator_cfg.get("agents", [])
                if agents and isinstance(agents[0], str):
                    return agents[0]

            return "unknown"

        except Exception as e:
            logger.error(f"Failed to determine current node: {e}")
            return "unknown"

    async def _get_visited_nodes(self, orchestrator: Any, run_id: str) -> Set[str]:
        """Get set of already visited nodes."""
        try:
            visited: Set[str] = set()

            # Check memory for executed agents
            if hasattr(orchestrator, "memory") and orchestrator.memory:
                # TODO: Query memory for executed agents in this run
                pass

            return visited

        except Exception as e:
            logger.error(f"Failed to get visited nodes: {e}")
            return set()

    async def _get_runtime_state(self, orchestrator: Any, run_id: str) -> Dict[str, Any]:
        """Get current runtime state."""
        try:
            memory_obj = getattr(orchestrator, "memory", None)
            memory_backend_name = type(memory_obj).__name__ if memory_obj else "None"

            return {
                "run_id": run_id,
                "step_index": getattr(orchestrator, "step_index", 0),
                "queue_length": len(getattr(orchestrator, "queue", [])),
                "memory_backend": memory_backend_name,
            }

        except Exception as e:
            logger.error(f"Failed to get runtime state: {e}")
            return {}

    async def _get_budgets(self, orchestrator: Any) -> Dict[str, Any]:
        """Get budget constraints."""
        try:
            # Extract budget information from orchestrator config
            config = getattr(orchestrator, "orchestrator_cfg", {})
            budgets = config.get("budgets", {})

            # Add default budgets if not specified
            return budgets or {"max_tokens": 10000, "max_cost_usd": 1.0, "max_latency_ms": 30000}

        except Exception as e:
            logger.error(f"Failed to get budgets: {e}")
            return {}

    async def _get_constraints(self, orchestrator: Any) -> Dict[str, Any]:
        """Get workflow constraints."""
        try:
            config = getattr(orchestrator, "orchestrator_cfg", {})
            constraints = config.get("constraints", {})
            return constraints if isinstance(constraints, dict) else {}

        except Exception as e:
            logger.error(f"Failed to get constraints: {e}")
            return {}

    def _extract_prompt_summary(self, agent: Any) -> str:
        """Extract a summary of the agent's prompt."""
        try:
            prompt = getattr(agent, "prompt", "")
            if prompt:
                # Return first 100 characters as summary
                return prompt[:100].replace("\n", " ").strip()
            return f"{agent.__class__.__name__} agent"

        except Exception:
            return "No prompt available"

    def _extract_capabilities(self, agent: Any) -> List[str]:
        """Extract agent capabilities."""
        try:
            capabilities: List[str] = []

            # Infer capabilities from agent type
            agent_type = agent.__class__.__name__.lower()

            if "memory" in agent_type:
                if "reader" in agent_type:
                    capabilities.extend(["memory_read", "semantic_search"])
                elif "writer" in agent_type:
                    capabilities.extend(["memory_write", "data_storage"])
            elif "llm" in agent_type or "openai" in agent_type:
                capabilities.extend(["text_generation", "reasoning", "analysis"])
            elif "router" in agent_type:
                capabilities.extend(["routing", "decision_making"])
            elif "fork" in agent_type:
                capabilities.extend(["parallel_execution", "branching"])
            elif "join" in agent_type:
                capabilities.extend(["aggregation", "merging"])

            return capabilities

        except Exception:
            return []

    def _extract_contract(self, agent: Any) -> Dict[str, Any]:
        """Extract agent input/output contract."""
        try:
            contract = {
                "required_inputs": [],
                "optional_inputs": [],
                "outputs": [],
                "side_effects": False,
            }

            # TODO: Implement contract extraction based on agent type
            # This would analyze the agent's run method signature and behavior

            return contract

        except Exception:
            return {}

    def _extract_cost_model(self, agent: Any) -> Dict[str, Any]:
        """Extract agent cost model."""
        try:
            # Default cost model - can be enhanced with actual metrics
            return {
                "base_cost": 0.001,  # Base cost in USD
                "token_cost": 0.00001,  # Cost per token
                "latency_estimate_ms": 1000,  # Estimated latency
            }

        except Exception:
            return {}

    def _extract_safety_tags(self, agent: Any) -> List[str]:
        """Extract safety-related tags."""
        try:
            tags = []

            # Infer safety considerations from agent type
            agent_type = agent.__class__.__name__.lower()

            if "memory" in agent_type and "writer" in agent_type:
                tags.append("data_modification")
            if "llm" in agent_type:
                tags.append("content_generation")

            return tags

        except Exception:
            return []

    def _extract_metadata(self, agent: Any) -> Dict[str, Any]:
        """Extract additional agent metadata."""
        try:
            return {
                "class_name": agent.__class__.__name__,
                "module": agent.__class__.__module__,
                "node_id": getattr(agent, "node_id", "unknown"),
            }

        except Exception:
            return {}
