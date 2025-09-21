# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Smart Path Evaluator
===================

Intelligent LLM-powered path evaluation system that replaces static mocks
with dynamic reasoning about optimal workflow paths.

Uses a two-stage LLM approach:
1. Path Selection LLM: Analyzes agent capabilities and suggests best paths
2. Validation LLM: Validates selections and assesses efficiency
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PathEvaluation:
    """Result of LLM path evaluation."""

    node_id: str
    relevance_score: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    reasoning: str
    expected_output: str
    estimated_tokens: int
    estimated_cost: float
    estimated_latency_ms: int
    risk_factors: List[str]
    efficiency_rating: str  # "high", "medium", "low"


@dataclass
class ValidationResult:
    """Result of LLM validation."""

    is_valid: bool
    confidence: float
    efficiency_score: float  # 0.0 - 1.0
    validation_reasoning: str
    suggested_improvements: List[str]
    risk_assessment: str


class SmartPathEvaluator:
    """
    LLM-powered intelligent path evaluation system.

    Replaces static mocks with dynamic reasoning about:
    - Agent capability matching
    - Expected output quality
    - Resource efficiency
    - Risk assessment
    """

    def __init__(self, config: Any):
        """Initialize smart evaluator with LLM configuration."""
        self.config = config
        self.max_preview_tokens = config.max_preview_tokens

        # LLM configuration for two-stage evaluation
        self.evaluation_llm_config = {
            "model": getattr(config, "evaluation_model", "local_llm"),  # Fast local model
            "model_name": getattr(
                config, "evaluation_model_name", "llama3.2:latest"
            ),  # Configurable model name
            "max_tokens": 500,
            "temperature": 0.1,  # Low temperature for consistent reasoning
        }

        self.validation_llm_config = {
            "model": getattr(config, "validation_model", "local_llm"),  # Fast local model
            "model_name": getattr(
                config, "validation_model_name", "llama3.2:latest"
            ),  # Configurable model name
            "max_tokens": 300,
            "temperature": 0.0,  # Deterministic validation
        }

        logger.debug("SmartPathEvaluator initialized with LLM-powered evaluation")

    async def simulate_candidates(
        self,
        candidates: List[Dict[str, Any]],
        question: str,
        context: Dict[str, Any],
        orchestrator: Any,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate candidates using LLM reasoning based on real agent information.

        Args:
            candidates: List of candidate paths
            question: The question being routed
            context: Execution context
            orchestrator: Orchestrator instance

        Returns:
            Candidates with LLM evaluation results
        """
        try:
            # Extract all available agent information
            available_agents = await self._extract_all_agent_info(orchestrator)

            # Generate all possible path combinations
            possible_paths = self._generate_possible_paths(available_agents, candidates)

            # Let LLM evaluate all paths at once for optimal decision making
            evaluation_results = await self._llm_path_evaluation(
                question, available_agents, possible_paths, context
            )

            # Map evaluation results back to candidates
            evaluated_candidates = self._map_evaluation_to_candidates(
                candidates, evaluation_results, available_agents
            )

            logger.info(
                f"LLM-evaluated {len(evaluated_candidates)} candidates based on real agent data"
            )
            return evaluated_candidates

        except Exception as e:
            logger.error(f"Smart evaluation failed, falling back to heuristics: {e}")
            # Fallback to basic heuristic evaluation
            return await self._fallback_heuristic_evaluation(candidates, question, context)

    async def _stage1_path_evaluation(
        self, candidate: Dict[str, Any], question: str, context: Dict[str, Any], orchestrator: Any
    ) -> PathEvaluation:
        """
        Stage 1: LLM analyzes agent capabilities and suggests path suitability.
        """
        try:
            node_id = candidate["node_id"]

            # Get agent information
            agent_info = await self._extract_agent_info(node_id, orchestrator)

            # Construct evaluation prompt
            evaluation_prompt = self._build_evaluation_prompt(
                question, agent_info, candidate, context
            )

            # Call LLM for path evaluation
            llm_response = await self._call_evaluation_llm(evaluation_prompt)

            # Parse LLM response into structured evaluation
            evaluation = self._parse_evaluation_response(llm_response, node_id)

            # CRITICAL: Prevent self-routing by overriding LLM if it tries to route to current agent
            current_agent = context.get("current_agent_id", "unknown")
            if node_id == current_agent:
                logger.warning(
                    f"LLM tried to route to current agent {node_id}, overriding to prevent loop"
                )
                evaluation.relevance_score = 0.0
                evaluation.confidence = 0.0
                evaluation.reasoning = f"Prevented self-routing to {node_id} to avoid infinite loop"
                evaluation.efficiency_rating = "low"
                evaluation.risk_factors = ["infinite_loop_prevention"]

            return evaluation

        except Exception as e:
            logger.error(f"Stage 1 evaluation failed for {candidate.get('node_id')}: {e}")
            return self._create_fallback_evaluation(candidate["node_id"])

    async def _stage2_path_validation(
        self,
        candidate: Dict[str, Any],
        evaluation: PathEvaluation,
        question: str,
        context: Dict[str, Any],
    ) -> ValidationResult:
        """
        Stage 2: LLM validates the path selection and assesses efficiency.
        """
        try:
            # Construct validation prompt
            validation_prompt = self._build_validation_prompt(
                question, candidate, evaluation, context
            )

            # Call LLM for validation
            llm_response = await self._call_validation_llm(validation_prompt)

            # Parse validation response
            return self._parse_validation_response(llm_response)

        except Exception as e:
            logger.error(f"Stage 2 validation failed for {candidate.get('node_id')}: {e}")
            return self._create_fallback_validation()

    def _build_evaluation_prompt(
        self,
        question: str,
        agent_info: Dict[str, Any],
        candidate: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        """Build prompt for Stage 1 LLM evaluation."""

        current_agent = context.get("current_agent_id", "unknown")

        return f"""You are an AI workflow routing expert. Analyze if this agent is suitable for the given question.

QUESTION TO ROUTE:
{question}

AGENT INFORMATION:
- Agent ID: {agent_info['id']}
- Agent Type: {agent_info['type']}
- Capabilities: {', '.join(agent_info['capabilities'])}
- Agent Prompt: {agent_info['prompt'][:200]}...

PATH INFORMATION:
- Path: {' -> '.join(candidate['path'])}
- Depth: {candidate.get('depth', 1)}

CONTEXT:
- Current Agent: {current_agent}
- Previous outputs available: {list(context.get('previous_outputs', {}).keys())}

CRITICAL REQUIREMENTS:
- The workflow MUST end with an agent type that generate comprehensive LLM response to the user. Best suitable agent type for this task are local_llm and openaai based ones. 
- NEVER route to the same agent that is currently making the routing decision
- This prevents infinite loops and ensures workflow progression
- Consider if this path leads to or enables a final answer generation
- Prioritize paths that contribute to complete user responses and workflow progression

CONSTRAINS: 
- The result path has to finish with a llm agent able to return a response 

TASK: Evaluate this agent's suitability for answering the question and contributing to a final response.

RESPONSE FORMAT: You MUST respond with ONLY valid JSON. No explanations, no markdown, no code blocks. Just the JSON object:

{{
    "relevance_score": 0.0 to 1.0,
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation here",
    "expected_output": "What this agent would produce",
    "estimated_tokens": "Estimated token used",
    "estimated_cost": "Estimated cost average",
    "estimated_latency_ms": "Estimated latency average in ms",
    "risk_factors": ["risk1", "risk2"],
    "efficiency_rating": "high"
}}"""

    def _build_validation_prompt(
        self,
        question: str,
        candidate: Dict[str, Any],
        evaluation: PathEvaluation,
        context: Dict[str, Any],
    ) -> str:
        """Build prompt for Stage 2 LLM validation."""

        return f"""You are an AI workflow efficiency validator. Review this path selection and validate its quality.

ORIGINAL QUESTION:
{question}

PROPOSED PATH:
- Agent: {candidate['node_id']}
- Path: {' -> '.join(candidate['path'])}

STAGE 1 EVALUATION:
- Relevance Score: {evaluation.relevance_score}
- Confidence: {evaluation.confidence}
- Reasoning: {evaluation.reasoning}
- Expected Output: {evaluation.expected_output}
- Efficiency Rating: {evaluation.efficiency_rating}
- Risk Factors: {', '.join(evaluation.risk_factors)}

CRITICAL REQUIREMENT:
- The workflow MUST end with a comprehensive LLM-generated response to the user
- Validate that this path contributes to complete user satisfaction
- Consider the full workflow completion, not just this single step

CONSTRAINS: 
- The result path has to finish with a llm agent able to return a response 

TASK: Validate this selection and assess its efficiency for complete workflow execution.

Consider:
1. Is the agent truly capable of handling this question?
2. Does this path contribute to a complete final response?
3. Are there obvious better alternatives for workflow completion?
4. Is the resource usage justified for the full workflow?
5. Are the risk factors acceptable?

RESPONSE FORMAT: You MUST respond with ONLY valid JSON. No explanations, no markdown, no code blocks. Just the JSON object:

{{
    "is_valid": true/false,
    "confidence": 0.0 to 1.0,
    "efficiency_score": 0.0 to 1.0,
    "validation_reasoning": "Brief explanation here",
    "suggested_improvements": ["improvement1", "improvement2"],
    "risk_assessment": "low"
}}"""

    async def _call_evaluation_llm(self, prompt: str) -> str:
        """Call LLM for Stage 1 evaluation."""
        try:
            # Check if LLM evaluation is enabled
            if not getattr(self.config, "llm_evaluation_enabled", True):
                logger.warning("LLM evaluation disabled, cannot proceed without LLM")
                raise ValueError("LLM evaluation is required but disabled")

            # Get LLM configuration
            model = getattr(self.config, "evaluation_model", "local_llm")
            model_name = getattr(self.config, "evaluation_model_name", "llama3.2:latest")
            model_url = getattr(self.config, "model_url", "http://localhost:11434/api/generate")
            provider = getattr(self.config, "provider", "ollama")
            temperature = 0.1  # Low temperature for consistent evaluation

            # Make actual LLM call
            if model == "local_llm" or provider.lower() == "ollama":
                raw_response = await self._call_ollama_async(
                    model_url, model_name, prompt, temperature
                )
            elif provider.lower() in ["lm_studio", "lmstudio"]:
                raw_response = await self._call_lm_studio_async(
                    model_url, model_name, prompt, temperature
                )
            else:
                # Unsupported provider
                logger.error(f"Unsupported LLM provider: {provider}")
                raise ValueError(f"Unsupported LLM provider: {provider}")

            # Try to extract JSON from response
            json_response = self._extract_json_from_response(raw_response)
            if json_response:
                return json_response

            # If JSON extraction fails, raise error
            logger.error("Failed to extract JSON from LLM response")
            raise ValueError("LLM response does not contain valid JSON")

        except Exception as e:
            logger.error(f"Evaluation LLM call failed: {e}")
            raise

    async def _call_validation_llm(self, prompt: str) -> str:
        """Call LLM for Stage 2 validation."""
        try:
            # Check if LLM evaluation is enabled
            if not getattr(self.config, "llm_evaluation_enabled", True):
                logger.warning("LLM validation disabled, cannot proceed without LLM")
                raise ValueError("LLM validation is required but disabled")

            # Get LLM configuration
            model = getattr(self.config, "validation_model", "local_llm")
            model_name = getattr(self.config, "validation_model_name", "llama3.2:latest")
            model_url = getattr(self.config, "model_url", "http://localhost:11434/api/generate")
            provider = getattr(self.config, "provider", "ollama")
            temperature = 0.0  # Deterministic validation

            # Make actual LLM call
            if model == "local_llm" or provider.lower() == "ollama":
                raw_response = await self._call_ollama_async(
                    model_url, model_name, prompt, temperature
                )
            elif provider.lower() in ["lm_studio", "lmstudio"]:
                raw_response = await self._call_lm_studio_async(
                    model_url, model_name, prompt, temperature
                )
            else:
                # Unsupported provider
                logger.error(f"Unsupported LLM provider: {provider}")
                raise ValueError(f"Unsupported LLM provider: {provider}")

            # Try to extract JSON from response
            json_response = self._extract_json_from_response(raw_response)
            if json_response:
                return json_response

            # If JSON extraction fails, raise error
            logger.error("Failed to extract JSON from LLM validation response")
            raise ValueError("LLM validation response does not contain valid JSON")

        except Exception as e:
            logger.error(f"Validation LLM call failed: {e}")
            raise

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
        if agent_class_name == "LocalLLMAgent":
            return "Local Large Language Model agent for text generation, reasoning, and analysis"
        elif agent_class_name == "OpenAIAnswerBuilder":
            return "OpenAI-powered answer builder for comprehensive response generation"
        elif agent_class_name == "DuckDuckGoTool":
            return "DuckDuckGo search tool for retrieving current information from web sources"
        elif agent_class_name == "MemoryReaderNode":
            return "Memory reader that retrieves stored information from the knowledge base"
        elif agent_class_name == "MemoryWriterNode":
            return "Memory writer that stores information in the knowledge base"
        elif agent_class_name == "OpenAIClassificationAgent":
            return "OpenAI-powered classification agent for categorizing input"
        elif agent_class_name == "ClassificationAgent":
            return "Classification agent that categorizes input into predefined categories"
        elif agent_class_name == "RouterNode":
            return "Router node that makes intelligent routing decisions in workflows"
        elif agent_class_name == "GraphScoutAgent":
            return "GraphScout intelligent routing agent for optimal path selection"
        elif agent_class_name == "BinaryAgent":
            return "Binary decision agent for yes/no evaluations"
        elif agent_class_name == "OpenAIBinaryAgent":
            return "OpenAI-powered binary decision agent"
        elif agent_class_name == "ValidationAndStructuringAgent":
            return "Validation and structuring agent for data formatting and validation"
        elif agent_class_name == "ForkNode":
            return "Fork node for parallel workflow execution"
        elif agent_class_name == "JoinNode":
            return "Join node for merging parallel workflow results"
        elif agent_class_name == "LoopNode":
            return "Loop node for iterative workflow execution"
        elif agent_class_name == "FailoverNode":
            return "Failover node for fault-tolerant workflow execution"
        elif agent_class_name == "FailingNode":
            return "Failing node for testing error handling"
        else:
            return f"Orka agent of type {agent_class_name}"

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
        if agent_class_name == "OpenAIAnswerBuilder":
            return 0.003  # OpenAI API cost (higher than local)
        elif agent_class_name == "OpenAIClassificationAgent":
            return 0.001  # OpenAI classification cost
        elif agent_class_name == "OpenAIBinaryAgent":
            return 0.0008  # OpenAI binary decision cost
        elif agent_class_name == "LocalLLMAgent":
            return 0.0005  # Local LLM cost (electricity + compute)
        elif agent_class_name == "DuckDuckGoTool":
            return 0.0002  # Free search API, minimal compute cost
        elif agent_class_name in ["MemoryReaderNode", "MemoryWriterNode"]:
            return 0.0001  # Memory operation cost
        elif agent_class_name in ["ClassificationAgent", "BinaryAgent"]:
            return 0.0003  # Local classification cost
        elif agent_class_name == "GraphScoutAgent":
            return 0.002  # Complex routing decisions with LLM evaluation
        elif agent_class_name in ["RouterNode", "ForkNode", "JoinNode", "LoopNode"]:
            return 0.00005  # Minimal workflow control cost
        else:
            return 0.001  # Default cost

    def _estimate_agent_latency(self, agent: Any) -> int:
        """Estimate the latency of running this Orka agent in milliseconds."""
        agent_class_name = agent.__class__.__name__

        # Real Orka agent latency estimates
        if agent_class_name == "OpenAIAnswerBuilder":
            return 3000  # OpenAI API latency (network + processing)
        elif agent_class_name == "OpenAIClassificationAgent":
            return 1500  # OpenAI classification latency
        elif agent_class_name == "OpenAIBinaryAgent":
            return 1200  # OpenAI binary decision latency
        elif agent_class_name == "LocalLLMAgent":
            return 4000  # Local LLM latency (depends on model size)
        elif agent_class_name == "DuckDuckGoTool":
            return 800  # Web search latency
        elif agent_class_name == "MemoryReaderNode":
            return 200  # Memory read latency (Redis/vector search)
        elif agent_class_name == "MemoryWriterNode":
            return 300  # Memory write latency (Redis + embedding)
        elif agent_class_name in ["ClassificationAgent", "BinaryAgent"]:
            return 100  # Local classification latency
        elif agent_class_name == "GraphScoutAgent":
            return 2500  # Complex routing with LLM evaluation
        elif agent_class_name in ["RouterNode", "ForkNode", "JoinNode", "LoopNode"]:
            return 50  # Minimal workflow control latency
        else:
            return 1000  # Default latency

    def _generate_possible_paths(
        self, available_agents: Dict[str, Dict[str, Any]], candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate all possible path combinations from available agents."""
        possible_paths = []

        # Extract existing candidate paths
        for candidate in candidates:
            path = candidate.get("path", [candidate.get("node_id", "")])
            if path:
                possible_paths.append(
                    {
                        "path": path,
                        "agents": [available_agents.get(agent_id, {}) for agent_id in path],
                        "total_cost": sum(
                            available_agents.get(agent_id, {}).get("cost_estimate", 0)
                            for agent_id in path
                        ),
                        "total_latency": sum(
                            available_agents.get(agent_id, {}).get("latency_estimate", 0)
                            for agent_id in path
                        ),
                    }
                )

        return possible_paths

    async def _llm_path_evaluation(
        self,
        question: str,
        available_agents: Dict[str, Dict[str, Any]],
        possible_paths: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Let LLM evaluate all possible paths and choose the best one."""
        try:
            # Build comprehensive evaluation prompt
            evaluation_prompt = self._build_comprehensive_evaluation_prompt(
                question, available_agents, possible_paths, context
            )

            # Call LLM for evaluation
            llm_response = await self._call_evaluation_llm(evaluation_prompt)

            # Parse the response
            return self._parse_comprehensive_evaluation_response(llm_response)

        except Exception as e:
            logger.error(f"LLM path evaluation failed: {e}")
            return {"error": str(e), "fallback": True}

    def _build_comprehensive_evaluation_prompt(
        self,
        question: str,
        available_agents: Dict[str, Dict[str, Any]],
        possible_paths: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> str:
        """Build a comprehensive prompt for LLM to evaluate all paths."""

        # Format available agents
        agents_info = []
        for agent_id, agent_info in available_agents.items():
            agents_info.append(
                f"""
Agent ID: {agent_id}
Type: {agent_info['type']}
Description: {agent_info['description']}
Capabilities: {', '.join(agent_info['capabilities'])}
Prompt: {agent_info['prompt'][:200]}...
Cost Estimate: ${agent_info['cost_estimate']:.4f}
Latency Estimate: {agent_info['latency_estimate']}ms
"""
            )

        # Format possible paths
        paths_info = []
        for i, path_info in enumerate(possible_paths):
            path_agents = " → ".join([agent["id"] for agent in path_info["agents"]])
            paths_info.append(
                f"""
Path {i+1}: {path_agents}
Total Cost: ${path_info['total_cost']:.4f}
Total Latency: {path_info['total_latency']}ms
Agent Details:
{chr(10).join([f"  - {agent['id']}: {agent['description']}" for agent in path_info['agents']])}
"""
            )

        current_agent = context.get("current_agent_id", "unknown")
        previous_outputs = list(context.get("previous_outputs", {}).keys())

        return f"""You are an AI workflow routing expert. Analyze the question and provide SPECIFIC, DIFFERENTIATED evaluations for each path.

QUESTION TO ROUTE: "{question}"
QUESTION TYPE: {"Factual information request" if "news" in question.lower() or "today" in question.lower() else "General query"}

AVAILABLE AGENTS:
{chr(10).join(agents_info)}

POSSIBLE PATHS TO EVALUATE:
{chr(10).join(paths_info)}

CONTEXT:
- Current Agent: {current_agent}
- Previous Outputs Available: {', '.join(previous_outputs)}

EVALUATION CRITERIA:
1. **Relevance**: How well does this path match the question type?
   - For news/factual queries: Search agents score higher
   - For analysis queries: Analysis agents score higher
   - For memory queries: Memory agents score higher

2. **Completeness**: Does the path end with a response-generating agent?
   - Multi-hop paths ending with response_builder score higher
   - Single agents that can't generate final responses score lower

3. **Efficiency**: Balance of cost, latency, and quality
   - Shorter paths are more efficient but may lack completeness
   - Longer paths are more complete but costlier

4. **Specificity**: Each path should have DIFFERENT scores and reasoning

CRITICAL REQUIREMENTS:
- NEVER route to the current agent ({current_agent})
- Each path MUST have a UNIQUE score (no identical scores)
- Provide SPECIFIC pros/cons for each path
- For factual questions, prioritize search → response_builder paths
- Multi-hop paths should generally score higher than single-hop for completeness

RESPONSE FORMAT: You MUST respond with ONLY valid JSON. Each path must have different scores and specific reasoning:

{{
    "recommended_path": ["best_agent1", "best_agent2"],
    "reasoning": "Specific explanation why this path is optimal for this question type",
    "confidence": 0.0 to 1.0,
    "expected_outcome": "Specific outcome for this question",
    "path_evaluations": [
        {{
            "path": ["agent1"],
            "score": 0.X,
            "pros": ["specific advantage 1", "specific advantage 2"],
            "cons": ["specific limitation 1", "specific limitation 2"]
        }},
        {{
            "path": ["agent2", "response_builder"],
            "score": 0.Y,
            "pros": ["different advantage 1", "different advantage 2"],
            "cons": ["different limitation 1"]
        }}
    ]
}}

IMPORTANT: Make each evaluation UNIQUE and SPECIFIC to the path and question type. No generic responses!"""

    def _parse_comprehensive_evaluation_response(self, response: str) -> Dict[str, Any]:
        """Parse the comprehensive LLM evaluation response."""
        try:
            data = json.loads(response)

            # Ensure data is a dictionary
            if not isinstance(data, dict):
                raise ValueError("Response is not a valid JSON object")

            # Validate required fields
            required_fields = ["recommended_path", "reasoning", "confidence"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            return data

        except Exception as e:
            logger.error(f"Failed to parse comprehensive evaluation response: {e}")
            return {
                "recommended_path": [],
                "reasoning": "Failed to parse LLM response",
                "confidence": 0.3,
                "expected_outcome": "Unknown",
                "path_evaluations": [],
            }

    def _map_evaluation_to_candidates(
        self,
        candidates: List[Dict[str, Any]],
        evaluation_results: Dict[str, Any],
        available_agents: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Map LLM evaluation results back to original candidates."""
        try:
            recommended_path = evaluation_results.get("recommended_path", [])
            path_evaluations = evaluation_results.get("path_evaluations", [])

            # Create a comprehensive mapping of path evaluations
            path_details = {}
            for eval_data in path_evaluations:
                path_key = " → ".join(eval_data.get("path", []))
                path_details[path_key] = {
                    "score": eval_data.get("score", 0.5),
                    "pros": eval_data.get("pros", []),
                    "cons": eval_data.get("cons", []),
                    "reasoning": (
                        " ".join(eval_data.get("pros", []))
                        if eval_data.get("pros")
                        else "Standard evaluation"
                    ),
                    "expected_outcome": self._generate_path_specific_outcome(
                        eval_data.get("path", []), available_agents
                    ),
                }

            # Update candidates with path-specific evaluation results
            for candidate in candidates:
                path = candidate.get("path", [candidate.get("node_id", "")])
                path_key = " → ".join(path)

                # Get path-specific details or generate them
                path_detail = path_details.get(path_key)
                if not path_detail:
                    # Generate specific evaluation for this path if not found in LLM response
                    path_detail = self._generate_fallback_path_evaluation(path, available_agents)

                # Check if this is the recommended path
                is_recommended = path == recommended_path

                # Update candidate with path-specific LLM evaluation
                candidate.update(
                    {
                        "llm_evaluation": {
                            "score": path_detail["score"],
                            "is_recommended": is_recommended,
                            "reasoning": path_detail["reasoning"],
                            "confidence": evaluation_results.get("confidence", 0.7),
                            "expected_outcome": path_detail["expected_outcome"],
                            "pros": path_detail.get("pros", []),
                            "cons": path_detail.get("cons", []),
                        },
                        "preview": f"LLM evaluation: {path_detail['expected_outcome']}",
                        "estimated_cost": sum(
                            available_agents.get(agent_id, {}).get("cost_estimate", 0)
                            for agent_id in path
                        ),
                        "estimated_latency": sum(
                            available_agents.get(agent_id, {}).get("latency_estimate", 0)
                            for agent_id in path
                        ),
                        "estimated_tokens": 150,  # Default estimate
                    }
                )

            return candidates

        except Exception as e:
            logger.error(f"Failed to map evaluation to candidates: {e}")
            return candidates

    def _generate_path_specific_outcome(
        self, path: List[str], available_agents: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate a specific expected outcome based on the path composition."""
        if not path:
            return "Unknown outcome"

        try:
            # Single agent outcomes based on real Orka agent types
            if len(path) == 1:
                agent_id = path[0]
                agent_info = available_agents.get(agent_id, {})
                agent_class_name = agent_info.get("type", "")

                if agent_class_name == "DuckDuckGoTool":
                    return "Current news and information from web sources"
                elif agent_class_name in ["OpenAIClassificationAgent", "ClassificationAgent"]:
                    return "Question categorized for optimal routing"
                elif agent_class_name == "MemoryReaderNode":
                    return "Relevant stored information retrieved from knowledge base"
                elif agent_class_name == "MemoryWriterNode":
                    return "Information stored in knowledge base for future reference"
                elif agent_class_name == "LocalLLMAgent" and "analysis" in agent_id.lower():
                    return "Detailed analysis and insights from local LLM"
                elif agent_class_name in ["LocalLLMAgent", "OpenAIAnswerBuilder"] and (
                    "response" in agent_id.lower() or "builder" in agent_id.lower()
                ):
                    return "Comprehensive LLM-generated response"
                elif agent_class_name == "GraphScoutAgent":
                    return "Intelligent routing decision with optimal path selection"
                elif agent_class_name in ["BinaryAgent", "OpenAIBinaryAgent"]:
                    return "Binary decision (yes/no) based on input criteria"
                else:
                    return f"Output from {agent_class_name}"

            # Multi-agent path outcomes based on real Orka agent types
            else:
                outcomes = []
                for agent_id in path:
                    agent_info = available_agents.get(agent_id, {})
                    agent_class_name = agent_info.get("type", "")

                    if agent_class_name == "DuckDuckGoTool":
                        outcomes.append("web search results")
                    elif agent_class_name == "LocalLLMAgent" and "analysis" in agent_id.lower():
                        outcomes.append("analytical insights")
                    elif agent_class_name == "MemoryReaderNode":
                        outcomes.append("retrieved information")
                    elif agent_class_name == "MemoryWriterNode":
                        outcomes.append("stored information")
                    elif agent_class_name in ["OpenAIClassificationAgent", "ClassificationAgent"]:
                        outcomes.append("classification result")
                    elif agent_class_name in ["LocalLLMAgent", "OpenAIAnswerBuilder"] and (
                        "response" in agent_id.lower() or "builder" in agent_id.lower()
                    ):
                        outcomes.append("final comprehensive response")
                    else:
                        outcomes.append(f"{agent_class_name} processing")

                return f"Multi-step workflow: {' → '.join(outcomes)}"

        except Exception as e:
            logger.error(f"Failed to generate path-specific outcome: {e}")
            return "Processing outcome"

    def _generate_fallback_path_evaluation(
        self, path: List[str], available_agents: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate intelligent fallback evaluation when LLM evaluation is missing."""
        try:
            if not path:
                return {
                    "score": 0.3,
                    "reasoning": "Empty path",
                    "expected_outcome": "No processing",
                    "pros": [],
                    "cons": ["No agents to execute"],
                }

            # Analyze path composition
            agent_types = []
            has_search = False
            has_analysis = False
            has_memory = False
            has_response_builder = False
            has_classifier = False

            for agent_id in path:
                agent_info = available_agents.get(agent_id, {})
                # Use the actual Orka agent class name, not YAML type
                agent_class_name = agent_info.get("type", "").lower()
                agent_types.append(agent_class_name)

                # Real Orka agent type detection based on actual class names
                if "duckduckgotool" in agent_class_name or "search" in agent_class_name:
                    has_search = True
                elif "localllmagent" in agent_class_name and "analysis" in agent_id.lower():
                    has_analysis = True
                elif (
                    "memoryreadernode" in agent_class_name or "memorywriternode" in agent_class_name
                ):
                    has_memory = True
                elif (
                    "classificationagent" in agent_class_name
                    or "openaiclassificationagent" in agent_class_name
                ):
                    has_classifier = True
                elif (
                    "localllmagent" in agent_class_name or "openaianswerbuilder" in agent_class_name
                ) and (
                    "response" in agent_id.lower()
                    or "answer" in agent_id.lower()
                    or "builder" in agent_id.lower()
                ):
                    has_response_builder = True

            # Calculate intelligent score with uniqueness factor
            base_score = 0.4 + (hash(str(path)) % 100) / 1000  # Add small unique component
            pros = []
            cons = []

            # Strongly boost search agents for factual/news queries
            if has_search:
                base_score += 0.25
                pros.append("Retrieves current information from web")
                pros.append("Ideal for factual and news queries")

            # Boost multi-hop paths that end with response builder significantly
            if len(path) > 1 and has_response_builder:
                base_score += 0.2
                pros.append("Complete end-to-end workflow")
                pros.append("Ensures comprehensive final response")

            # Boost search → response_builder paths specifically
            if has_search and has_response_builder and len(path) == 2:
                base_score += 0.1
                pros.append("Optimal two-step information retrieval and response")

            # Boost analysis for complex reasoning
            if has_analysis:
                base_score += 0.12
                pros.append("Provides detailed analytical insights")

            # Memory agents get moderate boost
            if has_memory:
                base_score += 0.08
                pros.append("Accesses stored knowledge")

            # Classifiers get lower scores as they're typically intermediate
            if has_classifier:
                base_score += 0.05
                pros.append("Categorizes input for routing")
                cons.append("Intermediate step, needs follow-up")

            # Penalize single agents that aren't response builders
            if len(path) == 1 and not has_response_builder:
                base_score -= 0.15
                cons.append("Requires additional response generation step")

            # Penalize memory-only paths for news queries
            if has_memory and not has_search and not has_analysis:
                base_score -= 0.1
                cons.append("May lack current information")

            # Penalize overly complex paths
            if len(path) > 3:
                base_score -= 0.12
                cons.append("Complex multi-step workflow increases latency")

            # Cap score between 0.2 and 0.95 to ensure differentiation
            final_score = max(0.2, min(0.95, base_score))

            # Generate specific reasoning based on path
            if len(path) == 1:
                agent_id = path[0]
                if has_search:
                    reasoning = (
                        f"Direct web search using {agent_id} - excellent for current information"
                    )
                elif has_response_builder:
                    reasoning = (
                        f"Direct response generation using {agent_id} - good for general queries"
                    )
                elif has_memory:
                    reasoning = f"Memory retrieval using {agent_id} - useful for stored information"
                elif has_classifier:
                    reasoning = f"Input classification using {agent_id} - intermediate routing step"
                else:
                    reasoning = f"Single-step execution using {agent_id}"
            else:
                if has_search and has_response_builder:
                    reasoning = f"Optimal news workflow: {' → '.join(path)} - retrieves current info then generates response"
                elif has_analysis and has_response_builder:
                    reasoning = f"Analytical workflow: {' → '.join(path)} - analyzes then responds"
                elif has_memory and has_response_builder:
                    reasoning = f"Memory-based workflow: {' → '.join(path)} - retrieves stored info then responds"
                else:
                    reasoning = f"Multi-step workflow: {' → '.join(path)}"

            if pros:
                reasoning += f". Key advantages: {', '.join(pros[:2])}"  # Limit to top 2 pros

            return {
                "score": round(final_score, 3),  # Round for cleaner display
                "reasoning": reasoning,
                "expected_outcome": self._generate_path_specific_outcome(path, available_agents),
                "pros": pros,
                "cons": cons,
            }

        except Exception as e:
            logger.error(f"Failed to generate fallback evaluation: {e}")
            return {
                "score": 0.5,
                "reasoning": "Standard evaluation",
                "expected_outcome": "Processing outcome",
                "pros": [],
                "cons": [],
            }

    def _parse_evaluation_response(self, response: str, node_id: str) -> PathEvaluation:
        """Parse LLM evaluation response into structured format."""
        try:
            data = json.loads(response)

            # Validate required fields exist and are not None
            required_fields = ["relevance_score", "confidence", "reasoning"]
            for field in required_fields:
                if field not in data or data[field] is None:
                    raise ValueError(f"Missing or null required field: {field}")

            return PathEvaluation(
                node_id=node_id,
                relevance_score=float(data.get("relevance_score", 0.5)),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=str(data.get("reasoning", "No reasoning provided")),
                expected_output=str(data.get("expected_output", "Unknown output")),
                estimated_tokens=int(data.get("estimated_tokens") or 100),
                estimated_cost=float(data.get("estimated_cost") or 0.001),
                estimated_latency_ms=int(data.get("estimated_latency_ms") or 1000),
                risk_factors=data.get("risk_factors") or [],
                efficiency_rating=str(data.get("efficiency_rating", "medium")),
            )

        except Exception as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            return self._create_fallback_evaluation(node_id)

    def _parse_validation_response(self, response: str) -> ValidationResult:
        """Parse LLM validation response into structured format."""
        try:
            data = json.loads(response)

            return ValidationResult(
                is_valid=bool(data.get("is_valid", True)),
                confidence=float(data.get("confidence", 0.5)),
                efficiency_score=float(data.get("efficiency_score", 0.5)),
                validation_reasoning=str(
                    data.get("validation_reasoning", "No validation reasoning")
                ),
                suggested_improvements=data.get("suggested_improvements", []),
                risk_assessment=str(data.get("risk_assessment", "medium")),
            )

        except Exception as e:
            logger.error(f"Failed to parse validation response: {e}")
            return self._create_fallback_validation()

    def _combine_evaluation_results(
        self, candidate: Dict[str, Any], evaluation: PathEvaluation, validation: ValidationResult
    ) -> Dict[str, Any]:
        """Combine LLM evaluation results with candidate."""

        # Calculate final scores based on both stages
        final_relevance = evaluation.relevance_score
        if not validation.is_valid:
            final_relevance *= 0.5  # Penalize invalid selections

        final_confidence = (evaluation.confidence + validation.confidence) / 2
        final_efficiency = validation.efficiency_score

        # Add LLM evaluation results to candidate
        candidate.update(
            {
                "llm_evaluation": {
                    "stage1": {
                        "relevance_score": evaluation.relevance_score,
                        "confidence": evaluation.confidence,
                        "reasoning": evaluation.reasoning,
                        "expected_output": evaluation.expected_output,
                        "efficiency_rating": evaluation.efficiency_rating,
                        "risk_factors": evaluation.risk_factors,
                    },
                    "stage2": {
                        "is_valid": validation.is_valid,
                        "confidence": validation.confidence,
                        "efficiency_score": validation.efficiency_score,
                        "validation_reasoning": validation.validation_reasoning,
                        "suggested_improvements": validation.suggested_improvements,
                        "risk_assessment": validation.risk_assessment,
                    },
                    "final_scores": {
                        "relevance": final_relevance,
                        "confidence": final_confidence,
                        "efficiency": final_efficiency,
                    },
                },
                "estimated_cost": evaluation.estimated_cost,
                "estimated_latency": evaluation.estimated_latency_ms,
                "estimated_tokens": evaluation.estimated_tokens,
                "preview": evaluation.expected_output,  # Use LLM-generated expected output as preview
            }
        )

        return candidate

    def _create_fallback_evaluation(self, node_id: str) -> PathEvaluation:
        """Create fallback evaluation when LLM fails."""
        return PathEvaluation(
            node_id=node_id,
            relevance_score=0.5,
            confidence=0.3,
            reasoning="LLM evaluation failed, using fallback",
            expected_output="Unable to predict output",
            estimated_tokens=100,
            estimated_cost=0.001,
            estimated_latency_ms=1000,
            risk_factors=["evaluation_failure"],
            efficiency_rating="medium",
        )

    def _create_fallback_validation(self) -> ValidationResult:
        """Create fallback validation when LLM fails."""
        return ValidationResult(
            is_valid=True,
            confidence=0.3,
            efficiency_score=0.5,
            validation_reasoning="LLM validation failed, using fallback",
            suggested_improvements=["retry_evaluation"],
            risk_assessment="medium",
        )

    async def _fallback_heuristic_evaluation(
        self, candidates: List[Dict[str, Any]], question: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fallback to simple heuristic evaluation when LLM fails."""
        try:
            for candidate in candidates:
                node_id = candidate["node_id"]

                # Simple heuristic scoring
                relevance_score = 0.5
                if "search" in question.lower() and "search" in node_id.lower():
                    relevance_score = 0.7
                elif "memory" in question.lower() and "memory" in node_id.lower():
                    relevance_score = 0.7
                elif "analyze" in question.lower() and "llm" in node_id.lower():
                    relevance_score = 0.7

                candidate.update(
                    {
                        "preview": f"Heuristic evaluation for {node_id}",
                        "estimated_cost": 0.001,
                        "estimated_latency": 1000,
                        "estimated_tokens": 100,
                        "llm_evaluation": {
                            "final_scores": {
                                "relevance": relevance_score,
                                "confidence": 0.5,
                                "efficiency": 0.5,
                            }
                        },
                    }
                )

            return candidates

        except Exception as e:
            logger.error(f"Fallback heuristic evaluation failed: {e}")
            return candidates

    async def _call_ollama_async(
        self, model_url: str, model: str, prompt: str, temperature: float
    ) -> str:
        """Call Ollama API endpoint asynchronously."""
        try:
            import aiohttp

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(model_url, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return str(result.get("response", "")).strip()

        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            raise

    async def _call_lm_studio_async(
        self, model_url: str, model: str, prompt: str, temperature: float
    ) -> str:
        """Call LM Studio API endpoint asynchronously."""
        try:
            import aiohttp

            # LM Studio uses OpenAI-compatible format
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": 500,
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{model_url}/v1/chat/completions", json=payload
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return str(result["choices"][0]["message"]["content"]).strip()

        except Exception as e:
            logger.error(f"LM Studio API call failed: {e}")
            raise

    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """Extract JSON from LLM response, handling various formats."""
        import re

        # Clean the response
        response = response.strip()

        # Try to parse the response directly as JSON
        try:
            json.loads(response)
            return response
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from code blocks (```json ... ```)
        json_match = re.search(r"```json\s*\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
        if json_match:
            json_content = json_match.group(1).strip()
            try:
                json.loads(json_content)
                return json_content
            except json.JSONDecodeError:
                pass

        # Try to extract JSON from code blocks (``` ... ```)
        json_match = re.search(r"```\s*\n(.*?)\n```", response, re.DOTALL)
        if json_match:
            json_content = json_match.group(1).strip()
            try:
                json.loads(json_content)
                return json_content
            except json.JSONDecodeError:
                pass

        # Look for { ... } blocks (greedy match for complete JSON)
        json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response, re.DOTALL)
        if json_match:
            json_content = json_match.group(0).strip()
            try:
                json.loads(json_content)
                return json_content
            except json.JSONDecodeError:
                pass

        # Try to fix common JSON issues
        # Remove trailing commas
        cleaned_response = re.sub(r",\s*}", "}", response)
        cleaned_response = re.sub(r",\s*]", "]", cleaned_response)

        # Try parsing the cleaned response
        try:
            json.loads(cleaned_response)
            return cleaned_response
        except json.JSONDecodeError:
            pass

        # No valid JSON found
        logger.warning(f"Could not extract valid JSON from response: {response[:200]}...")
        return None


# Keep backward compatibility by aliasing the new class
DryRunEngine = SmartPathEvaluator
