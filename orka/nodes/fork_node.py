# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning
from .base_node import BaseNode


class ForkNode(BaseNode):
    """
    A node that splits the workflow into parallel branches.
    Can handle both sequential and parallel execution of agent branches.
    """

    def __init__(self, node_id, prompt=None, queue=None, memory_logger=None, **kwargs):
        """
        Initialize the fork node.

        Args:
            node_id (str): Unique identifier for the node.
            prompt (str, optional): Prompt or instruction for the node.
            queue (list, optional): Queue of agents or nodes to be processed.
            memory_logger: Logger for tracking node state.
            **kwargs: Additional configuration parameters.
        """
        super().__init__(node_id=node_id, prompt=prompt, queue=queue, **kwargs)
        self.memory_logger = memory_logger
        self.targets = kwargs.get("targets", [])  # Store the fork branches
        self.config = kwargs  # Store config explicitly
        self.mode = kwargs.get("mode", "sequential")  # Default to sequential execution

    async def run(self, orchestrator, context):
        """
        Execute the fork operation by creating parallel branches.

        Args:
            orchestrator: The orchestrator instance managing the workflow.
            context: Context data for the fork operation.

        Returns:
            dict: Status and fork group information.

        Raises:
            ValueError: If no targets are specified.
        """
        targets = self.config.get("targets", [])
        if not targets:
            raise ValueError(f"ForkNode '{self.node_id}' requires non-empty 'targets' list.")

        # Generate a unique ID for this fork group
        fork_group_id = orchestrator.fork_manager.generate_group_id(self.node_id)
        all_flat_agents = []  # Store all agents in a flat list

        # Process each branch in the targets
        for branch in self.targets:
            if isinstance(branch, list):
                # Branch is a sequence - only queue the FIRST agent now
                first_agent = branch[0]
                if self.mode == "sequential":
                    # For sequential mode, only queue the first agent
                    orchestrator.enqueue_fork([first_agent], fork_group_id)
                    orchestrator.fork_manager.track_branch_sequence(fork_group_id, branch)
                else:
                    # For parallel mode, queue all agents
                    orchestrator.enqueue_fork(branch, fork_group_id)
                all_flat_agents.extend(branch)
            else:
                # Single agent, flat structure (fallback)
                orchestrator.enqueue_fork([branch], fork_group_id)
                all_flat_agents.append(branch)

            # Create the fork group with all agents
            orchestrator.fork_manager.create_group(fork_group_id, all_flat_agents)

        # Store fork group mapping and agent list using backend-agnostic methods
        self.memory_logger.hset(f"fork_group_mapping:{self.node_id}", "group_id", fork_group_id)
        self.memory_logger.sadd(f"fork_group:{fork_group_id}", *all_flat_agents)
        return {"status": "forked", "fork_group": fork_group_id}
