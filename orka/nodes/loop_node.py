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

import ast
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
    Optional,
    Protocol,
    TypedDict,
    TypeGuard,
    TypeVar,
    Union,
    cast,
)

import numpy as np
import yaml
from jinja2 import Template

from ..memory.redisstack_logger import RedisStackMemoryLogger
from ..scoring import BooleanScoreCalculator
from ..utils.embedder import get_embedder
from .base_node import BaseNode

T = TypeVar("T")

logger = logging.getLogger(__name__)


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
    A specialized node that executes an internal workflow repeatedly until a condition is met.

    The LoopNode enables iterative improvement workflows by running a sub-workflow multiple
    times, learning from each iteration, and stopping when either a quality threshold is met
    or a maximum number of iterations is reached.

    Key Features:
        - Iterative execution with quality thresholds
        - Cognitive insight extraction from each iteration
        - Learning from past iterations
        - Automatic loop termination based on scores or max iterations
        - Metadata tracking across iterations

    Attributes:
        max_loops (int): Maximum number of iterations allowed
        score_threshold (float): Quality score required to stop iteration
        score_extraction_pattern (str): Regex pattern to extract quality scores
        cognitive_extraction (dict): Configuration for extracting insights
        past_loops_metadata (dict): Template for tracking iteration data
        internal_workflow (dict): The workflow to execute in each iteration

    Example:

    .. code-block:: yaml

        - id: improvement_loop
          type: loop
          max_loops: 5
          score_threshold: 0.85
          score_extraction_pattern: "QUALITY_SCORE:\\s*([0-9.]+)"
          cognitive_extraction:
            enabled: true
            extract_patterns:
              insights: ["(?:provides?|shows?)\\s+(.+?)(?:\\n|$)"]
              improvements: ["(?:lacks?|needs?)\\s+(.+?)(?:\\n|$)"]
          past_loops_metadata:
            iteration: "{{ loop_number }}"
            score: "{{ score }}"
            insights: "{{ insights }}"
          internal_workflow:
            orchestrator:
              id: improvement-cycle
              agents: [analyzer, scorer]
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
                - high_priority_agents (List[str]): Agent names to check first for scores (default: ["agreement_moderator", "quality_moderator", "score_moderator"])
                - score_extraction_config (dict): Complete score extraction configuration with strategies
                - score_extraction_pattern (str): Regex pattern to extract score from results (deprecated, use score_extraction_config)
                - score_extraction_key (str): Direct key to look for score in result dict (deprecated, use score_extraction_config)
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

        # Boolean scoring configuration (optional)
        scoring_config = kwargs.get("scoring", {})
        self.scoring_preset: Optional[str] = (
            scoring_config.get("preset") if isinstance(scoring_config, dict) else None
        )
        self.custom_weights: Optional[Dict[str, float]] = (
            scoring_config.get("custom_weights") if isinstance(scoring_config, dict) else None
        )

        # Initialize boolean score calculator if preset is configured
        self.score_calculator: Optional[BooleanScoreCalculator] = None
        if self.scoring_preset:
            try:
                self.score_calculator = BooleanScoreCalculator(
                    preset=self.scoring_preset,
                    custom_weights=self.custom_weights,
                )
                logger.info(
                    f"LoopNode '{node_id}': Initialized with boolean scoring preset '{self.scoring_preset}'"
                )
            except Exception as e:
                logger.warning(
                    f"LoopNode '{node_id}': Failed to initialize boolean scoring: {e}. "
                    "Falling back to legacy score extraction."
                )
                self.score_calculator = None

        # High-priority agents for score extraction (configurable)
        self.high_priority_agents: List[str] = kwargs.get(
            "high_priority_agents", ["agreement_moderator", "quality_moderator", "score_moderator"]
        )

        # Debug: Log the received configuration
        if "score_extraction_config" in kwargs:
            logger.debug(f"LoopNode {node_id}: Received custom score_extraction_config from YAML")
            custom_config = kwargs["score_extraction_config"]
            if "strategies" in custom_config:
                logger.debug(
                    f"LoopNode {node_id}: Found {len(custom_config['strategies'])} strategies"
                )
                for i, strategy in enumerate(custom_config["strategies"]):
                    if strategy.get("type") == "pattern" and "patterns" in strategy:
                        logger.debug(
                            f"LoopNode {node_id}: Strategy {i+1} has {len(strategy['patterns'])} patterns"
                        )
                        logger.debug(
                            f"LoopNode {node_id}: First pattern: {strategy['patterns'][0] if strategy['patterns'] else 'None'}"
                        )
        else:
            logger.debug(f"LoopNode {node_id}: No custom score_extraction_config, using defaults")

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
                                r"agreement:\s*(\d+\.?\d*)",
                                r"consensus:\s*(\d+\.?\d*)",
                                r"AGREEMENT:\s*(\d+\.?\d*)",
                                r"SCORE:\s*(\d+\.?\d*)",
                                r"Score:\s*(\d+\.?\d*)",
                                r"Agreement:\s*(\d+\.?\d*)",
                                r"(\d+\.?\d*)/10",
                                r"(\d+\.?\d*)%",
                                r"(\d+\.?\d*)\s*out\s*of\s*10",
                                r"(\d+\.?\d*)\s*points?",
                                r"0\.[6-9][0-9]?",  # Pattern for high agreement scores
                                r"([0-9]+\.[0-9]+)",  # Any decimal number
                            ],
                        }
                    ]
                },
            )
        )

        # Debug: Log which configuration is actually being used
        if "strategies" in self.score_extraction_config:
            strategy_count = len(self.score_extraction_config["strategies"])
            logger.debug(f"LoopNode {node_id}: Using {strategy_count} extraction strategies")
            for i, strategy in enumerate(self.score_extraction_config["strategies"]):
                if strategy.get("type") == "pattern" and "patterns" in strategy:
                    pattern_count = len(strategy["patterns"])
                    first_pattern = strategy["patterns"][0] if strategy["patterns"] else "None"
                    logger.debug(
                        f"LoopNode {node_id}: Strategy {i+1} (pattern): {pattern_count} patterns, first: {first_pattern}"
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
        default_metadata_fields: Dict[MetadataKey, str] = {
            "loop_number": "{{ loop_number }}",
            "score": "{{ score }}",
            "timestamp": "{{ timestamp }}",
            "insights": "{{ insights }}",
            "improvements": "{{ improvements }}",
            "mistakes": "{{ mistakes }}",
        }

        # Load user-defined past_loops_metadata from YAML configuration
        user_metadata = kwargs.get("past_loops_metadata", {})
        if user_metadata:
            self.past_loops_metadata: Dict[MetadataKey, str] = user_metadata
        else:
            logger.debug("Using default past_loops_metadata structure")
            self.past_loops_metadata = default_metadata_fields

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

        # Persistence configuration
        self.persist_across_runs: bool = kwargs.get("persist_across_runs", True)

    async def _run_impl(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the loop node with threshold checking."""
        original_input = payload.get("input")
        original_previous_outputs = payload.get("previous_outputs", {})

        # DEBUG: Log what we receive at the start
        logger.debug(f"LoopNode.run() received payload keys: {list(payload.keys())}")
        logger.debug(f"LoopNode.run() original_input: {original_input}")
        logger.debug(f"LoopNode.run() original_input type: {type(original_input)}")

        # 🐛 GraphScout Fix: Extract parent orchestrator's agents for internal workflow
        if "orchestrator" in payload and hasattr(payload["orchestrator"], "agent_cfgs"):
            self._parent_agents = payload["orchestrator"].agent_cfgs
            logger.debug(
                f"LoopNode: Captured {len(self._parent_agents)} parent agents for GraphScout"
            )

        # Create a working copy of previous_outputs to avoid circular references
        loop_previous_outputs = original_previous_outputs.copy()

        # Initialize past_loops - load from Redis if persistence is enabled
        past_loops: List[PastLoopMetadata] = []
        if self.persist_across_runs:
            past_loops = await self._load_past_loops_from_redis()

        # Set past_loops in the working copy once at the beginning
        loop_previous_outputs["past_loops"] = past_loops

        current_loop = 0
        loop_result: Optional[Dict[str, Any]] = None
        score = 0.0

        while current_loop < self.max_loops:
            current_loop += 1
            logger.info(f"Loop {current_loop}/{self.max_loops} starting")

            # Clear any Redis cache that might cause response duplication
            await self._clear_loop_cache(current_loop)

            # Execute internal workflow
            loop_result = await self._execute_internal_workflow(
                original_input,
                loop_previous_outputs,
                current_loop,
            )

            if loop_result is None:
                logger.error("Internal workflow execution failed")
                break

            # Extract score
            score = await self._extract_score(loop_result)

            # Create past_loop object using metadata template
            past_loop_obj = self._create_past_loop_object(
                current_loop,
                score,
                loop_result,
                original_input,
            )

            # Add to our local past_loops array
            past_loops.append(past_loop_obj)

            # 🐛 Fix: Limit past_loops size to prevent unbounded growth
            MAX_PAST_LOOPS_PER_RUN = 20
            if len(past_loops) > MAX_PAST_LOOPS_PER_RUN:
                past_loops = past_loops[-MAX_PAST_LOOPS_PER_RUN:]
                logger.debug(f"Trimmed past_loops to most recent {MAX_PAST_LOOPS_PER_RUN} entries")

            # Store loop result in Redis if memory_logger is available
            if self.memory_logger is not None:
                try:
                    # Store individual loop result
                    loop_key = f"loop_result:{self.node_id}:{current_loop}"
                    self._store_in_redis(loop_key, loop_result)
                    logger.debug(f"- Stored loop result: {loop_key}")

                    # Store past loops array
                    past_loops_key = f"past_loops:{self.node_id}"
                    self._store_in_redis(past_loops_key, past_loops)
                    logger.debug(f"- Stored past loops: {past_loops_key}")

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
                    logger.debug(f"- Stored result in group for loop {current_loop}")
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
                        logger.debug(f"- Stored final result: {final_key}")
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
                logger.debug(f"- Stored final result: {final_key}")
            except Exception as e:
                logger.error(f"Failed to store final result in Redis: {e}")

        return final_result

    async def _execute_internal_workflow(
        self, original_input: Any, previous_outputs: Dict[str, Any], current_loop: int
    ) -> Optional[Dict[str, Any]]:
        """Execute the internal workflow configuration."""
        from ..orchestrator import Orchestrator

        # Get the original workflow configuration
        original_workflow = self.internal_workflow.copy()

        # 🐛 GraphScout Fix: Inject parent orchestrator's agents for GraphScout discovery
        # If the internal workflow has a GraphScout agent, it needs access to all agents
        # from the parent orchestrator to discover routing candidates
        if hasattr(self, "_parent_agents") and self._parent_agents:
            # Merge parent agents with internal workflow agents
            internal_agents = original_workflow.get("agents", [])
            internal_agent_ids = {
                agent["id"] for agent in internal_agents if isinstance(agent, dict)
            }

            # Add parent agents that aren't already in internal workflow
            for parent_agent in self._parent_agents:
                if (
                    isinstance(parent_agent, dict)
                    and parent_agent.get("id") not in internal_agent_ids
                ):
                    internal_agents.append(parent_agent)

            original_workflow["agents"] = internal_agents
            logger.debug(
                f"LoopNode: Merged {len(self._parent_agents)} parent agents for GraphScout visibility"
            )

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

        # DEBUG: Log the orchestrator config before creating temp file
        orchestrator_agents = original_workflow.get("orchestrator", {}).get("agents", [])
        logger.info(f"🔍 DEBUG: Internal workflow orchestrator.agents BEFORE temp file: {orchestrator_agents}")
        logger.debug(f"🔍 DEBUG: Full orchestrator config: {original_workflow.get('orchestrator', {})}")
        
        # Create temporary workflow file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(original_workflow, f)
            temp_file = f.name
            logger.info(f"🔍 DEBUG: Wrote temp workflow file: {temp_file}")

        try:
            # Create orchestrator for internal workflow
            orchestrator = Orchestrator(temp_file)
            logger.info(f"🔍 DEBUG: Orchestrator created with queue: {orchestrator.orchestrator_cfg.get('agents', [])}")

            # Use parent's memory logger to maintain consistency
            if self.memory_logger is not None:
                # Close the orphaned memory logger created by Orchestrator.__init__
                # to prevent connection pool exhaustion
                if hasattr(orchestrator.memory, "close"):
                    try:
                        orchestrator.memory.close()
                    except Exception as e:
                        logger.debug(f"Failed to close orphaned memory logger: {e}")

                orchestrator.memory = self.memory_logger
                orchestrator.fork_manager.redis = self.memory_logger.redis  # Fixed attribute name

            # ✅ CRITICAL FIX: Ensure template rendering is properly initialized
            # The internal orchestrator needs SimplifiedPromptRenderer capabilities
            if not hasattr(orchestrator, "render_template"):
                # Initialize SimplifiedPromptRenderer if not already done
                from ..orchestrator.simplified_prompt_rendering import (
                    SimplifiedPromptRenderer,
                )

                SimplifiedPromptRenderer.__init__(orchestrator)

            # Create a safe version of previous_outputs to prevent circular references
            # BUT preserve important loop context for agents to see previous results
            safe_previous_outputs = self._create_safe_result_with_context(previous_outputs)

            # Use the actual current loop number from the loop iteration
            current_loop_number = current_loop

            # Prepare input with past_loops context AND loop_number
            # Build dynamic past_loops_metadata using user-defined fields
            dynamic_metadata = {}
            past_loops_data = cast(List[PastLoopMetadata], previous_outputs.get("past_loops", []))

            for field_name in self.past_loops_metadata.keys():
                if field_name in ["insights", "improvements", "mistakes"]:
                    # Extract from cognitive extraction
                    dynamic_metadata[field_name] = self._extract_metadata_field(
                        field_name, past_loops_data
                    )
                else:
                    # For other fields, extract from past loop metadata if available
                    if past_loops_data:
                        last_loop = past_loops_data[-1]
                        value = last_loop.get(field_name, f"No {field_name} available")
                        dynamic_metadata[field_name] = str(value)
                    else:
                        dynamic_metadata[field_name] = f"No {field_name} available"

            # Ensure input is passed as a simple string for template rendering
            simple_input = original_input
            if isinstance(original_input, dict) and "input" in original_input:
                simple_input = original_input["input"]

            workflow_input = {
                "input": simple_input,  # Pass simple string input for template rendering
                "previous_outputs": safe_previous_outputs,
                "loop_number": current_loop_number,
                "past_loops_metadata": dynamic_metadata,
            }

            # DEBUG: Log the input being passed to agents
            logger.debug(f"LoopNode original_input: {original_input}")
            logger.debug(f"LoopNode simple_input: {simple_input}")
            logger.debug(f"LoopNode workflow_input keys: {list(workflow_input.keys())}")

            # Execute workflow with return_logs=True to get full logs for processing
            # Get the ORCHESTRATOR's execution sequence, not all agent definitions
            # (since some agents may be defined for GraphScout routing but not executed)
            orchestrator_cfg = self.internal_workflow.get("orchestrator", {})
            agent_sequence = orchestrator_cfg.get("agents", [])
            # If agents is a simple list of strings, use as-is. If it's dicts, extract IDs
            if agent_sequence and isinstance(agent_sequence[0], dict):
                agent_sequence = [agent.get("id") for agent in agent_sequence]
            logger.debug(
                f"About to execute internal workflow with {len(agent_sequence)} agents in execution sequence"
            )
            logger.debug(f"Full agent sequence: {agent_sequence}")

            try:
                logs = await orchestrator.run(workflow_input, return_logs=True)
                logger.debug(f"Internal workflow execution completed with {len(logs)} log entries")

                # Debug which agents actually executed
                executed_sequence = []
                for log_entry in logs:
                    if (
                        isinstance(log_entry, dict)
                        and log_entry.get("agent_id")
                        and log_entry.get("agent_id") not in executed_sequence
                    ):
                        executed_sequence.append(log_entry.get("agent_id"))

                logger.debug(f"Actual execution sequence: {executed_sequence}")
                logger.debug(
                    f"Expected vs actual count: {len(agent_sequence)} expected, {len(executed_sequence)} executed"
                )

                # Identify missing agents
                missing_agents = [
                    agent for agent in agent_sequence if agent not in executed_sequence
                ]
                if missing_agents:
                    logger.error(f"CRITICAL: Missing agents from execution: {missing_agents}")
                else:
                    logger.info("All agents executed successfully")

            except Exception as e:
                logger.error(f"CRITICAL: Internal workflow execution failed with exception: {e}")
                logger.error(f"CRITICAL: Exception type: {type(e)}")
                raise

            # Extract actual agent responses from logs - ENHANCED for all execution types
            agents_results: Dict[str, Any] = {}
            executed_agents = []

            # Track extraction statistics for debugging
            extraction_stats: Dict[str, Any] = {
                "total_log_entries": len(logs),
                "agent_entries": 0,
                "successful_extractions": 0,
                "extraction_methods": {},
            }

            for log_entry in logs:
                if isinstance(log_entry, dict) and log_entry.get("event_type") == "MetaReport":
                    continue  # Skip meta report

                if isinstance(log_entry, dict):
                    agent_id = log_entry.get("agent_id")
                    if agent_id:
                        executed_agents.append(agent_id)
                        extraction_stats["agent_entries"] += 1

                        # ENHANCED: Multiple extraction strategies for different agent execution types
                        result_found = False
                        extraction_method = None

                        # Strategy 1: Standard payload.result (for most agents)
                        if not result_found and "payload" in log_entry:
                            payload = log_entry["payload"]
                            if "result" in payload:
                                agents_results[agent_id] = payload["result"]
                                result_found = True
                                extraction_method = "payload.result"

                        # Strategy 2: Check if the log entry itself contains result data
                        if not result_found and "result" in log_entry:
                            agents_results[agent_id] = log_entry["result"]
                            result_found = True
                            extraction_method = "direct_result"

                        # Strategy 3: Extract from structured log content (for embedded results)
                        if not result_found:
                            # Parse the full log entry content for embedded data structures
                            log_content = str(log_entry)

                            # Look for JSON-like structures containing our agent
                            if f'"{agent_id}":' in log_content and '"response":' in log_content:
                                try:
                                    # Try to extract the JSON structure
                                    import json
                                    import re

                                    # Look for the pattern: "agent_id": {"response": "...", ...}
                                    pattern = f'"{re.escape(agent_id)}":\\s*\\{{[^}}]+\\}}'
                                    match = re.search(pattern, log_content)

                                    if match:
                                        agent_data_str = "{" + match.group(0) + "}"
                                        # Clean up the string to make it valid JSON
                                        agent_data_str = agent_data_str.replace(
                                            f'"{agent_id}":', f'"{agent_id}":'
                                        )
                                        try:
                                            agent_data = json.loads(agent_data_str)
                                            if agent_id in agent_data:
                                                agents_results[agent_id] = agent_data[agent_id]
                                                result_found = True
                                                extraction_method = "embedded_json"
                                        except json.JSONDecodeError:
                                            pass
                                except Exception as e:
                                    logger.debug(
                                        f"Failed to parse embedded JSON for {agent_id}: {e}"
                                    )

                        # Strategy 4: For LocalLLM agents, check for response/content patterns in log entry
                        if not result_found and isinstance(log_entry, dict):
                            potential_response = None

                            # Check common response patterns
                            if "response" in log_entry:
                                potential_response = {"response": log_entry["response"]}
                            elif "content" in log_entry:
                                potential_response = {"response": log_entry["content"]}
                            elif "output" in log_entry:
                                potential_response = {"response": log_entry["output"]}
                            # Check nested payload structures
                            elif "payload" in log_entry and isinstance(log_entry["payload"], dict):
                                payload = log_entry["payload"]
                                if "response" in payload:
                                    potential_response = {"response": payload["response"]}
                                elif "content" in payload:
                                    potential_response = {"response": payload["content"]}
                                elif "output" in payload:
                                    potential_response = {"response": payload["output"]}

                            if potential_response:
                                agents_results[agent_id] = potential_response
                                result_found = True
                                extraction_method = "response_pattern"

                        # Strategy 5: Search for agent data in the entire log structure
                        if not result_found:
                            # Convert entire log entry to string and search for response patterns
                            full_content = str(log_entry)

                            # Look for common score patterns that indicate this agent has useful data
                            score_indicators = [
                                "AGREEMENT_SCORE:",
                                "SCORE:",
                                "score:",
                                "Score:",
                                "RATING:",
                                "rating:",
                            ]
                            for indicator in score_indicators:
                                if indicator in full_content and agent_id in full_content:
                                    # Create a basic response structure with the content
                                    agents_results[agent_id] = {"response": full_content}
                                    result_found = True
                                    extraction_method = "content_search"
                                    break

                        # Track extraction statistics
                        if result_found:
                            extraction_stats["successful_extractions"] += 1
                            extraction_stats["extraction_methods"][extraction_method] = (
                                extraction_stats["extraction_methods"].get(extraction_method, 0) + 1
                            )
                            logger.debug(
                                f"✅ Extracted result for '{agent_id}' via {extraction_method}"
                            )
                        else:
                            logger.debug(
                                f"❌ No result found for '{agent_id}' - Available keys: {list(log_entry.keys())}"
                            )
                            # Log a sample of the log entry for debugging
                            sample_content = (
                                str(log_entry)[:500] + "..."
                                if len(str(log_entry)) > 500
                                else str(log_entry)
                            )
                            logger.debug(f"   Sample content: {sample_content}")

            logger.debug(f"Agents that actually executed: {executed_agents}")
            logger.debug(f"Agents with results: {list(agents_results.keys())}")
            logger.debug(f"Extraction statistics: {extraction_stats}")

            # Generic debugging: Check for any agents that might contain scores
            score_patterns = ["AGREEMENT_SCORE", "SCORE:", "score:", "Score:"]
            potential_scoring_agents = []

            for agent_id, agent_result in agents_results.items():
                if isinstance(agent_result, dict) and "response" in agent_result:
                    response_text = str(agent_result["response"])
                    for pattern in score_patterns:
                        if pattern in response_text:
                            potential_scoring_agents.append(agent_id)
                            logger.info(
                                f"Found potential scoring agent '{agent_id}' with pattern '{pattern}'"
                            )
                        logger.debug(f"{agent_id} response: {response_text[:200]}...")
                        break

            if potential_scoring_agents:
                logger.debug(f"Potential scoring agents found: {potential_scoring_agents}")
            else:
                logger.debug("No agents found with score patterns!")
                logger.debug(f"All executed agents: {executed_agents}")
                logger.debug(
                    f"Expected agents: {[agent.get('id') for agent in self.internal_workflow.get('agents', [])]}"
                )

                # Show sample responses to understand format
                for agent_id, agent_result in list(agents_results.items())[
                    :3
                ]:  # Show first 3 agents
                    if isinstance(agent_result, dict) and "response" in agent_result:
                        logger.debug(
                            f"Sample response from '{agent_id}': {str(agent_result['response'])[:100]}..."
                        )

            # Store agent results in Redis
            for agent_id, result in agents_results.items():
                # Store agent result in Redis
                result_key = f"agent_result:{agent_id}:{current_loop_number}"
                self._store_in_redis(result_key, result)

                # Store in Redis hash for tracking
                group_key = f"agent_results:{self.node_id}:{current_loop_number}"
                self._store_in_redis_hash(group_key, agent_id, result)

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

    def _try_boolean_scoring(self, result: Dict[str, Any]) -> Optional[float]:
        """
        Try to extract boolean evaluations and calculate score.

        Args:
            result: Agent execution results

        Returns:
            Calculated score or None if no boolean evaluations found
        """
        if not self.score_calculator:
            logger.debug(
                f"LoopNode '{self.node_id}': No score_calculator configured (scoring preset not set)"
            )
            return None

        logger.info(
            f"LoopNode '{self.node_id}': Attempting boolean score extraction from {len(result)} agents"
        )

        # Look for boolean evaluation structure in agent responses
        for agent_id, agent_result in result.items():
            if not isinstance(agent_result, dict):
                logger.debug(f"  - Agent '{agent_id}': Not a dict, skipping")
                continue

            logger.debug(f"  - Agent '{agent_id}': Checking for boolean evaluations...")

            # Check for direct boolean_evaluations key (from PlanValidator)
            if "boolean_evaluations" in agent_result:
                boolean_evals = agent_result["boolean_evaluations"]
                logger.info(f"  - Agent '{agent_id}': Found boolean_evaluations field")

                if isinstance(boolean_evals, dict) and self._is_valid_boolean_structure(
                    boolean_evals
                ):
                    try:
                        score_result = self.score_calculator.calculate(boolean_evals)
                        logger.info(
                            f"✅ Boolean evaluations from '{agent_id}': "
                            f"{score_result['passed_count']}/{score_result['total_criteria']} passed, "
                            f"score={score_result['score']:.4f}"
                        )
                        return float(score_result["score"])
                    except Exception as e:
                        logger.error(
                            f"Failed to calculate boolean score from '{agent_id}': {e}",
                            exc_info=True,
                        )
                        continue
                else:
                    logger.warning(f"  - Agent '{agent_id}': boolean_evaluations invalid structure")

            # Check for validation_score (which might be from boolean scoring)
            if "validation_score" in agent_result and "boolean_evaluations" in agent_result:
                logger.info(f"  - Agent '{agent_id}': Found validation_score field")
                try:
                    score = float(agent_result["validation_score"])
                    logger.info(f"✅ Using validation_score from '{agent_id}': {score:.4f}")
                    return score
                except (ValueError, TypeError) as e:
                    logger.warning(f"  - Agent '{agent_id}': Invalid validation_score: {e}")
                    continue

            # Try to parse boolean structure from response text
            if "response" in agent_result:
                response_text = str(agent_result["response"])
                logger.debug(
                    f"  - Agent '{agent_id}': Checking response text ({len(response_text)} chars)..."
                )

                boolean_evals = self._extract_boolean_from_text(response_text)
                if boolean_evals and self._is_valid_boolean_structure(boolean_evals):
                    try:
                        score_result = self.score_calculator.calculate(boolean_evals)
                        logger.info(
                            f"✅ Boolean evaluations from '{agent_id}' response text: "
                            f"{score_result['passed_count']}/{score_result['total_criteria']} passed, "
                            f"score={score_result['score']:.4f}"
                        )
                        return float(score_result["score"])
                    except Exception as e:
                        logger.debug(f"  - Failed to parse boolean from '{agent_id}' response: {e}")
                        continue
                else:
                    logger.debug(f"  - Agent '{agent_id}': No valid boolean structure in response")

        logger.warning(
            f"LoopNode '{self.node_id}': ❌ No valid boolean evaluations found in any agent"
        )
        return None

    def _is_valid_boolean_structure(self, data: Any) -> bool:
        """
        Check if data contains valid boolean evaluation structure.

        Args:
            data: Data to check

        Returns:
            True if valid boolean structure
        """
        if not isinstance(data, dict):
            return False

        expected_dimensions = ["completeness", "efficiency", "safety", "coherence"]
        found_valid = 0

        for dimension in expected_dimensions:
            if dimension in data and isinstance(data[dimension], dict):
                dim_data = data[dimension]
                # Check if it has boolean values
                if any(isinstance(v, bool) for v in dim_data.values()):
                    found_valid += 1

        return found_valid >= 2

    def _extract_boolean_from_text(self, text: str) -> Optional[Dict[str, Dict[str, bool]]]:
        """
        Extract boolean evaluations from text.

        🐛 Fix: Normalize Python dict syntax to JSON before parsing

        Args:
            text: Text to parse

        Returns:
            Boolean evaluations dict or None
        """
        try:
            # Try to extract JSON
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)

                # 🐛 Normalize Python syntax to JSON (same fix as llm_agents.py)
                json_text = re.sub(r"\bTrue\b", "true", json_text)
                json_text = re.sub(r"\bFalse\b", "false", json_text)
                json_text = re.sub(r"\bNone\b", "null", json_text)
                json_text = json_text.replace("'", '"')

                data = json.loads(json_text)

                # 🐛 CRITICAL FIX: Convert UPPERCASE keys to lowercase
                # LLMs return {"COMPLETENESS": ...} but we need {"completeness": ...}
                if isinstance(data, dict):
                    normalized_data: Dict[str, Dict[str, bool]] = {}
                    for key, value in data.items():
                        normalized_key = key.lower()
                        if isinstance(value, dict):
                            # Normalize nested dict (keep snake_case)
                            normalized_data[normalized_key] = {k: v for k, v in value.items()}
                        else:
                            normalized_data[normalized_key] = value
                    data = normalized_data
                    logger.debug(f"Normalized keys to lowercase: {list(data.keys())}")

                if self._is_valid_boolean_structure(data):
                    logger.info(f"✅ Successfully extracted boolean evaluations from text")
                    return cast(Dict[str, Dict[str, bool]], data)
                else:
                    logger.debug(f"❌ Invalid boolean structure. Keys found: {list(data.keys())}")

        except json.JSONDecodeError as e:
            logger.debug(f"JSON parse failed: {e}")
        except Exception as e:
            logger.error(f"Boolean extraction exception: {e}", exc_info=True)

        return None

    async def _extract_score(self, result: Dict[str, Any]) -> float:
        """Extract score from result using configured extraction strategies."""
        if not result:
            return 0.0

        # DEBUG: Log what data we're trying to extract from
        logger.debug(f"Score extraction called with {len(result)} agents")
        for agent_id, agent_result in result.items():
            if isinstance(agent_result, dict) and "response" in agent_result:
                response_text = str(agent_result["response"])
                response_preview = (
                    response_text[:100] + "..." if len(response_text) > 100 else response_text
                )
                logger.debug(f"Agent '{agent_id}' response preview: {response_preview}")

        # PRIORITY 0: Try boolean scoring if configured
        if self.score_calculator:
            boolean_score = self._try_boolean_scoring(result)
            if boolean_score is not None:
                logger.info(
                    f"✅ Using boolean scoring: {boolean_score:.4f} (preset: {self.scoring_preset})"
                )
                return boolean_score
            else:
                logger.debug(
                    "Boolean scoring attempted but no valid evaluations found, falling back to legacy"
                )

        strategies = self.score_extraction_config.get("strategies", [])

        # PRIORITY 1: Check for high-priority agents first (configurable)
        for priority_agent in self.high_priority_agents:
            if priority_agent in result:
                agent_result = result[priority_agent]
                if isinstance(agent_result, dict) and "response" in agent_result:
                    response_text = str(agent_result["response"])
                    logger.info(
                        f"🔍 Checking high-priority agent '{priority_agent}': {response_text[:100]}..."
                    )

                    # Collect all patterns from the configuration
                    all_patterns = []
                    for strategy in strategies:
                        if strategy.get("type") == "pattern" and "patterns" in strategy:
                            patterns = strategy["patterns"]
                            if isinstance(patterns, list):
                                all_patterns.extend(patterns)

                    # If no patterns in config, use basic fallback patterns
                    if not all_patterns:
                        all_patterns = [
                            r"AGREEMENT_SCORE:\s*([0-9.]+)",
                            r"Agreement Score:\s*([0-9.]+)",
                            r"AGREEMENT_SCORE\s*([0-9.]+)",
                            r"Score:\s*([0-9.]+)",
                            r"SCORE:\s*([0-9.]+)",
                        ]

                    score_patterns = all_patterns

                    for score_pattern in score_patterns:
                        match = re.search(score_pattern, response_text)
                        if match and match.group(1):
                            try:
                                score = float(match.group(1))
                                logger.info(
                                    f"✅ Found score {score} from high-priority agent '{priority_agent}' using pattern: {score_pattern}"
                                )
                                return score
                            except (ValueError, TypeError):
                                continue

                    logger.warning(
                        f"❌ High-priority agent '{priority_agent}' found but no score extracted from: {response_text}"
                    )

        # PRIORITY 2: Use configured extraction strategies
        for strategy in strategies:
            if not isinstance(strategy, dict):
                continue  # type: ignore [unreachable]

            strategy_type = strategy.get("type")

            if strategy_type == "direct_key":
                key = str(strategy.get("key", ""))
                if key in result:
                    value = result[key]
                    if self._is_valid_value(value):
                        logger.info(f"✅ Found score {value} via direct_key strategy")
                        return float(value)  # Now type-safe due to TypeGuard

            elif strategy_type == "pattern":
                patterns = strategy.get("patterns", [])
                if not isinstance(patterns, list):
                    continue

                for pattern in patterns:
                    if not isinstance(pattern, str):
                        continue  # type: ignore [unreachable]

                    logger.debug(f"🔍 Trying pattern: {pattern}")

                    # Look deeper into agent result structures
                    for agent_id, agent_result in result.items():
                        # Check direct string values
                        if isinstance(agent_result, str):
                            match = re.search(pattern, agent_result)
                            if match and match.group(1):
                                try:
                                    score = float(match.group(1))
                                    logger.info(
                                        f"✅ Found score {score} in {agent_id} (direct string) using pattern: {pattern}"
                                    )
                                    return score
                                except (ValueError, TypeError):
                                    continue

                        # Check nested response fields in agent dictionaries
                        elif isinstance(agent_result, dict):
                            for key in ["response", "result", "output", "data"]:
                                if key in agent_result and isinstance(agent_result[key], str):
                                    text_content = agent_result[key]
                                    logger.debug(
                                        f"🔍 Searching in {agent_id}.{key}: {repr(text_content[:200])}"
                                    )
                                    match = re.search(pattern, text_content)
                                    if match:
                                        try:
                                            score = float(match.group(1))
                                            logger.debug(f"✅ Matched text: '{text_content[:200]}'")
                                            logger.info(
                                                f"✅ Found score {score} in {agent_id}.{key} using pattern: {pattern}"
                                            )
                                            return score
                                        except (ValueError, TypeError, IndexError):
                                            # Pattern might not have a capture group or couldn't convert to float
                                            continue
                                    else:
                                        if (
                                            "agreement" in agent_id.lower()
                                            or "AGREEMENT_SCORE" in text_content
                                        ):
                                            logger.debug(
                                                f"❌ No match for pattern '{pattern}' in {agent_id}.{key}: '{text_content[:100]}'"
                                            )

            elif strategy_type == "agent_key":
                agents = strategy.get("agents", [])
                key = str(strategy.get("key", "response"))
                logger.debug(f"🔍 Trying agent_key strategy for agents: {agents}, key: {key}")

                for agent_name in agents:
                    if agent_name in result:
                        logger.debug(f"🔍 Found agent '{agent_name}' in results")
                        agent_result = result[agent_name]
                        if isinstance(agent_result, dict) and key in agent_result:
                            response_text = str(agent_result[key])
                            logger.debug(f"🔍 Agent '{agent_name}' {key}: '{response_text[:100]}'")
                            # Use configured patterns for agent_key strategy
                            agent_score_patterns = []
                            for strategy in strategies:
                                if strategy.get("type") == "pattern" and "patterns" in strategy:
                                    patterns = strategy["patterns"]
                                    if isinstance(patterns, list):
                                        agent_score_patterns.extend(patterns)

                            # If no patterns in config, use basic fallback patterns
                            if not agent_score_patterns:
                                agent_score_patterns = [
                                    r"AGREEMENT_SCORE:\s*([0-9.]+)",
                                    r"Agreement Score:\s*([0-9.]+)",
                                    r"SCORE:\s*([0-9.]+)",
                                    r"Score:\s*([0-9.]+)",
                                ]

                            for score_pattern in agent_score_patterns:
                                score_match = re.search(score_pattern, response_text)
                                if score_match:
                                    try:
                                        score = float(score_match.group(1))
                                        logger.info(
                                            f"✅ Found score {score} in agent_key strategy from {agent_name} using pattern: {score_pattern}"
                                        )
                                        return score
                                    except (ValueError, TypeError):
                                        continue
                    else:
                        logger.debug(
                            f"🔍 Agent '{agent_name}' not found in results. Available agents: {list(result.keys())}"
                        )

        # PRIORITY 3: Fallback to embedding computation ONLY if no explicit scores found
        # AND this appears to be a cognitive debate scenario without explicit moderators
        agent_ids = list(result.keys())

        # Check if we have any explicit score agents that might have failed
        has_score_agents = any(agent_id in result for agent_id in self.high_priority_agents)

        if has_score_agents:
            logger.warning(
                "❌ Score agents present but no scores extracted. NOT using embedding fallback to avoid overriding explicit scores."
            )
            return 0.0

        # Only use embedding fallback for pure cognitive debates without score moderators
        cognitive_agents = [
            aid
            for aid in agent_ids
            if any(
                word in aid.lower()
                for word in ["progressive", "conservative", "realist", "purist"]
                # Note: "agreement" excluded to avoid confusion with agreement_moderator
            )
        ]

        if len(cognitive_agents) >= 2:
            logger.info(
                f"Detected cognitive debate with agents: {cognitive_agents} (no score moderators found)"
            )
            logger.info("Using embedding-based agreement computation as final fallback")
            try:
                # Run agreement computation directly since we're already in async context
                agreement_score = await self._compute_agreement_score(result)
                logger.info(f"✅ Computed fallback agreement score: {agreement_score}")
                return agreement_score

            except Exception as e:
                logger.error(f"Failed to compute agreement score: {e}")
                return 0.0

        logger.warning("❌ No valid score extraction method succeeded")
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

    async def _compute_agreement_score(self, result: dict[str, Any]) -> float:
        """
        Compute agreement score between agent responses using embeddings and cosine similarity.

        This function replaces the text-based agreement_finder agent with proper
        embedding-based similarity calculation.

        Args:
            result: Dictionary containing agent responses

        Returns:
            float: Agreement score between 0.0 and 1.0
        """
        try:
            # Extract responses from all agents
            agent_responses: List[Dict[str, Any]] = []
            for agent_id, agent_result in result.items():
                if isinstance(agent_result, dict):
                    # Look for response content in common fields
                    response_text = None
                    for field in ["response", "result", "output", "content", "answer"]:
                        if field in agent_result and agent_result[field]:
                            response_text = str(agent_result[field])
                            break

                    if response_text:
                        agent_responses.append(
                            {"agent_id": agent_id, "response": response_text, "embedding": None}
                        )
                elif isinstance(agent_result, str) and agent_result.strip():
                    # Handle direct string responses
                    agent_responses.append(
                        {"agent_id": agent_id, "response": agent_result, "embedding": None}
                    )

            # Need at least 2 responses to compute agreement
            if len(agent_responses) < 2:
                logger.warning(
                    f"Only {len(agent_responses)} agent responses found, need at least 2 for agreement"
                )
                return 0.0

            # Generate embeddings for each response

            embedder = get_embedder()

            for agent_data in agent_responses:
                try:
                    response_text = agent_data["response"]
                    if response_text and isinstance(response_text, str):
                        embedding = await embedder.encode(response_text)
                        agent_data["embedding"] = (
                            np.array(embedding) if embedding is not None else None
                        )
                    else:
                        agent_data["embedding"] = None
                except Exception as e:
                    logger.warning(
                        f"Failed to generate embedding for {agent_data['agent_id']}: {e}"
                    )
                    agent_data["embedding"] = None

            # Filter out responses without valid embeddings
            valid_embeddings = []
            valid_agents = []
            for agent_data in agent_responses:
                if agent_data["embedding"] is not None and len(agent_data["embedding"]) > 0:
                    valid_embeddings.append(agent_data["embedding"])
                    valid_agents.append(agent_data["agent_id"])

            if len(valid_embeddings) < 2:
                logger.warning(f"Only {len(valid_embeddings)} valid embeddings, returning 0.0")
                return 0.0

            # Compute pairwise cosine similarities
            from sklearn.metrics.pairwise import (  # type: ignore[import-untyped]
                cosine_similarity,
            )

            embeddings_matrix = np.array(valid_embeddings)
            similarity_matrix = cosine_similarity(embeddings_matrix)

            # Calculate mean similarity (excluding diagonal)
            n = len(similarity_matrix)
            if n < 2:
                return 0.0

            # Sum all similarities except diagonal, then normalize
            total_similarity = np.sum(similarity_matrix) - np.trace(similarity_matrix)
            max_pairs = n * (n - 1)  # All pairs excluding self-similarity

            if max_pairs == 0:
                return 0.0

            mean_agreement = total_similarity / max_pairs

            # Ensure score is between 0 and 1
            agreement_score = max(0.0, min(1.0, float(mean_agreement)))

            logger.info(
                f"Computed agreement score: {agreement_score:.3f} from {len(valid_agents)} agents: {valid_agents}"
            )

            return agreement_score

        except Exception as e:
            logger.error(f"Error computing agreement score: {e}")
            return 0.0

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

        # ✅ FIX: Extract insights from ALL agent responses, not just prioritized ones
        for agent_id, agent_result in result.items():
            if not isinstance(agent_result, (str, dict)):
                continue

            # ✅ FIX: Get text from proper structure - look in response field for LLM agents
            texts_to_analyze = []

            if isinstance(agent_result, str):
                texts_to_analyze.append(agent_result)
            elif isinstance(agent_result, dict):
                # Look for response content in common fields
                for field in ["response", "result", "output", "data"]:
                    if field in agent_result and isinstance(agent_result[field], str):
                        texts_to_analyze.append(agent_result[field])

                # Fallback: convert entire dict to string
                if not texts_to_analyze:
                    texts_to_analyze.append(str(agent_result))

            # Apply extraction patterns to all found text content
            for text in texts_to_analyze:
                if not text or len(text) < 20:  # Skip very short content
                    continue

                # ✅ FIX: Apply patterns for ALL categories to ALL agents (not just prioritized)
                for category in ["insights", "improvements", "mistakes"]:
                    cat_key = cast(CategoryType, category)
                    patterns = extract_patterns.get(category, [])
                    if not isinstance(patterns, list):
                        continue  # type: ignore[unreachable]

                    for pattern in patterns:
                        if not isinstance(pattern, str):
                            continue  # type: ignore[unreachable]

                        try:
                            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                            for match in matches:
                                if len(match.groups()) > 0:
                                    insight = match.group(1).strip()
                                    if insight and len(insight) > 10:  # Minimum length threshold
                                        # Clean up the insight
                                        insight = re.sub(
                                            r"\s+", " ", insight
                                        )  # Normalize whitespace
                                        if len(insight) <= 200:  # Reasonable length limit
                                            extracted[cat_key].append(insight)
                                            logger.debug(
                                                f"✅ Extracted {category} from {agent_id}: {insight[:50]}..."
                                            )
                        except re.error as e:
                            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                            continue

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
        # 🐛 FIX Bug #9: Do NOT include full result in template to prevent trace bloat
        # Only include summary data that won't cause exponential growth
        template_context = {
            "loop_number": loop_number,
            "score": score,
            "reasoning_quality": reasoning_quality,
            "convergence_trend": convergence_trend,
            "timestamp": datetime.now().isoformat(),
            # REMOVED: "result": safe_result - causes O(2^N) data growth in traces
            "input": safe_input,
            "insights": cognitive_insights.get("insights", ""),
            "improvements": cognitive_insights.get("improvements", ""),
            "mistakes": cognitive_insights.get("mistakes", ""),
            # REMOVED: "previous_outputs": safe_result - not needed in metadata
        }

        # ✅ FIX: Add helper functions to template context for LoopNode metadata rendering
        try:
            # Create a payload-like structure for helper functions
            # 🐛 FIX Bug #9: Don't include full result to prevent trace bloat
            helper_payload = {
                "input": safe_input,
                "previous_outputs": {},  # Empty to prevent bloat - templates should use template_context instead
                "loop_number": loop_number,
            }

            # Add helper functions using the same approach as execution engine
            from ..orchestrator.simplified_prompt_rendering import (
                SimplifiedPromptRenderer,
            )

            renderer = SimplifiedPromptRenderer()
            helper_functions = renderer._get_template_helper_functions(helper_payload)
            template_context.update(helper_functions)

            logger.debug(
                f"- Added {len(helper_functions)} helper functions to LoopNode template context"
            )
            logger.debug(f"- Helper payload input: {helper_payload.get('input', 'MISSING')}")
            logger.debug(f"- Template context keys: {list(template_context.keys())}")
        except Exception as e:
            logger.warning(f"Failed to add helper functions to LoopNode template context: {e}")
            # Continue without helper functions - fallback gracefully

        # ✅ FIX: Create past loop object using user-defined metadata template
        past_loop_obj: PastLoopMetadata = {}

        # Render each metadata field using the user-defined templates
        for field_name, template_str in self.past_loops_metadata.items():
            try:
                logger.debug(f"- Rendering field '{field_name}' with template: {template_str}")
                template = Template(template_str)
                rendered_value = template.render(template_context)
                past_loop_obj[field_name] = rendered_value
                logger.debug(f"- Rendered metadata field '{field_name}': {rendered_value[:50]}...")
            except Exception as e:
                logger.warning(
                    f"Failed to render metadata field '{field_name}' with template '{template_str}': {e}"
                )
                # Fallback to simple value
                if field_name == "loop_number":
                    past_loop_obj[field_name] = loop_number
                elif field_name == "score":
                    past_loop_obj[field_name] = score
                elif field_name == "timestamp":
                    past_loop_obj[field_name] = datetime.now().isoformat()
                elif field_name in cognitive_insights:
                    past_loop_obj[field_name] = cognitive_insights[field_name]
                else:
                    past_loop_obj[field_name] = f"Error rendering {field_name}"  # type: ignore[unreachable]

        # Always ensure we have the basic required fields for compatibility
        past_loop_obj.setdefault("loop_number", loop_number)
        past_loop_obj.setdefault("score", score)
        past_loop_obj.setdefault("timestamp", datetime.now().isoformat())
        # 🐛 Bug #9 Fix: DO NOT add result field - it causes exponential trace bloat
        # past_loop_obj.setdefault("result", safe_result)  # REMOVED - was causing O(2^N) growth

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

    def _create_safe_result_with_context(self, result: Any) -> Any:
        """
        Create a safe, serializable version of the result that preserves important loop context.

        This version preserves agent responses and past_loops data needed for context
        in subsequent loop iterations, unlike _create_safe_result which truncates everything.
        """

        def _make_safe_with_context(
            obj: Any, seen: Optional[set[int]] = None, depth: int = 0
        ) -> Any:
            if seen is None:
                seen = set()

            # Prevent infinite depth
            if depth > 10:
                return "<max_depth_reached>"

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
                    return [_make_safe_with_context(item, seen.copy(), depth + 1) for item in obj]

                if isinstance(obj, dict):
                    safe_dict = {}
                    for key, value in obj.items():
                        key_str = str(key)

                        # Always preserve past_loops for context
                        if key_str == "past_loops":
                            safe_dict[key_str] = _make_safe_with_context(
                                value, seen.copy(), depth + 1
                            )

                        # Preserve agent responses for cognitive debate context
                        elif any(
                            agent_type in key_str.lower()
                            for agent_type in [
                                "progressive",
                                "conservative",
                                "realist",
                                "purist",
                                "agreement",
                            ]
                        ):
                            if isinstance(value, dict):
                                # For agent dictionaries, preserve response but limit size
                                agent_dict = {}
                                for agent_key, agent_value in value.items():
                                    if agent_key == "response":
                                        # Preserve full response for context but limit to reasonable size
                                        response_str = str(agent_value)
                                        if len(response_str) > 2000:
                                            agent_dict[agent_key] = (
                                                response_str[:2000] + "...<truncated_for_safety>"
                                            )
                                        else:
                                            agent_dict[agent_key] = response_str
                                    elif agent_key in ["confidence", "internal_reasoning"]:
                                        # Preserve other important fields
                                        agent_dict[agent_key] = (
                                            str(agent_value)[:500]
                                            if len(str(agent_value)) > 500
                                            else agent_value
                                        )
                                    # Skip large metadata like _metrics, formatted_prompt
                                safe_dict[key_str] = agent_dict
                            else:
                                safe_dict[key_str] = (
                                    str(value)[:1000] if len(str(value)) > 1000 else value
                                )

                        # Skip problematic circular references but preserve simple values
                        elif key_str not in ("previous_outputs", "payload"):
                            if isinstance(value, (str, int, float, bool, type(None))):
                                safe_dict[key_str] = value
                            elif isinstance(value, (dict, list)):
                                safe_dict[key_str] = _make_safe_with_context(
                                    value, seen.copy(), depth + 1
                                )
                            else:
                                # Convert complex objects to strings with size limit
                                str_value = str(value)
                                if len(str_value) > 500:
                                    safe_dict[key_str] = str_value[:500] + "...<truncated>"
                                else:
                                    safe_dict[key_str] = str_value

                    return safe_dict

                # Convert other objects to strings with size limit
                str_obj = str(obj)
                return str_obj[:1000] + "..." if len(str_obj) > 1000 else str_obj

            finally:
                seen.discard(obj_id)

        return _make_safe_with_context(result)

    async def _clear_loop_cache(self, loop_number: int) -> None:
        """
        Clear Redis cache that might cause response duplication between loop iterations.

        This ensures that agents in subsequent loops don't reuse cached responses
        from previous iterations.
        """
        if self.memory_logger is None:
            return

        try:
            # Clear loop-specific caches
            cache_patterns = [
                f"loop_cache:{self.node_id}:{loop_number}",
                f"loop_cache:{self.node_id}:*",
                f"agent_cache:{self.node_id}:{loop_number}:*",
                f"response_cache:{self.node_id}:{loop_number}:*",
            ]

            for pattern in cache_patterns:
                try:
                    # Use SCAN to find keys matching pattern
                    cursor = 0
                    while True:
                        cursor, keys = self.memory_logger.redis.scan(
                            cursor, match=pattern, count=100
                        )
                        if keys:
                            self.memory_logger.redis.delete(*keys)
                            logger.debug(f"Cleared {len(keys)} cache keys matching {pattern}")
                        if cursor == 0:
                            break
                except Exception as e:
                    logger.warning(f"Failed to clear cache pattern {pattern}: {e}")

        except Exception as e:
            logger.warning(f"Failed to clear loop cache for loop {loop_number}: {e}")

    def _extract_metadata_field(
        self, field: MetadataKey, past_loops: List[PastLoopMetadata], max_entries: int = 5
    ) -> str:
        """Extract metadata field from past loops."""
        values = []
        for loop in reversed(past_loops[-max_entries:]):
            if field in loop and loop[field]:
                values.append(str(loop[field]))
        return " | ".join(values)

    async def _load_past_loops_from_redis(self) -> List[PastLoopMetadata]:
        """
        Load past loops from Redis if available.

        🐛 Fix: Limit past_loops to prevent unbounded growth across runs
        """
        past_loops: List[PastLoopMetadata] = []
        MAX_PAST_LOOPS = 20  # Limit to prevent memory/trace bloat

        if self.memory_logger is not None:
            try:
                past_loops_key = f"past_loops:{self.node_id}"

                # Try to load past loops from Redis
                stored_data = self.memory_logger.get(past_loops_key)
                if stored_data:
                    loaded_loops = json.loads(stored_data)
                    if isinstance(loaded_loops, list):
                        # 🐛 CRITICAL FIX: Limit to most recent N loops
                        if len(loaded_loops) > MAX_PAST_LOOPS:
                            past_loops = loaded_loops[-MAX_PAST_LOOPS:]
                            logger.warning(
                                f"Loaded {len(loaded_loops)} past loops from Redis, "
                                f"trimmed to most recent {MAX_PAST_LOOPS} to prevent bloat"
                            )
                        else:
                            past_loops = loaded_loops
                            logger.info(
                                f"Loaded {len(past_loops)} past loops from Redis for node {self.node_id}"
                            )
                    else:
                        logger.warning(
                            f"Invalid past loops data format in Redis for node {self.node_id}"
                        )
                else:
                    logger.debug(f"No past loops found in Redis for node {self.node_id}")

            except Exception as e:
                logger.error(f"Failed to load past loops from Redis: {e}")
                # Continue with empty past_loops on error

        return past_loops

    def _store_in_redis(self, key: str, value: Any) -> None:
        """Safely store a value in Redis."""
        if self.memory_logger is not None:
            try:
                self.memory_logger.set(key, json.dumps(value))
                logger.debug(f"- Stored in Redis: {key}")
            except Exception as e:
                logger.error(f"Failed to store in Redis: {e}")

    def _store_in_redis_hash(self, hash_key: str, field: str, value: Any) -> None:
        """Safely store a value in a Redis hash."""
        if self.memory_logger is not None:
            try:
                self.memory_logger.hset(hash_key, field, json.dumps(value))
                logger.debug(f"- Stored in Redis hash: {hash_key}[{field}]")
            except Exception as e:
                logger.error(f"Failed to store in Redis hash: {e}")
