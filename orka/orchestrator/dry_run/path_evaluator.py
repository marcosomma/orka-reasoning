# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Path Evaluator
==============

Methods for evaluating and generating path outcomes.
"""

import logging
from typing import Any, Dict, List

from .data_classes import PathEvaluation, ValidationResult

logger = logging.getLogger(__name__)


class PathEvaluatorMixin:
    """Mixin providing path evaluation methods."""

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

                outcomes = {
                    "DuckDuckGoTool": "Current news and information from web sources",
                    "OpenAIClassificationAgent": "Question categorized for optimal routing",
                    "ClassificationAgent": "Question categorized for optimal routing",
                    "MemoryReaderNode": "Relevant stored information retrieved from knowledge base",
                    "MemoryWriterNode": "Information stored in knowledge base for future reference",
                    "GraphScoutAgent": "Intelligent routing decision with optimal path selection",
                    "BinaryAgent": "Binary decision (yes/no) based on input criteria",
                    "OpenAIBinaryAgent": "Binary decision (yes/no) based on input criteria",
                }

                if agent_class_name in outcomes:
                    return outcomes[agent_class_name]
                elif agent_class_name == "LocalLLMAgent" and "analysis" in agent_id.lower():
                    return "Detailed analysis and insights from local LLM"
                elif agent_class_name in ["LocalLLMAgent", "OpenAIAnswerBuilder"] and (
                    "response" in agent_id.lower() or "builder" in agent_id.lower()
                ):
                    return "Comprehensive LLM-generated response"
                else:
                    return f"Output from {agent_class_name}"

            # Multi-agent path outcomes
            else:
                outcomes = []
                for agent_id in path:
                    agent_info = available_agents.get(agent_id, {})
                    agent_class_name = agent_info.get("type", "")

                    outcome_map = {
                        "DuckDuckGoTool": "web search results",
                        "MemoryReaderNode": "retrieved information",
                        "MemoryWriterNode": "stored information",
                        "OpenAIClassificationAgent": "classification result",
                        "ClassificationAgent": "classification result",
                    }

                    if agent_class_name in outcome_map:
                        outcomes.append(outcome_map[agent_class_name])
                    elif agent_class_name == "LocalLLMAgent" and "analysis" in agent_id.lower():
                        outcomes.append("analytical insights")
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
            has_search = False
            has_analysis = False
            has_memory = False
            has_response_builder = False
            has_classifier = False

            for agent_id in path:
                agent_info = available_agents.get(agent_id, {})
                agent_class_name = agent_info.get("type", "").lower()

                if "duckduckgotool" in agent_class_name or "search" in agent_class_name:
                    has_search = True
                elif "localllmagent" in agent_class_name and "analysis" in agent_id.lower():
                    has_analysis = True
                elif (
                    "memoryreadernode" in agent_class_name
                    or "memorywriternode" in agent_class_name
                ):
                    has_memory = True
                elif (
                    "classificationagent" in agent_class_name
                    or "openaiclassificationagent" in agent_class_name
                ):
                    has_classifier = True
                elif (
                    "localllmagent" in agent_class_name
                    or "openaianswerbuilder" in agent_class_name
                ) and (
                    "response" in agent_id.lower()
                    or "answer" in agent_id.lower()
                    or "builder" in agent_id.lower()
                ):
                    has_response_builder = True

            # Calculate intelligent score with uniqueness factor
            base_score = 0.4 + (hash(str(path)) % 100) / 1000
            pros = []
            cons = []

            if has_search:
                base_score += 0.25
                pros.extend(["Retrieves current information from web", "Ideal for factual and news queries"])

            if len(path) > 1 and has_response_builder:
                base_score += 0.2
                pros.extend(["Complete end-to-end workflow", "Ensures comprehensive final response"])

            if has_search and has_response_builder and len(path) == 2:
                base_score += 0.1
                pros.append("Optimal two-step information retrieval and response")

            if has_analysis:
                base_score += 0.12
                pros.append("Provides detailed analytical insights")

            if has_memory:
                base_score += 0.08
                pros.append("Accesses stored knowledge")

            if has_classifier:
                base_score += 0.05
                pros.append("Categorizes input for routing")
                cons.append("Intermediate step, needs follow-up")

            if len(path) == 1 and not has_response_builder:
                base_score -= 0.15
                cons.append("Requires additional response generation step")

            if has_memory and not has_search and not has_analysis:
                base_score -= 0.1
                cons.append("May lack current information")

            if len(path) > 3:
                base_score -= 0.12
                cons.append("Complex multi-step workflow increases latency")

            final_score = max(0.2, min(0.95, base_score))

            # Generate specific reasoning
            if len(path) == 1:
                agent_id = path[0]
                if has_search:
                    reasoning = f"Direct web search using {agent_id} - excellent for current information"
                elif has_response_builder:
                    reasoning = f"Direct response generation using {agent_id} - good for general queries"
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
                reasoning += f". Key advantages: {', '.join(pros[:2])}"

            return {
                "score": round(final_score, 3),
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
                "preview": evaluation.expected_output,
            }
        )

        return candidate

