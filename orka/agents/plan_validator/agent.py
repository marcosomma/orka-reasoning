# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Plan Validator Agent
====================

Meta-cognitive agent that validates and critiques proposed agent execution paths.
Works in feedback loops with GraphScout to iteratively improve path selection.
"""

import json
import logging
from typing import Any, Dict, List, cast

from ..base_agent import BaseAgent, Context
from . import critique_parser, llm_client

logger = logging.getLogger(__name__)


class PlanValidatorAgent(BaseAgent):
    """
    Agent that validates and critiques proposed agent execution paths.

    Evaluates paths across multiple dimensions (completeness, efficiency,
    safety, coherence, fallback) and provides structured feedback for
    iterative improvement.

    Args:
        agent_id: Unique identifier for the agent
        llm_model: LLM model name (default: "gpt-oss:20b")
        llm_provider: Provider type ("ollama" or "openai_compatible")
        llm_url: LLM API endpoint URL
        temperature: Temperature for LLM generation
        **kwargs: Additional arguments for BaseAgent
    """

    def __init__(
        self,
        agent_id: str,
        llm_model: str = "gpt-oss:20b",
        llm_provider: str = "ollama",
        llm_url: str = "http://localhost:11434/api/generate",
        temperature: float = 0.2,
        **kwargs: Any,
    ):
        super().__init__(agent_id, **kwargs)

        self.llm_model = llm_model
        self.llm_provider = llm_provider
        self.llm_url = llm_url
        self.temperature = temperature

        logger.info(f"Initialized PlanValidatorAgent '{agent_id}' with model '{llm_model}'")

    async def _run_impl(self, ctx: Context) -> Dict[str, Any]:
        """
        Validate a proposed agent path.

        Args:
            ctx: Context containing:
                - input: Original user query
                - previous_outputs: Including GraphScout proposed path
                - loop_number: Current iteration number
                - past_loops: Previous validation rounds (optional)

        Returns:
            Structured critique dict with validation_score
        """
        # Extract information from context
        original_query = self._extract_query(ctx)
        proposed_path = self._extract_proposed_path(ctx)
        previous_critiques = self._extract_previous_critiques(ctx)
        loop_num_val = ctx.get("loop_number", 1)
        if isinstance(loop_num_val, int):
            loop_number = loop_num_val
        else:
            loop_number = 1

        logger.info(f"PlanValidator (Round {loop_number}): Evaluating proposed path")
        logger.debug(f"Query: {original_query[:100]}...")

        # Build validation prompt
        validation_prompt = self._build_validation_prompt(
            original_query,
            proposed_path,
            previous_critiques,
            loop_number,
        )

        # Call LLM for critique
        try:
            critique_response = await llm_client.call_llm(
                prompt=validation_prompt,
                model=self.llm_model,
                url=self.llm_url,
                provider=self.llm_provider,
                temperature=self.temperature,
            )
        except RuntimeError as e:
            logger.error(f"LLM call failed: {e}")
            return self._create_error_critique(str(e))

        # Parse and structure the critique
        validation_result = critique_parser.parse_critique(critique_response)

        logger.info(
            f"Validation Score: {validation_result['validation_score']:.2f} "
            f"- {validation_result['overall_assessment']}"
        )

        return validation_result

    def _extract_query(self, ctx: Context) -> str:
        """
        Extract original query from context.

        Args:
            ctx: Context dict

        Returns:
            Query string
        """
        input_val: Any = ctx.get("input")
        # Handle nested input dict
        if isinstance(input_val, dict) and "input" in input_val:
            return str(input_val["input"])
        # Handle direct input or None
        return str(input_val) if input_val is not None else ""

    def _extract_proposed_path(self, ctx: Context) -> Dict[str, Any]:
        """
        Extract proposed path from GraphScout output in previous_outputs.

        Args:
            ctx: Context dict

        Returns:
            Proposed path dict or error dict if not found
        """
        previous_outputs = ctx.get("previous_outputs", {})

        # Look for GraphScout output by common agent IDs
        graphscout_keys = [
            "graph_scout",
            "graphscout_planner",
            "path_proposer",
            "dynamic_router",
        ]

        for key in graphscout_keys:
            if key in previous_outputs:
                logger.debug(f"Found proposed path in '{key}'")
                return cast(Dict[str, Any], previous_outputs[key])

        # Fallback: look for any agent with path/decision info
        for agent_id, output in previous_outputs.items():
            if isinstance(output, dict):
                if any(k in output for k in ["decision_type", "target", "path"]):
                    logger.debug(f"Found proposed path in '{agent_id}' (fallback)")
                    return cast(Dict[str, Any], output)

        logger.warning("No proposed path found in previous_outputs")
        return {"error": "No proposed path found", "available_keys": list(previous_outputs.keys())}

    def _extract_previous_critiques(self, ctx: Context) -> List[Dict[str, Any]]:
        """
        Extract previous validation critiques from past loop iterations.

        Args:
            ctx: Context dict

        Returns:
            List of previous critique dicts
        """
        past_loops = ctx.get("previous_outputs", {}).get("past_loops", [])
        critiques = []

        for loop in past_loops:
            loop_str = str(loop)
            if "validation_score" in loop_str or "critiques" in loop_str:
                critiques.append(loop)

        return critiques

    def _build_validation_prompt(
        self,
        query: str,
        proposed_path: Dict[str, Any],
        previous_critiques: List[Dict[str, Any]],
        loop_number: int,
    ) -> str:
        """
        Build validation prompt for LLM.

        Args:
            query: Original user query
            proposed_path: Path proposed by GraphScout
            previous_critiques: Past validation feedback
            loop_number: Current iteration number

        Returns:
            Formatted prompt string
        """
        # Format previous critiques section
        critique_history = ""
        if previous_critiques:
            critique_history = "\n\n**PREVIOUS CRITIQUES:**\n"
            for i, critique in enumerate(previous_critiques, 1):
                critique_history += f"Round {i}: {json.dumps(critique, indent=2)}\n"

        prompt = f"""You are a Plan Validator agent. Your job is to critique and validate proposed agent execution paths.

**VALIDATION ROUND:** {loop_number}

**ORIGINAL QUERY:**
{query}

**PROPOSED PATH (from GraphScout):**
{json.dumps(proposed_path, indent=2)}
{critique_history}

**YOUR TASK:**
Evaluate the proposed path across these dimensions:
1. **Completeness**: Does it address all aspects of the query?
2. **Efficiency**: Is it optimal (cost, latency, agent selection)?
3. **Safety**: Any risky combinations or missing safeguards?
4. **Coherence**: Do the agents work well together in this sequence?
5. **Fallback**: Are error cases and edge cases handled?

**OUTPUT FORMAT (JSON only):**
{{
    "validation_score": <0.0-1.0 overall score>,
    "overall_assessment": "<APPROVED|NEEDS_IMPROVEMENT|REJECTED>",
    "critiques": {{
        "completeness": {{"score": <0-1>, "issues": ["..."], "suggestions": ["..."]}},
        "efficiency": {{"score": <0-1>, "issues": [], "suggestions": []}},
        "safety": {{"score": <0-1>, "issues": ["..."], "suggestions": ["..."]}},
        "coherence": {{"score": <0-1>, "issues": [], "suggestions": []}},
        "fallback": {{"score": <0-1>, "issues": ["..."], "suggestions": ["..."]}}
    }},
    "recommended_changes": ["specific change 1", "specific change 2"],
    "approval_confidence": <0.0-1.0>,
    "rationale": "Brief explanation of the overall assessment and key concerns"
}}

**SCORING GUIDELINES:**
- 0.9-1.0: Excellent, approve immediately
- 0.8-0.89: Good with minor suggestions
- 0.7-0.79: Needs improvement, loop again
- 0.0-0.69: Major issues, reject or significantly revise

VALIDATION_SCORE: <your score>
"""
        return prompt

    def _create_error_critique(self, error_message: str) -> Dict[str, Any]:
        """
        Create error critique when validation fails.

        Args:
            error_message: Error description

        Returns:
            Error critique dict
        """
        return {
            "validation_score": 0.0,
            "overall_assessment": "REJECTED",
            "critiques": {
                "completeness": {"score": 0.0, "issues": [error_message], "suggestions": []},
                "efficiency": {"score": 0.0, "issues": [], "suggestions": []},
                "safety": {"score": 0.0, "issues": [], "suggestions": []},
                "coherence": {"score": 0.0, "issues": [], "suggestions": []},
                "fallback": {"score": 0.0, "issues": [], "suggestions": []},
            },
            "recommended_changes": [],
            "approval_confidence": 0.0,
            "rationale": f"Validation failed: {error_message}",
        }
