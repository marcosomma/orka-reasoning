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

"""
🎼 **Execution Engine** - The Conductor of Your AI Orchestra
=========================================================

The ExecutionEngine is the heart of OrKa's orchestration capabilities, coordinating
complex multi-agent workflows with precision, reliability, and intelligence.

**Core Orchestration Philosophy:**
Think of the ExecutionEngine as a world-class conductor leading a symphony orchestra.
Each agent is a specialized musician, and the engine ensures perfect timing,
coordination, and harmony across the entire performance.

**Execution Strategies:**
- **Sequential**: Step-by-step processing with full context propagation
- **Parallel**: Simultaneous execution for maximum speed and efficiency
- **Decision-tree**: Dynamic branching based on runtime conditions
- **Pipeline**: Streaming processing for large-scale data workflows

**Advanced Capabilities:**
- 🔄 **Intelligent Retry**: Exponential backoff with context preservation
- 🛡️ **Circuit Breaker**: Automatic failure isolation and recovery
- ⚡ **Resource Pooling**: Efficient connection and agent management
- 📊 **Real-time Monitoring**: Performance metrics and bottleneck detection
- 🎯 **Distributed Execution**: Scale across multiple workers and machines

**Real-world Applications:**
- Customer service workflows with intelligent escalation
- Content processing pipelines with quality assurance
- Research automation with multi-source synthesis
- Real-time decision systems with complex logic
"""

import asyncio
import inspect
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from time import time

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    🎼 **The conductor of your AI orchestra** - coordinates complex multi-agent workflows.

    **What makes execution intelligent:**
    - **Perfect Timing**: Orchestrates agent execution with precise coordination
    - **Context Flow**: Maintains rich context across all workflow steps
    - **Fault Tolerance**: Graceful handling of failures with automatic recovery
    - **Performance Intelligence**: Real-time optimization and resource management
    - **Scalable Architecture**: From single-threaded to distributed execution

    **Execution Patterns:**

    **1. Sequential Processing** (most common):
    ```yaml
    orchestrator:
      strategy: sequential
      agents: [classifier, router, processor, responder]
    # Each agent receives full context from all previous steps
    ```

    **2. Parallel Processing** (for speed):
    ```yaml
    orchestrator:
      strategy: parallel
      agents: [validator_1, validator_2, validator_3]
    # All agents run simultaneously, results aggregated
    ```

    **3. Decision Tree** (for complex logic):
    ```yaml
    orchestrator:
      strategy: decision-tree
      agents: [classifier, router, [path_a, path_b], aggregator]
    # Dynamic routing based on classification results
    ```

    **Advanced Features:**

    **🔄 Intelligent Retry Logic:**
    - Exponential backoff for transient failures
    - Context preservation across retry attempts
    - Configurable retry policies per agent type
    - Partial success handling for complex workflows

    **📊 Real-time Monitoring:**
    - Agent execution timing and performance metrics
    - LLM token usage and cost tracking
    - Memory usage and optimization insights
    - Error pattern detection and alerting

    **⚡ Resource Management:**
    - Connection pooling for external services
    - Agent lifecycle management and cleanup
    - Memory optimization for long-running workflows
    - Graceful shutdown and resource release

    **🎯 Production Features:**
    - Distributed execution across multiple workers
    - Load balancing and auto-scaling capabilities
    - Health checks and service discovery
    - Comprehensive logging and audit trails

    **Perfect for:**
    - Multi-step AI reasoning workflows
    - High-throughput content processing pipelines
    - Real-time decision systems with complex branching
    - Fault-tolerant distributed AI applications
    """

    async def run(self, input_data):
        """
        Main entry point for orchestrator execution.
        Creates empty logs list and delegates to the comprehensive error handling method.
        """
        logs = []
        try:
            return await self._run_with_comprehensive_error_handling(input_data, logs)
        except Exception as e:
            self._record_error(
                "orchestrator_run",
                "orchestrator",
                f"Fatal error during run: {e}",
                e,
                recovery_action="abort",
            )
            self.error_telemetry["execution_status"] = "failed"
            self.error_telemetry["critical_failures"].append(
                {"error": str(e), "timestamp": datetime.now(UTC).isoformat()},
            )
            self._save_error_report(logs, e)
            raise

    async def _run_with_comprehensive_error_handling(self, input_data, logs):
        """
        Main execution loop with comprehensive error handling wrapper.
        """
        queue = self.orchestrator_cfg["agents"][:]

        while queue:
            agent_id = queue.pop(0)

            try:
                agent = self.agents[agent_id]
                agent_type = agent.type
                self.step_index += 1

                # Build payload for the agent: current input and all previous outputs
                payload = {
                    "input": input_data,
                    "previous_outputs": self.build_previous_outputs(logs),
                }
                freezed_payload = json.dumps(
                    payload,
                )  # Freeze the payload as a string for logging/debug
                print(
                    f"{datetime.now()} > [ORKA] {self.step_index} >  Running agent '{agent_id}' of type '{agent_type}', payload: {freezed_payload}",
                )
                log_entry = {
                    "agent_id": agent_id,
                    "event_type": agent.__class__.__name__,
                    "timestamp": datetime.now(UTC).isoformat(),
                }

                start_time = time()

                # Attempt to run agent with retry logic
                max_retries = 3
                retry_count = 0
                agent_result = None

                while retry_count <= max_retries:
                    try:
                        agent_result = await self._execute_single_agent(
                            agent_id,
                            agent,
                            agent_type,
                            payload,
                            input_data,
                            queue,
                            logs,
                        )

                        # If we had retries, record partial success
                        if retry_count > 0:
                            self._record_partial_success(agent_id, retry_count)

                        # Handle waiting status - re-queue the agent
                        if isinstance(agent_result, dict) and agent_result.get("status") in [
                            "waiting",
                            "timeout",
                        ]:
                            if agent_result.get("status") == "waiting":
                                queue.append(agent_id)  # Re-queue for later
                            # For these statuses, we should continue to the next agent in queue
                            continue

                        break  # Success - exit retry loop

                    except Exception as agent_error:
                        retry_count += 1
                        self._record_retry(agent_id)
                        self._record_error(
                            "agent_execution",
                            agent_id,
                            f"Attempt {retry_count} failed: {agent_error}",
                            agent_error,
                            recovery_action="retry" if retry_count <= max_retries else "skip",
                        )

                        if retry_count <= max_retries:
                            print(
                                f"🔄 [ORKA-RETRY] Agent {agent_id} failed, retrying ({retry_count}/{max_retries})",
                            )
                            await asyncio.sleep(1)  # Brief delay before retry
                        else:
                            print(
                                f"❌ [ORKA-SKIP] Agent {agent_id} failed {max_retries} times, skipping",
                            )
                            # Create a failure result
                            agent_result = {
                                "status": "failed",
                                "error": str(agent_error),
                                "retries_attempted": retry_count - 1,
                            }
                            break

                # Process the result (success or failure)
                if agent_result is not None:
                    # Log the result and timing for this step
                    duration = round(time() - start_time, 4)
                    payload_out = {"input": input_data, "result": agent_result}
                    payload_out["previous_outputs"] = payload["previous_outputs"]
                    log_entry["duration"] = duration

                    # Extract LLM metrics if present (even from failed agents)
                    try:
                        llm_metrics = self._extract_llm_metrics(agent, agent_result)
                        if llm_metrics:
                            log_entry["llm_metrics"] = llm_metrics
                    except Exception as metrics_error:
                        self._record_error(
                            "metrics_extraction",
                            agent_id,
                            f"Failed to extract metrics: {metrics_error}",
                            metrics_error,
                            recovery_action="continue",
                        )

                    log_entry["payload"] = payload_out
                    logs.append(log_entry)

                    # Save to memory even if agent failed
                    try:
                        if agent_type != "forknode":
                            self.memory.log(
                                agent_id,
                                agent.__class__.__name__,
                                payload_out,
                                step=self.step_index,
                                run_id=self.run_id,
                            )
                    except Exception as memory_error:
                        self._record_error(
                            "memory_logging",
                            agent_id,
                            f"Failed to log to memory: {memory_error}",
                            memory_error,
                            recovery_action="continue",
                        )

                    print(
                        f"{datetime.now()} > [ORKA] {self.step_index} > Agent '{agent_id}' returned: {agent_result}",
                    )

            except Exception as step_error:
                # Catch-all for any other step-level errors
                self._record_error(
                    "step_execution",
                    agent_id,
                    f"Step execution failed: {step_error}",
                    step_error,
                    recovery_action="continue",
                )
                print(
                    f"⚠️ [ORKA-STEP-ERROR] Step {self.step_index} failed for {agent_id}: {step_error}",
                )
                continue  # Continue to next agent

        # Generate meta report with aggregated metrics
        meta_report = self._generate_meta_report(logs)

        # Save logs to file at the end of the run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")

        # Store meta report in memory for saving
        meta_report_entry = {
            "agent_id": "meta_report",
            "event_type": "MetaReport",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {
                "meta_report": meta_report,
                "run_id": self.run_id,
                "timestamp": timestamp,
            },
        }
        self.memory.memory.append(meta_report_entry)

        # Save to memory backend
        self.memory.save_to_file(log_path)

        # Cleanup memory backend resources to prevent hanging
        try:
            self.memory.close()
        except Exception as e:
            print(f"Warning: Failed to cleanly close memory backend: {e!s}")

        # Print meta report summary
        print("\n" + "=" * 50)
        print("ORKA EXECUTION META REPORT")
        print("=" * 50)
        print(f"Total Execution Time: {meta_report['total_duration']:.3f}s")
        print(f"Total LLM Calls: {meta_report['total_llm_calls']}")
        print(f"Total Tokens: {meta_report['total_tokens']}")
        print(f"Total Cost: ${meta_report['total_cost_usd']:.6f}")
        print(f"Average Latency: {meta_report['avg_latency_ms']:.2f}ms")
        print("=" * 50)

        return logs

    async def _execute_single_agent(
        self,
        agent_id,
        agent,
        agent_type,
        payload,
        input_data,
        queue,
        logs,
    ):
        """
        Execute a single agent with proper error handling and status tracking.
        Returns the result of the agent execution.
        """
        # Handle RouterNode: dynamic routing based on previous outputs
        if agent_type == "routernode":
            decision_key = agent.params.get("decision_key")
            routing_map = agent.params.get("routing_map")
            if decision_key is None:
                raise ValueError("Router agent must have 'decision_key' in params.")
            raw_decision_value = payload["previous_outputs"].get(decision_key)
            normalized = self.normalize_bool(raw_decision_value)
            payload["previous_outputs"][decision_key] = "true" if normalized else "false"

            result = agent.run(payload)
            next_agents = result if isinstance(result, list) else [result]
            # For router nodes, we need to update the queue
            queue.clear()
            queue.extend(next_agents)

            payload_out = {
                "input": input_data,
                "decision_key": decision_key,
                "decision_value": "true" if normalized else "false",
                "raw_decision_value": str(raw_decision_value),
                "routing_map": str(routing_map),
                "next_agents": str(next_agents),
            }
            self._add_prompt_to_payload(agent, payload_out, payload)
            return payload_out

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
                    f"ForkNode '{agent_id}' requires non-empty 'targets' list.",
                )

            fork_group_id = self.fork_manager.generate_group_id(agent_id)
            self.fork_manager.create_group(fork_group_id, fork_targets)
            payload["fork_group_id"] = fork_group_id

            mode = agent.config.get(
                "mode",
                "sequential",
            )  # Default to sequential if not set

            payload_out = {
                "input": input_data,
                "fork_group": fork_group_id,
                "fork_targets": fork_targets,
            }
            self._add_prompt_to_payload(agent, payload_out, payload)

            self.memory.log(
                agent_id,
                agent.__class__.__name__,
                payload_out,
                step=self.step_index,
                run_id=self.run_id,
            )

            print(
                f"{datetime.now()} > [ORKA][FORK][PARALLEL] {self.step_index} >  Running forked agents in parallel for group {fork_group_id}",
            )
            fork_logs = await self.run_parallel_agents(
                fork_targets,
                fork_group_id,
                input_data,
                payload["previous_outputs"],
            )
            logs.extend(fork_logs)  # Add forked agent logs to the main log
            return payload_out

        # Handle JoinNode: wait for all forked agents to finish, then join results
        elif agent_type == "joinnode":
            fork_group_id = self.memory.hget(
                f"fork_group_mapping:{agent.group_id}",
                "group_id",
            )
            if fork_group_id:
                fork_group_id = (
                    fork_group_id.decode() if isinstance(fork_group_id, bytes) else fork_group_id
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
            self._add_prompt_to_payload(agent, payload_out, payload)

            if not fork_group_id:
                raise ValueError(
                    f"JoinNode '{agent_id}' missing required group_id.",
                )

            # Handle different JoinNode statuses
            if result.get("status") == "waiting":
                print(
                    f"{datetime.now()} > [ORKA][JOIN][WAITING] {self.step_index} > Node '{agent_id}' is still waiting on fork group: {fork_group_id}",
                )
                queue.append(agent_id)
                self.memory.log(
                    agent_id,
                    agent.__class__.__name__,
                    payload_out,
                    step=self.step_index,
                    run_id=self.run_id,
                )
                # Return waiting status instead of continue
                return {"status": "waiting", "result": result}
            elif result.get("status") == "timeout":
                print(
                    f"{datetime.now()} > [ORKA][JOIN][TIMEOUT] {self.step_index} > Node '{agent_id}' timed out waiting for fork group: {fork_group_id}",
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
                return {"status": "timeout", "result": result}
            elif result.get("status") == "done":
                self.fork_manager.delete_group(
                    fork_group_id,
                )  # Clean up fork group after successful join

            return payload_out

        else:
            # Normal Agent: run and handle result

            # Render prompt before running agent if agent has a prompt
            self._render_agent_prompt(agent, payload)

            if agent_type in ("memoryreadernode", "memorywriternode", "failovernode"):
                # Memory nodes and failover nodes have async run methods
                result = await agent.run(payload)
            else:
                # Regular synchronous agent
                result = agent.run(payload)

            # If agent is waiting (e.g., for async input), return waiting status
            if isinstance(result, dict) and result.get("status") == "waiting":
                print(
                    f"{datetime.now()} > [ORKA][WAITING] {self.step_index} > Node '{agent_id}' is still waiting: {result.get('received')}",
                )
                queue.append(agent_id)
                return {"status": "waiting", "result": result}

            # After normal agent finishes, mark it done if it's part of a fork
            fork_group = payload.get("input", {})
            if fork_group:
                self.fork_manager.mark_agent_done(fork_group, agent_id)

            # Check if this agent has a next-in-sequence step in its branch
            next_agent = self.fork_manager.next_in_sequence(fork_group, agent_id)
            if next_agent:
                print(
                    f"{datetime.now()} > [ORKA][FORK-SEQUENCE] {self.step_index} > Agent '{agent_id}' finished. Enqueuing next in sequence: '{next_agent}'",
                )
                self.enqueue_fork([next_agent], fork_group)

            payload_out = {"input": input_data, "result": result}
            self._add_prompt_to_payload(agent, payload_out, payload)
            return payload_out

    async def _run_agent_async(self, agent_id, input_data, previous_outputs):
        """
        Run a single agent asynchronously.
        """
        agent = self.agents[agent_id]
        payload = {"input": input_data, "previous_outputs": previous_outputs}

        # Render prompt before running agent if agent has a prompt
        self._render_agent_prompt(agent, payload)

        # 🔍 DEBUG: Check if template rendering worked (only if DEBUG logging is enabled)
        if logger.isEnabledFor(logging.DEBUG) and hasattr(agent, "prompt") and agent.prompt:
            if "formatted_prompt" in payload:
                original_template = agent.prompt
                rendered_template = payload["formatted_prompt"]

                # Check if template was actually rendered (changed from original)
                if original_template != rendered_template:
                    logger.debug(f"Agent '{agent_id}' template rendered successfully")
                else:
                    logger.debug(f"Agent '{agent_id}' template unchanged - possible template issue")

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
                agent_id,
                input_data,
                previous_outputs,
            )
            branch_results[agent_id] = result
            # Update previous_outputs for the next agent in the branch
            previous_outputs = {**previous_outputs, **branch_results}
        return branch_results

    async def run_parallel_agents(
        self,
        agent_ids,
        fork_group_id,
        input_data,
        previous_outputs,
    ):
        """
        Run multiple branches in parallel, with agents within each branch running sequentially.
        Returns a list of log entries for each forked agent.
        """
        # 🔧 GENERIC FIX: Ensure complete context is passed to forked agents
        logger.debug(
            f"run_parallel_agents called with previous_outputs keys: {list(previous_outputs.keys())}",
        )

        # Enhanced debugging: Check the structure of previous_outputs (only if DEBUG enabled)
        if logger.isEnabledFor(logging.DEBUG):
            for agent_id, agent_result in previous_outputs.items():
                if isinstance(agent_result, dict):
                    # Check for common nested structures
                    if "memories" in agent_result:
                        memories = agent_result["memories"]
                        logger.debug(
                            f"Agent '{agent_id}' has {len(memories) if isinstance(memories, list) else 'non-list'} memories",
                        )
                    if "result" in agent_result:
                        logger.debug(f"Agent '{agent_id}' has nested result structure")

        # Get the fork node to understand the branch structure
        # Fork group ID format: {node_id}_{timestamp}, so we need to remove the timestamp
        fork_node_id = "_".join(
            fork_group_id.split("_")[:-1],
        )  # Remove the last part (timestamp)
        fork_node = self.agents[fork_node_id]
        branches = fork_node.targets

        # 🔧 GENERIC FIX: Ensure previous_outputs is properly structured
        # Make a deep copy to avoid modifying the original
        enhanced_previous_outputs = self._ensure_complete_context(previous_outputs)

        # Run each branch in parallel
        branch_tasks = [
            self._run_branch_async(branch, input_data, enhanced_previous_outputs)
            for branch in branches
        ]

        # Wait for all branches to complete
        branch_results = await asyncio.gather(*branch_tasks)

        # Process results and create logs
        forked_step_index = 0
        result_logs = []
        updated_previous_outputs = enhanced_previous_outputs.copy()

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

            # Create log entry with current previous_outputs (before updating with this agent's result)
            payload_data = {"result": result}
            agent = self.agents[agent_id]
            payload_context = {
                "input": input_data,
                "previous_outputs": updated_previous_outputs,
            }
            self._add_prompt_to_payload(agent, payload_data, payload_context)

            log_data = {
                "agent_id": agent_id,
                "event_type": f"ForkedAgent-{self.agents[agent_id].__class__.__name__}",
                "timestamp": datetime.now(UTC).isoformat(),
                "payload": payload_data,
                "previous_outputs": updated_previous_outputs.copy(),
                "step": step_index,
                "run_id": self.run_id,
            }
            result_logs.append(log_data)

            # Log to memory
            self.memory.log(
                agent_id,
                f"ForkedAgent-{self.agents[agent_id].__class__.__name__}",
                payload_data,
                step=step_index,
                run_id=self.run_id,
                previous_outputs=updated_previous_outputs.copy(),
            )

            # Update previous_outputs with this agent's result AFTER logging
            updated_previous_outputs[agent_id] = result

        return result_logs

    def _ensure_complete_context(self, previous_outputs):
        """
        Generic method to ensure previous_outputs has complete context for template rendering.
        This handles various agent result structures and ensures templates can access data.
        """
        enhanced_outputs = {}

        for agent_id, agent_result in previous_outputs.items():
            # Start with the original result
            enhanced_outputs[agent_id] = agent_result

            # If the result is a complex structure, ensure it's template-friendly
            if isinstance(agent_result, dict):
                # Handle different common agent result patterns
                # Pattern 1: Direct result (like memory nodes)
                if "memories" in agent_result and isinstance(agent_result["memories"], list):
                    logger.debug(
                        f"Agent '{agent_id}' has {len(agent_result['memories'])} memories directly accessible",
                    )

                # Pattern 2: Nested result structure
                elif "result" in agent_result and isinstance(agent_result["result"], dict):
                    nested_result = agent_result["result"]
                    logger.debug(
                        f"Agent '{agent_id}' has nested result with keys: {list(nested_result.keys())}",
                    )

                    # For nested structures, also provide direct access to common fields
                    if "memories" in nested_result:
                        # Create a version that allows both access patterns
                        enhanced_outputs[agent_id] = {
                            **agent_result,  # Keep original structure
                            "memories": nested_result["memories"],  # Direct access
                        }
                        logger.debug(f"Agent '{agent_id}' enhanced with direct memory access")

                    if "response" in nested_result:
                        enhanced_outputs[agent_id] = {
                            **enhanced_outputs.get(agent_id, agent_result),
                            "response": nested_result["response"],  # Direct access
                        }
                        logger.debug(f"Agent '{agent_id}' enhanced with direct response access")

        return enhanced_outputs

    def enqueue_fork(self, agent_ids, fork_group_id):
        """
        Add agents to the fork queue for processing.
        """
        for agent_id in agent_ids:
            self.queue.append(agent_id)
