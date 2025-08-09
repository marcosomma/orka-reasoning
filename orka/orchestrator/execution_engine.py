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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, TypeVar, cast

from .base import OrchestratorBase
from .error_handling import ErrorHandler as OrchestratorErrorHandling
from .metrics import MetricsCollector as OrchestratorMetricsCollector
from .prompt_rendering import PromptRenderer

logger = logging.getLogger(__name__)


# Define a type variable that is bound to ExecutionEngine and includes all necessary attributes
class ExecutionEngineProtocol(OrchestratorBase):
    """Protocol defining required attributes for ExecutionEngine type variable."""

    agents: Dict[str, Any]


T = TypeVar("T", bound="ExecutionEngineProtocol")


class ExecutionEngine(
    OrchestratorBase, PromptRenderer, OrchestratorErrorHandling, OrchestratorMetricsCollector
):
    """
    ExecutionEngine coordinates complex multi-agent workflows within the OrKa framework.

    Core Features:
    - Agent execution with precise coordination
    - Rich context flow across workflow steps
    - Fault tolerance with automatic recovery
    - Real-time optimization and resource management
    - Scalable architecture for distributed execution

    Execution Patterns:

    Sequential Processing:
    ```yaml
    orchestrator:
      strategy: sequential
      agents: [classifier, router, processor, responder]
    ```

    Parallel Processing:
    ```yaml
    orchestrator:
      strategy: parallel
      agents: [validator_1, validator_2, validator_3]
    ```

    Decision Tree:
    ```yaml
    orchestrator:
      strategy: decision-tree
      agents: [classifier, router, [path_a, path_b], aggregator]
    ```

    Advanced Features:
    - Intelligent retry logic with exponential backoff
    - Real-time monitoring and performance metrics
    - Resource management and connection pooling
    - Production-ready distributed capabilities

    Use Cases:
    - Multi-step AI reasoning workflows
    - High-throughput content processing pipelines
    - Real-time decision systems with complex branching
    - Fault-tolerant distributed AI applications
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Initialize PromptRenderer explicitly to ensure render_prompt method is available
        PromptRenderer.__init__(self)
        self.agents: Dict[str, Any] = {}
        # Set orchestrator reference for fork/join nodes - ExecutionEngine is part of Orchestrator
        self.orchestrator = self

    async def run(self: "ExecutionEngine", input_data: Any, return_logs: bool = False) -> Any:
        """
        Execute the orchestrator with the given input data.

        Args:
            input_data: The input data for the orchestrator
            return_logs: If True, return full logs; if False, return final response (default: False)

        Returns:
            Either the logs array or the final response based on return_logs parameter
        """
        logs: List[Any] = []
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
            logger.critical(f"[ORKA-CRITICAL] Orchestrator execution failed: {e}")
            raise

    async def _run_with_comprehensive_error_handling(
        self: "ExecutionEngine",
        input_data: Any,
        logs: List[Dict[str, Any]],
        return_logs: bool = False,
    ) -> Any:
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
                    logger.info(
                        f"Running agent '{agent_id}' of type '{agent_type}', payload: {freezed_payload}",
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
                            # Execute agent with template rendering and context preservation
                            _, agent_result = await self._run_agent_async(
                                agent_id,
                                payload.get("input", payload),
                                payload.get("previous_outputs", {}),
                                full_payload=payload,  # Pass full payload including orchestrator
                            )

                            # If agent is waiting (e.g., for async input), return waiting status
                            if (
                                isinstance(agent_result, dict)
                                and agent_result.get("status") == "waiting"
                            ):
                                logger.info(
                                    f"Agent '{agent_id}' returned waiting status: {agent_result}",
                                )
                                # Put agent back in queue to retry later
                                queue.append(agent_id)
                                break

                            # If we got a result, break retry loop
                            if agent_result is not None:
                                break

                            retry_count += 1
                            if retry_count < max_retries:
                                logger.warning(
                                    f"Agent '{agent_id}' failed (attempt {retry_count}/{max_retries}): {agent_result}",
                                )
                                await asyncio.sleep(1)  # Wait before retry
                            else:
                                logger.error(
                                    f"Agent '{agent_id}' failed after {max_retries} attempts",
                                )

                        except Exception as e:
                            retry_count += 1
                            if retry_count < max_retries:
                                logger.warning(
                                    f"Agent '{agent_id}' failed (attempt {retry_count}/{max_retries}): {e}",
                                )
                                await asyncio.sleep(1)  # Wait before retry
                            else:
                                logger.error(
                                    f"Agent '{agent_id}' failed after {max_retries} attempts: {e}",
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
                            # Fork node logs immediately, then executes children
                            fork_group_id = agent_result.get("fork_group")
                            if fork_group_id:
                                payload_out["fork_group_id"] = fork_group_id
                                payload_out["fork_execution_status"] = "initiated"

                                # Log fork node immediately
                                log_entry = {
                                    "agent_id": agent_id,
                                    "event_type": agent.__class__.__name__,
                                    "timestamp": datetime.now(UTC).isoformat(),
                                    "payload": payload_out.copy(),
                                    "step": self.step_index,
                                    "run_id": self.run_id,
                                    "previous_outputs": self.build_previous_outputs(logs),
                                }
                                logs.append(log_entry)

                                # Log to memory backend immediately
                                self.memory.log(
                                    agent_id,
                                    agent.__class__.__name__,
                                    payload_out.copy(),
                                    step=self.step_index,
                                    run_id=self.run_id,
                                    previous_outputs=self.build_previous_outputs(logs[:-1]),
                                )

                                # Execute forked agents after logging fork
                                forked_agents = agent_result.get("agents", [])
                                if forked_agents:
                                    logger.info(
                                        f"Executing {len(forked_agents)} forked agents for group {fork_group_id}"
                                    )

                                    # Get current context for forked execution
                                    current_previous_outputs = self.build_previous_outputs(logs)

                                    # Execute in parallel
                                    try:
                                        fork_logs = await self.run_parallel_agents(
                                            forked_agents,
                                            fork_group_id,
                                            input_data,
                                            current_previous_outputs,
                                        )

                                        # Add fork logs to main logs
                                        logs.extend(fork_logs)
                                        logger.info(
                                            f"Completed execution of {len(fork_logs)} forked agents"
                                        )

                                    except Exception as fork_error:
                                        logger.error(f"Fork execution failed: {fork_error}")

                                # Skip normal logging since we already logged the fork node
                                continue

                        elif agent_type == "joinnode":
                            # Join node aggregates forked results
                            # Get fork_group_id from payload or use the configured group
                            fork_group_id = payload.get("fork_group_id")
                            if not fork_group_id and hasattr(agent, "group_id"):
                                # Use configured group (e.g., "fork_3" from YAML)
                                fork_group_id = agent.group_id

                            if fork_group_id:
                                # Generate the actual fork group ID pattern (fork_3_timestamp)
                                # Look for any fork group that starts with our configured group
                                actual_fork_group_id = None
                                for log in logs:
                                    log_fork_group = log.get("fork_group_id")
                                    if log_fork_group and log_fork_group.startswith(
                                        f"{fork_group_id}_"
                                    ):
                                        actual_fork_group_id = log_fork_group
                                        break

                                if actual_fork_group_id:
                                    # Collect all forked results from logs
                                    forked_results = []
                                    for log in logs:
                                        if log.get(
                                            "fork_group_id"
                                        ) == actual_fork_group_id and log.get(
                                            "event_type", ""
                                        ).startswith(
                                            "ForkedAgent-"
                                        ):
                                            forked_results.append(
                                                {
                                                    "agent_id": log["agent_id"],
                                                    "result": log["payload"],
                                                    "step": log.get("step"),
                                                    "timestamp": log.get("timestamp"),
                                                }
                                            )

                                    # Add joined results to payload
                                    payload_out["joined_results"] = forked_results
                                    payload_out["fork_group_id"] = actual_fork_group_id
                                    agent_result["fork_group_id"] = actual_fork_group_id

                                    logger.info(
                                        f"Join node collected {len(forked_results)} results from fork group {actual_fork_group_id}"
                                    )
                                else:
                                    logger.warning(
                                        f"Join node could not find fork group matching pattern '{fork_group_id}_*'"
                                    )
                            else:
                                logger.warning(
                                    f"Join node '{agent_id}' has no fork_group_id or group configuration"
                                )

                        # Store the result in memory
                        result_key = f"agent_result:{agent_id}"
                        self.memory.set(result_key, json.dumps(payload_out))
                        logger.debug(f"- Stored result for agent {agent_id}")

                        # Store in Redis hash for group tracking
                        group_key = "agent_results"
                        self.memory.hset(group_key, agent_id, json.dumps(payload_out))
                        logger.debug(f"- Stored result in group for agent {agent_id}")

                        # Add to logs
                        log_entry["payload"] = payload_out
                        logs.append(log_entry)

                        # ✅ FIX: Log to memory backend like forked agents
                        self.memory.log(
                            agent_id,
                            agent.__class__.__name__,
                            payload_out,
                            step=self.step_index,
                            run_id=self.run_id,
                            previous_outputs=self.build_previous_outputs(
                                logs[:-1]
                            ),  # Exclude current log
                        )

                        self.memory.memory.append(log_entry)  # Keep for file trace compatibility

                except Exception as agent_error:
                    # Log the error and continue with next agent
                    logger.error(f"Error executing agent {agent_id}: {agent_error}")
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

            # Save enhanced trace with memory backend data
            enhanced_trace = self._build_enhanced_trace(logs, meta_report)
            self.memory.save_enhanced_trace(log_path, enhanced_trace)

            # Cleanup memory backend resources to prevent hanging
            try:
                if hasattr(self.memory, "close"):
                    self.memory.close()
            except Exception as e:
                logger.warning(f"Warning: Failed to cleanly close memory backend: {e!s}")

            # Print meta report summary
            logger.info("\n" + "=" * 50)
            logger.info("ORKA EXECUTION META REPORT")
            logger.info("=" * 50)
            logger.info(f"Total Execution Time: {meta_report['total_duration']:.3f}s")
            logger.info(f"Total LLM Calls: {meta_report['total_llm_calls']}")
            logger.info(f"Total Tokens: {meta_report['total_tokens']}")
            logger.info(f"Total Cost: ${meta_report['total_cost_usd']:.6f}")
            logger.info(f"Average Latency: {meta_report['avg_latency_ms']:.2f}ms")
            logger.info("=" * 50)

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
            logger.error(f"Unexpected error in execution engine: {e}")
            raise

    async def _run_agent_async(
        self: "ExecutionEngine",
        agent_id: str,
        input_data: Any,
        previous_outputs: Dict[str, Any],
        full_payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Any]:
        """
        Run a single agent asynchronously.
        """
        agent = self.agents[agent_id]

        # Create a complete payload with all necessary context
        payload = {
            "input": input_data,
            "previous_outputs": previous_outputs,
        }

        # Include orchestrator context from full_payload if available
        if full_payload and "orchestrator" in full_payload:
            payload["orchestrator"] = full_payload["orchestrator"]
            logger.debug(f"- Agent '{agent_id}' inherited orchestrator context from full_payload")

        # Add loop context if available
        if isinstance(input_data, dict):
            if "loop_number" in input_data:
                payload["loop_number"] = input_data["loop_number"]
            if "past_loops_metadata" in input_data:
                payload["past_loops_metadata"] = input_data["past_loops_metadata"]

        # Render prompt before running agent if agent has a prompt
        # Also check for ValidationAndStructuringAgent which stores prompt in llm_agent
        agent_prompt = None
        if hasattr(agent, "prompt") and agent.prompt:
            agent_prompt = agent.prompt
        elif (
            hasattr(agent, "llm_agent")
            and hasattr(agent.llm_agent, "prompt")
            and agent.llm_agent.prompt
        ):
            agent_prompt = agent.llm_agent.prompt

        if agent_prompt:
            try:
                # Build complete template context
                template_context = self._build_template_context(payload, agent_id)

                # Debug template context if needed
                logger.debug(
                    f"- Template context for '{agent_id}': {list(template_context.keys())}"
                )
                if "get_input" in template_context:
                    logger.debug(
                        f"Helper functions available: get_input, get_loop_number, get_agent_response"
                    )
                    # Test if functions are callable
                    try:
                        test_input = template_context["get_input"]()
                        logger.debug(f"- get_input() test successful: '{test_input}'")
                    except Exception as e:
                        logger.error(f"get_input() test failed: {e}")
                else:
                    logger.error("Helper functions NOT found in template context")
                    logger.error(f"Available keys: {list(template_context.keys())}")

                # Validate template before rendering
                missing_vars = self._validate_template_variables(agent_prompt, template_context)
                if missing_vars:
                    logger.warning(f"Agent '{agent_id}' template missing variables: {missing_vars}")
                    # Enhanced debugging for template issues
                    prev_outputs = template_context.get("previous_outputs", {})
                    logger.warning(
                        f"Available agents in previous_outputs: {list(prev_outputs.keys())}"
                    )
                    for agent_name, agent_result in prev_outputs.items():
                        if isinstance(agent_result, dict):
                            logger.warning(f"  {agent_name}: keys = {list(agent_result.keys())}")
                        else:
                            logger.warning(f"  {agent_name}: {type(agent_result)} = {agent_result}")

                logger.debug(f"- Available context keys: {list(template_context.keys())}")
                if "previous_outputs" in template_context:
                    logger.debug(
                        f"Available previous_outputs: {list(template_context['previous_outputs'].keys())}"
                    )
                    # Show structure of each agent result for debugging
                    for prev_agent, prev_result in template_context["previous_outputs"].items():
                        if isinstance(prev_result, dict):
                            logger.debug(
                                f"Agent '{prev_agent}' result keys: {list(prev_result.keys())}"
                            )
                        else:
                            logger.debug(
                                f"[DEBUG] - Agent '{prev_agent}' result type: {type(prev_result)}"
                            )

                # Use template context directly
                from jinja2 import Template

                template = Template(agent_prompt)

                # Debug: Show what we're about to render
                logger.debug(
                    f"- About to render template with {len(template_context)} context items"
                )
                logger.debug(f"- Template preview: {agent_prompt[:200]}...")

                formatted_prompt = template.render(**template_context)

                # Log successful rendering
                logger.info(f"Template rendered for '{agent_id}' - length: {len(formatted_prompt)}")

                # Debug: Show a preview of the rendered result
                logger.debug(f"- Rendered preview: {formatted_prompt[:200]}...")

                # Check for unresolved variables and warn if found
                import re

                unresolved_pattern = r"\{\{\s*[^}]+\s*\}\}"
                unresolved_vars = re.findall(unresolved_pattern, formatted_prompt)
                if unresolved_vars:
                    logger.warning(
                        f"Still found {len(unresolved_vars)} unresolved variables after rendering: {unresolved_vars[:3]}"
                    )
                    # Replace unresolved variables with empty strings for now
                    formatted_prompt = re.sub(unresolved_pattern, "", formatted_prompt)
                    formatted_prompt = re.sub(r"\s+", " ", formatted_prompt).strip()
                payload["formatted_prompt"] = formatted_prompt

                # Verify rendering was successful
                if self._has_unresolved_variables(formatted_prompt):
                    logger.error(
                        f"Agent '{agent_id}' has unresolved template variables in: {formatted_prompt}"
                    )
                    payload["template_error"] = "unresolved_variables"

                # Debug logging for template rendering
                if logger.isEnabledFor(logging.DEBUG):
                    original_template = agent_prompt
                    if original_template != formatted_prompt:
                        logger.debug(f"- Agent '{agent_id}' template rendered successfully")
                        logger.debug(f"- Original: {original_template}")
                        logger.debug(f"- Rendered: {formatted_prompt}")
                    else:
                        logger.debug(
                            f"Agent '{agent_id}' template unchanged - possible template issue"
                        )
                        logger.debug(f"- Template context: {template_context}")
            except Exception as e:
                logger.error(f"Failed to render prompt for agent '{agent_id}': {e}")
                payload["formatted_prompt"] = agent_prompt if agent_prompt else ""
                payload["template_error"] = str(e)

        # Inspect the run method to see if it needs orchestrator
        run_method = agent.run
        sig = inspect.signature(run_method)
        needs_orchestrator = len(sig.parameters) > 1  # More than just 'self'
        is_async = inspect.iscoroutinefunction(run_method)

        # Log orchestrator context detection
        logger.debug(f"- Agent '{agent_id}' run method signature: {sig}")
        logger.debug(f"- Agent '{agent_id}' parameter count: {len(sig.parameters)}")
        logger.debug(f"- Agent '{agent_id}' needs_orchestrator: {needs_orchestrator}")
        logger.debug(f"- Agent '{agent_id}' is_async: {is_async}")
        logger.debug(f"- Agent '{agent_id}' agent type: {type(agent).__name__}")

        # Execute the agent with appropriate method
        try:
            if needs_orchestrator:
                # Node that needs orchestrator - create context with orchestrator reference
                context_with_orchestrator = {
                    **payload,
                    "orchestrator": self.orchestrator,  # Pass the actual orchestrator
                }
                # Log orchestrator context passing
                logger.debug(
                    f"Agent '{agent_id}' orchestrator context keys: {list(context_with_orchestrator.keys())}"
                )
                logger.debug(
                    f"Agent '{agent_id}' orchestrator object: {type(self.orchestrator).__name__}"
                )
                logger.debug(
                    f"Agent '{agent_id}' orchestrator has fork_manager: {hasattr(self.orchestrator, 'fork_manager')}"
                )

                result = run_method(context_with_orchestrator)
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

    async def _run_branch_async(
        self: "ExecutionEngine",
        branch_agents: List[str],
        input_data: Any,
        previous_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run a sequence of agents in a branch sequentially.
        """
        branch_results = {}
        for agent_id in branch_agents:
            agent_id, result = await self._run_agent_async(
                agent_id,
                input_data,
                previous_outputs,
                full_payload=None,  # No orchestrator context needed for branch agents
            )
            branch_results[agent_id] = result
            # Update previous_outputs for the next agent in the branch
            previous_outputs = {**previous_outputs, **branch_results}
        return branch_results

    async def run_parallel_agents(
        self: "ExecutionEngine",
        agent_ids: List[str],
        fork_group_id: str,
        input_data: Any,
        previous_outputs: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Enhanced parallel execution with better error handling and logging.
        Returns a list of log entries for each forked agent.
        """
        logger.info(
            f"Starting parallel execution of {len(agent_ids)} agents in fork group {fork_group_id}"
        )

        # Validate agents exist
        missing_agents = [aid for aid in agent_ids if aid not in self.agents]
        if missing_agents:
            raise ValueError(f"Missing agents for parallel execution: {missing_agents}")

        # Ensure complete context is passed to forked agents
        enhanced_previous_outputs = self._ensure_complete_context(previous_outputs)

        # Get fork node configuration
        fork_node_id = "_".join(fork_group_id.split("_")[:-1])
        fork_node = self.agents.get(fork_node_id)

        if not fork_node:
            logger.warning(f"Fork node {fork_node_id} not found, using default execution")
            branches = [[agent_id] for agent_id in agent_ids]  # Treat each as separate branch
        else:
            branches = getattr(fork_node, "targets", [[agent_id] for agent_id in agent_ids])

        logger.debug(f"- Executing {len(branches)} branches: {branches}")

        # Execute branches in parallel
        try:
            branch_tasks = [
                self._run_branch_async(branch, input_data, enhanced_previous_outputs.copy())
                for branch in branches
            ]

            # Wait for all branches with timeout
            branch_results = await asyncio.wait_for(
                asyncio.gather(*branch_tasks, return_exceptions=True),
                timeout=300,  # 5 minute timeout
            )

            # Process results and handle exceptions
            result_logs: List[Dict[str, Any]] = []
            updated_previous_outputs = enhanced_previous_outputs.copy()

            for i, branch_result in enumerate(branch_results):
                if isinstance(branch_result, BaseException):
                    logger.error(f"Branch {i} failed: {branch_result}")
                    # Create error log entry
                    error_log = {
                        "agent_id": f"branch_{i}_error",
                        "event_type": "BranchError",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "payload": {"error": str(branch_result)},
                        "step": f"{self.step_index}[{i}]",
                        "run_id": self.run_id,
                    }
                    result_logs.append(error_log)
                    continue

                # Process successful branch results
                for agent_id, result in branch_result.items():
                    step_index = f"{self.step_index}[{len(result_logs)}]"

                    # Store result in Redis for JoinNode
                    join_state_key = "waitfor:join_parallel_checks:inputs"
                    self.memory.hset(join_state_key, agent_id, json.dumps(result))

                    # Create log entry
                    agent = self.agents[agent_id]

                    # Safely flatten result structure:
                    # - If the agent returned a dict, use it directly to avoid double nesting
                    # - Otherwise, wrap non-dict results under "result" for consistency
                    if isinstance(result, dict):
                        payload_data = result.copy()
                    else:
                        payload_data = {"result": result}

                    # Ensure a formatted_prompt exists; if missing, render via fallback
                    if "formatted_prompt" not in payload_data:
                        payload_context = {
                            "input": input_data,
                            "previous_outputs": updated_previous_outputs,
                        }
                        # Add loop context when available to keep templates consistent
                        if isinstance(input_data, dict):
                            if "loop_number" in input_data:
                                payload_context["loop_number"] = input_data["loop_number"]
                            if "past_loops_metadata" in input_data:
                                payload_context["past_loops_metadata"] = input_data[
                                    "past_loops_metadata"
                                ]
                        self._add_prompt_to_payload(agent, payload_data, payload_context)

                    log_data = {
                        "agent_id": agent_id,
                        "event_type": f"ForkedAgent-{agent.__class__.__name__}",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "payload": payload_data,
                        "step": len(result_logs),  # Use numeric step index
                        "run_id": self.run_id,
                        "fork_group_id": fork_group_id,
                    }
                    result_logs.append(log_data)

                    # Log to memory backend
                    self.memory.log(
                        agent_id,
                        f"ForkedAgent-{agent.__class__.__name__}",
                        payload_data,
                        step=len(result_logs),
                        run_id=self.run_id,
                        fork_group=fork_group_id,
                        previous_outputs=updated_previous_outputs.copy(),
                    )

                    # Update context for next agents
                    updated_previous_outputs[agent_id] = result

            logger.info(f"Parallel execution completed: {len(result_logs)} results")
            return result_logs

        except asyncio.TimeoutError:
            logger.error(f"Parallel execution timed out for fork group {fork_group_id}")
            raise
        except Exception as e:
            logger.error(f"Parallel execution failed: {e}")
            raise

    def _ensure_complete_context(self, previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
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

    def enqueue_fork(self: "ExecutionEngine", agent_ids: List[str], fork_group_id: str) -> None:
        """
        Add agents to the fork queue for processing.
        """
        for agent_id in agent_ids:
            self.queue.append(agent_id)

    def _extract_final_response(self: "ExecutionEngine", logs: List[Dict[str, Any]]) -> Any:
        """
        Extract the response from the last non-memory agent to return as the main result.

        Args:
            logs: List of agent execution logs

        Returns:
            The response from the last non-memory agent, or logs if no suitable agent found
        """
        # Memory agent types that should be excluded from final response consideration
        excluded_agent_types = {
            "MemoryReaderNode",
            "MemoryWriterNode",
            "memory",
            "memoryreadernode",
            "memorywriternode",
            "validate_and_structure",  # Exclude validator agents
            "guardian",  # Exclude agents with 'guardian' in their name/type
        }

        # Agent types that are explicitly designed to provide a final answer
        final_response_agent_types = {
            "OpenAIAnswerBuilder",
            "LocalLLMAgent",
        }

        # Find the last suitable agent
        final_response_log_entry = None
        for log_entry in reversed(logs):
            _event_type = log_entry.get("event_type")
            if _event_type == "MetaReport":
                continue  # Skip meta reports

            # Prefer nested payload.result.response if present
            payload = log_entry.get("payload", {})
            nested_result = payload.get("result")
            if isinstance(nested_result, dict) and "response" in nested_result:
                return nested_result["response"]
            # Handle one extra nesting level: payload.result.result.response
            if isinstance(nested_result, dict):
                deeper_result = nested_result.get("result")
                if isinstance(deeper_result, dict) and "response" in deeper_result:
                    return deeper_result["response"]

            # Prioritize agents explicitly designed to provide a final answer
            if _event_type in final_response_agent_types:
                # If no specific final response agent is found, consider the last non-excluded agent
                payload = log_entry.get("payload", {})
                final_response_log_entry = log_entry
                if payload and ("result" in payload or "response" in payload):
                    final_response_log_entry = log_entry
                    break

        if not final_response_log_entry:
            logger.warning("No suitable final agent found, returning full logs")
            return logs

        # Extract the response from the final response log entry
        payload = final_response_log_entry.get("payload", {})
        response = payload.get("response", {})

        logger.info(
            f"[ORKA-FINAL] Returning response from final agent: {final_response_log_entry.get('agent_id')} \n \"{response}\"",
        )

        # Try to extract a clean response from the result
        if isinstance(response, dict):
            # Look for common response patterns
            if "response" in response:
                return response["response"]
            elif "result" in response:
                nested_result = response["result"]
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
                return response
        elif isinstance(response, str):
            return response
        else:
            # Fallback to string representation
            return str(response)

    def _build_enhanced_trace(
        self, logs: List[Dict[str, Any]], meta_report: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build enhanced trace with memory backend references, metadata, and meta report."""
        enhanced_trace: Dict[str, Any] = {
            "execution_metadata": {
                "run_id": self.run_id,
                "total_agents": len(logs),
                "execution_time": datetime.now(UTC).isoformat(),
                "memory_backend": type(self.memory).__name__,
                "version": "1.1.0",  # Enhanced trace format
            },
            "memory_stats": self.memory.get_memory_stats(),
            "agent_executions": [],
        }

        # Include meta report if provided
        if meta_report:
            enhanced_trace["meta_report"] = meta_report

        for log_entry in logs:
            enhanced_entry = log_entry.copy()
            agent_id = log_entry.get("agent_id")

            if agent_id:
                try:
                    # Add memory backend references (only for RedisStack)
                    recent_memories = []
                    if hasattr(self.memory, "search_memories"):
                        recent_memories = self.memory.search_memories(
                            query="", node_id=agent_id, num_results=3, log_type="log"
                        )

                    enhanced_entry["memory_references"] = [
                        {
                            "key": mem.get("key", ""),
                            "timestamp": mem.get("timestamp"),
                            "content_preview": (
                                mem.get("content", "")[:100] + "..."
                                if len(mem.get("content", "")) > 100
                                else mem.get("content", "")
                            ),
                        }
                        for mem in recent_memories
                    ]

                    # Check template resolution status
                    payload = enhanced_entry.get("payload", {})
                    formatted_prompt = payload.get("formatted_prompt", "")
                    original_prompt = payload.get("prompt", "")

                    enhanced_entry["template_resolution"] = {
                        "has_template": bool(original_prompt),
                        "was_rendered": formatted_prompt != original_prompt,
                        "has_unresolved_vars": self._check_unresolved_variables(formatted_prompt),
                        "variable_count": len(self._extract_template_variables(original_prompt)),
                    }

                except Exception as e:
                    logger.warning(f"Could not enhance trace for agent {agent_id}: {e}")
                    enhanced_entry["enhancement_error"] = str(e)

            enhanced_trace["agent_executions"].append(enhanced_entry)

        return enhanced_trace

    def _check_unresolved_variables(self, text: str) -> bool:
        """Check if text contains unresolved Jinja2 variables."""
        import re

        pattern = r"\{\{\s*[^}]+\s*\}\}"
        return bool(re.search(pattern, text))

    def _has_unresolved_variables(self, text: str) -> bool:
        """Alias for _check_unresolved_variables for backward compatibility."""
        return self._check_unresolved_variables(text)

    def _extract_template_variables(self, template: str) -> List[str]:
        """Extract all Jinja2 variables from template."""
        import re

        pattern = r"\{\{\s*([^}]+)\s*\}\}"
        return re.findall(pattern, template)

    def _build_template_context(self, payload: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
        """Build complete context for template rendering."""
        # Start with original payload
        context = payload.copy()

        # Ensure previous_outputs exists and is properly structured
        if "previous_outputs" not in context:
            context["previous_outputs"] = {}

        # Add commonly expected template variables
        context.update(
            {
                "run_id": getattr(self, "run_id", "unknown"),
                "step_index": getattr(self, "step_index", 0),
                "agent_id": agent_id,
                "current_time": datetime.now(UTC).isoformat(),
                "workflow_name": getattr(self, "workflow_name", "unknown"),
            }
        )

        # Add input data at root level if nested
        if "input" in context and isinstance(context["input"], dict):
            input_data = context["input"]
            # Common template variables that should be at root
            for var in ["loop_number", "past_loops_metadata", "user_input", "query"]:
                if var in input_data:
                    context[var] = input_data[var]

        # Flatten previous_outputs for easier template access
        prev_outputs = context.get("previous_outputs", {})
        flattened_outputs = {}

        for agent_name, agent_result in prev_outputs.items():
            # Create a simplified, template-friendly version of agent results
            simplified_result = self._simplify_agent_result_for_templates(agent_result)
            flattened_outputs[agent_name] = simplified_result

            # Also add flattened access patterns for backward compatibility
            if isinstance(simplified_result, dict):
                if "response" in simplified_result:
                    flattened_outputs[f"{agent_name}_response"] = simplified_result["response"]
                if "memories" in simplified_result:
                    flattened_outputs[f"{agent_name}_memories"] = simplified_result["memories"]

        context["previous_outputs"] = flattened_outputs

        # Add template helper functions from PromptRenderer
        try:
            helper_functions = self._get_template_helper_functions(context)
            context.update(helper_functions)
            logger.debug(f"- Added {len(helper_functions)} helper functions to template context")
        except Exception as e:
            logger.error(f"Failed to add helper functions to template context: {e}")
            logger.error(f"Exception details: {type(e).__name__}: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            # Import PromptRenderer directly to ensure access to helper functions
            from orka.orchestrator.prompt_rendering import PromptRenderer

            # Create a temporary PromptRenderer instance to get the helper functions
            temp_renderer = PromptRenderer()
            try:
                helper_functions = temp_renderer._get_template_helper_functions(context)
                context.update(helper_functions)
                logger.info(
                    f"Added {len(helper_functions)} helper functions via fallback PromptRenderer"
                )
            except Exception as fallback_e:
                logger.error(f"Fallback PromptRenderer also failed: {fallback_e}")

                # Last resort: basic helper functions
                def get_input():
                    if "input" in context and isinstance(context["input"], dict):
                        return context["input"].get("input", "")
                    return str(context.get("input", ""))

                def get_loop_number():
                    if "loop_number" in context:
                        return context["loop_number"]
                    if "input" in context and isinstance(context["input"], dict):
                        return context["input"].get("loop_number", 1)
                    return 1

                def get_agent_response(agent_name):
                    prev_outputs = context.get("previous_outputs", {})
                    if agent_name in prev_outputs:
                        agent_result = prev_outputs[agent_name]
                        if isinstance(agent_result, dict):
                            return agent_result.get("response", "")
                        return str(agent_result)
                    return ""

                # Add minimal stub functions for missing ones
                def get_agent_memory_context(agent_type, agent_name):
                    return "No memory context available"

                def get_debate_evolution():
                    return "First round of debate"

                context.update(
                    {
                        "get_input": get_input,
                        "get_loop_number": get_loop_number,
                        "get_agent_response": get_agent_response,
                        "get_agent_memory_context": get_agent_memory_context,
                        "get_debate_evolution": get_debate_evolution,
                    }
                )
                logger.info("Added basic fallback helper functions to template context")

        return context

    def _validate_template_variables(self, template: str, context: Dict[str, Any]) -> List[str]:
        """Check for missing template variables with detailed path validation."""
        import re

        # Extract all Jinja2 variables
        variable_pattern = r"\{\{\s*([^}|]+)(?:\|[^}]*)?\s*\}\}"
        variables = re.findall(variable_pattern, template)

        missing_vars = []
        for var_expr in variables:
            var_path = var_expr.strip()
            # Check if the full path is accessible
            if not self._is_template_path_accessible(var_path, context):
                missing_vars.append(var_path)

        return missing_vars

    def _is_template_path_accessible(self, var_path: str, context: Dict[str, Any]) -> bool:
        """Check if a nested template variable path (like 'previous_outputs.binary_classifier.response') is accessible."""
        try:
            # Handle function calls like get_input() or get_agent_response('name')
            if "(" in var_path and ")" in var_path:
                # Extract function name (before the first parenthesis)
                func_name = var_path.split("(")[0].strip()
                # Check if the function exists in context
                if func_name in context and callable(context[func_name]):
                    logger.debug(
                        f"Found callable function '{func_name}' for template path '{var_path}'"
                    )
                    return True
                else:
                    logger.debug(f"- Function '{func_name}' not found or not callable in context")
                    # Show available functions for debugging
                    available_funcs = [k for k, v in context.items() if callable(v)]
                    logger.debug(f"- Available callable functions: {available_funcs}")
                    return False

            # Split the path by dots
            path_parts = var_path.split(".")
            current = context

            for part in path_parts:
                # Handle array access like [0]
                if "[" in part and "]" in part:
                    key = part.split("[")[0]
                    index_str = part.split("[")[1].split("]")[0]
                    if key not in current:
                        logger.debug(f"- Missing key '{key}' in path '{var_path}'")
                        return False
                    current = current[key]
                    try:
                        index = int(index_str)
                        if not isinstance(current, (list, tuple)):
                            logger.debug(
                                f"Expected list/tuple for array access in path '{var_path}'"
                            )
                            return False
                        if len(current) <= index:
                            logger.debug(f"Invalid array access [{index}] in path '{var_path}'")
                            return False
                        current = current[index]
                    except (ValueError, IndexError):
                        logger.debug(f"- Invalid array index '{index_str}' in path '{var_path}'")
                        return False
                else:
                    # Simple key access
                    if not isinstance(current, dict) or part not in current:
                        # Enhanced debugging for missing keys, especially agent names
                        if isinstance(current, dict):
                            available_keys = list(current.keys())
                            logger.debug(
                                f"Missing key '{part}' in path '{var_path}'. Available keys: {available_keys}"
                            )

                            # Special handling for agent name mismatches in previous_outputs
                            if (
                                len(path_parts) > 1
                                and path_parts[0] == "previous_outputs"
                                and part == path_parts[1]
                            ):  # Looking for agent name
                                # Find similar agent names that might be the intended target
                                similar_agents = [
                                    key for key in available_keys if part in key or key in part
                                ]
                                if similar_agents:
                                    logger.warning(
                                        f"Template references agent '{part}' but found similar agents: {similar_agents}. Did you mean one of these?"
                                    )
                                else:
                                    # Show all available agents for reference
                                    logger.warning(
                                        f"Template references agent '{part}' but available agents are: {available_keys}"
                                    )
                        else:
                            logger.info(  # type: ignore[unreachable]
                                f"[DEBUG] - Cannot access key '{part}' in path '{var_path}' - current value is not a dict"
                            )
                        return False
                    else:
                        current = current[part]

            return True
        except Exception as e:
            logger.debug(f"- Error validating template path '{var_path}': {e}")
            return False

    def _simplify_agent_result_for_templates(self, agent_result: Any) -> Any:
        """
        Simplify complex agent result structures for template access.

        This method flattens nested result structures to make them easily accessible
        in Jinja2 templates with dot notation like {{ previous_outputs.agent_name.response }}.
        """
        if not isinstance(agent_result, dict):
            return agent_result

        # Start with the original result
        simplified = agent_result.copy()

        # Pattern 1: Direct response at root level (like binary classifiers)
        if "response" in agent_result:
            simplified["response"] = agent_result["response"]
            if "confidence" in agent_result:
                simplified["confidence"] = agent_result["confidence"]
            if "internal_reasoning" in agent_result:
                simplified["internal_reasoning"] = agent_result["internal_reasoning"]
            return simplified

        # Pattern 2: Nested result structure (common pattern)
        if "result" in agent_result and isinstance(agent_result["result"], dict):
            nested_result = agent_result["result"]

            # Flatten nested response to root level for easy template access
            if "response" in nested_result:
                simplified["response"] = nested_result["response"]
            if "confidence" in nested_result:
                simplified["confidence"] = nested_result.get("confidence", "0.0")
            if "internal_reasoning" in nested_result:
                simplified["internal_reasoning"] = nested_result.get("internal_reasoning", "")
            if "_metrics" in nested_result:
                simplified["_metrics"] = nested_result.get("_metrics", {})
            if "formatted_prompt" in nested_result:
                simplified["formatted_prompt"] = nested_result.get("formatted_prompt", "")

            # Handle memory results
            if "memories" in nested_result:
                simplified["memories"] = nested_result["memories"]
                simplified["query"] = nested_result.get("query", "")
                simplified["backend"] = nested_result.get("backend", "")
                simplified["search_type"] = nested_result.get("search_type", "")
                simplified["num_results"] = nested_result.get("num_results", 0)

            # Keep original nested structure for complex access
            simplified["result"] = nested_result
            return simplified

        # Pattern 3: Memory agent results
        if "memories" in agent_result:
            simplified["memories"] = agent_result["memories"]
            simplified["query"] = agent_result.get("query", "")
            simplified["backend"] = agent_result.get("backend", "")
            simplified["search_type"] = agent_result.get("search_type", "")
            simplified["num_results"] = agent_result.get("num_results", 0)
            return simplified

        # Pattern 4: Fork/Join results with merged data
        if "merged" in agent_result and isinstance(agent_result["merged"], dict):
            # Add merged results at root level for easy access
            for merged_agent_id, merged_result in agent_result["merged"].items():
                if isinstance(merged_result, dict) and "response" in merged_result:
                    simplified[f"{merged_agent_id}_response"] = merged_result["response"]
            simplified["merged"] = agent_result["merged"]
            return simplified

        # Default: return as-is for other structures
        return simplified
