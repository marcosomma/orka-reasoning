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
Agent Analyzer
==============

Methods for extracting and analyzing agent information.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class AgentAnalyzerMixin:
    """Mixin providing agent analysis methods for path evaluation."""

    async def _extract_all_agent_info(self, orchestrator: Any) -> Dict[str, Dict[str, Any]]:
        """Extract information for all available agents."""
        try:
            available_agents: Dict[str, Dict[str, Any]] = {}

            if not hasattr(orchestrator, "agents"):
                logger.warning("Orchestrator has no agents attribute")
                return available_agents

            for agent_id, agent in orchestrator.agents.items():
                try:
                    agent_info = {
                        "id": agent_id,
                        "type": agent.__class__.__name__,
                        "description": self._get_agent_description(agent),
                        "prompt": getattr(agent, "prompt", "No prompt available"),
                        "capabilities": self._infer_capabilities(agent),
                        "parameters": self._extract_agent_parameters(agent),
                        "cost_estimate": self._estimate_agent_cost(agent),
                        "latency_estimate": self._estimate_agent_latency(agent),
                    }
                    available_agents[agent_id] = agent_info

                except Exception as e:
                    logger.error(f"Failed to extract info for agent {agent_id}: {e}")
                    available_agents[agent_id] = {
                        "id": agent_id,
                        "type": "error",
                        "description": "Failed to extract agent information",
                        "prompt": "",
                        "capabilities": [],
                        "parameters": {},
                        "cost_estimate": 0.0,
                        "latency_estimate": 0,
                    }

            logger.info(f"Extracted information for {len(available_agents)} agents")
            return available_agents

        except Exception as e:
            logger.error(f"Failed to extract agent information: {e}")
            return {}

    async def _extract_agent_info(self, node_id: str, orchestrator: Any) -> Dict[str, Any]:
        """Extract comprehensive agent information for a single agent."""
        try:
            if not hasattr(orchestrator, "agents") or node_id not in orchestrator.agents:
                return {
                    "id": node_id,
                    "type": "unknown",
                    "capabilities": [],
                    "prompt": "Agent not found",
                }

            agent = orchestrator.agents[node_id]

            return {
                "id": node_id,
                "type": agent.__class__.__name__,
                "capabilities": self._infer_capabilities(agent),
                "prompt": getattr(agent, "prompt", "No prompt available"),
                "cost_model": getattr(agent, "cost_model", {}),
                "safety_tags": getattr(agent, "safety_tags", []),
            }

        except Exception as e:
            logger.error(f"Failed to extract agent info for {node_id}: {e}")
            return {"id": node_id, "type": "error", "capabilities": [], "prompt": ""}

    def _infer_capabilities(self, agent: Any) -> List[str]:
        """Infer agent capabilities from real Orka agent class names."""
        capabilities = []
        agent_class_name = agent.__class__.__name__.lower()

        # Real Orka agent capability mapping
        if "localllmagent" in agent_class_name or "openaianswerbuilder" in agent_class_name:
            capabilities.extend(["text_generation", "reasoning", "analysis", "response_generation"])
        elif "duckduckgotool" in agent_class_name:
            capabilities.extend(["information_retrieval", "web_search", "current_information"])
        elif "memoryreadernode" in agent_class_name:
            capabilities.extend(["memory_retrieval", "information_access"])
        elif "memorywriternode" in agent_class_name:
            capabilities.extend(["memory_storage", "information_persistence"])
        elif (
            "classificationagent" in agent_class_name
            or "openaiclassificationagent" in agent_class_name
        ):
            capabilities.extend(["text_classification", "categorization", "input_routing"])
        elif "routernode" in agent_class_name:
            capabilities.extend(["routing", "decision_making", "workflow_control"])
        elif "graphscoutagent" in agent_class_name:
            capabilities.extend(["intelligent_routing", "path_optimization", "workflow_planning"])
        elif "binaryagent" in agent_class_name or "openaibinaryagent" in agent_class_name:
            capabilities.extend(["binary_decision", "yes_no_evaluation"])
        elif "validationandstructuringagent" in agent_class_name:
            capabilities.extend(["validation", "structuring", "data_formatting"])

        return capabilities

    def _get_agent_description(self, agent: Any) -> str:
        """Generate a human-readable description based on real Orka agent class names."""
        agent_class_name = agent.__class__.__name__

        # Real Orka agent descriptions
        descriptions = {
            "LocalLLMAgent": "Local Large Language Model agent for text generation, reasoning, and analysis",
            "OpenAIAnswerBuilder": "OpenAI-powered answer builder for comprehensive response generation",
            "DuckDuckGoTool": "DuckDuckGo search tool for retrieving current information from web sources",
            "MemoryReaderNode": "Memory reader that retrieves stored information from the knowledge base",
            "MemoryWriterNode": "Memory writer that stores information in the knowledge base",
            "OpenAIClassificationAgent": "OpenAI-powered classification agent for categorizing input",
            "ClassificationAgent": "Classification agent that categorizes input into predefined categories",
            "RouterNode": "Router node that makes intelligent routing decisions in workflows",
            "GraphScoutAgent": "GraphScout intelligent routing agent for optimal path selection",
            "BinaryAgent": "Binary decision agent for yes/no evaluations",
            "OpenAIBinaryAgent": "OpenAI-powered binary decision agent",
            "ValidationAndStructuringAgent": "Validation and structuring agent for data formatting and validation",
            "ForkNode": "Fork node for parallel workflow execution",
            "JoinNode": "Join node for merging parallel workflow results",
            "LoopNode": "Loop node for iterative workflow execution",
            "FailoverNode": "Failover node for fault-tolerant workflow execution",
            "FailingNode": "Failing node for testing error handling",
        }

        return descriptions.get(agent_class_name, f"Orka agent of type {agent_class_name}")

    def _extract_agent_parameters(self, agent: Any) -> Dict[str, Any]:
        """Extract relevant parameters from agent configuration."""
        params = {}

        # Common parameters to extract
        param_names = ["model", "temperature", "max_tokens", "timeout", "max_results"]

        for param in param_names:
            if hasattr(agent, param):
                params[param] = getattr(agent, param)

        return params

    def _estimate_agent_cost(self, agent: Any) -> float:
        """Estimate the cost of running this Orka agent."""
        agent_class_name = agent.__class__.__name__

        # Real Orka agent cost estimates
        cost_map = {
            "OpenAIAnswerBuilder": 0.003,  # OpenAI API cost (higher than local)
            "OpenAIClassificationAgent": 0.001,  # OpenAI classification cost
            "OpenAIBinaryAgent": 0.0008,  # OpenAI binary decision cost
            "LocalLLMAgent": 0.0005,  # Local LLM cost (electricity + compute)
            "DuckDuckGoTool": 0.0002,  # Free search API, minimal compute cost
            "MemoryReaderNode": 0.0001,  # Memory operation cost
            "MemoryWriterNode": 0.0001,  # Memory operation cost
            "ClassificationAgent": 0.0003,  # Local classification cost
            "BinaryAgent": 0.0003,  # Local classification cost
            "GraphScoutAgent": 0.002,  # Complex routing decisions with LLM evaluation
            "RouterNode": 0.00005,  # Minimal workflow control cost
            "ForkNode": 0.00005,
            "JoinNode": 0.00005,
            "LoopNode": 0.00005,
        }

        return cost_map.get(agent_class_name, 0.001)

    def _estimate_agent_latency(self, agent: Any) -> int:
        """Estimate the latency of running this Orka agent in milliseconds."""
        agent_class_name = agent.__class__.__name__

        # Real Orka agent latency estimates
        latency_map = {
            "OpenAIAnswerBuilder": 3000,  # OpenAI API latency (network + processing)
            "OpenAIClassificationAgent": 1500,  # OpenAI classification latency
            "OpenAIBinaryAgent": 1200,  # OpenAI binary decision latency
            "LocalLLMAgent": 4000,  # Local LLM latency (depends on model size)
            "DuckDuckGoTool": 800,  # Web search latency
            "MemoryReaderNode": 200,  # Memory read latency (Redis/vector search)
            "MemoryWriterNode": 300,  # Memory write latency (Redis + embedding)
            "ClassificationAgent": 100,  # Local classification latency
            "BinaryAgent": 100,
            "GraphScoutAgent": 2500,  # Complex routing with LLM evaluation
            "RouterNode": 50,  # Minimal workflow control latency
            "ForkNode": 50,
            "JoinNode": 50,
            "LoopNode": 50,
        }

        return latency_map.get(agent_class_name, 1000)

