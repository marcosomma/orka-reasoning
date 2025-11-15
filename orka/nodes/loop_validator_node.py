"""
LoopValidatorNode - Specialized node for robust boolean evaluation in LoopNodes.

This node wraps LLM evaluation with built-in format handling, eliminating the need
for fragile prompt engineering in workflows. It provides:
- Built-in, tested prompt templates
- Robust parsing with multiple fallback strategies
- Consistent output format for LoopNode consumption
- Model-agnostic operation
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from orka.agents.local_llm_agents import LocalLLMAgent
from orka.nodes.base_node import BaseNode


@dataclass
class BooleanCriteria:
    """Standard boolean criteria categories for path evaluation."""

    completeness: Dict[str, bool]
    efficiency: Dict[str, bool]
    safety: Dict[str, bool]
    coherence: Dict[str, bool]


class LoopValidatorNode(BaseNode):
    """
    Specialized node for LoopNode boolean evaluation.

    Wraps LLM evaluation with robust format handling to ensure reliable
    score extraction regardless of LLM output variations.

    Example usage:
        ```yaml
        - id: validator
          type: loop_validator
          llm_model: gpt-oss:20b
          provider: ollama
          scoring_preset: moderate
          evaluation_target: improver
        ```
    """

    # Built-in prompt templates (tested and reliable)
    PROMPT_TEMPLATES = {
        "strict": """Evaluate this proposed execution path against STRICT criteria.

Path to evaluate:
{content}

For each criterion below, answer ONLY "true" or "false":

COMPLETENESS:
- has_all_required_steps: Does the path include every necessary step?
- addresses_all_query_aspects: Are all aspects of the query covered?
- handles_edge_cases: Are edge cases and error scenarios handled?
- includes_fallback_path: Are fallback mechanisms defined?

EFFICIENCY:
- minimizes_redundant_calls: Are redundant operations avoided?
- uses_appropriate_agents: Are the right agents used for each task?
- optimizes_cost: Is the approach cost-efficient?
- optimizes_latency: Is the approach time-efficient?

SAFETY:
- validates_inputs: Are inputs validated before processing?
- handles_errors_gracefully: Are errors caught and handled properly?
- has_timeout_protection: Are timeouts configured to prevent hangs?
- avoids_risky_combinations: Are risky agent combinations avoided?

COHERENCE:
- logical_agent_sequence: Do agents execute in a logical order?
- proper_data_flow: Is data passed correctly between agents?
- no_conflicting_actions: Are there no contradictory operations?

Respond in JSON format:
{
  "COMPLETENESS": {
    "has_all_required_steps": true,
    "addresses_all_query_aspects": false,
    ...
  },
  "EFFICIENCY": {...},
  "SAFETY": {...},
  "COHERENCE": {...}
}""",
        "moderate": """Evaluate this proposed execution path with BALANCED criteria.

Path to evaluate:
{content}

For each criterion, answer "true" or "false":

COMPLETENESS:
- has_all_required_steps: [true/false]
- addresses_all_query_aspects: [true/false]
- handles_edge_cases: [true/false]
- includes_fallback_path: [true/false]

EFFICIENCY:
- minimizes_redundant_calls: [true/false]
- uses_appropriate_agents: [true/false]
- optimizes_cost: [true/false]
- optimizes_latency: [true/false]

SAFETY:
- validates_inputs: [true/false]
- handles_errors_gracefully: [true/false]
- has_timeout_protection: [true/false]
- avoids_risky_combinations: [true/false]

COHERENCE:
- logical_agent_sequence: [true/false]
- proper_data_flow: [true/false]
- no_conflicting_actions: [true/false]

Return JSON with your evaluation.""",
        "lenient": """Evaluate this proposed execution path with LENIENT criteria.

Path to evaluate:
{content}

Answer true/false for each criterion (be generous in interpretation):

COMPLETENESS: has_all_required_steps, addresses_all_query_aspects, handles_edge_cases, includes_fallback_path
EFFICIENCY: minimizes_redundant_calls, uses_appropriate_agents, optimizes_cost, optimizes_latency
SAFETY: validates_inputs, handles_errors_gracefully, has_timeout_protection, avoids_risky_combinations
COHERENCE: logical_agent_sequence, proper_data_flow, no_conflicting_actions

Return as JSON.""",
    }

    # Standard criteria structure
    CRITERIA_STRUCTURE = {
        "completeness": [
            "has_all_required_steps",
            "addresses_all_query_aspects",
            "handles_edge_cases",
            "includes_fallback_path",
        ],
        "efficiency": [
            "minimizes_redundant_calls",
            "uses_appropriate_agents",
            "optimizes_cost",
            "optimizes_latency",
        ],
        "safety": [
            "validates_inputs",
            "handles_errors_gracefully",
            "has_timeout_protection",
            "avoids_risky_combinations",
        ],
        "coherence": ["logical_agent_sequence", "proper_data_flow", "no_conflicting_actions"],
    }

    def __init__(
        self,
        node_id: str,
        llm_model: str,
        provider: str,
        model_url: Optional[str] = None,
        scoring_preset: str = "moderate",
        evaluation_target: Optional[str] = None,
        temperature: float = 0.1,
        custom_prompt: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize LoopValidatorNode.

        Args:
            node_id: Unique identifier for this node
            llm_model: LLM model to use for evaluation
            provider: LLM provider (ollama, openai, etc.)
            model_url: Optional custom model URL
            scoring_preset: Evaluation strictness (strict/moderate/lenient)
            evaluation_target: Agent ID to evaluate (if None, evaluates previous output)
            temperature: LLM temperature (default 0.1 for consistency)
            custom_prompt: Optional custom prompt template (overrides preset)
        """
        # BaseNode requires prompt and queue, but LoopValidatorNode doesn't use them
        # Pass None for both since validation logic is handled internally
        super().__init__(node_id, prompt=None, queue=None, **kwargs)

        self.llm_model = llm_model
        self.provider = provider
        self.model_url = model_url
        self.scoring_preset = scoring_preset
        self.evaluation_target = evaluation_target
        self.temperature = temperature
        self.custom_prompt = custom_prompt

        # Initialize LLM agent
        self.llm_agent = LocalLLMAgent(
            agent_id=f"{node_id}_llm",
            model=llm_model,
            model_url=model_url,
            provider=provider,
            temperature=temperature,
        )

        # Select prompt template
        if custom_prompt:
            self.prompt_template = custom_prompt
        elif scoring_preset in self.PROMPT_TEMPLATES:
            self.prompt_template = self.PROMPT_TEMPLATES[scoring_preset]
        else:
            raise ValueError(
                f"Invalid scoring_preset: {scoring_preset}. "
                f"Must be one of: {list(self.PROMPT_TEMPLATES.keys())}"
            )

    async def _run_impl(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute validation with robust parsing (async implementation for BaseNode).

        Args:
            payload: Input payload containing the content to evaluate

        Returns:
            Dict with boolean_evaluations, validation_score, passed/failed criteria
        """
        try:
            # Extract content to evaluate
            content = self._get_evaluation_content(payload)

            # Run LLM evaluation
            prompt = self.prompt_template.format(content=content)
            llm_response = await self.llm_agent.run({"input": prompt})

            # Extract response text
            response_text = self._extract_response_text(llm_response)

            # Parse with fallbacks
            boolean_evals = self._parse_with_fallbacks(response_text)

            # Calculate score and format output
            return self._format_for_loop_node(boolean_evals)

        except Exception as e:
            # Safe fallback on any error
            return self._safe_fallback_response(str(e))

    def _get_evaluation_content(self, input_data: Dict[str, Any]) -> str:
        """Extract content to evaluate from input data."""
        if self.evaluation_target:
            # Evaluate specific agent output
            prev_outputs = input_data.get("previous_outputs", {})
            if self.evaluation_target in prev_outputs:
                target_output = prev_outputs[self.evaluation_target]
                if isinstance(target_output, dict):
                    return json.dumps(target_output, indent=2)
                return str(target_output)

        # Evaluate the entire input
        return json.dumps(input_data, indent=2, default=str)

    def _extract_response_text(self, llm_response: Any) -> str:
        """Extract text from LLM response (handles various formats including OrkaResponse)."""
        # Handle string responses directly
        if isinstance(llm_response, str):
            return llm_response

        # Handle dict-like responses (Dict[str, Any], OrkaResponse, etc.)
        if isinstance(llm_response, dict):
            # Try common response keys in order, ensure we always return a string
            for key in ["response", "result", "text", "content"]:
                if key in llm_response:
                    value = llm_response[key]
                    if isinstance(value, dict) and "response" in value:
                        return str(value["response"])
                    return str(value)

        # Fallback to string representation of entire response
        return str(llm_response)

    def _parse_with_fallbacks(self, response_text: str) -> Dict[str, Dict[str, bool]]:
        """
        Parse boolean evaluations with multiple fallback strategies.

        Attempts in order:
        1. JSON parsing
        2. Regex extraction from various formats
        3. Keyword detection
        4. Safe conservative defaults
        """
        # Strategy 1: Direct JSON parsing
        if parsed := self._try_json_parse(response_text):
            return parsed

        # Strategy 2: Regex extraction (handles plain text formats)
        if parsed := self._try_regex_parse(response_text):
            return parsed

        # Strategy 3: Keyword detection (handles malformed responses)
        if parsed := self._try_keyword_parse(response_text):
            return parsed

        # Strategy 4: Safe conservative defaults (all false)
        return self._conservative_defaults()

    def _try_json_parse(self, text: str) -> Optional[Dict[str, Dict[str, bool]]]:
        """Attempt to parse as JSON."""
        try:
            # Try direct JSON parse
            data = json.loads(text)
            if self._validate_structure(data):
                return self._normalize_structure(data)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from text
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if self._validate_structure(data):
                    return self._normalize_structure(data)
            except json.JSONDecodeError:
                pass

        return None

    def _try_regex_parse(self, text: str) -> Optional[Dict[str, Dict[str, bool]]]:
        """Extract boolean values using regex patterns."""
        result: Dict[str, Dict[str, bool]] = {}

        for category, criteria in self.CRITERIA_STRUCTURE.items():
            result[category] = {}

            for criterion in criteria:
                # Try various patterns
                patterns = [
                    rf'{criterion}["\']?\s*[:=]\s*(true|false)',
                    rf'{criterion}["\']?\s*:\s*"?(true|false)"?',
                    rf'["\']?{criterion}["\']?\s*:\s*(true|false)',
                ]

                value = None
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).lower() == "true"
                        break

                # Default to false if not found
                result[category][criterion] = value if value is not None else False

        # Only return if we found at least some values
        if any(any(v for v in cat.values()) for cat in result.values()):
            return result

        return None

    def _try_keyword_parse(self, text: str) -> Optional[Dict[str, Dict[str, bool]]]:
        """Parse using keyword detection (last resort)."""
        text_lower = text.lower()
        result: Dict[str, Dict[str, bool]] = {}

        for category, criteria in self.CRITERIA_STRUCTURE.items():
            result[category] = {}

            for criterion in criteria:
                criterion_lower = criterion.lower()
                # Look for criterion name followed by positive indicators
                if criterion_lower in text_lower:
                    # Check for true/yes/pass near the criterion
                    criterion_idx = text_lower.find(criterion_lower)
                    context = text_lower[criterion_idx : criterion_idx + 100]

                    if any(word in context for word in ["true", "yes", "pass", "✓", "correct"]):
                        result[category][criterion] = True
                    elif any(word in context for word in ["false", "no", "fail", "✗", "incorrect"]):
                        result[category][criterion] = False
                    else:
                        result[category][criterion] = False
                else:
                    result[category][criterion] = False

        return result

    def _conservative_defaults(self) -> Dict[str, Dict[str, bool]]:
        """Return conservative defaults (all false)."""
        result = {}
        for category, criteria in self.CRITERIA_STRUCTURE.items():
            result[category] = {criterion: False for criterion in criteria}
        return result

    def _validate_structure(self, data: Any) -> bool:
        """Validate that data has the expected structure."""
        if not isinstance(data, dict):
            return False

        # Check for category keys (case-insensitive)
        data_keys_lower = {k.lower() for k in data.keys()}
        expected_categories = set(self.CRITERIA_STRUCTURE.keys())

        # Must have at least one category
        return len(data_keys_lower & expected_categories) > 0

    def _normalize_structure(self, data: Dict[str, Any]) -> Dict[str, Dict[str, bool]]:
        """Normalize structure to standard format."""
        result: Dict[str, Dict[str, bool]] = {}

        for category, criteria in self.CRITERIA_STRUCTURE.items():
            result[category] = {}

            # Find category in data (case-insensitive)
            category_data = None
            for key, value in data.items():
                if key.lower() == category.lower():
                    category_data = value
                    break

            if isinstance(category_data, dict):
                for criterion in criteria:
                    # Find criterion in category data (case-insensitive)
                    value = None
                    for key, val in category_data.items():
                        if key.lower() == criterion.lower():
                            # Convert to bool
                            if isinstance(val, bool):
                                value = val
                            elif isinstance(val, str):
                                value = val.lower() in ["true", "yes", "1", "pass"]
                            break

                    result[category][criterion] = value if value is not None else False
            else:
                # Category not found, default to false
                result[category] = {criterion: False for criterion in criteria}

        return result

    def _format_for_loop_node(self, boolean_evals: Dict[str, Dict[str, bool]]) -> Dict[str, Any]:
        """Format output in exact format LoopNode expects."""
        # Calculate passed/failed criteria
        passed_criteria = []
        failed_criteria = []

        for category, criteria in boolean_evals.items():
            for criterion, passed in criteria.items():
                criterion_key = f"{category}.{criterion}"
                if passed:
                    passed_criteria.append(criterion_key)
                else:
                    failed_criteria.append(criterion_key)

        # Calculate validation score (percentage of passed criteria)
        total_criteria = sum(len(criteria) for criteria in boolean_evals.values())
        validation_score = len(passed_criteria) / total_criteria if total_criteria > 0 else 0.0

        return {
            "boolean_evaluations": boolean_evals,
            "validation_score": validation_score,
            "passed_criteria": passed_criteria,
            "failed_criteria": failed_criteria,
            "overall_assessment": "APPROVED" if validation_score >= 0.7 else "REJECTED",
        }

    def _safe_fallback_response(self, error_msg: str) -> Dict[str, Any]:
        """Return safe fallback response on error."""
        boolean_evals = self._conservative_defaults()
        return {
            "boolean_evaluations": boolean_evals,
            "validation_score": 0.0,
            "passed_criteria": [],
            "failed_criteria": [
                f"{cat}.{crit}" for cat, crits in self.CRITERIA_STRUCTURE.items() for crit in crits
            ],
            "overall_assessment": "ERROR",
            "error": error_msg,
        }
