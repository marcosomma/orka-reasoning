# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

import logging
import os
import re
import tempfile
from datetime import datetime

import yaml

from .base_node import BaseNode

logger = logging.getLogger(__name__)


class LoopNode(BaseNode):
    """
    Simple loop node that repeats an internal workflow until threshold is met.

    This node executes an internal workflow repeatedly until a score threshold is reached
    or the maximum number of loops is exceeded. Each loop's result is tracked in the
    past_loops array, allowing for iterative improvement based on previous attempts.
    """

    def __init__(self, node_id, prompt=None, queue=None, **kwargs):
        """
        Initialize the loop node.

        Args:
            node_id (str): Unique identifier for the node.
            prompt (str, optional): Prompt or instruction for the node.
            queue (list, optional): Queue of agents or nodes to be processed.
            **kwargs: Additional configuration parameters:
                - max_loops (int): Maximum number of loop iterations (default: 5)
                - score_threshold (float): Score threshold to meet before continuing (default: 0.8)
                - score_extraction_pattern (str): Regex pattern to extract score from results
                - score_extraction_key (str): Direct key to look for score in result dict
                - internal_workflow (dict): Complete workflow configuration to execute in loop
                - past_loops_metadata (dict): Template for past_loops object structure
                - cognitive_extraction (dict): Configuration for extracting valuable cognitive data
        """
        super().__init__(node_id, prompt, queue, **kwargs)

        # Configuration
        self.max_loops = kwargs.get("max_loops", 5)
        self.score_threshold = kwargs.get("score_threshold", 0.8)
        self.score_extraction_pattern = kwargs.get(
            "score_extraction_pattern",
            r"SCORE:\s*([0-9.]+)",
        )
        self.score_extraction_key = kwargs.get("score_extraction_key", "score")

        # Internal workflow configuration
        self.internal_workflow = kwargs.get("internal_workflow", {})

        # Past loops metadata structure (user-defined)
        self.past_loops_metadata = kwargs.get(
            "past_loops_metadata",
            {
                "loop_number": "{{ loop_number }}",
                "score": "{{ score }}",
                "timestamp": "{{ timestamp }}",
                "insights": "{{ insights }}",
                "improvements": "{{ improvements }}",
                "mistakes": "{{ mistakes }}",
            },
        )

        # Cognitive extraction configuration
        self.cognitive_extraction = kwargs.get(
            "cognitive_extraction",
            {
                "enabled": True,
                "max_length_per_category": 300,
                "extract_patterns": {
                    "insights": [
                        r"(?:key insight|insight|finding|discovery|conclusion)[:\s]+(.+?)(?:\n|$)",
                        r"(?:provides?|identifies?|shows?|reveals?)\s+(.+?)(?:\n|$)",
                        r"(?:solid|good|strong)\s+(.+?)(?:\n|$)",
                        r"(?:accurately|correctly)\s+(.+?)(?:\n|$)",
                    ],
                    "improvements": [
                        r"(?:lacks?|lacking|needs?|requires?|missing|should|could)\s+(.+?)(?:\n|$)",
                        r"(?:would improve|would enhance|would strengthen)\s+(.+?)(?:\n|$)",
                        r"(?:could benefit from|would benefit from)\s+(.+?)(?:\n|$)",
                        r"(?:more|better|clearer|deeper|further)\s+(.+?)(?:\n|$)",
                        r"\*\*([^*]+)\*\*:\s*(?:While|Although|However|But)?\s*(.+?)(?:\n|$)",
                        r"(?:addressing|exploring|developing|conducting)\s+(.+?)(?:would|could)(?:\n|$)",
                        r"\d+\.\s*\*\*([^*]+)\*\*:\s*(.+?)(?:\n|$)",
                        r"(?:lacks depth|lacks specificity|more detailed|more thorough|clearer outline)\s+(.+?)(?:\n|$)",
                    ],
                    "mistakes": [
                        r"(?:error|mistake|wrong|incorrect|flaw|oversight)\s*[:\s]*(.+?)(?:\n|$)",
                        r"(?:overlooked|missed|ignored|failed to|not adequately|does not)\s+(.+?)(?:\n|$)",
                        r"(?:weakness|limitation|gap|problem)\s*[:\s]*(.+?)(?:\n|$)",
                        r"(?:lacks depth|lacks specificity|insufficient|inadequate)\s+(.+?)(?:\n|$)",
                    ],
                },
                "agent_priorities": {
                    "analyzer": ["insights", "improvements", "mistakes"],
                    "scorer": ["mistakes", "improvements"],
                    "evaluator": ["insights", "improvements"],
                    "critic": ["mistakes", "improvements"],
                },
            },
        )

    async def run(self, payload):
        """
        Execute the loop node with threshold checking.

        Args:
            payload: Dictionary containing 'input' and 'previous_outputs'

        Returns:
            dict: Final result with loop metadata and past_loops array
        """
        original_input = payload.get("input")
        original_previous_outputs = payload.get("previous_outputs", {})

        # Create a working copy of previous_outputs to avoid circular references
        # DON'T modify the original previous_outputs object
        loop_previous_outputs = original_previous_outputs.copy()

        # Initialize past_loops in our working copy
        past_loops = []

        current_loop = 0
        loop_result = None
        score = 0.0

        while current_loop < self.max_loops:
            current_loop += 1
            logger.info(f"Loop {current_loop}/{self.max_loops} starting")

            # Update the working copy with current past_loops for this iteration
            loop_previous_outputs["past_loops"] = past_loops

            # Execute internal workflow
            loop_result = await self._execute_internal_workflow(
                original_input,
                loop_previous_outputs,
            )

            # Extract score
            score = self._extract_score(loop_result)

            # Create past_loop object using metadata template
            past_loop_obj = self._create_past_loop_object(
                current_loop,
                score,
                loop_result,
                original_input,
            )

            # Add to our local past_loops array (not the original previous_outputs)
            past_loops.append(past_loop_obj)

            # Check threshold
            if score >= self.score_threshold:
                logger.info(f"Threshold met: {score} >= {self.score_threshold}")
                # Return final result with clean past_loops array and safe result
                return {
                    "input": original_input,
                    "result": self._create_safe_result(loop_result),
                    "loops_completed": current_loop,
                    "final_score": score,
                    "threshold_met": True,
                    "past_loops": past_loops,
                }

            logger.info(f"Threshold not met: {score} < {self.score_threshold}, continuing...")

        # Max loops reached without meeting threshold
        logger.info(f"Max loops reached: {self.max_loops}")
        return {
            "input": original_input,
            "result": self._create_safe_result(loop_result),
            "loops_completed": current_loop,
            "final_score": score,
            "threshold_met": False,
            "past_loops": past_loops,
        }

    async def _execute_internal_workflow(self, original_input, previous_outputs):
        """
        Execute the internal workflow configuration.

        Args:
            original_input: The original input data
            previous_outputs: Dictionary containing past_loops and other outputs

        Returns:
            The result of the internal workflow execution
        """
        from ..orchestrator import Orchestrator

        # Create temporary workflow file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(self.internal_workflow, f)
            temp_file = f.name

        try:
            # Create orchestrator for internal workflow
            orchestrator = Orchestrator(temp_file)

            # Create a safe version of previous_outputs to prevent circular references
            safe_previous_outputs = self._create_safe_result(previous_outputs)

            # 🔧 FIX: Calculate current loop number from past_loops length
            current_loop_number = len(previous_outputs.get("past_loops", [])) + 1

            # Prepare input with past_loops context AND loop_number
            workflow_input = {
                "input": original_input,
                "previous_outputs": safe_previous_outputs,
                "loop_number": current_loop_number,  # 🔧 CRITICAL FIX: Pass loop_number to internal agents
                "past_loops_metadata": {
                    "insights": self._extract_metadata_field(
                        "insights", previous_outputs.get("past_loops", [])
                    ),
                    "improvements": self._extract_metadata_field(
                        "improvements", previous_outputs.get("past_loops", [])
                    ),
                    "mistakes": self._extract_metadata_field(
                        "mistakes", previous_outputs.get("past_loops", [])
                    ),
                },
            }

            # Execute workflow with return_logs=True to get full logs for processing
            logs = await orchestrator.run(workflow_input, return_logs=True)

            # Extract actual agent responses from logs
            agents_results = {}
            for log_entry in logs:
                if isinstance(log_entry, dict) and log_entry.get("event_type") == "MetaReport":
                    continue  # Skip meta report

                if isinstance(log_entry, dict):
                    agent_id = log_entry.get("agent_id")
                    if agent_id and "payload" in log_entry:
                        payload = log_entry["payload"]
                        if "result" in payload:
                            agents_results[agent_id] = payload["result"]

            return agents_results

        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def _extract_score(self, result):
        """
        Extract score from workflow result.

        Args:
            result: The workflow result to extract score from (now a dict of agent responses)

        Returns:
            float: Extracted score value, defaults to 0.0 if not found
        """
        # Strategy 1: Direct key lookup in the result dictionary
        if isinstance(result, dict):
            # Check if there's a direct score key in the result
            if self.score_extraction_key in result:
                try:
                    return float(result[self.score_extraction_key])
                except (ValueError, TypeError):
                    pass

            # Check each agent's result for the score key
            for agent_id, agent_result in result.items():
                if isinstance(agent_result, dict) and self.score_extraction_key in agent_result:
                    try:
                        return float(agent_result[self.score_extraction_key])
                    except (ValueError, TypeError):
                        pass

        # Strategy 2: Pattern matching in result text
        # Convert the entire result to text and search for the pattern
        result_text = str(result)
        match = re.search(self.score_extraction_pattern, result_text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        # Strategy 3: Look for specific agent responses that might contain scores
        # This is useful for workflows where a specific agent (like "scorer") provides the score
        if isinstance(result, dict):
            for agent_id, agent_result in result.items():
                if "score" in agent_id.lower() or "scorer" in agent_id.lower():
                    # This agent likely contains the score
                    agent_text = str(agent_result)
                    match = re.search(self.score_extraction_pattern, agent_text)
                    if match:
                        try:
                            return float(match.group(1))
                        except ValueError:
                            pass

        # Default: return 0
        logger.warning(f"No score found in result: {result}, defaulting to 0")
        return 0.0

    def _extract_cognitive_insights(self, result):
        """
        Extract valuable cognitive insights from the loop result.

        Args:
            result: The workflow result (dict of agent responses)

        Returns:
            dict: Extracted cognitive insights categorized by type
        """
        if not self.cognitive_extraction.get("enabled", True):
            return {"insights": "", "improvements": "", "mistakes": ""}

        extracted = {"insights": [], "improvements": [], "mistakes": []}

        if isinstance(result, dict):
            for agent_id, agent_result in result.items():
                # Extract the actual text content from the agent result
                if isinstance(agent_result, dict):
                    # Look for response content in common result structures
                    if "response" in agent_result:
                        agent_text = str(agent_result["response"])
                    elif "result" in agent_result:
                        agent_text = str(agent_result["result"])
                    else:
                        agent_text = str(agent_result)
                else:
                    agent_text = str(agent_result)

                logger.debug(
                    f"Cognitive extraction for {agent_id}: processing {len(agent_text)} chars",
                )

                # Get priority categories for this agent
                agent_name = agent_id.lower()
                priorities = None
                for pattern, cats in self.cognitive_extraction.get("agent_priorities", {}).items():
                    if pattern in agent_name:
                        priorities = cats
                        break

                # If no specific priorities, use all categories
                if not priorities:
                    priorities = ["insights", "improvements", "mistakes"]

                logger.debug(f"Cognitive extraction for {agent_id}: using priorities {priorities}")

                # Extract from each priority category
                for category in priorities:
                    if category in extracted:
                        patterns = self.cognitive_extraction.get("extract_patterns", {}).get(
                            category,
                            [],
                        )

                        for pattern in patterns:
                            matches = re.findall(
                                pattern,
                                agent_text,
                                re.IGNORECASE | re.MULTILINE | re.DOTALL,
                            )
                            if matches:
                                logger.debug(
                                    f"Pattern '{pattern}' found {len(matches)} matches for {category}",
                                )
                            for match in matches:
                                # Handle tuple matches (from patterns with multiple groups)
                                if isinstance(match, tuple):
                                    # Join all non-empty groups
                                    clean_match = " ".join([m.strip() for m in match if m.strip()])
                                else:
                                    clean_match = match.strip()

                                if len(clean_match) > 10:  # Only keep meaningful extractions
                                    extracted[category].append(clean_match)
                                    logger.debug(f"Extracted {category}: {clean_match[:100]}...")

        # Consolidate and limit length for each category
        max_length = self.cognitive_extraction.get("max_length_per_category", 300)

        final_insights = {}
        for category, items in extracted.items():
            if items:
                # Remove duplicates while preserving order
                unique_items = []
                seen = set()
                for item in items:
                    if item.lower() not in seen:
                        unique_items.append(item)
                        seen.add(item.lower())

                # Join and truncate
                combined = " | ".join(unique_items)
                if len(combined) > max_length:
                    combined = combined[:max_length] + "..."

                final_insights[category] = combined
            else:
                final_insights[category] = ""

        return final_insights

    def _create_past_loop_object(self, loop_number, score, result, original_input):
        """
        Create past_loop object using metadata template with cognitive insights.

        Args:
            loop_number (int): Current loop iteration number
            score (float): Score extracted from this loop's result
            result: The result from this loop's execution (dict of agent responses)
            original_input: The original input data

        Returns:
            dict: Past loop object with templated metadata and cognitive insights
        """
        # Extract cognitive insights from the result
        cognitive_insights = self._extract_cognitive_insights(result)

        # Create a safe version of the result for fallback
        safe_result = self._create_safe_result(result)

        # Ensure input is also safe and truncated
        safe_input = str(original_input)
        if len(safe_input) > 200:
            safe_input = safe_input[:200] + "...<truncated>"

        # Template variables with cognitive insights
        template_vars = {
            "loop_number": loop_number,
            "score": score,
            "timestamp": datetime.now().isoformat(),
            "result": safe_result,
            "input": safe_input,
            "insights": cognitive_insights.get("insights", ""),
            "improvements": cognitive_insights.get("improvements", ""),
            "mistakes": cognitive_insights.get("mistakes", ""),
        }

        # Build past_loop object from metadata template - ensure only primitives
        past_loop_obj = {}
        for key, template in self.past_loops_metadata.items():
            if (
                isinstance(template, str)
                and template.startswith("{{ ")
                and template.endswith(" }}")
            ):
                # Extract variable name from template
                var_name = template.strip("{{ ").strip(" }}")
                value = template_vars.get(var_name, template)
                # Ensure the value is a safe primitive type
                if isinstance(value, (str, int, float, bool, type(None))):
                    past_loop_obj[key] = value
                elif isinstance(value, dict):
                    # For dict values, convert to a safe string representation
                    past_loop_obj[key] = str(value)
                else:
                    past_loop_obj[key] = str(value)
            # Ensure template is also a primitive
            elif isinstance(template, (str, int, float, bool, type(None))):
                past_loop_obj[key] = template
            else:
                past_loop_obj[key] = str(template)

        return past_loop_obj

    def _create_safe_result(self, result):
        """
        Create a safe, serializable version of the result that avoids circular references.

        Args:
            result: The original result object

        Returns:
            A safe version of the result without circular references
        """

        def _make_safe(obj, seen=None):
            """Recursively make an object safe by removing circular references."""
            if seen is None:
                seen = set()

            # Check for already seen objects (circular reference)
            obj_id = id(obj)
            if obj_id in seen:
                return "<circular_reference>"

            if obj is None:
                return None

            if isinstance(obj, (str, int, float, bool)):
                return obj

            # For collections, track this object to detect cycles
            seen.add(obj_id)

            try:
                if isinstance(obj, list):
                    safe_result = []
                    for item in obj:
                        safe_result.append(_make_safe(item, seen.copy()))
                    return safe_result

                if isinstance(obj, dict):
                    safe_result = {}
                    for key, value in obj.items():
                        # Skip problematic keys that are known to cause circular references
                        if key in ["previous_outputs", "payload"]:
                            continue
                        # For other keys, recursively make them safe
                        safe_result[key] = _make_safe(value, seen.copy())
                    return safe_result

                # For any other type, convert to string (truncated if too long)
                str_repr = str(obj)
                if len(str_repr) > 1000:
                    return str_repr[:1000] + "...<truncated>"
                return str_repr

            finally:
                seen.discard(obj_id)

        return _make_safe(result)

    def _extract_metadata_field(self, field_name, past_loops):
        """
        Extract and combine a specific metadata field from past loops.

        Args:
            field_name (str): The metadata field to extract (e.g., "insights", "improvements")
            past_loops (list): List of past loop objects

        Returns:
            str: Combined metadata from all past loops
        """
        if not past_loops:
            return ""

        values = []
        for loop in past_loops:
            if isinstance(loop, dict) and field_name in loop:
                value = loop[field_name]
                if value and isinstance(value, str):
                    values.append(value)

        return " | ".join(values) if values else ""
