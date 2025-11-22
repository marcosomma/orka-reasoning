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
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .base_node import BaseNode

logger = logging.getLogger(__name__)


def _make_json_serializable(obj: Any) -> Any:
    """Convert non-JSON-serializable objects to serializable formats."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return _make_json_serializable(vars(obj))
    else:
        return obj


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

            # Filter out control flow nodes (PathExecutor, GraphScout, validators) from path
            original_path_length = len(agent_path)
            agent_path = [
                agent_id for agent_id in agent_path
                if agent_id != self.node_id  # Skip self to prevent recursion
                and not self._is_control_flow_node(agent_id, context)
            ]
            
            if len(agent_path) < original_path_length:
                filtered_count = original_path_length - len(agent_path)
                logger.info(
                    f"PathExecutor '{self.node_id}': Filtered {filtered_count} control flow node(s) "
                    f"from path (including self: {self.node_id})"
                )

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
                "results": _make_json_serializable(results),
                "status": status,
            }

            if errors:
                result_dict["errors"] = _make_json_serializable(errors)

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

        🐛 Bug #3 Fix: Try multiple path variants to handle different output structures

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

        # Try multiple path variants to handle different output structures
        paths_to_try = [
            self.path_source,  # Original path
        ]

        # Generate common variations
        # Example: "loop.response.result.agent.target" ->
        #   also try: "loop.result.agent.target", "loop.response.agent.target"
        parts = self.path_source.split(".")

        # Try removing 'response' if present
        if "response" in parts:
            variant = [p for p in parts if p != "response"]
            paths_to_try.append(".".join(variant))

        # Try removing 'result' if present
        if "result" in parts:
            variant = [p for p in parts if p != "result"]
            paths_to_try.append(".".join(variant))

        # Try adding '.response' if not present
        if "response" not in parts and len(parts) > 1:
            variant = parts[:1] + ["response"] + parts[1:]
            paths_to_try.append(".".join(variant))

        # Try each path variant
        last_error = None
        for path_variant in paths_to_try:
            agent_path, error, resolved_obj, decision_container = self._try_navigate_path(
                previous_outputs, path_variant
            )
            if agent_path is not None:
                decision_type = self._extract_decision(
                    decision_container, previous_outputs, resolved_obj
                )

                # Handle shortlist by executing ALL candidates (not just best)
                if decision_type == "shortlist":
                    logger.info(
                        f"PathExecutor '{self.node_id}': GraphScout returned shortlist with {len(agent_path)} agents, "
                        f"will execute all in sequence: {agent_path}"
                    )
                    # agent_path already contains all agents from shortlist (excluding logical ones)
                    # Just continue to execute them all
                    pass  # Continue to return agent_path normally
                elif decision_type and decision_type not in {"commit_next", "commit_path", "shortlist"}:
                    logger.error(
                        f"PathExecutor '{self.node_id}': Decision '{decision_type}' is not executable "
                        f"for path_source '{path_variant}'."
                    )
                    return [], (
                        f"GraphScout decision '{decision_type}' cannot be executed automatically. "
                        "Awaiting validated path."
                    )

                if decision_type == "commit_next" and len(agent_path) > 1:
                    agent_path = [agent_path[0]]

                logger.info(
                    f"PathExecutor '{self.node_id}': [OK] Successfully extracted path using variant '{path_variant}': {agent_path}"
                )
                return agent_path, None
            else:
                logger.debug(
                    f"PathExecutor '{self.node_id}': [FAIL] Variant '{path_variant}' failed: {error}"
                )
            last_error = error

        # All variants failed - log structure for debugging
        logger.error(
            f"PathExecutor '{self.node_id}': [ERROR] Failed all path variants. Tried: {paths_to_try}"
        )
        logger.error(
            f"PathExecutor '{self.node_id}': Available keys in previous_outputs: {list(previous_outputs.keys())}"
        )
        # Log first level of structure to help debugging
        for key in list(previous_outputs.keys())[:5]:
            val = previous_outputs[key]
            if isinstance(val, dict):
                logger.error(f"  - {key}: dict with keys {list(val.keys())[:5]}")
            else:
                logger.error(f"  - {key}: {type(val).__name__}")
        return [], last_error or "Could not find path data in any variant"

    def _try_navigate_path(
        self, previous_outputs: Dict[str, Any], path: str
    ) -> Tuple[Optional[List[str]], Optional[str], Optional[Any], Optional[Any]]:
        """
        Try to navigate a specific dot-notation path.

        Returns:
            Tuple of (agent_path or None, error_message or None, resolved_object, decision_container)
        """
        path_parts = path.split(".")
        current: Any = previous_outputs
        parent: Any = None

        for i, part in enumerate(path_parts):
            if not isinstance(current, dict):
                return None, f"Not a dict at '{'.'.join(path_parts[:i])}'", current, parent

            if part not in current:
                return None, f"Key '{part}' not found", current, parent

            parent = current
            current = current[part]

        # Extract agent list from the result
        agent_path = self._parse_agent_list(current)

        if agent_path is None:
            return None, f"No agent list at path '{path}'", current, parent

        return agent_path, None, current, parent

    def _extract_decision(
        self,
        decision_container: Optional[Any],
        previous_outputs: Dict[str, Any],
        resolved_obj: Any,
    ) -> Optional[str]:
        """
        Determine the decision type associated with the resolved GraphScout output.

        Args:
            decision_container: Immediate container object returned by navigation.
            previous_outputs: Full previous_outputs structure.
            resolved_obj: The resolved GraphScout target object.

        Returns:
            Decision string if available, otherwise None.
        """
        if isinstance(decision_container, dict) and isinstance(
            decision_value := decision_container.get("decision"), str
        ):
            return decision_value

        # Fall back to searching the broader previous_outputs structure
        return self._find_decision_for_target(previous_outputs, resolved_obj)

    def _find_decision_for_target(self, data: Any, target: Any) -> Optional[str]:
        """
        Recursively search for the decision type associated with a GraphScout target object.
        """
        if isinstance(data, dict):
            target_obj = data.get("target")
            if target_obj is target and isinstance(data.get("decision"), str):
                return str(data["decision"])
            for value in data.values():
                decision = self._find_decision_for_target(value, target)
                if decision is not None:
                    return decision

        elif isinstance(data, list):
            for item in data:
                decision = self._find_decision_for_target(item, target)
                if decision is not None:
                    return decision

        return None

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
            # Check if list contains dicts (GraphScout candidate format)
            if data and isinstance(data[0], dict):
                # Extract node_id from each candidate dict
                agent_ids = []
                for item in data:
                    if isinstance(item, dict) and "node_id" in item:
                        node_id = str(item["node_id"])
                        # Exclude logical/routing agents
                        if not self._is_logical_agent(node_id):
                            agent_ids.append(node_id)
                    elif (
                        isinstance(item, dict) and "path" in item and isinstance(item["path"], list)
                    ):
                        # Use path items, excluding logical agents
                        for path_item in item["path"]:
                            if not self._is_logical_agent(str(path_item)):
                                agent_ids.append(str(path_item))
                    else:
                        # Fallback: try to use as string
                        agent_id = str(item)
                        if not self._is_logical_agent(agent_id):
                            agent_ids.append(agent_id)
                return agent_ids if agent_ids else None
            else:
                # Simple list of agent ID strings
                return [str(agent_id) for agent_id in data if not self._is_logical_agent(str(agent_id))]

        # Case 2: Dict with 'target' field (GraphScout format)
        if isinstance(data, dict):
            if "target" in data:
                target = data["target"]
                if isinstance(target, list):
                    # Recursively parse the list (handles both dict and string formats)
                    return self._parse_agent_list(target)

            # Case 3: Dict with 'path' field (alternative format)
            if "path" in data:
                path = data["path"]
                if isinstance(path, list):
                    return [str(agent_id) for agent_id in path if not self._is_logical_agent(str(agent_id))]

        return None
    
    def _is_logical_agent(self, agent_id: str) -> bool:
        """
        Check if an agent is a logical/routing agent that should be excluded from execution.
        
        Logical agents include:
        - GraphScout agents (routing)
        - PathValidator agents (validation)
        - Loop nodes (control flow)
        - Fork/Join nodes (control flow)
        
        Args:
            agent_id: Agent identifier to check
            
        Returns:
            True if agent is logical and should be excluded, False otherwise
        """
        logical_patterns = [
            "graph_scout",
            "graphscout",
            "path_proposer",
            "path_validator",
            "validator",
            "router",
            "routing",
            "loop",
            "fork",
            "join",
        ]
        
        agent_id_lower = agent_id.lower()
        return any(pattern in agent_id_lower for pattern in logical_patterns)

    def _is_control_flow_node(self, agent_id: str, context: Dict[str, Any]) -> bool:
        """
        Check if an agent is a control flow node (PathExecutor, GraphScout, validators, etc.)
        that should not be executed by PathExecutor.
        
        Args:
            agent_id: ID of the agent to check
            context: Execution context with orchestrator reference
            
        Returns:
            True if agent is a control flow node, False otherwise
        """
        # Check by agent ID patterns
        control_patterns = [
            "path_executor", "pathexecutor",
            "graph_scout", "graphscout",
            "validator", "plan_validator",
            "classifier", "query_classifier"
        ]
        
        agent_id_lower = agent_id.lower()
        if any(pattern in agent_id_lower for pattern in control_patterns):
            return True
        
        # Check by agent type if available
        try:
            orchestrator = context.get("orchestrator")
            if orchestrator and hasattr(orchestrator, "agents"):
                agent_obj = orchestrator.agents.get(agent_id)
                if agent_obj:
                    agent_type = getattr(agent_obj, "type", "").lower()
                    agent_class = agent_obj.__class__.__name__
                    
                    # Check type string
                    if any(pattern in agent_type for pattern in control_patterns):
                        return True
                    
                    # Check class name
                    if any(cls_pattern in agent_class for cls_pattern in [
                        "PathExecutor", "GraphScout", "Validator", "Classifier"
                    ]):
                        return True
        except Exception:
            pass  # Fallback to ID-based check only
        
        return False

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
