# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

import logging
from datetime import datetime

from ..utils.common_utils import CommonUtils

logger = logging.getLogger(__name__)


class AgentExecutor:
    """
    Handles execution of individual agents with proper error handling and state tracking.
    """

    def __init__(self, fork_manager=None, memory_logger=None, orchestrator_queue=None, agents=None):
        """
        Initialize the agent executor.

        Args:
            fork_manager: Fork group manager for handling parallel execution
            memory_logger: Memory logger for storing execution data
            orchestrator_queue: Reference to the orchestrator's execution queue
            agents: Dictionary of available agents for validation
        """
        self.fork_manager = fork_manager
        self.memory_logger = memory_logger
        self.orchestrator_queue = orchestrator_queue
        self.agents = agents or {}

    def enqueue_fork(self, agent_ids, fork_group_id):
        """
        Add agent IDs to the execution queue (used for forked/parallel execution).

        Args:
            agent_ids: List of agent IDs to add to the queue
            fork_group_id: ID of the fork group (for tracking)
        """
        if self.orchestrator_queue is not None:
            self.orchestrator_queue.extend(agent_ids)  # Add to queue keeping order

    async def execute_single_agent(
        self,
        agent_id,
        agent,
        agent_type,
        payload,
        input_data,
        queue,
        logs,
        step_index,
    ):
        """
        Execute a single agent with proper error handling and status tracking.

        Args:
            agent_id: ID of the agent to execute
            agent: Agent instance
            agent_type: Type of the agent
            payload: Input payload for the agent
            input_data: Original input data
            queue: Execution queue
            logs: Execution logs
            step_index: Current step index

        Returns:
            dict: Result of the agent execution
        """
        # Handle RouterNode: dynamic routing based on previous outputs
        if agent_type == "routernode":
            return await self._execute_router_node(agent, payload, input_data, queue)

        # Handle ForkNode: run multiple agents in parallel branches
        elif agent_type == "forknode":
            return await self._execute_fork_node(
                agent_id,
                agent,
                payload,
                input_data,
                logs,
                step_index,
            )

        # Handle JoinNode: wait for all forked agents to finish, then join results
        elif agent_type == "joinnode":
            return await self._execute_join_node(agent_id, agent, payload, input_data, queue)

        else:
            # Normal Agent: run and handle result
            return await self._execute_normal_agent(
                agent_id,
                agent,
                agent_type,
                payload,
                input_data,
            )

    async def _execute_router_node(self, agent, payload, input_data, queue):
        """Execute a router node."""
        decision_key = agent.params.get("decision_key")
        routing_map = agent.params.get("routing_map")

        if decision_key is None:
            raise ValueError("Router agent must have 'decision_key' in params.")

        raw_decision_value = payload["previous_outputs"].get(decision_key)
        normalized = CommonUtils.normalize_bool(raw_decision_value)
        payload["previous_outputs"][decision_key] = "true" if normalized else "false"

        result = agent.run(payload)
        next_agents = result if isinstance(result, list) else [result]

        # For router nodes, we need to update the queue
        queue.clear()
        queue.extend(next_agents)

        payload_out = {
            "input": input_data,
            "decision_key": decision_key,
            "decision_value": str(raw_decision_value),
            "routing_map": str(routing_map),
            "next_agents": str(next_agents),
        }
        CommonUtils.add_prompt_to_payload(agent, payload_out, payload)
        return payload_out

    async def _execute_fork_node(self, agent_id, agent, payload, input_data, logs, step_index):
        """Execute a fork node."""
        # Validate fork targets before execution
        # Check both agent.targets (direct attribute) and agent.config.get("targets", [])
        fork_targets = getattr(agent, "targets", agent.config.get("targets", []))

        # Flatten branch steps for validation
        flat_targets = []
        for branch in fork_targets:
            if isinstance(branch, list):
                flat_targets.extend(branch)
            else:
                flat_targets.append(branch)

        # Check if all targets exist in the agents dictionary
        missing_targets = []
        for target in flat_targets:
            if target not in self.agents:
                missing_targets.append(target)

        if missing_targets:
            error_msg = f"Fork node '{agent_id}' has invalid targets: {missing_targets}"
            # Return the failed result directly - orchestrator will wrap it in payload_out
            return {
                "status": "failed",
                "error": error_msg,
                "fork_targets": fork_targets,
            }

        # The fork node expects an orchestrator-like object with enqueue_fork method
        # We'll create a mock orchestrator object that delegates to our methods
        mock_orchestrator = type(
            "MockOrchestrator",
            (),
            {
                "fork_manager": self.fork_manager,
                "enqueue_fork": self.enqueue_fork,
            },
        )()

        result = await agent.run(mock_orchestrator, payload)

        # Extract fork information from the result
        fork_group_id = result.get("fork_group")
        if not fork_group_id:
            raise ValueError(f"ForkNode '{agent_id}' did not return a valid fork_group.")

        payload_out = {
            "input": input_data,
            "fork_group": fork_group_id,
            "fork_targets": agent.config.get("targets", []),
        }
        CommonUtils.add_prompt_to_payload(agent, payload_out, payload)

        self.memory_logger.log(
            agent_id,
            agent.__class__.__name__,
            payload_out,
            step=step_index,
            run_id=getattr(self, "run_id", "unknown"),
        )

        print(
            f"{datetime.now()} > [ORKA][FORK][PARALLEL] {step_index} > Running forked agents in parallel for group {fork_group_id}",
        )

        return payload_out

    async def _execute_join_node(self, agent_id, agent, payload, input_data, queue):
        """Execute a join node."""
        # First try to get fork_group_id from previous outputs (from the fork node)
        fork_group_id = None
        previous_outputs = payload.get("previous_outputs", {})

        # Look for the fork node output that matches our group_id
        for output_key, output_data in previous_outputs.items():
            if output_key == agent.group_id and isinstance(output_data, dict):
                fork_group_id = output_data.get("fork_group")
                if fork_group_id:
                    break

        # Fallback to memory lookup
        if not fork_group_id:
            fork_group_id = self.memory_logger.hget(
                f"fork_group_mapping:{agent.group_id}",
                "group_id",
            )
            if fork_group_id:
                fork_group_id = (
                    fork_group_id.decode() if isinstance(fork_group_id, bytes) else fork_group_id
                )

        # Final fallback to agent.group_id
        if not fork_group_id:
            fork_group_id = agent.group_id

        payload["fork_group_id"] = fork_group_id  # inject
        result = agent.run(payload)

        payload_out = {
            "input": input_data,
            "fork_group_id": fork_group_id,
            "result": result,
        }
        CommonUtils.add_prompt_to_payload(agent, payload_out, payload)

        if not fork_group_id:
            raise ValueError(f"JoinNode '{agent_id}' missing required group_id.")

        # Handle different JoinNode statuses
        if result.get("status") == "waiting":
            print(
                f"{datetime.now()} > [ORKA][JOIN][WAITING] > Node '{agent_id}' is still waiting on fork group: {fork_group_id}",
            )
            queue.append(agent_id)
            self.memory_logger.log(
                agent_id,
                agent.__class__.__name__,
                payload_out,
                step=getattr(self, "step_index", 0),
                run_id=getattr(self, "run_id", "unknown"),
            )
            return {"status": "waiting", "result": result}

        elif result.get("status") == "timeout":
            print(
                f"{datetime.now()} > [ORKA][JOIN][TIMEOUT] > Node '{agent_id}' timed out waiting for fork group: {fork_group_id}",
            )
            self.memory_logger.log(
                agent_id,
                agent.__class__.__name__,
                payload_out,
                step=getattr(self, "step_index", 0),
                run_id=getattr(self, "run_id", "unknown"),
            )
            # Clean up the fork group even on timeout
            self.fork_manager.delete_group(fork_group_id)
            return {"status": "timeout", "result": result}

        elif result.get("status") == "done":
            self.fork_manager.delete_group(
                fork_group_id,
            )  # Clean up fork group after successful join

        return payload_out

    async def _execute_normal_agent(self, agent_id, agent, agent_type, payload, input_data):
        """Execute a normal agent."""
        # Render prompt before running agent if agent has a prompt
        CommonUtils.render_agent_prompt(agent, payload)

        if agent_type in ("memoryreadernode", "memorywriternode"):
            # Memory nodes have async run methods
            result = await agent.run(payload)
        else:
            # Regular synchronous agent
            result = agent.run(payload)

        # If agent is waiting (e.g., for async input), return waiting status
        if isinstance(result, dict) and result.get("status") == "waiting":
            print(
                f"{datetime.now()} > [ORKA][WAITING] > Node '{agent_id}' is still waiting: {result.get('received')}",
            )
            return {"status": "waiting", "result": result}

        # After normal agent finishes, mark it done if it's part of a fork
        fork_group = payload.get("input", {})
        if fork_group and self.fork_manager:
            self.fork_manager.mark_agent_done(fork_group, agent_id)

        # Check if this agent has a next-in-sequence step in its branch
        if self.fork_manager:
            next_agent = self.fork_manager.next_in_sequence(fork_group, agent_id)
            if next_agent:
                print(
                    f"{datetime.now()} > [ORKA][FORK-SEQUENCE] > Agent '{agent_id}' finished. Enqueuing next in sequence: '{next_agent}'",
                )
                # This would need to be handled by the orchestrator
                # self.enqueue_fork([next_agent], fork_group)

        payload_out = {"input": input_data, "result": result}
        CommonUtils.add_prompt_to_payload(agent, payload_out, payload)
        return payload_out

    async def run_agent_async(self, agent_id, input_data, previous_outputs):
        """
        Run a single agent asynchronously.

        Args:
            agent_id: ID of the agent to run
            input_data: Input data for the agent
            previous_outputs: Previous agent outputs

        Returns:
            tuple: (agent_id, result)
        """
        # This would need access to the agents dict from orchestrator
        # agent = self.agents[agent_id]
        # payload = {"input": input_data, "previous_outputs": previous_outputs}

        # # Render prompt before running agent if agent has a prompt
        # CommonUtils.render_agent_prompt(agent, payload)

        # # Inspect the run method to see if it needs orchestrator
        # run_method = agent.run
        # sig = inspect.signature(run_method)
        # needs_orchestrator = len(sig.parameters) > 1  # More than just 'self'
        # is_async = inspect.iscoroutinefunction(run_method)

        # if needs_orchestrator:
        #     # Node that needs orchestrator
        #     result = run_method(self, payload)
        #     if is_async or asyncio.iscoroutine(result):
        #         result = await result
        # elif is_async:
        #     # Async node/agent that doesn't need orchestrator
        #     result = await run_method(payload)
        # else:
        #     # Synchronous agent
        #     loop = asyncio.get_event_loop()
        #     with ThreadPoolExecutor() as pool:
        #         result = await loop.run_in_executor(pool, run_method, payload)

        # return agent_id, result

        # Placeholder - this method needs to be implemented with access to agents
        raise NotImplementedError(
            "This method needs access to the agents dictionary from orchestrator",
        )

    def get_agent_type_string(self, agent):
        """
        Get the agent type string for an agent instance.

        Args:
            agent: Agent instance

        Returns:
            str: Agent type string
        """
        class_name = agent.__class__.__name__.lower()

        # Map class names to agent type strings
        type_mapping = {
            "routernode": "routernode",
            "forknode": "forknode",
            "joinnode": "joinnode",
            "memoryreadernode": "memoryreadernode",
            "memorywriternode": "memorywriternode",
            "failovernode": "failovernode",
            "failingnode": "failingnode",
        }

        return type_mapping.get(class_name, class_name)
