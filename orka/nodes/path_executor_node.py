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
🚀 **PathExecutor Node** - Dynamic Agent Path Execution
=======================================================

The PathExecutorNode executes dynamically provided agent paths from validation loops,
GraphScout decisions, or manual configurations. It enables the "validate-then-execute"
pattern by taking validated agent sequences and actually executing them.

**Core Capabilities:**
- **Dynamic Execution**: Execute agent paths determined at runtime
- **Sequential Processing**: Run agents in order with result accumulation
- **Context Preservation**: Pass results between agents seamlessly
- **Error Handling**: Configurable failure behavior (continue or abort)

**Key Features:**
- Flexible path source configuration (dot notation support)
- Full integration with validation loops and GraphScout
- Comprehensive error handling and logging
- Result accumulation and propagation

**Use Cases:**
- Execute validated paths from PlanValidator + GraphScout loops
- Run dynamically selected agent sequences
- Implement validate-then-execute patterns
- Conditional agent execution based on runtime decisions

**Example Usage:**

.. code-block:: yaml

    agents:
      - id: validation_loop
        type: loop
        # Validates path and returns approved agent sequence

      - id: path_executor
        type: path_executor
        path_source: validation_loop.response.result.graphscout_router
        on_agent_failure: continue
        # Executes the validated agent sequence
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .base_node import BaseNode

logger = logging.getLogger(__name__)


class PathExecutorNode(BaseNode):
    """
    🚀 **The dynamic path executor** - executes validated agent sequences.

    **What makes PathExecutor powerful:**
    - **Runtime Flexibility**: Executes paths determined during execution
    - **Validation Integration**: Works seamlessly with validation loops
    - **Result Accumulation**: Passes outputs between agents automatically
    - **Error Resilience**: Configurable failure handling strategies

    **Common Patterns:**

    **1. Validate-Then-Execute:**

    .. code-block:: yaml

        agents:
          - id: validation_loop
            type: loop
            internal_workflow:
              agents: [graphscout_router, path_validator]

          - id: path_executor
            type: path_executor
            path_source: validation_loop.response.result.graphscout_router

    **2. GraphScout Direct Execution:**

    .. code-block:: yaml

        agents:
          - id: graphscout_router
            type: graph-scout

          - id: path_executor
            type: path_executor
            path_source: graphscout_router
            on_agent_failure: abort

    **3. Conditional Execution:**

    .. code-block:: yaml

        agents:
          - id: decision_maker
            type: local_llm
            # Returns: {"path": ["agent1", "agent2"]}

          - id: path_executor
            type: path_executor
            path_source: decision_maker.path

    **Perfect for:**
    - Validated path execution
    - Dynamic workflow routing
    - Conditional agent sequences
    - Runtime path determination
    """

    def __init__(
        self,
        node_id: str,
        path_source: str = "validated_path",
        on_agent_failure: str = "continue",
        **kwargs: Any,
    ):
        """
        Initialize the PathExecutor node.

        Args:
            node_id: Unique identifier for the node
            path_source: Dot-notation path to agent sequence in previous_outputs.
                        Can be:
                        - Simple key: "graphscout_router"
                        - Nested path: "validation_loop.response.result.graphscout_router"
                        - Direct field: "graphscout_router.target"
            on_agent_failure: Behavior when an agent fails:
                            - "continue": Log error and continue with next agent
                            - "abort": Stop execution and return error
            **kwargs: Additional configuration parameters

        Raises:
            ValueError: If on_agent_failure is not "continue" or "abort"
        """
        super().__init__(node_id=node_id, prompt=None, queue=None, **kwargs)

        self.path_source = path_source

        if on_agent_failure not in ("continue", "abort"):
            raise ValueError(
                f"PathExecutor '{node_id}': on_agent_failure must be 'continue' or 'abort', "
                f"got '{on_agent_failure}'"
            )
        self.on_agent_failure = on_agent_failure

        logger.info(
            f"PathExecutor '{node_id}' initialized: path_source='{path_source}', "
            f"on_agent_failure='{on_agent_failure}'"
        )

    async def _run_impl(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the validated agent path.

        Args:
            context: Execution context containing:
                    - input: Original input data
                    - previous_outputs: Dict containing path source
                    - orchestrator: Orchestrator instance for agent execution
                    - run_id: Execution run identifier

        Returns:
            Dict containing:
                - executed_path: List of agent IDs that were executed
                - results: Dict mapping agent_id -> agent_result
                - status: "success" or "partial" or "error"
                - errors: List of error messages (if any)
        """
        try:
            # Step 1: Extract agent path from previous outputs
            agent_path, extraction_error = self._extract_agent_path(context)

            if extraction_error:
                logger.error(f"PathExecutor '{self.node_id}': {extraction_error}")
                return {
                    "executed_path": [],
                    "results": {},
                    "status": "error",
                    "error": extraction_error,
                }

            if not agent_path:
                error_msg = (
                    f"PathExecutor '{self.node_id}': Extracted path is empty. "
                    f"path_source='{self.path_source}'"
                )
                logger.error(error_msg)
                return {
                    "executed_path": [],
                    "results": {},
                    "status": "error",
                    "error": error_msg,
                }

            logger.info(
                f"PathExecutor '{self.node_id}': Extracted path with {len(agent_path)} agents: "
                f"{agent_path}"
            )

            # Step 2: Validate execution context
            validation_error = self._validate_execution_context(context)
            if validation_error:
                logger.error(f"PathExecutor '{self.node_id}': {validation_error}")
                return {
                    "executed_path": [],
                    "results": {},
                    "status": "error",
                    "error": validation_error,
                }

            # Step 3: Execute agent sequence
            results, errors = await self._execute_agent_sequence(
                agent_path=agent_path, context=context
            )

            # Step 4: Determine status
            if errors and self.on_agent_failure == "abort":
                status = "error"
            elif errors:
                status = "partial"
            else:
                status = "success"

            result_dict: Dict[str, Any] = {
                "executed_path": agent_path,
                "results": results,
                "status": status,
            }

            if errors:
                result_dict["errors"] = errors

            logger.info(
                f"PathExecutor '{self.node_id}': Execution complete. "
                f"Status: {status}, Agents executed: {len(results)}/{len(agent_path)}"
            )

            return result_dict

        except Exception as e:
            error_msg = f"PathExecutor '{self.node_id}': Unexpected error: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "executed_path": [],
                "results": {},
                "status": "error",
                "error": error_msg,
            }

    def _extract_agent_path(self, context: Dict[str, Any]) -> Tuple[List[str], Optional[str]]:
        """
        Extract agent path from previous_outputs using path_source.

        Args:
            context: Execution context with previous_outputs

        Returns:
            Tuple of (agent_path_list, error_message)
            - agent_path_list: List of agent IDs to execute (empty if error)
            - error_message: Error description (None if successful)
        """
        previous_outputs = context.get("previous_outputs", {})

        if not previous_outputs:
            return [], "No previous_outputs available"

        # Navigate the dot-notation path
        path_parts = self.path_source.split(".")
        current = previous_outputs

        for i, part in enumerate(path_parts):
            if not isinstance(current, dict):
                partial_path = ".".join(path_parts[:i])
                return [], (
                    f"Cannot navigate path at '{partial_path}': "
                    f"expected dict, got {type(current).__name__}"
                )

            if part not in current:
                partial_path = ".".join(path_parts[: i + 1])
                available_keys = list(current.keys())[:5]
                return [], (
                    f"Key '{part}' not found in path '{partial_path}'. "
                    f"Available keys: {available_keys}"
                )

            current = current[part]

        # Extract agent list from the result
        agent_path = self._parse_agent_list(current)

        if agent_path is None:
            return [], (
                f"Could not extract agent list from path '{self.path_source}'. "
                f"Expected 'target' field or list, got: {type(current).__name__}"
            )

        return agent_path, None

    def _parse_agent_list(self, data: Any) -> Optional[List[str]]:
        """
        Parse agent list from various data formats.

        Args:
            data: Data that may contain agent list (dict with 'target', or list directly)

        Returns:
            List of agent IDs, or None if cannot parse
        """
        # Case 1: Direct list
        if isinstance(data, list):
            return [str(agent_id) for agent_id in data]

        # Case 2: Dict with 'target' field (GraphScout format)
        if isinstance(data, dict):
            if "target" in data:
                target = data["target"]
                if isinstance(target, list):
                    return [str(agent_id) for agent_id in target]

            # Case 3: Dict with 'path' field (alternative format)
            if "path" in data:
                path = data["path"]
                if isinstance(path, list):
                    return [str(agent_id) for agent_id in path]

        return None

    def _validate_execution_context(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Validate that execution context has required components.

        Args:
            context: Execution context

        Returns:
            Error message if validation fails, None if successful
        """
        if "orchestrator" not in context:
            return "Orchestrator context is missing (required for agent execution)"

        orchestrator = context["orchestrator"]
        if not orchestrator:
            return "Orchestrator is None"

        if not hasattr(orchestrator, "_run_agent_async"):
            return "Orchestrator missing '_run_agent_async' method"

        return None

    async def _execute_agent_sequence(
        self, agent_path: List[str], context: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Execute agents in sequence, accumulating results.

        Args:
            agent_path: List of agent IDs to execute
            context: Execution context with orchestrator

        Returns:
            Tuple of (results_dict, errors_list)
            - results_dict: Mapping of agent_id -> agent_result
            - errors_list: List of error messages for failed agents
        """
        orchestrator = context["orchestrator"]
        current_input = context.get("input")
        run_id = context.get("run_id", "unknown")

        execution_results: Dict[str, Any] = {}
        errors: List[str] = []

        for agent_id in agent_path:
            logger.info(f"PathExecutor '{self.node_id}': Executing agent '{agent_id}'")

            # Check if agent exists
            if not hasattr(orchestrator, "agents") or agent_id not in orchestrator.agents:
                error_msg = f"Agent '{agent_id}' not found in orchestrator"
                logger.error(f"PathExecutor '{self.node_id}': {error_msg}")
                errors.append(error_msg)

                if self.on_agent_failure == "abort":
                    logger.warning(
                        f"PathExecutor '{self.node_id}': Aborting execution due to missing agent"
                    )
                    break

                # Continue with error recorded
                execution_results[agent_id] = {"error": error_msg}
                continue

            # Build payload for agent execution
            payload = {
                "input": current_input,
                "previous_outputs": execution_results,
                "orchestrator": orchestrator,
                "run_id": run_id,
            }

            # Execute the agent
            try:
                _, agent_result = await orchestrator._run_agent_async(
                    agent_id, current_input, execution_results, full_payload=payload
                )

                execution_results[agent_id] = agent_result
                logger.info(
                    f"PathExecutor '{self.node_id}': Agent '{agent_id}' completed successfully"
                )
                logger.debug(
                    f"PathExecutor '{self.node_id}': Result preview: {str(agent_result)[:100]}"
                )

            except Exception as e:
                error_msg = f"Agent '{agent_id}' execution failed: {e}"
                logger.error(f"PathExecutor '{self.node_id}': {error_msg}", exc_info=True)
                errors.append(error_msg)

                execution_results[agent_id] = {"error": str(e)}

                if self.on_agent_failure == "abort":
                    logger.warning(
                        f"PathExecutor '{self.node_id}': Aborting execution due to agent failure"
                    )
                    break

        return execution_results, errors
