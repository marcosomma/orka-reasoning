# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Prompt Builder
==============

Methods for building LLM prompts for path evaluation and validation.
"""

from typing import Any, Dict, List

from .data_classes import PathEvaluation


class PromptBuilderMixin:
    """Mixin providing prompt building methods for path evaluation."""

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
- Avoid routing to the agent that is currently making the routing decision where possible; document exceptions and tests where this is needed
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
Prompt: {(agent_info.get('prompt') or '')[:200]}...
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
- Avoid routing to the current agent ({current_agent}) when possible; document exceptions and test coverage
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

