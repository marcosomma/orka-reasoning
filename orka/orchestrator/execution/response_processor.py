import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResponseProcessor:
    """Handles post-normalization processing of agent responses.

    Responsibilities:
    - Handle fork node initiation and parallel execution
    - Persist agent result payloads into memory (set + log)
    - Append log entries to the shared logs list
    """

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    async def process(
        self,
        agent_id: str,
        agent_id_ret: str,
        agent_result: Any,
        payload_out: Dict[str, Any],
        agent: Any,
        input_data: Any,
        logs: List[Dict[str, Any]],
        log_entry: Dict[str, Any],
        step_index: int,
    ) -> bool:
        """Process the normalized response and handle logging/storage.

        Returns True if caller should continue the main loop (e.g., fork was handled)
        and not perform the default logging, otherwise False.
        """
        engine = self.engine

        # Detect node type
        agent_type = (
            (getattr(agent, "type", None) or getattr(agent, "__class__", type(agent)).__name__).lower()
            if agent is not None
            else ""
        )

        # Fork handling (initiates parallel run and records fork_group metadata)
        if agent_type == "forknode":
            fork_result = agent_result.get("result", {}) if isinstance(agent_result, dict) else {}
            fork_group_id = fork_result.get("fork_group")
            if fork_group_id:
                payload_out["fork_group_id"] = fork_group_id
                payload_out["fork_execution_status"] = "initiated"

                log_entry["payload"] = payload_out
                logs.append(log_entry)

                # Write to memory backend if available
                if hasattr(engine, "memory"):
                    try:
                        engine.memory.log(
                            agent_id,
                            agent.__class__.__name__ if agent is not None else "",
                            payload_out.copy(),
                            step=step_index,
                            run_id=engine.run_id,
                            previous_outputs=engine.build_previous_outputs(logs[:-1]) if hasattr(engine, "build_previous_outputs") else {},
                        )
                    except Exception as e:
                        logger.warning(f"Warning: memory.log failed for fork node {agent_id}: {e}")

                forked_agents = fork_result.get("agents", [])
                fork_mode = fork_result.get("mode", "sequential")

                # Only run parallel execution immediately when the fork was declared as
                # parallel mode. Sequential forks enqueue first agents and will be
                # progressed by queue-driven execution.
                if forked_agents and fork_mode == "parallel":
                    try:
                        fork_logs = await engine.run_parallel_agents(
                            forked_agents, fork_group_id, input_data, engine.build_previous_outputs(logs)
                        )
                        logs.extend(fork_logs)
                    except Exception as e:
                        logger.error(f"Fork execution failed for group {fork_group_id}: {e}")

                # Fork handled — caller should continue
                return True

        # Default: persist result to memory and append log
        try:
            result_key = f"agent_result:{agent_id_ret}"
            if hasattr(engine, "memory"):
                try:
                    engine.memory.set(result_key, json.dumps(payload_out, default=str))
                except Exception as e:
                    logger.warning(f"Warning: memory.set failed for {result_key}: {e}")

            log_entry["payload"] = payload_out
            logs.append(log_entry)

            if hasattr(engine, "memory"):
                try:
                    engine.memory.log(
                        agent_id_ret,
                        agent.__class__.__name__ if agent is not None else "",
                        payload_out,
                        step=step_index,
                        run_id=engine.run_id,
                        previous_outputs=engine.build_previous_outputs(logs[:-1]) if hasattr(engine, "build_previous_outputs") else {},
                    )
                except Exception as e:
                    logger.warning(f"Warning: memory.log failed for {agent_id_ret}: {e}")

            # Ensure minimal response footprint so downstream components (Join/Validators)
            # can rely on presence of 'response' and 'confidence' fields.
            try:
                if "response" not in payload_out:
                    payload_out["response"] = payload_out.get("result") or ""
                if "confidence" not in payload_out:
                    payload_out["confidence"] = payload_out.get("confidence", "0.0")
            except Exception:
                logger.debug("Failed to set fallback response/confidence for %s", agent_id_ret)

            # If this agent is part of a fork group, progress the fork manager:
            # - Try to find fork_group via the join state hash (created by ForkNode)
            # - Mark agent done and enqueue the next agent in sequence if present
            if hasattr(engine, "memory") and hasattr(engine, "fork_manager"):
                # Resolve fork group for this agent; fail silently on any memory access errors
                try:
                    mapped = engine.memory.hget("fork_agent_to_group", agent_id_ret)
                    fork_group = (
                        mapped.decode() if isinstance(mapped, (bytes, bytearray)) else mapped
                    )
                except Exception:
                    fork_group = None

                if fork_group:
                    try:
                        engine.fork_manager.mark_agent_done(fork_group, agent_id_ret)
                    except Exception:
                        logger.debug(
                            "Failed to mark agent %s done in fork group %s",
                            agent_id_ret,
                            fork_group,
                        )

                    # update group results table for join node
                    try:
                        group_key = f"fork_group_results:{fork_group}"
                        engine.memory.hset(
                            group_key, agent_id_ret, json.dumps(payload_out, default=str)
                        )
                    except Exception:
                        logger.debug(
                            "Failed to update fork group results for %s in %s",
                            agent_id_ret,
                            fork_group,
                        )

                    # Also update the join state key so JoinNode will read the final
                    # payload instead of the initial placeholder created by ForkNode.
                    try:
                        state_key = f"waitfor:{fork_group}:inputs"
                        engine.memory.hset(
                            state_key, agent_id_ret, json.dumps(payload_out, default=str)
                        )
                    except Exception:
                        logger.debug(
                            "Failed to update join state for %s in %s",
                            agent_id_ret,
                            fork_group,
                        )

                    # Set a direct agent_result key for backwards compatibility
                    try:
                        fork_agent_key = f"agent_result:{fork_group}:{agent_id_ret}"
                        engine.memory.set(fork_agent_key, json.dumps(payload_out, default=str))
                    except Exception:
                        logger.debug(
                            "Failed to set agent_result key for %s in %s",
                            agent_id_ret,
                            fork_group,
                        )

                    # enqueue next agent in sequence if any
                    try:
                        next_agent = engine.fork_manager.next_in_sequence(fork_group, agent_id_ret)
                        if next_agent:
                            engine.enqueue_fork([next_agent], fork_group)
                    except Exception:
                        logger.debug(
                            "Error while enqueuing next agent for fork group %s", fork_group
                        )

        except Exception as e:
            logger.error(f"Unexpected error in ResponseProcessor: {e}")

        return False
