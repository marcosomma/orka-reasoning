# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

from __future__ import annotations

import logging
import os
import tempfile

import yaml

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, cast
logger = logging.getLogger(__name__)


@dataclass
class InternalWorkflowRunContext:
    node_id: str
    internal_workflow: dict[str, Any]
    past_loops_metadata_templates: dict[str, str]
    scoring_context: str
    memory_logger: Any = None
    parent_agents: Optional[list[dict[str, Any]]] = None


def compile_internal_workflow_config(ctx: InternalWorkflowRunContext) -> dict[str, Any]:
    """Return a workflow config dict ready to be dumped to YAML.

    Preserves current LoopNode behavior:
    - merges parent agents into internal workflow agent definitions (GraphScout visibility)
    - ensures orchestrator block exists
    - injects orchestrator memory config defaults
    """
    original_workflow = ctx.internal_workflow.copy()

    # GraphScout visibility: merge parent agents with internal workflow agents
    if ctx.parent_agents:
        internal_agents = original_workflow.get("agents", [])
        internal_agent_ids = {a["id"] for a in internal_agents if isinstance(a, dict) and "id" in a}
        for parent_agent in ctx.parent_agents:
            if isinstance(parent_agent, dict) and parent_agent.get("id") not in internal_agent_ids:
                internal_agents.append(parent_agent)
        original_workflow["agents"] = internal_agents

    if "orchestrator" not in original_workflow:
        original_workflow["orchestrator"] = {}

    orchestrator_config = original_workflow["orchestrator"]
    if isinstance(orchestrator_config, dict):
        orchestrator_config.update(
            {
                "id": orchestrator_config.get("id", "internal-workflow"),
                "strategy": orchestrator_config.get("strategy", "sequential"),
                "memory": {
                    "config": {
                        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6380/0"),
                        "backend": "redisstack",
                        "enable_hnsw": True,
                        "vector_params": {"M": 16, "ef_construction": 200, "ef_runtime": 10},
                    }
                },
            }
        )

    return original_workflow


def build_loop_workflow_input(
    *,
    original_input: Any,
    previous_outputs_safe: dict[str, Any],
    current_loop_number: int,
    scoring_context: str,
    dynamic_metadata: dict[str, Any],
) -> dict[str, Any]:
    # Ensure input is passed as a simple string for template rendering
    simple_input = original_input
    if isinstance(original_input, dict) and "input" in original_input:
        simple_input = original_input["input"]

    return {
        "input": simple_input,
        "previous_outputs": previous_outputs_safe,
        "loop_number": current_loop_number,
        "scoring_context": scoring_context,
        "past_loops_metadata": dynamic_metadata,
    }


async def run_internal_workflow_with_temp_yaml(
    *,
    workflow_config: dict[str, Any],
    workflow_input: dict[str, Any],
    memory_logger: Any,
) -> list[Any]:
    """Execute an internal workflow via temp YAML and return logs.

    This is intentionally close to the current LoopNode implementation, but
    extracted so LoopNode can become a thin coordinator.
    """

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(workflow_config, f)
        temp_file = f.name
        logger.info("[...] DEBUG: Wrote temp workflow file: %s", temp_file)

    try:
        # Lazy import to avoid circular import at package import time:
        # orka.orchestrator -> agent_factory -> orka.nodes -> LoopNode -> this module
        from orka.orchestrator import Orchestrator

        orchestrator = Orchestrator(temp_file)

        if memory_logger is not None:
            if hasattr(orchestrator.memory, "close"):
                try:
                    orchestrator.memory.close()
                except Exception as e:
                    logger.debug("Failed to close orphaned memory logger: %s", e)

            orchestrator.memory = memory_logger
            orchestrator.fork_manager.redis = memory_logger.redis

        if not hasattr(orchestrator, "render_template"):
            from ...orchestrator.simplified_prompt_rendering import SimplifiedPromptRenderer

            SimplifiedPromptRenderer.__init__(orchestrator)

        logs = await orchestrator.run(workflow_input, return_logs=True)
        return cast(list[Any], logs)
    finally:
        try:
            os.unlink(temp_file)
        except Exception as e:
            logger.warning("Failed to delete temporary workflow file: %s", e)


