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
from typing import Any, Dict, List, Optional

from ..memory.redisstack_logger import RedisStackMemoryLogger
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class ForkNode(BaseNode):
    """
    A node that splits the workflow into parallel branches.
    Can handle both sequential and parallel execution of agent branches.
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
        Initialize the fork node.

        Args:
            node_id (str): Unique identifier for the node.
            prompt (str, optional): Prompt or instruction for the node.
            queue (list, optional): Queue of agents or nodes to be processed.
            memory_logger (RedisStackMemoryLogger, optional): Logger for tracking node state.
            **kwargs: Additional configuration parameters.
        """
        super().__init__(node_id=node_id, prompt=prompt, queue=queue, **kwargs)
        self.memory_logger = memory_logger
        self.targets = kwargs.get("targets", [])  # Store the fork branches
        self.config = kwargs  # Store config explicitly
        self.mode = kwargs.get("mode", "sequential")  # Default to sequential execution

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the fork operation by creating parallel branches.

        Args:
            context: Context data for the fork operation, must include orchestrator.

        Returns:
            dict: Status and fork group information.

        Raises:
            ValueError: If no targets are specified or orchestrator is missing.
        """
        targets = self.config.get("targets", [])
        if not targets:
            raise ValueError(f"ForkNode '{self.node_id}' requires non-empty 'targets' list.")

        # Get orchestrator from context
        orchestrator = context.get("orchestrator")
        if not orchestrator:
            raise ValueError("ForkNode requires orchestrator in context")

        # Generate a unique ID for this fork group
        fork_group_id = orchestrator.fork_manager.generate_group_id(self.node_id)
        all_flat_agents = []

        # Process each branch in the targets
        for branch in self.targets:
            if isinstance(branch, list):
                # Branch is a sequence - only queue the FIRST agent now
                first_agent = branch[0]
                if self.mode == "sequential":
                    # For sequential mode, only queue the first agent
                    orchestrator.enqueue_fork([first_agent], fork_group_id)
                    orchestrator.fork_manager.track_branch_sequence(fork_group_id, branch)
                    logger.debug(f"- Queued first agent {first_agent} in sequential mode")
                else:
                    # For parallel mode, queue all agents
                    orchestrator.enqueue_fork(branch, fork_group_id)
                    logger.debug(f"- Queued all agents {branch} in parallel mode")
                all_flat_agents.extend(branch)
            else:
                # Single agent, flat structure (fallback)
                orchestrator.enqueue_fork([branch], fork_group_id)
                all_flat_agents.append(branch)
                logger.debug(f"- Queued single agent {branch}")

        # Create the fork group with all agents
        orchestrator.fork_manager.create_group(fork_group_id, all_flat_agents)
        logger.debug(f"- Created fork group {fork_group_id} with agents {all_flat_agents}")

        if self.memory_logger is not None:
            # Store fork group mapping and agent list using backend-agnostic methods
            self.memory_logger.hset(f"fork_group_mapping:{self.node_id}", "group_id", fork_group_id)
            self.memory_logger.sadd(f"fork_group:{fork_group_id}", *all_flat_agents)

            # Store initial state for join node
            state_key = "waitfor:join_parallel_checks:inputs"
            for agent_id in all_flat_agents:
                # Initialize empty result for each agent with proper structure
                initial_result = {
                    "response": "",
                    "confidence": "0.0",
                    "internal_reasoning": "",
                    "_metrics": {},
                    "formatted_prompt": "",
                    "memories": [],
                    "query": "",
                    "backend": "",
                    "search_type": "",
                    "num_results": 0,
                    "status": "pending",
                    "fork_group": fork_group_id,
                    "agent_id": agent_id,
                }

                # Store in Redis hash for join node
                self.memory_logger.hset(state_key, agent_id, json.dumps(initial_result))
                logger.debug(f"- Initialized state for agent {agent_id}")

                # Store in Redis key for direct access
                agent_key = f"agent_result:{fork_group_id}:{agent_id}"
                self.memory_logger.set(agent_key, json.dumps(initial_result))
                logger.debug(f"- Stored initial result for agent {agent_id}")

                # Store in Redis hash for group tracking
                group_key = f"fork_group_results:{fork_group_id}"
                self.memory_logger.hset(group_key, agent_id, json.dumps(initial_result))
                logger.debug(f"- Stored initial result in group for agent {agent_id}")

        # Return fork status with group info
        return {
            "status": "forked",
            "fork_group": fork_group_id,
            "agents": all_flat_agents,
            "mode": self.mode,
            "initial_state": {
                "state_key": state_key,
                "group_key": f"fork_group_results:{fork_group_id}",
            },
        }
