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

import logging
from typing import Any, Dict

from ...response_builder import ResponseBuilder
from ...utils.metric_normalization import normalize_payload

logger = logging.getLogger(__name__)


class ResponseNormalizer:
    """Normalize agent results into a consistent payload dict for logging and storage."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    def normalize(self, agent, agent_id: str, agent_result: Any) -> Dict[str, Any]:
        """Return a normalized payload dict representing the agent result.

        This mirrors the previous inlined logic in QueueProcessor but is
        centralized for testing and reuse.
        """
        payload_out: Dict[str, Any] = {"agent_id": agent_id}

        try:
            # Unwrap a BaseAgent OrkaResponse before generic routing.
            # BaseAgent.run wraps _run_impl output as
            #   {result: <legacy dict>, status, component_id, component_type, ...}
            # and does NOT promote confidence/cost/internal_reasoning to the top level —
            # they live inside `result`. Without this, the generic block below sees no
            # top-level "response" key, routes to from_node_response, and silently
            # defaults confidence to 0.0 and drops cost_usd (data loss).
            # Only unwrap genuine LLM legacy responses — those carry a "response" key.
            # Node/agent outputs (e.g. GraphScout returns {decision, target, confidence,
            # result}) also have "confidence"/"_metrics" but NO "response"; treating them
            # as LLM responses would extract a non-existent "response" field and null out
            # their real result. Require "response" so those fall through to from_node_response.
            if (
                isinstance(agent_result, dict)
                and "component_type" in agent_result
                and "status" in agent_result
                and isinstance(agent_result.get("result"), dict)
                and "response" in agent_result["result"]
            ):
                inner = dict(agent_result["result"])
                for k in (
                    "cost_usd", "token_usage", "confidence", "formatted_prompt",
                    "internal_reasoning", "trace_id", "execution_time_ms",
                ):
                    if agent_result.get(k) is not None and inner.get(k) is None:
                        inner[k] = agent_result[k]
                # CRITICAL: keep `result` as the full inner dict. build_previous_outputs
                # exposes previous_outputs[agent_id] = payload["result"], so templates
                # navigate it as previous_outputs.x.<field> (e.g. .response, .domain,
                # .episode_count). Collapsing result to inner["response"] would make it a
                # bare string and break that navigation. We additionally PROMOTE the
                # rich fields (confidence/cost/...) to the top level for logging/metrics.
                payload_out.update(
                    {
                        "result": inner,
                        "status": agent_result.get("status") or "success",
                        "error": agent_result.get("error"),
                        "response": inner.get("response"),
                        "confidence": inner.get("confidence", 0.0),
                        "internal_reasoning": inner.get("internal_reasoning", ""),
                        "formatted_prompt": inner.get("formatted_prompt", ""),
                        "execution_time_ms": agent_result.get("execution_time_ms"),
                        "token_usage": inner.get("token_usage"),
                        "cost_usd": inner.get("cost_usd"),
                        "_metrics": inner.get("_metrics", {}),
                        "trace_id": inner.get("trace_id") or agent_result.get("trace_id"),
                    }
                )
                # Also surface agent-specific extras at the top level for any consumer
                # that reads the normalized payload directly (not via previous_outputs).
                for k, v in inner.items():
                    if k not in payload_out:
                        payload_out[k] = v
                return normalize_payload(payload_out)

            # Dict-like results (LLM agents, nodes, memory agents)
            if isinstance(agent_result, dict) and (
                "result" in agent_result or "memories" in agent_result or "response" in agent_result
            ):
                agent_type = (getattr(agent, "type", None) or getattr(agent, "__class__", type(agent)).__name__).lower() if agent is not None else ""

                # Loopnode has special preserved structure
                if agent_type == "loopnode":
                    loop_data = agent_result.get("result", agent_result) if isinstance(agent_result, dict) and "result" in agent_result else agent_result
                    if isinstance(loop_data, dict) and all(k in loop_data for k in ["result", "loops_completed", "final_score"]):
                        payload_out.update({
                            "response": loop_data,
                            "result": loop_data.get("result"),
                            "loops_completed": loop_data.get("loops_completed"),
                            "final_score": loop_data.get("final_score"),
                            "threshold_met": loop_data.get("threshold_met"),
                            "past_loops": loop_data.get("past_loops", []),
                            "status": "success",
                            "confidence": 1.0,
                            "internal_reasoning": "",
                        })
                        return normalize_payload(payload_out)
                    else:
                        converted = ResponseBuilder.from_node_response(agent_result, agent_id)
                        payload_out.update({
                            "result": converted.get("result"),
                            "status": converted.get("status"),
                            "error": converted.get("error"),
                            "response": converted.get("result"),
                        })
                        return normalize_payload(payload_out)

                # Generic conversion for other dicts
                if "response" in agent_result:
                    converted = ResponseBuilder.from_llm_agent_response(agent_result, agent_id)
                elif "memories" in agent_result:
                    converted = ResponseBuilder.from_memory_agent_response(agent_result, agent_id)
                else:
                    converted = ResponseBuilder.from_node_response(agent_result, agent_id)

                payload_out.update(
                    {
                        "result": converted.get("result"),
                        "status": converted.get("status"),
                        "error": converted.get("error"),
                        "response": converted.get("result"),
                        "confidence": converted.get("confidence", 0.0),
                        "internal_reasoning": converted.get("internal_reasoning", ""),
                        "formatted_prompt": converted.get("formatted_prompt", ""),
                        "execution_time_ms": converted.get("execution_time_ms"),
                        "token_usage": converted.get("token_usage"),
                        "cost_usd": converted.get("cost_usd"),
                        "memory_entries": converted.get("memory_entries"),
                        "_metrics": converted.get("metrics", {}),
                        "trace_id": converted.get("trace_id"),
                    }
                )
                return normalize_payload(payload_out)

            # Non-dict results (tools, etc.)
            converted = ResponseBuilder.from_tool_response(agent_result, agent_id)
            payload_out.update(
                {
                    "result": converted.get("result"),
                    "status": converted.get("status"),
                    "response": converted.get("result"),
                    "_metrics": converted.get("metrics", {}),
                }
            )
            return normalize_payload(payload_out)

        except Exception as e:
            logger.error(f"ResponseNormalizer failed for agent {agent_id}: {e}")
            # Fallback minimal payload
            return {"agent_id": agent_id, "result": None, "status": "error", "error": str(e)}
