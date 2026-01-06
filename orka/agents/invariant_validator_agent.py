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
Invariant Validator Agent
==========================

Executes deterministic validation of orchestrator execution invariants.
This is a Python-based agent (not LLM) that computes hard facts about
execution correctness.
"""

import re
import json
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING
from .base_agent import BaseAgent
from ..orchestrator.execution_invariants import (
    ExecutionInvariantsValidator,
    ExecutionInvariants,
)

if TYPE_CHECKING:
    from ..contracts import Context

logger = logging.getLogger(__name__)


class InvariantValidatorAgent(BaseAgent):
    """
    Agent that validates execution invariants deterministically.
    
    This is NOT an LLM agent - it performs deterministic checks on
    execution artifacts to detect structural issues.
    
    Usage in YAML:
    ```yaml
    - id: invariant_validator
      type: invariant_validator
      params:
        max_depth: 5
        allow_reentrant_nodes: ["loop_iteration"]
        strict_tool_errors: false
        # Data sources for validation (template these from context)
        execution_data:
          nodes_executed: "{{ nodes_executed }}"
          fork_groups: "{{ fork_groups }}"
          router_decisions: "{{ router_decisions }}"
          tool_calls: "{{ tool_calls }}"
          structured_outputs: "{{ structured_outputs }}"
          graph_structure: "{{ graph_structure }}"
    """
    
    def __init__(
        self,
        agent_id: str,
        prompt: str = "",
        queue: Optional[list] = None,
        **kwargs
    ):
        """
        Initialize invariant validator agent.
        
        Args:
            agent_id: Unique identifier for this agent
            prompt: Not used (deterministic agent), but kept for BaseAgent compatibility
            queue: Next agents in workflow
            **kwargs: Configuration parameters including:
                - params: Dict with max_depth, allow_reentrant_nodes, strict_tool_errors, execution_data
                - Or pass config directly via kwargs
        """
        super().__init__(agent_id=agent_id, prompt=prompt, queue=queue, **kwargs)
        
        # BaseAgent stores kwargs in self.params, so use that
        # Also check for "params" key which might contain nested config
        if "params" in self.params:
            config_params = self.params["params"]
        else:
            config_params = self.params
        
        # Extract validation config
        self.validator_config = {
            "max_depth": config_params.get("max_depth"),
            "allow_reentrant_nodes": config_params.get("allow_reentrant_nodes", []),
            "strict_tool_errors": config_params.get("strict_tool_errors", False),
        }
        
        # Initialize validator
        self.validator = ExecutionInvariantsValidator(self.validator_config)
        
        logger.info(
            f"Initialized InvariantValidatorAgent '{agent_id}' with config: {self.validator_config}"
        )

    async def _run_impl(self, ctx: "Context") -> Dict[str, Any]:
        """
        Async implementation required by BaseAgent.
        Delegates to synchronous process() method.
        """
        input_data = ctx.get("input", "") or ""
        return self.process(input_data)
    
    def process(self, input_data: str) -> Dict[str, Any]:
        """
        Execute invariant validation on execution data.
        
        Args:
            input_data: Not used directly (execution data comes from params.execution_data)
        
        Returns:
            Dict with validation results in compact facts format:
            {
                "fork_join_integrity": {"status": "PASS/FAIL", "violations": [...]},
                "routing_integrity": {"status": "PASS/FAIL", "violations": [...]},
                "cycle_detection": {"status": "PASS/FAIL", "cycles_found": [...], "violations": [...]},
                "tool_integrity": {"status": "PASS/FAIL", "violations": [...]},
                "schema_compliance": {"status": "PASS/FAIL", "violations": [...]},
                "depth_compliance": {"status": "PASS/FAIL", "violations": [...]},
                "critical_failures_detected": bool,
                "validation_summary": {
                    "total_violations": int,
                    "critical_count": int,
                    "warning_count": int,
                    "categories_failed": List[str]
                }
            }
        """
        logger.info(f"InvariantValidatorAgent '{self.agent_id}' starting validation")
        
        try:
            # Get execution data - first try from params, then from rendered prompt
            # Params are NOT template-rendered, but prompts ARE
            execution_data = None
            
            # Check params first (for programmatic usage)
            if "params" in self.params:
                execution_data = self.params["params"].get("execution_data")
            if not execution_data:
                execution_data = self.params.get("execution_data")
            
            # If not in params, extract from the rendered prompt (in context dict)
            if not execution_data and input_data:
                # input_data might be a dict with formatted_prompt, or a string
                prompt_text = None
                if isinstance(input_data, dict):
                    prompt_text = input_data.get("formatted_prompt") or input_data.get("input")
                elif isinstance(input_data, str):
                    prompt_text = input_data
                
                if prompt_text and isinstance(prompt_text, str):
                    # Look for EXECUTION_DATA_JSON marker in the rendered prompt
                    match = re.search(r'EXECUTION_DATA_JSON:\s*(.+)', prompt_text, re.DOTALL)
                    if match:
                        execution_data = match.group(1).strip()
                        logger.debug(f"Extracted execution_data from prompt: {execution_data[:200]}...")
            
            # Debug: log what we received
            logger.debug(f"InvariantValidatorAgent received execution_data type: {type(execution_data)}")
            if isinstance(execution_data, str):
                logger.debug(f"execution_data string preview: {execution_data[:200] if len(execution_data) > 200 else execution_data}")
            
            # Handle both dict and JSON string (for backward compatibility)
            if isinstance(execution_data, str):
                # Try to detect if it's Python repr format (single quotes) instead of JSON
                if execution_data.startswith("{'") or execution_data.startswith("{\'"): 
                    logger.warning("execution_data appears to be Python dict repr, not JSON. Attempting ast.literal_eval")
                    import ast
                    try:
                        execution_data = ast.literal_eval(execution_data)
                    except (ValueError, SyntaxError) as e:
                        logger.error(f"Failed to parse execution_data as Python literal: {e}")
                        return {
                            "status": "error",
                            "error": f"Invalid execution_data format: {str(e)}",
                            "facts": []
                        }
                else:
                    try:
                        execution_data = json.loads(execution_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse execution_data JSON: {e}")
                        logger.error(f"execution_data content: {execution_data[:500] if len(execution_data) > 500 else execution_data}")
                        return {
                            "status": "error",
                            "error": f"Invalid execution_data JSON: {str(e)}",
                            "facts": []
                        }
            
            if not execution_data:
                execution_data = {}  # Use empty dict for validation
                logger.warning(
                    f"InvariantValidatorAgent '{self.agent_id}': No execution_data provided, "
                    "validation will be limited"
                )
            
            # Run validation
            invariants = self.validator.validate(execution_data)
            
            # Convert to compact facts format
            facts = invariants.to_compact_facts()
            
            # Add summary statistics
            all_violations = invariants.all_violations
            critical_violations = [v for v in all_violations if v.severity == "error"]
            warning_violations = [v for v in all_violations if v.severity == "warning"]
            
            categories_failed = list(set(v.category for v in critical_violations))
            
            facts["validation_summary"] = {
                "total_violations": len(all_violations),
                "critical_count": len(critical_violations),
                "warning_count": len(warning_violations),
                "categories_failed": categories_failed,
                "validator_config": self.validator_config
            }
            
            # Log results
            if invariants.has_critical_failures:
                logger.error(
                    f"InvariantValidatorAgent '{self.agent_id}': {len(critical_violations)} "
                    f"critical violations detected in categories: {categories_failed}"
                )
                for violation in critical_violations[:5]:  # Log first 5
                    logger.error(f"  [{violation.category}] {violation.message}")
            else:
                logger.info(
                    f"InvariantValidatorAgent '{self.agent_id}': All invariants passed "
                    f"({len(warning_violations)} warnings)"
                )
            
            return facts
            
        except Exception as e:
            logger.error(
                f"InvariantValidatorAgent '{self.agent_id}' failed with error: {e}",
                exc_info=True
            )
            
            # Return error state as failed validation
            return {
                "fork_join_integrity": {"status": "ERROR", "violations": []},
                "routing_integrity": {"status": "ERROR", "violations": []},
                "cycle_detection": {"status": "ERROR", "cycles_found": [], "violations": []},
                "tool_integrity": {"status": "ERROR", "violations": []},
                "schema_compliance": {"status": "ERROR", "violations": []},
                "depth_compliance": {"status": "ERROR", "violations": []},
                "critical_failures_detected": True,
                "validation_summary": {
                    "total_violations": 1,
                    "critical_count": 1,
                    "warning_count": 0,
                    "categories_failed": ["validator_error"],
                    "error": str(e)
                }
            }
