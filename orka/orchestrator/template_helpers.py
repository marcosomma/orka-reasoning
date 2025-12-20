"""
Template Helper Functions for OrKa Workflows
============================================

This module provides custom Jinja2 filters and functions for use in OrKa workflow templates.
These helpers enable safe access to previous outputs, loop metadata, and other workflow context.

Usage in YAML templates:
    {{ safe_get_response('agent_name', 'default_value') }}
    {{ get_agent_response('agent_name') }}
    {{ safe_get(dict_variable, 'key', 'default') }}
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def safe_get(obj: Any, key: str, default: Any = "unknown") -> Any:
    """
    Safely get a value from a dict/object with a default fallback.
    
    Args:
        obj: Dictionary or object to access
        key: Key or attribute name
        default: Default value if key not found (default: "unknown")
    
    Returns:
        Value at key or default
    
    Example:
        {{ safe_get(previous_outputs.agent_name, 'result', 'No result') }}
    """
    if obj is None:
        return default
    
    if isinstance(obj, dict):
        return obj.get(key, default)
    
    return getattr(obj, key, default)


def safe_get_response(agent_id: str, default: str = "unknown", previous_outputs: Optional[Dict[str, Any]] = None) -> str:
    """
    Safely get the response from a previous agent.
    
    Args:
        agent_id: ID of the agent whose response to retrieve
        default: Default value if response not found
        previous_outputs: Dict of previous agent outputs (injected by context)
    
    Returns:
        Agent's response or default value
    
    Example:
        {{ safe_get_response('synthesis_attempt', 'No synthesis') }}
    """
    if previous_outputs is None:
        logger.warning(f"safe_get_response: previous_outputs is None for agent '{agent_id}'")
        return default
    
    if agent_id not in previous_outputs:
        logger.debug(f"safe_get_response: agent '{agent_id}' not found in previous_outputs")
        return default
    
    output = previous_outputs[agent_id]
    
    # Try different response fields
    if isinstance(output, dict):
        # Orchestrator log/event shape: payload.response / payload.result
        payload = output.get("payload")
        if isinstance(payload, dict):
            if "response" in payload:
                resp_val = payload["response"]
                # If payload.response is itself a dict with nested 'response', unwrap once
                if isinstance(resp_val, dict) and "response" in resp_val:
                    return str(resp_val["response"])
                return str(resp_val)
            if "result" in payload:
                res_val = payload["result"]
                if isinstance(res_val, dict) and "response" in res_val:
                    return str(res_val["response"])
                return str(res_val)

        # Check common response fields
        for key in ['response', 'result', 'output']:
            if key in output:
                value = output[key]
                # Handle nested response structures
                if isinstance(value, dict) and 'response' in value:
                    return str(value['response'])
                return str(value)
        
        # If no standard field, return the whole dict as string
        return str(output)
    
    # If not a dict, return as string
    return str(output)


def get_loop_output(agent_id: str, previous_outputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get the complete output dict from a LoopNode agent.
    
    Unlike safe_get_response which returns a string, this returns the full dict
    so you can access fields like loops_completed, final_score, past_loops, etc.
    
    Args:
        agent_id: ID of the loop agent
        previous_outputs: Dict of previous agent outputs
    
    Returns:
        Complete output dict from the loop, or empty dict if not found
    
    Example:
        {% set loop_data = get_loop_output('cognitive_debate_loop', previous_outputs) %}
        Rounds: {{ loop_data.loops_completed }}
        Score: {{ loop_data.final_score }}
    """
    if previous_outputs is None:
        logger.warning(f"get_loop_output: previous_outputs is None for agent '{agent_id}'")
        return {}
    
    if agent_id not in previous_outputs:
        logger.debug(f"get_loop_output: agent '{agent_id}' not found in previous_outputs")
        return {}
    
    output = previous_outputs[agent_id]
    
    # LoopNode wraps output in 'response' field
    if isinstance(output, dict) and 'response' in output:
        response_value = output['response']
        if isinstance(response_value, dict):
            return response_value
    
    # Fallback: return the output dict itself
    if isinstance(output, dict):
        return output
    
    logger.warning(f"get_loop_output: output for '{agent_id}' is not a dict: {type(output)}")
    return {}


def get_agent_response(agent_id: str, previous_outputs: Optional[Dict[str, Any]] = None) -> str:
    """
    Get the response from a previous agent (strict version).
    
    Args:
        agent_id: ID of the agent whose response to retrieve
        previous_outputs: Dict of previous agent outputs (injected by context)
    
    Returns:
        Agent's response or empty string
    
    Example:
        {{ get_agent_response('radical_progressive') }}
    """
    return safe_get_response(agent_id, "", previous_outputs)


def truncate_text(text: str, length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        length: Maximum length
        suffix: Suffix to add when truncated
    
    Returns:
        Truncated text
    
    Example:
        {{ some_long_text | truncate(150) }}
    """
    if text is None:
        return ""
    
    text_str = str(text)
    if len(text_str) <= length:
        return text_str
    
    return text_str[:length - len(suffix)] + suffix


def format_loop_metadata(past_loops: list, max_loops: int = 5) -> str:
    """
    Format past loop metadata for display in templates.
    
    Args:
        past_loops: List of past loop metadata dicts
        max_loops: Maximum number of loops to show
    
    Returns:
        Formatted string of loop history
    
    Example:
        {{ format_loop_metadata(get_past_loops(), 3) }}
    """
    if not past_loops:
        return "No previous loops"
    
    lines = []
    for i, loop in enumerate(past_loops[-max_loops:], 1):
        score = loop.get('score', 'N/A')
        status = loop.get('status', 'completed')
        lines.append(f"Loop {i}: score={score}, status={status}")
    
    return "\n".join(lines)


def get_debate_evolution(past_loops: Optional[list] = None) -> str:
    """
    Get a summary of how the debate evolved across loops.
    
    Args:
        past_loops: List of past loop metadata
    
    Returns:
        Summary string
    
    Example:
        {{ get_debate_evolution() }}
    """
    if not past_loops or len(past_loops) == 0:
        return "First round of debate"
    
    if len(past_loops) == 1:
        return f"Second round - previous score: {past_loops[0].get('score', 'N/A')}"
    
    scores = [loop.get('score', 0) for loop in past_loops]
    trend = "improving" if scores[-1] > scores[0] else "declining"
    
    return f"Round {len(past_loops) + 1} - debate {trend} (scores: {' → '.join(map(str, scores))})"


def register_template_helpers(env) -> None:
    """
    Register all template helpers as Jinja2 filters and globals.
    
    Args:
        env: Jinja2 Environment instance
    
    Usage:
        from jinja2 import Environment
        from orka.orchestrator.template_helpers import register_template_helpers
        
        env = Environment()
        register_template_helpers(env)
    """
    # Register filters
    env.filters['safe_get'] = safe_get
    env.filters['truncate'] = truncate_text
    env.filters['format_loop_metadata'] = format_loop_metadata
    
    # Register global functions (callable without filter syntax)
    env.globals['safe_get'] = safe_get
    env.globals['safe_get_response'] = safe_get_response
    env.globals['get_agent_response'] = get_agent_response
    env.globals['get_loop_output'] = get_loop_output
    env.globals['truncate_text'] = truncate_text
    env.globals['format_loop_metadata'] = format_loop_metadata
    env.globals['get_debate_evolution'] = get_debate_evolution
    
    logger.debug("Registered template helpers: safe_get, safe_get_response, get_agent_response, get_loop_output, truncate, format_loop_metadata, get_debate_evolution")
