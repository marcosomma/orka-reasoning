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
# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

import asyncio
import inspect
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from time import time
from uuid import uuid4

from jinja2 import Template

from .agents import (
    agents,
    llm_agents,
    local_llm_agents,
    validation_and_structuring_agent,
)
from .fork_group_manager import ForkGroupManager
from .loader import YAMLLoader
from .memory_logger import RedisMemoryLogger
from .nodes import failing_node, failover_node, fork_node, join_node, router_node
from .nodes.memory_reader_node import MemoryReaderNode
from .nodes.memory_writer_node import MemoryWriterNode
from .tools.search_tools import DuckDuckGoTool

logger = logging.getLogger(__name__)

AGENT_TYPES = {
    "binary": agents.BinaryAgent,
    "classification": agents.ClassificationAgent,
    "local_llm": local_llm_agents.LocalLLMAgent,
    "openai-answer": llm_agents.OpenAIAnswerBuilder,
    "openai-binary": llm_agents.OpenAIBinaryAgent,
    "openai-classification": llm_agents.OpenAIClassificationAgent,
    "validate_and_structure": validation_and_structuring_agent.ValidationAndStructuringAgent,
    "duckduckgo": DuckDuckGoTool,
    "router": router_node.RouterNode,
    "failover": failover_node.FailoverNode,
    "failing": failing_node.FailingNode,
    "join": join_node.JoinNode,
    "fork": fork_node.ForkNode,
    "memory": "special_handler",  # This will be handled specially in init_single_agent
}


class Orchestrator:
    """
    The Orchestrator is the core engine that loads a YAML configuration,
    instantiates agents and nodes, and manages the execution of the reasoning workflow.
    It supports parallelism, dynamic routing, and full trace logging.
    """

    def __init__(self, config_path):
        """
        Initialize the Orchestrator with a YAML config file.
        Loads orchestrator and agent configs, sets up memory and fork management.
        """
        self.loader = YAMLLoader(config_path)
        self.loader.validate()

        self.orchestrator_cfg = self.loader.get_orchestrator()
        self.agent_cfgs = self.loader.get_agents()

        self.memory = RedisMemoryLogger()
        self.fork_manager = ForkGroupManager(self.memory.redis)
        self.queue = self.orchestrator_cfg["agents"][:]  # Initial agent execution queue
        self.agents = self._init_agents()  # Dict of agent_id -> agent instance
        self.run_id = str(uuid4())  # Unique run/session ID
        self.step_index = 0  # Step counter for traceability

    def _init_agents(self):
        """
        Instantiate all agents/nodes as defined in the YAML config.
        Returns a dict mapping agent IDs to their instances.
        """
        print(self.orchestrator_cfg)
        print(self.agent_cfgs)
        instances = {}

        def init_single_agent(cfg):
            agent_cls = AGENT_TYPES.get(cfg["type"])
            if not agent_cls:
                raise ValueError(f"Unsupported agent type: {cfg['type']}")

            agent_type = cfg["type"].strip().lower()
            agent_id = cfg["id"]

            # Remove fields not needed for instantiation
            clean_cfg = cfg.copy()
            clean_cfg.pop("id", None)
            clean_cfg.pop("type", None)
            clean_cfg.pop("prompt", None)
            clean_cfg.pop("queue", None)

            print(
                f"{datetime.now()} > [ORKA][INIT] Instantiating agent {agent_id} of type {agent_type}"
            )

            # Special handling for node types with unique constructor signatures
            if agent_type in ("router"):
                # RouterNode expects node_id and params
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(node_id=agent_id, **clean_cfg)

            if agent_type in ("fork", "join"):
                # Fork/Join nodes need memory_logger for group management
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(
                    node_id=agent_id,
                    prompt=prompt,
                    queue=queue,
                    memory_logger=self.memory,
                    **clean_cfg,
                )

            if agent_type == "failover":
                # FailoverNode takes a list of child agent instances
                queue = cfg.get("queue", None)
                child_instances = [
                    init_single_agent(child_cfg)
                    for child_cfg in cfg.get("children", [])
                ]
                return agent_cls(
                    node_id=agent_id, children=child_instances, queue=queue
                )

            if agent_type == "failing":
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(
                    node_id=agent_id, prompt=prompt, queue=queue, **clean_cfg
                )

            # Special handling for memory agent type
            if agent_type == "memory" or agent_cls == "special_handler":
                # Special handling for memory nodes based on operation
                operation = cfg.get("config", {}).get("operation", "read")
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                namespace = cfg.get("namespace", "default")

                # Clean the config to remove any already processed fields
                memory_cfg = clean_cfg.copy()

                if operation == "write":
                    # Use memory writer node for write operations
                    vector_enabled = memory_cfg.get("vector", False)
                    return MemoryWriterNode(
                        node_id=agent_id,
                        prompt=prompt,
                        queue=queue,
                        namespace=namespace,
                        vector=vector_enabled,
                        key_template=cfg.get("key_template"),
                        metadata=cfg.get("metadata", {}),
                    )
                else:  # default to read
                    # Use memory reader node for read operations
                    return MemoryReaderNode(
                        node_id=agent_id,
                        prompt=prompt,
                        queue=queue,
                        namespace=namespace,
                        limit=memory_cfg.get("limit", 10),
                        similarity_threshold=memory_cfg.get(
                            "similarity_threshold", 0.6
                        ),
                    )

            # Special handling for search tools
            if agent_type in ("duckduckgo"):
                prompt = cfg.get("prompt", None)
                queue = cfg.get("queue", None)
                return agent_cls(
                    tool_id=agent_id, prompt=prompt, queue=queue, **clean_cfg
                )

            # Special handling for validation agent
            if agent_type == "validate_and_structure":
                # Create params dictionary with all configuration
                params = {
                    "agent_id": agent_id,
                    "prompt": cfg.get("prompt", ""),
                    "queue": cfg.get("queue", None),
                    "store_structure": cfg.get("store_structure"),
                    **clean_cfg,
                }
                return agent_cls(params=params)

            # Default agent instantiation
            prompt = cfg.get("prompt", None)
            queue = cfg.get("queue", None)
            return agent_cls(agent_id=agent_id, prompt=prompt, queue=queue, **clean_cfg)

        for cfg in self.agent_cfgs:
            agent = init_single_agent(cfg)
            instances[cfg["id"]] = agent

        return instances

    def render_prompt(self, template_str, payload):
        """
        Render a Jinja2 template string with the given payload.
        Used for dynamic prompt construction.
        """
        if not isinstance(template_str, str):
            raise ValueError(
                f"Expected template_str to be str, got {type(template_str)} instead."
            )
        return Template(template_str).render(**payload)

    @staticmethod
    def normalize_bool(value):
        """
        Normalize a value to boolean.
        Accepts bools or strings like 'true', 'yes', etc.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ["true", "yes"]
        return False

    def enqueue_fork(self, agent_ids, fork_group_id):
        """
        Add agent IDs to the execution queue (used for forked/parallel execution).
        """
        self.queue.extend(agent_ids)  # Add to queue keeping order

    @staticmethod
    def build_previous_outputs(logs):
        """
        Build a dictionary of previous agent outputs from the execution logs.
        Used to provide context to downstream agents.
        """
        outputs = {}
        for log in logs:
            agent_id = log["agent_id"]
            payload = log.get("payload", {})

            # Case: regular agent output
            if "result" in payload:
                outputs[agent_id] = payload["result"]

            # Case: JoinNode with merged dict
            if "result" in payload and isinstance(payload["result"], dict):
                merged = payload["result"].get("merged")
                if isinstance(merged, dict):
                    outputs.update(merged)

        return outputs

    async def run(self, input_data):
        """
        Main execution loop for the orchestrator.
        Iterates through the agent queue, passing input and previous outputs,
        handling special node types (router, fork, join, etc.), and logging results.
        """
        logs = []
        queue = self.orchestrator_cfg["agents"][:]

        while queue:
            agent_id = queue.pop(0)
            agent = self.agents[agent_id]
            agent_type = agent.type
            self.step_index += 1

            # Build payload for the agent: current input and all previous outputs
            payload = {
                "input": input_data,
                "previous_outputs": self.build_previous_outputs(logs),
            }
            freezed_payload = json.dumps(
                payload
            )  # Freeze the payload as a string for logging/debug
            print(
                f"{datetime.now()} > [ORKA] {self.step_index} >  Running agent '{agent_id}' of type '{agent_type}', payload: {freezed_payload}"
            )
            log_entry = {
                "agent_id": agent_id,
                "event_type": agent.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
            }

            start_time = time()

            # Handle RouterNode: dynamic routing based on previous outputs
            if agent_type == "routernode":
                decision_key = agent.params.get("decision_key")
                routing_map = agent.params.get("routing_map")
                if decision_key is None:
                    raise ValueError("Router agent must have 'decision_key' in params.")
                raw_decision_value = payload["previous_outputs"].get(decision_key)
                normalized = self.normalize_bool(raw_decision_value)
                payload["previous_outputs"][decision_key] = (
                    "true" if normalized else "false"
                )

                result = agent.run(payload)
                next_agents = result if isinstance(result, list) else [result]
                queue = next_agents

                payload_out = {
                    "input": input_data,
                    "decision_key": decision_key,
                    "decision_value": str(raw_decision_value),
                    "routing_map": str(routing_map),
                    "next_agents": str(next_agents),
                }

            # Handle ForkNode: run multiple agents in parallel branches
            elif agent_type == "forknode":
                result = await agent.run(self, payload)
                fork_targets = agent.config.get("targets", [])
                # Flatten branch steps for parallel execution
                flat_targets = []
                for branch in fork_targets:
                    if isinstance(branch, list):
                        flat_targets.extend(branch)
                    else:
                        flat_targets.append(branch)
                fork_targets = flat_targets

                if not fork_targets:
                    raise ValueError(
                        f"ForkNode '{agent_id}' requires non-empty 'targets' list."
                    )

                fork_group_id = self.fork_manager.generate_group_id(agent_id)
                self.fork_manager.create_group(fork_group_id, fork_targets)
                payload["fork_group_id"] = fork_group_id

                mode = agent.config.get(
                    "mode", "sequential"
                )  # Default to sequential if not set

                payload_out = {
                    "input": input_data,
                    "fork_group": fork_group_id,
                    "fork_targets": fork_targets,
                }
                self.memory.log(
                    agent_id,
                    agent.__class__.__name__,
                    payload_out,
                    step=self.step_index,
                    run_id=self.run_id,
                )

                print(
                    f"{datetime.now()} > [ORKA][FORK][PARALLEL] {self.step_index} >  Running forked agents in parallel for group {fork_group_id}"
                )
                fork_logs = await self.run_parallel_agents(
                    fork_targets, fork_group_id, input_data, payload["previous_outputs"]
                )
                logs.extend(fork_logs)  # Add forked agent logs to the main log

            # Handle JoinNode: wait for all forked agents to finish, then join results
            elif agent_type == "joinnode":
                fork_group_id = self.memory.redis.get(
                    f"fork_group_mapping:{agent.group_id}"
                )
                if fork_group_id:
                    fork_group_id = (
                        fork_group_id.decode()
                        if isinstance(fork_group_id, bytes)
                        else fork_group_id
                    )
                else:
                    fork_group_id = agent.group_id  # fallback

                payload["fork_group_id"] = fork_group_id  # inject
                result = agent.run(payload)
                payload_out = {
                    "input": input_data,
                    "fork_group_id": fork_group_id,
                    "result": result,
                }
                if not fork_group_id:
                    raise ValueError(
                        f"JoinNode '{agent_id}' missing required group_id."
                    )

                # Handle different JoinNode statuses
                if result.get("status") == "waiting":
                    print(
                        f"{datetime.now()} > [ORKA][JOIN][WAITING] {self.step_index} > Node '{agent_id}' is still waiting on fork group: {fork_group_id}"
                    )
                    queue.append(agent_id)
                    self.memory.log(
                        agent_id,
                        agent.__class__.__name__,
                        payload_out,
                        step=self.step_index,
                        run_id=self.run_id,
                    )
                    continue  # Skip logging this round
                elif result.get("status") == "timeout":
                    print(
                        f"{datetime.now()} > [ORKA][JOIN][TIMEOUT] {self.step_index} > Node '{agent_id}' timed out waiting for fork group: {fork_group_id}"
                    )
                    self.memory.log(
                        agent_id,
                        agent.__class__.__name__,
                        payload_out,
                        step=self.step_index,
                        run_id=self.run_id,
                    )
                    # Clean up the fork group even on timeout
                    self.fork_manager.delete_group(fork_group_id)
                    continue
                elif result.get("status") == "done":
                    self.fork_manager.delete_group(
                        fork_group_id
                    )  # Clean up fork group after successful join

            else:
                # Normal Agent: run and handle result
                if agent_type in ("memoryreadernode", "memorywriternode"):
                    # Memory nodes have async run methods
                    result = await agent.run(payload)
                else:
                    # Regular synchronous agent
                    result = agent.run(payload)

                # If agent is waiting (e.g., for async input), re-queue it
                if isinstance(result, dict) and result.get("status") == "waiting":
                    print(
                        f"{datetime.now()} > [ORKA][WAITING] {self.step_index} > Node '{agent_id}' is still waiting: {result.get('received')}"
                    )
                    queue.append(agent_id)
                    continue

                # After normal agent finishes, mark it done if it's part of a fork
                fork_group = payload.get("input", {})
                if fork_group:
                    self.fork_manager.mark_agent_done(fork_group, agent_id)

                # Check if this agent has a next-in-sequence step in its branch
                next_agent = self.fork_manager.next_in_sequence(fork_group, agent_id)
                if next_agent:
                    print(
                        f"{datetime.now()} > [ORKA][FORK-SEQUENCE] {self.step_index} > Agent '{agent_id}' finished. Enqueuing next in sequence: '{next_agent}'"
                    )
                    self.enqueue_fork([next_agent], fork_group)

                payload_out = {"input": input_data, "result": result}
                if hasattr(agent, "prompt") and agent.prompt:
                    payload_out["prompt"] = agent.prompt

            # Log the result and timing for this step
            duration = round(time() - start_time, 4)
            payload_out["previous_outputs"] = payload["previous_outputs"]
            log_entry["duration"] = duration
            log_entry["payload"] = payload_out
            logs.append(log_entry)
            if agent_type != "forknode":
                self.memory.log(
                    agent_id,
                    agent.__class__.__name__,
                    payload_out,
                    step=self.step_index,
                    run_id=self.run_id,
                )

            print(
                f"{datetime.now()} > [ORKA] {self.step_index} > Agent '{agent_id}' returned: {result}"
            )

        # Save logs to file at the end of the run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")
        self.memory.save_to_file(log_path)

        return logs

    async def _run_agent_async(self, agent_id, input_data, previous_outputs):
        """
        Run a single agent asynchronously.
        """
        agent = self.agents[agent_id]
        payload = {"input": input_data, "previous_outputs": previous_outputs}

        # Inspect the run method to see if it needs orchestrator
        run_method = agent.run
        sig = inspect.signature(run_method)
        needs_orchestrator = len(sig.parameters) > 1  # More than just 'self'
        is_async = inspect.iscoroutinefunction(run_method)

        if needs_orchestrator:
            # Node that needs orchestrator
            result = run_method(self, payload)
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

    async def _run_branch_async(self, branch_agents, input_data, previous_outputs):
        """
        Run a sequence of agents in a branch sequentially.
        """
        branch_results = {}
        for agent_id in branch_agents:
            agent_id, result = await self._run_agent_async(
                agent_id, input_data, previous_outputs
            )
            branch_results[agent_id] = result
            # Update previous_outputs for the next agent in the branch
            previous_outputs = {**previous_outputs, **branch_results}
        return branch_results

    async def run_parallel_agents(
        self, agent_ids, fork_group_id, input_data, previous_outputs
    ):
        """
        Run multiple branches in parallel, with agents within each branch running sequentially.
        Returns a list of log entries for each forked agent.
        """
        # Get the fork node to understand the branch structure
        fork_node_id = (
            fork_group_id.split("_")[0] + "_" + fork_group_id.split("_")[1]
        )  # Get 'fork_temporal' from 'fork_temporal_1746645176'
        fork_node = self.agents[fork_node_id]
        branches = fork_node.targets

        # Run each branch in parallel
        branch_tasks = [
            self._run_branch_async(branch, input_data, previous_outputs)
            for branch in branches
        ]

        # Wait for all branches to complete
        branch_results = await asyncio.gather(*branch_tasks)

        # Process results and create logs
        forked_step_index = 0
        result_logs = []

        # Flatten branch results into a single list of (agent_id, result) pairs
        all_results = []
        for branch_result in branch_results:
            all_results.extend(branch_result.items())

        for agent_id, result in all_results:
            forked_step_index += 1
            step_index = f"{self.step_index}[{forked_step_index}]"

            # Ensure result is awaited if it's a coroutine
            if asyncio.iscoroutine(result):
                result = await result

            # Save result to Redis for JoinNode
            join_state_key = "waitfor:join_parallel_checks:inputs"
            self.memory.hset(join_state_key, agent_id, json.dumps(result))

            # Create log entry
            log_data = {
                "agent_id": agent_id,
                "event_type": f"ForkedAgent-{self.agents[agent_id].__class__.__name__}",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {"result": result},
                "previous_outputs": previous_outputs,
                "step": step_index,
                "run_id": self.run_id,
            }
            result_logs.append(log_data)

            # Log to memory
            self.memory.log(
                agent_id,
                f"ForkedAgent-{self.agents[agent_id].__class__.__name__}",
                {"result": result},
                step=step_index,
                run_id=self.run_id,
                previous_outputs=previous_outputs,
            )

        return result_logs
