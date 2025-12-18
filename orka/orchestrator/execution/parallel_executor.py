import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List

from .utils import sanitize_for_json, json_serializer

logger = logging.getLogger(__name__)


class ParallelExecutor:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    async def run_parallel_agents(
        self, agent_ids: List[str], fork_group_id: str, input_data: Any, previous_outputs: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Run agents in parallel as branches and return a list of log entries."""
        logger.info(f"Starting parallel execution of {len(agent_ids)} agents in fork group {fork_group_id}")

        missing_agents = [aid for aid in agent_ids if aid not in self.orchestrator.agents]
        if missing_agents:
            raise ValueError(f"Missing agents for parallel execution: {missing_agents}")

        enhanced_previous_outputs = self.orchestrator._context_manager.ensure_complete_context(previous_outputs)
        # Ensure we have a dict for previous outputs; tests may use mocks that don't return dicts
        if not isinstance(enhanced_previous_outputs, dict):
            try:
                enhanced_previous_outputs = dict(enhanced_previous_outputs)
            except Exception:
                enhanced_previous_outputs = {}

        fork_node_id = "_".join(fork_group_id.split("_")[:-1])
        fork_node = self.orchestrator.agents.get(fork_node_id)

        if not fork_node:
            logger.warning(f"Fork node {fork_node_id} not found, using default execution")
            branches = [[agent_id] for agent_id in agent_ids]
        else:
            branches = getattr(fork_node, "targets", [[agent_id] for agent_id in agent_ids])

        logger.debug(f"- Executing {len(branches)} branches: {branches}")

        try:
            # Prefer the orchestrator-level _run_branch_with_retry when available so tests can
            # monkeypatch ExecutionEngine._run_branch_with_retry. Fall back to the agent_runner
            # implementation for older test doubles that set only _agent_runner.
            runner_callable = None
            if hasattr(self.orchestrator, "_run_branch_with_retry"):
                runner_callable = lambda branch: self.orchestrator._run_branch_with_retry(
                    branch, input_data, enhanced_previous_outputs.copy(), max_retries=2, retry_delay=1.0
                )
            else:
                runner_callable = lambda branch: self.orchestrator._agent_runner.run_branch_with_retry(
                    branch, input_data, enhanced_previous_outputs.copy(), max_retries=2, retry_delay=1.0
                )

            branch_tasks = [runner_callable(branch) for branch in branches]

            branch_results = await asyncio.wait_for(
                asyncio.gather(*branch_tasks, return_exceptions=True),
                timeout=300,
            )

            result_logs: List[Dict[str, Any]] = []
            updated_previous_outputs = enhanced_previous_outputs.copy()

            for i, branch_result in enumerate(branch_results):
                if isinstance(branch_result, BaseException):
                    error_type = type(branch_result).__name__
                    error_msg = str(branch_result)
                    error_traceback = None

                    if hasattr(branch_result, "__traceback__"):
                        error_traceback = "".join(
                            traceback.format_exception(
                                type(branch_result), branch_result, branch_result.__traceback__
                            )
                        )

                    logger.error(
                        f"Branch {i} failed with {error_type}: {error_msg}\nBranch agents: {branches[i]}\nFork group: {fork_group_id}"
                    )

                    if error_traceback:
                        logger.debug(f"Full traceback:\n{error_traceback}")

                    error_log = {
                        "agent_id": f"branch_{i}_error",
                        "event_type": "BranchError",
                        "timestamp": datetime.now().isoformat(),
                        "payload": {
                            "error": error_msg,
                            "error_type": error_type,
                            "error_traceback": error_traceback,
                            "branch_agents": branches[i],
                            "fork_group_id": fork_group_id,
                        },
                        "step": f"{getattr(self.orchestrator, 'step_index', 0)}[{i}]",
                        "run_id": getattr(self.orchestrator, "run_id", "unknown"),
                    }
                    result_logs.append(error_log)
                    continue

                for agent_id, result in branch_result.items():
                    # Sanitize result
                    sanitized_result = sanitize_for_json(result)

                    # Store result in join state for JoinNode
                    join_state_key = "waitfor:join_parallel_checks:inputs"
                    # Use json dumps to emulate original behavior
                    if hasattr(self.orchestrator, "memory"):
                        try:
                            self.orchestrator.memory.hset(
                                join_state_key, agent_id, json.dumps(sanitized_result, default=json_serializer)
                            )
                            # Also update the fork group results hash so JoinNode sees the
                            # final agent payload (otherwise the initial placeholder from
                            # ForkNode may remain and the join will merge empty values).
                            try:
                                group_key = f"fork_group_results:{fork_group_id}"
                                self.orchestrator.memory.hset(
                                    group_key, agent_id, json.dumps(sanitized_result, default=json_serializer)
                                )
                            except Exception:
                                logger.debug("Failed to update fork group results for %s in %s", agent_id, fork_group_id)
                            # Also store a direct agent_result key for backwards compat
                            try:
                                agent_key = f"agent_result:{fork_group_id}:{agent_id}"
                                self.orchestrator.memory.set(agent_key, json.dumps(sanitized_result, default=json_serializer))
                            except Exception:
                                logger.debug("Failed to set agent_result key for %s in %s", agent_id, fork_group_id)
                        except Exception:
                            logger.debug("Memory hset not available or failed during parallel execution")

                    # Defensive logging: detect missing or low-confidence results from branch agents
                    try:
                        resp = None
                        conf = None
                        if isinstance(sanitized_result, dict):
                            resp = sanitized_result.get("response")
                            conf = sanitized_result.get("confidence")

                        if resp in (None, "", []) or conf in (None, "0.0", 0, "0"):
                            logger.warning(
                                f"Fork group {fork_group_id}: agent {agent_id} returned empty/low-confidence result: response={resp!r}, confidence={conf!r}"
                            )
                    except Exception:
                        logger.debug("Failed to inspect sanitized_result for agent %s in fork %s", agent_id, fork_group_id)

                    agent = self.orchestrator.agents[agent_id]

                    if isinstance(result, dict):
                        payload_data = result.copy()
                    else:
                        payload_data = {"result": result}

                    if "formatted_prompt" not in payload_data:
                        payload_context = {"input": input_data, "previous_outputs": updated_previous_outputs}
                        if isinstance(input_data, dict):
                            for var in ["loop_number", "past_loops_metadata"]:
                                if var in input_data:
                                    payload_context[var] = input_data[var]
                        # Use ExecutionEngine helper to add prompt if missing
                        try:
                            self.orchestrator._add_prompt_to_payload(agent, payload_data, payload_context)
                        except Exception:
                            # Best effort: skip prompt enrichment on failure
                            pass

                    log_data = {
                        "agent_id": agent_id,
                        "event_type": f"ForkedAgent-{agent.__class__.__name__}",
                        "timestamp": datetime.now().isoformat(),
                        "payload": payload_data,
                        "step": len(result_logs),
                        "run_id": getattr(self.orchestrator, "run_id", "unknown"),
                        "fork_group_id": fork_group_id,
                    }
                    result_logs.append(log_data)

                    if hasattr(self.orchestrator, "memory"):
                        try:
                            self.orchestrator.memory.log(
                                agent_id,
                                f"ForkedAgent-{agent.__class__.__name__}",
                                payload_data,
                                step=len(result_logs),
                                run_id=getattr(self.orchestrator, "run_id", "unknown"),
                                fork_group=fork_group_id,
                                previous_outputs=updated_previous_outputs.copy(),
                            )
                        except Exception:
                            logger.debug("Memory log failed during parallel execution")

                    # Mark agent done in fork manager and progress sequential branches if any
                    try:
                        if hasattr(self.orchestrator, "fork_manager"):
                            try:
                                self.orchestrator.fork_manager.mark_agent_done(fork_group_id, agent_id)
                            except Exception:
                                logger.debug(f"Failed to mark agent {agent_id} done in fork group {fork_group_id}")

                            # If there is a next agent in sequence for this branch, enqueue it
                            try:
                                next_agent = self.orchestrator.fork_manager.next_in_sequence(fork_group_id, agent_id)
                                if next_agent:
                                    try:
                                        self.orchestrator.enqueue_fork([next_agent], fork_group_id)
                                    except Exception:
                                        logger.debug(f"Failed to enqueue next agent {next_agent} for fork {fork_group_id}")
                            except Exception:
                                logger.debug(f"Error checking next_in_sequence for {agent_id} in {fork_group_id}")
                    except Exception:
                        # Best-effort - failures should not break parallel execution
                        logger.debug("Ignoring fork manager progress errors during parallel execution")

                    updated_previous_outputs[agent_id] = sanitized_result

            if not any(not isinstance(r, BaseException) for r in branch_results):
                logger.error(f"All {len(branch_results)} branches failed in fork group {fork_group_id}. Creating fallback empty result.")
                fallback_result = {
                    "status": "partial_failure",
                    "successful_branches": 0,
                    "total_branches": len(branch_results),
                    "error": "All parallel branches failed",
                }
                result_logs.append(
                    {
                        "agent_id": f"{fork_group_id}_fallback",
                        "event_type": "ForkGroupFallback",
                        "timestamp": datetime.now().isoformat(),
                        "payload": fallback_result,
                        "step": getattr(self.orchestrator, "step_index", 0),
                        "run_id": getattr(self.orchestrator, "run_id", "unknown"),
                    }
                )

            logger.info(f"Parallel execution completed: {len(result_logs)} results")
            return result_logs

        except asyncio.TimeoutError:
            logger.error(f"Parallel execution timed out for fork group {fork_group_id}")
            raise
        except Exception as e:
            logger.error(f"Parallel execution failed: {e}")
            raise
