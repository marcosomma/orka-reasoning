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


import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from ..memory.redisstack_logger import RedisStackMemoryLogger
from .base_node import BaseNode

logger = logging.getLogger(__name__)


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class JoinNode(BaseNode):
    """
    A node that waits for and merges results from parallel branches created by a ForkNode.
    Uses a max retry counter to prevent infinite waiting.
    """

    def __init__(self, node_id, prompt, queue, memory_logger=None, **kwargs):
        super().__init__(node_id, prompt, queue, **kwargs)
        self.memory_logger = memory_logger
        self.group_id = kwargs.get("group")
        self.max_retries = kwargs.get("max_retries", 30)
        self.output_key = f"{self.node_id}:output"
        self._retry_key = f"{self.node_id}:join_retry_count"

    async def _run_impl(self, input_data):
        """
        Run the join operation by collecting and merging results from forked agents.
        """
        logger.info(f"🔗 JOIN NODE START: {self.node_id}")
        logger.info(f"🔗 JOIN - Input data: {input_data}")
        
        # Try to get fork_group_id from input, fallback to finding by pattern
        fork_group_id = input_data.get("fork_group_id")
        logger.info(f"🔗 JOIN - Fork group ID from input: {fork_group_id}")

        # Track whether we recovered the group using an explicit mapping
        mapping_used = False
        if not fork_group_id and self.group_id:
            # Prefer explicit mapping written by ForkNode (avoids stale fork_group:* keys from prior runs)
            try:
                mapping_key = f"fork_group_mapping:{self.group_id}"
                mapped = self.memory_logger.hget(mapping_key, "group_id")
                if mapped:
                    fork_group_id = mapped.decode() if isinstance(mapped, bytes) else mapped
                    mapping_used = True
                    logger.info(
                        f"Join node '{self.node_id}' recovered fork group from mapping: {fork_group_id}"
                    )
            except Exception as e:
                logger.debug(
                    f"Join node '{self.node_id}': error reading mapping key fork_group_mapping:{self.group_id}: {e}"
                )

        if not fork_group_id and self.group_id:
            # Fallback: scan for fork groups that match our pattern (e.g., "opening_positions_*")
            pattern = f"fork_group:{self.group_id}_*"
            try:
                matching_keys = []
                cursor = 0
                while True:
                    cursor, keys = self.memory_logger.scan(cursor, match=pattern, count=100)
                    matching_keys.extend(keys)
                    if cursor == 0:
                        break

                if matching_keys:
                    latest_key = max(
                        matching_keys, key=lambda k: k.decode() if isinstance(k, bytes) else k
                    )
                    fork_group_id = (
                        latest_key.decode() if isinstance(latest_key, bytes) else latest_key
                    ).replace("fork_group:", "")
                    logger.info(f"Join node '{self.node_id}' found fork group: {fork_group_id}")
                else:
                    logger.warning(
                        f"Join node '{self.node_id}' could not find fork group matching pattern: {pattern}"
                    )
            except Exception as e:
                logger.error(f"Join node '{self.node_id}' error finding fork group: {e}")

        if not fork_group_id:
            fork_group_id = self.group_id

        logger.info(f"🔗 JOIN - Final fork_group_id: {fork_group_id}")

        # NOTE:
        # - fork_group_results:<id> is the stable hash containing entries for all agents in the fork
        # - fork_group:<id> may be used as a "pending set" by ForkGroupManager (members removed as done)
        # - waitfor:<fork_group_id>:inputs tracks received payloads written during execution
        #   (must be per-fork group to avoid leaking results across workflows/runs)
        state_key = f"waitfor:{fork_group_id}:inputs"

        # Get or increment retry count using backend-agnostic hash operations
        retry_count_str = self.memory_logger.hget("join_retry_counts", self._retry_key)
        if retry_count_str is None:
            retry_count = 3
        else:
            retry_count = int(retry_count_str) + 1
        self.memory_logger.hset("join_retry_counts", self._retry_key, str(retry_count))

        logger.info(f"🔗 JOIN - Retry count: {retry_count}/{self.max_retries}")

        # "Received" agents are the ones with entries in the join state hash
        inputs_received = self.memory_logger.hkeys(state_key)
        received = [i.decode() if isinstance(i, bytes) else i for i in inputs_received]

        # Determine expected agents.
        # Prefer fork_group_results:<id> (stable registry of all agents in the fork) if present.
        group_results_key = f"fork_group_results:{fork_group_id}" if fork_group_id else None
        fork_targets: list[str] = []
        if group_results_key:
            try:
                keys = self.memory_logger.hkeys(group_results_key)
                fork_targets = [i.decode() if isinstance(i, bytes) else i for i in keys]
            except Exception:
                fork_targets = []

        # Fallback: use fork_group:<id> (can be either registry or pending set depending on backend)
        if not fork_targets and fork_group_id:
            try:
                fork_targets = self.memory_logger.smembers(f"fork_group:{fork_group_id}")
                fork_targets = [i.decode() if isinstance(i, bytes) else i for i in fork_targets]
            except Exception:
                fork_targets = []

        # If we don't have a fork_group or the recovered mapping returned an empty set,
        # try to infer the correct fork_group from the stored agent state in the
        # join state hash (the initial_result stored by ForkNode includes 'fork_group').
        if (not fork_group_id or (mapping_used and not fork_targets)) and received:
            try:
                # Inspect the first received entry to find its fork_group
                first_agent = received[0]
                raw = self.memory_logger.hget(state_key, first_agent)
                if raw:
                    raw_val = raw.decode() if isinstance(raw, bytes) else raw
                    try:
                        parsed = json.loads(raw_val)
                        detected = parsed.get("fork_group")
                        if detected and detected != fork_group_id:
                            # Capture the inferred group and decide whether to use its
                            # smembers or fallback to the received inputs. If the
                            # mapping recovery had returned no targets (common in
                            # race conditions) prefer falling back to the received
                            # inputs so the join can proceed instead of waiting.
                            original_empty = not fork_targets and mapping_used
                            fork_group_id = detected
                            logger.info(
                                f"Join node '{self.node_id}' inferred fork group from state entry: {fork_group_id}"
                            )

                            # If we previously recovered a mapping but it had no
                            # registered targets, prefer using the received inputs
                            # rather than switching to the smembers of the detected
                            # group (which might expect more agents that never
                            # arrive due to the race). This makes joins more
                            # resilient in recovery scenarios.
                            if original_empty:
                                logger.info(
                                    f"Join node '{self.node_id}': mapping used but had no targets; falling back to received inputs for merge."
                                )
                                fork_targets = list(received)
                            else:
                                fork_targets = self.memory_logger.smembers(f"fork_group:{fork_group_id}")
                                fork_targets = [i.decode() if isinstance(i, bytes) else i for i in fork_targets]
                    except Exception:
                        logger.debug(f"Join node '{self.node_id}': could not parse state for agent {first_agent}")
            except Exception as e:
                logger.debug(f"Join node '{self.node_id}': error reading state for inference: {e}")
        # If no fork targets are registered for this group, decide behavior.
        # If we recovered the group via an explicit mapping, it's safer to
        # wait — the Fork node likely hasn't registered targets yet. If we
        # did not use mapping and we already have received inputs, it's
        # reasonable to fall back to received inputs to allow the join to
        # proceed in certain race conditions.
        if not fork_targets:
            if mapping_used:
                # Before immediately waiting, check if the join state already contains
                # completed payloads for the received agents. This can happen when
                # fork targets were created but quickly removed (mark_agent_done), or
                # when results were written directly into the join state by the
                # ParallelExecutor/ResponseProcessor. If we detect any completed
                # payloads, it's safe to fall back to merging the received entries.
                try:
                    completed_found = False
                    for agent in received:
                        raw = self.memory_logger.hget(state_key, agent)
                        if raw:
                            raw_val = raw.decode() if isinstance(raw, bytes) else raw
                            try:
                                parsed = json.loads(raw_val)
                                status = parsed.get("status")
                                response = parsed.get("response")
                                # Consider non-pending or non-empty response as completed
                                if status and status != "pending":
                                    completed_found = True
                                    break
                                if response not in (None, "", []):
                                    completed_found = True
                                    break
                            except Exception:
                                # If parsing fails, continue checking other agents
                                continue
                except Exception:
                    completed_found = False

                if completed_found:
                    logger.warning(
                        f"Join node '{self.node_id}': mapping used but fork set empty, merging using received completed inputs."
                    )
                    fork_targets = list(received)
                else:
                    logger.info(
                        f"Join node '{self.node_id}': no fork targets found for group '{fork_group_id}' after mapping. Waiting for targets to be created."
                    )
                    return {
                        "status": "waiting",
                        "pending": [],
                        "received": received,
                        "retry_count": retry_count,
                        "max_retries": self.max_retries,
                        "message": "No expected fork targets yet; waiting for Fork to register targets",
                    }
            if received:
                logger.warning(
                    f"Join node '{self.node_id}': no fork targets found for group '{fork_group_id}'. "
                    "Falling back to received inputs as targets."
                )
                fork_targets = list(received)
        # Pending agents are those expected but not yet present in the join state.
        pending = [agent for agent in fork_targets if agent not in received]

        logger.info(f"🔗 JOIN - Expected agents (fork_targets): {fork_targets}")
        logger.info(f"🔗 JOIN - Received agents: {received}")
        logger.info(f"🔗 JOIN - Pending agents: {pending}")

        # Check if all forked agents have completed
        if not pending:
            logger.info(f"🔗 JOIN - All agents completed! Proceeding to merge results.")
            self.memory_logger.hdel("join_retry_counts", self._retry_key)
            # Merge from the stable results hash if available; otherwise merge from join state.
            if group_results_key and fork_targets:
                return self._complete(fork_targets, group_results_key, input_data=input_data)
            return self._complete(fork_targets, state_key, input_data=input_data)

        # Check for max retries
        if retry_count >= self.max_retries:
            logger.error(f"🔗 JOIN - TIMEOUT! Max retries reached.")
            self.memory_logger.hdel("join_retry_counts", self._retry_key)
            logger.error(
                f"[ORKA][NODE][JOIN][TIMEOUT] Join node '{self.node_id}' timed out after {self.max_retries} retries. "
                f"Fork group: {fork_group_id}. "
                f"Pending agents: {pending}. "
                f"Received agents: {received}. "
                f"This usually means some forked agents failed or took too long to complete."
            )
            return {
                "status": "timeout",
                "pending": pending,
                "received": received,
                "max_retries": self.max_retries,
                "fork_group": fork_group_id,
                "message": f"Join timed out waiting for agents: {', '.join(pending)}",
            }

        # Return waiting status if not all agents have completed
        logger.info(f"🔗 JOIN - Still waiting for {len(pending)} agents: {pending}")
        return {
            "status": "waiting",
            "pending": pending,
            "received": received,
            "retry_count": retry_count,
            "max_retries": self.max_retries,
        }

    def _complete(self, fork_targets, state_key, input_data: Any = None):
        """
        Complete the join operation by merging all fork results.

        Args:
            fork_targets (list): List of agent IDs to collect results from
            state_key (str): Redis key where results are stored

        Returns:
            dict: Merged results from all agents
        """
        logger.info(f"🔗 JOIN COMPLETE - Starting merge for {len(fork_targets)} agents")

        # Get all results from Redis
        merged = {}
        for agent_id in fork_targets:
            try:
                # Get result from Redis
                result_str = self.memory_logger.hget(state_key, agent_id)
                if result_str:
                    # Parse result JSON
                    try:
                        result = json.loads(result_str)
                    except (json.JSONDecodeError, TypeError):
                        result = result_str
                    # Store result in merged dict
                    if isinstance(result, dict):
                        if "result" in result:
                            # If result has a nested result field, use that
                            merged[agent_id] = result["result"]
                        elif "response" in result:
                            # If result has a response field (common for LLM agents), use that
                            merged[agent_id] = {
                                "response": result["response"],
                                "confidence": result.get("confidence", "0.0"),
                                "internal_reasoning": result.get("internal_reasoning", ""),
                                "_metrics": result.get("_metrics", {}),
                                "formatted_prompt": result.get("formatted_prompt", ""),
                            }
                        else:
                            # Otherwise use the whole result
                            merged[agent_id] = result
                    else:
                        # If not a dict, use as is
                        merged[agent_id] = result

                    logger.debug(f"- Merged result for agent {agent_id}")

                    # Store the result in Redis key for direct access
                    fork_group_id = result.get("fork_group", "unknown")
                    agent_key = f"agent_result:{fork_group_id}:{agent_id}"
                    self.memory_logger.set(agent_key, json.dumps(merged[agent_id], default=json_serializer))
                    logger.debug(f"- Stored result for agent {agent_id}")

                    # Store in Redis hash for group tracking
                    group_key = f"fork_group_results:{fork_group_id}"
                    self.memory_logger.hset(group_key, agent_id, json.dumps(merged[agent_id], default=json_serializer))
                    logger.debug(f"- Stored result in group for agent {agent_id}")
                else:
                    logger.warning(
                        f"[ORKA][NODE][JOIN][WARNING] No result found for agent '{agent_id}' in state key '{state_key}'"
                    )
            except Exception as e:
                logger.error(
                    f"[ORKA][NODE][JOIN][ERROR] Error processing result for agent '{agent_id}': {type(e).__name__}: {e}"
                )
                # Add error result to show something went wrong
                merged[agent_id] = {"error": str(e), "error_type": type(e).__name__}

        # Store output using hash operations
        self.memory_logger.hset("join_outputs", self.output_key, json.dumps(merged, default=json_serializer))

        # Clean up state using hash operations.
        # IMPORTANT: Do not delete fork_group_results:<id> because it is used as the stable
        # results table for joins and diagnostics. Only delete legacy transient join state.
        if fork_targets and isinstance(state_key, str) and state_key.startswith("waitfor:"):
            self.memory_logger.hdel(state_key, *fork_targets)

        # Return merged results with status and individual agent results
        result = {
            "status": "done",
            "merged": merged,
            **merged,  # Expose individual agent results at top level
        }

        logger.info(f"🔗 JOIN COMPLETE - Merged {len(merged)} results")
        logger.info(f"🔗 JOIN COMPLETE - Result keys: {list(result.keys())}")
        logger.info(f"🔗 JOIN COMPLETE - Status: {result['status']}")

        # Store the final result in Redis
        join_key = f"join_result:{self.node_id}"
        self.memory_logger.set(join_key, json.dumps(result, default=json_serializer))
        logger.debug(f"- Stored final join result: {join_key}")
        # Log join_key info at info level for easier runtime visibility
        try:
            stored_join = self.memory_logger.get(join_key)
            join_len = len(stored_join) if stored_join else 0
            logger.info(f"🔗 JOIN COMPLETE - join_key='{join_key}', bytes={join_len}")
        except Exception as e:
            logger.warning(f"🔗 JOIN COMPLETE - could not read back join_key '{join_key}': {e}")

        # Store in Redis hash for group tracking
        group_key = f"join_results:{self.node_id}"
        self.memory_logger.hset(group_key, "result", json.dumps(result, default=json_serializer))
        logger.debug(f"- Stored final result in group")

        # Additional info log to help debug missing join_results entries
        try:
            stored = self.memory_logger.hget(group_key, "result")
            stored_val = stored.decode() if isinstance(stored, bytes) else stored
            stored_len = len(stored_val) if stored_val else 0
            logger.info(f"🔗 JOIN COMPLETE - group_key='{group_key}', result_len={stored_len}, join_key='{join_key}'")
            sample = stored_val[:400] if stored_val else ""
            logger.info(f"🔗 JOIN COMPLETE - sample result (truncated): {sample}")
        except Exception as e:
            logger.warning(f"🔗 JOIN COMPLETE - unable to read back stored group result: {e}")

        # Also create an indexed memory entry so template helpers and FT.SEARCH can find the join result
        try:
            trace_id = input_data.get("trace_id") if isinstance(input_data, dict) else None

            # Only attempt memory logging if the backend supports it (RedisStackMemoryLogger does).
            if hasattr(self.memory_logger, "log_memory"):
                memory_content = json.dumps(result, default=json_serializer)
                memory_key = self.memory_logger.log_memory(
                    memory_content,
                    node_id=self.node_id,
                    trace_id=trace_id or join_key,
                    metadata={"event_type": "join_result", "node_id": self.node_id},
                    importance_score=1.0,
                    memory_type="short_term",
                )
                logger.info(f"🔗 JOIN COMPLETE - logged memory key: {memory_key}")
        except Exception as e:
            logger.warning(f"🔗 JOIN COMPLETE - failed to log join memory: {e}")

        return result
