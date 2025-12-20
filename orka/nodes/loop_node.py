# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

from __future__ import annotations

import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    cast,
)

from ..memory.redisstack_logger import RedisStackMemoryLogger
from ..scoring import BooleanScoreCalculator
from .base_node import BaseNode
from .loop.boolean_extraction import extract_boolean_from_text, is_valid_boolean_structure
from .loop.config import build_loop_node_config
from .loop.metadata import build_dynamic_metadata
from .loop.internal_workflow_runner import (
    InternalWorkflowRunContext,
    build_loop_workflow_input,
    compile_internal_workflow_config,
    run_internal_workflow_with_temp_yaml,
)
from .loop.log_result_extractor import extract_agent_results_from_logs
from .loop.past_loop_builder import create_past_loop_object
from .loop.persistence import LoopPersistence
from .loop.sanitize import create_safe_result, create_safe_result_with_context
from .loop.score_extractor import LoopScoreExtractor
from .loop.score_utils import normalize_score
from .loop.runner import LoopRunnerDeps, run_loop
from .loop.types import InsightCategory, PastLoopMetadata

logger = logging.getLogger(__name__)


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

        cfg = build_loop_node_config(
            node_id=node_id,
            kwargs=kwargs,
            calculator_cls=BooleanScoreCalculator,  # keep patchable from orka.nodes.loop_node
            logger=logger,
        )

        self.max_loops = cfg.max_loops
        self.score_threshold = cfg.score_threshold
        self.scoring_preset = cfg.scoring_preset
        self.scoring_context = cfg.scoring_context
        self.custom_weights = cfg.custom_weights
        self.score_calculator = cfg.score_calculator
        self.high_priority_agents = cfg.high_priority_agents
        self.score_extraction_config = cfg.score_extraction_config
        self.internal_workflow = cfg.internal_workflow
        self.past_loops_metadata = cfg.past_loops_metadata
        self.cognitive_extraction = cfg.cognitive_extraction
        self.persist_across_runs = cfg.persist_across_runs

        # Extracted persistence/cache logic (keeps Redis key formats stable)
        self._persistence = LoopPersistence(node_id=self.node_id, memory_logger=self.memory_logger)

        # Extracted score extraction logic (keeps behavior stable while shrinking LoopNode)
        self._score_extractor = LoopScoreExtractor(
            node_id=self.node_id,
            score_calculator=self.score_calculator,
            scoring_preset=self.scoring_preset,
            score_extraction_config=self.score_extraction_config,
            high_priority_agents=self.high_priority_agents,
        )

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

        def _build_past_loop_object(loop_number: int, score: float, result: Dict[str, Any]) -> PastLoopMetadata:
            return create_past_loop_object(
                loop_number=loop_number,
                score=score,
                result=result,
                original_input=original_input,
                past_loops_metadata_templates=self.past_loops_metadata,
                cognitive_extraction=self.cognitive_extraction,
                create_safe_result_fn=create_safe_result,
            )

        deps = LoopRunnerDeps(
            execute_internal_workflow=self._execute_internal_workflow,
            extract_score=self._score_extractor.extract_score,
            load_past_loops=self._load_past_loops_from_redis,
            clear_loop_cache=self._clear_loop_cache,
            build_past_loop_object=_build_past_loop_object,
            store_json=self._store_in_redis,
            store_hash_json=self._store_in_redis_hash,
            create_safe_result=self._create_safe_result,
        )

        return await run_loop(
            node_id=self.node_id,
            original_input=original_input,
            original_previous_outputs=original_previous_outputs,
            max_loops=self.max_loops,
            score_threshold=self.score_threshold,
            persist_across_runs=self.persist_across_runs,
            deps=deps,
        )

    async def _execute_internal_workflow(
        self, original_input: Any, previous_outputs: Dict[str, Any], current_loop: int
    ) -> Optional[Dict[str, Any]]:
        """Execute the internal workflow configuration."""
        # Build/compile internal workflow config (GraphScout parent agent merge + orchestrator defaults)
        ctx = InternalWorkflowRunContext(
            node_id=self.node_id,
            internal_workflow=self.internal_workflow,
            past_loops_metadata_templates=self.past_loops_metadata,
            scoring_context=self.scoring_context,
            memory_logger=self.memory_logger,
            parent_agents=getattr(self, "_parent_agents", None),
        )

        workflow_config = compile_internal_workflow_config(ctx)

        # Prepare workflow input (including dynamic past_loops_metadata)
        safe_previous_outputs = self._create_safe_result_with_context(previous_outputs)
        current_loop_number = current_loop

        past_loops_data = cast(List[PastLoopMetadata], previous_outputs.get("past_loops", []))
        dynamic_metadata = build_dynamic_metadata(self.past_loops_metadata, past_loops_data)

        workflow_input = build_loop_workflow_input(
            original_input=original_input,
            previous_outputs_safe=safe_previous_outputs,
            current_loop_number=current_loop_number,
            scoring_context=self.scoring_context,
            dynamic_metadata=dynamic_metadata,
        )

        try:
            logs = await run_internal_workflow_with_temp_yaml(
                workflow_config=workflow_config,
                workflow_input=workflow_input,
                memory_logger=self.memory_logger,
            )

            agents_results, executed_agents, extraction_stats = extract_agent_results_from_logs(logs)
            logger.debug("Agents that actually executed: %s", executed_agents)
            logger.debug("Agents with results: %s", list(agents_results.keys()))
            logger.debug("Extraction statistics: %s", extraction_stats)

            # Store agent results in Redis (unchanged keys)
            for agent_id, result in agents_results.items():
                result_key = f"agent_result:{agent_id}:{current_loop_number}"
                self._store_in_redis(result_key, result)
                group_key = f"agent_results:{self.node_id}:{current_loop_number}"
                self._store_in_redis_hash(group_key, agent_id, result)

            loop_results_key = f"loop_agents:{self.node_id}:{current_loop_number}"
            self._store_in_redis(loop_results_key, agents_results)
            group_key = f"loop_agents:{self.node_id}"
            self._store_in_redis_hash(group_key, str(current_loop_number), agents_results)

            return agents_results
        except Exception as e:
            logger.error("Failed to execute internal workflow: %s", e)
            return None

    def _sync_score_extractor(self) -> None:
        # Tests (and callers) sometimes mutate these fields after __init__.
        # Keep the extracted score component in sync with the LoopNode instance.
        self._score_extractor.score_calculator = self.score_calculator
        self._score_extractor.scoring_preset = self.scoring_preset
        self._score_extractor.score_extraction_config = self.score_extraction_config
        self._score_extractor.high_priority_agents = self.high_priority_agents

    def _is_valid_value(self, value: Any) -> bool:
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
        self._sync_score_extractor()
        return self._score_extractor._try_boolean_scoring(result)

    def _is_valid_boolean_structure(self, data: Any) -> bool:
        return is_valid_boolean_structure(data)

    def _extract_boolean_from_text(self, text: str) -> Optional[Dict[str, Dict[str, bool]]]:
        return extract_boolean_from_text(text)

    async def _extract_score(self, result: Dict[str, Any]) -> float:
        self._sync_score_extractor()
        return await self._score_extractor.extract_score(result)

    def _normalize_score(self, raw: float, pattern: Optional[str] = None, matched_text: Optional[str] = None) -> float:
        return normalize_score(raw, pattern=pattern, matched_text=matched_text)

    async def _compute_agreement_score(self, result: dict[str, Any]) -> float:
        self._sync_score_extractor()
        return await self._score_extractor._compute_agreement_score(result)

    def _extract_nested_path(self, result: dict[str, Any], path: str) -> float | None:
        from .loop.score_utils import extract_nested_path

        return extract_nested_path(result, path)

    def _extract_pattern(self, result: dict[str, Any], patterns: list[str]) -> float | None:
        from .loop.score_utils import extract_pattern

        return extract_pattern(result, patterns)

    def _extract_secondary_metric(
        self, result: dict[str, Any], metric_key: str, default: Any = 0.0
    ) -> Any:
        from .loop.secondary_metrics import extract_secondary_metric

        return extract_secondary_metric(result, metric_key, default=default)

    def _extract_cognitive_insights(
        self, result: Dict[str, Any], max_length: int = 300
    ) -> InsightCategory:
        from .loop.cognitive_extraction import extract_cognitive_insights

        return extract_cognitive_insights(
            result=result,
            cognitive_extraction=self.cognitive_extraction,
            max_length=max_length,
        )

    def _create_past_loop_object(
        self, loop_number: int, score: float, result: Dict[str, Any], original_input: Any
    ) -> PastLoopMetadata:
        # Back-compat private helper: keep name but delegate to extracted implementation.
        return create_past_loop_object(
            loop_number=loop_number,
            score=score,
            result=result,
            original_input=original_input,
            past_loops_metadata_templates=self.past_loops_metadata,
            cognitive_extraction=self.cognitive_extraction,
            create_safe_result_fn=create_safe_result,
        )

    def _create_safe_result(self, result: Any) -> Any:
        return create_safe_result(result)

    def _create_safe_result_with_context(self, result: Any) -> Any:
        return create_safe_result_with_context(result)

    async def _clear_loop_cache(self, loop_number: int) -> None:
        """Clear Redis cache that might cause response duplication between loop iterations."""
        await self._persistence.clear_loop_cache(loop_number)

    async def _load_past_loops_from_redis(self) -> List[PastLoopMetadata]:
        """Load past loops from Redis if available (trimmed to prevent bloat)."""
        return await self._persistence.load_past_loops(max_past_loops=20)

    def _store_in_redis(self, key: str, value: Any) -> None:
        """Safely store a value in Redis."""
        self._persistence.store_json(key, value)

    def _store_in_redis_hash(self, hash_key: str, field: str, value: Any) -> None:
        """Safely store a value in a Redis hash."""
        self._persistence.store_hash_json(hash_key, field, value)
