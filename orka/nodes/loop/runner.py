from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .score_utils import normalize_score
from .types import PastLoopMetadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoopRunnerDeps:
    """Dependency bundle for running the LoopNode core control-flow.

    This keeps LoopNode thin and makes it easier to test/migrate behavior without
    touching orchestration logic.
    """

    execute_internal_workflow: Callable[
        [Any, Dict[str, Any], int], Awaitable[Optional[Dict[str, Any]]]
    ]
    extract_score: Callable[[Dict[str, Any]], Awaitable[float]]
    load_past_loops: Callable[[], Awaitable[List[PastLoopMetadata]]]
    clear_loop_cache: Callable[[int], Awaitable[None]]
    build_past_loop_object: Callable[[int, float, Dict[str, Any]], PastLoopMetadata]
    store_json: Callable[[str, Any], None]
    store_hash_json: Callable[[str, str, Any], None]
    create_safe_result: Callable[[Any], Any]


async def run_loop(
    *,
    node_id: str,
    original_input: Any,
    original_previous_outputs: Dict[str, Any],
    max_loops: int,
    score_threshold: float,
    persist_across_runs: bool,
    deps: LoopRunnerDeps,
) -> Dict[str, Any]:
    """Run LoopNode iterations until threshold met or max_loops reached.

    Mirrors the previous LoopNode._run_impl behavior, but extracted.
    """

    # Create a working copy of previous_outputs to avoid circular references
    loop_previous_outputs = original_previous_outputs.copy()

    # Initialize past_loops - optionally load from Redis if persistence is enabled
    past_loops: List[PastLoopMetadata] = []
    if persist_across_runs:
        past_loops = await deps.load_past_loops()

    # Set past_loops in the working copy once at the beginning
    loop_previous_outputs["past_loops"] = past_loops

    current_loop = 0
    loop_result: Optional[Dict[str, Any]] = None
    score = 0.0

    while current_loop < max_loops:
        current_loop += 1
        logger.info("Loop %s/%s starting", current_loop, max_loops)

        # Clear any Redis cache that might cause response duplication
        await deps.clear_loop_cache(current_loop)

        # Execute internal workflow
        loop_result = await deps.execute_internal_workflow(
            original_input, loop_previous_outputs, current_loop
        )

        if loop_result is None:
            logger.error("Internal workflow execution failed")
            break

        # Extract score
        score = await deps.extract_score(loop_result)

        # Safety: ensure final score is normalized and clamped to [0.0, 1.0]
        normalized_score = normalize_score(score)
        if abs(normalized_score - float(score)) > 1e-9:
            logger.info("Normalized final extracted score: raw=%s -> normalized=%s", score, normalized_score)
        score = normalized_score

        # Create past_loop object using metadata template
        past_loop_obj = deps.build_past_loop_object(current_loop, score, loop_result)

        # Add to our local past_loops array
        past_loops.append(past_loop_obj)

        # 🐛 Fix: Limit past_loops size to prevent unbounded growth
        MAX_PAST_LOOPS_PER_RUN = 20
        if len(past_loops) > MAX_PAST_LOOPS_PER_RUN:
            past_loops = past_loops[-MAX_PAST_LOOPS_PER_RUN:]
            logger.debug("Trimmed past_loops to most recent %s entries", MAX_PAST_LOOPS_PER_RUN)

        # Store loop result
        try:
            loop_key = f"loop_result:{node_id}:{current_loop}"
            deps.store_json(loop_key, loop_result)

            # Only persist past_loops across runs when explicitly enabled.
            if persist_across_runs:
                past_loops_key = f"past_loops:{node_id}"
                deps.store_json(past_loops_key, past_loops)

            group_key = f"loop_results:{node_id}"
            deps.store_hash_json(
                group_key,
                str(current_loop),
                {"result": loop_result, "score": score, "past_loop": past_loop_obj},
            )
        except Exception as e:
            logger.error("Failed to store loop result in Redis: %s", e)

        # Check threshold
        if score >= score_threshold:
            logger.info("Threshold met: %s >= %s", score, score_threshold)
            final_result = {
                "input": original_input,
                "result": deps.create_safe_result(loop_result),
                "loops_completed": current_loop,
                "final_score": score,
                "threshold_met": True,
                "past_loops": past_loops,
            }

            try:
                final_key = f"final_result:{node_id}"
                deps.store_json(final_key, final_result)
            except Exception as e:
                logger.error("Failed to store final result in Redis: %s", e)

            return final_result

        logger.info("Threshold not met: %s < %s, continuing...", score, score_threshold)

    # Max loops reached without meeting threshold
    if loop_result is None:
        loop_result = {}

    logger.info("Max loops reached: %s", max_loops)
    final_result = {
        "input": original_input,
        "result": deps.create_safe_result(loop_result),
        "loops_completed": current_loop,
        "final_score": score,
        "threshold_met": False,
        "past_loops": past_loops,
    }

    try:
        final_key = f"final_result:{node_id}"
        deps.store_json(final_key, final_result)
    except Exception as e:
        logger.error("Failed to store final result in Redis: %s", e)

    return final_result


