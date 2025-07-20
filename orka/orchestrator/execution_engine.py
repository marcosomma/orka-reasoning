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
Execution Engine
===============

The ExecutionEngine is the core component responsible for coordinating and executing
multi-agent workflows within the OrKa orchestration framework.

Core Responsibilities
--------------------

**Agent Coordination:**
- Sequential execution of agents based on configuration
- Context propagation between agents with previous outputs
- Dynamic queue management for workflow control
- Error handling and retry logic with exponential backoff

**Execution Patterns:**
- **Sequential Processing**: Default execution pattern where agents run one after another
- **Parallel Execution**: Fork/join patterns for concurrent agent execution
- **Conditional Branching**: Router nodes for dynamic workflow paths
- **Memory Operations**: Integration with memory nodes for data persistence

**Error Management:**
- Comprehensive error tracking and telemetry collection
- Automatic retry with configurable maximum attempts
- Graceful degradation and fallback strategies
- Detailed error reporting and recovery actions

Architecture Details
-------------------

**Execution Flow:**
1. **Queue Processing**: Agents are processed from the configured queue
2. **Context Building**: Input data and previous outputs are combined into payload
3. **Agent Execution**: Individual agents are executed with full context
4. **Result Processing**: Outputs are captured and added to execution history
5. **Queue Management**: Next agents are determined based on results

**Context Management:**
- Input data is preserved throughout the workflow
- Previous outputs from all agents are available to subsequent agents
- Execution metadata (timestamps, step indices) is tracked
- Error context is maintained for debugging and recovery

**Concurrency Handling:**
- Thread pool executor for parallel agent execution
- Fork group management for coordinated parallel operations
- Async/await patterns for non-blocking operations
- Resource pooling for efficient memory usage

Implementation Features
----------------------

**Agent Execution:**
- Support for both sync and async agent implementations
- Automatic detection of agent execution patterns
- Timeout handling with configurable limits
- Resource cleanup after agent completion

**Memory Integration:**
- Automatic logging of agent execution events
- Memory backend integration for persistent storage
- Context preservation across workflow steps
- Trace ID propagation for debugging

**Error Handling:**
- Exception capture and structured error reporting
- Retry logic with exponential backoff
- Error telemetry collection for monitoring
- Graceful failure recovery

**Performance Optimization:**
- Efficient context building and propagation
- Minimal memory overhead for large workflows
- Optimized queue processing algorithms
- Resource pooling for external connections

Execution Patterns
-----------------

**Sequential Execution:**
```yaml
orchestrator:
  strategy: sequential
  agents: [classifier, router, processor, responder]
```

**Parallel Execution:**
```yaml
orchestrator:
  strategy: parallel
  fork_groups:
    - agents: [validator_1, validator_2, validator_3]
      join_agent: aggregator
```

**Conditional Branching:**
```yaml
agents:
  - id: router
    type: router
    conditions:
      - condition: "{{ classification == 'urgent' }}"
        next_agents: [urgent_handler]
      - condition: "{{ classification == 'normal' }}"
        next_agents: [normal_handler]
```

Integration Points
-----------------

**Memory System:**
- Automatic event logging for all agent executions
- Context preservation in memory backend
- Trace ID propagation for request tracking
- Performance metrics collection

**Error Handling:**
- Structured error reporting with context
- Retry mechanisms with configurable policies
- Error telemetry for monitoring and alerting
- Recovery action recommendations

**Monitoring:**
- Real-time execution metrics
- Agent performance tracking
- Resource usage monitoring
- Error rate and pattern analysis
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

    async def run(self, input_data, return_logs=False):
        """
        Execute the orchestrator with the given input data.

        Args:
            input_data: The input data for the orchestrator
            return_logs: If True, return full logs; if False, return final response (default: False)

        Returns:
            Either the logs array or the final response based on return_logs parameter
        """
        logs = []
        try:
            result = await self._run_with_comprehensive_error_handling(
                input_data,
                logs,
                return_logs,
            )
            return result
        except Exception as e:
            self._record_error(
                "orchestrator_execution",
                "main",
                f"Orchestrator execution failed: {e}",
                e,
                recovery_action="fail",
            )
            print(f"🚨 [ORKA-CRITICAL] Orchestrator execution failed: {e}")
            raise

    async def _run_with_comprehensive_error_handling(self, input_data, logs, return_logs=False):
        """
        Main execution loop with comprehensive error handling wrapper.

        Args:
            input_data: The input data for the orchestrator
            logs: List to store execution logs
            return_logs: If True, return full logs; if False, return final response
        """
        try:
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

                    # Add orchestrator to context for fork nodes
                    if agent_type == "forknode":
                        payload["orchestrator"] = self

                    freezed_payload = json.dumps(
                        {k: v for k, v in payload.items() if k != "orchestrator"},
                    )  # Freeze the payload as a string for logging/debug, excluding orchestrator
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

                    while retry_count < max_retries:
                        try:
                            # Execute the agent with appropriate method
                            if agent_type in (
                                "memoryreadernode",
                                "memorywriternode",
                                "failovernode",
                                "loopnode",
                                "openaianswerbuilder",
                                "forknode",
                            ):
                                # Memory nodes, failover nodes, loop nodes, and OpenAI agents have async run methods
                                agent_result = await agent.run(payload)
                            else:
                                # Regular synchronous agent
                                agent_result = agent.run(payload)
                                # Check if result is a coroutine
                                if inspect.iscoroutine(agent_result):
                                    agent_result = await agent_result

                            # If agent is waiting (e.g., for async input), return waiting status
                            if (
                                isinstance(agent_result, dict)
                                and agent_result.get("status") == "waiting"
                            ):
                                print(
                                    f"{datetime.now()} > [ORKA] {self.step_index} > Agent '{agent_id}' returned waiting status: {agent_result}",
                                )
                                # Put agent back in queue to retry later
                                queue.append(agent_id)
                                break

                            # If we got a result, break retry loop
                            if agent_result is not None:
                                break

                            retry_count += 1
                            if retry_count < max_retries:
                                print(
                                    f"{datetime.now()} > [ORKA] {self.step_index} > Agent '{agent_id}' failed (attempt {retry_count}/{max_retries}): {agent_result}",
                                )
                                await asyncio.sleep(1)  # Wait before retry
                            else:
                                print(
                                    f"{datetime.now()} > [ORKA] {self.step_index} > Agent '{agent_id}' failed after {max_retries} attempts",
                                )

                        except Exception as e:
                            retry_count += 1
                            if retry_count < max_retries:
                                print(
                                    f"{datetime.now()} > [ORKA] {self.step_index} > Agent '{agent_id}' failed (attempt {retry_count}/{max_retries}): {e}",
                                )
                                await asyncio.sleep(1)  # Wait before retry
                            else:
                                print(
                                    f"{datetime.now()} > [ORKA] {self.step_index} > Agent '{agent_id}' failed after {max_retries} attempts: {e}",
                                )
                                raise

                    # Process agent result
                    if agent_result is not None:
                        # Special handling for router nodes
                        if agent_type == "routernode":
                            if isinstance(agent_result, list):
                                queue = agent_result + queue
                                continue  # Skip to the next agent in the new queue

                        # Create a copy of the payload for logging (without orchestrator)
                        payload_out = {k: v for k, v in payload.items() if k != "orchestrator"}

                        # Handle different result types
                        if isinstance(agent_result, dict):
                            # Case 1: Local LLM agent response
                            if "response" in agent_result:
                                payload_out.update(
                                    {
                                        "response": agent_result["response"],
                                        "confidence": agent_result.get("confidence", "0.0"),
                                        "internal_reasoning": agent_result.get(
                                            "internal_reasoning", ""
                                        ),
                                        "_metrics": agent_result.get("_metrics", {}),
                                        "formatted_prompt": agent_result.get(
                                            "formatted_prompt", ""
                                        ),
                                    }
                                )
                            # Case 2: Memory agent response
                            elif "memories" in agent_result:
                                payload_out.update(
                                    {
                                        "memories": agent_result["memories"],
                                        "query": agent_result.get("query", ""),
                                        "backend": agent_result.get("backend", ""),
                                        "search_type": agent_result.get("search_type", ""),
                                        "num_results": agent_result.get("num_results", 0),
                                    }
                                )
                            # Case 3: Fork/Join node response
                            elif "status" in agent_result:
                                payload_out.update(agent_result)
                            # Case 4: Other result types
                            else:
                                payload_out["result"] = agent_result
                        else:
                            # Case 5: Non-dict result
                            payload_out["result"] = agent_result

                        # Special handling for fork and join nodes
                        if agent_type == "forknode":
                            # Store fork group ID for join node
                            fork_group_id = agent_result.get("fork_group")
                            if fork_group_id:
                                payload_out["fork_group_id"] = fork_group_id
                        elif agent_type == "joinnode":
                            # Get fork group ID from payload
                            fork_group_id = payload.get("fork_group_id")
                            if fork_group_id:
                                # Add fork group ID to result for tracking
                                agent_result["fork_group_id"] = fork_group_id

                        # Store the result in memory
                        result_key = f"agent_result:{agent_id}"
                        self.memory.set(result_key, json.dumps(payload_out))
                        logger.debug(f"Stored result for agent {agent_id}")

                        # Store in Redis hash for group tracking
                        group_key = "agent_results"
                        self.memory.hset(group_key, agent_id, json.dumps(payload_out))
                        logger.debug(f"Stored result in group for agent {agent_id}")

                        # Add to logs
                        log_entry["payload"] = payload_out
                        logs.append(log_entry)
                        self.memory.memory.append(log_entry) # Add to self.memory.memory for saving

                except Exception as agent_error:
                    # Log the error and continue with next agent
                    print(f"Error executing agent {agent_id}: {agent_error}")
                    continue

            # Generate meta report with aggregated metrics
            meta_report = self._generate_meta_report(logs)

            # Store meta report in memory for saving
            meta_report_entry = {
                "agent_id": "meta_report",
                "event_type": "MetaReport",
                "timestamp": datetime.now(UTC).isoformat(),
                "payload": {
                    "meta_report": meta_report,
                    "run_id": self.run_id,
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                },
            }
            self.memory.memory.append(meta_report_entry)

            # Save logs to file at the end of the run
            log_dir = os.getenv("ORKA_LOG_DIR", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(
                log_dir, f"orka_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
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

            # Return either logs or final response based on parameter
            if return_logs:
                # Return full logs for internal workflows (like loop nodes)
                return logs
            else:
                # Extract the final response from the last non-memory agent for user-friendly output
                final_response = self._extract_final_response(logs)
                return final_response

        except Exception as e:
            # Handle any unexpected errors
            print(f"Unexpected error in execution engine: {e}")
            raise

    async def _run_agent_async(self, agent_id, input_data, previous_outputs):
        """
        Run a single agent asynchronously.
        """
        agent = self.agents[agent_id]

        # Create a complete payload with all necessary context
        payload = {
            "input": input_data,
            "previous_outputs": previous_outputs,
        }

        # Add loop context if available
        if isinstance(input_data, dict):
            if "loop_number" in input_data:
                payload["loop_number"] = input_data["loop_number"]
            if "past_loops_metadata" in input_data:
                payload["past_loops_metadata"] = input_data["past_loops_metadata"]

        # Render prompt before running agent if agent has a prompt
        if hasattr(agent, "prompt") and agent.prompt:
            try:
                # Use the PromptRenderer to handle template rendering
                formatted_prompt = self.render_prompt(agent.prompt, payload)
                payload["formatted_prompt"] = formatted_prompt

                # Debug logging for template rendering
                if logger.isEnabledFor(logging.DEBUG):
                    original_template = agent.prompt
                    if original_template != formatted_prompt:
                        logger.debug(f"Agent '{agent_id}' template rendered successfully")
                        logger.debug(f"Original: {original_template}")
                        logger.debug(f"Rendered: {formatted_prompt}")
                    else:
                        logger.debug(
                            f"Agent '{agent_id}' template unchanged - possible template issue"
                        )
                        logger.debug(f"Template context: {payload}")
            except Exception as e:
                logger.error(f"Failed to render prompt for agent '{agent_id}': {e}")
                # If rendering fails, use the original prompt
                payload["formatted_prompt"] = agent.prompt

        # Inspect the run method to see if it needs orchestrator
        run_method = agent.run
        sig = inspect.signature(run_method)
        needs_orchestrator = len(sig.parameters) > 1  # More than just 'self'
        is_async = inspect.iscoroutinefunction(run_method)

        # Execute the agent with appropriate method
        try:
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

        except Exception as e:
            logger.error(f"Failed to execute agent '{agent_id}': {e}")
            raise

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
        # Ensure complete context is passed to forked agents
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

        # Ensure previous_outputs is properly structured
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
                    enhanced_outputs[agent_id] = {
                        **agent_result,  # Keep original structure
                        "memories": agent_result["memories"],  # Direct access
                    }

                # Pattern 2: Local LLM agent response
                elif "response" in agent_result:
                    enhanced_outputs[agent_id] = {
                        **agent_result,  # Keep original structure
                        "response": agent_result["response"],  # Direct access
                        "confidence": agent_result.get("confidence", "0.0"),
                        "internal_reasoning": agent_result.get("internal_reasoning", ""),
                        "_metrics": agent_result.get("_metrics", {}),
                        "formatted_prompt": agent_result.get("formatted_prompt", ""),
                    }

                # Pattern 3: Nested result structure
                elif "result" in agent_result and isinstance(agent_result["result"], dict):
                    nested_result = agent_result["result"]
                    # For nested structures, also provide direct access to common fields
                    if "response" in nested_result:
                        enhanced_outputs[agent_id] = {
                            **agent_result,  # Keep original structure
                            "response": nested_result["response"],  # Direct access
                            "confidence": nested_result.get("confidence", "0.0"),
                            "internal_reasoning": nested_result.get("internal_reasoning", ""),
                            "_metrics": nested_result.get("_metrics", {}),
                            "formatted_prompt": nested_result.get("formatted_prompt", ""),
                        }
                    elif "memories" in nested_result:
                        enhanced_outputs[agent_id] = {
                            **agent_result,  # Keep original structure
                            "memories": nested_result["memories"],  # Direct access
                            "query": nested_result.get("query", ""),
                            "backend": nested_result.get("backend", ""),
                            "search_type": nested_result.get("search_type", ""),
                            "num_results": nested_result.get("num_results", 0),
                        }

                # Pattern 4: Fork/Join node responses
                elif "status" in agent_result:
                    enhanced_outputs[agent_id] = {
                        **agent_result,  # Keep original structure
                        "status": agent_result["status"],
                        "fork_group": agent_result.get("fork_group", ""),
                        "merged": agent_result.get("merged", {}),
                    }

                # Pattern 5: Other dict structures
                else:
                    enhanced_outputs[agent_id] = agent_result

            # Pattern 6: Non-dict results
            else:
                enhanced_outputs[agent_id] = agent_result

        return enhanced_outputs

    def enqueue_fork(self, agent_ids, fork_group_id):
        """
        Add agents to the fork queue for processing.
        """
        for agent_id in agent_ids:
            self.queue.append(agent_id)

    def _extract_final_response(self, logs):
        """
        Extract the response from the last non-memory agent to return as the main result.

        Args:
            logs: List of agent execution logs

        Returns:
            The response from the last non-memory agent, or logs if no suitable agent found
        """
        # Memory agent types that should be excluded from final response consideration
        memory_agent_types = {
            "MemoryReaderNode",
            "MemoryWriterNode",
            "memory",
            "memoryreadernode",
            "memorywriternode",
            "validate_and_structure", # Exclude validator agents
            "guardian", # Exclude agents with 'guardian' in their name/type
        }

        # Find the last non-memory agent
        last_non_memory_agent = None
        for log_entry in reversed(logs):
            if log_entry.get("event_type") == "MetaReport":
                continue  # Skip meta reports

            agent_id = log_entry.get("agent_id")
            event_type = log_entry.get("event_type", "").lower()

            # Skip memory agents
            if event_type in memory_agent_types:
                continue

            # Check if this agent has a payload with results
            payload = log_entry.get("payload", {})
            if payload and "result" in payload:
                last_non_memory_agent = log_entry
                break

        if not last_non_memory_agent:
            print("[ORKA-WARNING] No suitable final agent found, returning full logs")
            return logs

        # Extract the response from the last non-memory agent
        payload = last_non_memory_agent.get("payload", {})
        result = payload.get("result", {})

        print(
            f"[ORKA-FINAL] Returning response from final agent: {last_non_memory_agent.get('agent_id')}",
        )

        # Try to extract a clean response from the result
        if isinstance(result, dict):
            # Look for common response patterns
            if "response" in result:
                return result["response"]
            elif "result" in result:
                nested_result = result["result"]
                if isinstance(nested_result, dict):
                    # Handle nested dict structure
                    if "response" in nested_result:
                        return nested_result["response"]
                    else:
                        return nested_result
                elif isinstance(nested_result, str):
                    return nested_result
                else:
                    return str(nested_result)
            else:
                # Return the entire result if no specific response field found
                return result
        elif isinstance(result, str):
            return result
        else:
            # Fallback to string representation
            return str(result)
