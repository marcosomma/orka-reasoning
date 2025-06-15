# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

import asyncio
import inspect
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from ..utils.common_utils import CommonUtils

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """
    Handles parallel execution of agents in fork/join scenarios.
    """

    def __init__(self, agent_manager=None, memory_logger=None):
        """
        Initialize the parallel executor.

        Args:
            agent_manager: Agent manager instance for accessing agents
            memory_logger: Memory logger for storing execution data
        """
        self.agent_manager = agent_manager
        self.memory_logger = memory_logger

    async def run_parallel_agents(
        self,
        agent_ids,
        fork_group_id,
        input_data,
        previous_outputs,
        agents,
        run_id,
        step_index,
    ):
        """
        Run multiple branches in parallel, with agents within each branch running sequentially.
        Returns a list of log entries for each forked agent.

        Args:
            agent_ids: List of agent IDs to run in parallel
            fork_group_id: ID of the fork group
            input_data: Input data for agents
            previous_outputs: Previous agent outputs
            agents: Dictionary of agent instances
            run_id: Current run ID
            step_index: Current step index

        Returns:
            list: Log entries for forked agents
        """
        # Get the fork node to understand the branch structure
        # Fork group ID format: {node_id}_{timestamp}, so we need to remove the timestamp
        fork_node_id = "_".join(
            fork_group_id.split("_")[:-1],
        )  # Remove the last part (timestamp)
        fork_node = agents[fork_node_id]
        branches = fork_node.targets

        # Run each branch in parallel
        branch_tasks = [
            self._run_branch_async(branch, input_data, previous_outputs, agents)
            for branch in branches
        ]

        # Wait for all branches to complete
        branch_results = await asyncio.gather(*branch_tasks)

        # Process results and create logs
        forked_step_index = 0
        result_logs = []
        updated_previous_outputs = previous_outputs.copy()

        # Flatten branch results into a single list of (agent_id, result) pairs
        all_results = []
        for branch_result in branch_results:
            all_results.extend(branch_result.items())

        for agent_id, result in all_results:
            forked_step_index += 1
            step_index_str = f"{step_index}[{forked_step_index}]"

            # Ensure result is awaited if it's a coroutine
            if asyncio.iscoroutine(result):
                result = await result

            # Save result to Redis for JoinNode
            join_state_key = "waitfor:join_parallel_checks:inputs"
            self.memory_logger.hset(join_state_key, agent_id, json.dumps(result))

            # Create log entry with current previous_outputs (before updating with this agent's result)
            payload_data = {"result": result}
            agent = agents[agent_id]
            payload_context = {
                "input": input_data,
                "previous_outputs": updated_previous_outputs,
            }
            CommonUtils.add_prompt_to_payload(agent, payload_data, payload_context)

            log_data = {
                "agent_id": agent_id,
                "event_type": f"ForkedAgent-{agents[agent_id].__class__.__name__}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": payload_data,
                "previous_outputs": updated_previous_outputs.copy(),
                "step": step_index_str,
                "run_id": run_id,
            }
            result_logs.append(log_data)

            # Log to memory
            self.memory_logger.log(
                agent_id,
                f"ForkedAgent-{agents[agent_id].__class__.__name__}",
                payload_data,
                step=step_index_str,
                run_id=run_id,
                previous_outputs=updated_previous_outputs.copy(),
            )

            # Update previous_outputs with this agent's result AFTER logging
            updated_previous_outputs[agent_id] = result

        return result_logs

    async def _run_branch_async(self, branch_agents, input_data, previous_outputs, agents):
        """
        Run a sequence of agents in a branch sequentially.

        Args:
            branch_agents: List of agent IDs in the branch
            input_data: Input data for agents
            previous_outputs: Previous agent outputs
            agents: Dictionary of agent instances

        Returns:
            dict: Results from all agents in the branch
        """
        branch_results = {}
        for agent_id in branch_agents:
            agent_id, result = await self._run_agent_async(
                agent_id,
                input_data,
                previous_outputs,
                agents,
            )
            branch_results[agent_id] = result
            # Update previous_outputs for the next agent in the branch
            previous_outputs = {**previous_outputs, **branch_results}
        return branch_results

    async def _run_agent_async(self, agent_id, input_data, previous_outputs, agents):
        """
        Run a single agent asynchronously.

        Args:
            agent_id: ID of the agent to run
            input_data: Input data for the agent
            previous_outputs: Previous agent outputs
            agents: Dictionary of agent instances

        Returns:
            tuple: (agent_id, result)
        """
        agent = agents[agent_id]
        payload = {"input": input_data, "previous_outputs": previous_outputs}

        # Render prompt before running agent if agent has a prompt
        CommonUtils.render_agent_prompt(agent, payload)

        # Inspect the run method to see if it needs orchestrator
        run_method = agent.run
        sig = inspect.signature(run_method)
        needs_orchestrator = len(sig.parameters) > 1  # More than just 'self'
        is_async = inspect.iscoroutinefunction(run_method)

        if needs_orchestrator:
            # Node that needs orchestrator - this would need to be handled differently
            # For now, we'll assume it doesn't need orchestrator for parallel execution
            result = run_method(payload)
            if is_async or asyncio.iscoroutine(result):
                result = await result
        elif is_async:
            # Async node/agent that doesn't need orchestrator
            result = await run_method(payload)
        else:
            # Synchronous agent
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, run_method, payload)

        return agent_id, result

    def validate_branch_structure(self, branches):
        """
        Validate the structure of branches for parallel execution.

        Args:
            branches: List of branches to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(branches, list):
            logger.error("Branches must be a list")
            return False

        for i, branch in enumerate(branches):
            if not isinstance(branch, list):
                logger.error(f"Branch {i} must be a list of agent IDs")
                return False

            if not branch:  # Empty branch
                logger.warning(f"Branch {i} is empty")

            for agent_id in branch:
                if not isinstance(agent_id, str):
                    logger.error(f"Agent ID in branch {i} must be a string: {agent_id}")
                    return False

        return True

    def get_branch_dependencies(self, branches):
        """
        Analyze dependencies between branches.

        Args:
            branches: List of branches

        Returns:
            dict: Dependency information
        """
        all_agents = set()
        branch_agents = {}

        for i, branch in enumerate(branches):
            branch_agents[i] = set(branch)
            all_agents.update(branch)

        # Check for agent conflicts (same agent in multiple branches)
        conflicts = []
        for i, branch_i in branch_agents.items():
            for j, branch_j in branch_agents.items():
                if i < j:  # Avoid duplicate comparisons
                    overlap = branch_i.intersection(branch_j)
                    if overlap:
                        conflicts.append(
                            {
                                "branches": [i, j],
                                "conflicting_agents": list(overlap),
                            },
                        )

        return {
            "total_agents": len(all_agents),
            "branch_count": len(branches),
            "conflicts": conflicts,
            "has_conflicts": len(conflicts) > 0,
        }
