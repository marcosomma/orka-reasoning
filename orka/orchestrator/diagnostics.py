"""Diagnostic utilities for troubleshooting OrKa workflows."""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def diagnose_template_variables(
    template_str: str,
    context: Dict[str, Any],
    agent_id: str
) -> List[str]:
    """
    Diagnose why template variables might be 'unknown'.
    
    Logs detailed information about:
    - What variables are referenced in the template
    - What variables are available in context
    - What's missing and why
    
    Returns:
        List of missing variable paths
    """
    # Extract variable references from template
    # Matches {{ variable }}, {{ dict.key }}, {{ dict['key'] }}
    var_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.\[\]\'\"]*)\s*(?:\|[^}]*)?\}\}'
    referenced_vars = re.findall(var_pattern, template_str)
    
    logger.debug(f"[{agent_id}] Template diagnostic:")
    logger.debug(f"  Template length: {len(template_str)} chars")
    logger.debug(f"  Referenced variables: {referenced_vars[:10]}...")  # Show first 10
    logger.debug(f"  Available context keys: {list(context.keys())}")
    
    # Check each referenced variable
    missing_vars = []
    for var in referenced_vars:
        # Handle nested access like 'agent.result'
        parts = var.replace('[', '.').replace(']', '').replace("'", "").replace('"', '').split('.')
        
        current = context
        path = []
        for part in parts:
            path.append(part)
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                missing_vars.append('.'.join(path))
                logger.warning(
                    f"  ❌ Missing: {'.'.join(path)}\n"
                    f"     Available at this level: {list(current.keys()) if isinstance(current, dict) else type(current).__name__}"
                )
                break
        else:
            # Truncate long values
            value_str = str(current)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            logger.debug(f"  ✅ Found: {var} = {value_str}")
    
    if missing_vars:
        logger.error(
            f"[{agent_id}] Template has {len(missing_vars)} missing variables: {missing_vars[:5]}\n"
            f"This will cause 'unknown' values in the rendered prompt."
        )
    else:
        logger.debug(f"[{agent_id}] All template variables resolved successfully")
    
    return missing_vars


def log_previous_outputs_structure(previous_outputs: Dict[str, Any], agent_id: str) -> None:
    """Log the structure of previous_outputs for debugging."""
    if not previous_outputs:
        logger.debug(f"[{agent_id}] Previous outputs: EMPTY")
        return
    
    logger.debug(f"[{agent_id}] Previous outputs structure:")
    
    for prev_agent_id, output in previous_outputs.items():
        if isinstance(output, dict):
            keys = list(output.keys())
            logger.debug(f"  {prev_agent_id}: dict with keys {keys}")
            
            # Show nested structure for common keys
            for key in ['result', 'response', 'joined_results', 'status']:
                if key in output:
                    value = output[key]
                    if isinstance(value, dict):
                        nested_keys = list(value.keys())[:5]  # First 5 keys
                        logger.debug(f"    {key}: dict with keys {nested_keys}...")
                    elif isinstance(value, list):
                        logger.debug(f"    {key}: list with {len(value)} items")
                    else:
                        value_str = str(value)
                        if len(value_str) > 50:
                            value_str = value_str[:50] + "..."
                        logger.debug(f"    {key}: {type(value).__name__} = {value_str}")
        else:
            value_str = str(output)
            if len(value_str) > 50:
                value_str = value_str[:50] + "..."
            logger.debug(f"  {prev_agent_id}: {type(output).__name__} = {value_str}")


def validate_template_context(
    template_str: str,
    context: Dict[str, Any],
    agent_id: str
) -> Dict[str, Any]:
    """
    Validate that all required template variables are available in context.
    
    Returns:
        Dict with:
        - is_valid: bool
        - missing_vars: List[str]
        - warnings: List[str]
    """
    missing_vars = diagnose_template_variables(template_str, context, agent_id)
    
    result = {
        "is_valid": len(missing_vars) == 0,
        "missing_vars": missing_vars,
        "warnings": []
    }
    
    # Check for common issues
    if "previous_outputs" not in context:
        result["warnings"].append("previous_outputs missing from context")
    
    if "input" not in context:
        result["warnings"].append("input missing from context")
    
    # Check if previous_outputs is empty but template expects it
    if context.get("previous_outputs") == {} and "previous_outputs." in template_str:
        result["warnings"].append("previous_outputs is empty but template references it")
    
    return result
