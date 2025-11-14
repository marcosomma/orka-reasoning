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

from ..contracts import OrkaResponse
from ..response_builder import ResponseBuilder
from .base import OrchestratorBase


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


from .error_handling import ErrorHandler as OrchestratorErrorHandling
from .metrics import MetricsCollector as OrchestratorMetricsCollector
from .simplified_prompt_rendering import SimplifiedPromptRenderer

logger = logging.getLogger(__name__)


# Define a type variable that is bound to ExecutionEngine and includes all necessary attributes
class ExecutionEngineProtocol(OrchestratorBase):
    """Protocol defining required attributes for ExecutionEngine type variable."""

    agents: Dict[str, Any]


T = TypeVar("T", bound="ExecutionEngineProtocol")


class ExecutionEngine(
    OrchestratorBase,
    SimplifiedPromptRenderer,
    OrchestratorErrorHandling,
    OrchestratorMetricsCollector,
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
        # Initialize SimplifiedPromptRenderer explicitly to ensure render_template method is available
        SimplifiedPromptRenderer.__init__(self)
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

                    # Add orchestrator to context for nodes that need it
                    if agent_type in (
                        "forknode",
                        "graphscoutagent",
                        "pathexecutornode",
                        "loopnode",
                        "loopvalidatornode",
                    ):
                        payload["orchestrator"] = self
                        payload["run_id"] = self.run_id

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

                        # Special handling for GraphScout decisions
                        if agent_type == "graphscoutagent":
                            logger.info(
                                f"🔍 DEBUG: GraphScout agent detected, agent_result type: {type(agent_result)}"
                            )
                            logger.info(
                                f"🔍 DEBUG: GraphScout agent_result keys: {list(agent_result.keys()) if isinstance(agent_result, dict) else 'Not a dict'}"
                            )

                            # 🔍 CRITICAL: Save remaining queue before GraphScout routing
                            # In sequential workflows, we want to preserve agents that come after GraphScout
                            remaining_queue = queue.copy()
                            logger.info(
                                f"🔍 DEBUG: Saved remaining queue ({len(remaining_queue)} agents): {remaining_queue}"
                            )

                            # ✅ CRITICAL FIX: Handle both OrkaResponse and legacy formats
                            graphscout_decision = None
                            if isinstance(agent_result, dict):
                                # Check for OrkaResponse format (decision in result field)
                                if (
                                    "result" in agent_result
                                    and isinstance(agent_result["result"], dict)
                                    and "decision" in agent_result["result"]
                                ):
                                    graphscout_decision = agent_result["result"]
                                    logger.info(
                                        f"🔍 DEBUG: Found GraphScout decision in OrkaResponse format"
                                    )
                                # Check for legacy format (decision at top level)
                                elif "decision" in agent_result:
                                    graphscout_decision = agent_result
                                    logger.info(
                                        f"🔍 DEBUG: Found GraphScout decision in legacy format"
                                    )

                            if graphscout_decision:
                                # CRITICAL: Log GraphScout result BEFORE routing to ensure it appears in traces
                                payload_out = {
                                    k: v for k, v in payload.items() if k != "orchestrator"
                                }
                                # 🔍 DEBUG: Check graphscout_decision before logging
                                logger.info(
                                    f"🔍 DEBUG: graphscout_decision before logging: {graphscout_decision.get('target')}"
                                )
                                payload_out.update(
                                    graphscout_decision
                                )  # Include the full GraphScout result
                                # 🔍 DEBUG: Check payload_out after update
                                logger.info(
                                    f"🔍 DEBUG: payload_out target after update: {payload_out.get('target')}"
                                )

                                # Log GraphScout execution
                                log_data = {
                                    "agent_id": agent_id,
                                    "event_type": "GraphScoutAgent",
                                    "timestamp": datetime.now(UTC).isoformat(),
                                    "payload": payload_out,
                                    "step": self.step_index,
                                    "run_id": self.run_id,
                                }
                                logs.append(log_data)

                                # Log to memory backend
                                if self.memory:
                                    self.memory.log(
                                        agent_id,
                                        "GraphScoutAgent",
                                        payload_out,
                                        step=self.step_index,
                                        run_id=self.run_id,
                                    )

                                # Note: Don't modify payload directly to avoid recursion issues
                                # The result will be stored in logs and available for subsequent agents

                                # Now handle routing decisions
                                # Create a copy to avoid modifying the logged result
                                decision_type = graphscout_decision.get("decision")
                                target = graphscout_decision.get("target")
                                # Work with a copy of the target to avoid modifying the original
                                if isinstance(target, list):
                                    target = target.copy()

                                if decision_type == "commit_next" and target:
                                    # Route to single next agent, then continue with remaining queue
                                    initial_queue = [str(target)]
                                    # ✅ STRUCTURED ENFORCEMENT: Validate terminal agent
                                    validated_queue = self._validate_and_enforce_terminal_agent(
                                        initial_queue
                                    )
                                    queue = validated_queue + remaining_queue
                                    logger.info(
                                        f"GraphScout routing to: {target}, then {len(remaining_queue)} remaining agents"
                                    )
                                    continue
                                elif decision_type == "commit_path" and target:
                                    # Route to path sequence, then continue with remaining queue
                                    if isinstance(target, list):
                                        # ✅ STRUCTURED ENFORCEMENT: Validate terminal agent
                                        validated_path = self._validate_and_enforce_terminal_agent(
                                            target
                                        )
                                        queue = validated_path + remaining_queue
                                        logger.info(
                                            f"GraphScout routing to path: {validated_path}, then {len(remaining_queue)} remaining agents"
                                        )
                                        continue
                                elif decision_type == "shortlist":
                                    # ========================================================================
                                    # CRITICAL: GraphScout Shortlist Handling - Validation vs Execution
                                    # ========================================================================
                                    # GraphScout returns "shortlist" decision type in TWO distinct scenarios:
                                    #
                                    # 1. VALIDATION PATTERN (Propose → Validate → Execute):
                                    #    - GraphScout proposes a path for validator to score
                                    #    - Validator (PlanValidator) runs next in queue
                                    #    - DO NOT auto-execute the shortlist
                                    #    - Let validator score the proposal first
                                    #    - PathExecutor executes AFTER validation passes
                                    #
                                    # 2. DIRECT EXECUTION PATTERN (Propose → Execute):
                                    #    - GraphScout makes final routing decision
                                    #    - No validator in remaining queue
                                    #    - DO auto-execute the shortlist immediately
                                    #    - Legacy behavior for direct GraphScout routing
                                    #
                                    # We distinguish patterns by checking if a validator is next in queue.
                                    # This prevents premature execution before validation completes.
                                    # ========================================================================

                                    has_validator = any(
                                        "validator" in agent_id.lower()
                                        or "path_validator" in agent_id.lower()
                                        for agent_id in remaining_queue
                                    )

                                    if has_validator:
                                        # VALIDATION PATTERN DETECTED
                                        # GraphScout proposal stored in agent result, validator runs next
                                        # The validator will access the proposal via previous_outputs
                                        # and score it using boolean criteria or numeric scoring
                                        logger.info(
                                            f"GraphScout returned shortlist for VALIDATION (not execution). "
                                            f"Validator will score this proposal: {remaining_queue[0] if remaining_queue else 'unknown'}"
                                        )
                                        # Continue normal flow - validator runs next in sequence
                                    else:
                                        # DIRECT EXECUTION PATTERN DETECTED
                                        # No validator found - this is a direct routing decision
                                        # Auto-execute the shortlist as the final path
                                        shortlist = graphscout_decision.get("target", [])
                                        if shortlist:
                                            # Apply memory agent routing logic
                                            agent_sequence = self._apply_memory_routing_logic(
                                                shortlist
                                            )

                                            # 🔍 CRITICAL FIX: Append remaining queue to preserve sequential workflow
                                            # GraphScout provides routing suggestions, but shouldn't override the workflow structure
                                            queue = agent_sequence + remaining_queue
                                            logger.info(
                                                f"GraphScout routing sequence: {' → '.join(agent_sequence)} ({len(agent_sequence)} agents), "
                                                f"then continuing with {len(remaining_queue)} remaining agents: {remaining_queue}"
                                            )
                                            continue
                                    # For fallback or other decisions, continue normal execution

                        # Create a copy of the payload for logging (without orchestrator)
                        payload_out = {k: v for k, v in payload.items() if k != "orchestrator"}

                        # Handle OrkaResponse format (new standardized format)
                        if isinstance(agent_result, dict) and "component_type" in agent_result:
                            # This is an OrkaResponse - use it directly
                            payload_out.update(
                                {
                                    "result": agent_result.get("result"),
                                    "status": agent_result.get("status"),
                                    "error": agent_result.get("error"),
                                    "response": agent_result.get("result"),  # Legacy compatibility
                                    "confidence": agent_result.get("confidence", "0.0"),
                                    "internal_reasoning": agent_result.get(
                                        "internal_reasoning", ""
                                    ),
                                    "formatted_prompt": agent_result.get("formatted_prompt", ""),
                                    "execution_time_ms": agent_result.get("execution_time_ms"),
                                    "token_usage": agent_result.get("token_usage"),
                                    "cost_usd": agent_result.get("cost_usd"),
                                    "memory_entries": agent_result.get("memory_entries"),
                                    "memories": agent_result.get(
                                        "memory_entries"
                                    ),  # Legacy compatibility
                                    "_metrics": agent_result.get("metrics", {}),
                                    "trace_id": agent_result.get("trace_id"),
                                }
                            )
                            payload_out = {k: v for k, v in payload_out.items() if v is not None}
                        # Handle legacy response formats (for backward compatibility during migration)
                        elif isinstance(agent_result, dict):
                            # 🔍 CRITICAL: Preserve LoopNode top-level metadata
                            # LoopNode returns important fields like loops_completed, final_score, threshold_met
                            # that must be preserved at the top level for template access
                            logger.debug(
                                f"Processing dict result for agent_id={agent_id}, agent_type={agent_type}, "
                                f"has_result={('result' in agent_result)}, "
                                f"has_loops_completed={('loops_completed' in agent_result)}, "
                                f"has_final_score={('final_score' in agent_result)}, "
                                f"top_level_keys={list(agent_result.keys())[:10]}"
                            )
                            if agent_type == "loopnode" and all(
                                k in agent_result
                                for k in ["result", "loops_completed", "final_score"]
                            ):
                                # LoopNode: Preserve complete structure with metadata
                                payload_out.update(
                                    {
                                        "response": agent_result,  # Complete LoopNode result
                                        "result": agent_result.get(
                                            "result"
                                        ),  # Also at result for compatibility
                                        "loops_completed": agent_result.get("loops_completed"),
                                        "final_score": agent_result.get("final_score"),
                                        "threshold_met": agent_result.get("threshold_met"),
                                        "past_loops": agent_result.get("past_loops", []),
                                        "status": "success",
                                        "confidence": "1.0",
                                        "internal_reasoning": "",
                                    }
                                )
                                logger.debug(
                                    f"LoopNode result preserved: loops={agent_result.get('loops_completed')}, "
                                    f"score={agent_result.get('final_score')}, "
                                    f"threshold_met={agent_result.get('threshold_met')}"
                                )
                            else:
                                # Convert legacy response to OrkaResponse format for consistency
                                if "response" in agent_result:
                                    converted_response = ResponseBuilder.from_llm_agent_response(
                                        agent_result, agent_id
                                    )
                                elif "memories" in agent_result:
                                    converted_response = ResponseBuilder.from_memory_agent_response(
                                        agent_result, agent_id
                                    )
                                else:
                                    converted_response = ResponseBuilder.from_node_response(
                                        agent_result, agent_id
                                    )

                                payload_out.update(
                                    {
                                        "result": converted_response.get("result"),
                                        "status": converted_response.get("status"),
                                        "error": converted_response.get("error"),
                                        "response": converted_response.get(
                                            "result"
                                        ),  # Legacy compatibility
                                        "confidence": converted_response.get("confidence", "0.0"),
                                        "internal_reasoning": converted_response.get(
                                            "internal_reasoning", ""
                                        ),
                                        "formatted_prompt": converted_response.get(
                                            "formatted_prompt", ""
                                        ),
                                        "execution_time_ms": converted_response.get(
                                            "execution_time_ms"
                                        ),
                                        "token_usage": converted_response.get("token_usage"),
                                        "cost_usd": converted_response.get("cost_usd"),
                                        "memory_entries": converted_response.get("memory_entries"),
                                        "memories": converted_response.get(
                                            "memory_entries"
                                        ),  # Legacy compatibility
                                        "_metrics": converted_response.get("metrics", {}),
                                        "trace_id": converted_response.get("trace_id"),
                                    }
                                )
                            payload_out = {k: v for k, v in payload_out.items() if v is not None}
                        else:
                            # Non-dict result - convert to OrkaResponse format
                            converted_response = ResponseBuilder.from_tool_response(
                                agent_result, agent_id
                            )
                            payload_out.update(
                                {
                                    "result": converted_response.get("result"),
                                    "status": converted_response.get("status"),
                                    "response": converted_response.get(
                                        "result"
                                    ),  # Legacy compatibility
                                    "_metrics": converted_response.get("metrics", {}),
                                }
                            )
                            payload_out = {k: v for k, v in payload_out.items() if v is not None}

                        # Special handling for fork and join nodes
                        if agent_type == "forknode":
                            # Fork node logs immediately, then executes children
                            # Extract fork data from OrkaResponse format
                            fork_result = (
                                agent_result.get("result", {})
                                if isinstance(agent_result, dict)
                                else {}
                            )
                            fork_group_id = fork_result.get("fork_group")
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
                                forked_agents = fork_result.get("agents", [])
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
                                        logger.error(
                                            f"Fork execution failed for group {fork_group_id}: {type(fork_error).__name__}: {fork_error}. "
                                            f"Agents: {forked_agents}. Check individual agent logs for details."
                                        )

                                # Skip normal logging since we already logged the fork node
                                continue

                        elif agent_type == "joinnode":
                            # Join nodes handle their own coordination internally
                            # No special handling needed here - let the join node do its work
                            pass

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
            # Ensure agent_prompt is a string, not a dict
            agent_prompt = str(agent.prompt) if not isinstance(agent.prompt, str) else agent.prompt
        elif (
            hasattr(agent, "llm_agent")
            and hasattr(agent.llm_agent, "prompt")
            and agent.llm_agent.prompt
        ):
            # Ensure agent_prompt is a string, not a dict
            agent_prompt = (
                str(agent.llm_agent.prompt)
                if not isinstance(agent.llm_agent.prompt, str)
                else agent.llm_agent.prompt
            )

        if agent_prompt:
            try:
                # Use simplified template rendering
                formatted_prompt = self.render_template(agent_prompt, payload)
                payload["formatted_prompt"] = formatted_prompt

                # Log successful rendering
                logger.info(f"Template rendered for '{agent_id}' - length: {len(formatted_prompt)}")
                logger.debug(f"- Rendered preview: {formatted_prompt[:200]}...")
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

    async def _run_branch_with_retry(
        self: "ExecutionEngine",
        branch_agents: List[str],
        input_data: Any,
        previous_outputs: Dict[str, Any],
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Run a branch with exponential backoff retry logic.

        Args:
            branch_agents: List of agent IDs to execute sequentially
            input_data: Input data for the branch
            previous_outputs: Context from previous agents
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            Branch execution results

        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                result = await self._run_branch_async(branch_agents, input_data, previous_outputs)

                if attempt > 0:
                    logger.info(f"Branch {branch_agents} succeeded on retry {attempt}")

                return result

            except Exception as e:
                last_exception = e

                if attempt < max_retries:
                    delay = retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Branch {branch_agents} failed (attempt {attempt + 1}/{max_retries + 1}): "
                        f"{type(e).__name__}: {e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Branch {branch_agents} failed after {max_retries + 1} attempts: "
                        f"{type(e).__name__}: {e}"
                    )

        # All retries exhausted
        raise last_exception  # type: ignore

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

        # Execute branches in parallel with retry logic
        try:
            branch_tasks = [
                self._run_branch_with_retry(
                    branch,
                    input_data,
                    enhanced_previous_outputs.copy(),
                    max_retries=2,  # Configurable via orchestrator config
                    retry_delay=1.0,
                )
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
                    # ENHANCED: Capture full exception details
                    error_type = type(branch_result).__name__
                    error_msg = str(branch_result)
                    error_traceback = None

                    if hasattr(branch_result, "__traceback__"):
                        import traceback

                        error_traceback = "".join(
                            traceback.format_exception(
                                type(branch_result), branch_result, branch_result.__traceback__
                            )
                        )

                    # Log with full context
                    logger.error(
                        f"Branch {i} failed with {error_type}: {error_msg}\n"
                        f"Branch agents: {branches[i]}\n"
                        f"Fork group: {fork_group_id}"
                    )

                    if error_traceback:
                        logger.debug(f"Full traceback:\n{error_traceback}")

                    # Create comprehensive error log entry
                    error_log = {
                        "agent_id": f"branch_{i}_error",
                        "event_type": "BranchError",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "payload": {
                            "error": error_msg,
                            "error_type": error_type,
                            "error_traceback": error_traceback,
                            "branch_agents": branches[i],
                            "fork_group_id": fork_group_id,
                        },
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
                    self.memory.hset(
                        join_state_key, agent_id, json.dumps(result, default=json_serializer)
                    )

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

            # Check if we have any successful branches
            successful_branches = [r for r in branch_results if not isinstance(r, BaseException)]

            if not successful_branches and len(branch_results) > 0:
                # All branches failed - create fallback result
                logger.error(
                    f"All {len(branch_results)} branches failed in fork group {fork_group_id}. "
                    "Creating fallback empty result."
                )

                # Return minimal valid structure so workflow can continue
                fallback_result = {
                    "status": "partial_failure",
                    "successful_branches": 0,
                    "total_branches": len(branch_results),
                    "error": "All parallel branches failed",
                }

                # Add to result logs
                result_logs.append(
                    {
                        "agent_id": f"{fork_group_id}_fallback",
                        "event_type": "ForkGroupFallback",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "payload": fallback_result,
                        "step": self.step_index,
                        "run_id": self.run_id,
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
                logger.info(
                    f"[ORKA-FINAL] Returning response from final agent: {log_entry.get('agent_id')}",
                )
                return nested_result["response"]
            # Handle one extra nesting level: payload.result.result.response
            if isinstance(nested_result, dict):
                deeper_result = nested_result.get("result")
                if isinstance(deeper_result, dict) and "response" in deeper_result:
                    logger.info(
                        f"[ORKA-FINAL] Returning response from final agent: {log_entry.get('agent_id')}",
                    )
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
            f"[ORKA-FINAL] Returning response from final agent: {final_response_log_entry.get('agent_id')}",
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

        # Template helper functions are now handled by SimplifiedPromptRenderer

        return context

    # Template validation is now handled by SimplifiedPromptRenderer

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

    def _select_best_candidate_from_shortlist(
        self, shortlist: List[Dict[str, Any]], question: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Select the best candidate from GraphScout's shortlist.

        GraphScout has already done sophisticated evaluation including LLM assessment,
        scoring, and ranking. We should trust its decision and use the top candidate.

        Args:
            shortlist: List of candidate agents from GraphScout (already ranked by score)
            question: The user's question
            context: Execution context

        Returns:
            The best candidate from the shortlist (typically the first one)
        """
        try:
            if not shortlist:
                return {}

            # Trust GraphScout's intelligent ranking - use the top candidate
            best_candidate = shortlist[0]
            logger.info(
                f"Selected GraphScout's top choice: {best_candidate.get('node_id')} "
                f"(score: {best_candidate.get('score', 0.0):.3f})"
            )
            return best_candidate

        except Exception as e:
            logger.error(f"Candidate selection failed: {e}")
            # Return first candidate as ultimate fallback
            return shortlist[0] if shortlist else {}

    def _validate_and_enforce_terminal_agent(self, queue: List[str]) -> List[str]:
        """
        Validate that the workflow queue ends with an LLM-based response builder.
        If not, automatically append the best available response builder.

        Args:
            queue: Current agent execution queue

        Returns:
            Validated queue with guaranteed LLM terminal agent
        """
        if not queue:
            return queue

        # Check if the last agent is already a response builder
        last_agent_id = queue[-1]
        if self._is_response_builder(last_agent_id):
            logger.info(f"✅ Terminal validation passed: {last_agent_id} is a response builder")
            return queue

        # Find the best response builder to append
        response_builder = self._get_best_response_builder()
        if response_builder:
            validated_queue = queue + [response_builder]
            logger.info(f"🔧 Terminal enforcement: Added {response_builder} to ensure LLM response")
            logger.info(f"📋 Final validated queue: {validated_queue}")
            return validated_queue
        else:
            logger.warning(
                "⚠️ No response builder found - workflow may not provide comprehensive response"
            )
            return queue

    def _is_response_builder(self, agent_id: str) -> bool:
        """Check if an agent is a response builder."""
        if agent_id not in self.agents:
            return False

        agent = self.agents[agent_id]
        agent_type = getattr(agent, "type", "").lower()

        # Response builder identification criteria
        return (
            any(
                term in agent_type
                for term in ["localllm", "local_llm", "answer", "response", "builder"]
            )
            and "classification" not in agent_type
        )

    def _apply_memory_routing_logic(self, shortlist: List[Dict[str, Any]]) -> List[str]:
        """
        Apply intelligent memory agent routing logic.

        Memory agents have special positioning rules:
        - Memory readers (read operation) should be at the beginning of the path
        - Memory writers (write operation) should be at the end of the path
        - Other agents maintain their relative order

        Args:
            shortlist: List of candidate agents from GraphScout

        Returns:
            Intelligently ordered list of agent IDs
        """
        try:
            # Separate agents by type
            memory_readers = []
            memory_writers = []
            regular_agents = []
            response_builder_found = False

            for candidate in shortlist:
                # GraphScout candidates have a 'path' field with the full agent sequence
                candidate_path = candidate.get("path")

                # Fallback: if no path, use node_id as single-item path
                if not candidate_path:
                    agent_id = candidate.get("node_id")
                    candidate_path = [agent_id] if agent_id else []

                # Ensure candidate_path is a list
                if not isinstance(candidate_path, list):
                    candidate_path = [candidate_path]

                # Process each agent in the path
                for agent_id in candidate_path:
                    if not agent_id:
                        continue

                    # Check if this is a memory agent
                    if self._is_memory_agent(agent_id):
                        operation = self._get_memory_operation(agent_id)
                        if operation == "read":
                            memory_readers.append(agent_id)
                            logger.info(
                                f"Memory reader agent detected: {agent_id} - positioning at beginning"
                            )
                        elif operation == "write":
                            memory_writers.append(agent_id)
                            logger.info(
                                f"Memory writer agent detected: {agent_id} - positioning at end"
                            )
                        else:
                            # Unknown memory operation, treat as regular agent
                            regular_agents.append(agent_id)
                    elif self._is_response_builder(agent_id):
                        regular_agents.append(agent_id)
                        response_builder_found = True
                    else:
                        regular_agents.append(agent_id)

            # Build the intelligent sequence: readers → regular agents → writers → response_builder
            agent_sequence = []

            # 1. Memory readers first (for context retrieval)
            agent_sequence.extend(memory_readers)

            # 2. Regular processing agents (excluding response builders for now)
            non_response_regular = [
                agent for agent in regular_agents if not self._is_response_builder(agent)
            ]
            agent_sequence.extend(non_response_regular)

            # 3. Memory writers (to store processed information)
            agent_sequence.extend(memory_writers)

            # 4. Response builder last (if not already present, add one)
            if not response_builder_found:
                response_builder = self._get_best_response_builder()
                if response_builder and response_builder not in agent_sequence:
                    agent_sequence.append(response_builder)
            else:
                # Add existing response builders at the end
                response_builders = [
                    agent for agent in regular_agents if self._is_response_builder(agent)
                ]
                agent_sequence.extend(response_builders)

            logger.info(
                f"Memory routing applied: readers={memory_readers}, writers={memory_writers}, regular={len(non_response_regular)}"
            )
            return agent_sequence

        except Exception as e:
            logger.error(f"Failed to apply memory routing logic: {e}")
            # Fallback to original order
            return [
                str(candidate.get("node_id"))
                for candidate in shortlist
                if candidate.get("node_id") is not None
            ]

    def _is_memory_agent(self, agent_id: str) -> bool:
        """Check if an agent is a memory agent (reader or writer)."""
        try:
            if hasattr(self, "orchestrator") and hasattr(self.orchestrator, "agents"):
                agent = self.orchestrator.agents.get(agent_id)
                if agent:
                    agent_class_name = agent.__class__.__name__
                    return agent_class_name in ["MemoryReaderNode", "MemoryWriterNode"]
            return False
        except Exception as e:
            logger.error(f"Failed to check if {agent_id} is memory agent: {e}")
            return False

    def _get_memory_operation(self, agent_id: str) -> str:
        """Get the operation type (read/write) for a memory agent."""
        try:
            if hasattr(self, "orchestrator") and hasattr(self.orchestrator, "agents"):
                agent = self.orchestrator.agents.get(agent_id)
                if agent:
                    agent_class_name = agent.__class__.__name__
                    if agent_class_name == "MemoryReaderNode":
                        return "read"
                    elif agent_class_name == "MemoryWriterNode":
                        return "write"
            return "unknown"
        except Exception as e:
            logger.error(f"Failed to get memory operation for {agent_id}: {e}")
            return "unknown"

    def _get_best_response_builder(self) -> str | None:
        """Get the best available response builder from the orchestrator configuration."""
        original_agents = self.orchestrator_cfg.get("agents", [])
        response_builders = []

        for agent_id in original_agents:
            if self._is_response_builder(agent_id):
                response_builders.append(agent_id)

        if not response_builders:
            return None

        # Priority order: response_builder > local_llm > others
        for builder in response_builders:
            if "response_builder" in builder.lower():
                return str(builder)

        # Return first available response builder
        return str(response_builders[0])
