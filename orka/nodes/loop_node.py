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

import json
import logging
import os
import re
import tempfile
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Mapping,
    NoReturn,
    Optional,
    Protocol,
    TypedDict,
    TypeGuard,
    TypeVar,
    Union,
    cast,
)

import yaml
from redis import Redis
from redis.client import Redis as RedisType

from ..memory.redisstack_logger import RedisStackMemoryLogger
from .base_node import BaseNode

T = TypeVar("T")

logger = logging.getLogger(__name__)
logger.info(f"DEBUG: Loading loop_node.py from {__file__}")


class PastLoopMetadata(TypedDict, total=False):
    loop_number: int
    score: float
    timestamp: str
    insights: str
    improvements: str
    mistakes: str
    result: Dict[str, Any]


class InsightCategory(TypedDict):
    insights: str
    improvements: str
    mistakes: str


class FloatConvertible(Protocol):
    def __float__(self) -> float: ...


CategoryType = Literal["insights", "improvements", "mistakes"]
MetadataKey = Literal["loop_number", "score", "timestamp", "insights", "improvements", "mistakes"]


class LoopNode(BaseNode):
    """
    Simple loop node that repeats an internal workflow until threshold is met.

    This node executes an internal workflow repeatedly until a score threshold is reached
    or the maximum number of loops is exceeded. Each loop's result is tracked in the
    past_loops array, allowing for iterative improvement based on previous attempts.
    """

    def __init__(
        self,
        node_id: str,
        prompt: Optional[str] = None,
        queue: Optional[List[Any]] = None,
        memory_logger: Optional[RedisStackMemoryLogger] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the loop node.

        Args:
            node_id (str): Unique identifier for the node.
            prompt (Optional[str]): Prompt or instruction for the node.
            queue (Optional[List[Any]]): Queue of agents or nodes to be processed.
            memory_logger (Optional[RedisStackMemoryLogger]): The RedisStackMemoryLogger instance.
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

        # Ensure memory_logger is of correct type
        if memory_logger is not None and not isinstance(memory_logger, RedisStackMemoryLogger):
            logger.warning(f"Expected RedisStackMemoryLogger but got {type(memory_logger)}")  # type: ignore [unreachable]
            try:
                memory_logger = cast(RedisStackMemoryLogger, memory_logger)
            except Exception as e:
                logger.error(f"Failed to cast memory logger: {e}")
                memory_logger = None

        self.memory_logger = memory_logger

        # Configuration with type hints
        self.max_loops: int = kwargs.get("max_loops", 5)
        self.score_threshold: float = kwargs.get("score_threshold", 0.8)
        self.score_extraction_config: Dict[str, List[Dict[str, Union[str, List[str]]]]] = (
            kwargs.get(
                "score_extraction_config",
                {
                    "strategies": [
                        {
                            "type": "pattern",
                            "patterns": [
                                r"score:\s*(\d+\.?\d*)",
                                r"rating:\s*(\d+\.?\d*)",
                                r"confidence:\s*(\d+\.?\d*)",
                            ],
                        }
                    ]
                },
            )
        )

        # Backward compatibility - convert old format to new format
        if "score_extraction_pattern" in kwargs or "score_extraction_key" in kwargs:
            logger.warning(
                "score_extraction_pattern and score_extraction_key are deprecated. Use score_extraction_config instead.",
            )

            # Convert old format to new format
            old_strategies = []

            if "score_extraction_key" in kwargs:
                old_strategies.append(
                    {
                        "type": "direct_key",
                        "key": kwargs["score_extraction_key"],
                    },
                )

            if "score_extraction_pattern" in kwargs:
                old_strategies.append(
                    {
                        "type": "pattern",
                        "patterns": [kwargs["score_extraction_pattern"]],
                    },
                )

            if old_strategies:
                self.score_extraction_config = {"strategies": old_strategies}

        # Internal workflow configuration
        self.internal_workflow = kwargs.get("internal_workflow", {})

        # Past loops metadata structure (user-defined)
        metadata_fields: Dict[MetadataKey, str] = {
            "loop_number": "{{ loop_number }}",
            "score": "{{ score }}",
            "timestamp": "{{ timestamp }}",
            "insights": "{{ insights }}",
            "improvements": "{{ improvements }}",
            "mistakes": "{{ mistakes }}",
        }
        self.past_loops_metadata: Dict[MetadataKey, str] = metadata_fields

        # Cognitive extraction configuration
        self.cognitive_extraction: Dict[str, Any] = kwargs.get(
            "cognitive_extraction",
            {
                "enabled": True,
                "max_length_per_category": 300,
                "extract_patterns": {
                    "insights": [],
                    "improvements": [],
                    "mistakes": [],
                },
                "agent_priorities": {},
            },
        )

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the loop node with threshold checking."""
        original_input = payload.get("input")
        original_previous_outputs = payload.get("previous_outputs", {})

        # Create a working copy of previous_outputs to avoid circular references
        loop_previous_outputs = original_previous_outputs.copy()

        # Initialize past_loops in our working copy
        past_loops: List[PastLoopMetadata] = []

        current_loop = 0
        loop_result: Optional[Dict[str, Any]] = None
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

            if loop_result is None:
                logger.error("Internal workflow execution failed")
                break

            # Extract score
            score = self._extract_score(loop_result)

            # Create past_loop object using metadata template
            past_loop_obj = self._create_past_loop_object(
                current_loop,
                score,
                loop_result,
                original_input,
            )

            # Add to our local past_loops array
            past_loops.append(past_loop_obj)

            # Store loop result in Redis if memory_logger is available
            if self.memory_logger is not None:
                try:
                    # Store individual loop result
                    loop_key = f"loop_result:{self.node_id}:{current_loop}"
                    self._store_in_redis(loop_key, loop_result)
                    logger.debug(f"Stored loop result: {loop_key}")

                    # Store past loops array
                    past_loops_key = f"past_loops:{self.node_id}"
                    self._store_in_redis(past_loops_key, past_loops)
                    logger.debug(f"Stored past loops: {past_loops_key}")

                    # Store in Redis hash for tracking
                    group_key = f"loop_results:{self.node_id}"
                    self._store_in_redis_hash(
                        group_key,
                        str(current_loop),
                        {
                            "result": loop_result,
                            "score": score,
                            "past_loop": past_loop_obj,
                        },
                    )
                    logger.debug(f"Stored result in group for loop {current_loop}")
                except Exception as e:
                    logger.error(f"Failed to store loop result in Redis: {e}")

            # Check threshold
            if score >= self.score_threshold:
                logger.info(f"Threshold met: {score} >= {self.score_threshold}")
                # Return final result with clean past_loops array and safe result
                final_result = {
                    "input": original_input,
                    "result": self._create_safe_result(loop_result),
                    "loops_completed": current_loop,
                    "final_score": score,
                    "threshold_met": True,
                    "past_loops": past_loops,
                }

                # Store final result in Redis
                if self.memory_logger is not None:
                    try:
                        final_key = f"final_result:{self.node_id}"
                        self._store_in_redis(final_key, final_result)
                        logger.debug(f"Stored final result: {final_key}")
                    except Exception as e:
                        logger.error(f"Failed to store final result in Redis: {e}")

                return final_result

            logger.info(f"Threshold not met: {score} < {self.score_threshold}, continuing...")

        # Max loops reached without meeting threshold
        if loop_result is None:
            loop_result = {}

        logger.info(f"Max loops reached: {self.max_loops}")
        final_result = {
            "input": original_input,
            "result": self._create_safe_result(loop_result),
            "loops_completed": current_loop,
            "final_score": score,
            "threshold_met": False,
            "past_loops": past_loops,
        }

        # Store final result in Redis
        if self.memory_logger is not None:
            try:
                final_key = f"final_result:{self.node_id}"
                self._store_in_redis(final_key, final_result)
                logger.debug(f"Stored final result: {final_key}")
            except Exception as e:
                logger.error(f"Failed to store final result in Redis: {e}")

        return final_result

    async def _execute_internal_workflow(
        self, original_input: Any, previous_outputs: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Execute the internal workflow configuration."""
        import os

        from ..orchestrator import Orchestrator

        # Get the original workflow configuration
        original_workflow = self.internal_workflow.copy()

        # Ensure we have the basic structure
        if "orchestrator" not in original_workflow:
            original_workflow["orchestrator"] = {}

        # Update the orchestrator configuration while preserving agents
        orchestrator_config = original_workflow["orchestrator"]
        orchestrator_config.update(
            {
                "id": orchestrator_config.get("id", "internal-workflow"),
                "strategy": orchestrator_config.get("strategy", "sequential"),
                "memory": {
                    "config": {
                        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6380/0"),
                        "backend": "redisstack",
                        "enable_hnsw": True,
                        "vector_params": {
                            "M": 16,
                            "ef_construction": 200,
                            "ef_runtime": 10,
                        },
                    }
                },
            }
        )

        # Create temporary workflow file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(original_workflow, f)
            temp_file = f.name

        try:
            # Create orchestrator for internal workflow
            orchestrator = Orchestrator(temp_file)

            # Use parent's memory logger to maintain consistency
            if self.memory_logger is not None:
                orchestrator.memory = self.memory_logger
                orchestrator.fork_manager.redis = self.memory_logger.redis  # Fixed attribute name

            # Create a safe version of previous_outputs to prevent circular references
            safe_previous_outputs = self._create_safe_result(previous_outputs)

            # Calculate current loop number from past_loops length
            current_loop_number = len(previous_outputs.get("past_loops", [])) + 1

            # Prepare input with past_loops context AND loop_number
            workflow_input = {
                "input": original_input,
                "previous_outputs": safe_previous_outputs,
                "loop_number": current_loop_number,
                "past_loops_metadata": {
                    "insights": self._extract_metadata_field(
                        "insights",
                        cast(List[PastLoopMetadata], previous_outputs.get("past_loops", [])),
                    ),
                    "improvements": self._extract_metadata_field(
                        "improvements",
                        cast(List[PastLoopMetadata], previous_outputs.get("past_loops", [])),
                    ),
                    "mistakes": self._extract_metadata_field(
                        "mistakes",
                        cast(List[PastLoopMetadata], previous_outputs.get("past_loops", [])),
                    ),
                },
            }

            # Execute workflow with return_logs=True to get full logs for processing
            logs = await orchestrator.run(workflow_input, return_logs=True)

            # Extract actual agent responses from logs
            agents_results: Dict[str, Any] = {}
            for log_entry in logs:
                if isinstance(log_entry, dict) and log_entry.get("event_type") == "MetaReport":
                    continue  # Skip meta report

                if isinstance(log_entry, dict):
                    agent_id = log_entry.get("agent_id")
                    if agent_id and "payload" in log_entry:
                        payload = log_entry["payload"]
                        if "result" in payload:
                            agents_results[agent_id] = payload["result"]
                            # Store agent result in Redis
                            result_key = f"agent_result:{agent_id}:{current_loop_number}"
                            self._store_in_redis(result_key, payload["result"])

                            # Store in Redis hash for tracking
                            group_key = f"agent_results:{self.node_id}:{current_loop_number}"
                            self._store_in_redis_hash(group_key, agent_id, payload["result"])

            # Store all results for this loop
            loop_results_key = f"loop_agents:{self.node_id}:{current_loop_number}"
            self._store_in_redis(loop_results_key, agents_results)

            # Store in Redis hash for tracking
            group_key = f"loop_agents:{self.node_id}"
            self._store_in_redis_hash(group_key, str(current_loop_number), agents_results)

            return agents_results

        except Exception as e:
            logger.error(f"Failed to execute internal workflow: {e}")
            return None

        finally:
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to delete temporary workflow file: {e}")

    def _is_valid_value(self, value: Any) -> TypeGuard[Union[str, int, float]]:
        """Check if a value can be converted to float."""
        try:
            if isinstance(value, (int, float)):
                return True
            if isinstance(value, str) and value.strip():
                float(value)
                return True
            return False
        except (ValueError, TypeError):
            return False

    def _extract_score(self, result: Dict[str, Any]) -> float:
        """Extract score from result using configured extraction strategies."""
        if not result:
            return 0.0

        strategies = self.score_extraction_config.get("strategies", [])

        for strategy in strategies:
            if not isinstance(strategy, dict):
                continue  # type: ignore [unreachable]

            strategy_type = strategy.get("type")

            if strategy_type == "direct_key":
                key = str(strategy.get("key", ""))
                if key in result:
                    value = result[key]
                    if self._is_valid_value(value):
                        return float(value)  # Now type-safe due to TypeGuard

            elif strategy_type == "pattern":
                patterns = strategy.get("patterns", [])
                if not isinstance(patterns, list):
                    continue

                for pattern in patterns:
                    if not isinstance(pattern, str):
                        continue  # type: ignore [unreachable]

                    for value in result.values():
                        if isinstance(value, str):
                            match = re.search(pattern, value)
                            if match and match.group(1):
                                try:
                                    return float(match.group(1))
                                except (ValueError, TypeError):
                                    continue

        return 0.0

    def _extract_direct_key(self, result: dict[str, Any], key: str) -> float | None:
        """Extract score from direct key in result."""
        if key in result:
            try:
                return float(result[key])
            except (ValueError, TypeError):
                pass
        return None

    def _extract_agent_key(
        self, result: dict[str, Any], agents: list[str], key: str
    ) -> float | None:
        """Extract score from specific agent results."""
        import ast
        import json

        for agent_id, agent_result in result.items():
            # Check if this agent matches our priority list
            if agents and not any(agent_name in agent_id.lower() for agent_name in agents):
                continue

            # 🔧 FIXED: Handle nested result structures (result.response, result.result, etc.)
            possible_values = []

            # Direct key access
            if isinstance(agent_result, dict) and key in agent_result:
                possible_values.append(agent_result[key])

            # Nested access - look in result.response, result.result, etc.
            if isinstance(agent_result, dict):
                for nested_key in ["response", "result", "output", "data"]:
                    if nested_key in agent_result:
                        nested_value = agent_result[nested_key]

                        # If nested value is a dict, look for our key directly
                        if isinstance(nested_value, dict) and key in nested_value:
                            possible_values.append(nested_value[key])

                        # 🔧 NEW: Parse string dictionaries from LLM responses
                        elif isinstance(nested_value, str):
                            # Try to parse as JSON first
                            try:
                                parsed = json.loads(nested_value)
                                if isinstance(parsed, dict) and key in parsed:
                                    possible_values.append(parsed[key])
                            except json.JSONDecodeError:
                                pass

                            # Try to parse as Python dictionary string
                            try:
                                parsed = ast.literal_eval(nested_value)
                                if isinstance(parsed, dict) and key in parsed:
                                    possible_values.append(parsed[key])
                            except (ValueError, SyntaxError):
                                pass

                            # Try regex pattern matching on the string
                            import re

                            pattern = rf"['\"]?{re.escape(key)}['\"]?\s*:\s*([0-9.]+)"
                            match = re.search(pattern, nested_value)
                            if match:
                                possible_values.append(match.group(1))

            # Try to convert any found values to float
            for value in possible_values:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue

        return None

    def _extract_nested_path(self, result: dict[str, Any], path: str) -> float | None:
        """Extract score from nested path (e.g., 'result.score')."""
        if not path:
            return None

        path_parts = path.split(".")
        current = result

        for part in path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        if self._is_valid_value(current):
            return float(current)
        return None

    def _extract_pattern(self, result: dict[str, Any], patterns: list[str]) -> float | None:
        """Extract score using regex patterns."""
        result_text = str(result)

        for pattern in patterns:
            try:
                match = re.search(pattern, result_text)
                if match:
                    try:
                        return float(match.group(1))
                    except (ValueError, IndexError):
                        continue
            except re.error:
                # Skip invalid regex patterns
                continue

        return None

    def _extract_secondary_metric(
        self, result: dict[str, Any], metric_key: str, default: Any = 0.0
    ) -> Any:
        """
        Extract secondary metrics (like REASONING_QUALITY, CONVERGENCE_TREND) from agent responses.

        Args:
            result: The workflow result to extract metric from
            metric_key: The key to look for (e.g., "REASONING_QUALITY", "CONVERGENCE_TREND")
            default: Default value if metric not found

        Returns:
            The extracted metric value or default
        """
        if not isinstance(result, dict):
            logger.warning(f"Result is not a dict, cannot extract {metric_key}: {type(result)}")  # type: ignore [unreachable]
            return default

        import ast
        import json
        import re

        # Try different extraction strategies
        for agent_id, agent_result in result.items():
            if not isinstance(agent_result, dict):
                continue

            # Look in nested structures
            for nested_key in ["response", "result", "output", "data"]:
                if nested_key not in agent_result:
                    continue

                nested_value = agent_result[nested_key]

                # If nested value is a dict, look for our key directly
                if isinstance(nested_value, dict) and metric_key in nested_value:
                    return nested_value[metric_key]

                # Parse string dictionaries from LLM responses
                elif isinstance(nested_value, str):
                    # Try to parse as JSON first
                    try:
                        parsed = json.loads(nested_value)
                        if isinstance(parsed, dict) and metric_key in parsed:
                            return parsed[metric_key]
                    except json.JSONDecodeError:
                        pass

                    # Try to parse as Python dictionary string
                    try:
                        parsed = ast.literal_eval(nested_value)
                        if isinstance(parsed, dict) and metric_key in parsed:
                            return parsed[metric_key]
                    except (ValueError, SyntaxError):
                        pass

                    # Try regex pattern matching on the string
                    pattern = (
                        rf"['\"]?{re.escape(metric_key)}['\"]?\s*:\s*['\"]?([^'\",$\}}]+)['\"]?"
                    )
                    match = re.search(pattern, nested_value)
                    if match:
                        value = match.group(1).strip()
                        # For numeric values, try to convert to float
                        if (
                            metric_key in ["REASONING_QUALITY", "AGREEMENT_SCORE"]
                            and value.replace(".", "").isdigit()
                        ):
                            try:
                                return float(value)
                            except ValueError:
                                pass
                        return value

        # Fallback: return default
        logger.debug(
            f"Secondary metric '{metric_key}' not found in result, using default: {default}",
        )
        return default

    def _extract_cognitive_insights(
        self, result: Dict[str, Any], max_length: int = 300
    ) -> InsightCategory:
        """Extract cognitive insights from result using configured patterns."""
        if not self.cognitive_extraction.get("enabled", True):
            return InsightCategory(insights="", improvements="", mistakes="")

        extract_patterns = cast(
            Dict[str, List[str]], self.cognitive_extraction.get("extract_patterns", {})
        )
        agent_priorities = cast(
            Dict[str, List[str]], self.cognitive_extraction.get("agent_priorities", {})
        )
        max_length = self.cognitive_extraction.get("max_length_per_category", max_length)

        extracted: Dict[CategoryType, List[str]] = {
            "insights": [],
            "improvements": [],
            "mistakes": [],
        }

        if not isinstance(result, dict):
            return InsightCategory(insights="", improvements="", mistakes="")  # type: ignore [unreachable]

        # Extract insights from each agent's response based on priorities
        for agent_id, agent_result in result.items():
            if not isinstance(agent_result, (str, dict)):
                continue

            # Get text to analyze - either direct string or from dict
            text = agent_result if isinstance(agent_result, str) else str(agent_result)

            # Get categories to extract for this agent
            agent_cats = agent_priorities.get(agent_id, [])
            valid_categories = [
                cat
                for cat in agent_cats
                if cat in extract_patterns and cat in ("insights", "improvements", "mistakes")
            ]

            # Apply patterns for each category
            for category in valid_categories:
                cat_key = cast(CategoryType, category)
                patterns = extract_patterns.get(category, [])
                if not isinstance(patterns, list):
                    continue  # type: ignore [unreachable]

                for pattern in patterns:
                    if not isinstance(pattern, str):
                        continue  # type: ignore [unreachable]

                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        if len(match.groups()) > 0:
                            insight = match.group(1).strip()
                            if insight and len(insight) > 10:  # Minimum length threshold
                                extracted[cat_key].append(insight)

        # Process each category
        result_insights = []
        result_improvements = []
        result_mistakes = []

        for category, items in extracted.items():
            if not items:
                continue

            # Remove duplicates while preserving order
            unique_items = []
            seen: set[str] = set()
            for item in items:
                if item.lower() not in seen:
                    unique_items.append(item)
                    seen.add(item.lower())

            # Join and truncate
            combined = " | ".join(unique_items)
            if len(combined) > max_length:
                combined = combined[:max_length] + "..."

            if category == "insights":
                result_insights.append(combined)
            elif category == "improvements":
                result_improvements.append(combined)
            elif category == "mistakes":
                result_mistakes.append(combined)

        return InsightCategory(
            insights=" | ".join(result_insights),
            improvements=" | ".join(result_improvements),
            mistakes=" | ".join(result_mistakes),
        )

    def _create_past_loop_object(
        self, loop_number: int, score: float, result: Dict[str, Any], original_input: Any
    ) -> PastLoopMetadata:
        """Create past_loop object using metadata template with cognitive insights."""
        # Extract cognitive insights from the result
        cognitive_insights = self._extract_cognitive_insights(result)

        # Extract secondary metrics from agent responses
        reasoning_quality = self._extract_secondary_metric(result, "REASONING_QUALITY")
        convergence_trend = self._extract_secondary_metric(
            result,
            "CONVERGENCE_TREND",
            default="STABLE",
        )

        # Create a safe version of the result for fallback
        safe_result = self._create_safe_result(result)

        # Ensure input is also safe and truncated
        safe_input = str(original_input)
        if len(safe_input) > 200:
            safe_input = safe_input[:200] + "...<truncated>"

        # Complete template context for Jinja2 rendering
        template_context = {
            "loop_number": loop_number,
            "score": score,
            "reasoning_quality": reasoning_quality,
            "convergence_trend": convergence_trend,
            "timestamp": datetime.now().isoformat(),
            "result": safe_result,
            "input": safe_input,
            "insights": cognitive_insights.get("insights", ""),
            "improvements": cognitive_insights.get("improvements", ""),
            "mistakes": cognitive_insights.get("mistakes", ""),
            "previous_outputs": safe_result,
        }

        # Create past loop object with proper type
        past_loop_obj: PastLoopMetadata = {
            "loop_number": loop_number,
            "score": score,
            "timestamp": datetime.now().isoformat(),
            "insights": cognitive_insights.get("insights", ""),
            "improvements": cognitive_insights.get("improvements", ""),
            "mistakes": cognitive_insights.get("mistakes", ""),
            "result": safe_result,
        }

        return past_loop_obj

    def _create_safe_result(self, result: Any) -> Any:
        """Create a safe, serializable version of the result that avoids circular references."""

        def _make_safe(obj: Any, seen: Optional[set[int]] = None) -> Any:
            if seen is None:
                seen = set()

            obj_id = id(obj)
            if obj_id in seen:
                return "<circular_reference>"

            if obj is None:
                return None

            if isinstance(obj, (str, int, float, bool)):
                return obj

            seen.add(obj_id)

            try:
                if isinstance(obj, list):
                    return [_make_safe(item, seen.copy()) for item in obj]

                if isinstance(obj, dict):
                    return {
                        str(key): _make_safe(value, seen.copy())
                        for key, value in obj.items()
                        if key not in ("previous_outputs", "payload")
                    }

                return str(obj)[:1000] + "..." if len(str(obj)) > 1000 else str(obj)

            finally:
                seen.discard(obj_id)

        return _make_safe(result)

    def _extract_metadata_field(
        self, field: MetadataKey, past_loops: List[PastLoopMetadata], max_entries: int = 5
    ) -> str:
        """Extract metadata field from past loops."""
        values = []
        for loop in reversed(past_loops[-max_entries:]):
            if field in loop and loop[field]:
                values.append(str(loop[field]))
        return " | ".join(values)

    def _store_in_redis(self, key: str, value: Any) -> None:
        """Safely store a value in Redis."""
        if self.memory_logger is not None:
            try:
                self.memory_logger.set(key, json.dumps(value))
                logger.debug(f"Stored in Redis: {key}")
            except Exception as e:
                logger.error(f"Failed to store in Redis: {e}")

    def _store_in_redis_hash(self, hash_key: str, field: str, value: Any) -> None:
        """Safely store a value in a Redis hash."""
        if self.memory_logger is not None:
            try:
                self.memory_logger.hset(hash_key, field, json.dumps(value))
                logger.debug(f"Stored in Redis hash: {hash_key}[{field}]")
            except Exception as e:
                logger.error(f"Failed to store in Redis hash: {e}")
