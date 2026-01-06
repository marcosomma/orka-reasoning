# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

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
- Near real-time execution metrics (deployment-dependent)
- Agent performance tracking
- Resource usage monitoring
- Error rate and pattern analysis
"""

import asyncio
import inspect
import json
import logging
import os
import traceback
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from time import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, TypeVar, cast
from ..contracts import OrkaResponse
from ..response_builder import ResponseBuilder
from .base import OrchestratorBase
from .execution.utils import json_serializer, sanitize_for_json
from .execution.context_manager import ContextManager
from .execution.parallel_executor import ParallelExecutor
from .execution.response_extractor import ResponseExtractor
from .execution.memory_router import MemoryRouter
from .execution.trace_builder import TraceBuilder
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
    - Resilience patterns and configurable recovery actions (operational validation required)
    - Optimization features (deployment-dependent)
    - Support for distributed execution patterns (requires validation and tests)

    Assumptions:
    - External systems (Redis, APIs) must be provisioned with appropriate HA and monitoring.

    Proof: See `tests/integration/test_execution_*` and `docs/INTEGRATION_EXAMPLES.md` for concrete verification and examples.

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
    - Near real-time monitoring and performance metrics (deployment-dependent)
    - Resource management and connection pooling
    - Distributed execution capabilities (operational validation required)

    Use Cases:
    - Multi-step AI reasoning workflows
    - High-throughput content processing pipelines
    - Near real-time decision systems with complex branching (deployment-dependent)
    - Resilience patterns for distributed applications (no absolute availability guarantees) 
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Initialize SimplifiedPromptRenderer explicitly to ensure render_template method is available
        SimplifiedPromptRenderer.__init__(self)
        self.agents: Dict[str, Any] = {}
        # Set orchestrator reference for fork/join nodes - ExecutionEngine is part of Orchestrator
        self.orchestrator = self
        # Initialize ContextManager for template/context helpers
        self._context_manager = ContextManager(self)
        # Initialize AgentRunner for agent execution
        self._agent_runner = __import__("orka.orchestrator.execution.agent_runner", fromlist=["AgentRunner"]).AgentRunner(self)
        # Initialize ParallelExecutor for fork/join operations
        self._parallel_executor = ParallelExecutor(self)
        # Initialize ResponseExtractor, MemoryRouter and TraceBuilder
        self._response_extractor = ResponseExtractor(self)
        self._memory_router = MemoryRouter(self)
        self._trace_builder = TraceBuilder(self)
        # Initialize ResponseNormalizer for standardized payload creation
        self._response_normalizer = __import__("orka.orchestrator.execution.response_normalizer", fromlist=["ResponseNormalizer"]).ResponseNormalizer(self)
        # Initialize ResponseProcessor to handle post-normalization processing (logging/storage/forks)
        self._response_processor = __import__("orka.orchestrator.execution.response_processor", fromlist=["ResponseProcessor"]).ResponseProcessor(self)

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
        # Delegate queue processing to QueueProcessor for easier migration
        processor = __import__("orka.orchestrator.execution.queue_processor", fromlist=["QueueProcessor"]).QueueProcessor(self)
        return await processor.run_queue(input_data, logs, return_logs)


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

        # Pass orchestrator-level structured output defaults to agents when configured
        try:
            so_defaults = self.orchestrator_cfg.get("structured_output_defaults")
            if isinstance(so_defaults, dict) and so_defaults:
                payload["structured_output_defaults"] = so_defaults
        except Exception:
            # Non-fatal: simply skip if orchestrator config not available
            pass

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

        # Delegate execution to AgentRunner
        return await self._agent_runner.run_agent_async(agent_id, input_data, previous_outputs, full_payload)

    async def _run_branch_with_retry(
        self: "ExecutionEngine",
        branch_agents: List[str],
        input_data: Any,
        previous_outputs: Dict[str, Any],
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ) -> Dict[str, Any]:
        """Run a branch with exponential backoff retry logic.

        This implementation calls `self._run_branch_async` which allows tests to
        monkeypatch engine-level branch behavior; if not patched, it will
        fall back to the agent-runner-backed implementation.
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
        """Run a sequence of agents in a branch sequentially.

        This calls `self._run_agent_async` for each agent which keeps the
        engine-level execution point patchable for tests while still delegating
        behavior to the AgentRunner by default.
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
        """Compatibility wrapper delegating parallel execution to ParallelExecutor."""
        return await self._parallel_executor.run_parallel_agents(agent_ids, fork_group_id, input_data, previous_outputs)

    def _ensure_complete_context(self, previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibility wrapper that delegates to ContextManager.ensure_complete_context."""
        return self._context_manager.ensure_complete_context(previous_outputs)

    def enqueue_fork(self: "ExecutionEngine", agent_ids: List[str], fork_group_id: str) -> None:
        """
        Add agents to the fork queue for processing.

        Behavior note:
        - Insert forked agents at the front of the queue so they execute immediately
          after the fork node. This preserves the user's expectation that the first
          layer of fork branches runs next instead of being processed at the end.
        """
        # Insert new agents at the front to ensure immediate execution ordering
        try:
            self.queue = list(agent_ids) + list(self.queue)
        except Exception:
            # Fallback to append behavior on unexpected queue types
            for agent_id in agent_ids:
                self.queue.append(agent_id)

    def _extract_final_response(self: "ExecutionEngine", logs: List[Dict[str, Any]]) -> Any:
        """Compatibility wrapper delegating to ResponseExtractor.extract_final_response."""
        return self._response_extractor.extract_final_response(logs)
    def _build_enhanced_trace(
        self, logs: List[Dict[str, Any]], meta_report: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Delegates enhanced trace building to the TraceBuilder component."""
        return self._trace_builder.build_enhanced_trace(logs, meta_report)

    def _check_unresolved_variables(self, text: str) -> bool:
        """Compatibility wrapper delegating to TraceBuilder.check_unresolved_variables."""
        return self._trace_builder.check_unresolved_variables(text)

    def _extract_template_variables(self, template: str) -> List[str]:
        """Compatibility wrapper delegating to TraceBuilder.extract_template_variables."""
        return self._trace_builder.extract_template_variables(template)

    def _build_template_context(self, payload: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
        """Compatibility wrapper that delegates to ContextManager.build_template_context."""
        return self._context_manager.build_template_context(payload, agent_id)

    # Template validation is now handled by SimplifiedPromptRenderer

    def _simplify_agent_result_for_templates(self, agent_result: Any) -> Any:
        """Compatibility wrapper that delegates to ContextManager.simplify_agent_result_for_templates."""
        return self._context_manager.simplify_agent_result_for_templates(agent_result)

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
        """Compatibility wrapper delegating to ResponseExtractor.validate_and_enforce_terminal_agent."""
        return self._response_extractor.validate_and_enforce_terminal_agent(queue)
    def _is_response_builder(self, agent_id: str) -> bool:
        """Compatibility wrapper delegating to ResponseExtractor.is_response_builder."""
        return self._response_extractor.is_response_builder(agent_id)
    def _apply_memory_routing_logic(self, shortlist: List[Dict[str, Any]]) -> List[str]:
        """Compatibility wrapper delegating to MemoryRouter.apply_memory_routing_logic."""
        return self._memory_router.apply_memory_routing_logic(shortlist)
    def _is_memory_agent(self, agent_id: str) -> bool:
        """Compatibility wrapper delegating to MemoryRouter.is_memory_agent."""
        return self._memory_router.is_memory_agent(agent_id)
    def _get_memory_operation(self, agent_id: str) -> str:
        """Get the operation type (read/write) for a memory agent."""
        return self._memory_router.get_memory_operation(agent_id)
    def _get_best_response_builder(self) -> str | None:
        """Compatibility wrapper delegating to ResponseExtractor._get_best_response_builder."""
        return self._response_extractor._get_best_response_builder()
