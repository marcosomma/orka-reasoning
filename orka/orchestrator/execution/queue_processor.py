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

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from time import time
from typing import Any, Dict, List, Optional

from ...contracts import OrkaResponse
from ...response_builder import ResponseBuilder
from ...response_builder import OrkaResponse as _OrkaResponse

logger = logging.getLogger(__name__)


class QueueProcessor:
    """Encapsulates the main execution queue loop.

    This class was extracted from the previous monolithic ExecutionEngine to
    keep the engine thin and make GraphScout extraction simpler later.
    """

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    async def run_queue(self, input_data: Any, logs: List[Dict[str, Any]], return_logs: bool = False) -> Any:
        """Run the main orchestrator queue until exhaustion and return final response or logs.

        Args:
            input_data: input payload passed to the orchestrator
            logs: list to accumulate execution logs
            return_logs: if True return full logs, otherwise return final response
        """
        engine = self.engine
        try:
            # Initialize run metadata
            # Only assign a new run_id if not already set by caller/tests
            if not getattr(engine, "run_id", None):
                engine.run_id = f"run_{int(time() * 1000)}"
            engine.step_index = 0
            start_time = time()

            # Ensure engine.queue exists
            if not hasattr(engine, "queue"):
                engine.queue = []

            # Initialize queue from orchestrator_cfg if available (tests expect orchestrator_cfg to drive the run)
            if hasattr(engine, "orchestrator_cfg"):
                try:
                    engine.queue = list(engine.orchestrator_cfg.get("agents", []))
                except Exception:
                    engine.queue = []

            # Main loop
            while engine.queue:
                agent_id = engine.queue.pop(0)
                agent = engine.agents.get(agent_id)
                engine.step_index += 1

                log_entry = {
                    "agent_id": agent_id,
                    "event_type": agent.__class__.__name__ if agent is not None else "Unknown",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "payload": {},
                    "step": engine.step_index,
                    "run_id": engine.run_id,
                    "previous_outputs": engine.build_previous_outputs(logs) if hasattr(engine, "build_previous_outputs") else {},
                }

                # Run agent and capture result(s) with retry semantics for None/waiting
                try:
                    # Prepare full_payload with orchestrator context (tests expect this)
                    full_payload = {"orchestrator": engine, "run_id": getattr(engine, "run_id", None)}

                    attempts = 0
                    max_attempts = getattr(engine, "max_agent_retries", 2)
                    agent_id_ret = None
                    agent_result = None

                    while attempts <= max_attempts:
                        attempts += 1
                        agent_id_ret, agent_result = await engine._run_agent_async(
                            agent_id, input_data, engine.build_previous_outputs(logs), full_payload=full_payload
                        )

                        # If agent returned None tuple -> retry
                        if agent_id_ret is None and agent_result is None:
                            if attempts <= max_attempts:
                                if hasattr(engine, "_record_retry"):
                                    try:
                                        engine._record_retry(agent_id)
                                    except Exception:
                                        pass
                                continue
                            else:
                                break

                        # If agent returned waiting status, retry
                        if isinstance(agent_result, dict) and agent_result.get("status") == "waiting":
                            if attempts <= max_attempts:
                                if hasattr(engine, "_record_retry"):
                                    try:
                                        engine._record_retry(agent_id)
                                    except Exception:
                                        pass
                                continue
                            else:
                                break

                        # Otherwise, got a real result - break
                        break

                    # Normalize result to payload_out dict using ResponseNormalizer
                    payload_out: Dict[str, Any] = {"agent_id": agent_id_ret}
                    try:
                        if hasattr(engine, "_response_normalizer"):
                            normalized = engine._response_normalizer.normalize(agent, agent_id_ret, agent_result)
                            payload_out.update(normalized)
                        else:
                            # Fallback to inline conversion if normalizer is not present
                            if isinstance(agent_result, dict) and (
                                "result" in agent_result or "memories" in agent_result or "response" in agent_result
                            ):
                                if "response" in agent_result:
                                    converted = ResponseBuilder.from_llm_agent_response(agent_result, agent_id_ret)
                                elif "memories" in agent_result:
                                    converted = ResponseBuilder.from_memory_agent_response(agent_result, agent_id_ret)
                                else:
                                    converted = ResponseBuilder.from_node_response(agent_result, agent_id_ret)
                                payload_out.update({
                                    "result": converted.get("result"),
                                    "status": converted.get("status"),
                                    "error": converted.get("error"),
                                    "response": converted.get("result"),
                                    "confidence": converted.get("confidence", "0.0"),
                                    "internal_reasoning": converted.get("internal_reasoning", ""),
                                    "formatted_prompt": converted.get("formatted_prompt", ""),
                                    "execution_time_ms": converted.get("execution_time_ms"),
                                    "token_usage": converted.get("token_usage"),
                                    "cost_usd": converted.get("cost_usd"),
                                    "memory_entries": converted.get("memory_entries"),
                                    "_metrics": converted.get("metrics", {}),
                                    "trace_id": converted.get("trace_id"),
                                })
                            else:
                                converted = ResponseBuilder.from_tool_response(agent_result, agent_id_ret)
                                payload_out.update({
                                    "result": converted.get("result"),
                                    "status": converted.get("status"),
                                    "response": converted.get("result"),
                                    "_metrics": converted.get("metrics", {}),
                                })
                    except Exception as e:
                        logger.error(f"Failed to normalize result for agent {agent_id_ret}: {e}")
                        payload_out.update({"result": None, "status": "error", "error": str(e)})

                    # Handle router and fork nodes specially
                    agent_type = (getattr(agent, "type", None) or getattr(agent, "__class__", type(agent)).__name__).lower() if agent is not None else ""

                    # Router node: if result is a list of agents, prepend them to the queue
                    if agent_type == "routernode" or agent_type == "router":
                        if isinstance(agent_result, dict) and isinstance(agent_result.get("result"), list):
                            new_agents = agent_result.get("result", [])
                            if new_agents:
                                engine.queue = new_agents + engine.queue
                                logger.info(f"Router inserted agents at front of queue: {new_agents}")

                    # GraphScout handling
                    if agent_type in ("graph-scout", "graphscout", "graph_scout"):
                        try:
                            handler = __import__("orka.orchestrator.execution.graphscout_handler", fromlist=["GraphScoutHandler"]).GraphScoutHandler(engine)
                            await handler.handle(agent_id, agent_result, logs, input_data)
                        except Exception as e:
                            logger.error(f"GraphScout handling failed for {agent_id}: {e}")

                    # Delegate post-normalization handling to ResponseProcessor (fork/logging/memory)
                    try:
                        if hasattr(engine, "_response_processor"):
                            handled = await engine._response_processor.process(
                                agent_id,
                                agent_id_ret,
                                agent_result,
                                payload_out,
                                agent,
                                input_data,
                                logs,
                                log_entry,
                                engine.step_index,
                            )
                            if handled:
                                continue
                        else:
                            # fallback: inline handling (preserve previous behavior)
                            result_key = f"agent_result:{agent_id_ret}"
                            if hasattr(engine, "memory"):
                                engine.memory.set(result_key, json.dumps(payload_out, default=str))
                            log_entry["payload"] = payload_out
                            logs.append(log_entry)

                            if hasattr(engine, "memory"):
                                engine.memory.log(
                                    agent_id_ret,
                                    agent.__class__.__name__ if agent is not None else "",
                                    payload_out,
                                    step=engine.step_index,
                                    run_id=engine.run_id,
                                    previous_outputs=engine.build_previous_outputs(logs[:-1]),
                                )
                    except Exception as e:
                        logger.error(f"Response processing failed for {agent_id_ret}: {e}")

                except Exception as agent_error:
                    logger.error(f"Error executing agent {agent_id}: {agent_error}")
                    continue

            # End of queue
            meta_report = engine._generate_meta_report(logs) if hasattr(engine, "_generate_meta_report") else {}

            # Save enhanced trace
            log_dir = os.getenv("ORKA_LOG_DIR", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, f"orka_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

            enhanced_trace = engine._build_enhanced_trace(logs, meta_report) if hasattr(engine, "_build_enhanced_trace") else {"logs": logs}
            if hasattr(engine, "memory") and hasattr(engine.memory, "save_enhanced_trace"):
                engine.memory.save_enhanced_trace(log_path, enhanced_trace)

            try:
                if hasattr(engine.memory, "close"):
                    engine.memory.close()
            except Exception as e:
                logger.warning(f"Warning: Failed to cleanly close memory backend: {e!s}")

            if return_logs:
                return logs
            else:
                final_resp = engine._extract_final_response(logs) if hasattr(engine, "_extract_final_response") else None
                return final_resp

        except Exception as e:
            logger.error(f"Unexpected error in QueueProcessor: {e}")
            raise
