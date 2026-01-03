# Template Rendering Fix for Local LLM Agents

## Issue Description

The template rendering system is failing when trying to access local LLM agent responses through templates like `{{ previous_outputs.radical_progressive.response }}`. The error occurs because the response structure doesn't match the expected template access pattern.

## Current Behavior

1. Local LLM agent returns response in format:
```python
{
    "response": "actual response text",
    "confidence": "0.9",
    "internal_reasoning": "reasoning text",
    "_metrics": {...},
    "formatted_prompt": "..."
}
```

2. This gets stored in `previous_outputs` but templates can't access it properly.

## Root Cause

The issue is in the `_ensure_complete_context` method in `execution_engine.py`. The method doesn't properly flatten the response structure to match the template access pattern.

## Proposed Fix

1. Modify `_ensure_complete_context` to properly handle local LLM agent responses:

```python
def _ensure_complete_context(self, previous_outputs):
    enhanced_outputs = {}
    
    for agent_id, agent_result in previous_outputs.items():
        # Start with the original result
        enhanced_outputs[agent_id] = agent_result
        
        # If the result is a dict, ensure it has a 'response' field
        if isinstance(agent_result, dict):
            # If response is directly in the result
            if "response" in agent_result:
                enhanced_outputs[agent_id] = {
                    **agent_result,  # Keep original structure
                    "response": agent_result["response"]  # Ensure response is accessible
                }
            # If response is nested in result.result
            elif "result" in agent_result and isinstance(agent_result["result"], dict):
                nested_result = agent_result["result"]
                if "response" in nested_result:
                    enhanced_outputs[agent_id] = {
                        **agent_result,  # Keep original structure
                        "response": nested_result["response"]  # Make response accessible
                    }
    
    return enhanced_outputs
```

2. This ensures that templates can access responses via:
   - `{{ previous_outputs.agent_id.response }}`
   - While preserving the full response structure

## Testing

Test cases should verify:
1. Template access works for local LLM agent responses
2. Template access works for memory agent responses
3. Template access works for other agent types
4. Original response structure is preserved
5. No regression in other template functionality

## Implementation Plan

1. Create unit tests for the new context handling
2. Implement the fix in `execution_engine.py`
3. Add debug logging for template context building
4. Update documentation for template access patterns
---
← [Template Filters](TEMPLATE_FILTERS.md) | [📚 INDEX](index.md) | [Json Inputs Guide](JSON_INPUTS.md) →
